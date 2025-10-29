# -*- coding: utf-8 -*-
"""管理界面端点 - 仅保留路由，页面渲染在 app/pages 中。"""

from starlette.responses import RedirectResponse, FileResponse, Response, JSONResponse
from pathlib import Path
from app.providers.logger import get_logger
from app.api.endpoints import main_app
from fastmcp.tools.tool_manager import ToolManager
from app.pages.admin_dashboard import render_admin_dashboard
from app.pages.admin_config import render_admin_config
from app.pages.admin_login import render_admin_login
from app.pages.admin_inspector import render_admin_inspector


logger = get_logger()

@main_app.custom_route("/", methods=["GET"])
@main_app.custom_route("/dashboard", methods=["GET"])
async def admin_dashboard(request):
    return render_admin_dashboard()


@main_app.custom_route("/config", methods=["GET"])
async def admin_config_page(request):
    return render_admin_config()


@main_app.custom_route("/login", methods=["GET"])
async def admin_login_page(request):
    return render_admin_login()


@main_app.custom_route("/inspector", methods=["GET"])
async def admin_inspector_page(request):
    return await render_admin_inspector()


# 兼容导航路径：/admin 与 /admin/ 均重定向到 /dashboard
@main_app.custom_route("/admin", methods=["GET"])
async def admin_root_redirect(request):
    return RedirectResponse(url="/dashboard")


@main_app.custom_route("/admin/", methods=["GET"])
async def admin_root_redirect_slash(request):
    return RedirectResponse(url="/dashboard")


# API endpoint for MCP data
@main_app.custom_route("/api/mcp/data", methods=["GET"])
async def get_mcp_data(request):
    try:
        # 直接使用 main_app 获取数据
        tools_result = await main_app.get_tools()
        prompts_result = await main_app.get_prompts()
        resources_result = await main_app.get_resources()
        
        # 转换为标准格式
        tools_list = []
        if isinstance(tools_result, dict):
            for tool_name, tool_obj in tools_result.items():
                tools_list.append({
                    "name": tool_obj.name,
                    "description": tool_obj.description,
                    "platform": tool_name.split('_')[0] if '_' in tool_name else 'unknown'
                })
        
        prompts_list = []
        if isinstance(prompts_result, dict):
            for prompt_name, prompt_obj in prompts_result.items():
                prompts_list.append({
                    "name": prompt_obj.name,
                    "description": prompt_obj.description
                })
        
        resources_list = []
        if isinstance(resources_result, dict):
            for uri, resource_obj in resources_result.items():
                resources_list.append({
                    "uri": str(resource_obj.uri),
                    "name": getattr(resource_obj, 'name', ''),
                    "description": resource_obj.description
                })
        
        return JSONResponse(content={
            "tools": {"tools": tools_list},
            "prompts": {"prompts": prompts_list},
            "resources": {"resources": resources_list}
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# API endpoint for executing MCP tools
@main_app.custom_route("/api/admin/inspector/execute", methods=["POST"])
async def execute_inspector_tool(request):
    from app.core.mcp.client import mcp_client_manager
    
    try:
        body = await request.json()
        tool_name = body.get("tool")
        params = body.get("params", {})
        
        if not tool_name:
            return JSONResponse(content={"error": "Missing tool name"}, status_code=400)
        
        # 使用 MCP Client 调用工具
        result = await mcp_client_manager.call_tool(tool_name, params)
        logger.info(f"Tool {tool_name} executed successfully via MCP Client {result}")
        
        return JSONResponse(content={"result": result.structured_content if not isinstance(result, str) else result, "tool": tool_name})
        
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@main_app.custom_route("/static/js/{file_path:path}", methods=["GET"])
async def serve_static_js(request):
    base_dir = Path(__file__).resolve().parents[3] / "pages" / "js"
    rel_path = request.path_params.get("file_path", "")
    try:
        target_path = (base_dir / rel_path).resolve()
        # Prevent path traversal
        if not str(target_path).startswith(str(base_dir.resolve())):
            return Response(status_code=404)
        if not target_path.is_file():
            return Response(status_code=404)
        return FileResponse(target_path, media_type="application/javascript")
    except Exception:
        return Response(status_code=404)
