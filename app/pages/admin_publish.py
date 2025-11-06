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
                <button type="button" class="btn btn-primary" id="btn-publish-xhs">发布小红书</button>
                <button type="button" class="btn btn-primary" id="btn-publish-dy" disabled>发布抖音</button>
                <button type="button" class="btn btn-secondary" id="refresh-tasks-btn">刷新</button>
            </div>
        </div>
        
        <!-- 小红书发布折叠框 -->
        <div id="xhs-publish-collapse" class="publish-collapse" style="display: none;">
            <div class="mc-form" style="border: 1px solid var(--border-color, #e2e8f0); border-radius: .5rem; padding: 1rem; margin-bottom: 1rem; background: var(--item-bg, #f8fafc);">
                <h5 style="margin: 0 0 1rem 0; color: var(--text-color, #1f2937);">小红书发布参数</h5>
                <div class="mc-form-group">
                    <label>内容类型</label>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-secondary is-active" data-type="image" id="xhs-btn-type-image">图文</button>
                        <button type="button" class="btn btn-secondary" data-type="video" id="xhs-btn-type-video">视频</button>
                    </div>
                    <input type="hidden" id="xhs-content-type" value="image" />
                </div>
                <div class="mc-form-group">
                    <label for="xhs-title">标题</label>
                    <input type="text" id="xhs-title" placeholder="请输入标题">
                </div>
                <div class="mc-form-group">
                    <label for="xhs-content">正文内容</label>
                    <textarea id="xhs-content" rows="5" placeholder="请输入正文内容"></textarea>
                </div>
                <div class="mc-form-group">
                    <label for="xhs-tags">标签</label>
                    <input type="text" id="xhs-tags" placeholder="多个标签用逗号分隔，如：美食推荐,好吃">
                </div>
                <div class="mc-form-group">
                    <label for="xhs-topics">话题</label>
                    <input type="text" id="xhs-topics" placeholder="多个话题用逗号分隔，如：#美食探店,#周末好去处">
                </div>
                <div class="mc-form-group" id="xhs-image-upload-section">
                    <label>图片上传</label>
                    <div class="mc-dropzone" id="xhs-image-dropzone">
                        <p>点击选择或直接拖拽图片到此处</p>
                        <input type="file" id="xhs-image-files" multiple accept="image/*" style="display:none">
                        <button type="button" class="btn btn-secondary" id="xhs-choose-images">选择图片</button>
                        <small style="display:block;margin-top:0.5rem;">最多支持9张图片，支持JPG、PNG等格式</small>
                    </div>
                    <div id="xhs-image-preview" style="margin-top:0.75rem;"></div>
                </div>
                <div class="mc-form-group is-hidden" id="xhs-video-upload-section">
                    <label>视频上传</label>
                    <div class="mc-dropzone" id="xhs-video-dropzone">
                        <p>点击选择或直接拖拽视频到此处</p>
                        <input type="file" id="xhs-video-file" accept="video/*" style="display:none">
                        <button type="button" class="btn btn-secondary" id="xhs-choose-video">选择视频</button>
                        <small style="display:block;margin-top:0.5rem;">支持MP4、MOV等格式</small>
                    </div>
                    <div id="xhs-video-preview" style="margin-top:0.75rem;"></div>
                </div>
                <div class="mc-form-group">
                    <label for="xhs-location">定位（可选）</label>
                    <input type="text" id="xhs-location" placeholder="请输入地点">
                </div>
                <div class="mc-form-group">
                    <label style="display:flex;align-items:center;gap:.5rem;">
                        <input type="checkbox" id="xhs-is-private"> 私密发布（仅自己可见）
                    </label>
                </div>
                <div class="mc-form-group">
                    <div class="btn-group">
                        <button type="button" class="btn btn-primary" id="xhs-publish-btn">立即发布</button>
                        <button type="button" class="btn btn-secondary" id="xhs-clear-btn">清空</button>
                        <button type="button" class="btn btn-secondary" id="xhs-cancel-btn">取消</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 抖音发布折叠框（暂时禁用） -->
        <div id="dy-publish-collapse" class="publish-collapse" style="display: none;">
            <div class="mc-form" style="border: 1px solid var(--border-color, #e2e8f0); border-radius: .5rem; padding: 1rem; margin-bottom: 1rem; background: var(--item-bg, #f8fafc);">
                <h5 style="margin: 0 0 1rem 0; color: var(--text-color, #1f2937);">抖音发布参数</h5>
                <p style="color: var(--text-muted, #6b7280);">抖音发布功能暂未开放</p>
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
    .mc-dropzone { 
        border: 2px dashed var(--border-color, #e2e8f0); 
        padding: 2rem; 
        text-align: center; 
        border-radius: .5rem; 
        color: var(--text-muted, #6b7280);
        background: var(--bg-color, #fafafa);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    .mc-dropzone:hover { 
        background: var(--item-bg, #f0f0f0); 
        border-color: var(--primary-color, #007bff);
    }
    .mc-dropzone.dragover {
        background: var(--primary-bg, #e3f2fd);
        border-color: var(--primary-color, #007bff);
        color: var(--primary-color, #007bff);
    }
    .is-hidden { display: none !important; }
    .publish-collapse { 
        transition: all 0.3s ease-in-out; 
        overflow: hidden;
    }
    .btn.is-active {
        background-color: var(--primary-color, #007bff) !important;
        color: white !important;
        border-color: var(--primary-color, #007bff) !important;
    }
    .image-preview-item {
        display: inline-block;
        position: relative;
        margin: 0.25rem;
        border-radius: 0.375rem;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
    }
    .image-preview-item img {
        width: 80px;
        height: 80px;
        object-fit: cover;
        display: block;
    }
    .image-preview-item .remove-btn {
        position: absolute;
        top: 4px;
        right: 4px;
        width: 20px;
        height: 20px;
        background: rgba(220, 53, 69, 0.9);
        color: white;
        border: none;
        border-radius: 50%;
        font-size: 12px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
    }
    .image-preview-item .remove-btn:hover {
        background: rgba(220, 53, 69, 1);
    }
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
            {create_task_list_card()}
        </div>
        <div class="mc-dashboard-grid" style="margin-top: 2rem;">
            {create_strategy_card()}
        </div>
        {create_publish_styles()}
        {create_publish_scripts()}
    """

    return build_page_with_nav(
        main_content=main,
        title="发布管理 · MediaCrawler MCP",
        current_path="/publish"
    )
