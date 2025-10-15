# -*- coding: utf-8 -*-
"""
登录服务相关数据模型
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from playwright.async_api import BrowserContext, Page


@dataclass
class LoginStartPayload:
    """登录启动请求载体（已验证的数据）"""

    platform: str
    login_type: str = "qrcode"
    phone: str = ""
    cookie: str = ""


@dataclass
class LoginSession:
    """登录会话实体"""

    id: str
    platform: str
    login_type: str
    status: str = "created"
    message: str = ""
    qr_code_base64: Optional[str] = None
    qrcode_timestamp: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    browser_context: Optional[BrowserContext] = None
    context_page: Optional[Page] = None
    playwright: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    runtime: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def touch(self):
        self.updated_at = time.time()

    def to_storage_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform,
            "login_type": self.login_type,
            "status": self.status,
            "message": self.message,
            "qr_code_base64": self.qr_code_base64,
            "qrcode_timestamp": self.qrcode_timestamp,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_storage_dict(cls, data: Dict[str, Any]) -> "LoginSession":
        session = cls(
            id=data["id"],
            platform=data["platform"],
            login_type=data.get("login_type", "qrcode"),
            status=data.get("status", "created"),
            message=data.get("message", ""),
            qr_code_base64=data.get("qr_code_base64"),
            qrcode_timestamp=data.get("qrcode_timestamp", 0.0),
            created_at=data.get("created_at", time.time()),
            metadata=data.get("metadata") or {},
        )
        session.updated_at = data.get("updated_at", session.created_at)
        return session

    def to_public_dict(self) -> Dict[str, Any]:
        """转换为前端可见的会话信息"""
        elapsed = 0.0
        if self.qrcode_timestamp:
            elapsed = max(0.0, time.time() - self.qrcode_timestamp)
        return {
            "session_id": self.id,
            "platform": self.platform,
            "login_type": self.login_type,
            "status": self.status,
            "message": self.message,
            "qr_code_base64": self.qr_code_base64,
            "qrcode_timestamp": self.qrcode_timestamp,
            "elapsed": elapsed,
        }


@dataclass
class PlatformLoginState:
    """平台登录状态缓存"""

    platform: str
    is_logged_in: bool = False
    last_checked_at: float = 0.0
    last_success_at: float = 0.0
    updated_at: float = field(default_factory=time.time)
    user_info: Dict[str, Any] = field(default_factory=dict)
    cookie_dict: Dict[str, str] = field(default_factory=dict)
    cookie_str: str = ""
    message: str = ""

    def touch(self):
        now = time.time()
        self.updated_at = now
        self.last_checked_at = now

    def to_storage_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "is_logged_in": self.is_logged_in,
            "last_checked_at": self.last_checked_at,
            "last_success_at": self.last_success_at,
            "updated_at": self.updated_at,
            "user_info": self.user_info,
            "cookie_dict": self.cookie_dict,
            "cookie_str": self.cookie_str,
            "message": self.message,
        }

    @classmethod
    def from_storage_dict(cls, data: Dict[str, Any]) -> "PlatformLoginState":
        state = cls(
            platform=data["platform"],
            is_logged_in=data.get("is_logged_in", False),
            last_checked_at=data.get("last_checked_at", 0.0),
            last_success_at=data.get("last_success_at", 0.0),
            user_info=data.get("user_info") or {},
            cookie_dict=data.get("cookie_dict") or {},
            cookie_str=data.get("cookie_str", ""),
            message=data.get("message", ""),
        )
        state.updated_at = data.get("updated_at", state.last_checked_at)
        return state
