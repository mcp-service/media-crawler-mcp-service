# -*- coding: utf-8 -*-
"""登录服务端点 - 仅负责路由注册，将业务逻辑委托给核心登录服务"""

from __future__ import annotations

import uuid

from pydantic import ValidationError
from starlette.responses import JSONResponse
from app.api.scheme.request.login_scheme import (
    LoginStatusResponse,
    LogoutResponse,
    PlatformSessionInfo,
    SessionStatusResponse,
    StartLoginRequest,
    StartLoginResponse,
)
from app.config.settings import global_settings
from app.core.login import LoginServiceError, login_service
from app.providers.logger import get_logger
from app.api.endpoints import main_app

logger = get_logger()
service = login_service


@main_app.custom_route("/platforms", methods=["GET"])
@main_app.custom_route("/api/login/platforms", methods=["GET"])
async def login_get_platforms(request):
    try:
        platforms = service.get_supported_platforms()
        if not platforms:
            fallback = [
                p.value if hasattr(p, "value") else str(p)
                for p in getattr(global_settings.platform, "enabled_platforms", [])
            ]
            logger.warning(
                f"登录适配器列表为空，使用配置回退: {', '.join(fallback) or '<none>'}"
            )
            platforms = fallback
        return JSONResponse(content=platforms)
    except Exception as exc:
        logger.error(f"获取平台列表失败: {exc}")
        return JSONResponse(content={"detail": str(exc)}, status_code=500)


@main_app.custom_route("/start", methods=["POST"])
@main_app.custom_route("/api/login/start", methods=["POST"])
async def login_start(request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    try:
        request_model = StartLoginRequest.model_validate(payload)
    except ValidationError as exc:
        return JSONResponse(content={"detail": exc.errors()}, status_code=400)

    try:
        result = await service.start_login(request_model.to_payload())
        response_model = StartLoginResponse.model_validate(result)
        return JSONResponse(content=response_model.model_dump())
    except LoginServiceError as exc:
        return JSONResponse(content={"detail": str(exc)}, status_code=400)
    except ValidationError as exc:
        logger.error(f"启动登录响应验证失败: {exc}")
        return JSONResponse(content={"detail": "响应数据格式错误"}, status_code=500)
    except Exception as exc:
        logger.error(f"启动登录失败: {exc}")
        return JSONResponse(content={"detail": "启动登录失败"}, status_code=500)


@main_app.custom_route("/status/{platform}", methods=["GET"])
@main_app.custom_route("/api/login/status/{platform}", methods=["GET"])
async def login_status(request):
    platform = request.path_params.get("platform", "")
    try:
        result = await service.get_login_status(platform)
        response_model = LoginStatusResponse.model_validate(result)
        return JSONResponse(content=response_model.model_dump())
    except LoginServiceError as exc:
        return JSONResponse(content={"detail": str(exc)}, status_code=400)
    except ValidationError as exc:
        logger.error(f"登录状态响应验证失败: {exc}")
        return JSONResponse(content={"detail": "响应数据格式错误"}, status_code=500)
    except Exception as exc:
        logger.error(f"获取登录状态失败: {exc}")
        return JSONResponse(content={"detail": "获取登录状态失败"}, status_code=500)


@main_app.custom_route("/logout/{platform}", methods=["POST"])
@main_app.custom_route("/api/login/logout/{platform}", methods=["POST"])
async def login_logout(request):
    platform = request.path_params.get("platform", "")
    try:
        result = await service.logout(platform)
        response_model = LogoutResponse.model_validate(result)
        return JSONResponse(content=response_model.model_dump())
    except LoginServiceError as exc:
        return JSONResponse(content={"detail": str(exc)}, status_code=400)
    except ValidationError as exc:
        logger.error(f"退出登录响应验证失败: {exc}")
        return JSONResponse(content={"detail": "响应数据格式错误"}, status_code=500)
    except Exception as exc:
        logger.error(f"退出登录失败: {exc}")
        return JSONResponse(content={"detail": "退出登录失败"}, status_code=500)


@main_app.custom_route("/session/{session_id}", methods=["GET"])
@main_app.custom_route("/api/login/session/{session_id}", methods=["GET"])
async def login_session_status(request):
    session_id = request.path_params.get("session_id", "")

    try:
        uuid.UUID(str(session_id))
    except (ValueError, TypeError):
        return JSONResponse(content={"detail": "无效的会话ID"}, status_code=400)

    try:
        result = await service.get_session_status(session_id)
        response_model = SessionStatusResponse.model_validate(result)
        return JSONResponse(content=response_model.model_dump())
    except LoginServiceError as exc:
        return JSONResponse(content={"detail": str(exc)}, status_code=404)
    except ValidationError as exc:
        logger.error(f"会话状态响应验证失败: {exc}")
        return JSONResponse(content={"detail": "响应数据格式错误"}, status_code=500)
    except Exception as exc:
        logger.error(f"获取会话状态失败: {exc}")
        return JSONResponse(content={"detail": "获取会话状态失败"}, status_code=500)


@main_app.custom_route("/sessions", methods=["GET"])
@main_app.custom_route("/api/login/sessions", methods=["GET"])
async def login_sessions(request):
    try:
        params = request.query_params or {}
        force = params.get('force')

        if force:
            # 刷新小红书和bilibili为 DOM 检测并回写（不分离新端点）
            from app.config.settings import Platform
            await service.refresh_platform_state(Platform.XIAOHONGSHU.value, force=True)
            await service.refresh_platform_state(Platform.BILIBILI.value, force=True)
            # 之后走缓存读取，避免其它平台被动触发
            result = await service.list_sessions_cached()
        else:
            # 仅从缓存读取
            result = await service.list_sessions_cached()
        response_models = [PlatformSessionInfo.model_validate(item) for item in result]
        return JSONResponse(content=[model.model_dump() for model in response_models])
    except ValidationError as exc:
        logger.error(f"会话列表响应验证失败: {exc}")
        return JSONResponse(content={"detail": "响应数据格式错误"}, status_code=500)
    except Exception as exc:
        logger.error(f"获取会话列表失败: {exc}")
        return JSONResponse(content={"detail": "获取会话列表失败"}, status_code=500)
