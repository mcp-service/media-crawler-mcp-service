# -*- coding: utf-8 -*-
"""Bilibili 登录完整实现"""

import asyncio
import base64
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, Any

from playwright.async_api import BrowserContext, Page, async_playwright

from app.config.settings import Platform, LoginType, global_settings
from app.core.login.base import AbstractLogin
from app.core.login.models import LoginSession, LoginStartPayload, PlatformLoginState
from app.providers.logger import get_logger

from app.core.crawler.platforms.bilibili.client import BilibiliClient
from app.core.login.browser_manager import get_browser_manager

logger = get_logger()
browser_manager = get_browser_manager()


class BilibiliLogin(AbstractLogin):
    """Bilibili 登录完整实现类"""

    def __init__(self, service, login_type: str, browser_context: BrowserContext, 
                 context_page: Page, login_phone: Optional[str] = "", cookie_str: str = ""):
        super().__init__(service, login_type, browser_context, context_page, login_phone, cookie_str)
        self.playwright = None
        # 配置参数
        browser_cfg = global_settings.browser
        self._headless = browser_cfg.headless
        self._user_agent = getattr(
            browser_cfg,
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        viewport_width = browser_cfg.viewport_width or 1280
        viewport_height = browser_cfg.viewport_height or 800
        self._viewport = {"width": int(viewport_width), "height": int(viewport_height)}

    @property
    def platform(self) -> str:
        return Platform.BILIBILI.value

    @property
    def display_name(self) -> str:
        return "哔哩哔哩"

    @property
    def user_data_dir(self) -> Path:
        return Path("browser_data") / self.platform

    def _qr_code_dir(self, login_type: str) -> Path:
        return Path("browser_data") / f"{self.platform}_{login_type}"

    async def begin(self):
        """开始登录流程"""
        logger.info("[BilibiliLogin.begin] Begin login Bilibili ...")

        if self.login_type == LoginType.QRCODE.value:
            await self.login_by_qrcode()
        elif self.login_type == LoginType.PHONE.value:
            await self.login_by_mobile()
        elif self.login_type == LoginType.COOKIE.value:
            await self.login_by_cookies()
        else:
            raise ValueError(
                "[BilibiliLogin.begin] Invalid Login Type Currently only supported qrcode or phone or cookie ..."
            )

    async def login_by_qrcode(self):
        """二维码登录实现"""
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
        """手机号登录 - 暂未实现"""
        raise NotImplementedError("手机号登录暂未实现")

    async def login_by_cookies(self):
        """Cookie登录实现"""
        logger.info("[BilibiliLogin.login_by_cookies] Begin login bilibili by cookie ...")

        cookie_dict = {}
        if self.cookie_str:
            for item in self.cookie_str.split(';'):
                if '=' in item:
                    key, value = item.strip().split('=', 1)
                    cookie_dict[key] = value

        for key, value in cookie_dict.items():
            await self.browser_context.add_cookies([
                {
                    'name': key,
                    'value': value,
                    'domain': ".bilibili.com",
                    'path': "/"
                }
            ])

        logger.info("[BilibiliLogin.login_by_cookies] Cookie login completed")

    async def generate_qrcode(self) -> Optional[Path]:
        """生成二维码"""
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
        """检查是否有有效的Cookie"""
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

        via_page = await self._check_login_via_page()
        logger.debug(f"[BilibiliLogin.has_valid_cookie] Additional page fallback result: {via_page}")
        if via_page:
            return True

        if cookie_present:
            logger.debug("[BilibiliLogin.has_valid_cookie] Falling back to cookie presence result")
            return True

        return False

    async def wait_for_login(self, timeout: float = 180.0, interval: float = 1.0) -> bool:
        """等待登录完成"""
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

    async def fetch_login_state(self) -> PlatformLoginState:
        """获取当前登录状态"""
        state = PlatformLoginState(platform=self.platform)
        data_dir = self.user_data_dir
        if not data_dir.exists():
            state.message = "浏览器数据不存在"
            state.last_checked_at = time.time()
            return state

        browser_context: Optional[BrowserContext] = None
        playwright: Optional[any] = None
        try:
            # 使用浏览器管理器获取临时上下文
            browser_context, playwright = await browser_manager.get_context_for_check(
                platform=self.platform,
                user_data_dir=data_dir,
                headless=self._headless,
                viewport=self._viewport,
                user_agent=self._user_agent,
            )

            # 检查Cookie
            cookies = await browser_context.cookies()
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
            cookie_dict = {c["name"]: c["value"] for c in cookies}

            has_sessdata = bool(cookie_dict.get("SESSDATA"))
            has_userid = bool(cookie_dict.get("DedeUserID"))

            if not (has_sessdata and has_userid):
                state.is_logged_in = False
                state.cookie_str = cookie_str
                state.cookie_dict = cookie_dict
                state.user_info = {}
                state.message = "关键登录信息缺失"
                state.last_checked_at = time.time()
                return state

            # 验证登录状态
            is_logged_in = await self._verify_login_status(cookie_str, cookie_dict, browser_context)

            state.is_logged_in = is_logged_in
            state.cookie_str = cookie_str
            state.cookie_dict = cookie_dict

            if is_logged_in:
                state.user_info = {
                    "uid": cookie_dict.get("DedeUserID", ""),
                    "sessdata": (
                        cookie_dict.get("SESSDATA", "")[:20] + "..."
                        if cookie_dict.get("SESSDATA")
                        else ""
                    ),
                }
                state.message = "已登录"
                state.last_success_at = time.time()
            else:
                state.user_info = {}
                state.message = "未登录"

            state.last_checked_at = time.time()
            return state

        except Exception as exc:
            logger.error(f"[登录管理] 检查 Bilibili 登录状态失败: {exc}")
            return await self.create_failed_state(f"状态检查失败: {exc}")
        finally:
            if browser_context:
                try:
                    await browser_context.close()
                except Exception:
                    pass
            if playwright:
                try:
                    await playwright.stop()
                except Exception:
                    pass

    async def _build_api_client(self) -> Optional[BilibiliClient]:
        """构建API客户端"""
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
        """通过页面检查登录状态（避免httpx风控）"""
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
            if body.get("code") == 0:
                payload = body.get("data") or {}
                if isinstance(payload, dict) and payload.get("isLogin"):
                    return True
            if body.get("isLogin"):
                return True
            logger.info(f"[BilibiliLogin._check_login_via_page] Response body without login flag: {body}")
        else:
            logger.info(f"[BilibiliLogin._check_login_via_page] Raw evaluate result: {result}")
        return False

    async def _verify_login_status(self, cookie_str: str, cookie_dict: Dict[str, str],
                                 browser_context: BrowserContext) -> bool:
        """验证登录状态（增强风控容错）"""
        has_key_cookies = bool(cookie_dict.get("SESSDATA") and cookie_dict.get("DedeUserID"))

        try:
            # 先尝试API验证
            bili_client = BilibiliClient(
                proxy=None,
                headers={
                    "User-Agent": self._user_agent,
                    "Cookie": cookie_str,
                    "Origin": "https://www.bilibili.com",
                    "Referer": "https://www.bilibili.com",
                },
                playwright_page=None,
                cookie_dict=cookie_dict,
            )
            api_result = await bili_client.pong()
            is_logged_in = bool(api_result)
            logger.debug(f"[登录管理] Bilibili API 检查结果: {is_logged_in}")
            return is_logged_in
        except Exception as api_exc:
            error_msg = str(api_exc)
            logger.debug(f"[登录管理] Bilibili API 检查失败: {api_exc}")

            # ⚠️ 风控错误（412/461/412/风控/banned）→ 保守判断为已登录
            is_risk_control = any(keyword in error_msg for keyword in ["412", "461", "471", "风控", "banned", "risk"])
            if has_key_cookies and is_risk_control:
                logger.info(f"[登录管理] 检测到风控，但Cookie存在，保守判断为已登录")
                return True

            # API失败时，尝试页面检查
            page = None
            try:
                page = await browser_context.new_page()
                await page.goto("https://www.bilibili.com/",
                              wait_until="domcontentloaded", timeout=10000)

                result = await page.evaluate(
                    """
                    async () => {
                        try {
                            const resp = await fetch("https://api.bilibili.com/x/web-interface/nav",
                                                    { credentials: "include" });
                            if (resp.status !== 200) return { success: false, status: resp.status };
                            const data = await resp.json();
                            return {
                                success: true,
                                isLogin: data?.data?.isLogin || false,
                                code: data?.code || -1
                            };
                        } catch (error) {
                            return { success: false, error: String(error) };
                        }
                    }
                    """
                )

                if isinstance(result, dict) and result.get("success"):
                    is_logged_in = bool(result.get("isLogin", False))
                    logger.debug(f"[登录管理] Bilibili 页面检查结果: {is_logged_in}")
                    return is_logged_in
                else:
                    # 页面检查失败，但有关键Cookie → 保守判断为已登录
                    if has_key_cookies:
                        logger.info(f"[登录管理] 页面检查失败，但Cookie存在，保守判断为已登录")
                        return True
                    return False

            except Exception as page_exc:
                logger.debug(f"[登录管理] 页面加载失败: {page_exc}")
                # 页面检查异常，但有关键Cookie → 保守判断为已登录
                if has_key_cookies:
                    logger.info(f"[登录管理] 页面检查异常，但Cookie存在，保守判断为已登录")
                    return True
                return False
            finally:
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass


# === 登录服务接口实现 ===

async def start_login(service, session: LoginSession, payload: LoginStartPayload) -> Dict[str, Any]:
    """启动登录流程"""
    session.status = "starting"
    session.message = "正在启动登录流程..."
    await service.persist_session(session)

    # 清理旧二维码目录
    qr_dir = get_user_data_dir().parent / f"{Platform.BILIBILI.value}_{payload.login_type}"
    if qr_dir.exists():
        try:
            shutil.rmtree(qr_dir)
        except Exception as exc:
            logger.warning(f"[登录管理] 清理旧二维码目录失败: {exc}")

    # 检查现有登录状态（仅在非Cookie登录且非二维码登录时）
    cookie_candidate = (payload.cookie or "").strip()

    # 如果是二维码登录，则跳过现有状态检查，直接生成新二维码
    # 如果已提供Cookie，则尝试Cookie登录
    # 如果什么都没提供，才检查现有状态
    if not cookie_candidate and payload.login_type != "qrcode":
        try:
            current_state = await service.refresh_platform_state(session.platform, force=False)
        except Exception as exc:
            current_state = None
            logger.warning(f"[登录管理] 检查现有登录状态失败，继续登录流程: {exc}")
        else:
            if current_state and current_state.is_logged_in:
                session.status = "success"
                session.message = "已检测到登录状态，无需重新登录"
                session.metadata["cookie_dict"] = current_state.cookie_dict
                session.metadata["cookie_str"] = current_state.cookie_str
                await service.persist_session(session)
                return session.to_public_dict()

    # 使用浏览器管理器启动浏览器
    user_data_dir = get_user_data_dir()
    browser_cfg = global_settings.browser
    viewport = {"width": int(browser_cfg.viewport_width or 1280),
               "height": int(browser_cfg.viewport_height or 800)}

    try:
        browser_context, context_page, playwright = await browser_manager.acquire_context(
            platform=Platform.BILIBILI.value,
            user_data_dir=user_data_dir,
            headless=browser_cfg.headless,
            viewport=viewport,
            user_agent=getattr(browser_cfg, "user_agent",
                              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        )
    except Exception as exc:
        logger.error(f"[登录管理] 获取浏览器实例失败: {exc}")
        session.status = "failed"
        session.message = f"浏览器启动失败: {exc}"
        await service.persist_session(session)
        return session.to_public_dict()

    # 创建登录对象
    login_obj = BilibiliLogin(
        service=service,
        login_type=payload.login_type,
        browser_context=browser_context,
        context_page=context_page,
        login_phone=payload.phone,
        cookie_str=payload.cookie,
    )
    login_obj.playwright = playwright

    session.browser_context = browser_context
    session.context_page = context_page
    session.playwright = playwright
    session.runtime["login_obj"] = login_obj

    try:
        # 处理Cookie登录
        if cookie_candidate:
            success = await _handle_cookie_login(session, login_obj, cookie_candidate, payload, service)
            if success:
                await browser_manager.release_context(Platform.BILIBILI.value, keep_alive=True)
                return session.to_public_dict()

        # 处理二维码登录
        if payload.login_type == "qrcode" or session.login_type == LoginType.QRCODE.value:
            await _handle_qrcode_login(session, login_obj, payload, service)
        else:
            # 其他登录类型
            await _handle_other_login(session, login_obj, service)

        return session.to_public_dict()

    except Exception as exc:
        logger.error(f"[登录管理] 登录过程发生错误: {exc}")
        session.status = "failed"
        session.message = f"登录失败: {exc}"
        await service.persist_session(session)
        await _cleanup_session_resources(session)
        await browser_manager.release_context(Platform.BILIBILI.value, keep_alive=False)
        return session.to_public_dict()


async def _handle_cookie_login(session: LoginSession, login_obj: BilibiliLogin, 
                             cookie_candidate: str, payload: LoginStartPayload, service) -> bool:
    """处理Cookie登录"""
    session.login_type = LoginType.COOKIE.value
    session.status = "processing"
    session.message = "检测到 Cookie，正在尝试 Cookie 登录..."
    await service.persist_session(session)

    login_obj.cookie_str = cookie_candidate
    try:
        await login_obj.login_by_cookies()
        
        # 验证登录状态
        login_success = False
        try:
            await session.context_page.goto("https://www.bilibili.com/", 
                                           wait_until="domcontentloaded", timeout=10000)
            login_success = await login_obj.wait_for_login(timeout=10.0, interval=0.5)
        except Exception as page_exc:
            logger.warning(f"[登录管理] 页面加载失败，尝试直接验证 Cookie: {page_exc}")
            try:
                login_success = await login_obj.has_valid_cookie()
            except Exception as cookie_exc:
                logger.warning(f"[登录管理] Cookie 验证也失败: {cookie_exc}")

        if login_success:
            await _save_login_success(session, login_obj, service)
            await _cleanup_session_resources(session)
            return True

        # Cookie登录失败，如果原始请求是二维码登录，则回退
        if payload.login_type == "qrcode":
            logger.info(f"[登录管理] Cookie 登录失败，回退到二维码登录: session_id={session.id}")
            session.login_type = LoginType.QRCODE.value
            session.status = "started"
            session.message = "Cookie 登录失败，正在生成二维码..."
            return False
        else:
            session.status = "failed"
            session.message = "Cookie 登录失败，Cookie 可能已失效"
            await service.persist_session(session)
            await _cleanup_session_resources(session)
            return True

    except Exception as exc:
        # 尝试直接验证Cookie
        try:
            if await login_obj.has_valid_cookie():
                await _save_login_success(session, login_obj, service)
                await _cleanup_session_resources(session)
                return True
        except Exception:
            pass

        if payload.login_type == "qrcode":
            session.login_type = LoginType.QRCODE.value
            session.status = "started"
            session.message = "Cookie 验证失败，正在生成二维码..."
            return False
        else:
            session.status = "failed"
            session.message = f"Cookie 登录失败: {exc}"
            await service.persist_session(session)
            await _cleanup_session_resources(session)
            return True


async def _handle_qrcode_login(session: LoginSession, login_obj: BilibiliLogin, 
                             payload: LoginStartPayload, service):
    """处理二维码登录"""
    login_obj.login_type = "qrcode"
    session.status = "started"
    session.message = "正在生成二维码..."
    session.qrcode_timestamp = time.time()

    qr_path = await login_obj.generate_qrcode()
    if qr_path is None:
        session.status = "failed"
        session.message = "二维码生成失败，请稍后重试"
        await service.persist_session(session)
        await _cleanup_session_resources(session)
        return

    qr_b64 = await _wait_for_qrcode(payload.login_type)
    if qr_b64:
        session.qr_code_base64 = qr_b64
        session.status = "waiting"
        session.message = "二维码已生成，等待扫码..."
        await service.persist_session(session)

        # 启动轮询任务
        async def _poll_qrcode():
            try:
                timeout_seconds = 180
                poll_interval = 1.5
                start_ts = time.time()

                while True:
                    if await login_obj.has_valid_cookie():
                        await _save_login_success(session, login_obj, service)
                        break

                    if time.time() - start_ts > timeout_seconds:
                        session.status = "expired"
                        session.message = "二维码已过期，请重新获取"
                        await service.persist_session(session)
                        break

                    await asyncio.sleep(poll_interval)
            except Exception as exc:
                session.status = "failed"
                session.message = f"登录失败: {exc}"
                await service.persist_session(session)
            finally:
                await asyncio.sleep(2)
                await _cleanup_session_resources(session)

        task = asyncio.create_task(_poll_qrcode())
        session.runtime["task"] = task
    else:
        session.status = "failed"
        session.message = "二维码生成超时，请重新开始登录"
        await service.persist_session(session)
        await _cleanup_session_resources(session)


async def _handle_other_login(session: LoginSession, login_obj: BilibiliLogin, service):
    """处理其他登录方式"""
    session.status = "processing"
    session.message = "正在尝试登录..."
    session.qrcode_timestamp = 0.0

    async def _execute_login():
        try:
            await login_obj.begin()
            session.status = "success"
            session.message = "登录成功"
            await service.persist_session(session)
            await service.refresh_platform_state(session.platform, force=True)
        except Exception as exc:
            session.status = "failed"
            session.message = f"登录失败: {exc}"
            await service.persist_session(session)
        finally:
            await asyncio.sleep(3)
            await _cleanup_session_resources(session)

    task = asyncio.create_task(_execute_login())
    session.runtime["task"] = task
    await service.persist_session(session)


async def _save_login_success(session: LoginSession, login_obj: BilibiliLogin, service):
    """保存登录成功状态"""
    cookies = await session.browser_context.cookies()
    cookie_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
    cookie_str = "; ".join(f"{name}={value}" for name, value in cookie_dict.items())

    session.metadata["cookie_dict"] = cookie_dict
    session.metadata["cookie_str"] = cookie_str
    session.status = "success"
    session.message = "登录成功"
    await service.persist_session(session)

    # 保存平台状态
    success_state = PlatformLoginState(
        platform=login_obj.platform,
        is_logged_in=True,
        cookie_str=cookie_str,
        cookie_dict=cookie_dict,
        user_info={
            "uid": cookie_dict.get("DedeUserID", ""),
            "sessdata": (
                cookie_dict.get("SESSDATA", "")[:20] + "..."
                if cookie_dict.get("SESSDATA")
                else ""
            ),
        },
        message="已登录",
        last_checked_at=time.time(),
        last_success_at=time.time(),
    )

    try:
        await service._storage.save_platform_state(success_state)
        logger.info(f"[登录管理] 登录成功，状态已保存: session_id={session.id}")
    except Exception as save_exc:
        logger.warning(f"[登录管理] 保存登录状态失败: {save_exc}")


async def _wait_for_qrcode(login_type: str) -> Optional[str]:
    """等待二维码文件生成并转换为base64"""
    qrcode_path = get_user_data_dir().parent / f"{Platform.BILIBILI.value}_{login_type}" / "qrcode.png"
    attempts = 50
    interval = 0.2
    for _ in range(attempts):
        if qrcode_path.exists():
            try:
                size = qrcode_path.stat().st_size
                if size > 1024:
                    with qrcode_path.open("rb") as fp:
                        data = fp.read()
                    if data:
                        return base64.b64encode(data).decode("utf-8")
            except Exception:
                pass
        await asyncio.sleep(interval)
    return None


async def _cleanup_session_resources(session: LoginSession):
    """清理会话资源"""
    if session.browser_context:
        try:
            # 注意：不关闭 browser_context，因为它由 browser_manager 管理
            # await session.browser_context.close()
            session.browser_context = None
        except Exception:
            pass
    if session.playwright:
        try:
            # 注意：不停止 playwright，因为它由 browser_manager 管理
            # await session.playwright.stop()
            session.playwright = None
        except Exception:
            pass


async def fetch_login_state(service) -> PlatformLoginState:
    """获取登录状态 - 服务接口"""
    # 临时创建登录对象来检查状态
    user_data_dir = get_user_data_dir()
    if not user_data_dir.exists():
        return PlatformLoginState(
            platform=Platform.BILIBILI.value,
            is_logged_in=False,
            message="浏览器数据不存在",
            last_checked_at=time.time()
        )

    browser_context: Optional[BrowserContext] = None
    playwright: Optional[any] = None
    try:
        browser_cfg = global_settings.browser
        viewport = {"width": int(browser_cfg.viewport_width or 1280),
                   "height": int(browser_cfg.viewport_height or 800)}

        # 使用浏览器管理器获取临时上下文
        browser_context, playwright = await browser_manager.get_context_for_check(
            platform=Platform.BILIBILI.value,
            user_data_dir=user_data_dir,
            headless=True,
            viewport=viewport,
            user_agent=getattr(browser_cfg, "user_agent", "Mozilla/5.0"),
        )

        context_page = await browser_context.new_page()

        # 创建临时登录对象进行状态检查
        temp_login = BilibiliLogin(
            service=service,
            login_type="temp",
            browser_context=browser_context,
            context_page=context_page
        )
        temp_login.playwright = playwright

        return await temp_login.fetch_login_state()

    finally:
        if context_page:
            try:
                await context_page.close()
            except Exception:
                pass
        if browser_context:
            try:
                await browser_context.close()
            except Exception:
                pass
        if playwright:
            try:
                await playwright.stop()
            except Exception:
                pass


async def logout(service) -> None:
    """退出登录 - 服务接口"""
    await service.cleanup_platform_sessions(Platform.BILIBILI.value, drop=True)

    # 强制清理浏览器管理器中的实例
    await browser_manager.force_cleanup(Platform.BILIBILI.value)

    data_dir = get_user_data_dir()
    if data_dir.exists():
        try:
            await asyncio.to_thread(shutil.rmtree, data_dir)
        except Exception as exc:
            logger.warning(f"[登录管理] 清理浏览器数据目录失败: {exc}")

    qr_parent = Path("browser_data")
    if qr_parent.exists():
        for qr_dir in qr_parent.glob(f"{Platform.BILIBILI.value}_*"):
            try:
                await asyncio.to_thread(shutil.rmtree, qr_dir)
            except Exception:
                pass


def get_user_data_dir() -> Path:
    """获取用户数据目录"""
    return Path("browser_data") / Platform.BILIBILI.value


# 向后兼容的常量
DISPLAY_NAME = "哔哩哔哩"