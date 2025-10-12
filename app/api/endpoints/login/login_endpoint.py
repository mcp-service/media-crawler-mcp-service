# -*- coding: utf-8 -*-
"""
登录服务端点 - 平台登录管理API
"""
from typing import Dict, Any, List
from pathlib import Path
from fastapi import HTTPException
from pydantic import BaseModel

from app.mcp.base_endpoint import BaseEndpoint
from app.providers.logger import get_logger
from app.config.settings import global_settings
from app.core.login_service import login_service


class LoginRequest(BaseModel):
    """登录请求"""
    platform: str
    login_type: str = "qrcode"  # qrcode, phone, cookie
    phone: str = ""
    cookie: str = ""


class LoginStatusResponse(BaseModel):
    """登录状态响应"""
    platform: str
    is_logged_in: bool
    user_info: Dict[str, Any] = {}
    message: str = ""


class LoginEndpoint(BaseEndpoint):
    """登录服务端点"""

    prefix = "/login"
    tags = ["登录管理", "平台认证"]

    def __init__(self):
        super().__init__()
        self.logger = get_logger()

    def register_routes(self):
        """注册路由"""
        from fastapi import APIRouter

        router = APIRouter(prefix=self.prefix, tags=self.tags)

        @router.get("/platforms")
        async def get_platforms() -> List[Dict[str, str]]:
            """获取支持的平台列表"""
            try:
                return global_settings.platforms.list_enabled_platforms()
            except Exception as e:
                self.logger.error(f"获取平台列表失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.post("/start")
        async def start_login(request: LoginRequest) -> Dict[str, Any]:
            """
            启动登录流程

            这个接口会启动一个登录会话，返回二维码或提示信息
            """
            try:
                if request.platform not in global_settings.platforms.get_enabled_platforms():
                    raise HTTPException(status_code=400, detail=f"平台 {request.platform} 未启用")

                self.logger.info(f"[登录管理] 启动登录: platform={request.platform}, type={request.login_type}")

                # 创建登录会话
                session = await login_service.start_login(
                    platform=request.platform,
                    login_type=request.login_type,
                    phone=request.phone,
                    cookie=request.cookie
                )

                return {
                    "status": session.get("status"),
                    "platform": request.platform,
                    "login_type": request.login_type,
                    "message": session.get("message"),
                    "session_id": session.get("session_id"),
                    "qr_code_base64": session.get("qr_code_base64")  # 直接返回base64图片数据
                }

            except Exception as e:
                self.logger.error(f"[登录管理] 启动登录失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.get("/status/{platform}")
        async def get_login_status(platform: str) -> LoginStatusResponse:
            """
            获取平台登录状态
            """
            try:
                if platform not in global_settings.platforms.get_enabled_platforms():
                    raise HTTPException(status_code=400, detail=f"平台 {platform} 未启用")

                # TODO: 实际实现
                # 1. 检查browser_data目录是否有登录态
                # 2. 验证Cookie是否有效
                # 3. 返回用户信息

                return LoginStatusResponse(
                    platform=platform,
                    is_logged_in=False,  # 实际实现时检查登录态
                    user_info={},
                    message="未登录"
                )

            except Exception as e:
                self.logger.error(f"[登录管理] 获取登录状态失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.post("/logout/{platform}")
        async def logout(platform: str) -> Dict[str, Any]:
            """
            退出登录

            清除指定平台的登录态
            """
            try:
                if platform not in global_settings.platforms.get_enabled_platforms():
                    raise HTTPException(status_code=400, detail=f"平台 {platform} 未启用")

                # TODO: 实际实现
                # 1. 删除browser_data中的登录态
                # 2. 清除Cookie
                # 3. 清除Redis中的Session

                self.logger.info(f"[登录管理] 退出登录: platform={platform}")

                return {
                    "status": "success",
                    "platform": platform,
                    "message": "退出登录成功"
                }

            except Exception as e:
                self.logger.error(f"[登录管理] 退出登录失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.get("/session/{session_id}")
        async def get_session_status(session_id: str) -> Dict[str, Any]:
            """
            获取登录会话状态
            """
            try:
                session = await login_service.get_session_status(session_id)
                if not session:
                    raise HTTPException(status_code=404, detail="会话不存在")
                
                return {
                    "status": session.get("status"),
                    "platform": session.get("platform"),
                    "message": session.get("message"),
                    "qr_code_base64": session.get("qr_code_base64")
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"[登录管理] 获取会话状态失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @router.get("/sessions")
        async def list_sessions() -> List[Dict[str, Any]]:
            """
            列出所有平台的登录会话
            """
            try:
                sessions = []
                for platform_info in global_settings.platforms.list_enabled_platforms():
                    platform_code = platform_info["code"]
                    
                    # 检查是否有保存的会话
                    browser_data_dir = Path(f"browser_data/{platform_code}")
                    session_file = Path(f"browser_data/{platform_code}_session.json")
                    
                    is_logged_in = browser_data_dir.exists() or session_file.exists()
                    
                    sessions.append({
                        "platform": platform_code,
                        "platform_name": platform_info["name"],
                        "is_logged_in": is_logged_in,
                        "last_login": "最近登录" if is_logged_in else "从未登录",
                        "session_path": str(browser_data_dir) if browser_data_dir.exists() else None
                    })

                return sessions

            except Exception as e:
                self.logger.error(f"[登录管理] 获取会话列表失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        return router.routes
    
    def register_mcp_tools(self, app):
        """注册MCP工具（可选实现）"""
        # 登录管理主要提供HTTP API，暂不注册MCP工具
        pass