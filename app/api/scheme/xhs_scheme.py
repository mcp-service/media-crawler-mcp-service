# -*- coding: utf-8 -*-
"""Xiaohongshu request models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _XhsBaseRequest(BaseModel):
    headless: Optional[bool] = Field(None, description="是否使用无头浏览器")
    save_media: Optional[bool] = Field(None, description="是否保存媒体资源")
    options: Dict[str, Any] = Field(default_factory=dict, description="额外参数")

    model_config = ConfigDict(extra="forbid")

    def to_common_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if self.headless is not None:
            params["headless"] = self.headless

        extras = dict(self.options)
        if self.save_media is not None:
            extras.setdefault("enable_save_media", self.save_media)

        params.update({k: v for k, v in extras.items() if v is not None})
        return params


class XhsSearchRequest(_XhsBaseRequest):
    keywords: str = Field(..., description="搜索关键词，多个关键词用逗号分隔", examples=["美食,旅游", "护肤"])
    page_num: int = Field(1, ge=1, description="页码，从1开始", examples=[1, 2])
    page_size: int = Field(20, ge=1, le=50, description="每页数量", examples=[20, 30])

    @model_validator(mode="after")
    def validate_keywords(self) -> "XhsSearchRequest":
        cleaned = ",".join(filter(None, (part.strip() for part in self.keywords.split(","))))
        if not cleaned:
            raise ValueError("keywords 不能为空")
        self.keywords = cleaned
        return self

    def to_service_params(self) -> Dict[str, Any]:
        params = {
            "keywords": self.keywords,
        }
        params.update(self.to_common_params())
        # 添加分页参数到 extra
        extra = params.setdefault("options", {})
        extra["page_num"] = self.page_num
        extra["page_size"] = self.page_size
        return params


class XhsDetailRequest(_XhsBaseRequest):
    note_urls: List[str] = Field(..., min_length=1, description="笔记 URL 或 note_id 列表", examples=[["https://www.xiaohongshu.com/explore/12345"], ["https://www.xiaohongshu.com/explore/12345", "https://www.xiaohongshu.com/explore/67890"]])
    enable_comments: bool = Field(True, description="是否抓取评论", examples=[True, False])
    max_comments_per_note: int = Field(50, ge=0, description="单条笔记最大评论数", examples=[50, 100])

    @model_validator(mode="after")
    def sanitize_urls(self) -> "XhsDetailRequest":
        cleaned = [item.strip() for item in self.note_urls if item and item.strip()]
        if not cleaned:
            raise ValueError("note_urls 不能为空")
        self.note_urls = cleaned
        return self

    def to_service_params(self) -> Dict[str, Any]:
        params = {
            "note_urls": self.note_urls,
            "enable_comments": self.enable_comments,
            "max_comments_per_note": self.max_comments_per_note,
        }
        params.update(self.to_common_params())
        return params


class XhsCreatorRequest(_XhsBaseRequest):
    creator_ids: List[str] = Field(..., min_length=1, description="创作者 ID 或主页 URL 列表", examples=[["user123"], ["user123", "user456"]])
    enable_comments: bool = Field(False, description="是否抓取评论", examples=[False, True])
    max_comments_per_note: int = Field(0, ge=0, description="单条笔记最大评论数", examples=[0, 20])

    @model_validator(mode="after")
    def sanitize_ids(self) -> "XhsCreatorRequest":
        cleaned = [item.strip() for item in self.creator_ids if item and item.strip()]
        if not cleaned:
            raise ValueError("creator_ids 不能为空")
        self.creator_ids = cleaned
        return self

    def to_service_params(self) -> Dict[str, Any]:
        params = {
            "creator_ids": self.creator_ids,
            "enable_comments": self.enable_comments,
            "max_comments_per_note": self.max_comments_per_note,
        }
        params.update(self.to_common_params())
        return params


class XhsCommentsRequest(_XhsBaseRequest):
    note_urls: List[str] = Field(..., min_length=1, description="笔记 URL 或 note_id 列表", examples=[["https://www.xiaohongshu.com/explore/12345"], ["https://www.xiaohongshu.com/explore/12345", "https://www.xiaohongshu.com/explore/67890"]])
    max_comments: int = Field(50, ge=1, description="单条笔记最大评论数", examples=[50, 100])

    @model_validator(mode="after")
    def sanitize_urls(self) -> "XhsCommentsRequest":
        cleaned = [item.strip() for item in self.note_urls if item and item.strip()]
        if not cleaned:
            raise ValueError("note_urls 不能为空")
        self.note_urls = cleaned
        return self

    def to_service_params(self) -> Dict[str, Any]:
        params = {
            "note_urls": self.note_urls,
            "max_comments": self.max_comments,
        }
        params.update(self.to_common_params())
        return params
