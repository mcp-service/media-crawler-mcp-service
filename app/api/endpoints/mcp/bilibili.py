# -*- coding: utf-8 -*-
"""Bilibili MCP endpoints and tool registrations."""

from __future__ import annotations

import json
from typing import Any, Dict

from pydantic import ValidationError

from app.api.scheme import error_codes
from app.api.scheme.request.bilibili_scheme import (
    BiliCommentsRequest,
    BiliCreatorRequest,
    BiliDetailRequest,
    BiliSearchRequest,
    BiliSearchTimeRangeRequest,
)
from app.config.settings import global_settings
from app.core.crawler.platforms import bilibili as bilibili_core
from app.core.login.exceptions import LoginExpiredError
from app.providers.logger import get_logger
from fastmcp import FastMCP

logger = get_logger()

bili_mcp = FastMCP(name="B站MCP")


def _validation_error(exc: ValidationError) -> Dict[str, Any]:
    return {
        "code": error_codes.PARAM_ERROR[0],
        "msg": error_codes.PARAM_ERROR[1],
        "data": {"errors": exc.errors()},
    }


def _server_error(message: str) -> Dict[str, Any]:
    return {
        "code": error_codes.SERVER_ERROR[0],
        "msg": message or error_codes.SERVER_ERROR[1],
        "data": {},
    }


@bili_mcp.tool(
    name="search",
    description="搜索 Bilibili 视频",
    tags={"bilibili", "search"}
)
async def search(keywords: str, page_size: int = 5, page_num: int = 1):
    try:
        # 直接实例化Crawler调用方法
        crawler = bilibili_core.BilibiliCrawler(headless=global_settings.browser.headless, enable_save_media=False)
        await crawler.ensure_login_and_client(no_auto_login=True)

        result = await crawler.search_by_keywords_fast(
            keywords=keywords,
            page_size=page_size,
            page_num=page_num,
        )

        await crawler.cleanup()

        return {
            "code": error_codes.SUCCESS[0],
            "msg": error_codes.SUCCESS[1],
            "data": result,
        }
    except LoginExpiredError:
        return {
            "code": error_codes.INVALID_TOKEN[0],
            "msg": "登录过期，Cookie失效",
            "data": {},
        }
    except Exception as exc:  # pragma: no cover - runtime safeguard
        logger.error(f"[Bilibili.search] failed: {exc}")
        return _server_error(f"bilibili 搜索失败: {exc}")


@bili_mcp.tool(
    name="crawler_detail",
    description="获取 Bilibili 视频详情",
    tags={"bilibili", "detail"}
)
async def crawler_detail(video_ids: list[str]):
    try:
        req = BiliDetailRequest.model_validate({
            "video_ids": video_ids
        })
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        # 直接实例化Crawler调用方法
        crawler = bilibili_core.BilibiliCrawler(headless=global_settings.browser.headless, enable_save_media=False)
        await crawler.ensure_login_and_client(no_auto_login=True)

        result = await crawler.get_specified_videos(
            video_ids=req.video_ids,
            source_keyword="detail"
        )

        await crawler.cleanup()

        return {
            "code": error_codes.SUCCESS[0],
            "msg": error_codes.SUCCESS[1],
            "data": result,
        }
    except LoginExpiredError:
        return {
            "code": error_codes.INVALID_TOKEN[0],
            "msg": "登录过期，Cookie失效",
            "data": {},
        }
    except Exception as exc:  # pragma: no cover
        import traceback
        logger.error(f"[Bilibili.detail] failed: {traceback.format_exc()}")
        return _server_error(f"bilibili 详情获取失败: {exc}, 可以重试一下")


@bili_mcp.tool(
    name="crawler_creator",
    description="获取 Bilibili UP 主视频",
    tags={"bilibili", "creator"}
)
async def crawler_creator(creator_id: str, page_num: int = 1, page_size: int = 30):
    try:
        req = BiliCreatorRequest.model_validate({
            "creator_id": creator_id,
            "page_num": page_num,
            "page_size": page_size
        })
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        # 直接实例化Crawler调用方法
        crawler = bilibili_core.BilibiliCrawler(headless=global_settings.browser.headless, enable_save_media=False)
        await crawler.ensure_login_and_client(no_auto_login=True)

        result = await crawler.get_creator_videos(
            creator_id=req.creator_id,
            page_num=req.page_num,
            page_size=req.page_size
        )

        await crawler.cleanup()

        return {
            "code": error_codes.SUCCESS[0],
            "msg": error_codes.SUCCESS[1],
            "data": result,
        }
    except LoginExpiredError:
        return {
            "code": error_codes.INVALID_TOKEN[0],
            "msg": "登录过期，Cookie失效",
            "data": {},
        }
    except Exception as exc:  # pragma: no cover
        logger.error(f"[Bilibili.creator] failed: {exc}")
        return _server_error(f"bilibili 创作者抓取失败: {exc}")


@bili_mcp.tool(
    name="search_time_range_http",
    description="按时间范围搜索 Bilibili 视频",
    tags={"bilibili", "search", "time_range"}
)
async def search_time_range_http(keywords: str, start_day: str, end_day: str, page_size: int = 5, page_num: int = 1):
    try:
        req = BiliSearchTimeRangeRequest.model_validate({
            "keywords": keywords,
            "start_day": start_day,
            "end_day": end_day,
            "page_size": page_size,
            "page_num": page_num
        })
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        # 直接实例化Crawler调用方法
        crawler = bilibili_core.BilibiliCrawler(headless=global_settings.browser.headless, enable_save_media=False)
        await crawler.ensure_login_and_client(no_auto_login=True)

        result = await crawler.search_by_keywords_in_time_range(
            keywords=req.keywords,
            start_day=req.start_day,
            end_day=req.end_day,
            page_size=req.page_size,
            page_num=req.page_num
        )

        await crawler.cleanup()

        return {
            "code": error_codes.SUCCESS[0],
            "msg": error_codes.SUCCESS[1],
            "data": result,
        }
    except LoginExpiredError:
        return {
            "code": error_codes.INVALID_TOKEN[0],
            "msg": "登录过期，Cookie失效",
            "data": {},
        }
    except Exception as exc:  # pragma: no cover
        import traceback
        logger.error(f"[Bilibili.search_time_range] failed: {traceback.format_exc()}")
        return _server_error(f"bilibili 时间范围搜索失败: {exc}")


@bili_mcp.tool(
    name="crawler_comments",
    description="按视频 ID 抓取 Bilibili 评论",
    tags={"bilibili", "comments"}
)
async def crawler_comments(video_ids: list[str], max_comments: int = 20, fetch_sub_comments: bool = False):
    try:
        req = BiliCommentsRequest.model_validate({
            "video_ids": video_ids,
            "max_comments": max_comments,
            "fetch_sub_comments": fetch_sub_comments
        })
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        # 直接实例化Crawler调用方法
        crawler = bilibili_core.BilibiliCrawler(headless=global_settings.browser.headless, enable_save_media=False)
        await crawler.ensure_login_and_client(no_auto_login=True)

        result = await crawler.fetch_comments_for_ids(
            video_ids=req.video_ids,
            enable_get_sub_comments=req.fetch_sub_comments,
            max_comments_per_note=req.max_comments
        )

        await crawler.cleanup()

        return {
            "code": error_codes.SUCCESS[0],
            "msg": error_codes.SUCCESS[1],
            "data": result,
        }
    except LoginExpiredError:
        return {
            "code": error_codes.INVALID_TOKEN[0],
            "msg": "登录过期，Cookie失效",
            "data": {},
        }
    except Exception as exc:  # pragma: no cover
        logger.error(f"[Bilibili.comments] failed: {exc}")
        return _server_error(f"bilibili 评论抓取失败: {exc}")


__all__ = ["bili_mcp"]