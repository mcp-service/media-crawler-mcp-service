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
from app.core.mcp import xhs as xhs_tools
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


@xhs_mcp.tool(
    name="search",
    description="小红书关键词搜索",
    tags={"xiaohongshu", "search"}
)
async def search(keywords: str, page_num: int = 1, page_size: int = 20):
    try:
        req = XhsSearchRequest.model_validate({
            "keywords": keywords,
            "page_num": page_num,
            "page_size": page_size
        })
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


@xhs_mcp.tool(
    name="crawler_detail",
    description="获取小红书笔记详情（必传：note_id, xsec_token；xsec_source 未传默认 pc_search）",
    tags={"xiaohongshu", "detail"}
)
async def crawler_detail(note_id: str, xsec_token: str, xsec_source: str = "pc_search"):
    try:
        req = XhsDetailRequest.model_validate({
            "note_id": note_id,
            "xsec_token": xsec_token,
            "xsec_source": xsec_source
        })
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


@xhs_mcp.tool(
    name="crawler_creator",
    description="获取小红书创作者作品",
    tags={"xiaohongshu", "creator"}
)
async def crawler_creator(creator_ids: list[str], save_media: bool = False):
    try:
        req = XhsCreatorRequest.model_validate({
            "creator_ids": creator_ids,
            "save_media": save_media
        })
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


@xhs_mcp.tool(
    name="crawler_comments",
    description="小红书笔记评论",
    tags={"xiaohongshu", "comments"}
)
async def crawler_comments(note_id: str, xsec_token: str, max_comments: int = 50):
    try:
        req = XhsCommentsRequest.model_validate({
            "note_id": note_id,
            "xsec_token": xsec_token,
            "max_comments": max_comments
        })
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
