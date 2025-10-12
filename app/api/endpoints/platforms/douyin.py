# -*- coding: utf-8 -*-
"""
Douyin (抖音) Platform Endpoint
"""
from .base import BasePlatformEndpoint


class DouyinEndpoint(BasePlatformEndpoint):
    """抖音平台端点"""

    def __init__(self) -> None:
        super().__init__(
            platform_code="dy",
            platform_name="抖音",
            prefix="/douyin"
        )