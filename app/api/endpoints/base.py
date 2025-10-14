# -*- coding: utf-8 -*-
"""
统一的端点基类，支持同时注册 Starlette 路由和 FastMCP 工具
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastmcp import FastMCP
from app.providers.logger import get_logger


class BaseEndpoint(ABC):
    """端点基类，提供统一的注册机制"""
    
    def __init__(self, prefix: str = "", tags: Optional[List[str]] = None):
        """
        初始化端点
        
        Args:
            prefix: API路由前缀
            tags: API标签列表
        """
        self.prefix = prefix
        self.tags = tags or []
        self.routes = []
        self._tools_info = []
        
    @abstractmethod
    def register_routes(self) -> List[Route]:
        """注册 Starlette 路由（子类必须实现）"""
        pass
    
    @abstractmethod
    def register_mcp_tools(self, app: FastMCP):
        """注册 FastMCP 工具（子类必须实现）"""
        pass
    
    def get_routes(self) -> List[Route]:
        """获取 Starlette 路由列表"""
        if not self.routes:
            self.routes = self.register_routes()
        return self.routes
    
    async def _parse_json_body(self, request: Request) -> dict:
        """解析JSON请求体"""
        try:
            body = await request.json()
            return body if body else {}
        except Exception:
            return {}
    
    def _create_json_response(self, data: Any, status_code: int = 200) -> JSONResponse:
        """创建 JSON 响应"""
        from app.api.scheme import jsonify_response
        
        if status_code == 200:
            response_data = jsonify_response(data=data)
        else:
            response_data = jsonify_response(success=False, message=str(data))
        
        return JSONResponse(
            content=response_data,
            status_code=status_code
        )
    
    def _create_route(self, path: str, endpoint: Callable, methods: List[str] = None) -> Route:
        """创建 Starlette 路由"""
        if methods is None:
            methods = ["GET"]
        
        full_path = f"{self.prefix}{path}"
        return Route(full_path, endpoint=endpoint, methods=methods)
    
    def register_tools_to_mcp(self, app: FastMCP):
        """注册工具到 FastMCP 应用"""
        try:
            self.register_mcp_tools(app)
            get_logger().info(f"✅ {self.__class__.__name__} MCP工具注册成功")
        except Exception as e:
            get_logger().error(f"❌ {self.__class__.__name__} MCP工具注册失败: {e}")
            raise
    
    def get_tools_info(self) -> Dict[str, Any]:
        """获取工具信息"""
        return {
            "category": self.__class__.__name__.replace("Endpoint", "").lower(),
            "tools": self._tools_info,
            "prefix": self.prefix,
            "tags": self.tags
        }
    
    def _add_tool_info(self, name: str, description: str):
        """添加工具信息（内部方法）"""
        self._tools_info.append({
            "name": name,
            "description": description
        })


class EndpointRegistry:
    """端点注册器，管理所有端点"""
    
    def __init__(self):
        self.endpoints: List[BaseEndpoint] = []
    
    def register(self, endpoint: BaseEndpoint):
        """注册端点"""
        self.endpoints.append(endpoint)
        get_logger().info(f"📝 注册端点: {endpoint.__class__.__name__}")
    
    def get_all_routes(self) -> List[Route]:
        """获取所有 Starlette 路由"""
        all_routes = []
        for endpoint in self.endpoints:
            routes = endpoint.get_routes()
            all_routes.extend(routes)
        return all_routes

    def get_all_endpoints(self) -> List[BaseEndpoint]:
        """获取所有注册的端点"""
        return self.endpoints
    
    def register_all_mcp_tools(self, app: FastMCP):
        """将所有端点的工具注册到 FastMCP 应用"""
        total_tools = 0
        for endpoint in self.endpoints:
            endpoint.register_tools_to_mcp(app)
            total_tools += len(endpoint.get_tools_info()["tools"])
        
        get_logger().info(f"✅ 所有MCP工具注册成功！共注册 {total_tools} 个工具")
        return total_tools
    
    def get_tools_summary(self) -> Dict[str, Any]:
        """获取所有工具的摘要信息"""
        summary = {}
        total_tools = 0
        
        for endpoint in self.endpoints:
            info = endpoint.get_tools_info()
            category = info["category"]
            tools = info["tools"]
            summary[category] = [tool["name"] for tool in tools]
            total_tools += len(tools)
        
        return {
            "categories": summary,
            "total_tools": total_tools,
            "endpoints_count": len(self.endpoints)
        }


# 全局端点注册器实例
endpoint_registry = EndpointRegistry()