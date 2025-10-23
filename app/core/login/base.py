# -*- coding: utf-8 -*-
"""
登录基础类和接口定义
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from playwright.async_api import BrowserContext, Page

from app.providers.logger import get_logger

from .models import LoginSession, LoginStartPayload, PlatformLoginState

if TYPE_CHECKING:
    from .service import LoginService

logger = get_logger()


class AbstractLogin(ABC):
    """
    登录抽象基类
    
    各平台登录类需要继承此类并实现所有抽象方法
    """

    def __init__(
        self,
        service: "LoginService",
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        login_phone: Optional[str] = "",
        cookie_str: str = ""
    ):
        """
        初始化登录对象

        Args:
            service: 登录服务实例
            login_type: 登录类型 (qrcode, phone, cookie)
            browser_context: 浏览器上下文
            context_page: 页面对象
            login_phone: 手机号（手机登录时使用）
            cookie_str: Cookie字符串（Cookie登录时使用）
        """
        self.service = service
        self.login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str
        self.logger = get_logger()

    @property
    @abstractmethod
    def platform(self) -> str:
        """平台标识"""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """平台显示名称"""
        pass

    @property
    @abstractmethod
    def user_data_dir(self) -> Path:
        """浏览器数据目录"""
        pass

    @abstractmethod
    async def begin(self):
        """开始登录流程"""
        pass

    @abstractmethod
    async def login_by_qrcode(self):
        """二维码登录"""
        pass

    @abstractmethod
    async def login_by_mobile(self):
        """手机号登录"""
        pass

    @abstractmethod
    async def login_by_cookies(self):
        """Cookie登录"""
        pass

    @abstractmethod
    async def has_valid_cookie(self) -> bool:
        """检查是否有有效的Cookie"""
        pass

    @abstractmethod
    async def fetch_login_state(self) -> PlatformLoginState:
        """获取当前登录状态"""
        pass

    async def cleanup_browser_resources(self):
        """清理浏览器资源"""
        if self.browser_context:
            try:
                await self.browser_context.close()
            except Exception as exc:
                self.logger.warning(f"[{self.platform}] 关闭浏览器上下文失败: {exc}")
        
        if hasattr(self, 'playwright') and self.playwright:
            try:
                await self.playwright.stop()
            except Exception as exc:
                self.logger.warning(f"[{self.platform}] 停止 Playwright 失败: {exc}")

    def format_last_login(self, state: PlatformLoginState) -> str:
        """格式化最近登录时间"""
        if state.last_success_at:
            from time import localtime, strftime
            return strftime("%Y-%m-%d %H:%M:%S", localtime(state.last_success_at))
        return "从未登录"

    async def create_success_state(self, cookie_str: str, cookie_dict: Dict[str, str], 
                                 user_info: Optional[Dict[str, Any]] = None) -> PlatformLoginState:
        """创建登录成功状态"""
        return PlatformLoginState(
            platform=self.platform,
            is_logged_in=True,
            cookie_str=cookie_str,
            cookie_dict=cookie_dict,
            user_info=user_info or {},
            message="已登录",
            last_checked_at=time.time(),
            last_success_at=time.time(),
        )

    async def create_failed_state(self, message: str = "未登录") -> PlatformLoginState:
        """创建登录失败状态"""
        return PlatformLoginState(
            platform=self.platform,
            is_logged_in=False,
            message=message,
            last_checked_at=time.time(),
        )