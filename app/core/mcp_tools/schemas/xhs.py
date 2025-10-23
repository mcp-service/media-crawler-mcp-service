# -*- coding: utf-8 -*-
"""Pydantic schemas for Xiaohongshu MCP tools."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class XhsNoteBase(BaseModel):
    note_id: str = Field(..., description="笔记 ID")
    title: str = Field("", description="笔记标题")
    desc: str = Field("", description="笔记描述")
    type: str = Field("", description="笔记类型")
    time: Optional[int] = Field(None, description="发布时间")
    note_url: Optional[str] = Field(None, description="笔记 URL")
    user_id: Optional[str] = Field(None, description="作者 ID")
    nickname: Optional[str] = Field(None, description="作者昵称")
    avatar: Optional[str] = Field(None, description="作者头像 URL")
    liked_count: Optional[int] = Field(None, description="点赞数")
    comment_count: Optional[int] = Field(None, description="评论数")
    share_count: Optional[int] = Field(None, description="分享数")
    collected_count: Optional[int] = Field(None, description="收藏数")
    ip_location: Optional[str] = Field(None, description="IP 属地")


class XhsNoteDetail(XhsNoteBase):
    image_list: List[Dict[str, Any]] = Field(default_factory=list, description="图片列表")
    video_url: Optional[str] = Field(None, description="视频 URL 列表（逗号分隔）")
    tag_list: List[str] = Field(default_factory=list, description="标签列表")
    xsec_token: Optional[str] = Field(None, description="xsec token")
    xsec_source: Optional[str] = Field(None, description="xsec source")


class XhsNoteSearchResult(BaseModel):
    notes: List[XhsNoteDetail] = Field(default_factory=list, description="笔记列表")
    total_count: int = Field(0, description="笔记数量")
    crawl_info: Dict[str, Any] = Field(default_factory=dict, description="爬虫信息")


class XhsCommentsResult(BaseModel):
    comments: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict, description="评论映射")
    total_count: int = Field(0, description="评论数量")
    crawl_info: Dict[str, Any] = Field(default_factory=dict, description="爬虫信息")
