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
        # API expects integer code for note_type, not string labels
        note_type_code = self._normalize_note_type(note_type)

        payload = {
            "keyword": keyword,
            "page": page,
            "page_size": 20,
            "sort": sort.value,
            "note_type": note_type_code,
            "search_id": search_id or get_search_id(),
        }
        return await self._post("/api/sns/web/v1/search/notes", payload)

    def _normalize_note_type(self, note_type: Union[SearchNoteType, str, int]) -> int:
        """Convert note_type to API expected integer codes.

        Mapping (based on PC web API behavior):
        - 0: all
        - 1: video
        - 2: image
        """
        mapping = {"all": 0, "video": 1, "image": 2}
        if isinstance(note_type, SearchNoteType):
            return mapping.get(note_type.value, 0)
        if isinstance(note_type, int):
            return note_type
        try:
            # accept numeric strings
            return int(str(note_type))
        except (TypeError, ValueError):
            s = str(note_type).lower().strip()
            return mapping.get(s, 0)

    async def get_note_by_id(self, note_id: str, xsec_source: str, xsec_token: str) -> Optional[Dict]:
        """Fetch note detail using API, with MediaCrawler's feed fallback.

        Strategy:
        1) Try feed endpoint (/api/sns/web/v1/feed) with source_note_id (more tolerant)
        2) Fallback to note/detail GET
        3) HTML extraction fallback handled by caller
        """
        # 1) feed endpoint (MediaCrawler behavior)
        feed_data: Dict[str, Any] = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": 1},
        }
        # Default xsec_source when blank (observed as pc_search in MediaCrawler)
        xs = xsec_source or "pc_search"
        if xs:
            feed_data["xsec_source"] = xs
        if xsec_token:
            feed_data["xsec_token"] = xsec_token
        try:
            feed_res = await self._post_once("/api/sns/web/v1/feed", feed_data)
            if isinstance(feed_res, dict) and feed_res.get("items"):
                first = feed_res["items"][0]
                note_card = first.get("note_card") or {}
                if note_card:
                    return note_card
        except DataFetchError:
            pass

        # 2) fallback to note/detail GET
        params: Dict[str, Any] = {"note_id": note_id, "image_formats": "jpg,webp,avif"}
        if xsec_source:
            params["xsec_source"] = xsec_source
        if xsec_token:
            params["xsec_token"] = xsec_token
        try:
            return await self._get_once("/api/sns/web/v1/note/detail", params)
        except DataFetchError:
            return None

    async def get_note_by_id_from_html(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str,
        enable_cookie: bool = False,
    ) -> Optional[Dict]:
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

    async def _get_html_via_page(self, url: str) -> str:
        try:
            await self.page.goto(url, wait_until="domcontentloaded")
            try:
                await self.page.wait_for_function(
                    "() => typeof window.__INITIAL_STATE__ === 'object'",
                    timeout=1500,
                )
            except Exception:
                pass
            return await self.page.content()
        except Exception:
            return ""

    async def _extract_note_via_page(self, url: str, note_id: str) -> Optional[Dict]:
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

    async def _request_html(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout, proxy=self.proxy) as client:
                resp = await client.get(url, headers=headers)
                logger.debug(f"url {url} status={resp.status_code}")
                if resp.status_code == 200:
                    return resp.text
                return ""
        except Exception:
            return ""

    async def _post_once(self, path: str, data: Dict) -> Dict:
        url = f"{self._host}{path}"
        headers = await self._prepare_headers(url, data)
        return await self._request_once("POST", url, headers=headers, json=data)

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
                "top_comment_id": "",
                "xsec_token": xsec_token,
            }
            # 使用单次 GET，避免在 404 情况下重试三次
            response = await self._get_once("/api/sns/web/v2/comment/page", params)
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
        # 避免对 feed 端点进行多次重试，直接走单次请求
        if path == "/api/sns/web/v1/feed":
            return await self._post_once(path, data)
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
            logger.debug(f"url {url} status={response.status_code}")
        if response.status_code in (461, 471):
            raise DataFetchError("触发风控验证码")

        if return_response:
            return response.text

        if response.status_code != 200:
            raise DataFetchError(f"http {response.status_code}")

        try:
            data = response.json()
        except Exception as exc:
            raise DataFetchError(f"invalid response: {exc}")
        if data.get("success"):
            return data.get("data", data.get("success"))

        if data.get("code") == self._ip_error_code:
            raise IPBlockError("网络连接异常，请检查网络设置或稍后再试")

        raise DataFetchError(data.get("msg", "unknown error"))

    async def _request_once(self, method: str, url: str, **kwargs) -> Union[str, Dict]:
        """Single-attempt request without tenacity retry, used for endpoints
        where retries are not helpful (e.g., 404 for note detail)."""
        return_response = kwargs.pop("return_response", False)
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)
            logger.debug(f"url {url} status={response.status_code}")
        if response.status_code in (461, 471):
            raise DataFetchError("触发风控验证码")
        if return_response:
            return response.text
        try:
            data = response.json()
        except Exception as exc:
            raise DataFetchError(f"invalid response: {exc}")
        if data.get("success"):
            return data.get("data", data.get("success"))
        if data.get("code") == self._ip_error_code:
            raise IPBlockError("网络连接异常，请检查网络设置或稍后再试")
        raise DataFetchError(data.get("msg", "unknown error"))

    async def _get_once(self, path: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self._host}{path}"
        headers = await self._prepare_headers(url, params)
        return await self._request_once("GET", url, headers=headers, params=params)


__all__ = ["XiaoHongShuClient"]
