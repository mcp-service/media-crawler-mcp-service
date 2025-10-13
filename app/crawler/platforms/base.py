# -*- coding: utf-8 -*-
"""
改造后的爬虫基础类

去除全局 config 依赖，所有配置通过 CrawlerConfig 传递
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from playwright.async_api import BrowserContext, BrowserType, Playwright, Page

from app.config.settings import CrawlerConfig


class AbstractCrawler(ABC):
    """
    爬虫抽象基类（改造版）

    关键改变：
    - 构造函数接受 CrawlerConfig 参数
    - 移除对全局 config 的依赖
    - 所有方法使用 self.config 访问配置
    """

    def __init__(self, config: CrawlerConfig):
        """
        初始化爬虫

        Args:
            config: 爬虫配置对象
        """
        self.config = config
        self.context_page: Optional[Page] = None
        self.browser_context: Optional[BrowserContext] = None

    @abstractmethod
    async def start(self) -> Dict:
        """
        启动爬虫

        Returns:
            爬取结果字典
        """
        pass

    @abstractmethod
    async def search(self) -> Dict:
        """
        搜索爬取

        Returns:
            搜索结果字典
        """
        pass

    @abstractmethod
    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True
    ) -> BrowserContext:
        """
        启动浏览器

        Args:
            chromium: Playwright chromium 对象
            playwright_proxy: 代理配置
            user_agent: 用户代理
            headless: 是否无头模式

        Returns:
            浏览器上下文
        """
        pass

    async def close(self):
        """关闭浏览器"""
        if self.browser_context:
            await self.browser_context.close()


class AbstractLogin(ABC):
    """
    登录抽象基类（改造版）

    关键改变：
    - 构造函数接受 login_type 和其他参数
    - 不修改全局 config
    """

    def __init__(
        self,
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        login_phone: Optional[str] = "",
        cookie_str: str = ""
    ):
        """
        初始化登录对象

        Args:
            login_type: 登录类型 (qrcode, phone, cookie)
            browser_context: 浏览器上下文
            context_page: 页面对象
            login_phone: 手机号（手机登录时使用）
            cookie_str: Cookie字符串（Cookie登录时使用）
        """
        self.login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str

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


class AbstractStore(ABC):
    """数据存储抽象基类"""

    @abstractmethod
    async def store_content(self, content_item: Dict):
        """存储内容数据"""
        pass

    @abstractmethod
    async def store_comment(self, comment_item: Dict):
        """存储评论数据"""
        pass

    @abstractmethod
    async def store_creator(self, creator: Dict):
        """存储创作者数据"""
        pass