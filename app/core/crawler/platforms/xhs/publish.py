# -*- coding: utf-8 -*-
"""Playwright-based publisher for Xiaohongshu image posts (aligned with xiaohongshu-mcp)."""

from __future__ import annotations

import asyncio
from typing import List, Dict, Any

from playwright.async_api import Page


class XhsPublisher:
    def __init__(self, page: Page) -> None:
        self.page = page

    async def goto_publish(self) -> None:
        url = "https://creator.xiaohongshu.com/publish/publish?source=official"
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(1000)

        # Try click "上传图文" tab
        try:
            await self.page.locator("div.creator-tab:has-text('上传图文')").first.click(timeout=3000)
        except Exception:
            try:
                await self.page.locator("text=上传图文").first.click(timeout=2000)
            except Exception:
                pass
        await self.page.wait_for_timeout(1000)

    async def upload_images(self, image_paths: List[str]) -> None:
        if not image_paths:
            return
        # Find file input
        selector_candidates = [
            ".upload-input input[type=file]",
            "input[type=file]",
        ]
        file_input = None
        for sel in selector_candidates:
            try:
                file_input = self.page.locator(sel).first
                if await file_input.count() > 0:
                    break
            except Exception:
                continue
        if not file_input:
            raise RuntimeError("未找到图片上传输入框")
        await file_input.set_input_files(image_paths)

        # Wait until previews appear
        try:
            await self.page.wait_for_selector(".img-preview-area .pr", timeout=60000)
        except Exception:
            # fallback to small delay
            await self.page.wait_for_timeout(1500)

    async def goto_publish_video(self) -> None:
        url = "https://creator.xiaohongshu.com/publish/publish?source=official"
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(1000)
        # Try click "上传视频" tab
        try:
            await self.page.locator("div.creator-tab:has-text('上传视频')").first.click(timeout=3000)
        except Exception:
            try:
                await self.page.locator("text=上传视频").first.click(timeout=2000)
            except Exception:
                pass
        await self.page.wait_for_timeout(800)

    async def upload_video(self, video_path: str) -> None:
        if not video_path:
            raise RuntimeError("视频路径不能为空")
        selector_candidates = [
            ".upload-input input[type=file]",
            "input[type=file]",
        ]
        file_input = None
        for sel in selector_candidates:
            try:
                file_input = self.page.locator(sel).first
                if await file_input.count() > 0:
                    break
            except Exception:
                continue
        if not file_input:
            raise RuntimeError("未找到视频上传输入框")
        await file_input.set_input_files(video_path)

        # Wait preview or processing indicator
        try:
            await self.page.wait_for_selector("video, .video-preview, .pr", timeout=90000)
        except Exception:
            await self.page.wait_for_timeout(2000)

    async def fill_title(self, title: str) -> None:
        if not title:
            return
        candidates = ["div.d-input input", "input[placeholder]", "input"]
        for sel in candidates:
            try:
                el = self.page.locator(sel).first
                if await el.count() > 0:
                    await el.fill(title)
                    await self.page.wait_for_timeout(500)
                    return
            except Exception:
                continue
        # no title filled

    async def _find_content_element(self) -> Page:
        # Prefer quill editor
        try:
            el = self.page.locator("div.ql-editor").first
            if await el.count() > 0:
                return el
        except Exception:
            pass
        # Fallback: search for p[data-placeholder*='输入正文描述']
        try:
            ph = self.page.locator("p[data-placeholder*='输入正文描述']").first
            if await ph.count() > 0:
                # bubble up to role= textbox parent
                parent = ph
                for _ in range(5):
                    parent = parent.locator("xpath=..")
                return parent
        except Exception:
            pass
        # ultimate fallback: contenteditable region
        return self.page.locator("[contenteditable='true']").first

    async def fill_content_and_tags(self, content: str, tags: List[str]) -> None:
        el = await self._find_content_element()
        if await el.count() == 0:
            raise RuntimeError("未找到正文输入框")
        if content:
            await el.click()
            await el.type(content, delay=20)
        if tags:
            # Move caret
            await el.press("End")
            await self.page.wait_for_timeout(300)
            for tag in tags[:10]:
                t = tag.lstrip('#').strip()
                if not t:
                    continue
                await el.type("#", delay=10)
                await self.page.wait_for_timeout(200)
                for ch in t:
                    await el.type(ch, delay=30)
                await self.page.wait_for_timeout(500)
                # Try select first suggestion
                try:
                    dropdown = self.page.locator("#creator-editor-topic-container .item").first
                    if await dropdown.count() > 0:
                        await dropdown.click()
                    else:
                        await el.type(" ")
                except Exception:
                    await el.type(" ")
                await self.page.wait_for_timeout(200)

    async def submit(self) -> None:
        # Click publish button
        selectors = [
            "div.submit div.d-button-content",
            "button:has-text('发布')",
        ]
        for sel in selectors:
            try:
                btn = self.page.locator(sel).first
                if await btn.count() > 0:
                    await btn.click()
                    await self.page.wait_for_timeout(1500)
                    return
            except Exception:
                continue
        # If not found, do nothing

    async def publish_image_post(self, *, title: str, content: str, images: List[str], tags: List[str]) -> Dict[str, Any]:
        await self.goto_publish()
        await self.upload_images(images)
        await self.fill_title(title)
        await self.fill_content_and_tags(content, tags)
        await self.submit()
        return {"success": True, "message": "发布完成(已尝试提交)"}

    async def publish_video_post(self, *, title: str, content: str, video: str, tags: List[str]) -> Dict[str, Any]:
        await self.goto_publish_video()
        await self.upload_video(video)
        await self.fill_title(title)
        await self.fill_content_and_tags(content, tags)
        await self.submit()
        return {"success": True, "message": "发布视频完成(已尝试提交)"}
