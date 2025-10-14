# -*- coding: utf-8 -*-
"""
登录适配器基础类
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from app.providers.logger import get_logger

from .models import LoginSession, LoginStartPayload, PlatformLoginState

if TYPE_CHECKING:
    from .service import LoginService


class BaseLoginAdapter:
    """平台登录适配器基类"""

    def __init__(self, service: "LoginService"):
        self.service = service
        self.logger = get_logger()

    @property
    def platform(self) -> str:
        raise NotImplementedError

    @property
    def display_name(self) -> str:
        return self.platform

    @property
    def user_data_dir(self) -> Path:
        raise NotImplementedError

    async def start_login(self, session: LoginSession, payload: LoginStartPayload) -> Dict[str, Any]:
        raise NotImplementedError

    async def fetch_login_state(self) -> PlatformLoginState:
        raise NotImplementedError

    async def logout(self) -> None:
        raise NotImplementedError

    def format_last_login(self, state: PlatformLoginState) -> str:
        """格式化最近登录时间"""
        if state.last_success_at:
            from time import localtime, strftime

            return strftime("%Y-%m-%d %H:%M:%S", localtime(state.last_success_at))
        return "从未登录"
