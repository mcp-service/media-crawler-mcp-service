# -*- coding: utf-8 -*-
"""
登录状态存储 - Redis 实现
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from pathlib import Path
import json

import ujson

from app.core.login.models import LoginSession, PlatformLoginState
from app.providers.cache.redis_cache import async_redis_storage
from app.providers.logger import get_logger


class RedisLoginStorage:
    """使用 Redis 持久化登录会话与平台状态"""

    SESSION_KEY_PREFIX = "login:session:"
    SESSION_INDEX_KEY = "login:session:index"
    PLATFORM_SESSION_KEY_PREFIX = "login:platform:sessions:"
    PLATFORM_STATE_KEY_PREFIX = "login:platform:state:"
    PLATFORM_INDEX_KEY = "login:platform:index"

    def __init__(self, session_ttl: int = 86400, platform_ttl: int = 365 * 86400):  # 平台状态改为 365 天（1年）
        self.session_ttl = session_ttl
        self.platform_ttl = platform_ttl
        self.logger = get_logger()

    # === Session 操作 ===

    def _session_key(self, session_id: str) -> str:
        return f"{self.SESSION_KEY_PREFIX}{session_id}"

    def _platform_sessions_key(self, platform: str) -> str:
        return f"{self.PLATFORM_SESSION_KEY_PREFIX}{platform}"

    def _platform_state_key(self, platform: str) -> str:
        return f"{self.PLATFORM_STATE_KEY_PREFIX}{platform}"

    async def save_session(self, session: LoginSession) -> None:
        """保存或更新会话状态"""
        data = session.to_storage_dict()
        payload = ujson.dumps(data, ensure_ascii=False).encode("utf-8")
        key = self._session_key(session.id)
        await async_redis_storage.set(key, payload, ex=self.session_ttl)
        await async_redis_storage.zadd(
            self.SESSION_INDEX_KEY,
            {session.id: data["created_at"]},
        )
        await async_redis_storage.sadd(
            self._platform_sessions_key(session.platform),
            session.id,
        )

    async def update_session_fields(self, session_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """增量更新会话字段"""
        existing = await self.get_session_raw(session_id)
        if not existing:
            return None
        existing.update(fields)
        existing["updated_at"] = time.time()
        payload = ujson.dumps(existing, ensure_ascii=False).encode("utf-8")
        await async_redis_storage.set(self._session_key(session_id), payload, ex=self.session_ttl)
        return existing

    async def get_session_raw(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话原始数据"""
        key = self._session_key(session_id)
        raw = await async_redis_storage.get(key)
        if not raw:
            return None
        return ujson.loads(raw)

    async def get_session(self, session_id: str) -> Optional[LoginSession]:
        data = await self.get_session_raw(session_id)
        if not data:
            return None
        return LoginSession.from_storage_dict(data)

    async def delete_session(self, session_id: str, platform: Optional[str] = None) -> None:
        if platform is None:
            existing = await self.get_session_raw(session_id)
            if existing:
                platform = existing.get("platform")
        await async_redis_storage.delete(self._session_key(session_id))
        await async_redis_storage.zrem(self.SESSION_INDEX_KEY, session_id)
        if platform:
            await async_redis_storage.srem(self._platform_sessions_key(platform), session_id)

    async def list_session_ids_by_platform(self, platform: str) -> List[str]:
        members = await async_redis_storage.smembers(self._platform_sessions_key(platform))
        if not members:
            return []
        return [member.decode("utf-8") if isinstance(member, bytes) else str(member) for member in members]

    async def list_all_sessions(self) -> List[LoginSession]:
        session_ids = await async_redis_storage.zrevrange(self.SESSION_INDEX_KEY, 0, -1)
        results: List[LoginSession] = []
        for raw_id in session_ids:
            session_id = raw_id.decode("utf-8") if isinstance(raw_id, bytes) else str(raw_id)
            data = await self.get_session(session_id)
            if data:
                results.append(data)
        return results

    # === 平台状态操作 ===

    async def save_platform_state(self, state: PlatformLoginState) -> None:
        data = state.to_storage_dict()
        data["saved_at"] = time.time()
        payload = ujson.dumps(data, ensure_ascii=False).encode("utf-8")
        key = self._platform_state_key(state.platform)
        await async_redis_storage.set(key, payload, ex=self.platform_ttl)
        await async_redis_storage.sadd(self.PLATFORM_INDEX_KEY, state.platform)

        # 若为已登录状态，同时刷新本地 cookie 文件，便于外部工具读取
        try:
            if state.is_logged_in:
                base_dir = Path("browser_data") / (state.platform or "unknown")
                base_dir.mkdir(parents=True, exist_ok=True)
                # cookies.txt
                if state.cookie_str:
                    (base_dir / "cookies.txt").write_text(state.cookie_str, encoding="utf-8")
                # cookies.json
                if state.cookie_dict:
                    (base_dir / "cookies.json").write_text(
                        json.dumps(state.cookie_dict, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
        except Exception as exc:
            self.logger.warning(f"[登录管理] 刷新本地 cookie 文件失败: {exc}")

    async def get_platform_state_raw(self, platform: str) -> Optional[Dict[str, Any]]:
        raw = await async_redis_storage.get(self._platform_state_key(platform))
        if not raw:
            return None
        return ujson.loads(raw)

    async def get_platform_state(self, platform: str) -> Optional[PlatformLoginState]:
        data = await self.get_platform_state_raw(platform)
        if not data:
            self.logger.debug(f"{platform} 存储中没有状态数据")
            return None
        state = PlatformLoginState.from_storage_dict(data)
        self.logger.debug(f" {platform} 从存储加载状态: is_logged_in={state.is_logged_in}, message='{state.message}'")
        return state

    async def remove_platform_state(self, platform: str) -> None:
        await async_redis_storage.delete(self._platform_state_key(platform))
        await async_redis_storage.srem(self.PLATFORM_INDEX_KEY, platform)
