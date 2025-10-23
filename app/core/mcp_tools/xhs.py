# -*- coding: utf-8 -*-
"""Xiaohongshu MCP tool implementations."""

from __future__ import annotations

import json
from typing import List, Optional

from app.core.crawler.platforms.xhs import service as xhs_service
from .schemas.xhs import XhsCommentsResult, XhsNoteDetail, XhsNoteSearchResult


async def xhs_search(
    keywords: str,
    page_num: int = 1,
    page_size: int = 20,
    headless: Optional[bool] = None,
    save_media: bool = False,
    login_phone: Optional[str] = None,
    login_cookie: Optional[str] = None,
    save_login_state: bool = True,
    options: Optional[dict] = None,
) -> str:
    """
    搜索小红书笔记，返回结构化的搜索结果。

    Args:
        keywords: 搜索关键词，多个关键词用逗号分隔。
        page_num: 页码，从1开始。
        page_size: 每页数量。
        headless: 是否使用无头浏览器。
        save_media: 是否保存媒体资源（图片、视频）。
        login_phone: 登录手机号。
        login_cookie: 登录Cookie字符串，格式如 "key1=value1; key2=value2"。
        save_login_state: 是否保存登录状态。
        options: 额外选项字典。
    """
    extra = options.copy() if options else {}
    if login_phone is not None:
        extra["login_phone"] = login_phone
    if login_cookie is not None:
        extra["login_cookie"] = login_cookie
    extra["save_login_state"] = save_login_state
    extra["page_num"] = page_num
    extra["page_size"] = page_size
    
    result = await xhs_service.search(
        keywords=keywords,
        headless=headless,
        enable_save_media=save_media,
        **extra,
    )
    payload = XhsNoteSearchResult(
        notes=[XhsNoteDetail(**note) for note in result.get("notes", [])],
        total_count=result.get("total_count", 0),
        crawl_info=result.get("crawl_info", {}),
    )
    return payload.model_dump_json(ensure_ascii=False, indent=2)


async def xhs_detail(
    note_urls: List[str],
    enable_comments: bool = True,
    max_comments_per_note: int = 50,
    headless: Optional[bool] = None,
    save_media: bool = False,
    login_phone: Optional[str] = None,
    login_cookie: Optional[str] = None,
    save_login_state: bool = True,
) -> str:
    """
    获取小红书笔记详情，返回结构化的详情信息。

    Args:
        note_urls: 笔记URL列表，例如: ["https://www.xiaohongshu.com/explore/xxxxx"]
        enable_comments: 是否抓取评论，默认 True
        max_comments_per_note: 单条笔记最大评论数，默认 50
        headless: 是否使用无头浏览器，None 使用全局配置
        save_media: 是否保存媒体资源（图片、视频），默认 False
        login_phone: 登录手机号，可选
        login_cookie: 登录Cookie字符串，可选，格式如: "key1=value1; key2=value2"
        save_login_state: 是否保存登录状态，默认 True

    Returns:
        JSON字符串，包含笔记详情列表、总数量和抓取信息

    Example:
        note_urls=["https://www.xiaohongshu.com/explore/12345"], enable_comments=True, max_comments_per_note=20
    """
    extra = {}
    if login_phone is not None:
        extra["login_phone"] = login_phone
    if login_cookie is not None:
        extra["login_cookie"] = login_cookie
    extra["save_login_state"] = save_login_state
    
    result = await xhs_service.get_detail(
        note_urls=note_urls,
        enable_comments=enable_comments,
        max_comments_per_note=max_comments_per_note,
        headless=headless,
        enable_save_media=save_media,
        **extra,
    )
    payload = XhsNoteSearchResult(
        notes=[XhsNoteDetail(**note) for note in result.get("notes", [])],
        total_count=result.get("total_count", 0),
        crawl_info=result.get("crawl_info", {}),
    )
    return payload.model_dump_json(ensure_ascii=False, indent=2)


async def xhs_creator(
    creator_ids: List[str],
    enable_comments: bool = False,
    max_comments_per_note: int = 0,
    headless: Optional[bool] = None,
    save_media: bool = False,
    login_phone: Optional[str] = None,
    login_cookie: Optional[str] = None,
    save_login_state: bool = True,
) -> str:
    """
    获取小红书创作者的作品，返回创作者信息和作品列表。

    Args:
        creator_ids: 创作者ID列表，例如: ["user123", "user456"]
        enable_comments: 是否抓取作品评论，默认 False
        max_comments_per_note: 单条作品最大评论数，仅在 enable_comments=True 时有效，默认 0
        headless: 是否使用无头浏览器，None 使用全局配置
        save_media: 是否保存媒体资源（图片、视频），默认 False
        login_phone: 登录手机号，可选
        login_cookie: 登录Cookie字符串，可选，格式如: "key1=value1; key2=value2"
        save_login_state: 是否保存登录状态，默认 True

    Returns:
        JSON字符串，包含创作者信息和作品列表

    Example:
        creator_ids=["user12345"], enable_comments=False, save_media=True
    """
    extra = {}
    if login_phone is not None:
        extra["login_phone"] = login_phone
    if login_cookie is not None:
        extra["login_cookie"] = login_cookie
    extra["save_login_state"] = save_login_state
    
    result = await xhs_service.get_creator(
        creator_ids=creator_ids,
        enable_comments=enable_comments,
        max_comments_per_note=max_comments_per_note,
        headless=headless,
        enable_save_media=save_media,
        **extra,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


async def xhs_comments(
    note_urls: List[str],
    max_comments: int = 50,
    headless: Optional[bool] = None,
    login_phone: Optional[str] = None,
    login_cookie: Optional[str] = None,
    save_login_state: bool = True,
) -> str:
    """
    获取小红书笔记评论，返回结构化的评论信息。

    Args:
        note_urls: 笔记URL列表，例如: ["https://www.xiaohongshu.com/explore/xxxxx"]
        max_comments: 最大评论数量，默认 50
        headless: 是否使用无头浏览器，None 使用全局配置
        login_phone: 登录手机号，可选
        login_cookie: 登录Cookie字符串，可选，格式如: "key1=value1; key2=value2"
        save_login_state: 是否保存登录状态，默认 True

    Returns:
        JSON字符串，包含评论列表、总数量和抓取信息

    Example:
        note_urls=["https://www.xiaohongshu.com/explore/12345"], max_comments=100
    """
    extra = {}
    if login_phone is not None:
        extra["login_phone"] = login_phone
    if login_cookie is not None:
        extra["login_cookie"] = login_cookie
    extra["save_login_state"] = save_login_state
    
    result = await xhs_service.fetch_comments(
        note_urls=note_urls,
        max_comments=max_comments,
        headless=headless,
        **extra,
    )
    payload = XhsCommentsResult(
        comments=result.get("comments", {}),
        total_count=result.get("total_count", 0),
        crawl_info=result.get("crawl_info", {}),
    )
    return payload.model_dump_json(ensure_ascii=False, indent=2)


__all__ = ["xhs_search", "xhs_detail", "xhs_creator", "xhs_comments"]
