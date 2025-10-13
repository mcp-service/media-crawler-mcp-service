# -*- coding: utf-8 -*-
"""
数据库模型包 - 统一导出所有 Tortoise ORM 模型

按照 Rule 5: PostgreSQL Database Storage Standards
所有数据库模型集中在 app/providers/models/
"""

from .base_model import BaseModel
from .bilibili import (
    BilibiliVideo,
    BilibiliVideoComment,
    BilibiliUpInfo,
    BilibiliContactInfo,
    BilibiliUpDynamic,
)

__all__ = [
    "BaseModel",
    # Bilibili models
    "BilibiliVideo",
    "BilibiliVideoComment",
    "BilibiliUpInfo",
    "BilibiliContactInfo",
    "BilibiliUpDynamic",
]