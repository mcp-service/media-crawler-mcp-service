# -*- coding: utf-8 -*-
"""
Admin 相关端点
"""

from .config_endpoint import ConfigEndpoint
from .status_endpoint import StatusEndpoint
from .admin_page_endpoint import AdminPageEndpoint
from .mcp_inspector_endpoint import McpInspectorEndpoint

__all__ = [
    "ConfigEndpoint",
    "StatusEndpoint",
    "AdminPageEndpoint",
    "McpInspectorEndpoint",
]
