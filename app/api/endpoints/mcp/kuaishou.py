# -*- coding: utf-8 -*-
"""
Kuaishou (快手) Platform Endpoint
"""
from .base import BasePlatformEndpoint


class KuaishouEndpoint(BasePlatformEndpoint):
    """快手平台端点"""

    def __init__(self) -> None:
        super().__init__(
            platform_code="ks",
            platform_name="快手",
            prefix="/kuaishou"
        )