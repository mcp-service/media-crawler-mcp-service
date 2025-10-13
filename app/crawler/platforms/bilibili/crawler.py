
import asyncio
import os
from asyncio import Task
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
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

from app.crawler.platforms.base import AbstractCrawler
from app.config.settings import CrawlerConfig, Platform, CrawlerType
from app.config.settings import Platform
from .client import BilibiliClient
from .exception import DataFetchError
from .field import SearchOrderType
from .login import BilibiliLogin

logger = get_logger()


class BilibiliCrawler(AbstractCrawler):
    """
    B站爬虫（改造版）

    关键改变：
    1. 构造函数接受 CrawlerConfig 参数
    2. 移除所有对全局 config 模块的依赖
    3. 所有配置通过 self.config 访问
    """

    def __init__(self, config: CrawlerConfig):
        """
        初始化B站爬虫

        Args:
            config: 爬虫配置对象
        """
        super().__init__(config)

        # 验证平台
        if config.platform != Platform.BILIBILI:
            raise ValueError(f"Invalid platform: {config.platform}, expected {Platform.BILIBILI}")

        self.index_url = "https://www.bilibili.com"
        self.user_agent = config.user_agent or self._get_default_user_agent()

        # 客户端和浏览器相关
        self.bili_client: Optional[BilibiliClient] = None
        self.cdp_manager: Optional[any] = None

    def _get_default_user_agent(self) -> str:
        """获取默认User-Agent"""
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    async def start(self) -> Dict:
        """
        启动爬虫

        Returns:
            爬取结果字典
        """
        logger.info("[BilibiliCrawler.start] Starting Bilibili crawler...")

        # 代理配置（暂不支持，可扩展）
        playwright_proxy = None
        httpx_proxy = None

        if self.config.extra.get('enable_ip_proxy', False):
            logger.warning("[BilibiliCrawler.start] IP proxy is not yet supported in refactored version")

        async with async_playwright() as playwright:
            # 启动浏览器
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium,
                playwright_proxy,
                self.user_agent,
                headless=self.config.headless
            )

            # 加载反爬脚本（相对于当前文件路径）
            stealth_js_path = Path(__file__).parent.parent.parent / "libs" / "stealth.min.js"
            if stealth_js_path.exists():
                await self.browser_context.add_init_script(path=str(stealth_js_path))
            else:
                logger.warning(f"[BilibiliCrawler.start] stealth.min.js not found at {stealth_js_path}")

            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            # 创建 Bilibili 客户端
            self.bili_client = await self.create_bilibili_client(httpx_proxy)

            # 检查登录状态
            if not await self.bili_client.pong():
                logger.info("[BilibiliCrawler.start] Not logged in, starting login process...")
                login_obj = BilibiliLogin(
                    login_type=self.config.login_type,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    login_phone=self.config.phone or "",
                    cookie_str=self.config.cookie_str or "",
                )
                await login_obj.begin()
                await self.bili_client.update_cookies(browser_context=self.browser_context)

            # 根据爬虫类型执行不同操作
            result = {}
            if self.config.crawler_type == CrawlerType.SEARCH:
                result = await self.search()
            elif self.config.crawler_type == CrawlerType.DETAIL:
                if self.config.note_ids:
                    result = await self.get_specified_videos(self.config.note_ids)
            elif self.config.crawler_type == CrawlerType.CREATOR:
                if self.config.creator_ids:
                    creator_mode = self.config.extra.get('creator_mode', True)
                    if creator_mode:
                        for creator_id in self.config.creator_ids:
                            await self.get_creator_videos(int(creator_id))
                    else:
                        await self.get_all_creator_details([int(cid) for cid in self.config.creator_ids])

            logger.info("[BilibiliCrawler.start] Bilibili Crawler finished")
            return result

    async def search(self) -> Dict:
        """
        搜索爬取

        Returns:
            搜索结果字典
        """
        search_mode = self.config.search_mode

        if search_mode == "normal":
            return await self.search_by_keywords()
        elif search_mode == "all_in_time_range":
            return await self.search_by_keywords_in_time_range(daily_limit=False)
        elif search_mode == "daily_limit_in_time_range":
            return await self.search_by_keywords_in_time_range(daily_limit=True)
        else:
            logger.warning(f"[BilibiliCrawler.search] Unknown search_mode: {search_mode}")
            return {}

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

    async def search_by_keywords(self) -> Dict:
        """
        按关键词搜索（普通模式）

        Returns:
            搜索结果字典
        """
        logger.info("[BilibiliCrawler.search_by_keywords] Begin search bilibili keywords")

        bili_limit_count = 20  # B站固定每页数量
        max_notes_count = max(self.config.max_notes_count, bili_limit_count)
        start_page = self.config.start_page
        keywords = self.config.keywords or ""

        results = {}

        for keyword in keywords.split(","):
            keyword = keyword.strip()
            if not keyword:
                continue

            logger.info(f"[BilibiliCrawler.search_by_keywords] Current search keyword: {keyword}")
            page = 1

            while (page - start_page + 1) * bili_limit_count <= max_notes_count:
                if page < start_page:
                    logger.info(f"[BilibiliCrawler.search_by_keywords] Skip page: {page}")
                    page += 1
                    continue

                logger.info(f"[BilibiliCrawler.search_by_keywords] Searching keyword: {keyword}, page: {page}")

                try:
                    videos_res = await self.bili_client.search_video_by_keyword(
                        keyword=keyword,
                        page=page,
                        page_size=bili_limit_count,
                        order=SearchOrderType.DEFAULT,
                        pubtime_begin_s="0",
                        pubtime_end_s="0",
                    )
                    video_list: List[Dict] = videos_res.get("result", [])

                    if not video_list:
                        logger.info(f"[BilibiliCrawler.search_by_keywords] No more videos for '{keyword}'")
                        break

                    semaphore = asyncio.Semaphore(self.config.max_concurrency)
                    task_list = [
                        self.get_video_info_task(aid=video_item.get("aid"), bvid="", semaphore=semaphore)
                        for video_item in video_list
                    ]
                    video_items = await asyncio.gather(*task_list)

                    video_id_list: List[str] = []
                    for video_item in video_items:
                        if video_item:
                            video_aid = video_item.get("View", {}).get("aid")
                            if video_aid:
                                video_id_list.append(str(video_aid))
                            # TODO: 保存数据到存储（暂时记录到results）
                            if keyword not in results:
                                results[keyword] = []
                            results[keyword].append(video_item)

                    page += 1

                    # 爬取间隔
                    await asyncio.sleep(self.config.crawl_interval)
                    logger.info(f"[BilibiliCrawler.search_by_keywords] Sleeping {self.config.crawl_interval}s after page {page-1}")

                    # 获取评论
                    await self.batch_get_video_comments(video_id_list)

                except Exception as e:
                    logger.error(f"[BilibiliCrawler.search_by_keywords] Error on page {page}: {e}")
                    break

        return results

    async def search_by_keywords_in_time_range(self, daily_limit: bool) -> Dict:
        """
        按关键词和时间范围搜索

        Args:
            daily_limit: 是否限制每天的爬取数量

        Returns:
            搜索结果字典
        """
        logger.info(f"[BilibiliCrawler.search_by_keywords_in_time_range] Begin search with daily_limit={daily_limit}")

        bili_limit_count = 20
        start_page = self.config.start_page
        keywords = self.config.keywords or ""
        start_day = self.config.start_day or datetime.now().strftime("%Y-%m-%d")
        end_day = self.config.end_day or datetime.now().strftime("%Y-%m-%d")

        results = {}

        for keyword in keywords.split(","):
            keyword = keyword.strip()
            if not keyword:
                continue

            logger.info(f"[BilibiliCrawler.search_by_keywords_in_time_range] Current keyword: {keyword}")
            total_notes_crawled_for_keyword = 0

            for day in pd.date_range(start=start_day, end=end_day, freq="D"):
                if daily_limit and total_notes_crawled_for_keyword >= self.config.max_notes_count:
                    logger.info(f"[BilibiliCrawler] Reached max_notes_count limit for keyword '{keyword}'")
                    break

                pubtime_begin_s, pubtime_end_s = await self.get_pubtime_datetime(
                    start=day.strftime("%Y-%m-%d"),
                    end=day.strftime("%Y-%m-%d")
                )
                page = 1
                notes_count_this_day = 0

                while True:
                    if notes_count_this_day >= self.config.max_notes_per_day:
                        logger.info(f"[BilibiliCrawler] Reached max_notes_per_day limit for {day.date()}")
                        break
                    if daily_limit and total_notes_crawled_for_keyword >= self.config.max_notes_count:
                        break

                    try:
                        logger.info(f"[BilibiliCrawler] Searching keyword: {keyword}, date: {day.date()}, page: {page}")
                        videos_res = await self.bili_client.search_video_by_keyword(
                            keyword=keyword,
                            page=page,
                            page_size=bili_limit_count,
                            order=SearchOrderType.DEFAULT,
                            pubtime_begin_s=pubtime_begin_s,
                            pubtime_end_s=pubtime_end_s,
                        )
                        video_list: List[Dict] = videos_res.get("result", [])

                        if not video_list:
                            logger.info(f"[BilibiliCrawler] No more videos for '{keyword}' on {day.date()}")
                            break

                        semaphore = asyncio.Semaphore(self.config.max_concurrency)
                        task_list = [
                            self.get_video_info_task(aid=video_item.get("aid"), bvid="", semaphore=semaphore)
                            for video_item in video_list
                        ]
                        video_items = await asyncio.gather(*task_list)

                        video_id_list: List[str] = []
                        for video_item in video_items:
                            if video_item:
                                if daily_limit and total_notes_crawled_for_keyword >= self.config.max_notes_count:
                                    break
                                if notes_count_this_day >= self.config.max_notes_per_day:
                                    break

                                notes_count_this_day += 1
                                total_notes_crawled_for_keyword += 1

                                video_aid = video_item.get("View", {}).get("aid")
                                if video_aid:
                                    video_id_list.append(str(video_aid))

                                # TODO: 保存数据
                                if keyword not in results:
                                    results[keyword] = []
                                results[keyword].append(video_item)

                        page += 1
                        await asyncio.sleep(self.config.crawl_interval)
                        await self.batch_get_video_comments(video_id_list)

                    except Exception as e:
                        logger.error(f"[BilibiliCrawler] Error searching on {day.date()}: {e}")
                        break

        return results

    async def batch_get_video_comments(self, video_id_list: List[str]):
        """
        批量获取视频评论

        Args:
            video_id_list: 视频ID列表
        """
        if not self.config.enable_get_comments:
            logger.info("[BilibiliCrawler.batch_get_video_comments] Comments crawling is disabled")
            return

        logger.info(f"[BilibiliCrawler.batch_get_video_comments] Getting comments for {len(video_id_list)} videos")
        semaphore = asyncio.Semaphore(self.config.max_concurrency)
        task_list: List[Task] = []

        for video_id in video_id_list:
            task = asyncio.create_task(self.get_comments(video_id, semaphore), name=video_id)
            task_list.append(task)

        await asyncio.gather(*task_list)

    async def get_comments(self, video_id: str, semaphore: asyncio.Semaphore):
        """
        获取单个视频的评论

        Args:
            video_id: 视频ID
            semaphore: 并发控制信号量
        """
        async with semaphore:
            try:
                logger.info(f"[BilibiliCrawler.get_comments] Getting comments for video: {video_id}")
                await asyncio.sleep(self.config.crawl_interval)

                # TODO: 实现评论获取和存储
                # await self.bili_client.get_video_all_comments(...)

            except DataFetchError as ex:
                logger.error(f"[BilibiliCrawler.get_comments] Error getting comments for {video_id}: {ex}")
            except Exception as e:
                logger.error(f"[BilibiliCrawler.get_comments] Unexpected error for {video_id}: {e}")
                raise

    async def get_creator_videos(self, creator_id: int):
        """
        获取创作者的视频列表

        Args:
            creator_id: 创作者ID
        """
        logger.info(f"[BilibiliCrawler.get_creator_videos] Getting videos for creator: {creator_id}")
        ps = 30
        pn = 1

        while True:
            result = await self.bili_client.get_creator_videos(creator_id, pn, ps)
            video_bvids_list = [video["bvid"] for video in result.get("list", {}).get("vlist", [])]

            if not video_bvids_list:
                break

            await self.get_specified_videos(video_bvids_list)

            if int(result.get("page", {}).get("count", 0)) <= pn * ps:
                break

            await asyncio.sleep(self.config.crawl_interval)
            pn += 1

    async def get_specified_videos(self, bvids_list: List[str]) -> Dict:
        """
        获取指定视频的详情

        Args:
            bvids_list: 视频BV号列表

        Returns:
            视频详情字典
        """
        logger.info(f"[BilibiliCrawler.get_specified_videos] Getting details for {len(bvids_list)} videos")
        semaphore = asyncio.Semaphore(self.config.max_concurrency)
        task_list = [
            self.get_video_info_task(aid=0, bvid=video_id, semaphore=semaphore)
            for video_id in bvids_list
        ]
        video_details = await asyncio.gather(*task_list)

        video_aids_list = []
        results = []

        for video_detail in video_details:
            if video_detail is not None:
                video_item_view: Dict = video_detail.get("View", {})
                video_aid: str = video_item_view.get("aid")
                if video_aid:
                    video_aids_list.append(str(video_aid))
                results.append(video_detail)
                # TODO: 保存数据

        await self.batch_get_video_comments(video_aids_list)
        return {"videos": results}

    async def get_video_info_task(self, aid: int, bvid: str, semaphore: asyncio.Semaphore) -> Optional[Dict]:
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
                await asyncio.sleep(self.config.crawl_interval)
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

        semaphore = asyncio.Semaphore(self.config.max_concurrency)
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
        async with semaphore:
            try:
                creator_unhandled_info: Dict = await self.bili_client.get_creator_info(creator_id)
                creator_info: Dict = {
                    "id": creator_id,
                    "name": creator_unhandled_info.get("name"),
                    "sign": creator_unhandled_info.get("sign"),
                    "avatar": creator_unhandled_info.get("face"),
                }
                # TODO: 实现粉丝、关注、动态的获取
                logger.info(f"[BilibiliCrawler.get_creator_details] Got details for creator: {creator_id}")
            except Exception as e:
                logger.error(f"[BilibiliCrawler.get_creator_details] Error for creator {creator_id}: {e}")

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

        if self.config.save_login_state:
            # 保存登录状态
            user_data_dir = os.path.join(
                os.getcwd(),
                "browser_data",
                f"{self.config.platform}"
            )

            # 使用配置中的 headless 设置，确保登录和搜索时使用相同的模式
            logger.info(f"[BilibiliCrawler.launch_browser] Using persistent context with headless={self.config.headless}")

            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=self.config.headless,  # 使用配置中的headless设置
                proxy=playwright_proxy,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height
                },
                user_agent=user_agent,
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
            browser_context = await browser.new_context(
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height
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
