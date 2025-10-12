# -*- coding: utf-8 -*-
"""
Weibo (微博) Platform Endpoint
"""
from .base import BasePlatformEndpoint


class WeiboEndpoint(BasePlatformEndpoint):
    """微博平台端点"""

    def __init__(self) -> None:
        super().__init__(
            platform_code="wb",
            platform_name="微博",
            prefix="/weibo"
        )