# -*- coding: utf-8 -*-
"""Bilibili MCP tool implementations."""

from __future__ import annotations

import json
from typing import List, Optional

from app.core.crawler.platforms.bilibili import service as bilibili_core


async def bili_search(
    keywords: str,
    page_size: int = 1,
    page_num: int = 1,
    limit: Optional[int] = None,
    headless: bool = False,
    save_media: bool = False,
) -> str:
    """
    搜索 Bilibili 视频。

    Args:
        keywords: 搜索关键词，多个关键词用逗号分隔。
        page_size: 单页作品数量。
        page_num: 抓取页数。
        limit: 返回作品数量上限，默认为 page_size * page_num。
        headless: 是否无头模式。
        save_media: 是否保存媒体文件。
    """
    total_limit = limit if limit is not None else page_size * page_num
    result = await bilibili_core.search(
        keywords=keywords,
        page_size=page_size,
        page_num=page_num,
        limit=total_limit,
        headless=headless,
        enable_save_media=save_media,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


async def bili_search_time_range(
    keywords: str,
    start_day: str,
    end_day: str,
    page_size: int = 1,
    page_num: int = 1,
    limit: Optional[int] = None,
    max_notes_per_day: int = 50,
    daily_limit: bool = False,
    headless: bool = False,
    save_media: bool = False,
) -> str:
    """
    按时间范围搜索 Bilibili 视频。
    """
    total_limit = limit if limit is not None else page_size * page_num
    result = await bilibili_core.search_with_time_range(
        keywords=keywords,
        start_day=start_day,
        end_day=end_day,
        page_size=page_size,
        page_num=page_num,
        limit=total_limit,
        max_notes_per_day=max_notes_per_day,
        daily_limit=daily_limit,
        headless=headless,
        enable_save_media=save_media,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


async def bili_detail(
    video_ids: List[str],
    headless: bool = False,
    save_media: bool = False,
) -> str:
    """
    获取指定视频详情。
    """
    result = await bilibili_core.get_detail(
        video_ids=video_ids,
        headless=headless,
        enable_save_media=save_media,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


async def bili_creator(
    creator_ids: List[str],
    creator_mode: bool = True,
    headless: bool = False,
    save_media: bool = False,
) -> str:
    """
    获取指定创作者的视频。
    """
    result = await bilibili_core.get_creator(
        creator_ids=creator_ids,
        creator_mode=creator_mode,
        headless=headless,
        enable_save_media=save_media,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


async def bili_comments(
    video_ids: List[str],
    max_comments: int = 20,
    fetch_sub_comments: bool = False,
    headless: bool = False,
) -> str:
    """
    根据视频ID抓取评论。
    """
    result = await bilibili_core.fetch_comments(
        video_ids=video_ids,
        max_comments=max_comments,
        fetch_sub_comments=fetch_sub_comments,
        headless=headless,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


__all__ = [
    "bili_search",
    "bili_search_time_range",
    "bili_detail",
    "bili_creator",
    "bili_comments",
]
