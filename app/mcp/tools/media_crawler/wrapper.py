# -*- coding: utf-8 -*-
"""
MediaCrawler Wrapper - 通过 HTTP 客户端调用边车服务

注意：此文件已重构为使用 HTTP 客户端模式，
不再直接调用 media_crawler，而是通过边车服务
"""
from typing import Dict, List, Optional, Any
import os

from app.core.client.media_crawler_client import MediaCrawlerClient, MediaCrawlerClientConfig
from app.config.settings import global_settings


class MediaCrawlerWrapper:
    """
    MediaCrawler功能包装器

    现在作为 HTTP 客户端的简单包装，保持与原接口的兼容性
    """

    SUPPORTED_PLATFORMS = ["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"]
    CRAWLER_TYPES = ["search", "detail", "creator"]
    LOGIN_TYPES = ["qrcode", "phone", "cookie"]

    def __init__(self, sidecar_url: Optional[str] = None) -> None:
        """
        初始化MediaCrawler包装器

        Args:
            sidecar_url: 边车服务地址，默认从全局配置读取
        """
        # 从全局配置获取边车服务地址
        if sidecar_url is None:
            sidecar_url = global_settings.sidecar.url

        # 创建 HTTP 客户端
        config = MediaCrawlerClientConfig(
            base_url=sidecar_url,
            timeout=global_settings.sidecar.timeout,
            max_retries=global_settings.sidecar.max_retries
        )
        self.client = MediaCrawlerClient(config)

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
        根据关键词爬取平台内容（通过边车服务）

        Args:
            platform: 平台代码 (xhs, dy, ks, bili, wb, tieba, zhihu)
            keywords: 搜索关键词,多个关键词用逗号分隔
            max_notes: 最大爬取帖子数量
            enable_comments: 是否爬取评论
            max_comments_per_note: 每个帖子最大评论数
            login_type: 登录类型 (qrcode, phone, cookie)
            headless: 是否无头模式
            save_data_option: 数据保存方式 (json, csv, db, sqlite)

        Returns:
            Dict包含爬取任务状态和数据路径
        """
        return await self.client.crawl_by_keyword(
            platform=platform,
            keywords=keywords,
            max_notes=max_notes,
            enable_comments=enable_comments,
            max_comments_per_note=max_comments_per_note,
            login_type=login_type,
            headless=headless,
            save_data_option=save_data_option
        )

    async def crawl_by_note_urls(
        self,
        platform: str,
        note_urls: List[str],
        enable_comments: bool = True,
        max_comments_per_note: int = 10,
        login_type: str = "cookie",
        headless: bool = False,
        save_data_option: str = "json"
    ) -> Dict[str, Any]:
        """
        根据帖子URL爬取指定内容（通过边车服务）

        Args:
            platform: 平台代码 (xhs, dy, ks, bili, wb, tieba, zhihu)
            note_urls: 帖子URL列表
            enable_comments: 是否爬取评论
            max_comments_per_note: 每个帖子最大评论数
            login_type: 登录类型 (qrcode, phone, cookie)
            headless: 是否无头模式
            save_data_option: 数据保存方式 (json, csv, db, sqlite)

        Returns:
            Dict包含爬取任务状态和数据路径
        """
        return await self.client.crawl_by_note_urls(
            platform=platform,
            note_urls=note_urls,
            enable_comments=enable_comments,
            max_comments_per_note=max_comments_per_note,
            login_type=login_type,
            headless=headless,
            save_data_option=save_data_option
        )

    async def crawl_creator_content(
        self,
        platform: str,
        creator_ids: List[str],
        enable_comments: bool = True,
        max_comments_per_note: int = 10,
        login_type: str = "cookie",
        headless: bool = False,
        save_data_option: str = "json"
    ) -> Dict[str, Any]:
        """
        爬取创作者主页内容（通过边车服务）

        Args:
            platform: 平台代码 (xhs, dy, ks, bili, wb, tieba, zhihu)
            creator_ids: 创作者ID列表
            enable_comments: 是否爬取评论
            max_comments_per_note: 每个帖子最大评论数
            login_type: 登录类型 (qrcode, phone, cookie)
            headless: 是否无头模式
            save_data_option: 数据保存方式 (json, csv, db, sqlite)

        Returns:
            Dict包含爬取任务状态和数据路径
        """
        return await self.client.crawl_creator_content(
            platform=platform,
            creator_ids=creator_ids,
            enable_comments=enable_comments,
            max_comments_per_note=max_comments_per_note,
            login_type=login_type,
            headless=headless,
            save_data_option=save_data_option
        )

    async def init_database(self, db_type: str = "sqlite") -> Dict[str, Any]:
        """
        初始化数据库（已废弃，数据库由边车服务管理）

        Args:
            db_type: 数据库类型 (sqlite, mysql)

        Returns:
            Dict包含初始化结果
        """
        return {
            "status": "deprecated",
            "message": "数据库初始化现由边车服务管理，无需手动调用"
        }

    def get_supported_platforms(self) -> List[str]:
        """获取支持的平台列表"""
        return self.SUPPORTED_PLATFORMS

    def get_crawler_types(self) -> List[str]:
        """获取支持的爬取类型"""
        return self.CRAWLER_TYPES

    def get_login_types(self) -> List[str]:
        """获取支持的登录类型"""
        return self.LOGIN_TYPES