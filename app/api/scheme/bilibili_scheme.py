# -*- coding: utf-8 -*-
"""
Bilibili 爬虫请求模型定义
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator


class _BaseCrawlerRequest(BaseModel):
    """公共字段基类"""

    headless: Optional[bool] = Field(default=None, description="是否启用无头浏览器")
    save_media: Optional[bool] = Field(default=None, description="是否保存媒体资源")
    options: Dict[str, Any] = Field(default_factory=dict, description="额外参数")

    model_config = ConfigDict(extra="forbid")

    def _collect_common_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if self.headless is not None:
            params["headless"] = self.headless

        extras = self.options.copy()
        if self.save_media is not None:
            extras.setdefault("enable_save_media", self.save_media)

        # 过滤掉 None 值
        params.update({k: v for k, v in extras.items() if v is not None})
        return params


class BiliSearchRequest(_BaseCrawlerRequest):
    """Bilibili 搜索请求"""

    keywords: str = Field(..., description="搜索关键词，多个关键词用逗号分隔")
    max_notes: int = Field(default=15, ge=1, description="最大作品数量")
    enable_comments: bool = Field(default=True, description="是否抓取评论")
    max_comments_per_note: int = Field(default=10, ge=0, description="单个作品最大评论数")

    @model_validator(mode="after")
    def validate_keywords(self) -> "BiliSearchRequest":
        cleaned = ",".join(filter(None, [kw.strip() for kw in self.keywords.split(",")]))
        if not cleaned:
            raise ValueError("keywords 不能为空")
        self.keywords = cleaned
        return self

    def to_service_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "keywords": self.keywords,
            "max_notes": self.max_notes,
            "enable_comments": self.enable_comments,
            "max_comments_per_note": self.max_comments_per_note,
        }
        params.update(self._collect_common_params())
        return params


class BiliDetailRequest(_BaseCrawlerRequest):
    """Bilibili 指定视频详情请求"""

    video_ids: List[str] = Field(..., min_length=1, description="视频ID列表（BV号或AV号）")
    enable_comments: bool = Field(default=True, description="是否抓取评论")
    max_comments_per_note: int = Field(default=10, ge=0, description="单个作品最大评论数")

    @model_validator(mode="after")
    def sanitize_ids(self) -> "BiliDetailRequest":
        cleaned = [vid.strip() for vid in self.video_ids if vid and vid.strip()]
        if not cleaned:
            raise ValueError("视频ID列表不能为空")
        self.video_ids = cleaned
        return self

    def to_service_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "video_ids": self.video_ids,
            "enable_comments": self.enable_comments,
            "max_comments_per_note": self.max_comments_per_note,
        }
        params.update(self._collect_common_params())
        return params


class BiliCreatorRequest(_BaseCrawlerRequest):
    """Bilibili 创作者内容请求"""

    creator_ids: List[str] = Field(..., min_length=1, description="创作者ID列表")
    enable_comments: bool = Field(default=True, description="是否抓取评论")
    max_comments_per_note: int = Field(default=10, ge=0, description="单个作品最大评论数")
    creator_mode: bool = Field(default=True, description="True=抓取作品，False=抓取创作者信息")

    @model_validator(mode="after")
    def sanitize_ids(self) -> "BiliCreatorRequest":
        cleaned = [cid.strip() for cid in self.creator_ids if cid and cid.strip()]
        if not cleaned:
            raise ValueError("创作者ID列表不能为空")
        self.creator_ids = cleaned
        return self

    def to_service_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "creator_ids": self.creator_ids,
            "enable_comments": self.enable_comments,
            "max_comments_per_note": self.max_comments_per_note,
            "creator_mode": self.creator_mode,
        }
        params.update(self._collect_common_params())
        return params


class BiliSearchTimeRangeRequest(BiliSearchRequest):
    """Bilibili 时间范围搜索请求"""

    start_day: str = Field(..., description="开始日期 YYYY-MM-DD")
    end_day: str = Field(..., description="结束日期 YYYY-MM-DD")
    max_notes_per_day: int = Field(default=50, ge=1, description="单日最大作品数量")
    daily_limit: bool = Field(default=False, description="是否严格限制总量")

    def to_service_params(self) -> Dict[str, Any]:
        params = super().to_service_params()
        params.update(
            {
                "start_day": self.start_day,
                "end_day": self.end_day,
                "max_notes_per_day": self.max_notes_per_day,
                "daily_limit": self.daily_limit,
            }
        )
        return params
