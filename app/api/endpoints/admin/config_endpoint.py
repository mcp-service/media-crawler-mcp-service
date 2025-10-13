# -*- coding: utf-8 -*-
"""
配置管理端点 - 统一管理服务配置
"""
import os
from typing import Dict, Any, List
from fastapi import HTTPException
from starlette.routing import Route, Mount
from pydantic import BaseModel

from app.api.endpoints.base import BaseEndpoint
from app.providers.logger import get_logger
from app.config.settings import global_settings, Platform


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


class ConfigEndpoint(BaseEndpoint):
    """配置管理端点"""

    def __init__(self):
        super().__init__("/admin/api/config", ["配置管理"])
        self.logger = get_logger()

    def register_routes(self):
        """注册路由"""
        from starlette.routing import Route
        from starlette.responses import JSONResponse
        import json

        async def get_platform_config_handler(request):
            """获取平台配置"""
            try:
                enabled = global_settings.platform.get_enabled_platforms()

                data = {
                    "enabled_platforms": list(enabled),
                    "all_platforms": list(Platform),
                    "platform_names": global_settings.platforms.PLATFORM_NAMES
                }
                return JSONResponse(content=data)

            except Exception as e:
                self.logger.error(f"[配置管理] 获取平台配置失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        async def update_platform_config_handler(request):
            """
            更新平台配置

            注意：这会修改环境变量，需要重启服务才能生效
            """
            try:
                body = await request.json()
                config = PlatformConfigUpdate(**body)

                # 验证平台代码
                invalid_platforms = set(config.enabled_platforms) - set(Platform)
                if invalid_platforms:
                    return JSONResponse(
                        content={"detail": f"无效的平台代码: {invalid_platforms}"},
                        status_code=400
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

                self.logger.info(f"[配置管理] 平台配置已更新: {enabled_str}")

                return JSONResponse(content={
                    "status": "success",
                    "message": "平台配置已更新，请重启服务使配置生效",
                    "enabled_platforms": config.enabled_platforms,
                    "need_restart": True
                })

            except Exception as e:
                self.logger.error(f"[配置管理] 更新平台配置失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        async def get_crawler_config_handler(request):
            """获取爬虫配置"""
            try:
                platform_config = global_settings.platforms
                data = {
                    "max_notes": int(os.getenv("MEDIA_CRAWLER_MAX_NOTES", str(platform_config.max_notes_per_request))),
                    "enable_comments": os.getenv("MEDIA_CRAWLER_ENABLE_COMMENTS", "true").lower() == "true",
                    "max_comments_per_note": int(os.getenv("MEDIA_CRAWLER_MAX_COMMENTS_PER_NOTE", str(platform_config.max_comments_per_note))),
                    "headless": os.getenv("MEDIA_CRAWLER_HEADLESS", str(platform_config.default_headless)).lower() == "true",
                    "save_data_option": os.getenv("MEDIA_CRAWLER_SAVE_DATA_OPTION", platform_config.default_save_format),
                    "default_login_type": os.getenv("DEFAULT_LOGIN_TYPE", platform_config.default_login_type)
                }
                return JSONResponse(content=data)

            except Exception as e:
                self.logger.error(f"[配置管理] 获取爬虫配置失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        async def update_crawler_config_handler(request):
            """
            更新爬虫配置

            注意：这会修改环境变量，需要重启服务才能生效
            """
            try:
                body = await request.json()
                config = CrawlerConfigUpdate(**body)

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

                self.logger.info(f"[配置管理] 爬虫配置已更新")

                return JSONResponse(content={
                    "status": "success",
                    "message": "爬虫配置已更新，请重启服务使配置生效",
                    "config": config.model_dump(),
                    "need_restart": True
                })

            except Exception as e:
                self.logger.error(f"[配置管理] 更新爬虫配置失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        async def get_database_config_handler(request):
            """获取数据库配置（隐藏敏感信息）"""
            try:
                db_config = global_settings.database
                data = {
                    "type": "PostgreSQL",
                    "host": os.getenv("DB_HOST", db_config.host),
                    "port": os.getenv("DB_PORT", str(db_config.port)),
                    "database": os.getenv("DB_NAME", db_config.database),
                    "user": os.getenv("DB_USER", db_config.user),
                    "password": "******"  # 隐藏密码
                }
                return JSONResponse(content=data)

            except Exception as e:
                self.logger.error(f"[配置管理] 获取数据库配置失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        async def get_current_config_handler(request):
            """获取当前完整配置"""
            try:
                # 调用其他处理器获取数据
                platform_response = await get_platform_config_handler(request)
                crawler_response = await get_crawler_config_handler(request)
                database_response = await get_database_config_handler(request)

                # 解析JSON响应
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
                        "port": global_settings.app.port
                    }
                }
                return JSONResponse(content=data)

            except Exception as e:
                self.logger.error(f"[配置管理] 获取当前配置失败: {e}")
                return JSONResponse(content={"detail": str(e)}, status_code=500)

        # 返回 Starlette 路由
        return [
            Route(f"{self.prefix}/platforms", get_platform_config_handler, methods=["GET"]),
            Route(f"{self.prefix}/platforms", update_platform_config_handler, methods=["PUT"]),
            Route(f"{self.prefix}/crawler", get_crawler_config_handler, methods=["GET"]),
            Route(f"{self.prefix}/crawler", update_crawler_config_handler, methods=["PUT"]),
            Route(f"{self.prefix}/database", get_database_config_handler, methods=["GET"]),
            Route(f"{self.prefix}/current", get_current_config_handler, methods=["GET"]),
        ]

    def register_mcp_tools(self, app):
        """不注册MCP工具，只提供HTTP API"""
        pass