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

### 问题排查黄金法则

**遇到数据流问题时，永远先问这三个问题：**

1. **数据从哪来？** - 上游API返回了什么字段？什么格式？
2. **数据要到哪去？** - 下游API需要什么参数？什么格式？
3. **原始实现怎么做的？** - MediaCrawler源码是如何处理这个流程的？

**反面教材（避免）：**
- ❌ 过早陷入技术细节（WBI签名、Cookie认证等）
- ❌ 基于假设猜测问题（"可能是XX"而不是验证）
- ❌ 忽略用户提供的关键信息（URL参数、错误日志等）

**正确方法（推荐）：**
1. ✅ **先画数据流图**：`search API → video_id → detail API`，标注每个环节的输入输出
2. ✅ **对比原始代码**：第一时间查看MediaCrawler如何实现相同功能
3. ✅ **端到端验证**：从源头（API响应）到终点（用户收到的数据）追踪每一步转换
4. ✅ **提取用户反馈中的硬证据**：URL参数、日志片段、实际响应数据

### B站爬虫特定注意事项

**视频ID的两种格式（关键）：**
- `aid`（数字ID）：detail API必需参数，如 `aid=1504494553`
- `bvid`（BV号）：前端URL使用，如 `BV1Dr421q7YD`

**数据流正确实现：**
```
search API 返回: {"result": [{"aid": 123, "bvid": "BV1xxx"}]}
                      ↓
              提取 aid 作为 video_id
                      ↓
detail API 调用: get_video_info(aid=123)  ← 注意：必须用aid，不能用bvid
                      ↓
            返回嵌套结构: {"View": {...}, "Card": {...}}
                      ↓
           转换为扁平格式返回给用户
```

**常见错误模式：**
- 搜索返回`bvid`直接作为`video_id` → detail API失败（"啥都木有"）
- detail API返回原始嵌套结构 → 用户收到空响应或难以使用
- 频繁调用`pong()`检查登录状态 → 触发风控

**正确处理方式：**
- 搜索时：返回`aid`作为`video_id`，同时保留`bvid`字段供参考
- 详情时：使用`aid`调用API，返回前转换为扁平格式
- 登录检查：优先使用缓存状态（TTL 60s未登录/3600s已登录），避免频繁pong

### 登录状态管理最佳实践

#### 1.浏览器实例管理规范（重要 ⚠️）

**问题背景**：
- 多平台（Bilibili、小红书等）共享浏览器实例会导致状态混乱
- 频繁创建/销毁浏览器实例会影响性能
- 登录状态需要在浏览器上下文中持久化

**解决方案：BrowserManager 统一管理**

所有涉及浏览器操作的模块（Login、Crawler）必须通过 `BrowserManager` 获取浏览器实例：

**使用规范**：

1. **获取浏览器上下文（Login/Crawler）**：
2. **释放浏览器上下文**：
3. **强制清理（仅在 logout 时）**：
4. **临时上下文（状态检查）**：


**关键原则**：
- ✅ 每个平台使用独立的浏览器实例（通过 `platform` 参数区分）
- ✅ 同一平台的 Login 和 Crawler 共享浏览器实例（减少资源占用）
- ✅ 使用 `keep_alive=True` 保持实例存活，避免频繁创建/销毁
- ✅ BrowserManager 内部使用互斥锁，防止并发创建多个实例
- ❌ 禁止在 Login/Crawler 模块中直接使用 `async_playwright()`
- ❌ 禁止手动 `close()` 或 `stop()` 由 BrowserManager 管理的实例

**实现位置**：
- 浏览器管理器：`app/core/login/browser_manager.py`
- Bilibili Login：`app/core/login/bilibili/login.py:456-464`
- Bilibili Crawler：`app/core/crawler/platforms/bilibili/crawler.py:105-111`
- XHS Login：`app/core/login/xhs/login.py:155-161`
- XHS Crawler：`app/core/crawler/platforms/xhs/crawler.py:69-75`

#### 2.登录防抖机制

**问题背景**：
- 用户可能在短时间内多次点击登录按钮
- 多个登录请求同时进行会导致浏览器资源竞争
- 登录会话状态混乱

**解决方案：平台级登录锁**

`LoginService` 为每个平台维护一个登录锁，防止同一平台重复登录：

**关键点**：
- ✅ 同一平台同一时间只能有一个登录流程在进行
- ✅ 如果检测到正在进行的登录，返回友好提示而不是报错
- ✅ 锁会在登录完成（成功/失败）后自动释放

**实现位置**：`app/core/login/service.py:38-40, 44-49, 97-170`

#### 3. 二维码登录规范（重要 ⚠️）

**问题背景**：
- 二维码登录时，如果检测到已有登录状态就直接返回，导致没有生成二维码
- 二维码图片可能没有完全加载就被读取，导致返回空图片
- 内部阻塞等待扫码会导致接口超时，应该使用异步轮询

**核心原则：症状优先，数据格式优先**

当遇到二维码相关问题时，应该：
1. ✅ **优先检查用户症状**：
   - "空图片" + "长度: 6294" → 数据已获取，格式处理有问题
   - "二维码不显示" + 无日志 → 元素未找到或加载超时
   - "立即登录成功" + 未扫码 → 状态验证逻辑错误

2. ✅ **优先检查数据格式**：
   ```python
   # 二维码数据的三种格式
   # 1. HTTP URL: "https://example.com/qrcode.png"
   # 2. Data URL: "data:image/png;base64,iVBORw0KG..."
   # 3. Pure base64: "iVBORw0KGgoAAAANSUhEUg..."

   # 前端需要的是纯 base64，不包含任何前缀
   ```

3. ✅ **对比不同平台实现**：
   - Bilibili: `qrcode_element.screenshot()` → 直接返回 base64
   - 小红书: `img.getAttribute("src")` → 可能是 data URL，需要提取

**常见问题与解决方案**：

**问题 1：二维码显示为空图片**

```python
# 错误实现 ❌
async def find_login_qrcode(page, selector):
    element = await page.wait_for_selector(selector)
    src = await element.get_property("src")
    return src  # 直接返回 data:image/png;base64,xxx 导致前端无法显示

# 正确实现 ✅
async def find_login_qrcode(page, selector):
    element = await page.wait_for_selector(selector)
    src = await element.get_property("src")

    # 处理 HTTP URL
    if src.startswith("http"):
        response = await fetch(src)
        return base64.b64encode(response.content).decode()

    # 处理 data URL（关键！）
    if src.startswith("data:image"):
        # 提取纯 base64 部分
        return src.split(",", 1)[1]

    # 已经是纯 base64
    return src
```

**问题 2：未登录却显示已登录**

```python
# 错误实现 ❌
async def has_valid_cookie(self):
    cookies = await self.browser_context.cookies()
    cookie_dict = {c["name"]: c["value"] for c in cookies}
    # 仅检查 Cookie 存在，不验证有效性
    return bool(cookie_dict.get("web_session"))

# 正确实现 ✅
async def has_valid_cookie(self):
    cookies = await self.browser_context.cookies()
    cookie_dict = {c["name"]: c["value"] for c in cookies}

    if not cookie_dict.get("web_session"):
        return False

    # 调用 API 验证 Cookie 是否真正有效
    try:
        client = self._build_client(cookie_dict)
        return await client.pong()  # 真正的登录验证
    except Exception:
        return False
```

**问题 3：二维码轮询立即成功（未扫码）**

```python
# 错误实现 ❌
async def _poll_qrcode():
    while True:
        # 只检查 Cookie 存在
        if await login_obj.has_valid_cookie():
            await _save_login_success()
            break

# 正确实现 ✅
async def _poll_qrcode():
    # 记录轮询开始前的 session
    cookies_before = await browser_context.cookies()
    before_session = cookie_dict_before.get("web_session")

    while True:
        cookies_current = await browser_context.cookies()
        current_session = cookie_dict_current.get("web_session")

        # 检查 session 是否发生变化（而不仅仅是存在）
        if current_session and current_session != before_session:
            await _save_login_success()
            break
```

**问题排查优先级（黄金法则）**：

遇到登录问题时，按此顺序排查：

1. **用户症状分析**（30秒）
   - 空图片 → 数据格式问题
   - 无二维码 → 元素选择器或加载超时
   - 立即成功 → 状态验证逻辑错误

2. **日志关键信息**（1分钟）
   - "长度: 6294" → 数据已获取，检查格式处理
   - "wait_for_selector timeout" → 选择器错误或页面未加载
   - "登录状态变化: None -> xxx" → 正常流程

3. **数据格式验证**（2分钟）
   - 在 `find_login_qrcode()` 添加日志：`logger.info(f"src[:100] = {src[:100]}")`
   - 检查是否是 data URL、HTTP URL 还是纯 base64

4. **对比平台实现**（3分钟）
   - Bilibili 怎么处理的？
   - MediaCrawler 源码怎么处理的？

5. **最后才看流程**（避免过早陷入）
   - 登录流程编排
   - 轮询逻辑
   - 会话管理

**反面教材（避免）**：
- ❌ 一开始就阅读整个登录流程（数百行代码）
- ❌ 过早关注技术细节（async/await、锁机制等）
- ❌ 忽略日志中的数字线索（"长度: 6294" 说明数据存在）
- ❌ 基于假设猜测（"可能是加载慢"而不是验证）

**核心要点总结**：

1. **跳过已登录状态检查（二维码登录专用）**：
   ```python
   if not cookie_candidate and payload.login_type != "qrcode":
       # 只有非二维码登录才检查现有状态
       current_state = await service.refresh_platform_state(...)
   ```

2. **等待二维码完全加载**：
   ```python
   await self.context_page.wait_for_selector(selector, timeout=10000)
   await asyncio.sleep(1)  # 确保图片完全加载
   ```

3. **处理不同二维码格式**：
   ```python
   if src.startswith("data:image"):
       return src.split(",", 1)[1]  # 提取纯 base64
   ```

4. **使用异步轮询，检测 session 变化**：
   ```python
   before_session = cookie_dict_before.get("web_session")
   # 轮询时检查 session 是否变化
   if current_session and current_session != before_session:
       await _save_login_success()
   ```

5. **验证登录状态要调用 API**：
   ```python
   async def has_valid_cookie(self):
       if not cookie_dict.get("web_session"):
           return False
       # 真正验证，而不是仅检查 Cookie 存在
       return await client.pong()
   ```

**实现位置**：
- 二维码格式处理：`app/core/crawler/tools/crawler_util.py:34-69`
- 登录状态验证：`app/core/login/xhs/login.py:132-169`
- 二维码轮询逻辑：`app/core/login/xhs/login.py:280-352`
- Bilibili 参考实现：`app/core/login/bilibili/login.py:438, 582-638`


## 10. 提交前自检清单

- 是否遵守 Endpoint/Service/Crawler 分层与注册规范？
- 是否使用统一的日志与配置入口？
- 是否避免引入与任务无关的大范围重构？
- README/Agent.md 中提到的开发者路径与命令是否仍然正确？

— End —
