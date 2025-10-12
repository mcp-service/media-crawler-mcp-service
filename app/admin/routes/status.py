# -*- coding: utf-8 -*-
"""
状态监控路由
"""
import os
import psutil
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.providers.logger import get_logger
from app.config.platform_config import PlatformConfig

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
        mcp_port = int(os.getenv("APP_PORT", "9090"))
        admin_port = 9091

        services = {
            "mcp_service": {
                "name": "MCP工具服务",
                "port": mcp_port,
                "url": f"http://localhost:{mcp_port}/sse",
                "status": "running"  # 实际实现时应该ping服务
            },
            "admin_service": {
                "name": "管理服务",
                "port": admin_port,
                "url": f"http://localhost:{admin_port}",
                "status": "running"
            }
        }

        # 检查数据库
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        services["database"] = {
            "name": "PostgreSQL数据库",
            "host": db_host,
            "port": db_port,
            "status": "unknown"  # 实际实现时应该ping数据库
        }

        # 检查Redis
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = os.getenv("REDIS_PORT", "6379")
        services["redis"] = {
            "name": "Redis缓存",
            "host": redis_host,
            "port": redis_port,
            "status": "unknown"  # 实际实现时应该ping Redis
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
        for platform_info in PlatformConfig.list_enabled_platforms():
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