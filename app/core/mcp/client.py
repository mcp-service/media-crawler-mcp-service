# -*- coding: utf-8 -*-
"""MCP Client 用于调用工具"""

from fastmcp import Client
from app.providers.logger import get_logger
from app.config.settings import global_settings

logger = get_logger()

class MCPClientManager:
    """MCP Client 管理器 - 用于调用 MCP 工具"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def call_tool(self, tool_name: str, arguments: dict):
        """通过 MCP Client 调用工具"""
        try:
            # 创建 Client 连接到本地 MCP 服务
            async with Client(f"http://localhost:{global_settings.app.port}/mcp") as client:
                # 直接传递参数字典，让 FastMCP 处理参数转换
                result = await client.call_tool(tool_name, arguments)
                return result
        except Exception as e:
            logger.error(f"MCP Client call tool failed: {e}")
            # 返回一个简单的错误信息而不是重新抛出异常
            return f"工具执行失败: {str(e)}"

# 全局实例
mcp_client_manager = MCPClientManager()