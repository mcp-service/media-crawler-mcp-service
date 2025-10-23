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
from app.core.login.exceptions import LoginExpiredError
from app.providers.logger import get_logger


logger = get_logger()


def _resolve_login_type(provided_cookie: Optional[str], provided_phone: Optional[str]) -> LoginType:
    """根据传入参数自动判定登录方式：
    - 传入 Cookie -> COOKIE
    - 否则传入手机号 -> PHONE
    - 否则默认使用 QRCODE（内部缺省，不再依赖可配置项）
    """
    if provided_cookie:
        return LoginType.COOKIE
    if provided_phone:
        return LoginType.PHONE
    return LoginType.QRCODE


def _build_common_context(
    *,
    crawler_type: CrawlerType,
    keywords: Optional[str] = None,
    note_ids: Optional[List[str]] = None,
    creator_ids: Optional[List[str]] = None,
    login_cookie: Optional[str] = None,
    headless: Optional[bool] = None,
    enable_comments: bool = False,
    max_notes: int = 0,
    max_comments_per_note: int = 0,
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

    if "fetch_sub_comments" in options:
        enable_get_sub_comments = bool(options.pop("fetch_sub_comments"))
    else:
        enable_get_sub_comments = options.pop(
            "enable_get_sub_comments", crawl_defaults.enable_get_sub_comments
        )

    max_notes_value = max(max_notes, 0) or crawl_defaults.max_notes_count

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
        max_notes_count=max_notes_value,
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
        login_type=_resolve_login_type(login_cookie, login_phone),
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
        extra=options,
    )
    return context


async def search(
    *,
    keywords: str,
    page_size: int = 1,
    page_num: int = 1,
    limit: Optional[int] = None,
    headless: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    logger.info(f"[bilibili.core.search] keywords={keywords}")

    enable_save_media = kwargs.pop("enable_save_media", None)
    extra = dict(kwargs) if kwargs else {}
    extra["page_size"] = page_size
    extra["page_num"] = page_num

    total_limit = limit if limit is not None else page_size

    login_cookie = await login_service.get_cookie(Platform.BILIBILI.value)
    if not login_cookie:
        raise LoginExpiredError("登录过期，Cookie失效")

    context = _build_common_context(
        crawler_type=CrawlerType.SEARCH,
        keywords=keywords,
        headless=headless,
        enable_comments=False,
        max_notes=total_limit,
        max_comments_per_note=0,
        enable_save_media=enable_save_media,
        extra={**extra, "no_auto_login": True},
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
    page_size: int = 1,
    page_num: int = 1,
    limit: Optional[int] = None,
    max_notes_per_day: int = 50,
    daily_limit: bool = False,
    headless: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    logger.info(
        "[bilibili.core.search_with_time_range] "
        f"keywords={keywords} start={start_day} end={end_day} limit={daily_limit}"
    )

    enable_save_media = kwargs.pop("enable_save_media", None)
    extra = dict(kwargs) if kwargs else {}
    extra["page_size"] = page_size
    extra["page_num"] = page_num
    extra["search_mode"] = "daily_limit_in_time_range" if daily_limit else "all_in_time_range"

    total_limit = limit if limit is not None else page_size

    login_cookie = await login_service.get_cookie(Platform.BILIBILI.value)
    if not login_cookie:
        raise LoginExpiredError("登录过期，Cookie失效")

    context = _build_common_context(
        crawler_type=CrawlerType.SEARCH,
        keywords=keywords,
        headless=headless,
        enable_comments=False,
        max_notes=total_limit,
        max_comments_per_note=0,
        enable_save_media=enable_save_media,
        extra={**extra, "no_auto_login": True},
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


async def get_detail(
    *,
    video_ids: List[str],
    headless: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    logger.info(f"[bilibili.core.get_detail] video_count={len(video_ids)}")

    enable_save_media = kwargs.pop("enable_save_media", None)
    extra = dict(kwargs) if kwargs else {}

    login_cookie = await login_service.get_cookie(Platform.BILIBILI.value)
    if not login_cookie:
        raise LoginExpiredError("登录过期，Cookie失效")

    context = _build_common_context(
        crawler_type=CrawlerType.DETAIL,
        note_ids=video_ids,
        headless=headless,
        enable_comments=False,
        max_notes=len(video_ids),
        max_comments_per_note=0,
        enable_save_media=enable_save_media,
        extra={**extra, "no_auto_login": True},
        login_cookie=login_cookie,
    )

    crawler = BilibiliCrawler(context)
    try:
        return await crawler.start()
    finally:
        await crawler.close()


async def get_creator(
    *,
    creator_id: str,
    page_num: int = 1,
    page_size: int = 30,
    headless: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    logger.info(
        f"[bilibili.core.get_creator] creator_id={creator_id} "
        f"page={page_num} size={page_size}"
    )

    enable_save_media = kwargs.pop("enable_save_media", None)
    extra = dict(kwargs) if kwargs else {}
    extra["page_num"] = page_num
    extra["page_size"] = page_size

    login_cookie = await login_service.get_cookie(Platform.BILIBILI.value)
    if not login_cookie:
        raise LoginExpiredError("登录过期，Cookie失效")

    context = _build_common_context(
        crawler_type=CrawlerType.CREATOR,
        creator_ids=[creator_id],  # 转换为单元素列表以保持兼容
        headless=headless,
        enable_comments=False,
        max_notes=1,
        max_comments_per_note=0,
        enable_save_media=enable_save_media,
        extra={**extra, "no_auto_login": True},
        login_cookie=login_cookie,
    )

    crawler = BilibiliCrawler(context)
    try:
        return await crawler.start()
    finally:
        await crawler.close()


async def fetch_comments(
    *,
    video_ids: List[str],
    max_comments: int = 20,
    fetch_sub_comments: bool = False,
    headless: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    logger.info(
        f"[bilibili.core.fetch_comments] video_count={len(video_ids)} "
        f"max_comments={max_comments} fetch_sub={fetch_sub_comments}"
    )

    extra = dict(kwargs) if kwargs else {}
    extra["fetch_sub_comments"] = fetch_sub_comments

    login_cookie = await login_service.get_cookie(Platform.BILIBILI.value)
    if not login_cookie:
        raise LoginExpiredError("登录过期，Cookie失效")

    context = _build_common_context(
        crawler_type=CrawlerType.COMMENTS,
        note_ids=video_ids,
        headless=headless,
        enable_comments=True,
        max_notes=len(video_ids),
        max_comments_per_note=max_comments,
        enable_save_media=None,
        extra={**extra, "no_auto_login": True},
        login_cookie=login_cookie,
    )

    crawler = BilibiliCrawler(context)
    try:
        return await crawler.start()
    finally:
        await crawler.close()
