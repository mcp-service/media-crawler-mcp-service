# Agent Guide — MediaCrawler MCP Service

本文件为在本仓库中协作的智能编码代理提供统一约定与上下文说明。请在进行任何实现或重构前先通读本指南。

## 1. 项目概览

**目标**：将 MediaCrawler 的能力以 MCP（Model Context Protocol）方式暴露，便于 Claude/ChatGPT 等 AI 助手直接调用。

**技术栈**：
- FastMCP + Starlette（SSE 集成）
- Playwright（浏览器自动化）
- Pydantic Settings（配置管理）
- httpx（HTTP 客户端）
- Redis（登录状态缓存）

**运行模式**：`Http-streamble`。

**已完成平台：Bilibili（生产就绪 ✅）**
- 5 个 MCP 工具（search/detail/creator/search_time_range/comments）
- 完整的登录状态管理（Redis 缓存 + 持久化 Cookie）
- 数据存储支持（JSON/CSV/SQLite/DB）
- 风控优化（登录状态缓存、请求间隔控制）

**规划中平台**：xhs/dy/ks/wb/tieba/zhihu

**非目标（明确约束）**：
- 面向个人效率的单用户/单账号使用场景
- 不做多账号池/多租户/分布式集群等复杂特性
- 保持架构清晰，提供可扩展点，鼓励他人自行按需扩展

## 2. 架构总览

### 2.1 核心流转（数据流）

```
MCP 工具调用
    ↓
MCP Tools 层 (app/core/mcp_tools/bilibili.py)
    - 参数验证与转换
    - 结果结构化（Pydantic Models）
    ↓
Service 层 (app/core/crawler/platforms/bilibili/service.py)
    - 构建 CrawlerContext（配置聚合）
    - 生命周期管理（crawler.start/close）
    - 登录状态获取（login_service）
    ↓
Crawler 层 (app/core/crawler/platforms/bilibili/crawler.py)
    - 浏览器启动与管理
    - 登录流程编排（优先缓存，避免风控）
    - 业务逻辑调度（search/detail/creator/comments）
    ↓
Client 层 (app/core/crawler/platforms/bilibili/client.py)
    - HTTP API 调用（httpx）
    - WBI 签名（Bilibili 防爬）
    - Cookie 管理与更新
    ↓
Store 层 (app/core/crawler/store/bilibili/)
    - 数据持久化（JSON/CSV/SQLite/DB）
    - 媒体文件保存
```

### 2.2 关键模块（文件路径）

**应用入口与配置**：
- 应用入口：`main.py`
- 应用工厂：`app/api_service.py`（FastMCP + Starlette 集成）
- 配置系统：`app/config/settings.py`（Pydantic Settings，`env_nested_delimiter='__'`）

**Bilibili 平台完整架构**：
```
app/core/crawler/platforms/bilibili/
├── __init__.py
├── crawler.py          # 爬虫主逻辑（搜索/详情/创作者/评论）
├── service.py          # 服务层（Context 构建与生命周期管理）
├── client.py           # HTTP 客户端（API 调用 + WBI 签名）
├── login.py            # 登录流程（QRCODE/COOKIE/PHONE）
├── field.py            # 枚举定义（SearchOrderType/CommentOrderType）
├── help.py             # 辅助函数（BilibiliSign/parse_video_info）
└── exception.py        # 异常定义（DataFetchError）

app/core/crawler/store/bilibili/
├── __init__.py
├── _store_impl.py      # 存储实现（JSON/CSV/SQLite/DB）
└── bilibilli_store_media.py  # 媒体文件存储
```

**MCP 工具与端点**：
- MCP Tools：`app/core/mcp_tools/bilibili.py`（工具函数实现）
- MCP Schemas：`app/core/mcp_tools/schemas/bilibili.py`（Pydantic 模型）
- HTTP 端点：`app/api/endpoints/mcp/bilibili.py`（路由注册 + Blueprint）
- 请求验证：`app/api/scheme/bilibili_scheme.py`（请求/响应 Schema）

**登录与状态管理**：
- 登录服务：`app/core/login/service.py`（统一登录接口）
- 登录存储：`app/core/login/storage.py`（Redis 缓存 TTL 管理）
- 登录适配器：`app/core/login/bilibili/adapter.py`（Bilibili 登录适配）
- 登录端点：`app/api/endpoints/login/login_endpoint.py`（HTTP API）

**管理页与监控**：
- 管理页：`app/api/endpoints/admin/admin_page_endpoint.py`
- 配置管理：`app/api/endpoints/admin/config_endpoint.py`
- 状态监控：`app/api/endpoints/admin/status_endpoint.py`

**基础设施**：
- 日志：`app/providers/logger.py`（统一日志入口）
- 缓存：`app/providers/cache/*`（Redis 抽象层）
- 端点基类：`app/api/endpoints/base.py`（MCPBlueprint）

### 2.3 SSE 集成要点

- 见 `app/api_service.py:_patch_fastmcp_sse()`
- 在 `/sse` 提供 SSE 端点
- 挂载 `/messages/` 与各业务路由（/bili/*, /admin/*, /login/*）

## 3. 运行与开发

### 3.1 本地运行

```bash
# 安装依赖
poetry install
poetry run playwright install chromium

# 启动服务（双传输模式）
python main.py --transport both

# 访问地址：
#   MCP SSE: http://localhost:9090/sse
#   管理页面: http://localhost:9090/admin
#   状态概览: http://localhost:9090/admin/api/status/summary
#   登录管理: http://localhost:9090/login
```

### 3.2 环境变量（.env 示例）

```bash
# 应用配置
APP__ENV=dev
APP__DEBUG=true
APP__PORT=9090

# 平台配置
PLATFORM__ENABLED_PLATFORMS=all

# 浏览器配置
BROWSER__HEADLESS=false
BROWSER__USER_AGENT=Mozilla/5.0 ...
BROWSER__VIEWPORT_WIDTH=1920
BROWSER__VIEWPORT_HEIGHT=1080

# 爬取配置
CRAWL__MAX_NOTES_COUNT=15
CRAWL__MAX_COMMENTS_PER_NOTE=10
CRAWL__MAX_CONCURRENCY=5
CRAWL__CRAWL_INTERVAL=1.0
CRAWL__SEARCH_MODE=normal
CRAWL__START_PAGE=1

# 存储配置
STORE__SAVE_FORMAT=json
STORE__OUTPUT_DIR=./data
STORE__ENABLE_SAVE_MEDIA=false

# 日志配置
LOGGER__LEVEL=INFO
LOGGER__FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# Redis 配置（登录状态缓存）
REDIS__HOST=localhost
REDIS__PORT=6379
REDIS__DB=0
```

### 3.3 配置说明

- 配置通过 Pydantic Settings 自动读取（支持双下划线嵌套）
- 任务级参数（如 `headless`、`login_cookie`、`max_notes`）可在 MCP 工具调用时覆盖全局默认
- 登录状态缓存 TTL：未登录 60s，已登录 3600s（可在 `app/core/login/storage.py` 调整）

## 5. 代码规范（约定）

### 5.1 日志格式

- 一律使用 f-string 进行字符串插值，避免使用 `%s` 占位符或逗号分隔的参数传递。
- 目的：确保日志内容与上下文直观一致，减少格式化歧义；同时保持各层日志风格统一。

正确示例：

```python
logger.info(f"[xhs.client] url={url} status={status_code}")
logger.error(f"[bili.login] Pong failed: {exc}")
logger.debug(f"[store] saved file={file_path} size={size}B")
```

错误示例（禁止）：

```python
logger.info("[xhs.client] url=%s status=%s", url, status_code)
logger.error("[bili.login] Pong failed: %s", exc)
```

### 5.2 其他建议

- 大对象或响应体仅在 debug 级别打印，避免 info 级别刷屏。
- 网络错误、风控触发（如 406/412/461/471）使用 warning/error 级别，并附加关键信息（endpoint、note_id、trace）。

## 6. UI 前端实现规则（替代旧规范）

本节为管理界面（/dashboard, /login, /config, /inspector）实现规则，替代此前所有与前端相关的说明。

- 基础框架
  - 使用 FastMCP UI 基础设施与 `app/pages/ui_base.py` 提供的样式与布局，不引入第三方前端框架（React/Vue 等）。
  - 页面以 Python 函数方式渲染（`app/pages/*.py`），统一通过 `build_page_with_nav` 输出。

- 脚本与静态资源
  - 页面逻辑脚本放在 `app/pages/js/*.js`，通过后端路由 `GET /static/js/{file}` 提供；页面内只保留少量挂载代码。
  - 统一使用 `fetch` 调用后端 `/api/*` 路由，封装 `apiRequest()` 处理 JSON、错误与重试。
  - CSP 规则由 `ui_base.py` 统一设置：允许同源脚本与少量内联初始化，不允许外链第三方脚本/字体。

- 布局与样式
  - 采用 `ui_base.py` 中的 `FASTMCP_PAGE_STYLES`，不要在页面内定义额外全局样式；必要时在 `ui_base.py` 增补通用样式。
  - 使用组件化辅助函数（`create_page_header`、`create_button_group` 等）保持一致的结构与可读性。

- 交互与可用性
  - 表单使用语义化元素与唯一 `id`，事件在 `DOMContentLoaded` 中注册，避免在标签上直接使用内联事件（少量按钮可例外）。
  - 错误与状态统一使用页面内的消息组件或 `alert` 简单提示，不引入复杂状态管理。
  - 所有配置变更通过 `/api/config/*` 路由写入 `.env`，内容、类型在后端严格校验。

- 命名与目录
  - 平台目录与代号统一：`bili`、`xhs` 等；媒体落盘路径 `data/{platform}/videos`，结构化数据存于 `json/`、`csv/`。
  - 新增页面规则：页面在 `app/pages/` 下新建渲染函数；脚本在 `app/pages/js/` 下新建同名 `*.js` 并在页面底部以 `<script src="/static/js/xxx.js"></script>` 引入。

- 质量与测试
  - UI 改动需覆盖：加载失败处理、空数据占位、慢网路体验（加载占位符）。
  - 确保与后端 schema 对齐：变更字段同时更新 JS 读写逻辑与 `/api/config/*` 的 pydantic 模型。

以上规则自本次变更起生效，用以替代此前关于前端的所有规范描述。

## 4. MCP 工具（当前状态）

### 4.1 服务内置工具（通用）

- `service_info` - 服务信息
- `service_health` - 健康检查
- `list_tools` - 工具列表
- `tool_info` - 工具详情

### 4.2 Bilibili 工具（已完成 5 个）✅

**实现位置**：
- 工具函数：`app/core/mcp_tools/bilibili.py`
- HTTP 端点：`app/api/endpoints/mcp/bilibili.py`
- 路由前缀：`/bili/*`

**工具清单**：

1. **bili_search** - 快速搜索视频
   - 路径：`POST /bili/search`
   - 参数：keywords, page_size, page_num, limit, headless, save_media
   - 返回：简化结构（BilibiliVideoSimple）
   - 特点：使用 aid 作为 video_id，方便后续调用详情

2. **bili_detail** - 获取视频详情
   - 路径：`POST /bili/detail`
   - 参数：video_ids (List[str]), headless, save_media
   - 返回：完整结构（BilibiliVideoFull）
   - 包含字段：
     - 基础信息：title/desc/duration/video_url/cover_url
     - 分区信息：tname/tid
     - 视频属性：copyright/cid
     - UP主信息：user_id/nickname/avatar/sex/sign/level/fans/official_verify
     - 统计数据：play_count/liked_count/disliked_count/comment/coin/share/favorite/danmaku
     - **标签**：tags (List[{tag_id, tag_name}])

3. **bili_creator** - 获取 UP 主视频
   - 路径：`POST /bili/creator`
   - 参数：creator_ids (List[str]), creator_mode, headless, save_media
   - creator_mode=True：获取UP主所有视频
   - creator_mode=False：获取UP主详情（粉丝/关注/动态）

4. **bili_search_time_range** - 时间范围搜索
   - 路径：`POST /bili/search/time-range`
   - 参数：keywords, start_day, end_day, page_size, page_num, limit, max_notes_per_day, daily_limit, headless, save_media
   - daily_limit=True：限制每天爬取数量
   - daily_limit=False：全量爬取（仅受 limit 约束）

5. **bili_comments** - 抓取视频评论
   - 路径：`POST /bili/comments`
   - 参数：video_ids (List[str]), max_comments, fetch_sub_comments, headless
   - fetch_sub_comments=True：递归抓取子评论
   - 返回：{"comments": {video_id: [comment_list]}}

### 4.3 其它平台（规划中）

- xhs（小红书）
- dy（抖音）
- ks（快手）
- wb（微博）
- tieba（贴吧）
- zhihu（知乎）

## 5. 管理与状态

### 5.1 Web 管理界面

访问地址：`http://localhost:9090/admin`

**功能**：
- 配置查看与管理
- 系统资源监控
- 数据统计概览
- 平台状态检查

**注意**：本地开发默认不鉴权，公开部署需自行加鉴权。

### 5.2 状态/统计 API

- 系统资源：`GET /admin/api/status/system`（CPU/内存/磁盘）
- 数据统计：`GET /admin/api/status/data`（爬取数量/存储大小）
- 服务状态：`GET /admin/api/status/services`（Playwright/Redis/数据库）
- 平台状态：`GET /admin/api/status/platforms`（各平台工具状态）
- 概览汇总：`GET /admin/api/status/summary`（所有状态聚合）

### 5.3 登录管理 API（Bilibili 已接入）

- 启动登录：`POST /admin/api/login/start`
  - 参数：platform, login_type (QRCODE/COOKIE/PHONE)
  - 返回：session_id, qr_url (QRCODE 模式)
- 登录状态：`GET /admin/api/login/status/{platform}`
  - 返回：is_logged_in, user_info, cache_ttl
- 会话状态：`GET /admin/api/login/session/{session_id}`
  - 返回：status, qr_url, user_info
- 退出登录：`POST /admin/api/login/logout/{platform}`
  - 清除 Redis 缓存与浏览器持久化状态
- 会话列表：`GET /admin/api/login/sessions`
  - 返回所有活跃登录会话

### 5.4 会话持久化

- **浏览器状态**：保存在 `browser_data/<platform>/`（Playwright persistent context）
- **Redis 缓存**：登录状态缓存（TTL：未登录 60s，已登录 3600s）
- **优势**：
  - 避免频繁调用 `pong()` 触发风控
  - 重启服务后自动恢复登录状态
  - 支持跨进程共享（通过 Redis）

## 6. 代码约定（请务必遵守）

### 6.1 架构分层（严格遵守）

```
MCP Tools 层 (app/core/mcp_tools/)
    - 职责：参数验证、结果结构化、错误处理
    - 原则：薄封装，不包含业务逻辑
    ↓
Service 层 (app/core/crawler/platforms/{platform}/service.py)
    - 职责：Context 构建、生命周期管理、登录状态获取
    - 原则：协调者角色，不直接操作浏览器
    ↓
Crawler 层 (app/core/crawler/platforms/{platform}/crawler.py)
    - 职责：浏览器管理、业务逻辑编排、数据提取
    - 原则：核心业务逻辑所在，调用 Client 和 Store
    ↓
Client 层 (app/core/crawler/platforms/{platform}/client.py)
    - 职责：HTTP API 调用、签名计算、Cookie 管理
    - 原则：纯 HTTP 客户端，不依赖浏览器
    ↓
Store 层 (app/core/crawler/store/{platform}/)
    - 职责：数据持久化、媒体文件保存
    - 原则：可插拔存储实现（JSON/CSV/SQLite/DB）
```

### 6.2 端点规范

- 使用 `MCPBlueprint`（继承自 FastMCP 的 Blueprint）
- 在 `app/api/endpoints/mcp/{platform}.py` 中注册
- 通过 `bp.tool()` 装饰器绑定 MCP 工具与 HTTP 路由
- 在 `app/api_service.py:auto_discover_endpoints()` 中自动发现并注册

**示例**：
```python
from app.api.endpoints.base import MCPBlueprint
from app.core.mcp_tools import bilibili as bili_tools

bp = MCPBlueprint(prefix="/bili", name="bilibili", tags=["bili"])

bp.tool(
    "bili_search",
    description="搜索 Bilibili 视频",
    http_path="/search",
    http_methods=["POST"],
)(bili_tools.bili_search)
```

### 6.3 日志规范

- 统一使用 `app/providers/logger.py` 的 `get_logger()`，禁止私建 logger
- 日志格式：`[ClassName.method_name] message`
- 重要操作必须记录日志（登录/API调用/错误）

### 6.4 配置规范

- 统一通过 `app/config/settings.py` 的 Pydantic Settings 读取
- 不要新建零散的 config 文件或全局单例
- 环境变量支持双下划线嵌套（如 `CRAWL__MAX_NOTES_COUNT`）

### 6.5 缓存规范

- 如需缓存，优先使用 `app/providers/cache` 抽象层
- 登录状态缓存示例：`app/core/login/storage.py`

### 6.6 代码风格

- 遵循仓库现有 Black/isort/mypy 配置
- 避免一次性大改无关代码
- 类型注解：所有公共函数必须提供类型注解

## 7. 扩展新平台（模板）

目标：快速为一个新平台接入登录、抓取、MCP 工具与数据落盘，保持目录与命名统一，稳定与质量优先。

1) 注册平台枚举
- 文件：`app/config/settings.py`
- 在 `class Platform(str, Enum)` 中新增平台代号（小写，作为目录名与端点前缀），如：`YOUR = "your"`

2) 目录与最小骨架
```bash
# Crawler 实现
mkdir -p app/core/crawler/platforms/your
touch app/core/crawler/platforms/your/__init__.py
touch app/core/crawler/platforms/your/crawler.py       # 爬虫主流程（search/detail/creator/comments）
touch app/core/crawler/platforms/your/client.py        # HTTP/页面抓取客户端（httpx/Playwright）
touch app/core/crawler/platforms/your/service.py       # 编排与上下文聚合
# 可选：登录与枚举/异常
touch app/core/crawler/platforms/your/field.py         # 枚举与常量（可选）
touch app/core/crawler/platforms/your/exception.py     # 领域异常（可选）
mkdir -p app/core/login/your && touch app/core/login/your/login.py   # 登录适配（可选）

# 请求模型
touch app/api/scheme/request/your_scheme.py

# MCP 工具实现与端点注册
touch app/core/mcp/your.py
touch app/api/endpoints/mcp/your.py
```

3) Crawler：`app/core/crawler/platforms/your/crawler.py`
```python
from __future__ import annotations
from typing import Any, Dict, List, Optional
from app.providers.logger import get_logger
from app.config.settings import global_settings

logger = get_logger()

class YourCrawler:
    def __init__(self, headless: Optional[bool] = None, **kwargs):
        browser_cfg = global_settings.browser
        self.headless = browser_cfg.headless if headless is None else headless
        # 其他选项按需透传（如 proxy/user_agent 等，由服务层决定是否开启）

    async def search(self, keywords: str, page_num: int = 1, page_size: int = 20) -> Dict:
        logger.info(f"[your.crawler.search] keywords={keywords}")
        # TODO: 实现页面/API 抓取
        return {"items": [], "page_num": page_num, "page_size": page_size}

    async def get_detail(self, ids: List[str]) -> Dict:
        logger.info(f"[your.crawler.detail] ids={len(ids)}")
        return {"items": []}

    async def get_creator(self, creator_ids: List[str], page_num: int = 1, page_size: int = 30) -> Dict:
        logger.info(f"[your.crawler.creator] creators={len(creator_ids)}")
        return {"items": []}

    async def fetch_comments(self, ids: List[str], max_comments: int = 50) -> Dict:
        logger.info(f"[your.crawler.comments] ids={len(ids)} max={max_comments}")
        return {"comments": {}}
```

4) Service：`app/core/crawler/platforms/your/service.py`
```python
from __future__ import annotations
from typing import Dict, List
from app.config.settings import global_settings
from .crawler import YourCrawler

class YourService:
    async def search(self, keywords: str, page_num: int = 1, page_size: int = 20) -> Dict:
        crawler = YourCrawler(headless=global_settings.browser.headless)
        return await crawler.search(keywords, page_num=page_num, page_size=page_size)

    async def detail(self, ids: List[str]) -> Dict:
        crawler = YourCrawler(headless=global_settings.browser.headless)
        return await crawler.get_detail(ids)

    async def creator(self, creator_ids: List[str], page_num: int = 1, page_size: int = 30) -> Dict:
        crawler = YourCrawler(headless=global_settings.browser.headless)
        return await crawler.get_creator(creator_ids, page_num=page_num, page_size=page_size)

    async def comments(self, ids: List[str], max_comments: int = 50) -> Dict:
        crawler = YourCrawler(headless=global_settings.browser.headless)
        return await crawler.fetch_comments(ids, max_comments=max_comments)
```

5) 请求模型：`app/api/scheme/request/your_scheme.py`
```python
from pydantic import BaseModel, ConfigDict, Field

class YourSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keywords: str = Field(..., min_length=1)
    page_num: int = 1
    page_size: int = 20

    def to_service_params(self) -> dict:
        return self.model_dump()
```

6) MCP 工具：`app/core/mcp/your.py`
```python
from __future__ import annotations
from typing import Dict, List
from app.core.crawler.platforms.your.service import YourService

svc = YourService()

async def your_search(keywords: str, page_num: int = 1, page_size: int = 20) -> Dict:
    """返回简化结构：适合 AI 处理的扁平字段"""
    return await svc.search(keywords, page_num=page_num, page_size=page_size)
```

7) MCP 端点：`app/api/endpoints/mcp/your.py`
```python
from __future__ import annotations
from fastmcp import FastMCP
from pydantic import ValidationError
from app.api.scheme import error_codes
from app.api.scheme.request.your_scheme import YourSearchRequest
from app.core.mcp import your as your_tools
from app.providers.logger import get_logger

logger = get_logger()
your_mcp = FastMCP(name="Your MCP")

@your_mcp.tool(name="search", description="搜索 Your 平台")
async def search(keywords: str, page_num: int = 1, page_size: int = 20):
    try:
        req = YourSearchRequest.model_validate({
            "keywords": keywords, "page_num": page_num, "page_size": page_size
        })
    except ValidationError as exc:
        return {"code": error_codes.PARAM_ERROR[0], "msg": error_codes.PARAM_ERROR[1], "data": {"errors": exc.errors()}}

    result = await your_tools.your_search(**req.to_service_params())
    return {"code": error_codes.SUCCESS[0], "msg": error_codes.SUCCESS[1], "data": result}

__all__ = ["your_mcp"]
```

8) 挂载子服务：`app/api_service.py`
```python
from app.api.endpoints import main_app, bili_mcp, xhs_mcp
from app.api.endpoints.mcp.your import your_mcp

async def setup_servers():
    await main_app.import_server(xhs_mcp, 'xhs')
    await main_app.import_server(bili_mcp, 'bili')
    await main_app.import_server(your_mcp, 'your')
```

9) 数据落盘（可选）
- 复用 `app/core/crawler/tools/async_file_writer.py`：目录固定为 `data/{platform}/{json|csv|videos}`
- 存储格式由 `STORE__SAVE_FORMAT` 控制（json/csv/sqlite/db），平台代号必须与 `Platform` 枚举一致（如 `your`）

10) UI/管理联动（可选）
- 如需在“平台会话面板”展示中文名，更新以下映射表：
  - `app/api/endpoints/admin/status_endpoint.py` → `platform_names`
  - `app/api/endpoints/admin/config_endpoint.py` → `platform_names`
  - `app/core/resources/__init__.py`（资源展示）
- MCP Inspector 会自动读取主应用工具清单，无需额外前端改动。

11) 验收清单
- 工具可在 `/inspector` 正常调用：search → detail → comments 流程链打通
- `.env` 未新增无效项；数据落盘目录为 `data/your/*`
- 日志可读（抓取/错误/风控告警），失败路径给出明确提示

## 8. 问题排查黄金法则（稳定与质量优先）

- 三问法（必做）
  - 数据从哪来：上游 API/页面返回哪些字段？结构是什么？
  - 数据要到哪去：下游工具/存储需要哪些字段？结构是什么？
  - 代码怎么走：工具 → 请求模型 → 服务 → 爬虫 → 客户端 → 存储 各环节如何处理？

- 端到端自查清单
  - 工具可见性：`GET /api/mcp/data` 能看到你的平台工具；`/inspector` 可调用。
  - 登录状态：`/login` 已登录；`GET /api/status/platforms` 显示 is_logged_in=true。
  - 服务健康：`GET /api/status/services`、`GET /api/status/system` 正常。
  - 数据落盘：`/api/status/data` 有统计，且生成 `data/{platform}/{json|csv|videos}`。
  - 日志：查看 `logs/mcp-toolse.log`（资源 `logs://recent`）是否记录抓取/错误关键信息。

- 常见错误归因
  - 参数错误：`code=50001(PARAM_ERROR)` → 对照 `app/api/scheme/request/{platform}_scheme.py` 修正必填项/类型。
  - 登录失效：`code=401(INVALID_TOKEN)` 或平台 412/461/471 → 在 `/login` 重新登录并复用会话；避免高频 `pong`。
  - 路由不存在：404/405 → 检查 `app/api/endpoints/mcp/{platform}.py` 是否存在，并在 `app/api_service.py` 通过 `import_server(..., '{code}')` 挂载。
  - 空数据：`code=50004(NOT_DATA)` 或 items 为空 → 优先核对关键词/时间段与上游 DOM/接口是否改版。

- 最小复现路径
  1) `/login` 登录 → 2) `/inspector` 跑 `search` → 3) 取 ID 跑 `detail` → 4) 跑 `comments` → 5) 看 `/status/data` 与日志。

- 日志与级别
  - 重要步骤 `info`，网络/风控异常 `warning/error`，附 endpoint、note_id、trace。
  - 大响应体仅在 debug 打印，避免 info 刷屏。

## 9. 项目数据流注意事项（按现行架构）

- 标准数据流
  工具（`app/core/mcp/{platform}.py`）
  → 请求校验（`app/api/scheme/request/{platform}_scheme.py`）
  → 服务（`service.py`）
  → 爬虫（`crawler.py`）
  → 客户端（`client.py`）
  → 存储（AsyncFileWriter/DB）
  → 扁平化 JSON 返回。

- 参数与默认值
  - 工具入参 → pydantic 校验 → `to_service_params()` 标准化。
  - 服务层创建爬虫，默认读取 `global_settings.browser.headless` 等；必要时在端点层做字段映射（如 `enable_save_media → save_media`）。

- 存储与目录
  - 目录：`data/{platform}/{json|csv|videos}`，平台代号与 `Platform` 枚举一致（如 `bili`、`xhs`）。
  - 文件：`{crawler_type}_{item_type}_{YYYY-MM-DD}.{json|csv}`；“数据持久化概览”会统计 json/csv 与 videos 体积。

- 平台特定要点
  - Bilibili：search 返回 `aid`；下游 detail/评论使用 `aid` 作为 video_id（不要用 bvid）。
  - 小红书：detail/comments 必须提供 `xsec_token`（可从搜索结果或分享链接解析）。

- 稳定性建议
  - 最小化请求规模与页面跳转；复用持久化会话（Playwright persistent context）。
  - DOM/接口变更优先在 `client.py` 与解析模块修复；保证工具层输出字段稳定、扁平，必要字段标可选。

## 10. 提交前自检清单

- 是否遵守 Endpoint/Service/Crawler 分层与注册规范？
- 是否使用统一的日志与配置入口？
- 是否避免引入与任务无关的大范围重构？
- README/Agent.md 中提到的开发者路径与命令是否仍然正确？

— End —
