# -*- coding: utf-8 -*-
"""
Session Manager - 管理登录会话、Cookie 存储和复用
"""
import json
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from app.providers.logger import get_logger


@dataclass
class SessionInfo:
    """会话信息"""
    platform: str
    user_id: Optional[str] = None
    cookies: Dict[str, Any] = None
    login_time: Optional[datetime] = None
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_valid: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 转换 datetime 为字符串
        if self.login_time:
            data['login_time'] = self.login_time.isoformat()
        if self.last_used:
            data['last_used'] = self.last_used.isoformat()
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionInfo':
        """从字典创建"""
        # 转换字符串为 datetime
        if data.get('login_time'):
            data['login_time'] = datetime.fromisoformat(data['login_time'])
        if data.get('last_used'):
            data['last_used'] = datetime.fromisoformat(data['last_used'])
        if data.get('expires_at'):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)


class SessionManager:
    """
    会话管理器

    功能:
    - 持久化存储 Cookie（避免重复登录）
    - 自动检查会话有效性
    - 支持多平台独立会话
    - 会话过期自动清理
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        初始化会话管理器

        Args:
            storage_dir: Cookie 存储目录，默认为 media_crawler/browser_data/
        """
        if storage_dir is None:
            # 使用 media_crawler 的 browser_data 目录
            storage_dir = Path(__file__).parent.parent.parent / "browser_data"

        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 内存中的会话缓存
        self.sessions: Dict[str, SessionInfo] = {}

        self.logger = get_logger()
        self._lock = asyncio.Lock()

    async def load_session(self, platform: str) -> Optional[SessionInfo]:
        """
        加载平台的会话信息

        Args:
            platform: 平台代码

        Returns:
            SessionInfo 或 None
        """
        async with self._lock:
            # 优先从内存缓存读取
            if platform in self.sessions:
                session = self.sessions[platform]
                if self._is_session_valid(session):
                    session.last_used = datetime.now()
                    self.logger.debug(f"从缓存加载平台 {platform} 的会话")
                    return session
                else:
                    # 会话已过期，移除
                    del self.sessions[platform]

            # 从文件加载
            session_file = self.storage_dir / f"{platform}_session.json"
            if session_file.exists():
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    session = SessionInfo.from_dict(data)

                    if self._is_session_valid(session):
                        session.last_used = datetime.now()
                        self.sessions[platform] = session
                        self.logger.info(f"从文件加载平台 {platform} 的会话")
                        return session
                    else:
                        self.logger.warning(f"平台 {platform} 的会话已过期")
                        session_file.unlink()  # 删除过期文件

                except Exception as e:
                    self.logger.error(f"加载平台 {platform} 会话失败: {e}")

        return None

    async def save_session(
        self,
        platform: str,
        cookies: Dict[str, Any],
        user_id: Optional[str] = None,
        expires_in_days: int = 30
    ) -> SessionInfo:
        """
        保存平台的会话信息

        Args:
            platform: 平台代码
            cookies: Cookie 字典
            user_id: 用户ID（可选）
            expires_in_days: 会话有效期（天）

        Returns:
            SessionInfo
        """
        async with self._lock:
            now = datetime.now()
            session = SessionInfo(
                platform=platform,
                user_id=user_id,
                cookies=cookies,
                login_time=now,
                last_used=now,
                expires_at=now + timedelta(days=expires_in_days),
                is_valid=True
            )

            # 保存到内存缓存
            self.sessions[platform] = session

            # 持久化到文件
            session_file = self.storage_dir / f"{platform}_session.json"
            try:
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
                self.logger.info(f"平台 {platform} 会话已保存")
            except Exception as e:
                self.logger.error(f"保存平台 {platform} 会话失败: {e}")

            return session

    async def invalidate_session(self, platform: str) -> None:
        """
        使平台会话失效

        Args:
            platform: 平台代码
        """
        async with self._lock:
            # 从内存移除
            if platform in self.sessions:
                del self.sessions[platform]

            # 删除文件
            session_file = self.storage_dir / f"{platform}_session.json"
            if session_file.exists():
                session_file.unlink()
                self.logger.info(f"平台 {platform} 会话已失效")

    def _is_session_valid(self, session: SessionInfo) -> bool:
        """
        检查会话是否有效

        Args:
            session: 会话信息

        Returns:
            是否有效
        """
        if not session.is_valid:
            return False

        # 检查是否过期
        if session.expires_at and datetime.now() > session.expires_at:
            self.logger.debug(f"平台 {session.platform} 会话已过期")
            return False

        # 检查是否有 Cookie
        if not session.cookies:
            return False

        return True

    async def get_cookies(self, platform: str) -> Optional[Dict[str, Any]]:
        """
        获取平台的 Cookie

        Args:
            platform: 平台代码

        Returns:
            Cookie 字典或 None
        """
        session = await self.load_session(platform)
        if session and session.cookies:
            return session.cookies
        return None

    async def has_valid_session(self, platform: str) -> bool:
        """
        检查平台是否有有效会话

        Args:
            platform: 平台代码

        Returns:
            是否有有效会话
        """
        session = await self.load_session(platform)
        return session is not None

    async def cleanup_expired_sessions(self) -> int:
        """
        清理所有过期会话

        Returns:
            清理的会话数量
        """
        async with self._lock:
            cleaned = 0

            # 检查内存缓存
            expired_platforms = []
            for platform, session in self.sessions.items():
                if not self._is_session_valid(session):
                    expired_platforms.append(platform)

            for platform in expired_platforms:
                await self.invalidate_session(platform)
                cleaned += 1

            # 检查文件
            for session_file in self.storage_dir.glob("*_session.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    session = SessionInfo.from_dict(data)

                    if not self._is_session_valid(session):
                        session_file.unlink()
                        cleaned += 1
                except Exception as e:
                    self.logger.error(f"检查会话文件 {session_file} 时出错: {e}")

            if cleaned > 0:
                self.logger.info(f"清理了 {cleaned} 个过期会话")

            return cleaned

    def get_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        return {
            "total_sessions": len(self.sessions),
            "platforms": list(self.sessions.keys()),
            "storage_dir": str(self.storage_dir),
            "valid_sessions": sum(
                1 for s in self.sessions.values()
                if self._is_session_valid(s)
            )
        }
