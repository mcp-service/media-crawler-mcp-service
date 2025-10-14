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
                enabled_codes = [p.value if hasattr(p, 'value') else str(p) for p in global_settings.platform.enabled_platforms]
                platform_names = {
                    "bili": "哔哩哔哩",
                    "xhs": "小红书",
                    "dy": "抖音",
                    "ks": "快手",
                    "wb": "微博",
                    "tieba": "贴吧",
                    "zhihu": "知乎"
                }

                data = {
                    "enabled_platforms": enabled_codes,
                    "all_platforms": [p.value for p in Platform],
                    "platform_names": platform_names
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
                invalid_platforms = set(config.enabled_platforms) - set([p.value for p in Platform])
                if invalid_platforms:
                    return JSONResponse(
                        content={"detail": f"无效的平台代码: {invalid_platforms}"},
                        status_code=400
                    )

                # 更新 .env 文件（嵌套结构）
                env_file = ".env"
                enabled_str = ",".join(config.enabled_platforms) if config.enabled_platforms else "all"

                # 读取现有.env文件
                env_lines = []
                if os.path.exists(env_file):
                    with open(env_file, "r", encoding="utf-8") as f:
                        env_lines = f.readlines()

                # 更新 PLATFORM__ENABLED_PLATFORMS 配置
                updated = False
                new_lines = []
                for line in env_lines:
                    if line.startswith("PLATFORM__ENABLED_PLATFORMS="):
                        new_lines.append(f"PLATFORM__ENABLED_PLATFORMS={enabled_str}\n")
                        updated = True
                    else:
                        new_lines.append(line)

                # 如果没找到配置行，添加它
                if not updated:
                    new_lines.append(f"\nPLATFORM__ENABLED_PLATFORMS={enabled_str}\n")

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
                data = {
                    "max_notes": int(global_settings.crawl.max_notes_count),
                    "enable_comments": bool(global_settings.crawl.enable_get_comments),
                    "max_comments_per_note": int(global_settings.crawl.max_comments_per_note),
                    "headless": bool(global_settings.browser.headless),
                    "save_data_option": str(global_settings.store.save_format),
                    "default_login_type": str(global_settings.platform.default_login_type)
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

                # 配置项映射（嵌套结构）
                config_map = {
                    "CRAWL__MAX_NOTES_COUNT": str(config.max_notes),
                    "CRAWL__ENABLE_GET_COMMENTS": str(config.enable_comments).lower(),
                    "CRAWL__MAX_COMMENTS_PER_NOTE": str(config.max_comments_per_note),
                    "BROWSER__HEADLESS": str(config.headless).lower(),
                    "STORE__SAVE_FORMAT": config.save_data_option,
                    "PLATFORM__DEFAULT_LOGIN_TYPE": config.default_login_type
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
                    "host": db_config.host,
                    "port": str(db_config.port),
                    "database": db_config.database,
                    "user": db_config.user,
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
