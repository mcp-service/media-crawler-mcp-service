# -*- coding: utf-8 -*-
"""
Admin Service - 管理服务主入口
提供Web UI用于登录管理、配置管理等人机交互功能
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path

from app.providers.logger import get_logger


def create_admin_app() -> FastAPI:
    """创建管理服务应用"""
    app = FastAPI(
        title="MCP Tools Admin",
        description="管理服务 - 登录管理、配置管理",
        version="1.0.0"
    )

    # 静态文件和模板
    admin_dir = Path(__file__).parent
    app.mount("/static", StaticFiles(directory=str(admin_dir / "static")), name="static")
    templates = Jinja2Templates(directory=str(admin_dir / "templates"))

    # 注册路由
    from .routes import login, config, status

    app.include_router(login.router, prefix="/api/login", tags=["登录管理"])
    app.include_router(config.router, prefix="/api/config", tags=["配置管理"])
    app.include_router(status.router, prefix="/api/status", tags=["状态监控"])

    # 首页 - 仪表板
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """仪表板首页"""
        return templates.TemplateResponse("dashboard.html", {"request": request})

    # 登录管理页面
    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        """登录管理页面"""
        return templates.TemplateResponse("login.html", {"request": request})

    # 配置管理页面
    @app.get("/config", response_class=HTMLResponse)
    async def config_page(request: Request):
        """配置管理页面"""
        return templates.TemplateResponse("config.html", {"request": request})

    get_logger().info("✅ 管理服务创建完成")
    return app


# 创建应用实例
admin_app = create_admin_app()