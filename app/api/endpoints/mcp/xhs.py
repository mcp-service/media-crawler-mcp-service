# -*- coding: utf-8 -*-
"""Xiaohongshu MCP endpoints and tool registrations."""

from __future__ import annotations

import json
from typing import Any, Dict

from pydantic import ValidationError
from fastmcp import FastMCP
from app.api.scheme import error_codes
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

xhs_mcp = FastMCP(name="小红书MCP")

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


@xhs_mcp.tool(description="小红书关键词搜索")
async def search(request):
    payload = await _safe_json(request)
    try:
        req = XhsSearchRequest.model_validate(payload)
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        result = await xhs_tools.xhs_search(**req.to_service_params())
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
        logger.error(f"[xhs.search] failed: {exc}")
        return _server_error(f"小红书搜索失败: {exc}")


@xhs_mcp.tool(description="获取小红书笔记详情（必传：node_id, xsec_token；xsec_source 未传默认 pc_search）")
async def crawler_detail(request):
    payload = await _safe_json(request)
    try:
        req = XhsDetailRequest.model_validate(payload)
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        result = await xhs_tools.xhs_detail(**req.to_service_params())
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
    except Exception as exc:
        logger.error(f"[xhs.detail] failed: {exc}")
        return _server_error(f"小红书详情抓取失败: {exc}")


@xhs_mcp.tool(description="获取小红书创作者作品")
async def crawler_creator(request):
    payload = await _safe_json(request)
    try:
        req = XhsCreatorRequest.model_validate(payload)
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        result = await xhs_tools.xhs_creator(**req.to_service_params())
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
    except Exception as exc:
        logger.error("[xhs.creator] failed: %s", exc)
        return _server_error(f"小红书创作者抓取失败: {exc}")


@xhs_mcp.tool(description="小红书笔记评论")
async def crawler_comments(request):
    payload = await _safe_json(request)
    try:
        req = XhsCommentsRequest.model_validate(payload)
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        result = await xhs_tools.xhs_comments(**req.to_service_params())
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
    except Exception as exc:
        logger.error("[xhs.comments] failed: %s", exc)
        return _server_error(f"小红书评论抓取失败: {exc}")


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


__all__ = ["xhs_mcp"]
