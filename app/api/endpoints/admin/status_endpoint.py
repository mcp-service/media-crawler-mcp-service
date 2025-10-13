# -*- coding: utf-8 -*-
"""
状态监控端点 - 统一管理服务状态
"""
import psutil
import httpx
from pathlib import Path
from typing import Dict, Any, List
from fastapi import HTTPException
from datetime import datetime

from app.api.endpoints.base import BaseEndpoint
from app.providers.logger import get_logger
from app.config.settings import global_settings


class StatusEndpoint(BaseEndpoint):
    """状态监控端点"""

    def __init__(self):
        super().__init__('/admin/api/status', ["状态监控"])
        self.logger = get_logger()

    def register_routes(self):
        """注册路由"""
        from starlette.responses import JSONResponse

        async def get_system_status_handler(request):
            """获取系统状态"""
            try:
                data = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "memory_used_gb": round(psutil.virtual_memory().used / 1024 / 1024 / 1024, 2),
                    "memory_total_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2),
                    "disk_usage_percent": psutil.disk_usage('/').percent,
                    "disk_used_gb": round(psutil.disk_usage('/').used / 1024 / 1024 / 1024, 2),
                    "disk_total_gb": round(psutil.disk_usage('/').total / 1024 / 1024 / 1024, 2)
                }
                return JSONResponse(content=data)

            except Exception as e:
                self.logger.error(f"[状态监控] 获取系统状态失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        async def get_data_status_handler(request):
            """获取爬取数据统计"""
            try:
                data_path = Path("data")

                if not data_path.exists():
                    return JSONResponse(content={
                        "status": "empty",
                        "message": "数据目录不存在",
                        "platforms": {}
                    })

                # 统计各平台数据
                platform_stats = {}
                total_files = 0
                total_size = 0

                for platform_dir in data_path.iterdir():
                    if platform_dir.is_dir():
                        files = list(platform_dir.glob("*.json")) + list(platform_dir.glob("*.csv"))
                        size = sum(f.stat().st_size for f in files if f.is_file())

                        platform_stats[platform_dir.name] = {
                            "files_count": len(files),
                            "total_size_mb": round(size / 1024 / 1024, 2),
                            "latest_file": max([f.name for f in files], default="无") if files else "无"
                        }

                        total_files += len(files)
                        total_size += size

                data = {
                    "status": "active",
                    "data_path": str(data_path.absolute()),
                    "total_files": total_files,
                    "total_size_mb": round(total_size / 1024 / 1024, 2),
                    "platforms": platform_stats,
                    "updated_at": datetime.now().isoformat()
                }
                return JSONResponse(content=data)

            except Exception as e:
                self.logger.error(f"[状态监控] 获取数据状态失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        async def get_services_status_handler(request):
            """获取服务状态"""
            try:
                # MCP服务端口
                mcp_port = global_settings.app.port

                data = {
                    "mcp_service": {
                        "name": "MCP工具服务",
                        "port": mcp_port,
                        "url": f"http://localhost:{mcp_port}/sse",
                        "status": "running"  # 当前请求正在处理，所以肯定运行中
                    },
                    "database": {
                        "name": "PostgreSQL数据库",
                        "host": global_settings.database.host,
                        "port": global_settings.database.port,
                        "status": "unknown"  # TODO: 实现数据库连接检查
                    },
                    "redis": {
                        "name": "Redis缓存",
                        "host": global_settings.redis.host,
                        "port": global_settings.redis.port,
                        "status": "unknown"  # TODO: 实现Redis连接检查
                    }
                }
                return JSONResponse(content=data)

            except Exception as e:
                self.logger.error(f"[状态监控] 获取服务状态失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        async def get_platforms_status_handler(request):
            """获取平台状态"""
            try:
                # 平台名称映射
                platform_names = {
                    "bili": "哔哩哔哩",
                    "xhs": "小红书",
                    "dy": "抖音",
                    "ks": "快手",
                    "wb": "微博",
                    "tieba": "贴吧",
                    "zhihu": "知乎"
                }

                platforms = []
                for platform_enum in global_settings.platform.enabled_platforms:
                    platform_code = platform_enum.value
                    platform_name = platform_names.get(platform_code, platform_code)

                    # 检查browser_data目录
                    browser_data_path = Path(f"browser_data/{platform_code}_user_data_dir")
                    has_session = browser_data_path.exists()

                    platforms.append({
                        "code": platform_code,
                        "name": platform_name,
                        "enabled": True,
                        "has_session": has_session,
                        "tools_available": True
                    })

                return JSONResponse(content=platforms)

            except Exception as e:
                self.logger.error(f"[状态监控] 获取平台状态失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        async def get_status_summary_handler(request):
            """获取状态概述"""
            try:
                # 调用其他处理器获取数据
                system_response = await get_system_status_handler(request)
                data_response = await get_data_status_handler(request)
                services_response = await get_services_status_handler(request)
                platforms_response = await get_platforms_status_handler(request)

                # 解析JSON响应
                import json
                system_status = json.loads(system_response.body.decode())
                data_status = json.loads(data_response.body.decode())
                services_status = json.loads(services_response.body.decode())
                platforms_status = json.loads(platforms_response.body.decode())

                # 统计服务健康状态
                running_services = sum(
                    1 for service in services_status.values()
                    if service.get("status") == "running"
                )
                total_services = len(services_status)

                # 统计启用平台
                enabled_platforms = sum(1 for platform in platforms_status if platform["enabled"])

                summary = {
                    "timestamp": datetime.now().isoformat(),
                    "service_healthy": running_services >= 1,  # 至少MCP服务在运行
                    "active_connections": 0,  # TODO: 实际连接数
                    "system": {
                        "cpu_usage": system_status["cpu_percent"],
                        "memory_usage": system_status["memory_percent"],
                        "disk_usage": system_status["disk_usage_percent"]
                    },
                    "services": {
                        "total": total_services,
                        "running": running_services,
                        "status": "healthy" if running_services >= 1 else "degraded"
                    },
                    "platforms": {
                        "enabled": enabled_platforms,
                        "total": len(global_settings.platforms.ALL_PLATFORMS)
                    },
                    "data": {
                        "total_files": data_status["total_files"],
                        "total_size_mb": data_status["total_size_mb"]
                    }
                }
                return JSONResponse(content=summary)

            except Exception as e:
                self.logger.error(f"[状态监控] 获取状态概述失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        # 返回 Starlette 路由
        from starlette.routing import Route
        return [
            Route(f"{self.prefix}/system", get_system_status_handler, methods=["GET"]),
            Route(f"{self.prefix}/data", get_data_status_handler, methods=["GET"]),
            Route(f"{self.prefix}/services", get_services_status_handler, methods=["GET"]),
            Route(f"{self.prefix}/platforms", get_platforms_status_handler, methods=["GET"]),
            Route(f"{self.prefix}/summary", get_status_summary_handler, methods=["GET"]),
        ]

    def register_mcp_tools(self, app):
        """不注册MCP工具，只提供HTTP API"""
        pass