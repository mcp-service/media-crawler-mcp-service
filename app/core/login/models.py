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
    browser_context: Optional[BrowserContext] = None
    context_page: Optional[Page] = None
    playwright: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

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
    user_info: Dict[str, Any] = field(default_factory=dict)
    cookie_dict: Dict[str, str] = field(default_factory=dict)
    cookie_str: str = ""
    message: str = ""
