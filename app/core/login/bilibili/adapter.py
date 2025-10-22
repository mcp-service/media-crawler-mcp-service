# -*- coding: utf-8 -*-
"""
Bilibili 平台登录适配器
"""
from __future__ import annotations

import asyncio
import base64
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional

from playwright.async_api import BrowserContext, async_playwright

from app.config.settings import Platform, LoginType, global_settings
from app.core.crawler.platforms.bilibili.client import BilibiliClient
from app.core.crawler.platforms.bilibili.login import BilibiliLogin

from ..base import BaseLoginAdapter
from ..models import LoginSession, LoginStartPayload, PlatformLoginState


class BilibiliLoginAdapter(BaseLoginAdapter):
    """Bilibili 登录适配器"""

    def __init__(self, service):
        super().__init__(service)
        browser_cfg = global_settings.browser
        self._headless = browser_cfg.headless
        self._user_agent = getattr(
            browser_cfg,
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        viewport_width = browser_cfg.viewport_width or 1280
        viewport_height = browser_cfg.viewport_height or 800
        self._viewport = {"width": int(viewport_width), "height": int(viewport_height)}
        self._qr_wait_attempts = 50
        self._qr_wait_interval = 0.2
        self._qr_login_timeout = 180
        self._qr_poll_interval = 1.5

    @property
    def platform(self) -> str:
        return Platform.BILIBILI.value

    @property
    def display_name(self) -> str:
        return "哔哩哔哩"

    @property
    def user_data_dir(self) -> Path:
        return Path("browser_data") / self.platform

    def _qr_code_dir(self, login_type: str) -> Path:
        return Path("browser_data") / f"{self.platform}_{login_type}"

    async def start_login(self, session: LoginSession, payload: LoginStartPayload) -> Dict[str, Any]:
        session.status = "starting"
        session.message = "正在启动登录流程..."
        self.logger.info(
            f"[登录管理] 启动 Bilibili 登录: platform={payload.platform}, type={payload.login_type}"
        )
        await self.service.persist_session(session)

        qr_dir = self._qr_code_dir(payload.login_type)
        if qr_dir.exists():
            try:
                shutil.rmtree(qr_dir)
            except Exception as exc:
                self.logger.warning(f"[登录管理] 清理旧二维码目录失败: {exc}")

        cookie_candidate = (payload.cookie or "").strip()

        # 如果没有提供新的 Cookie，则优先通过状态检测确认是否已登录
        if not cookie_candidate:
            try:
                current_state = await self.service.refresh_platform_state(session.platform, force=True)
            except Exception as exc:
                current_state = None
                self.logger.warning(f"[登录管理] 检查现有登录状态失败，继续登录流程: {exc}")
            else:
                if current_state and current_state.is_logged_in:
                    session.status = "success"
                    session.message = "已检测到登录状态，无需重新登录"
                    session.metadata["cookie_dict"] = current_state.cookie_dict
                    session.metadata["cookie_str"] = current_state.cookie_str

                    await self.service.persist_session(session)
                    response = {
                        "status": session.status,
                        "platform": session.platform,
                        "login_type": session.login_type,
                        "message": session.message,
                        "session_id": session.id,
                        "qr_code_base64": session.qr_code_base64,
                        "qrcode_timestamp": session.qrcode_timestamp,
                    }
                    return response

        playwright = await async_playwright().start()
        chromium = playwright.chromium

        user_data_dir = self.user_data_dir
        user_data_dir.parent.mkdir(parents=True, exist_ok=True)

        browser_context = await chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=self._headless,
            viewport=self._viewport,
            user_agent=self._user_agent,
            accept_downloads=True,
        )
        context_page = await browser_context.new_page()

        login_obj = BilibiliLogin(
            login_type=payload.login_type,
            browser_context=browser_context,
            context_page=context_page,
            login_phone=payload.phone,
            cookie_str=payload.cookie,
        )

        session.browser_context = browser_context
        session.context_page = context_page
        session.playwright = playwright
        session.runtime["login_obj"] = login_obj

        # 如果有新的 cookie，则直接尝试使用 cookie 登录
        if cookie_candidate:
            session.login_type = LoginType.COOKIE.value
            session.status = "processing"
            session.message = "检测到 Cookie，正在尝试 Cookie 登录..."
            await self.service.persist_session(session)

            login_obj.cookie_str = cookie_candidate
            try:
                await login_obj.login_by_cookies()
                
                # 即使页面加载失败，也要检查 Cookie 是否有效
                login_success = False
                try:
                    # 尝试页面加载验证
                    await context_page.goto("https://www.bilibili.com/", 
                                           wait_until="domcontentloaded", 
                                           timeout=10000)
                    login_success = await login_obj.wait_for_login(timeout=10.0, interval=0.5)
                except Exception as page_exc:
                    self.logger.warning(f"[登录管理] 页面加载失败，尝试直接验证 Cookie: {page_exc}")
                    # 页面加载失败时，直接检查 Cookie 有效性
                    try:
                        login_success = await login_obj.has_valid_cookie()
                        if login_success:
                            self.logger.info(f"[登录管理] Cookie 验证成功，跳过页面加载: session_id={session.id}")
                    except Exception as cookie_exc:
                        self.logger.warning(f"[登录管理] Cookie 验证也失败: {cookie_exc}")

                if login_success:
                    cookies = await browser_context.cookies()
                    cookie_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
                    cookie_str = "; ".join(
                        f"{name}={value}" for name, value in cookie_dict.items()
                    )

                    session.metadata["cookie_dict"] = cookie_dict
                    session.metadata["cookie_str"] = cookie_str
                    session.status = "success"
                    session.message = "Cookie 登录成功"

                    await self.service.persist_session(session)
                    
                    # 直接创建并保存登录状态，避免重新调用可能被风控的检查
                    from ..models import PlatformLoginState
                    
                    success_state = PlatformLoginState(
                        platform=self.platform,
                        is_logged_in=True,
                        cookie_str=cookie_str,
                        cookie_dict=cookie_dict,
                        user_info={
                            "uid": cookie_dict.get("DedeUserID", ""),
                            "sessdata": (
                                cookie_dict.get("SESSDATA", "")[:20] + "..."
                                if cookie_dict.get("SESSDATA")
                                else ""
                            ),
                        },
                        message="已登录",
                        last_checked_at=time.time(),
                        last_success_at=time.time(),
                    )
                    
                    # 直接保存状态，避免重新检查
                    try:
                        await self.service._storage.save_platform_state(success_state)
                        self.logger.info(f"[登录管理] Cookie 登录成功，状态已保存: session_id={session.id}")
                    except Exception as save_exc:
                        self.logger.warning(f"[登录管理] 保存登录状态失败: {save_exc}")
                        # 即使保存失败，也不影响登录流程
                    
                    response = {
                        "status": session.status,
                        "platform": session.platform,
                        "login_type": session.login_type,
                        "message": session.message,
                        "session_id": session.id,
                        "qr_code_base64": session.qr_code_base64,
                        "qrcode_timestamp": session.qrcode_timestamp,
                    }
                    await self.service.cleanup_session(session.id, remove_resources=True, drop=False)
                    return response

                # Cookie 登录失败，如果原始请求是二维码登录，则继续二维码流程
                if payload.login_type == "qrcode":
                    self.logger.info(f"[登录管理] Cookie 登录失败，回退到二维码登录: session_id={session.id}")
                    session.login_type = LoginType.QRCODE.value  # 恢复为二维码登录
                    session.status = "started"
                    session.message = "Cookie 登录失败，正在生成二维码..."
                    # 不直接返回，继续执行二维码登录逻辑
                else:
                    # 非二维码登录类型的 Cookie 失败，直接返回失败
                    session.status = "failed"
                    session.message = "Cookie 登录失败，Cookie 可能已失效"
                    await self.service.persist_session(session)
                    response = {
                        "status": session.status,
                        "platform": session.platform,
                        "login_type": session.login_type,
                        "message": session.message,
                        "session_id": session.id,
                        "qr_code_base64": session.qr_code_base64,
                        "qrcode_timestamp": session.qrcode_timestamp,
                    }
                    await self.service.cleanup_session(session.id, remove_resources=True, drop=False)
                    return response
                    
            except Exception as exc:
                # Cookie 登录异常，先尝试直接验证 Cookie 是否有效
                login_success = False
                try:
                    login_success = await login_obj.has_valid_cookie()
                    if login_success:
                        self.logger.info(f"[登录管理] Cookie 登录过程异常但 Cookie 有效: session_id={session.id}")
                        # 直接处理登录成功逻辑
                        cookies = await browser_context.cookies()
                        cookie_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
                        cookie_str = "; ".join(
                            f"{name}={value}" for name, value in cookie_dict.items()
                        )

                        session.metadata["cookie_dict"] = cookie_dict
                        session.metadata["cookie_str"] = cookie_str
                        session.status = "success"
                        session.message = "Cookie 登录成功"

                        await self.service.persist_session(session)
                        
                        # 直接创建并保存登录状态
                        from ..models import PlatformLoginState
                        
                        success_state = PlatformLoginState(
                            platform=self.platform,
                            is_logged_in=True,
                            cookie_str=cookie_str,
                            cookie_dict=cookie_dict,
                            user_info={
                                "uid": cookie_dict.get("DedeUserID", ""),
                                "sessdata": (
                                    cookie_dict.get("SESSDATA", "")[:20] + "..."
                                    if cookie_dict.get("SESSDATA")
                                    else ""
                                ),
                            },
                            message="已登录",
                            last_checked_at=time.time(),
                            last_success_at=time.time(),
                        )
                        
                        try:
                            await self.service._storage.save_platform_state(success_state)
                            self.logger.info(f"[登录管理] Cookie 登录异常但验证成功，状态已保存: session_id={session.id}")
                        except Exception as save_exc:
                            self.logger.warning(f"[登录管理] 保存登录状态失败: {save_exc}")
                        
                        response = {
                            "status": session.status,
                            "platform": session.platform,
                            "login_type": session.login_type,
                            "message": session.message,
                            "session_id": session.id,
                            "qr_code_base64": session.qr_code_base64,
                            "qrcode_timestamp": session.qrcode_timestamp,
                        }
                        await self.service.cleanup_session(session.id, remove_resources=True, drop=False)
                        return response
                except Exception as verify_exc:
                    self.logger.warning(f"[登录管理] Cookie 验证失败: {verify_exc}")
                    
                # Cookie 登录异常，如果原始请求是二维码登录，则继续二维码流程
                if payload.login_type == "qrcode":
                    self.logger.info(
                        f"[登录管理] Cookie 登录异常，回退到二维码登录: session_id={session.id}, error={exc}"
                    )
                    session.login_type = LoginType.QRCODE.value  # 恢复为二维码登录
                    session.status = "started"
                    session.message = "Cookie 验证失败，正在生成二维码..."
                    # 不直接返回，继续执行二维码登录逻辑
                else:
                    # 非二维码登录类型的 Cookie 异常，直接返回失败
                    session.status = "failed"
                    session.message = f"Cookie 登录失败: {exc}"
                    self.logger.error(
                        f"[登录管理] Cookie 登录失败: session_id={session.id}, error={exc}"
                    )
                    await self.service.persist_session(session)
                    response = {
                        "status": session.status,
                        "platform": session.platform,
                        "login_type": session.login_type,
                        "message": session.message,
                        "session_id": session.id,
                        "qr_code_base64": session.qr_code_base64,
                        "qrcode_timestamp": session.qrcode_timestamp,
                    }
                    await self.service.cleanup_session(session.id, remove_resources=True, drop=False)
                    return response

        # 执行二维码登录逻辑（无论是直接请求二维码登录，还是从 Cookie 登录回退过来）
        if payload.login_type == "qrcode" or session.login_type == LoginType.QRCODE.value:
            # 确保 login_obj 使用正确的登录类型
            login_obj.login_type = "qrcode"
            
            session.status = "started"
            session.message = "正在生成二维码..."
            session.qrcode_timestamp = time.time()

            qr_path = await login_obj.generate_qrcode()
            if qr_path is None:
                session.status = "failed"
                session.message = "二维码生成失败，请稍后重试"
                await self.service.persist_session(session)
                await self.service.cleanup_session(session.id, remove_resources=True)
            else:
                qr_code_base64 = await self._wait_for_qrcode(payload.login_type)
                if qr_code_base64:
                    session.qr_code_base64 = qr_code_base64
                    session.status = "waiting"
                    session.message = "二维码已生成，等待扫码..."
                    poll_task = asyncio.create_task(self._poll_qrcode_session(session.id))
                    session.runtime["task"] = poll_task
                    await self.service.persist_session(session)
                else:
                    session.status = "failed"
                    session.message = "二维码生成超时，请重新开始登录"
                    await self.service.persist_session(session)
                    await self.service.cleanup_session(session.id, remove_resources=True)
        else:
            session.status = "processing"
            session.message = "正在尝试登录..."
            session.qrcode_timestamp = 0.0
            login_task = asyncio.create_task(self._execute_login(session.id))
            session.runtime["task"] = login_task
            await self.service.persist_session(session)

        response = {
            "status": session.status,
            "platform": session.platform,
            "login_type": session.login_type,
            "message": session.message,
            "session_id": session.id,
            "qr_code_base64": session.qr_code_base64,
            "qrcode_timestamp": session.qrcode_timestamp,
        }
        await self.service.persist_session(session)
        return response

    async def _poll_qrcode_session(self, session_id: str) -> None:
        """轮询检测二维码登录状态"""
        session = self.service.get_session(session_id)
        if not session:
            return

        login_obj: Optional[BilibiliLogin] = session.runtime.get("login_obj")
        if not login_obj:
            self.logger.error(f"[登录管理] 会话缺少登录对象: {session_id}")
            return

        timeout_seconds = self._qr_login_timeout
        poll_interval = self._qr_poll_interval
        start_ts = time.time()

        try:
            while True:
                if await login_obj.has_valid_cookie():
                    cookies = await session.browser_context.cookies()
                    cookie_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
                    cookie_str = "; ".join(
                        f"{name}={value}" for name, value in cookie_dict.items()
                    )
                    session.metadata["cookie_dict"] = cookie_dict
                    session.metadata["cookie_str"] = cookie_str
                    session.status = "success"
                    session.message = "登录成功"
                    self.logger.info(
                        f"[登录管理] Bilibili 登录成功: session_id={session_id}"
                    )
                    await self.service.persist_session(session)
                    
                    # 直接创建并保存登录状态，避免重新调用可能被风控的检查
                    from ..models import PlatformLoginState
                    
                    success_state = PlatformLoginState(
                        platform=self.platform,
                        is_logged_in=True,
                        cookie_str=cookie_str,
                        cookie_dict=cookie_dict,
                        user_info={
                            "uid": cookie_dict.get("DedeUserID", ""),
                            "sessdata": (
                                cookie_dict.get("SESSDATA", "")[:20] + "..."
                                if cookie_dict.get("SESSDATA")
                                else ""
                            ),
                        },
                        message="已登录",
                        last_checked_at=time.time(),
                        last_success_at=time.time(),
                    )
                    
                    # 直接保存状态，避免重新检查
                    try:
                        await self.service._storage.save_platform_state(success_state)
                        self.logger.info(f"[登录管理] 二维码登录成功，状态已保存: session_id={session_id}")
                    except Exception as save_exc:
                        self.logger.warning(f"[登录管理] 保存登录状态失败: {save_exc}")
                    
                    break

                if time.time() - start_ts > timeout_seconds:
                    session.status = "expired"
                    session.message = "二维码已过期，请重新获取"
                    self.logger.warning(
                        f"[登录管理] Bilibili 登录超时: session_id={session_id}"
                    )
                    await self.service.persist_session(session)
                    break

                await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            session.status = "failed"
            session.message = f"登录失败: {exc}"
            session.metadata["error"] = str(exc)
            self.logger.error(
                f"[登录管理] Bilibili 登录轮询失败: session_id={session_id}, error={exc}"
            )
        finally:
            session.runtime.pop("task", None)
            await self.service.persist_session(session)
            await asyncio.sleep(2)
            await self.service.cleanup_session(session_id, remove_resources=True)

    async def _wait_for_qrcode(self, login_type: str) -> Optional[str]:
        """等待二维码文件生成并转换为 base64"""
        qrcode_path = self._qr_code_dir(login_type) / "qrcode.png"
        for attempt in range(self._qr_wait_attempts):
            if qrcode_path.exists():
                try:
                    file_size = qrcode_path.stat().st_size
                    if file_size > 1024:
                        with qrcode_path.open("rb") as fp:
                            data = fp.read()
                        if data:
                            return base64.b64encode(data).decode("utf-8")
                except Exception as exc:
                    self.logger.warning(
                        f"[登录管理] 读取二维码失败（第{attempt + 1}次）: {exc}"
                    )
            await asyncio.sleep(self._qr_wait_interval)
        self.logger.warning("[登录管理] 二维码未能及时生成（等待超时）")
        return None

    async def _execute_login(self, session_id: str):
        """执行登录流程"""
        session = self.service.get_session(session_id)
        if not session:
            self.logger.error(f"[登录管理] 会话不存在: {session_id}")
            return

        login_obj: Optional[BilibiliLogin] = session.runtime.get("login_obj")
        if not login_obj:
            self.logger.error(f"[登录管理] 会话缺少登录对象: {session_id}")
            return

        if session.login_type == "qrcode":
            # 二维码登录不再由服务端主动拉起，改为前端轮询触发
            return

        try:
            session.status = "processing"
            session.message = "正在尝试登录..."
            await self.service.persist_session(session)

            await login_obj.begin()

            session.status = "success"
            session.message = "登录成功"
            self.logger.info(f"[登录管理] Bilibili 登录成功: session_id={session_id}")
            await self.service.persist_session(session)
            await self.service.refresh_platform_state(session.platform, force=True)
        except Exception as exc:
            session.status = "failed"
            session.message = f"登录失败: {exc}"
            session.metadata["error"] = str(exc)
            self.logger.error(
                f"[登录管理] Bilibili 登录失败: session_id={session_id}, error={exc}"
            )
            await self.service.persist_session(session)
        finally:
            await asyncio.sleep(3)
            await self.service.cleanup_session(session_id, remove_resources=True)

    async def fetch_login_state(self) -> PlatformLoginState | None:
        """检查登录状态"""
        state = PlatformLoginState(platform=self.platform)
        data_dir = self.user_data_dir
        if not data_dir.exists():
            state.message = "浏览器数据不存在"
            state.last_checked_at = time.time()
            return state

        playwright = await async_playwright().start()
        browser_context: Optional[BrowserContext] = None
        try:
            chromium = playwright.chromium
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=str(data_dir),
                headless=self._headless,
                viewport=self._viewport,
                user_agent=self._user_agent,
                accept_downloads=True,
            )

            # 首先检查保存的 Cookie 是否包含关键字段
            cookies = await browser_context.cookies()
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
            cookie_dict = {c["name"]: c["value"] for c in cookies}
            
            # 检查关键 Cookie 是否存在
            has_sessdata = bool(cookie_dict.get("SESSDATA"))
            has_userid = bool(cookie_dict.get("DedeUserID"))
            
            if not (has_sessdata and has_userid):
                state.is_logged_in = False
                state.cookie_str = cookie_str
                state.cookie_dict = cookie_dict
                state.user_info = {}
                state.message = "关键登录信息缺失"
                state.last_checked_at = time.time()
                return state

            # 尝试通过 API 验证登录状态（不依赖页面加载）
            bili_client = BilibiliClient(
                proxy=None,
                headers={
                    "User-Agent": self._user_agent,
                    "Cookie": cookie_str,
                    "Origin": "https://www.bilibili.com",
                    "Referer": "https://www.bilibili.com",
                },
                playwright_page=None,  # 先不使用页面，避免加载超时
                cookie_dict=cookie_dict,
            )

            is_logged_in = False
            try:
                # 直接使用 API 检查，不依赖页面加载
                api_result = await bili_client.pong()
                is_logged_in = bool(api_result)
                self.logger.debug(f"[登录管理] Bilibili API 检查结果: {is_logged_in}")
            except Exception as api_exc:
                self.logger.debug(f"[登录管理] Bilibili API 检查失败: {api_exc}")
                
                # API 失败时，尝试轻量级页面检查（使用更短的超时）
                page = None
                try:
                    page = await browser_context.new_page()
                    # 使用更短的超时时间和更宽松的等待条件
                    await page.goto("https://www.bilibili.com/", 
                                   wait_until="domcontentloaded",  # 只等待 DOM 加载完成
                                   timeout=10000)  # 10秒超时
                    
                    # 使用页面内 API 调用验证
                    result = await page.evaluate(
                        """
                        async () => {
                            try {
                                const resp = await fetch("https://api.bilibili.com/x/web-interface/nav", {
                                    credentials: "include"
                                });
                                if (resp.status !== 200) return { success: false, status: resp.status };
                                const data = await resp.json();
                                return { 
                                    success: true, 
                                    isLogin: data?.data?.isLogin || false,
                                    code: data?.code || -1
                                };
                            } catch (error) {
                                return { success: false, error: String(error) };
                            }
                        }
                        """
                    )
                    
                    if isinstance(result, dict) and result.get("success"):
                        is_logged_in = bool(result.get("isLogin", False))
                        self.logger.debug(f"[登录管理] Bilibili 页面检查结果: {is_logged_in}")
                    else:
                        # 页面检查也失败，基于 Cookie 做保守判断
                        is_logged_in = True  # 有关键 Cookie 就认为可能已登录
                        self.logger.debug("[登录管理] 页面检查失败，基于 Cookie 保守判断为已登录")
                        
                except Exception as page_exc:
                    # 页面加载失败，基于 Cookie 存在性判断
                    is_logged_in = True  # 有关键 Cookie 就认为可能已登录
                    self.logger.debug(f"[登录管理] 页面加载失败，基于 Cookie 判断: {page_exc}")
                finally:
                    if page:
                        try:
                            await page.close()
                        except Exception:
                            pass

            # 设置状态信息
            state.is_logged_in = is_logged_in
            state.cookie_str = cookie_str
            state.cookie_dict = cookie_dict
            
            if is_logged_in:
                state.user_info = {
                    "uid": cookie_dict.get("DedeUserID", ""),
                    "sessdata": (
                        cookie_dict.get("SESSDATA", "")[:20] + "..."
                        if cookie_dict.get("SESSDATA")
                        else ""
                    ),
                }
                state.message = "已登录"
                state.last_success_at = time.time()
            else:
                state.user_info = {}
                state.message = "未登录"
                
            state.last_checked_at = time.time()
            return state
            
        except Exception as exc:
            self.logger.error(f"[登录管理] 检查 Bilibili 登录状态失败: {exc}")
            # 即使检查失败，也尝试基于现有数据返回状态
            try:
                cookies = await browser_context.cookies() if browser_context else []
                cookie_dict = {c["name"]: c["value"] for c in cookies}
                has_key_cookies = bool(cookie_dict.get("SESSDATA") and cookie_dict.get("DedeUserID"))
                
                state.is_logged_in = has_key_cookies
                state.cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
                state.cookie_dict = cookie_dict
                state.message = f"状态检查失败，基于 Cookie 判断: {'可能已登录' if has_key_cookies else '未登录'}"
                state.last_checked_at = time.time()
                return state
            except Exception:
                state.message = f"状态检查失败: {exc}"
                state.last_checked_at = time.time()
                return state
        finally:
            if browser_context:
                try:
                    await browser_context.close()
                except Exception:
                    pass
            try:
                await playwright.stop()
            except Exception:
                pass

    async def logout(self) -> None:
        """退出登录并清理数据"""
        await self.service.cleanup_platform_sessions(self.platform, drop=True)

        data_dir = self.user_data_dir
        if data_dir.exists():
            try:
                await asyncio.to_thread(shutil.rmtree, data_dir)
            except Exception as exc:
                self.logger.warning(f"[登录管理] 清理浏览器数据目录失败: {exc}")

        qr_parent = Path("browser_data")
        if qr_parent.exists():
            for qr_dir in qr_parent.glob(f"{self.platform}_*"):
                try:
                    await asyncio.to_thread(shutil.rmtree, qr_dir)
                except Exception:
                    pass
