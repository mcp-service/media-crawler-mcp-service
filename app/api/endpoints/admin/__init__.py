# -*- coding: utf-8 -*-
"""Admin 相关端点蓝图。"""

from .admin_page_endpoint import bp as admin_page_bp
from .config_endpoint import bp as config_bp
from .mcp_inspector_endpoint import bp as inspector_bp
from .status_endpoint import bp as status_bp

__all__ = [
    "admin_page_bp",
    "config_bp",
    "status_bp",
    "inspector_bp",
]
