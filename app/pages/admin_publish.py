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
        <div style="display:flex;justify-content:space-between;align-items:center;gap:1rem; margin-bottom: 1rem;">
            <h3 style="margin:0;">发布任务队列</h3>
            <div class="btn-group">
                <button type="button" class="btn btn-primary" id="btn-publish-xhs">
                    <i class="fas fa-plus-circle" style="margin-right: 0.5rem;"></i>发布小红书
                </button>
                <button type="button" class="btn btn-primary" id="btn-publish-dy" disabled>
                    <i class="fas fa-plus-circle" style="margin-right: 0.5rem;"></i>发布抖音
                </button>
                <button type="button" class="btn btn-secondary" id="refresh-tasks-btn">
                    <i class="fas fa-sync-alt" style="margin-right: 0.5rem;"></i>刷新
                </button>
            </div>
        </div>

        <!-- 小红书发布折叠框 -->
        <div id="xhs-publish-collapse" class="publish-collapse" style="display: none;">
            <div class="publish-form-card">
                <div class="publish-form-header">
                    <h5><i class="fas fa-feather-alt" style="margin-right: 0.5rem;"></i>小红书发布参数</h5>
                </div>
                <div class="mc-form-group">
                    <label>内容类型</label>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-secondary is-active" data-type="image" id="xhs-btn-type-image">
                            <i class="fas fa-images" style="margin-right: 0.25rem;"></i>图文
                        </button>
                        <button type="button" class="btn btn-secondary" data-type="video" id="xhs-btn-type-video">
                            <i class="fas fa-video" style="margin-right: 0.25rem;"></i>视频
                        </button>
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
                        <button type="button" class="btn btn-primary" id="xhs-publish-btn">
                            <i class="fas fa-paper-plane" style="margin-right: 0.5rem;"></i>立即发布
                        </button>
                        <button type="button" class="btn btn-secondary" id="xhs-clear-btn">
                            <i class="fas fa-eraser" style="margin-right: 0.5rem;"></i>清空
                        </button>
                        <button type="button" class="btn btn-secondary" id="xhs-cancel-btn">
                            <i class="fas fa-times" style="margin-right: 0.5rem;"></i>取消
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- 状态筛选标签 -->
        <div class="task-filter-tabs">
            <button class="filter-tab is-active" data-status="all">
                <i class="fas fa-list"></i>
                <span>全部</span>
                <span class="tab-count" id="count-all">0</span>
            </button>
            <button class="filter-tab" data-status="queued">
                <i class="fas fa-clock"></i>
                <span>排队中</span>
                <span class="tab-count" id="count-queued">0</span>
            </button>
            <button class="filter-tab" data-status="processing">
                <i class="fas fa-spinner"></i>
                <span>处理中</span>
                <span class="tab-count" id="count-processing">0</span>
            </button>
            <button class="filter-tab" data-status="success">
                <i class="fas fa-check-circle"></i>
                <span>成功</span>
                <span class="tab-count" id="count-success">0</span>
            </button>
            <button class="filter-tab" data-status="failed">
                <i class="fas fa-times-circle"></i>
                <span>失败</span>
                <span class="tab-count" id="count-failed">0</span>
            </button>
        </div>

        <!-- 队列统计 -->
        <div class="queue-stats-bar">
            <div class="stat-item">
                <i class="fas fa-layer-group"></i>
                <span id="queue-stats">加载中...</span>
            </div>
        </div>

        <!-- 任务列表 -->
        <div id="task-list" class="task-list-container"></div>
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
        margin-bottom: 1.5rem;
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

    /* 任务展开箭头样式 */
    .task-toggle-icon {
        font-size: 1em;
        margin-right: 0.5rem;
        color: #0066cc;
        transition: transform 0.2s ease;
        display: inline-block;
    }
    .task-toggle-icon.expanded {
        transform: rotate(180deg);
    }

    /* 发布表单卡片 */
    .publish-form-card {
        background: var(--card-bg, white);
        border: 1px solid var(--border-color, #e2e8f0);
        border-radius: 0.5rem;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    }
    .publish-form-header {
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid var(--border-color, #e2e8f0);
    }
    .publish-form-header h5 {
        margin: 0;
        color: var(--primary-color, #0066cc);
        font-size: 1.125rem;
        font-weight: 600;
        display: flex;
        align-items: center;
    }

    /* 详情值样式 */
    .detail-value {
        padding: 0.75rem;
        background: var(--bg-color, #f9fafb);
        border: 1px solid var(--border-color, #e5e7eb);
        border-radius: 0.375rem;
        color: var(--text-color, #374151);
    }

    /* Alert样式 */
    .alert {
        padding: 0.75rem 1rem;
        border-radius: 0.375rem;
        border: 1px solid;
    }
    .alert-danger {
        background: #fee2e2;
        color: #991b1b;
        border-color: #fecaca;
    }

    /* 状态筛选标签 */
    .task-filter-tabs {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
        padding: 0.75rem;
        background: var(--bg-color, #f8f9fa);
        border-radius: 0.5rem;
        flex-wrap: wrap;
    }
    .filter-tab {
        flex: 1;
        min-width: 120px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 0.75rem 1rem;
        background: white;
        border: 2px solid var(--border-color, #e2e8f0);
        border-radius: 0.375rem;
        color: var(--text-color, #374151);
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        position: relative;
    }
    .filter-tab:hover {
        background: var(--item-bg, #f3f4f6);
        border-color: var(--primary-color, #0066cc);
        transform: translateY(-1px);
    }
    .filter-tab.is-active {
        background: var(--primary-color, #0066cc);
        color: white;
        border-color: var(--primary-color, #0066cc);
        box-shadow: 0 2px 4px rgba(0, 102, 204, 0.2);
    }
    .filter-tab i {
        font-size: 1rem;
    }
    .tab-count {
        background: rgba(0, 0, 0, 0.1);
        padding: 0.125rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.75rem;
        font-weight: 600;
        min-width: 24px;
        text-align: center;
    }
    .filter-tab.is-active .tab-count {
        background: rgba(255, 255, 255, 0.3);
    }

    /* 队列统计栏 */
    .queue-stats-bar {
        display: flex;
        align-items: center;
        gap: 1.5rem;
        padding: 0.875rem 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(102, 126, 234, 0.2);
    }
    .queue-stats-bar .stat-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.9rem;
    }
    .queue-stats-bar i {
        font-size: 1.25rem;
        opacity: 0.9;
    }

    /* 任务列表容器 */
    .task-list-container {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    /* 任务卡片样式优化 */
    .task-item {
        background: var(--card-bg, white);
        border: 1px solid var(--border-color, #e2e8f0);
        border-radius: 0.5rem;
        padding: 1rem;
        transition: all 0.2s ease;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
        cursor: pointer;
    }
    .task-item:hover {
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-color: var(--primary-color, #0066cc);
    }
    .task-item-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        user-select: none;
    }
    .task-item-header:hover .task-toggle-icon {
        color: var(--primary-color, #0066cc);
    }
    .task-item-title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex: 1;
        font-weight: 500;
        color: var(--text-color, #1f2937);
    }
    .task-status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.025em;
    }
    .task-status-badge.queued {
        background: #fef3c7;
        color: #92400e;
    }
    .task-status-badge.processing {
        background: #dbeafe;
        color: #1e40af;
    }
    .task-status-badge.success {
        background: #d1fae5;
        color: #065f46;
    }
    .task-status-badge.failed {
        background: #fee2e2;
        color: #991b1b;
    }
    .task-status-badge.pending {
        background: #f3f4f6;
        color: #4b5563;
    }

    /* 任务详情 */
    .task-details {
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 2px solid var(--border-color, #e2e8f0);
    }

    /* 删除按钮样式 - 与登录页面退出按钮保持一致 */
    .btn-delete {
        background: #fee2e2 !important;
        color: #991b1b !important;
        border-color: #fecaca !important;
    }
    .btn-delete:hover {
        background: #fecaca !important;
        color: #7f1d1d !important;
        border-color: #fca5a5 !important;
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
