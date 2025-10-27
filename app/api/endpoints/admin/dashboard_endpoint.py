# -*- coding: utf-8 -*-
"""管理界面端点 - 仅保留路由，页面渲染在 app/pages 中。"""

from starlette.responses import RedirectResponse
from app.providers.logger import get_logger
from app.api.endpoints import main_app

from app.pages.admin_dashboard import render_admin_dashboard
from app.pages.admin_config import render_admin_config
from app.pages.admin_login import render_admin_login
from app.pages.admin_inspector import render_admin_inspector


logger = get_logger()


@main_app.custom_route("/dashboard", methods=["GET"])
async def admin_dashboard(request):
    return render_admin_dashboard()


@main_app.custom_route("/config", methods=["GET"])
async def admin_config_page(request):
    return render_admin_config()


@main_app.custom_route("/login", methods=["GET"])
async def admin_login_page(request):
    return render_admin_login()


@main_app.custom_route("/inspector", methods=["GET"])
async def admin_inspector_page(request):
    return render_admin_inspector()


# 兼容导航路径：/admin 与 /admin/ 均重定向到 /dashboard
@main_app.custom_route("/admin", methods=["GET"])
async def admin_root_redirect(request):
    return RedirectResponse(url="/dashboard")


@main_app.custom_route("/admin/", methods=["GET"])
async def admin_root_redirect_slash(request):
    return RedirectResponse(url="/dashboard")

