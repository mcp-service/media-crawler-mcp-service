# -*- coding: utf-8 -*-
"""
登录管理路由
"""
import sys
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 添加media_crawler到路径
MEDIA_CRAWLER_PATH = Path(__file__).parent.parent.parent.parent / "media_crawler"
sys.path.insert(0, str(MEDIA_CRAWLER_PATH))

from app.providers.logger import get_logger
from app.config.platform_config import PlatformConfig

router = APIRouter()


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


@router.get("/platforms")
async def get_platforms() -> List[Dict[str, str]]:
    """获取支持的平台列表"""
    return PlatformConfig.list_enabled_platforms()


@router.post("/start")
async def start_login(request: LoginRequest) -> Dict[str, Any]:
    """
    启动登录流程

    这个接口会启动一个登录会话，返回二维码或提示信息
    """
    try:
        if request.platform not in PlatformConfig.get_enabled_platforms():
            raise HTTPException(status_code=400, detail=f"平台 {request.platform} 未启用")

        # TODO: 实现实际的登录逻辑
        # 1. 创建登录会话
        # 2. 根据login_type启动对应的登录流程
        # 3. 返回二维码URL或其他提示信息

        get_logger().info(f"[登录管理] 启动登录: platform={request.platform}, type={request.login_type}")

        return {
            "status": "pending",
            "platform": request.platform,
            "login_type": request.login_type,
            "message": f"登录流程已启动，请在{request.platform}完成登录操作",
            "session_id": f"session_{request.platform}_{request.login_type}",
            "qr_code_url": None  # 实际实现时返回二维码图片URL
        }

    except Exception as e:
        get_logger().error(f"[登录管理] 启动登录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{platform}")
async def get_login_status(platform: str) -> LoginStatusResponse:
    """
    获取平台登录状态
    """
    try:
        if platform not in PlatformConfig.get_enabled_platforms():
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
        get_logger().error(f"[登录管理] 获取登录状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout/{platform}")
async def logout(platform: str) -> Dict[str, Any]:
    """
    退出登录

    清除指定平台的登录态
    """
    try:
        if platform not in PlatformConfig.get_enabled_platforms():
            raise HTTPException(status_code=400, detail=f"平台 {platform} 未启用")

        # TODO: 实际实现
        # 1. 删除browser_data中的登录态
        # 2. 清除Cookie
        # 3. 清除Redis中的Session

        get_logger().info(f"[登录管理] 退出登录: platform={platform}")

        return {
            "status": "success",
            "platform": platform,
            "message": "退出登录成功"
        }

    except Exception as e:
        get_logger().error(f"[登录管理] 退出登录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions() -> List[Dict[str, Any]]:
    """
    列出所有平台的登录会话
    """
    try:
        sessions = []
        for platform_info in PlatformConfig.list_enabled_platforms():
            platform_code = platform_info["code"]

            # TODO: 实际检查登录状态
            sessions.append({
                "platform": platform_code,
                "platform_name": platform_info["name"],
                "is_logged_in": False,  # 实际实现时检查
                "last_login_time": None,
                "expires_at": None
            })

        return sessions

    except Exception as e:
        get_logger().error(f"[登录管理] 获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))