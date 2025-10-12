# -*- coding: utf-8 -*-
"""
日志模块
"""

import sys
import os
from pathlib import Path
from typing import Optional
from loguru import logger


class Logger:
    """简化的日志器"""
    
    def __init__(self, 
                 name: str = "mcp-toolse",
                 level: str = "INFO",
                 log_file: Optional[str] = None,
                 enable_file: bool = False,
                 enable_console: bool = True,
                 max_file_size: str = "10 MB",
                 retention_days: int = 7):
        """
        初始化日志器
        
        Args:
            name: 日志器名称
            level: 日志级别
            log_file: 日志文件路径
            enable_file: 是否启用文件日志
            enable_console: 是否启用控制台输出
            max_file_size: 最大文件大小
            retention_days: 日志保留天数
        """
        self.name = name
        self.level = level
        self.log_file = log_file
        self.enable_file = enable_file
        self.enable_console = enable_console
        self.max_file_size = max_file_size
        self.retention_days = retention_days
        
        # 移除默认处理器
        logger.remove()
        
        # 配置日志格式
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        
        # 添加控制台输出
        if self.enable_console:
            logger.add(
                sys.stdout,
                format=log_format,
                level=self.level,
                colorize=True
            )
        
        # 添加文件输出（仅在启用文件日志且有文件路径时）
        if self.enable_file and self.log_file:
            # 确保日志目录存在
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.add(
                self.log_file,
                format=log_format,
                level=self.level,
                rotation=self.max_file_size,
                retention=f"{self.retention_days} days",
                compression="zip",
                encoding="utf-8"
            )
    
    def get_logger(self):
        """获取logger实例"""
        return logger
    
    def info(self, message: str):
        """信息日志"""
        logger.info(message)
    
    def debug(self, message: str):
        """调试日志"""
        logger.debug(message)
    
    def warning(self, message: str):
        """警告日志"""
        logger.warning(message)
    
    def error(self, message: str):
        """错误日志"""
        logger.error(message)
    
    def critical(self, message: str):
        """严重错误日志"""
        logger.critical(message)


# 全局日志器实例
_logger_instance: Optional[Logger] = None


def init_logger(name: str = "mcp-toolse",
                level: str = "INFO",
                log_file: Optional[str] = None,
                enable_file: bool = False,
                enable_console: bool = True,
                max_file_size: str = "10 MB",
                retention_days: int = 7) -> Logger:
    """
    初始化全局日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径
        enable_file: 是否启用文件日志
        enable_console: 是否启用控制台输出
        max_file_size: 最大文件大小
        retention_days: 日志保留天数
        
    Returns:
        Logger实例
    """
    global _logger_instance
    _logger_instance = Logger(
        name=name,
        level=level,
        log_file=log_file,
        enable_file=enable_file,
        enable_console=enable_console,
        max_file_size=max_file_size,
        retention_days=retention_days
    )
    return _logger_instance


def get_logger():
    """
    获取全局日志器实例
    
    Returns:
        loguru logger实例
    """
    global _logger_instance
    if _logger_instance is None:
        # 使用默认配置初始化
        _logger_instance = Logger()
    return logger


# 便捷函数
def info(message: str):
    """信息日志"""
    logger.info(message)


def debug(message: str):
    """调试日志"""
    logger.debug(message)


def warning(message: str):
    """警告日志"""
    logger.warning(message)


def error(message: str):
    """错误日志"""
    logger.error(message)


def critical(message: str):
    """严重错误日志"""
    logger.critical(message)
