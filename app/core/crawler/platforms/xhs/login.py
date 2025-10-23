# -*- coding: utf-8 -*-
"""Xiaohongshu login workflow."""

from __future__ import annotations

import asyncio
import functools
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import retry, retry_if_result, stop_after_attempt, wait_fixed

from app.core.crawler.platforms.base import AbstractLogin
from app.core.crawler.tools import crawler_util
from app.providers.logger import get_logger

logger = get_logger()


class XiaoHongShuLogin(AbstractLogin):
    """Implements qrcode and cookie login flows."""

    def __init__(
        self,
        *,
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        login_phone: Optional[str] = "",
        cookie_str: str = "",
    ):
        super().__init__(
            login_type=login_type,
            browser_context=browser_context,
            context_page=context_page,
            login_phone=login_phone,
            cookie_str=cookie_str,
        )

    async def begin(self) -> None:
        logger.info("[xhs.login] begin login type=%s", self.login_type)
        if self.login_type == "cookie":
            await self.login_by_cookies()
            return
        if self.login_type == "phone":
            raise NotImplementedError("phone login 未实现，请使用二维码或 Cookie")
        await self.login_by_qrcode()

    async def login_by_qrcode(self):
        selector = "xpath=//img[@class='qrcode-img']"
        base64_qrcode = await crawler_util.find_login_qrcode(self.context_page, selector)
        if not base64_qrcode:
            try:
                login_button = self.context_page.locator(
                    "xpath=//*[@id='app']/div[1]/div[2]/div[1]/ul/div[1]/button"
                )
                await login_button.click()
                base64_qrcode = await crawler_util.find_login_qrcode(self.context_page, selector)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("[xhs.login] 展示二维码失败: %s", exc)

        if not base64_qrcode:
            raise RuntimeError("未能获取小红书登录二维码")

        cookies = await self.browser_context.cookies()
        _, cookie_dict = crawler_util.convert_cookies(cookies)
        before_session = cookie_dict.get("web_session")

        loop = asyncio.get_running_loop()
        show_task = functools.partial(crawler_util.show_qrcode, base64_qrcode)
        loop.run_in_executor(None, show_task)

        await self._wait_login_state(before_session)
        await asyncio.sleep(5)

    async def login_by_mobile(self):
        raise NotImplementedError("phone login 未实现")

    async def login_by_cookies(self):
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

    @retry(stop=stop_after_attempt(120), wait=wait_fixed(1), retry=retry_if_result(lambda result: result is False))
    async def _wait_login_state(self, before_session: Optional[str]) -> bool:
        cookies = await self.browser_context.cookies()
        _, cookie_dict = crawler_util.convert_cookies(cookies)
        current_session = cookie_dict.get("web_session")
        if current_session and current_session != before_session:
            logger.info("[xhs.login] 登录状态已更新")
            return True
        return False
