# -*- coding: utf-8 -*-
"""Service layer for Xiaohongshu crawler."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config.settings import CrawlerType, LoginType, Platform, global_settings
from app.core.crawler import (
    BrowserOptions,
    CrawlOptions,
    CrawlerContext,
    LoginOptions,
    StoreOptions,
)
from app.core.crawler.platforms.xhs.crawler import XiaoHongShuCrawler
from app.core.login import login_service
from app.core.login.exceptions import LoginExpiredError
from app.providers.logger import get_logger

logger = get_logger()


def _resolve_login_type(cookie: Optional[str], phone: Optional[str]) -> LoginType:
    if cookie:
        return LoginType.COOKIE
    if phone:
        return LoginType.PHONE
    return LoginType.QRCODE


def _build_context(
    *,
    crawler_type: CrawlerType,
    keywords: Optional[str] = None,
    note_urls: Optional[List[str]] = None,
    creator_ids: Optional[List[str]] = None,
    enable_comments: bool = False,
    max_notes: int = 20,
    max_comments: int = 0,
    headless: Optional[bool] = None,
    enable_save_media: Optional[bool] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> CrawlerContext:
    browser_cfg = global_settings.browser
    crawl_cfg = global_settings.crawl
    store_cfg = global_settings.store

    extra_options = dict(extra or {})
    login_phone = extra_options.pop("login_phone", None)
    login_cookie = extra_options.pop("login_cookie", None)
    save_login_state = extra_options.pop("save_login_state", True)

    browser = BrowserOptions(
        headless=headless if headless is not None else browser_cfg.headless,
        user_agent=browser_cfg.user_agent,
        proxy=browser_cfg.proxy,
        viewport_width=browser_cfg.viewport_width,
        viewport_height=browser_cfg.viewport_height,
    )

    crawl = CrawlOptions(
        keywords=keywords,
        note_ids=note_urls,
        creator_ids=creator_ids,
        max_notes_count=max_notes,
        max_comments_per_note=max_comments,
        enable_get_comments=enable_comments,
        enable_get_sub_comments=False,
        enable_save_media=enable_save_media
        if enable_save_media is not None
        else store_cfg.enable_save_media,
        max_concurrency=extra_options.pop("max_concurrency", crawl_cfg.max_concurrency),
        crawl_interval=extra_options.pop("crawl_interval", crawl_cfg.crawl_interval),
        search_mode=crawl_cfg.search_mode,
        start_page=extra_options.pop("start_page", crawl_cfg.start_page),
        start_day=extra_options.pop("start_day", crawl_cfg.start_day),
        end_day=extra_options.pop("end_day", crawl_cfg.end_day),
        max_notes_per_day=extra_options.pop("max_notes_per_day", crawl_cfg.max_notes_per_day),
    )

    store = StoreOptions(
        save_format=str(store_cfg.save_format),
        enable_save_media=crawl.enable_save_media,
    )

    login = LoginOptions(
        login_type=_resolve_login_type(login_cookie, login_phone),
        cookie=login_cookie,
        phone=login_phone,
        save_login_state=save_login_state,
    )

    return CrawlerContext(
        platform=Platform.XIAOHONGSHU,
        crawler_type=crawler_type,
        login=login,
        browser=browser,
        crawl=crawl,
        store=store,
        extra=extra_options,
    )


async def search(
    *,
    keywords: str,
    headless: Optional[bool] = None,
    enable_save_media: Optional[bool] = None,
    **kwargs,
) -> Dict[str, Any]:
    login_cookie = await login_service.get_cookie(Platform.XIAOHONGSHU.value)
    if not login_cookie:
        # MCP 工具不进行自动登录，直接返回登录过期
        raise LoginExpiredError("登录过期，Cookie失效")

    # 从kwargs中获取分页参数，使用page_size作为max_notes
    page_size = kwargs.get("page_size", 20)
    
    context = _build_context(
        crawler_type=CrawlerType.SEARCH,
        keywords=keywords,
        enable_comments=False,  # 搜索不获取评论
        max_notes=page_size,
        max_comments=0,  # 搜索不获取评论
        headless=headless,
        enable_save_media=enable_save_media,
        extra={**kwargs, "login_cookie": login_cookie, "no_auto_login": True},
    )
    crawler = XiaoHongShuCrawler(context)
    try:
        return await crawler.start()
    finally:
        await crawler.close()


async def search_with_time_range(
    *,
    keywords: str,
    start_day: str,
    end_day: str,
    limit: int = 20,
    headless: Optional[bool] = None,
    enable_save_media: Optional[bool] = None,
    **kwargs,
) -> Dict[str, Any]:
    extra = dict(kwargs)
    extra["start_day"] = start_day
    extra["end_day"] = end_day
    return await search(
        keywords=keywords,
        limit=limit,
        headless=headless,
        enable_save_media=enable_save_media,
        **extra,
    )


async def get_detail(
    *,
    node_id: str,
    xsec_token: str,
    xsec_source: Optional[str] = "",
    enable_comments: bool = True,
    max_comments_per_note: int = 50,
    headless: Optional[bool] = None,
    enable_save_media: Optional[bool] = None,
    **kwargs,
) -> Dict[str, Any]:
    login_cookie = await login_service.get_cookie(Platform.XIAOHONGSHU.value)
    if not login_cookie:
        raise LoginExpiredError("登录过期，Cookie失效")
    context = _build_context(
        crawler_type=CrawlerType.DETAIL,
        note_urls=[{"note_id": node_id, "xsec_token": xsec_token or "", "xsec_source": xsec_source or ""}],
        enable_comments=enable_comments,
        max_notes=1,
        max_comments=max_comments_per_note,
        headless=headless,
        enable_save_media=enable_save_media,
        extra={**kwargs, "login_cookie": login_cookie, "no_auto_login": True},
    )
    crawler = XiaoHongShuCrawler(context)
    try:
        return await crawler.start()
    finally:
        await crawler.close()


async def get_creator(
    *,
    creator_ids: List[str],
    enable_comments: bool = False,
    max_comments_per_note: int = 0,
    headless: Optional[bool] = None,
    enable_save_media: Optional[bool] = None,
    **kwargs,
) -> Dict[str, Any]:
    login_cookie = await login_service.get_cookie(Platform.XIAOHONGSHU.value)
    if not login_cookie:
        raise LoginExpiredError("登录过期，Cookie失效")
    context = _build_context(
        crawler_type=CrawlerType.CREATOR,
        creator_ids=creator_ids,
        enable_comments=enable_comments,
        max_notes=len(creator_ids),
        max_comments=max_comments_per_note,
        headless=headless,
        enable_save_media=enable_save_media,
        extra={**kwargs, "login_cookie": login_cookie, "no_auto_login": True},
    )
    crawler = XiaoHongShuCrawler(context)
    try:
        return await crawler.start()
    finally:
        await crawler.close()


async def fetch_comments(
    *,
    note_ids: List[str],
    max_comments: int = 50,
    headless: Optional[bool] = None,
    **kwargs,
) -> Dict[str, Any]:
    login_cookie = await login_service.get_cookie(Platform.XIAOHONGSHU.value)
    if not login_cookie:
        raise LoginExpiredError("登录过期，Cookie失效")
    context = _build_context(
        crawler_type=CrawlerType.COMMENTS,
        note_urls=note_ids,
        enable_comments=True,
        max_notes=len(note_ids),
        max_comments=max_comments,
        headless=headless,
        enable_save_media=False,
        extra={**kwargs, "login_cookie": login_cookie, "no_auto_login": True},
    )
    crawler = XiaoHongShuCrawler(context)
    try:
        return await crawler.start()
    finally:
        await crawler.close()
