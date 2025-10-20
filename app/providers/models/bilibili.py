# -*- coding: utf-8 -*-
"""
B站数据模型 - Tortoise ORM
迁移自 media_crawler/database/models.py
"""
from tortoise import fields
from .base_model import BaseModel


class BilibiliVideo(BaseModel):
    """B站视频模型"""

    video_id = fields.BigIntField(unique=True, db_index=True, description="视频ID")
    video_url = fields.TextField(description="视频URL")
    user_id = fields.BigIntField(db_index=True, description="UP主用户ID")
    nickname = fields.TextField(null=True, description="UP主昵称")
    avatar = fields.TextField(null=True, description="UP主头像URL")
    liked_count = fields.IntField(default=0, description="点赞数")
    add_ts = fields.BigIntField(description="添加时间戳")
    last_modify_ts = fields.BigIntField(description="最后修改时间戳")
    video_type = fields.TextField(null=True, description="视频类型")
    title = fields.TextField(null=True, description="视频标题")
    desc = fields.TextField(null=True, description="视频简介")
    create_time = fields.BigIntField(db_index=True, description="视频发布时间戳")
    disliked_count = fields.TextField(null=True, description="踩数")
    video_play_count = fields.TextField(null=True, description="播放量")
    video_favorite_count = fields.TextField(null=True, description="收藏数")
    video_share_count = fields.TextField(null=True, description="分享数")
    video_coin_count = fields.TextField(null=True, description="投币数")
    video_danmaku = fields.TextField(null=True, description="弹幕数")
    video_comment = fields.TextField(null=True, description="评论数")
    video_cover_url = fields.TextField(null=True, description="视频封面URL")
    source_keyword = fields.TextField(default="", description="搜索关键词")

    class Meta:
        table = "bilibili_video"
        indexes = [
            ("video_id",),
            ("user_id",),
            ("create_time",),
        ]

    def __str__(self):
        return f"BilibiliVideo(video_id={self.video_id}, title={self.title})"


class BilibiliVideoComment(BaseModel):
    """B站视频评论模型"""

    user_id = fields.CharField(max_length=255, description="评论用户ID")
    nickname = fields.TextField(null=True, description="评论用户昵称")
    sex = fields.TextField(null=True, description="用户性别")
    sign = fields.TextField(null=True, description="用户签名")
    avatar = fields.TextField(null=True, description="用户头像URL")
    add_ts = fields.BigIntField(description="添加时间戳")
    last_modify_ts = fields.BigIntField(description="最后修改时间戳")
    comment_id = fields.BigIntField(db_index=True, description="评论ID")
    video_id = fields.BigIntField(db_index=True, description="所属视频ID")
    content = fields.TextField(null=True, description="评论内容")
    create_time = fields.BigIntField(description="评论发布时间戳")
    sub_comment_count = fields.TextField(null=True, description="子评论数")
    parent_comment_id = fields.CharField(max_length=255, null=True, description="父评论ID")
    like_count = fields.TextField(default="0", description="点赞数")

    class Meta:
        table = "bilibili_video_comment"
        indexes = [
            ("comment_id",),
            ("video_id",),
        ]

    def __str__(self):
        return f"BilibiliVideoComment(comment_id={self.comment_id}, video_id={self.video_id})"


class BilibiliUpInfo(BaseModel):
    """B站UP主信息模型"""

    user_id = fields.BigIntField(db_index=True, description="UP主用户ID")
    nickname = fields.TextField(null=True, description="UP主昵称")
    sex = fields.TextField(null=True, description="UP主性别")
    sign = fields.TextField(null=True, description="UP主签名")
    avatar = fields.TextField(null=True, description="UP主头像URL")
    add_ts = fields.BigIntField(description="添加时间戳")
    last_modify_ts = fields.BigIntField(description="最后修改时间戳")
    total_fans = fields.IntField(default=0, description="总粉丝数")
    total_liked = fields.IntField(default=0, description="总获赞数")
    user_rank = fields.IntField(default=0, description="用户等级")
    is_official = fields.IntField(default=0, description="是否官方认证")

    class Meta:
        table = "bilibili_up_info"
        indexes = [
            ("user_id",),
        ]

    def __str__(self):
        return f"BilibiliUpInfo(user_id={self.user_id}, nickname={self.nickname})"


class BilibiliContactInfo(BaseModel):
    """B站联系人信息模型（UP主和粉丝关系）"""

    up_id = fields.BigIntField(db_index=True, description="UP主用户ID")
    fan_id = fields.BigIntField(db_index=True, description="粉丝用户ID")
    up_name = fields.TextField(null=True, description="UP主昵称")
    fan_name = fields.TextField(null=True, description="粉丝昵称")
    up_sign = fields.TextField(null=True, description="UP主签名")
    fan_sign = fields.TextField(null=True, description="粉丝签名")
    up_avatar = fields.TextField(null=True, description="UP主头像URL")
    fan_avatar = fields.TextField(null=True, description="粉丝头像URL")
    add_ts = fields.BigIntField(description="添加时间戳")
    last_modify_ts = fields.BigIntField(description="最后修改时间戳")

    class Meta:
        table = "bilibili_contact_info"
        indexes = [
            ("up_id",),
            ("fan_id",),
            ("up_id", "fan_id"),  # Composite index
        ]

    def __str__(self):
        return f"BilibiliContactInfo(up_id={self.up_id}, fan_id={self.fan_id})"


class BilibiliUpDynamic(BaseModel):
    """B站UP主动态模型"""

    dynamic_id = fields.BigIntField(db_index=True, description="动态ID")
    user_id = fields.CharField(max_length=255, description="UP主用户ID")
    user_name = fields.TextField(null=True, description="UP主昵称")
    text = fields.TextField(null=True, description="动态文本内容")
    type = fields.TextField(null=True, description="动态类型")
    pub_ts = fields.BigIntField(description="发布时间戳")
    total_comments = fields.IntField(default=0, description="总评论数")
    total_forwards = fields.IntField(default=0, description="总转发数")
    total_liked = fields.IntField(default=0, description="总点赞数")
    add_ts = fields.BigIntField(description="添加时间戳")
    last_modify_ts = fields.BigIntField(description="最后修改时间戳")

    class Meta:
        table = "bilibili_up_dynamic"
        indexes = [
            ("dynamic_id",),
        ]

    def __str__(self):
        return f"BilibiliUpDynamic(dynamic_id={self.dynamic_id}, user_id={self.user_id})"
