# -*- coding: utf-8 -*-
"""Xiaohongshu MCP tool implementations."""

from __future__ import annotations

import json
from typing import List, Optional

from app.core.crawler.platforms.xhs import service as xhs_service
from app.providers.logger import get_logger
from app.api.scheme.response.xhs import XhsCommentsResult, XhsNoteDetail, XhsNoteSearchResult

logger = get_logger()


def _parse_count(value) -> Optional[int]:
    """
    解析小红书的数量字符串，支持 "3万"、"1.3万" 等格式。

    Args:
        value: 可能是整数、字符串或 None

    Returns:
        整数或 None

    Examples:
        "3万" -> 30000
        "1.3万" -> 13000
        "123" -> 123
        123 -> 123
        None -> None
    """
    if value is None:
        return None

    # 如果已经是整数，直接返回
    if isinstance(value, int):
        return value

    # 转换为字符串处理
    s = str(value).strip()
    if not s:
        return None

    try:
        # 处理 "万" 单位
        if "万" in s:
            s = s.replace("万", "")
            return int(float(s) * 10000)
        # 直接解析数字
        return int(s)
    except (ValueError, TypeError):
        return None


def _flatten_note(note: dict) -> dict:
    """
    将 crawler 返回的嵌套结构扁平化为 XhsNoteDetail 所需的格式。

    Crawler 返回的结构：
    {
        "note_id": "xxx",
        "user": {"user_id": "xxx", "nickname": "xxx", "avatar": "xxx"},
        "interact_info": {"liked_count": 123, ...}
    }

    XhsNoteDetail 需要的结构：
    {
        "note_id": "xxx",
        "user_id": "xxx",
        "nickname": "xxx",
        "avatar": "xxx",
        "liked_count": 123,
        ...
    }
    """
    flattened = dict(note)

    # 提取 user 信息到顶层
    user = note.get("user", {})
    if isinstance(user, dict):
        flattened["user_id"] = user.get("user_id") or user.get("userId")
        flattened["nickname"] = user.get("nickname") or user.get("nick_name")
        flattened["avatar"] = user.get("avatar")

    # 提取 interact_info 信息到顶层，并转换数量字符串
    interact = note.get("interact_info", {}) or note.get("interactInfo", {})
    if isinstance(interact, dict):
        flattened["liked_count"] = _parse_count(interact.get("liked_count") or interact.get("likedCount"))
        flattened["comment_count"] = _parse_count(interact.get("comment_count") or interact.get("commentCount"))
        flattened["share_count"] = _parse_count(interact.get("share_count") or interact.get("shareCount"))
        flattened["collected_count"] = _parse_count(interact.get("collected_count") or interact.get("collectedCount"))

    return flattened

async def xhs_search(
    keywords: str,
    page_num: int = 1,
    page_size: int = 20,
    save_media: bool = False,
) -> str:
    """
    搜索小红书笔记，返回结构化的搜索结果。

    Args:
        keywords: 搜索关键词，多个关键词用逗号分隔。
        page_num: 页码，从1开始。
        page_size: 每页数量。
        save_media: 是否保存媒体资源（图片、视频）。
    """
    result = await xhs_service.search(
        keywords=keywords,
        page_num=page_num,
        page_size=page_size,
        enable_save_media=save_media,
    )
    payload = XhsNoteSearchResult(
        notes=[_flatten_note(note) for note in result.get("notes", [])],
        total_count=result.get("total_count", 0),
        crawl_info=result.get("crawl_info", {}),
    )
    return payload.model_dump_json(ensure_ascii=False, indent=2)


async def xhs_detail(
    note_id: str,
    xsec_token: str,
    xsec_source: Optional[str] = None,
    save_media: bool = False
) -> str:
    """
    获取小红书笔记详情，返回结构化的详情信息（不包含评论，评论请使用 xhs_comments）。

    Args:
        note_id: 笔记ID
        xsec_token: 必传，推荐从搜索结果或分享链接中获取
        xsec_source: 可选，未提供时服务会默认 pc_search
        save_media: 是否保存媒体资源（图片、视频），默认 False

    Returns:
        JSON字符串，包含笔记详情列表、总数量和抓取信息

    Example:
        node_id="68f9b8b20000000004010353", xsec_token="从搜索结果获取"
    """
    result = await xhs_service.get_detail(
        note_id=note_id,
        xsec_token=xsec_token,
        xsec_source=xsec_source,
        enable_save_media=save_media,
    )
    logger.debug(f"[xhs-detail] result {result}")
    payload = XhsNoteSearchResult(
        notes=[_flatten_note(note) for note in result.get("notes", [])],
        total_count=result.get("total_count", 0),
        crawl_info=result.get("crawl_info", {}),
    )
    return payload.model_dump_json(ensure_ascii=False, indent=2)


async def xhs_creator(
    creator_ids: List[str],
    save_media: bool = False,
) -> str:
    """
    获取小红书创作者的作品，返回创作者信息和作品列表。

    Args:
        creator_ids: 创作者ID列表，例如: ["user123", "user456"]
        save_media: 是否保存媒体资源（图片、视频），默认 False

    Returns:
        JSON字符串，包含创作者信息和作品列表

    Example:
        creator_ids=["user12345"], save_media=True
    """
    result = await xhs_service.get_creator(
        creator_ids=creator_ids,
        enable_save_media=save_media,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


async def xhs_comments(
    note_id: str,
    xsec_token: str,
    xsec_source: Optional[str] = None,
    max_comments: int = 50
) -> str:
    """
    获取单条小红书笔记的评论，返回结构化的评论信息。

    Args:
        note_id: 笔记ID
        xsec_token: 必传，从搜索结果中获取
        xsec_source: 可选，未提供时默认 pc_search
        max_comments: 最大评论数量，默认 50

    Returns:
        JSON字符串，包含评论列表、总数量和抓取信息

    Example:
        note_id="68f9b8b20000000004010353", xsec_token="ABxxx", max_comments=100
    """
    result = await xhs_service.fetch_comments(
        note_id=note_id,
        xsec_token=xsec_token,
        xsec_source=xsec_source or "",
        max_comments=max_comments,
    )
    payload = XhsCommentsResult(
        comments=result.get("comments", {}),
        total_count=result.get("total_count", 0),
        crawl_info=result.get("crawl_info", {}),
    )
    return payload.model_dump_json(ensure_ascii=False, indent=2)


async def xhs_publish(
    title: str,
    content: str,
    images: list[str],
    tags: list[str] | None = None,
    headless: bool | None = None,
) -> str:
    """发布小红书图文内容（图文版）。"""
    result = await xhs_service.publish_image(
        title=title,
        content=content,
        images=images,
        tags=tags or [],
        headless=headless,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


async def xhs_publish_video(
    title: str,
    content: str,
    video: str,
    tags: list[str] | None = None,
    headless: bool | None = None,
) -> str:
    result = await xhs_service.publish_video(
        title=title,
        content=content,
        video=video,
        tags=tags or [],
        headless=headless,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


__all__ = ["xhs_search", "xhs_detail", "xhs_creator", "xhs_comments"]
__all__.append("xhs_publish")
__all__.append("xhs_publish_video")
