# MediaCrawler MCP 边车服务

基于 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 的 AI 社交媒体爬虫边车服务，通过 MCP (Model Context Protocol) 协议为 AI 助手提供社交媒体数据采集能力。

## 🎯 项目概述

本项目是一个 **企业级边车服务架构**，将 MediaCrawler 的社交媒体爬虫功能封装为 MCP 协议工具，使 Claude、ChatGPT 等 AI 助手能够智能化地采集和分析社交媒体数据。

### ✨ 核心特性

- **🏗️ 边车服务架构**: 浏览器池复用、Cookie 持久化、高并发支持
- **⚙️ 统一配置管理**: 从 `app/config/settings.py` 统一管理所有配置
- **🔧 Endpoint 重构**: 独立的 sidecar 和 login endpoint 模块
- **🎛️ Web 管理界面**: 完整的 Admin 系统，处理登录验证码等交互场景
- **🔌 MCP 协议支持**: SSE 和 STDIO 双传输模式，21+ 爬虫工具
- **🐳 容器化部署**: 一键 Docker Compose 部署，包含数据库和缓存
- **📊 多平台支持**: 小红书、抖音、快手、B站、微博、贴吧、知乎

## ⚙️ 统一配置管理

本项目采用企业级配置管理架构，所有配置从 `app/config/settings.py` 统一获取：

### 配置层次结构

```
GlobalSettings (根配置)
├── AppConfig (应用配置)
├── SidecarConfig (边车服务配置)
├── PlatformSettings (平台设置)
├── DatabaseConfig (数据库配置)
├── RedisConfig (Redis配置)
└── LoggerConfig (日志配置)
```

### 平台枚举与验证

```
# 支持的平台
class PlatformCode(str, Enum):
    XHS = "xhs"         # 小红书
    DOUYIN = "dy"       # 抖音
    KUAISHOU = "ks"     # 快手
    BILIBILI = "bili"   # B站
    WEIBO = "wb"        # 微博
    TIEBA = "tieba"     # 贴吧
    ZHIHU = "zhihu"     # 知乎

# 爬虫类型
class CrawlerType(str, Enum):
    SEARCH = "search"   # 关键词搜索
    DETAIL = "detail"   # 指定内容
    CREATOR = "creator" # 创作者主页

# 登录方式
class LoginType(str, Enum):
    QRCODE = "qrcode"   # 二维码登录
    PHONE = "phone"     # 手机号登录
    COOKIE = "cookie"   # Cookie登录
```

## 🔧 核心组件

### 1. 浏览器池管理 (Browser Pool)

**文件：** `app/core/browser_pool.py`

- 预初始化 3-5 个浏览器实例（可配置）
- 支持多平台独立池（xhs, dy, bili 等）
- 自动清理长时间未使用的实例
- 限制单个浏览器最大使用次数（防止内存泄漏）

### 2. 会话管理器 (Session Manager)

**文件：** `app/core/session_manager.py`

- Cookie 持久化存储（`browser_data/` 目录）
- 自动检查会话有效性
- 支持多平台独立会话
- 会话过期自动清理

### 3. MediaCrawler 客户端

**文件：** `app/core/media_crawler_client.py`

- 与边车服务通信的 HTTP 客户端
- 提供与原 wrapper 相同的接口
- 支持超时、重试、错误处理

### 4. Endpoint 重构架构

**新增结构：**
- `app/api/endpoints/sidecar/` - 边车服务端点
- `app/api/endpoints/login/` - 登录管理端点
- 统一的 `BaseEndpoint` 抽象类
- 自动发现和注册系统

## 🙏 致谢

本项目基于以下优秀的开源项目构建：

- **[MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)** - 感谢 [@NanmiCoder](https://github.com/NanmiCoder) 提供的强大社交媒体爬虫引擎
- **[FastMCP](https://github.com/jlowin/fastmcp)** - MCP 协议的 Python 实现框架

## 🏗️ 边车服务架构

### 架构概览

```
┌─────────────────────────┐
│   AI 助手 (Claude/GPT)   │
└───────┬─────────────────┘
        │ MCP Protocol (SSE/STDIO)
        ↓
┌─────────────────────────────────┐
│    MCP Service (:9090)          │  
│    - 21+ FastMCP 工具            │
│    - Prompts & Resources        │
│    - HTTP Client → Sidecar      │
└─────────┬───────────────────────┘
          │ HTTP API
          ↓
┌─────────────────────────────────┐
│  MediaCrawler Sidecar (:8001)  │
│  ✓ 浏览器池（预热5个实例）         │
│  ✓ 会话管理（Cookie复用）         │
│  ✓ 任务队列                     │
│  ✓ 配置注入                     │
└─────────┬───────────────────────┘
          ↑ 管理调用
          │
┌─────────────────────────────────┐
│    Admin Service (:9091)        │
│    - MCP 工具测试 & 管理         │
│    - 边车服务监控 & 配置         │
│    - 登录验证码处理              │
│    - 爬虫任务监控               │
│    - 数据查看 & 导出            │
└─────────────────────────────────┘
          │
          └───────────────────────────────── MCP API & Sidecar API
```

### 性能对比

| 指标 | 旧架构（进程模式） | 新架构（边车模式） | 提升 |
|------|-------------------|-------------------|---------|
| 浏览器启动时间 | 5-10秒 | 0秒（复用） | **∞** |
| 并发能力 | 1-2 req/min | 10+ req/min | **5-10x** |
| 登录状态 | 每次重新登录 | Cookie复用 | **✓** |
| 内存占用 | 峰值2-3GB | 稳定1.5GB | **-40%** |
| 资源利用率 | 低（频繁创建销毁） | 高（池化复用） | **+80%** |

## 🚀 快速开始

## 🚀 快速开始

### ⚡ 3 分钟上手（推荐）

**Docker Compose 一键部署（无需 Python 环境）：**

```bash
# 1. 克隆项目（含 MediaCrawler 子模块）
git clone --recurse-submodules <repository-url>
cd media-crawler-mcp-service

# 2. 配置环境变量（可选，使用默认配置可跳过）
cp .env.example .env

# 3. 启动所有服务（PostgreSQL + Redis + Sidecar + MCP + Admin）
cd deploy && docker compose up -d
```

启动成功后访问：
- **MCP SSE 服务**: http://localhost:9090/sse
- **管理服务**: http://localhost:9091
- **边车服务**: http://localhost:8001
- **健康检查**: http://localhost:9090/health

### 💻 环境要求

#### Docker 方式（推荐）
- **Docker 20.10+** & **Docker Compose 2.0+**

#### 本地开发方式
- **Python 3.11+** & **Poetry 2.0+**
- PostgreSQL 12+ & Redis 6+ (可选)

### 📝 配置说明

**必需配置（.env 文件）：**

```bash
# === 应用基础配置 ===
APP_ENV=dev              # 环境：dev 或 prod
APP_PORT=9090            # MCP 服务端口
ADMIN_PORT=9091          # 管理服务端口
SIDECAR_PORT=8001        # 边车服务端口

# === 平台选择（可选） ===
ENABLED_PLATFORMS=all    # all 或指定：xhs,dy,bili

# === 边车服务配置 ===
MEDIA_CRAWLER_SIDECAR_URL=http://localhost:8001
BROWSER_POOL_SIZE=3      # 浏览器池大小
```

**可选配置：**

```bash
# MediaCrawler 配置
DEFAULT_HEADLESS=true              # 无头模式（生产环境推荐）
DEFAULT_LOGIN_TYPE=cookie          # 登录方式：cookie, qrcode, phone
DEFAULT_SAVE_FORMAT=json           # 数据存储：json, csv, db, sqlite

# 数据库配置（Docker 会自动配置）
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your-password
DB_NAME=mcp_tools_db
```

### 🚀 启动服务

**Docker Compose 方式（推荐）：**

```bash
# 启动所有服务
cd deploy && docker compose up -d

# 查看服务状态
docker compose ps

# 查看实时日志
docker compose logs -f

# 重启服务
docker compose restart mcp-service

# 停止服务
docker compose down
```

**本地开发方式：**

```bash
# 1. 安装依赖
poetry install

# 2. 启动边车服务（终端 1）
python sidecar_main.py --host 0.0.0.0 --port 8001

# 3. 启动主服务（终端 2）
python main.py --transport both
```

### 🌐 服务地址

启动成功后可以访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| **MCP SSE 服务** | http://localhost:9090/sse | AI 工具调用入口 |
| **边车服务** | http://localhost:8001 | MediaCrawler 边车服务 |
| **管理服务** | http://localhost:9091 | Web 管理界面 |
| **健康检查** | http://localhost:9090/health | 服务健康状态 |
| **API 文档** | http://localhost:8001/docs | 边车服务 API 文档 |

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

#### 1. 测试小红书爬虫

在 AI 助手中输入：

```plaintext
使用 xhs_search 工具搜索"AI绘画"相关的小红书笔记，
返回前 5 条结果的标题和点赞数。
```

#### 2. 处理登录（如需要）

首次爬取某些平台时，需要登录：

1. 打开管理界面：http://localhost:9091
2. 选择平台（如"小红书"）
3. 使用二维码扫码登录
4. 登录状态会自动保存到 `browser_data/` 目录

#### 3. 查看爬取数据

数据保存在 `data/` 目录：

```bash
# 查看小红书数据
ls -lh data/xhs/

# 查看最新的 JSON 文件
cat data/xhs/notes_*.json | jq '.[0]'
```

### 常见问题

**Q: 子模块没有下载怎么办？**

```bash
git submodule update --init --recursive
```

**Q: 端口被占用怎么办？**

编辑 `.env` 文件，修改端口：

```bash
APP_PORT=9090    # 改为其他端口，如 9095
ADMIN_PORT=9091  # 改为其他端口，如 9096
```

**Q: 启动失败怎么办？**

查看日志文件：

```bash
tail -f logs/mcp-toolse.log
```

**Q: Docker 部署失败？**

检查 Docker 是否运行：

```bash
docker info
```

查看容器日志：

```bash
cd deploy && docker compose logs mcp-service
```

## 🔧 MCP 工具列表（21 个智能爬虫工具）

### 💝 小红书 (xhs)
- **`xhs_search`** - 关键词搜索爬取（支持多关键词）
- **`xhs_detail`** - 指定笔记详情爬取
- **`xhs_creator`** - 创作者主页和作品爬取

### 🎨 抖音 (dy)
- **`dy_search`** - 视频关键词搜索爬取
- **`dy_detail`** - 指定视频详情爬取
- **`dy_creator`** - 创作者主页和视频爬取

### ⚡ 快手 (ks)
- **`ks_search`** - 快手视频搜索爬取
- **`ks_detail`** - 指定视频详情爬取
- **`ks_creator`** - 创作者主页爬取

### 📺 B站 (bili)
- **`bili_search`** - B站视频搜索爬取
- **`bili_detail`** - 指定视频详情爬取
- **`bili_creator`** - UP主主页和视频爬取

### 📱 微博 (wb)
- **`wb_search`** - 微博关键词搜索爬取
- **`wb_detail`** - 指定微博详情爬取
- **`wb_creator`** - 博主主页和微博爬取

### 💬 贴吧 (tieba)
- **`tieba_search`** - 贴吧关键词搜索爬取
- **`tieba_detail`** - 指定帖子详情爬取

### 🧮 知乎 (zhihu)
- **`zhihu_search`** - 知乎内容搜索爬取
- **`zhihu_detail`** - 指定内容详情爬取

### 📈 AI 智能使用示例

``plaintext
请使用 xhs_search 工具爬取"AI绘画"相关的小红书笔记，
爬取 20 条，并提取标题、点赞数、评论数，生成数据报告。
```

AI 会自动调用 MCP 工具并返回结构化数据。

## 🎛️ Web 管理界面

独立的 Web 管理系统（端口 9091），处理人工交互场景：

### ✨ 核心功能

- **🔑 智能登录**: 二维码扫码、验证码识别、Cookie 管理
- **📊 实时监控**: 爬虫任务执行状态、浏览器池监控
- **💾 数据管理**: 浏览、导出、分析爬取数据
- **⚙️ 配置管理**: 动态调整平台设置和爬虫参数

**访问地址：** http://localhost:9091

## 📊 数据存储

数据默认保存在 `data/` 目录：

```
data/
├── xhs/                 # 小红书数据
│   ├── notes_*.json     # 笔记数据
│   └── comments_*.json  # 评论数据
├── dy/                  # 抖音数据
├── bili/                # B站数据
└── ...                  # 其他平台
```

**支持存储格式：**
- **JSON** - 文件存储（默认，AI 友好）
- **CSV** - Excel 兼容格式
- **SQLite** - 本地数据库
- **PostgreSQL** - 生产环境推荐

## 🐳 Docker 部署

### 完整部署（推荐）

```bash
cd deploy && docker compose up -d
```

包含服务：
- PostgreSQL - 数据持久化
- Redis - 缓存和会话
- MCP Service - 主服务
- Nginx - 反向代理（可选）

### 查看日志

```bash
# 所有服务日志
cd deploy && docker compose logs -f

# 特定服务日志
cd deploy && docker compose logs -f mcp-service
```

### 停止服务

```bash
cd deploy && docker compose down
```

## 🔍 常用命令

### 开发调试

```bash
# 格式化代码
poetry run black app/ && poetry run isort app/

# 类型检查
poetry run mypy app/

# 运行测试
poetry run pytest tests/ -v

# 更新依赖
poetry update
```

### Docker 管理

```bash
# 查看服务状态
cd deploy && docker compose ps

# 重启 MCP 服务
cd deploy && docker compose restart mcp-service

# 进入容器
cd deploy && docker compose exec mcp-service bash

# 查看资源使用
docker stats mcp-tools-service

# 清理并重建
cd deploy && docker compose down -v
cd deploy && docker compose up -d --build
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
用户: 监控"某品牌"在各平台的评论情绪
AI: 批量调用多个平台工具 → 情感分析 → 实时预警
```

## ⚙️ 高级配置

**平台选择（.env 文件）：**

```bash
# 仅启用小红书和抖音
ENABLED_PLATFORMS=xhs,dy

# 启用所有平台
ENABLED_PLATFORMS=all
```

**边车服务配置：**

```bash
# 浏览器池配置
BROWSER_POOL_SIZE=5           # 浏览器池大小
DEFAULT_HEADLESS=true         # 无头模式（生产推荐）
DEFAULT_LOGIN_TYPE=cookie     # 默认登录方式
DEFAULT_SAVE_FORMAT=json      # 默认数据格式
```

## 🔧 故障排查

**常见问题：**

```bash
# Q: 子模块没有下载怎么办？
git submodule update --init --recursive

# Q: 端口被占用怎么办？
# 编辑 .env 文件，修改端口
APP_PORT=9095
ADMIN_PORT=9096
SIDECAR_PORT=8002

# Q: 没有爬取到数据？
# 1. 检查平台登录状态
# 2. 验证 URL 格式
# 3. 查看日志：tail -f logs/mcp-toolse.log

# Q: Docker 部署失败？
docker info  # 检查 Docker 状态
cd deploy && docker compose logs mcp-service  # 查看日志
```

## 🛡️ 重要提示

1. **合规使用**: 仅用于学习研究，请遵守平台服务条款
2. **频率控制**: 设置合理爬取间隔，避免对平台造成负担
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

## 📄 许可证 & 联系

- **许可证**: MIT License
- **问题反馈**: [GitHub Issues](https://github.com/your-repo/issues)
- **邮箱支持**: yancyyu.ok@gmail.com

---

## 🌟 致谢

感谢以下开源项目的支持：
- [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) - 强大的社交媒体爬虫引擎
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP 协议 Python 实现

**如果这个项目对你有帮助，请给个 Star ⭐️ 支持一下！**

**MediaCrawler MCP 边车服务** - 让 AI 拥有社交媒体数据采集能力 🚀