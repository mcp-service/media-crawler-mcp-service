# -*- coding: utf-8 -*-
"""发布管理端点"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field
from starlette.responses import JSONResponse
from starlette.requests import Request

from app.api.endpoints import main_app
from app.providers.logger import get_logger
from app.providers.queue.queuer import queuer, PublishTask, TaskType, PublishStrategy, config_to_strategy
from app.core.crawler.platforms.xhs.publish import XhsPublisher
from app.config.settings import global_settings

logger = get_logger()


class PublishImageRequest(BaseModel):
    """发布图文请求"""
    title: str = Field(..., description="标题")
    content: str = Field(..., description="正文内容")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    topics: List[str] = Field(default_factory=list, description="话题列表")
    image_paths: List[str] = Field(..., description="图片路径列表")
    is_private: bool = Field(default=False, description="是否私密发布")
    location: Optional[str] = Field(None, description="位置信息")


class PublishStrategyRequest(BaseModel):
    """发布策略配置请求"""
    min_interval: int = Field(..., description="最小发布间隔(秒)")
    max_concurrent: int = Field(..., description="最大并发数")
    retry_count: int = Field(..., description="重试次数")
    retry_delay: int = Field(..., description="重试延迟(秒)")
    daily_limit: int = Field(..., description="每日发布限制")
    hourly_limit: int = Field(..., description="每小时发布限制")


class PublishVideoRequest(BaseModel):
    """发布视频请求"""
    title: str = Field(..., description="标题")
    content: str = Field(..., description="正文内容")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    topics: List[str] = Field(default_factory=list, description="话题列表")
    video_path: str = Field(..., description="视频文件路径")
    cover_path: Optional[str] = Field(None, description="封面图片路径")
    is_private: bool = Field(default=False, description="是否私密发布")
    location: Optional[str] = Field(None, description="位置信息")


class PublishResponse(BaseModel):
    """发布响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="发布状态")
    message: str = Field(default="", description="状态消息")
    note_url: Optional[str] = Field(None, description="发布成功后的笔记链接")
    error_detail: Optional[str] = Field(None, description="错误详情")


class PublishTaskStatus(BaseModel):
    """发布任务状态"""
    task_id: str = Field(..., description="任务ID")
    platform: str = Field(..., description="发布平台")
    content_type: str = Field(..., description="内容类型：image/video")
    status: str = Field(..., description="任务状态：pending/uploading/processing/success/failed")
    progress: int = Field(default=0, description="进度百分比")
    message: str = Field(default="", description="状态消息")
    note_url: Optional[str] = Field(None, description="发布成功后的笔记链接")
    created_at: float = Field(..., description="创建时间戳")
    updated_at: float = Field(..., description="更新时间戳")


# XHS发布执行器
async def xhs_executor(task: PublishTask) -> Dict[str, Any]:
    """小红书发布执行器"""
    publisher = XhsPublisher()
    await publisher.ensure_login_and_client()
    
    if task.task_type == TaskType.IMAGE:
        # 验证图片路径
        image_paths = []
        for path_str in task.payload["image_paths"]:
            path = Path(path_str)
            if not path.exists():
                raise FileNotFoundError(f"图片文件不存在: {path_str}")
            image_paths.append(path)
        
        # 发布图文
        publish_data = {
            "title": task.payload["title"],
            "content": task.payload["content"],
            "tags": task.payload.get("tags", []),
            "topics": task.payload.get("topics", []),
            "image_paths": image_paths,
            "is_private": task.payload.get("is_private", False),
            "location": task.payload.get("location")
        }
        
        return await publisher.publish_image_note(**publish_data)
        
    elif task.task_type == TaskType.VIDEO:
        # 验证视频路径
        video_path = Path(task.payload["video_path"])
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {task.payload['video_path']}")
        
        cover_path = None
        if task.payload.get("cover_path"):
            cover_path = Path(task.payload["cover_path"])
            if not cover_path.exists():
                raise FileNotFoundError(f"封面文件不存在: {task.payload['cover_path']}")
        
        # 发布视频
        publish_data = {
            "title": task.payload["title"],
            "content": task.payload["content"],
            "tags": task.payload.get("tags", []),
            "topics": task.payload.get("topics", []),
            "video_path": video_path,
            "cover_path": cover_path,
            "is_private": task.payload.get("is_private", False),
            "location": task.payload.get("location")
        }
        
        return await publisher.publish_video_note(**publish_data)
    
    else:
        raise ValueError(f"不支持的任务类型: {task.task_type}")

# 注册XHS平台到队列管理器
queuer.register_platform("xhs", xhs_executor)


@main_app.custom_route("/api/publish/xhs/image", methods=["POST"])
async def publish_xhs_image(request: Request):
    """发布小红书图文"""
    try:
        payload = await request.json()
        req = PublishImageRequest.model_validate(payload)

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 创建发布任务
        task = PublishTask(
            task_id=task_id,
            platform="xhs",
            task_type=TaskType.IMAGE,
            payload=req.model_dump()
        )

        # 提交到队列
        await queuer.submit_task(task)

        response = PublishResponse(
            task_id=task_id,
            status="queued",
            message="发布任务已提交到队列"
        )

        return JSONResponse(content=response.model_dump())

    except Exception as exc:
        logger.error(f"发布图文失败: {exc}")
        return JSONResponse(
            content={"error": "发布失败", "detail": str(exc)},
            status_code=500
        )


@main_app.custom_route("/api/publish/xhs/video", methods=["POST"])
async def publish_xhs_video(request: Request):
    """发布小红书视频"""
    try:
        payload = await request.json()
        req = PublishVideoRequest.model_validate(payload)

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 创建发布任务
        task = PublishTask(
            task_id=task_id,
            platform="xhs",
            task_type=TaskType.VIDEO,
            payload=req.model_dump()
        )

        # 提交到队列
        await queuer.submit_task(task)

        response = PublishResponse(
            task_id=task_id,
            status="queued",
            message="发布任务已提交到队列"
        )

        return JSONResponse(content=response.model_dump())

    except Exception as exc:
        logger.error(f"发布视频失败: {exc}")
        return JSONResponse(
            content={"error": "发布失败", "detail": str(exc)},
            status_code=500
        )


@main_app.custom_route("/api/publish/task/{task_id}", methods=["GET"])
async def get_publish_task_status(request: Request):
    """获取发布任务状态"""
    task_id = request.path_params.get("task_id", "")
    platform = request.query_params.get("platform", "xhs")

    task = await queuer.get_task_status(task_id, platform)
    if not task:
        return JSONResponse(
            content={"error": "任务不存在"},
            status_code=404
        )

    # 转换为兼容的响应格式
    response_data = {
        "task_id": task.task_id,
        "platform": task.platform,
        "content_type": task.task_type.value,
        "status": task.status.value,
        "progress": task.progress,
        "message": task.message,
        "note_url": task.result.get("note_url") if task.result else None,
        "created_at": task.created_at,
        "updated_at": task.completed_at or task.started_at or task.queued_at or task.created_at
    }
    
    return JSONResponse(content=response_data)


@main_app.custom_route("/api/publish/tasks", methods=["GET"])
async def list_publish_tasks(request: Request):
    """获取所有发布任务列表"""
    platform = request.query_params.get("platform", "xhs")
    
    # 获取队列统计
    stats = await queuer.get_all_stats()
    platform_stats = stats.get("platforms", {}).get(platform, {})
    
    # 这里简化处理，实际应该从Redis获取任务列表
    # 暂时返回统计信息
    return JSONResponse(content={
        "tasks": [],  # TODO: 实现任务列表获取
        "total": 0,
        "stats": platform_stats
    })


@main_app.custom_route("/api/publish/stats", methods=["GET"])
async def get_publish_stats(request: Request):
    """获取发布队列统计信息"""
    stats = await queuer.get_all_stats()
    return JSONResponse(content=stats)


@main_app.custom_route("/api/publish/strategy/{platform}", methods=["GET"])
async def get_publish_strategy(request: Request):
    """获取平台发布策略"""
    platform = request.path_params.get("platform", "")
    
    strategy = queuer.get_platform_strategy(platform)
    if not strategy:
        return JSONResponse(
            content={"error": f"平台 {platform} 未注册"},
            status_code=404
        )
    
    return JSONResponse(content={
        "platform": platform,
        "strategy": {
            "min_interval": strategy.min_interval,
            "max_concurrent": strategy.max_concurrent,
            "retry_count": strategy.retry_count,
            "retry_delay": strategy.retry_delay,
            "daily_limit": strategy.daily_limit,
            "hourly_limit": strategy.hourly_limit
        }
    })


@main_app.custom_route("/api/publish/strategy/{platform}", methods=["PUT"])
async def update_publish_strategy(request: Request):
    """更新平台发布策略"""
    platform = request.path_params.get("platform", "")
    
    try:
        payload = await request.json()
        strategy_req = PublishStrategyRequest.model_validate(payload)
        
        # 创建新策略
        new_strategy = PublishStrategy(
            min_interval=strategy_req.min_interval,
            max_concurrent=strategy_req.max_concurrent,
            retry_count=strategy_req.retry_count,
            retry_delay=strategy_req.retry_delay,
            daily_limit=strategy_req.daily_limit,
            hourly_limit=strategy_req.hourly_limit
        )
        
        # 更新队列策略
        await queuer.update_platform_strategy(platform, new_strategy)
        
        return JSONResponse(content={
            "message": f"平台 {platform} 策略已更新",
            "strategy": strategy_req.model_dump()
        })
        
    except ValueError as exc:
        return JSONResponse(
            content={"error": str(exc)},
            status_code=400
        )
    except Exception as exc:
        logger.error(f"更新发布策略失败: {exc}")
        return JSONResponse(
            content={"error": "更新策略失败", "detail": str(exc)},
            status_code=500
        )


# 启动队列管理器
@main_app.on_event("startup")
async def startup_event():
    """应用启动时启动队列"""
    await queuer.start_all()
    logger.info("发布队列管理器已启动")

@main_app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时停止队列"""
    await queuer.stop_all()
    logger.info("发布队列管理器已停止")