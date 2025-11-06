# -*- coding: utf-8 -*-
"""发布管理端点"""

from __future__ import annotations

import os
import uuid
import json
import time
import tempfile
from typing import Dict, Any, List

from starlette.responses import JSONResponse
from starlette.requests import Request

from app.api.endpoints import main_app
from app.api.scheme.request.publish import PublishStrategyRequest
from app.api.scheme.response.publish import PublishResponse
from app.providers.logger import get_logger
from app.providers.cache.queue import PublishTask, TaskType, TaskStatus, PublishStrategy
from app.pages.admin_publish import render_publish_management_page

logger = get_logger()


def _get_publish_queue():
    """获取全局发布队列实例（延迟导入避免循环依赖）"""
    from app.api_service import get_publish_queue
    return get_publish_queue()


async def _save_uploaded_files(files: List, upload_dir: str = None) -> List[str]:
    """保存上传的文件并返回文件路径列表"""
    if upload_dir is None:
        upload_dir = os.path.join(tempfile.gettempdir(), "media_uploads")
    
    os.makedirs(upload_dir, exist_ok=True)
    saved_paths = []
    
    for file in files:
        if hasattr(file, 'filename') and hasattr(file, 'read'):
            # 生成唯一文件名
            file_ext = os.path.splitext(file.filename)[1] if file.filename else ''
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            # 保存文件
            with open(file_path, 'wb') as f:
                content = await file.read()
                f.write(content)
            
            saved_paths.append(file_path)
            logger.info(f"保存上传文件: {file_path}")
    
    return saved_paths


@main_app.custom_route("/api/publish/xhs/image", methods=["POST"])
async def publish_xhs_image(request: Request):
    """发布小红书图文"""
    try:
        # 解析multipart/form-data
        form = await request.form()
        
        # 获取基本字段
        title = form.get('title', '').strip()
        content = form.get('content', '').strip()
        tags_str = form.get('tags', '[]')
        location = form.get('location', '').strip()
        is_private = form.get('is_private') == 'true'
        
        # 解析标签
        try:
            tags = json.loads(tags_str) if tags_str else []
        except json.JSONDecodeError:
            tags = []
        
        # 验证必填字段
        if not title or not content:
            return JSONResponse(
                content={"error": "标题和内容不能为空"},
                status_code=400
            )
        
        # 获取上传的图片文件
        image_files = form.getlist('images')
        if not image_files:
            return JSONResponse(
                content={"error": "请至少上传一张图片"},
                status_code=400
            )
        
        if len(image_files) > 9:
            return JSONResponse(
                content={"error": "最多支持9张图片"},
                status_code=400
            )
        
        # 保存上传的图片文件
        image_paths = await _save_uploaded_files(image_files)
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建发布任务payload
        payload = {
            'title': title,
            'content': content,
            'tags': tags,
            'image_paths': image_paths
        }
        if location:
            payload['location'] = location
        if is_private:
            payload['is_private'] = is_private
        
        # 创建发布任务
        task = PublishTask(
            task_id=task_id,
            platform="xhs",
            task_type=TaskType.IMAGE,
            payload=payload
        )
        
        # 提交到发布队列（直接发布，不再需要审核）
        publish_queue = _get_publish_queue()
        await publish_queue.submit_task(task)
        
        response = PublishResponse(
            task_id=task_id,
            status=TaskStatus.QUEUED.value,
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
        # 解析multipart/form-data
        form = await request.form()
        
        # 获取基本字段
        title = form.get('title', '').strip()
        content = form.get('content', '').strip()
        tags_str = form.get('tags', '[]')
        location = form.get('location', '').strip()
        is_private = form.get('is_private') == 'true'
        
        # 解析标签
        try:
            tags = json.loads(tags_str) if tags_str else []
        except json.JSONDecodeError:
            tags = []
        
        # 验证必填字段
        if not title or not content:
            return JSONResponse(
                content={"error": "标题和内容不能为空"},
                status_code=400
            )
        
        # 获取上传的视频文件
        video_file = form.get('video')
        if not video_file:
            return JSONResponse(
                content={"error": "请上传视频文件"},
                status_code=400
            )
        
        # 保存上传的视频文件
        video_paths = await _save_uploaded_files([video_file])
        if not video_paths:
            return JSONResponse(
                content={"error": "视频文件保存失败"},
                status_code=500
            )
        
        video_path = video_paths[0]
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建发布任务payload
        payload = {
            'title': title,
            'content': content,
            'tags': tags,
            'video_path': video_path
        }
        if location:
            payload['location'] = location
        if is_private:
            payload['is_private'] = is_private
        
        # 创建发布任务
        task = PublishTask(
            task_id=task_id,
            platform="xhs",
            task_type=TaskType.VIDEO,
            payload=payload
        )
        
        # 提交到发布队列（直接发布，不再需要审核）
        publish_queue = _get_publish_queue()
        await publish_queue.submit_task(task)
        
        response = PublishResponse(
            task_id=task_id,
            status=TaskStatus.QUEUED.value,
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
        "content_type": task.task_type,
        "status": task.status,
        "progress": task.progress,
        "message": task.message,
        "payload": task.payload,  # 添加payload，用于展示参数
        "note_url": task.result.get("note_url") if task.result else None,
        "created_at": task.created_at,
        "updated_at": task.completed_at or task.started_at or task.queued_at or task.created_at
    }

    return JSONResponse(content=response_data)


@main_app.custom_route("/api/publish/task/{task_id}", methods=["PUT"])
async def update_publish_task(request: Request):
    """更新排队中的任务"""
    task_id = request.path_params.get("task_id", "")
    platform = request.query_params.get("platform", "xhs")

    try:
        # 获取更新数据
        payload = await request.json()
        changes = payload.get("changes", {})

        if not changes:
            return JSONResponse(
                content={"error": "没有提供要更新的数据"},
                status_code=400
            )

        # 更新任务
        publish_queue = _get_publish_queue()
        updated_task = await publish_queue.update_queued_task(platform, task_id, changes)

        return JSONResponse(content={
            "message": "任务已更新",
            "task": {
                "task_id": updated_task.task_id,
                "status": updated_task.status,
                "payload": updated_task.payload,
                "message": updated_task.message
            }
        })

    except ValueError as exc:
        return JSONResponse(
            content={"error": str(exc)},
            status_code=400
        )
    except Exception as exc:
        import traceback
        logger.error(f"更新任务失败: {exc} {traceback.format_exc()}")
        return JSONResponse(
            content={"error": "更新任务失败", "detail": str(exc)},
            status_code=500
        )


@main_app.custom_route("/api/publish/tasks", methods=["GET"])
async def list_publish_tasks(request: Request):
    """获取所有发布任务列表"""
    platform = request.query_params.get("platform", "xhs")

    # 获取队列统计
    publish_queue = _get_publish_queue()
    stats = await publish_queue.get_all_stats()
    platform_stats = stats.get("platforms", {}).get(platform, {})
    tasks = await publish_queue.list_tasks(platform, limit=100)

    # 规范化任务输出
    task_list = []
    for t in tasks:
        task_list.append({
            "task_id": t.task_id,
            "platform": t.platform,
            "content_type": t.task_type,
            "status": t.status,
            "progress": t.progress,
            "message": t.message,
            "note_url": (t.result or {}).get("note_url") if t.result else None,
            "created_at": t.created_at,
            "updated_at": t.completed_at or t.started_at or t.queued_at or t.created_at,
        })

    return JSONResponse(content={
        "tasks": task_list,
        "total": len(task_list),
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


@main_app.custom_route("/api/publish/task/{task_id}/resubmit", methods=["POST"])
async def resubmit_publish_task(request: Request):
    """重新提交失败的任务"""
    task_id = request.path_params.get("task_id", "")
    platform = request.query_params.get("platform", "xhs")

    try:
        publish_queue = _get_publish_queue()

        # 获取任务
        task = await publish_queue.get_task_status(task_id, platform)
        if not task:
            return JSONResponse(
                content={"error": "任务不存在"},
                status_code=404
            )

        # 只允许失败的任务重新提交
        if task.status != TaskStatus.FAILED.value:
            return JSONResponse(
                content={"error": f"只能重新提交失败的任务，当前状态: {task.status}"},
                status_code=400
            )

        # 重置任务状态
        task.status = TaskStatus.QUEUED
        task.retry_count = 0  # 重置重试次数
        task.error_detail = None
        task.message = "任务已重新提交"
        task.queued_at = time.time()
        task.started_at = None
        task.completed_at = None
        task.progress = 0

        # 重新加入队列
        await publish_queue.submit_task(task)

        return JSONResponse(content={
            "message": "任务已重新提交到发布队列",
            "task_id": task_id
        })

    except Exception as exc:
        logger.error(f"重新提交任务失败: {exc}")
        return JSONResponse(
            content={"error": "重新提交失败", "detail": str(exc)},
            status_code=500
        )


@main_app.custom_route("/api/publish/task/{task_id}", methods=["DELETE"])
async def delete_publish_task(request: Request):
    """删除任务"""
    task_id = request.path_params.get("task_id", "")
    platform = request.query_params.get("platform", "xhs")

    try:
        publish_queue = _get_publish_queue()
        await publish_queue.delete_task(platform, task_id)

        return JSONResponse(content={
            "message": "任务已删除"
        })

    except ValueError as exc:
        return JSONResponse(
            content={"error": str(exc)},
            status_code=400
        )
    except Exception as exc:
        logger.error(f"删除任务失败: {exc}")
        return JSONResponse(
            content={"error": "删除失败", "detail": str(exc)},
            status_code=500
        )


# 发布管理页面路由
@main_app.custom_route("/publish", methods=["GET"])
async def publish_page(request: Request):
    """发布管理页面"""
    return render_publish_management_page()
