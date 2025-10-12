#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MediaCrawler Sidecar Service - 入口文件

启动常驻的 MediaCrawler 边车服务

Usage:
    python sidecar_main.py
    python sidecar_main.py --port 8001 --host 0.0.0.0
"""
import sys
import argparse
from pathlib import Path

# 确保项目根目录在 Python 路径中
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="MediaCrawler Sidecar Service - 常驻爬虫服务"
    )

    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="服务绑定地址 (默认: 0.0.0.0)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="服务端口 (默认: 8001)"
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用热重载（仅开发环境）"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="日志级别 (默认: info)"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="工作进程数 (默认: 1，推荐单进程以共享浏览器池)"
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    print("=" * 60)
    print("  MediaCrawler Sidecar Service")
    print("  常驻爬虫服务 - 提供高并发爬取能力")
    print("=" * 60)
    print(f"  服务地址: http://{args.host}:{args.port}")
    print(f"  健康检查: http://{args.host}:{args.port}/health")
    print(f"  服务统计: http://{args.host}:{args.port}/stats")
    print(f"  API文档: http://{args.host}:{args.port}/docs")
    print("=" * 60)
    print()

    # 启动 Uvicorn 服务器
    import uvicorn

    uvicorn.run(
        "app.core.media_crawler_service:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
        workers=args.workers,
        access_log=True,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n服务已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n启动失败: {e}")
        sys.exit(1)
