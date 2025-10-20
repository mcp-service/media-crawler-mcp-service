# -*- coding: utf-8 -*-
"""FastMCP API 服务模块 - 集成蓝图、工具与资源。"""

from __future__ import annotations

from importlib import import_module

from fastmcp import FastMCP
from starlette.applications import Starlette

from app.api.endpoints.base import get_registered_blueprints
from app.config.settings import Platform, global_settings
from app.core.mcp_tools import list_tools, service_health, service_info, tool_info
from app.providers.logger import get_logger, init_logger


def create_app() -> Starlette:
    """创建 FastMCP 应用并返回 ASGI 应用。"""

    init_logger(
        name=global_settings.app.name,
        level=global_settings.logger.level,
        log_file=global_settings.logger.log_file,
        enable_file=global_settings.logger.enable_file,
        enable_console=global_settings.logger.enable_console,
        max_file_size=global_settings.logger.max_file_size,
        retention_days=global_settings.logger.retention_days,
    )
    logger = get_logger()

    app = FastMCP(
        name=global_settings.app.name,
        version=global_settings.app.version,
    )

    _import_common_endpoints()
    _import_platform_endpoints()

    http_app = app.http_app(path="/mcp")
    blueprints = list(get_registered_blueprints())
    for blueprint in blueprints:
        blueprint.install(app, http_app)
        logger.info(
            f"🧩 已安装蓝图 {blueprint.name} "
            f"(prefix={blueprint.prefix} "
            f"routes={len(blueprint.routes)} "
            f"tools={len(blueprint.tools)})"
        )
    logger.info(f"✅ 蓝图安装完成，共 {len(blueprints)} 个")

    service_tools = {
        "service_info": service_info,
        "service_health": service_health,
        "list_tools": list_tools,
        "tool_info": tool_info,
    }
    for tool_name, handler in service_tools.items():
        app.tool(name=tool_name)(handler)
    logger.info(f"✅ 服务信息工具注册成功: {', '.join(sorted(service_tools))}")

    from app.core.prompts import register_prompts
    from app.core.resources import register_resources

    register_prompts(app)
    register_resources(app)
    logger.info("✅ MCP Prompts 和 Resources 注册成功")

    logger.info(f"✅ {global_settings.app.name} ASGI 应用创建完成")
    return http_app


def _import_common_endpoints() -> None:
    """导入通用端点模块，触发蓝图注册。"""
    modules = (
        "app.api.endpoints.login.login_endpoint",
        "app.api.endpoints.admin.admin_page_endpoint",
        "app.api.endpoints.admin.config_endpoint",
        "app.api.endpoints.admin.status_endpoint",
        "app.api.endpoints.admin.mcp_inspector_endpoint",
    )
    for module_name in modules:
        import_module(module_name)


def _import_platform_endpoints() -> None:
    """按配置导入平台端点模块。"""
    platform_modules = {
        Platform.BILIBILI: "app.api.endpoints.mcp.bilibili",
    }

    enabled_platforms = getattr(global_settings.platform, "enabled_platforms", [])
    for platform in enabled_platforms:
        for enum_item, module_name in platform_modules.items():
            code = enum_item.value
            current = (
                platform.value
                if isinstance(platform, Platform)
                else str(platform)
            )
            if current == code:
                import_module(module_name)
                break
