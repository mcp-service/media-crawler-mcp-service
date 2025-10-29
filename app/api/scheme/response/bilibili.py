# -*- coding: utf-8 -*-
"""Bilibili MCP 工具的数据模型定义"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class BilibiliVideoBase(BaseModel):
    """Bilibili 视频基础信息模型"""
    video_id: str = Field(..., description="视频 ID")
    title: str = Field(..., description="视频标题")
    desc: str = Field(default="", description="视频描述")
    create_time: Optional[int] = Field(None, description="发布时间戳")
    user_id: str = Field(..., description="用户 ID")
    nickname: str = Field(..., description="用户昵称")
    video_play_count: str = Field(default="0", description="播放量")
    liked_count: str = Field(default="0", description="点赞数")
    video_comment: str = Field(default="0", description="评论数")
    video_url: str = Field(..., description="视频链接")
    video_cover_url: str = Field(default="", description="封面图片链接")
    source_keyword: str = Field(default="", description="搜索关键词")


class BilibiliVideoSimple(BilibiliVideoBase):
    """简化的 Bilibili 视频信息（用于搜索结果）"""
    desc: str = Field(default="", max_length=200, description="视频描述（限制200字符）")
    
    @classmethod
    def from_full_video(cls, video_data: dict) -> 'BilibiliVideoSimple':
        """从完整视频数据创建简化版本"""
        desc = video_data.get("desc", "")
        if len(desc) > 200:
            desc = desc[:200] + "..."
            
        return cls(
            video_id=video_data.get("video_id", ""),
            title=video_data.get("title", ""),
            desc=desc,
            create_time=video_data.get("create_time"),
            user_id=video_data.get("user_id", ""),
            nickname=video_data.get("nickname", ""),
            video_play_count=video_data.get("video_play_count", "0"),
            liked_count=video_data.get("liked_count", "0"),
            video_comment=video_data.get("video_comment", "0"),
            video_url=video_data.get("video_url", ""),
            video_cover_url=video_data.get("video_cover_url", ""),
            source_keyword=video_data.get("source_keyword", ""),
        )


class TagInfo(BaseModel):
    """标签信息"""
    tag_id: Optional[int] = Field(None, description="标签 ID")
    tag_name: Optional[str] = Field(None, description="标签名称")


class BilibiliVideoFull(BilibiliVideoBase):
    """完整的 Bilibili 视频信息（用于详情获取）"""
    # 视频标识
    bvid: str = Field(default="", description="视频 BV 号")

    # 时间与时长
    duration: Optional[int] = Field(None, description="视频时长（秒）")

    # 分区信息
    tname: str = Field(default="", description="分区名称")
    tid: Optional[int] = Field(None, description="分区 ID")

    # 视频属性
    copyright: Optional[int] = Field(None, description="版权标识（1原创 2转载）")
    cid: Optional[int] = Field(None, description="视频 CID")

    # UP主基础信息
    avatar: str = Field(default="", description="用户头像")

    # UP主详细信息（从 Card 获取）
    user_sex: str = Field(default="", description="用户性别")
    user_sign: str = Field(default="", description="用户个性签名")
    user_level: Optional[int] = Field(None, description="用户等级")
    user_fans: Optional[int] = Field(None, description="粉丝数")
    user_official_verify: Optional[int] = Field(None, description="官方认证类型")

    # 统计数据（详细）
    disliked_count: str = Field(default="0", description="踩数")
    coin_count: str = Field(default="0", description="投币数")
    share_count: str = Field(default="0", description="分享数")
    favorite_count: str = Field(default="0", description="收藏数")
    danmaku_count: str = Field(default="0", description="弹幕数")

    # 标签列表
    tags: List[TagInfo] = Field(default_factory=list, description="视频标签列表")

    # 兼容旧字段名
    video_favorite_count: str = Field(default="0", description="收藏数（兼容字段）")
    video_share_count: str = Field(default="0", description="分享数（兼容字段）")
    video_coin_count: str = Field(default="0", description="投币数（兼容字段）")
    video_danmaku: str = Field(default="0", description="弹幕数（兼容字段）")

    # 其他
    last_modify_ts: Optional[int] = Field(None, description="最后修改时间戳")
    video_type: str = Field(default="video", description="视频类型")


class BilibiliSearchResult(BaseModel):
    """Bilibili 搜索结果"""
    videos: List[BilibiliVideoSimple] = Field(default_factory=list, description="视频列表")
    total_count: Optional[int] = Field(None, description="总数量")
    keywords: str = Field(default="", description="搜索关键词")
    crawl_info: dict = Field(default_factory=dict, description="爬虫信息")


class BilibiliDetailResult(BaseModel):
    """Bilibili 详情结果"""
    videos: List[BilibiliVideoFull] = Field(default_factory=list, description="视频列表")
    total_count: Optional[int] = Field(None, description="总数量")
    crawl_info: dict = Field(default_factory=dict, description="爬虫信息")


class BilibiliComment(BaseModel):
    """Bilibili 评论模型 - 使用Pydantic验证器处理原始数据"""
    comment_id: str = Field(..., description="评论 ID")
    parent_comment_id: str = Field(default="0", description="父评论 ID")
    create_time: Optional[int] = Field(None, description="评论时间戳")
    video_id: str = Field(..., description="视频 ID")
    content: str = Field(..., description="评论内容")
    user_id: Optional[str] = Field(None, description="用户 ID")
    nickname: Optional[str] = Field(None, description="用户昵称")
    sex: Optional[str] = Field(None, description="性别")
    sign: Optional[str] = Field(None, description="个性签名")
    avatar: Optional[str] = Field(None, description="头像")
    sub_comment_count: str = Field(default="0", description="子评论数")
    like_count: int = Field(default=0, description="点赞数")

    # 原始数据字段，用于内部处理
    rpid: Optional[Any] = Field(None, exclude=True)  # 原始评论ID
    parent: Optional[Any] = Field(None, exclude=True)  # 原始父评论ID
    ctime: Optional[Any] = Field(None, exclude=True)  # 原始时间戳
    member: Optional[Dict[str, Any]] = Field(None, exclude=True)  # 原始用户数据
    content_data: Optional[Dict[str, Any]] = Field(None, exclude=True)  # 原始内容数据
    rcount: Optional[Any] = Field(None, exclude=True)  # 原始回复数
    like: Optional[Any] = Field(None, exclude=True)  # 原始点赞数

    @model_validator(mode='before')
    @classmethod
    def process_raw_data(cls, data: Any) -> Dict[str, Any]:
        """在模型创建前处理原始数据"""
        if not isinstance(data, dict):
            return {}

        # 处理评论ID
        if 'rpid' in data:
            data['comment_id'] = str(data['rpid'])

        # 处理父评论ID
        if 'parent' in data:
            data['parent_comment_id'] = str(data['parent'])

        # 处理时间戳
        if 'ctime' in data:
            data['create_time'] = data['ctime']

        # 处理回复数
        if 'rcount' in data:
            data['sub_comment_count'] = str(data['rcount'])

        # 处理点赞数
        if 'like' in data:
            data['like_count'] = data['like']

        # 处理用户数据
        member = data.get('member', {})
        if isinstance(member, dict):
            data['user_id'] = str(member.get('mid', ''))
            data['nickname'] = member.get('uname', '')
            data['sex'] = member.get('sex', '')
            data['sign'] = member.get('sign', '')
            data['avatar'] = member.get('avatar', '')

        # 处理内容数据
        content = data.get('content', {})
        if isinstance(content, dict):
            data['content'] = content.get('message', '')

        return data


class BilibiliCommentsResult(BaseModel):
    """Bilibili 评论结果"""
    comments: List[BilibiliComment] = Field(default_factory=list, description="评论列表")
    total_count: Optional[int] = Field(None, description="总数量")
    video_ids: List[str] = Field(default_factory=list, description="视频 ID 列表")
    crawl_info: dict = Field(default_factory=dict, description="爬虫信息")


class BilibiliCreatorInfo(BaseModel):
    """创作者基础信息"""
    creator_id: str = Field(..., description="创作者 ID")
    creator_name: str = Field(..., description="创作者名称")
    total_videos: int = Field(default=0, description="视频总数")


class BilibiliCreatorResult(BaseModel):
    """Bilibili 单个创作者视频结果"""
    creator_info: BilibiliCreatorInfo = Field(..., description="创作者信息")
    videos: List[BilibiliVideoSimple] = Field(default_factory=list, description="视频列表")
    total_count: Optional[int] = Field(None, description="当前页视频数量")
    page_info: dict = Field(default_factory=dict, description="分页信息")
    crawl_info: dict = Field(default_factory=dict, description="爬虫信息")