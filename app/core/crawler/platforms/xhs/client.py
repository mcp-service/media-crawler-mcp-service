# -*- coding: utf-8 -*-
"""HTTP client wrapper for Xiaohongshu PC web APIs."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional, Union

import httpx
from playwright.async_api import BrowserContext, Page
from tenacity import retry, stop_after_attempt, wait_fixed

from app.providers.logger import get_logger

from .exception import DataFetchError, IPBlockError
from .field import SearchNoteType, SearchSortType
from .help import get_search_id, sign
from .extractor import XiaoHongShuExtractor

logger = get_logger()


class XiaoHongShuClient:
    """Wraps Xiaohongshu APIs with signing logic executed inside Playwright."""

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

        self._host = "https://edith.xiaohongshu.com"
        self._domain = "https://www.xiaohongshu.com"
        self._extractor = XiaoHongShuExtractor()

        self._ip_error_code = 300012

    async def update_cookies(self, browser_context: BrowserContext) -> None:
        """Refresh cookie headers after login."""
        cookies = await browser_context.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        self.base_headers["Cookie"] = cookie_str
        self.cookie_dict = {c["name"]: c["value"] for c in cookies}

    async def pong(self) -> bool:
        """Check login state by calling nav API."""
        url = f"{self._domain}/api/sns/web/v1/homefeed"
        headers = await self._prepare_headers(url, None)
        try:
            await self._request("GET", url, headers=headers)
            return True
        except DataFetchError:
            return False

    async def get_note_by_keyword(
        self,
        *,
        keyword: str,
        page: int,
        sort: SearchSortType,
        note_type: SearchNoteType,
        search_id: Optional[str] = None,
    ) -> Dict:
        payload = {
            "keyword": keyword,
            "page": page,
            "page_size": 20,
            "sort": sort.value,
            "note_type": note_type.value,
            "search_id": search_id or get_search_id(),
        }
        return await self._post("/api/sns/web/v1/search/notes", payload)

    async def get_note_by_id(self, note_id: str, xsec_source: str, xsec_token: str) -> Optional[Dict]:
        params = {
            "note_id": note_id,
            "xsec_source": xsec_source,
            "xsec_token": xsec_token,
            "image_info": True,
        }
        try:
            return await self._get("/api/sns/web/v1/note/detail", params)
        except DataFetchError:
            return None

    async def get_note_by_id_from_html(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str,
        enable_cookie: bool = False,
    ) -> Optional[Dict]:
        url = (
            f"{self._domain}/explore/{note_id}"
            f"?xsec_token={xsec_token}&xsec_source={xsec_source}"
        )
        headers = dict(self.base_headers)
        if not enable_cookie:
            headers.pop("Cookie", None)
        html = await self._request("GET", url, headers=headers, return_response=True)
        return self._extractor.extract_note_detail_from_html(note_id, html)

    async def get_all_notes_by_creator(
        self,
        user_id: str,
        *,
        crawl_interval: float,
        callback: Optional[Callable[[List[Dict]], Any]] = None,
        max_notes: int = 200,
    ) -> List[Dict]:
        params = {
            "user_id": user_id,
            "cursor": "",
            "num": 30,
            "image_formats": "jpg,webp,avif",
        }
        result: List[Dict] = []
        has_more = True

        while has_more and len(result) < max_notes:
            response = await self._get("/api/sns/web/v1/user_posted", params)
            notes = response.get("notes") or []
            params["cursor"] = response.get("cursor", "")
            has_more = response.get("has_more", False)

            if callback and notes:
                await callback(notes)

            result.extend(notes)
            if len(result) >= max_notes or not has_more:
                break

            if crawl_interval > 0:
                await asyncio.sleep(crawl_interval)

        return result

    async def get_note_all_comments(
        self,
        *,
        note_id: str,
        xsec_token: str,
        crawl_interval: float,
        callback: Callable[[str, List[Dict]], Any],
        max_count: int,
    ) -> None:
        cursor = ""
        fetched = 0

        while fetched < max_count:
            params = {
                "note_id": note_id,
                "cursor": cursor,
                "image_formats": "jpg,webp,avif",
                "top_comment": True,
            }
            response = await self._get("/api/sns/web/v2/comment/list", params)
            comments = response.get("comments") or []
            if not comments:
                break

            await callback(note_id, comments)
            fetched += len(comments)
            cursor = response.get("cursor", "")
            if not response.get("has_more", False):
                break

            if crawl_interval > 0:
                await asyncio.sleep(crawl_interval)

    async def get_creator_info(
        self,
        *,
        user_id: str,
        xsec_token: str = "",
        xsec_source: str = "",
    ) -> Optional[Dict]:
        path = f"/user/profile/{user_id}"
        if xsec_token and xsec_source:
            path = f"{path}?xsec_token={xsec_token}&xsec_source={xsec_source}"

        url = f"{self._domain}{path}"
        html = await self._request("GET", url, headers=self.base_headers, return_response=True)
        return self._extractor.extract_creator_info_from_html(html)

    async def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self._host}{path}"
        headers = await self._prepare_headers(url, params)
        return await self._request("GET", url, headers=headers, params=params)

    async def _post(self, path: str, data: Dict) -> Dict:
        url = f"{self._host}{path}"
        headers = await self._prepare_headers(url, data)
        return await self._request("POST", url, headers=headers, json=data)

    async def _prepare_headers(self, url: str, data: Optional[Dict]) -> Dict[str, str]:
        encrypt_params = await self.page.evaluate(
            "([targetUrl, body]) => window._webmsxyw(targetUrl, body)", [url, data]
        )
        local_storage = await self.page.evaluate("() => window.localStorage")

        sign_result = sign(
            a1=self.cookie_dict.get("a1", ""),
            b1=local_storage.get("b1", ""),
            x_s=encrypt_params.get("X-s", ""),
            x_t=str(encrypt_params.get("X-t", "")),
        )

        headers = dict(self.base_headers)
        headers.update(
            {
                "X-S": sign_result["x-s"],
                "X-T": sign_result["x-t"],
                "x-s-common": sign_result["x-s-common"],
                "X-B3-Traceid": sign_result["x-b3-traceid"],
            }
        )
        return headers

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def _request(self, method: str, url: str, **kwargs) -> Union[str, Dict]:
        return_response = kwargs.pop("return_response", False)
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)

        if response.status_code in (461, 471):
            raise DataFetchError("触发风控验证码")

        if return_response:
            return response.text

        data = response.json()
        if data.get("success"):
            return data.get("data", data.get("success"))

        if data.get("code") == self._ip_error_code:
            raise IPBlockError("网络连接异常，请检查网络设置或稍后再试")

        raise DataFetchError(data.get("msg", "unknown error"))


__all__ = ["XiaoHongShuClient"]
