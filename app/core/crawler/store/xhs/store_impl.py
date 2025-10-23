# -*- coding: utf-8 -*-
"""Storage implementations for Xiaohongshu crawler."""

from __future__ import annotations

from typing import Dict

from app.config.settings import Platform
from app.core.crawler.tools.async_file_writer import AsyncFileWriter


class _BaseFileStore:
    def __init__(self, crawler_type: str = "general") -> None:
        self.file_writer = AsyncFileWriter(
            platform=Platform.XIAOHONGSHU.value,
            crawler_type=crawler_type or "general",
        )


class XhsJsonStoreImplement(_BaseFileStore):
    async def store_content(self, content_item: Dict) -> None:
        await self.file_writer.write_single_item_to_json(content_item, item_type="contents")

    async def store_comment(self, comment_item: Dict) -> None:
        await self.file_writer.write_single_item_to_json(comment_item, item_type="comments")

    async def store_creator(self, creator: Dict) -> None:
        await self.file_writer.write_single_item_to_json(creator, item_type="creators")


class XhsCsvStoreImplement(_BaseFileStore):
    async def store_content(self, content_item: Dict) -> None:
        await self.file_writer.write_to_csv(content_item, item_type="contents")

    async def store_comment(self, comment_item: Dict) -> None:
        await self.file_writer.write_to_csv(comment_item, item_type="comments")

    async def store_creator(self, creator: Dict) -> None:
        await self.file_writer.write_to_csv(creator, item_type="creators")


class XhsDbStoreImplement:
    """Placeholder for future DB support."""

    def __init__(self, *args, **kwargs) -> None:  # noqa: D401
        raise NotImplementedError("database storage 尚未实现")

    async def store_content(self, content_item: Dict) -> None:  # pragma: no cover - defensive
        raise NotImplementedError

    async def store_comment(self, comment_item: Dict) -> None:  # pragma: no cover - defensive
        raise NotImplementedError

    async def store_creator(self, creator: Dict) -> None:  # pragma: no cover - defensive
        raise NotImplementedError


class XhsSqliteStoreImplement(XhsDbStoreImplement):
    """Placeholder for SQLite support."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
