# -*- coding: utf-8 -*-
"""
Bilibili (B站) Platform Endpoint - 使用重构后的爬虫
"""
from typing import List
from fastmcp import FastMCP

from app.api.endpoints.base import BaseEndpoint
from app.crawler.platforms.bilibili.service import BilibiliCrawlerService


class BilibiliEndpoint(BaseEndpoint):
    """B站平台端点"""

    def __init__(self) -> None:
        super().__init__(prefix="/bilibili", tags=["B站"])
        self.service = BilibiliCrawlerService()

    def register_routes(self):
        """不注册HTTP路由，只使用MCP工具"""
        return []

    def register_mcp_tools(self, app: FastMCP):
        """注册 MCP 工具"""

        @app.tool(name="bili_search")
        async def bili_search(
            keywords: str,
            max_notes: int = 15,
            enable_comments: bool = True,
            max_comments_per_note: int = 10,
            login_cookie: str = "",
            headless: bool = False
        ) -> str:
            """
            搜索 Bilibili 视频

            参数:
                keywords: 搜索关键词（多个关键词用逗号分隔，例如：Python教程,编程入门）
                max_notes: 最大爬取视频数量，默认15
                enable_comments: 是否爬取评论，默认True
                max_comments_per_note: 每个视频最大评论数，默认10
                login_cookie: 登录Cookie（可选，留空则使用二维码登录）
                headless: 是否无头模式（不显示浏览器窗口），默认False

            返回:
                包含视频信息的JSON字符串
            """
            import json
            result = await self.service.search(
                keywords=keywords,
                max_notes=max_notes,
                enable_comments=enable_comments,
                max_comments_per_note=max_comments_per_note,
                login_cookie=login_cookie if login_cookie else None,
                headless=headless
            )
            return json.dumps(result, ensure_ascii=False, indent=2)

        @app.tool(name="bili_detail")
        async def bili_detail(
            video_ids: List[str],
            enable_comments: bool = True,
            max_comments_per_note: int = 10,
            login_cookie: str = "",
            headless: bool = False
        ) -> str:
            """
            获取 Bilibili 视频详情

            参数:
                video_ids: 视频ID列表（BV号或AV号，例如：["BV1xx411c7mD", "BV1yy411c7mE"]）
                enable_comments: 是否爬取评论，默认True
                max_comments_per_note: 每个视频最大评论数，默认10
                login_cookie: 登录Cookie（可选）
                headless: 是否无头模式，默认False

            返回:
                包含视频详情的JSON字符串
            """
            import json
            result = await self.service.get_detail(
                video_ids=video_ids,
                enable_comments=enable_comments,
                max_comments_per_note=max_comments_per_note,
                login_cookie=login_cookie if login_cookie else None,
                headless=headless
            )
            return json.dumps(result, ensure_ascii=False, indent=2)

        @app.tool(name="bili_creator")
        async def bili_creator(
            creator_ids: List[str],
            enable_comments: bool = True,
            max_comments_per_note: int = 10,
            creator_mode: bool = True,
            login_cookie: str = "",
            headless: bool = False
        ) -> str:
            """
            获取 Bilibili UP主的视频

            参数:
                creator_ids: UP主ID列表（例如：["123456", "789012"]）
                enable_comments: 是否爬取评论，默认True
                max_comments_per_note: 每个视频最大评论数，默认10
                creator_mode: True=获取UP主视频列表，False=只获取UP主信息，默认True
                login_cookie: 登录Cookie（可选）
                headless: 是否无头模式，默认False

            返回:
                包含UP主视频的JSON字符串
            """
            import json
            result = await self.service.get_creator(
                creator_ids=creator_ids,
                enable_comments=enable_comments,
                max_comments_per_note=max_comments_per_note,
                creator_mode=creator_mode,
                login_cookie=login_cookie if login_cookie else None,
                headless=headless
            )
            return json.dumps(result, ensure_ascii=False, indent=2)

        @app.tool(name="bili_search_time_range")
        async def bili_search_time_range(
            keywords: str,
            start_day: str,
            end_day: str,
            max_notes: int = 15,
            max_notes_per_day: int = 50,
            daily_limit: bool = False,
            enable_comments: bool = True,
            max_comments_per_note: int = 10,
            login_cookie: str = "",
            headless: bool = False
        ) -> str:
            """
            按时间范围搜索 Bilibili 视频

            参数:
                keywords: 搜索关键词（多个关键词用逗号分隔）
                start_day: 开始日期（格式：YYYY-MM-DD，例如：2024-01-01）
                end_day: 结束日期（格式：YYYY-MM-DD，例如：2024-01-31）
                max_notes: 总最大爬取数量，默认15
                max_notes_per_day: 每天最大爬取数量，默认50
                daily_limit: 是否严格限制总数量（True=达到max_notes停止，False=每天独立计数），默认False
                enable_comments: 是否爬取评论，默认True
                max_comments_per_note: 每个视频最大评论数，默认10
                login_cookie: 登录Cookie（可选）
                headless: 是否无头模式，默认False

            返回:
                包含视频信息的JSON字符串，按关键词和日期组织
            """
            import json
            result = await self.service.search_with_time_range(
                keywords=keywords,
                start_day=start_day,
                end_day=end_day,
                max_notes=max_notes,
                max_notes_per_day=max_notes_per_day,
                daily_limit=daily_limit,
                enable_comments=enable_comments,
                max_comments_per_note=max_comments_per_note,
                login_cookie=login_cookie if login_cookie else None,
                headless=headless
            )
            return json.dumps(result, ensure_ascii=False, indent=2)

        # 记录工具信息
        self._add_tool_info("bili_search", "搜索Bilibili视频")
        self._add_tool_info("bili_detail", "获取Bilibili视频详情")
        self._add_tool_info("bili_creator", "获取Bilibili UP主视频")
        self._add_tool_info("bili_search_time_range", "按时间范围搜索Bilibili视频")