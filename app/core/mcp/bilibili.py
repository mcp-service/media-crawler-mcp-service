# -*- coding: utf-8 -*-
"""Bilibili MCP tool implementations."""

from __future__ import annotations

import json
from typing import List, Optional

from app.core.crawler.platforms import bilibili as bilibili_core
from app.providers.logger import get_logger
from app.api.scheme.response import (
    BilibiliSearchResult,
    BilibiliDetailResult,
    BilibiliVideoSimple,
    BilibiliVideoFull,
    BilibiliCommentsResult,
    BilibiliComment,
    BilibiliCreatorResult,
    TagInfo,
)

logger = get_logger()


def _process_search_fast_result(raw_result: dict) -> BilibiliSearchResult:
    """处理 Fast 搜索结果（预期返回包含 videos 列表）。不做兜底。"""
    videos: list[BilibiliVideoSimple] = []
    for item in raw_result.get("videos", []):
        videos.append(BilibiliVideoSimple.from_full_video(item))
    return BilibiliSearchResult(
        videos=videos,
        total_count=raw_result.get("total_count", len(videos)),
        keywords=raw_result.get("keywords", ""),
        crawl_info=raw_result.get("crawl_info", {}),
    )


def _process_search_api_result(raw_result: dict) -> BilibiliSearchResult:
    """处理直出 API 搜索结果（预期返回包含 result 列表）。不做兜底。"""
    videos: list[BilibiliVideoSimple] = []
    for it in raw_result.get("result", []):
        aid = str(it.get("aid", it.get("id", "")))
        bvid = it.get("bvid", "")
        url = f"https://www.bilibili.com/video/{bvid}" if bvid else f"https://www.bilibili.com/video/av{aid}"
        cover = it.get("pic", "")
        if isinstance(cover, str) and cover.startswith("//"):
            cover = "https:" + cover
        mapped = {
            "video_id": aid,
            "title": it.get("title", ""),
            "desc": it.get("description", ""),
            "create_time": it.get("pubdate"),
            "user_id": str(it.get("mid", "")),
            "nickname": it.get("author", ""),
            "video_play_count": str(it.get("play", 0)),
            "liked_count": str(it.get("like", 0)),
            "video_comment": str(it.get("review", it.get("video_review", 0))),
            "video_url": url,
            "video_cover_url": cover,
            "source_keyword": raw_result.get("keywords", ""),
        }
        videos.append(BilibiliVideoSimple.from_full_video(mapped))
    return BilibiliSearchResult(
        videos=videos,
        total_count=raw_result.get("numResults", len(videos)),
        keywords=raw_result.get("keywords", ""),
        crawl_info=raw_result.get("crawl_info", {}),
    )


def _process_search_detail_map_result(raw_result: dict) -> BilibiliSearchResult:
    """处理普通/时间范围搜索结果（预期返回 {keyword: [detail(View/Card)...]}）。不做兜底。"""
    flattened: list[dict] = []
    keywords_collected: list[str] = []
    for k, v in raw_result.items():
        if not isinstance(v, list):
            continue
        keywords_collected.append(str(k))
        for detail in v:
            view = (detail or {}).get("View", {})
            stat = view.get("stat", {})
            owner = view.get("owner", {})
            aid = str(view.get("aid", ""))
            bvid = view.get("bvid", "")
            url = f"https://www.bilibili.com/video/{bvid}" if bvid else f"https://www.bilibili.com/video/av{aid}"
            cover = view.get("pic", "")
            if isinstance(cover, str) and cover.startswith("//"):
                cover = "https:" + cover
            mapped = {
                "video_id": aid,
                "title": view.get("title", ""),
                "desc": view.get("desc", ""),
                "create_time": view.get("pubdate"),
                "user_id": str(owner.get("mid", "")),
                "nickname": owner.get("name", ""),
                "video_play_count": str(stat.get("view", 0)),
                "liked_count": str(stat.get("like", 0)),
                "video_comment": str(stat.get("reply", 0)),
                "video_url": url,
                "video_cover_url": cover,
                "source_keyword": str(k),
            }
            flattened.append(mapped)

    videos = [BilibiliVideoSimple.from_full_video(item) for item in flattened]
    return BilibiliSearchResult(
        videos=videos,
        total_count=len(videos),
        keywords=",".join([kw for kw in keywords_collected if kw]),
        crawl_info=raw_result.get("crawl_info", {}),
    )


def _process_detail_result(raw_result: dict) -> BilibiliDetailResult:
    """处理详情结果，转换为完整模型"""
    if not isinstance(raw_result, dict):
        return BilibiliDetailResult()

    videos = []
    if "videos" in raw_result and isinstance(raw_result["videos"], list):
        for video_data in raw_result["videos"]:
            try:
                full_video = BilibiliVideoFull(**video_data)
                videos.append(full_video)
            except Exception as e:
                # 如果某个视频数据有问题，跳过但不影响其他视频
                continue

    return BilibiliDetailResult(
        videos=videos,
        total_count=raw_result.get("total_count"),
        crawl_info=raw_result.get("crawl_info", {}),
    )


def _process_creator_result(raw_result: dict) -> BilibiliCreatorResult:
    """处理创作者结果，转换为结构化模型"""
    if not isinstance(raw_result, dict):
        return BilibiliCreatorResult(
            creator_info={"creator_id": "", "creator_name": "", "total_videos": 0},
            videos=[]
        )

    videos = []
    if "videos" in raw_result and isinstance(raw_result["videos"], list):
        for video_data in raw_result["videos"]:
            try:
                simple_video = BilibiliVideoSimple(**video_data)
                videos.append(simple_video)
            except Exception as e:
                # 如果某个视频数据有问题，跳过但不影响其他视频
                continue

    return BilibiliCreatorResult(
        creator_info=raw_result.get("creator_info", {}),
        videos=videos,
        total_count=raw_result.get("total_count"),
        page_info=raw_result.get("page_info", {}),
        crawl_info=raw_result.get("crawl_info", {}),
    )


def _process_comments_result(raw_result: dict) -> BilibiliCommentsResult:
    """处理评论结果，转换为结构化模型

    输入格式: {"comments": {video_id: [comment_dict_list]}}
    输出格式: BilibiliCommentsResult with flat comment list
    """
    if not isinstance(raw_result, dict):
        return BilibiliCommentsResult()

    comments_dict = raw_result.get("comments", {})
    if not isinstance(comments_dict, dict):
        return BilibiliCommentsResult()

    all_comments = []
    video_ids = []

    for video_id, comment_list in comments_dict.items():
        video_ids.append(str(video_id))
        if not isinstance(comment_list, list):
            continue

        for comment_data in comment_list:
            try:
                # 从原始评论数据提取字段
                comment_id = str(comment_data.get("rpid", ""))
                parent_comment_id = str(comment_data.get("parent", 0))
                content_dict = comment_data.get("content", {})
                user_info = comment_data.get("member", {})

                comment = BilibiliComment(
                    comment_id=comment_id,
                    parent_comment_id=parent_comment_id,
                    create_time=comment_data.get("ctime"),
                    video_id=str(video_id),
                    content=content_dict.get("message", "") if isinstance(content_dict, dict) else "",
                    user_id=str(user_info.get("mid", "")) if isinstance(user_info, dict) else "",
                    nickname=user_info.get("uname", "") if isinstance(user_info, dict) else "",
                    sex=user_info.get("sex", "") if isinstance(user_info, dict) else "",
                    sign=user_info.get("sign", "") if isinstance(user_info, dict) else "",
                    avatar=user_info.get("avatar", "") if isinstance(user_info, dict) else "",
                    sub_comment_count=str(comment_data.get("rcount", 0)),
                    like_count=comment_data.get("like", 0),
                )
                all_comments.append(comment)
            except Exception as e:
                # 如果某个评论数据有问题，跳过但不影响其他评论
                continue

    return BilibiliCommentsResult(
        comments=all_comments,
        total_count=len(all_comments),
        video_ids=video_ids,
    )


async def bili_search(
    keywords: str,
    page_size: int = 1,
    page_num: int = 1,
    save_media: bool = False,
) -> str:
    """
    搜索 Bilibili 视频，返回简化的结果。

    Args:
        keywords: 搜索关键词，多个关键词用逗号分隔。
        page_size: 单页作品数量。
        page_num: 页码（从 1 开始，不循环）。
        save_media: 是否保存媒体文件。
    """
    raw_result = await bilibili_core.search(
        keywords=keywords,
        page_size=page_size,
        page_num=page_num,
        enable_save_media=save_media,
    )
    
    # 转换为简化的结构化数据（search 固定按 Fast 模式处理，不做兜底）
    structured_result = _process_search_fast_result(raw_result)
    return structured_result.model_dump_json(ensure_ascii=False, indent=2)


async def bili_search_time_range(
    keywords: str,
    start_day: str,
    end_day: str,
    page_size: int = 1,
    page_num: int = 1,
    save_media: bool = False,
) -> str:
    """
    按时间范围搜索 Bilibili 视频，返回简化的结果。

    Args:
        keywords: 搜索关键词，多个关键词用逗号分隔。
        start_day: 起始时间 YYYY/MM/DD
        end_day: 结束时间 YYYY/MM/DD
        page_size: 单页作品数量。
        page_num: 页码（从 1 开始，不循环）。
        save_media: 是否保存媒体文件。
    """
    raw_result = await bilibili_core.search_with_time_range(
        keywords=keywords,
        start_day=start_day,
        end_day=end_day,
        page_size=page_size,
        page_num=page_num,
        enable_save_media=save_media,
    )
    
    # 转换为简化的结构化数据（时间范围工具固定按 detail map 处理，不做兜底）
    structured_result = _process_search_detail_map_result(raw_result)
    return structured_result.model_dump_json(ensure_ascii=False, indent=2)


async def bili_detail(
    video_ids: List[str],
    save_media: bool = False,
) -> str:
    """
    获取指定视频详情，返回完整的结果。

    Args:
        video_ids: 视频id列表。
        save_media: 是否保存媒体文件。
    """
    raw_result = await bilibili_core.get_detail(
        video_ids=video_ids,
        enable_save_media=save_media,
    )
    
    # 直接返回原始结果，不进行格式化处理
    return json.dumps(raw_result, ensure_ascii=False, indent=2)


async def bili_creator(
    creator_ids: List[str],
    page_num: int = 1,
    page_size: int = 30,
    save_media: bool = False,
) -> str:
    """
    获取指定创作者的视频，支持批量获取多个创作者，支持分页。

    Args:
        creator_ids: 创作者ID列表，例如: ["99801185", "12345678"]
        page_num: 页码，从1开始，默认 1
        page_size: 每页视频数量，默认 30
        save_media: 是否保存媒体资源（图片、视频），默认 False

    Returns:
        JSON字符串，包含所有创作者信息和视频列表

    Example:
        creator_ids=["99801185", "12345678"], page_num=1, page_size=10
    """
    import asyncio
    
    all_results = {}
    
    for i, creator_id in enumerate(creator_ids):
        try:
            raw_result = await bilibili_core.get_creator(
                creator_id=creator_id,
                page_num=page_num,
                page_size=page_size,
                enable_save_media=save_media,
            )
            logger.info(f"raw_result ----> {raw_result}")
            # 转换为结构化数据
            structured_result = _process_creator_result(raw_result)
            all_results[creator_id] = structured_result.model_dump()
            
        except Exception as e:
            import traceback
            logger.error(f"Exception ----> {traceback.format_exc()}")
            all_results[creator_id] = {"error": str(e), "creator_id": creator_id}
        
        # 多个用户之间添加间隔，避免风控（最后一个不需要间隔）
        if i < len(creator_ids) - 1:
            await asyncio.sleep(2)  # 2秒间隔
    
    return json.dumps(all_results, ensure_ascii=False, indent=2)


async def bili_comments(
    video_ids: List[str],
    max_comments: int = 20,
    fetch_sub_comments: bool = False,
    headless: Optional[bool] = None,
) -> str:
    """
    根据视频ID抓取评论，返回结构化的评论列表。
    """
    raw_result = await bilibili_core.fetch_comments(
        video_ids=video_ids,
        max_comments=max_comments,
        fetch_sub_comments=fetch_sub_comments,
        headless=headless,
    )

    # 转换为结构化的评论数据
    structured_result = _process_comments_result(raw_result)
    return structured_result.model_dump_json(ensure_ascii=False, indent=2)


__all__ = [
    "bili_search",
    "bili_search_time_range",
    "bili_detail",
    "bili_creator",
    "bili_comments",
]
