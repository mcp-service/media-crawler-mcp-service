# -*- coding: utf-8 -*-
"""Login adapter for Xiaohongshu platform."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any, Dict

from playwright.async_api import async_playwright

from app.config.settings import Platform, global_settings
from app.core.crawler.platforms.xhs.login import XiaoHongShuLogin
from app.core.crawler.tools import crawler_util
from app.core.login.base import BaseLoginAdapter
from app.core.login.models import LoginSession, LoginStartPayload, PlatformLoginState
from app.providers.logger import get_logger

logger = get_logger()


class XiaoHongShuLoginAdapter(BaseLoginAdapter):
    """XHS login adapter integrated with LoginService."""

    platform = Platform.XIAOHONGSHU.value

    def __init__(self, service):
        super().__init__(service)
        browser_cfg = global_settings.browser
        self._headless = browser_cfg.headless
        self._user_agent = browser_cfg.user_agent or crawler_util.get_user_agent()
        self._viewport = {
            "width": browser_cfg.viewport_width,
            "height": browser_cfg.viewport_height,
        }

    @property
    def display_name(self) -> str:  # pragma: no cover - trivial
        return "小红书"

    @property
    def user_data_dir(self) -> Path:
        return Path("browser_data") / self.platform

    async def start_login(self, session: LoginSession, payload: LoginStartPayload) -> Dict[str, Any]:
        session.status = "starting"
        session.message = "启动小红书登录流程"
        await self.service.persist_session(session)

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
        await context_page.goto("https://www.xiaohongshu.com")

        session.browser_context = browser_context
        session.context_page = context_page
        session.playwright = playwright

        login = XiaoHongShuLogin(
            login_type=payload.login_type,
            browser_context=browser_context,
            context_page=context_page,
            login_phone=payload.phone,
            cookie_str=payload.cookie,
        )

        try:
            await login.begin()
            await self._finalize_success(session)
        except Exception as exc:
            logger.error("[xhs.login] 登录失败: %s", exc)
            await self._finalize_failure(session, str(exc))

        return session.to_public_dict()

    async def fetch_login_state(self) -> PlatformLoginState:
        playwright = await async_playwright().start()
        chromium = playwright.chromium

        browser_context = await chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=True,
            viewport=self._viewport,
            user_agent=self._user_agent,
            accept_downloads=True,
        )

        cookies = await browser_context.cookies()
        cookie_str, cookie_dict = crawler_util.convert_cookies(cookies)
        is_logged_in = bool(cookie_dict.get("web_session"))

        state = PlatformLoginState(
            platform=self.platform,
            is_logged_in=is_logged_in,
            cookie_dict=cookie_dict,
            cookie_str=cookie_str,
            message="已登录" if is_logged_in else "未登录",
        )

        await browser_context.close()
        await playwright.stop()
        return state

    async def logout(self) -> None:
        await self.service.cleanup_platform_sessions(self.platform, drop=True)
        data_dir = self.user_data_dir
        if data_dir.exists():
            await asyncio.to_thread(shutil.rmtree, data_dir, ignore_errors=True)

    async def _finalize_success(self, session: LoginSession) -> None:
        session.status = "success"
        session.message = "登录成功"
        await self._persist_state(session, True)

    async def _finalize_failure(self, session: LoginSession, message: str) -> None:
        session.status = "failed"
        session.message = message or "登录失败"
        await self._persist_state(session, False)

    async def _persist_state(self, session: LoginSession, success: bool) -> None:
        try:
            cookies = await session.browser_context.cookies() if session.browser_context else []
            cookie_str, cookie_dict = crawler_util.convert_cookies(cookies)
        except Exception:
            cookie_str, cookie_dict = "", {}

        state = PlatformLoginState(
            platform=self.platform,
            is_logged_in=success and bool(cookie_dict.get("web_session")),
            cookie_dict=cookie_dict,
            cookie_str=cookie_str,
            message=session.message,
        )
        await self.service.persist_session(session)
        await self.service._storage.save_platform_state(state)  # type: ignore[attr-defined]

        await self._cleanup_browser(session)

    async def _cleanup_browser(self, session: LoginSession) -> None:
        if session.browser_context:
            await session.browser_context.close()
            session.browser_context = None
        if session.playwright:
            await session.playwright.stop()
            session.playwright = None
