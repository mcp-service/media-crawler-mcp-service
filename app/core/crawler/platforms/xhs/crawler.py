# -*- coding: utf-8 -*-
"""Crawler implementation for Xiaohongshu."""

from __future__ import annotations

import asyncio
import os
from asyncio import Semaphore
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional, Union

from playwright.async_api import BrowserContext, BrowserType, Page, async_playwright
from playwright._impl._errors import TargetClosedError

from app.config.settings import CrawlerType, LoginType, Platform, global_settings
from app.core.crawler.store import xhs as xhs_store
from app.core.crawler.tools import crawler_util, time_util
from app.core.login import login_service
from app.core.login.browser_manager import get_browser_manager
from app.core.login.exceptions import LoginExpiredError
from app.core.login.xhs.login import get_user_data_dir as xhs_user_data_dir
from app.providers.logger import get_logger

from .client import XiaoHongShuClient
from .login import XiaoHongShuLogin
from .publish import XhsPublisher

logger = get_logger()
browser_manager = get_browser_manager()


def _parse_note_url(url: str) -> SimpleNamespace:
    """简单解析小红书笔记URL，提取note_id等信息"""
    import re
    from urllib.parse import urlparse, parse_qs

    # 提取note_id
    note_id_match = re.search(r'/explore/([a-f0-9]+)', url)
    note_id = note_id_match.group(1) if note_id_match else ""

    # 解析查询参数
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    xsec_token = query_params.get('xsec_token', [''])[0]
    xsec_source = query_params.get('xsec_source', [''])[0]

    return SimpleNamespace(
        note_id=note_id,
        xsec_token=xsec_token,
        xsec_source=xsec_source
    )


def _parse_creator_url(url: str) -> SimpleNamespace:
    """简单解析小红书用户URL，提取user_id等信息"""
    import re
    from urllib.parse import urlparse, parse_qs

    # 如果是纯ID字符串，直接返回
    if not url.startswith('http'):
        return SimpleNamespace(
            user_id=url.strip(),
            xsec_token="",
            xsec_source=""
        )

    # 提取user_id
    user_id_match = re.search(r'/user/profile/([a-f0-9]+)', url)
    user_id = user_id_match.group(1) if user_id_match else ""

    # 解析查询参数
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    xsec_token = query_params.get('xsec_token', [''])[0]
    xsec_source = query_params.get('xsec_source', [''])[0]

    return SimpleNamespace(
        user_id=user_id,
        xsec_token=xsec_token,
        xsec_source=xsec_source
    )


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


class XiaoHongShuCrawler:
    """Entry point for all Xiaohongshu crawl tasks."""

    def __init__(
        self,
        *,
        login_cookie: Optional[str] = None,
        login_phone: Optional[str] = None,
        login_type: Optional[Union[str, LoginType]] = None,
        headless: Optional[bool] = None,
        enable_save_media: Optional[bool] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        # 基本属性设置
        self.platform = Platform.XIAOHONGSHU
        self.context_page: Optional[Page] = None
        self.browser_context: Optional[BrowserContext] = None

        self.extra = dict(extra or {})
        self.platform_code = Platform.XIAOHONGSHU.value

        browser_defaults = global_settings.browser
        store_defaults = global_settings.store

        resolved_headless = headless if headless is not None else browser_defaults.headless
        resolved_enable_save_media = (
            bool(enable_save_media)
            if enable_save_media is not None
            else bool(getattr(store_defaults, "enable_save_media", False))
        )

        self.browser = SimpleNamespace(
            headless=resolved_headless,
            user_agent=self.extra.get("user_agent", browser_defaults.user_agent),
            proxy=self.extra.get("proxy", browser_defaults.proxy),
            viewport_width=int(self.extra.get("viewport_width", browser_defaults.viewport_width)),
            viewport_height=int(self.extra.get("viewport_height", browser_defaults.viewport_height)),
        )

        # 登录选项
        resolved_login_type = _resolve_login_type(login_cookie, login_phone, login_type)
        self.login_opts = SimpleNamespace(
            login_type=resolved_login_type,
            cookie=login_cookie,
            phone=login_phone,
            save_login_state=self.extra.get("save_login_state", False),
        )

        # 基础配置
        self.user_agent = self.browser.user_agent or crawler_util.get_user_agent()
        self.client: Optional[XiaoHongShuClient] = None
        self._closed: bool = False

    async def search_by_keywords(
        self,
        *,
        keywords: str,
        max_notes: int = 20,
        page_size: int = 20,
        crawl_interval: float = 1.0,
        enable_save: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """通过关键词搜索笔记"""
        # 确保浏览器和客户端已准备就绪
        await self._ensure_browser_and_client()

        keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
        if not keyword_list:
            raise ValueError("keywords 不能为空")

        collected: List[Dict[str, Any]] = []
        limit = max(1, max_notes)

        for keyword in keyword_list:
            try:
                logger.info(f"[xhs.search] searching keyword: {keyword}")
                search_results = await self.client.search_notes(
                    keyword=keyword,
                    max_notes=limit - len(collected)
                )

                for result in search_results:
                    if len(collected) >= limit:
                        break

                    # 可选的存储功能
                    if enable_save:
                        try:
                            await xhs_store.update_xhs_note(result)
                        except Exception as store_exc:
                            logger.error(f"[xhs.search] Store note error: {store_exc}")

                    collected.append(result)

                if crawl_interval > 0:
                    await asyncio.sleep(crawl_interval)

            except LoginExpiredError as e:
                logger.error(f"[xhs.search] Login required or permission denied: {e}")
                raise
            except Exception as e:
                logger.error(f"[xhs.search] Error processing keyword={keyword}: {type(e).__name__}: {e}")
                continue

        return {
            "notes": collected[:page_size],
            "total_count": min(len(collected), page_size),
            "page_info": {
                "current_page": 1,
                "page_size": page_size,
                "has_more": False
            },
            "crawl_info": self._build_crawl_info("search"),
        }

    async def get_detail(
        self,
        *,
        note_ids: List[Union[str, Dict[str, Any]]],
        max_concurrency: int = 5,
        enable_get_comments: bool = False,
        max_comments_per_note: int = 0,
        enable_save_media: bool = False,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """获取笔记详情"""
        if not note_ids:
            raise ValueError("note_ids 不能为空")

        semaphore = Semaphore(max_concurrency)
        details: List[Dict[str, Any]] = []
        for item in note_ids:
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
                    info = _parse_note_url(s)
                    note_id, xsec_source, xsec_token = info.note_id, info.xsec_source, info.xsec_token
                else:
                    note_id = s
            if not note_id:
                continue

            note_detail = await self._get_note_detail(note_id, xsec_source, xsec_token, semaphore)
            if not note_detail:
                continue
            await xhs_store.update_xhs_note(note_detail)
            if enable_save_media:
                await xhs_store.update_xhs_note_media(note_detail)
            details.append(note_detail)

        if enable_get_comments and max_comments_per_note > 0:
            await self._batch_fetch_comments(details, max_comments_per_note)

        return {
            "notes": details,
            "total_count": len(details),
            "crawl_info": self._build_crawl_info(),
        }

    async def get_creator(
        self,
        *,
        creator_ids: List[str],
        max_notes: Optional[int] = None,
        enable_get_comments: bool = False,
        max_comments_per_note: int = 0,
        enable_save_media: bool = False,
        crawl_interval: float = 1.0,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """获取创作者信息"""
        if not creator_ids:
            raise ValueError("creator_ids 不能为空")

        # 使用全局配置作为默认值
        crawl_defaults = global_settings.crawl
        resolved_max_notes = max_notes if max_notes is not None else crawl_defaults.max_notes_count

        collected: List[Dict[str, Any]] = []
        for raw_id in creator_ids:
            info = _parse_creator_url(raw_id)
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
                max_notes=resolved_max_notes,
            )
            # 与 MediaCrawler 对齐：拉取每条作品详情，必要时再抓评论
            details = await self._gather_details_from_items(notes, max_concurrency=5)
            for detail in details:
                if not detail:
                    continue
                await xhs_store.update_xhs_note(detail)
                if enable_save_media:
                    await xhs_store.update_xhs_note_media(detail)
                collected.append(detail)

            if enable_get_comments and max_comments_per_note > 0 and collected:
                await self._batch_fetch_comments([d for d in details if d], max_comments_per_note, crawl_interval)
            await asyncio.sleep(crawl_interval)

        return {
            "notes": collected,
            "total_count": len(collected),
            "crawl_info": self._build_crawl_info(),
        }

    async def fetch_comments(
        self,
        *,
        note_items: List[Dict[str, Any]],
        max_concurrency: int = 5,
        crawl_interval: float = 1.0,
        max_comments_per_note: int = 50,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """获取评论"""
        if not note_items:
            raise ValueError("note_items 不能为空")

        semaphore = Semaphore(max_concurrency)
        comments: Dict[str, List[Dict[str, Any]]] = {}

        for item in note_items:
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
                    crawl_interval=crawl_interval,
                    callback=_collector,
                    max_count=max_comments_per_note,
                )
            except Exception as exc:
                logger.error(f"[xhs.comments] 获取评论失败 note_id={note_id}: {exc}")
                continue

        return {
            "comments": comments,
            "total_count": sum(len(v) for v in comments.values()),
            "crawl_info": self._build_crawl_info(),
        }

    async def search_with_time_range(
        self,
        *,
        keywords: str,
        start_day: str,
        end_day: str,
        max_notes: int = 20,
        page_size: int = 20,
        crawl_interval: float = 1.0,
        enable_save: bool = False,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """按时间范围搜索笔记"""
        # 设置时间范围参数
        self.extra.update({
            "start_day": start_day,
            "end_day": end_day,
        })

        # 调用普通搜索方法
        return await self.search_by_keywords(
            keywords=keywords,
            max_notes=max_notes,
            page_size=page_size,
            crawl_interval=crawl_interval,
            enable_save=enable_save,
        )

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
                    "width": self.browser.viewport_width,
                    "height": self.browser.viewport_height,
                },
            )
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
            browser_context = await browser.new_context(
                user_agent=user_agent,
                viewport={
                    "width": self.browser.viewport_width,
                    "height": self.browser.viewport_height,
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
            proxy=self.browser.proxy,
            timeout=60,
        )
        await client.update_cookies(browser_context)
        return client

    async def _gather_details_from_items(self, items: Iterable[Dict[str, Any]], max_concurrency: int = 5) -> List[Optional[Dict]]:
        semaphore = Semaphore(max_concurrency)
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

    async def _batch_fetch_comments(self, details: List[Dict[str, Any]], max_comments: int, crawl_interval: float = 1.0) -> None:
        for detail in details:
            note_id = detail.get("note_id")
            if not note_id:
                continue
            await self.client.get_note_all_comments(
                note_id=note_id,
                xsec_token=detail.get("xsec_token", ""),
                crawl_interval=crawl_interval,
                callback=xhs_store.batch_update_xhs_note_comments,
                max_count=max_comments,
            )

    async def _creator_notes_callback(self, notes: List[Dict[str, Any]]) -> None:
        details = await self._gather_details_from_items(notes)
        for detail in details:
            if detail:
                await xhs_store.update_xhs_note(detail)

    async def _ensure_browser_and_client(self) -> None:
        """确保浏览器上下文和客户端已准备就绪"""
        if not self.browser_context or not self.client:
            # 使用浏览器管理器获取浏览器上下文
            user_data_dir = Path("browser_data") / Platform.XIAOHONGSHU.value
            viewport = {
                "width": self.browser.viewport_width,
                "height": self.browser.viewport_height,
            }

            self.browser_context, self.context_page, playwright = await browser_manager.acquire_context(
                platform=Platform.XIAOHONGSHU.value,
                user_data_dir=user_data_dir,
                headless=self.browser.headless,
                viewport=viewport,
                user_agent=self.user_agent,
            )

            await self.context_page.goto("https://www.xiaohongshu.com")
            await self._ensure_login_state()
            self.client = await self._build_client(self.browser_context)

    def _build_crawl_info(self, crawler_type: str = "unknown") -> Dict[str, Any]:
        return {
            "platform": Platform.XIAOHONGSHU.value,
            "crawler_type": crawler_type,
            "timestamp": time_util.get_current_timestamp(),
        }