# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**mcp-toolse** is an AI Tools Service built on FastMCP + FastAPI that integrates multiple AI tools and models, providing a unified tool invocation interface through the Model Context Protocol (MCP). The service supports dual transport modes: STDIO (for local communication) and SSE (Server-Sent Events for web-based communication).

### MediaCrawler Integration

This project integrates **media_crawler** as a git submodule, exposing its social media crawling capabilities as MCP tools through SSE/HTTP protocol. The integration follows a **sidecar service pattern**:

- **Submodule**: `media_crawler/` - Social media crawler supporting platforms like Xiaohongshu, Douyin, Kuaishou, Bilibili, Weibo, Tieba, and Zhihu
- **Integration Approach**: Edge service that wraps media_crawler's functionality without modifying its codebase
- **Dependency Management**: All dependencies (both main project and media_crawler) are unified in the main project's `pyproject.toml`
- **Database**: Shared database infrastructure managed through Docker containers
- **Deployment**: Unified Docker Compose configuration for both services

**IMPORTANT**: Never modify code inside `media_crawler/` directory - it's a git submodule and should remain untouched. All integration logic resides in `app/api/endpoints/media_crawler.py`.

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

**Important**: The SSE server runs on `http://0.0.0.0:9090/sse` (port configured in `app/config/dev.yaml`)

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

Configuration is managed via:
- Environment variables (`.env` file)
- YAML files (`app/config/dev.yaml`, `app/config/prod.yaml`)
- Pydantic Settings for validation

Configuration is environment-based:
- Set `APP_ENV=dev` or `APP_ENV=prod` in `.env`
- Corresponding YAML file is loaded automatically

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
│       ├── calculator.py   # Calculator tools
│       ├── file.py        # File operations
│       ├── text.py        # Text processing
│       ├── xiaohongshu.py # Social media integration (legacy)
│       └── media_crawler.py # MediaCrawler MCP tools wrapper
├── config/
│   ├── settings.py        # Configuration management
│   ├── dev.yaml          # Development config
│   └── prod.yaml         # Production config
├── core/
│   ├── base_endpoint.py  # Endpoint base class & registry
│   └── tools/            # Tool implementations
│       └── media_crawler/ # MediaCrawler integration helpers
├── providers/
│   ├── logger.py         # Logging configuration
│   ├── authentication.py # Auth providers
│   └── models/           # Data models
└── api_service.py        # Application factory

common_sdk/               # Shared SDK components
├── auth/                 # Authentication utilities
├── logging/              # Logging utilities
├── service_client/       # Service clients
└── util/                 # Utility functions

media_crawler/            # Git submodule (DO NOT MODIFY)
├── main.py              # MediaCrawler entry point
├── config/              # MediaCrawler configs
├── media_platform/      # Platform crawlers (xhs, dy, ks, bili, etc.)
├── database/            # Database models
└── store/               # Data storage implementations

deploy/
├── docker-compose.yml   # Unified Docker services
├── Dockerfile           # Main service Docker image
└── dev.sh              # Development scripts
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

- Development: Edit `app/config/dev.yaml`
- Production: Edit `app/config/prod.yaml`
- New config fields: Add to settings classes in `app/config/settings.py`

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