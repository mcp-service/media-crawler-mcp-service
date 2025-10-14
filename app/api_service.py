# -*- coding: utf-8 -*-
"""
FastMCP API服务模块 - 集成 Starlette 路由和 FastMCP 工具
"""

from fastmcp import FastMCP
from app.providers.logger import init_logger, get_logger
from app.config.settings import global_settings, create_db_config, create_redis_config
from app.api.endpoints.base import BaseEndpoint, endpoint_registry 


def create_app() -> FastMCP:
    """创建FastMCP应用"""
    
    # 初始化日志器
    logger = init_logger(
        name=global_settings.app.name,
        level=global_settings.logger.level,
        log_file=global_settings.logger.log_file,
        enable_file=global_settings.logger.enable_file,
        enable_console=global_settings.logger.enable_console,
        max_file_size=global_settings.logger.max_file_size,
        retention_days=global_settings.logger.retention_days
    )
    
    # 创建FastMCP应用
    app = FastMCP(
        name=global_settings.app.name,
        version=global_settings.app.version,
        port=global_settings.app.port,
        debug=global_settings.app.debug
    )
    
    # 自动发现并注册所有端点
    auto_discover_endpoints()
    
    # 注册所有MCP工具
    endpoint_registry.register_all_mcp_tools(app)
    
    # 注册服务信息工具
    register_service_tools(app)

    # 注册MCP Prompts和Resources
    register_prompts_and_resources(app)

    # 修改FastMCP的SSE运行方式，集成我们的Starlette路由
    _patch_fastmcp_sse(app)
    
    logger.info(f"✅ {global_settings.app.name} 应用创建完成")
    return app


def _patch_fastmcp_sse(app: FastMCP):
    """修改FastMCP的SSE运行方式，集成我们的Starlette路由"""
    try:
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        from fastmcp.server import SseServerTransport
        import uvicorn
        
        # 保存原始的run_sse_async方法
        original_run_sse = app.run_sse_async
        
        async def patched_run_sse_async():
            """修改后的SSE异步运行方法"""
            sse = SseServerTransport("/messages/")

            async def handle_sse(request):
                """处理SSE连接"""
                async with sse.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    await app._mcp_server.run(
                        streams[0],
                        streams[1],
                        app._mcp_server.create_initialization_options(),
                    )
                # SSE连接由 connect_sse 管理，不需要返回值
                from starlette.responses import Response
                return Response()
            
            # 收集所有端点的路由
            api_routes = []
            for endpoint in endpoint_registry.get_all_endpoints():
                endpoint_routes = endpoint.register_routes()
                get_logger().info(f"[路由注册] {endpoint.__class__.__name__} 返回路由: {[str(r) for r in endpoint_routes]}")
                api_routes.extend(endpoint_routes)

            get_logger().info(f"[路由注册] 总共收集到 {len(api_routes)} 个路由")

            # 创建Starlette应用，集成MCP SSE和HTTP API路由
            routes = [
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ] + api_routes

            get_logger().info(f"[路由注册] Starlette 应用总路由数: {len(routes)}")
            
            starlette_app = Starlette(
                debug=app.settings.debug,
                routes=routes,
            )
            
            config = uvicorn.Config(
                starlette_app,
                host=app.settings.host,
                port=app.settings.port,
                log_level=app.settings.log_level.lower(),
            )
            server = uvicorn.Server(config)
            await server.serve()
        
        # 替换FastMCP的run_sse_async方法
        app.run_sse_async = patched_run_sse_async
        
        get_logger().info("✅ FastMCP SSE运行方式已修改，集成Starlette路由")
        
    except Exception as e:
        get_logger().error(f"❌ FastMCP SSE补丁失败: {e}")
        raise


def auto_discover_endpoints():
    """自动发现并注册所有端点（支持选择性注册平台）"""
    try:
        from app.config.settings import global_settings

        # 获取启用的平台
        enabled_platforms = global_settings.platform.enabled_platforms
        enabled_codes = sorted([(p.value if hasattr(p, 'value') else str(p)) for p in enabled_platforms])
        get_logger().info(f"✅ 启用的平台: {', '.join(enabled_codes)}")

        # 注册社交媒体平台端点
        from app.api.endpoints.mcp import (
            BilibiliEndpoint,
        )
        
        # 注册管理类端点
        from app.api.endpoints.login import LoginEndpoint
        from app.api.endpoints.admin import ConfigEndpoint, StatusEndpoint, AdminPageEndpoint

        # 平台端点映射
        platform_endpoints = {
            # "xhs": XiaohongshuEndpoint,
            # "dy": DouyinEndpoint,
            # "ks": KuaishouEndpoint,
            "bili": BilibiliEndpoint,
            # "wb": WeiboEndpoint,
            # "tieba": TiebaEndpoint,
            # "zhihu": ZhihuEndpoint,
        }

        # 只注册启用的平台
        registered_count = 0
        for platform_code, endpoint_class in platform_endpoints.items():
            if platform_code in set(enabled_codes):
                endpoint_registry.register(endpoint_class())
                registered_count += 1
                get_logger().info(f"  ✅ 已注册{platform_code}")

        # 注册管理端点（总是启用）
        endpoint_registry.register(LoginEndpoint())
        endpoint_registry.register(ConfigEndpoint())
        endpoint_registry.register(StatusEndpoint())
        endpoint_registry.register(AdminPageEndpoint())
        registered_count += 4
        get_logger().info(f"  ✅ 已注册 登录管理端点")
        get_logger().info(f"  ✅ 已注册 配置管理端点")
        get_logger().info(f"  ✅ 已注册 状态监控端点")
        get_logger().info(f"  ✅ 已注册 管理界面端点")

        get_logger().info(f"✅ 所有端点自动发现完成 ({registered_count} 个端点：{registered_count-4} 个平台 + 4 个管理服务）")

    except Exception as e:
        get_logger().error(f"❌ 端点自动发现失败: {e}")
        raise


def register_service_tools(app: FastMCP):
    """注册服务信息工具"""
    try:

        @app.tool()
        async def service_info() -> str:
            """获取服务信息"""
            import json
            info = {
                "name": global_settings.app.name,
                "version": global_settings.app.version,
                "description": "AI工具服务",
                "status": "running",
                "tools_count": endpoint_registry.get_tools_summary()["total_tools"]
            }
            return json.dumps(info, ensure_ascii=False, indent=2)
        
        @app.tool()
        async def service_health() -> str:
            """健康检查"""
            import json
            from datetime import datetime
            health = {
                "status": "healthy",
                "service": global_settings.app.name,
                "timestamp": datetime.now().isoformat() + "Z"
            }
            return json.dumps(health, ensure_ascii=False, indent=2)
        
        @app.tool()
        async def list_tools() -> str:
            """获取所有工具列表"""
            import json
            return json.dumps(endpoint_registry.get_tools_summary()["categories"], ensure_ascii=False, indent=2)
        
        @app.tool()
        async def tool_info(tool_name: str) -> str:
            """获取特定工具信息"""
            import json
            tools = endpoint_registry.get_tools_summary()["categories"]
            for category, tool_list in tools.items():
                if tool_name in tool_list:
                    info = {
                        "tool": tool_name,
                        "category": category,
                        "description": f"{tool_name} 工具",
                        "available": True
                    }
                    return json.dumps(info, ensure_ascii=False, indent=2)
            
            info = {
                "tool": tool_name,
                "available": False,
                "message": "工具不存在"
            }
            return json.dumps(info, ensure_ascii=False, indent=2)
        
        get_logger().info("✅ 服务信息工具注册成功")
        
    except Exception as e:
        get_logger().error(f"❌ 服务信息工具注册失败: {e}")



def register_prompts_and_resources(app: FastMCP):
    """注册MCP Prompts和Resources"""
    try:
        from app.core.prompts import register_prompts
        from app.core.resources import register_resources

        register_prompts(app)
        register_resources(app)

        get_logger().info("✅ MCP Prompts和Resources注册成功")

    except Exception as e:
        get_logger().error(f"❌ MCP Prompts和Resources注册失败: {e}")


# 数据库和Redis初始化函数（如果需要的话）
async def init_database():
    """初始化数据库"""
    try:
        from tortoise import Tortoise
        db_config = create_db_config()
        await Tortoise.init(config=db_config)
        get_logger().info("✅ 数据库初始化成功")
    except Exception as e:
        get_logger().error(f"❌ 数据库初始化失败: {e}")


async def init_redis():
    """初始化Redis"""
    try:
        import redis.asyncio as redis
        redis_config = create_redis_config()
        redis_client = redis.from_url(redis_config["url"])
        await redis_client.ping()
        get_logger().info("✅ Redis初始化成功")
        return redis_client
    except Exception as e:
        get_logger().error(f"❌ Redis初始化失败: {e}")
        return None


async def close_database():
    """关闭数据库连接"""
    try:
        from tortoise import Tortoise
        await Tortoise.close_connections()
        get_logger().info("✅ 数据库连接已关闭")
    except Exception as e:
        get_logger().error(f"❌ 关闭数据库连接失败: {e}")


async def close_redis(redis_client):
    """关闭Redis连接"""
    try:
        if redis_client:
            await redis_client.close()
            get_logger().info("✅ Redis连接已关闭")
    except Exception as e:
        get_logger().error(f"❌ 关闭Redis连接失败: {e}")
