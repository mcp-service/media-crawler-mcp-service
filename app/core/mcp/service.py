# -*- coding: utf-8 -*-
"""通用服务级 MCP 工具。"""

from __future__ import annotations

import json
from datetime import datetime

from app.config.settings import global_settings
from app.providers.logger import get_logger

logger = get_logger()


async def service_info() -> str:
    """获取服务信息。"""
    try:
        # 直接使用 main_app 获取工具数量
        from app.api.endpoints import main_app
        tools_result = await main_app.get_tools()
        tools_count = len(tools_result) if tools_result else 0
        
        logger.info(f"动态获取工具数量: {tools_count}")
        
    except Exception as e:
        logger.warning(f"获取动态工具数量失败，使用默认值: {e}")
        tools_count = 8  # 默认值
    
    info = {
        "name": global_settings.app.name,
        "version": global_settings.app.version,
        "description": "AI工具服务",
        "status": "running",
        "tools_count": tools_count,
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
    """获取所有工具列表 - 直接使用 main_app。"""
    try:
        # 直接使用 main_app 获取工具列表
        from app.api.endpoints import main_app
        tools_result = await main_app.get_tools()
        logger.info(f"Direct main_app tools result: {tools_result}")
        
        # 转换字典格式为简化的分类格式
        tools_categories = {}
        
        if isinstance(tools_result, dict):
            for tool_name, tool_obj in tools_result.items():
                # 从工具名称提取平台
                platform = tool_name.split('_')[0] if '_' in tool_name else 'unknown'
                if platform not in tools_categories:
                    tools_categories[platform] = []
                
                tools_categories[platform].append({
                    "name": tool_obj.name,
                    "description": tool_obj.description,
                    "full_name": tool_name
                })
        
        # 如果没有获取到数据，使用默认结构
        if not tools_categories:
            tools_categories = {
                "status": "无可用工具或获取失败"
            }
            
        return json.dumps(tools_categories, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"动态获取工具列表失败: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)


async def tool_info(tool_name: str) -> str:
    """获取特定工具信息 - 直接使用 main_app。"""
    try:
        # 直接使用 main_app 获取所有工具信息
        from app.api.endpoints import main_app
        tools_result = await main_app.get_tools()
        
        # 在工具字典中查找指定工具
        if isinstance(tools_result, dict) and tool_name in tools_result:
            tool_obj = tools_result[tool_name]
            platform = tool_name.split('_')[0] if '_' in tool_name else 'unknown'
            
            info = {
                "tool": tool_name,
                "name": tool_obj.name,
                "description": tool_obj.description,
                "platform": platform,
                "available": True,
                "source": "Direct main_app 获取"
            }
        else:
            info = {
                "tool": tool_name,
                "available": False,
                "message": "工具不存在或未在 MCP 服务中注册",
                "source": "Direct main_app 查询"
            }
            
        return json.dumps(info, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"动态获取工具信息失败: {e}")
        info = {
            "tool": tool_name,
            "available": False,
            "message": str(e),
            "source": f"Error - {str(e)}"
        }
        return json.dumps(info, ensure_ascii=False, indent=2)


__all__ = ["service_info", "service_health", "list_tools", "tool_info"]