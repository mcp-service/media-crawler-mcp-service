# MediaCrawler MCP 服务

> **🎯 学习效率工具，而非爬虫工具**  
> 本项目致力于为个人学习和研究提供便捷的数据获取能力，请合理使用，避免高频访问给平台带来压力。

---

一个将传统 CLI 爬虫升级为现代化 AI 助手工具的创新项目。通过 MCP (Model Context Protocol) 协议，让 Claude、ChatGPT 等 AI 助手能够直接调用社交媒体平台的数据获取能力，为个人学习和内容研究提供强大支持。

## ✨ 核心创新

### 🔄 **从 CLI 到 MCP 的范式转变**
- **传统方式**: 命令行脚本，每次执行都需要重新登录、配置
- **本项目**: MCP 标准化工具，AI 助手原生调用，一次配置持久可用

### 🎨 **登录管理外部化**
- **创新点**: 将登录逻辑从业务代码中完全分离
- **管理界面**: 可视化登录状态管理，支持二维码/Cookie 双模式
- **持久化**: 登录状态跨服务重启保持，智能风控规避

### 🧠 **智能化架构设计**
- **任务级配置**: Pydantic Settings 确保配置隔离，消除全局变量竞争
- **浏览器复用**: Playwright 持久化上下文，避免重复启动开销
- **分层解耦**: Service/Endpoint/Crawler 清晰分离，易于扩展新平台

### 🛡️ **风控对抗与状态管理**
- **智能缓存**: 多层状态缓存策略，减少不必要的平台检查
- **风控规避**: 模拟真实用户行为，合理控制请求频率
- **故障恢复**: 网络异常、Cookie 失效的自动处理机制

## 🎯 项目定位

**🎓 个人学习效率工具**
- 面向内容研究、学习分析、趋势观察等教育场景
- 支持小规模、合理频率的数据获取需求
- 强调工具的学习价值，而非商业爬取能力

**🚫 明确的非目标**
- ❌ 不是商业级爬虫服务
- ❌ 不支持大规模、高频率数据采集
- ❌ 不提供多账号池、分布式集群功能
- ❌ 不鼓励违反平台使用条款的行为

**⚖️ 使用原则**
- ✅ 遵守平台 robots.txt 和使用条款
- ✅ 控制请求频率，避免给平台造成负担
- ✅ 仅用于个人学习、研究、内容分析
- ✅ 尊重内容创作者权益和平台生态

## 🚀 当前进展

- ✅ **B 站平台完整重构**: `bili_search`、`bili_detail`、`bili_creator`、`bili_comments` 等工具
- 🔄 **登录体系焕新**: 非阻塞二维码登录 + 实时状态轮询 + 智能风控规避
- 🔧 **架构优化**: 快速搜索模式，搜索与详情数据分离，响应速度提升 80%+
- 🚧 **多平台迁移中**: 小红书、抖音、快手等平台适配统一架构中

后续会持续接入：小红书，抖音，快手，微博、贴吧、知乎等主流平台的公开信息抓取。

## 🏗️ 系统架构

```text
┌─────────────────────────────────────┐
│ 🤖 AI 助手 (Claude / ChatGPT 等)   │
│    ├─ 内容分析与总结                │
│    ├─ 趋势研究与洞察                │
│    └─ 学习辅助与知识提取            │
└─────────────────┬───────────────────┘
                  │ MCP Protocol
                  ▼
┌─────────────────────────────────────┐
│ 🎯 MediaCrawler MCP Service        │
│  ┌─ 🔧 管理层                      │
│  │   ├─ 登录状态管理 (/api/login)   │
│  │   ├─ 系统监控 (/api/status)     │
│  │   └─ 配置管理 (/api/config)     │
│  ├─ 🛠️ 服务层                      │
│  │   ├─ Bilibili Service (已完成)  │
│  │   ├─ XiaoHongShu Service (开发中)│
│  │   └─ 更多平台... (欢迎贡献)      │
│  └─ 🎨 工具层                      │
│      ├─ bili_search (快速搜索)     │
│      ├─ bili_detail (详细信息)     │
│      ├─ bili_creator (创作者信息)  │
│      └─ bili_comments (评论获取)   │
│      └─  ...  ....                 │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 🌐 Playwright Browser Engine       │
│  ├─ 持久化登录上下文                │
│  ├─ 智能风控规避                    │
│  └─ 真实用户行为模拟                │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ 💾 数据层                           │
│  ├─ Redis (状态缓存)                │
│  ├─ 本地存储 (./data)               │
│  └─ 结构化输出 (JSON/CSV)           │
└─────────────────────────────────────┘
```

## 🔄 技术架构对比

| 维度 | 传统 MediaCrawler | 本项目 (MCP 服务) |
|------|------------------|-------------------|
| **调用方式** | CLI 命令行脚本 | MCP 标准化工具 |
| **AI 集成** | ❌ 需要复杂封装 | ✅ 原生支持 |
| **登录管理** | 每次手动扫码 | 🎯 **外部化管理界面** |
| **状态持久化** | ❌ 重启即丢失 | ✅ 跨重启保持 |
| **配置管理** | 全局变量竞争 | 🎯 **任务级隔离** |
| **浏览器性能** | 每次冷启动 5-10s | 🎯 **常驻复用** |
| **风控处理** | 硬编码策略 | 🎯 **智能缓存机制** |
| **架构扩展性** | 脚本式耦合 | 🎯 **Service/Endpoint 分层** |
| **数据格式** | 原始爬取数据 | 🎯 **Pydantic 结构化** |

## 🚀 快速开始

### 📋 环境要求
- Python 3.8+
- Node.js 16+ (可选，用于前端开发)
- Redis (用于状态缓存)
- Chrome/Chromium 浏览器

### 🛠️ 本地部署

#### 1. 项目初始化
```bash
# 克隆项目
git clone <your-repo-url>
cd media-crawler-mcp-service

# 安装 Python 依赖
poetry install

# 安装浏览器驱动
poetry run playwright install chromium
```

#### 2. 环境配置
创建 `.env` 配置文件：

```bash
# === 应用基础配置 ===
APP__ENV=dev
APP__DEBUG=true
APP__PORT=9090

# === 平台配置 ===
# 启用的平台 (bili=B站, xhs=小红书, dy=抖音, ks=快手)
PLATFORM__ENABLED_PLATFORMS=bili

# === 性能与安全配置 ===
# 开发模式建议关闭无头模式，便于观察登录过程
BROWSER__HEADLESS=false

# 合理控制爬取频率，避免给平台造成压力
CRAWL__MAX_NOTES_COUNT=10
CRAWL__ENABLE_GET_COMMENTS=true
CRAWL__MAX_COMMENTS_PER_NOTE=5
CRAWL__CRAWL_INTERVAL=2  # 请求间隔 2 秒

# === 数据存储配置 ===
STORE__OUTPUT_DIR=./data
STORE__SAVE_FORMAT=json

# === Redis 配置 (状态缓存) ===
REDIS__HOST=localhost
REDIS__PORT=6379
REDIS__DB=0
```

#### 3. 启动服务
```bash
# 启动 Redis (如果未启动)
redis-server

# 启动 MCP 服务
poetry run python main.py

# 🎉 服务启动成功！
# 管理界面: http://localhost:9090/admin
# 工具调试: http://localhost:9090/admin (点击 MCP Tools Inspector)
```

### 🔐 平台登录配置

#### 1. 访问管理界面
```
📱 浏览器打开: http://localhost:9090/admin
```

#### 2. 配置平台登录
- **B 站登录**: 点击"登录管理" → 选择"哔哩哔哩"
- **二维码模式**: 推荐首次使用，安全便捷
- **Cookie 模式**: 适合批量配置或 Cookie 已知的情况

![登录界面](docs/login.png)

#### 3. 验证登录状态
登录成功后可在管理界面看到：
- ✅ 绿色状态：已登录且有效
- ❌ 红色状态：未登录或已过期
- 🔄 黄色状态：正在验证中

![登录状态](docs/login-state.png)

### 🧪 工具测试体验

#### 1. 打开工具调试器
```
🔧 访问: http://localhost:9090/admin → MCP Tools Inspector
```

#### 2. 测试搜索功能
```json
// bili_search - 快速搜索 (优化版，响应速度提升 80%+)
{
  "keywords": "Python 机器学习",
  "page_size": 3,
  "page_num": 1
}
```

#### 3. 获取详细信息
```json
// bili_detail - 获取完整视频信息
{
  "video_ids": ["BV1xx411c7mD"]
}
```

#### 4. 创作者分析
```json
// bili_creator - 分析创作者内容
{
  "creator_ids": ["123456"],
  "creator_mode": true
}
```

![工具测试](docs/tools-test.png)

### 🎯 AI 助手集成

配置完成后，你的 AI 助手就能直接调用这些工具：

```
🤖 与 Claude 对话示例:
"帮我搜索一下 Python 教程相关的 B 站视频，并分析一下哪些内容比较受欢迎"

Claude 会自动调用:
1. bili_search 搜索相关视频
2. 分析播放量、评论数等数据
3. 总结趋势和推荐内容
```

### ⚠️ 重要提醒

**🎓 学习导向使用**
- 建议单次搜索不超过 20 条数据
- 请求间隔建议 2 秒以上
- 主要用于学习、研究、内容分析

**🛡️ 风控友好**
- 系统已内置智能风控规避
- 异常时会自动降低请求频率
- 遇到限制时请稍后再试

**⚖️ 合规使用**
- 遵守平台使用条款
- 尊重内容创作者权益
- 不用于商业爬取目的

## 🏗️ 代码架构导览

### 📁 核心目录结构
```
media-crawler-mcp-service/
├── 🎯 main.py                    # 服务启动入口
├── 📦 app/
│   ├── 🔧 api_service.py         # FastMCP 应用工厂
│   ├── 🌐 api/endpoints/         # API 路由层
│   │   ├── 🔐 login/             # 登录管理接口
│   │   ├── 📊 admin/             # 系统管理接口
│   │   └── 🛠️ mcp/               # MCP 工具路由
│   ├── 💼 core/                  # 核心业务层
│   │   ├── 🔑 login/             # 登录服务架构
│   │   │   ├── 📝 service.py     # 登录服务编排
│   │   │   ├── 💾 storage.py     # 状态持久化
│   │   │   └── 🎭 bilibili/      # B站登录适配器
│   │   ├── 🕷️ crawler/           # 爬虫引擎层
│   │   │   └── 📺 platforms/     # 平台实现
│   │   └── 🧰 mcp_tools/         # MCP工具定义
│   │       ├── 🔧 bilibili.py    # B站工具实现
│   │       └── 📊 schemas/       # 数据模型定义
│   ├── ⚙️ config/settings.py     # 配置管理中心
│   └── 🎨 admin/                 # 管理界面
│       ├── 🖼️ templates/         # HTML模板
│       └── 📄 static/            # 前端资源
└── 📚 MediaCrawler/              # 原始爬虫库 (参考实现)
```

### 🎯 核心模块职责

#### 🔐 登录管理层 (`app/core/login/`)
```python
# 创新亮点：外部化登录管理
- service.py       # 登录服务编排，支持多平台
- storage.py       # Redis 状态缓存，跨重启持久化  
- bilibili/        # B站专用适配器，智能风控处理
  ├── adapter.py   # 登录流程适配 (二维码/Cookie)
  └── models.py    # 登录状态数据模型
```

#### 🕷️ 爬虫引擎层 (`app/core/crawler/`)
```python
# 创新亮点：任务级配置隔离
- CrawlerContext   # 任务上下文，避免全局变量竞争
- BilibiliCrawler  # B站爬虫实现
  ├── search_by_keywords_fast()  # 🎯 新增快速搜索
  ├── search_by_keywords()       # 传统详细搜索  
  └── get_specified_videos()     # 视频详情获取
```

#### 🧰 MCP工具层 (`app/core/mcp_tools/`)
```python
# 创新亮点：Pydantic 结构化输出
- bilibili.py              # MCP 工具实现
  ├── bili_search()         # 快速搜索 (简化数据)
  ├── bili_detail()         # 详情获取 (完整数据)
  └── bili_creator()        # 创作者分析
- schemas/bilibili.py      # 数据模型定义
  ├── BilibiliVideoSimple  # 搜索结果模型
  └── BilibiliVideoFull    # 详情结果模型
```

### 🌊 数据流转图

```text
🤖 AI助手请求
    ↓ MCP调用
🎯 MCP Tools (bili_search)
    ↓ 业务编排
💼 Bilibili Service 
    ↓ 上下文构建
🕷️ BilibiliCrawler.search_by_keywords_fast()
    ↓ 登录检查
🔐 Login Service (智能缓存)
    ↓ API调用
🌐 Bilibili API (search_video_by_keyword)
    ↓ 数据处理
📊 Pydantic模型验证 (BilibiliVideoSimple)
    ↓ 结构化输出
🎉 JSON响应 (简化字段，快速返回)
```

## 🔌 API 接口文档

### 🔐 登录管理接口
```http
# 获取支持的平台列表
GET /api/login/platforms

# 启动登录流程 (二维码/Cookie)
POST /api/login/start
{
  "platform": "bili",
  "login_type": "qrcode",  # qrcode | cookie
  "cookie": "optional_cookie_string"
}

# 查询登录会话状态
GET /api/login/session/{session_id}

# 获取平台登录状态
GET /api/login/status/{platform}

# 退出平台登录
POST /api/login/logout/{platform}

# 获取所有会话信息
GET /api/login/sessions
```

### 📊 系统状态接口
```http
# 系统资源状态
GET /api/status/system

# 数据存储状态  
GET /api/status/data

# 服务运行状态
GET /api/status/services

# 平台连接状态
GET /api/status/platforms

# 综合状态概览
GET /api/status/summary
```

### ⚙️ 配置管理接口
```http
# 获取平台配置
GET /api/config/platforms

# 更新平台配置
PUT /api/config/platforms

# 获取爬虫配置
GET /api/config/crawler

# 更新爬虫配置  
PUT /api/config/crawler

# 获取当前完整配置
GET /api/config/current
```

## 🎓 开发指南

### 🔧 添加新平台支持

1. **创建平台适配器**
```python
# app/core/login/{platform}/adapter.py
class XiaoHongShuLoginAdapter(BaseLoginAdapter):
    async def start_login(self, payload):
        # 实现平台特定的登录逻辑
        pass
```

2. **实现爬虫服务**
```python  
# app/core/crawler/platforms/{platform}/service.py
async def search(keywords: str, **kwargs) -> Dict[str, Any]:
    # 实现平台搜索逻辑
    pass
```

3. **定义MCP工具**
```python
# app/core/mcp_tools/{platform}.py
async def {platform}_search(keywords: str) -> str:
    # MCP工具包装
    result = await {platform}_core.search(keywords=keywords)
    return json.dumps(result, ensure_ascii=False, indent=2)
```

4. **注册工具路由**
```python
# app/api/endpoints/mcp/{platform}.py
from app.core.mcp_tools.{platform} import {platform}_search

bp.mcp_tool()({platform}_search)
```

### 📐 编码规范

#### 🎯 目录命名约定
- `snake_case` 用于文件和目录名
- 平台代码使用官方简称 (bili/xhs/dy/ks)
- 功能模块按职责分层 (login/crawler/mcp_tools)

#### 🔧 代码规范
```python
# 类命名：PascalCase
class BilibiliLoginAdapter:
    pass

# 函数命名：snake_case  
async def search_by_keywords_fast():
    pass

# 常量命名：UPPER_SNAKE_CASE
STATUS_CACHE_TTL = 3600

# 私有方法：_前缀
def _process_search_result():
    pass
```

#### 📝 文档规范
- 所有公共方法必须包含详细的 docstring
- 使用类型注解确保代码可读性
- 重要配置项需要在代码中添加注释说明

## 🤝 贡献指南

### 🎯 贡献重点方向

**🎨 前端UI优化** (急需支持!)
- 登录界面 UX 改进
- 工具调试器功能增强  
- 状态监控可视化
- 移动端适配优化

**🕷️ 新平台适配**
- 小红书 (XiaoHongShu) 
- 抖音 (Douyin)
- 快手 (Kuaishou)
- 知乎 (Zhihu)

**🔧 工具增强**
- 数据导出功能
- 批量操作支持
- 高级筛选条件
- 内容分析工具

### 📋 开发流程

1. **Fork 项目** 并创建特性分支
2. **阅读 `Agent.MD`** 了解项目规范
3. **本地开发测试** 确保功能正常
4. **提交 PR** 并描述变更内容
5. **代码审查** 通过后合并主分支

### 🛡️ 合规要求

在贡献代码时，请确保：
- ✅ 遵循平台API使用限制
- ✅ 实现合理的请求频率控制
- ✅ 添加适当的错误处理
- ✅ 包含必要的安全检查
- ✅ 编写相应的测试用例

## ❓ 常见问题

### 🚀 部署相关

**Q: 首次启动失败怎么办？**
```bash
# 检查依赖安装
poetry install
poetry run playwright install chromium

# 检查 Redis 服务
redis-cli ping  # 应返回 PONG

# 查看详细错误日志
APP__DEBUG=true poetry run python main.py
```

**Q: 二维码不显示？**
```bash
# 确保浏览器可以正常启动
BROWSER__HEADLESS=false poetry run python main.py

# 检查是否缺少浏览器依赖
poetry run playwright install-deps chromium
```

### 🔐 登录相关

**Q: 登录状态经常丢失？**
- 检查 Redis 服务是否稳定运行
- 确认网络连接正常，避免频繁请求触发风控
- 查看日志确认是否有异常状态覆盖

**Q: Cookie 登录失败？**
- 确保 Cookie 格式正确且未过期
- 检查 Cookie 是否包含必要的认证字段
- 尝试重新获取有效的 Cookie

### 🛠️ 工具使用

**Q: 搜索结果为空？**
- 确认对应平台已成功登录
- 检查关键词是否过于特殊
- 降低搜索频率，避免触发限制

**Q: 响应速度慢？**
- 使用 `bili_search` 而非 `bili_detail` 进行快速搜索
- 减少 `page_size` 和 `page_num` 参数
- 检查网络连接质量

---

## 🌟 致谢

感谢所有为项目贡献代码、建议和反馈的开发者们！

**特别致谢：**
- 原始 MediaCrawler 项目提供的技术基础
- FastMCP 框架的优秀设计理念  
- 所有测试和使用本项目的学习者们

如果这个项目对你的学习和研究有帮助，欢迎 ⭐ Star 支持！

---

> **💡 记住项目初心**  
> 这是一个学习效率工具，而非商业爬虫服务。让我们一起合理使用，共同维护健康的网络环境！
