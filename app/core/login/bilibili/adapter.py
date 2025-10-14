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

from app.config.settings import Platform, global_settings
from app.crawler.platforms.bilibili.client import BilibiliClient
from app.crawler.platforms.bilibili.login import BilibiliLogin

from ..base import BaseLoginAdapter
from ..models import LoginSession, LoginStartPayload, PlatformLoginState


class BilibiliLoginAdapter(BaseLoginAdapter):
    """Bilibili 登录适配器"""

    def __init__(self, service):
        super().__init__(service)
        browser_cfg = getattr(global_settings, "browser", None)
        self._headless = getattr(browser_cfg, "headless", False)
        self._user_agent = getattr(
            browser_cfg,
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        viewport_width = getattr(browser_cfg, "viewport_width", 1280) or 1280
        viewport_height = getattr(browser_cfg, "viewport_height", 800) or 800
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

        qr_dir = self._qr_code_dir(payload.login_type)
        if qr_dir.exists():
            try:
                shutil.rmtree(qr_dir)
            except Exception as exc:
                self.logger.warning(f"[登录管理] 清理旧二维码目录失败: {exc}")

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
        session.metadata["login_obj"] = login_obj

        if payload.login_type == "qrcode":
            session.status = "started"
            session.message = "正在生成二维码..."
            session.qrcode_timestamp = time.time()

            qr_path = await login_obj.generate_qrcode()
            if qr_path is None:
                session.status = "failed"
                session.message = "二维码生成失败，请稍后重试"
                await self.service.cleanup_session(session.id, remove_resources=True)
            else:
                qr_code_base64 = await self._wait_for_qrcode(payload.login_type)
                if qr_code_base64:
                    session.qr_code_base64 = qr_code_base64
                    session.status = "waiting"
                    session.message = "二维码已生成，等待扫码..."
                    poll_task = asyncio.create_task(self._poll_qrcode_session(session.id))
                    session.metadata["task"] = poll_task
                else:
                    session.status = "failed"
                    session.message = "二维码生成超时，请重新开始登录"
                    await self.service.cleanup_session(session.id, remove_resources=True)
        else:
            session.status = "processing"
            session.message = "正在尝试登录..."
            session.qrcode_timestamp = 0.0
            login_task = asyncio.create_task(self._execute_login(session.id))
            session.metadata["task"] = login_task

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

    async def _poll_qrcode_session(self, session_id: str) -> None:
        """轮询检测二维码登录状态"""
        session = self.service.get_session(session_id)
        if not session:
            return

        login_obj: Optional[BilibiliLogin] = session.metadata.get("login_obj")
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
                    await self.service.refresh_platform_state(session.platform, force=True)
                    break

                if time.time() - start_ts > timeout_seconds:
                    session.status = "expired"
                    session.message = "二维码已过期，请重新获取"
                    self.logger.warning(
                        f"[登录管理] Bilibili 登录超时: session_id={session_id}"
                    )
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
            session.metadata.pop("task", None)
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

        login_obj: Optional[BilibiliLogin] = session.metadata.get("login_obj")
        if not login_obj:
            self.logger.error(f"[登录管理] 会话缺少登录对象: {session_id}")
            return

        if session.login_type == "qrcode":
            # 二维码登录不再由服务端主动拉起，改为前端轮询触发
            return

        try:
            session.status = "processing"
            session.message = "正在尝试登录..."

            await login_obj.begin()

            session.status = "success"
            session.message = "登录成功"
            self.logger.info(f"[登录管理] Bilibili 登录成功: session_id={session_id}")

            await self.service.refresh_platform_state(session.platform, force=True)
        except Exception as exc:
            session.status = "failed"
            session.message = f"登录失败: {exc}"
            session.metadata["error"] = str(exc)
            self.logger.error(
                f"[登录管理] Bilibili 登录失败: session_id={session_id}, error={exc}"
            )
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

            is_logged_in = await bili_client.pong()
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
            state.message = "已登录" if is_logged_in else "未登录"
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

