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
                # Cookie 写入后刷新页面，确保状态生效
                await context_page.goto("https://www.bilibili.com/", wait_until="networkidle")

                if await login_obj.wait_for_login(timeout=10.0, interval=0.5):
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
                    await self.service.refresh_platform_state(session.platform, force=True)
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

                session.status = "failed"
                session.message = "Cookie 登录失败，Cookie 可能已失效"
                await self.service.persist_session(session)
            except Exception as exc:
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

        if payload.login_type == "qrcode":
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
                    await self.service.refresh_platform_state(session.platform, force=True)
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

            page = await browser_context.new_page()
            await page.goto("https://www.bilibili.com")

            cookies = await browser_context.cookies()
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
            cookie_dict = {c["name"]: c["value"] for c in cookies}

            bili_client = BilibiliClient(
                proxy=None,
                headers={
                    "User-Agent": self._user_agent,
                    "Cookie": cookie_str,
                    "Origin": "https://www.bilibili.com",
                    "Referer": "https://www.bilibili.com",
                },
                playwright_page=page,
                cookie_dict=cookie_dict,
            )

            async def _check_via_page() -> bool:
                try:
                    result = await page.evaluate(
                        """
                        async () => {
                            try {
                                const resp = await fetch("https://api.bilibili.com/x/web-interface/nav", {
                                    credentials: "include"
                                });
                                const status = resp.status;
                                const text = await resp.text();
                                let parsed = null;
                                try { parsed = JSON.parse(text); } catch (err) { parsed = null; }
                                return { status, body: parsed };
                            } catch (error) {
                                return { status: 0, error: String(error) };
                            }
                        }
                        """
                    )
                except Exception as exc:
                    self.logger.info(f"[登录管理] Bilibili 状态检测浏览器回退失败: {exc}")
                    return False

                if not isinstance(result, dict):
                    self.logger.info(f"[登录管理] Bilibili 状态检测浏览器回退返回异常类型: {result}")
                    return False
                body = result.get("body")
                if isinstance(body, dict):
                    if body.get("code") == 0:
                        payload = body.get("data") or {}
                        if isinstance(payload, dict) and payload.get("isLogin"):
                            return True
                    if body.get("isLogin"):
                        return True
                else:
                    self.logger.info(f"[登录管理] Bilibili 状态检测浏览器回退返回原始数据: {result}")
                return False

            is_logged_in = False
            via_page_logged_in = False
            try:
                is_logged_in = await bili_client.pong()
            except Exception as exc:
                fallback = bool(cookie_dict.get("SESSDATA") and cookie_dict.get("DedeUserID"))
                reason = str(exc)
                if fallback and ("request was banned" in reason or "412" in reason or "风控" in reason):
                    self.logger.debug("[登录管理] Bilibili 状态检测被风控阻断，使用 Cookie 回退结果")
                    via_page = await _check_via_page()
                    self.logger.debug(f"[登录管理] Bilibili 浏览器回退结果: {via_page}")
                    if via_page:
                        via_page_logged_in = True
                    is_logged_in = via_page or fallback
                else:
                    raise

            cookie_present = bool(cookie_dict.get("SESSDATA") and cookie_dict.get("DedeUserID"))
            if not is_logged_in and cookie_present:
                via_page_logged_in = await _check_via_page()
                self.logger.debug(f"[登录管理] Bilibili 状态检测补充回退结果: {via_page_logged_in}")
                if via_page_logged_in:
                    is_logged_in = True
                else:
                    self.logger.info("[登录管理] Bilibili 状态检测接口被风控，基于 Cookie 兜底为已登录")
                    is_logged_in = True

            state.is_logged_in = is_logged_in
            state.cookie_str = cookie_str
            state.cookie_dict = cookie_dict
            state.user_info = (
                {
                    "uid": cookie_dict.get("DedeUserID", ""),
                    "sessdata": (
                        cookie_dict.get("SESSDATA", "")[:20] + "..."
                        if cookie_dict.get("SESSDATA")
                        else ""
                    ),
                }
                if is_logged_in
                else {}
            )
            if is_logged_in:
                if via_page_logged_in or (state.user_info and state.user_info.get("uid")):
                    state.message = "已登录"
                else:
                    state.message = "Cookie 已缓存（待验证）"
            else:
                state.message = "未登录"
            state.last_checked_at = time.time()
            if is_logged_in:
                state.last_success_at = state.last_checked_at
            return state
        except Exception as exc:
            self.logger.error(f"[登录管理] 检查 Bilibili 登录状态失败: {exc}")
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
