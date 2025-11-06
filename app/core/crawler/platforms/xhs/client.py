# -*- coding: utf-8 -*-
"""HTTP client wrapper for Xiaohongshu PC web DOM mode."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from playwright.async_api import BrowserContext, Page

from app.providers.logger import get_logger
import ujson


logger = get_logger()


class XiaoHongShuClient:
    """Xiaohongshu DOM mode client - extracts data from HTML without API calls."""

    def __init__(
        self,
        *,
        playwright_page: Page,
        cookie_dict: Dict[str, str],
        headers: Dict[str, str],
        proxy: Optional[str] = None,
        timeout: int = 60,
    ) -> None:
        self.page = playwright_page
        self.cookie_dict = cookie_dict
        self.base_headers = headers
        self.proxy = proxy
        self.timeout = timeout

        self._domain = "https://www.xiaohongshu.com"

    async def update_cookies(self, browser_context: BrowserContext) -> None:
        """Refresh cookie headers after login."""
        cookies = await browser_context.cookies()
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        self.base_headers["Cookie"] = cookie_str
        self.cookie_dict = {c["name"]: c["value"] for c in cookies}

    async def pong(self) -> bool:
        """Check login status by DOM presence like xiaohongshu-mcp.

        Navigate to /explore, wait for load, and check the user channel element:
        `.main-container .user .link-wrapper .channel`
        """
        try:
            await self.page.goto(f"{self._domain}/explore", wait_until="domcontentloaded")
        except Exception:
            # try landing page
            try:
                await self.page.goto(self._domain, wait_until="domcontentloaded")
            except Exception:
                pass

        # small settle time to allow CSR to render header
        try:
            await self.page.wait_for_timeout(600)
        except Exception:
            pass

        try:
            count = await self.page.eval_on_selector_all(
                ".main-container .user .link-wrapper .channel",
                "els => els.length"
            )
            return bool(count and int(count) > 0)
        except Exception:
            # fallback to simple querySelector
            try:
                return await self.page.evaluate(
                    "() => !!document.querySelector('.main-container .user .link-wrapper .channel')"
                )
            except Exception:
                return False

    async def get_note_by_id(self, note_id: str, xsec_source: str, xsec_token: str) -> Optional[Dict]:
        """Fetch note detail via DOM mode - prefer HTML extraction over API calls."""
        # 优先使用DOM模式获取详情
        detail = await self.get_note_by_id_from_html(
            note_id,
            xsec_source,
            xsec_token,
            enable_cookie=True,
        )
        return detail

    async def get_note_by_id_from_html(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str,
        enable_cookie: bool = False,
    ) -> Optional[Dict]:
        """Extract note detail from HTML using DOM mode like xiaohongshu-mcp."""
        # 构建 URL，仅在提供 xsec 参数时追加查询串
        url = f"{self._domain}/explore/{note_id}"
        if xsec_token:
            source = xsec_source or "pc_search"
            url = f"{url}?xsec_token={xsec_token}&xsec_source={source}"
        
        # 直接通过 Playwright 页面获取数据
        detail = await self._extract_note_via_page(url, note_id)
        logger.debug(f"[xhs.client] DOM extracted note {note_id} success={detail is not None}")
        return detail

    async def _extract_note_via_page(self, url: str, note_id: str) -> Optional[Dict]:
        """Extract note data directly from page's window.__INITIAL_STATE__ like xiaohongshu-mcp."""
        try:
            await self.page.goto(url, wait_until="domcontentloaded")
            
            # 等待页面加载和 __INITIAL_STATE__.note.noteDetailMap 初始化
            try:
                await self.page.wait_for_function(
                    "() => !!window.__INITIAL_STATE__ && !!window.__INITIAL_STATE__.note && !!window.__INITIAL_STATE__.note.noteDetailMap",
                    timeout=10000
                )
            except Exception:
                # fallback wait
                await self.page.wait_for_timeout(1000)
                
            # 提取整个 noteDetailMap（与 Go 实现一致）
            raw_json = await self.page.evaluate(
                """
                () => {
                    try {
                        const st = window.__INITIAL_STATE__;
                        if (st && st.note && st.note.noteDetailMap) {
                            return JSON.stringify(st.note.noteDetailMap);
                        }
                    } catch (e) {
                        console.error('Extract note error:', e);
                    }
                    return "";
                }
                """
            )
            
            if not raw_json:
                logger.warning(f"[xhs.client] noteDetailMap is empty for note {note_id}")
                return None
                
            import json
            try:
                note_detail_map = json.loads(raw_json)
                
                # 从 map 中提取对应 note_id 的数据
                if note_id not in note_detail_map:
                    logger.warning(f"[xhs.client] note {note_id} not found in noteDetailMap, keys: {list(note_detail_map.keys())}")
                    return None
                    
                note_data = note_detail_map[note_id]
                
                # 返回 note 字段（与 Go 实现一致）
                if "note" in note_data:
                    return note_data["note"]
                else:
                    logger.warning(f"[xhs.client] 'note' field not found in noteDetailMap[{note_id}]")
                    return None
                    
            except Exception as e:
                logger.error(f"[xhs.client] Parse note JSON failed: {e}")
                return None
                
        except Exception as e:
            logger.error(f"[xhs.client] Extract note via page failed: {e}")
            return None

    async def get_creator_info(
        self,
        *,
        user_id: str,
        xsec_token: str = "",
        xsec_source: str = "",
    ) -> Optional[Dict]:
        """Get creator info via DOM mode like xiaohongshu-mcp."""
        path = f"/user/profile/{user_id}"
        if xsec_token and xsec_source:
            path = f"{path}?xsec_token={xsec_token}&xsec_source={xsec_source}"

        url = f"{self._domain}{path}"
        return await self._extract_creator_via_page(url, user_id)

    async def _extract_creator_via_page(self, url: str, user_id: str) -> Optional[Dict]:
        """Extract creator data directly from page's window.__INITIAL_STATE__."""
        try:
            await self.page.goto(url, wait_until="domcontentloaded")
            # 等待页面加载和用户数据初始化
            try:
                await self.page.wait_for_function("() => !!window.__INITIAL_STATE__ && !!window.__INITIAL_STATE__.user", timeout=8000)
            except Exception:
                await self.page.wait_for_timeout(1000)
                
            # 使用 JavaScript 直接提取用户数据
            raw_json = await self.page.evaluate(
                """
                () => {
                    try {
                        const st = window.__INITIAL_STATE__;
                        if (st && st.user && st.user.userPageData) {
                            return JSON.stringify(st.user.userPageData);
                        }
                    } catch (e) {
                        console.error('Extract creator error:', e);
                    }
                    return "";
                }
                """
            )
            
            if not raw_json:
                return None
                
            import json
            try:
                return json.loads(raw_json)
            except Exception as e:
                logger.error(f"[xhs.client] Parse creator JSON failed: {e}")
                return None
                
        except Exception as e:
            logger.error(f"[xhs.client] Extract creator via page failed: {e}")
            return None
            
    async def get_all_notes_by_creator(
        self,
        user_id: str,
        *,
        page_num: int = 1,
        page_size: int = 10,
        callback = None,
    ) -> List[Dict[str, Any]]:
        """
        Get notes by creator using DOM method - matches xiaohongshu-mcp implementation.

        Args:
            user_id: 用户ID
            page_num: 页码（从1开始）
            page_size: 每页数量
            callback: 回调函数

        Returns:
            笔记列表
        """

        try:
            # 构建用户主页 URL
            url = f"{self._domain}/user/profile/{user_id}"
            await self.page.goto(url, wait_until="domcontentloaded")

            # 等待页面稳定（与 xiaohongshu-mcp 的 MustWaitStable 对齐）
            await self.page.wait_for_load_state("networkidle")

            # 等待 __INITIAL_STATE__ 初始化
            try:
                await self.page.wait_for_function(
                    "() => window.__INITIAL_STATE__ !== undefined",
                    timeout=8000
                )
            except Exception:
                await self.page.wait_for_timeout(1000)

            # 提取笔记数据（与 xiaohongshu-mcp 完全一致）
            raw_json = await self.page.evaluate(
                """
                () => {
                    if (window.__INITIAL_STATE__ &&
                        window.__INITIAL_STATE__.user &&
                        window.__INITIAL_STATE__.user.notes) {
                        const notes = window.__INITIAL_STATE__.user.notes;
                        // 优先使用 value（getter），如果不存在则使用 _value（内部字段）
                        const data = notes.value !== undefined ? notes.value : notes._value;
                        if (data) {
                            return JSON.stringify(data);
                        }
                    }
                    return "";
                }
                """
            )

            if not raw_json:
                logger.warning(f"[xhs.client] No notes found for user {user_id}")
                return []

            try:
                # 解析帖子数据（帖子为双重数组）
                notes_feeds = ujson.loads(raw_json)
                if not notes_feeds:
                    return []

                # 展平双重数组（与 xiaohongshu-mcp 完全一致）
                all_notes = []
                for feeds in notes_feeds:
                    if isinstance(feeds, list) and len(feeds) != 0:
                        all_notes.extend(feeds)

                if not all_notes:
                    return []

                # 分页处理
                start_idx = (page_num - 1) * page_size
                end_idx = start_idx + page_size
                page_notes = all_notes[start_idx:end_idx]

                logger.info(f"[xhs.client] Found {len(all_notes)} notes, returning page {page_num} ({len(page_notes)} notes)")

                # 回调处理
                if callback and page_notes:
                    await callback(page_notes)

                return page_notes

            except Exception as e:
                import traceback
                logger.error(f"[xhs.client] Parse notes JSON failed: {traceback.format_exc()}")
                return []

        except Exception as e:
            logger.error(f"[xhs.client] Get creator notes failed: {e}")
            return []

    async def search_notes(
        self,
        keyword: str,
        *,
        max_notes: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search notes by keyword using DOM method like xiaohongshu-mcp."""
        import json
        import urllib.parse
        
        # 构建搜索 URL
        encoded_keyword = urllib.parse.quote(keyword)
        search_url = f"{self._domain}/search_result?keyword={encoded_keyword}&source=web_explore_feed"
        
        try:
            await self.page.goto(search_url, wait_until="domcontentloaded")
            
            # 等待搜索结果数据加载，检查feeds数组存在且有内容
            try:
                await self.page.wait_for_function(
                    """() => {
                        const st = window.__INITIAL_STATE__;
                        if (st && st.search && st.search.feeds) {
                            const feeds = st.search.feeds;
                            const val = feeds.value !== undefined ? feeds.value : feeds._value;
                            return val && val.length > 0;
                        }
                        return false;
                    }""",
                    timeout=10000
                )
            except Exception as e:
                logger.warning(f"[xhs.client] Search timeout or no results for keyword={keyword}: {e}")
                return []
                
            # 提取搜索结果
            raw_json = await self.page.evaluate(
                """
                () => {
                    try {
                        const st = window.__INITIAL_STATE__;
                        if (st && st.search && st.search.feeds) {
                            const feeds = st.search.feeds;
                            const val = feeds.value !== undefined ? feeds.value : feeds._value;
                            if (val) return JSON.stringify(val);
                        }
                    } catch (e) {
                        console.error('Search error:', e);
                    }
                    return "";
                }
                """
            )
            logger.debug(f"[xhs.client] search_notes raw_json: {raw_json}")
            if not raw_json:
                logger.info(f"[xhs.client] No search results for keyword={keyword}")
                return []
                
            try:
                feeds = json.loads(raw_json)
                result = []
                
                for item in feeds:
                    if len(result) >= max_notes:
                        break
                        
                    note_id = str(item.get("id") or item.get("noteId") or "").strip()
                    if not note_id:
                        continue
                        
                    xsec_token = item.get("xsecToken", "")
                    note_obj = item.get("noteCard") or item.get("note") or {}
                    title = (note_obj.get("displayTitle") or note_obj.get("title") or "") if isinstance(note_obj, dict) else ""
                    user = note_obj.get("user", {}) if isinstance(note_obj, dict) else {}
                    inter = note_obj.get("interactInfo", {}) if isinstance(note_obj, dict) else {}

                    def _to_int(v):
                        try:
                            return int(v)
                        except Exception:
                            try:
                                return int(str(v))
                            except Exception:
                                return None

                    result.append({
                        "note_id": note_id,
                        "xsec_token": xsec_token,
                        "xsec_source": "pc_feed",
                        "title": title,
                        "note_url": f"{self._domain}/explore/{note_id}",
                        "user": {
                            "user_id": user.get("userId") or user.get("user_id"),
                            "nickname": user.get("nickname") or user.get("nickName") or user.get("nick_name"),
                            "avatar": user.get("avatar"),
                        },
                        "interact_info": {
                            "liked_count": _to_int(inter.get("likedCount")),
                            "collected_count": _to_int(inter.get("collectedCount")),
                            "comment_count": _to_int(inter.get("commentCount")),
                            "share_count": _to_int(inter.get("sharedCount")),
                        }
                    })
                    
                return result
                
            except Exception as e:
                logger.error(f"[xhs.client] Parse search results failed: {e}")
                return []
                
        except Exception as e:
            logger.error(f"[xhs.client] Search notes failed: {e}")
            return []
        
    async def get_note_all_comments(
        self,
        note_id: str,
        xsec_token: str,
        *,
        page_num: int = 1,
        page_size: int = 20,
        callback = None,
    ) -> None:
        """
        Get comments for a note using DOM method with pagination support.
        
        Args:
            note_id: 笔记ID
            xsec_token: 安全token
            page_num: 页码（从1开始）
            page_size: 每页数量
            callback: 回调函数
        """
        import asyncio
        import json
        
        try:
            # 构建笔记详情页 URL
            url = f"{self._domain}/explore/{note_id}"
            if xsec_token:
                url = f"{url}?xsec_token={xsec_token}&xsec_source=pc_search"
                
            await self.page.goto(url, wait_until="domcontentloaded")
            
            # 等待页面加载和评论数据初始化
            try:
                await self.page.wait_for_function(
                    "() => !!window.__INITIAL_STATE__ && !!window.__INITIAL_STATE__.note && !!window.__INITIAL_STATE__.note.noteDetailMap",
                    timeout=8000
                )
            except Exception:
                await self.page.wait_for_timeout(1000)

            # 等待评论加载完成（等待 firstRequestFinish 为 true 或 loading 为 false）
            try:
                await self.page.wait_for_function(
                    f"""() => {{
                        try {{
                            const st = window.__INITIAL_STATE__;
                            if (st && st.note && st.note.noteDetailMap) {{
                                const noteData = st.note.noteDetailMap['{note_id}'];
                                if (noteData && noteData.comments) {{
                                    const comments = noteData.comments;
                                    // 等待评论加载完成：firstRequestFinish 为 true 或 loading 为 false
                                    return comments.firstRequestFinish === true || comments.loading === false;
                                }}
                            }}
                        }} catch (e) {{
                            console.error('Wait comments error:', e);
                        }}
                        return false;
                    }}""",
                    timeout=10000
                )
                logger.debug(f"[xhs.client] Comments loaded for note {note_id}")
            except Exception as e:
                logger.warning(f"[xhs.client] Wait for comments timeout for note {note_id}: {e}")
                # 继续尝试提取，即使超时也可能有部分评论

            # 提取评论数据 - comments 是一个对象而不是数组
            raw_json = await self.page.evaluate(
                f"""
                () => {{
                    try {{
                        const st = window.__INITIAL_STATE__;
                        if (st && st.note && st.note.noteDetailMap) {{
                            const noteData = st.note.noteDetailMap['{note_id}'];
                            if (noteData && noteData.comments) {{
                                // comments 是对象，包含 list, cursor, hasMore 字段
                                return JSON.stringify(noteData.comments);
                            }}
                        }}
                    }} catch (e) {{
                        console.error('Extract comments error:', e);
                    }}
                    return "";
                }}
                """
            )
            logger.debug(f"[xhs.client] search_notes raw_json: {raw_json}")
            if not raw_json:
                logger.warning(f"[xhs.client] No comments found for note {note_id}")
                return

            try:
                comments_obj = json.loads(raw_json)
                if not comments_obj:
                    return

                # comments 是对象 {list: [...], cursor: "...", hasMore: bool}
                # 需要提取 list 字段
                all_comments = comments_obj.get("list", []) if isinstance(comments_obj, dict) else []
                if not all_comments:
                    return

                # 分页处理
                start_idx = (page_num - 1) * page_size
                end_idx = start_idx + page_size
                page_comments = all_comments[start_idx:end_idx]

                logger.info(f"[xhs.client] Found {len(all_comments)} comments, returning page {page_num} ({len(page_comments)} comments)")

                # 回调处理
                if callback and page_comments:
                    await callback(note_id, page_comments)
                    
            except Exception as e:
                logger.error(f"[xhs.client] Parse comments JSON failed: {e}")
                
        except Exception as e:
            logger.error(f"[xhs.client] Get note comments failed: {e}")


__all__ = ["XiaoHongShuClient"]