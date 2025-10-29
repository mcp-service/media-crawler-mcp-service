# -*- coding: utf-8 -*-
"""
Bilibili 登录实现类

"""

import asyncio
from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext, Page

from app.config.settings import Platform, LoginType
from app.core.crawler.platforms.base import AbstractLogin
from app.providers.logger import get_logger

from .client import BilibiliClient

logger = get_logger()

class BilibiliLogin(AbstractLogin):
    """
    Bilibili 登录类
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

    async def _build_api_client(self) -> Optional[BilibiliClient]:
        """Create a lightweight Bilibili client based on current browser context."""
        current_cookie = await self.browser_context.cookies()
        if not current_cookie:
            return None

        cookie_dict = {cookie["name"]: cookie["value"] for cookie in current_cookie}
        if not (cookie_dict.get("SESSDATA") or cookie_dict.get("DedeUserID")):
            return None

        cookie_str = "; ".join(f"{cookie['name']}={cookie['value']}" for cookie in current_cookie)
        try:
            user_agent = await self.context_page.evaluate("() => navigator.userAgent")
        except Exception:
            user_agent = "Mozilla/5.0"

        client = BilibiliClient(
            proxy=None,
            headers={
                "User-Agent": user_agent,
                "Cookie": cookie_str,
                "Origin": "https://www.bilibili.com",
                "Referer": "https://www.bilibili.com",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return client

    async def _check_login_via_page(self) -> bool:
        """Fallback login detection using in-page fetch (avoids httpx风控)."""
        try:
            result = await self.context_page.evaluate(
                """
                async () => {
                    try {
                        const resp = await fetch("https://api.bilibili.com/x/web-interface/nav", {
                            credentials: "include"
                        });
                        const status = resp.status;
                        const text = await resp.text();
                        let parsed = null;
                        try { parsed = JSON.parse(text); } catch (err) { parsed = null; }
                        return { status, body: parsed };
                    } catch (error) {
                        return { status: 0, error: String(error) };
                    }
                }
                """
            )
        except Exception as exc:
            logger.info(f"[BilibiliLogin._check_login_via_page] Evaluate failed: {exc}")
            return False

        if not isinstance(result, dict):
            logger.info(f"[BilibiliLogin._check_login_via_page] Unexpected result type: {result}")
            return False

        body = result.get("body")
        if isinstance(body, dict):
            # Standard nav response: {"code": 0, "data": {..., "isLogin": true}}
            if body.get("code") == 0:
                payload = body.get("data") or {}
                if isinstance(payload, dict) and payload.get("isLogin"):
                    return True
            # Some responses may inline isLogin at top-level
            if body.get("isLogin"):
                return True
            logger.info(f"[BilibiliLogin._check_login_via_page] Response body without login flag: {body}")
        else:
            logger.info(f"[BilibiliLogin._check_login_via_page] Raw evaluate result: {result}")
        return False

    async def has_valid_cookie(self) -> bool:
        """检测当前上下文是否已登录"""
        client = await self._build_api_client()
        if not client:
            return False
        cookie_present = bool(client.cookie_dict.get("SESSDATA") and client.cookie_dict.get("DedeUserID"))
        try:
            if await client.pong():
                return True
        except Exception as exc:
            reason = str(exc)
            if cookie_present and ("request was banned" in reason or "412" in reason or "风控" in reason):
                logger.debug("[BilibiliLogin.has_valid_cookie] Pong blocked by risk control, trying page fallback")
                via_page = await self._check_login_via_page()
                logger.debug(f"[BilibiliLogin.has_valid_cookie] Page fallback result: {via_page}")
                return via_page or cookie_present
            logger.debug(f"[BilibiliLogin.has_valid_cookie] Pong failed: {exc}")
            return False

        if not cookie_present:
            return False

        # httpx 返回未登录但 cookie 仍在，尝试使用浏览器上下文进行检测
        via_page = await self._check_login_via_page()
        logger.debug(f"[BilibiliLogin.has_valid_cookie] Additional page fallback result: {via_page}")
        if via_page:
            return True

        # 最终兜底：Cookie 存在但无法请求接口时，认为已登录（与旧实现保持一致）
        if cookie_present:
            logger.debug("[BilibiliLogin.has_valid_cookie] Falling back to cookie presence result")
            return True

        return False

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
