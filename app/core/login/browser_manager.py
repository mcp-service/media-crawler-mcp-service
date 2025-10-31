# -*- coding: utf-8 -*-
"""
浏览器实例管理器
使用新的浏览器池系统
"""
from __future__ import annotations

from app.core.browser_manager import BrowserManager, get_browser_manager

# 导出统一的浏览器管理器
__all__ = ["BrowserManager", "get_browser_manager"]


def get_browser_manager() -> BrowserManager:
    """获取全局浏览器管理器实例"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager


__all__ = ["BrowserManager", "get_browser_manager"]
