
import asyncio
import os
from asyncio import Task
from functools import partial
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
import pandas as pd
from app.providers.logger import get_logger

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)
from playwright._impl._errors import TargetClosedError

from app.core.crawler.store import bilibili as bilibili_store
from app.core.crawler.tools.time_util import get_current_timestamp
from app.config.settings import Platform, CrawlerType, global_settings
from app.core.login import login_service
from app.core.login.exceptions import LoginExpiredError
from app.core.browser_manager import get_browser_manager

from .client import BilibiliClient
from .exception import DataFetchError
from .field import SearchOrderType
from .login import BilibiliLogin

logger = get_logger()
browser_manager = get_browser_manager()


class BilibiliCrawler:
    """B站爬虫实现"""

    def __init__(
        self,
        *,
        login_cookie: Optional[str] = None,
        login_phone: Optional[str] = None,
        login_type: Optional[str] = None,
        headless: Optional[bool] = None,
        enable_save_media: Optional[bool] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        # 移除父类调用，因为不再继承 AbstractCrawler
        # super().__init__(platform=Platform.BILIBILI, crawler_type=CrawlerType.SEARCH)

        self.index_url = "https://www.bilibili.com"
        self.extra = dict(extra or {})
        self.base_extra = dict(self.extra)
        self.platform_code = Platform.BILIBILI.value

        browser_defaults = global_settings.browser
        resolved_headless = headless if headless is not None else browser_defaults.headless

        self.browser = SimpleNamespace(
            headless=resolved_headless,
            user_agent=self.extra.get("user_agent", browser_defaults.user_agent),
            proxy=self.extra.get("proxy", browser_defaults.proxy),
            viewport_width=int(self.extra.get("viewport_width", browser_defaults.viewport_width)),
            viewport_height=int(self.extra.get("viewport_height", browser_defaults.viewport_height)),
        )

        # 移除crawl配置，只保留基础配置和全局参数
        self.user_agent = self.browser.user_agent or self._get_default_user_agent()
        self.bili_client: Optional[BilibiliClient] = None
        self.cdp_manager: Optional[Any] = None
        
        # 全局参数设置
        crawl_defaults = global_settings.crawl
        self.crawl_interval = crawl_defaults.crawl_interval
        self.max_concurrency = crawl_defaults.max_concurrency
        
        # 添加缺失的属性
        self.crawler_label = "bilibili_crawler"

    @staticmethod
    def _resolve_login_type_hint(
        provided_type: Optional[str],
        cookie: Optional[str],
        phone: Optional[str],
    ) -> str:
        if provided_type:
            return str(provided_type)
        if cookie:
            return "cookie"
        if phone:
            return "phone"
        return "qrcode"

    async def ensure_login_and_client(
        self,
        *,
        login_cookie: Optional[str] = None,
        login_phone: Optional[str] = None,
        login_type: Optional[str] = None,
        no_auto_login: bool = False
    ) -> None:
        """
        确保登录状态并初始化客户端
        """
        logger.info("[BilibiliCrawler.ensure_login_and_client] Initializing browser and client...")
        
        # 代理配置（暂不支持，可扩展）
        playwright_proxy = None
        httpx_proxy = None

        # 使用浏览器管理器获取浏览器上下文
        user_data_dir = Path("browser_data") / self.platform_code
        viewport = {
            "width": self.browser.viewport_width,
            "height": self.browser.viewport_height,
        }

        self.browser_context, self.context_page, playwright = await browser_manager.acquire_context(
            platform=self.platform_code,
            user_data_dir=user_data_dir,
            headless=self.browser.headless,
            viewport=viewport,
            user_agent=self.user_agent,
        )

        # 加载反爬脚本（相对于当前文件路径）
        stealth_js_path = Path(__file__).parent.parent.parent / "libs" / "stealth.min.js"
        if stealth_js_path.exists():
            await self.browser_context.add_init_script(path=str(stealth_js_path))
        else:
            logger.warning(f"[BilibiliCrawler.ensure_login_and_client] stealth.min.js not found at {stealth_js_path}")

        await self.context_page.goto(self.index_url)

        # 创建 Bilibili 客户端
        self.bili_client = await self.create_bilibili_client(httpx_proxy)

        # 处理登录
        login_type_hint = self._resolve_login_type_hint(login_type, login_cookie, login_phone)
        
        # 优先使用登录服务的缓存状态，避免频繁触发风控
        is_logged_in: Optional[bool] = None
        try:
            login_status = await login_service.get_login_status("bili")
            is_logged_in = bool(login_status.get('is_logged_in', False))
            if is_logged_in:
                logger.info("[BilibiliCrawler.ensure_login_and_client] Using cached login state from login service")
            else:
                logger.info("[BilibiliCrawler.ensure_login_and_client] Cached state shows not logged in, will verify with pong")
        except Exception as exc:
            logger.warning(f"[BilibiliCrawler.ensure_login_and_client] Failed to get login status from service: {exc}")
            is_logged_in = None

        # 仅在未登录或未知时做一次 pong 校验，避免重复调用
        if not is_logged_in:
            is_logged_in = await self.bili_client.pong()
            # 若页面侧 pong 判定为登录，立刻回写 Redis，保证服务端状态一致
            if is_logged_in:
                try:
                    await login_service.refresh_platform_state(Platform.BILIBILI.value, force=True, strict=True)
                except Exception as exc:
                    logger.warning(f"[BilibiliCrawler.ensure_login_and_client] Update platform state after pong failed: {exc}")

        if not is_logged_in:
            # MCP 工具场景下不自动登录，直接提示登录过期
            if no_auto_login:
                raise LoginExpiredError("登录过期，Cookie失效")
            logger.info("[BilibiliCrawler.ensure_login_and_client] Not logged in, starting login process...")
            login_obj = BilibiliLogin(
                login_type=login_type_hint,
                browser_context=self.browser_context,
                context_page=self.context_page,
                login_phone=login_phone or "",
                cookie_str=login_cookie or "",
            )
            await login_obj.begin()

        # 无论是否重新登录，都要更新cookies以确保使用最新的认证信息
        await self.bili_client.update_cookies(browser_context=self.browser_context)
        logger.info("[BilibiliCrawler.ensure_login_and_client] Cookies updated from browser context")

    async def cleanup(self) -> None:
        """
        清理浏览器资源 - 现在不再真正关闭浏览器上下文，只清理引用
        浏览器实例由BrowserManager统一管理，实现复用
        """
        try:
            # 不再释放浏览器上下文，保持常驻以实现复用
            # await browser_manager.release_context(self.platform_code, keep_alive=True)
            logger.info("[BilibiliCrawler.cleanup] Browser context kept alive for reuse")
        except Exception as e:
            logger.error(f"[BilibiliCrawler.cleanup] Error during cleanup: {e}")

    def _get_default_user_agent(self) -> str:
        """获取默认User-Agent"""
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    async def get_pubtime_datetime(self, start: str, end: str) -> Tuple[str, str]:
        """
        获取 bilibili 作品发布日期起始时间戳和结束时间戳

        Args:
            start: 发布日期起始时间，YYYY-MM-DD
            end: 发布日期结束时间，YYYY-MM-DD

        Returns:
            (pubtime_begin_s, pubtime_end_s) 时间戳字符串元组
        """
        start_day = datetime.strptime(start, "%Y-%m-%d")
        end_day = datetime.strptime(end, "%Y-%m-%d")

        if start_day > end_day:
            raise ValueError("Start date cannot exceed end date")

        if start_day == end_day:
            # 搜索同一天的内容
            end_day = start_day + timedelta(days=1) - timedelta(seconds=1)
        else:
            # 搜索 start 至 end
            end_day = end_day + timedelta(days=1) - timedelta(seconds=1)

        return str(int(start_day.timestamp())), str(int(end_day.timestamp()))

    async def search_by_keywords_fast(
        self,
        *,
        keywords: str,
        page_size: int = 1,
        page_num: Optional[int] = None,
    ) -> Dict:
        """
        快速搜索（不获取详细信息）
        只返回搜索API提供的基础数据，提高响应速度

        Returns:
            搜索结果字典
        """
        from app.api.scheme.response import BilibiliSearchResult, BilibiliVideoSimple

        logger.info("[BilibiliCrawler.search_by_keywords_fast] Begin fast search bilibili keywords")

        page_size = max(1, min(page_size, 50))

        all_videos = []

        for keyword in keywords.split(","):
            keyword = keyword.strip()
            if not keyword:
                continue

            logger.info(
                f"[BilibiliCrawler.search_by_keywords_fast] keyword={keyword} "
                f"page_size={page_size} page={page_num}"
            )

            try:
                videos_res = await self.bili_client.search_video_by_keyword(
                    keyword=keyword,
                    page=page_num,
                    page_size=page_size,
                    order=SearchOrderType.DEFAULT,
                    pubtime_begin_s="0",
                    pubtime_end_s="0",
                )
            except Exception as exc:
                logger.error(
                    f"[BilibiliCrawler.search_by_keywords_fast] Error requesting page {page_num}: {exc}"
                )
                continue

            video_list: List[Dict] = videos_res.get("result", [])[:page_size]
            if not video_list:
                logger.info(
                    f"[BilibiliCrawler.search_by_keywords_fast] No videos for keyword '{keyword}' on page {page_num}"
                )
                continue

            # 直接处理搜索结果，不获取详细信息
            for item in video_list:
                # 从搜索结果构建基础视频信息
                aid = str(item.get("aid", ""))
                bvid = item.get("bvid", "")
                # 将搜索结果中的可用统计字段映射到简化信息中
                # liked_count: 取搜索接口返回的 like 字段；
                # video_comment: 优先取 review（评论数），其次 video_review/danmaku（可能为弹幕数，作为兜底不使用，此处仅在缺失时回退）。
                liked = item.get("like", 0)
                # 有些返回只有 review 或 video_review，这里优先使用 review
                review = item.get("review")
                if review is None:
                    review = item.get("video_review") or item.get("danmaku", 0)

                video_info = {
                    # 使用 aid 作为对外视频 ID，方便后续请求详情
                    "video_id": aid,
                    "title": item.get("title", ""),
                    "desc": item.get("description", ""),
                    "create_time": item.get("pubdate"),
                    "user_id": str(item.get("mid", "")),
                    "nickname": item.get("author", ""),
                    "video_play_count": str(item.get("play", "0")),
                    "liked_count": str(liked),
                    "video_comment": str(review if review is not None else 0),
                    # 使用 BV 号生成视频链接
                    "video_url": f"https://www.bilibili.com/video/{bvid}",
                    "video_cover_url": item.get("pic", ""),
                    "source_keyword": keyword,
                    "aid": aid,
                    "bvid": bvid,
                    "duration": item.get("duration", ""),
                    "video_type": "video",
                }

                # 在循环中直接转换为Pydantic模型
                try:
                    video = BilibiliVideoSimple.from_full_video(video_info)
                    all_videos.append(video)
                except Exception as e:
                    logger.debug(f"视频数据转换失败，跳过: {e}")
                    continue

            await asyncio.sleep(self.crawl_interval)

        # 构建结果并返回
        result = BilibiliSearchResult(
            videos=all_videos,
            total_count=len(all_videos),
            keywords=keywords,
            crawl_info={
                "crawl_time": get_current_timestamp(),
                "platform": "bilibili",
                "crawler_type": "search_fast",
                "total_videos": len(all_videos)
            }
        )

        return result.model_dump()

    async def search_by_keywords(
        self,
        *,
        keywords: str,
        page_size: int = 1,
        page_num: Optional[int] = None,
        start_page: int = 1
    ) -> Dict:
        """
        按关键词搜索（普通模式）

        Returns:
            搜索结果字典
        """
        logger.info("[BilibiliCrawler.search_by_keywords] Begin search bilibili keywords")

        page_size = max(1, min(page_size, 50))
        start_page = max(1, start_page)
        keywords = keywords or ""

        results: Dict[str, List[Dict]] = {}

        for keyword in keywords.split(","):
            keyword = keyword.strip()
            if not keyword:
                continue

            logger.info(
                f"[BilibiliCrawler.search_by_keywords] keyword={keyword} "
                f"page_size={page_size} page={(page_num or start_page)}"
            )

            collected_items: List[Dict] = []

            # 仅抓取指定页
            page = page_num or start_page
            logger.info(
                f"[BilibiliCrawler.search_by_keywords] Searching keyword={keyword} page={page}"
            )

            try:
                videos_res = await self.bili_client.search_video_by_keyword(
                    keyword=keyword,
                    page=page,
                    page_size=page_size,
                    order=SearchOrderType.DEFAULT,
                    pubtime_begin_s="0",
                    pubtime_end_s="0",
                )
            except Exception as exc:
                logger.error(
                    f"[BilibiliCrawler.search_by_keywords] Error requesting page {page}: {exc}"
                )
                continue

            video_list: List[Dict] = videos_res.get("result", [])[:page_size]
            if not video_list:
                logger.info(
                    f"[BilibiliCrawler.search_by_keywords] No videos for keyword '{keyword}' on page {page}"
                )
                continue

            # 使用aid而不是bvid获取视频详情，因为detail API需要aid
            semaphore = asyncio.Semaphore(self.max_concurrency)
            tasks = [
                self.get_video_info_task(aid=item.get("aid"), bvid="", semaphore=semaphore)
                for item in video_list
            ]
            video_items = await asyncio.gather(*tasks)

            for video_item in video_items:
                if not video_item:
                    continue
                try:
                    await bilibili_store.update_bilibili_video(
                        video_item,
                        crawler_type=self.crawler_label,
                        source_keyword=keyword,
                    )
                    await bilibili_store.update_up_info(
                        video_item,
                        crawler_type=self.crawler_label,
                    )
                    await self.get_bilibili_video(video_item, semaphore)
                except Exception as store_exc:  # pragma: no cover - best effort logging
                    logger.error(
                        f"[BilibiliCrawler.search_by_keywords] Store media error: {store_exc}"
                    )

                collected_items.append(video_item)

            await asyncio.sleep(self.crawl_interval)

            if collected_items:
                results[keyword] = collected_items

        return results

    async def search_by_keywords_in_time_range(
        self,
        *,
        keywords: str,
        start_day: str,
        end_day: str,
        page_size: int = 1,
        page_num: Optional[int] = None,
        start_page: int = 1
    ) -> Dict:
        """
        按关键词和时间范围搜索。

        Args:
            keywords: 搜索关键词
            start_day: 开始日期
            end_day: 结束日期
            page_size: 页面大小
            page_num: 页码
            start_page: 开始页码

        Returns:
            搜索结果字典。
        """
        from app.api.scheme.response import BilibiliSearchResult, BilibiliVideoSimple

        logger.info(
            f"[BilibiliCrawler.search_by_keywords_in_time_range] Begin search"
        )

        page_size = max(1, min(page_size, 50))

        keywords = keywords or ""
        start_day = start_day or datetime.now().strftime("%Y-%m-%d")
        end_day = end_day or datetime.now().strftime("%Y-%m-%d")

        all_videos = []
        keywords_list = []

        for keyword in keywords.split(","):
            keyword = keyword.strip()
            if not keyword:
                continue

            keywords_list.append(keyword)

            logger.info(
                f"[BilibiliCrawler.search_by_keywords_in_time_range] keyword={keyword} "
                f"page_size={page_size} page={(page_num or start_page)}"
            )

            # 直接使用整个时间范围，不需要按天循环
            pubtime_begin_s, pubtime_end_s = await self.get_pubtime_datetime(
                start=start_day,
                end=end_day,
            )

            page = page_num or start_page
            logger.info(
                f"[BilibiliCrawler] Searching keyword={keyword} from {start_day} to {end_day} page={page} size={page_size}"
            )

            try:
                videos_res = await self.bili_client.search_video_by_keyword(
                    keyword=keyword,
                    page=page,
                    page_size=page_size,
                    order=SearchOrderType.DEFAULT,
                    pubtime_begin_s=pubtime_begin_s,
                    pubtime_end_s=pubtime_end_s,
                )
            except Exception as exc:
                logger.error(
                    f"[BilibiliCrawler] Error searching keyword={keyword} from {start_day} to {end_day} page={page}: {exc}"
                )
                continue

            video_list: List[Dict] = videos_res.get("result", [])
            if not video_list:
                logger.info(
                    f"[BilibiliCrawler] No videos for keyword '{keyword}' from {start_day} to {end_day}"
                )
                continue

            semaphore = asyncio.Semaphore(self.max_concurrency)
            tasks = [
                self.get_video_info_task(aid=item.get("aid"), bvid="", semaphore=semaphore)
                for item in video_list
            ]
            video_items = await asyncio.gather(*tasks)

            for video_item in video_items:
                if not video_item:
                    continue

                # 从 video_item 中提取 View 数据
                view = video_item.get("View", {})
                stat = view.get("stat", {})
                owner = view.get("owner", {})

                aid = str(view.get("aid", ""))
                bvid = view.get("bvid", "")
                url = f"https://www.bilibili.com/video/{bvid}" if bvid else f"https://www.bilibili.com/video/av{aid}"
                cover = view.get("pic", "")
                if isinstance(cover, str) and cover.startswith("//"):
                    cover = "https:" + cover

                # 构建映射数据
                mapped = {
                    "video_id": aid,
                    "title": view.get("title", ""),
                    "desc": view.get("desc", ""),
                    "create_time": view.get("pubdate"),
                    "user_id": str(owner.get("mid", "")),
                    "nickname": owner.get("name", ""),
                    "video_play_count": str(stat.get("view", 0)),
                    "liked_count": str(stat.get("like", 0)),
                    "video_comment": str(stat.get("reply", 0)),
                    "video_url": url,
                    "video_cover_url": cover,
                    "source_keyword": keyword,
                }

                # 在循环中直接转换为Pydantic模型
                try:
                    video = BilibiliVideoSimple.from_full_video(mapped)
                    all_videos.append(video)
                except Exception as e:
                    logger.debug(f"视频数据转换失败，跳过: {e}")
                    continue

                # 保存到存储
                try:
                    await bilibili_store.update_bilibili_video(
                        video_item,
                        crawler_type=self.crawler_label,
                        source_keyword=keyword,
                    )
                    await bilibili_store.update_up_info(
                        video_item,
                        crawler_type=self.crawler_label,
                    )
                    await self.get_bilibili_video(video_item, semaphore)
                except Exception as store_exc:  # pragma: no cover - log but continue
                    logger.error(
                        f"[BilibiliCrawler.search_by_keywords_in_time_range] Store media error: {store_exc}"
                    )

            await asyncio.sleep(self.crawl_interval)

        # 构建结果并返回
        result = BilibiliSearchResult(
            videos=all_videos,
            total_count=len(all_videos),
            keywords=",".join([kw for kw in keywords_list if kw]),
            crawl_info={
                "crawl_time": get_current_timestamp(),
                "platform": "bilibili",
                "crawler_type": "search_time_range",
                "total_videos": len(all_videos),
                "start_day": start_day,
                "end_day": end_day
            }
        )

        return result.model_dump()

    async def fetch_comments_for_ids(
        self,
        video_ids: List[str],
        enable_get_sub_comments: bool = False,
        max_comments_per_note: int = 20
    ) -> Dict[str, Any]:
        """
        根据视频ID批量获取评论。

        Args:
            video_ids: 视频ID列表
            enable_get_sub_comments: 是否获取子评论
            max_comments_per_note: 每个视频最大评论数
        """
        from app.api.scheme.response import BilibiliComment, BilibiliCommentsResult

        if not video_ids:
            empty_result = BilibiliCommentsResult(
                comments=[],
                total_count=0,
                video_ids=[],
                crawl_info={}
            )
            return empty_result.model_dump()

        logger.info(
            f"[BilibiliCrawler.fetch_comments_for_ids] Fetching comments for {len(video_ids)} videos"
        )

        semaphore = asyncio.Semaphore(self.max_concurrency)
        results: Dict[str, List[Dict]] = {}

        async def _fetch(video_id: str) -> List[Dict]:
            async with semaphore:
                try:
                    comments = await self.bili_client.get_video_all_comments(
                        video_id=video_id,
                        crawl_interval=self.crawl_interval,
                        is_fetch_sub_comments=enable_get_sub_comments,
                        callback=None,
                        max_count=max_comments_per_note,
                    )
                    return comments or []
                except Exception as exc:
                    logger.error(
                        f"[BilibiliCrawler.fetch_comments_for_ids] Failed to fetch comments for {video_id}: {exc}"
                    )
                    return []

        tasks = {str(video_id): asyncio.create_task(_fetch(str(video_id))) for video_id in video_ids}

        for video_id, task in tasks.items():
            try:
                results[video_id] = await task
            except Exception as exc:  # pragma: no cover - unexpected failure
                logger.error(
                    f"[BilibiliCrawler.fetch_comments_for_ids] Task failed for {video_id}: {exc}"
                )
                results[video_id] = []

        # 在循环中转换评论为Pydantic模型
        all_comments = []
        video_id_list = []

        for video_id, comment_list in results.items():
            video_id_list.append(str(video_id))
            if not isinstance(comment_list, list):
                continue

            for comment_data in comment_list:
                if isinstance(comment_data, dict):
                    try:
                        # 添加video_id到评论数据中
                        comment_data_with_video = dict(comment_data)
                        comment_data_with_video["video_id"] = str(video_id)
                        comment = BilibiliComment.model_validate(comment_data_with_video)
                        all_comments.append(comment)
                    except Exception as e:
                        logger.debug(f"单条评论转换失败: {e}")
                        continue

        # 构建结果并返回
        result = BilibiliCommentsResult(
            comments=all_comments,
            total_count=len(all_comments),
            video_ids=video_id_list,
            crawl_info={
                "crawl_time": get_current_timestamp(),
                "platform": "bilibili",
                "crawler_type": "comments",
                "total_comments": len(all_comments)
            }
        )

        return result.model_dump()

    async def batch_get_video_comments(
        self, 
        video_id_list: List[str], 
        source_keyword: str = "",
        enable_get_comments: bool = True,
        max_concurrency: int = 5,
        crawl_interval: float = 1.0
    ):
        """
        批量获取视频评论

        Args:
            video_id_list: 视频ID列表
            source_keyword: 来源关键词
            enable_get_comments: 是否启用评论获取
            max_concurrency: 最大并发数
            crawl_interval: 爬取间隔
        """
        if not enable_get_comments:
            logger.info("[BilibiliCrawler.batch_get_video_comments] Comments crawling is disabled")
            return

        logger.info(f"[BilibiliCrawler.batch_get_video_comments] Getting comments for {len(video_id_list)} videos")
        semaphore = asyncio.Semaphore(max_concurrency)
        task_list: List[Task] = []

        for video_id in video_id_list:
            task = asyncio.create_task(
                self.get_comments(video_id, semaphore, source_keyword, crawl_interval),
                name=video_id
            )
            task_list.append(task)

        await asyncio.gather(*task_list)

    async def get_comments(
        self, 
        video_id: str, 
        semaphore: asyncio.Semaphore, 
        source_keyword: str = "",
        crawl_interval: float = 1.0,
        enable_get_sub_comments: bool = False,
        max_comments_per_note: int = 20
    ):
        """
        获取单个视频的评论

        Args:
            video_id: 视频ID
            semaphore: 并发控制信号量
            source_keyword: 来源关键词
            crawl_interval: 爬取间隔
            enable_get_sub_comments: 是否获取子评论
            max_comments_per_note: 每个视频最大评论数
        """
        async with semaphore:
            try:
                logger.info(f"[BilibiliCrawler.get_comments] Getting comments for video: {video_id}")
                await asyncio.sleep(crawl_interval)
                callback = partial(
                    bilibili_store.batch_update_bilibili_video_comments,
                    crawler_type=self.crawler_label,
                    source_keyword=source_keyword,
                )
                await self.bili_client.get_video_all_comments(
                    video_id=video_id,
                    crawl_interval=crawl_interval,
                    is_fetch_sub_comments=enable_get_sub_comments,
                    callback=callback,
                    max_count=max_comments_per_note,
                )

            except DataFetchError as ex:
                logger.error(f"[BilibiliCrawler.get_comments] Error getting comments for {video_id}: {ex}")
            except Exception as e:
                logger.error(f"[BilibiliCrawler.get_comments] Unexpected error for {video_id}: {e}")
                raise

    async def get_creator_videos(self, creator_id: str, page_num: int = 1, page_size: int = 30) -> Dict:
        """
        获取创作者的视频列表，支持分页

        Args:
            creator_id: 创作者ID
            page_num: 页码，从1开始
            page_size: 每页数量，默认30

        Returns:
            格式化的创作者视频数据
        """
        from app.api.scheme.response import BilibiliCreatorResult, BilibiliCreatorInfo, BilibiliVideoSimple

        logger.info(f"[BilibiliCrawler.get_creator_videos] Getting videos for creator: {creator_id}, page: {page_num}, size: {page_size}")

        # 添加请求间隔避免风控
        await asyncio.sleep(self.crawl_interval)

        result = await self.bili_client.get_creator_videos(creator_id, page_num, page_size)
        logger.info(f"[BilibiliCrawler.get_creator_videos] Getting videos -----> result {result}")
        # 从结果中提取创作者信息
        video_list = result.get("list", {}).get("vlist", [])
        creator_info = None

        if video_list:
            first_video = video_list[0]
            creator_info = {
                "creator_id": str(creator_id),
                "creator_name": first_video.get("author", ""),
                "total_videos": result.get("page", {}).get("count", 0)
            }

        # 处理当前页的视频列表
        all_videos = []
        for video in video_list:
            aid = video.get("aid")
            if not aid:
                continue

            # 构建视频信息，使用类似search的格式
            video_info = {
                "video_id": str(aid),
                "title": video.get("title", ""),
                "desc": video.get("description", ""),
                "create_time": video.get("created"),
                "user_id": str(video.get("mid", "")),
                "nickname": video.get("author", ""),
                "video_play_count": str(video.get("play", 0)),
                "liked_count": "0",  # creator API中没有点赞数
                "video_comment": str(video.get("comment", 0)),
                "video_url": f"https://www.bilibili.com/video/{video.get('bvid', '')}",
                "video_cover_url": video.get("pic", ""),
                "source_keyword": f"creator:{creator_id}",
                "aid": str(aid),
                "bvid": video.get("bvid", ""),
                "duration": video.get("length", ""),
                "video_type": "video",
                "typeid": video.get("typeid"),
                "copyright": video.get("copyright"),
            }

            # 在循环中直接转换为Pydantic模型
            try:
                video_model = BilibiliVideoSimple.from_full_video(video_info)
                all_videos.append(video_model)
            except Exception as e:
                logger.debug(f"创作者视频转换失败: {e}")
                continue

        # 构建结果并返回
        creator_result = BilibiliCreatorResult(
            creator_info=BilibiliCreatorInfo(**( creator_info or {
                "creator_id": str(creator_id),
                "creator_name": "Unknown",
                "total_videos": 0
            })),
            videos=all_videos,
            total_count=len(all_videos),
            page_info={
                "current_page": page_num,
                "page_size": page_size,
                "total_videos": result.get("page", {}).get("count", 0),
                "has_more": len(all_videos) == page_size
            },
            crawl_info={
                "crawl_time": get_current_timestamp(),
                "platform": "bilibili",
                "crawler_type": "creator",
                "total_videos": len(all_videos),
                "page_num": page_num,
                "page_size": page_size
            }
        )

        return creator_result.model_dump()

    async def get_specified_videos(
        self,
        video_ids: List[str],
        source_keyword: str = ""
    ) -> Dict:
        """
        获取指定视频的详情

        Args:
            video_ids: 视频 ID 列表（支持 BV 号、带 AV 前缀、纯数字 avid）
            source_keyword: 来源关键词

        Returns:
            视频详情字典
        """
        from app.api.scheme.response import BilibiliDetailResult, BilibiliVideoFull

        logger.info(f"[BilibiliCrawler.get_specified_videos] Getting details for {len(video_ids)} videos")
        semaphore = asyncio.Semaphore(self.max_concurrency)

        task_list = []
        for raw_video_id in video_ids:
            if raw_video_id is None:
                continue

            cleaned_id = str(raw_video_id).strip()
            if not cleaned_id:
                continue

            lowered = cleaned_id.lower()
            aid = 0

            if lowered.startswith("bv"):
                # 对于BV号，暂时跳过，因为detail API需要aid
                logger.warning(f"[BilibiliCrawler.get_specified_videos] 跳过BV号 {cleaned_id}，detail API需要aid")
                continue
            elif lowered.startswith("av") and lowered[2:].isdigit():
                aid = int(lowered[2:])
            elif cleaned_id.isdigit():
                aid = int(cleaned_id)
            else:
                # 其他格式跳过
                logger.warning(f"[BilibiliCrawler.get_specified_videos] 跳过未识别格式 {cleaned_id}，仅支持aid格式")
                continue

            # 只处理有效的aid
            if aid > 0:
                task_list.append(
                    self.get_video_info_task(
                        aid=aid,
                        bvid="",  # 不再使用bvid
                        semaphore=semaphore,
                    )
                )

        video_details = await asyncio.gather(*task_list)

        video_aids_list = []
        results = []

        for video_detail in video_details:
            if video_detail is not None:
                video_item_view: Dict = video_detail.get("View", {})
                video_aid: str = video_item_view.get("aid")
                if video_aid:
                    video_aids_list.append(str(video_aid))

                # 转换为用户友好的格式，提取所有有用字段
                owner = video_item_view.get("owner", {})
                stat = video_item_view.get("stat", {})
                card_info = video_detail.get("Card", {}).get("card", {})
                tags_list = video_detail.get("Tags", [])

                # 提取tags信息
                tags = [{"tag_id": tag.get("tag_id"), "tag_name": tag.get("tag_name")} for tag in tags_list] if tags_list else []

                formatted_video = {
                    # 基础视频信息
                    "video_id": str(video_aid),
                    "bvid": video_item_view.get("bvid", ""),
                    "title": video_item_view.get("title", ""),
                    "desc": video_item_view.get("desc", ""),
                    "create_time": video_item_view.get("pubdate"),
                    "duration": video_item_view.get("duration"),
                    "video_url": f"https://www.bilibili.com/video/{video_item_view.get('bvid', '')}",
                    "video_cover_url": video_item_view.get("pic", ""),

                    # 分区信息
                    "tname": video_item_view.get("tname", ""),  # 分区名称
                    "tid": video_item_view.get("tid"),  # 分区ID

                    # 视频属性
                    "copyright": video_item_view.get("copyright"),  # 1原创 2转载
                    "cid": video_item_view.get("cid"),  # 视频CID

                    # UP主信息
                    "user_id": str(owner.get("mid", "")),
                    "nickname": owner.get("name", ""),
                    "avatar": owner.get("face", ""),

                    # UP主详细信息（从Card获取）
                    "user_sex": card_info.get("sex", ""),
                    "user_sign": card_info.get("sign", ""),
                    "user_level": card_info.get("level_info", {}).get("current_level") if card_info.get("level_info") else None,
                    "user_fans": card_info.get("fans"),
                    "user_official_verify": card_info.get("official_verify", {}).get("type") if card_info.get("official_verify") else None,

                    # 统计数据
                    "video_play_count": str(stat.get("view", 0)),
                    "liked_count": str(stat.get("like", 0)),
                    "disliked_count": str(stat.get("dislike", 0)),
                    "video_comment": str(stat.get("reply", 0)),
                    "coin_count": str(stat.get("coin", 0)),
                    "share_count": str(stat.get("share", 0)),
                    "favorite_count": str(stat.get("favorite", 0)),
                    "danmaku_count": str(stat.get("danmaku", 0)),

                    # 标签
                    "tags": tags,

                    # 来源关键词
                    "source_keyword": source_keyword,
                }

                # 在循环中直接转换为Pydantic模型
                try:
                    video_full = BilibiliVideoFull(**formatted_video)
                    results.append(video_full)
                except Exception as e:
                    logger.debug(f"视频详情转换失败，跳过: {e}")
                    continue

                try:
                    await bilibili_store.update_bilibili_video(
                        video_detail,
                        crawler_type=self.crawler_label,
                        source_keyword=source_keyword,
                    )
                    await bilibili_store.update_up_info(
                        video_detail,
                        crawler_type=self.crawler_label,
                    )
                    await self.get_bilibili_video(video_detail, semaphore)
                except Exception as store_exc:  # pragma: no cover - best effort
                    logger.error(f"[BilibiliCrawler.get_specified_videos] Store media error: {store_exc}")

        await self.batch_get_video_comments(video_aids_list, source_keyword=source_keyword)

        # 构建结果并返回
        detail_result = BilibiliDetailResult(
            videos=results,
            total_count=len(results),
            crawl_info={
                "crawl_time": get_current_timestamp(),
                "platform": "bilibili",
                "crawler_type": "detail",
                "total_videos": len(results)
            }
        )

        logger.info(f"[BilibiliCrawler.get_specified_videos] Returning {len(results)} video details")
        return detail_result.model_dump()

    async def get_video_info_task(
        self, 
        aid: int, 
        bvid: str, 
        semaphore: asyncio.Semaphore
    ) -> Optional[Dict]:
        """
        获取视频详情任务

        Args:
            aid: 视频AID
            bvid: 视频BVID
            semaphore: 并发控制信号量

        Returns:
            视频详情字典或None
        """
        async with semaphore:
            try:
                result = await self.bili_client.get_video_info(aid=aid, bvid=bvid)
                await asyncio.sleep(self.crawl_interval)
                return result
            except DataFetchError as ex:
                logger.error(f"[BilibiliCrawler.get_video_info_task] Error: {ex}")
                return None
            except KeyError as ex:
                logger.error(f"[BilibiliCrawler.get_video_info_task] Not found: {bvid or aid}, err: {ex}")
                return None

    async def get_all_creator_details(self, creator_id_list: List[int]):
        """
        获取所有创作者的详情

        Args:
            creator_id_list: 创作者ID列表
        """
        logger.info(f"[BilibiliCrawler.get_all_creator_details] Getting details for {len(creator_id_list)} creators")

        semaphore = asyncio.Semaphore(self.max_concurrency)
        task_list: List[Task] = []

        for creator_id in creator_id_list:
            task = asyncio.create_task(
                self.get_creator_details(creator_id, semaphore),
                name=str(creator_id)
            )
            task_list.append(task)

        await asyncio.gather(*task_list)

    async def get_creator_details(self, creator_id: int, semaphore: asyncio.Semaphore):
        """
        获取单个创作者的详情

        Args:
            creator_id: 创作者ID
            semaphore: 并发控制信号量
        """
        creator_info: Optional[Dict] = None
        async with semaphore:
            try:
                creator_unhandled_info: Dict = await self.bili_client.get_creator_info(creator_id)
                creator_info = {
                    "id": creator_id,
                    "name": creator_unhandled_info.get("name"),
                    "sign": creator_unhandled_info.get("sign"),
                    "avatar": creator_unhandled_info.get("face"),
                }
                logger.info(f"[BilibiliCrawler.get_creator_details] Got details for creator: {creator_id}")
            except Exception as e:
                logger.error(f"[BilibiliCrawler.get_creator_details] Error for creator {creator_id}: {e}")
                return

        if not creator_info:
            return

        await self.get_fans(creator_info, semaphore)
        await self.get_followings(creator_info, semaphore)
        await self.get_dynamics(creator_info, semaphore)

    def _max_contacts_per_creator(self) -> int:
        """获取创作者粉丝/关注抓取数量上限"""
        return int(self.extra.get("max_contacts_per_creator", 100))

    def _max_dynamics_per_creator(self) -> int:
        """获取创作者动态抓取数量上限"""
        return int(self.extra.get("max_dynamics_per_creator", 50))

    async def get_fans(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """获取创作者粉丝信息"""
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                logger.info(f"[BilibiliCrawler.get_fans] begin get creator_id: {creator_id} fans ...")
                await self.bili_client.get_creator_all_fans(
                    creator_info=creator_info,
                    crawl_interval=self.crawl_interval,
                    callback=partial(
                        bilibili_store.batch_update_bilibili_creator_fans,
                        crawler_type=self.crawler_label,
                    ),
                    max_count=self._max_contacts_per_creator(),
                )
            except DataFetchError as ex:
                logger.error(f"[BilibiliCrawler.get_fans] get creator_id: {creator_id} fans error: {ex}")

            except Exception as e:
                logger.error(f"[BilibiliCrawler.get_fans] may be blocked, err:{e}")

    async def get_followings(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """获取创作者关注信息"""
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                logger.info(f"[BilibiliCrawler.get_followings] begin get creator_id: {creator_id} followings ...")
                await self.bili_client.get_creator_all_followings(
                    creator_info=creator_info,
                    crawl_interval=self.crawl_interval,
                    callback=partial(
                        bilibili_store.batch_update_bilibili_creator_followings,
                        crawler_type=self.crawler_label,
                    ),
                    max_count=self._max_contacts_per_creator(),
                )
            except DataFetchError as ex:
                logger.error(f"[BilibiliCrawler.get_followings] get creator_id: {creator_id} followings error: {ex}")
            except Exception as e:
                logger.error(f"[BilibiliCrawler.get_followings] may be blocked, err:{e}")

    async def get_dynamics(self, creator_info: Dict, semaphore: asyncio.Semaphore):
        """获取创作者动态"""
        creator_id = creator_info["id"]
        async with semaphore:
            try:
                logger.info(f"[BilibiliCrawler.get_dynamics] begin get creator_id: {creator_id} dynamics ...")
                await self.bili_client.get_creator_all_dynamics(
                    creator_info=creator_info,
                    crawl_interval=self.crawl_interval,
                    callback=partial(
                        bilibili_store.batch_update_bilibili_creator_dynamics,
                        crawler_type=self.crawler_label,
                    ),
                    max_count=self._max_dynamics_per_creator(),
                )
            except DataFetchError as ex:
                logger.error(f"[BilibiliCrawler.get_dynamics] get creator_id: {creator_id} dynamics error: {ex}")
            except Exception as e:
                logger.error(f"[BilibiliCrawler.get_dynamics] may be blocked, err:{e}")

    async def get_video_play_url_task(self, aid: int, cid: int, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """获取视频播放地址任务"""
        async with semaphore:
            try:
                result = await self.bili_client.get_video_play_url(aid=aid, cid=cid)
                return result
            except DataFetchError as ex:
                logger.error(f"[BilibiliCrawler.get_video_play_url_task] Get video play url error: {ex}")
                return None
            except KeyError as ex:
                logger.error(f"[BilibiliCrawler.get_video_play_url_task] Not found play url for {aid}|{cid}, err: {ex}")
                return None

    async def get_bilibili_video(self, video_item: Dict, semaphore: asyncio.Semaphore):
        """下载并保存视频"""
        # 检查是否需要保存媒体文件
        store_defaults = global_settings.store
        if not bool(getattr(store_defaults, "enable_save_media", False)):
            return

        video_item_view: Dict = video_item.get("View", {})
        aid = video_item_view.get("aid")
        cid = video_item_view.get("cid")
        if not aid or not cid:
            logger.info("[BilibiliCrawler.get_bilibili_video] Missing aid or cid, skip media download")
            return

        result = await self.get_video_play_url_task(int(aid), int(cid), semaphore)
        if result is None:
            logger.info("[BilibiliCrawler.get_bilibili_video] get video play url failed")
            return

        durl_list = result.get("durl") or []
        video_url = ""
        max_size = -1
        for durl in durl_list:
            size = durl.get("size", -1)
            if size > max_size:
                max_size = size
                video_url = durl.get("url", "")

        if not video_url:
            logger.info("[BilibiliCrawler.get_bilibili_video] get video url failed")
            return

        content = await self.bili_client.get_video_media(video_url)
        await asyncio.sleep(self.crawl_interval)
        if content is None:
            return

        extension_file_name = "video.mp4"
        await bilibili_store.store_video(aid, content, extension_file_name)

    async def create_bilibili_client(self, httpx_proxy: Optional[str]) -> BilibiliClient:
        """
        创建 Bilibili 客户端

        Args:
            httpx_proxy: HTTP代理

        Returns:
            BilibiliClient 实例
        """
        logger.info("[BilibiliCrawler.create_bilibili_client] Creating Bilibili API client...")

        cookies = await self.browser_context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        cookie_dict = {c['name']: c['value'] for c in cookies}

        bilibili_client_obj = BilibiliClient(
            proxy=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": "https://www.bilibili.com",
                "Referer": "https://www.bilibili.com",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return bilibili_client_obj

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        启动浏览器

        Args:
            chromium: Playwright chromium 对象
            playwright_proxy: 代理配置
            user_agent: 用户代理
            headless: 是否无头模式

        Returns:
            浏览器上下文
        """
        logger.info("[BilibiliCrawler.launch_browser] Creating browser context...")

        if self.login_options.save_login_state:
            # 保存登录状态
            user_data_dir = os.path.join(
                os.getcwd(),
                "browser_data",
                self.platform_code
            )

            # 使用配置中的 headless 设置，确保登录和搜索时使用相同的模式
            logger.info(f"[BilibiliCrawler.launch_browser] Using persistent context with headless={self.browser.headless}")

            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=self.browser.headless,  # 使用配置中的headless设置
                proxy=playwright_proxy,
                viewport={
                    "width": self.browser.viewport_width,
                    "height": self.browser.viewport_height
                },
                user_agent=user_agent,
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
            browser_context = await browser.new_context(
                viewport={
                    "width": self.browser.viewport_width,
                    "height": self.browser.viewport_height
                },
                user_agent=user_agent
            )
            return browser_context

    async def close(self):
        """关闭浏览器上下文"""
        try:
            if self.cdp_manager:
                # CDP模式清理（暂未实现）
                self.cdp_manager = None
            elif self.browser_context:
                await self.browser_context.close()
            logger.info("[BilibiliCrawler.close] Browser context closed")
        except TargetClosedError:
            logger.warning("[BilibiliCrawler.close] Browser context was already closed")
        except Exception as e:
            logger.error(f"[BilibiliCrawler.close] Error during close: {e}")
