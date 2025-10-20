# -*- coding: utf-8 -*-
"""Bilibili 平台相关的 MCP 工具实现。"""

from __future__ import annotations

import json
from typing import List

from app.core import bilibili as bilibili_core


async def bili_search(
    keywords: str,
    max_notes: int = 15,
    enable_comments: bool = True,
    max_comments_per_note: int = 10,
    headless: bool = False,
    save_media: bool = False,
) -> str:
    """
    搜索 Bilibili 视频。

    参数:
        keywords: 搜索关键词（多个用逗号分隔）。
        max_notes: 最大爬取视频数量。
        enable_comments: 是否爬取评论。
        max_comments_per_note: 每个视频最大评论数。
        headless: 是否无头模式。
        save_media: 是否保存媒体文件。
    """
    result = await bilibili_core.search(
        keywords=keywords,
        max_notes=max_notes,
        enable_comments=enable_comments,
        max_comments_per_note=max_comments_per_note,
        headless=headless,
        enable_save_media=save_media,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


async def bili_detail(
    video_ids: List[str],
    enable_comments: bool = True,
    max_comments_per_note: int = 10,
    headless: bool = False,
    save_media: bool = False,
) -> str:
    """
    获取 Bilibili 视频详情。
    """
    result = await bilibili_core.get_detail(
        video_ids=video_ids,
        enable_comments=enable_comments,
        max_comments_per_note=max_comments_per_note,
        headless=headless,
        enable_save_media=save_media,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


async def bili_creator(
    creator_ids: List[str],
    enable_comments: bool = True,
    max_comments_per_note: int = 10,
    creator_mode: bool = True,
    headless: bool = False,
    save_media: bool = False,
) -> str:
    """
    获取指定 Bilibili UP 主的视频。
    """
    result = await bilibili_core.get_creator(
        creator_ids=creator_ids,
        enable_comments=enable_comments,
        max_comments_per_note=max_comments_per_note,
        creator_mode=creator_mode,
        headless=headless,
        enable_save_media=save_media,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


async def bili_search_time_range(
    keywords: str,
    start_day: str,
    end_day: str,
    max_notes: int = 15,
    max_notes_per_day: int = 50,
    daily_limit: bool = False,
    enable_comments: bool = True,
    max_comments_per_note: int = 10,
    headless: bool = False,
    save_media: bool = False,
) -> str:
    """
    按时间范围搜索 Bilibili 视频。
    """
    result = await bilibili_core.search_with_time_range(
        keywords=keywords,
        start_day=start_day,
        end_day=end_day,
        max_notes=max_notes,
        max_notes_per_day=max_notes_per_day,
        daily_limit=daily_limit,
        enable_comments=enable_comments,
        max_comments_per_note=max_comments_per_note,
        headless=headless,
        enable_save_media=save_media,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


__all__ = [
    "bili_search",
    "bili_detail",
    "bili_creator",
    "bili_search_time_range",
]

