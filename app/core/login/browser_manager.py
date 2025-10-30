# -*- coding: utf-8 -*-
"""
浏览器实例管理器
解决不同平台浏览器实例相互影响的问题
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import json
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

    async def _load_cookies_from_file(self, user_data_dir: Path) -> List[Dict]:
        """
        从 cookies.json 文件加载 Cookie（支持两种格式）
        
        Args:
            user_data_dir: 用户数据目录
            
        Returns:
            Cookie 列表，格式符合 Playwright 的 add_cookies 要求
        """
        cookies_json = user_data_dir / "cookies.json"
        if not cookies_json.exists():
            return []
            
        try:
            # 读取 cookies.json
            raw_data = cookies_json.read_text(encoding="utf-8")
            cookies_data = json.loads(raw_data)
            
            playwright_cookies = []
            
            # 判断格式：字典格式（Python storage.py保存的）还是数组格式（Go Rod保存的）
            if isinstance(cookies_data, dict):
                # 字典格式: {"name": "value", ...} 转换为 Playwright 格式
                # 需要推断domain，根据platform确定
                platform_domain_map = {
                    "xhs": ".xiaohongshu.com",
                    "bili": ".bilibili.com",
                    "dy": ".douyin.com",
                }
                
                # 从路径推断platform
                platform = user_data_dir.name
                domain = platform_domain_map.get(platform, ".xiaohongshu.com")
                
                for name, value in cookies_data.items():
                    pw_cookie = {
                        "name": name,
                        "value": str(value),
                        "domain": domain,
                        "path": "/",
                    }
                    playwright_cookies.append(pw_cookie)
                logger.info(f"[BrowserManager] 从 {cookies_json} 加载了 {len(playwright_cookies)} 个 Cookie")
                return playwright_cookies
            else:
                logger.warning(f"[BrowserManager] 未知的 Cookie 格式: {type(cookies_data)}")
                return []


        except Exception as exc:
            logger.warning(f"[BrowserManager] 加载 Cookie 文件失败: {exc}")
            return []

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
                    # 不再维护引用计数，直接复用
                    logger.info(
                        f"[BrowserManager] 复用 {platform} 浏览器实例 "
                        f"(浏览器常驻模式)"
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

            # 在创建上下文前加载 Cookie 文件（如果存在）
            cookies_to_load = await self._load_cookies_from_file(user_data_dir)

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

            # 如果有 Cookie 文件，则添加到上下文中
            if cookies_to_load:
                try:
                    await context.add_cookies(cookies_to_load)
                    logger.info(f"[BrowserManager] {platform} 已加载 {len(cookies_to_load)} 个 Cookie")
                except Exception as exc:
                    logger.warning(f"[BrowserManager] {platform} 加载 Cookie 失败: {exc}")

            # 缓存实例
            self._contexts[platform] = context
            self._playwrights[platform] = playwright
            self._ref_counts[platform] = 1

            logger.info(f"[BrowserManager] {platform} 浏览器实例创建成功")

            return context, page, playwright

    async def release_context(self, platform: str, keep_alive: bool = True):
        """
        释放浏览器上下文引用 - 现在不再真正释放，保持浏览器常驻

        Args:
            platform: 平台标识
            keep_alive: 是否保持实例存活（现在默认总是保持）
        """
        # 不再减少引用计数，保持浏览器实例常驻
        logger.info(
            f"[BrowserManager] 保持 {platform} 浏览器实例常驻，不释放引用"
        )
        # 可以在这里添加延迟清理逻辑，比如设置定时器在一段时间后清理
        # 但目前保持简单：浏览器实例一旦创建就常驻

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
            # 优先复用已缓存的上下文，避免频繁创建新浏览器实例
            cached_ctx = self._contexts.get(platform)
            cached_pw = self._playwrights.get(platform)
            if cached_ctx and cached_pw:
                try:
                    _ = cached_ctx.pages  # 触发连接探测
                    logger.info(f"[BrowserManager] 复用 {platform} 浏览器上下文用于状态检查")
                    return cached_ctx, cached_pw
                except Exception:
                    logger.warning(f"[BrowserManager] 复用 {platform} 失败，将创建临时上下文")

            logger.info(f"[BrowserManager] 为 {platform} 创建临时浏览器上下文用于状态检查")

            playwright = await async_playwright().start()
            chromium = playwright.chromium

            # 设置默认值
            if viewport is None:
                viewport = {"width": 1280, "height": 800}
            if user_agent is None:
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

            context = await chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir.resolve()),
                headless=headless,
                viewport=viewport,
                user_agent=user_agent,
                accept_downloads=True,
            )

            # 兼容：如果新上下文内没有有效 Cookie，尝试从本地文件加载并写入
            try:
                existing = await context.cookies()
                if not existing:
                    from pathlib import Path as _Path
                    import json as _json
                    cookie_base = _Path("browser_data") / platform
                    cookie_json = cookie_base / "cookies.json"
                    cookie_txt = cookie_base / "cookies.txt"
                    cookie_dict: Dict[str, str] = {}
                    if cookie_json.exists():
                        try:
                            cookie_dict = _json.loads(cookie_json.read_text(encoding="utf-8")) or {}
                        except Exception:
                            cookie_dict = {}
                    elif cookie_txt.exists():
                        try:
                            raw = cookie_txt.read_text(encoding="utf-8")
                            for part in raw.split(";"):
                                part = part.strip()
                                if not part or "=" not in part:
                                    continue
                                k, v = part.split("=", 1)
                                cookie_dict[k.strip()] = v.strip()
                        except Exception:
                            cookie_dict = {}
                    if cookie_dict:
                        domain_map = {
                            "bili": ".bilibili.com",
                            "xhs": ".xiaohongshu.com",
                            "dy": ".douyin.com",
                            "ks": ".kuaishou.com",
                            "wb": ".weibo.com",
                            "zhihu": ".zhihu.com",
                        }
                        dom = domain_map.get(platform, None)
                        cookies_payload = []
                        for name, value in cookie_dict.items():
                            payload = {"name": name, "value": value, "path": "/"}
                            if dom:
                                payload["domain"] = dom
                            cookies_payload.append(payload)
                        if cookies_payload:
                            await context.add_cookies(cookies_payload)
                            logger.info(f"[BrowserManager] 已从本地文件为 {platform} 注入 {len(cookies_payload)} 条 Cookie")
            except Exception as exc:
                logger.warning(f"[BrowserManager] 尝试注入本地 Cookie 失败: {exc}")

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
