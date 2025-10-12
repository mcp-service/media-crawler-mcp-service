# -*- coding: utf-8 -*-
"""
Browser Pool Manager - 管理浏览器实例池，避免每次启动新浏览器
"""
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import sys
from pathlib import Path

# 添加 media_crawler 到 Python 路径
MEDIA_CRAWLER_PATH = Path(__file__).parent.parent.parent / "media_crawler"
if str(MEDIA_CRAWLER_PATH) not in sys.path:
    sys.path.insert(0, str(MEDIA_CRAWLER_PATH))

from app.providers.logger import get_logger


@dataclass
class BrowserContext:
    """浏览器上下文包装"""
    context: Any  # Playwright BrowserContext
    browser: Any  # Playwright Browser
    platform: str
    created_at: datetime
    last_used: datetime
    use_count: int = 0

    def mark_used(self) -> None:
        """标记使用"""
        self.last_used = datetime.now()
        self.use_count += 1


class BrowserPool:
    """
    浏览器池管理器

    特性:
    - 预初始化浏览器实例，减少启动开销
    - 支持多平台独立的浏览器池
    - 自动清理长时间未使用的实例
    - 限制最大实例数防止资源耗尽
    """

    def __init__(
        self,
        pool_size: int = 5,
        max_use_count: int = 100,
        max_idle_seconds: int = 3600,
    ):
        """
        初始化浏览器池

        Args:
            pool_size: 每个平台的浏览器池大小
            max_use_count: 单个浏览器实例最大使用次数（防止内存泄漏）
            max_idle_seconds: 最大空闲时间（秒），超过后回收
        """
        self.pool_size = pool_size
        self.max_use_count = max_use_count
        self.max_idle_seconds = max_idle_seconds

        # 每个平台独立的浏览器池
        self.pools: Dict[str, asyncio.Queue] = {}

        # 追踪所有创建的浏览器实例
        self.all_contexts: Dict[str, list[BrowserContext]] = {}

        self.logger = get_logger()
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def init_pool(self, platforms: list[str]) -> None:
        """
        初始化指定平台的浏览器池

        Args:
            platforms: 需要预初始化的平台列表，如 ['xhs', 'dy', 'bili']
        """
        self.logger.info(f"开始初始化浏览器池，平台: {platforms}, 每个平台池大小: {self.pool_size}")

        for platform in platforms:
            if platform not in self.pools:
                self.pools[platform] = asyncio.Queue(maxsize=self.pool_size)
                self.all_contexts[platform] = []

            # 预创建浏览器实例
            for i in range(self.pool_size):
                try:
                    context = await self._create_browser_context(platform)
                    await self.pools[platform].put(context)
                    self.all_contexts[platform].append(context)
                    self.logger.info(f"✓ 平台 {platform} 浏览器 #{i+1} 初始化成功")
                except Exception as e:
                    self.logger.error(f"✗ 平台 {platform} 浏览器 #{i+1} 初始化失败: {e}")

        # 启动清理任务
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        self.logger.info("浏览器池初始化完成")

    async def _create_browser_context(self, platform: str) -> BrowserContext:
        """
        创建新的浏览器上下文

        注意：这里通过导入 media_crawler 的代码创建浏览器，
        但不修改 media_crawler 内部代码
        """
        # 动态导入 media_crawler 的模块
        from tools.playwright_helper import PlaywrightHelper
        import config as mc_config

        # 临时设置配置
        original_platform = getattr(mc_config, 'PLATFORM', None)
        mc_config.PLATFORM = platform

        try:
            # 创建 Playwright 浏览器实例
            playwright_helper = PlaywrightHelper()
            browser, context = await playwright_helper.create_browser()

            browser_context = BrowserContext(
                context=context,
                browser=browser,
                platform=platform,
                created_at=datetime.now(),
                last_used=datetime.now(),
            )

            self.logger.debug(f"为平台 {platform} 创建了新的浏览器上下文")
            return browser_context

        finally:
            # 恢复原配置
            if original_platform:
                mc_config.PLATFORM = original_platform

    async def acquire(self, platform: str, timeout: float = 30.0) -> BrowserContext:
        """
        从池中获取浏览器实例

        Args:
            platform: 平台代码
            timeout: 超时时间（秒）

        Returns:
            BrowserContext 实例

        Raises:
            asyncio.TimeoutError: 超时未获取到浏览器
        """
        # 如果该平台的池不存在，动态创建
        if platform not in self.pools:
            async with self._lock:
                if platform not in self.pools:
                    await self.init_pool([platform])

        try:
            context = await asyncio.wait_for(
                self.pools[platform].get(),
                timeout=timeout
            )

            # 检查是否需要更换浏览器（使用次数过多）
            if context.use_count >= self.max_use_count:
                self.logger.info(
                    f"浏览器实例达到最大使用次数 ({context.use_count})，创建新实例"
                )
                await self._close_browser_context(context)
                context = await self._create_browser_context(platform)
                self.all_contexts[platform].append(context)

            context.mark_used()
            self.logger.debug(
                f"获取平台 {platform} 浏览器，已使用 {context.use_count} 次"
            )
            return context

        except asyncio.TimeoutError:
            self.logger.error(f"获取平台 {platform} 浏览器超时")
            raise

    async def release(self, context: BrowserContext) -> None:
        """
        归还浏览器实例到池中

        Args:
            context: 要归还的浏览器上下文
        """
        platform = context.platform

        if platform not in self.pools:
            self.logger.warning(f"尝试归还到不存在的平台池: {platform}")
            await self._close_browser_context(context)
            return

        try:
            # 非阻塞放回队列
            self.pools[platform].put_nowait(context)
            self.logger.debug(f"归还平台 {platform} 浏览器到池中")
        except asyncio.QueueFull:
            # 如果池已满，关闭该浏览器
            self.logger.warning(f"平台 {platform} 浏览器池已满，关闭浏览器实例")
            await self._close_browser_context(context)

    async def _close_browser_context(self, context: BrowserContext) -> None:
        """关闭浏览器上下文"""
        try:
            if context.context:
                await context.context.close()
            if context.browser:
                await context.browser.close()
            self.logger.debug(f"关闭平台 {context.platform} 的浏览器实例")
        except Exception as e:
            self.logger.error(f"关闭浏览器时出错: {e}")

    async def _cleanup_loop(self) -> None:
        """定期清理长时间未使用的浏览器实例"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟检查一次

                now = datetime.now()
                for platform, contexts in self.all_contexts.items():
                    for context in contexts[:]:  # 复制列表以便修改
                        idle_seconds = (now - context.last_used).total_seconds()

                        if idle_seconds > self.max_idle_seconds:
                            self.logger.info(
                                f"清理平台 {platform} 空闲 {idle_seconds:.0f}s 的浏览器"
                            )
                            await self._close_browser_context(context)
                            contexts.remove(context)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"清理循环出错: {e}")

    async def shutdown(self) -> None:
        """关闭所有浏览器实例"""
        self.logger.info("开始关闭浏览器池...")

        # 取消清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # 关闭所有浏览器
        for platform, contexts in self.all_contexts.items():
            for context in contexts:
                await self._close_browser_context(context)

        self.pools.clear()
        self.all_contexts.clear()
        self.logger.info("浏览器池已关闭")

    def get_stats(self) -> Dict[str, Any]:
        """获取池状态统计"""
        stats = {}
        for platform in self.pools:
            contexts = self.all_contexts.get(platform, [])
            stats[platform] = {
                "pool_size": self.pools[platform].qsize(),
                "total_contexts": len(contexts),
                "total_uses": sum(c.use_count for c in contexts),
                "avg_uses": (
                    sum(c.use_count for c in contexts) / len(contexts)
                    if contexts else 0
                ),
            }
        return stats
