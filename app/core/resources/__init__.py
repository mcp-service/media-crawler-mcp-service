# -*- coding: utf-8 -*-
"""
MCP Resources - 提供可访问的资源
"""
import os
from pathlib import Path
from fastmcp import FastMCP
from app.providers.logger import get_logger
from app.config.settings import global_settings


def register_resources(app: FastMCP) -> None:
    """注册所有MCP资源"""

    # 爬取数据目录资源
    @app.resource("data://crawler_data")
    async def get_crawler_data_info() -> str:
        """
        获取爬虫数据目录信息

        返回爬取数据的存储位置和统计信息
        """
        import json
        from datetime import datetime

        data_path = Path("data")
        if not data_path.exists():
            return json.dumps({
                "status": "empty",
                "message": "数据目录不存在，尚未进行任何爬取",
                "path": str(data_path.absolute())
            }, ensure_ascii=False, indent=2)

        # 统计各平台数据
        platform_stats = {}
        for platform_dir in data_path.iterdir():
            if platform_dir.is_dir():
                files = list(platform_dir.glob("*.json")) + list(platform_dir.glob("*.csv"))
                total_size = sum(f.stat().st_size for f in files if f.is_file())

                platform_stats[platform_dir.name] = {
                    "files_count": len(files),
                    "total_size_mb": round(total_size / 1024 / 1024, 2),
                    "latest_file": max([f.name for f in files], default="无") if files else "无"
                }

        return json.dumps({
            "status": "active",
            "data_path": str(data_path.absolute()),
            "platforms": platform_stats,
            "updated_at": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)

    # 浏览器会话数据目录资源
    @app.resource("data://browser_data")
    async def get_browser_data_info() -> str:
        """
        获取浏览器会话数据目录信息

        返回浏览器登录状态存储位置和平台登录信息
        """
        import json
        from datetime import datetime

        browser_data_path = Path("browser_data")
        if not browser_data_path.exists():
            return json.dumps({
                "status": "empty",
                "message": "浏览器数据目录不存在，尚未进行任何平台登录",
                "path": str(browser_data_path.absolute())
            }, ensure_ascii=False, indent=2)

        # 检查各平台登录状态
        platform_sessions = {}
        for session_dir in browser_data_path.iterdir():
            if session_dir.is_dir() and session_dir.name.endswith("_user_data_dir"):
                platform_code = session_dir.name.replace("_user_data_dir", "")
                # 检查是否有登录状态文件
                has_session = (session_dir / "Default").exists() or (session_dir / "Cookies").exists()

                platform_sessions[platform_code] = {
                    "has_session": has_session,
                    "path": str(session_dir),
                    "size_mb": round(sum(f.stat().st_size for f in session_dir.rglob("*") if f.is_file()) / 1024 / 1024, 2)
                }

        return json.dumps({
            "status": "active",
            "browser_data_path": str(browser_data_path.absolute()),
            "platforms": platform_sessions,
            "updated_at": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)

    # 配置文件资源
    @app.resource("config://platform_config")
    async def get_platform_config() -> str:
        """
        获取当前平台配置

        返回已启用的平台列表和配置信息
        """
        import json
        from app.config.settings import global_settings

        enabled = [p.value if hasattr(p, 'value') else str(p) for p in global_settings.platform.enabled_platforms]
        platform_names = {
            "bili": "哔哩哔哩",
            "xhs": "小红书",
            "dy": "抖音",
            "ks": "快手",
            "wb": "微博",
            "tieba": "贴吧",
            "zhihu": "知乎"
        }
        all_platforms = [
            {"code": code, "name": platform_names.get(code, code)}
            for code in [p.value for p in global_settings.platform.enabled_platforms]
        ]

        return json.dumps({
            "enabled_platforms": enabled,
            "all_platforms": all_platforms,
            "enabled_count": len(enabled),
            "total_count": len(all_platforms)
        }, ensure_ascii=False, indent=2)

    # 数据库配置资源
    @app.resource("config://database")
    async def get_database_config() -> str:
        """
        获取数据库配置信息（隐藏敏感信息）
        """
        import json

        db_host = global_settings.database.host
        db_port = str(global_settings.database.port)
        db_name = global_settings.database.database

        return json.dumps({
            "type": "PostgreSQL",
            "host": db_host,
            "port": db_port,
            "database": db_name,
            "connection_string": f"postgresql://{db_host}:{db_port}/{db_name}"
        }, ensure_ascii=False, indent=2)

    # 日志资源
    @app.resource("logs://recent")
    async def get_recent_logs() -> str:
        """
        获取最近的日志信息

        返回最近100行应用日志
        """
        log_path = Path("logs/mcp-toolse.log")
        if not log_path.exists():
            return "日志文件不存在"

        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # 返回最后100行
                recent_lines = lines[-100:] if len(lines) > 100 else lines
                return "".join(recent_lines)
        except Exception as e:
            return f"读取日志失败: {str(e)}"

    # API文档资源
    @app.resource("docs://api_endpoints")
    async def get_api_endpoints() -> str:
        """
        获取所有可用的API端点文档
        """
        import json
        from app.api.endpoints.base import endpoint_registry

        endpoints_info = []
        for endpoint in endpoint_registry.get_all_endpoints():
            endpoints_info.append({
                "prefix": endpoint.prefix,
                "tags": endpoint.tags,
                "routes": [
                    {
                        "path": f"{endpoint.prefix}{route.path}",
                        "methods": route.methods
                    }
                    for route in endpoint.register_routes()
                ]
            })

        return json.dumps({
            "base_url": f"http://localhost:{global_settings.app.port}",
            "endpoints": endpoints_info
        }, ensure_ascii=False, indent=2)

    # 系统状态资源
    @app.resource("status://system")
    async def get_system_status() -> str:
        """
        获取系统运行状态
        """
        import json
        import psutil
        from datetime import datetime

        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "status": "running"
        }, ensure_ascii=False, indent=2)

    get_logger().info("✅ MCP Resources注册成功")
