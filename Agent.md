# Agent Guide — MediaCrawler MCP Service

本文件为在本仓库中协作的智能编码代理提供统一约定与上下文说明。请在进行任何实现或重构前先通读本指南。

## 1. 项目概览

- 目标：将 MediaCrawler 的能力以 MCP（Model Context Protocol）方式暴露，便于 Claude/ChatGPT 等 AI 助手直接调用。
- 技术栈：FastMCP + Starlette（SSE 集成）、Playwright、Pydantic Settings。
- 运行模式：`STDIO`、`SSE` 或两者同时（`--transport both`）。
- 已完成平台：Bilibili（4 个工具）；其它平台（xhs/dy/ks/wb/tieba/zhihu）处于规划中。

非目标（明确约束）：
- 面向个人效率的单用户/单账号使用场景。
- 不做多账号池/多租户/分布式集群等复杂特性。
- 保持架构清晰，提供可扩展点，鼓励他人自行按需扩展。

## 2. 架构总览

核心流转（高层）：
- MCP 工具调用 → Endpoint（MCP 工具注册点）→ Service（服务层）→ Crawler（Playwright 驱动的抓取逻辑）→ 数据输出到 `data/`
- SSE 与 Starlette 共用同一进程，`create_app()` 内对 FastMCP 的 `run_sse_async` 做了轻度补丁以挂载路由。

关键模块（文件路径）：
- 应用入口：`main.py`
- 应用工厂与路由挂载：`app/api_service.py`
- 端点基类与注册器：`app/api/endpoints/base.py`
- 已实现平台端点：`app/api/endpoints/mcp/bilibili.py`
- B 站服务层：`app/crawler/platforms/bilibili/service.py`
- B 站爬虫层：`app/crawler/platforms/bilibili/crawler.py`（若存在）
- 管理页与状态端点：
  - 管理页：`app/api/endpoints/admin/admin_page_endpoint.py`
  - 配置：`app/api/endpoints/admin/config_endpoint.py`
  - 状态：`app/api/endpoints/admin/status_endpoint.py`
  - 登录：`app/api/endpoints/login/login_endpoint.py`
- 配置系统：`app/config/settings.py`（Pydantic Settings，`env_nested_delimiter='__'`）
- 日志：`app/providers/logger.py`
- 缓存：`app/providers/cache/*`

SSE 集成要点：
- 见 `app/api_service.py:_patch_fastmcp_sse()`；在 `/sse` 提供 SSE，挂载 `/messages/` 与各业务路由。

## 3. 运行与开发

本地运行：
```bash
poetry install
poetry run playwright install chromium
python main.py --transport both
# 访问：
#   MCP SSE: http://localhost:9090/sse
#   管理页面: http://localhost:9090/admin
#   状态概览: http://localhost:9090/admin/api/status/summary
```

环境变量（.env，示例）：
```bash
APP__ENV=dev
APP__DEBUG=true
APP__PORT=9090
PLATFORM__ENABLED_PLATFORMS=all
BROWSER__HEADLESS=false
CRAWL__MAX_NOTES_COUNT=15
CRAWL__MAX_COMMENTS_PER_NOTE=10
STORE__SAVE_FORMAT=json
STORE__OUTPUT_DIR=./data
LOGGER__LEVEL=INFO
```

说明：
- 配置通过 Pydantic Settings 自动读取（支持双下划线嵌套）。
- 任务级参数（如 `headless`、`login_cookie`、`max_notes`）可在 MCP 工具调用时覆盖全局默认。

## 4. MCP 工具（当前状态）

服务内置工具（通用）
- `service_info` / `service_health` / `list_tools` / `tool_info`

B 站（已实现 4 个）：见 `app/api/endpoints/mcp/bilibili.py`
- `bili_search`
- `bili_detail`
- `bili_creator`
- `bili_search_time_range`

其它平台（xhs/dy/ks/wb/tieba/zhihu）：规划中。

## 5. 管理与状态

Web 管理：`http://localhost:9090/admin`（本地开发默认不鉴权，公开部署需自行加鉴权）

状态/统计 API：
- 系统资源: `GET /admin/api/status/system`
- 数据统计: `GET /admin/api/status/data`
- 服务状态: `GET /admin/api/status/services`
- 平台状态: `GET /admin/api/status/platforms`
- 概览汇总: `GET /admin/api/status/summary`

登录管理 API（B 站已接好）：
- 启动登录: `POST /admin/api/login/start`
- 登录状态: `GET /admin/api/login/status/{platform}`
- 会话状态: `GET /admin/api/login/session/{session_id}`
- 退出登录: `POST /admin/api/login/logout/{platform}`
- 会话列表: `GET /admin/api/login/sessions`

会话持久化：
- 浏览器登录态保存在 `browser_data/<platform>/`，任务会尽量复用。

## 6. 代码约定（请务必遵守）

- Endpoint 规范：
  - 继承 `BaseEndpoint`，实现 `register_routes()` 与 `register_mcp_tools()`。
  - 在 `app/api_service.py:auto_discover_endpoints()` 中注册。
  - 所有 API 均放在 `app/api/endpoints/` 统一管理。

- 日志：统一使用 `app/providers/logger.py` 的 `get_logger()`，禁止私建 logger。

- 配置：统一通过 `app/config/settings.py` 的 Pydantic Settings 读取；不要新建零散的 config 文件或全局单例。

- 缓存：如需缓存，优先使用 `app/providers/cache` 抽象层。

- 风格：遵循仓库现有 Black/isort/mypy 配置；避免一次性大改无关代码。

## 7. 扩展新平台（模板）

1) 目录与文件
```bash
mkdir app/crawler/platforms/yourplatform
touch app/crawler/platforms/yourplatform/__init__.py
touch app/crawler/platforms/yourplatform/crawler.py
touch app/crawler/platforms/yourplatform/service.py
touch app/crawler/platforms/yourplatform/client.py
```

2) Crawler：`crawler.py`
```python
from app.crawler.platforms.base import AbstractCrawler
from app.config.settings import CrawlerConfig

class YourPlatformCrawler(AbstractCrawler):
    def __init__(self, config: CrawlerConfig):
        super().__init__(config)

    async def start(self) -> dict:
        # TODO: 实现抓取逻辑
        return {"ok": True}
```

3) Service：`service.py`
```python
from app.config.settings import create_search_config, Platform
from .crawler import YourPlatformCrawler

class YourPlatformCrawlerService:
    async def search(self, keywords: str, **kwargs) -> dict:
        config = create_search_config(platform=Platform.XIAOHONGSHU, keywords=keywords, **kwargs)
        crawler = YourPlatformCrawler(config)
        try:
            return await crawler.start()
        finally:
            await crawler.close()
```

4) MCP 端点：`app/api/endpoints/mcp/yourplatform.py`
```python
from fastmcp import FastMCP
from app.api.endpoints.base import BaseEndpoint
from app.crawler.platforms.yourplatform.service import YourPlatformCrawlerService

class YourPlatformEndpoint(BaseEndpoint):
    def __init__(self):
        super().__init__(prefix="/yourplatform", tags=["你的平台"])
        self.service = YourPlatformCrawlerService()

    def register_routes(self):
        return []

    def register_mcp_tools(self, app: FastMCP):
        @app.tool(name="yourplatform_search")
        async def yourplatform_search(keywords: str) -> str:
            import json
            result = await self.service.search(keywords)
            return json.dumps(result, ensure_ascii=False)

        self._add_tool_info("yourplatform_search", "搜索你的平台内容")
```

5) 注册端点：`app/api_service.py`
```python
from app.api.endpoints.mcp import BilibiliEndpoint  # 现有
# from app.api.endpoints.mcp.yourplatform import YourPlatformEndpoint

def auto_discover_endpoints():
    # ... 启用平台判定
    # endpoint_registry.register(YourPlatformEndpoint())
    pass
```

## 8. TODO（里程碑）

平台与功能
- [ ] 小红书（xhs）服务层与端点重构（search/detail/creator）
- [ ] 抖音（dy）服务层与端点重构（search/detail/creator）
- [ ] 快手、微博、贴吧、知乎 平台适配
- [ ] 统一评论抓取策略与阈值（跨平台）

稳定性与性能
- [ ] Playwright 浏览器上下文复用与池化策略
- [ ] 限速与退避策略（按域名/平台）
- [ ] 并发调度与队列隔离（按任务/平台）

可观测性与运维
- [ ] 统一结构化日志与 trace-id 贯穿
- [ ] 指标上报（采集耗时、成功率、队列长度）
- [ ] 管理页面补充运行时统计与任务面板

配置与存储
- [ ] 环境变量与默认值核对（.env.example 同步至代码）
- [ ] 数据持久化：SQLite/PostgreSQL 写入适配层
- [ ] 数据校验与脱敏（导出前处理）

API/MCP 与体验
- [ ] 服务内置工具补充文档示例（service_info/list_tools）
- [ ] 增加错误码与统一异常响应（MCP 与 HTTP）
- [ ] 示例 Prompt 与使用范式完善

测试与发布
- [ ] 单元测试与集成测试覆盖关键路径（Bili 完整用例）
- [ ] Docker 本地运行与 CI 构建流程
- [ ] 版本化变更日志（CHANGELOG）

安全
- [ ] Cookie/会话安全存储与清理策略
- [ ] Admin UI 基础鉴权（公开部署）

## 9. 常见问题

- 首次运行请执行：`poetry run playwright install chromium`。
- 首次抓取 B 站可能需要扫码登录；登录态会保存在 `browser_data/bili/`。
- 未抓到数据：打开 `headless=false` 观察浏览器行为，或检查登录态。

## 10. 提交前自检清单

- 是否遵守 Endpoint/Service/Crawler 分层与注册规范？
- 是否使用统一的日志与配置入口？
- 是否避免引入与任务无关的大范围重构？
- README/Agent.md 中提到的开发者路径与命令是否仍然正确？

— End —

