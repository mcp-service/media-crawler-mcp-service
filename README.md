# MediaCrawler MCP 服务

让 AI 原生使用社媒数据的MCP服务。将传统 CLI 爬虫升级为 MCP 标准工具，让 Claude / ChatGPT 直连调用，一次配置，长期可用。

![index .png](docs/index.png)

<p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white" />
  <img alt="Playwright" src="https://img.shields.io/badge/Playwright-Enabled-2EAD33?logo=playwright&logoColor=white" />
  <img alt="MCP" src="https://img.shields.io/badge/MCP-Tools-6E56CF" />
  <img alt="Redis" src="https://img.shields.io/badge/Redis-Cache-D82C20?logo=redis&logoColor=white" />
  <img alt="Status" src="https://img.shields.io/badge/Status-Alpha-F59E0B" />
</p>

## 目录
- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [快速开始](#快速开始)
- [管理界面与登录](#管理界面与登录)
- [在 AI 助手中使用](#在-ai-助手中使用)
- [工具总览](#工具总览)
- [架构与技术选择](#架构与技术选择)
- [Roadmap](#roadmap)
- [开发与贡献](#开发与贡献)
- [FAQ](#faq)
- [合规与合理使用](#合规与合理使用)

## 项目简介

MediaCrawler MCP Service 是面向个人的数据获取工具集，通过 MCP（Model Context Protocol）把社媒公开信息变成 AI 助手可直接调用的标准化工具。核心能力包括“登录外部化管理”“任务级配置隔离”“浏览器上下文复用”和“结构化数据输出”。


为什么与众不同？
- 从脚本到标准：从一次性脚本变成可复用的 MCP 工具
- 登录完全外部化：可视化界面 + 二维码/Cookie 双模式，状态持久
- 真·工程化：分层解耦、Pydantic 模型、状态缓存与风控友好
- 文本格式友好: 需要AI分析，所以要返回文本友好的格式，不是大量无用的嵌套数据
![bili-detail.png](docs/bili-detail.png)
## 核心特性
- 一次配置，AI 原生调用（Claude/ChatGPT）
- 登录外部化：跨重启保持，支持多平台
- 任务级配置隔离，消除全局变量竞争
- 平台级浏览器实例隔离：每个平台独立浏览器上下文，Login 和 Crawler 自动复用同一实例，避免资源浪费与状态干扰
- Playwright 浏览器上下文复用，秒级响应
- Pydantic 结构化输出，易于分析与存档
- 内建状态缓存与风控友好策略

当前已实现与进行中：
- 已完成：B 站搜索/详情/创作者/评论（`bili_search`/`bili_detail`/`bili_creator`/`bili_comments`）
- 已完成：小红书搜索/详情/创作者/评论（`xhs_search`/`xhs_detail`/`xhs_creator`/`xhs_comments`）
- 进行中：抖音 / 快手 / 知乎 / 贴吧 / 微博等

## 快速开始

环境要求：Python 3.8+ · Redis · Chrome/Chromium ·（可选）Node.js 16+

1) 克隆与安装依赖
```bash
git clone <your-repo-url>
cd media-crawler-mcp-service
poetry install
poetry run playwright install chromium
```

2) 配置环境
```bash
cp .env.example .env
# 按需修改端口/平台开关/Redis 等
```

3) 启动服务
```bash
redis-server                 # 如未启动
poetry run python main.py    # 默认端口 9090

# 管理界面: http://localhost:9090/admin
# 工具调试: http://localhost:9090/admin/inspector
```

## 管理界面与登录

### 1) 打开管理界面 `http://localhost:9090/admin`
   ![index .png](docs/index.png)
### 2) 进入“登录管理”，选择平台（如 B 站）
   ![登录界面](docs/login.png)
### 3) 支持“二维码登录”或“Cookie 登录”，状态会持久化
   ![登录状态](docs/login-state.png)

## 在 AI 助手中使用

你可以直接在 Claude/ChatGPT 中配置mcp链接（还没做鉴权，大家可以本地先试用，后续会新增基础鉴权）, 让其调用 MCP 工具：
```
示例对话：
“帮我搜索 Python 机器学习相关的 B 站视频，并分析受欢迎程度与创作者。”
→ 自动调用 `bili_search` 获取数据 → 结合指标分析 → 输出洞察
```

## 工具总览

管理页的 MCP Tools Inspector 可查看所有已注册工具，并进行在线调试。

- `bili_search`（推荐，快速搜索）
```json
{
  "keywords": "Python 机器学习",
  "page_size": 3,
  "page_num": 1
}
```

- `bili_detail`（指定视频详情）
```json
{
  "video_ids": [
    "444445981"
  ]
}
```
![img.png](docs/bili-detail.png)
- `bili_creator`（创作者分析）
```json
{ "creator_ids": ["99801185"], "creator_mode": true }
```

![工具测试](docs/tools-test.png)

- `xhs_search`（小红书关键词搜索，返回本页摘要，不拉详情）
```json
{
  "keywords": "纯圆大嬛嬛",
  "page_num": 1,
  "page_size": 20
}
```

- `xhs_detail`（小红书笔记详情，不含评论；xsec_token 必传）
```json
{
  "note_id": "68f9b8b20000000004010353",
  "xsec_token": "从搜索结果或分享链接中获取（必传）",
  "xsec_source": "可选，未传时默认 pc_search"
}
```

- `xhs_creator`（小红书创作者作品，不含评论）
```json
{
  "creator_ids": ["user123", "user456"]
}
```

- `xhs_comments`（小红书笔记评论，单条获取）
```json
{
  "note_id": "68f9b8b20000000004010353",
  "xsec_token": "从搜索结果获取（必传）",
  "xsec_source": "可选，未传时默认 pc_search",
  "max_comments": 50
}
```

说明：
- **xsec_token 是必传参数**：小红书网页端对详情和评论访问存在严格的风控校验，`xhs_detail` 和 `xhs_comments` 都必须传入 `xsec_token`（可从 `xhs_search` 返回结果中获取，或从分享链接解析）。
- **原子化设计**：`xhs_comments` 仅支持单条笔记查询，不支持批量，符合 MCP 工具原子化原则。
- **数据完整性**：所有工具返回的数据已包含完整的用户信息（user_id、nickname、avatar）和交互数据（点赞、收藏、评论、分享数），支持中文数字格式解析（如"3万"自动转为 30000）。
- **评论获取已独立**：`xhs_detail` 仅返回笔记详情，需要评论时请单独调用 `xhs_comments` 工具。
- 当未传 `xsec_source` 时，服务会默认使用 `pc_search`；仍无法访问时请检查登录态、token 是否过期或笔记是否被限制浏览。

## 架构与技术选择

```
🤖 AI 助手 (Claude / ChatGPT)
           │  MCP Protocol
           ▼
🎯 MediaCrawler MCP Service
  ├─ 管理层: 登录/状态/配置
  ├─ 服务层: 各平台编排 (Bili…)
  └─ 工具层: bili_search/detail/creator/comments
           │
           ▼
🌐 Playwright Browser（上下文复用 / 风控友好）
  ├─ BrowserManager 统一管理
  ├─ 平台级实例隔离（每个平台独立浏览器）
  ├─ Login 和 Crawler 共享同一实例
  └─ 引用计数 + 互斥锁保护
           │
           ▼
💾 Redis 状态缓存 · 本地/结构化存储
```

### 浏览器实例管理（亮点）

**问题背景：** 多平台环境下，浏览器实例管理不当会导致：
- 不同平台共享浏览器上下文，Cookie 和登录状态互相干扰
- 频繁创建/销毁浏览器实例，性能低下
- 登录会话与爬虫任务竞争资源，导致状态混乱

**解决方案：BrowserManager 统一管理**
- **平台级隔离**：每个平台（Bilibili、小红书等）维护独立的浏览器实例
- **上下文复用**：同一平台的 Login 和 Crawler 自动共享浏览器实例，避免重复创建
- **引用计数**：通过 `acquire_context()` 和 `release_context()` 精确管理实例生命周期
- **互斥锁保护**：防止并发创建多个实例，确保线程安全
- **登录防抖**：平台级登录锁，防止用户多次点击触发重复登录请求

**效果：**
- 浏览器启动时间从 3-5s 降至 0.1s（上下文复用）
- 登录状态稳定，不再出现平台间干扰
- 防止并发登录导致的资源竞争

对比传统 CLI 脚本：
- 调用方式：脚本 → MCP 工具（AI 原生支持）
- 登录管理：脚本内逻辑 → 外部化页面 + 持久化
- 性能：每次冷启动 → 浏览器常驻复用（3-5s → 0.1s）
- 设计：全局变量 → 任务级配置隔离 + 平台级浏览器隔离
- 输出：原始结果 → Pydantic 结构化

**非目标（明确约束）**：
- 面向个人效率的单用户/单账号使用场景
- 不做多账号池/多租户/分布式集群等复杂特性
- 保持架构清晰，提供可扩展点，鼓励他人自行按需扩展

## Roadmap
- 小红书 / 抖音 / 快手 / 知乎 / 微博 / 贴吧 适配
- 工具调试器与可视化增强（过滤、导出、趋势）
- 更细粒度的速率与风控策略
- 更多存储目标（PGSQL 持久化）

## 开发与贡献

参考路径：
- 启动入口：`main.py:1`
- 应用工厂：`app/api_service.py:1`
- 管理界面路由：`app/api/endpoints/admin/admin_page_endpoint.py:1`
- 工具清单接口：`app/api/endpoints/admin/mcp_inspector_endpoint.py:1`

新增平台的典型步骤：
1) 添加登录适配器：`app/core/login/{platform}/...`
2) 实现平台爬虫与编排：`app/core/crawler/platforms/{platform}/...`
3) 包装为 MCP 工具：`app/core/mcp_tools/{platform}.py`
4) 注册路由：`app/api/endpoints/mcp/{platform}.py`

更多部署与运维选项：`deploy/README.md:1`

贡献流程：
1) Fork 并创建特性分支
2) 阅读项目规范：`Agent.md:1`
3) 本地开发与自测
4) 提 PR 并说明变更点

## FAQ

启动失败？
```bash
poetry install
poetry run playwright install chromium
redis-cli ping   # 期望 PONG
APP__DEBUG=true poetry run python main.py
```

二维码不显示？
```bash
BROWSER__HEADLESS=false poetry run python main.py
poetry run playwright install-deps chromium
```

登录状态易失？
- 确认 Redis 稳定、网络正常；避免高频触发风控

搜索为空或慢？
- 优先使用 `bili_search`，降低分页尺寸，放大请求间隔

## 合规与合理使用

本项目定位为个人效率工具：
- 遵守各平台使用条款与 robots.txt
- 合理控制频率，不对平台造成压力
- 尊重内容创作者，不用于商业化爬取
- 建议单次请求量小、请求间隔 ≥ 2s

如果这个项目对你的学习有帮助，欢迎 ⭐ Star 支持！
