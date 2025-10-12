# -*- coding: utf-8 -*-
"""
Zhihu (知乎) Platform Endpoint
"""
from .base import BasePlatformEndpoint


class ZhihuEndpoint(BasePlatformEndpoint):
    """知乎平台端点"""

    def __init__(self) -> None:
        super().__init__(
            platform_code="zhihu",
            platform_name="知乎",
            prefix="/zhihu"
        )