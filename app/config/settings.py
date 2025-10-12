# -*- coding: utf-8 -*-
"""
简化的配置管理模块
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, Set, List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from enum import Enum
from dataclasses import dataclass


def safe_print(message: str):
    """Windows safe print that handles emoji characters"""
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        # Fallback: remove emojis or use safe encoding
        safe_message = message.encode('ascii', 'ignore').decode('ascii')
        print(safe_message, flush=True)


# === 平台和爬虫相关枚举 ===

class PlatformCode(str, Enum):
    """平台代码枚举"""
    XHS = "xhs"         # 小红书
    DOUYIN = "dy"       # 抖音
    KUAISHOU = "ks"     # 快手
    BILIBILI = "bili"   # B站
    WEIBO = "wb"        # 微博
    TIEBA = "tieba"     # 贴吧
    ZHIHU = "zhihu"     # 知乎


class CrawlerType(str, Enum):
    """爬虫类型枚举"""
    SEARCH = "search"   # 关键词搜索
    DETAIL = "detail"   # 指定内容
    CREATOR = "creator" # 创作者主页


class LoginType(str, Enum):
    """登录类型枚举"""
    QRCODE = "qrcode"   # 二维码登录
    PHONE = "phone"     # 手机号登录
    COOKIE = "cookie"   # Cookie登录


class SaveFormat(str, Enum):
    """保存格式枚举"""
    JSON = "json"
    CSV = "csv"
    DB = "db"
    SQLITE = "sqlite"


@dataclass
class CrawlerConfig:
    """爬虫配置"""
    platform: str
    crawler_type: str  # search, detail, creator
    keywords: Optional[str] = None
    max_notes_count: int = 15
    enable_comments: bool = True
    max_comments_per_note: int = 10
    login_type: str = "qrcode"  # qrcode, phone, cookie
    headless: bool = False
    save_data_option: str = "json"  # json, csv, db, sqlite

    # 平台特定配置
    note_urls: Optional[list] = None
    creator_ids: Optional[list] = None


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


class SidecarConfig(BaseModel):
    """边车服务配置"""
    url: str = 'http://localhost:8001'
    timeout: float = 300.0  # 5分钟超时
    max_retries: int = 3
    enable_browser_pool: bool = True
    browser_pool_size: int = 3
    session_timeout: int = 3600  # 1小时


class PlatformSettings(BaseModel):
    """平台设置配置"""
    enabled_platforms: str = 'all'  # all 或 逗号分隔的平台代码
    default_login_type: str = 'cookie'
    default_headless: bool = False
    default_save_format: str = 'json'
    max_notes_per_request: int = 50
    max_comments_per_note: int = 20
    
    # 平台常量
    ALL_PLATFORMS: Set[str] = {
        PlatformCode.XHS, PlatformCode.DOUYIN, PlatformCode.KUAISHOU,
        PlatformCode.BILIBILI, PlatformCode.WEIBO, PlatformCode.TIEBA, PlatformCode.ZHIHU
    }
    
    PLATFORM_NAMES: Dict[str, str] = {
        PlatformCode.XHS: "小红书",
        PlatformCode.DOUYIN: "抖音",
        PlatformCode.KUAISHOU: "快手",
        PlatformCode.BILIBILI: "B站",
        PlatformCode.WEIBO: "微博",
        PlatformCode.TIEBA: "贴吧",
        PlatformCode.ZHIHU: "知乎",
    }
    
    PLATFORM_URLS: Dict[str, str] = {
        PlatformCode.XHS: "https://www.xiaohongshu.com",
        PlatformCode.DOUYIN: "https://www.douyin.com",
        PlatformCode.KUAISHOU: "https://www.kuaishou.com",
        PlatformCode.BILIBILI: "https://www.bilibili.com",
        PlatformCode.WEIBO: "https://weibo.com",
        PlatformCode.TIEBA: "https://tieba.baidu.com",
        PlatformCode.ZHIHU: "https://www.zhihu.com",
    }
    
    PLATFORM_COOKIES: Dict[str, str] = {
        PlatformCode.XHS: "web_session",
        PlatformCode.DOUYIN: "sessionid", 
        PlatformCode.BILIBILI: "SESSDATA",
        PlatformCode.WEIBO: "SUB",
        PlatformCode.TIEBA: "BDUSS",
        PlatformCode.ZHIHU: "z_c0",
        PlatformCode.KUAISHOU: "kpf",
    }
    
    def get_enabled_platforms(self) -> Set[str]:
        """获取启用的平台列表"""
        enabled_str = os.getenv("ENABLED_PLATFORMS", self.enabled_platforms).strip().lower()
        
        if enabled_str == "all" or not enabled_str:
            return self.ALL_PLATFORMS.copy()
        
        platforms = {p.strip() for p in enabled_str.split(",")}
        valid_platforms = platforms & self.ALL_PLATFORMS
        
        if not valid_platforms:
            return self.ALL_PLATFORMS.copy()
        
        return valid_platforms
    
    def is_platform_enabled(self, platform_code: str) -> bool:
        """检查平台是否启用"""
        return platform_code in self.get_enabled_platforms()
    
    def get_platform_name(self, platform_code: str) -> str:
        """获取平台中文名称"""
        return self.PLATFORM_NAMES.get(platform_code, platform_code)
    
    def get_platform_url(self, platform_code: str) -> str:
        """获取平台URL"""
        return self.PLATFORM_URLS.get(platform_code, "")
    
    def get_platform_cookie_name(self, platform_code: str) -> str:
        """获取平台特有Cookie名称"""
        return self.PLATFORM_COOKIES.get(platform_code, "")
    
    def list_enabled_platforms(self) -> List[Dict[str, str]]:
        """列出所有启用的平台信息"""
        enabled = self.get_enabled_platforms()
        return [
            {
                "code": code, 
                "name": self.PLATFORM_NAMES[code],
                "url": self.PLATFORM_URLS[code]
            }
            for code in sorted(enabled)
        ]
    
    def validate_platform(self, platform_code: str) -> bool:
        """验证平台代码是否支持"""
        return platform_code in self.ALL_PLATFORMS
    
    def validate_crawler_type(self, crawler_type: str) -> bool:
        """验证爬虫类型是否支持"""
        return crawler_type in {e.value for e in CrawlerType}
    
    def validate_login_type(self, login_type: str) -> bool:
        """验证登录类型是否支持"""
        return login_type in {e.value for e in LoginType}
    
    def validate_save_format(self, save_format: str) -> bool:
        """验证保存格式是否支持"""
        return save_format in {e.value for e in SaveFormat}
    
    def get_platform_config_summary(self) -> Dict[str, Any]:
        """获取平台配置概述"""
        return {
            "enabled_platforms": list(self.get_enabled_platforms()),
            "total_platforms": len(self.ALL_PLATFORMS),
            "supported_platforms": list(self.ALL_PLATFORMS),
            "crawler_types": [e.value for e in CrawlerType],
            "login_types": [e.value for e in LoginType],
            "save_formats": [e.value for e in SaveFormat],
        }


class GlobalSettings(BaseSettings):
    """全局配置设置"""
    # 嵌套配置
    app: AppConfig = AppConfig()
    jwt: JWTConfig = JWTConfig()
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    logger: LoggerConfig = LoggerConfig()
    sidecar: SidecarConfig = SidecarConfig()
    platforms: PlatformSettings = PlatformSettings()

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
                settings = GlobalSettings(**yaml_config)
                # 从环境变量覆盖特定配置
                _override_from_env(settings)
                return settings

        # 其次从环境变量加载
        safe_print("🌍 使用环境变量配置")
        settings = GlobalSettings()
        _override_from_env(settings)
        return settings

    except Exception as e:
        safe_print(f"❌ 加载配置失败: {e}")
        # 返回默认配置
        settings = GlobalSettings()
        _override_from_env(settings)
        return settings


def _override_from_env(settings: GlobalSettings) -> None:
    """从环境变量覆盖配置（支持单下划线格式）"""
    # APP 配置
    if port := os.getenv('APP_PORT'):
        settings.app.port = int(port)
    if debug := os.getenv('APP_DEBUG'):
        settings.app.debug = debug.lower() in ('true', '1', 'yes')
    if env := os.getenv('APP_ENV'):
        settings.app.env = env

    # Database 配置
    if db_host := os.getenv('DB_HOST'):
        settings.database.host = db_host
    if db_port := os.getenv('DB_PORT'):
        settings.database.port = int(db_port)
    if db_user := os.getenv('DB_USER'):
        settings.database.user = db_user
    if db_password := os.getenv('DB_PASSWORD'):
        settings.database.password = db_password
    if db_name := os.getenv('DB_NAME'):
        settings.database.database = db_name

    # Redis 配置
    if redis_host := os.getenv('REDIS_HOST'):
        settings.redis.host = redis_host
    if redis_port := os.getenv('REDIS_PORT'):
        settings.redis.port = int(redis_port)
    if redis_password := os.getenv('REDIS_PASSWORD'):
        settings.redis.password = redis_password if redis_password else None
    if redis_db := os.getenv('REDIS_DB'):
        settings.redis.db = int(redis_db)
    
    # Sidecar 配置
    if sidecar_url := os.getenv('MEDIA_CRAWLER_SIDECAR_URL'):
        settings.sidecar.url = sidecar_url
    if sidecar_timeout := os.getenv('SIDECAR_TIMEOUT'):
        settings.sidecar.timeout = float(sidecar_timeout)
    if browser_pool_size := os.getenv('BROWSER_POOL_SIZE'):
        settings.sidecar.browser_pool_size = int(browser_pool_size)
    
    # Platform 配置
    if enabled_platforms := os.getenv('ENABLED_PLATFORMS'):
        settings.platforms.enabled_platforms = enabled_platforms
    if default_login_type := os.getenv('DEFAULT_LOGIN_TYPE'):
        settings.platforms.default_login_type = default_login_type
    if default_headless := os.getenv('DEFAULT_HEADLESS'):
        settings.platforms.default_headless = default_headless.lower() in ('true', '1', 'yes')


# 全局配置实例
global_settings = load_config()


# === MediaCrawler 配置适配器 ===

class MediaCrawlerConfigAdapter:
    """
    MediaCrawler 配置适配器
    
    将 GlobalSettings 配置注入到 media_crawler 的 config 模块中
    """
    
    def __init__(self, global_settings: 'GlobalSettings'):
        self.global_settings = global_settings
        # 延迟导入logger避免循环依赖
        self._logger = None
    
    @property
    def logger(self):
        if self._logger is None:
            try:
                from app.providers.logger import get_logger
                self._logger = get_logger()
            except ImportError:
                # 如果无法导入logger，使用基本的print
                class SimpleLogger:
                    def debug(self, msg): print(f"DEBUG: {msg}")
                    def info(self, msg): print(f"INFO: {msg}")
                    def error(self, msg): print(f"ERROR: {msg}")
                self._logger = SimpleLogger()
        return self._logger
    
    def inject_config(self, crawler_config: CrawlerConfig) -> None:
        """
        注入配置到 media_crawler 的 config 模块
        """
        try:
            # 添加 media_crawler 到 Python 路径
            import sys
            MEDIA_CRAWLER_PATH = Path(__file__).parent.parent.parent / "media_crawler"
            if str(MEDIA_CRAWLER_PATH) not in sys.path:
                sys.path.insert(0, str(MEDIA_CRAWLER_PATH))
            
            # 动态导入 media_crawler 的 config 模块
            import config as mc_config

            # === 基础配置 ===
            mc_config.PLATFORM = crawler_config.platform
            mc_config.CRAWLER_TYPE = crawler_config.crawler_type
            mc_config.LOGIN_TYPE = crawler_config.login_type
            mc_config.HEADLESS = crawler_config.headless
            mc_config.SAVE_DATA_OPTION = crawler_config.save_data_option

            # === 爬取参数 ===
            if crawler_config.keywords:
                mc_config.KEYWORDS = crawler_config.keywords

            mc_config.CRAWLER_MAX_NOTES_COUNT = crawler_config.max_notes_count
            mc_config.ENABLE_GET_COMMENTS = crawler_config.enable_comments
            mc_config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = crawler_config.max_comments_per_note

            # === 平台特定配置 ===
            self._inject_platform_specific_config(mc_config, crawler_config)

            # === 数据库配置（从 GlobalSettings 注入）===
            if crawler_config.save_data_option in ["db", "sqlite"]:
                self._inject_database_config(mc_config)

            self.logger.debug(
                f"配置已注入: platform={crawler_config.platform}, "
                f"type={crawler_config.crawler_type}"
            )

        except Exception as e:
            self.logger.error(f"配置注入失败: {e}")
            raise
    
    def _inject_platform_specific_config(self, mc_config: Any, crawler_config: CrawlerConfig) -> None:
        """注入平台特定配置"""
        platform = crawler_config.platform

        # 根据 crawler_type 设置对应的配置
        if crawler_config.crawler_type == "detail" and crawler_config.note_urls:
            if platform == "xhs":
                mc_config.XHS_SPECIFIED_NOTE_URL_LIST = crawler_config.note_urls
            elif platform == "dy":
                mc_config.DY_SPECIFIED_ID_LIST = crawler_config.note_urls
            elif platform == "ks":
                mc_config.KS_SPECIFIED_ID_LIST = crawler_config.note_urls
            elif platform == "bili":
                mc_config.BILI_SPECIFIED_ID_LIST = crawler_config.note_urls
            elif platform == "wb":
                mc_config.WEIBO_SPECIFIED_ID_LIST = crawler_config.note_urls
            elif platform == "tieba":
                mc_config.TIEBA_SPECIFIED_POST_ID_LIST = crawler_config.note_urls
            elif platform == "zhihu":
                mc_config.ZHIHU_SPECIFIED_ID_LIST = crawler_config.note_urls

        elif crawler_config.crawler_type == "creator" and crawler_config.creator_ids:
            if platform == "xhs":
                mc_config.XHS_CREATOR_ID_LIST = crawler_config.creator_ids
            elif platform == "dy":
                mc_config.DY_CREATOR_ID_LIST = crawler_config.creator_ids
            elif platform == "ks":
                mc_config.KS_CREATOR_ID_LIST = crawler_config.creator_ids
            elif platform == "bili":
                mc_config.BILI_CREATOR_ID_LIST = crawler_config.creator_ids
            elif platform == "wb":
                mc_config.WEIBO_CREATOR_ID_LIST = crawler_config.creator_ids
    
    def _inject_database_config(self, mc_config: Any) -> None:
        """注入数据库配置（从 GlobalSettings）"""
        db_config = self.global_settings.database

        # 注入数据库连接信息
        mc_config.MYSQL_DB_HOST = db_config.host
        mc_config.MYSQL_DB_PORT = db_config.port
        mc_config.MYSQL_DB_USER = db_config.user
        mc_config.MYSQL_DB_PWD = db_config.password
        mc_config.MYSQL_DB_NAME = db_config.database

        self.logger.debug(
            f"数据库配置已注入: {db_config.host}:{db_config.port}/{db_config.database}"
        )
    
    def get_media_crawler_config(self) -> Dict[str, Any]:
        """
        获取当前 media_crawler 的配置快照
        """
        try:
            import sys
            MEDIA_CRAWLER_PATH = Path(__file__).parent.parent.parent / "media_crawler"
            if str(MEDIA_CRAWLER_PATH) not in sys.path:
                sys.path.insert(0, str(MEDIA_CRAWLER_PATH))
            
            import config as mc_config

            config_dict = {}
            for attr in dir(mc_config):
                if attr.isupper() and not attr.startswith('_'):
                    config_dict[attr] = getattr(mc_config, attr)

            return config_dict

        except Exception as e:
            self.logger.error(f"获取配置失败: {e}")
            return {}


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