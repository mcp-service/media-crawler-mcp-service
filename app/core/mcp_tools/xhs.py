# -*- coding: utf-8 -*-
"""Xiaohongshu MCP tool implementations."""

from __future__ import annotations

import json
from typing import List, Optional

from app.core.crawler.platforms.xhs import service as xhs_service
from .schemas.xhs import XhsCommentsResult, XhsNoteDetail, XhsNoteSearchResult


async def xhs_search(
    keywords: str,
    limit: int = 20,
    enable_comments: bool = False,
    max_comments_per_note: int = 0,
    headless: Optional[bool] = None,
    save_media: bool = False,
    **kwargs,
) -> str:
    result = await xhs_service.search(
        keywords=keywords,
        limit=limit,
        enable_comments=enable_comments,
        max_comments_per_note=max_comments_per_note,
        headless=headless,
        enable_save_media=save_media,
        **kwargs,
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
    **kwargs,
) -> str:
    result = await xhs_service.get_detail(
        note_urls=note_urls,
        enable_comments=enable_comments,
        max_comments_per_note=max_comments_per_note,
        headless=headless,
        enable_save_media=save_media,
        **kwargs,
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
    **kwargs,
) -> str:
    result = await xhs_service.get_creator(
        creator_ids=creator_ids,
        enable_comments=enable_comments,
        max_comments_per_note=max_comments_per_note,
        headless=headless,
        enable_save_media=save_media,
        **kwargs,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


async def xhs_comments(
    note_urls: List[str],
    max_comments: int = 50,
    headless: Optional[bool] = None,
    **kwargs,
) -> str:
    result = await xhs_service.fetch_comments(
        note_urls=note_urls,
        max_comments=max_comments,
        headless=headless,
        **kwargs,
    )
    payload = XhsCommentsResult(
        comments=result.get("comments", {}),
        total_count=result.get("total_count", 0),
        crawl_info=result.get("crawl_info", {}),
    )
    return payload.model_dump_json(ensure_ascii=False, indent=2)


__all__ = ["xhs_search", "xhs_detail", "xhs_creator", "xhs_comments"]
