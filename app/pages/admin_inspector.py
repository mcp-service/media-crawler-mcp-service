# -*- coding: utf-8 -*-
from starlette.responses import HTMLResponse
import json

from .ui_base import (
    build_page_with_nav,
    create_page_header,
    create_info_box,
)

from app.providers.logger import get_logger

logger = get_logger()

async def render_admin_inspector() -> HTMLResponse:
    # 页面头部
    header = create_page_header(
        title="MCP Tools Inspector",
        breadcrumb="首页 / 工具调试台",
    )

    info_message = create_info_box("浏览并调试已注册的 MCP 工具，直接向对应 HTTP 接口提交请求，实时查看返回数据")

    # 左侧工具列表
    tools_list = f"""
    <div class=\"mc-status-card\">
        <h3>可用对象</h3>
        <div class='mc-form-group' id='inspector-filters'>
            <label style='font-weight:600; margin-bottom: .5rem;'>显示类别</label>
            <select id='filter-kind' class='form-control' style='max-width:260px;'>
                <option value='tools' selected>工具 (Tools)</option>
                <option value='prompts'>提示词 (Prompts)</option>
                <option value='resources'>资源 (Resources)</option>
            </select>
        </div>
        <div id='tool-list'>{create_info_box("加载工具/提示词/资源中...")}</div>
    </div>
    """

    # 右侧调试面板
    debug_panel = f"""
    <div class="mc-status-card">
        <div style='border-bottom: 1px solid var(--border-color, #e2e8f0); padding-bottom: 1rem; margin-bottom: 1.5rem;'>
            <h3 id='tool-name'>请选择工具</h3>
            <p id='tool-description' style='color: var(--text-muted, #6b7280); margin: 0.5rem 0;'>从左侧列表中选择一个工具进行调试。</p>
            <div style='display: flex; gap: 1rem; margin-top: 0.75rem;'>
                <div><span style='font-weight: 500;'>HTTP 路由：</span> <code id='tool-path'>-</code></div>
                <div><span style='font-weight: 500;'>请求方法：</span> <code id='tool-methods'>-</code></div>
            </div>
        </div>

        <div class='mc-form-group'>
            <label>请求体（JSON）</label>
            <textarea id='tool-request-body' rows='12' placeholder='工具参数将显示在这里...'></textarea>
            <small>修改参数后点击"执行请求"进行测试</small>
        </div>

        <div class='mc-form-group'>
            <div class='btn-group'>
                <button type='button' class='btn btn-primary' id='execute-tool' disabled>执行请求</button>
                <button type='button' class='btn btn-secondary' id='reset-body' disabled>恢复默认</button>
                <button type='button' class='btn btn-secondary' id='copy-response' style='display:none;'>复制响应</button>
            </div>
        </div>

        <div>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;'>
                <span style='font-weight: 500;'>响应结果</span>
                <span id='response-status' style='color: var(--text-muted, #6b7280);'>尚未执行</span>
            </div>
            <pre id='response-body' style='min-height: 200px; background: var(--code-bg, #f8fafc);'>{{}}</pre>
        </div>
    </div>
    """

    # 直接使用 main_app 获取动态数据
    try:
        # 这里不再获取数据，改为通过 AJAX 获取，保持与其他页面一致
        logger.info("Inspector 页面已改为 AJAX 模式获取数据")
        
    except Exception as e:
        logger.error(f"Inspector 页面加载失败: {e}")

    # 使用静态文件路径，不注入数据，改为 AJAX 获取
    inspector_js = "<script src='/static/js/inspector.js'></script>"

    # 组合主内容
    main_content = f"""
        {header}
        {info_message}
        <div class="mc-dashboard-grid">
            {tools_list}
            {debug_panel}
        </div>
        {inspector_js}
    """

    return build_page_with_nav(
        main_content=main_content,
        title="工具调试台 · MediaCrawler MCP",
        current_path="/inspector"
    )
