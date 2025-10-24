# -*- coding: utf-8 -*-
"""管理界面端点 - 提供 Web UI"""

from pathlib import Path

from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from fastmcp import FastMCP
from app.providers.logger import get_logger


logger = get_logger()
admin_router = FastMCP(name="管理界面路由")

_admin_dir = Path(__file__).parent.parent.parent.parent / "admin"
_templates = Jinja2Templates(directory=str(_admin_dir / "templates"))



@admin_router.custom_route("/dashboard", methods=["GET"])
async def admin_dashboard(request):
    """管理首页 - 仪表板"""
    try:
        return _templates.TemplateResponse(
            request,
            "dashboard.html",
            {"title": "MediaCrawler MCP Service"},
        )
    except Exception as exc:
        logger.error(f"[管理界面] 渲染 dashboard 失败: {exc}")
        return HTMLResponse(content=f"<h1>Error</h1><p>{exc}</p>", status_code=500)


@admin_router.custom_route("/config", methods=["GET"])
async def admin_config_page(request):
    """配置管理页面"""
    try:
        return _templates.TemplateResponse(
            request,
            "config.html",
            {"title": "配置管理"},
        )
    except Exception as exc:
        logger.error(f"[管理界面] 渲染 config 失败: {exc}")
        return HTMLResponse(content=f"<h1>Error</h1><p>{exc}</p>", status_code=500)


@admin_router.custom_route("/login", methods=["GET"])
async def admin_login_page(request):
    """登录管理页面"""
    try:
        return _templates.TemplateResponse(
            request,
            "login.html",
            {"title": "登录管理"},
        )
    except Exception as exc:
        logger.error(f"[管理界面] 渲染 login 失败: {exc}")
        return HTMLResponse(content=f"<h1>Error</h1><p>{exc}</p>", status_code=500)


@admin_router.custom_route("/inspector", methods=["GET"])
async def admin_inspector_page(request):
    """MCP 工具调试页面"""
    try:
        return _templates.TemplateResponse(
            request,
            "inspector.html",
            {"title": "Media Crawler Inspector"},
        )
    except Exception as exc:
        logger.error(f"[管理界面] 渲染 inspector 失败: {exc}")
        return HTMLResponse(content=f"<h1>Error</h1><p>{exc}</p>", status_code=500)


__all__ = ["admin_router"]
