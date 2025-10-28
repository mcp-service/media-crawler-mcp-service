# -*- coding: utf-8 -*-
"""HTTP client wrapper for Xiaohongshu PC web APIs."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional, Union
import time

import httpx
from playwright.async_api import BrowserContext, Page
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from app.providers.logger import get_logger
from app.core.login.exceptions import LoginExpiredError

from .exception import DataFetchError, IPBlockError
from .field import SearchNoteType, SearchSortType
from .help import get_search_id, sign
from .extractor import XiaoHongShuExtractor
from .secsign import seccore_signv2_playwright

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
        """Check login using signed API call with browser fallback.

        1) Try signed GET /api/sns/web/v1/homefeed (mnsv2/_webmsxyw)
        2) If signing/API blocked, fallback to page context heuristic
           (web_session cookie or localStorage a1 present)
        """
        path = "/api/sns/web/v1/homefeed"
        try:
            headers = await self._prepare_headers(path, None)
            url = f"{self._domain}{path}"
            await self._request("GET", url, headers=headers)
            return True
        except DataFetchError as e:
            logger.warning(f"[xhs.client] signed homefeed failed: {e}")
        except Exception as e:
            logger.warning(f"[xhs.client] signed homefeed error: {e}")

        # Fallback: page context check (less strict but avoids false negatives during risk control)
        try:
            cur = ""
            try:
                cur = self.page.url or ""
            except Exception:
                cur = ""
            if "xiaohongshu.com" not in cur:
                try:
                    await self.page.goto(self._domain, wait_until="domcontentloaded")
                except Exception:
                    pass
            return await self.page.evaluate(
                """
                () => {
                    try {
                        const hasCookie = (document.cookie || '').includes('web_session=');
                        const a1 = (window.localStorage && window.localStorage.getItem('a1')) || '';
                        return Boolean(hasCookie || a1);
                    } catch (e) {
                        return false;
                    }
                }
                """
            )
        except Exception:
            return False

    async def get_note_by_keyword(
        self,
        *,
        keyword: str,
        page: int,
        page_size: int,
        sort: SearchSortType,
        note_type: SearchNoteType,
        search_id: Optional[str] = None,
    ) -> Dict:
        # API expects integer code for note_type, not string labels
        note_type_code = self._normalize_note_type(note_type)

        payload = {
            "keyword": keyword,
            "page": page,
            "page_size": int(page_size) if page_size else 20,
            "sort": sort.value,
            "note_type": note_type_code,
            "search_id": search_id or get_search_id(),
        }
        # 为搜索接口设置与关键字匹配的 Referer，部分风控策略依赖该来源页
        from urllib.parse import quote
        path = "/api/sns/web/v1/search/notes"
        headers = await self._prepare_headers(path, payload)
        headers["Referer"] = f"{self._domain}/search_result?keyword={quote(keyword)}"
        url = f"{self._host}{path}"
        return await self._request("POST", url, headers=headers, json=payload)

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
        """Fetch note detail, prefer HTML when token is provided.

        If xsec_token is present (detail tool requires it), avoid API endpoints and
        directly extract from explore HTML to reduce 406/404 noise. When token is
        absent (other flows), fall back to API strategies.
        """
        if xsec_token:
            detail = await self.get_note_by_id_from_html(
                note_id,
                xsec_source,
                xsec_token,
                enable_cookie=True,
            )
            if detail:
                return detail

        # 1) feed endpoint (fallback when token is absent or HTML fallback failed)
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
        # 注意：_prepare_headers 传入的是 path (URI) 而不是完整 URL
        headers = await self._prepare_headers(path, data)
        url = f"{self._host}{path}"
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
        # 构建完整 URI（包含查询参数）用于签名
        final_path = path
        if params:
            from urllib.parse import urlencode
            final_path = f"{path}?{urlencode(params)}"
        # 注意：_prepare_headers 传入的是 URI (路径) 而不是完整 URL
        headers = await self._prepare_headers(final_path, None)
        url = f"{self._host}{final_path}"
        return await self._request("GET", url, headers=headers)

    async def _post(self, path: str, data: Dict) -> Dict:
        # 避免对 feed 端点进行多次重试，直接走单次请求
        if path == "/api/sns/web/v1/feed":
            return await self._post_once(path, data)
        # 注意：_prepare_headers 传入的是 path (URI) 而不是完整 URL
        headers = await self._prepare_headers(path, data)
        url = f"{self._host}{path}"
        return await self._request("POST", url, headers=headers, json=data)

    async def _prepare_headers(self, url: str, data: Optional[Dict]) -> Dict[str, str]:
        # 确保已加载站点脚本（提供 window.mnsv2 或 _webmsxyw）
        try:
            current_url = self.page.url or ""
        except Exception:
            current_url = ""
        if self._domain not in current_url:
            try:
                await self.page.goto(self._domain, wait_until="domcontentloaded")
            except Exception:
                # 继续尝试签名，不强制中断
                pass

        # 优先 seccore v2（mnsv2），不可用时回退 _webmsxyw；都不可用则报错
        x_t = str(int(time.time()))
        local_storage = await self.page.evaluate("() => window.localStorage")
        x_s: Optional[str] = None

        # 检查 mnsv2 是否可用
        try:
            has_mnsv2 = await self.page.evaluate("() => typeof window.mnsv2 === 'function'")
        except Exception:
            has_mnsv2 = False

        if has_mnsv2:
            x_s = await seccore_signv2_playwright(self.page, url, data)
        else:
            # 回退老方案 _webmsxyw
            try:
                has_legacy = await self.page.evaluate("() => typeof window._webmsxyw === 'function'")
            except Exception:
                has_legacy = False
            if has_legacy:
                encrypt_params = await self.page.evaluate(
                    "([targetUrl, body]) => window._webmsxyw(targetUrl, body)", [url, data]
                )
                x_s = encrypt_params.get("X-s", "")
                x_t = str(encrypt_params.get("X-t", x_t))

        if not x_s:
            raise DataFetchError("xhs seccore not ready: missing mnsv2/_webmsxyw")

        sign_result = sign(
            a1=self.cookie_dict.get("a1", ""),
            b1=local_storage.get("b1", ""),
            x_s=x_s,
            x_t=x_t,
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

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), retry=retry_if_exception_type((DataFetchError, IPBlockError)))
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

        # 业务失败增强日志，便于定位（200 但失败通常为签名/风控/登录）
        code = data.get("code")
        msg = data.get("msg") or data.get("message") or "unknown error"
        logger.error(f"[xhs.client] API error url={url} code={code} msg={msg}")
        if code == -104:
            # 账号无权限或登录失效：不重试，直接抛出登录过期异常供上层转换为 401
            raise LoginExpiredError(msg or "需要登录或账号权限不足")
        if code == self._ip_error_code:
            raise IPBlockError("网络连接异常，请检查网络设置或稍后再试")
        raise DataFetchError(msg)

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
        # 构建完整 URI（包含查询参数）用于签名
        final_path = path
        if params:
            from urllib.parse import urlencode
            final_path = f"{path}?{urlencode(params)}"
        # 注意：_prepare_headers 传入的是 URI (路径) 而不是完整 URL
        headers = await self._prepare_headers(final_path, None)
        url = f"{self._host}{final_path}"
        return await self._request_once("GET", url, headers=headers)


__all__ = ["XiaoHongShuClient"]
