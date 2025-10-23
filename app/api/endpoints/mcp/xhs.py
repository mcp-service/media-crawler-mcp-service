# -*- coding: utf-8 -*-
"""Xiaohongshu MCP endpoints and tool registrations."""

from __future__ import annotations

import json
from typing import Any, Dict

from pydantic import ValidationError
from starlette.responses import JSONResponse

from app.api.endpoints.base import MCPBlueprint
from app.api.scheme import error_codes, jsonify_response
from app.api.scheme.request.xhs_scheme import (
    XhsCommentsRequest,
    XhsCreatorRequest,
    XhsDetailRequest,
    XhsSearchRequest,
)
from app.config.settings import Platform
from app.core.mcp_tools import xhs as xhs_tools
from app.core.login.exceptions import LoginExpiredError
from app.providers.logger import get_logger

logger = get_logger()
bp = MCPBlueprint(
    prefix=f"/{Platform.XIAOHONGSHU.value}",
    name=Platform.XIAOHONGSHU.value,
    tags=["xhs"],
    category=Platform.XIAOHONGSHU.value,
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
async def xhs_search_http(request):
    payload = await _safe_json(request)
    try:
        req = XhsSearchRequest.model_validate(payload)
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        result = await xhs_tools.xhs_search(**req.to_service_params())
        return jsonify_response(_as_dict(result))
    except LoginExpiredError:
        return jsonify_response({}, status_response=(error_codes.INVALID_TOKEN[0], "登录过期，Cookie失效"))
    except Exception as exc:  # pragma: no cover - runtime safeguard
        logger.error(f"[xhs.search] failed: {exc}")
        return _server_error(f"小红书搜索失败: {exc}")


@bp.route("/detail", methods=["POST"])
async def xhs_detail_http(request):
    payload = await _safe_json(request)
    try:
        req = XhsDetailRequest.model_validate(payload)
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        result = await xhs_tools.xhs_detail(**req.to_service_params())
        return jsonify_response(_as_dict(result))
    except LoginExpiredError:
        return jsonify_response({}, status_response=(error_codes.INVALID_TOKEN[0], "登录过期，Cookie失效"))
    except Exception as exc:
        logger.error(f"[xhs.detail] failed: {exc}")
        return _server_error(f"小红书详情抓取失败: {exc}")


@bp.route("/creator", methods=["POST"])
async def xhs_creator_http(request):
    payload = await _safe_json(request)
    try:
        req = XhsCreatorRequest.model_validate(payload)
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        result = await xhs_tools.xhs_creator(**req.to_service_params())
        return jsonify_response(_as_dict(result))
    except LoginExpiredError:
        return jsonify_response({}, status_response=(error_codes.INVALID_TOKEN[0], "登录过期，Cookie失效"))
    except Exception as exc:
        logger.error("[xhs.creator] failed: %s", exc)
        return _server_error(f"小红书创作者抓取失败: {exc}")


@bp.route("/comments", methods=["POST"])
async def xhs_comments_http(request):
    payload = await _safe_json(request)
    try:
        req = XhsCommentsRequest.model_validate(payload)
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        result = await xhs_tools.xhs_comments(**req.to_service_params())
        return jsonify_response(_as_dict(result))
    except LoginExpiredError:
        return jsonify_response({}, status_response=(error_codes.INVALID_TOKEN[0], "登录过期，Cookie失效"))
    except Exception as exc:
        logger.error("[xhs.comments] failed: %s", exc)
        return _server_error(f"小红书评论抓取失败: {exc}")


bp.tool(
    "xhs_search",
    description="小红书关键词搜索",
    http_path="/search",
    http_methods=["POST"],
)(xhs_tools.xhs_search)

bp.tool(
    "xhs_detail",
    description="小红书笔记详情（必传：node_id, xsec_token；xsec_source 未传默认 pc_search）",
    http_path="/detail",
    http_methods=["POST"],
)(xhs_tools.xhs_detail)

bp.tool(
    "xhs_creator",
    description="小红书创作者作品",
    http_path="/creator",
    http_methods=["POST"],
)(xhs_tools.xhs_creator)

bp.tool(
    "xhs_comments",
    description="小红书笔记评论",
    http_path="/comments",
    http_methods=["POST"],
)(xhs_tools.xhs_comments)


async def _safe_json(request) -> Dict[str, Any]:
    try:
        return await request.json()
    except Exception:
        return {}


def _as_dict(result: str | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(result, dict):
        return result
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {"raw": result}


__all__ = ["bp"]
