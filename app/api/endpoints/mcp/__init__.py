# -*- coding: utf-8 -*-
"""Platform endpoint blueprints package."""

from app.api.endpoints.mcp.bilibili import bili_mcp
from app.api.endpoints.mcp.xhs import xhs_mcp

__all__ = ["bili_mcp", "xhs_mcp"]
