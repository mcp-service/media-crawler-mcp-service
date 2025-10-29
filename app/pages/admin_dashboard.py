# -*- coding: utf-8 -*-
from starlette.responses import HTMLResponse

from .ui_base import (
    build_page_with_nav,
    create_page_header,
    create_detail_box,
    create_button_group,
)


def render_admin_dashboard() -> HTMLResponse:
    # 页面头部
    header = create_page_header(
        title="实时状态监控中心",
        breadcrumb="首页 / 状态监控",
        actions=create_button_group([
            ("立即刷新", "#", "primary"),
        ]).replace("href='#'", "onclick='refreshAllData()' style='cursor:pointer'")
    )

    # 系统指标卡片
    metrics_card = f"""
    <div class="mc-status-card">
        <h3>系统资源监控</h3>
        <div id="system-metrics">
            {create_detail_box([
                ("CPU 使用率", "加载中..."),
                ("内存使用率", "加载中..."),
                ("磁盘使用率", "加载中..."),
                ("累计数据文件", "加载中..."),
            ])}
        </div>
    </div>
    """

    # 服务状态卡片
    services_card = f"""
    <div class="mc-status-card">
        <h3>核心服务状态</h3>
        <div id="services-status">
            {create_detail_box([
                ("MCP 服务", "检查中..."),
                ("数据库", "检查中..."),
                ("Redis", "检查中..."),
            ])}
        </div>
    </div>
    """

    # 平台状态卡片
    platforms_card = """
    <div class="mc-status-card">
        <h3>平台会话面板</h3>
        <div id='platforms-status' style='min-height: 100px;'>
            <div style='color: #718096; text-align: center; padding: 2rem 0;'>正在加载平台状态...</div>
        </div>
    </div>
    """

    # 数据状态卡片
    data_card = """
    <div class="mc-status-card">
        <h3>数据持久化概览</h3>
        <div id='data-path-container'>
            <div class="detail-box">
                <div class="detail-row">
                    <div class="detail-label">数据目录:</div>
                    <div class="detail-value">加载中...</div>
                </div>
            </div>
        </div>
        <div id='platform-data-stats' style='margin-top: 1rem;'></div>
    </div>
    """

    # 使用静态文件路径
    dashboard_js = "<script src='/static/js/dashboard.js'></script>"

    # 组合主内容
    main_content = f"""
        {header}
        <div class="mc-dashboard-grid">
            {metrics_card}
            {services_card}
            {platforms_card}
            {data_card}
        </div>
        {dashboard_js}
    """

    return build_page_with_nav(
        main_content=main_content,
        title="状态监控 · MediaCrawler MCP",
        current_path="/dashboard"
    )
