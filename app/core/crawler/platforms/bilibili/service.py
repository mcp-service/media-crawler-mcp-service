# -*- coding: utf-8 -*-
"""Bilibili crawler orchestration helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config.settings import (
    CrawlerType,
    LoginType,
    Platform,
    global_settings,
)
from app.core.crawler import (
    BrowserOptions,
    CrawlOptions,
    CrawlerContext,
    LoginOptions,
    StoreOptions,
)
from app.core.crawler.platforms.bilibili.crawler import BilibiliCrawler
from app.core.login import login_service
from app.providers.logger import get_logger


logger = get_logger()


def _resolve_login_type(provided_cookie: Optional[str]) -> LoginType:
    if provided_cookie:
        return LoginType.COOKIE
    default_login = global_settings.platform.default_login_type
    return default_login if isinstance(default_login, LoginType) else LoginType(str(default_login))


def _build_common_context(
    *,
    crawler_type: CrawlerType,
    keywords: Optional[str] = None,
    note_ids: Optional[List[str]] = None,
    creator_ids: Optional[List[str]] = None,
    login_cookie: Optional[str] = None,
    headless: Optional[bool] = None,
    enable_comments: bool = True,
    max_notes: int = 15,
    max_comments_per_note: int = 10,
    enable_save_media: Optional[bool] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> CrawlerContext:
    browser_defaults = global_settings.browser
    crawl_defaults = global_settings.crawl
    store_defaults = global_settings.store

    options = dict(extra) if extra else {}
    login_phone = options.pop("login_phone", None)
    save_login_state = options.pop("save_login_state", True)
    user_agent_override = options.pop("user_agent", browser_defaults.user_agent)
    proxy_override = options.pop("proxy", browser_defaults.proxy)
    viewport_width = options.pop("viewport_width", browser_defaults.viewport_width)
    viewport_height = options.pop("viewport_height", browser_defaults.viewport_height)
    max_concurrency = options.pop("max_concurrency", crawl_defaults.max_concurrency)
    crawl_interval = options.pop("crawl_interval", crawl_defaults.crawl_interval)
    enable_get_sub_comments = options.pop(
        "enable_get_sub_comments", crawl_defaults.enable_get_sub_comments
    )
    extra_payload = options

    browser = BrowserOptions(
        headless=headless if headless is not None else browser_defaults.headless,
        user_agent=user_agent_override,
        proxy=proxy_override,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
    )

    crawl = CrawlOptions(
        keywords=keywords,
        note_ids=note_ids,
        creator_ids=creator_ids,
        max_notes_count=max_notes,
        max_comments_per_note=max_comments_per_note,
        enable_get_comments=enable_comments,
        enable_get_sub_comments=enable_get_sub_comments,
        enable_save_media=enable_save_media
        if enable_save_media is not None
        else getattr(store_defaults, "enable_save_media", False),
        max_concurrency=max_concurrency,
        crawl_interval=crawl_interval,
        search_mode=crawl_defaults.search_mode,
        start_page=crawl_defaults.start_page,
        start_day=crawl_defaults.start_day,
        end_day=crawl_defaults.end_day,
        max_notes_per_day=crawl_defaults.max_notes_per_day,
    )

    store = StoreOptions(
        save_format=str(store_defaults.save_format),
        enable_save_media=crawl.enable_save_media,
    )

    login_options = LoginOptions(
        login_type=_resolve_login_type(login_cookie),
        cookie=login_cookie,
        phone=login_phone,
        save_login_state=save_login_state,
    )

    context = CrawlerContext(
        platform=Platform.BILIBILI,
        crawler_type=crawler_type,
        login=login_options,
        browser=browser,
        crawl=crawl,
        store=store,
        extra=extra_payload,
    )
    return context


async def search(
    *,
    keywords: str,
    max_notes: int = 15,
    enable_comments: bool = True,
    max_comments_per_note: int = 10,
    **kwargs: Any,
) -> Dict[str, Any]:
    logger.info(f"[bilibili.core.search] keywords={keywords}")

    enable_save_media = kwargs.pop("enable_save_media", None)
    extra = dict(kwargs) if kwargs else {}

    login_cookie = await login_service.get_cookie(Platform.BILIBILI.value)

    context = _build_common_context(
        crawler_type=CrawlerType.SEARCH,
        keywords=keywords,
        enable_comments=enable_comments,
        max_notes=max_notes,
        max_comments_per_note=max_comments_per_note,
        enable_save_media=enable_save_media,
        extra=extra,
        login_cookie=login_cookie,
    )

    crawler = BilibiliCrawler(context)
    try:
        return await crawler.start()
    finally:
        await crawler.close()


async def get_detail(
    *,
    video_ids: List[str],
    enable_comments: bool = True,
    max_comments_per_note: int = 10,
    headless: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    logger.info(f"[bilibili.core.get_detail] video_count={len(video_ids)}")

    enable_save_media = kwargs.pop("enable_save_media", None)
    extra = dict(kwargs) if kwargs else {}

    login_cookie = await login_service.get_cookie(Platform.BILIBILI.value)

    context = _build_common_context(
        crawler_type=CrawlerType.DETAIL,
        note_ids=video_ids,
        headless=headless,
        enable_comments=enable_comments,
        max_notes=len(video_ids),
        max_comments_per_note=max_comments_per_note,
        enable_save_media=enable_save_media,
        extra=extra,
        login_cookie=login_cookie,
    )

    crawler = BilibiliCrawler(context)
    try:
        return await crawler.start()
    finally:
        await crawler.close()


async def get_creator(
    *,
    creator_ids: List[str],
    enable_comments: bool = True,
    max_comments_per_note: int = 10,
    creator_mode: bool = True,
    headless: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    logger.info(
        f"[bilibili.core.get_creator] creator_count={len(creator_ids)} "
        f"creator_mode={creator_mode}"
    )

    enable_save_media = kwargs.pop("enable_save_media", None)
    extra = dict(kwargs) if kwargs else {}
    extra["creator_mode"] = creator_mode

    login_cookie = await login_service.get_cookie(Platform.BILIBILI.value)

    context = _build_common_context(
        crawler_type=CrawlerType.CREATOR,
        creator_ids=creator_ids,
        headless=headless,
        enable_comments=enable_comments,
        max_notes=len(creator_ids),
        max_comments_per_note=max_comments_per_note,
        enable_save_media=enable_save_media,
        extra=extra,
        login_cookie=login_cookie,
    )

    crawler = BilibiliCrawler(context)
    try:
        return await crawler.start()
    finally:
        await crawler.close()


async def search_with_time_range(
    *,
    keywords: str,
    start_day: str,
    end_day: str,
    max_notes: int = 15,
    max_notes_per_day: int = 50,
    daily_limit: bool = False,
    enable_comments: bool = True,
    max_comments_per_note: int = 10,
    **kwargs: Any,
) -> Dict[str, Any]:
    logger.info(
        "[bilibili.core.search_with_time_range] "
        f"keywords={keywords} start={start_day} end={end_day} limit={daily_limit}"
    )

    enable_save_media = kwargs.pop("enable_save_media", None)
    extra = dict(kwargs) if kwargs else {}
    extra["search_mode"] = (
        "daily_limit_in_time_range" if daily_limit else "all_in_time_range"
    )

    login_cookie = await login_service.get_cookie(Platform.BILIBILI.value)

    context = _build_common_context(
        crawler_type=CrawlerType.SEARCH,
        keywords=keywords,
        enable_comments=enable_comments,
        max_notes=max_notes,
        max_comments_per_note=max_comments_per_note,
        enable_save_media=enable_save_media,
        extra=extra,
        login_cookie=login_cookie,
    )

    context.crawl.start_day = start_day
    context.crawl.end_day = end_day
    context.crawl.max_notes_per_day = max_notes_per_day
    context.crawl.search_mode = extra["search_mode"]

    crawler = BilibiliCrawler(context)
    try:
        return await crawler.start()
    finally:
        await crawler.close()
