# -*- coding: utf-8 -*-
"""
Bilibili 登录实现类（改造版）

关键改变：
1. ❌ 移除：config.LOGIN_TYPE = login_type  （Line 39）
2. ✅ 改为：self.login_type = login_type
3. ✅ 所有 config.LOGIN_TYPE 改为 self.login_type
"""

import asyncio
import functools
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import (RetryError, retry, retry_if_result, stop_after_attempt, wait_fixed)

from app.config.settings import Platform, LoginType
from app.crawler.platforms.base import AbstractLogin
from app.providers.logger import get_logger


logger = get_logger()

class BilibiliLogin(AbstractLogin):
    """
    Bilibili 登录类（改造版）

    改造要点：
    - 不再修改全局 config
    - login_type 作为实例属性存储
    """

    def __init__(
        self,
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        login_phone: Optional[str] = "",
        cookie_str: str = ""
    ):
        super().__init__(login_type, browser_context, context_page, login_phone, cookie_str)


    async def begin(self):
        """开始登录 Bilibili"""
        logger.info("[BilibiliLogin.begin] Begin login Bilibili ...")

        # ✅ 使用 self.login_type 替代 config.LOGIN_TYPE
        if self.login_type == LoginType.QRCODE:
            await self.login_by_qrcode()
        elif self.login_type == LoginType.PHONE:
            await self.login_by_mobile()
        elif self.login_type == LoginType.COOKIE:
            await self.login_by_cookies()
        else:
            raise ValueError(
                "[BilibiliLogin.begin] Invalid Login Type Currently only supported qrcode or phone or cookie ..."
            )

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self) -> bool:
        """
        检查当前登录状态

        如果登录成功返回 True，否则返回 False
        重试装饰器会在返回 False 时重试 600 次，重试间隔为 1 秒
        如果达到最大重试次数，抛出 RetryError
        """
        current_cookie = await self.browser_context.cookies()
        cookie_dict = {cookie['name']: cookie['value'] for cookie in current_cookie}

        if cookie_dict.get("SESSDATA", "") or cookie_dict.get("DedeUserID"):
            return True
        return False

    async def login_by_qrcode(self):
        """二维码登录 Bilibili"""
        logger.info("[BilibiliLogin.login_by_qrcode] Begin login bilibili by qrcode ...")

        # 访问 Bilibili 首页
        await self.context_page.goto("https://www.bilibili.com/")
        await asyncio.sleep(2)

        # 点击登录按钮
        try:
            login_button_ele = self.context_page.locator(
                "xpath=//div[@class='right-entry__outside go-login-btn']//div"
            )
            await login_button_ele.click()
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"[BilibiliLogin.login_by_qrcode] Failed to click login button: {e}")

        # 查找登录二维码并截图保存
        qrcode_img_selector = "//div[@class='login-scan-box']//img"

        try:
            # 等待二维码出现
            qrcode_element = self.context_page.locator(qrcode_img_selector)
            await qrcode_element.wait_for(state="visible", timeout=10000)

            # 截取二维码图片
            from pathlib import Path
            qrcode_dir = Path(f"browser_data/{Platform.BILIBILI.value}_{self.login_type}")

            qrcode_dir.mkdir(parents=True, exist_ok=True)

            qrcode_path = qrcode_dir / f"qrcode.png"
            await qrcode_element.screenshot(path=str(qrcode_path))

            logger.info(f"[BilibiliLogin.login_by_qrcode] QR code saved to: {qrcode_path}")
            logger.info("[BilibiliLogin.login_by_qrcode] Waiting for QR code scan...")

        except Exception as e:
            logger.error(f"[BilibiliLogin.login_by_qrcode] Failed to capture QR code: {e}")

        try:
            await self.check_login_state()
        except RetryError:
            logger.error("[BilibiliLogin.login_by_qrcode] Login bilibili failed by qrcode login method (timeout)")
            raise Exception("二维码登录超时，用户未扫码或扫码失败")

        wait_redirect_seconds = 5
        logger.info(
            f"[BilibiliLogin.login_by_qrcode] Login successful then wait for {wait_redirect_seconds} seconds redirect ..."
        )
        await asyncio.sleep(wait_redirect_seconds)

    async def login_by_mobile(self):
        """手机号登录（待实现）"""
        pass

    async def login_by_cookies(self):
        """Cookie 登录"""
        logger.info("[BilibiliLogin.login_by_cookies] Begin login bilibili by cookie ...")

        # 解析 cookie 字符串
        cookie_dict = {}
        if self.cookie_str:
            for item in self.cookie_str.split(';'):
                if '=' in item:
                    key, value = item.strip().split('=', 1)
                    cookie_dict[key] = value

        # 添加 cookies
        for key, value in cookie_dict.items():
            await self.browser_context.add_cookies([{
                'name': key,
                'value': value,
                'domain': ".bilibili.com",
                'path': "/"
            }])

        logger.info("[BilibiliLogin.login_by_cookies] Cookie login completed")