# -*- coding: utf-8 -*-
"""Admin 相关端点蓝图。"""

from .admin_page_endpoint import admin_router
from .config_endpoint import config_router
from .mcp_inspector_endpoint import mcp_inspector_router
from .status_endpoint import status_router

__all__ = [
    "admin_router",
    "config_router",
    "mcp_inspector_router",
    "status_router",
]
