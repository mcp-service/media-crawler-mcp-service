# MediaCrawler MCP 服务

欢迎大家一起共建，尤其是前端伙伴 —— 作者的前端功底比较弱，真心需要你来补位。如果你打算使用 vibe-code 等智能代理协作，请先通读 `Agent.MD` 并严格遵循里面的规则。

## 当前进展

- ✅ B 站（bili）平台已完成服务化重构，提供 `bili_search`、`bili_detail`、`bili_creator`、`bili_search_time_range` 四个 MCP 工具。
- ♻️ B 站登录体系焕新：`/api/login/start` 立即返回二维码 + 会话 ID，后台原生轮询同一个浏览器上下文，`/api/login/status` 为前端提供准实时状态。
- 🚧 小红书、抖音、快手、微博、贴吧、知乎等平台正在迁移到统一 Service/Endpoint 架构，欢迎认领。

## 项目定位与非目标

- 定位：面向个人效率的单用户工具，优先易用性与清晰架构。
- 非目标：不做多账号账号池管理、不做多租户控制台、不做分布式集群。
- 取舍：尽量保持代码可读可扩展，提供 Service/Endpoint/Config 等扩展点，方便他人自行加功能。

## 前端改造规则（登录页起点）

- 管理端 UI 改造默认采用 `react-bits` 提供的 Base 设计体系（配色、排版、组件语义保持一致）。
- 登录交互仅依赖现有 `/api/login/{platforms|start|session/{id}|status/{platform}|logout/{platform}|sessions}` 路由，不新增或改写后端接口。
- 所有登录类型（二维码 / Cookie / 手机号）必须在同一界面内提供顺畅的切换体验，并保持清晰的状态提示与加载反馈。
- 表单与按钮需兼顾可访问性（语义化标签、键盘操作、可见的聚焦状态），并覆盖移动/桌面双端布局。
- 页面脚本在捕获异常时应给出可执行的修复建议，避免静默失败或无提示的错误状态。

## 核心亮点

- 🤖 **MCP 原生支持**：基于 FastMCP，Claude、ChatGPT 等助手可直接调用爬虫能力。
- ⚙️ **任务级配置**：Pydantic Settings 生成独立配置对象，彻底摆脱全局变量竞争。
- 🚀 **常驻服务**：Playwright 浏览器上下文复用，避免每次冷启动 5-10 秒的等待。
- 🔐 **全新登录链路**：二维码生成即时返回、后端协程轮询、超时自动清理，彻底告别 CLI 阻塞式扫码体验。
- 🧩 **模块化架构**：Endpoint / Service / Crawler 分层清晰，按需插拔新平台。

## 系统架构

```text
┌───────────────────────────────┐
│ AI 助手 (Claude / ChatGPT 等) │
└───────────────┬───────────────┘
                │ MCP (SSE / STDIO)
                ▼
┌───────────────────────────────┐
│ FastMCP Service (main.py)     │
│  ├─ Endpoint Registry         │
│  │    └─ /admin, /mcp/...     │
│  ├─ Login Service             │
│  │    └─ Bilibili LoginAdapter│
│  └─ Platform Services         │
│       └─ Bilibili Service     │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Playwright Browser Context    │
│  ├─ 扫码登录 (持久化 user-data) │
│  └─ 数据抓取 (Crawler 层)      │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ 数据持久化 (./data / Store)    │
└───────────────────────────────┘
```

## 登录流程概览

1. `POST /api/login/start`  
   建立 Playwright 持久化上下文，生成并返回二维码（base64）与 `session_id`，同时启动后台协程轮询登录状态。
2. `GET /api/login/session/{session_id}`  
   前端根据 `status`、`message` 与 `qr_code_base64` 判断展示二维码、提示超时或登录成功。
3. 登陆成功后，同步刷新平台登录态缓存（基于同一浏览器实例写入的 user-data-dir），后端自动回收浏览器资源。

## 架构对比

| 维度 | MediaCrawler 原始 | 本项目（MCP 服务） |
| --- | --- | --- |
| 调用方式 | CLI 命令行 | MCP 工具（AI 原生支持） |
| 配置管理 | 全局 `config.py` 文件 | Pydantic 参数化对象 |
| 并发安全 | ❌ 全局变量竞争 | ✅ 独立配置上下文 |
| 浏览器管理 | 每次启动（5-10 秒） | 服务常驻，实例复用 |
| 集成方式 | 无（只能命令行） | 标准 MCP 协议 |
| AI 可用性 | ❌ 需包装 shell | ✅ 直接调用工具 |
| 扩展性 | 修改 `config.py` | 继承 `BaseService` |
| 代码质量 | 脚本风格 | 企业级架构（Service + Endpoint） |
| 登录流程 | CLI 阻塞等待扫码 | Session/Status 解耦 + 后台轮询 |

## 快速开始

```bash
poetry install
poetry run playwright install chromium
python main.py --transport both

# 访问入口
# MCP SSE:      http://localhost:9090/sse
# 管理页面:     http://localhost:9090/admin
# 状态概要 API: http://localhost:9090/api/status/summary
```

常用环境变量示例：

```bash
APP__ENV=dev
APP__DEBUG=true
APP__PORT=9090
PLATFORM__ENABLED_PLATFORMS=all
BROWSER__HEADLESS=false
CRAWL__MAX_NOTES_COUNT=15
STORE__OUTPUT_DIR=./data
```

## 代码导览

- `main.py`：服务入口。
- `app/api_service.py`：应用工厂与路由挂载。
- `app/api/endpoints/mcp/bilibili.py`：B 站 MCP 工具。
- `app/core/login/bilibili/adapter.py`：B 站登录适配器（二维码生成、轮询、状态流转）。
- `app/crawler/platforms/bilibili/service.py`：B 站业务服务层。
- `app/config/settings.py`：配置中心（Pydantic Settings）。
- `app/providers/logger.py`：日志封装（loguru）。

## 管理与状态接口

- 管理页：`http://localhost:9090/admin`
- 登录接口：`/api/login/start`、`/api/login/session/{session_id}`、`/api/login/status/{platform}`、`/api/login/logout/{platform}`
- 系统状态：`/api/status/{system|data|services|platforms|summary}`

## 协作提示

- 修改代码前请先阅读 `Agent.MD`，遵守统一的目录、命名、提交规范。
- 日志、配置、缓存等基础设施已经封装，优先复用，避免重复造轮子。
- 欢迎前端/全栈伙伴补齐 Admin UI、扫码轮询界面等体验；也可以直接认领 Issue/PR。

## 常见问题

- **首次跑不起来？** 执行 `poetry install` 和 `poetry run playwright install chromium`。
- **二维码没有返回？** 检查日志是否提示截图失败或超时，必要时设置 `BROWSER__HEADLESS=false` 观察浏览器行为。
- **已扫码但状态没更新？** 确认后台轮询协程还在运行，查看 `app/core/login/bilibili/adapter.py` 中的日志输出。

如果这个项目对你有帮助，欢迎点个 Star ⭐️。感谢所有贡献者和即将加入的你！
