# -*- coding: utf-8 -*-
"""
边车服务端点 - MediaCrawler 爬虫功能API
"""
from typing import Dict, Any, Optional
from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.mcp.base_endpoint import BaseEndpoint
from app.providers.logger import get_logger
from app.core.media_crawler_service import MediaCrawlerService
from app.config.settings import global_settings


# === Request Models ===

class CrawlByKeywordRequest(BaseModel):
    """关键词爬取请求"""
    platform: str = Field(..., description="平台代码: xhs, dy, ks, bili, wb, tieba, zhihu")
    keywords: str = Field(..., description="搜索关键词，多个用逗号分隔")
    max_notes: int = Field(15, description="最大爬取帖子数")
    enable_comments: bool = Field(True, description="是否爬取评论")
    max_comments_per_note: int = Field(10, description="每个帖子最大评论数")
    login_type: str = Field("cookie", description="登录类型: qrcode, phone, cookie")
    headless: bool = Field(False, description="是否无头模式")
    save_data_option: str = Field("json", description="数据保存方式: json, csv, db, sqlite")


class CrawlByNoteUrlsRequest(BaseModel):
    """URL爬取请求"""
    platform: str = Field(..., description="平台代码")
    note_urls: list[str] = Field(..., description="帖子URL列表")
    enable_comments: bool = Field(True, description="是否爬取评论")
    max_comments_per_note: int = Field(10, description="每个帖子最大评论数")
    login_type: str = Field("cookie", description="登录类型")
    headless: bool = Field(False, description="是否无头模式")
    save_data_option: str = Field("json", description="数据保存方式")


class CrawlByCreatorRequest(BaseModel):
    """创作者爬取请求"""
    platform: str = Field(..., description="平台代码")
    creator_ids: list[str] = Field(..., description="创作者ID列表")
    enable_comments: bool = Field(True, description="是否爬取评论")
    max_comments_per_note: int = Field(10, description="每个帖子最大评论数")
    login_type: str = Field("cookie", description="登录类型")
    headless: bool = Field(False, description="是否无头模式")
    save_data_option: str = Field("json", description="数据保存方式")


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    config: Dict[str, Any] = Field(..., description="配置字典")


class SidecarEndpoint(BaseEndpoint):
    """边车服务端点"""

    prefix = "/sidecar"
    tags = ["边车服务", "MediaCrawler"]

    def __init__(self):
        super().__init__()
        self.logger = get_logger()
        self.crawler_service: Optional[MediaCrawlerService] = None

    async def startup(self):
        """启动时初始化边车服务"""
        try:
            self.crawler_service = MediaCrawlerService(global_settings)
            await self.crawler_service.startup()
            self.logger.info("✅ 边车服务端点初始化完成")
        except Exception as e:
            self.logger.error(f"❌ 边车服务端点初始化失败: {e}")
            raise

    async def shutdown(self):
        """关闭时清理资源"""
        try:
            if self.crawler_service:
                await self.crawler_service.shutdown()
            self.logger.info("✅ 边车服务端点资源已清理")
        except Exception as e:
            self.logger.error(f"❌ 边车服务端点清理失败: {e}")

    def register_routes(self):
        """注册路由"""
        from fastapi import APIRouter

        router = APIRouter(prefix=self.prefix, tags=self.tags)

        @router.get("/health")
        async def health_check():
            """健康检查"""
            return {"status": "healthy", "service": "MediaCrawler Sidecar"}

        @router.get("/stats")
        async def get_stats():
            """获取服务统计"""
            if not self.crawler_service:
                raise HTTPException(status_code=503, detail="Service not initialized")
            return self.crawler_service.get_stats()

        @router.post("/crawl/keyword")
        async def crawl_by_keyword(request: CrawlByKeywordRequest):
            """根据关键词爬取"""
            if not self.crawler_service:
                raise HTTPException(status_code=503, detail="Service not initialized")

            try:
                result = await self.crawler_service.crawl_by_keyword(**request.model_dump())
                return result
            except Exception as e:
                self.logger.error(f"关键词爬取失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.post("/crawl/note-urls")
        async def crawl_by_note_urls(request: CrawlByNoteUrlsRequest):
            """根据URL爬取"""
            if not self.crawler_service:
                raise HTTPException(status_code=503, detail="Service not initialized")

            try:
                result = await self.crawler_service.crawl_by_note_urls(**request.model_dump())
                return result
            except Exception as e:
                self.logger.error(f"URL爬取失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.post("/crawl/creator")
        async def crawl_by_creator(request: CrawlByCreatorRequest):
            """爬取创作者内容"""
            if not self.crawler_service:
                raise HTTPException(status_code=503, detail="Service not initialized")

            try:
                result = await self.crawler_service.crawl_by_creator(**request.model_dump())
                return result
            except Exception as e:
                self.logger.error(f"创作者爬取失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.post("/config/update")
        async def update_config(request: ConfigUpdateRequest):
            """更新配置"""
            if not self.crawler_service:
                raise HTTPException(status_code=503, detail="Service not initialized")

            try:
                # TODO: 实现配置热更新
                return {"status": "success", "message": "配置已更新"}
            except Exception as e:
                self.logger.error(f"配置更新失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        return router.routes
    
    def register_mcp_tools(self, app):
        """注册MCP工具（可选实现）"""
        # 边车服务主要提供HTTP API，暂不注册MCP工具
        pass