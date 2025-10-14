# -*- coding: utf-8 -*-
"""
登录服务端点 - 仅负责路由注册，将业务逻辑委托给核心登录服务
"""
from __future__ import annotations

from pydantic import ValidationError

from app.api.endpoints.base import BaseEndpoint
from app.api.scheme.login_scheme import (
    LoginStatusResponse,
    LogoutResponse,
    PlatformSessionInfo,
    SessionStatusResponse,
    StartLoginRequest,
    StartLoginResponse,
)
from app.core.login import LoginServiceError, login_service
from app.providers.logger import get_logger


class LoginEndpoint(BaseEndpoint):
    """登录服务端点"""

    def __init__(self):
        super().__init__("/admin/api/login", ["登录管理", "平台认证"])
        self.logger = get_logger()
        self.service = login_service

    def register_routes(self):
        """注册路由"""
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        async def get_platforms_handler(request):
            try:
                platforms = self.service.get_supported_platforms()
                return JSONResponse(content=platforms)
            except Exception as exc:
                self.logger.error(f"获取平台列表失败: {exc}")
                return JSONResponse(content={"detail": str(exc)}, status_code=500)

        async def start_login_handler(request):
            try:
                request_model = StartLoginRequest.model_validate(await request.json())
            except ValidationError as exc:
                return JSONResponse(content={"detail": exc.errors()}, status_code=400)

            try:
                result = await self.service.start_login(request_model.to_payload())
                response_model = StartLoginResponse.model_validate(result)
                return JSONResponse(content=response_model.model_dump())
            except LoginServiceError as exc:
                return JSONResponse(content={"detail": str(exc)}, status_code=400)
            except ValidationError as exc:
                self.logger.error(f"启动登录响应验证失败: {exc}")
                return JSONResponse(content={"detail": "响应数据格式错误"}, status_code=500)
            except Exception as exc:
                self.logger.error(f"启动登录失败: {exc}")
                return JSONResponse(content={"detail": "启动登录失败"}, status_code=500)

        async def get_login_status_handler(request):
            platform = request.path_params.get("platform", "")
            try:
                result = await self.service.get_login_status(platform)
                response_model = LoginStatusResponse.model_validate(result)
                return JSONResponse(content=response_model.model_dump())
            except LoginServiceError as exc:
                return JSONResponse(content={"detail": str(exc)}, status_code=400)
            except ValidationError as exc:
                self.logger.error(f"登录状态响应验证失败: {exc}")
                return JSONResponse(content={"detail": "响应数据格式错误"}, status_code=500)
            except Exception as exc:
                self.logger.error(f"获取登录状态失败: {exc}")
                return JSONResponse(content={"detail": "获取登录状态失败"}, status_code=500)

        async def logout_handler(request):
            platform = request.path_params.get("platform", "")
            try:
                result = await self.service.logout(platform)
                response_model = LogoutResponse.model_validate(result)
                return JSONResponse(content=response_model.model_dump())
            except LoginServiceError as exc:
                return JSONResponse(content={"detail": str(exc)}, status_code=400)
            except ValidationError as exc:
                self.logger.error(f"退出登录响应验证失败: {exc}")
                return JSONResponse(content={"detail": "响应数据格式错误"}, status_code=500)
            except Exception as exc:
                self.logger.error(f"退出登录失败: {exc}")
                return JSONResponse(content={"detail": "退出登录失败"}, status_code=500)

        async def get_session_status_handler(request):
            session_id = request.path_params.get("session_id", "")
            try:
                result = await self.service.get_session_status(session_id)
                response_model = SessionStatusResponse.model_validate(result)
                return JSONResponse(content=response_model.model_dump())
            except LoginServiceError as exc:
                return JSONResponse(content={"detail": str(exc)}, status_code=404)
            except ValidationError as exc:
                self.logger.error(f"会话状态响应验证失败: {exc}")
                return JSONResponse(content={"detail": "响应数据格式错误"}, status_code=500)
            except Exception as exc:
                self.logger.error(f"获取会话状态失败: {exc}")
                return JSONResponse(content={"detail": "获取会话状态失败"}, status_code=500)

        async def list_sessions_handler(request):
            try:
                result = await self.service.list_sessions()
                response_models = [PlatformSessionInfo.model_validate(item) for item in result]
                return JSONResponse(content=[model.model_dump() for model in response_models])
            except ValidationError as exc:
                self.logger.error(f"会话列表响应验证失败: {exc}")
                return JSONResponse(content={"detail": "响应数据格式错误"}, status_code=500)
            except Exception as exc:
                self.logger.error(f"获取会话列表失败: {exc}")
                return JSONResponse(content={"detail": "获取会话列表失败"}, status_code=500)

        return [
            Route(f"{self.prefix}/platforms", get_platforms_handler, methods=["GET"]),
            Route(f"{self.prefix}/start", start_login_handler, methods=["POST"]),
            Route(f"{self.prefix}/status/{{platform}}", get_login_status_handler, methods=["GET"]),
            Route(f"{self.prefix}/logout/{{platform}}", logout_handler, methods=["POST"]),
            Route(f"{self.prefix}/session/{{session_id}}", get_session_status_handler, methods=["GET"]),
            Route(f"{self.prefix}/sessions", list_sessions_handler, methods=["GET"]),
        ]

    def register_mcp_tools(self, app):
        """登录管理目前不提供 MCP 工具"""
        return None
