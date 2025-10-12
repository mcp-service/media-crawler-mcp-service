# media-crawler-mcp-service - 社交媒体爬虫 MCP 服务

基于 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 的 MCP (Model Context Protocol) 边车服务，将社交媒体爬虫能力封装为标准化的 AI 工具调用接口。

## 🎯 项目定位

本项目是一个 **MCP 边车服务**，将 MediaCrawler 的社交媒体爬虫功能暴露为 MCP 协议工具，使 AI 助手（Claude、ChatGPT 等）能够直接调用爬虫能力，实现智能化的社交媒体数据采集。

### 核心特性

- **🔌 MCP 协议封装**: 将 MediaCrawler 封装为标准 MCP 工具，支持 SSE 和 STDIO 双传输模式
- **🤖 AI 友好**: 提供结构化的 Prompts 和 Resources，优化 AI 调用体验
- **🎛️ 管理端模块**: 独立的 Web 管理界面，处理登录验证码等人工交互场景
- **🐳 容器化部署**: 完整的 Docker Compose 方案，一键启动所有服务
- **📊 多平台支持**: 小红书、抖音、快手、B站、微博、贴吧、知乎

## 🙏 致谢

本项目基于以下优秀的开源项目构建：

- **[MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)** - 感谢 [@NanmiCoder](https://github.com/NanmiCoder) 提供的强大社交媒体爬虫引擎
- **[FastMCP](https://github.com/jlowin/fastmcp)** - MCP 协议的 Python 实现框架

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      AI 助手 (Claude/GPT)                   │
└─────────────────────┬───────────────────────────────────────┘
                      │ MCP Protocol (SSE/STDIO)
┌─────────────────────▼───────────────────────────────────────┐
│                   MCP Tools Service                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  FastMCP Server                                     │   │
│  │  - Tools: 21 个爬虫工具 (xhs_search, dy_detail...) │   │
│  │  - Prompts: 使用指南、故障排查、最佳实践           │   │
│  │  - Resources: 数据目录、配置信息、系统状态         │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Admin Service (FastAPI)                            │   │
│  │  - 登录验证码处理                                   │   │
│  │  - 爬虫任务管理                                     │   │
│  │  - 数据查看导出                                     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │ 边车调用
┌─────────────────────▼───────────────────────────────────────┐
│              MediaCrawler (Git Submodule)                   │
│  - 小红书爬虫 (xhs)    - 抖音爬虫 (dy)                     │
│  - 快手爬虫 (ks)       - B站爬虫 (bili)                    │
│  - 微博爬虫 (wb)       - 贴吧爬虫 (tieba)                  │
│  - 知乎爬虫 (zhihu)                                         │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### ⚡ 最快 3 分钟上手（推荐）

**使用 Docker Compose 一键启动（无需安装 Python 和依赖）：**

```bash
# 1. 克隆项目（含 MediaCrawler 子模块）
git clone --recurse-submodules <repository-url>
cd ai-tools-core

# 2. 配置环境变量（可选，使用默认配置可跳过）
cp .env.example .env

# 3. 启动所有服务（数据库 + Redis + MCP 服务）
cd deploy && docker compose up -d
```

启动成功后访问：
- **MCP SSE 服务**: http://localhost:9090/sse
- **管理服务**: http://localhost:9091
- **健康检查**: http://localhost:9090/health

> **推荐使用 Docker Compose**: 开箱即用，自动配置数据库和 Redis，无需手动安装依赖。

### 环境要求

#### Docker 方式（推荐）
- **Docker 20.10+**
- **Docker Compose 2.0+**

#### 本地开发方式
- **Python 3.11+**
- **Poetry 2.0+**
- PostgreSQL 12+ (可选)
- Redis 6+ (可选)

### 详细安装步骤

#### 方式一：Docker Compose（生产推荐）⭐

**1. 克隆项目**

```bash
# 完整克隆（包含 MediaCrawler 子模块）
git clone --recurse-submodules <repository-url>
cd ai-tools-core

# 如果已克隆但缺少子模块，执行：
git submodule update --init --recursive
```

**2. 配置环境变量（可选）**

```bash
cp .env.example .env
```

默认配置已可直接使用，如需自定义：

```bash
# 编辑 .env 文件
nano .env  # 或使用其他编辑器
```

**3. 启动服务**

```bash
# 方式 A: 使用启动脚本
cd deploy && ./start.sh prod

# 方式 B: 直接使用 Docker Compose
cd deploy && docker compose up -d
```

**4. 验证服务**

```bash
# 查看服务状态
cd deploy && docker compose ps

# 查看日志
cd deploy && docker compose logs -f mcp-service

# 测试健康检查
curl http://localhost:9090/health
```

**Docker Compose 常用命令：**

```bash
# 查看所有服务状态
cd deploy && docker compose ps

# 查看实时日志
cd deploy && docker compose logs -f

# 重启 MCP 服务
cd deploy && docker compose restart mcp-service

# 停止所有服务
cd deploy && docker compose down

# 停止并删除数据卷
cd deploy && docker compose down -v

# 重新构建并启动
cd deploy && docker compose up -d --build

# 进入容器
cd deploy && docker compose exec mcp-service bash
```

#### 方式二：本地开发

**1. 克隆项目**

```bash
git clone --recurse-submodules <repository-url>
cd ai-tools-core
```

> **重要**: 必须使用 `--recurse-submodules` 参数克隆，否则 MediaCrawler 子模块不会被下载。

**2. 安装 Poetry**

```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

# 验证安装
poetry --version
```

**3. 安装项目依赖**

```bash
# 安装所有依赖
poetry install

# 激活虚拟环境（可选）
poetry shell
```

**4. 配置环境变量**

```bash
cp .env.example .env
nano .env  # 编辑配置
```

**必需配置项：**

```bash
# 应用基础配置
APP_ENV=dev              # 环境：dev 或 prod
APP_PORT=9090            # MCP 服务端口
ADMIN_PORT=9091          # 管理服务端口

# 平台选择（可选，默认启用所有）
ENABLED_PLATFORMS=all    # 或指定：xhs,dy,bili
```

**可选配置项：**

```bash
# MediaCrawler 配置
MEDIA_CRAWLER_HEADLESS=true              # 无头模式（生产环境推荐）
MEDIA_CRAWLER_LOGIN_TYPE=qrcode          # 登录方式：qrcode, phone, cookie
MEDIA_CRAWLER_SAVE_DATA_OPTION=json      # 数据存储：json, csv, db, sqlite

# 数据库配置（可选，Docker 会自动配置）
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your-password
DB_NAME=mcp_tools_db

# Redis 配置（可选，Docker 会自动配置）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

**5. 启动服务**

```bash
# 方式 A: 使用启动脚本（推荐）
cd deploy && ./start.sh dev

# 方式 B: 直接命令
poetry run python main.py --transport both

# 方式 C: 仅 SSE 模式
poetry run python main.py --transport sse

# 方式 D: 不启动管理服务
poetry run python main.py --transport sse --admin-port 0
```

### 服务地址

启动成功后可以访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| **MCP SSE 服务** | http://localhost:9090/sse | AI 工具调用入口 |
| **管理服务** | http://localhost:9091 | 登录管理、任务监控 |
| **健康检查** | http://localhost:9090/health | 服务健康状态 |
| **PostgreSQL** | localhost:5432 | 数据库（仅 Docker） |
| **Redis** | localhost:6379 | 缓存（仅 Docker） |

### 连接到 AI 助手

#### Claude Desktop 配置

编辑 Claude Desktop 配置文件：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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

重启 Claude Desktop，即可看到 21 个爬虫工具！

#### 其他 MCP 客户端

任何支持 MCP 协议的客户端都可以连接：

- **SSE 模式**: 使用 `http://localhost:9090/sse`
- **STDIO 模式**: 运行 `poetry run python main.py --transport stdio`

### 第一次使用

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

## 🔧 MCP 工具列表

### 小红书 (xhs)
- `xhs_search` - 关键词搜索爬取
- `xhs_detail` - 指定笔记详情
- `xhs_creator` - 创作者主页爬取

### 抖音 (dy)
- `dy_search` - 关键词搜索爬取
- `dy_detail` - 指定视频详情
- `dy_creator` - 创作者主页爬取

### 快手 (ks)
- `ks_search` - 关键词搜索爬取
- `ks_detail` - 指定视频详情
- `ks_creator` - 创作者主页爬取

### B站 (bili)
- `bili_search` - 关键词搜索爬取
- `bili_detail` - 指定视频详情
- `bili_creator` - 创作者主页爬取

### 微博 (wb)
- `wb_search` - 关键词搜索爬取
- `wb_detail` - 指定微博详情
- `wb_creator` - 创作者主页爬取

### 贴吧 (tieba)
- `tieba_search` - 关键词搜索爬取
- `tieba_detail` - 指定帖子详情

### 知乎 (zhihu)
- `zhihu_search` - 关键词搜索爬取
- `zhihu_detail` - 指定内容详情

## 📝 MCP Prompts（使用指南）

项目内置多个 Prompt 模板，帮助 AI 更好地使用爬虫工具：

- **crawler_basic** - 基础爬虫使用指南
- **xiaohongshu_guide** - 小红书爬虫详细说明
- **data_analysis** - 爬取数据分析指南
- **troubleshooting** - 故障排查指南
- **batch_crawler** - 批量爬取最佳实践

### 示例：让 AI 爬取小红书数据

```plaintext
请使用 xhs_search 工具爬取"AI绘画"相关的小红书笔记，
爬取 20 条，并提取标题、点赞数、评论数。
```

AI 会自动调用 `xhs_search` 工具并返回结构化数据。

## 🎛️ 管理端功能

独立的 Web 管理界面（端口 9091），解决人工交互场景：

### 核心功能

- **登录管理**: 处理平台登录、验证码识别
- **任务监控**: 查看爬虫任务执行状态
- **数据管理**: 浏览、导出爬取的数据
- **配置管理**: 动态调整爬虫参数

### 访问管理端

```bash
http://localhost:9091
```

## 📊 数据存储

爬取的数据默认保存在 `data/` 目录：

```
data/
├── xhs/                 # 小红书数据
│   ├── notes_*.json     # 笔记数据
│   └── comments_*.json  # 评论数据
├── dy/                  # 抖音数据
├── bili/                # B站数据
└── ...                  # 其他平台
```

支持多种存储方式：

- **JSON** - 文件存储（默认）
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

## 🎯 使用场景

### 1. AI 驱动的数据采集

```plaintext
用户: 帮我收集最近一周"新能源汽车"在小红书的热门讨论
AI: 调用 xhs_search 工具 → 返回结构化数据 → 生成分析报告
```

### 2. 竞品分析

```plaintext
用户: 分析"李佳琦"和"薇娅"在抖音的粉丝互动情况
AI: 调用 dy_creator 工具 → 对比数据 → 生成可视化报告
```

### 3. 舆情监控

```plaintext
用户: 监控"某品牌"在各平台的评论情绪
AI: 批量调用多个平台工具 → 情感分析 → 实时预警
```

## ⚙️ 高级配置

### 选择性启用平台

编辑 `.env` 文件：

```bash
# 仅启用小红书和抖音
ENABLED_PLATFORMS=xhs,dy

# 启用所有平台
ENABLED_PLATFORMS=all
```

### MediaCrawler 参数

```bash
# 无头模式（生产环境推荐）
MEDIA_CRAWLER_HEADLESS=true

# 登录方式
MEDIA_CRAWLER_LOGIN_TYPE=qrcode  # qrcode, phone, cookie

# 数据存储
MEDIA_CRAWLER_SAVE_DATA_OPTION=json  # json, csv, db, sqlite
```

## 🛡️ 注意事项

1. **合规使用**: 仅用于学习研究，请遵守平台的 robots.txt 和服务条款
2. **频率控制**: 建议设置合理的爬取间隔，避免对平台造成负担
3. **数据隐私**: 妥善保管爬取的数据，不得用于商业目的
4. **Cookie 安全**: 浏览器登录状态存储在 `browser_data/` 目录，注意权限控制

## 🔧 故障排查

### 登录失败

```bash
# 清除浏览器缓存
rm -rf browser_data/

# 使用扫码登录（推荐）
MEDIA_CRAWLER_LOGIN_TYPE=qrcode
```

### Docker 容器无法启动

```bash
# 查看日志
cd deploy && docker compose logs mcp-service

# 检查端口占用
netstat -tuln | grep 9090

# 重建容器
cd deploy && docker compose down -v
cd deploy && docker compose up -d --build
```

### 爬取数据为空

1. 检查平台登录状态
2. 验证 URL 格式是否正确
3. 查看日志文件 `logs/mcp-toolse.log`

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 添加新平台支持

参考 `app/api/endpoints/platforms/` 下的现有实现，创建新的 Endpoint 类并注册。

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 📞 支持与反馈

- 📧 邮箱: yancyyu.ok@gmail.com
- 🐛 问题反馈: [GitHub Issues](https://github.com/your-repo/issues)
- 💬 讨论: [GitHub Discussions](https://github.com/your-repo/discussions)

## 🌟 Star History

如果这个项目对你有帮助，请给个 Star ⭐️ 支持一下！

---

**MCP Tools** - 让 AI 拥有社交媒体数据采集能力 🚀