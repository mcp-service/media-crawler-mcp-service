from fastmcp import FastMCP
from app.config.settings import global_settings
from app.api.endpoints.mcp import bili_mcp, xhs_mcp

# 创建主应用
main_app = FastMCP(
    name=global_settings.app.name,
    version=global_settings.app.version,
)

# 注册路由
import app.api.endpoints.admin.dashboard_endpoint
import app.api.endpoints.admin.config_endpoint
import app.api.endpoints.admin.status_endpoint
import app.api.endpoints.admin.publish_endpoint
import app.api.endpoints.login.login_endpoint

__all__ = ["main_app", "bili_mcp", "xhs_mcp"]