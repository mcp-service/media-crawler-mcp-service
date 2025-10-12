# -*- coding: utf-8 -*-
"""
Platform Configuration - 平台启用配置
"""
import os
from typing import List, Set


class PlatformConfig:
    """平台配置管理"""

    # 所有支持的平台
    ALL_PLATFORMS = {"xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"}

    # 平台名称映射
    PLATFORM_NAMES = {
        "xhs": "小红书",
        "dy": "抖音",
        "ks": "快手",
        "bili": "B站",
        "wb": "微博",
        "tieba": "贴吧",
        "zhihu": "知乎",
    }

    @classmethod
    def get_enabled_platforms(cls) -> Set[str]:
        """
        获取启用的平台列表

        从环境变量ENABLED_PLATFORMS读取，格式: xhs,dy,ks
        如果未设置或设置为"all"，则启用所有平台

        Returns:
            启用的平台代码集合
        """
        enabled_str = os.getenv("ENABLED_PLATFORMS", "all").strip().lower()

        if enabled_str == "all" or not enabled_str:
            return cls.ALL_PLATFORMS.copy()

        # 解析平台列表
        platforms = {p.strip() for p in enabled_str.split(",")}

        # 过滤无效平台
        valid_platforms = platforms & cls.ALL_PLATFORMS

        if not valid_platforms:
            # 如果没有有效平台，返回所有平台
            return cls.ALL_PLATFORMS.copy()

        return valid_platforms

    @classmethod
    def is_platform_enabled(cls, platform_code: str) -> bool:
        """
        检查平台是否启用

        Args:
            platform_code: 平台代码

        Returns:
            是否启用
        """
        return platform_code in cls.get_enabled_platforms()

    @classmethod
    def get_platform_name(cls, platform_code: str) -> str:
        """获取平台中文名称"""
        return cls.PLATFORM_NAMES.get(platform_code, platform_code)

    @classmethod
    def list_enabled_platforms(cls) -> List[dict]:
        """
        列出所有启用的平台信息

        Returns:
            平台信息列表 [{"code": "xhs", "name": "小红书"}, ...]
        """
        enabled = cls.get_enabled_platforms()
        return [
            {"code": code, "name": cls.PLATFORM_NAMES[code]}
            for code in sorted(enabled)
        ]
