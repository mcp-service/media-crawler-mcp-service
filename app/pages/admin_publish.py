# -*- coding: utf-8 -*-
"""发布管理页面（FastMCP-UI 风格，折叠卡片排队 + 分页）"""

from starlette.responses import HTMLResponse

from .ui_base import (
    build_page_with_nav,
    create_page_header,
    create_button_group,
)


# ----------------------------------------------------------------------------
# 表单片段（统一使用 mc-* 样式）
# ----------------------------------------------------------------------------

def create_platform_selector() -> str:
    return """
    <div class="mc-form-group">
        <label>发布平台</label>
        <select id="platform-select">
            <option value="xhs">小红书</option>
        </select>
    </div>
    """


def create_content_type_selector() -> str:
    return """
    <div class="mc-form-group">
        <label>内容类型</label>
        <div class="btn-group" role="group">
            <button type="button" class="btn btn-secondary is-active" data-type="image" id="btn-type-image">图文</button>
            <button type="button" class="btn btn-secondary" data-type="video" id="btn-type-video">视频</button>
        </div>
        <input type="hidden" id="content-type" value="image" />
    </div>
    """


def create_title_input() -> str:
    return """
    <div class="mc-form-group">
        <label for="title">标题</label>
        <input type="text" id="title" placeholder="请输入标题">
    </div>
    """


def create_content_textarea() -> str:
    return """
    <div class="mc-form-group">
        <label for="content">正文内容</label>
        <textarea id="content" rows="5" placeholder="请输入正文内容"></textarea>
    </div>
    """


def create_tags_input() -> str:
    return """
    <div class="mc-form-group">
        <label for="tags">标签</label>
        <input type="text" id="tags" placeholder="多个标签用逗号分隔，如：美食推荐,好吃">
    </div>
    """


def create_topics_input() -> str:
    return """
    <div class="mc-form-group">
        <label for="topics">话题</label>
        <input type="text" id="topics" placeholder="多个话题用逗号分隔，如：#美食探店,#周末好去处">
    </div>
    """


def create_image_upload_section() -> str:
    return """
    <div class="mc-form-group" id="image-upload-section">
        <label>图片</label>
        <div class="btn-group" role="group" style="margin-bottom:.5rem;">
            <button type="button" class="btn btn-secondary is-active" data-mode="path" id="btn-image-path">本地路径</button>
            <button type="button" class="btn btn-secondary" data-mode="file" id="btn-image-file">文件上传</button>
        </div>
        <div id="image-path-input">
            <textarea id="image-paths" rows="3" placeholder="每行一个本地图片绝对路径"></textarea>
            <small>最多 9 张图片</small>
        </div>
        <div id="image-file-input" class="is-hidden">
            <div class="mc-dropzone">
                <p>点击选择或直接拖拽图片到此处</p>
                <input type="file" id="image-files" multiple accept="image/*" style="display:none">
                <button type="button" class="btn btn-secondary" id="choose-image-files">选择图片</button>
            </div>
        </div>
        <div id="image-preview" style="margin-top:.75rem;"></div>
    </div>
    """


def create_video_upload_section() -> str:
    return """
    <div class="mc-form-group is-hidden" id="video-upload-section">
        <label>视频</label>
        <div class="mc-dropzone">
            <p>点击选择或拖拽视频到此处</p>
            <input type="file" id="video-file" accept="video/*" style="display:none">
            <button type="button" class="btn btn-secondary" id="choose-video-file">选择视频</button>
        </div>
        <div id="video-preview" style="margin-top:.75rem;"></div>
    </div>
    """


def create_location_input() -> str:
    return """
    <div class="mc-form-group">
        <label for="location">定位（可选）</label>
        <input type="text" id="location" placeholder="请输入地点">
    </div>
    """


def create_private_switch() -> str:
    return """
    <div class="mc-form-group">
        <label style="display:flex;align-items:center;gap:.5rem;">
            <input type="checkbox" id="is-private"> 私密发布（仅自己可见）
        </label>
    </div>
    """


def create_publish_button() -> str:
    return """
    <div class="mc-form-group">
        <div class="btn-group">
            <button type="button" class="btn btn-primary" id="publish-btn">发布内容</button>
            <button type="button" class="btn btn-secondary" id="clear-form-btn">清空</button>
        </div>
    </div>
    """


def create_publish_form_card() -> str:
    return f"""
    <div class="mc-status-card">
        <h3>新建发布任务</h3>
        <div class="mc-form">
            {create_platform_selector()}
            {create_content_type_selector()}
            {create_title_input()}
            {create_content_textarea()}
            {create_tags_input()}
            {create_topics_input()}
            {create_location_input()}
            {create_image_upload_section()}
            {create_video_upload_section()}
            {create_private_switch()}
            {create_publish_button()}
        </div>
    </div>
    """


def create_strategy_form() -> str:
    return """
    <div class="mc-form-group">
        <label>最小发布间隔（秒）</label>
        <input type="number" id="min-interval" min="60" value="300">
        <small>建议不小于 60 秒</small>
    </div>
    <div class="mc-form-group">
        <label>每日发布限制（条）</label>
        <input type="number" id="daily-limit" min="1" value="10">
    </div>
    <div class="mc-form-group">
        <label>每小时发布限制（条）</label>
        <input type="number" id="hourly-limit" min="1" value="5">
    </div>
    <div class="mc-form-group">
        <label>失败重试次数</label>
        <input type="number" id="retry-count" min="0" value="3">
    </div>
    <div class="mc-form-group">
        <div class="btn-group">
            <button type="button" class="btn btn-primary" id="update-strategy-btn">保存配置</button>
            <button type="button" class="btn btn-secondary" id="refresh-strategy-btn">刷新</button>
        </div>
    </div>
    """


def create_strategy_card() -> str:
    return f"""
    <div class="mc-status-card">
        <h3>发布策略配置</h3>
        {create_strategy_form()}
    </div>
    """


def create_task_list_card() -> str:
    return """
    <div class="mc-status-card">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:1rem; margin-bottom: .5rem;">
            <h3 style="margin:0;">发布任务队列</h3>
            <div class="btn-group">
                <button type="button" class="btn btn-secondary" id="refresh-tasks-btn">刷新</button>
            </div>
        </div>
        <div id="queue-stats" style="color: var(--text-muted, #6b7280); margin-bottom:.5rem;">统计加载中...</div>
        <div id="task-list" class="mc-queue-list"></div>
        <div id="pagination" class="mc-pagination" aria-label="Pagination"></div>
    </div>
    """


def create_publish_styles() -> str:
    return """
    <style>
    .mc-dropzone { border: 1px dashed var(--border-color, #e2e8f0); padding: 1rem; text-align:center; border-radius: .5rem; color: var(--text-muted, #6b7280); }
    .mc-dropzone:hover { background: var(--item-bg, #f8fafc); }
    </style>
    """


def create_publish_scripts() -> str:
    return '<script src="/static/js/publish.js"></script>'


def render_publish_management_page() -> HTMLResponse:
    header = create_page_header(
        title="发布管理",
        breadcrumb="首页 / 发布管理",
        actions=create_button_group([
            ("刷新队列", "#", "secondary"),
        ]).replace("href='#'", "id=\"header-refresh-btn\" style='cursor:pointer'")
    )

    main = f"""
        {header}
        <div class="mc-dashboard-grid">
            {create_publish_form_card()}
            {create_strategy_card()}
            {create_task_list_card()}
        </div>
        {create_publish_styles()}
        {create_publish_scripts()}
    """

    return build_page_with_nav(
        main_content=main,
        title="发布管理 · MediaCrawler MCP",
        current_path="/publish"
    )

