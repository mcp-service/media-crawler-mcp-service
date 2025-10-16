# -*- coding: utf-8 -*-
"""MCP 工具调试端点"""

from starlette.responses import JSONResponse
from starlette.routing import Route

from app.api.endpoints.base import BaseEndpoint, endpoint_registry
from app.providers.logger import get_logger


class McpInspectorEndpoint(BaseEndpoint):
    """提供 MCP 工具信息的 API"""

    def __init__(self):
        super().__init__(prefix="/admin/api/mcp", tags=["MCP 工具"])
        self.logger = get_logger()

    def register_routes(self):
        async def list_tools(request):
            try:
                data = []
                for endpoint in endpoint_registry.get_all_endpoints():
                    tools_info = endpoint.get_tools_info()
                    routes_info = endpoint.get_http_routes()
                    data.append(
                        {
                            "category": tools_info["category"],
                            "prefix": tools_info["prefix"],
                            "tags": tools_info["tags"],
                            "tools": tools_info["tools"],
                            "http_routes": routes_info,
                        }
                    )
                return JSONResponse(content={"items": data})
            except Exception as exc:
                self.logger.error(f"[MCP Inspector] 获取工具信息失败: {exc}")
                return JSONResponse(content={"detail": str(exc)}, status_code=500)

        return [
            self._create_route(
                "/tools",
                list_tools,
                methods=["GET"],
                meta={"label": "获取 MCP 工具信息"},
            )
        ]

    def register_mcp_tools(self, app):  # noqa: D401 - inspector 不注册 MCP 工具
        return None
