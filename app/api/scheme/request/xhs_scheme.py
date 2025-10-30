# -*- coding: utf-8 -*-
"""Xiaohongshu request models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _XhsBaseRequest(BaseModel):
    headless: Optional[bool] = Field(None, description="是否使用无头浏览器")
    save_media: Optional[bool] = Field(None, description="是否保存媒体资源")

    model_config = ConfigDict(extra="forbid")

    def to_common_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if self.headless is not None:
            params["headless"] = self.headless

        if self.save_media is not None:
            params["save_media"] = self.save_media

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
            "page_num": self.page_num,
            "page_size": self.page_size,
        }
        params.update(self.to_common_params())
        return params


class XhsDetailRequest(_XhsBaseRequest):
    # 注意：接口不做向后兼容；xsec_token 必传
    note_id: str = Field(..., description="笔记ID")
    xsec_token: str = Field(..., description="xsec token（必传，来自搜索或分享链接）")
    xsec_source: Optional[str] = Field(default="", description="xsec source（可选，未传默认 pc_search）")

    @model_validator(mode="after")
    def sanitize(self) -> "XhsDetailRequest":
        self.note_id = self.note_id.strip()
        if not self.note_id:
            raise ValueError("node_id 不能为空")
        self.xsec_token = (self.xsec_token or "").strip()
        if not self.xsec_token:
            raise ValueError("xsec_token 不能为空")
        return self

    def to_service_params(self) -> Dict[str, Any]:
        params = {
            "note_id": self.note_id,
            "xsec_token": self.xsec_token,
            "xsec_source": self.xsec_source or "",
        }
        params.update(self.to_common_params())
        return params


class XhsCreatorRequest(_XhsBaseRequest):
    creator_id: str = Field(..., description="创作者id")
    page_num: int = Field(default=1, ge=1, description="页码，从1开始")
    page_size: int = Field(default=10, ge=1, le=50, description="每页数量")

    @model_validator(mode="after")
    def sanitize_ids(self) -> "XhsCreatorRequest":
        self.creator_id = self.creator_id.strip()
        if not self.creator_id:
            raise ValueError("creator_ids 不能为空")
        return self


class XhsCommentsRequest(_XhsBaseRequest):
    note_id: str = Field(..., description="笔记ID")
    xsec_token: str = Field(..., description="xsec token（必传，从搜索结果获取）")
    xsec_source: Optional[str] = Field(default="", description="xsec source（可选，未传默认 pc_search）")
    page_num: int = Field(default=1, ge=1, description="页码，从1开始")
    page_size: int = Field(default=10, ge=1, le=50, description="每页数量")

    @model_validator(mode="after")
    def sanitize(self) -> "XhsCommentsRequest":
        self.note_id = self.note_id.strip()
        if not self.note_id:
            raise ValueError("note_id 不能为空")
        self.xsec_token = (self.xsec_token or "").strip()
        if not self.xsec_token:
            raise ValueError("xsec_token 不能为空")
        return self

    def to_service_params(self) -> Dict[str, Any]:
        params = {
            "note_id": self.note_id,
            "xsec_token": self.xsec_token,
            "xsec_source": self.xsec_source or "",
            "max_comments": self.max_comments,
        }
        params.update(self.to_common_params())
        return params


class XhsPublishRequest(_XhsBaseRequest):
    title: str = Field(..., description="标题")
    content: str = Field("", description="正文内容")
    images: List[str] = Field(..., min_length=1, description="图片绝对路径列表")
    tags: Optional[List[str]] = Field(default=None, description="标签列表，最多10个")

    def to_service_params(self) -> Dict[str, Any]:
        params = {
            "title": self.title,
            "content": self.content,
            "images": self.images,
            "tags": self.tags or [],
        }
        params.update(self.to_common_params())
        return params


class XhsPublishVideoRequest(_XhsBaseRequest):
    title: str = Field(..., description="标题")
    content: str = Field("", description="正文内容")
    video: str = Field(..., description="视频绝对路径")
    tags: Optional[List[str]] = Field(default=None, description="标签列表，最多10个")

    def to_service_params(self) -> Dict[str, Any]:
        params = {
            "title": self.title,
            "content": self.content,
            "video": self.video,
            "tags": self.tags or [],
        }
        params.update(self.to_common_params())
        return params
