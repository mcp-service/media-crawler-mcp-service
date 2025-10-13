# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**mcp-toolse** is an AI Tools Service built on FastMCP + FastAPI that integrates multiple AI tools and models, providing a unified tool invocation interface through the Model Context Protocol (MCP). The service supports dual transport modes: STDIO (for local communication) and SSE (Server-Sent Events for web-based communication).

### MediaCrawler Integration

This project integrates **media_crawler** functionality by extracting its crawler implementations into our service architecture:

- **Crawler Modules**: `app/crawler/platforms/` - Platform-specific crawlers (Bilibili, Xiaohongshu, Douyin, Kuaishou, Weibo, Tieba, Zhihu)
- **Integration Approach**: Direct integration with parameterized configuration instead of global config
- **Configuration**: Unified Pydantic-based configuration in `app/config/settings.py`
- **Database**: PostgreSQL with models in `app/providers/models/`
- **API Layer**: MCP tools exposed via `app/api/endpoints/mcp/`

**Key Improvements**:
- ✅ Parameterized configuration (no global state)
- ✅ Concurrent-safe (no race conditions)
- ✅ Type-safe with Pydantic validation
- ✅ Unified provider pattern (logger, cache, database)

## Development Commands

### Environment Setup
```ba
# Install dependencies using Poetry
./deploy/dev.sh setup

# Update dependencies
./deploy/dev.sh update
```

### Running the Service

```bash
# Start both STDIO and SSE servers (default)
./deploy/dev.sh start
# or
poetry run python main.py --transport both

# Start only STDIO server
./deploy/dev.sh start-stdio
# or
poetry run python main.py --transport stdio

# Start only SSE server
./deploy/dev.sh start-sse
# or
poetry run python main.py --transport sse

# Start production server with Uvicorn
./deploy/dev.sh start-prod
```

**Important**: The SSE server runs on `http://0.0.0.0:9090/sse` (port configured in `app/config/settings.py`)

### Testing

```bash
# Run all tests
./deploy/dev.sh test
# or
poetry run pytest tests/ -v

# Test MCP tools
./deploy/dev.sh test-tools

# Test SSE connection
./deploy/dev.sh test-sse
```

### Code Quality

```bash
# Format code (Black + isort)
./deploy/dev.sh format

# Check code quality (flake8 + mypy)
./deploy/dev.sh check
```

### Docker Deployment

```bash
# Build Docker image
./deploy/dev.sh build

# Start Docker services
./deploy/dev.sh docker

# Stop Docker services
./deploy/dev.sh docker-stop
```

## 🏗️ API Architecture Rules

### **CRITICAL: Unified API Layer Pattern**

**All API-related functionality MUST be placed in `app/api/endpoints/`** - No exceptions!

#### Rule 1: No Separate Admin Routes
❌ **WRONG**: Creating routes in `app/admin/routes/`
✅ **CORRECT**: Creating endpoints in `app/api/endpoints/admin/`

**Rationale**:
- Unified endpoint registration through `BaseEndpoint`
- Consistent HTTP routing via Starlette
- Single source of truth for all API routes
- Easier maintenance and debugging

#### Rule 2: All Endpoints Must Extend BaseEndpoint

Every endpoint class must:
1. Extend `app.mcp.base_endpoint.BaseEndpoint`
2. Implement `register_routes()` - return list of Starlette routes
3. Implement `register_mcp_tools()` - register FastMCP tools (can be empty)
4. Be registered in `app.api_service.py:auto_discover_endpoints()`

**Example**:
```python
# app/api/endpoints/admin/config_endpoint.py
from app.mcp.base_endpoint import BaseEndpoint

class ConfigEndpoint(BaseEndpoint):
    prefix = "/config"
    tags = ["配置管理"]

    def register_routes(self):
        from fastapi import APIRouter
        router = APIRouter(prefix=self.prefix, tags=self.tags)

        @router.get("/platforms")
        async def get_platforms():
            # Handler logic
            pass

        return router.routes

    def register_mcp_tools(self, app):
        # Optional: register MCP tools
        pass
```

#### Rule 3: Endpoint Registration

All endpoints are registered in `app/api_service.py:auto_discover_endpoints()`:

```python
# Platform endpoints (conditional registration based on enabled_platforms)
from app.api.endpoints.mcp import BilibiliEndpoint, XiaohongshuEndpoint, ...
if "bili" in enabled_platforms:
    endpoint_registry.register(BilibiliEndpoint())

# Management endpoints (always registered)
from app.api.endpoints.login import LoginEndpoint
from app.api.endpoints.admin import ConfigEndpoint, StatusEndpoint
endpoint_registry.register(LoginEndpoint())
endpoint_registry.register(ConfigEndpoint())
endpoint_registry.register(StatusEndpoint())
```

#### Current Endpoint Structure

```
app/api/endpoints/
├── mcp/              # Platform MCP tools
│   ├── bilibili.py   # Bilibili爬虫工具
│   ├── xiaohongshu.py
│   ├── douyin.py
│   ├── kuaishou.py
│   ├── weibo.py
│   ├── tieba.py
│   └── zhihu.py
├── login/            # Login management
│   └── login_endpoint.py
└── admin/            # Admin & monitoring
    ├── config_endpoint.py   # Config management
    └── status_endpoint.py   # Status monitoring
```

#### Migration History (2025-01)

**Migrated from `app/admin/routes/` to `app/api/endpoints/admin/`:**
- ✅ `login.py` → `app/api/endpoints/login/login_endpoint.py`
- ✅ `config.py` → `app/api/endpoints/admin/config_endpoint.py`
- ✅ `status.py` → `app/api/endpoints/admin/status_endpoint.py`
- 🗑️ Deleted: `app/admin/routes/` directory (obsolete)

### **CRITICAL: Provider Usage Rules**

**Rule 4: Standardized Logger and Cache Usage**

All code MUST use the centralized provider modules for logging and caching.

**Rule 5: PostgreSQL Database Storage Standards**

All database operations MUST follow these standards:

1. **Database Choice**: Use PostgreSQL exclusively (not SQLite, MySQL, or others)
2. **Model Location**: All database models MUST be placed in `app/providers/models/`
3. **Configuration**: Database settings are in `app/config/settings.py` → `DatabaseConfig` class
4. **Connection Management**: Use `app.database.db_session.get_session()` for async sessions

❌ **WRONG**: Models scattered in different directories
```python
# app/database/models.py  # ❌ Old location
# app/crawler/models.py   # ❌ Wrong location
```

✅ **CORRECT**: Centralized model definitions
```python
# app/providers/models/bilibili.py
from sqlalchemy import Column, String, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class BilibiliVideo(Base):
    __tablename__ = "bilibili_videos"

    video_id = Column(String(50), primary_key=True)
    title = Column(String(500))
    view_count = Column(Integer)
    # ... more fields
```

**Usage in Store Layer**:
```python
from app.providers.models.bilibili import BilibiliVideo
from app.database.db_session import get_session

async def store_video(video_data: Dict):
    async with get_session() as session:
        video = BilibiliVideo(**video_data)
        session.add(video)
        await session.commit()
```

**Why**:
- Single source of truth for data schemas
- Easy to manage migrations
- Better IDE support and type checking
- Consistent database access patterns

**Rule 6: Unified Configuration System**

All crawler configuration MUST be unified in `app/config/settings.py` using platform-specific Pydantic models.

**Problem**: Original architecture had two config locations:
- `app/crawler/config/` - Platform-specific settings (scattered)
- `app/config/settings.py` - App settings (centralized)

**Solution**: Delete `app/crawler/config/` and merge everything into `app/config/settings.py` with per-platform configuration classes.

❌ **WRONG**: Separate config files per platform
```python
# app/crawler/config/bilibili.py  # ❌ Delete this
BILI_MAX_NOTES = 20
BILI_HEADLESS = True
```

✅ **CORRECT**: Unified Pydantic configuration
```python
# app/config/settings.py
from pydantic import BaseModel

class BilibiliConfig(BaseModel):
    """Bilibili平台配置"""
    max_notes: int = 20
    enable_comments: bool = True
    max_comments_per_note: int = 50
    headless: bool = True
    save_data_option: str = "json"  # json/csv/db
    login_type: str = "qrcode"  # qrcode/cookie

    # 平台特定设置
    video_quality: str = "1080p"
    download_cover: bool = True

class GlobalSettings(BaseSettings):
    # ... other configs
    bilibili: BilibiliConfig = BilibiliConfig()
    xiaohongshu: XiaohongshuConfig = XiaohongshuConfig()
    douyin: DouyinConfig = DouyinConfig()
    # ... more platforms
```

**Usage Pattern**:
```python
from app.config.settings import global_settings

# Access platform config
bili_config = global_settings.bilibili
max_notes = bili_config.max_notes  # 20
headless = bili_config.headless  # True

# Pass config to crawler
crawler = BilibiliCrawler(config=bili_config)
await crawler.search(keywords="Python", max_notes=bili_config.max_notes)
```

**Benefits**:
1. **Parameterized Configuration**: Each request can have different settings
2. **Type Safety**: Pydantic validation ensures correct types
3. **Environment Overrides**: Can override via env vars (e.g., `BILI_MAX_NOTES=50`)
4. **Single Source of Truth**: One place to manage all settings
5. **No Global State**: No race conditions from shared config objects

**Migration Checklist**:
- 🔴 Delete `app/crawler/config/` directory
- 🔴 Create platform config classes in `settings.py` (start with Bilibili)
- 🔴 Update all crawler usage to pass config instances
- 🔴 Remove `import config` from all crawler files

#### Logger Usage
❌ **WRONG**: Using custom loggers or utils.logger
```python
import logging
logger = logging.getLogger(__name__)  # ❌ Don't do this

from tools import utils
utils.logger.info("message")  # ❌ Don't do this
```

✅ **CORRECT**: Use app.providers.logger
```python
from app.providers.logger import get_logger

logger = get_logger()
logger.info("message")
logger.error(f"Error occurred: {e}")
```

**Why**:
- Centralized logging configuration
- Consistent log formatting across all modules
- Easy to modify logging behavior globally
- Proper log rotation and file handling

#### Cache Usage
❌ **WRONG**: Direct Redis or custom cache implementation
```python
import redis
redis_client = redis.Redis()  # ❌ Don't do this
```

✅ **CORRECT**: Use app.providers.cache
```python
from app.providers.cache import get_cache

cache = get_cache()
await cache.set("key", "value", expire=3600)
value = await cache.get("key")
```

**Why**:
- Connection pooling and reuse
- Automatic serialization/deserialization
- Consistent error handling
- Easy to switch cache backends

#### Enforcement
These rules apply to:
- ✅ All new code
- ✅ All refactored code
- ✅ Platform crawlers (`app/crawler/platforms/*/`)
- ✅ API endpoints (`app/api/endpoints/*/`)
- ✅ Services and utilities

**Migration Required**:
- 🔴 `app/crawler/store/bilibili/_store_impl.py` - Uses old imports (line 27, 28, 32)
- 🔴 `app/crawler/store/bilibili/bilibilli_store_media.py` - Uses `utils.logger` (line 68)

## Architecture

### Core Concepts

This application uses a **dual-layer architecture** that integrates FastMCP (for MCP tool protocol) with Starlette (for HTTP routing):

1. **FastMCP Layer**: Provides MCP protocol support for tool invocation via STDIO and SSE
2. **Starlette Layer**: Provides HTTP/REST API endpoints alongside MCP endpoints

### Key Components

#### 1. Endpoint Registration System (`app/core/base_endpoint.py`)

The codebase uses a unified endpoint registration pattern where each endpoint:
- Extends `BaseEndpoint` abstract class
- Registers both Starlette HTTP routes AND FastMCP tools
- Is auto-discovered and registered via `endpoint_registry`

**Pattern to follow when adding new endpoints**:
```python
class MyEndpoint(BaseEndpoint):
    def __init__(self):
        super().__init__(prefix="/my-endpoint", tags=["My Category"])

    def register_routes(self) -> List[Route]:
        # Define Starlette HTTP routes
        async def my_handler(request: Request) -> JSONResponse:
            # Handler logic
            pass

        return [
            self._create_route("/action", my_handler, ["POST"])
        ]

    def register_mcp_tools(self, app: FastMCP):
        # Define MCP tools
        @app.tool()
        async def my_tool(param: str) -> str:
            """Tool description"""
            # Tool logic
            pass

        self._add_tool_info("my_tool", "Tool description")
```

#### 2. Application Initialization (`app/api_service.py`)

The `create_app()` function:
- Initializes logging
- Creates FastMCP application
- Auto-discovers endpoints (add new endpoints in `auto_discover_endpoints()`)
- Patches FastMCP's SSE runner to integrate Starlette routes
- Registers service info tools

**To add a new endpoint**: Edit `auto_discover_endpoints()` in `app/api_service.py:110-133`:
```python
from app.api.endpoints.my_endpoint import MyEndpoint
endpoint_registry.register(MyEndpoint())
```

#### 3. Configuration System (`app/config/settings.py`)

**⚠️ CRITICAL KNOWN ISSUE**: The current configuration injection mechanism has a race condition bug in concurrent scenarios. See "Configuration System Issues" section below.

Configuration is managed via:
- Environment variables (`.env` file) - Primary configuration source
- Pydantic Settings with default values - `GlobalSettings` class
- NO YAML files used (legacy code references them but files don't exist)

Configuration hierarchy:
```
GlobalSettings (root)
├── AppConfig - Application settings (name, port, debug, env, version)
├── JWTConfig - Authentication settings
├── DatabaseConfig - PostgreSQL settings
├── RedisConfig - Redis cache settings
├── LoggerConfig - Logging configuration
├── SidecarConfig - MediaCrawler sidecar service settings
└── PlatformSettings - Platform-specific settings (enabled platforms, login types, etc.)
```

Environment variable naming:
- **Current implementation uses SINGLE underscore**: `APP_PORT`, `DB_HOST`, `REDIS_PORT`
- **⚠️ BUG**: `.env` file uses DOUBLE underscore (`APP__PORT`), causing `_override_from_env()` to fail
- See "Configuration System Issues" section for details

#### 4. Main Entry Point (`main.py`)

Supports three transport modes via `--transport` argument:
- `stdio`: STDIO-based MCP communication
- `sse`: SSE-based web communication
- `both`: Run both concurrently (default)

### Project Structure

```
app/
├── api/
│   └── endpoints/          # Endpoint implementations
│       ├── mcp/            # MCP platform endpoints
│       │   ├── base.py         # Base platform endpoint
│       │   ├── xiaohongshu.py  # 小红书 MCP tools
│       │   ├── douyin.py       # 抖音 MCP tools
│       │   ├── bilibili.py     # B站 MCP tools
│       │   ├── kuaishou.py     # 快手 MCP tools
│       │   ├── weibo.py        # 微博 MCP tools
│       │   ├── tieba.py        # 贴吧 MCP tools
│       │   └── zhihu.py        # 知乎 MCP tools
│       ├── sidecar/        # Sidecar HTTP endpoints
│       │   └── sidecar_endpoint.py  # Sidecar management API
│       └── login/          # Login management endpoints
│           └── login_endpoint.py    # Login & verification API
├── config/
│   └── settings.py         # Configuration management (YAML files don't exist)
├── core/
│   ├── base_endpoint.py    # Endpoint base class & registry
│   ├── browser_pool.py     # Browser instance pooling
│   ├── session_manager.py  # Cookie & session management
│   ├── media_crawler_service.py  # Sidecar service implementation
│   └── client/
│       └── media_crawler_client.py  # HTTP client for sidecar
├── providers/
│   ├── logger.py           # Logging configuration
│   ├── authentication.py   # Auth providers
│   └── models/             # Data models
├── api_service.py          # MCP application factory
└── admin.py                # Admin web interface

media_crawler/              # Git submodule (DO NOT MODIFY)
├── main.py                 # MediaCrawler entry point
├── config/                 # MediaCrawler configs (global state!)
├── media_platform/         # Platform crawlers (xhs, dy, ks, bili, etc.)
├── database/               # Database models
└── store/                  # Data storage implementations

deploy/
├── docker-compose.yml      # Unified Docker services
├── Dockerfile              # Main service Docker image
└── dev.sh                  # Development scripts
```

## Important Implementation Details

### FastMCP + Starlette Integration

The application **patches FastMCP's SSE runner** to serve both MCP SSE endpoints AND Starlette HTTP routes on the same server. This is done in `_patch_fastmcp_sse()` (app/api_service.py:50-107).

**Key insight**: All endpoint routes are collected and mounted alongside MCP routes:
```python
routes = [
    Route("/sse", endpoint=handle_sse),           # MCP SSE endpoint
    Mount("/messages/", app=sse.handle_post_message),  # MCP messages
] + api_routes  # HTTP API routes from all endpoints
```

### Tool Discovery Pattern

Tools are not manually registered. Instead:
1. Each endpoint class implements `register_mcp_tools(app: FastMCP)`
2. `endpoint_registry.register_all_mcp_tools(app)` calls each endpoint's method
3. Tools use FastMCP's `@app.tool()` decorator

### Logging

Logging is initialized once in `create_app()` using `init_logger()` from `app/providers/logger.py`. Access the logger anywhere via:
```python
from app.providers.logger import get_logger
get_logger().info("Message")
```

## Development Workflow

### Adding a New Tool Category

1. Create endpoint file in `app/api/endpoints/my_category.py`
2. Implement tool logic in `app/core/tools/my_category.py` (if complex)
3. Create endpoint class extending `BaseEndpoint`
4. Implement `register_routes()` and `register_mcp_tools()`
5. Register in `auto_discover_endpoints()` in `app/api_service.py`

### Configuration Changes

⚠️ **Note**: The configuration system has known issues. See "Configuration System Issues" section below before making changes.

To modify configuration:
1. Edit `.env` file with your environment variables
2. Add new fields to appropriate classes in `app/config/settings.py`
3. Update `_override_from_env()` function if needed (ensure variable naming matches `.env`)
4. Update README.md to document new configuration options

**Current issue**: YAML files (`dev.yaml`, `prod.yaml`) don't exist despite being referenced in code.

### Database & Redis

Database (PostgreSQL) and Redis are configured but initialization is optional:
- `init_database()` - Tortoise ORM initialization
- `init_redis()` - Redis client initialization

These must be called manually if needed (not auto-initialized).

## Python Environment

- **Python**: 3.11+
- **Package Manager**: Poetry 2.0+
- **Dependencies**: See `pyproject.toml`

## Code Quality Standards

### Type Checking (mypy)
The project uses strict mypy configuration:
- All functions must have type hints
- Untyped definitions are disallowed
- See `[tool.mypy]` in `pyproject.toml` for full config

### Formatting
- **Black**: Line length 88, Python 3.11 target
- **isort**: Black-compatible profile

### Testing
- **pytest**: Tests in `tests/` directory
- Use `pytest-asyncio` for async tests
- Run with: `poetry run pytest tests/ -v`

## Common Patterns

### Error Handling in Endpoints
```python
async def my_handler(request: Request) -> JSONResponse:
    try:
        body = await self._parse_json_body(request)
        # Process request
        return self._create_json_response(result)
    except Exception as e:
        get_logger().error(f"Error: {e}")
        return self._create_json_response(str(e), 500)
```

### MCP Tool Registration
```python
@app.tool()
async def my_tool(param: str) -> str:
    """Clear description of what the tool does"""
    # Implementation
    return result

# Track the tool
self._add_tool_info("my_tool", "Clear description")
```

## Transport Modes

### STDIO Mode
- Used for local/desktop applications
- Direct process communication
- Configuration: MCP client config files reference this service

### SSE Mode
- Used for web-based applications
- Server-Sent Events for real-time updates
- Endpoint: `http://0.0.0.0:9090/sse`
- Also serves HTTP API routes on same server

### Both Mode (Default)
- Runs STDIO and SSE concurrently using `asyncio.gather()`
- Allows simultaneous local and web access

## ⚠️ Configuration System Issues

### Critical Issue #1: Configuration Injection Race Condition

**Location**: `app/config/settings.py:415-458` (`MediaCrawlerConfigAdapter.inject_config`)

**Problem**: The configuration adapter directly modifies `media_crawler`'s global `config.py` module, which causes race conditions in concurrent scenarios.

**Root Cause**:
```python
# In MediaCrawlerConfigAdapter.inject_config()
import config as mc_config  # This imports a cached singleton module
mc_config.PLATFORM = crawler_config.platform  # Modifies global state!
``

Since Python modules are singletons (imported once and cached), all concurrent requests share the same `config` object. In a sidecar service handling multiple crawl requests simultaneously, configurations will overwrite each other.

**Concurrent Scenario Example**:
```
Time  | Request A (xhs, keywords="AI")  | Request B (dy, keywords="Tech")
------|----------------------------------|----------------------------------
T1    | inject_config(xhs, "AI")         |
      | config.PLATFORM = "xhs"          |
      | config.KEYWORDS = "AI"           |
T2    |                                  | inject_config(dy, "Tech")
      |                                  | config.PLATFORM = "dy" ← Overwrites!
      |                                  | config.KEYWORDS = "Tech" ← Overwrites!
T3    | Starts crawling...               |
      | Uses PLATFORM="dy", KEYWORDS="Tech" | ← BUG: Should be xhs/AI!
```

**Impact**: In production sidecar service with browser pooling, this will cause:
- Wrong platform being crawled
- Wrong keywords being searched
- Data corruption and user confusion

**Recommended Fix** (Priority: P0 - Critical):

**Option A - Environment Variable Isolation** (Recommended):
```python
def inject_config_via_env(self, crawler_config: CrawlerConfig) -> dict:
    """Create isolated environment for each crawl task"""
    env = os.environ.copy()
    env['MC_PLATFORM'] = crawler_config.platform
    env['MC_CRAWLER_TYPE'] = crawler_config.crawler_type
    env['MC_KEYWORDS'] = crawler_config.keywords or ''
    # ... more configs
    return env

# In media_crawler_service.py
async def _execute_crawl(self, crawler_config: CrawlerConfig):
    env = self.config_adapter.inject_config_via_env(crawler_config)
    # Run crawler in separate process with isolated env
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "media_crawler.main",
        env=env,  # Isolated configuration!
        cwd=str(MEDIA_CRAWLER_PATH)
    )
```

**Option B - Fork MediaCrawler for Instance-based Config** (Not recommended):
Requires modifying the `media_crawler` submodule to use instance-based configuration instead of global config, which violates the "don't modify submodule" principle.

---

### Issue #2: Environment Variable Naming Mismatch

**Location**: `.env` file vs `app/config/settings.py:333-380` (`_override_from_env()`)

**Problem**: Environment variable names don't match between configuration file and code.

**Mismatch Table**:

| Configuration | .env File | _override_from_env() | Works? |
|---------------|-----------|---------------------|--------|
| APP Port      | `APP__PORT=9090` | `os.getenv('APP_PORT')` | ❌ No |
| DB Host       | `DB__HOST=localhost` | `os.getenv('DB_HOST')` | ❌ No |
| Enabled Platforms | `ENABLED__PLATFORMS=all` | `os.getenv('ENABLED_PLATFORMS')` | ❌ No |

**Root Cause**:
- `.env` uses **double underscore** (`__`) - Pydantic nested env var convention
- Code uses **single underscore** (`_`) - Traditional env var naming
- Result: `_override_from_env()` reads nothing and has no effect

**Impact**: Environment variables cannot override default settings, making configuration inflexible.

**Recommended Fix** (Priority: P0 - Critical):

**Choose ONE naming convention and apply consistently:**

**Option A - Single Underscore** (Simpler, recommended):
```bash
# .env
APP_ENV=dev
APP_PORT=9090
APP_DEBUG=true
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=mcp_tools_db
REDIS_HOST=localhost
REDIS_PORT=6379
SIDECAR_URL=http://localhost:8001
ENABLED_PLATFORMS=all
```

**Option B - Double Underscore** (Pydantic standard):
```bash
# .env (following Pydantic nested delimiter convention)
APP__ENV=dev
APP__PORT=9090
DATABASE__HOST=localhost
DATABASE__PORT=5432
SIDECAR__URL=http://localhost:8001
PLATFORMS__ENABLED_PLATFORMS=all
```

Then update `_override_from_env()` to match:
```python
def _override_from_env(settings: GlobalSettings) -> None:
    # Match the naming in .env!
    if port := os.getenv('APP_PORT'):  # or 'APP__PORT'
        settings.app.port = int(port)
```

---

### Issue #3: Missing Configuration Fields

**Location**: `app/config/settings.py` - `AppConfig` and `SidecarConfig`

**Problem**: README and `main.py` reference configuration fields that don't exist in `settings.py`:

- `ADMIN_PORT` - Used in `main.py:73-96` but not in `AppConfig`
- `SIDECAR_PORT` - Mentioned in README but not in `SidecarConfig`

**Impact**: These ports are hardcoded in `main.py` instead of being configurable.

**Recommended Fix** (Priority: P1 - High):

```python
# In settings.py
class AppConfig(BaseModel):
    name: str = 'mcp-toolse'
    port: int = 9090          # MCP service port
    admin_port: int = 9091    # ← Add this
    debug: bool = True
    env: str = 'dev'
    version: str = '1.0.0'
    auto_reload: bool = False

class SidecarConfig(BaseModel):
    url: str = 'http://localhost:8001'
    port: int = 8001          # ← Add this
    timeout: float = 300.0
    # ... rest of config
```

Then update `main.py`:
```python
# OLD: args.admin_port (hardcoded default 9091)
# NEW: global_settings.app.admin_port
await run_admin_service(global_settings.app.admin_port)
```

---

### Issue #4: YAML Files Referenced But Don't Exist

**Location**: `app/config/settings.py:299-331` (`load_config()`)

**Problem**: Code attempts to load `dev.yaml` and `prod.yaml`, but these files don't exist in `app/config/` directory.

**Current Code**:
```python
def load_config() -> GlobalSettings:
    yaml_file_path = config_dir / f"{app_env}.yaml"
    if yaml_file_path.exists():  # ← Always False!
        # YAML loading logic (never executed)
```

**Impact**: Dead code that adds complexity without providing value.

**Recommended Fix** (Priority: P2 - Medium):

**Option A - Remove YAML Logic** (Recommended):
Simplify to pure Pydantic + environment variables:
```python
def load_config() -> GlobalSettings:
    """Load configuration from Pydantic defaults + env vars"""
    settings = GlobalSettings()  # Loads from .env via Pydantic
    _override_from_env(settings)  # Explicit overrides
    return settings
```

**Option B - Create YAML Files**:
If you want to keep YAML support, create the files. But this adds complexity for little benefit.

---

### Issue #5: Duplicate and Inconsistent .env Entries

**Location**: `.env` file lines 39-44

**Problem**: Duplicate configuration with inconsistent naming:
```bash
# Lines 1-12: New format with double underscores
ENABLED__PLATFORMS=all

# Lines 39-44: Old format with single underscores (DUPLICATE!)
ENABLED_PLATFORMS=xhs,tieba,ks,bili,wb,zhihu
MEDIA_CRAWLER_MAX_NOTES=15
MEDIA_CRAWLER_ENABLE_COMMENTS=true
```

**Impact**: Confusing, conflicting configuration that's hard to maintain.

**Recommended Fix** (Priority: P1 - High):

Remove lines 39-44 from `.env` file. Keep only one set of configuration using consistent naming.

---

### Configuration Changes Checklist

When modifying configuration:

1. **Environment Variables**: Update `.env` file with correct naming convention
2. **Settings Classes**: Add/modify fields in `app/config/settings.py`
3. **Override Function**: Update `_override_from_env()` to read new env vars
4. **Documentation**: Update README.md configuration section
5. **Default Values**: Ensure sensible defaults in Pydantic models

---

### Configuration Priority Order

Current configuration loading order (from lowest to highest priority):

1. **Pydantic Defaults** - Hardcoded in `settings.py` model classes
2. **YAML Files** - Attempted but files don't exist (dead code)
3. **Environment Variables** - Loaded by Pydantic via `.env` file
4. **Explicit Overrides** - `_override_from_env()` function (currently broken)

**Recommended simplified order**:
1. Pydantic Defaults
2. `.env` file (parsed by Pydantic)
3. Runtime environment variables (highest priority)

---

## 📋 Development TODO List

This comprehensive TODO list tracks the refactoring and optimization work for the MediaCrawler MCP Service. Tasks are organized by priority (P0-P2) and grouped into phases.

### **Phase 1: 配置系统重构（P0 - 关键问题）**

#### ✅ 1.1 移除全局配置注入机制
- **路径**: `app/config/settings.py:415-458`
- **任务**: 删除 `MediaCrawlerConfigAdapter.inject_config()` 方法（直接修改全局config导致并发冲突）
- **影响范围**: `app/core/media_crawler_service.py:191`
- **状态**: 🔴 待处理

#### 🔧 1.2 实现配置上下文管理器
- **新建文件**: `app/core/config_context.py`
- **功能**:
  - 实现 `async_media_crawler_config_context()` 异步上下文管理器
  - 临时修改 media_crawler 的 config 模块，退出时自动恢复
  - 提供配置快照（snapshot）和恢复（restore）功能
- **示例代码结构**:
```python
@asynccontextmanager
async def async_media_crawler_config_context(crawler_config: CrawlerConfig):
    original_snapshot = _get_config_snapshot()
    try:
        _inject_config(crawler_config)
        yield
    finally:
        _restore_config_snapshot(original_snapshot)
```
- **状态**: 🔴 待处理

#### 🔧 1.3 修复环境变量命名不一致
- **路径**: `.env` 文件 + `app/config/settings.py:333-380`
- **问题**: `.env` 使用双下划线（`APP__PORT`），代码读取单下划线（`APP_PORT`）
- **修复方案**: 统一使用单下划线命名（简单直观）
- **影响条目**:
  - `APP__PORT` → `APP_PORT`
  - `DB__HOST` → `DB_HOST`
  - `REDIS__HOST` → `REDIS_HOST`
  - 删除 `.env` 中的重复配置（行39-44）
- **状态**: 🔴 待处理

#### 🔧 1.4 补充缺失的配置字段
- **路径**: `app/config/settings.py:81-97`
- **新增字段**:
  - `AppConfig`: 添加 `admin_port: int = 9091`
  - `SidecarConfig`: 添加 `port: int = 8001`
- **影响文件**: `main.py`, `sidecar_main.py`, `admin_main.py`
- **状态**: 🔴 待处理

---

### **Phase 2: API 端点优化（P1 - 功能完善）**

#### 🔧 3.1 完善 Sidecar Endpoint
- **路径**: `app/api/endpoints/sidecar/sidecar_endpoint.py`
- **待完成功能**:
  - Line 150: 实现配置热更新（`/config/update`）
  - 增加批量爬取端点（支持多平台并行）
  - 增加任务队列管理端点（查看、取消、重试）
  - 增加数据导出端点（JSON/CSV/Excel）
- **状态**: 🔴 待处理

#### 🔧 3.2 完善 Login Endpoint
- **路径**: `app/api/endpoints/login/login_endpoint.py`
- **待完成功能**:
  - Line 100-110: 实现真实的登录状态检查（`/status/{platform}`）
  - Line 127-138: 实现退出登录逻辑（`/logout/{platform}`）
  - 集成 `SessionManager` 检查会话有效性
  - 增加会话刷新端点（延长有效期）
- **状态**: 🔴 待处理

#### 📝 3.3 新增 MCP Tools Endpoint（注册21个爬虫工具）
- **新建文件**: `app/api/endpoints/mcp/mcp_tools_endpoint.py`
- **功能**:
  - 将边车服务的 HTTP API 包装为 MCP Tools
  - 注册 21 个平台特定工具（xhs_search, dy_detail, bili_creator 等）
  - 使用 `MediaCrawlerClient` 调用边车服务
- **工具列表**:
  - 小红书: `xhs_search`, `xhs_detail`, `xhs_creator`
  - 抖音: `dy_search`, `dy_detail`, `dy_creator`
  - 快手: `ks_search`, `ks_detail`, `ks_creator`
  - B站: `bili_search`, `bili_detail`, `bili_creator`
  - 微博: `wb_search`, `wb_detail`, `wb_creator`
  - 贴吧: `tieba_search`, `tieba_detail`
  - 知乎: `zhihu_search`, `zhihu_detail`
- **状态**: 🔴 待处理

---

### **Phase 3: 部署和容器化（P1 - 生产就绪）**

#### 📝 3.1 完善 Docker Compose 配置
- **路径**: `deploy/docker-compose.yml`
- **优化点**:
  - 增加健康检查（healthcheck）
  - 配置资源限制（memory/cpu limits）
  - 增加 Nginx 反向代理服务
  - 配置日志驱动和卷挂载
- **状态**: 🔴 待处理

---

## 📊 优先级总结

### **立即执行（P0 - 关键问题）**
1. ✅ Phase 1: 配置系统重构（1.1-1.4）

### **本周完成（P1 - 重要功能）**
2. 🔧 Phase 2: API 端点优化
3. 📝 Phase 3: 部署和容器化

---

## 🔄 状态图例

- 🔴 待处理 (Not Started)
- 🟡 进行中 (In Progress)
- 🟢 已完成 (Completed)
- ⚠️ 阻塞中 (Blocked)
- ✅ 已验证 (Verified)