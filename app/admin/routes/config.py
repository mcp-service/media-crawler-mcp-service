# -*- coding: utf-8 -*-
"""
配置管理路由
"""
import os
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.providers.logger import get_logger
from app.config.platform_config import PlatformConfig

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


@router.get("/platforms")
async def get_platform_config() -> Dict[str, Any]:
    """获取平台配置"""
    try:
        enabled = PlatformConfig.get_enabled_platforms()
        all_platforms = PlatformConfig.ALL_PLATFORMS

        return {
            "enabled_platforms": list(enabled),
            "all_platforms": list(all_platforms),
            "platform_names": PlatformConfig.PLATFORM_NAMES
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
        invalid_platforms = set(config.enabled_platforms) - PlatformConfig.ALL_PLATFORMS
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
        return {
            "max_notes": int(os.getenv("MEDIA_CRAWLER_MAX_NOTES", "15")),
            "enable_comments": os.getenv("MEDIA_CRAWLER_ENABLE_COMMENTS", "true").lower() == "true",
            "max_comments_per_note": int(os.getenv("MEDIA_CRAWLER_MAX_COMMENTS_PER_NOTE", "10")),
            "headless": os.getenv("MEDIA_CRAWLER_HEADLESS", "false").lower() == "true",
            "save_data_option": os.getenv("MEDIA_CRAWLER_SAVE_DATA_OPTION", "json")
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


@router.get("/database")
async def get_database_config() -> Dict[str, Any]:
    """获取数据库配置（隐藏敏感信息）"""
    try:
        return {
            "type": "PostgreSQL",
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "database": os.getenv("DB_NAME", "mcp_tools_db"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": "******"  # 隐藏密码
        }

    except Exception as e:
        get_logger().error(f"[配置管理] 获取数据库配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))