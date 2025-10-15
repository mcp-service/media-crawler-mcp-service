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
from .bilibili import BilibiliLoginAdapter
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
        self._handlers: Dict[str, BaseLoginAdapter] = {
            Platform.BILIBILI.value: BilibiliLoginAdapter(self),
        }

    # === 基础能力 ===

    def get_supported_platforms(self) -> List[str]:
        """获取支持的登录平台"""
        enabled = {
            (p.value if hasattr(p, "value") else str(p))
            for p in global_settings.platform.enabled_platforms
        }
        return [platform for platform in self._handlers if platform in enabled]

    def get_session(self, session_id: str) -> Optional[LoginSession]:
        """获取活跃会话（仅限当前进程内存）"""
        return self._active_sessions.get(session_id)

    def _get_handler(self, platform: str) -> BaseLoginAdapter:
        handler = self._handlers.get(platform)
        if not handler:
            raise LoginServiceError(f"平台 {platform} 暂不支持或未启用登录功能")
        return handler

    async def _register_active_session(self, session: LoginSession):
        async with self._active_sessions_lock:
            self._active_sessions[session.id] = session

    async def _remove_active_session(self, session_id: str):
        async with self._active_sessions_lock:
            self._active_sessions.pop(session_id, None)

    async def persist_session(self, session: LoginSession):
        """持久化会话状态到 Redis"""
        session.touch()
        await self._storage.save_session(session)

    # === 登录流程 ===

    async def start_login(self, payload: LoginStartPayload) -> Dict[str, Any]:
        """启动登录流程"""
        platform = payload.platform
        handler = self._get_handler(platform)

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
            response = await handler.start_login(session, payload)
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
        record = await self._storage.get_session(session_id)
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
        cached_state = await self._storage.get_platform_state(platform)
        if (
            not force
            and cached_state
            and (time.time() - cached_state.last_checked_at) < self.STATUS_CACHE_TTL
        ):
            return cached_state

        handler = self._get_handler(platform)
        state = await handler.fetch_login_state()
        state.touch()

        if cached_state and state.is_logged_in and not state.last_success_at:
            state.last_success_at = cached_state.last_success_at or state.last_checked_at

        await self._storage.save_platform_state(state)
        return state

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
