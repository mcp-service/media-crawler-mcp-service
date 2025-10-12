# -*- coding: utf-8 -*-
"""
MediaCrawler Sidecar Service - 常驻进程，提供爬虫服务
"""
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import os

# 添加 media_crawler 到 Python 路径
MEDIA_CRAWLER_PATH = Path(__file__).parent.parent.parent / "media_crawler"
if str(MEDIA_CRAWLER_PATH) not in sys.path:
    sys.path.insert(0, str(MEDIA_CRAWLER_PATH))

from app.config.settings import (
    GlobalSettings,
    MediaCrawlerConfigAdapter,
    CrawlerConfig
)
from app.core.browser_pool import BrowserPool
from app.core.session_manager import SessionManager
from app.providers.logger import get_logger


# === MediaCrawler Service ===

class MediaCrawlerService:
    """
    MediaCrawler 边车服务

    常驻进程，管理浏览器池、会话状态，提供高并发爬取能力
    """

    def __init__(self, global_settings: GlobalSettings):
        """
        初始化服务

        Args:
            global_settings: 全局配置
        """
        self.global_settings = global_settings
        self.logger = get_logger()

        # 初始化组件（延迟到 startup）
        self.browser_pool: Optional[BrowserPool] = None
        self.session_manager: Optional[SessionManager] = None
        self.config_adapter = MediaCrawlerConfigAdapter(global_settings)

        # 任务队列（用于后台任务管理）
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None

    async def startup(self) -> None:
        """服务启动时初始化"""
        self.logger.info("MediaCrawler Sidecar Service 启动中...")

        # 初始化浏览器池（预热常用平台）
        self.browser_pool = BrowserPool(pool_size=3)
        await self.browser_pool.init_pool(["xhs", "dy", "bili"])

        # 初始化会话管理器
        self.session_manager = SessionManager()

        # 清理过期会话
        await self.session_manager.cleanup_expired_sessions()

        self.logger.info("✓ MediaCrawler Sidecar Service 启动完成")

    async def shutdown(self) -> None:
        """服务关闭时清理"""
        self.logger.info("MediaCrawler Sidecar Service 关闭中...")

        if self.browser_pool:
            await self.browser_pool.shutdown()

        self.logger.info("✓ MediaCrawler Sidecar Service 已关闭")

    async def crawl_by_keyword(
        self,
        platform: str,
        keywords: str,
        max_notes: int = 15,
        enable_comments: bool = True,
        max_comments_per_note: int = 10,
        login_type: str = "cookie",
        headless: bool = False,
        save_data_option: str = "json"
    ) -> Dict[str, Any]:
        """
        根据关键词爬取

        Args:
            platform: 平台代码
            keywords: 搜索关键词
            max_notes: 最大帖子数
            enable_comments: 是否爬取评论
            max_comments_per_note: 每帖最大评论数
            login_type: 登录类型
            headless: 无头模式
            save_data_option: 保存方式

        Returns:
            爬取结果
        """
        # 验证平台
        if not self.global_settings.platforms.validate_platform(platform):
            raise ValueError(f"不支持的平台: {platform}")

        # 构建配置
        crawler_config = CrawlerConfig(
            platform=platform,
            crawler_type="search",
            keywords=keywords,
            max_notes_count=max_notes,
            enable_comments=enable_comments,
            max_comments_per_note=max_comments_per_note,
            login_type=login_type,
            headless=headless,
            save_data_option=save_data_option
        )

        # 执行爬取
        return await self._execute_crawl(crawler_config)

    async def crawl_by_note_urls(
        self,
        platform: str,
        note_urls: list[str],
        enable_comments: bool = True,
        max_comments_per_note: int = 10,
        login_type: str = "cookie",
        headless: bool = False,
        save_data_option: str = "json"
    ) -> Dict[str, Any]:
        """根据URL爬取"""
        if not self.global_settings.platforms.validate_platform(platform):
            raise ValueError(f"不支持的平台: {platform}")

        crawler_config = CrawlerConfig(
            platform=platform,
            crawler_type="detail",
            enable_comments=enable_comments,
            max_comments_per_note=max_comments_per_note,
            login_type=login_type,
            headless=headless,
            save_data_option=save_data_option,
            note_urls=note_urls
        )

        return await self._execute_crawl(crawler_config)

    async def crawl_by_creator(
        self,
        platform: str,
        creator_ids: list[str],
        enable_comments: bool = True,
        max_comments_per_note: int = 10,
        login_type: str = "cookie",
        headless: bool = False,
        save_data_option: str = "json"
    ) -> Dict[str, Any]:
        """爬取创作者内容"""
        if not self.global_settings.platforms.validate_platform(platform):
            raise ValueError(f"不支持的平台: {platform}")

        crawler_config = CrawlerConfig(
            platform=platform,
            crawler_type="creator",
            enable_comments=enable_comments,
            max_comments_per_note=max_comments_per_note,
            login_type=login_type,
            headless=headless,
            save_data_option=save_data_option,
            creator_ids=creator_ids
        )

        return await self._execute_crawl(crawler_config)

    async def _execute_crawl(self, crawler_config: CrawlerConfig) -> Dict[str, Any]:
        """
        执行爬取任务（核心逻辑）

        使用浏览器池中的浏览器实例，避免重复启动
        """
        platform = crawler_config.platform
        browser_context = None

        try:
            # 1. 注入配置
            self.config_adapter.inject_config(crawler_config)

            # 2. 从浏览器池获取浏览器
            self.logger.info(f"开始爬取: platform={platform}, type={crawler_config.crawler_type}")
            browser_context = await self.browser_pool.acquire(platform, timeout=60.0)

            # 3. 切换到 media_crawler 目录执行
            original_cwd = os.getcwd()
            os.chdir(str(MEDIA_CRAWLER_PATH))

            try:
                # 4. 创建 crawler 并注入浏览器上下文
                from media_crawler.main import CrawlerFactory

                crawler = CrawlerFactory.create_crawler(platform=platform)

                # 注入预初始化的浏览器上下文（避免 crawler 内部重新创建）
                if hasattr(crawler, 'context_page'):
                    crawler.context_page.context = browser_context.context
                    crawler.context_page.browser = browser_context.browser

                # 5. 执行爬取
                await crawler.start()

                # 6. 保存会话信息（如果使用了 cookie 登录）
                if crawler_config.login_type == "cookie":
                    cookies = await browser_context.context.cookies()
                    await self.session_manager.save_session(
                        platform=platform,
                        cookies=cookies
                    )

                # 7. 返回结果
                data_path = MEDIA_CRAWLER_PATH / "data"
                return {
                    "status": "success",
                    "platform": platform,
                    "crawler_type": crawler_config.crawler_type,
                    "data_path": str(data_path),
                    "browser_uses": browser_context.use_count,
                    "message": f"成功爬取平台 {platform}"
                }

            finally:
                # 恢复工作目录
                os.chdir(original_cwd)

        except Exception as e:
            self.logger.error(f"爬取失败: {e}", exc_info=True)
            return {
                "status": "error",
                "platform": platform,
                "error": str(e),
                "message": f"爬取失败: {str(e)}"
            }

        finally:
            # 归还浏览器到池中
            if browser_context:
                await self.browser_pool.release(browser_context)

    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        stats = {
            "service": "MediaCrawler Sidecar",
            "status": "running"
        }

        if self.browser_pool:
            stats["browser_pool"] = self.browser_pool.get_stats()

        if self.session_manager:
            stats["session_manager"] = self.session_manager.get_stats()

        return stats

