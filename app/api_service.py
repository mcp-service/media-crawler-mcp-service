# -*- coding: utf-8 -*-
"""FastMCP API 服务模块 - 集成子服务、工具与资源。"""

from __future__ import annotations

from typing import Any

from app.config.settings import Platform, global_settings

from fastmcp import FastMCP
from app.providers.logger import get_logger, init_logger
from app.api.endpoints import main_app, bili_mcp, xhs_mcp
from app.providers.cache.queue import PublishQueue
from app.core.crawler.platforms.xhs.publish import register_xhs_publisher


import asyncio

# 创建全局发布队列实例
_publish_queue = PublishQueue()


def get_publish_queue() -> PublishQueue:
    """获取全局发布队列实例"""
    return _publish_queue


def create_app() -> tuple[Any, Any]:
    """创建 FastMCP 应用并返回 ASGI 应用。"""

    # 初始化日志
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



    # 挂载子应用到主应用 - 使用 asyncio.run 来处理异步调用
    async def setup_servers():
        await main_app.import_server(xhs_mcp, 'xhs')
        await main_app.import_server(bili_mcp, 'bili')

        logger.info(f"✅ MCP tools {await main_app.get_tools()}")
        logger.info(f"✅ MCP prompts {await main_app.get_prompts()}")
        logger.info(f"✅ MCP custom_route {main_app._get_additional_http_routes()}")

    asyncio.run(setup_servers())

    # 注册发布平台到队列
    register_xhs_publisher(_publish_queue)
    logger.info("✅ 发布平台注册完成")

    # 注册服务工具和资源
    from app.core.prompts import register_prompts
    from app.core.resources import register_resources

    register_prompts(main_app)
    register_resources(main_app)

    logger.info("✅ MCP Prompts 和 Resources 注册成功")
    logger.info("✅ 子服务挂载完成: 小红书MCP(/mcp/xhs), B站MCP(/mcp/bili)")
    logger.info("✅ CORS 中间件已添加，支持 OPTIONS 请求")
    logger.info(f"✅ {global_settings.app.name} ASGI 应用创建完成")

    # 获取底层的 Starlette 应用并注册生命周期事件
    asgi_app = main_app.http_app(path='/mcp/')

    # 注册启动和关闭事件
    @asgi_app.on_event("startup")
    async def startup_publish_queue():
        """应用启动时启动发布队列"""
        await _publish_queue.start_all()
        logger.info("✅ 发布队列管理器已启动")

    @asgi_app.on_event("shutdown")
    async def shutdown_publish_queue():
        """应用关闭时停止发布队列"""
        await _publish_queue.stop_all()
        logger.info("✅ 发布队列管理器已停止")

    return asgi_app


# 创建应用并返回
main_asgi = create_app()

