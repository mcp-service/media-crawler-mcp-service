# -*- coding: utf-8 -*-
"""
Xiaohongshu (小红书) Platform Endpoint
"""
from .base import BasePlatformEndpoint


class XiaohongshuEndpoint(BasePlatformEndpoint):
    """小红书平台端点"""

    def __init__(self) -> None:
        super().__init__(
            platform_code="xhs",
            platform_name="小红书",
            prefix="/xiaohongshu"
        )