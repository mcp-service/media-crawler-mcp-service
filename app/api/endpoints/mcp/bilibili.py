# -*- coding: utf-8 -*-
"""
Bilibili (B站) Platform Endpoint
"""
from .base import BasePlatformEndpoint


class BilibiliEndpoint(BasePlatformEndpoint):
    """B站平台端点"""

    def __init__(self) -> None:
        super().__init__(
            platform_code="bili",
            platform_name="B站",
            prefix="/bilibili"
        )