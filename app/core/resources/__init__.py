# -*- coding: utf-8 -*-
"""
MCP Resources - 提供可访问的资源
"""
from pathlib import Path
from fastmcp import FastMCP
from app.providers.logger import get_logger
from app.config.settings import global_settings


def register_resources(app: FastMCP) -> None:
    """注册所有MCP资源"""

    # 爬取数据目录资源
    @app.resource("data://crawler_data")
    async def get_crawler_data_info() -> str:
        """
        获取爬虫数据目录信息

        返回爬取数据的存储位置和统计信息
        """
        import json
        from datetime import datetime

        data_path = Path("data")
        if not data_path.exists():
            return json.dumps({
                "status": "empty",
                "message": "数据目录不存在，尚未进行任何爬取",
                "path": str(data_path.absolute())
            }, ensure_ascii=False, indent=2)

        # 统计各平台数据（包含 json/csv 与 videos 目录体积，不做历史别名兼容）
        platform_stats = {}

        def _collect_files(p: Path):
            files = list(p.glob("*.json")) + list(p.glob("*.csv"))
            json_dir = p / "json"
            csv_dir = p / "csv"
            videos_dir = p / "videos"
            if json_dir.exists() and json_dir.is_dir():
                files += list(json_dir.glob("*.json"))
            if csv_dir.exists() and csv_dir.is_dir():
                files += list(csv_dir.glob("*.csv"))
            bin_files = []
            if videos_dir.exists() and videos_dir.is_dir():
                bin_files += [f for f in videos_dir.rglob("*") if f.is_file()]
            return files, bin_files

        for platform_dir in data_path.iterdir():
            if platform_dir.is_dir():
                files, bin_files = _collect_files(platform_dir)
                total_size = sum(f.stat().st_size for f in files if f.is_file()) + sum(
                    f.stat().st_size for f in bin_files
                )
                latest_file = "无"
                if files:
                    newest = max(files, key=lambda f: f.stat().st_mtime)
                    latest_file = newest.name

                platform_stats[platform_dir.name] = {
                    "files_count": len(files),
                    "total_size_mb": round(total_size / 1024 / 1024, 2),
                    "latest_file": latest_file,
                }

        return json.dumps({
            "status": "active",
            "data_path": str(data_path.absolute()),
            "platforms": platform_stats,
            "updated_at": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)

    # 浏览器会话数据目录资源
    @app.resource("data://browser_data")
    async def get_browser_data_info() -> str:
        """
        获取浏览器会话数据目录信息

        返回浏览器登录状态存储位置和平台登录信息
        """
        import json
        from datetime import datetime

        browser_data_path = Path("browser_data")
        if not browser_data_path.exists():
            return json.dumps({
                "status": "empty",
                "message": "浏览器数据目录不存在，尚未进行任何平台登录",
                "path": str(browser_data_path.absolute())
            }, ensure_ascii=False, indent=2)

        # 检查各平台登录状态
        platform_sessions = {}
        for session_dir in browser_data_path.iterdir():
            if session_dir.is_dir() and session_dir.name.endswith("_user_data_dir"):
                platform_code = session_dir.name.replace("_user_data_dir", "")
                # 检查是否有登录状态文件
                has_session = (session_dir / "Default").exists() or (session_dir / "Cookies").exists()

                platform_sessions[platform_code] = {
                    "has_session": has_session,
                    "path": str(session_dir),
                    "size_mb": round(sum(f.stat().st_size for f in session_dir.rglob("*") if f.is_file()) / 1024 / 1024, 2)
                }

        return json.dumps({
            "status": "active",
            "browser_data_path": str(browser_data_path.absolute()),
            "platforms": platform_sessions,
            "updated_at": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)

    # 配置文件资源
    @app.resource("config://platform_config")
    async def get_platform_config() -> str:
        """
        获取当前平台配置

        返回已启用的平台列表和配置信息
        """
        import json
        from app.config.settings import global_settings

        enabled = [p.value if hasattr(p, 'value') else str(p) for p in global_settings.platform.enabled_platforms]
        platform_names = {
            "bili": "哔哩哔哩",
            "xhs": "小红书",
            "dy": "抖音",
            "ks": "快手",
            "wb": "微博",
            "tieba": "贴吧",
            "zhihu": "知乎"
        }
        all_platforms = [
            {"code": code, "name": platform_names.get(code, code)}
            for code in [p.value for p in global_settings.platform.enabled_platforms]
        ]

        return json.dumps({
            "enabled_platforms": enabled,
            "all_platforms": all_platforms,
            "enabled_count": len(enabled),
            "total_count": len(all_platforms)
        }, ensure_ascii=False, indent=2)

    # 数据库配置资源
    @app.resource("config://database")
    async def get_database_config() -> str:
        """
        获取数据库配置信息（隐藏敏感信息）
        """
        import json

        db_host = global_settings.database.host
        db_port = str(global_settings.database.port)
        db_name = global_settings.database.database

        return json.dumps({
            "type": "PostgreSQL",
            "host": db_host,
            "port": db_port,
            "database": db_name,
            "connection_string": f"postgresql://{db_host}:{db_port}/{db_name}"
        }, ensure_ascii=False, indent=2)

    # 日志资源
    @app.resource("logs://recent")
    async def get_recent_logs() -> str:
        """
        获取最近的日志信息

        返回最近100行应用日志
        """
        log_path = Path("logs/mcp-toolse.log")
        if not log_path.exists():
            return "日志文件不存在"

        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # 返回最后100行
                recent_lines = lines[-100:] if len(lines) > 100 else lines
                return "".join(recent_lines)
        except Exception as e:
            return f"读取日志失败: {str(e)}"

    # API文档资源
    @app.resource("docs://api_endpoints")
    async def get_api_endpoints() -> str:
        """
        获取所有可用的API端点文档
        """
        import json

        # 现在使用fastmcp原生格式，直接返回已知的端点信息
        endpoints_info = [
            {
                "name": "bili_mcp",
                "category": "B站MCP",
                "prefix": "/bili",
                "tags": ["哔哩哔哩", "视频", "MCP工具"],
                "routes": [
                    {"path": "/bili/search", "methods": ["POST"], "kind": "tool"},
                    {"path": "/bili/crawler_detail", "methods": ["POST"], "kind": "tool"},
                    {"path": "/bili/crawler_creator", "methods": ["POST"], "kind": "tool"},
                    {"path": "/bili/search_time_range_http", "methods": ["POST"], "kind": "tool"},
                    {"path": "/bili/crawler_comments", "methods": ["POST"], "kind": "tool"}
                ]
            },
            {
                "name": "xhs_mcp",
                "category": "小红书MCP", 
                "prefix": "/xhs",
                "tags": ["小红书", "笔记", "MCP工具"],
                "routes": [
                    {"path": "/xhs/search", "methods": ["POST"], "kind": "tool"},
                    {"path": "/xhs/crawler_detail", "methods": ["POST"], "kind": "tool"},
                    {"path": "/xhs/crawler_creator", "methods": ["POST"], "kind": "tool"},
                    {"path": "/xhs/crawler_comments", "methods": ["POST"], "kind": "tool"}
                ]
            }
        ]

        return json.dumps(
            {
                "base_url": f"http://localhost:{global_settings.app.port}",
                "endpoints": endpoints_info,
            },
            ensure_ascii=False,
            indent=2,
        )

    # 系统状态资源
    @app.resource("status://system")
    async def get_system_status() -> str:
        """
        获取系统运行状态
        """
        import json
        import psutil
        from datetime import datetime

        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "status": "running"
        }, ensure_ascii=False, indent=2)

    # ==================== 爬取数据访问资源 ====================

    @app.resource("crawler-data://{platform}/{date}")
    async def get_platform_crawl_data(platform: str, date: str) -> str:
        """
        获取指定平台和日期的爬取数据

        参数:
        - platform: 平台代码 (xhs/dy/bili/ks/wb/tieba/zhihu)
        - date: 日期 (YYYY-MM-DD格式)

        示例:
        - crawler-data://xhs/2024-01-15
        - crawler-data://dy/2024-01-15
        """
        import json
        import glob as glob_module

        # 构建数据文件路径模式
        json_pattern = f"data/{platform}/json/*_{date}.json"
        csv_pattern = f"data/{platform}/csv/*_{date}.csv"

        json_files = glob_module.glob(json_pattern)
        csv_files = glob_module.glob(csv_pattern)

        if not json_files and not csv_files:
            return json.dumps({
                "error": f"未找到 {platform} 平台在 {date} 的爬取数据",
                "platform": platform,
                "date": date,
                "suggestion": "请检查平台代码和日期是否正确"
            }, ensure_ascii=False, indent=2)

        # 读取JSON文件数据
        all_data = []
        files_info = []

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_data.extend(data)
                    else:
                        all_data.append(data)

                    files_info.append({
                        "file": Path(json_file).name,
                        "type": "json",
                        "items": len(data) if isinstance(data, list) else 1,
                        "size_kb": round(Path(json_file).stat().st_size / 1024, 2)
                    })
            except Exception as e:
                files_info.append({
                    "file": Path(json_file).name,
                    "type": "json",
                    "error": str(e)
                })

        # CSV文件只统计不加载内容
        for csv_file in csv_files:
            files_info.append({
                "file": Path(csv_file).name,
                "type": "csv",
                "size_kb": round(Path(csv_file).stat().st_size / 1024, 2),
                "note": "CSV文件请使用专门工具打开"
            })

        platform_names = {
            "xhs": "小红书",
            "dy": "抖音",
            "bili": "B站",
            "ks": "快手",
            "wb": "微博",
            "tieba": "贴吧",
            "zhihu": "知乎"
        }

        return json.dumps({
            "platform": platform_names.get(platform, platform),
            "date": date,
            "summary": {
                "total_files": len(json_files) + len(csv_files),
                "json_files": len(json_files),
                "csv_files": len(csv_files),
                "total_items": len(all_data)
            },
            "files": files_info,
            "data": all_data[:100] if len(all_data) > 100 else all_data,  # 最多返回前100条
            "note": f"返回了前100条数据(共{len(all_data)}条)" if len(all_data) > 100 else f"返回了全部{len(all_data)}条数据"
        }, ensure_ascii=False, indent=2)

    @app.resource("crawler-data://{platform}/range/{start_date}/{end_date}")
    async def get_platform_crawl_data_range(platform: str, start_date: str, end_date: str) -> str:
        """
        获取指定平台和日期范围的爬取数据统计

        参数:
        - platform: 平台代码 (xhs/dy/bili/ks/wb/tieba/zhihu)
        - start_date: 开始日期 (YYYY-MM-DD)
        - end_date: 结束日期 (YYYY-MM-DD)

        示例:
        - crawler-data://xhs/range/2024-01-01/2024-01-07
        """
        import json
        import glob as glob_module
        from datetime import datetime, timedelta

        # 解析日期范围
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return json.dumps({
                "error": "日期格式错误，请使用 YYYY-MM-DD 格式"
            }, ensure_ascii=False, indent=2)

        stats_by_date = {}
        current = start

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            json_pattern = f"data/{platform}/json/*_{date_str}.json"
            csv_pattern = f"data/{platform}/csv/*_{date_str}.csv"

            json_files = glob_module.glob(json_pattern)
            csv_files = glob_module.glob(csv_pattern)

            if json_files or csv_files:
                total_items = 0
                for json_file in json_files:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            total_items += len(data) if isinstance(data, list) else 1
                    except:
                        pass

                stats_by_date[date_str] = {
                    "files": len(json_files) + len(csv_files),
                    "json_files": len(json_files),
                    "csv_files": len(csv_files),
                    "total_items": total_items
                }

            current += timedelta(days=1)

        platform_names = {
            "xhs": "小红书",
            "dy": "抖音",
            "bili": "B站",
            "ks": "快手",
            "wb": "微博",
            "tieba": "贴吧",
            "zhihu": "知乎"
        }

        return json.dumps({
            "platform": platform_names.get(platform, platform),
            "start_date": start_date,
            "end_date": end_date,
            "days_with_data": len(stats_by_date),
            "total_days": (end - start).days + 1,
            "stats_by_date": stats_by_date,
            "tip": "使用 crawler-data://{platform}/{date} 获取具体某天的数据"
        }, ensure_ascii=False, indent=2)

    @app.resource("crawler-data://list/{platform}")
    async def list_platform_crawl_data(platform: str) -> str:
        """
        列出指定平台的所有可用爬取数据

        参数:
        - platform: 平台代码 (xhs/dy/bili/ks/wb/tieba/zhihu)

        示例:
        - crawler-data://list/xhs
        - crawler-data://list/dy
        """
        import json
        import glob as glob_module
        from collections import defaultdict

        json_pattern = f"data/{platform}/json/*.json"
        csv_pattern = f"data/{platform}/csv/*.csv"

        json_files = glob_module.glob(json_pattern)
        csv_files = glob_module.glob(csv_pattern)

        if not json_files and not csv_files:
            return json.dumps({
                "error": f"未找到 {platform} 平台的爬取数据",
                "platform": platform,
                "suggestion": "请检查平台代码是否正确，支持: xhs, dy, bili, ks, wb, tieba, zhihu"
            }, ensure_ascii=False, indent=2)

        # 按日期分组
        dates = set()
        crawler_types = defaultdict(int)

        for file_path in json_files + csv_files:
            filename = Path(file_path).name
            # 解析文件名: crawler_type_item_type_date.ext
            parts = filename.rsplit('_', 1)
            if len(parts) == 2:
                date_with_ext = parts[1]
                date = date_with_ext.replace('.json', '').replace('.csv', '')
                dates.add(date)

                # 提取爬虫类型
                name_parts = parts[0].split('_')
                if name_parts:
                    crawler_type = name_parts[0]
                    crawler_types[crawler_type] += 1

        platform_names = {
            "xhs": "小红书",
            "dy": "抖音",
            "bili": "B站",
            "ks": "快手",
            "wb": "微博",
            "tieba": "贴吧",
            "zhihu": "知乎"
        }

        sorted_dates = sorted(list(dates), reverse=True)

        return json.dumps({
            "platform": platform_names.get(platform, platform),
            "summary": {
                "total_files": len(json_files) + len(csv_files),
                "json_files": len(json_files),
                "csv_files": len(csv_files),
                "total_dates": len(dates)
            },
            "available_dates": sorted_dates[:30],  # 只显示最近30天
            "latest_date": sorted_dates[0] if sorted_dates else None,
            "crawler_types": dict(crawler_types),
            "sample_files": [Path(f).name for f in (json_files + csv_files)[:10]],
            "tip": "使用 crawler-data://{platform}/{date} 获取具体日期的数据"
        }, ensure_ascii=False, indent=2)

    get_logger().info("✅ MCP Resources注册成功")
