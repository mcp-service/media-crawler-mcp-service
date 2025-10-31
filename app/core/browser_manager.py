# -*- coding: utf-8 -*-
"""
浏览器管理器 - 基于新的浏览器池系统
提供统一的浏览器实例管理接口
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

from playwright.async_api import BrowserContext, Page, Playwright

from app.core.browser_pool import (
    BrowserPoolManager, TaskType, BrowserInstance, PoolConfig,
    get_pool_manager
)
from app.providers.logger import get_logger

logger = get_logger()


class BrowserManager:
    """
    浏览器管理器
    基于新的浏览器池系统，提供统一的浏览器实例管理接口
    """
    
    def __init__(self):
        self._pool_manager: Optional[BrowserPoolManager] = None
        self._instance_cache: Dict[str, BrowserInstance] = {}
    
    async def _get_pool_manager(self) -> BrowserPoolManager:
        """获取浏览器池管理器"""
        if self._pool_manager is None:
            self._pool_manager = await get_pool_manager()
        return self._pool_manager
    
    async def acquire_context(
        self,
        platform: str,
        user_data_dir: Path,
        headless: bool = True,
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[BrowserContext, Page, Playwright]:
        """
        获取或创建浏览器上下文（兼容接口）
        
        Args:
            platform: 平台标识
            user_data_dir: 用户数据目录（用于兼容，实际由池管理）
            headless: 是否无头模式
            viewport: 视口大小
            user_agent: 用户代理
            
        Returns:
            (browser_context, page, playwright) 三元组
        """
        pool_manager = await self._get_pool_manager()
        
        # 获取爬虫类型的实例（默认用于爬虫任务）
        instance = await pool_manager.acquire(platform, TaskType.CRAWL)
        
        # 缓存实例以便后续 release_context 调用
        cache_key = f"{platform}_crawl"
        self._instance_cache[cache_key] = instance
        
        logger.info(f"[BrowserManager] 获取浏览器上下文: {platform}")
        
        return instance.context, instance.page, instance.playwright
    
    async def release_context(self, platform: str, keep_alive: bool = True):
        """
        释放浏览器上下文引用（兼容接口）
        
        Args:
            platform: 平台标识
            keep_alive: 是否保持实例存活（在新池中总是保持）
        """
        cache_key = f"{platform}_crawl"
        instance = self._instance_cache.pop(cache_key, None)
        
        if instance:
            pool_manager = await self._get_pool_manager()
            await pool_manager.release(instance)
            logger.info(f"[BrowserManager] 释放浏览器上下文: {platform}")
        else:
            logger.warning(f"[BrowserManager] 未找到缓存的实例: {platform}")
    
    async def get_context_for_check(
        self,
        platform: str,
        user_data_dir: Path,
        headless: bool = True,
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[BrowserContext, Playwright]:
        """
        获取用于状态检查的临时浏览器上下文（兼容接口）
        
        Args:
            platform: 平台标识
            user_data_dir: 用户数据目录（用于兼容，实际由池管理）
            headless: 是否无头模式
            viewport: 视口大小
            user_agent: 用户代理
            
        Returns:
            (browser_context, playwright) 二元组
        """
        pool_manager = await self._get_pool_manager()
        
        # 获取检查类型的实例
        instance = await pool_manager.acquire(platform, TaskType.CHECK)
        
        # 缓存实例以便后续清理
        cache_key = f"{platform}_check"
        self._instance_cache[cache_key] = instance
        
        logger.info(f"[BrowserManager] 获取检查浏览器上下文: {platform}")
        
        return instance.context, instance.playwright
    
    async def force_cleanup(self, platform: str):
        """
        强制清理平台的浏览器实例（兼容接口）
        
        Args:
            platform: 平台标识
        """
        pool_manager = await self._get_pool_manager()
        await pool_manager.cleanup_platform(platform, force=True)
        
        # 清理本地缓存
        keys_to_remove = [key for key in self._instance_cache.keys() if key.startswith(f"{platform}_")]
        for key in keys_to_remove:
            self._instance_cache.pop(key, None)
        
        logger.info(f"[BrowserManager] 强制清理平台: {platform}")
    
    async def cleanup_all(self):
        """清理所有浏览器实例"""
        if self._pool_manager:
            await self._pool_manager.close()
            self._pool_manager = None
        
        self._instance_cache.clear()
        logger.info("[BrowserManager] 清理所有浏览器实例")
    
    async def get_lock(self, platform: str) -> asyncio.Lock:
        """获取平台专属锁"""
        # 在新的池管理中，锁已经内置在池中，这里返回一个虚拟锁
        return asyncio.Lock()


# 全局管理器实例
_browser_manager: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    """获取全局浏览器管理器实例"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager


# 直接接口函数（用于简化迁移）
async def acquire_browser_for_login(platform: str) -> BrowserInstance:
    """获取用于登录的浏览器实例"""
    pool_manager = await get_pool_manager()
    return await pool_manager.acquire(platform, TaskType.LOGIN)


async def acquire_browser_for_crawl(platform: str) -> BrowserInstance:
    """获取用于爬虫的浏览器实例"""
    pool_manager = await get_pool_manager()
    return await pool_manager.acquire(platform, TaskType.CRAWL)


async def acquire_browser_for_check(platform: str) -> BrowserInstance:
    """获取用于状态检查的浏览器实例"""
    pool_manager = await get_pool_manager()
    return await pool_manager.acquire(platform, TaskType.CHECK)


async def release_browser_instance(instance: BrowserInstance):
    """释放浏览器实例"""
    pool_manager = await get_pool_manager()
    await pool_manager.release(instance)


# 配置函数
async def configure_browser_pool(platform: str, **config_kwargs):
    """配置特定平台的浏览器池"""
    pool_manager = await get_pool_manager()
    config = PoolConfig(**config_kwargs)
    pool_manager.configure_platform(platform, config)


async def get_browser_stats() -> Dict[str, Any]:
    """获取浏览器池统计信息"""
    pool_manager = await get_pool_manager()
    return pool_manager.get_stats()


async def browser_health_check() -> Dict[str, Any]:
    """浏览器池健康检查"""
    pool_manager = await get_pool_manager()
    return await pool_manager.health_check()


__all__ = [
    "BrowserManager", "get_browser_manager",
    "acquire_browser_for_login", "acquire_browser_for_crawl", "acquire_browser_for_check",
    "release_browser_instance", "configure_browser_pool", 
    "get_browser_stats", "browser_health_check"
]