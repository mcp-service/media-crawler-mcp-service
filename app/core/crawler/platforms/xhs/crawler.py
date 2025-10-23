# -*- coding: utf-8 -*-
"""Crawler implementation for Xiaohongshu."""

from __future__ import annotations

import asyncio
import os
from asyncio import Semaphore
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from playwright.async_api import BrowserContext, BrowserType, async_playwright

from app.config.settings import CrawlerType, Platform, global_settings
from app.core.crawler import CrawlerContext
from app.core.crawler.platforms.base import AbstractCrawler
from app.core.crawler.store import xhs as xhs_store
from app.core.crawler.tools import crawler_util, time_util
from app.core.login import login_service
from app.providers.logger import get_logger

from .client import XiaoHongShuClient
from .exception import DataFetchError
from .field import SearchNoteType, SearchSortType
from .help import (
    get_search_id,
    parse_creator_info_from_url,
    parse_note_info_from_note_url,
)
from .login import XiaoHongShuLogin

logger = get_logger()


class XiaoHongShuCrawler(AbstractCrawler):
    """Entry point for all Xiaohongshu crawl tasks."""

    def __init__(self, context: CrawlerContext) -> None:
        super().__init__(context)
        if context.platform != Platform.XIAOHONGSHU:
            raise ValueError("XHS crawler only supports Platform.XIAOHONGSHU")

        self.browser_opts = context.browser
        self.crawl_opts = context.crawl
        self.login_opts = context.login
        self.store_opts = context.store
        self.extra = context.extra or {}

        self.user_agent = self.browser_opts.user_agent or crawler_util.get_user_agent()
        self.client: Optional[XiaoHongShuClient] = None
        self.browser_context: Optional[BrowserContext] = None

    async def start(self) -> Dict[str, Any]:
        logger.info("[xhs.crawler] start crawler type=%s", self.ctx.crawler_type.value)
        async with async_playwright() as playwright:
            chromium = playwright.chromium

            self.browser_context = await self.launch_browser(
                chromium=chromium,
                playwright_proxy=None,
                user_agent=self.user_agent,
                headless=self.browser_opts.headless,
            )

            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto("https://www.xiaohongshu.com")

            await self._ensure_login_state()
            self.client = await self._build_client(self.browser_context)

            crawler_type = self.ctx.crawler_type
            if crawler_type == CrawlerType.SEARCH:
                return await self.search()
            if crawler_type == CrawlerType.DETAIL:
                return await self.get_detail()
            if crawler_type == CrawlerType.CREATOR:
                return await self.get_creator()
            if crawler_type == CrawlerType.COMMENTS:
                return await self.fetch_comments()

            raise RuntimeError(f"Unsupported crawler type: {crawler_type}")

    async def search(self) -> Dict[str, Any]:
        keywords = self.crawl_opts.keywords or ""
        keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
        if not keyword_list:
            raise ValueError("keywords 不能为空")

        limit = max(1, self.crawl_opts.max_notes_count)
        sleep_interval = float(self.extra.get("sleep_interval", self.crawl_opts.crawl_interval))
        note_type = SearchNoteType(self.extra.get("note_type", SearchNoteType.ALL.value))
        sort_type = SearchSortType(self.extra.get("sort_type", SearchSortType.GENERAL.value))
        start_page = int(self.extra.get("start_page", self.crawl_opts.start_page or 1))

        collected: List[Dict[str, Any]] = []

        for keyword in keyword_list:
            page = start_page
            search_id = get_search_id()

            while len(collected) < limit:
                logger.info("[xhs.search] keyword=%s page=%s collected=%s", keyword, page, len(collected))
                payload = await self.client.get_note_by_keyword(
                    keyword=keyword,
                    page=page,
                    sort=sort_type,
                    note_type=note_type,
                    search_id=search_id,
                )

                items = [
                    item
                    for item in payload.get("items") or []
                    if item.get("model_type") not in ("rec_query", "hot_query")
                ]
                if not items:
                    break

                details = await self._gather_details_from_items(items)
                for detail in details:
                    if not detail:
                        continue
                    await xhs_store.update_xhs_note(detail)
                    if self.store_opts.enable_save_media:
                        await xhs_store.update_xhs_note_media(detail)
                    collected.append(detail)
                    if len(collected) >= limit:
                        break

                if not payload.get("has_more", False):
                    break

                page += 1
                if sleep_interval > 0:
                    await asyncio.sleep(sleep_interval)

        return {
            "notes": collected,
            "total_count": len(collected),
            "crawl_info": self._build_crawl_info(),
        }

    async def get_detail(self) -> Dict[str, Any]:
        note_urls = self.crawl_opts.note_ids or self.extra.get("note_urls") or []
        if not note_urls:
            raise ValueError("note_urls 不能为空")

        semaphore = Semaphore(self.crawl_opts.max_concurrency)
        details: List[Dict[str, Any]] = []
        for url in note_urls:
            info = parse_note_info_from_note_url(url)
            note_detail = await self._get_note_detail(info.note_id, info.xsec_source, info.xsec_token, semaphore)
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
            collected.extend(notes)

        return {
            "notes": collected,
            "total_count": len(collected),
            "crawl_info": self._build_crawl_info(),
        }

    async def fetch_comments(self) -> Dict[str, Any]:
        note_urls = self.crawl_opts.note_ids or self.extra.get("note_urls") or []
        if not note_urls:
            raise ValueError("note_urls 不能为空")

        semaphore = Semaphore(self.crawl_opts.max_concurrency)
        comments: Dict[str, List[Dict[str, Any]]] = {}

        for url in note_urls:
            info = parse_note_info_from_note_url(url)
            note_detail = await self._get_note_detail(info.note_id, info.xsec_source, info.xsec_token, semaphore)
            if not note_detail:
                continue

            note_id = note_detail.get("note_id")
            if not note_id:
                continue

            comments[note_id] = []

            async def _collector(note: str, payload: List[Dict[str, Any]]):
                comments[note].extend(payload)

            await self.client.get_note_all_comments(
                note_id=note_id,
                xsec_token=note_detail.get("xsec_token", ""),
                crawl_interval=self.crawl_opts.crawl_interval,
                callback=_collector,
                max_count=self.crawl_opts.max_comments_per_note or 50,
            )

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
        if self.browser_context:
            await self.browser_context.close()

    async def _ensure_login_state(self) -> None:
        state = await login_service.refresh_platform_state(Platform.XIAOHONGSHU.value, force=False)
        if state.is_logged_in:
            logger.info("[xhs.login] 使用缓存登录状态")
            return

        login = XiaoHongShuLogin(
            login_type=self.login_opts.login_type.value,
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
            "referer": "https://www.xiaohongshu.com/",
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
            note_id = item.get("id") or item.get("note_id")
            if not note_id:
                continue
            xsec_token = item.get("xsec_token", "")
            xsec_source = item.get("xsec_source", "")
            tasks.append(self._get_note_detail(str(note_id), xsec_source, xsec_token, semaphore))
        return await asyncio.gather(*tasks)

    async def _get_note_detail(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str,
        semaphore: Semaphore,
    ) -> Optional[Dict[str, Any]]:
        async with semaphore:
            try:
                detail = await self.client.get_note_by_id(note_id, xsec_source, xsec_token)
            except DataFetchError:
                detail = None

            if not detail:
                detail = await self.client.get_note_by_id_from_html(
                    note_id,
                    xsec_source,
                    xsec_token,
                    enable_cookie=True,
                )
                if not detail:
                    logger.warning("[xhs.detail] 获取笔记失败 note_id=%s", note_id)
                    return None

            detail["xsec_token"] = xsec_token
            detail["xsec_source"] = xsec_source
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
            "crawler_type": self.ctx.crawler_type.value,
            "timestamp": time_util.get_current_timestamp(),
        }
