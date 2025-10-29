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
    XhsPublishRequest,
    XhsPublishVideoRequest,
)
from app.config.settings import Platform, global_settings
from app.core.crawler.platforms import xhs as xhs_core
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
        # 直接实例化Crawler调用方法
        crawler = xhs_core.XiaoHongShuCrawler(
            headless=global_settings.browser.headless,
            enable_save_media=False,
            extra={"no_auto_login": True}
        )
        await crawler._ensure_browser_and_client()

        result = await crawler.search_by_keywords(
            keywords=req.keywords,
            max_notes=req.page_size,
            page_size=req.page_size,
            crawl_interval=1.0,
            enable_save=False,
        )

        await crawler.close()

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
        # 直接实例化Crawler调用方法
        crawler = xhs_core.XiaoHongShuCrawler(
            headless=global_settings.browser.headless,
            enable_save_media=False,
            extra={"no_auto_login": True}
        )
        await crawler._ensure_browser_and_client()

        note_items = [{
            "note_id": req.note_id,
            "xsec_token": req.xsec_token,
            "xsec_source": req.xsec_source or "",
        }]

        result = await crawler.get_detail(
            note_ids=note_items,
            max_concurrency=1,
            enable_get_comments=False,
            enable_save_media=False,
        )

        await crawler.close()

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
        # 直接实例化Crawler调用方法
        crawler = xhs_core.XiaoHongShuCrawler(
            headless=global_settings.browser.headless,
            enable_save_media=req.save_media,
            extra={"no_auto_login": True}
        )
        await crawler._ensure_browser_and_client()

        result = await crawler.get_creator(
            creator_ids=req.creator_ids,
            max_notes=None,
            enable_get_comments=False,
            enable_save_media=req.save_media,
            crawl_interval=1.0,
        )

        await crawler.close()

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
    except Exception as exc:
        logger.error(f"[xhs.creator] failed: {exc}")
        return _server_error(f"小红书创作者抓取失败: {exc}")


@xhs_mcp.tool(
    name="crawler_comments",
    description="小红书笔记评论(必传: note_id, xsec_token)",
    tags={"xiaohongshu", "comments"}
)
async def crawler_comments(note_id: str, xsec_token: str, xsec_source: str = "", max_comments: int = 50):
    try:
        req = XhsCommentsRequest.model_validate({
            "note_id": note_id,
            "xsec_token": xsec_token,
            "xsec_source": xsec_source or "",
            "max_comments": max_comments
        })
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        # 直接实例化Crawler调用方法
        crawler = xhs_core.XiaoHongShuCrawler(
            headless=global_settings.browser.headless,
            extra={"no_auto_login": True}
        )
        await crawler._ensure_browser_and_client()

        note_items = [{
            "note_id": req.note_id,
            "xsec_token": req.xsec_token,
            "xsec_source": req.xsec_source or "",
        }]

        result = await crawler.fetch_comments(
            note_items=note_items,
            max_concurrency=1,
            crawl_interval=1.0,
            max_comments_per_note=req.max_comments,
        )

        await crawler.close()

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
    except Exception as exc:
        logger.error(f"[xhs.comments] failed: {exc}")
        return _server_error(f"小红书评论抓取失败: {exc}")


@xhs_mcp.tool(
    name="publish_image",
    description="发布小红书图文内容",
    tags={"xiaohongshu", "publish"}
)
async def publish_image(title: str, content: str, images: list[str], tags: list[str] | None = None):
    try:
        req = XhsPublishRequest.model_validate({
            "title": title,
            "content": content,
            "images": images,
            "tags": tags or [],
        })
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        # 直接实例化Crawler调用方法
        crawler = xhs_core.XiaoHongShuCrawler(
            headless=global_settings.browser.headless,
            extra={"no_auto_login": True}
        )
        await crawler._ensure_browser_and_client()

        # Import and use publisher
        from app.core.crawler.platforms.xhs.publish import XhsPublisher

        publisher = XhsPublisher(
            page=crawler.context_page,
        )

        result = await publisher.publish_image_post(
            title=req.title,
            content=req.content,
            images=req.images,
            tags=req.tags or [],
        )

        await crawler.close()

        return {
            "code": error_codes.SUCCESS[0],
            "msg": error_codes.SUCCESS[1],
            "data": {
                "success": result.get("success", False),
                "message": result.get("message", ""),
            },
        }
    except LoginExpiredError:
        return {
            "code": error_codes.INVALID_TOKEN[0],
            "msg": "登录过期，Cookie失效",
            "data": {},
        }
    except Exception as exc:
        logger.error(f"[xhs.publish] failed: {exc}")
        return _server_error(f"小红书发布失败: {exc}")


@xhs_mcp.tool(
    name="publish_video",
    description="发布小红书视频内容",
    tags={"xiaohongshu", "publish"}
)
async def publish_video(title: str, content: str, video: str, tags: list[str] | None = None):
    try:
        req = XhsPublishVideoRequest.model_validate({
            "title": title,
            "content": content,
            "video": video,
            "tags": tags or [],
        })
    except ValidationError as exc:
        return _validation_error(exc)

    try:
        # 直接实例化Crawler调用方法
        crawler = xhs_core.XiaoHongShuCrawler(
            headless=global_settings.browser.headless,
            extra={"no_auto_login": True}
        )
        await crawler._ensure_browser_and_client()

        # Import and use publisher
        from app.core.crawler.platforms.xhs.publish import XhsPublisher

        publisher = XhsPublisher(
            page=crawler.context_page,
        )

        result = await publisher.publish_video_post(
            title=req.title,
            content=req.content,
            video=req.video,
            tags=req.tags or [],
        )

        await crawler.close()

        return {
            "code": error_codes.SUCCESS[0],
            "msg": error_codes.SUCCESS[1],
            "data": {
                "success": result.get("success", False),
                "message": result.get("message", ""),
            },
        }
    except LoginExpiredError:
        return {
            "code": error_codes.INVALID_TOKEN[0],
            "msg": "登录过期，Cookie失效",
            "data": {},
        }
    except Exception as exc:
        logger.error(f"[xhs.publish_video] failed: {exc}")
        return _server_error(f"小红书发布视频失败: {exc}")


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
