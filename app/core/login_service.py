# -*- coding: utf-8 -*-
"""
登录服务 - 调用 media_crawler 的登录功能
"""
import asyncio
import sys
import os
import uuid
from pathlib import Path
from typing import Dict, Optional, Any
from contextlib import contextmanager

from playwright.async_api import async_playwright, BrowserContext, Page

# 添加media_crawler到路径
MEDIA_CRAWLER_PATH = Path(__file__).parent.parent.parent.parent / "media_crawler"
sys.path.insert(0, str(MEDIA_CRAWLER_PATH))

from app.providers.logger import get_logger
from tools import utils as crawler_utils


@contextmanager
def working_directory(path: Path):
    """临时切换工作目录的上下文管理器"""
    original_cwd = os.getcwd()
    try:
        os.chdir(str(path))
        yield
    finally:
        os.chdir(original_cwd)


class LoginService:
    """登录服务"""

    def __init__(self) -> None:
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.playwright_instance: Optional[Any] = None
        self.browser: Optional[Any] = None

    async def start_login(
        self,
        platform: str,
        login_type: str,
        phone: str = "",
        cookie: str = ""
    ) -> Dict[str, Any]:
        """
        启动登录流程

        Args:
            platform: 平台代码 (xhs, dy, ks, etc.)
            login_type: 登录方式 (qrcode, phone, cookie)
            phone: 手机号（phone登录时需要）
            cookie: Cookie字符串（cookie登录时需要）

        Returns:
            登录会话信息
        """
        session_id = f"{platform}_{login_type}_{uuid.uuid4().hex[:8]}"

        get_logger().info(f"[LoginService] 启动登录: {session_id}")

        # 初始化会话
        session = {
            "session_id": session_id,
            "platform": platform,
            "login_type": login_type,
            "status": "initializing",
            "message": "正在初始化登录...",
            "qr_code_base64": None
        }
        self.sessions[session_id] = session

        # 异步启动登录流程
        asyncio.create_task(self._login_flow(session_id, platform, login_type, phone, cookie))

        # 如果是二维码登录，等待二维码生成
        if login_type == "qrcode":
            # 最多等待10秒获取二维码
            for _ in range(20):  # 20 * 0.5 = 10秒
                await asyncio.sleep(0.5)
                session = self.sessions.get(session_id, session)
                if session.get("qr_code_base64") or session.get("status") in ["failed", "expired"]:
                    break

        return session

    async def _login_flow(
        self,
        session_id: str,
        platform: str,
        login_type: str,
        phone: str,
        cookie: str
    ) -> None:
        """登录流程（异步执行）"""
        try:
            session = self.sessions[session_id]

            # 初始化浏览器
            if not self.playwright_instance:
                self.playwright_instance = await async_playwright().start()
                self.browser = await self.playwright_instance.chromium.launch(
                    headless=False
                )

            # 平台URL映射
            platform_urls = {
                "xhs": "https://www.xiaohongshu.com",
                "dy": "https://www.douyin.com",
                "ks": "https://www.kuaishou.com",
                "bili": "https://www.bilibili.com",
                "wb": "https://weibo.com",
                "tieba": "https://tieba.baidu.com",
                "zhihu": "https://www.zhihu.com"
            }

            url = platform_urls.get(platform)
            if not url:
                session["status"] = "failed"
                session["message"] = f"不支持的平台: {platform}"
                return

            # 创建浏览器上下文（持久化，保存登录态）
            user_data_dir = Path(__file__).parent.parent.parent.parent / "browser_data" / platform
            user_data_dir.mkdir(parents=True, exist_ok=True)

            browser_context = await self.playwright_instance.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=False,
                viewport={"width": 1920, "height": 1080},
                user_agent=crawler_utils.get_user_agent()
            )

            # 添加stealth脚本
            stealth_js = Path(__file__).parent.parent.parent.parent / "media_crawler" / "libs" / "stealth.min.js"
            if stealth_js.exists():
                await browser_context.add_init_script(path=str(stealth_js))

            page = await browser_context.new_page()

            # 访问平台
            get_logger().info(f"[LoginService] 访问平台: {url}")
            await page.goto(url)
            await asyncio.sleep(2)

            # 根据登录类型处理
            if login_type == "qrcode":
                await self._handle_qrcode_login(session_id, platform, browser_context, page)
            elif login_type == "cookie":
                await self._handle_cookie_login(session_id, platform, browser_context, page, cookie)
            else:
                session["status"] = "failed"
                session["message"] = f"不支持的登录类型: {login_type}"

        except Exception as e:
            get_logger().error(f"[LoginService] 登录流程失败: {e}")
            self.sessions[session_id]["status"] = "failed"
            self.sessions[session_id]["message"] = str(e)

    async def _handle_qrcode_login(
        self,
        session_id: str,
        platform: str,
        browser_context: BrowserContext,
        page: Page
    ) -> None:
        """处理二维码登录"""
        try:
            session = self.sessions[session_id]

            # 在media_crawler目录下执行
            with working_directory(MEDIA_CRAWLER_PATH):
                # 不同平台的二维码选择器
                qrcode_selectors = {
                    "xhs": "xpath=//img[@class='qrcode-img']",
                    "dy": "xpath=//img[@class='web-login-scan-code__content__qrcode-img']",
                    "bili": "xpath=//img[@class='qrcode-img']",
                    "wb": "xpath=//img[@class='qrcode']",
                    "tieba": "xpath=//img[@class='tang-pass-qrcode-img']",
                    "zhihu": "xpath=//div[@class='qrcode']//canvas",
                    "ks": "xpath=//div[@class='qrcode']//canvas"
                }

                selector = qrcode_selectors.get(platform, "xpath=//img[contains(@class, 'qrcode')]")

                # 尝试点击登录按钮（某些平台需要）
                try:
                    if platform == "xhs":
                        login_btn = await page.wait_for_selector(
                            "xpath=//*[@id='app']/div[1]/div[2]/div[1]/ul/div[1]/button",
                            timeout=3000
                        )
                        if login_btn:
                            await login_btn.click()
                            await asyncio.sleep(1)
                except Exception:
                    pass

                # 获取二维码
                get_logger().info(f"[LoginService] 获取二维码: {platform}")

                if "canvas" in selector:
                    base64_qrcode = await crawler_utils.find_qrcode_img_from_canvas(page, selector)
                else:
                    base64_qrcode = await crawler_utils.find_login_qrcode(page, selector)

            if base64_qrcode:
                # 确保base64格式正确（去掉data:image前缀）
                if "," in base64_qrcode:
                    base64_qrcode = base64_qrcode.split(",")[1]

                session["qr_code_base64"] = base64_qrcode
                session["status"] = "qr_ready"
                session["message"] = "二维码已生成，请扫码登录"
                get_logger().info(f"[LoginService] 二维码获取成功: {session_id}")

                # 启动登录状态检查
                asyncio.create_task(self._check_login_status(session_id, platform, browser_context, page))
            else:
                session["status"] = "failed"
                session["message"] = "无法获取二维码"

        except Exception as e:
            get_logger().error(f"[LoginService] 获取二维码失败: {e}")
            self.sessions[session_id]["status"] = "failed"
            self.sessions[session_id]["message"] = f"获取二维码失败: {str(e)}"

    async def _handle_cookie_login(
        self,
        session_id: str,
        platform: str,
        browser_context: BrowserContext,
        page: Page,
        cookie: str
    ) -> None:
        """处理Cookie登录"""
        try:
            session = self.sessions[session_id]

            # 解析并添加Cookie
            cookie_dict = crawler_utils.convert_str_cookie_to_dict(cookie)

            # 根据平台添加关键Cookie
            platform_domains = {
                "xhs": ".xiaohongshu.com",
                "dy": ".douyin.com",
                "ks": ".kuaishou.com",
                "bili": ".bilibili.com",
                "wb": ".weibo.com",
                "tieba": ".baidu.com",
                "zhihu": ".zhihu.com"
            }

            domain = platform_domains.get(platform, "")

            for key, value in cookie_dict.items():
                await browser_context.add_cookies([{
                    'name': key,
                    'value': value,
                    'domain': domain,
                    'path': "/"
                }])

            # 刷新页面验证登录
            await page.reload()
            await asyncio.sleep(2)

            # 检查登录状态
            cookies = await browser_context.cookies()
            cookie_dict = {c['name']: c['value'] for c in cookies}

            # 根据平台检查特定Cookie
            platform_cookies = {
                "xhs": "web_session",
                "dy": "sessionid",
                "bili": "SESSDATA",
                "wb": "SUB",
                "tieba": "BDUSS",
                "zhihu": "z_c0",
                "ks": "kpf"
            }

            cookie_name = platform_cookies.get(platform)
            if cookie_name and cookie_dict.get(cookie_name):
                session["status"] = "logged_in"
                session["message"] = "登录成功"
                get_logger().info(f"[LoginService] Cookie登录成功: {session_id}")
            else:
                session["status"] = "failed"
                session["message"] = "Cookie无效或已过期"

        except Exception as e:
            get_logger().error(f"[LoginService] Cookie登录失败: {e}")
            self.sessions[session_id]["status"] = "failed"
            self.sessions[session_id]["message"] = f"Cookie登录失败: {str(e)}"

    async def _check_login_status(
        self,
        session_id: str,
        platform: str,
        browser_context: BrowserContext,
        page: Page
    ) -> None:
        """检查登录状态（轮询）"""
        max_wait_time = 120  # 最长等待120秒
        check_interval = 2  # 每2秒检查一次

        try:
            session = self.sessions[session_id]

            for _ in range(max_wait_time // check_interval):
                await asyncio.sleep(check_interval)

                if session["status"] != "qr_ready":
                    break

                # 检查Cookie变化
                cookies = await browser_context.cookies()
                cookie_dict = {c['name']: c['value'] for c in cookies}

                # 根据平台检查特定Cookie
                platform_cookies = {
                    "xhs": "web_session",
                    "dy": "sessionid",
                    "bili": "SESSDATA",
                    "wb": "SUB",
                    "tieba": "BDUSS",
                    "zhihu": "z_c0",
                    "ks": "kpf"
                }

                cookie_name = platform_cookies.get(platform)
                if cookie_name and cookie_dict.get(cookie_name):
                    session["status"] = "logged_in"
                    session["message"] = "登录成功！登录态已保存"
                    get_logger().info(f"[LoginService] 登录成功: {session_id}")
                    break

            # 超时
            if session["status"] == "qr_ready":
                session["status"] = "expired"
                session["message"] = "二维码已过期，请重新获取"
                get_logger().info(f"[LoginService] 二维码过期: {session_id}")

        except Exception as e:
            get_logger().error(f"[LoginService] 检查登录状态失败: {e}")
            self.sessions[session_id]["status"] = "failed"
            self.sessions[session_id]["message"] = str(e)

    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话状态"""
        return self.sessions.get(session_id)

    async def cleanup(self) -> None:
        """清理资源"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright_instance:
            await self.playwright_instance.stop()
            self.playwright_instance = None
        get_logger().info("[LoginService] 资源已清理")


# 全局单例
login_service = LoginService()
