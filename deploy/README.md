# 生产部署说明

## 架构概述

本项目使用 **程序化 uvicorn** (Programmatic uvicorn) 方式部署,而不是传统的 `uvicorn app:app` 命令行方式。

### 为什么这样设计?

#### 1. **多服务协调**
我们需要同时运行三种服务:
- **STDIO MCP Service**: 用于本地客户端
- **SSE MCP Service** (端口 9090): 用于Web客户端
- **Admin Service** (端口 9091): 用于人工管理

这些服务需要在同一个进程中协调运行,共享配置和资源。

#### 2. **FastMCP 的特殊性**
FastMCP 提供了 `run_stdio_async()` 和 `run_sse_async()` 方法,这些方法需要特殊处理:
- STDIO 模式需要读取 stdin/stdout
- SSE 模式我们 patch 了它的实现 (见 `app/api_service.py:53-61`)

#### 3. **代码中已经使用 uvicorn**

**SSE 服务** (`app/api_service.py:94-101`):
```python
config = uvicorn.Config(
    starlette_app,
    host=app.settings.host,
    port=app.settings.port,
    log_level=app.settings.log_level.lower(),
)
server = uvicorn.Server(config)
await server.serve()
```

**Admin 服务** (`main.py:22-30`):
```python
config = uvicorn.Config(
    admin_app,
    host="0.0.0.0",
    port=port,
    log_level="info",
    loop="asyncio"
)
server = uvicorn.Server(config)
await server.serve()
```

### 当前启动流程

```
Docker CMD: python -u main.py --transport sse --admin
           ↓
      main() 函数
           ↓
    ┌──────┴──────┐
    ↓             ↓
MCP Service   Admin Service
(port 9090)   (port 9091)
    ↓             ↓
uvicorn.Server  uvicorn.Server
    ↓             ↓
    └──────┬──────┘
           ↓
   asyncio.gather()
   (并发运行)
```

## 为什么不用 `uvicorn app:app` 命令?

### 传统方式的限制

如果用传统的 uvicorn 命令:
```bash
# 只能启动一个服务
uvicorn app.admin:admin_app --host 0.0.0.0 --port 9091
```

问题:
1. ❌ 只能启动一个服务 (要么 MCP,要么 Admin)
2. ❌ 无法处理 STDIO 模式
3. ❌ 无法协调多个服务的生命周期
4. ❌ 无法共享应用状态和配置

### 当前方式的优势

```bash
python -u main.py --transport sse --admin
```

优势:
1. ✅ 同时运行多个服务 (MCP + Admin)
2. ✅ 支持三种传输模式 (stdio/sse/both)
3. ✅ 统一的配置管理
4. ✅ 共享资源 (数据库连接、Redis、Logger)
5. ✅ 内部使用 uvicorn.Server,性能相同

## 生产环境考虑

### 1. 进程管理

**当前方案** (推荐):
```yaml
# docker-compose.yml
services:
  mcp-tools:
    command: python -u main.py --transport sse --admin
    restart: unless-stopped
```

**替代方案** (如果需要独立进程管理):
```yaml
# 使用 supervisord 分别管理两个服务
command: supervisord -c /app/deploy/supervisord.conf
```

### 2. 性能调优

#### 单容器多Worker (不推荐)
由于我们有自定义的启动逻辑,使用多个 uvicorn worker 会有问题:
```bash
# ❌ 这样不行
gunicorn app:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

#### 多容器扩展 (推荐)
使用 Docker Compose 或 Kubernetes 扩展容器数量:
```bash
# Docker Compose
docker-compose up --scale mcp-tools=3

# Kubernetes
kubectl scale deployment mcp-tools --replicas=3
```

### 3. 监控和日志

当前配置:
- `python -u`: 无缓冲输出,实时查看日志
- 日志输出到 stdout/stderr,方便 Docker 收集
- 可以用 `docker logs` 查看

建议添加:
- Prometheus metrics endpoint
- Sentry 错误追踪
- ELK/Loki 日志聚合

## 常见问题

### Q: 为什么不用 gunicorn?

A: Gunicorn 是为传统 WSGI/ASGI 应用设计的,我们的启动逻辑是自定义的:
- FastMCP 的 STDIO 模式需要特殊处理
- 多个异步服务需要 `asyncio.gather` 协调
- 使用 gunicorn 会失去这些灵活性

### Q: 性能会不会差?

A: **不会**,因为:
- 内部使用 `uvicorn.Server`,性能完全相同
- Uvicorn 本身就是高性能 ASGI 服务器
- 单个容器可以处理大量并发连接
- 需要扩展时,直接扩展容器数量

### Q: 如何做负载均衡?

A: 在容器前加负载均衡器:
```
       Nginx/Traefik
              ↓
    ┌─────────┼─────────┐
    ↓         ↓         ↓
Container1  Container2  Container3
(9090/9091) (9090/9091) (9090/9091)
```

### Q: 如何优雅停机?

A: 添加信号处理:
```python
# main.py
import signal

def shutdown_handler(sig, frame):
    get_logger().info("收到停机信号,开始优雅关闭...")
    # 清理资源
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)
```

## 开发 vs 生产

### 开发环境
```bash
# 直接运行
python main.py --transport both --admin

# 或使用热重载
uvicorn app.admin:admin_app --reload --port 9091
```

### 生产环境
```bash
# Docker
docker-compose up -d

# 查看日志
docker-compose logs -f mcp-tools

# 重启服务
docker-compose restart mcp-tools
```

## 总结

当前的部署方式 (`python -u main.py --transport sse --admin`) **已经是生产就绪的**:

✅ 使用 uvicorn 作为 ASGI 服务器
✅ 支持多服务并发运行
✅ 配置灵活,易于管理
✅ Docker 友好,日志清晰
✅ 可以通过扩展容器数量来扩展

如果有特殊需求 (如独立进程管理),可以考虑使用 supervisord,但当前方案已经满足大部分生产场景。

---

## 📖 快速部署指南

### 前提条件

1. **Docker Desktop 已安装并运行** (Windows/macOS) 或 Docker Engine (Linux)
2. **项目根目录下有 .env 文件**

### 部署步骤

```bash
# 1. 进入 deploy 目录
cd deploy

# 2. 确保 start.sh 有执行权限 (Linux/macOS)
chmod +x start.sh start-prod.sh

# 3. 启动服务（首次部署）
./start.sh prod --build

# 4. 查看服务状态
docker compose ps

# 5. 查看日志
docker compose logs -f

# 6. 访问服务
# MCP Service: http://localhost:9090/sse
# Admin Service: http://localhost:9091
```

### 常用操作

```bash
cd deploy

# 启动服务
./start.sh prod

# 停止服务
docker compose down

# 重启服务
docker compose restart mcp-service

# 查看日志
docker compose logs -f mcp-service

# 清理并重新部署
./start.sh prod --clean --build
```

### Windows 用户注意事项

如果无法运行 `./start.sh`，可以直接使用 Docker Compose 命令：

```powershell
# 进入 deploy 目录
cd deploy

# 启动服务
docker compose up -d --build

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

### 排查 Docker 问题

如果遇到 Docker 连接错误：

```
unable to get image: error during connect: open //./pipe/dockerDesktopLinuxEngine
```

**解决方法：**
1. 确认 Docker Desktop 正在运行
2. 在 Windows 系统托盘中查看 Docker 图标
3. 如果没有启动，双击 Docker Desktop 启动
4. 等待 Docker 完全启动后再次尝试

验证 Docker 运行状态：
```bash
docker info
docker compose version
```

### 服务访问地址

启动成功后，可以访问以下地址：

- **MCP SSE Service:** http://localhost:9090/sse
- **Admin Service:** http://localhost:9091
- **Health Check:** http://localhost:9090/health

### 目录说明

```
deploy/
├── docker-compose.yml    # ⭐ Docker Compose 主配置
├── start.sh              # ⭐ 智能启动脚本
├── start-prod.sh         # 生产启动脚本（容器内用）
├── Dockerfile            # Docker 镜像构建文件（符号链接）
├── init-db.sql           # 数据库初始化脚本
├── nginx.conf            # Nginx 反向代理配置
├── supervisord.conf      # Supervisor 进程管理配置
└── README.md             # 本文档
```

### 相关文档

- **架构说明:** 见上方 "架构概述" 部分
- **项目文档:** `../CLAUDE.md`
- **API 文档:** `../ADMIN_SERVICE.md`
- **部署架构:** `../DEPLOYMENT.md`
