# -*- coding: utf-8 -*-
"""
状态监控路由
"""
import os
import psutil
import httpx
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.providers.logger import get_logger
from app.config.settings import global_settings

router = APIRouter()


@router.get("/system")
async def get_system_status() -> Dict[str, Any]:
    """获取系统状态"""
    try:
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_gb": round(psutil.virtual_memory().used / 1024 / 1024 / 1024, 2),
            "memory_total_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2),
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "disk_used_gb": round(psutil.disk_usage('/').used / 1024 / 1024 / 1024, 2),
            "disk_total_gb": round(psutil.disk_usage('/').total / 1024 / 1024 / 1024, 2)
        }

    except Exception as e:
        get_logger().error(f"[状态监控] 获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data")
async def get_data_status() -> Dict[str, Any]:
    """获取爬取数据统计"""
    try:
        data_path = Path("data")

        if not data_path.exists():
            return {
                "status": "empty",
                "message": "数据目录不存在",
                "platforms": {}
            }

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

        return {
            "status": "active",
            "data_path": str(data_path.absolute()),
            "total_files": total_files,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "platforms": platform_stats,
            "updated_at": datetime.now().isoformat()
        }

    except Exception as e:
        get_logger().error(f"[状态监控] 获取数据状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services")
async def get_services_status() -> Dict[str, Any]:
    """获取服务状态"""
    try:
        # 检查MCP服务
        mcp_port = global_settings.app.port
        admin_port = 9091
        sidecar_url = global_settings.sidecar.url

        services = {
            "mcp_service": {
                "name": "MCP工具服务",
                "port": mcp_port,
                "url": f"http://localhost:{mcp_port}/sse",
                "status": await check_service_health(f"http://localhost:{mcp_port}/health")
            },
            "admin_service": {
                "name": "管理服务",
                "port": admin_port,
                "url": f"http://localhost:{admin_port}",
                "status": "running"  # 当前请求正在处理，所以肯定运行中
            },
            "sidecar_service": {
                "name": "边车服务", 
                "url": sidecar_url,
                "status": await check_service_health(f"{sidecar_url}/health")
            }
        }

        # 检查数据库
        db_config = global_settings.database
        services["database"] = {
            "name": "PostgreSQL数据库",
            "host": db_config.host,
            "port": db_config.port,
            "status": "unknown"  # TODO: 实现数据库连接检查
        }

        # 检查Redis
        redis_config = global_settings.redis
        services["redis"] = {
            "name": "Redis缓存",
            "host": redis_config.host,
            "port": redis_config.port,
            "status": "unknown"  # TODO: 实现Redis连接检查
        }

        return {
            "timestamp": datetime.now().isoformat(),
            "services": services
        }

    except Exception as e:
        get_logger().error(f"[状态监控] 获取服务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platforms")
async def get_platforms_status() -> List[Dict[str, Any]]:
    """获取平台状态"""
    try:
        platforms = []
        for platform_info in global_settings.platforms.list_enabled_platforms():
            platform_code = platform_info["code"]

            # 检查browser_data目录
            browser_data_path = Path(f"browser_data/{platform_code}_user_data_dir")
            has_session = browser_data_path.exists()

            platforms.append({
                "code": platform_code,
                "name": platform_info["name"],
                "enabled": True,
                "has_session": has_session,
                "tools_available": True
            })

        return platforms

    except Exception as e:
        get_logger().error(f"[状态监控] 获取平台状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def check_service_health(url: str, timeout: float = 5.0) -> str:
    """检查服务健康状态"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            return "running" if response.status_code == 200 else "error"
    except Exception:
        return "stopped"


@router.get("/summary")
async def get_status_summary() -> Dict[str, Any]:
    """获取状态概述"""
    try:
        system_status = await get_system_status()
        data_status = await get_data_status()
        services_status = await get_services_status()
        platforms_status = await get_platforms_status()
        
        # 统计服务健康状态
        running_services = sum(
            1 for service in services_status["services"].values()
            if service.get("status") == "running"
        )
        total_services = len(services_status["services"])
        
        # 统计启用平台
        enabled_platforms = sum(1 for platform in platforms_status if platform["enabled"])
        
        return {
            "timestamp": datetime.now().isoformat(),
            "service_healthy": running_services == total_services,
            "active_connections": 0,  # TODO: 实际连接数
            "system": {
                "cpu_usage": system_status["cpu_percent"],
                "memory_usage": system_status["memory_percent"],
                "disk_usage": system_status["disk_usage_percent"]
            },
            "services": {
                "total": total_services,
                "running": running_services,
                "status": "healthy" if running_services == total_services else "degraded"
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
    
    except Exception as e:
        get_logger().error(f"[状态监控] 获取状态概述失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))