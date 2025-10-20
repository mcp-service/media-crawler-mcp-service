# -*- coding: utf-8 -*-
"""
管理服务模块 - Web 管理界面

提供简单的 Web UI 用于管理和监控服务
"""

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.responses import HTMLResponse, JSONResponse
from pathlib import Path

# 获取当前文件所在目录
ADMIN_DIR = Path(__file__).parent


def create_admin_app() -> Starlette:
    """
    创建管理服务应用

    Returns:
        Starlette: 管理服务应用实例
    """
    templates = Jinja2Templates(directory=str(ADMIN_DIR / "templates"))

    async def index(request):
        """首页"""
        return templates.TemplateResponse(request, "index.html")

    async def health(request):
        """健康检查"""
        return JSONResponse({"status": "ok"})

    routes = [
        Route("/", index),
        Route("/health", health),
        Mount("/static", StaticFiles(directory=str(ADMIN_DIR / "static")), name="static"),
    ]

    app = Starlette(debug=True, routes=routes)

    return app


__all__ = ["create_admin_app"]
