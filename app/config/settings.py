# -*- coding: utf-8 -*-
"""
简化的配置管理模块
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


def safe_print(message: str):
    """Windows safe print that handles emoji characters"""
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        # Fallback: remove emojis or use safe encoding
        safe_message = message.encode('ascii', 'ignore').decode('ascii')
        print(safe_message, flush=True)


# 子类用于嵌套配置
class AppConfig(BaseModel):
    name: str = 'mcp-toolse'
    port: int = 5000
    debug: bool = True
    env: str = 'dev'
    version: str = '1.0.0'
    auto_reload: bool = False


class JWTConfig(BaseModel):
    """JWT认证配置"""
    secret_key: str = 'Ts3fw5#'
    algorithm: str = 'HS256'
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    issuer: str = 'tools'


class DatabaseConfig(BaseModel):
    """数据库配置"""
    host: str = 'localhost'
    port: int = 5432
    user: str = 'postgres'
    password: str = 'password'
    database: str = 'ai-tools'
    schema_name: str = 'public'
    maxsize: int = 10
    minsize: int = 1


class RedisConfig(BaseModel):
    """Redis配置"""
    host: str = 'localhost'
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


class LoggerConfig(BaseModel):
    """日志配置"""
    level: str = 'INFO'
    log_file: Optional[str] = None
    enable_file: bool = False
    enable_console: bool = True
    max_file_size: str = '10 MB'
    retention_days: int = 7


class GlobalSettings(BaseSettings):
    """全局配置设置"""
    # 嵌套配置
    app: AppConfig = AppConfig()
    jwt: JWTConfig = JWTConfig()
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    logger: LoggerConfig = LoggerConfig()

    class Config:
        env_file = ".env"  # 默认从 .env 文件加载配置
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = "allow"
        # 支持嵌套环境变量，使用双下划线分隔
        env_nested_delimiter = '__'


def load_from_yaml(yaml_file_path: str) -> Dict[str, Any]:
    """从 YAML 文件加载配置"""
    try:
        with open(yaml_file_path, 'r', encoding='utf-8') as file:
            config_data = yaml.safe_load(file)
            safe_print(f"✅ 从 YAML 文件加载配置成功: {yaml_file_path}")
            return config_data
    except Exception as e:
        safe_print(f"❌ 从 YAML 文件加载配置失败: {e}")
        return {}


def load_from_env() -> Dict[str, Any]:
    """从环境变量加载配置"""
    try:
        # 创建默认配置实例
        settings = GlobalSettings()
        safe_print("✅ 从环境变量加载配置成功")
        return settings.model_dump()
    except Exception as e:
        safe_print(f"❌ 从环境变量加载配置失败: {e}")
        return {}


def load_config() -> GlobalSettings:
    """加载配置的入口函数"""
    try:
        # 获取环境
        app_env = os.getenv('APP_ENV', 'dev')

        # 根据环境选择配置文件
        config_dir = Path(__file__).parent
        yaml_file_path = config_dir / f"{app_env}.yaml"

        # 优先从 YAML 文件加载
        if yaml_file_path.exists():
            yaml_config = load_from_yaml(str(yaml_file_path))
            if yaml_config:
                safe_print(f"📄 使用 YAML 文件配置: {yaml_file_path}")
                return GlobalSettings(**yaml_config)

        # 其次从环境变量加载
        safe_print("🌍 使用环境变量配置")
        return GlobalSettings()

    except Exception as e:
        safe_print(f"❌ 加载配置失败: {e}")
        # 返回默认配置
        return GlobalSettings()


# 全局配置实例
global_settings = load_config()


def create_db_config() -> dict:
    """创建数据库配置"""
    return {
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": global_settings.database.host,
                    "port": global_settings.database.port,
                    "user": global_settings.database.user,
                    "password": global_settings.database.password,
                    "database": global_settings.database.database,
                    "schema": global_settings.database.schema_name,
                    "maxsize": global_settings.database.maxsize,
                    "minsize": global_settings.database.minsize,
                    "command_timeout": 30,
                    "server_settings": {
                        "application_name": global_settings.app.name,
                        "tcp_keepalives_idle": "300",
                        "tcp_keepalives_interval": "30",
                        "tcp_keepalives_count": "3",
                    },
                    "ssl": "prefer",
                }
            }
        },
        "apps": {
            "models": {
                "models": [
                    "app.providers.models.identity.application",
                    "app.providers.models.config.data",
                    "app.providers.models.config.type",
                ],
                "default_connection": "default"
            }
        },
        "use_tz": False,
        "timezone": "Asia/Shanghai",
    }


def create_redis_config() -> dict:
    """创建Redis配置"""
    return {
        "host": global_settings.redis.host,
        "port": global_settings.redis.port,
        "db": global_settings.redis.db,
        "password": global_settings.redis.password,
        "decode_responses": True,
        "encoding": "utf-8",
    }