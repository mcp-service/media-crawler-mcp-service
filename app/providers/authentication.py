# -*- coding: utf-8 -*-
"""
JWT认证模块
"""

import datetime
import jwt
from typing import Dict, Any, Optional
from app.config.settings import global_settings


class JwtAuth:
    """简化的JWT认证类"""

    def __init__(self,
                 secret_key: str = 'your-secret-key-here',
                 algorithm: str = 'HS256',
                 issuer: str = 'mcp-toolse',
                 access_token_expire_minutes: int = 30):
        """
        初始化JWT认证

        Args:
            secret_key: JWT密钥
            algorithm: 加密算法
            issuer: 发行者
            access_token_expire_minutes: 访问令牌过期时间（分钟）
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.issuer = issuer
        self.access_token_expire_minutes = access_token_expire_minutes

    def create_access_token(self, user_info: Dict[str, Any], expires_delta: Optional[datetime.timedelta] = None) -> str:
        """
        创建访问令牌

        Args:
            user_info: 用户信息
            expires_delta: 过期时间增量

        Returns:
            JWT令牌字符串
        """
        if expires_delta:
            expire = datetime.datetime.utcnow() + expires_delta
        else:
            expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=self.access_token_expire_minutes)

        to_encode = {
            "exp": expire,
            "iss": self.issuer,
            "iat": datetime.datetime.utcnow(),
            "data": user_info
        }

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_info: Dict[str, Any], expires_days: int = 7) -> str:
        """
        创建刷新令牌

        Args:
            user_info: 用户信息
            expires_days: 过期天数

        Returns:
            JWT令牌字符串
        """
        expire = datetime.datetime.utcnow() + datetime.timedelta(days=expires_days)

        to_encode = {
            "exp": expire,
            "iss": self.issuer,
            "iat": datetime.datetime.utcnow(),
            "type": "refresh",
            "data": user_info
        }

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        解码令牌

        Args:
            token: JWT令牌

        Returns:
            解码后的数据
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                options={"verify_exp": True}
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("令牌已过期")
        except jwt.InvalidTokenError:
            raise ValueError("无效的令牌")

    def verify_token(self, token: str) -> bool:
        """
        验证令牌是否有效

        Args:
            token: JWT令牌

        Returns:
            是否有效
        """
        try:
            self.decode_token(token)
            return True
        except ValueError:
            return False

    def get_user_data(self, token: str) -> Dict[str, Any]:
        """
        从令牌中获取用户数据

        Args:
            token: JWT令牌

        Returns:
            用户数据
        """
        payload = self.decode_token(token)
        return payload.get('data', {})


# 项目特定的JWT认证实例
_jwt_auth_instance: Optional[JwtAuth] = JwtAuth(
    global_settings.jwt.secret_key,
    global_settings.jwt.algorithm,
    global_settings.jwt.issuer,
    global_settings.jwt.access_token_expire_minutes)


