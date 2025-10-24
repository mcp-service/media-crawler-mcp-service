# -*- coding: utf-8 -*-
"""Bilibili MCP endpoints and tool registrations."""

from __future__ import annotations

import json
from typing import Any, Dict

from pydantic import ValidationError
from starlette.responses import JSONResponse

from app.api.scheme import error_codes, jsonify_response
from app.api.scheme.request.bilibili_scheme import (
    BiliCommentsRequest,
    BiliCreatorRequest,
    BiliDetailRequest,
    BiliSearchRequest,
    BiliSearchTimeRangeRequest,
)
from app.config.settings import Platform
from app.core.mcp_tools import bilibili as bili_tools
from app.core.login.exceptions import LoginExpiredError
from app.providers.logger import get_logger
from fastmcp import FastMCP

logger = get_logger()

bili_mcp = FastMCP(name="B站MCP")


def _validation_error(exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        {
            "code": error_codes.PARAM_ERROR[0],
            "msg": error_codes.PARAM_ERROR[1],
            "data": {"errors": exc.errors()},
        },
        status_code=400,
    )


def _server_error(message: str) -> JSONResponse:
    return JSONResponse(
        {
            "code": error_codes.SERVER_ERROR[0],
            "msg": message or error_codes.SERVER_ERROR[1],
            "data": {},
        },
        status_code=500,
    )


@bili_mcp.tool(description="搜索 Bilibili 视频",)
async def search(request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    try:
        req = BiliSearchRequest.model_validate(payload)
    except ValidationError as exc:
        return _validation_error(exc)

    params = _to_tool_params(req.to_service_params())
    try:
        result = await bili_tools.bili_search(**params)
        return jsonify_response(_as_dict(result))
    except LoginExpiredError:
        return jsonify_response({}, status_response=(error_codes.INVALID_TOKEN[0], "登录过期，Cookie失效"))
    except Exception as exc:  # pragma: no cover - runtime safeguard
        logger.error(f"[Bilibili.search] failed: {exc}")
        return _server_error(f"bilibili 搜索失败: {exc}")


@bili_mcp.tool(description="获取 Bilibili 视频详情")
async def crawler_detail(request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    try:
        req = BiliDetailRequest.model_validate(payload)
    except ValidationError as exc:
        return _validation_error(exc)

    params = _to_tool_params(req.to_service_params())
    try:
        result = await bili_tools.bili_detail(**params)
        return jsonify_response(_as_dict(result))
    except LoginExpiredError:
        return jsonify_response({}, status_response=(error_codes.INVALID_TOKEN[0], "登录过期，Cookie失效"))
    except Exception as exc:  # pragma: no cover
        logger.error(f"[Bilibili.detail] failed: {exc}")
        return _server_error(f"bilibili 详情获取失败: {exc}")


@bili_mcp.tool(description="获取 Bilibili UP 主视频")
async def crawler_creator(request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    try:
        req = BiliCreatorRequest.model_validate(payload)
    except ValidationError as exc:
        return _validation_error(exc)

    params = _to_tool_params(req.to_service_params())
    try:
        result = await bili_tools.bili_creator(**params)
        return jsonify_response(_as_dict(result))
    except LoginExpiredError:
        return jsonify_response({}, status_response=(error_codes.INVALID_TOKEN[0], "登录过期，Cookie失效"))
    except Exception as exc:  # pragma: no cover
        logger.error(f"[Bilibili.creator] failed: {exc}")
        return _server_error(f"bilibili 创作者抓取失败: {exc}")


@bili_mcp.tool(description="按时间范围搜索 Bilibili 视频")
async def search_time_range_http(request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    try:
        req = BiliSearchTimeRangeRequest.model_validate(payload)
    except ValidationError as exc:
        return _validation_error(exc)

    params = _to_tool_params(req.to_service_params())
    try:
        result = await bili_tools.bili_search_time_range(**params)
        return jsonify_response(_as_dict(result))
    except LoginExpiredError:
        return jsonify_response({}, status_response=(error_codes.INVALID_TOKEN[0], "登录过期，Cookie失效"))
    except Exception as exc:  # pragma: no cover
        logger.error(f"[Bilibili.search_time_range] failed: {exc}")
        return _server_error(f"bilibili 时间范围搜索失败: {exc}")


@bili_mcp.tool(description="按视频 ID 抓取 Bilibili 评论")
async def crawler_comments(request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    try:
        req = BiliCommentsRequest.model_validate(payload)
    except ValidationError as exc:
        return _validation_error(exc)

    params = _to_tool_params(req.to_service_params())
    try:
        result = await bili_tools.bili_comments(**params)
        return jsonify_response(_as_dict(result))
    except LoginExpiredError:
        return jsonify_response({}, status_response=(error_codes.INVALID_TOKEN[0], "登录过期，Cookie失效"))
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
