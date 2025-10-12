# 管理服务 (Admin Service)

## 概述

管理服务是一个独立的Web UI服务,运行在端口 **9091** 上,用于处理需要人机交互的操作,如平台登录和配置管理。

## 为什么需要管理服务?

某些操作不适合作为 MCP 工具暴露:
- **登录操作**: 需要扫描二维码或输入Cookie,这是典型的人机交互场景
- **配置管理**: 需要可视化界面来管理平台启用/禁用
- **系统监控**: 需要实时查看系统状态和爬取数据统计

## 架构设计

### Sidecar 模式
- **MCP服务** (端口9090): 提供MCP工具协议,供AI客户端调用
- **管理服务** (端口9091): 提供Web UI,供人类用户配置和管理
- 两个服务并行运行,共享同一进程和配置

### 技术栈
- **Backend**: FastAPI (轻量级异步框架)
- **Frontend**: Tailwind CSS (样式) + Alpine.js (交互)
- **Templates**: Jinja2 (服务端渲染)
- **优势**: 无需构建步骤,纯HTML/CSS/JS,部署简单

## 服务端口

| 服务 | 端口 | 用途 |
|------|------|------|
| MCP SSE服务 | 9090 | MCP工具协议端点 `/sse` |
| 管理服务 | 9091 | Web UI管理界面 |

## 页面功能

### 1. 仪表板 (`/`)
- **系统状态**: CPU、内存、磁盘使用率
- **服务状态**: MCP服务、数据库、Redis状态
- **平台状态**: 各社交平台启用状态和登录状态
- **数据统计**: 爬取数据文件数量和大小
- **快捷操作**: 快速跳转到登录/配置页面

### 2. 登录管理 (`/login`)
- **登录状态查看**: 显示所有平台的登录状态
- **登录方式**:
  - 二维码扫码登录 (需要实现)
  - Cookie手动输入登录
- **平台支持**: xiaohongshu, douyin, kuaishou, bilibili, weibo, tieba, zhihu

### 3. 配置管理 (`/config`)
- **平台配置**: 勾选启用/禁用特定平台
- **爬虫配置**:
  - 最大爬取数量
  - 每帖最大评论数
  - 是否启用评论爬取
  - 无头模式开关
  - 数据保存方式 (JSON/CSV/SQLite/DB)
- **配置持久化**: 自动保存到 `.env` 文件

## API端点

### 登录管理 API (`/api/login`)
```http
GET  /api/login/sessions       # 获取所有平台登录状态
POST /api/login/start           # 启动登录流程
GET  /api/login/status/{platform} # 获取单个平台登录状态
POST /api/login/logout/{platform} # 登出平台
```

### 配置管理 API (`/api/config`)
```http
GET  /api/config/platforms      # 获取平台配置
PUT  /api/config/platforms      # 更新平台配置
GET  /api/config/crawler        # 获取爬虫配置
PUT  /api/config/crawler        # 更新爬虫配置
```

### 状态监控 API (`/api/status`)
```http
GET  /api/status/system         # 系统状态 (CPU/内存/磁盘)
GET  /api/status/data           # 数据统计
GET  /api/status/services       # 服务状态
GET  /api/status/platforms      # 平台状态
```

## 启动方式

### 开发环境
```bash
# 启动MCP服务 + 管理服务
python main.py --transport sse --admin

# 仅启动管理服务
python main.py --transport sse --admin --admin-port 9091
```

### Docker环境
```bash
# 使用docker-compose启动
cd deploy
docker-compose up -d

# 访问服务
# MCP服务: http://localhost:9090/sse
# 管理服务: http://localhost:9091
```

## 文件结构

```
app/admin/
├── __init__.py              # FastAPI应用创建
├── static/                  # 静态文件目录 (空)
├── templates/               # Jinja2模板
│   ├── layout.html         # 基础布局模板
│   ├── dashboard.html      # 仪表板页面
│   ├── login.html          # 登录管理页面
│   └── config.html         # 配置管理页面
└── routes/                  # API路由模块
    ├── __init__.py
    ├── login.py            # 登录管理路由
    ├── config.py           # 配置管理路由
    └── status.py           # 状态监控路由
```

## TODO: 待实现功能

### 登录功能实现
目前登录功能的API接口已创建,但具体实现标记为 `TODO`:

1. **二维码登录**:
   - 需要启动 Playwright 浏览器
   - 截取二维码图片
   - 通过WebSocket推送到前端显示
   - 监听登录成功事件

2. **Cookie登录**:
   - 解析用户输入的Cookie字符串
   - 注入到 Playwright 浏览器上下文
   - 验证登录状态

3. **会话持久化**:
   - 保存浏览器会话到 `browser_data` 目录
   - 使用 Redis 缓存登录状态
   - 定期检查会话有效性

### 配置更新实现
目前配置更新API接口已创建,但需要完善:

1. **环境变量更新**:
   - 读取 `.env` 文件
   - 更新 `ENABLED_PLATFORMS` 配置
   - 写回 `.env` 文件

2. **爬虫配置更新**:
   - 更新 MediaCrawler 配置文件
   - 动态重新加载配置(可能需要重启)

3. **重启提示**:
   - 检测哪些配置需要重启服务
   - 前端显示重启警告

## 安全注意事项

- 目前管理服务**没有认证机制**,仅用于本地开发
- 生产环境建议:
  - 添加基本认证 (HTTP Basic Auth)
  - 使用 JWT Token
  - 配置防火墙规则限制访问
  - 使用 HTTPS

## 与MCP服务的关系

```
┌─────────────────────────────────────────┐
│           Docker Container              │
│                                         │
│  ┌────────────────┐  ┌───────────────┐ │
│  │  MCP Service   │  │ Admin Service │ │
│  │  (Port 9090)   │  │ (Port 9091)   │ │
│  │                │  │               │ │
│  │ - MCP Tools    │  │ - Web UI      │ │
│  │ - SSE Endpoint │  │ - Login Mgmt  │ │
│  │ - Resources    │  │ - Config Mgmt │ │
│  │ - Prompts      │  │ - Monitoring  │ │
│  └────────────────┘  └───────────────┘ │
│           │                    │        │
│           └────────┬───────────┘        │
│                    │                    │
│         ┌──────────▼──────────┐         │
│         │  Shared Resources   │         │
│         │  - PostgreSQL       │         │
│         │  - Redis            │         │
│         │  - Media Crawler    │         │
│         │  - Browser Data     │         │
│         └─────────────────────┘         │
└─────────────────────────────────────────┘
```

## 使用场景

### 场景1: 首次部署
1. 访问 `http://localhost:9091/config`
2. 选择要启用的平台 (如只启用小红书)
3. 配置爬虫参数
4. 访问 `http://localhost:9091/login`
5. 为启用的平台完成登录
6. MCP工具自动可用

### 场景2: 日常监控
1. 访问 `http://localhost:9091/` (仪表板)
2. 查看系统资源使用情况
3. 查看爬取数据统计
4. 查看平台登录状态
5. 发现某平台登录过期,点击快捷跳转到登录页

### 场景3: 切换平台
1. 访问 `http://localhost:9091/config`
2. 取消勾选不需要的平台
3. 勾选新平台
4. 保存配置 (可能需要重启)
5. 到登录页完成新平台登录

## 开发指南

### 添加新的管理页面
1. 创建模板文件 `app/admin/templates/new_page.html`
2. 继承 `layout.html` 布局
3. 在 `app/admin/__init__.py` 添加路由:
```python
@app.get("/new-page", response_class=HTMLResponse)
async def new_page(request: Request):
    return templates.TemplateResponse("new_page.html", {"request": request})
```

### 添加新的API端点
1. 在 `app/admin/routes/` 创建新模块或修改现有模块
2. 使用 FastAPI 的 `APIRouter`
3. 在 `app/admin/__init__.py` 中注册路由:
```python
from .routes import my_new_routes
app.include_router(my_new_routes.router, prefix="/api/my-routes", tags=["My Routes"])
```

### 前端开发
- 使用 Alpine.js 进行交互 (无需构建)
- 使用 Tailwind CSS CDN (无需安装)
- 使用 `fetch` API 调用后端接口
- 参考 `dashboard.html` 中的 Alpine.js 模式

## 常见问题

**Q: 为什么不用React/Vue?**
A: 为了简化部署,避免构建步骤。Alpine.js提供足够的交互能力,适合后台管理场景。

**Q: 如何添加认证?**
A: 可以使用 FastAPI 的 `Depends` 和 `HTTPBasic`:
```python
from fastapi.security import HTTPBasic, HTTPBasicCredentials
security = HTTPBasic()

@app.get("/")
async def dashboard(credentials: HTTPBasicCredentials = Depends(security)):
    # 验证逻辑
```

**Q: 管理服务能否独立部署?**
A: 可以,但需要访问相同的数据库和文件系统。建议使用当前的sidecar模式。

**Q: 如何自定义端口?**
A: 启动时使用 `--admin-port` 参数:
```bash
python main.py --admin-port 8080
```