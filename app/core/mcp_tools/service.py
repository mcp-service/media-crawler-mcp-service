# -*- coding: utf-8 -*-
"""通用服务级 MCP 工具。"""

from __future__ import annotations

import json
from datetime import datetime

from app.config.settings import global_settings


async def service_info() -> str:
    """获取服务信息。"""
    info = {
        "name": global_settings.app.name,
        "version": global_settings.app.version,
        "description": "AI工具服务",
        "status": "running",
        "tools_count": 8,  # 4个B站工具 + 4个小红书工具
    }
    return json.dumps(info, ensure_ascii=False, indent=2)


async def service_health() -> str:
    """健康检查。"""
    health = {
        "status": "healthy",
        "service": global_settings.app.name,
        "timestamp": datetime.now().isoformat() + "Z",
    }
    return json.dumps(health, ensure_ascii=False, indent=2)


async def list_tools() -> str:
    """获取所有工具列表。"""
    # 现在使用fastmcp原生格式，直接返回已知的工具分类
    tools_categories = {
        "B站MCP": ["search", "crawler_detail", "crawler_creator", "search_time_range_http", "crawler_comments"],
        "小红书MCP": ["search", "crawler_detail", "crawler_creator", "crawler_comments"]
    }
    return json.dumps(tools_categories, ensure_ascii=False, indent=2)


async def tool_info(tool_name: str) -> str:
    """获取特定工具信息。"""
    # 工具映射
    tools_map = {
        "search": {"category": "通用", "description": "搜索功能"},
        "crawler_detail": {"category": "通用", "description": "获取详情信息"},
        "crawler_creator": {"category": "通用", "description": "获取创作者信息"},
        "search_time_range_http": {"category": "B站MCP", "description": "按时间范围搜索"},
        "crawler_comments": {"category": "通用", "description": "获取评论信息"}
    }
    
    if tool_name in tools_map:
        info = {
            "tool": tool_name,
            "category": tools_map[tool_name]["category"],
            "description": tools_map[tool_name]["description"],
            "available": True,
        }
    else:
        info = {
            "tool": tool_name,
            "available": False,
            "message": "工具不存在",
        }
    return json.dumps(info, ensure_ascii=False, indent=2)


__all__ = ["service_info", "service_health", "list_tools", "tool_info"]

