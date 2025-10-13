# MediaCrawler MCP 智能爬虫服务

基于 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 的 **企业级 AI 社交媒体爬虫服务**，通过 MCP (Model Context Protocol) 协议为 Claude、ChatGPT 等 AI 助手提供强大的社交媒体数据采集能力。

## 🎯 项目概述

本项目将 MediaCrawler 从 **CLI 命令行工具** 重构为 **AI 可调用的 MCP 服务**，通过配置分离实现灵活、安全的爬虫能力。

### ✨ 核心亮点

#### 🎯 从 CLI 到 MCP 服务

**原始 MediaCrawler 的问题：**
```bash
# ❌ 原始方式：命令行运行，需要手动编辑 config.py
python main.py --platform xhs --keywords "AI绘画" --type search

# 问题：
# 1. AI 无法直接调用（需要 shell 命令）
# 2. 全局 config.py 文件，多任务互相覆盖
# 3. 每次爬取需要重启浏览器，耗时 5-10 秒
# 4. 没有 API 接口，无法集成
```

**本项目的方案：MCP 协议化**
```python
# ✅ 新方式：AI 直接调用 MCP 工具
# AI 助手自动调用：
bili_search(keywords="AI绘画", max_notes=20, headless=True)

# 优势：
# 1. AI 原生支持（Claude、ChatGPT 直接调用）
# 2. 参数化配置，每个任务独立
# 3. 服务常驻，浏览器复用
# 4. 标准 MCP 协议，通用集成
```

#### ⚙️ 配置分离与参数化

**核心创新：从全局配置到参数化配置**

**原始架构的致命问题：**
```python
# ❌ MediaCrawler 原始方式：全局单例 config
# config.py
PLATFORM = "xhs"  # 全局变量
KEYWORDS = "AI绘画"

# 并发场景崩溃：
# 任务A: config.PLATFORM = "xhs", config.KEYWORDS = "AI"
# 任务B: config.PLATFORM = "bili", config.KEYWORDS = "Python"
# 结果：任务A 读到了 PLATFORM="bili", KEYWORDS="Python" ❌
```

**本项目方案：Pydantic 参数化配置**
```python
# ✅ 新方式：每个任务独立配置对象
config_a = create_search_config(platform="xhs", keywords="AI")
config_b = create_search_config(platform="bili", keywords="Python")

crawler_a = XHSCrawler(config_a)  # 独立配置
crawler_b = BilibiliCrawler(config_b)  # 独立配置

# 并发安全：任务A 和 任务B 互不干扰 ✅
```

### 📊 架构对比

| 维度 | MediaCrawler 原始 | 本项目（MCP 服务） |
|------|-----------------|-----------------|
| **调用方式** | CLI 命令行 | MCP 工具（AI 原生支持） |
| **配置管理** | 全局 config.py 文件 | Pydantic 参数化对象 |
| **并发安全** | ❌ 全局变量竞争 | ✅ 独立配置上下文 |
| **浏览器管理** | 每次启动（5-10秒） | 服务常驻，实例复用 |
| **集成方式** | 无（只能命令行） | 标准 MCP 协议 |
| **AI 可用性** | ❌ 需包装 shell | ✅ 直接调用工具 |
| **扩展性** | 修改 config.py | 继承 BaseService |
| **代码质量** | 脚本风格 | 企业级架构（Service + Endpoint）|

### 🎯 核心优势总结

1. **🤖 AI 原生支持**: 从"命令行脚本"升级为"MCP 工具"，Claude/ChatGPT 直接调用
2. **⚙️ 配置分离**: 从"全局 config.py"升级为"Pydantic 参数对象"，彻底解决并发问题
3. **🔧 服务化架构**: 从"一次性脚本"升级为"常驻服务"，性能提升 5-10 倍
4. **📦 模块化设计**: Service 层 + Endpoint 层，代码清晰可维护
5. **🔌 标准协议**: MCP 协议，与任何 AI 助手无缝集成

## 🏗️ 全新架构设计

### 架构概览

```
┌─────────────────────────────────────────────────────┐
│          AI 助手 (Claude / ChatGPT)                  │
└───────────┬─────────────────────────────────────────┘
            │ MCP Protocol (SSE/STDIO)
            ↓
┌────────────────────────────────────────────────────┐
│         MCP Service (:9090)                         │
│  ┌──────────────────────────────────────────────┐  │
│  │  21+ FastMCP 工具 (bili_search, xhs_detail...) │  │
│  └────────┬─────────────────────────────────────┘  │
│           │ 直接调用                                 │
│           ↓                                         │
│  ┌──────────────────────────────────────────────┐  │
│  │  Service 层 (BilibiliCrawlerService...)      │  │
│  │  - search() / get_detail() / get_creator()   │  │
│  └────────┬─────────────────────────────────────┘  │
│           │ 参数化配置                               │
│           ↓                                         │
│  ┌──────────────────────────────────────────────┐  │
│  │  Crawler 层 (BilibiliCrawler)                │  │
│  │  - 接受 CrawlerConfig 参数                    │  │
│  │  - 启动浏览器并执行爬取                        │  │
│  └────────┬─────────────────────────────────────┘  │
│           │                                         │
│           ↓                                         │
│  ┌──────────────────────────────────────────────┐  │
│  │  Playwright 浏览器自动化                      │  │
│  │  - 自动登录处理                               │  │
│  │  - Cookie 管理                                │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

### 核心设计理念

#### 1. **参数化配置（Parameterized Configuration）**

**旧架构问题：**
```python
# ❌ 全局单例config，并发冲突
import config
config.PLATFORM = "bili"
config.KEYWORDS = "AI"
crawler = BilibiliCrawler()  # 读取全局config
```

**新架构方案：**
```python
# ✅ 参数化配置，并发安全
from app.crawler.config import CrawlerConfig, create_search_config

config = create_search_config(
    platform=Platform.BILIBILI,
    keywords="AI",
    max_notes=15
)
crawler = BilibiliCrawler(config)  # 配置通过参数传入
await crawler.start()
```

#### 2. **服务层抽象（Service Layer）**

每个平台提供统一的高层API：

```python
from app.crawler.platforms.bilibili.service import BilibiliCrawlerService

service = BilibiliCrawlerService()

# 简洁的API调用
result = await service.search(
    keywords="Python教程",
    max_notes=20,
    headless=True
)
```

#### 3. **MCP工具直接调用（Direct Invocation）**

```python
# app/api/endpoints/platform/bilibili.py
class BilibiliEndpoint(BaseEndpoint):
    def __init__(self):
        self.service = BilibiliCrawlerService()

    def register_mcp_tools(self, app: FastMCP):
        @app.tool(name="bili_search")
        async def bili_search(keywords: str, max_notes: int = 15) -> str:
            # 直接调用服务层，无需HTTP请求
            result = await self.service.search(keywords, max_notes)
            return json.dumps(result, ensure_ascii=False)
```

### 🔧 核心组件

#### 1. 配置管理（Configuration）

**文件位置**: `app/crawler/config/crawler_config.py`

```python
@dataclass
class CrawlerConfig:
    """爬虫统一配置类"""
    platform: Platform              # 平台：BILIBILI, XHS, DOUYIN...
    crawler_type: CrawlerType       # 类型：SEARCH, DETAIL, CREATOR
    keywords: Optional[str]         # 搜索关键词
    note_ids: Optional[List[str]]   # 指定内容ID
    creator_ids: Optional[List[str]]# 创作者ID

    # 子配置
    browser: BrowserConfig          # 浏览器配置（headless、user_agent...）
    login: LoginConfig              # 登录配置（login_type、cookie_str...）
    crawl: CrawlConfig              # 爬取配置（max_notes、enable_comments...）
    store: StoreConfig              # 存储配置（save_mode、data_dir...）
```

#### 2. 服务层（Service Layer）

**示例**: `app/crawler/platforms/bilibili/service.py`

```python
class BilibiliCrawlerService:
    """B站爬虫服务"""

    async def search(
        self,
        keywords: str,
        max_notes: int = 15,
        enable_comments: bool = True,
        login_cookie: Optional[str] = None,
        headless: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """搜索B站视频"""
        config = create_search_config(
            platform=Platform.BILIBILI,
            keywords=keywords,
            max_notes=max_notes,
            enable_comments=enable_comments,
            cookie_str=login_cookie,
            headless=headless,
            **kwargs
        )

        crawler = BilibiliCrawler(config)
        try:
            return await crawler.start()
        finally:
            await crawler.close()
```

#### 3. 爬虫层（Crawler Layer）

**示例**: `app/crawler/platforms/bilibili/crawler.py`

```python
class BilibiliCrawler(AbstractCrawler):
    """B站爬虫（改造版 - 参数化配置）"""

    def __init__(self, config: CrawlerConfig):
        super().__init__(config)
        if config.platform != Platform.BILIBILI:
            raise ValueError("Invalid platform")

        self.index_url = "https://www.bilibili.com"
        self.bili_client: Optional[BilibiliClient] = None

    async def start(self) -> Dict:
        """启动爬虫"""
        async with async_playwright() as playwright:
            self.browser_context = await self.launch_browser(...)
            self.bili_client = await self.create_bilibili_client()

            # 根据爬虫类型执行不同操作
            if self.config.crawler_type == CrawlerType.SEARCH:
                return await self.search()
            elif self.config.crawler_type == CrawlerType.DETAIL:
                return await self.get_specified_videos(self.config.note_ids)
```

#### 4. 端点层（Endpoint Layer）

**文件位置**: `app/api/endpoints/platform/bilibili.py`

所有端点继承 `BaseEndpoint` 并实现：
- `register_routes()`: 注册 HTTP 路由（可选）
- `register_mcp_tools()`: 注册 MCP 工具（必须）

```python
class BilibiliEndpoint(BaseEndpoint):
    def __init__(self):
        super().__init__(prefix="/bilibili", tags=["B站"])
        self.service = BilibiliCrawlerService()

    def register_routes(self):
        return []  # 不提供HTTP接口

    def register_mcp_tools(self, app: FastMCP):
        @app.tool(name="bili_search")
        async def bili_search(keywords: str, max_notes: int = 15) -> str:
            """搜索B站视频"""
            result = await self.service.search(keywords, max_notes)
            return json.dumps(result, ensure_ascii=False)

        self._add_tool_info("bili_search", "搜索Bilibili视频")
```

## 🚀 快速开始

### ⚡ 3 分钟上手（推荐）

**本地开发方式：**

```bash
# 1. 克隆项目（不含子模块，我们已经重构了）
git clone <repository-url>
cd media-crawler-mcp-service

# 2. 安装依赖
poetry install

# 3. 配置环境变量（可选）
cp .env.example .env

# 4. 启动服务
python main.py --transport both
```

启动成功后访问：
- **MCP SSE 服务**: http://localhost:9090/sse
- **健康检查**: http://localhost:9090/health

### 💻 环境要求

- **Python 3.11+** & **Poetry 2.0+**
- **Playwright** (自动安装)
- PostgreSQL 12+ & Redis 6+ (可选)

### 📝 配置说明

**环境变量（.env 文件）：**

```bash
# === 应用基础配置 ===
APP_ENV=dev              # 环境：dev 或 prod
APP_PORT=9090            # MCP 服务端口
APP_DEBUG=true           # 调试模式

# === 平台选择 ===
ENABLED_PLATFORMS=all    # all 或指定：xhs,dy,bili

# === 爬虫默认配置 ===
DEFAULT_HEADLESS=false              # 无头模式（开发时建议false查看浏览器）
DEFAULT_LOGIN_TYPE=qrcode           # 登录方式：cookie, qrcode, phone
DEFAULT_SAVE_FORMAT=json            # 数据存储：json, csv, db, sqlite
DEFAULT_MAX_NOTES=15                # 每次爬取最大数量
DEFAULT_ENABLE_COMMENTS=true        # 是否爬取评论
DEFAULT_MAX_COMMENTS_PER_NOTE=10    # 每条内容最大评论数
```

### 🌐 启动服务

```bash
# 启动 MCP 服务（SSE + STDIO双模式）
python main.py --transport both

# 仅启动 SSE 模式（Web连接）
python main.py --transport sse

# 仅启动 STDIO 模式（本地CLI）
python main.py --transport stdio
```

### 🤖 连接 AI 助手

#### Claude Desktop 配置

编辑 Claude Desktop 配置文件：

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

添加配置：

```json
{
  "mcpServers": {
    "media-crawler": {
      "url": "http://localhost:9090/sse"
    }
  }
}
```

重启 Claude Desktop，即可看到 **21 个爬虫工具**！

### 🎆 第一次使用

#### 1. 测试 B站爬虫

在 AI 助手中输入：

```plaintext
使用 bili_search 工具搜索"Python教程"相关的B站视频，
返回前 5 条结果的标题、UP主和播放量。
```

#### 2. 处理登录（首次爬取）

首次爬取某些平台时，会弹出浏览器进行登录：
1. 浏览器会自动打开（`headless=false` 时）
2. 扫描二维码或输入账号密码登录
3. 登录状态会自动保存到 `browser_data/` 目录
4. 下次爬取会自动复用登录态

**提示**：如果想跳过登录，可以传入 `login_cookie` 参数：

```plaintext
使用 bili_search 工具搜索"AI"，并传入我的B站Cookie：
SESSDATA=xxxxx; bili_jct=xxxxx
```

#### 3. 查看爬取数据

数据保存在 `data/` 目录：

```bash
# 查看B站数据
ls -lh data/bili/

# 查看最新的 JSON 文件
cat data/bili/videos_*.json | jq '.[0]'
```

## 🔧 MCP 工具列表（21+ 智能爬虫工具）

### 📺 B站 (bili) - 已完成重构

- **`bili_search`** - B站视频搜索爬取
  ```plaintext
  使用 bili_search 工具搜索"Python教程"，爬取20条视频
  ```

- **`bili_detail`** - 指定视频详情爬取
  ```plaintext
  使用 bili_detail 工具获取视频 BV1xx411c7mD 的详细信息
  ```

- **`bili_creator`** - UP主主页和视频爬取
  ```plaintext
  使用 bili_creator 工具爬取UP主 123456 的所有视频
  ```

- **`bili_search_time_range`** - 按时间范围搜索
  ```plaintext
  使用 bili_search_time_range 搜索2024-01-01到2024-01-31期间的"AI"相关视频
  ```

### 💝 小红书 (xhs) - 待重构

- **`xhs_search`** - 关键词搜索爬取
- **`xhs_detail`** - 指定笔记详情爬取
- **`xhs_creator`** - 创作者主页和作品爬取

### 🎨 抖音 (dy) - 待重构

- **`dy_search`** - 视频关键词搜索爬取
- **`dy_detail`** - 指定视频详情爬取
- **`dy_creator`** - 创作者主页和视频爬取

### ⚡ 快手 (ks) - 待重构

- **`ks_search`** - 快手视频搜索爬取
- **`ks_detail`** - 指定视频详情爬取
- **`ks_creator`** - 创作者主页爬取

### 📱 微博 (wb) - 待重构

- **`wb_search`** - 微博关键词搜索爬取
- **`wb_detail`** - 指定微博详情爬取
- **`wb_creator`** - 博主主页和微博爬取

### 💬 贴吧 (tieba) - 待重构

- **`tieba_search`** - 贴吧关键词搜索爬取
- **`tieba_detail`** - 指定帖子详情爬取

### 🧮 知乎 (zhihu) - 待重构

- **`zhihu_search`** - 知乎内容搜索爬取
- **`zhihu_detail`** - 指定内容详情爬取

## 📊 数据存储

数据默认保存在 `data/` 目录：

```
data/
├── bili/                # B站数据
│   ├── videos_*.json    # 视频数据
│   └── comments_*.json  # 评论数据
├── xhs/                 # 小红书数据
├── dy/                  # 抖音数据
└── ...                  # 其他平台
```

**支持存储格式：**
- **JSON** - 文件存储（默认，AI 友好）
- **CSV** - Excel 兼容格式
- **SQLite** - 本地数据库
- **PostgreSQL** - 生产环境推荐

## 🔍 常用命令

### 开发调试

```bash
# 安装依赖
poetry install

# 格式化代码
poetry run black app/ && poetry run isort app/

# 类型检查
poetry run mypy app/

# 运行测试
poetry run pytest tests/ -v

# 更新依赖
poetry update
```

### 启动服务

```bash
# 启动 MCP 服务（推荐）
python main.py --transport both

# 启动管理界面（可选）
python admin_main.py --port 9091
```

## 🚀 使用场景

### 🎨 AI 驱动的数据采集

```plaintext
用户: 帮我收集最近一周"新能源汽车"在小红书的热门讨论
AI: 调用 xhs_search 工具 → 返回结构化数据 → 生成分析报告
```

### 📊 竞品分析

```plaintext
用户: 分析"李佳琦"和"薇娅"在抖音的粉丝互动情况
AI: 调用 dy_creator 工具 → 对比数据 → 生成可视化报告
```

### 📢 舆情监控

```plaintext
用户: 监控"某品牌"在B站的评论情绪
AI: 调用 bili_search 工具 → 获取评论 → 情感分析 → 实时预警
```

## ⚙️ 扩展新平台

基于新架构，扩展新平台非常简单：

### 1. 创建平台目录

```bash
mkdir app/crawler/platforms/yourplatform
touch app/crawler/platforms/yourplatform/__init__.py
touch app/crawler/platforms/yourplatform/crawler.py
touch app/crawler/platforms/yourplatform/service.py
touch app/crawler/platforms/yourplatform/client.py
```

### 2. 实现 Crawler

```python
# app/crawler/platforms/yourplatform/crawler.py
from app.crawler.base import AbstractCrawler

class YourPlatformCrawler(AbstractCrawler):
    def __init__(self, config: CrawlerConfig):
        super().__init__(config)
        # 初始化逻辑

    async def start(self) -> Dict:
        # 爬取逻辑
        pass
```

### 3. 实现 Service

```python
# app/crawler/platforms/yourplatform/service.py
class YourPlatformCrawlerService:
    async def search(self, keywords: str, **kwargs) -> Dict:
        config = create_search_config(...)
        crawler = YourPlatformCrawler(config)
        try:
            return await crawler.start()
        finally:
            await crawler.close()
```

### 4. 注册 MCP 端点

```python
# app/api/endpoints/platform/yourplatform.py
class YourPlatformEndpoint(BaseEndpoint):
    def __init__(self):
        super().__init__(prefix="/yourplatform", tags=["你的平台"])
        self.service = YourPlatformCrawlerService()

    def register_mcp_tools(self, app: FastMCP):
        @app.tool(name="yourplatform_search")
        async def yourplatform_search(keywords: str) -> str:
            result = await self.service.search(keywords)
            return json.dumps(result, ensure_ascii=False)
```

### 5. 注册到应用

```python
# app/api_service.py
from app.api.endpoints.platform.yourplatform import YourPlatformEndpoint

def auto_discover_endpoints():
    endpoint_registry.register(YourPlatformEndpoint())
```

完成！新平台的 MCP 工具自动可用。

## 🔧 故障排查

**常见问题：**

```bash
# Q: 启动失败，提示找不到模块？
poetry install  # 确保依赖已安装

# Q: 浏览器启动失败？
poetry run playwright install chromium  # 安装浏览器

# Q: 没有爬取到数据？
# 1. 检查平台登录状态（首次需要登录）
# 2. 设置 headless=false 查看浏览器行为
# 3. 查看日志：tail -f logs/mcp-toolse.log

# Q: 并发爬取数据混乱？
# 新架构已解决此问题！每个任务使用独立配置上下文
```

## 🛡️ 重要提示

1. **合规使用**: 仅用于学习研究，请遵守平台服务条款
2. **频率控制**: 设置合理爬取间隔（`crawl_interval`），避免对平台造成负担
3. **数据隐私**: 妥善保管数据，不得用于商业目的
4. **Cookie 安全**: 登录状态存储在 `browser_data/` 目录，注意权限控制

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

**开发流程：**
1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

**重构进度**:
- ✅ **B站 (bili)**: 完成参数化重构，提供4个MCP工具
- 🔄 **小红书 (xhs)**: 重构中...
- ⏳ **抖音、快手、微博、贴吧、知乎**: 待重构

## 📄 许可证 & 联系

- **许可证**: MIT License
- **问题反馈**: [GitHub Issues](https://github.com/your-repo/issues)
- **邮箱支持**: yancyyu.ok@gmail.com

---

## 🙏 致谢

本项目基于以下优秀的开源项目构建：

- **[MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)** - 感谢 [@NanmiCoder](https://github.com/NanmiCoder) 提供的强大社交媒体爬虫引擎
- **[FastMCP](https://github.com/jlowin/fastmcp)** - MCP 协议的 Python 实现框架

**如果这个项目对你有帮助，请给个 Star ⭐️ 支持一下！**

**MediaCrawler MCP 智能爬虫服务** - 让 AI 拥有社交媒体数据采集能力 🚀