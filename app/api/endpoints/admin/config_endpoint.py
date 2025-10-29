# -*- coding: utf-8 -*-
"""配置管理端点 - 统一管理服务配置"""

from __future__ import annotations

import json
import os
from typing import List

from pydantic import BaseModel
from starlette.responses import JSONResponse

from fastmcp import FastMCP
from app.config.settings import Platform, global_settings
from app.providers.logger import get_logger
from app.api.endpoints import main_app

logger = get_logger()


class PlatformConfigUpdate(BaseModel):
    """平台配置更新"""

    enabled_platforms: List[str]


class CrawlerConfigUpdate(BaseModel):
    """爬虫配置更新（精简为当前实际可用项）"""

    headless: bool | None = None
    save_data_option: str | None = None
    output_dir: str | None = None
    enable_save_media: bool | None = None

@main_app.custom_route("/api/config/platforms", methods=["GET"])
async def get_platform_config(request):
    """获取平台配置"""
    try:
        enabled_codes = [
            p.value if hasattr(p, "value") else str(p)
            for p in global_settings.platform.enabled_platforms
        ]
        platform_names = {
            "bili": "哔哩哔哩",
            "xhs": "小红书",
            "dy": "抖音",
            "ks": "快手",
            "wb": "微博",
            "tieba": "贴吧",
            "zhihu": "知乎",
        }

        data = {
            "enabled_platforms": enabled_codes,
            "all_platforms": [p.value for p in Platform],
            "platform_names": platform_names,
        }
        return JSONResponse(content=data)

    except Exception as exc:
        logger.error(f"[配置管理] 获取平台配置失败: {exc}")
        return JSONResponse(content={"detail": str(exc)}, status_code=500)

@main_app.custom_route("/api/config/platforms", methods=["PUT"])
async def update_platform_config(request):
    """
    更新平台配置

    注意：这会修改环境变量，需要重启服务才能生效
    """
    try:
        body = await request.json()
        config = PlatformConfigUpdate(**body)

        invalid_platforms = set(config.enabled_platforms) - {p.value for p in Platform}
        if invalid_platforms:
            return JSONResponse(
                content={"detail": f"无效的平台代码: {invalid_platforms}"},
                status_code=400,
            )

        env_file = ".env"
        enabled_str = ",".join(config.enabled_platforms) if config.enabled_platforms else "all"

        env_lines: List[str] = []
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                env_lines = f.readlines()

        updated = False
        new_lines: List[str] = []
        for line in env_lines:
            if line.startswith("PLATFORM__ENABLED_PLATFORMS="):
                new_lines.append(f"PLATFORM__ENABLED_PLATFORMS={enabled_str}\n")
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            new_lines.append(f"\nPLATFORM__ENABLED_PLATFORMS={enabled_str}\n")

        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        logger.info(f"[配置管理] 平台配置已更新: {enabled_str}")

        return JSONResponse(
            content={
                "status": "success",
                "message": "平台配置已更新，请重启服务使配置生效",
                "enabled_platforms": config.enabled_platforms,
                "need_restart": True,
            }
        )

    except Exception as exc:
        logger.error(f"[配置管理] 更新平台配置失败: {exc}")
        return JSONResponse(content={"detail": str(exc)}, status_code=500)

@main_app.custom_route("/api/config/crawler", methods=["GET"])
async def get_crawler_config(request):
    """获取爬虫配置"""
    try:
        data = {
            "headless": bool(global_settings.browser.headless),
            "save_data_option": str(global_settings.store.save_format),
            "output_dir": getattr(global_settings.store, "output_dir", "./data"),
            "enable_save_media": bool(getattr(global_settings.store, "enable_save_media", False)),
        }
        return JSONResponse(content=data)

    except Exception as exc:
        logger.error(f"[配置管理] 获取爬虫配置失败: {exc}")
        return JSONResponse(content={"detail": str(exc)}, status_code=500)

@main_app.custom_route("/api/config/crawler", methods=["PUT"])
async def update_crawler_config(request):
    """
    更新爬虫配置

    注意：这会修改环境变量，需要重启服务才能生效
    """
    try:
        body = await request.json()
        config = CrawlerConfigUpdate(**body)

        env_file = ".env"
        env_lines: List[str] = []
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                env_lines = f.readlines()

        # 仅写入当前存在的配置项
        config_map: dict[str, str] = {}
        if config.headless is not None:
            config_map["BROWSER__HEADLESS"] = str(config.headless).lower()
        if config.save_data_option is not None:
            config_map["STORE__SAVE_FORMAT"] = config.save_data_option
        if config.output_dir is not None:
            config_map["STORE__OUTPUT_DIR"] = config.output_dir
        if config.enable_save_media is not None:
            config_map["STORE__ENABLE_SAVE_MEDIA"] = str(config.enable_save_media).lower()

        new_lines: List[str] = []
        updated_keys = set()
        for line in env_lines:
            key = line.split("=")[0].strip() if "=" in line else ""
            if key in config_map:
                new_lines.append(f"{key}={config_map[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)

        for key, value in config_map.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")

        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        logger.info("[配置管理] 爬虫配置已更新")

        return JSONResponse(
            content={
                "status": "success",
                "message": "爬虫配置已更新，请重启服务使配置生效",
                "config": config.model_dump(),
                "need_restart": True,
            }
        )

    except Exception as exc:
        logger.error(f"[配置管理] 更新爬虫配置失败: {exc}")
        return JSONResponse(content={"detail": str(exc)}, status_code=500)


@main_app.custom_route("/api/config/database", methods=["GET"])
async def get_database_config(request):
    """获取数据库配置（隐藏敏感信息）"""
    try:
        db_config = global_settings.database
        data = {
            "type": "PostgreSQL",
            "host": db_config.host,
            "port": str(db_config.port),
            "database": db_config.database,
            "user": db_config.user,
            "password": "******",  # 隐藏密码
        }
        return JSONResponse(content=data)

    except Exception as exc:
        logger.error(f"[配置管理] 获取数据库配置失败: {exc}")
        return JSONResponse(content={"detail": str(exc)}, status_code=500)


@main_app.custom_route("/api/config/current", methods=["GET"])
async def get_current_config(request):
    """获取当前完整配置"""
    try:
        platform_response = await get_platform_config(request)
        crawler_response = await get_crawler_config(request)
        database_response = await get_database_config(request)

        platform_config = json.loads(platform_response.body.decode())
        crawler_config = json.loads(crawler_response.body.decode())
        database_config = json.loads(database_response.body.decode())

        data = {
            "platform": platform_config,
            "crawler": crawler_config,
            "database": database_config,
            "app": {
                "name": global_settings.app.name,
                "version": global_settings.app.version,
                "env": global_settings.app.env,
                "debug": global_settings.app.debug,
                "port": global_settings.app.port,
            },
        }
        return JSONResponse(content=data)

    except Exception as exc:
        logger.error(f"[配置管理] 获取当前配置失败: {exc}")
        return JSONResponse(content={"detail": str(exc)}, status_code=500)
