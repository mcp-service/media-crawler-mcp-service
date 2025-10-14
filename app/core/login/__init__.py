# -*- coding: utf-8 -*-
"""
登录核心模块

提供统一的登录服务入口以及平台适配器注册。
"""

from .exceptions import LoginServiceError
from .service import LoginService, login_service
from .models import LoginSession, PlatformLoginState, LoginStartPayload

__all__ = [
    "LoginServiceError",
    "LoginService",
    "login_service",
    "LoginSession",
    "PlatformLoginState",
    "LoginStartPayload",
]
