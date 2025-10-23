# -*- coding: utf-8 -*-
"""High level store helpers for Xiaohongshu."""

from __future__ import annotations

import json
from typing import Dict, List, Optional

import httpx

from app.config.settings import global_settings
from app.core.crawler.tools import time_util
from app.providers.logger import get_logger

from .store_impl import (
    XhsCsvStoreImplement,
    XhsDbStoreImplement,
    XhsJsonStoreImplement,
    XhsSqliteStoreImplement,
)
from .xhs_store_media import XiaoHongShuImage, XiaoHongShuVideo

logger = get_logger()


class XhsStoreFactory:
    STORES = {
        "json": XhsJsonStoreImplement,
        "csv": XhsCsvStoreImplement,
        "db": XhsDbStoreImplement,
        "sqlite": XhsSqliteStoreImplement,
    }

    @classmethod
    def create_store(cls, *, crawler_type: str = "general"):
        save_format = str(getattr(global_settings.store.save_format, "value", global_settings.store.save_format))
        store_cls = cls.STORES.get(save_format, XhsJsonStoreImplement)
        if store_cls in (XhsDbStoreImplement, XhsSqliteStoreImplement):
            logger.warning("[xhs.store] %s 未实现，fallback 到 JSON", save_format)
            store_cls = XhsJsonStoreImplement
        return store_cls(crawler_type=crawler_type)


async def update_xhs_note(note_item: Dict) -> None:
    user_info = note_item.get("user", {})
    interact_info = note_item.get("interact_info", {})
    image_list = note_item.get("image_list") or []
    tag_list = note_item.get("tag_list") or []

    for image in image_list:
        if image.get("url_default"):
            image["url"] = image["url_default"]

    record = {
        "note_id": note_item.get("note_id"),
        "type": note_item.get("type"),
        "title": note_item.get("title") or note_item.get("desc", "")[:255],
        "desc": note_item.get("desc", ""),
        "time": note_item.get("time"),
        "last_update_time": note_item.get("last_update_time", 0),
        "user_id": user_info.get("user_id"),
        "nickname": user_info.get("nickname"),
        "avatar": user_info.get("avatar"),
        "liked_count": interact_info.get("liked_count"),
        "collected_count": interact_info.get("collected_count"),
        "comment_count": interact_info.get("comment_count"),
        "share_count": interact_info.get("share_count"),
        "ip_location": note_item.get("ip_location"),
        "image_list": ",".join(img.get("url", "") for img in image_list),
        "tag_list": ",".join(tag.get("name", "") for tag in tag_list if tag.get("type") == "topic"),
        "video_url": ",".join(get_video_url_list(note_item)),
        "last_modify_ts": time_util.get_current_timestamp(),
        "note_url": f"https://www.xiaohongshu.com/explore/{note_item.get('note_id')}",
        "xsec_token": note_item.get("xsec_token"),
    }

    store = XhsStoreFactory.create_store()
    await store.store_content(record)


async def update_xhs_note_media(note_item: Dict) -> None:
    if not global_settings.store.enable_save_media:
        return
    await get_note_images(note_item)
    await get_note_videos(note_item)


async def batch_update_xhs_note_comments(note_id: str, comments: List[Dict]) -> None:
    if not comments:
        return
    store = XhsStoreFactory.create_store()
    for comment in comments:
        await update_xhs_note_comment(store, note_id, comment)


async def update_xhs_note_comment(store, note_id: str, comment_item: Dict) -> None:
    user_info = comment_item.get("user_info", {})
    target_comment = comment_item.get("target_comment", {})
    pictures = [pic.get("url_default", "") for pic in comment_item.get("pictures", [])]

    record = {
        "comment_id": comment_item.get("id"),
        "note_id": note_id,
        "content": comment_item.get("content"),
        "create_time": comment_item.get("create_time"),
        "ip_location": comment_item.get("ip_location"),
        "user_id": user_info.get("user_id"),
        "nickname": user_info.get("nickname"),
        "avatar": user_info.get("image"),
        "sub_comment_count": comment_item.get("sub_comment_count", 0),
        "parent_comment_id": target_comment.get("id", 0),
        "pictures": ",".join(pictures),
        "last_modify_ts": time_util.get_current_timestamp(),
        "like_count": comment_item.get("like_count", 0),
    }
    await store.store_comment(record)


async def save_creator(user_id: str, creator: Dict) -> None:
    store = XhsStoreFactory.create_store()
    basic = creator.get("basicInfo", {}) if creator else {}
    interactions = {item.get("type"): item.get("count") for item in creator.get("interactions", [])} if creator else {}
    tags = {
        tag.get("tagType"): tag.get("name")
        for tag in (creator.get("tags") or [])
        if tag.get("tagType")
    }

    record = {
        "user_id": user_id,
        "nickname": basic.get("nickname"),
        "gender": basic.get("gender"),
        "avatar": basic.get("images"),
        "desc": basic.get("desc"),
        "ip_location": basic.get("ipLocation"),
        "follows": interactions.get("follows"),
        "fans": interactions.get("fans"),
        "interaction": interactions.get("interaction"),
        "tag_list": json.dumps(tags, ensure_ascii=False),
        "last_modify_ts": time_util.get_current_timestamp(),
    }
    await store.store_creator(record)


async def get_note_images(note_item: Dict) -> None:
    image_list = note_item.get("image_list") or []
    image_store = XiaoHongShuImage()
    for index, pic in enumerate(image_list):
        url = pic.get("url") or pic.get("url_size_large")
        if not url:
            continue
        content = await _download_binary(url)
        if content is None:
            continue
        await image_store.store_image(
            {
                "notice_id": note_item.get("note_id"),
                "pic_content": content,
                "extension_file_name": f"{index}.jpg",
            }
        )


async def get_note_videos(note_item: Dict) -> None:
    videos = get_video_url_list(note_item)
    video_store = XiaoHongShuVideo()
    for index, url in enumerate(videos):
        content = await _download_binary(url)
        if content is None:
            continue
        await video_store.store_video(
            {
                "notice_id": note_item.get("note_id"),
                "video_content": content,
                "extension_file_name": f"{index}.mp4",
            }
        )


def get_video_url_list(note_item: Dict) -> List[str]:
    if note_item.get("type") != "video":
        return []
    consumer = note_item.get("video", {}).get("consumer", {})
    origin_key = consumer.get("origin_video_key") or consumer.get("originVideoKey")
    if origin_key:
        return [f"http://sns-video-bd.xhscdn.com/{origin_key}"]
    streams = note_item.get("video", {}).get("media", {}).get("stream", {}).get("h264")
    if isinstance(streams, list):
        return [stream.get("master_url", "") for stream in streams if stream.get("master_url")]
    return []


async def _download_binary(url: str) -> Optional[bytes]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30)
            if response.status_code == 200:
                return response.content
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("[xhs.store] download media failed url=%s err=%s", url, exc)
    return None
