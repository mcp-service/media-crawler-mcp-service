# -*- coding: utf-8 -*-
"""MCP 工具调试端点"""

from starlette.responses import JSONResponse

from app.api.endpoints.base import MCPBlueprint, get_registered_blueprints
from app.providers.logger import get_logger


logger = get_logger()
bp = MCPBlueprint(
    prefix="/mcp",
    name="mcp_inspector",
    tags=["MCP 工具"],
    category="admin",
)


@bp.route("/tools", methods=["GET"])
async def list_tools(request):
    """获取已注册的 MCP 工具信息"""
    try:
        items = [registered.summary() for registered in get_registered_blueprints()]
        return JSONResponse(content={"items": items})
    except Exception as exc:
        logger.error(f"[MCP Inspector] 获取工具信息失败: {exc}")
        return JSONResponse(content={"detail": str(exc)}, status_code=500)


__all__ = ["bp"]
