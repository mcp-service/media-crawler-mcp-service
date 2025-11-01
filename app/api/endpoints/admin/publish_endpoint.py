# -*- coding: utf-8 -*-
"""发布管理端点"""

from __future__ import annotations

import uuid
from typing import Dict, Any

from starlette.responses import JSONResponse
from starlette.requests import Request

from app.api.endpoints import main_app
from app.api.scheme.request.publish import (
    PublishImageRequest,
    PublishVideoRequest,
    PublishStrategyRequest
)
from app.api.scheme.response.publish import PublishResponse
from app.providers.logger import get_logger
from app.providers.cache.queue import PublishTask, TaskType, PublishStrategy
from app.pages.admin_publish import render_publish_management_page

logger = get_logger()


def _get_publish_queue():
    """获取全局发布队列实例（延迟导入避免循环依赖）"""
    from app.api_service import get_publish_queue
    return get_publish_queue()


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
        publish_queue = _get_publish_queue()
        await publish_queue.submit_task(task)

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
        publish_queue = _get_publish_queue()
        await publish_queue.submit_task(task)

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

    publish_queue = _get_publish_queue()
    task = await publish_queue.get_task_status(task_id, platform)
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
    publish_queue = _get_publish_queue()
    stats = await publish_queue.get_all_stats()
    platform_stats = stats.get("platforms", {}).get(platform, {})

    return JSONResponse(content={
        "tasks": [],  # TODO: 实现任务列表获取
        "total": 0,
        "stats": platform_stats
    })


@main_app.custom_route("/api/publish/stats", methods=["GET"])
async def get_publish_stats(request: Request):
    """获取发布队列统计信息"""
    publish_queue = _get_publish_queue()
    stats = await publish_queue.get_all_stats()
    return JSONResponse(content=stats)


@main_app.custom_route("/api/publish/strategy/{platform}", methods=["GET"])
async def get_publish_strategy(request: Request):
    """获取平台发布策略"""
    platform = request.path_params.get("platform", "")

    publish_queue = _get_publish_queue()
    strategy = publish_queue.get_platform_strategy(platform)
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
        publish_queue = _get_publish_queue()
        await publish_queue.update_platform_strategy(platform, new_strategy)

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


# 发布管理页面路由
@main_app.custom_route("/publish", methods=["GET"])
async def publish_page(request: Request):
    """发布管理页面"""
    return render_publish_management_page()