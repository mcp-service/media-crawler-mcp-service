# -*- coding: utf-8 -*-
"""Crawler implementation for Xiaohongshu."""

from __future__ import annotations

import asyncio
import os
from asyncio import Semaphore
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional, Union

from playwright.async_api import BrowserContext, BrowserType, async_playwright
from playwright._impl._errors import TargetClosedError

from app.config.settings import CrawlerType, LoginType, Platform, global_settings
from app.core.crawler.platforms.base import AbstractCrawler
from app.core.crawler.store import xhs as xhs_store
from app.core.crawler.tools import crawler_util, time_util
from app.core.login import login_service
from app.core.login.browser_manager import get_browser_manager
from app.core.login.exceptions import LoginExpiredError
from app.core.login.xhs.login import get_user_data_dir as xhs_user_data_dir
from app.providers.logger import get_logger

from .client import XiaoHongShuClient
from .exception import DataFetchError
from .help import (
    parse_creator_info_from_url,
    parse_note_info_from_note_url,
)
from .login import XiaoHongShuLogin
from .publish import XhsPublisher

logger = get_logger()
browser_manager = get_browser_manager()


def _resolve_login_type(
    cookie: Optional[str],
    phone: Optional[str],
    hint: Optional[Union[str, LoginType]],
) -> LoginType:
    if isinstance(hint, LoginType):
        return hint
    if isinstance(hint, str):
        try:
            return LoginType(hint)
        except ValueError:
            logger.warning("[xhs.login] Unknown login_type hint=%s, fallback to auto detect", hint)
    if cookie:
        return LoginType.COOKIE
    if phone:
        return LoginType.PHONE
    return LoginType.QRCODE


class XiaoHongShuCrawler(AbstractCrawler):
    """Entry point for all Xiaohongshu crawl tasks."""

    def __init__(
        self,
        *,
        crawler_type: CrawlerType,
        keywords: Optional[str] = None,
        note_items: Optional[List[Dict[str, Any]]] = None,
        creator_ids: Optional[List[str]] = None,
        login_cookie: Optional[str] = None,
        login_phone: Optional[str] = None,
        login_type: Optional[Union[str, LoginType]] = None,
        headless: Optional[bool] = None,
        enable_comments: bool = False,
        max_notes: int = 20,
        max_comments: int = 0,
        enable_save_media: Optional[bool] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(platform=Platform.XIAOHONGSHU, crawler_type=crawler_type)

        browser_cfg = global_settings.browser
        crawl_cfg = global_settings.crawl
        store_cfg = global_settings.store

        self.extra = dict(extra or {})

        user_agent = self.extra.pop("user_agent", browser_cfg.user_agent)
        proxy = self.extra.pop("proxy", browser_cfg.proxy)
        viewport_width = self.extra.pop("viewport_width", browser_cfg.viewport_width)
        viewport_height = self.extra.pop("viewport_height", browser_cfg.viewport_height)
        max_concurrency = self.extra.pop("max_concurrency", crawl_cfg.max_concurrency)
        crawl_interval = self.extra.pop("crawl_interval", crawl_cfg.crawl_interval)
        start_page = self.extra.pop("start_page", crawl_cfg.start_page)
        start_day = self.extra.pop("start_day", crawl_cfg.start_day)
        end_day = self.extra.pop("end_day", crawl_cfg.end_day)
        max_notes_per_day = self.extra.pop("max_notes_per_day", crawl_cfg.max_notes_per_day)

        resolved_headless = headless if headless is not None else browser_cfg.headless
        resolved_max_notes = max(max_notes, 0) or crawl_cfg.max_notes_count
        resolved_enable_save_media = (
            enable_save_media if enable_save_media is not None else store_cfg.enable_save_media
        )

        self.browser_opts = SimpleNamespace(
            headless=resolved_headless,
            user_agent=user_agent,
            proxy=proxy,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
        )

        self.crawl_opts = SimpleNamespace(
            keywords=keywords,
            note_ids=note_items,
            creator_ids=creator_ids,
            max_notes_count=resolved_max_notes,
            max_comments_per_note=max_comments,
            enable_get_comments=enable_comments,
            enable_get_sub_comments=False,
            enable_save_media=bool(resolved_enable_save_media),
            max_concurrency=max_concurrency,
            crawl_interval=crawl_interval,
            search_mode=self.extra.pop("search_mode", crawl_cfg.search_mode),
            start_page=start_page,
            start_day=start_day,
            end_day=end_day,
            max_notes_per_day=max_notes_per_day,
        )

        save_login_state = bool(self.extra.pop("save_login_state", True))
        login_type_hint = login_type if login_type is not None else self.extra.pop("login_type", None)
        resolved_login_type = _resolve_login_type(login_cookie, login_phone, login_type_hint)

        self.login_opts = SimpleNamespace(
            login_type=resolved_login_type,
            cookie=login_cookie,
            phone=login_phone,
            save_login_state=save_login_state,
        )

        self.store_opts = SimpleNamespace(
            save_format=str(store_cfg.save_format),
            enable_save_media=self.crawl_opts.enable_save_media,
        )

        self.user_agent = self.browser_opts.user_agent or crawler_util.get_user_agent()
        self.client: Optional[XiaoHongShuClient] = None
        self.browser_context: Optional[BrowserContext] = None
        self._closed: bool = False

    async def start(self) -> Dict[str, Any]:
        logger.info(f"[xhs.crawler] start crawler type={self.crawler_type.value}")

        # 使用浏览器管理器获取浏览器上下文
        user_data_dir = Path("browser_data") / Platform.XIAOHONGSHU.value
        viewport = {
            "width": self.browser_opts.viewport_width,
            "height": self.browser_opts.viewport_height,
        }

        try:
            self.browser_context, self.context_page, playwright = await browser_manager.acquire_context(
                platform=Platform.XIAOHONGSHU.value,
                user_data_dir=user_data_dir,
                headless=self.browser_opts.headless,
                viewport=viewport,
                user_agent=self.user_agent,
            )

            await self.context_page.goto("https://www.xiaohongshu.com")

            await self._ensure_login_state()
            self.client = await self._build_client(self.browser_context)

            crawler_type = self.crawler_type
            if crawler_type == CrawlerType.SEARCH:
                return await self.search()
            if crawler_type == CrawlerType.DETAIL:
                return await self.get_detail()
            if crawler_type == CrawlerType.CREATOR:
                return await self.get_creator()
            if crawler_type == CrawlerType.COMMENTS:
                return await self.fetch_comments()

            raise RuntimeError(f"Unsupported crawler type: {crawler_type}")
        finally:
            # 释放浏览器上下文引用（保持实例存活）
            await browser_manager.release_context(Platform.XIAOHONGSHU.value, keep_alive=True)

    async def search(self) -> Dict[str, Any]:
        keywords = self.crawl_opts.keywords or ""
        keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
        if not keyword_list:
            raise ValueError("keywords 不能为空")

        limit = max(1, self.crawl_opts.max_notes_count)
        sleep_interval = float(self.extra.get("sleep_interval", self.crawl_opts.crawl_interval))
        page_size = int(self.extra.get("page_size", 20))

        collected: List[Dict[str, Any]] = []

        for keyword in keyword_list:
            try:
                # Page-based search like xiaohongshu-mcp
                search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_explore_feed"
                logger.info(f"[xhs.search] goto search_result: {search_url}")
                await self.context_page.goto(search_url, wait_until="domcontentloaded")
                try:
                    await self.context_page.wait_for_function("() => !!window.__INITIAL_STATE__ && !!window.__INITIAL_STATE__.search", timeout=8000)
                except Exception:
                    logger.warning("[xhs.search] __INITIAL_STATE__ not ready")

                raw_json = await self.context_page.evaluate(
                    """
                    () => {
                        try {
                            const st = window.__INITIAL_STATE__;
                            if (st && st.search && st.search.feeds) {
                                const feeds = st.search.feeds;
                                const val = feeds.value !== undefined ? feeds.value : feeds._value;
                                if (val) return JSON.stringify(val);
                            }
                        } catch (e) {}
                        return "";
                    }
                    """
                )
                if not raw_json:
                    logger.info(f"[xhs.search] no feeds for keyword={keyword}")
                    continue

                import json as _json
                try:
                    feeds = _json.loads(raw_json)
                except Exception as je:
                    logger.error(f"[xhs.search] parse feeds json failed: {je}")
                    continue

                for item in feeds:
                    if len(collected) >= limit:
                        break
                    note_id = str(item.get("id") or item.get("noteId") or "").strip()
                    if not note_id:
                        continue
                    xsec_token = item.get("xsecToken", "")
                    note_obj = item.get("noteCard") or item.get("note") or {}
                    title = (note_obj.get("displayTitle") or note_obj.get("title") or "") if isinstance(note_obj, dict) else ""
                    user = note_obj.get("user", {}) if isinstance(note_obj, dict) else {}
                    inter = note_obj.get("interactInfo", {}) if isinstance(note_obj, dict) else {}

                    def _to_int(v):
                        try:
                            return int(v)
                        except Exception:
                            try:
                                return int(str(v))
                            except Exception:
                                return None

                    collected.append({
                        "note_id": note_id,
                        "xsec_token": xsec_token,
                        "xsec_source": "pc_feed",
                        "title": title,
                        "note_url": f"https://www.xiaohongshu.com/explore/{note_id}",
                        "user": {
                            "user_id": user.get("userId") or user.get("user_id"),
                            "nickname": user.get("nickname") or user.get("nickName") or user.get("nick_name"),
                            "avatar": user.get("avatar"),
                        },
                        "interact_info": {
                            "liked_count": _to_int(inter.get("likedCount")),
                            "collected_count": _to_int(inter.get("collectedCount")),
                            "comment_count": _to_int(inter.get("commentCount")),
                            "share_count": _to_int(inter.get("sharedCount")),
                        }
                    })

                if sleep_interval > 0:
                    await asyncio.sleep(sleep_interval)
                    
            except LoginExpiredError as e:
                # 账号权限或登录失效，直接向上抛出给 MCP 层返回 401
                logger.error(f"[xhs.search] Login required or permission denied: {e}")
                raise
            except Exception as e:
                logger.error(f"[xhs.search] Error processing keyword={keyword}: {type(e).__name__}: {e}")
                # 继续处理下一个关键词，而不是让整个搜索失败
                continue

        return {
            "notes": collected[:page_size],
            "total_count": min(len(collected), page_size),
            "page_info": {
                "current_page": 1,
                "page_size": page_size,
                "has_more": False
            },
            "crawl_info": self._build_crawl_info(),
        }

    async def get_detail(self) -> Dict[str, Any]:
        targets = self.crawl_opts.note_ids or self.extra.get("note_ids") or []
        if not targets:
            raise ValueError("note_ids 不能为空")

        semaphore = Semaphore(self.crawl_opts.max_concurrency)
        details: List[Dict[str, Any]] = []
        for item in targets:
            note_id = ""
            xsec_token = ""
            xsec_source = ""
            if isinstance(item, dict):
                note_id = str(item.get("note_id", "")).strip()
                xsec_token = str(item.get("xsec_token", "") or "")
                xsec_source = str(item.get("xsec_source", "") or "")
            else:
                s = str(item or "").strip()
                if not s:
                    continue
                if s.startswith("http://") or s.startswith("https://"):
                    info = parse_note_info_from_note_url(s)
                    note_id, xsec_source, xsec_token = info.note_id, info.xsec_source, info.xsec_token
                else:
                    note_id = s
            if not note_id:
                continue

            note_detail = await self._get_note_detail(note_id, xsec_source, xsec_token, semaphore)
            if not note_detail:
                continue
            await xhs_store.update_xhs_note(note_detail)
            if self.store_opts.enable_save_media:
                await xhs_store.update_xhs_note_media(note_detail)
            details.append(note_detail)

        if self.crawl_opts.enable_get_comments and self.crawl_opts.max_comments_per_note > 0:
            await self._batch_fetch_comments(details, self.crawl_opts.max_comments_per_note)

        return {
            "notes": details,
            "total_count": len(details),
            "crawl_info": self._build_crawl_info(),
        }

    async def get_creator(self) -> Dict[str, Any]:
        creator_ids = self.crawl_opts.creator_ids or []
        if not creator_ids:
            raise ValueError("creator_ids 不能为空")

        collected: List[Dict[str, Any]] = []
        crawl_interval = self.crawl_opts.crawl_interval
        for raw_id in creator_ids:
            info = parse_creator_info_from_url(raw_id)
            creator_detail = await self.client.get_creator_info(
                user_id=info.user_id,
                xsec_token=info.xsec_token,
                xsec_source=info.xsec_source,
            )
            if creator_detail:
                await xhs_store.save_creator(info.user_id, creator_detail)

            notes = await self.client.get_all_notes_by_creator(
                info.user_id,
                crawl_interval=crawl_interval,
                callback=self._creator_notes_callback,
                max_notes=self.crawl_opts.max_notes_count,
            )
            # 与 MediaCrawler 对齐：拉取每条作品详情，必要时再抓评论
            details = await self._gather_details_from_items(notes)
            for detail in details:
                if not detail:
                    continue
                await xhs_store.update_xhs_note(detail)
                if self.store_opts.enable_save_media:
                    await xhs_store.update_xhs_note_media(detail)
                collected.append(detail)

            if self.crawl_opts.enable_get_comments and self.crawl_opts.max_comments_per_note > 0 and collected:
                await self._batch_fetch_comments([d for d in details if d], self.crawl_opts.max_comments_per_note)

        return {
            "notes": collected,
            "total_count": len(collected),
            "crawl_info": self._build_crawl_info(),
        }

    async def fetch_comments(self) -> Dict[str, Any]:
        targets = self.crawl_opts.note_ids or self.extra.get("note_ids") or []
        if not targets:
            raise ValueError("note_ids 不能为空")

        semaphore = Semaphore(self.crawl_opts.max_concurrency)
        comments: Dict[str, List[Dict[str, Any]]] = {}

        for item in targets:
            # 只支持字典格式
            if not isinstance(item, dict):
                logger.warning(f"[xhs.comments] 不支持的格式，跳过: {type(item)}")
                continue

            note_id = str(item.get("note_id", "")).strip()
            xsec_token = str(item.get("xsec_token", "") or "")
            xsec_source = str(item.get("xsec_source", "") or "")

            if not note_id:
                logger.warning("[xhs.comments] note_id 为空，跳过")
                continue

            if not xsec_token:
                logger.warning(f"[xhs.comments] xsec_token 为空，跳过 note_id={note_id}")
                continue

            comments[note_id] = []

            async def _collector(note: str, payload: List[Dict[str, Any]]):
                comments[note].extend(payload)

            try:
                await self.client.get_note_all_comments(
                    note_id=note_id,
                    xsec_token=xsec_token,
                    crawl_interval=self.crawl_opts.crawl_interval,
                    callback=_collector,
                    max_count=self.crawl_opts.max_comments_per_note or 50,
                )
            except Exception as exc:
                logger.error(f"[xhs.comments] 获取评论失败 note_id={note_id}: {exc}")
                continue

        return {
            "comments": comments,
            "total_count": sum(len(v) for v in comments.values()),
            "crawl_info": self._build_crawl_info(),
        }

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict[str, Any]],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        if self.login_opts.save_login_state:
            user_data_dir = Path(os.getcwd()) / "browser_data" / Platform.XIAOHONGSHU.value
            user_data_dir.parent.mkdir(parents=True, exist_ok=True)
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=headless,
                user_agent=user_agent,
                accept_downloads=True,
                viewport={
                    "width": self.browser_opts.viewport_width,
                    "height": self.browser_opts.viewport_height,
                },
            )
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
            browser_context = await browser.new_context(
                user_agent=user_agent,
                viewport={
                    "width": self.browser_opts.viewport_width,
                    "height": self.browser_opts.viewport_height,
                },
            )

        stealth_js = Path(__file__).resolve().parents[3] / "libs" / "stealth.min.js"
        if stealth_js.exists():
            await browser_context.add_init_script(path=str(stealth_js))
        return browser_context

    async def close(self):
        """关闭浏览器上下文"""
        if self._closed:
            return
        try:
            if self.browser_context:
                await self.browser_context.close()
            logger.info("[XiaoHongShuCrawler.close] Browser context closed")
        except TargetClosedError:
            # 上下文已关闭时静默处理，避免多余告警日志
            logger.debug("[XiaoHongShuCrawler.close] Browser context already closed")
        except Exception as e:
            logger.debug(f"[XiaoHongShuCrawler.close] Ignore close error: {e}")
        finally:
            self._closed = True
            self.browser_context = None
            self.client = None

    async def _ensure_login_state(self) -> None:
        state = await login_service.refresh_platform_state(Platform.XIAOHONGSHU.value, force=False)
        if state.is_logged_in:
            logger.info("[xhs.login] 使用缓存登录状态")
            return

        # 在 MCP 工具场景下不自动触发登录，直接返回登录过期
        if self.extra.get("no_auto_login"):
            raise LoginExpiredError("登录过期，Cookie失效")

        login_type_value = (
            self.login_opts.login_type.value
            if isinstance(self.login_opts.login_type, LoginType)
            else str(self.login_opts.login_type)
        )

        login = XiaoHongShuLogin(
            login_type=login_type_value,
            browser_context=self.browser_context,
            context_page=self.context_page,
            login_phone=self.login_opts.phone,
            cookie_str=self.login_opts.cookie or state.cookie_str,
        )
        await login.begin()
        await login_service.refresh_platform_state(Platform.XIAOHONGSHU.value, force=True)

    async def _build_client(self, browser_context: BrowserContext) -> XiaoHongShuClient:
        cookies = await browser_context.cookies()
        cookie_str, cookie_dict = crawler_util.convert_cookies(cookies)

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://www.xiaohongshu.com",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://www.xiaohongshu.com/",
            "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": self.user_agent,
            "Cookie": cookie_str,
        }

        client = XiaoHongShuClient(
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
            headers=headers,
            proxy=self.browser_opts.proxy,
            timeout=60,
        )
        await client.update_cookies(browser_context)
        return client

    async def _gather_details_from_items(self, items: Iterable[Dict[str, Any]]) -> List[Optional[Dict]]:
        semaphore = Semaphore(self.crawl_opts.max_concurrency)
        tasks = []
        for item in items:
            note_info = self._extract_note_info_from_search_item(item)
            if not note_info:
                continue
            note_id, xsec_source, xsec_token = note_info
            tasks.append(self._get_note_detail(str(note_id), xsec_source, xsec_token, semaphore))
        return await asyncio.gather(*tasks)

    def _extract_note_info_from_search_item(self, item: Dict[str, Any]) -> Optional[tuple[str, str, str]]:
        """Best-effort extraction of note_id and xsec fields from a search item.

        The search API may return different shapes. We support:
        - Top-level note with fields: id/note_id, xsec_token, xsec_source
        - Nested under 'note' or 'note_card'
        - Only accept items that look like note results (model_type contains 'note')
        """
        model_type = str(item.get("model_type", "")).lower()
        # Skip non-note items early when model_type is present
        if model_type and "note" not in model_type:
            return None

        # Candidates to inspect in order
        candidates: List[Dict[str, Any]] = [item]
        if isinstance(item.get("note"), dict):
            candidates.append(item.get("note") or {})
        if isinstance(item.get("note_card"), dict):
            nc = item.get("note_card") or {}
            candidates.append(nc)
            # Some responses use 'display_note' inside note_card
            if isinstance(nc.get("display_note"), dict):
                candidates.append(nc.get("display_note") or {})

        note_id = ""
        xsec_token = ""
        xsec_source = ""
        for cand in candidates:
            note_id = cand.get("note_id") or cand.get("id") or note_id
            xsec_token = cand.get("xsec_token", xsec_token)
            xsec_source = cand.get("xsec_source", xsec_source)
        if not note_id:
            return None
        return str(note_id), str(xsec_source or ""), str(xsec_token or "")

    async def _get_note_detail(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str,
        semaphore: Semaphore,
    ) -> Optional[Dict[str, Any]]:
        async with semaphore:
            # 对齐 xiaohongshu-mcp：仅通过 HTML/DOM 提取详情
            detail = await self.client.get_note_by_id_from_html(
                note_id,
                xsec_source,
                xsec_token,
                enable_cookie=True,
            )
            if not detail:
                logger.warning(f"[xhs.detail] 获取笔记失败 note_id={note_id}")
                return None
            # Normalize essential fields for downstream schemas
            # Ensure note_id exists (feed note_card may miss it)
            if not detail.get("note_id"):
                detail["note_id"] = note_id
            # Normalize xsec token/source (prefer snake_case)
            xsec_token_val = detail.get("xsec_token") or detail.get("xsecToken") or xsec_token
            xsec_source_val = detail.get("xsec_source") or detail.get("xsecSource") or xsec_source
            detail["xsec_token"] = xsec_token_val or ""
            detail["xsec_source"] = xsec_source_val or ""
            # Cleanup camelCase duplicates to avoid confusion
            if "xsecToken" in detail:
                detail.pop("xsecToken", None)
            if "xsecSource" in detail:
                detail.pop("xsecSource", None)
            return detail

    async def _batch_fetch_comments(self, details: List[Dict[str, Any]], max_comments: int) -> None:
        for detail in details:
            note_id = detail.get("note_id")
            if not note_id:
                continue
            await self.client.get_note_all_comments(
                note_id=note_id,
                xsec_token=detail.get("xsec_token", ""),
                crawl_interval=self.crawl_opts.crawl_interval,
                callback=xhs_store.batch_update_xhs_note_comments,
                max_count=max_comments,
            )

    async def _creator_notes_callback(self, notes: List[Dict[str, Any]]) -> None:
        details = await self._gather_details_from_items(notes)
        for detail in details:
            if detail:
                await xhs_store.update_xhs_note(detail)

    def _build_crawl_info(self) -> Dict[str, Any]:
        return {
            "platform": Platform.XIAOHONGSHU.value,
            "crawler_type": self.crawler_type.value,
            "timestamp": time_util.get_current_timestamp(),
        }


async def _ensure_login_cookie() -> str:
    cookie = await login_service.get_cookie(Platform.XIAOHONGSHU.value)
    if not cookie:
        raise LoginExpiredError("登录过期，Cookie失效")
    return cookie


async def _run_xhs_crawler(**kwargs: Any) -> Dict[str, Any]:
    crawler = XiaoHongShuCrawler(**kwargs)
    try:
        return await crawler.start()
    finally:
        await crawler.close()


async def search(
    *,
    keywords: str,
    page_size: int = 20,
    page_num: int = 1,
    limit: Optional[int] = None,
    headless: Optional[bool] = None,
    enable_save_media: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    logger.info(f"[xhs.crawler.search] keywords={keywords}")
    extra = dict(kwargs)
    login_cookie = extra.pop("login_cookie", None)
    login_phone = extra.pop("login_phone", None)
    login_type_hint = extra.pop("login_type", None)

    if not login_cookie:
        login_cookie = await _ensure_login_cookie()

    extra.update({
        "page_size": page_size,
        "page_num": page_num,
        "no_auto_login": True,
    })

    total_limit = limit if limit is not None else page_size
    return await _run_xhs_crawler(
        crawler_type=CrawlerType.SEARCH,
        keywords=keywords,
        headless=headless,
        enable_comments=False,
        max_notes=total_limit,
        max_comments=0,
        enable_save_media=enable_save_media,
        extra=extra,
        login_cookie=login_cookie,
        login_phone=login_phone,
        login_type=login_type_hint,
    )


async def search_with_time_range(
    *,
    keywords: str,
    start_day: str,
    end_day: str,
    limit: int = 20,
    headless: Optional[bool] = None,
    enable_save_media: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    extra = dict(kwargs)
    extra.update({
        "start_day": start_day,
        "end_day": end_day,
    })
    return await search(
        keywords=keywords,
        limit=limit,
        headless=headless,
        enable_save_media=enable_save_media,
        **extra,
    )


async def get_detail(
    *,
    note_id: str,
    xsec_token: str,
    xsec_source: Optional[str] = "",
    headless: Optional[bool] = None,
    enable_save_media: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    note_info = {
        "note_id": note_id,
        "xsec_token": xsec_token or "",
        "xsec_source": xsec_source or "",
    }
    note_items = [note_info]

    extra = dict(kwargs)
    login_cookie = extra.pop("login_cookie", None)
    login_phone = extra.pop("login_phone", None)
    login_type_hint = extra.pop("login_type", None)

    if not login_cookie:
        login_cookie = await _ensure_login_cookie()

    extra.update({
        "no_auto_login": True,
        "note_ids": note_items,
    })

    return await _run_xhs_crawler(
        crawler_type=CrawlerType.DETAIL,
        note_items=note_items,
        headless=headless,
        enable_comments=False,
        max_notes=1,
        max_comments=0,
        enable_save_media=enable_save_media,
        extra=extra,
        login_cookie=login_cookie,
        login_phone=login_phone,
        login_type=login_type_hint,
    )


async def get_creator(
    *,
    creator_ids: List[str],
    max_notes: Optional[int] = None,
    headless: Optional[bool] = None,
    enable_save_media: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    extra = dict(kwargs)
    login_cookie = extra.pop("login_cookie", None)
    login_phone = extra.pop("login_phone", None)
    login_type_hint = extra.pop("login_type", None)

    if not login_cookie:
        login_cookie = await _ensure_login_cookie()

    extra.update({
        "no_auto_login": True,
    })

    resolved_max_notes = (
        max_notes
        if max_notes is not None
        else int(extra.pop("max_notes", global_settings.crawl.max_notes_count))
    )

    return await _run_xhs_crawler(
        crawler_type=CrawlerType.CREATOR,
        creator_ids=creator_ids,
        headless=headless,
        enable_comments=False,
        max_notes=resolved_max_notes,
        max_comments=0,
        enable_save_media=enable_save_media,
        extra=extra,
        login_cookie=login_cookie,
        login_phone=login_phone,
        login_type=login_type_hint,
    )


async def fetch_comments(
    *,
    note_id: str,
    xsec_token: str,
    xsec_source: str = "",
    max_comments: int = 50,
    headless: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    note_info = {
        "note_id": note_id,
        "xsec_token": xsec_token,
        "xsec_source": xsec_source or "",
    }
    note_items = [note_info]

    extra = dict(kwargs)
    login_cookie = extra.pop("login_cookie", None)
    login_phone = extra.pop("login_phone", None)
    login_type_hint = extra.pop("login_type", None)

    if not login_cookie:
        login_cookie = await _ensure_login_cookie()

    extra.update({
        "no_auto_login": True,
        "note_ids": note_items,
    })

    return await _run_xhs_crawler(
        crawler_type=CrawlerType.COMMENTS,
        note_items=note_items,
        headless=headless,
        enable_comments=True,
        max_notes=1,
        max_comments=max_comments,
        enable_save_media=False,
        extra=extra,
        login_cookie=login_cookie,
        login_phone=login_phone,
        login_type=login_type_hint,
    )


async def publish_image(
    *,
    title: str,
    content: str,
    images: List[str],
    tags: Optional[List[str]] = None,
    headless: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    tags = tags or []
    extra = dict(kwargs)

    login_cookie = extra.pop("login_cookie", None)
    if not login_cookie:
        login_cookie = await _ensure_login_cookie()

    browser_cfg = global_settings.browser
    viewport = {"width": browser_cfg.viewport_width, "height": browser_cfg.viewport_height}

    context = None
    page = None
    playwright = None
    try:
        context, page, playwright = await browser_manager.acquire_context(
            platform=Platform.XIAOHONGSHU.value,
            user_data_dir=xhs_user_data_dir(),
            headless=browser_cfg.headless if headless is None else headless,
            viewport=viewport,
            user_agent=browser_cfg.user_agent or crawler_util.get_user_agent(),
        )
    except Exception:
        context, playwright = await browser_manager.get_context_for_check(
            platform=Platform.XIAOHONGSHU.value,
            user_data_dir=xhs_user_data_dir(),
            headless=browser_cfg.headless if headless is None else headless,
            viewport=viewport,
            user_agent=browser_cfg.user_agent or crawler_util.get_user_agent(),
        )
        page = await context.new_page()

    try:
        publisher = XhsPublisher(page)
        result = await publisher.publish_image_post(
            title=title,
            content=content,
            images=images,
            tags=tags,
        )
        return result
    finally:
        try:
            if page:
                await page.close()
        except Exception:
            pass
        await browser_manager.release_context(Platform.XIAOHONGSHU.value, keep_alive=True)


async def publish_video(
    *,
    title: str,
    content: str,
    video: str,
    tags: Optional[List[str]] = None,
    headless: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    tags = tags or []
    extra = dict(kwargs)

    login_cookie = extra.pop("login_cookie", None)
    if not login_cookie:
        login_cookie = await _ensure_login_cookie()

    browser_cfg = global_settings.browser
    viewport = {"width": browser_cfg.viewport_width, "height": browser_cfg.viewport_height}

    context = None
    page = None
    playwright = None
    try:
        context, page, playwright = await browser_manager.acquire_context(
            platform=Platform.XIAOHONGSHU.value,
            user_data_dir=xhs_user_data_dir(),
            headless=browser_cfg.headless if headless is None else headless,
            viewport=viewport,
            user_agent=browser_cfg.user_agent or crawler_util.get_user_agent(),
        )
    except Exception:
        context, playwright = await browser_manager.get_context_for_check(
            platform=Platform.XIAOHONGSHU.value,
            user_data_dir=xhs_user_data_dir(),
            headless=browser_cfg.headless if headless is None else headless,
            viewport=viewport,
            user_agent=browser_cfg.user_agent or crawler_util.get_user_agent(),
        )
        page = await context.new_page()

    try:
        publisher = XhsPublisher(page)
        result = await publisher.publish_video_post(
            title=title,
            content=content,
            video=video,
            tags=tags,
        )
        return result
    finally:
        try:
            if page:
                await page.close()
        except Exception:
            pass
        await browser_manager.release_context(Platform.XIAOHONGSHU.value, keep_alive=True)
