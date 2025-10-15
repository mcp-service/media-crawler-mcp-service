# -*- coding: utf-8 -*-
"""
简化的配置管理模块
"""
from typing import Optional, Dict, Any, Set, List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from enum import Enum


def safe_print(message: str):
    """Windows safe print that handles emoji characters"""
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        # Fallback: remove emojis or use safe encoding
        safe_message = message.encode('ascii', 'ignore').decode('ascii')
        print(safe_message, flush=True)


# === 枚举类型 ===

class Platform(str, Enum):
    """支持的平台"""
    BILIBILI = "bili"
    XIAOHONGSHU = "xhs"
    DOUYIN = "dy"
    KUAISHOU = "ks"
    WEIBO = "wb"
    TIEBA = "tieba"
    ZHIHU = "zhihu"


class CrawlerType(str, Enum):
    """爬虫类型"""
    SEARCH = "search"      # 关键词搜索
    DETAIL = "detail"      # 指定内容详情
    CREATOR = "creator"    # 创作者主页


class LoginType(str, Enum):
    """登录类型"""
    QRCODE = "qrcode"      # 二维码登录
    PHONE = "phone"        # 手机号登录
    COOKIE = "cookie"      # Cookie登录


class SaveFormat(str, Enum):
    """数据保存格式"""
    JSON = "json"
    CSV = "csv"
    DATABASE = "db"
    SQLITE = "sqlite"


# === 配置子类 ===

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
    user: str = ''
    password: Optional[str] = None


class LoggerConfig(BaseModel):
    """日志配置"""
    level: str = 'INFO'
    log_file: Optional[str] = None
    enable_file: bool = False
    enable_console: bool = True
    max_file_size: str = '10 MB'
    retention_days: int = 7


class BrowserConfig(BaseModel):
    """浏览器配置"""
    headless: bool = True
    user_agent: Optional[str] = None
    proxy: Optional[str] = None
    user_data_dir: Optional[str] = None
    viewport_width: int = 1920
    viewport_height: int = 1080


class CrawlConfig(BaseModel):
    """爬取配置"""
    max_notes_count: int = 15
    max_comments_per_note: int = 10
    enable_get_comments: bool = True
    enable_get_sub_comments: bool = False
    max_concurrency: int = 5
    crawl_interval: float = 1.0  # 爬取间隔(秒)

    # 搜索模式配置
    search_mode: str = "normal"  # normal, all_in_time_range, daily_limit_in_time_range
    start_page: int = 1
    start_day: Optional[str] = None  # YYYY-MM-DD
    end_day: Optional[str] = None
    max_notes_per_day: int = 50


class StoreConfig(BaseModel):
    """存储配置"""
    save_format: SaveFormat = SaveFormat.JSON
    output_dir: str = "./data"
    enable_save_media: bool = False  # 是否保存图片/视频


class PlatformConfig(BaseModel):
    """平台配置"""
    enabled_platforms: List[Platform] = Field(
        default_factory=lambda: list(Platform),
        description="启用的平台列表，默认全部启用"
    )
    default_login_type: LoginType = LoginType.COOKIE
    default_headless: bool = False
    default_save_format: SaveFormat = SaveFormat.JSON

    @classmethod
    def parse_enabled_platforms(cls, value: Any) -> List[Platform]:
        """
        解析 enabled_platforms 配置

        支持格式：
        1. 字符串 "all" - 启用所有平台
        2. 字符串 "xhs,bili,dy" - 逗号分隔的平台代码
        3. List[Platform] - 直接的枚举列表
        """
        if isinstance(value, str):
            if value.lower() == "all":
                return list(Platform)
            # 逗号分隔的平台代码
            platforms = []
            for p in value.split(","):
                p = p.strip()
                try:
                    platforms.append(Platform(p))
                except ValueError:
                    pass
            return platforms if platforms else list(Platform)
        elif isinstance(value, list):
            return [Platform(p) if isinstance(p, str) else p for p in value]
        return list(Platform)

    def model_post_init(self, __context: Any) -> None:
        """Pydantic v2 post init hook"""
        # 如果从环境变量加载的是字符串，需要转换
        if hasattr(self, 'enabled_platforms') and isinstance(self.enabled_platforms, str):
            self.enabled_platforms = self.parse_enabled_platforms(self.enabled_platforms)


class CrawlerConfig(BaseModel):
    """
    爬虫统一配置类

    用于单次爬取任务的配置，从 GlobalSettings 继承默认值
    """
    # 平台和类型
    platform: Platform
    crawler_type: CrawlerType

    # 登录配置
    login_type: LoginType = LoginType.COOKIE
    cookie_str: Optional[str] = None
    phone: Optional[str] = None
    save_login_state: bool = True

    # 浏览器配置
    headless: bool = False
    user_agent: Optional[str] = None
    proxy: Optional[str] = None
    viewport_width: int = 1920
    viewport_height: int = 1080

    # 爬取目标
    keywords: Optional[str] = None  # 搜索关键词（逗号分隔）
    note_ids: Optional[List[str]] = None  # 指定内容ID列表
    note_urls: Optional[List[str]] = None  # 指定内容URL列表（兼容旧代码）
    creator_ids: Optional[List[str]] = None  # 创作者ID列表

    # 爬取参数
    max_notes_count: int = 15
    max_comments_per_note: int = 10
    enable_comments: bool = True
    enable_sub_comments: bool = False
    max_concurrency: int = 5
    crawl_interval: float = 1.0
    enable_get_comments: bool = True  # 兼容旧代码

    # 存储配置
    save_data_option: SaveFormat = SaveFormat.JSON
    output_dir: str = "./data"
    enable_save_media: bool = False

    # 搜索模式配置
    search_mode: str = "normal"
    start_page: int = 1
    start_day: Optional[str] = None
    end_day: Optional[str] = None
    max_notes_per_day: int = 50

    # 平台特定配置
    extra: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True

    def get(self, key: str, default: Any = None) -> Any:
        """兼容字典访问"""
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()


    @property
    def crawl(self):
        """模拟 crawl 配置对象"""
        class CrawlProxy:
            def __init__(self, parent):
                self.parent = parent

            @property
            def max_notes_count(self):
                return self.parent.max_notes_count

            @property
            def max_comments_per_note(self):
                return self.parent.max_comments_per_note

            @property
            def enable_get_comments(self):
                return self.parent.enable_get_comments

            @property
            def max_concurrency(self):
                return self.parent.max_concurrency

            @property
            def crawl_interval(self):
                return self.parent.crawl_interval

            @property
            def search_mode(self):
                return self.parent.search_mode

            @property
            def start_page(self):
                return self.parent.start_page

            @property
            def start_day(self):
                return self.parent.start_day

            @property
            def end_day(self):
                return self.parent.end_day

            @property
            def max_notes_per_day(self):
                return self.parent.max_notes_per_day

        return CrawlProxy(self)


def create_search_config(
    platform: Platform,
    keywords: str,
    max_notes: int = 15,
    enable_comments: bool = True,
    max_comments_per_note: int = 10,
    login_type: LoginType = LoginType.COOKIE,
    cookie_str: Optional[str] = None,
    headless: bool = False,
    **kwargs
) -> CrawlerConfig:
    """创建搜索爬取配置（工厂函数）"""
    return CrawlerConfig(
        platform=platform,
        crawler_type=CrawlerType.SEARCH,
        keywords=keywords,
        login_type=login_type,
        cookie_str=cookie_str,
        headless=headless,
        max_notes_count=max_notes,
        enable_comments=enable_comments,
        max_comments_per_note=max_comments_per_note,
        extra=kwargs
    )


def create_detail_config(
    platform: Platform,
    note_ids: List[str],
    enable_comments: bool = True,
    max_comments_per_note: int = 10,
    login_type: LoginType = LoginType.COOKIE,
    cookie_str: Optional[str] = None,
    headless: bool = False,
    **kwargs
) -> CrawlerConfig:
    """创建详情爬取配置（工厂函数）"""
    return CrawlerConfig(
        platform=platform,
        crawler_type=CrawlerType.DETAIL,
        note_ids=note_ids,
        note_urls=note_ids,  # 兼容旧代码
        login_type=login_type,
        cookie_str=cookie_str,
        headless=headless,
        enable_comments=enable_comments,
        max_comments_per_note=max_comments_per_note,
        extra=kwargs
    )


def create_creator_config(
    platform: Platform,
    creator_ids: List[str],
    enable_comments: bool = True,
    max_comments_per_note: int = 10,
    login_type: LoginType = LoginType.COOKIE,
    cookie_str: Optional[str] = None,
    headless: bool = False,
    **kwargs
) -> CrawlerConfig:
    """创建创作者爬取配置（工厂函数）"""
    return CrawlerConfig(
        platform=platform,
        crawler_type=CrawlerType.CREATOR,
        creator_ids=creator_ids,
        login_type=login_type,
        cookie_str=cookie_str,
        headless=headless,
        enable_comments=enable_comments,
        max_comments_per_note=max_comments_per_note,
        extra=kwargs
    )


class GlobalSettings(BaseSettings):
    """全局配置设置"""
    # 嵌套配置
    app: AppConfig = Field(default_factory=AppConfig)
    jwt: JWTConfig = Field(default_factory=JWTConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    logger: LoggerConfig = Field(default_factory=LoggerConfig)

    # 爬虫相关配置
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    crawl: CrawlConfig = Field(default_factory=CrawlConfig)
    store: StoreConfig = Field(default_factory=StoreConfig)
    platform: PlatformConfig = Field(default_factory=PlatformConfig)


    class Config:
        env_file = ".env"  # 默认从 .env 文件加载配置
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = "allow"
        # 支持嵌套环境变量，使用双下划线分隔
        env_nested_delimiter = '__'


def load_config() -> GlobalSettings:
    """
    加载配置的入口函数

    Pydantic Settings 会自动：
    1. 从 .env 文件加载环境变量
    2. 使用 env_nested_delimiter='__' 处理嵌套配置

    环境变量命名规则示例：
    - APP__PORT=5000
    - DATABASE__HOST=localhost
    - BROWSER__HEADLESS=true
    - CRAWL__MAX_NOTES_COUNT=20
    - PLATFORM__ENABLED_PLATFORMS=all
    """
    try:
        safe_print("🌍 使用 Pydantic Settings 加载配置（自动读取 .env）")
        settings = GlobalSettings()
        safe_print(f"✅ 配置加载成功: APP_ENV={settings.app.env}, APP_PORT={settings.app.port}")
        return settings
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