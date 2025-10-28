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
from app.config.settings import Platform
from app.core.mcp import bilibili as bili_tools
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
        # 只传递基本参数
        result = await bili_tools.bili_search(
            keywords=keywords,
            page_size=page_size,
            page_num=page_num,
            save_media=False
        )
        return {
            "code": error_codes.SUCCESS[0],
            "msg": error_codes.SUCCESS[1],
            "data": _as_dict(result),
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

    params = _to_tool_params(req.to_service_params())
    try:
        result = await bili_tools.bili_detail(**params)
        return {
            "code": error_codes.SUCCESS[0],
            "msg": error_codes.SUCCESS[1],
            "data": _as_dict(result),
        }
    except LoginExpiredError:
        return {
            "code": error_codes.INVALID_TOKEN[0],
            "msg": "登录过期，Cookie失效",
            "data": {},
        }
    except Exception as exc:  # pragma: no cover
        import traceback
        logger.error(f"[Bilibili.detail] failed: {traceback.format_exc(exc)}")
        return _server_error(f"bilibili 详情获取失败: {exc}, 可以重试一下")


@bili_mcp.tool(
    name="crawler_creator",
    description="获取 Bilibili UP 主视频",
    tags={"bilibili", "creator"}
)
async def crawler_creator(creator_ids: list[str], page_num: int = 1, page_size: int = 30):
    try:
        req = BiliCreatorRequest.model_validate({
            "creator_ids": creator_ids,
            "page_num": page_num,
            "page_size": page_size
        })
    except ValidationError as exc:
        return _validation_error(exc)

    params = _to_tool_params(req.to_service_params())
    try:
        result = await bili_tools.bili_creator(**params)
        return {
            "code": error_codes.SUCCESS[0],
            "msg": error_codes.SUCCESS[1],
            "data": _as_dict(result),
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

    # 只传递实际需要的参数
    params = {
        "keywords": keywords,
        "start_day": start_day,
        "end_day": end_day,
        "page_size": page_size,
        "page_num": page_num,
        "save_media": False
    }
    try:
        result = await bili_tools.bili_search_time_range(**params)
        return {
            "code": error_codes.SUCCESS[0],
            "msg": error_codes.SUCCESS[1],
            "data": _as_dict(result),
        }
    except LoginExpiredError:
        return {
            "code": error_codes.INVALID_TOKEN[0],
            "msg": "登录过期，Cookie失效",
            "data": {},
        }
    except Exception as exc:  # pragma: no cover
        import traceback
        logger.error(f"[Bilibili.search_time_range] failed: {traceback.format_exc(exc)}")
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

    params = _to_tool_params(req.to_service_params())
    try:
        result = await bili_tools.bili_comments(**params)
        return {
            "code": error_codes.SUCCESS[0],
            "msg": error_codes.SUCCESS[1],
            "data": _as_dict(result),
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



def _to_tool_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Adjust parameter names so they match tool signatures."""
    adjusted = dict(params)
    if "enable_save_media" in adjusted:
        adjusted["save_media"] = adjusted.pop("enable_save_media")
    return adjusted


def _as_dict(result: str | Dict[str, Any]) -> Dict[str, Any]:
    """Ensure tool responses are JSON objects."""
    if isinstance(result, dict):
        return result
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {"raw": result}


__all__ = ["bili_mcp"]
