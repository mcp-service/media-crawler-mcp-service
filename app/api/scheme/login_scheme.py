# -*- coding: utf-8 -*-
"""
登录 API 请求/响应模型
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.login.models import LoginStartPayload


class StartLoginRequest(BaseModel):
    """启动登录请求"""

    platform: str = Field(..., description="平台编码")
    login_type: str = Field("qrcode", description="登录方式，可选 qrcode/phone/cookie")
    phone: str = Field("", description="手机号（手机号登录使用）")
    cookie: str = Field("", description="Cookie 字符串（Cookie 登录使用）")

    model_config = {"extra": "ignore"}

    @field_validator("platform")
    @classmethod
    def normalize_platform(cls, value: str) -> str:
        if not value:
            raise ValueError("平台不能为空")
        return value.strip().lower()

    @field_validator("login_type")
    @classmethod
    def validate_login_type(cls, value: str) -> str:
        allowed = {"qrcode", "phone", "cookie"}
        norm = (value or "").strip().lower()
        if norm not in allowed:
            raise ValueError(f"不支持的登录方式: {value}")
        return norm

    def to_payload(self) -> LoginStartPayload:
        """转换为核心服务使用的载体"""
        return LoginStartPayload(
            platform=self.platform,
            login_type=self.login_type,
            phone=self.phone or "",
            cookie=self.cookie or "",
        )


class StartLoginResponse(BaseModel):
    status: str
    platform: str
    login_type: str
    message: str = ""
    session_id: Optional[str] = None
    qr_code_base64: Optional[str] = None
    qrcode_timestamp: float = 0.0


class LoginStatusResponse(BaseModel):
    platform: str
    platform_name: str
    is_logged_in: bool
    user_info: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""


class LogoutResponse(BaseModel):
    status: str
    platform: str
    message: str = ""


class SessionStatusResponse(BaseModel):
    session_id: str
    platform: str
    login_type: str
    status: str
    message: str = ""
    qr_code_base64: Optional[str] = None
    qrcode_timestamp: float = 0.0
    elapsed: float = 0.0


class PlatformSessionInfo(BaseModel):
    platform: str
    platform_name: str
    is_logged_in: bool
    last_login: str
    session_path: Optional[str] = None

