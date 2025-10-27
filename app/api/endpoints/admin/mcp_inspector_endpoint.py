# -*- coding: utf-8 -*-
"""MCP 工具调试端点"""

from starlette.responses import JSONResponse

from fastmcp import FastMCP
from app.providers.logger import get_logger
from app.api.endpoints import main_app

logger = get_logger()

@main_app.custom_route("/api/admin/tools", methods=["GET"])
async def list_tools(request):
    """获取已注册的 MCP 工具信息"""
    try:
        # 现在使用 fastmcp 原生格式，不再需要蓝图汇总
        # 返回直接的 MCP 工具信息
        items = [
            {
                "name": "bili_mcp",
                "category": "B站MCP",
                "tools": [
                    {"name": "search", "description": "搜索 Bilibili 视频"},
                    {"name": "crawler_detail", "description": "获取 Bilibili 视频详情"},
                    {"name": "crawler_creator", "description": "获取 Bilibili UP 主视频"},
                    {"name": "search_time_range_http", "description": "按时间范围搜索 Bilibili 视频"},
                    {"name": "crawler_comments", "description": "按视频 ID 抓取 Bilibili 评论"}
                ]
            },
            {
                "name": "xhs_mcp",
                "category": "小红书MCP",
                "tools": [
                    {"name": "search", "description": "小红书关键词搜索"},
                    {"name": "crawler_detail", "description": "获取小红书笔记详情"},
                    {"name": "crawler_creator", "description": "获取小红书创作者作品"},
                    {"name": "crawler_comments", "description": "小红书笔记评论"}
                ]
            }
        ]
        return JSONResponse(content={"items": items})
    except Exception as exc:
        logger.error(f"[MCP Inspector] 获取工具信息失败: {exc}")
        return JSONResponse(content={"detail": str(exc)}, status_code=500)
