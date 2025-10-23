# -*- coding: utf-8 -*-
"""小红书登录完整实现"""

import asyncio
import functools
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, Any

from playwright.async_api import BrowserContext, Page, async_playwright
from tenacity import retry, retry_if_result, stop_after_attempt, wait_fixed

from app.config.settings import Platform, global_settings
from app.core.login.base import AbstractLogin
from app.core.login.models import LoginSession, LoginStartPayload, PlatformLoginState
from app.core.crawler.tools import crawler_util
from app.providers.logger import get_logger
from app.core.login.browser_manager import get_browser_manager

logger = get_logger()
browser_manager = get_browser_manager()


class XiaoHongShuLogin(AbstractLogin):
    """小红书登录完整实现类"""

    def __init__(self, service, login_type: str, browser_context: BrowserContext, 
                 context_page: Page, login_phone: Optional[str] = "", cookie_str: str = ""):
        super().__init__(service, login_type, browser_context, context_page, login_phone, cookie_str)
        self.playwright = None
        # 配置参数
        browser_cfg = global_settings.browser
        self._headless = browser_cfg.headless
        self._user_agent = browser_cfg.user_agent or crawler_util.get_user_agent()
        self._viewport = {
            "width": browser_cfg.viewport_width,
            "height": browser_cfg.viewport_height,
        }

    @property
    def platform(self) -> str:
        return Platform.XIAOHONGSHU.value

    @property
    def display_name(self) -> str:
        return "小红书"

    @property
    def user_data_dir(self) -> Path:
        return Path("browser_data") / self.platform

    async def begin(self) -> None:
        """开始登录流程"""
        logger.info(f"[xhs.login] begin login type={self.login_type}")
        if self.login_type == "cookie":
            await self.login_by_cookies()
            return
        if self.login_type == "phone":
            raise NotImplementedError("phone login 未实现，请使用二维码或 Cookie")
        await self.login_by_qrcode()

    async def login_by_qrcode(self, wait_for_scan: bool = True):
        """
        二维码登录实现

        Args:
            wait_for_scan: 是否等待扫码完成（默认True用于兼容旧流程，False用于新的异步流程）
        """
        selector = "xpath=//img[@class='qrcode-img']"

        # 等待二维码图片加载完成（最多等待10秒）
        try:
            await self.context_page.wait_for_selector(selector, timeout=10000)
            # 额外等待一下确保图片完全加载
            await asyncio.sleep(1)
        except Exception as exc:
            logger.warning(f"[xhs.login] 等待二维码元素出现失败: {exc}")

        base64_qrcode = await crawler_util.find_login_qrcode(self.context_page, selector)
        if not base64_qrcode:
            try:
                login_button = self.context_page.locator(
                    "xpath=//*[@id='app']/div[1]/div[2]/div[1]/ul/div[1]/button"
                )
                await login_button.click()
                # 点击后等待二维码出现
                await asyncio.sleep(2)
                base64_qrcode = await crawler_util.find_login_qrcode(self.context_page, selector)
            except Exception as exc:
                logger.warning(f"[xhs.login] 展示二维码失败: {exc}")

        if not base64_qrcode:
            raise RuntimeError("未能获取小红书登录二维码")

        logger.info(f"[xhs.login] 二维码获取成功，长度: {len(base64_qrcode)}")

        # 保存二维码base64数据供前端显示（而不是弹窗显示）
        self.qr_code_base64 = base64_qrcode

        # 如果需要等待扫码，则执行阻塞等待
        if wait_for_scan:
            cookies = await self.browser_context.cookies()
            _, cookie_dict = crawler_util.convert_cookies(cookies)
            before_session = cookie_dict.get("web_session")

            await self._wait_login_state(before_session)
            await asyncio.sleep(5)

    async def login_by_mobile(self):
        """手机号登录 - 暂未实现"""
        raise NotImplementedError("phone login 未实现")

    async def login_by_cookies(self):
        """Cookie登录实现"""
        cookie_dict = crawler_util.convert_str_cookie_to_dict(self.cookie_str)
        if not cookie_dict.get("web_session"):
            raise ValueError("提供的 Cookie 缺少 web_session")

        await self.browser_context.add_cookies(
            [
                {
                    "name": name,
                    "value": value,
                    "domain": ".xiaohongshu.com",
                    "path": "/",
                }
                for name, value in cookie_dict.items()
            ]
        )

    async def has_valid_cookie(self) -> bool:
        """检查是否有有效的Cookie"""
        try:
            cookies = await self.browser_context.cookies()
            _, cookie_dict = crawler_util.convert_cookies(cookies)

            # 首先检查关键 Cookie 是否存在
            if not cookie_dict.get("web_session"):
                logger.info(f"[xhs.login] web_session 不存在")
                return False

            # 尝试通过 API 验证登录状态
            try:
                # 构建临时客户端来验证
                from app.core.crawler.platforms.xhs.client import XiaoHongShuClient
                cookie_str = ";".join(f"{k}={v}" for k, v in cookie_dict.items())
                headers = {
                    "User-Agent": self._user_agent,
                    "Cookie": cookie_str,
                }
                client = XiaoHongShuClient(
                    playwright_page=self.context_page,
                    cookie_dict=cookie_dict,
                    headers=headers,
                    proxy=None,
                    timeout=10,
                )
                is_valid = await client.pong()
                logger.info(f"[xhs.login] API 验证结果: {is_valid}")
                return is_valid
            except Exception as api_exc:
                logger.warning(f"[xhs.login] API 验证失败: {api_exc}，使用 Cookie 存在性判断")
                # API 验证失败时，基于 Cookie 存在性判断（保守处理）
                return True

        except Exception as exc:
            logger.warning(f"[xhs.login] 检查Cookie失败: {exc}")
            return False

    async def fetch_login_state(self) -> PlatformLoginState:
        """获取当前登录状态"""
        data_dir = self.user_data_dir
        if not data_dir.exists():
            return await self.create_failed_state("浏览器数据不存在")

        browser_context: Optional[BrowserContext] = None
        playwright: Optional[any] = None
        try:
            # 使用浏览器管理器获取临时上下文
            browser_context, playwright = await browser_manager.get_context_for_check(
                platform=self.platform,
                user_data_dir=data_dir,
                headless=True,
                viewport=self._viewport,
                user_agent=self._user_agent,
            )

            cookies = await browser_context.cookies()
            cookie_str, cookie_dict = crawler_util.convert_cookies(cookies)
            is_logged_in = bool(cookie_dict.get("web_session"))

            if is_logged_in:
                user_info = {
                    "web_session": cookie_dict.get("web_session", "")[:20] + "..."
                }
                return await self.create_success_state(cookie_str, cookie_dict, user_info)
            else:
                return await self.create_failed_state("未登录")

        except Exception as exc:
            logger.error("[xhs.login] 检查登录状态失败: %s", exc)
            return await self.create_failed_state(f"状态检查失败: {exc}")
        finally:
            if browser_context:
                try:
                    await browser_context.close()
                except Exception:
                    pass
            if playwright:
                try:
                    await playwright.stop()
                except Exception:
                    pass

    @retry(stop=stop_after_attempt(120), wait=wait_fixed(1), retry=retry_if_result(lambda result: result is False))
    async def _wait_login_state(self, before_session: Optional[str]) -> bool:
        """等待登录状态变化"""
        cookies = await self.browser_context.cookies()
        _, cookie_dict = crawler_util.convert_cookies(cookies)
        current_session = cookie_dict.get("web_session")
        if current_session and current_session != before_session:
            logger.info("[xhs.login] 登录状态已更新")
            return True
        return False


# === 登录服务接口实现 ===

async def start_login(service, session: LoginSession, payload: LoginStartPayload) -> Dict[str, Any]:
    """启动登录流程"""
    session.status = "starting"
    session.message = "启动小红书登录流程"
    await service.persist_session(session)

    # 检查现有登录状态（仅在非Cookie登录且非二维码登录时）
    cookie_candidate = (payload.cookie or "").strip()

    # 如果是二维码登录，则跳过现有状态检查，直接生成新二维码
    # 如果已提供Cookie，则尝试Cookie登录
    # 如果什么都没提供，才检查现有状态
    if not cookie_candidate and payload.login_type != "qrcode":
        try:
            current_state = await service.refresh_platform_state(session.platform, force=False)
        except Exception as exc:
            current_state = None
            logger.warning(f"[登录管理] 检查现有登录状态失败，继续登录流程: {exc}")
        else:
            if current_state and current_state.is_logged_in:
                session.status = "success"
                session.message = "已检测到登录状态，无需重新登录"
                session.metadata["cookie_dict"] = current_state.cookie_dict
                session.metadata["cookie_str"] = current_state.cookie_str
                await service.persist_session(session)
                return session.to_public_dict()

    # 使用浏览器管理器启动浏览器
    user_data_dir = get_user_data_dir()
    browser_cfg = global_settings.browser
    viewport = {"width": browser_cfg.viewport_width, "height": browser_cfg.viewport_height}

    try:
        browser_context, context_page, playwright = await browser_manager.acquire_context(
            platform=Platform.XIAOHONGSHU.value,
            user_data_dir=user_data_dir,
            headless=browser_cfg.headless,
            viewport=viewport,
            user_agent=browser_cfg.user_agent or crawler_util.get_user_agent(),
        )

        # 导航到小红书首页
        await context_page.goto("https://www.xiaohongshu.com")

    except Exception as exc:
        logger.error(f"[登录管理] 获取浏览器实例失败: {exc}")
        session.status = "failed"
        session.message = f"浏览器启动失败: {exc}"
        await service.persist_session(session)
        return session.to_public_dict()

    # 创建登录对象
    login_obj = XiaoHongShuLogin(
        service=service,
        login_type=payload.login_type,
        browser_context=browser_context,
        context_page=context_page,
        login_phone=payload.phone,
        cookie_str=payload.cookie,
    )
    login_obj.playwright = playwright

    session.browser_context = browser_context
    session.context_page = context_page
    session.playwright = playwright
    session.runtime["login_obj"] = login_obj

    try:
        # 处理Cookie登录
        if cookie_candidate:
            success = await _handle_cookie_login(session, login_obj, cookie_candidate, payload, service)
            if success:
                await browser_manager.release_context(Platform.XIAOHONGSHU.value, keep_alive=True)
                return session.to_public_dict()

        # 处理二维码登录
        if payload.login_type == "qrcode" or session.login_type == "qrcode":
            await _handle_qrcode_login(session, login_obj, payload, service)
        else:
            # 其他登录类型
            await _handle_other_login(session, login_obj, service)

        return session.to_public_dict()

    except Exception as exc:
        logger.error("[xhs.login] 登录失败: %s", exc)
        session.status = "failed"
        session.message = str(exc) or "登录失败"
        await service.persist_session(session)
        await _cleanup_browser_resources(session)
        await browser_manager.release_context(Platform.XIAOHONGSHU.value, keep_alive=False)
        return session.to_public_dict()


async def _handle_cookie_login(session: LoginSession, login_obj: XiaoHongShuLogin, 
                             cookie_candidate: str, payload: LoginStartPayload, service) -> bool:
    """处理Cookie登录"""
    session.login_type = "cookie"
    session.status = "processing"
    session.message = "检测到 Cookie，正在尝试 Cookie 登录..."
    await service.persist_session(session)

    login_obj.cookie_str = cookie_candidate
    try:
        await login_obj.login_by_cookies()
        
        # 验证登录状态
        login_success = await login_obj.has_valid_cookie()
        
        if login_success:
            await _save_login_success(session, login_obj, service)
            return True

        # Cookie登录失败，如果原始请求是二维码登录，则回退
        if payload.login_type == "qrcode":
            logger.info(f"[登录管理] Cookie 登录失败，回退到二维码登录: session_id={session.id}")
            session.login_type = "qrcode"
            session.status = "started"
            session.message = "Cookie 登录失败，正在生成二维码..."
            return False
        else:
            session.status = "failed"
            session.message = "Cookie 登录失败，Cookie 可能已失效"
            await service.persist_session(session)
            await _cleanup_browser_resources(session)
            return True

    except Exception as exc:
        if payload.login_type == "qrcode":
            session.login_type = "qrcode"
            session.status = "started"
            session.message = "Cookie 验证失败，正在生成二维码..."
            return False
        else:
            session.status = "failed"
            session.message = f"Cookie 登录失败: {exc}"
            await service.persist_session(session)
            await _cleanup_browser_resources(session)
            return True


async def _handle_qrcode_login(session: LoginSession, login_obj: XiaoHongShuLogin,
                             payload: LoginStartPayload, service):
    """处理二维码登录"""
    login_obj.login_type = "qrcode"
    session.status = "started"
    session.message = "正在生成二维码..."
    session.qrcode_timestamp = time.time()

    # 获取当前的 web_session，用于后续判断是否发生了变化
    cookies_before = await session.browser_context.cookies()
    _, cookie_dict_before = crawler_util.convert_cookies(cookies_before)
    before_session = cookie_dict_before.get("web_session")

    logger.info(f"[xhs.login] 二维码登录开始，当前 web_session: {before_session[:20] if before_session else 'None'}...")

    try:
        # 不等待扫码完成，直接获取二维码后返回
        await login_obj.login_by_qrcode(wait_for_scan=False)

        # 获取二维码base64数据并传递到session
        if hasattr(login_obj, 'qr_code_base64') and login_obj.qr_code_base64:
            session.qr_code_base64 = login_obj.qr_code_base64
            session.status = "waiting"
            session.message = "二维码已生成，等待扫码..."
            await service.persist_session(session)

            # 启动轮询任务
            async def _poll_qrcode():
                try:
                    timeout_seconds = 180
                    poll_interval = 2.0
                    start_ts = time.time()

                    while True:
                        # 检查 web_session 是否发生了变化（说明用户扫码登录了）
                        cookies_current = await session.browser_context.cookies()
                        _, cookie_dict_current = crawler_util.convert_cookies(cookies_current)
                        current_session = cookie_dict_current.get("web_session")

                        # 只有当 web_session 发生变化时，才认为登录成功
                        if current_session and current_session != before_session:
                            logger.info(f"[xhs.login] 检测到登录状态变化: {before_session[:20] if before_session else 'None'} -> {current_session[:20]}...")
                            await _save_login_success(session, login_obj, service)
                            break

                        if time.time() - start_ts > timeout_seconds:
                            session.status = "expired"
                            session.message = "二维码已过期，请重新获取"
                            await service.persist_session(session)
                            break

                        await asyncio.sleep(poll_interval)
                except Exception as exc:
                    session.status = "failed"
                    session.message = f"登录失败: {exc}"
                    await service.persist_session(session)
                finally:
                    await asyncio.sleep(2)
                    await _cleanup_browser_resources(session)

            task = asyncio.create_task(_poll_qrcode())
            session.runtime["task"] = task
        else:
            session.status = "failed"
            session.message = "二维码生成失败，请重新开始登录"
            await service.persist_session(session)
            await _cleanup_browser_resources(session)

    except Exception as exc:
        session.status = "failed"
        session.message = f"二维码登录失败: {exc}"
        await service.persist_session(session)
        await _cleanup_browser_resources(session)


async def _handle_other_login(session: LoginSession, login_obj: XiaoHongShuLogin, service):
    """处理其他登录方式"""
    session.status = "processing"
    session.message = "正在尝试登录..."
    session.qrcode_timestamp = 0.0

    async def _execute_login():
        try:
            await login_obj.begin()
            await _save_login_success(session, login_obj, service)
        except Exception as exc:
            session.status = "failed"
            session.message = f"登录失败: {exc}"
            await service.persist_session(session)
        finally:
            await asyncio.sleep(3)
            await _cleanup_browser_resources(session)

    task = asyncio.create_task(_execute_login())
    session.runtime["task"] = task
    await service.persist_session(session)


async def _save_login_success(session: LoginSession, login_obj: XiaoHongShuLogin, service):
    """保存登录成功状态"""
    session.status = "success"
    session.message = "登录成功"
    
    try:
        cookies = await session.browser_context.cookies()
        cookie_str, cookie_dict = crawler_util.convert_cookies(cookies)
    except Exception:
        cookie_str, cookie_dict = "", {}

    session.metadata["cookie_dict"] = cookie_dict
    session.metadata["cookie_str"] = cookie_str

    # 保存平台状态
    is_logged_in = bool(cookie_dict.get("web_session"))
    user_info = {
        "web_session": cookie_dict.get("web_session", "")[:20] + "..."
    } if is_logged_in else {}

    if is_logged_in:
        state = await login_obj.create_success_state(cookie_str, cookie_dict, user_info)
    else:
        state = await login_obj.create_failed_state("登录成功但未获取到有效Cookie")

    await service.persist_session(session)
    await service._storage.save_platform_state(state)
    await _cleanup_browser_resources(session)


async def _save_login_failure(session: LoginSession, login_obj: XiaoHongShuLogin, service):
    """保存登录失败状态"""
    try:
        cookies = await session.browser_context.cookies()
        cookie_str, cookie_dict = crawler_util.convert_cookies(cookies)
    except Exception:
        cookie_str, cookie_dict = "", {}

    # 保存失败状态
    state = await login_obj.create_failed_state(session.message)
    state.cookie_str = cookie_str
    state.cookie_dict = cookie_dict

    await service.persist_session(session)
    await service._storage.save_platform_state(state)
    await _cleanup_browser_resources(session)


async def _cleanup_browser_resources(session: LoginSession):
    """清理浏览器资源"""
    if session.browser_context:
        try:
            # 注意：不关闭 browser_context，因为它由 browser_manager 管理
            # await session.browser_context.close()
            session.browser_context = None
        except Exception:
            pass
    if session.playwright:
        try:
            # 注意：不停止 playwright，因为它由 browser_manager 管理
            # await session.playwright.stop()
            session.playwright = None
        except Exception:
            pass


async def fetch_login_state(service) -> PlatformLoginState:
    """获取登录状态 - 服务接口"""
    user_data_dir = get_user_data_dir()
    if not user_data_dir.exists():
        return PlatformLoginState(
            platform=Platform.XIAOHONGSHU.value,
            is_logged_in=False,
            message="浏览器数据不存在",
            last_checked_at=time.time()
        )

    browser_context: Optional[BrowserContext] = None
    playwright: Optional[any] = None
    try:
        browser_cfg = global_settings.browser
        viewport = {"width": browser_cfg.viewport_width, "height": browser_cfg.viewport_height}

        # 使用浏览器管理器获取临时上下文
        browser_context, playwright = await browser_manager.get_context_for_check(
            platform=Platform.XIAOHONGSHU.value,
            user_data_dir=user_data_dir,
            headless=True,
            viewport=viewport,
            user_agent=browser_cfg.user_agent or crawler_util.get_user_agent(),
        )

        context_page = await browser_context.new_page()

        # 创建临时登录对象进行状态检查
        temp_login = XiaoHongShuLogin(
            service=service,
            login_type="temp",
            browser_context=browser_context,
            context_page=context_page
        )
        temp_login.playwright = playwright

        return await temp_login.fetch_login_state()

    finally:
        if 'context_page' in locals():
            try:
                await context_page.close()
            except Exception:
                pass
        if browser_context:
            try:
                await browser_context.close()
            except Exception:
                pass
        if playwright:
            try:
                await playwright.stop()
            except Exception:
                pass


async def logout(service) -> None:
    """退出登录 - 服务接口"""
    await service.cleanup_platform_sessions(Platform.XIAOHONGSHU.value, drop=True)

    # 强制清理浏览器管理器中的实例
    await browser_manager.force_cleanup(Platform.XIAOHONGSHU.value)

    data_dir = get_user_data_dir()
    if data_dir.exists():
        try:
            await asyncio.to_thread(shutil.rmtree, data_dir, ignore_errors=True)
        except Exception as exc:
            logger.warning(f"[登录管理] 清理浏览器数据目录失败: {exc}")


def get_user_data_dir() -> Path:
    """获取用户数据目录"""
    return Path("browser_data") / Platform.XIAOHONGSHU.value


# 向后兼容的常量
DISPLAY_NAME = "小红书"
