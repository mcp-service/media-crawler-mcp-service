# -*- coding: utf-8 -*-
"""
管理界面端点 - 提供 Web UI
"""
from pathlib import Path
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.responses import HTMLResponse, RedirectResponse

from app.api.endpoints.base import BaseEndpoint
from app.providers.logger import get_logger


class AdminPageEndpoint(BaseEndpoint):
    """管理界面端点"""

    def __init__(self):
        super().__init__(prefix="/admin", tags=["管理界面"])
        self.logger = get_logger()

        # 获取admin目录路径
        self.admin_dir = Path(__file__).parent.parent.parent.parent / "admin"
        self.templates = Jinja2Templates(directory=str(self.admin_dir / "templates"))

    def register_routes(self):
        """注册路由"""

        async def index(request):
            """管理首页 - 仪表板"""
            try:
                return self.templates.TemplateResponse("dashboard.html", {
                    "request": request,
                    "title": "MediaCrawler MCP Service"
                })
            except Exception as e:
                self.logger.error(f"[管理界面] 渲染页面失败: {e}")
                return HTMLResponse(content=f"<h1>Error</h1><p>{e}</p>", status_code=500)

        async def config_page(request):
            """配置管理页面"""
            try:
                return self.templates.TemplateResponse("config.html", {
                    "request": request,
                    "title": "配置管理"
                })
            except Exception as e:
                self.logger.error(f"[管理界面] 渲染配置页面失败: {e}")
                return HTMLResponse(content=f"<h1>Error</h1><p>{e}</p>", status_code=500)

        async def login_page(request):
            """登录管理页面"""
            try:
                return self.templates.TemplateResponse("login.html", {
                    "request": request,
                    "title": "登录管理"
                })
            except Exception as e:
                self.logger.error(f"[管理界面] 渲染登录页面失败: {e}")
                return HTMLResponse(content=f"<h1>Error</h1><p>{e}</p>", status_code=500)

        # 静态文件路由
        static_files = StaticFiles(directory=str(self.admin_dir / "static"))

        return [
            Route(f"{self.prefix}", index, methods=["GET"]),
            Route(f"{self.prefix}/", index, methods=["GET"]),
            Route(f"{self.prefix}/dashboard", index, methods=["GET"]),
            Route(f"{self.prefix}/config", config_page, methods=["GET"]),
            Route(f"{self.prefix}/login", login_page, methods=["GET"]),
            Mount(f"{self.prefix}/static", static_files, name="static"),
        ]

    def register_mcp_tools(self, app):
        """不注册MCP工具，只提供HTTP API"""
        pass