# -*- coding: utf-8 -*-
"""Platform endpoint blueprints package."""

from app.api.endpoints.mcp.bilibili import bp as bilibili_bp
from app.api.endpoints.mcp.xhs import bp as xhs_bp

__all__ = ["bilibili_bp", "xhs_bp"]
