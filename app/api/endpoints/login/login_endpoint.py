# -*- coding: utf-8 -*-
"""
登录服务端点 - 平台登录管理API（重构版）

使用直接调用模式，不再依赖 login_service
"""
import asyncio
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from pydantic import BaseModel

from app.api.endpoints.base import BaseEndpoint
from app.providers.logger import get_logger
from app.config.settings import global_settings, Platform

# 用于存储临时登录会话
_login_sessions: Dict[str, Dict[str, Any]] = {}


class LoginRequest(BaseModel):
    """登录请求"""
    platform: str
    login_type: str = "qrcode"  # qrcode, phone, cookie
    phone: str = ""
    cookie: str = ""


class LoginStatusResponse(BaseModel):
    """登录状态响应"""
    platform: str
    is_logged_in: bool
    user_info: Dict[str, Any] = {}
    message: str = ""


class LoginEndpoint(BaseEndpoint):
    """登录服务端点"""

    # 登录状态缓存（减少浏览器启动次数）
    _login_status_cache: Dict[str, tuple] = {}  # {platform: (is_logged_in, user_info, timestamp)}
    _cache_ttl = 300  # 缓存5分钟

    def __init__(self):
        super().__init__("/admin/api/login", ["登录管理", "平台认证"])
        self.logger = get_logger()

    def register_routes(self):
        """注册路由"""
        from starlette.routing import Route
        from starlette.responses import JSONResponse


        async def get_platforms_handler(request):
            """获取支持的平台列表"""
            try:
                platforms = [p.value for p in global_settings.platform.enabled_platforms]
                return JSONResponse(content=platforms)
            except Exception as e:
                self.logger.error(f"获取平台列表失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        async def start_login_handler(request):
            """启动登录流程"""
            try:
                body = await request.json()
                login_request = LoginRequest(**body)

                # 检查平台是否启用
                enabled_platform_codes = [p.value for p in global_settings.platform.enabled_platforms]
                if login_request.platform not in enabled_platform_codes:
                    return JSONResponse(content={"detail": f"平台 {login_request.platform} 未启用"}, status_code=400)

                self.logger.info(f"[登录管理] 启动登录: platform={login_request.platform}, type={login_request.login_type}")

                # 清理该平台的旧登录会话
                self._cleanup_platform_sessions(login_request.platform)

                # 目前只实现了 Bilibili
                if login_request.platform == "bili":
                    result = await self._start_bilibili_login(login_request)
                    return JSONResponse(content=result)
                else:
                    return JSONResponse(
                        content={"detail": f"平台 {login_request.platform} 的登录功能正在重构中，目前仅支持 Bilibili"},
                        status_code=501
                    )
            except Exception as e:
                self.logger.error(f"[登录管理] 启动登录失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        async def get_login_status_handler(request):
            """获取平台登录状态"""
            try:
                platform = request.path_params['platform']

                # 检查平台是否启用
                enabled_platform_codes = [p.value for p in global_settings.platform.enabled_platforms]
                if platform not in enabled_platform_codes:
                    return JSONResponse(content={"detail": f"平台 {platform} 未启用"}, status_code=400)

                # 检查登录状态
                if platform == "bili":
                    is_logged_in, user_info = await self._check_bilibili_login_status()

                    response = LoginStatusResponse(
                        platform=platform,
                        is_logged_in=is_logged_in,
                        user_info=user_info,
                        message="已登录" if is_logged_in else "未登录"
                    )
                    return JSONResponse(content=response.dict())
                else:
                    response = LoginStatusResponse(
                        platform=platform,
                        is_logged_in=False,
                        user_info={},
                        message="平台登录功能正在重构中"
                    )
                    return JSONResponse(content=response.dict())

            except Exception as e:
                self.logger.error(f"[登录管理] 获取登录状态失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        async def logout_handler(request):
            """退出登录"""
            try:
                platform = request.path_params['platform']

                # 检查平台是否启用
                enabled_platform_codes = [p.value for p in global_settings.platform.enabled_platforms]
                if platform not in enabled_platform_codes:
                    return JSONResponse(content={"detail": f"平台 {platform} 未启用"}, status_code=400)

                if platform == "bili":
                    browser_data_dir = Path("browser_data") / f"{Platform.BILIBILI.value}"
                    if browser_data_dir.exists():
                        import shutil
                        shutil.rmtree(browser_data_dir)
                        self.logger.info(f"[登录管理] 已清除 Bilibili 登录态")

                return JSONResponse(content={
                    "status": "success",
                    "platform": platform,
                    "message": "退出登录成功"
                })

            except Exception as e:
                self.logger.error(f"[登录管理] 退出登录失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        async def get_session_status_handler(request):
            """获取登录会话状态"""
            try:
                import time
                session_id = request.path_params['session_id']
                session = _login_sessions.get(session_id)

                if not session:
                    return JSONResponse(content={"detail": "会话不存在"}, status_code=404)

                # 检查二维码是否过期（Bilibili二维码有效期180秒）
                if session.get("login_type") == "qrcode" and session.get("status") in ["started", "waiting"]:
                    qrcode_timestamp = session.get("qrcode_timestamp", 0)
                    elapsed = time.time() - qrcode_timestamp

                    # 如果超过180秒，标记为过期
                    if elapsed > 180:
                        session["status"] = "expired"
                        session["message"] = "二维码已过期（有效期3分钟），请点击刷新二维码按钮重新获取"
                        self.logger.warning(f"[登录管理] 二维码已过期: session_id={session_id}, elapsed={elapsed:.0f}s")

                return JSONResponse(content={
                    "status": session.get("status"),
                    "platform": session.get("platform"),
                    "message": session.get("message", "登录中..."),
                    "qr_code_base64": session.get("qr_code_base64"),  # 从会话中读取二维码
                    "qrcode_timestamp": session.get("qrcode_timestamp", 0),  # 返回时间戳供前端计算倒计时
                    "elapsed": time.time() - session.get("qrcode_timestamp", time.time())  # 已过去的秒数
                })

            except Exception as e:
                self.logger.error(f"[登录管理] 获取会话状态失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        async def list_sessions_handler(request):
            """列出所有平台的登录会话"""
            try:
                # 平台名称映射
                platform_names = {
                    "bili": "哔哩哔哩",
                    "xhs": "小红书",
                    "dy": "抖音",
                    "ks": "快手",
                    "wb": "微博",
                    "tieba": "贴吧",
                    "zhihu": "知乎"
                }

                sessions = []
                for platform_enum in global_settings.platform.enabled_platforms:
                    platform_code = platform_enum.value
                    platform_name = platform_names.get(platform_code, platform_code)

                    # 检查是否有保存的会话（真正检查 cookie）
                    if platform_code == "bili":
                        # 调用真实的登录状态检查
                        is_logged_in, _ = await self._check_bilibili_login_status()
                        browser_data_dir = Path("browser_data") / f"{Platform.BILIBILI.value}"
                    else:
                        is_logged_in = False
                        browser_data_dir = None

                    sessions.append({
                        "platform": platform_code,
                        "platform_name": platform_name,
                        "is_logged_in": is_logged_in,
                        "last_login": "最近登录" if is_logged_in else "从未登录",
                        "session_path": str(browser_data_dir) if platform_code == "bili" and is_logged_in else None
                    })

                return JSONResponse(content=sessions)

            except Exception as e:
                self.logger.error(f"[登录管理] 获取会话列表失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        # 返回 Starlette 路由
        return [
            Route(f"{self.prefix}/platforms", get_platforms_handler, methods=["GET"]),
            Route(f"{self.prefix}/start", start_login_handler, methods=["POST"]),
            Route(f"{self.prefix}/status/{{platform}}", get_login_status_handler, methods=["GET"]),
            Route(f"{self.prefix}/logout/{{platform}}", logout_handler, methods=["POST"]),
            Route(f"{self.prefix}/session/{{session_id}}", get_session_status_handler, methods=["GET"]),
            Route(f"{self.prefix}/sessions", list_sessions_handler, methods=["GET"]),
        ]

    async def _check_bilibili_login_status(self) -> tuple[bool, Dict[str, Any]]:
        """检查 Bilibili 登录状态（调用 API 验证）"""
        from playwright.async_api import async_playwright
        from app.crawler.platforms.bilibili.client import BilibiliClient

        browser_data_dir = Path("browser_data") / f"{Platform.BILIBILI.value}"

        # 如果目录不存在，直接返回未登录
        if not browser_data_dir.exists():
            self.logger.info("[登录管理] Bilibili browser_data 目录不存在，未登录")
            return False, {}

        playwright = None
        browser_context = None

        try:
            # 启动浏览器 - 使用全局配置的 headless 设置
            playwright = await async_playwright().start()
            chromium = playwright.chromium

            headless_mode = global_settings.browser.headless
            self.logger.info(f"[登录管理] 检查登录状态 - 使用全局配置 headless={headless_mode}")

            browser_context = await chromium.launch_persistent_context(
                user_data_dir=str(browser_data_dir),
                headless=headless_mode,
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            page = await browser_context.new_page()
            await page.goto("https://www.bilibili.com")

            # 获取 cookies 并创建 BilibiliClient
            current_cookies = await browser_context.cookies()
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in current_cookies])
            cookie_dict = {c['name']: c['value'] for c in current_cookies}

            bili_client = BilibiliClient(
                proxy=None,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Cookie": cookie_str,
                    "Origin": "https://www.bilibili.com",
                    "Referer": "https://www.bilibili.com",
                },
                playwright_page=page,
                cookie_dict=cookie_dict,
            )

            # 调用 pong() 方法检查登录状态
            is_logged_in = await bili_client.pong()

            if is_logged_in:
                user_info = {
                    "uid": cookie_dict.get("DedeUserID", "未知"),
                    "sessdata": cookie_dict.get("SESSDATA", "")[:20] + "..." if cookie_dict.get("SESSDATA") else ""
                }
                self.logger.info(f"[登录管理] Bilibili 已登录: uid={user_info['uid']}")
                return True, user_info
            else:
                self.logger.info("[登录管理] Bilibili 未登录（API验证失败）")
                return False, {}

        except Exception as e:
            self.logger.error(f"[登录管理] 检查 Bilibili 登录状态失败: {e}")
            return False, {}

        finally:
            # 清理资源
            if browser_context:
                try:
                    await browser_context.close()
                except:
                    pass
            if playwright:
                try:
                    await playwright.stop()
                except:
                    pass

    async def _start_bilibili_login(self, request: LoginRequest) -> Dict[str, Any]:
        """启动 Bilibili 登录"""
        from playwright.async_api import async_playwright
        from app.crawler.platforms.bilibili.login import BilibiliLogin

        # 生成会话 ID
        session_id = str(uuid.uuid4())

        # 清理旧的二维码文件（确保生成新的二维码）
        qrcode_dir = Path(f"browser_data/{Platform.BILIBILI.value}_{request.login_type}")
        if qrcode_dir.exists():
            import shutil
            try:
                shutil.rmtree(qrcode_dir)
                self.logger.info(f"[登录管理] 已清理旧的二维码目录: {qrcode_dir}")
            except Exception as e:
                self.logger.warning(f"[登录管理] 清理二维码目录失败: {e}")

        # 启动浏览器
        playwright = await async_playwright().start()
        chromium = playwright.chromium

        # 配置浏览器 - 使用全局配置中的 headless 设置
        user_data_dir = Path("browser_data") / f"{Platform.BILIBILI.value}"
        user_data_dir.parent.mkdir(parents=True, exist_ok=True)

        # 使用全局配置的 headless 设置，确保与爬虫使用相同的浏览器上下文
        headless_mode = global_settings.browser.headless
        self.logger.info(f"[登录管理] 使用全局配置 headless={headless_mode}")

        browser_context = await chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=headless_mode,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        context_page = await browser_context.new_page()

        # 创建登录对象
        login_obj = BilibiliLogin(
            login_type=request.login_type,
            browser_context=browser_context,
            context_page=context_page,
            login_phone=request.phone,
            cookie_str=request.cookie
        )

        # 存储会话信息
        _login_sessions[session_id] = {
            "platform": "bili",
            "login_type": request.login_type,
            "status": "started",
            "browser_context": browser_context,
            "context_page": context_page,
            "login_obj": login_obj,
            "playwright": playwright,
            "message": "登录流程已启动",
            "qrcode_timestamp": __import__('time').time()  # 记录二维码生成时间
        }

        # 开始登录（异步执行）
        asyncio.create_task(self._execute_bilibili_login(session_id))

        # 等待二维码生成（如果是二维码登录）
        qr_code_base64 = None
        if request.login_type == "qrcode":

            # 等待最多10秒让二维码生成,TODO:这个路径最好写成属性，要不很容易不一致
            qrcode_path = Path(f"browser_data/{Platform.BILIBILI.value}_{request.login_type}") / f"qrcode.png"
            for attempt in range(50):  # 50次 * 0.2秒 = 10秒
                if qrcode_path.exists():
                    try:
                        # 检查文件大小，确保文件已完整写入（Bilibili二维码通常>1KB）
                        file_size = qrcode_path.stat().st_size
                        if file_size > 1024:  # 文件大于1KB，说明二维码已完整生成
                            import base64
                            with open(qrcode_path, "rb") as f:
                                qr_data = f.read()
                                # 再次验证读取的数据不为空
                                if qr_data and len(qr_data) > 1024:
                                    qr_code_base64 = base64.b64encode(qr_data).decode('utf-8')
                                    self.logger.info(f"[登录管理] 二维码已生成并编码为 base64，大小: {len(qr_data)} bytes")
                                    break
                                else:
                                    self.logger.debug(f"[登录管理] 二维码数据太小，继续等待... ({len(qr_data) if qr_data else 0} bytes)")
                        else:
                            self.logger.debug(f"[登录管理] 二维码文件太小，继续等待... ({file_size} bytes, 第{attempt+1}次尝试)")
                    except Exception as e:
                        self.logger.warning(f"[登录管理] 读取二维码失败（第{attempt+1}次尝试）: {e}")
                await asyncio.sleep(0.2)

            if not qr_code_base64:
                self.logger.warning(f"[登录管理] 二维码未能及时生成（等待10秒后超时）")

        # 保存二维码到会话中
        _login_sessions[session_id]["qr_code_base64"] = qr_code_base64

        return {
            "status": "started",
            "platform": "bili",
            "login_type": request.login_type,
            "message": "登录流程已启动，请在浏览器中完成登录" if request.login_type != "qrcode" else "请扫描二维码登录",
            "session_id": session_id,
            "qr_code_base64": qr_code_base64
        }

    async def _execute_bilibili_login(self, session_id: str):
        """执行 Bilibili 登录（后台任务）"""
        session = _login_sessions.get(session_id)
        if not session:
            self.logger.error(f"[登录管理] 会话不存在: session_id={session_id}")
            return

        try:
            login_obj = session["login_obj"]

            # 更新会话消息
            session["status"] = "waiting"
            session["message"] = "等待扫描二维码..."
            self.logger.info(f"[登录管理] 更新会话状态为 waiting: session_id={session_id}")

            # 执行登录
            self.logger.info(f"[登录管理] 开始执行登录: session_id={session_id}")
            await login_obj.begin()

            # 登录成功
            session["status"] = "success"
            session["message"] = "登录成功"
            self.logger.info(f"[登录管理] Bilibili 登录成功: session_id={session_id}")

            # 等待几秒后关闭浏览器
            await asyncio.sleep(3)
            await self._cleanup_session(session_id)

        except Exception as e:
            self.logger.error(f"[登录管理] Bilibili 登录失败: session_id={session_id}, error={e}")
            session["status"] = "failed"
            session["message"] = f"登录失败: {str(e)}"

            # 失败后也要清理
            await asyncio.sleep(3)
            await self._cleanup_session(session_id)

    async def _cleanup_session(self, session_id: str):
        """清理登录会话"""
        session = _login_sessions.get(session_id)
        if not session:
            return

        try:
            # 关闭浏览器
            if "browser_context" in session:
                await session["browser_context"].close()

            # 停止 playwright
            if "playwright" in session:
                await session["playwright"].stop()

            # 从会话中移除（保留状态信息供查询）
            session.pop("browser_context", None)
            session.pop("context_page", None)
            session.pop("login_obj", None)
            session.pop("playwright", None)

        except Exception as e:
            self.logger.error(f"[登录管理] 清理会话失败: {e}")

    def _cleanup_platform_sessions(self, platform: str):
        """清理指定平台的所有旧会话"""
        session_ids_to_cleanup = []
        for session_id, session in _login_sessions.items():
            if session.get("platform") == platform:
                session_ids_to_cleanup.append(session_id)

        for session_id in session_ids_to_cleanup:
            self.logger.info(f"[登录管理] 清理平台 {platform} 的旧会话: {session_id}")
            # 异步清理会话
            asyncio.create_task(self._cleanup_session(session_id))
            # 从字典中删除
            _login_sessions.pop(session_id, None)

        if session_ids_to_cleanup:
            self.logger.info(f"[登录管理] 已清理 {len(session_ids_to_cleanup)} 个旧会话")

    def register_mcp_tools(self, app):
        """注册MCP工具（可选实现）"""
        # 登录管理主要提供HTTP API，暂不注册MCP工具
        pass
