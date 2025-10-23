# -*- coding: utf-8 -*-
"""登录服务相关异常定义。"""


class LoginServiceError(Exception):
    """登录服务异常"""


class LoginExpiredError(LoginServiceError):
    """登录过期或 Cookie 失效异常（用于 MCP 工具早返回）。"""
