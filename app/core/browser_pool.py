# -*- coding: utf-8 -*-
"""
浏览器池管理器 - 精简版
每个平台维护一个共享的浏览器实例，延迟销毁
"""

from __future__ import annotations

import asyncio
import time
import json
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from app.providers.logger import get_logger
from app.config.settings import global_settings

logger = get_logger()


class InstanceState(Enum):
    """浏览器实例状态"""
    CREATING = "creating"
    IDLE = "idle"
    BUSY = "busy"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass
class BrowserInstance:
    """浏览器实例"""
    platform: str
    instance_id: str = field(default_factory=lambda: f"instance_{int(time.time() * 1000)}")
    context: Optional[BrowserContext] = None
    page: Optional[Page] = None
    playwright: Optional[Playwright] = None
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    ref_count: int = 0
    state: InstanceState = InstanceState.CREATING
    user_data_dir: Optional[Path] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.user_data_dir is None:
            self.user_data_dir = Path("browser_data") / self.platform

    @property
    def is_idle(self) -> bool:
        """是否空闲"""
        return self.state == InstanceState.IDLE and self.ref_count == 0

    @property
    def is_expired(self) -> bool:
        """是否过期（空闲超过10分钟）"""
        idle_time = time.time() - self.last_used
        return idle_time > 600  # 10分钟

    def touch(self):
        """更新最后使用时间"""
        self.last_used = time.time()

    async def acquire(self) -> None:
        """获取实例"""
        if self.state != InstanceState.IDLE:
            raise RuntimeError(f"实例 {self.instance_id} 状态错误: {self.state}")

        self.ref_count += 1
        self.state = InstanceState.BUSY
        self.touch()
        logger.debug(f"[BrowserPool] 获取实例 {self.instance_id}, ref_count: {self.ref_count}")

    async def release(self) -> None:
        """释放实例"""
        if self.ref_count <= 0:
            logger.warning(f"[BrowserPool] 实例 {self.instance_id} ref_count 已为 0")
            return

        self.ref_count -= 1
        if self.ref_count == 0:
            self.state = InstanceState.IDLE

        self.touch()
        logger.debug(f"[BrowserPool] 释放实例 {self.instance_id}, ref_count: {self.ref_count}")

    async def close(self) -> None:
        """关闭实例"""
        if self.state == InstanceState.CLOSED:
            return

        self.state = InstanceState.CLOSING
        logger.info(f"[BrowserPool] 关闭实例 {self.instance_id}")

        # 并行关闭资源
        cleanup_tasks = []

        if self.page:
            cleanup_tasks.append(self._safe_close(self.page.close(), "page"))

        if self.context:
            cleanup_tasks.append(self._safe_close(self.context.close(), "context"))

        if self.playwright:
            cleanup_tasks.append(self._safe_close(self.playwright.stop(), "playwright"))

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        self.state = InstanceState.CLOSED
        logger.info(f"[BrowserPool] 实例 {self.instance_id} 已关闭")

    async def _safe_close(self, close_coro, resource_name: str) -> None:
        """安全关闭资源"""
        try:
            await close_coro
        except Exception as exc:
            logger.debug(f"[BrowserPool] 关闭 {resource_name} 时出错: {exc}")


class BrowserInstanceFactory:
    """浏览器实例工厂"""

    def __init__(self, platform: str):
        self.platform = platform
        self._domain_map = {
            "bili": ".bilibili.com",
            "xhs": ".xiaohongshu.com",
            "dy": ".douyin.com",
            "ks": ".kuaishou.com",
            "wb": ".weibo.com",
        }

    async def create_instance(
        self,
        headless: bool = True,
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None
    ) -> BrowserInstance:
        """创建浏览器实例"""

        instance = BrowserInstance(platform=self.platform)

        try:
            # 设置默认值
            if viewport is None:
                browser_cfg = global_settings.browser
                viewport = {
                    "width": getattr(browser_cfg, "viewport_width", 1280),
                    "height": getattr(browser_cfg, "viewport_height", 800)
                }

            if user_agent is None:
                browser_cfg = global_settings.browser
                user_agent = getattr(browser_cfg, "user_agent", None) or self._get_default_user_agent()

            # 创建 Playwright 实例
            instance.playwright = await async_playwright().start()
            chromium = instance.playwright.chromium

            # 确保用户数据目录存在
            instance.user_data_dir.parent.mkdir(parents=True, exist_ok=True)

            # 浏览器参数
            browser_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]

            # 创建持久化浏览器上下文
            instance.context = await chromium.launch_persistent_context(
                user_data_dir=str(instance.user_data_dir),
                headless=headless,
                viewport=viewport,
                user_agent=user_agent,
                accept_downloads=True,
                args=browser_args,
            )

            # 创建页面
            instance.page = await instance.context.new_page()

            # 加载本地 Cookie（如果存在）
            await self._load_cookies(instance)

            instance.state = InstanceState.IDLE
            logger.info(f"[BrowserPool] 创建 {self.platform} 实例成功: {instance.instance_id}")

            return instance

        except Exception as exc:
            logger.error(f"[BrowserPool] 创建 {self.platform} 实例失败: {exc}")
            await instance.close()
            raise

    def _get_default_user_agent(self) -> str:
        """获取默认User-Agent"""
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    async def _load_cookies(self, instance: BrowserInstance) -> None:
        """加载本地 Cookie"""
        cookies_json = instance.user_data_dir / "cookies.json"
        if not cookies_json.exists():
            return

        try:
            raw_data = cookies_json.read_text(encoding="utf-8")
            cookies_data = json.loads(raw_data)

            if isinstance(cookies_data, dict):
                # 字典格式转换为 Playwright 格式
                domain = self._domain_map.get(self.platform, f".{self.platform}.com")

                playwright_cookies = []
                for name, value in cookies_data.items():
                    playwright_cookies.append({
                        "name": name,
                        "value": str(value),
                        "domain": domain,
                        "path": "/",
                    })

                if playwright_cookies:
                    await instance.context.add_cookies(playwright_cookies)
                    logger.info(f"[BrowserPool] 为 {self.platform} 实例加载了 {len(playwright_cookies)} 个 Cookie")

        except Exception as exc:
            logger.warning(f"[BrowserPool] 加载 {self.platform} Cookie 失败: {exc}")


class PlatformBrowserPool:
    """单个平台的浏览器池（每个平台一个实例）"""

    def __init__(self, platform: str):
        self.platform = platform
        self.factory = BrowserInstanceFactory(platform)
        self.instance: Optional[BrowserInstance] = None
        self.lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_closed = False

    async def start(self) -> None:
        """启动池"""
        logger.info(f"[BrowserPool] 启动 {self.platform} 浏览器池")

        # 启动清理任务（每2分钟检查一次）
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info(f"[BrowserPool] {self.platform} 浏览器池启动完成")

    async def acquire(self) -> BrowserInstance:
        """获取浏览器实例"""
        async with self.lock:
            if self._is_closed:
                raise RuntimeError(f"浏览器池 {self.platform} 已关闭")

            # 如果有可用实例，直接使用
            if self.instance and not self.instance.is_expired and self.instance.state in [InstanceState.IDLE, InstanceState.BUSY]:
                await self.instance.acquire()
                return self.instance

            # 如果实例过期或不存在，创建新实例
            if self.instance:
                logger.info(f"[BrowserPool] {self.platform} 实例已过期，创建新实例")
                await self.instance.close()

            self.instance = await self._create_instance()
            await self.instance.acquire()
            return self.instance

    async def release(self, instance: BrowserInstance) -> None:
        """释放浏览器实例"""
        await instance.release()
        logger.debug(f"[BrowserPool] 释放 {self.platform} 实例")

    async def _create_instance(self) -> BrowserInstance:
        """创建新实例"""
        browser_cfg = global_settings.browser

        instance = await self.factory.create_instance(
            headless=getattr(browser_cfg, "headless", True),
            viewport={
                "width": getattr(browser_cfg, "viewport_width", 1280),
                "height": getattr(browser_cfg, "viewport_height", 800)
            },
            user_agent=getattr(browser_cfg, "user_agent", None)
        )

        logger.info(f"[BrowserPool] 创建 {self.platform} 实例: {instance.instance_id}")
        return instance

    async def _cleanup_loop(self) -> None:
        """清理循环（每2分钟检查一次过期实例）"""
        while not self._is_closed:
            try:
                await asyncio.sleep(120)  # 2分钟
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"[BrowserPool] {self.platform} 清理循环出错: {exc}")

    async def _cleanup_expired(self) -> None:
        """清理过期实例"""
        async with self.lock:
            if self.instance and self.instance.is_idle and self.instance.is_expired:
                logger.info(f"[BrowserPool] 清理 {self.platform} 过期实例: {self.instance.instance_id}")
                await self.instance.close()
                self.instance = None

    async def close(self) -> None:
        """关闭浏览器池"""
        if self._is_closed:
            return

        self._is_closed = True
        logger.info(f"[BrowserPool] 关闭 {self.platform} 浏览器池")

        # 取消清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # 关闭实例
        if self.instance:
            await self.instance.close()
            self.instance = None

        logger.info(f"[BrowserPool] {self.platform} 浏览器池已关闭")

    def get_stats(self) -> Dict[str, Any]:
        """获取池统计信息"""
        if self.instance:
            return {
                "platform": self.platform,
                "has_instance": True,
                "state": self.instance.state.value,
                "is_idle": self.instance.is_idle,
                "is_expired": self.instance.is_expired,
                "ref_count": self.instance.ref_count,
            }
        else:
            return {
                "platform": self.platform,
                "has_instance": False,
            }


class BrowserPoolManager:
    """浏览器池管理器 - 管理所有平台的浏览器池"""

    def __init__(self):
        self.pools: Dict[str, PlatformBrowserPool] = {}
        self.lock = asyncio.Lock()
        self._is_initialized = False
        self._is_closed = False

    async def initialize(self, platforms: list[str] = None) -> None:
        """初始化浏览器池管理器"""
        if self._is_initialized:
            return

        async with self.lock:
            if self._is_initialized:
                return

            logger.info("[BrowserPoolManager] 初始化浏览器池管理器")

            if platforms is None:
                # 从全局配置获取启用的平台
                from app.config.settings import global_settings
                platform_config = global_settings.platform

                if hasattr(platform_config, 'enabled_platforms'):
                    enabled_platforms = platform_config.enabled_platforms

                    # 处理不同的配置格式
                    if isinstance(enabled_platforms, str):
                        if enabled_platforms.lower() == "all":
                            platforms = ["xhs", "bili", "dy", "wb"]
                        else:
                            platforms = [p.strip() for p in enabled_platforms.split(",") if p.strip()]
                    elif isinstance(enabled_platforms, list):
                        platforms = []
                        for platform in enabled_platforms:
                            if hasattr(platform, 'value'):
                                platforms.append(platform.value)
                            else:
                                platforms.append(str(platform))
                    else:
                        platforms = ["xhs", "bili"]
                else:
                    platforms = ["xhs", "bili"]

            # 过滤有效的平台
            valid_platforms = []
            supported_platforms = {"xhs", "bili", "dy", "wb", "ks"}

            for platform in platforms:
                platform = str(platform).lower()
                if platform in supported_platforms:
                    valid_platforms.append(platform)
                else:
                    logger.warning(f"[BrowserPoolManager] 跳过不支持的平台: {platform}")

            if not valid_platforms:
                logger.warning("[BrowserPoolManager] 没有启用的平台，使用默认配置")
                valid_platforms = ["xhs", "bili"]

            # 为每个启用的平台创建浏览器池
            for platform in valid_platforms:
                await self._create_platform_pool(platform)

            self._is_initialized = True
            logger.info(f"[BrowserPoolManager] 初始化完成，启用平台: {', '.join(valid_platforms)}")

    async def _create_platform_pool(self, platform: str) -> None:
        """创建平台浏览器池"""
        pool = PlatformBrowserPool(platform)
        self.pools[platform] = pool

        # 启动池
        try:
            await pool.start()
        except Exception as exc:
            logger.error(f"[BrowserPoolManager] 启动 {platform} 浏览器池失败: {exc}")

    async def acquire(self, platform: str) -> BrowserInstance:
        """获取浏览器实例"""
        if not self._is_initialized:
            await self.initialize()

        if self._is_closed:
            raise RuntimeError("浏览器池管理器已关闭")

        if platform not in self.pools:
            # 动态创建平台池
            async with self.lock:
                if platform not in self.pools:
                    await self._create_platform_pool(platform)

        pool = self.pools[platform]
        instance = await pool.acquire()

        logger.debug(f"[BrowserPoolManager] 获取 {platform} 实例: {instance.instance_id}")
        return instance

    async def release(self, instance: BrowserInstance) -> None:
        """释放浏览器实例"""
        if instance.platform in self.pools:
            pool = self.pools[instance.platform]
            await pool.release(instance)
            logger.debug(f"[BrowserPoolManager] 释放 {instance.platform} 实例")
        else:
            logger.warning(f"[BrowserPoolManager] 未找到平台池: {instance.platform}")

    async def cleanup_platform(self, platform: str, force: bool = False) -> None:
        """清理指定平台的浏览器池"""
        if platform in self.pools:
            pool = self.pools[platform]
            if force:
                await pool.close()
                del self.pools[platform]
                logger.info(f"[BrowserPoolManager] 强制清理 {platform} 浏览器池")
            else:
                await pool._cleanup_expired()
                logger.info(f"[BrowserPoolManager] 清理 {platform} 过期实例")

    async def close(self) -> None:
        """关闭浏览器池管理器"""
        if self._is_closed:
            return

        self._is_closed = True
        logger.info("[BrowserPoolManager] 关闭浏览器池管理器")

        # 并行关闭所有平台池
        close_tasks = []
        for platform, pool in self.pools.items():
            close_tasks.append(pool.close())

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        self.pools.clear()
        logger.info("[BrowserPoolManager] 浏览器池管理器已关闭")

    def get_stats(self) -> Dict[str, Any]:
        """获取所有池的统计信息"""
        stats = {
            "total_platforms": len(self.pools),
            "platforms": {}
        }

        for platform, pool in self.pools.items():
            stats["platforms"][platform] = pool.get_stats()

        return stats

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health = {
            "status": "healthy",
            "initialized": self._is_initialized,
            "closed": self._is_closed,
            "platforms": {}
        }

        for platform, pool in self.pools.items():
            try:
                instance = await pool.acquire()
                await pool.release(instance)
                health["platforms"][platform] = "healthy"
            except Exception as exc:
                health["platforms"][platform] = f"unhealthy: {exc}"
                health["status"] = "unhealthy"

        return health


# 全局单例
_pool_manager: Optional[BrowserPoolManager] = None
_manager_lock = asyncio.Lock()


async def get_pool_manager() -> BrowserPoolManager:
    """获取全局浏览器池管理器实例"""
    global _pool_manager

    if _pool_manager is None:
        async with _manager_lock:
            if _pool_manager is None:
                _pool_manager = BrowserPoolManager()
                await _pool_manager.initialize()

    return _pool_manager


async def close_pool_manager() -> None:
    """关闭全局浏览器池管理器"""
    global _pool_manager

    if _pool_manager:
        await _pool_manager.close()
        _pool_manager = None


@asynccontextmanager
async def browser_instance(pool_manager: BrowserPoolManager, platform: str):
    """浏览器实例上下文管理器"""
    instance = await pool_manager.acquire(platform)
    try:
        yield instance
    finally:
        await pool_manager.release(instance)


# 导出主要类
__all__ = [
    "BrowserPoolManager",
    "PlatformBrowserPool",
    "BrowserInstance",
    "InstanceState",
    "browser_instance",
    "get_pool_manager",
    "close_pool_manager"
]
