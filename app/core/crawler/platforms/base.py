# -*- coding: utf-8 -*-
"""Lightweight crawler base interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional

from playwright.async_api import BrowserContext, Page


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
