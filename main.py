# -*- coding: utf-8 -*-
"""
MCP工具服务 - 支持STDIO和SSE双模式
"""

import argparse
import asyncio
import signal
import sys
from app.config.settings import global_settings
from app.api_service import create_app
from app.providers.logger import get_logger


# 全局变量存储运行中的任务
running_tasks = []
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """信号处理器 - 优雅关闭"""
    get_logger().info(f"\n收到信号 {signum}，开始优雅关闭...")
    shutdown_event.set()

    # 取消所有运行中的任务
    for task in running_tasks:
        if not task.done():
            task.cancel()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MCP工具服务")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "both"],
        default="both",
        help="传输方式: stdio(STDIO), sse(SSE), both(同时运行)"
    )

    args = parser.parse_args()

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    get_logger().info(f"🚀 启动 {global_settings.app.name} 服务...")
    get_logger().info(f"📋 版本: {global_settings.app.version}")
    get_logger().info(f"🔧 环境: {global_settings.app.env}")
    get_logger().info(f"🐛 调试模式: {global_settings.app.debug}")
    get_logger().info(f"📡 传输方式: {args.transport}")

    if args.transport in ["sse", "both"]:
        mcp_port = global_settings.app.port
        get_logger().info(f"🌐 MCP服务地址: http://0.0.0.0:{mcp_port}/sse")
        get_logger().info(f"🎛️ 管理界面地址: http://0.0.0.0:{mcp_port}/admin")

    # 创建MCP应用
    app = create_app()

    # 收集要运行的服务
    tasks = []

    # 添加MCP服务
    if args.transport == "stdio":
        tasks.append(asyncio.create_task(app.run_stdio_async()))
    elif args.transport == "sse":
        tasks.append(asyncio.create_task(app.run_sse_async()))
    elif args.transport == "both":
        get_logger().info("🚀 同时启动 STDIO 和 SSE 服务器...")
        tasks.append(asyncio.create_task(app.run_stdio_async()))
        tasks.append(asyncio.create_task(app.run_sse_async()))

    # 保存到全局变量以便信号处理器访问
    global running_tasks
    running_tasks = tasks

    try:
        # 使用 asyncio.gather 并发运行所有服务
        await asyncio.gather(*tasks, return_exceptions=False)
    except asyncio.CancelledError:
        get_logger().info("所有服务已取消")
    except KeyboardInterrupt:
        get_logger().info("收到键盘中断")
    except Exception as e:
        get_logger().error(f"服务运行出错: {e}")
        import traceback
        get_logger().error(traceback.format_exc())
    finally:
        # 清理资源
        get_logger().info("清理资源...")
        for task in tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        get_logger().info("✅ 所有服务已安全关闭")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        get_logger().info("程序退出")