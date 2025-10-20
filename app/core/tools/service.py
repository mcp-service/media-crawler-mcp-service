# -*- coding: utf-8 -*-
"""通用服务级 MCP 工具。"""

from __future__ import annotations

import json
from datetime import datetime

from app.api.endpoints.base import get_tools_summary
from app.config.settings import global_settings


async def service_info() -> str:
    """获取服务信息。"""
    info = {
        "name": global_settings.app.name,
        "version": global_settings.app.version,
        "description": "AI工具服务",
        "status": "running",
        "tools_count": get_tools_summary()["total_tools"],
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
    summary = get_tools_summary()["categories"]
    return json.dumps(summary, ensure_ascii=False, indent=2)


async def tool_info(tool_name: str) -> str:
    """获取特定工具信息。"""
    tools = get_tools_summary()["categories"]
    for category, tool_list in tools.items():
        if tool_name in tool_list:
            info = {
                "tool": tool_name,
                "category": category,
                "description": f"{tool_name} 工具",
                "available": True,
            }
            return json.dumps(info, ensure_ascii=False, indent=2)

    info = {
        "tool": tool_name,
        "available": False,
        "message": "工具不存在",
    }
    return json.dumps(info, ensure_ascii=False, indent=2)


__all__ = ["service_info", "service_health", "list_tools", "tool_info"]

