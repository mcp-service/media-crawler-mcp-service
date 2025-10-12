# -*- coding: utf-8 -*-
"""
Tieba (贴吧) Platform Endpoint
"""
from .base import BasePlatformEndpoint


class TiebaEndpoint(BasePlatformEndpoint):
    """贴吧平台端点"""

    def __init__(self) -> None:
        super().__init__(
            platform_code="tieba",
            platform_name="贴吧",
            prefix="/tieba"
        )