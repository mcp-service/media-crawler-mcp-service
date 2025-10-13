# -*- coding: utf-8 -*-
"""
Bilibili 爬虫服务层

提供简化的 Bilibili 爬虫调用接口
"""

from typing import Dict, List, Optional, Any
from app.providers.logger import get_logger

from app.config.settings import (
    CrawlerConfig,
    Platform,
    CrawlerType,
    LoginType,
    create_search_config,
    create_detail_config,
    create_creator_config
)
from .crawler import BilibiliCrawler

logger = get_logger()

class BilibiliCrawlerService:
    """
    Bilibili 爬虫服务

    提供高层次的接口，简化爬虫调用
    """

    async def search(
        self,
        keywords: str,
        max_notes: int = 15,
        enable_comments: bool = True,
        max_comments_per_note: int = 10,
        login_cookie: Optional[str] = None,
        headless: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        搜索 Bilibili 视频

        Args:
            keywords: 搜索关键词（多个关键词用逗号分隔）
            max_notes: 最大爬取视频数量
            enable_comments: 是否爬取评论
            max_comments_per_note: 每个视频最大评论数
            login_cookie: 登录Cookie（可选）
            headless: 是否无头模式
            **kwargs: 其他扩展参数

        Returns:
            爬取结果字典
        """
        logger.info(f"[BilibiliCrawlerService.search] Searching Bilibili with keywords: {keywords}")

        # 创建配置
        config = create_search_config(
            platform=Platform.BILIBILI,
            keywords=keywords,
            max_notes=max_notes,
            enable_comments=enable_comments,
            max_comments_per_note=max_comments_per_note,
            login_type=LoginType.COOKIE if login_cookie else LoginType.QRCODE,
            cookie_str=login_cookie,
            headless=headless,
            **kwargs
        )

        # 创建爬虫实例并执行
        crawler = BilibiliCrawler(config)
        try:
            result = await crawler.start()
            return result
        finally:
            await crawler.close()

    async def get_detail(
        self,
        video_ids: List[str],
        enable_comments: bool = True,
        max_comments_per_note: int = 10,
        login_cookie: Optional[str] = None,
        headless: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        获取指定视频的详情

        Args:
            video_ids: 视频ID列表（BV号或AV号）
            enable_comments: 是否爬取评论
            max_comments_per_note: 每个视频最大评论数
            login_cookie: 登录Cookie（可选）
            headless: 是否无头模式
            **kwargs: 其他扩展参数

        Returns:
            视频详情字典
        """
        logger.info(f"[BilibiliCrawlerService.get_detail] Getting details for {len(video_ids)} videos")

        # 创建配置
        config = create_detail_config(
            platform=Platform.BILIBILI,
            note_ids=video_ids,
            enable_comments=enable_comments,
            max_comments_per_note=max_comments_per_note,
            login_type=LoginType.COOKIE if login_cookie else LoginType.QRCODE,
            cookie_str=login_cookie,
            headless=headless,
            **kwargs
        )

        # 创建爬虫实例并执行
        crawler = BilibiliCrawler(config)
        try:
            result = await crawler.start()
            return result
        finally:
            await crawler.close()

    async def get_creator(
        self,
        creator_ids: List[str],
        enable_comments: bool = True,
        max_comments_per_note: int = 10,
        creator_mode: bool = True,
        login_cookie: Optional[str] = None,
        headless: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        获取创作者（UP主）的视频

        Args:
            creator_ids: UP主ID列表
            enable_comments: 是否爬取评论
            max_comments_per_note: 每个视频最大评论数
            creator_mode: True=获取UP主视频列表，False=只获取UP主信息
            login_cookie: 登录Cookie（可选）
            headless: 是否无头模式
            **kwargs: 其他扩展参数

        Returns:
            创作者视频字典
        """
        logger.info(f"[BilibiliCrawlerService.get_creator] Getting content for {len(creator_ids)} creators")

        # 创建配置
        extra = kwargs.copy()
        extra['creator_mode'] = creator_mode

        config = create_creator_config(
            platform=Platform.BILIBILI,
            creator_ids=creator_ids,
            enable_comments=enable_comments,
            max_comments_per_note=max_comments_per_note,
            login_type=LoginType.COOKIE if login_cookie else LoginType.QRCODE,
            cookie_str=login_cookie,
            headless=headless,
            **extra
        )

        # 创建爬虫实例并执行
        crawler = BilibiliCrawler(config)
        try:
            result = await crawler.start()
            return result
        finally:
            await crawler.close()

    async def search_with_time_range(
        self,
        keywords: str,
        start_day: str,
        end_day: str,
        max_notes: int = 15,
        max_notes_per_day: int = 50,
        daily_limit: bool = False,
        enable_comments: bool = True,
        max_comments_per_note: int = 10,
        login_cookie: Optional[str] = None,
        headless: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        按时间范围搜索 Bilibili 视频

        Args:
            keywords: 搜索关键词
            start_day: 开始日期（YYYY-MM-DD）
            end_day: 结束日期（YYYY-MM-DD）
            max_notes: 总最大爬取数量
            max_notes_per_day: 每天最大爬取数量
            daily_limit: 是否严格限制总数量
            enable_comments: 是否爬取评论
            max_comments_per_note: 每个视频最大评论数
            login_cookie: 登录Cookie（可选）
            headless: 是否无头模式
            **kwargs: 其他扩展参数

        Returns:
            爬取结果字典
        """
        logger.info(f"[BilibiliCrawlerService.search_with_time_range] Searching from {start_day} to {end_day}")

        # 创建配置
        extra = kwargs.copy()
        extra['search_mode'] = 'daily_limit_in_time_range' if daily_limit else 'all_in_time_range'

        config = create_search_config(
            platform=Platform.BILIBILI,
            keywords=keywords,
            max_notes=max_notes,
            enable_comments=enable_comments,
            max_comments_per_note=max_comments_per_note,
            login_type=LoginType.COOKIE if login_cookie else LoginType.QRCODE,
            cookie_str=login_cookie,
            headless=headless,
            **extra
        )

        # 设置时间范围
        config.start_day = start_day
        config.end_day = end_day
        config.max_notes_per_day = max_notes_per_day
        config.search_mode = 'daily_limit_in_time_range' if daily_limit else 'all_in_time_range'

        # 创建爬虫实例并执行
        crawler = BilibiliCrawler(config)
        try:
            result = await crawler.start()
            return result
        finally:
            await crawler.close()
