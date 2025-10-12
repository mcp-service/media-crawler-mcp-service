# -*- coding: utf-8 -*-
"""
MediaCrawler HTTP Client - 通过 HTTP 调用边车服务

替代原来的 wrapper.py，不再直接调用 media_crawler，
而是通过 HTTP 请求与边车服务通信
"""
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.providers.logger import get_logger
from app.config.settings import global_settings


@dataclass
class MediaCrawlerClientConfig:
    """客户端配置"""
    base_url: str = "http://localhost:8001"
    timeout: float = 300.0  # 5分钟超时（爬取可能需要较长时间）
    max_retries: int = 3


class MediaCrawlerClient:
    """
    MediaCrawler HTTP 客户端

    通过 HTTP 与边车服务通信，提供与原 wrapper 相同的接口
    """

    SUPPORTED_PLATFORMS = ["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"]
    CRAWLER_TYPES = ["search", "detail", "creator"]
    LOGIN_TYPES = ["qrcode", "phone", "cookie"]

    def __init__(self, config: Optional[MediaCrawlerClientConfig] = None):
        """
        初始化客户端

        Args:
            config: 客户端配置，如果为 None 则使用默认配置
        """
        self.config = config or MediaCrawlerClientConfig()
        self.logger = get_logger()

        # 创建 HTTP 客户端
        self.client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            follow_redirects=True
        )

    async def close(self) -> None:
        """关闭客户端"""
        await self.client.aclose()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            边车服务是否健康
        """
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"健康检查失败: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取边车服务统计信息

        Returns:
            统计信息字典
        """
        try:
            response = await self.client.get("/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {}

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
        根据关键词爬取平台内容

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
        if platform not in self.SUPPORTED_PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}. 支持的平台: {self.SUPPORTED_PLATFORMS}")

        if login_type not in self.LOGIN_TYPES:
            raise ValueError(f"不支持的登录类型: {login_type}. 支持的类型: {self.LOGIN_TYPES}")

        payload = {
            "platform": platform,
            "keywords": keywords,
            "max_notes": max_notes,
            "enable_comments": enable_comments,
            "max_comments_per_note": max_comments_per_note,
            "login_type": login_type,
            "headless": headless,
            "save_data_option": save_data_option
        }

        try:
            self.logger.info(f"发起关键词爬取请求: platform={platform}, keywords={keywords}")

            response = await self.client.post("/crawl/keyword", json=payload)
            response.raise_for_status()

            result = response.json()
            self.logger.info(f"爬取完成: status={result.get('status')}")

            return result

        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP 错误: {e.response.status_code} - {e.response.text}")
            return {
                "status": "error",
                "platform": platform,
                "keywords": keywords,
                "error": f"HTTP {e.response.status_code}",
                "message": f"请求失败: {e.response.text}"
            }
        except Exception as e:
            self.logger.error(f"爬取请求失败: {e}")
            return {
                "status": "error",
                "platform": platform,
                "keywords": keywords,
                "error": str(e),
                "message": f"爬取失败: {str(e)}"
            }

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
        根据帖子URL爬取指定内容

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
        if platform not in self.SUPPORTED_PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}. 支持的平台: {self.SUPPORTED_PLATFORMS}")

        if not note_urls:
            raise ValueError("note_urls不能为空")

        payload = {
            "platform": platform,
            "note_urls": note_urls,
            "enable_comments": enable_comments,
            "max_comments_per_note": max_comments_per_note,
            "login_type": login_type,
            "headless": headless,
            "save_data_option": save_data_option
        }

        try:
            self.logger.info(f"发起URL爬取请求: platform={platform}, count={len(note_urls)}")

            response = await self.client.post("/crawl/note-urls", json=payload)
            response.raise_for_status()

            result = response.json()
            self.logger.info(f"爬取完成: status={result.get('status')}")

            return result

        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP 错误: {e.response.status_code} - {e.response.text}")
            return {
                "status": "error",
                "platform": platform,
                "note_count": len(note_urls),
                "error": f"HTTP {e.response.status_code}",
                "message": f"请求失败: {e.response.text}"
            }
        except Exception as e:
            self.logger.error(f"爬取请求失败: {e}")
            return {
                "status": "error",
                "platform": platform,
                "note_count": len(note_urls),
                "error": str(e),
                "message": f"爬取失败: {str(e)}"
            }

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
        爬取创作者主页内容

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
        if platform not in self.SUPPORTED_PLATFORMS:
            raise ValueError(f"不支持的平台: {platform}. 支持的平台: {self.SUPPORTED_PLATFORMS}")

        if not creator_ids:
            raise ValueError("creator_ids不能为空")

        payload = {
            "platform": platform,
            "creator_ids": creator_ids,
            "enable_comments": enable_comments,
            "max_comments_per_note": max_comments_per_note,
            "login_type": login_type,
            "headless": headless,
            "save_data_option": save_data_option
        }

        try:
            self.logger.info(f"发起创作者爬取请求: platform={platform}, count={len(creator_ids)}")

            response = await self.client.post("/crawl/creator", json=payload)
            response.raise_for_status()

            result = response.json()
            self.logger.info(f"爬取完成: status={result.get('status')}")

            return result

        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP 错误: {e.response.status_code} - {e.response.text}")
            return {
                "status": "error",
                "platform": platform,
                "creator_count": len(creator_ids),
                "error": f"HTTP {e.response.status_code}",
                "message": f"请求失败: {e.response.text}"
            }
        except Exception as e:
            self.logger.error(f"爬取请求失败: {e}")
            return {
                "status": "error",
                "platform": platform,
                "creator_count": len(creator_ids),
                "error": str(e),
                "message": f"爬取失败: {str(e)}"
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


# 全局客户端实例（单例模式）
_global_client: Optional[MediaCrawlerClient] = None


async def get_client(
    base_url: Optional[str] = None
) -> MediaCrawlerClient:
    """
    获取全局客户端实例

    Args:
        base_url: 边车服务地址，默认使用全局配置

    Returns:
        MediaCrawlerClient 实例
    """
    global _global_client

    if _global_client is None:
        # 使用全局配置创建客户端
        sidecar_config = global_settings.sidecar
        config = MediaCrawlerClientConfig(
            base_url=base_url or sidecar_config.url,
            timeout=sidecar_config.timeout,
            max_retries=sidecar_config.max_retries
        )
        _global_client = MediaCrawlerClient(config)

    return _global_client


async def close_client() -> None:
    """关闭全局客户端"""
    global _global_client

    if _global_client is not None:
        await _global_client.close()
        _global_client = None
