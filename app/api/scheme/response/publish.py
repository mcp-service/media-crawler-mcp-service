# -*- coding: utf-8 -*-
"""发布响应数据模型"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class PublishResponse(BaseModel):
    """发布响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="发布状态")
    message: str = Field(default="", description="状态消息")
    note_url: Optional[str] = Field(None, description="发布成功后的笔记链接")
    error_detail: Optional[str] = Field(None, description="错误详情")


class PublishTaskStatus(BaseModel):
    """发布任务状态"""
    task_id: str = Field(..., description="任务ID")
    platform: str = Field(..., description="发布平台")
    content_type: str = Field(..., description="内容类型：image/video")
    status: str = Field(..., description="任务状态：pending/uploading/processing/success/failed")
    progress: int = Field(default=0, description="进度百分比")
    message: str = Field(default="", description="状态消息")
    note_url: Optional[str] = Field(None, description="发布成功后的笔记链接")
    created_at: float = Field(..., description="创建时间戳")
    updated_at: float = Field(..., description="更新时间戳")
