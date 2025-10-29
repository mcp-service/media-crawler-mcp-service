# -*- coding: utf-8 -*-
"""HTTP client wrapper for Xiaohongshu PC web DOM mode."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
from playwright.async_api import BrowserContext, Page

from app.providers.logger import get_logger

from .extractor import XiaoHongShuExtractor

logger = get_logger()


class XiaoHongShuClient:
    """Xiaohongshu DOM mode client - extracts data from HTML without API calls."""

    def __init__(
        self,
        *,
        playwright_page: Page,
        cookie_dict: Dict[str, str],
        headers: Dict[str, str],
        proxy: Optional[str] = None,
        timeout: int = 60,
    ) -> None:
        self.page = playwright_page
        self.cookie_dict = cookie_dict
        self.base_headers = headers
        self.proxy = proxy
        self.timeout = timeout

        self._domain = "https://www.xiaohongshu.com"
        self._extractor = XiaoHongShuExtractor()

    async def update_cookies(self, browser_context: BrowserContext) -> None:
        """Refresh cookie headers after login."""
        cookies = await browser_context.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        self.base_headers["Cookie"] = cookie_str
        self.cookie_dict = {c["name"]: c["value"] for c in cookies}

    async def pong(self) -> bool:
        """Check login status by DOM presence like xiaohongshu-mcp.

        Navigate to /explore, wait for load, and check the user channel element:
        `.main-container .user .link-wrapper .channel`
        """
        try:
            await self.page.goto(f"{self._domain}/explore", wait_until="domcontentloaded")
        except Exception:
            # try landing page
            try:
                await self.page.goto(self._domain, wait_until="domcontentloaded")
            except Exception:
                pass

        # small settle time to allow CSR to render header
        try:
            await self.page.wait_for_timeout(600)
        except Exception:
            pass

        try:
            count = await self.page.eval_on_selector_all(
                ".main-container .user .link-wrapper .channel",
                "els => els.length"
            )
            return bool(count and int(count) > 0)
        except Exception:
            # fallback to simple querySelector
            try:
                return await self.page.evaluate(
                    "() => !!document.querySelector('.main-container .user .link-wrapper .channel')"
                )
            except Exception:
                return False

    async def get_note_by_id(self, note_id: str, xsec_source: str, xsec_token: str) -> Optional[Dict]:
        """Fetch note detail via DOM mode - prefer HTML extraction over API calls."""
        # 优先使用DOM模式获取详情
        detail = await self.get_note_by_id_from_html(
            note_id,
            xsec_source,
            xsec_token,
            enable_cookie=True,
        )
        return detail

    async def get_note_by_id_from_html(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str,
        enable_cookie: bool = False,
    ) -> Optional[Dict]:
        """Extract note detail from HTML using DOM mode."""
        # 仅在提供 xsec 参数时追加查询串，避免空值触发 404 跳转
        url = f"{self._domain}/explore/{note_id}"
        if xsec_token:
            source = xsec_source or "pc_search"
            url = f"{url}?xsec_token={xsec_token}&xsec_source={source}"
        headers = dict(self.base_headers)
        if not enable_cookie:
            headers.pop("Cookie", None)
        html = await self._request_html(url, headers=headers)
        detail: Optional[Dict] = None
        if html and "__INITIAL_STATE__" in html:
            detail = self._extractor.extract_note_detail_from_html(note_id, html)
        if not detail:
            # 回退：Playwright 渲染并直接从 window.__INITIAL_STATE__ 提取
            detail = await self._extract_note_via_page(url, note_id)
        logger.debug(f"[xhs.client] fetched html for note {note_id} length={len(html) if html else 0}")
        return detail

    async def _extract_note_via_page(self, url: str, note_id: str) -> Optional[Dict]:
        """Extract note data directly from page's window.__INITIAL_STATE__."""
        try:
            await self.page.goto(url, wait_until="domcontentloaded")
            try:
                await self.page.wait_for_function("() => !!window.__INITIAL_STATE__", timeout=2000)
            except Exception:
                pass
            state = await self.page.evaluate("() => window.__INITIAL_STATE__ || null")
            if not state:
                return None
            try:
                return (
                    (state.get("note") or {})
                    .get("noteDetailMap", {})
                    .get(note_id, {})
                    .get("note")
                )
            except Exception:
                return None
        except Exception:
            return None

    async def get_creator_info(
        self,
        *,
        user_id: str,
        xsec_token: str = "",
        xsec_source: str = "",
    ) -> Optional[Dict]:
        """Get creator info via DOM mode - extract from HTML."""
        path = f"/user/profile/{user_id}"
        if xsec_token and xsec_source:
            path = f"{path}?xsec_token={xsec_token}&xsec_source={xsec_source}"

        url = f"{self._domain}{path}"
        html = await self._request_html(url, headers=self.base_headers, return_response=True)
        return self._extractor.extract_creator_info_from_html(html)

    async def _request_html(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """Request HTML content for DOM parsing."""
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout, proxy=self.proxy) as client:
                resp = await client.get(url, headers=headers)
                logger.debug(f"url {url} status={resp.status_code}")
                if resp.status_code == 200:
                    return resp.text
                return ""
        except Exception:
            return ""


__all__ = ["XiaoHongShuClient"]