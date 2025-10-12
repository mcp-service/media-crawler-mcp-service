# -*- coding: utf-8 -*-
"""
Base Platform Endpoint - 所有平台端点的基类
"""
from typing import List
from fastmcp import FastMCP
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.mcp.base_endpoint import BaseEndpoint
from app.mcp.tools.media_crawler import MediaCrawlerWrapper
from app.providers.logger import get_logger


class BasePlatformEndpoint(BaseEndpoint):
    """平台端点基类"""

    def __init__(self, platform_code: str, platform_name: str, prefix: str) -> None:
        """
        初始化平台端点

        Args:
            platform_code: 平台代码 (如 xhs, dy, ks等)
            platform_name: 平台中文名称 (如 小红书, 抖音等)
            prefix: API路径前缀
        """
        super().__init__(prefix=prefix, tags=[platform_name])
        self.platform_code = platform_code
        self.platform_name = platform_name
        self.wrapper = MediaCrawlerWrapper()

    def register_routes(self) -> List[Route]:
        """注册HTTP路由"""

        async def search_handler(request: Request) -> JSONResponse:
            """关键词搜索爬取"""
            try:
                body = await self._parse_json_body(request)
                keywords = body.get("keywords", "")
                max_notes = body.get("max_notes", 15)
                enable_comments = body.get("enable_comments", True)
                max_comments = body.get("max_comments_per_note", 10)
                login_type = body.get("login_type", "qrcode")
                headless = body.get("headless", False)

                result = await self.wrapper.crawl_by_keyword(
                    platform=self.platform_code,
                    keywords=keywords,
                    max_notes=max_notes,
                    enable_comments=enable_comments,
                    max_comments_per_note=max_comments,
                    login_type=login_type,
                    headless=headless
                )

                return self._create_json_response(result)
            except Exception as e:
                get_logger().error(f"[{self.platform_name}] 关键词搜索失败: {e}")
                return self._create_json_response({"error": str(e)}, 500)

        async def detail_handler(request: Request) -> JSONResponse:
            """指定内容爬取"""
            try:
                body = await self._parse_json_body(request)
                note_urls = body.get("urls", [])
                enable_comments = body.get("enable_comments", True)
                max_comments = body.get("max_comments_per_note", 10)
                login_type = body.get("login_type", "qrcode")
                headless = body.get("headless", False)

                result = await self.wrapper.crawl_by_note_urls(
                    platform=self.platform_code,
                    note_urls=note_urls,
                    enable_comments=enable_comments,
                    max_comments_per_note=max_comments,
                    login_type=login_type,
                    headless=headless
                )

                return self._create_json_response(result)
            except Exception as e:
                get_logger().error(f"[{self.platform_name}] 指定内容爬取失败: {e}")
                return self._create_json_response({"error": str(e)}, 500)

        async def creator_handler(request: Request) -> JSONResponse:
            """创作者主页爬取"""
            try:
                body = await self._parse_json_body(request)
                creator_ids = body.get("creator_ids", [])
                enable_comments = body.get("enable_comments", True)
                max_comments = body.get("max_comments_per_note", 10)
                login_type = body.get("login_type", "qrcode")
                headless = body.get("headless", False)

                result = await self.wrapper.crawl_creator_content(
                    platform=self.platform_code,
                    creator_ids=creator_ids,
                    enable_comments=enable_comments,
                    max_comments_per_note=max_comments,
                    login_type=login_type,
                    headless=headless
                )

                return self._create_json_response(result)
            except Exception as e:
                get_logger().error(f"[{self.platform_name}] 创作者主页爬取失败: {e}")
                return self._create_json_response({"error": str(e)}, 500)

        return [
            self._create_route("/search", search_handler, ["POST"]),
            self._create_route("/detail", detail_handler, ["POST"]),
            self._create_route("/creator", creator_handler, ["POST"]),
        ]

    def register_mcp_tools(self, app: FastMCP) -> None:
        """注册MCP工具 - 每个平台必须实现"""
        # 动态创建工具名称
        search_tool_name = f"{self.platform_code}_search"
        detail_tool_name = f"{self.platform_code}_detail"
        creator_tool_name = f"{self.platform_code}_creator"

        # 创建搜索工具
        @app.tool(name=search_tool_name)
        async def platform_search(
            keywords: str,
            max_notes: int = 15,
            enable_comments: bool = True,
            max_comments_per_note: int = 10,
            login_type: str = "qrcode",
            headless: bool = False,
            save_data_option: str = "json"
        ) -> str:
            f"""
            在{self.platform_name}平台根据关键词搜索并爬取内容

            参数:
                keywords: 搜索关键词，多个关键词用逗号分隔
                max_notes: 最大爬取帖子数量，默认15
                enable_comments: 是否爬取评论，默认True
                max_comments_per_note: 每个帖子最大评论数，默认10
                login_type: 登录类型 (qrcode/phone/cookie)，默认qrcode
                headless: 是否无头模式，默认False
                save_data_option: 数据保存方式 (json/csv/db/sqlite)，默认json

            返回:
                爬取结果的JSON字符串
            """
            import json
            result = await self.wrapper.crawl_by_keyword(
                platform=self.platform_code,
                keywords=keywords,
                max_notes=max_notes,
                enable_comments=enable_comments,
                max_comments_per_note=max_comments_per_note,
                login_type=login_type,
                headless=headless,
                save_data_option=save_data_option
            )
            return json.dumps(result, ensure_ascii=False, indent=2)

        # 创建详情工具
        @app.tool(name=detail_tool_name)
        async def platform_detail(
            urls: List[str],
            enable_comments: bool = True,
            max_comments_per_note: int = 10,
            login_type: str = "qrcode",
            headless: bool = False,
            save_data_option: str = "json"
        ) -> str:
            f"""
            在{self.platform_name}平台根据URL列表爬取指定内容

            参数:
                urls: 内容URL列表
                enable_comments: 是否爬取评论，默认True
                max_comments_per_note: 每个帖子最大评论数，默认10
                login_type: 登录类型 (qrcode/phone/cookie)，默认qrcode
                headless: 是否无头模式，默认False
                save_data_option: 数据保存方式 (json/csv/db/sqlite)，默认json

            返回:
                爬取结果的JSON字符串
            """
            import json
            result = await self.wrapper.crawl_by_note_urls(
                platform=self.platform_code,
                note_urls=urls,
                enable_comments=enable_comments,
                max_comments_per_note=max_comments_per_note,
                login_type=login_type,
                headless=headless,
                save_data_option=save_data_option
            )
            return json.dumps(result, ensure_ascii=False, indent=2)

        # 创建创作者工具
        @app.tool(name=creator_tool_name)
        async def platform_creator(
            creator_ids: List[str],
            enable_comments: bool = True,
            max_comments_per_note: int = 10,
            login_type: str = "qrcode",
            headless: bool = False,
            save_data_option: str = "json"
        ) -> str:
            f"""
            在{self.platform_name}平台爬取创作者主页的所有内容

            参数:
                creator_ids: 创作者ID列表
                enable_comments: 是否爬取评论，默认True
                max_comments_per_note: 每个帖子最大评论数，默认10
                login_type: 登录类型 (qrcode/phone/cookie)，默认qrcode
                headless: 是否无头模式，默认False
                save_data_option: 数据保存方式 (json/csv/db/sqlite)，默认json

            返回:
                爬取结果的JSON字符串
            """
            import json
            result = await self.wrapper.crawl_creator_content(
                platform=self.platform_code,
                creator_ids=creator_ids,
                enable_comments=enable_comments,
                max_comments_per_note=max_comments_per_note,
                login_type=login_type,
                headless=headless,
                save_data_option=save_data_option
            )
            return json.dumps(result, ensure_ascii=False, indent=2)

        # 记录工具信息
        self._add_tool_info(search_tool_name, f"在{self.platform_name}平台根据关键词搜索并爬取内容")
        self._add_tool_info(detail_tool_name, f"在{self.platform_name}平台根据URL列表爬取指定内容")
        self._add_tool_info(creator_tool_name, f"在{self.platform_name}平台爬取创作者主页的所有内容")