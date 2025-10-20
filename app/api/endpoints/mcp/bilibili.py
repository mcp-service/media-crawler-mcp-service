# -*- coding: utf-8 -*-
"""Bilibili (B站) 平台端点与 MCP 工具注册。"""

from __future__ import annotations

import json
from typing import Any, Dict

from pydantic import ValidationError
from starlette.responses import JSONResponse

from app.api.endpoints.base import MCPBlueprint
from app.api.scheme import error_codes, jsonify_response
from app.api.scheme.bilibili_scheme import (
    BiliCreatorRequest,
    BiliDetailRequest,
    BiliSearchRequest,
    BiliSearchTimeRangeRequest,
)
from app.config.settings import Platform
from app.core.tools import bilibili as bili_tools
from app.providers.logger import get_logger


logger = get_logger()
bp = MCPBlueprint(
    prefix=f"/{Platform.BILIBILI.value}",
    name=Platform.BILIBILI.value,
    tags=["B站"],
    category=Platform.BILIBILI.value,
)


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


@bp.route("/search", methods=["POST"])
async def bili_search_http(request):
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
    except Exception as exc:  # pragma: no cover - runtime safeguard
        logger.error(f"[Bilibili.search] 执行失败: {exc}")
        return _server_error(f"bilibili 搜索失败: {exc}")


@bp.route("/detail", methods=["POST"])
async def bili_detail_http(request):
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
    except Exception as exc:  # pragma: no cover
        logger.error(f"[Bilibili.detail] 执行失败: {exc}")
        return _server_error(f"bilibili 详情获取失败: {exc}")


@bp.route("/creator", methods=["POST"])
async def bili_creator_http(request):
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
    except Exception as exc:  # pragma: no cover
        logger.error(f"[Bilibili.creator] 执行失败: {exc}")
        return _server_error(f"bilibili 创作者抓取失败: {exc}")


@bp.route("/search/time-range", methods=["POST"])
async def bili_search_time_range_http(request):
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
    except Exception as exc:  # pragma: no cover
        logger.error(f"[Bilibili.search_time_range] 执行失败: {exc}")
        return _server_error(f"bilibili 时间范围搜索失败: {exc}")


bp.tool(
    "bili_search",
    description="搜索 Bilibili 视频",
    http_path="/search",
    http_methods=["POST"],
)(bili_tools.bili_search)

bp.tool(
    "bili_detail",
    description="获取 Bilibili 视频详情",
    http_path="/detail",
    http_methods=["POST"],
)(bili_tools.bili_detail)

bp.tool(
    "bili_creator",
    description="获取 Bilibili UP 主视频",
    http_path="/creator",
    http_methods=["POST"],
)(bili_tools.bili_creator)

bp.tool(
    "bili_search_time_range",
    description="按时间范围搜索 Bilibili 视频",
    http_path="/search/time-range",
    http_methods=["POST"],
)(bili_tools.bili_search_time_range)


def _to_tool_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """调整参数名称以匹配工具函数签名。"""
    adjusted = dict(params)
    if "enable_save_media" in adjusted:
        adjusted["save_media"] = adjusted.pop("enable_save_media")
    return adjusted


def _as_dict(result: str | Dict[str, Any]) -> Dict[str, Any]:
    """确保工具返回为 JSON 字典。"""
    if isinstance(result, dict):
        return result
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {"raw": result}


__all__ = ["bp"]
