# -*- coding: utf-8 -*-
from starlette.responses import HTMLResponse

from .ui_base import (
    build_page_with_nav,
    create_page_header,
    create_button_group,
    create_status_message,
)


def render_admin_config() -> HTMLResponse:
    # 页面头部
    header = create_page_header(
        title="平台与爬虫策略管理",
        breadcrumb="首页 / 配置管理",
    )

    # 重启警告
    restart_warning = f"""
    <div id='restart-warning' style='display:none; margin: 1rem 0;'>
        {create_status_message('某些配置可能需要重启后端服务', is_success=False)}
    </div>
    """

    # 平台配置卡片
    platforms_card = f"""
    <div class="mc-status-card">
        <h3>启用平台</h3>
        <div id='platform-checkboxes' class='mc-form-group'>
            <div style='color: #718096; padding: 1rem;'>正在加载平台列表...</div>
        </div>
        <div class='mc-form-group'>
            {create_button_group([("保存平台配置", "#", "primary")]).replace("href='#'", "onclick='savePlatformConfig()' style='cursor:pointer'")}
        </div>
    </div>
    """

    # 爬虫配置卡片（精简为当前有效配置）
    crawler_card = f"""
    <div class="mc-status-card">
        <h3>爬虫核心参数</h3>
        <form id='crawler-config-form' class='mc-form'>
            <div class='mc-form-group'>
                <label>无头模式</label>
                <label style='display:flex;align-items:center;gap:.5rem;'>
                    <input type='checkbox' id='headless' name='headless'> 浏览器后台运行（无界面）
                </label>
            </div>

            <div class='mc-form-group'>
                <label>数据保存方式</label>
                <select id='save_data_option' name='save_data_option'>
                    <option value='json'>JSON 文件</option>
                    <option value='csv'>CSV 文件</option>
                    <option value='sqlite'>SQLite 数据库</option>
                    <option value='db'>MySQL / PostgreSQL 数据库</option>
                </select>
                <small>选择爬取数据的存储格式</small>
            </div>

            <div class='mc-form-group'>
                <label>输出目录</label>
                <input type='text' id='output_dir' name='output_dir' placeholder='./data'>
            </div>

            <div class='mc-form-group'>
                <label style='display:flex;align-items:center;gap:.5rem;'>
                    <input type='checkbox' id='enable_save_media' name='enable_save_media'> 保存图片/视频
                </label>
            </div>

            <div class='mc-form-group'>
                {create_button_group([("保存爬虫配置", "#", "primary")]).replace("href='#'", "type='submit'")}
            </div>
        </form>
    </div>
    """

    # 当前配置显示卡片
    config_display_card = """
    <div class="mc-status-card">
        <h3>当前配置预览</h3>
        <div id='config-display'>
            <pre>{}</pre>
        </div>
    </div>
    """

    # 使用静态文件路径
    config_js = "<script src='/static/js/config.js'></script>"

    # 组合主内容
    main_content = f"""
        {header}
        {restart_warning}
        <div class="mc-dashboard-grid">
            {platforms_card}
            {crawler_card}
        </div>
        {config_display_card}
        {config_js}
    """

    return build_page_with_nav(
        main_content=main_content,
        title="配置管理 · MediaCrawler MCP",
        current_path="/config"
    )
