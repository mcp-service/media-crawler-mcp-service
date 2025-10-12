# -*- coding: utf-8 -*-
"""
MediaCrawler Wrapper - 包装media_crawler功能为可调用的API
"""
import sys
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

# 将media_crawler添加到Python路径
MEDIA_CRAWLER_PATH = Path(__file__).parent.parent.parent.parent.parent / "media_crawler"
sys.path.insert(0, str(MEDIA_CRAWLER_PATH))


class MediaCrawlerWrapper:
    """MediaCrawler功能包装器"""

    SUPPORTED_PLATFORMS = ["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"]
    CRAWLER_TYPES = ["search", "detail", "creator"]
    LOGIN_TYPES = ["qrcode", "phone", "cookie"]

    def __init__(self) -> None:
        """初始化MediaCrawler包装器"""
        self.media_crawler_path = MEDIA_CRAWLER_PATH

    async def crawl_by_keyword(
        self,
        platform: str,
        keywords: str,
        max_notes: int = 15,
        enable_comments: bool = True,
        max_comments_per_note: int = 10,
        login_type: str = "qrcode",
        headless: bool = False
    ) -> Dict[str, Any]:
        """
        根据关键词爬取平台内容

        Args:
            platform: 平台代码 (xhs, dy, ks, bili, wb, tieba, zhihu)
            keywords: 搜索关键词,多个关键词用逗号分隔
            max_notes: 最大爬取帖子数量
            enable_comments: 是否爬取评论
            max_comments_per_note: 每个帖子最大评论数
            login_type: 登录类型 (qrcode, phone, cookie)
            headless: 是否无头模式

        Returns:
            Dict包含爬取任务状态和数据路径
        """
        if platform not in self.SUPPORTED_PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}. 支持的平台: {self.SUPPORTED_PLATFORMS}")

        if login_type not in self.LOGIN_TYPES:
            raise ValueError(f"不支持的登录类型: {login_type}. 支持的类型: {self.LOGIN_TYPES}")

        # 动态导入media_crawler配置并修改
        import config as mc_config

        # 设置配置参数
        mc_config.PLATFORM = platform
        mc_config.KEYWORDS = keywords
        mc_config.CRAWLER_TYPE = "search"
        mc_config.CRAWLER_MAX_NOTES_COUNT = max_notes
        mc_config.ENABLE_GET_COMMENTS = enable_comments
        mc_config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = max_comments_per_note
        mc_config.LOGIN_TYPE = login_type
        mc_config.HEADLESS = headless
        mc_config.SAVE_DATA_OPTION = "db"  # 固定使用数据库存储

        # 执行爬取
        from main import CrawlerFactory

        crawler = None
        try:
            crawler = CrawlerFactory.create_crawler(platform=platform)
            await crawler.start()

            # 返回结果信息
            data_path = self.media_crawler_path / "data"
            return {
                "status": "success",
                "platform": platform,
                "keywords": keywords,
                "crawler_type": "search",
                "notes_count": max_notes,
                "data_path": str(data_path),
                "message": f"成功爬取平台 {platform} 关键词 {keywords} 的内容"
            }
        except Exception as e:
            return {
                "status": "error",
                "platform": platform,
                "keywords": keywords,
                "error": str(e),
                "message": f"爬取失败: {str(e)}"
            }
        finally:
            # 确保清理资源
            if crawler is not None and hasattr(crawler, 'context_page'):
                try:
                    if hasattr(crawler.context_page, 'context'):
                        await crawler.context_page.context.close()
                    if hasattr(crawler.context_page, 'browser'):
                        await crawler.context_page.browser.close()
                except Exception as cleanup_error:
                    print(f"清理浏览器资源时出错: {cleanup_error}")

    async def crawl_by_note_urls(
        self,
        platform: str,
        note_urls: List[str],
        enable_comments: bool = True,
        max_comments_per_note: int = 10,
        login_type: str = "qrcode",
        headless: bool = False
    ) -> Dict[str, Any]:
        """
        根据帖子URL爬取指定内容

        Args:
            platform: 平台代码 (xhs, dy, ks, bili, wb, tieba, zhihu)
            note_urls: 帖子URL列表
            enable_comments: 是否爬取评论
            max_comments_per_note: 每个帖子最大评论数
            login_type: 登录类型 (qrcode, phone, cookie)
            headless: 是否无头模式

        Returns:
            Dict包含爬取任务状态和数据路径
        """
        if platform not in self.SUPPORTED_PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}. 支持的平台: {self.SUPPORTED_PLATFORMS}")

        if not note_urls:
            raise ValueError("note_urls不能为空")

        # 动态导入media_crawler配置
        import config as mc_config

        # 设置配置参数
        mc_config.PLATFORM = platform
        mc_config.CRAWLER_TYPE = "detail"
        mc_config.ENABLE_GET_COMMENTS = enable_comments
        mc_config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = max_comments_per_note
        mc_config.LOGIN_TYPE = login_type
        mc_config.HEADLESS = headless
        mc_config.SAVE_DATA_OPTION = "db"  # 固定使用数据库存储

        # 根据平台设置note URL列表
        if platform == "xhs":
            mc_config.XHS_SPECIFIED_NOTE_URL_LIST = note_urls
        elif platform == "dy":
            mc_config.DY_SPECIFIED_ID_LIST = note_urls
        elif platform == "ks":
            mc_config.KS_SPECIFIED_ID_LIST = note_urls
        elif platform == "bili":
            mc_config.BILI_SPECIFIED_ID_LIST = note_urls
        elif platform == "wb":
            mc_config.WEIBO_SPECIFIED_ID_LIST = note_urls
        elif platform == "tieba":
            mc_config.TIEBA_SPECIFIED_POST_ID_LIST = note_urls
        elif platform == "zhihu":
            mc_config.ZHIHU_SPECIFIED_ID_LIST = note_urls

        # 执行爬取
        from main import CrawlerFactory

        crawler = None
        try:
            crawler = CrawlerFactory.create_crawler(platform=platform)
            await crawler.start()

            # 返回结果信息
            data_path = self.media_crawler_path / "data"
            return {
                "status": "success",
                "platform": platform,
                "note_count": len(note_urls),
                "crawler_type": "detail",
                "data_path": str(data_path),
                "message": f"成功爬取平台 {platform} 的 {len(note_urls)} 条指定内容"
            }
        except Exception as e:
            return {
                "status": "error",
                "platform": platform,
                "note_count": len(note_urls),
                "error": str(e),
                "message": f"爬取失败: {str(e)}"
            }
        finally:
            # 确保清理资源
            if crawler is not None and hasattr(crawler, 'context_page'):
                try:
                    if hasattr(crawler.context_page, 'context'):
                        await crawler.context_page.context.close()
                    if hasattr(crawler.context_page, 'browser'):
                        await crawler.context_page.browser.close()
                except Exception as cleanup_error:
                    print(f"清理浏览器资源时出错: {cleanup_error}")

    async def crawl_creator_content(
        self,
        platform: str,
        creator_ids: List[str],
        enable_comments: bool = True,
        max_comments_per_note: int = 10,
        login_type: str = "qrcode",
        headless: bool = False
    ) -> Dict[str, Any]:
        """
        爬取创作者主页内容

        Args:
            platform: 平台代码 (xhs, dy, ks, bili, wb, tieba, zhihu)
            creator_ids: 创作者ID列表
            enable_comments: 是否爬取评论
            max_comments_per_note: 每个帖子最大评论数
            login_type: 登录类型 (qrcode, phone, cookie)
            headless: 是否无头模式

        Returns:
            Dict包含爬取任务状态和数据路径
        """
        if platform not in self.SUPPORTED_PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}. 支持的平台: {self.SUPPORTED_PLATFORMS}")

        if not creator_ids:
            raise ValueError("creator_ids不能为空")

        # 动态导入media_crawler配置
        import config as mc_config

        # 设置配置参数
        mc_config.PLATFORM = platform
        mc_config.CRAWLER_TYPE = "creator"
        mc_config.ENABLE_GET_COMMENTS = enable_comments
        mc_config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = max_comments_per_note
        mc_config.LOGIN_TYPE = login_type
        mc_config.HEADLESS = headless
        mc_config.SAVE_DATA_OPTION = "db"  # 固定使用数据库存储

        # 根据平台设置创作者ID列表
        if platform == "xhs":
            mc_config.XHS_CREATOR_ID_LIST = creator_ids
        elif platform == "dy":
            mc_config.DY_CREATOR_ID_LIST = creator_ids
        elif platform == "ks":
            mc_config.KS_CREATOR_ID_LIST = creator_ids
        elif platform == "bili":
            mc_config.BILI_CREATOR_ID_LIST = creator_ids
        elif platform == "wb":
            mc_config.WEIBO_CREATOR_ID_LIST = creator_ids
        # tieba和zhihu暂不支持creator模式

        # 执行爬取
        from main import CrawlerFactory

        crawler = None
        try:
            crawler = CrawlerFactory.create_crawler(platform=platform)
            await crawler.start()

            # 返回结果信息
            data_path = self.media_crawler_path / "data"
            return {
                "status": "success",
                "platform": platform,
                "creator_count": len(creator_ids),
                "crawler_type": "creator",
                "data_path": str(data_path),
                "message": f"成功爬取平台 {platform} 的 {len(creator_ids)} 个创作者的内容"
            }
        except Exception as e:
            return {
                "status": "error",
                "platform": platform,
                "creator_count": len(creator_ids),
                "error": str(e),
                "message": f"爬取失败: {str(e)}"
            }
        finally:
            # 确保清理资源
            if crawler is not None and hasattr(crawler, 'context_page'):
                try:
                    if hasattr(crawler.context_page, 'context'):
                        await crawler.context_page.context.close()
                    if hasattr(crawler.context_page, 'browser'):
                        await crawler.context_page.browser.close()
                except Exception as cleanup_error:
                    print(f"清理浏览器资源时出错: {cleanup_error}")

    async def init_database(self, db_type: str = "sqlite") -> Dict[str, Any]:
        """
        初始化数据库

        Args:
            db_type: 数据库类型 (sqlite, mysql)

        Returns:
            Dict包含初始化结果
        """
        if db_type not in ["sqlite", "mysql"]:
            raise ValueError(f"不支持的数据库类型: {db_type}. 支持的类型: sqlite, mysql")

        from database import db

        try:
            await db.init_db(db_type)
            return {
                "status": "success",
                "db_type": db_type,
                "message": f"数据库 {db_type} 初始化成功"
            }
        except Exception as e:
            return {
                "status": "error",
                "db_type": db_type,
                "error": str(e),
                "message": f"数据库初始化失败: {str(e)}"
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