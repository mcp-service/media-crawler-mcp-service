# -*- coding: utf-8 -*-
"""
配置管理路由
"""
import os
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.providers.logger import get_logger
from app.config.settings import global_settings

router = APIRouter()


class PlatformConfigUpdate(BaseModel):
    """平台配置更新"""
    enabled_platforms: List[str]


class CrawlerConfigUpdate(BaseModel):
    """爬虫配置更新"""
    max_notes: int = 15
    enable_comments: bool = True
    max_comments_per_note: int = 10
    headless: bool = False
    save_data_option: str = "json"
    default_login_type: str = "qrcode"


class SidecarConfigUpdate(BaseModel):
    """边车服务配置更新"""
    url: str = "http://localhost:8001"
    browser_pool_size: int = 3
    timeout: float = 300.0
    session_timeout: int = 3600


@router.get("/platforms")
async def get_platform_config() -> Dict[str, Any]:
    """获取平台配置"""
    try:
        enabled = global_settings.platforms.get_enabled_platforms()
        all_platforms = global_settings.platforms.ALL_PLATFORMS

        return {
            "enabled_platforms": list(enabled),
            "all_platforms": list(all_platforms),
            "platform_names": global_settings.platforms.PLATFORM_NAMES
        }

    except Exception as e:
        get_logger().error(f"[配置管理] 获取平台配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/platforms")
async def update_platform_config(config: PlatformConfigUpdate) -> Dict[str, Any]:
    """
    更新平台配置

    注意：这会修改环境变量，需要重启服务才能生效
    """
    try:
        # 验证平台代码
        invalid_platforms = set(config.enabled_platforms) - global_settings.platforms.ALL_PLATFORMS
        if invalid_platforms:
            raise HTTPException(
                status_code=400,
                detail=f"无效的平台代码: {invalid_platforms}"
            )

        # 更新.env文件
        env_file = ".env"
        enabled_str = ",".join(config.enabled_platforms) if config.enabled_platforms else "all"

        # 读取现有.env文件
        env_lines = []
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                env_lines = f.readlines()

        # 更新ENABLED_PLATFORMS配置
        updated = False
        new_lines = []
        for line in env_lines:
            if line.startswith("ENABLED_PLATFORMS="):
                new_lines.append(f"ENABLED_PLATFORMS={enabled_str}\n")
                updated = True
            else:
                new_lines.append(line)

        # 如果没找到配置行，添加它
        if not updated:
            new_lines.append(f"\nENABLED_PLATFORMS={enabled_str}\n")

        # 写回文件
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        get_logger().info(f"[配置管理] 平台配置已更新: {enabled_str}")

        return {
            "status": "success",
            "message": "平台配置已更新，请重启服务使配置生效",
            "enabled_platforms": config.enabled_platforms,
            "need_restart": True
        }

    except Exception as e:
        get_logger().error(f"[配置管理] 更新平台配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/crawler")
async def get_crawler_config() -> Dict[str, Any]:
    """获取爬虫配置"""
    try:
        platform_config = global_settings.platforms
        return {
            "max_notes": int(os.getenv("MEDIA_CRAWLER_MAX_NOTES", str(platform_config.max_notes_per_request))),
            "enable_comments": os.getenv("MEDIA_CRAWLER_ENABLE_COMMENTS", "true").lower() == "true",
            "max_comments_per_note": int(os.getenv("MEDIA_CRAWLER_MAX_COMMENTS_PER_NOTE", str(platform_config.max_comments_per_note))),
            "headless": os.getenv("MEDIA_CRAWLER_HEADLESS", str(platform_config.default_headless)).lower() == "true",
            "save_data_option": os.getenv("MEDIA_CRAWLER_SAVE_DATA_OPTION", platform_config.default_save_format),
            "default_login_type": os.getenv("DEFAULT_LOGIN_TYPE", platform_config.default_login_type)
        }

    except Exception as e:
        get_logger().error(f"[配置管理] 获取爬虫配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/crawler")
async def update_crawler_config(config: CrawlerConfigUpdate) -> Dict[str, Any]:
    """
    更新爬虫配置

    注意：这会修改环境变量，需要重启服务才能生效
    """
    try:
        # 更新.env文件
        env_file = ".env"
        env_lines = []
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                env_lines = f.readlines()

        # 配置项映射
        config_map = {
            "MEDIA_CRAWLER_MAX_NOTES": str(config.max_notes),
            "MEDIA_CRAWLER_ENABLE_COMMENTS": str(config.enable_comments).lower(),
            "MEDIA_CRAWLER_MAX_COMMENTS_PER_NOTE": str(config.max_comments_per_note),
            "MEDIA_CRAWLER_HEADLESS": str(config.headless).lower(),
            "MEDIA_CRAWLER_SAVE_DATA_OPTION": config.save_data_option
        }

        # 更新配置
        new_lines = []
        updated_keys = set()

        for line in env_lines:
            key = line.split("=")[0].strip() if "=" in line else ""
            if key in config_map:
                new_lines.append(f"{key}={config_map[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)

        # 添加未找到的配置
        for key, value in config_map.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")

        # 写回文件
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        get_logger().info(f"[配置管理] 爬虫配置已更新")

        return {
            "status": "success",
            "message": "爬虫配置已更新，请重启服务使配置生效",
            "config": config.dict(),
            "need_restart": True
        }

    except Exception as e:
        get_logger().error(f"[配置管理] 更新爬虫配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sidecar")
async def get_sidecar_config() -> Dict[str, Any]:
    """获取边车服务配置"""
    try:
        sidecar_config = global_settings.sidecar
        return {
            "url": os.getenv("MEDIA_CRAWLER_SIDECAR_URL", sidecar_config.url),
            "browser_pool_size": int(os.getenv("BROWSER_POOL_SIZE", str(sidecar_config.browser_pool_size))),
            "timeout": float(os.getenv("SIDECAR_TIMEOUT", str(sidecar_config.timeout))),
            "session_timeout": int(os.getenv("SESSION_TIMEOUT", str(sidecar_config.session_timeout))),
            "enable_browser_pool": sidecar_config.enable_browser_pool
        }

    except Exception as e:
        get_logger().error(f"[配置管理] 获取边车配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sidecar")
async def update_sidecar_config(config: SidecarConfigUpdate) -> Dict[str, Any]:
    """
    更新边车服务配置

    注意：这会修改环境变量，需要重启服务才能生效
    """
    try:
        # 更新.env文件
        env_file = ".env"
        env_lines = []
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                env_lines = f.readlines()

        # 配置项映射
        config_map = {
            "MEDIA_CRAWLER_SIDECAR_URL": config.url,
            "BROWSER_POOL_SIZE": str(config.browser_pool_size),
            "SIDECAR_TIMEOUT": str(config.timeout),
            "SESSION_TIMEOUT": str(config.session_timeout)
        }

        # 更新配置
        new_lines = []
        updated_keys = set()

        for line in env_lines:
            key = line.split("=")[0].strip() if "=" in line else ""
            if key in config_map:
                new_lines.append(f"{key}={config_map[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)

        # 添加未找到的配置
        for key, value in config_map.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")

        # 写回文件
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        get_logger().info(f"[配置管理] 边车配置已更新")

        return {
            "status": "success",
            "message": "边车配置已更新，请重启服务使配置生效",
            "config": config.dict(),
            "need_restart": True
        }

    except Exception as e:
        get_logger().error(f"[配置管理] 更新边车配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database")
async def get_database_config() -> Dict[str, Any]:
    """获取数据库配置（隐藏敏感信息）"""
    try:
        db_config = global_settings.database
        return {
            "type": "PostgreSQL",
            "host": os.getenv("DB_HOST", db_config.host),
            "port": os.getenv("DB_PORT", str(db_config.port)),
            "database": os.getenv("DB_NAME", db_config.database),
            "user": os.getenv("DB_USER", db_config.user),
            "password": "******"  # 隐藏密码
        }

    except Exception as e:
        get_logger().error(f"[配置管理] 获取数据库配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current")
async def get_current_config() -> Dict[str, Any]:
    """获取当前完整配置"""
    try:
        platform_config = await get_platform_config()
        crawler_config = await get_crawler_config()
        sidecar_config = await get_sidecar_config()
        database_config = await get_database_config()
        
        return {
            "platform": platform_config,
            "crawler": crawler_config,
            "sidecar": sidecar_config,
            "database": database_config,
            "app": {
                "name": global_settings.app.name,
                "version": global_settings.app.version,
                "env": global_settings.app.env,
                "debug": global_settings.app.debug,
                "port": global_settings.app.port
            }
        }
    
    except Exception as e:
        get_logger().error(f"[配置管理] 获取当前配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))