# -*- coding: utf-8 -*-
"""Crawler implementation for Xiaohongshu."""

from __future__ import annotations

import asyncio
import os
from asyncio import Semaphore
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from playwright.async_api import BrowserContext, BrowserType, async_playwright
from playwright._impl._errors import TargetClosedError

from app.config.settings import CrawlerType, Platform, global_settings
from app.core.crawler import CrawlerContext
from app.core.crawler.platforms.base import AbstractCrawler
from app.core.crawler.store import xhs as xhs_store
from app.core.crawler.tools import crawler_util, time_util
from app.core.login import login_service
from app.core.login.exceptions import LoginExpiredError
from app.core.login.browser_manager import get_browser_manager
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
browser_manager = get_browser_manager()


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
        self._closed: bool = False

    async def start(self) -> Dict[str, Any]:
        logger.info(f"[xhs.crawler] start crawler type={self.ctx.crawler_type.value}")

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
        note_type = SearchNoteType(self.extra.get("note_type", SearchNoteType.ALL.value))
        sort_type = SearchSortType(self.extra.get("sort_type", SearchSortType.GENERAL.value))
        
        # 支持分页参数传入，不再使用while循环
        page_num = int(self.extra.get("page_num", self.crawl_opts.start_page or 1))
        page_size = int(self.extra.get("page_size", 20))  # 每页数量

        collected: List[Dict[str, Any]] = []

        for keyword in keyword_list:
            try:
                search_id = get_search_id()
                
                logger.info(f"[xhs.search] keyword={keyword} page={page_num} page_size={page_size}")
                payload = await self.client.get_note_by_keyword(
                    keyword=keyword,
                    page=page_num,
                    page_size=page_size,
                    sort=sort_type,
                    note_type=note_type,
                    search_id=search_id,
                )

                logger.info(f"[xhs.search] API response payload keys: {payload.keys() if payload else 'None'}")
                if not payload:
                    logger.warning(f"[xhs.search] Empty payload for keyword={keyword}")
                    continue

                items = [
                    item
                    for item in payload.get("items") or []
                    if item.get("model_type") not in ("rec_query", "hot_query")
                ]
                
                logger.info(f"[xhs.search] Filtered items count: {len(items)} for keyword={keyword}")
                if not items:
                    logger.info(f"[xhs.search] No items found for keyword={keyword} on page={page_num}")
                    continue

                # 限制每个关键词的结果数量（粗粒度：仅返回搜索摘要，不拉详情）
                items = items[:min(page_size, limit - len(collected))]

                for item in items:
                    info = self._extract_note_info_from_search_item(item)
                    if not info:
                        continue
                    note_id, xsec_source, xsec_token = info

                    note_obj = (item.get("note_card") or item.get("note") or {})
                    title = note_obj.get("display_title") or note_obj.get("title") or ""

                    user = note_obj.get("user", {}) if isinstance(note_obj, dict) else {}
                    interact = note_obj.get("interact_info", {}) if isinstance(note_obj, dict) else {}

                    def _to_int(v):
                        try:
                            return int(v)
                        except Exception:
                            try:
                                return int(str(v))
                            except Exception:
                                return None

                    collected.append({
                        "note_id": str(note_id),
                        "xsec_token": xsec_token,
                        "xsec_source": xsec_source,
                        "title": title,
                        "note_url": f"https://www.xiaohongshu.com/explore/{note_id}",
                        "user": {
                            "user_id": user.get("user_id"),
                            "nickname": user.get("nickname") or user.get("nick_name"),
                            "avatar": user.get("avatar"),
                        },
                        "interact_info": {
                            "liked_count": _to_int(interact.get("liked_count")),
                            "collected_count": _to_int(interact.get("collected_count")),
                            "comment_count": _to_int(interact.get("comment_count")),
                            "share_count": _to_int(interact.get("shared_count")),
                        }
                    })
                    if len(collected) >= limit:
                        break

                if len(collected) >= limit:
                    break

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
            "notes": collected,
            "total_count": len(collected),
            "page_info": {
                "current_page": page_num,
                "page_size": page_size,
                "has_more": len(collected) == page_size  # 如果当前页满了，可能还有更多
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
            "crawler_type": self.ctx.crawler_type.value,
            "timestamp": time_util.get_current_timestamp(),
        }
