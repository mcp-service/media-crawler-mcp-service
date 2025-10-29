# -*- coding: utf-8 -*-
"""Lightweight crawler base interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional

from playwright.async_api import BrowserContext, BrowserType, Page, Playwright

from app.config.settings import CrawlerType, Platform


class AbstractCrawler(ABC):
    """Simplified crawler contract used by all platforms."""

    def __init__(self, *, platform: Platform, crawler_type: CrawlerType) -> None:
        self.platform = platform
        self.crawler_type = crawler_type
        self.context_page: Optional[Page] = None
        self.browser_context: Optional[BrowserContext] = None

    @abstractmethod
    async def start(self) -> Dict:
        """Run crawler entrypoint."""

    @abstractmethod
    async def search(self) -> Dict:
        """Search flow."""

    @abstractmethod
    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """Launch playwright browser context."""

    async def close(self) -> None:
        """Close browser context when available."""
        if self.browser_context:
            await self.browser_context.close()


class AbstractLogin(ABC):
    """Generic login interface for platform crawlers."""

    def __init__(
        self,
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        login_phone: Optional[str] = "",
        cookie_str: str = "",
    ):
        self.login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str

    @abstractmethod
    async def begin(self):
        """Begin login flow."""

    @abstractmethod
    async def login_by_qrcode(self):
        """Login using QR code."""

    @abstractmethod
    async def login_by_mobile(self):
        """Login via mobile phone."""

    @abstractmethod
    async def login_by_cookies(self):
        """Login with cookie string."""


class AbstractStore(ABC):
    """Data persistence interface for crawlers."""

    @abstractmethod
    async def store_content(self, content_item: Dict):
        """Persist content items."""

    @abstractmethod
    async def store_comment(self, comment_item: Dict):
        """Persist comment items."""

    @abstractmethod
    async def store_creator(self, creator: Dict):
        """Persist creator info."""
