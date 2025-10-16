"""Crawler runtime context utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.config.settings import Platform, CrawlerType, LoginType


@dataclass
class LoginOptions:
    login_type: LoginType = LoginType.QRCODE
    cookie: Optional[str] = None
    phone: Optional[str] = None
    save_login_state: bool = True


@dataclass
class BrowserOptions:
    headless: bool = False
    user_agent: Optional[str] = None
    proxy: Optional[str] = None
    viewport_width: int = 1920
    viewport_height: int = 1080


@dataclass
class CrawlOptions:
    keywords: Optional[str] = None
    note_ids: Optional[List[str]] = None
    creator_ids: Optional[List[str]] = None
    max_notes_count: int = 15
    max_comments_per_note: int = 10
    enable_get_comments: bool = True
    enable_sub_comments: bool = False
    enable_save_media: bool = False
    max_concurrency: int = 5
    crawl_interval: float = 1.0
    search_mode: str = "normal"
    start_page: int = 1
    start_day: Optional[str] = None
    end_day: Optional[str] = None
    max_notes_per_day: int = 50


@dataclass
class StoreOptions:
    save_format: str = "json"
    enable_save_media: bool = False


@dataclass
class CrawlerContext:
    platform: Platform
    crawler_type: CrawlerType
    login: LoginOptions
    browser: BrowserOptions
    crawl: CrawlOptions
    store: StoreOptions
    extra: Dict[str, Any] = field(default_factory=dict)
