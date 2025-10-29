# -*- coding: utf-8 -*-
from starlette.responses import HTMLResponse

from .ui_base import (
    build_page_with_nav,
    create_page_header,
    create_info_box,
    create_button,
    create_button_row,
)


def render_admin_login() -> HTMLResponse:
    # 页面头部
    header = create_page_header(
        title="多平台登录中心",
        breadcrumb="首页 / 登录管理",
    )

    info_message = create_info_box(
        "支持二维码、Cookie、手机号等方式触发登录，并通过同一面板查看状态。\n"
        "智能优化：选择二维码登录时，系统会优先尝试使用缓存的 Cookie 自动登录；\n"
        "若 Cookie 失效，则自动降级为二维码登录。"
    )

    # 使用新的辅助函数生成按钮
    login_buttons = create_button_row(
        create_button("开始登录", btn_type="submit", btn_id="login-submit-btn", btn_class="btn btn-primary"),
        create_button("刷新状态", btn_id="refresh-login-status", btn_class="btn btn-secondary"),
        create_button("刷新二维码", btn_id="refresh-qr-btn", btn_class="btn btn-secondary", style="display:none;"),
    )

    # 登录表单卡片
    login_form_card = f"""
    <div class="mc-status-card">
        <h3>启动新的登录流程</h3>
        <form id='login-form' class='mc-form'>
            <div class='mc-form-group'>
                <label>选择平台</label>
                <select name='platform' id='platform' required>
                    <option value=''>请选择平台</option>
                </select>
                <small id='platform-tip'>正在加载可用平台...</small>
            </div>

            <div class='mc-form-group'>
                <label>登录方式</label>
                <select name='login_type' id='login_type'>
                    <option value='qrcode'>二维码扫码登录</option>
                    <option value='cookie'>Cookie 登录</option>
                    <option value='phone'>手机号登录</option>
                </select>
            </div>

            <div class='mc-form-group' id='phone-field' style='display:none;'>
                <label>手机号</label>
                <input type='tel' name='phone' id='phone' placeholder='请输入用于登录的手机号'>
            </div>

            <div class='mc-form-group' id='cookie-field' style='display:none;'>
                <label>Cookie</label>
                <textarea name='cookie' id='cookie' rows='4' placeholder='粘贴浏览器 Cookie'></textarea>
            </div>

            <div class='mc-form-group'>
                {login_buttons}
            </div>
        </form>
    </div>
    """

    # 登录状态显示卡片
    status_card = f"""
    <div class="mc-status-card">
        <h3>登录进度</h3>
        <div id='login-status'>{create_info_box("选择平台并点击 '开始登录'，进度将实时呈现")}</div>
        <div id='qr-code-container' style='display:none;'>
            <div id='qr-countdown' style='margin-bottom: 1rem; font-weight: 500;'></div>
            <div id='qr-image-wrapper' style='text-align: center;'></div>
        </div>
    </div>
    """

    # 平台会话状态卡片
    sessions_card = f"""
    <div class="mc-status-card">
        <h3>平台登录状态</h3>
        <div id='platform-sessions'>{create_info_box("正在加载平台状态...")}</div>
    </div>
    """

    # 使用静态文件路径
    login_js = "<script src='/static/js/login.js'></script>"

    # 组合主内容
    main_content = f"""
        {header}
        {info_message}
        <div class="mc-dashboard-grid">
            {login_form_card}
            {status_card}
        </div>
        {sessions_card}
        {login_js}
    """

    return build_page_with_nav(
        main_content=main_content,
        title="登录管理 · MediaCrawler MCP",
        current_path="/login"
    )
