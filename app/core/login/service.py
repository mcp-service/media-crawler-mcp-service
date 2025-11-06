"""
登录核心服务
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional

from app.config.settings import Platform, LoginType, global_settings
from app.providers.logger import get_logger

from .bilibili import login as bili_login
from .xhs import login as xhs_login
from .exceptions import LoginServiceError
from .models import LoginSession, LoginStartPayload, PlatformLoginState
from .storage import RedisLoginStorage

logger = get_logger()


class LoginService:
    """统一的登录服务"""

    STATUS_CACHE_TTL = 60  # 平台状态缓存时间（秒）
    QR_EXPIRE_SECONDS = 180  # 二维码有效期

    def __init__(self):
        self._active_sessions: Dict[str, LoginSession] = {}
        self._active_sessions_lock = asyncio.Lock()
        self._storage = RedisLoginStorage()
        # 直接使用各平台的登录模块
        self._platform_modules = {
            Platform.BILIBILI.value: bili_login,
            Platform.XIAOHONGSHU.value: xhs_login,
        }
        # 平台级别的登录锁，防止同一平台重复发起登录请求（防抖）
        self._platform_login_locks: Dict[str, asyncio.Lock] = {}
        self._platform_locks_access = asyncio.Lock()

    # === 基础能力 ===

    async def _get_platform_login_lock(self, platform: str) -> asyncio.Lock:
        """获取平台登录锁（防抖）"""
        async with self._platform_locks_access:
            if platform not in self._platform_login_locks:
                self._platform_login_locks[platform] = asyncio.Lock()
            return self._platform_login_locks[platform]

    def get_supported_platforms(self) -> List[str]:
        """获取支持的登录平台"""
        enabled = [
            p.value
            for p in global_settings.platform.enabled_platforms
        ]
        return [platform for platform in self._platform_modules if platform in enabled]

    def get_session(self, session_id: str) -> Optional[LoginSession]:
        """获取活跃会话（仅限当前进程内存）"""
        return self._active_sessions.get(session_id)

    def _get_platform_module(self, platform: str):
        """获取平台登录模块"""
        module = self._platform_modules.get(platform)
        if not module:
            raise LoginServiceError(f"平台 {platform} 暂不支持或未启用登录功能")
        return module

    def get_platform_display_name(self, platform: str) -> str:
        """获取平台显示名称"""
        module = self._get_platform_module(platform)
        return getattr(module, 'DISPLAY_NAME', platform)

    async def _register_active_session(self, session: LoginSession):
        async with self._active_sessions_lock:
            self._active_sessions[session.id] = session

    async def _remove_active_session(self, session_id: str):
        async with self._active_sessions_lock:
            self._active_sessions.pop(session_id, None)

    async def persist_session(self, session: LoginSession):
        """持久化会话状态到 Redis"""
        session.touch()
        try:
            await self._storage.save_session(session)
        except Exception as exc:
            logger.warning(f"[登录管理] 持久化会话失败: {exc}")

    # === 登录流程 ===

    async def start_login(self, payload: LoginStartPayload) -> Dict[str, Any]:
        """启动登录流程"""
        platform = payload.platform

        # 获取平台登录锁，防止同一平台重复登录（防抖）
        platform_lock = await self._get_platform_login_lock(platform)

        # 尝试获取锁，如果已被占用则返回错误
        if platform_lock.locked():
            # 检查是否有正在进行的登录会话
            session_ids = await self._storage.list_session_ids_by_platform(platform)
            for sid in session_ids:
                existing_session = await self._storage.get_session(sid)
                if existing_session and existing_session.status in {"starting", "started", "waiting", "processing"}:
                    logger.warning(f"[登录管理] {platform} 已有登录会话正在进行中: {sid}")
                    return {
                        "status": "failed",
                        "platform": platform,
                        "login_type": payload.login_type,
                        "message": f"登录正在进行中，请稍后重试（会话ID: {sid[:8]}...）",
                        "session_id": None,
                        "qr_code_base64": None,
                        "qrcode_timestamp": 0.0,
                    }

        async with platform_lock:
            platform_module = self._get_platform_module(platform)

            # 如果不是 cookie 登录，先检查当前状态是否已登录
            if payload.login_type != LoginType.COOKIE.value:
                try:
                    # 先尝试获取缓存状态，避免触发风控检查
                    current_state = await self.refresh_platform_state(platform, force=False)
                except Exception as exc:
                    logger.warning(f"[登录管理] 刷新 {platform} 登录状态失败，继续登录流程: {exc}")
                    current_state = None
                else:
                    if current_state and current_state.is_logged_in:
                        return {
                            "status": "success",
                            "platform": platform,
                            "login_type": payload.login_type,
                            "message": "已检测到登录状态，无需重新登录",
                            "session_id": None,
                            "qr_code_base64": None,
                            "qrcode_timestamp": 0.0,
                        }
                    # 如果有缓存的 cookie，优先尝试 cookie 登录（避免风控）
                    # 但不修改 payload.login_type，而是通过 session metadata 传递
                    if current_state and current_state.cookie_str and not payload.cookie:
                        payload.cookie = current_state.cookie_str
                        logger.info(f"[登录管理] 检测到缓存 Cookie，将先尝试 cookie 登录（如失败会降级到 {payload.login_type}）")

            session_id = str(uuid.uuid4())
            session = LoginSession(id=session_id, platform=platform, login_type=payload.login_type)

            # 清理旧会话，但保留历史记录
            await self.cleanup_platform_sessions(
                platform,
                drop=False,
                reason="已启动新的登录流程，旧的登录会话已终止",
            )

            await self._register_active_session(session)
            await self.persist_session(session)

            try:
                # 直接调用平台登录模块
                response = await platform_module.start_login(self, session, payload)
                await self.persist_session(session)
                return response
            except Exception as exc:
                logger.error(f"[登录管理] 启动登录失败: {exc}")
                await self.cleanup_session(
                    session_id,
                    remove_resources=True,
                    drop=True,
                    reason="登录启动失败",
                )
                raise LoginServiceError(f"启动登录失败: {exc}") from exc

    # === 状态查询 ===

    async def get_login_status(self, platform: str) -> Dict[str, Any]:
        """获取平台登录状态"""
        platform_module = self._get_platform_module(platform)
        state = await self.refresh_platform_state(platform, force=False)
        message = state.message or ("已登录" if state.is_logged_in else "未登录")
        return {
            "platform": platform,
            "platform_name": self.get_platform_display_name(platform),
            "is_logged_in": state.is_logged_in,
            "user_info": state.user_info,
            "message": message,
        }

    async def logout(self, platform: str) -> Dict[str, Any]:
        """退出登录"""
        platform_module = self._get_platform_module(platform)
        await platform_module.logout(self)

        state = PlatformLoginState(
            platform=platform,
            is_logged_in=False,
            last_checked_at=time.time(),
            message="已退出登录",
        )
        state.touch()
        await self._storage.save_platform_state(state)

        await self.cleanup_platform_sessions(platform, drop=False, reason="平台已退出登录")

        return {
            "status": "success",
            "platform": platform,
            "message": "退出登录成功",
        }

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """获取登录会话状态"""
        try:
            record = await self._storage.get_session(session_id)
        except Exception as exc:
            logger.error(f"[登录管理] 获取会话状态失败: {exc}")
            raise LoginServiceError("会话状态暂不可用") from exc
        if not record:
            raise LoginServiceError("会话不存在")

        if (
            record.login_type == "qrcode"
            and record.status in {"created", "starting", "started", "waiting", "processing"}
            and record.qrcode_timestamp
        ):
            elapsed = time.time() - record.qrcode_timestamp
            if elapsed > self.QR_EXPIRE_SECONDS and record.status != "expired":
                record.status = "expired"
                record.message = "二维码已过期，请重新获取"
                await self.persist_session(record)
                asyncio.create_task(self.cleanup_session(record.id, remove_resources=True))

        return record.to_public_dict()

    async def list_sessions(self, *, force: bool = False) -> List[Dict[str, Any]]:
        """列出所有平台的登录状态"""
        async def _collect(platform: str) -> Dict[str, Any]:
            platform_module = self._get_platform_module(platform)
            logger.debug(f"开始收集 {platform} 平台状态")
            
            try:
                if not force:
                    # 优先从存储读取，避免不必要的风控
                    state = await self._storage.get_platform_state(platform)
                    logger.debug(f"{platform} 从存储读取状态: {state.is_logged_in if state else 'None'}")
                    if not state:
                        logger.debug(f"{platform} 没有缓存，调用 refresh_platform_state(force=False)")
                        state = await self.refresh_platform_state(platform, force=False)
                        logger.debug(f"{platform} refresh 后状态: {state.is_logged_in}")
                    else:
                        logger.debug(f"{platform} 使用缓存状态，last_checked: {state.last_checked_at}, is_logged_in: {state.is_logged_in}")
                else:
                    # 手动刷新：跳过缓存，严格 pong 检查
                    logger.debug(f"{platform} 手动刷新(force=True) 严格校验，调用 refresh_platform_state")
                    state = await self.refresh_platform_state(platform, force=True, strict=True)
            
            except Exception as exc:
                logger.warning(f"[登录管理] 获取 {platform} 登录状态失败: {exc}")
                return {
                    "platform": platform,
                    "platform_name": self.get_platform_display_name(platform),
                    "is_logged_in": False,
                    "last_login": "未知",
                    "session_path": None,
                }
            
            last_login = self._format_last_login(state)
            if state.is_logged_in and not state.last_success_at:
                last_login = "最近登录"
                
            result = {
                "platform": platform,
                "platform_name": self.get_platform_display_name(platform),
                "is_logged_in": state.is_logged_in,
                "last_login": last_login,
                "session_path": str(platform_module.get_user_data_dir()) if state.is_logged_in else None,
            }
            logger.debug(f"{platform} 最终返回结果: {result}")
            return result

        tasks = [asyncio.create_task(_collect(platform)) for platform in self.get_supported_platforms()]
        if not tasks:
            return []
        results: List[Dict[str, Any]] = await asyncio.gather(*tasks)
        return results

    async def list_sessions_cached(self) -> List[Dict[str, Any]]:
        """仅从缓存读取平台状态，不做任何刷新/创建浏览器上下文。

        适用于轻量级的状态面板展示，避免触发风控或拉起浏览器。
        """
        results: List[Dict[str, Any]] = []
        for platform in self.get_supported_platforms():
            try:
                state = await self._storage.get_platform_state(platform)
                if state:
                    results.append({
                        "platform": platform,
                        "platform_name": self.get_platform_display_name(platform),
                        "is_logged_in": state.is_logged_in,
                        "last_login": self._format_last_login(state),
                        "session_path": None,
                    })
                else:
                    results.append({
                        "platform": platform,
                        "platform_name": self.get_platform_display_name(platform),
                        "is_logged_in": False,
                        "last_login": "从未登录",
                        "session_path": None,
                    })
            except Exception as exc:
                logger.warning(f"[登录管理] 读取 {platform} 缓存状态失败: {exc}")
                results.append({
                    "platform": platform,
                    "platform_name": self.get_platform_display_name(platform),
                    "is_logged_in": False,
                    "last_login": "未知",
                    "session_path": None,
                })
        return results

    def _format_last_login(self, state: PlatformLoginState) -> str:
        """格式化最近登录时间"""
        if state.last_success_at:
            from time import localtime, strftime
            return strftime("%Y-%m-%d %H:%M:%S", localtime(state.last_success_at))
        return "从未登录"

    async def refresh_platform_state(self, platform: str, force: bool = False) -> PlatformLoginState:
        """刷新或获取平台登录状态（带缓存）"""
        try:
            cached_state = await self._storage.get_platform_state(platform)
        except Exception as exc:
            logger.warning(f"[登录管理] 读取 {platform} 登录状态缓存失败: {exc}")
            cached_state = None
            
        # 如果有缓存状态且未强制刷新，检查是否需要刷新
        if cached_state and not force:
            cache_age = time.time() - cached_state.last_checked_at
            # 如果缓存时间小于 TTL，直接返回
            if cache_age < self.STATUS_CACHE_TTL:
                return cached_state
            # 如果是已登录状态，永久信任缓存（避免频繁风控检查）
            # 只有在force=True或用户主动调用logout时才会重新验证
            if cached_state.is_logged_in:
                logger.debug(f"[登录管理] {platform} 已登录状态，使用缓存（避免风控）")
                return cached_state

        platform_module = self._get_platform_module(platform)
        try:
            # 严格模式下，平台模块必须进行实时 pong 校验，不允许 Cookie 存在即视为已登录
            state = await platform_module.fetch_login_state(self, force=force)
            state.touch()

            if cached_state and state.is_logged_in and not state.last_success_at:
                state.last_success_at = cached_state.last_success_at or state.last_checked_at

            try:
                await self._storage.save_platform_state(state)
            except Exception as exc:
                logger.warning(f"[登录管理] 写入 {platform} 登录状态缓存失败: {exc}")
            return state
        except Exception as exc:
            # 如果检查失败但有缓存状态，返回缓存状态
            if cached_state:
                logger.warning(f"[登录管理] {platform} 状态检查失败，使用缓存状态: {exc}")
                return cached_state
            
            # 没有缓存时，创建一个默认的未登录状态
            logger.error(f"[登录管理] {platform} 状态检查失败且无缓存: {exc}")
            default_state = PlatformLoginState(
                platform=platform,
                is_logged_in=False,
                message=f"状态检查失败: {exc}",
                last_checked_at=time.time()
            )
            return default_state

    async def get_cookie(self, platform: str) -> Optional[str]:
        """获取平台登录 Cookie"""
        state = await self._storage.get_platform_state(platform)
        if state and state.is_logged_in and state.cookie_str:
            return state.cookie_str

        state = await self.refresh_platform_state(platform, force=True)
        if state.is_logged_in and state.cookie_str:
            return state.cookie_str
        return None

    # === 会话清理 ===

    async def cleanup_session(
        self,
        session_id: str,
        remove_resources: bool = False,
        drop: bool = False,
        reason: Optional[str] = None,
    ):
        """清理指定会话"""
        session = self._active_sessions.get(session_id)
        if not session:
            session = await self._storage.get_session(session_id)
            if not session:
                if drop:
                    await self._storage.delete_session(session_id, None)
                return

        if remove_resources:
            await self._close_session_resources(session)

        task = session.runtime.pop("task", None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        session.browser_context = None
        session.context_page = None
        session.playwright = None

        if reason and session.status not in {"success", "failed", "expired"}:
            session.status = "terminated"
            session.message = reason

        if drop:
            await self._storage.delete_session(session.id, session.platform)
        else:
            await self.persist_session(session)

        await self._remove_active_session(session.id)

    async def cleanup_platform_sessions(self, platform: str, drop: bool = False, reason: Optional[str] = None):
        """清理平台的所有会话"""
        session_ids = await self._storage.list_session_ids_by_platform(platform)
        if not session_ids:
            return

        reason = reason or "会话已结束"
        for session_id in session_ids:
            await self.cleanup_session(session_id, remove_resources=True, drop=drop, reason=reason)

    async def _close_session_resources(self, session: LoginSession):
        """关闭 Playwright 相关资源"""
        context = session.browser_context
        playwright = session.playwright
        session.browser_context = None
        session.context_page = None
        session.playwright = None

        if context:
            try:
                await context.close()
            except Exception:
                pass
        if playwright:
            try:
                await playwright.stop()
            except Exception:
                pass


# 单例服务实例
login_service = LoginService()

__all__ = ["LoginService", "login_service"]
