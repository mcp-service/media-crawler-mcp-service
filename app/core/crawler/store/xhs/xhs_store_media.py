# -*- coding: utf-8 -*-
"""Media storage helpers for Xiaohongshu."""

from __future__ import annotations

import pathlib
from typing import Dict

import aiofiles

from app.providers.logger import get_logger

logger = get_logger()


class XiaoHongShuImage:
    base_dir = pathlib.Path("data") / "xhs" / "images"

    async def store_image(self, payload: Dict) -> None:
        note_id = payload.get("notice_id")
        content = payload.get("pic_content")
        file_name = payload.get("extension_file_name", "0.jpg")
        if not note_id or content is None:
            return

        path = self.base_dir / str(note_id)
        path.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path / file_name, "wb") as fp:
            await fp.write(content)
        logger.info("[xhs.media] save image note_id=%s file=%s", note_id, file_name)


class XiaoHongShuVideo:
    base_dir = pathlib.Path("data") / "xhs" / "videos"

    async def store_video(self, payload: Dict) -> None:
        note_id = payload.get("notice_id")
        content = payload.get("video_content")
        file_name = payload.get("extension_file_name", "0.mp4")
        if not note_id or content is None:
            return

        path = self.base_dir / str(note_id)
        path.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path / file_name, "wb") as fp:
            await fp.write(content)
        logger.info("[xhs.media] save video note_id=%s file=%s", note_id, file_name)


__all__ = ["XiaoHongShuImage", "XiaoHongShuVideo"]
