# -*- coding: utf-8 -*-
"""
登录核心服务
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional

from app.config.settings import Platform, global_settings
from app.providers.logger import get_logger

from .base import BaseLoginAdapter
from .exceptions import LoginServiceError
from .models import LoginSession, LoginStartPayload, PlatformLoginState
from .bilibili import BilibiliLoginAdapter

logger = get_logger()


class LoginService:
    """统一的登录服务"""

    STATUS_CACHE_TTL = 60

    def __init__(self):
        self._sessions: Dict[str, LoginSession] = {}
        self._sessions_lock = asyncio.Lock()
        self._platform_state: Dict[str, PlatformLoginState] = {}
        self._state_lock = asyncio.Lock()

        self._handlers: Dict[str, BaseLoginAdapter] = {
            Platform.BILIBILI.value: BilibiliLoginAdapter(self),
        }

    def get_supported_platforms(self) -> List[str]:
        """获取支持的登录平台"""
        enabled = {
            (p.value if hasattr(p, "value") else str(p))
            for p in global_settings.platform.enabled_platforms
        }
        return [platform for platform in self._handlers.keys() if platform in enabled]

    def get_session(self, session_id: str) -> Optional[LoginSession]:
        """获取会话对象（无需锁）"""
        return self._sessions.get(session_id)

    def _get_handler(self, platform: str) -> BaseLoginAdapter:
        handler = self._handlers.get(platform)
        if not handler:
            raise LoginServiceError(f"平台 {platform} 暂不支持或未启用登录功能")
        return handler

    async def start_login(self, payload: LoginStartPayload) -> Dict[str, Any]:
        """启动登录流程"""
        platform = payload.platform
        handler = self._get_handler(platform)

        session_id = str(uuid.uuid4())
        session = LoginSession(id=session_id, platform=platform, login_type=payload.login_type)

        await self.cleanup_platform_sessions(platform, drop=True)

        async with self._sessions_lock:
            self._sessions[session_id] = session

        try:
            response = await handler.start_login(session, payload)
            return response
        except Exception as exc:
            logger.error(f"[登录管理] 启动登录失败: {exc}")
            await self.cleanup_session(session_id, remove_resources=True, drop=True)
            raise LoginServiceError(f"启动登录失败: {exc}") from exc

    async def get_login_status(self, platform: str) -> Dict[str, Any]:
        """获取平台登录状态"""
        handler = self._get_handler(platform)
        state = await self.refresh_platform_state(platform, force=False)
        message = state.message or ("已登录" if state.is_logged_in else "未登录")
        return {
            "platform": platform,
            "platform_name": handler.display_name,
            "is_logged_in": state.is_logged_in,
            "user_info": state.user_info,
            "message": message,
        }

    async def logout(self, platform: str) -> Dict[str, Any]:
        """退出登录"""
        handler = self._get_handler(platform)
        await handler.logout()
        await self._set_platform_state(
            platform,
            PlatformLoginState(
                platform=platform,
                is_logged_in=False,
                last_checked_at=time.time(),
                message="已退出登录",
            ),
        )
        return {
            "status": "success",
            "platform": platform,
            "message": "退出登录成功",
        }

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """获取登录会话状态"""
        async with self._sessions_lock:
            session = self._sessions.get(session_id)
        if not session:
            raise LoginServiceError("会话不存在")

        if (
            session.login_type == "qrcode"
            and session.status in {"started", "waiting", "processing"}
            and session.qrcode_timestamp
        ):
            elapsed = time.time() - session.qrcode_timestamp
            if elapsed > 180 and session.status not in {"success", "failed", "expired"}:
                session.status = "expired"
                session.message = "二维码已过期，请重新获取"
                asyncio.create_task(
                    self.cleanup_session(session_id, remove_resources=True)
                )

        return session.to_public_dict()

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有平台的登录状态"""
        results: List[Dict[str, Any]] = []
        for platform in self.get_supported_platforms():
            handler = self._get_handler(platform)
            state = await self.refresh_platform_state(platform, force=False)
            last_login = handler.format_last_login(state)
            if state.is_logged_in and not state.last_success_at:
                last_login = "最近登录"
            results.append(
                {
                    "platform": platform,
                    "platform_name": handler.display_name,
                    "is_logged_in": state.is_logged_in,
                    "last_login": last_login,
                    "session_path": str(handler.user_data_dir) if state.is_logged_in else None,
                }
            )
        return results

    async def refresh_platform_state(self, platform: str, force: bool = False) -> PlatformLoginState:
        """刷新或获取平台登录状态（带缓存）"""
        async with self._state_lock:
            cached = self._platform_state.get(platform)
            if (
                not force
                and cached
                and (time.time() - cached.last_checked_at) < self.STATUS_CACHE_TTL
            ):
                return cached

        handler = self._get_handler(platform)
        state = await handler.fetch_login_state()
        await self._set_platform_state(platform, state)
        return state

    async def _set_platform_state(self, platform: str, state: PlatformLoginState):
        async with self._state_lock:
            previous = self._platform_state.get(platform)
            if previous and not state.last_success_at and state.is_logged_in:
                state.last_success_at = previous.last_success_at or time.time()
            self._platform_state[platform] = state

    async def get_cookie(self, platform: str) -> Optional[str]:
        """获取平台登录 Cookie"""
        state = await self.refresh_platform_state(platform, force=False)
        if state.is_logged_in and state.cookie_str:
            return state.cookie_str
        state = await self.refresh_platform_state(platform, force=True)
        if state.is_logged_in and state.cookie_str:
            return state.cookie_str
        return None

    async def cleanup_session(
        self,
        session_id: str,
        remove_resources: bool = False,
        drop: bool = False,
    ):
        """清理指定会话"""
        async with self._sessions_lock:
            session = self._sessions.get(session_id)
        if not session:
            return

        if remove_resources:
            await self._close_session_resources(session)

        task = session.metadata.pop("task", None)
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
        session.metadata.pop("login_obj", None)
        session.metadata.pop("error", None)

        if drop:
            async with self._sessions_lock:
                self._sessions.pop(session_id, None)

    async def cleanup_platform_sessions(self, platform: str, drop: bool = False):
        """清理平台的所有会话"""
        async with self._sessions_lock:
            session_ids = [sid for sid, s in self._sessions.items() if s.platform == platform]
        for session_id in session_ids:
            await self.cleanup_session(session_id, remove_resources=True, drop=drop)

    async def _close_session_resources(self, session: LoginSession):
        """关闭 Playwright 相关资源"""
        context = session.browser_context
        playwright = session.playwright
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
