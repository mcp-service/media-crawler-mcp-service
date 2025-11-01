# -*- coding: utf-8 -*-
"""发布请求数据模型"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class PublishImageRequest(BaseModel):
    """发布图文请求"""
    title: str = Field(..., description="标题")
    content: str = Field(..., description="正文内容")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    image_paths: List[str] = Field(..., description="图片路径列表")


class PublishVideoRequest(BaseModel):
    """发布视频请求"""
    title: str = Field(..., description="标题")
    content: str = Field(..., description="正文内容")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    video_path: str = Field(..., description="视频文件路径")
    cover_path: Optional[str] = Field(None, description="封面图片路径")


class PublishStrategyRequest(BaseModel):
    """发布策略配置请求"""
    min_interval: int = Field(..., description="最小发布间隔(秒)")
    max_concurrent: int = Field(..., description="最大并发数")
    retry_count: int = Field(..., description="重试次数")
    retry_delay: int = Field(..., description="重试延迟(秒)")
    daily_limit: int = Field(..., description="每日发布限制")
    hourly_limit: int = Field(..., description="每小时发布限制")
