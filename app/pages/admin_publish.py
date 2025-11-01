# -*- coding: utf-8 -*-
"""发布管理页面"""

from starlette.responses import HTMLResponse

from .ui_base import build_page_with_nav


# ============================================================================
# 组件创建函数
# ============================================================================

def create_platform_selector() -> str:
    """创建平台选择器"""
    return """
    <div class="mb-3">
        <label class="form-label">发布平台</label>
        <select class="form-select" id="platform-select">
            <option value="xhs">小红书</option>
        </select>
    </div>
    """


def create_content_type_selector() -> str:
    """创建内容类型选择器"""
    return """
    <div class="mb-3">
        <label class="form-label">内容类型</label>
        <div class="btn-group w-100" role="group">
            <input type="radio" class="btn-check" name="content-type" id="type-image" value="image" checked>
            <label class="btn btn-outline-primary" for="type-image">图文</label>

            <input type="radio" class="btn-check" name="content-type" id="type-video" value="video">
            <label class="btn btn-outline-primary" for="type-video">视频</label>
        </div>
    </div>
    """


def create_title_input() -> str:
    """创建标题输入框"""
    return """
    <div class="mb-3">
        <label for="title" class="form-label">标题</label>
        <input type="text" class="form-control" id="title" placeholder="请输入标题">
    </div>
    """


def create_content_textarea() -> str:
    """创建正文内容输入框"""
    return """
    <div class="mb-3">
        <label for="content" class="form-label">正文内容</label>
        <textarea class="form-control" id="content" rows="4" placeholder="请输入正文内容"></textarea>
    </div>
    """


def create_tags_input() -> str:
    """创建标签输入框"""
    return """
    <div class="mb-3">
        <label for="tags" class="form-label">标签</label>
        <input type="text" class="form-control" id="tags" placeholder="多个标签用逗号分隔">
        <div class="form-text">例如：美食,推荐,好吃</div>
    </div>
    """


def create_topics_input() -> str:
    """创建话题输入框"""
    return """
    <div class="mb-3">
        <label for="topics" class="form-label">话题</label>
        <input type="text" class="form-control" id="topics" placeholder="多个话题用逗号分隔">
        <div class="form-text">例如：#美食探店,#周末好去处</div>
    </div>
    """


def create_image_upload_section() -> str:
    """创建图片上传区域"""
    return """
    <div class="mb-3" id="image-upload-section">
        <label class="form-label">图片</label>

        <!-- 选择上传模式 -->
        <div class="btn-group w-100 mb-2" role="group">
            <input type="radio" class="btn-check" name="image-upload-mode" id="image-path-mode" value="path" checked>
            <label class="btn btn-outline-secondary" for="image-path-mode">本地路径</label>

            <input type="radio" class="btn-check" name="image-upload-mode" id="image-file-mode" value="file">
            <label class="btn btn-outline-secondary" for="image-file-mode">文件上传</label>
        </div>

        <!-- 本地路径输入 -->
        <div id="image-path-input" class="mb-2">
            <textarea class="form-control" id="image-paths" rows="3"
                      placeholder="输入图片的本地绝对路径，每行一个&#10;例如：&#10;C:\\Users\\username\\Pictures\\image1.jpg&#10;C:\\Users\\username\\Pictures\\image2.jpg"></textarea>
            <div class="form-text">输入图片的完整路径，每行一个路径，最多9张图片</div>
        </div>

        <!-- 文件上传 -->
        <div id="image-file-input" class="d-none">
            <div class="border-dashed p-4 text-center" style="border: 2px dashed #dee2e6; border-radius: 8px;">
                <i class="fas fa-cloud-upload-alt fa-2x text-muted mb-2"></i>
                <p class="text-muted mb-2">点击上传图片或拖拽图片到此处</p>
                <input type="file" class="form-control d-none" id="image-files" multiple accept="image/*">
                <button type="button" class="btn btn-outline-primary" onclick="document.getElementById('image-files').click()">选择图片</button>
                <div class="form-text mt-2">支持JPG、PNG格式，最多9张图片</div>
            </div>
        </div>
        <div id="image-preview" class="mt-3"></div>
    </div>
    """


def create_video_upload_section() -> str:
    """创建视频上传区域"""
    return """
    <div class="mb-3 d-none" id="video-upload-section">
        <label class="form-label">视频</label>
        <div class="border-dashed p-4 text-center" style="border: 2px dashed #dee2e6; border-radius: 8px;">
            <i class="fas fa-video fa-2x text-muted mb-2"></i>
            <p class="text-muted mb-2">点击上传视频或拖拽视频到此处</p>
            <input type="file" class="form-control d-none" id="video-file" accept="video/*">
            <button type="button" class="btn btn-outline-primary" onclick="document.getElementById('video-file').click()">选择视频</button>
        </div>
        <div id="video-preview" class="mt-3"></div>

        <!-- 封面上传 -->
        <div class="mt-3">
            <label class="form-label">封面图片（可选）</label>
            <input type="file" class="form-control" id="cover-file" accept="image/*">
        </div>
    </div>
    """


def create_location_input() -> str:
    """创建位置信息输入框"""
    return """
    <div class="mb-3">
        <label for="location" class="form-label">位置信息（可选）</label>
        <input type="text" class="form-control" id="location" placeholder="请输入位置信息">
    </div>
    """


def create_privacy_checkbox() -> str:
    """创建隐私设置复选框"""
    return """
    <div class="mb-3">
        <div class="form-check">
            <input class="form-check-input" type="checkbox" id="is-private">
            <label class="form-check-label" for="is-private">
                私密发布（仅自己可见）
            </label>
        </div>
    </div>
    """


def create_publish_button() -> str:
    """创建发布按钮"""
    return """
    <div class="d-grid">
        <button type="button" class="btn btn-primary" id="publish-btn" onclick="publishContent()">
            <i class="fas fa-paper-plane me-2"></i>发布内容
        </button>
    </div>
    """


def create_publish_form_card() -> str:
    """创建发布表单卡片"""
    return f"""
    <div class="card">
        <div class="card-header">
            <h5>发布内容</h5>
        </div>
        <div class="card-body">
            {create_platform_selector()}
            {create_content_type_selector()}
            {create_title_input()}
            {create_content_textarea()}
            {create_tags_input()}
            {create_topics_input()}
            {create_image_upload_section()}
            {create_video_upload_section()}
            {create_location_input()}
            {create_privacy_checkbox()}
            {create_publish_button()}
        </div>
    </div>
    """


def create_strategy_form() -> str:
    """创建发布策略配置表单"""
    return """
    <form id="strategy-form">
        <div class="row">
            <div class="col-md-6">
                <div class="mb-2">
                    <label for="min-interval" class="form-label">最小间隔(秒)</label>
                    <input type="number" class="form-control form-control-sm" id="min-interval" min="60" value="300">
                </div>
            </div>
            <div class="col-md-6">
                <div class="mb-2">
                    <label for="daily-limit" class="form-label">每日限制</label>
                    <input type="number" class="form-control form-control-sm" id="daily-limit" min="1" value="10">
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6">
                <div class="mb-2">
                    <label for="hourly-limit" class="form-label">每小时限制</label>
                    <input type="number" class="form-control form-control-sm" id="hourly-limit" min="1" value="5">
                </div>
            </div>
            <div class="col-md-6">
                <div class="mb-2">
                    <label for="retry-count" class="form-label">重试次数</label>
                    <input type="number" class="form-control form-control-sm" id="retry-count" min="0" value="3">
                </div>
            </div>
        </div>
        <div class="d-grid">
            <button type="button" class="btn btn-sm btn-success" onclick="updateStrategy()">
                <i class="fas fa-save me-1"></i>保存策略
            </button>
        </div>
    </form>
    """


def create_strategy_card() -> str:
    """创建发布策略配置卡片"""
    return f"""
    <div class="card mb-3">
        <div class="card-header d-flex justify-content-between align-items-center">
            <h6>发布策略配置</h6>
            <button type="button" class="btn btn-sm btn-outline-primary" onclick="loadCurrentStrategy()">
                <i class="fas fa-refresh"></i> 刷新
            </button>
        </div>
        <div class="card-body">
            {create_strategy_form()}
        </div>
    </div>
    """


def create_task_list_card() -> str:
    """创建任务列表卡片"""
    return """
    <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
            <h5>发布任务</h5>
            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="refreshTasks()">
                <i class="fas fa-refresh"></i> 刷新
            </button>
        </div>
        <div class="card-body p-0">
            <div id="task-list">
                <div class="text-center p-4 text-muted">
                    <i class="fas fa-tasks fa-2x mb-2"></i>
                    <p>暂无发布任务</p>
                </div>
            </div>
        </div>
    </div>
    """


# ============================================================================
# 样式
# ============================================================================

def create_publish_styles() -> str:
    """创建发布页面样式"""
    return """
    <style>
    .border-dashed {
        transition: all 0.3s ease;
    }
    .border-dashed:hover {
        border-color: #007bff !important;
        background-color: #f8f9fa;
    }

    .task-item {
        border-bottom: 1px solid #dee2e6;
        padding: 1rem;
        transition: background-color 0.3s ease;
    }
    .task-item:hover {
        background-color: #f8f9fa;
    }
    .task-item:last-child {
        border-bottom: none;
    }

    .status-badge {
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
        border-radius: 0.375rem;
    }

    .progress-mini {
        height: 4px;
        border-radius: 2px;
    }
    </style>
    """


# ============================================================================
# JavaScript脚本
# ============================================================================

def create_publish_scripts() -> str:
    """引入发布页面JavaScript脚本"""
    return '<script src="/static/js/publish.js"></script>'


# ============================================================================
# 页面渲染
# ============================================================================

def render_publish_management_page() -> HTMLResponse:
    """渲染发布管理页面"""

    # Bootstrap和FontAwesome CDN
    cdn_links = """
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    """

    content = f"""
    {cdn_links}
    <div class="container-fluid">
        <div class="row">
            <!-- 左侧发布表单 -->
            <div class="col-md-6">
                {create_publish_form_card()}
            </div>

            <!-- 右侧任务列表和策略配置 -->
            <div class="col-md-6">
                {create_strategy_card()}
                {create_task_list_card()}
            </div>
        </div>
    </div>

    {create_publish_styles()}
    {create_publish_scripts()}
    """

    return build_page_with_nav(
        main_content=content,
        title="发布管理",
        current_path="/publish"
    )
