# -*- coding: utf-8 -*-
"""HTTP client wrapper for Xiaohongshu PC web DOM mode."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from playwright.async_api import BrowserContext, Page

from app.providers.logger import get_logger


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
        
        # 直接通过 Playwright 页面获取数据，类似 xiaohongshu-mcp 的实现
        detail = await self._extract_note_via_page(url, note_id)
        logger.debug(f"[xhs.client] DOM extracted note {note_id} success={detail is not None}")
        return detail

    async def _extract_note_via_page(self, url: str, note_id: str) -> Optional[Dict]:
        """Extract note data directly from page's window.__INITIAL_STATE__ like xiaohongshu-mcp."""
        try:
            await self.page.goto(url, wait_until="domcontentloaded")
            # 等待页面加载和 __INITIAL_STATE__ 初始化
            try:
                await self.page.wait_for_function("() => !!window.__INITIAL_STATE__ && !!window.__INITIAL_STATE__.note", timeout=8000)
            except Exception:
                # fallback wait
                await self.page.wait_for_timeout(1000)
                
            # 使用 JavaScript 直接提取数据，类似 xiaohongshu-mcp 的方式
            raw_json = await self.page.evaluate(
                """
                () => {
                    try {
                        const st = window.__INITIAL_STATE__;
                        if (st && st.note && st.note.noteDetailMap) {
                            const noteData = st.note.noteDetailMap[arguments[0]];
                            if (noteData && noteData.note) {
                                return JSON.stringify(noteData.note);
                            }
                        }
                    } catch (e) {
                        console.error('Extract note error:', e);
                    }
                    return "";
                }
                """, 
                note_id
            )
            
            if not raw_json:
                return None
                
            import json
            try:
                return json.loads(raw_json)
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
        crawl_interval: float = 1.0,
        callback = None,
        max_notes: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get all notes by creator using DOM method."""
        import asyncio
        
        notes = []
        page_num = 1
        
        while len(notes) < max_notes:
            try:
                # 构建用户主页 URL
                url = f"{self._domain}/user/profile/{user_id}"
                await self.page.goto(url, wait_until="domcontentloaded")
                
                # 等待页面加载
                try:
                    await self.page.wait_for_function("() => !!window.__INITIAL_STATE__", timeout=5000)
                except Exception:
                    pass
                    
                # 提取当前页面的笔记数据
                raw_json = await self.page.evaluate(
                    """
                    () => {
                        try {
                            const st = window.__INITIAL_STATE__;
                            if (st && st.user && st.user.notes) {
                                const notesData = st.user.notes;
                                const feeds = notesData.value !== undefined ? notesData.value : notesData._value;
                                if (feeds) {
                                    return JSON.stringify(feeds);
                                }
                            }
                        } catch (e) {
                            console.error('Extract notes error:', e);
                        }
                        return "";
                    }
                    """
                )
                
                if not raw_json:
                    break
                    
                import json
                try:
                    page_notes = json.loads(raw_json)
                    if not page_notes:
                        break
                        
                    for note in page_notes:
                        if len(notes) >= max_notes:
                            break
                        notes.append(note)
                        
                    # 如果回调函数存在，调用它
                    if callback:
                        await callback(page_notes)
                        
                    # 检查是否还有更多数据
                    if len(page_notes) == 0:
                        break
                        
                    # 休眠间隔
                    if crawl_interval > 0:
                        await asyncio.sleep(crawl_interval)
                        
                    page_num += 1
                    
                except Exception as e:
                    logger.error(f"[xhs.client] Parse notes JSON failed: {e}")
                    break
                    
            except Exception as e:
                logger.error(f"[xhs.client] Get creator notes failed page {page_num}: {e}")
                break
                
        return notes[:max_notes]
        
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
            # 等待搜索结果加载
            try:
                await self.page.wait_for_function("() => !!window.__INITIAL_STATE__ && !!window.__INITIAL_STATE__.search", timeout=8000)
            except Exception:
                await self.page.wait_for_timeout(1000)
                
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
        crawl_interval: float = 1.0,
        callback = None,
        max_count: int = 50,
    ) -> None:
        """Get all comments for a note using DOM method."""
        import asyncio
        
        try:
            # 构建笔记详情页 URL
            url = f"{self._domain}/explore/{note_id}"
            if xsec_token:
                url = f"{url}?xsec_token={xsec_token}&xsec_source=pc_search"
                
            await self.page.goto(url, wait_until="domcontentloaded")
            
            # 等待页面加载
            try:
                await self.page.wait_for_function("() => !!window.__INITIAL_STATE__", timeout=5000)
            except Exception:
                pass
                
            # 提取评论数据
            raw_json = await self.page.evaluate(
                """
                () => {
                    try {
                        const st = window.__INITIAL_STATE__;
                        if (st && st.note && st.note.noteDetailMap) {
                            const noteData = st.note.noteDetailMap[arguments[0]];
                            if (noteData && noteData.comments) {
                                return JSON.stringify(noteData.comments);
                            }
                        }
                    } catch (e) {
                        console.error('Extract comments error:', e);
                    }
                    return "";
                }
                """,
                note_id
            )
            
            if raw_json and callback:
                import json
                try:
                    comments = json.loads(raw_json)
                    # 限制评论数量
                    comments = comments[:max_count] if isinstance(comments, list) else []
                    await callback(note_id, comments)
                except Exception as e:
                    logger.error(f"[xhs.client] Parse comments JSON failed: {e}")
                    
        except Exception as e:
            logger.error(f"[xhs.client] Get note comments failed: {e}")


__all__ = ["XiaoHongShuClient"]