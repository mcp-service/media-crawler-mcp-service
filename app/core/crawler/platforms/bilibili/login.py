# -*- coding: utf-8 -*-
"""
Bilibili 登录实现类（改造版）

关键改变：
1. ❌ 移除：config.LOGIN_TYPE = login_type  （Line 39）
2. ✅ 改为：self.login_type = login_type
3. ✅ 所有 config.LOGIN_TYPE 改为 self.login_type
"""

import asyncio
from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext, Page

from app.config.settings import Platform, LoginType
from app.core.crawler.platforms.base import AbstractLogin
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

    async def generate_qrcode(self) -> Optional[Path]:
        """生成二维码并返回保存路径"""
        logger.info("[BilibiliLogin.generate_qrcode] Preparing Bilibili QR code ...")

        await self.context_page.goto("https://www.bilibili.com/")
        await asyncio.sleep(2)

        try:
            login_button_ele = self.context_page.locator(
                "xpath=//div[@class='right-entry__outside go-login-btn']//div"
            )
            await login_button_ele.click()
            await asyncio.sleep(2)
        except Exception as exc:
            logger.error(f"[BilibiliLogin.generate_qrcode] Failed to click login button: {exc}")

        qrcode_img_selector = "//div[@class='login-scan-box']//img"
        qrcode_dir = Path(f"browser_data/{Platform.BILIBILI.value}_{self.login_type}")
        qrcode_dir.mkdir(parents=True, exist_ok=True)
        qrcode_path = qrcode_dir / "qrcode.png"

        try:
            qrcode_element = self.context_page.locator(qrcode_img_selector)
            await qrcode_element.wait_for(state="visible", timeout=10000)
            await qrcode_element.screenshot(path=str(qrcode_path))
            logger.info(f"[BilibiliLogin.generate_qrcode] QR code saved to: {qrcode_path}")
            return qrcode_path
        except Exception as exc:
            logger.error(f"[BilibiliLogin.generate_qrcode] Failed to capture QR code: {exc}")
            return None

    async def has_valid_cookie(self) -> bool:
        """检测当前上下文是否已登录"""
        current_cookie = await self.browser_context.cookies()
        cookie_dict = {cookie["name"]: cookie["value"] for cookie in current_cookie}
        return bool(cookie_dict.get("SESSDATA") or cookie_dict.get("DedeUserID"))

    async def wait_for_login(self, timeout: float = 180.0, interval: float = 1.0) -> bool:
        """轮询检测登录状态"""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            try:
                if await self.has_valid_cookie():
                    return True
            except Exception as exc:
                logger.warning(f"[BilibiliLogin.wait_for_login] Failed to check login state: {exc}")
            await asyncio.sleep(interval)
        return False

    async def login_by_qrcode(self):
        """二维码登录 Bilibili"""
        logger.info("[BilibiliLogin.login_by_qrcode] Begin login bilibili by qrcode ...")

        await self.generate_qrcode()
        logger.info("[BilibiliLogin.login_by_qrcode] Waiting for QR code scan...")

        if not await self.wait_for_login():
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
