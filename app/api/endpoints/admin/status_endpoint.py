# -*- coding: utf-8 -*-
"""状态监控端点 - 统一管理服务状态"""

from __future__ import annotations

import json
from datetime import datetime
import asyncio
from pathlib import Path
from typing import Dict, Optional

import psutil
from starlette.responses import JSONResponse

from fastmcp import FastMCP
from app.config.settings import Platform, global_settings
from app.providers.cache.redis_cache import async_redis_storage
from app.core.login import login_service
from app.core.login.models import PlatformLoginState
from app.providers.logger import get_logger
from app.api.endpoints import main_app

logger = get_logger()

@main_app.custom_route("/api/status/system", methods=["GET"])
async def get_system_status(request):
    """获取系统状态"""
    try:
        data = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_gb": round(psutil.virtual_memory().used / 1024 / 1024 / 1024, 2),
            "memory_total_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2),
            "disk_usage_percent": psutil.disk_usage("/").percent,
            "disk_used_gb": round(psutil.disk_usage("/").used / 1024 / 1024 / 1024, 2),
            "disk_total_gb": round(psutil.disk_usage("/").total / 1024 / 1024 / 1024, 2),
        }
        return JSONResponse(content=data)

    except Exception as exc:
        logger.error(f"[状态监控] 获取系统状态失败: {exc}")
        return JSONResponse(content={"detail": str(exc)}, status_code=500)

@main_app.custom_route("/api/status/data", methods=["GET"])
async def get_data_status(request):
    """获取爬取数据统计"""
    try:
        data_path = Path("data")

        platform_stats: Dict[str, Dict[str, object]] = {}
        total_files = 0
        total_size = 0

        if not data_path.exists():
            data = {
                "status": "empty",
                "message": "数据目录不存在",
                "platforms": platform_stats,
                "total_files": total_files,
                "total_size_mb": 0,
                "data_path": str(data_path.absolute()),
                "updated_at": datetime.now().isoformat(),
            }
            return JSONResponse(content=data)

        def _collect_files(p: Path):
            files = list(p.glob("*.json")) + list(p.glob("*.csv"))
            json_dir = p / "json"
            csv_dir = p / "csv"
            videos_dir = p / "videos"
            if json_dir.exists() and json_dir.is_dir():
                files += list(json_dir.glob("*.json"))
            if csv_dir.exists() and csv_dir.is_dir():
                files += list(csv_dir.glob("*.csv"))
            # 统计视频等二进制文件体积与数量（不参与 latest_file 名称显示）
            bin_files = []
            if videos_dir.exists() and videos_dir.is_dir():
                bin_files += [f for f in videos_dir.rglob("*") if f.is_file()]
            return files, bin_files

        for platform_dir in data_path.iterdir():
            if platform_dir.is_dir():
                files, bin_files = _collect_files(platform_dir)
                size = sum(f.stat().st_size for f in files if f.is_file())
                bin_size = sum(f.stat().st_size for f in bin_files)

                latest_file = "无"
                if files:
                    newest = max(files, key=lambda f: f.stat().st_mtime)
                    latest_file = newest.name

                platform_stats[platform_dir.name] = {
                    "files_count": len(files),
                    "total_size_mb": round((size + bin_size) / 1024 / 1024, 2),
                    "latest_file": latest_file,
                }

                total_files += len(files)
                total_size += (size + bin_size)

        data = {
            "status": "active",
            "data_path": str(data_path.absolute()),
            "total_files": total_files,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "platforms": platform_stats,
            "updated_at": datetime.now().isoformat(),
        }
        return JSONResponse(content=data)

    except Exception as exc:
        logger.error(f"[状态监控] 获取数据状态失败: {exc}")
        return JSONResponse(content={"detail": str(exc)}, status_code=500)


@main_app.custom_route("/api/status/services", methods=["GET"])
async def get_services_status(request):
    """获取服务状态"""
    try:
        mcp_port = global_settings.app.port

        async def _probe_tcp(host: str, port: int, timeout: float = 1.0) -> bool:
            try:
                reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                return True
            except Exception:
                return False

        # Redis: 优先用 PING 校验，其次 TCP 端口存活
        redis_status = "unknown"
        try:
            pong = await async_redis_storage.ping()  # type: ignore
            redis_status = "running" if pong else "unknown"
        except Exception:
            alive = await _probe_tcp(global_settings.redis.host, int(global_settings.redis.port))
            redis_status = "running" if alive else "down"

        # PostgreSQL: 尝试 TCP 端口探测（无需引入驱动）
        db_host = global_settings.database.host
        db_port = int(global_settings.database.port)
        db_alive = await _probe_tcp(db_host, db_port)
        db_status = "running" if db_alive else "down"

        data = {
            "mcp_service": {
                "name": "MCP工具服务",
                "port": mcp_port,
                "url": f"http://localhost:{mcp_port}/sse",
                "status": "running",
            },
            "database": {
                "name": "PostgreSQL数据库",
                "host": db_host,
                "port": db_port,
                "status": db_status,
            },
            "redis": {
                "name": "Redis缓存",
                "host": global_settings.redis.host,
                "port": global_settings.redis.port,
                "status": redis_status,
            },
        }
        return JSONResponse(content=data)

    except Exception as exc:
        logger.error(f"[状态监控] 获取服务状态失败: {exc}")
        return JSONResponse(content={"detail": str(exc)}, status_code=500)


@main_app.custom_route("/api/status/platforms", methods=["GET"])
async def get_platforms_status(request):
    """获取平台状态"""
    try:
        platform_names = {
            "bili": "哔哩哔哩",
            "xhs": "小红书",
            "dy": "抖音",
            "ks": "快手",
            "wb": "微博",
            "tieba": "贴吧",
            "zhihu": "知乎",
        }

        platforms = []
        for platform_enum in global_settings.platform.enabled_platforms:
            platform_code = platform_enum.value
            platform_name = platform_names.get(platform_code, platform_code)

            state: Optional[PlatformLoginState] = None
            try:
                # 使用缓存状态，避免频繁风控检查
                state = await login_service.refresh_platform_state(platform_code, force=False)
            except Exception as exc:
                logger.warning(f"[状态监控] 刷新 {platform_code} 登录状态失败: {exc}")
                state = None

            is_logged_in = bool(state and state.is_logged_in)
            has_session = is_logged_in
            has_cookie = bool(state and (state.cookie_dict or state.cookie_str))
            message = state.message if state else "状态不可用"
            last_checked_at = state.last_checked_at if state else None

            platforms.append(
                {
                    "code": platform_code,
                    "name": platform_name,
                    "enabled": True,
                    "has_session": has_session,
                    "tools_available": True,
                    "is_logged_in": is_logged_in,
                    "message": message,
                    "last_checked_at": last_checked_at,
                    "has_cookie": has_cookie,
                }
            )

        return JSONResponse(content=platforms)

    except Exception as exc:
        logger.error(f"[状态监控] 获取平台状态失败: {exc}")
        return JSONResponse(content={"detail": str(exc)}, status_code=500)


@main_app.custom_route("/api/status/summary", methods=["GET"])
async def get_status_summary(request):
    """获取状态概述"""
    try:
        system_response = await get_system_status(request)
        data_response = await get_data_status(request)
        services_response = await get_services_status(request)
        platforms_response = await get_platforms_status(request)

        system_status = json.loads(system_response.body.decode())
        data_status = json.loads(data_response.body.decode())
        services_status = json.loads(services_response.body.decode())
        platforms_status = json.loads(platforms_response.body.decode())

        running_services = sum(
            1 for service in services_status.values() if service.get("status") == "running"
        )
        total_services = len(services_status)
        enabled_platforms = sum(1 for platform in platforms_status if platform["enabled"])

        summary = {
            "timestamp": datetime.now().isoformat(),
            "service_healthy": running_services >= 1,
            "active_connections": 0,
            "system": {
                "cpu_usage": system_status["cpu_percent"],
                "memory_usage": system_status["memory_percent"],
                "disk_usage": system_status["disk_usage_percent"],
            },
            "services": {
                "total": total_services,
                "running": running_services,
                "status": "healthy" if running_services >= 1 else "degraded",
            },
            "platforms": {"enabled": enabled_platforms, "total": len(list(Platform))},
            "data": {
                "total_files": data_status.get("total_files", 0),
                "total_size_mb": data_status.get("total_size_mb", 0),
            },
        }
        return JSONResponse(content=summary)

    except Exception as exc:
        logger.error(f"[状态监控] 获取状态概述失败: {exc}")
        return JSONResponse(content={"detail": str(exc)}, status_code=500)
