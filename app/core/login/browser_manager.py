# -*- coding: utf-8 -*-
"""
浏览器实例管理器
解决不同平台浏览器实例相互影响的问题
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, Optional, Tuple

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from app.providers.logger import get_logger

logger = get_logger()


class BrowserManager:
    """
    浏览器实例管理器

    功能：
    1. 为每个平台维护独立的 Playwright 实例
    2. 使用互斥锁防止同时创建多个浏览器实例
    3. 复用浏览器上下文，减少频繁创建/销毁
    4. 自动清理长时间未使用的浏览器实例
    """

    def __init__(self):
        # 每个平台的浏览器上下文缓存
        self._contexts: Dict[str, BrowserContext] = {}
        # 每个平台的 Playwright 实例缓存
        self._playwrights: Dict[str, Playwright] = {}
        # 每个平台的互斥锁
        self._locks: Dict[str, asyncio.Lock] = {}
        # 全局锁
        self._global_lock = asyncio.Lock()
        # 使用计数器
        self._ref_counts: Dict[str, int] = {}

    async def get_lock(self, platform: str) -> asyncio.Lock:
        """获取平台专属锁"""
        async with self._global_lock:
            if platform not in self._locks:
                self._locks[platform] = asyncio.Lock()
            return self._locks[platform]

    async def acquire_context(
        self,
        platform: str,
        user_data_dir: Path,
        headless: bool = True,
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[BrowserContext, Page, Playwright]:
        """
        获取或创建浏览器上下文

        Args:
            platform: 平台标识
            user_data_dir: 用户数据目录
            headless: 是否无头模式
            viewport: 视口大小
            user_agent: 用户代理

        Returns:
            (browser_context, page, playwright) 三元组
        """
        lock = await self.get_lock(platform)

        async with lock:
            # 检查是否已有缓存的实例
            if platform in self._contexts:
                try:
                    context = self._contexts[platform]
                    # 测试连接是否有效
                    pages = context.pages
                    if pages:
                        page = pages[0]
                    else:
                        page = await context.new_page()

                    playwright = self._playwrights.get(platform)
                    self._ref_counts[platform] = self._ref_counts.get(platform, 0) + 1

                    logger.info(
                        f"[BrowserManager] 复用 {platform} 浏览器实例 "
                        f"(引用计数: {self._ref_counts[platform]})"
                    )
                    return context, page, playwright

                except Exception as exc:
                    logger.warning(
                        f"[BrowserManager] {platform} 缓存的浏览器上下文已失效: {exc}，重新创建"
                    )
                    await self._cleanup_platform(platform)

            # 创建新的 Playwright 实例
            logger.info(f"[BrowserManager] 为 {platform} 创建新的浏览器实例")

            playwright = await async_playwright().start()
            chromium = playwright.chromium

            # 确保用户数据目录存在
            user_data_dir.parent.mkdir(parents=True, exist_ok=True)

            # 设置默认值
            if viewport is None:
                viewport = {"width": 1280, "height": 800}
            if user_agent is None:
                user_agent = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )

            # 创建持久化浏览器上下文
            context = await chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=headless,
                viewport=viewport,
                user_agent=user_agent,
                accept_downloads=True,
                # 减少资源占用
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )

            page = await context.new_page()

            # 缓存实例
            self._contexts[platform] = context
            self._playwrights[platform] = playwright
            self._ref_counts[platform] = 1

            logger.info(f"[BrowserManager] {platform} 浏览器实例创建成功")

            return context, page, playwright

    async def release_context(self, platform: str, keep_alive: bool = True):
        """
        释放浏览器上下文引用

        Args:
            platform: 平台标识
            keep_alive: 是否保持实例存活（默认True，仅减少引用计数）
        """
        lock = await self.get_lock(platform)

        async with lock:
            if platform not in self._ref_counts:
                return

            self._ref_counts[platform] -= 1

            logger.info(
                f"[BrowserManager] 释放 {platform} 浏览器引用 "
                f"(剩余引用: {self._ref_counts[platform]})"
            )

            # 如果引用计数为0且不保持存活，则清理实例
            if self._ref_counts[platform] <= 0 and not keep_alive:
                await self._cleanup_platform(platform)

    async def force_cleanup(self, platform: str):
        """
        强制清理平台的浏览器实例

        Args:
            platform: 平台标识
        """
        lock = await self.get_lock(platform)
        async with lock:
            await self._cleanup_platform(platform)

    async def _cleanup_platform(self, platform: str):
        """内部清理方法（需要在锁内调用）"""
        logger.info(f"[BrowserManager] 清理 {platform} 浏览器实例")

        # 清理浏览器上下文
        context = self._contexts.pop(platform, None)
        if context:
            try:
                await context.close()
            except Exception as exc:
                logger.warning(f"[BrowserManager] 关闭 {platform} 浏览器上下文失败: {exc}")

        # 清理 Playwright 实例
        playwright = self._playwrights.pop(platform, None)
        if playwright:
            try:
                await playwright.stop()
            except Exception as exc:
                logger.warning(f"[BrowserManager] 停止 {platform} Playwright 失败: {exc}")

        # 清理引用计数
        self._ref_counts.pop(platform, None)

    async def cleanup_all(self):
        """清理所有浏览器实例"""
        logger.info("[BrowserManager] 清理所有浏览器实例")

        platforms = list(self._contexts.keys())
        for platform in platforms:
            try:
                await self.force_cleanup(platform)
            except Exception as exc:
                logger.error(f"[BrowserManager] 清理 {platform} 失败: {exc}")

    async def get_context_for_check(
        self,
        platform: str,
        user_data_dir: Path,
        headless: bool = True,
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[BrowserContext, Playwright]:
        """
        获取用于状态检查的临时浏览器上下文
        这个上下文不会被缓存，用完即销毁

        Args:
            platform: 平台标识
            user_data_dir: 用户数据目录
            headless: 是否无头模式
            viewport: 视口大小
            user_agent: 用户代理

        Returns:
            (browser_context, playwright) 二元组
        """
        lock = await self.get_lock(platform)

        async with lock:
            logger.info(f"[BrowserManager] 为 {platform} 创建临时浏览器上下文用于状态检查")

            playwright = await async_playwright().start()
            chromium = playwright.chromium

            # 设置默认值
            if viewport is None:
                viewport = {"width": 1280, "height": 800}
            if user_agent is None:
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

            context = await chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=headless,
                viewport=viewport,
                user_agent=user_agent,
                accept_downloads=True,
            )

            return context, playwright


# 全局单例
_browser_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    """获取全局浏览器管理器实例"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager


__all__ = ["BrowserManager", "get_browser_manager"]
