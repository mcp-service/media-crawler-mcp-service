# -*- coding: utf-8 -*-
"""发布管理页面"""

from starlette.responses import HTMLResponse

from .ui_base import (
    build_page_with_nav,
    create_nav_links,
    JS_LIBS
)


def render_publish_management_page() -> HTMLResponse:
    """渲染发布管理页面"""
    
    nav_links = create_nav_links("publish")
    
    content = f"""
    <div class="container-fluid">
        <div class="row">
            <!-- 左侧发布表单 -->
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>发布内容</h5>
                    </div>
                    <div class="card-body">
                        <!-- 平台选择 -->
                        <div class="mb-3">
                            <label class="form-label">发布平台</label>
                            <select class="form-select" id="platform-select">
                                <option value="xhs">小红书</option>
                            </select>
                        </div>
                        
                        <!-- 内容类型选择 -->
                        <div class="mb-3">
                            <label class="form-label">内容类型</label>
                            <div class="btn-group w-100" role="group">
                                <input type="radio" class="btn-check" name="content-type" id="type-image" value="image" checked>
                                <label class="btn btn-outline-primary" for="type-image">图文</label>
                                
                                <input type="radio" class="btn-check" name="content-type" id="type-video" value="video">
                                <label class="btn btn-outline-primary" for="type-video">视频</label>
                            </div>
                        </div>
                        
                        <!-- 标题 -->
                        <div class="mb-3">
                            <label for="title" class="form-label">标题</label>
                            <input type="text" class="form-control" id="title" placeholder="请输入标题">
                        </div>
                        
                        <!-- 正文内容 -->
                        <div class="mb-3">
                            <label for="content" class="form-label">正文内容</label>
                            <textarea class="form-control" id="content" rows="4" placeholder="请输入正文内容"></textarea>
                        </div>
                        
                        <!-- 标签 -->
                        <div class="mb-3">
                            <label for="tags" class="form-label">标签</label>
                            <input type="text" class="form-control" id="tags" placeholder="多个标签用逗号分隔">
                            <div class="form-text">例如：美食,推荐,好吃</div>
                        </div>
                        
                        <!-- 话题 -->
                        <div class="mb-3">
                            <label for="topics" class="form-label">话题</label>
                            <input type="text" class="form-control" id="topics" placeholder="多个话题用逗号分隔">
                            <div class="form-text">例如：#美食探店,#周末好去处</div>
                        </div>
                        
                        <!-- 图片上传区域 -->
                        <div class="mb-3" id="image-upload-section">
                            <label class="form-label">图片</label>
                            <div class="border-dashed p-4 text-center" style="border: 2px dashed #dee2e6; border-radius: 8px;">
                                <i class="fas fa-cloud-upload-alt fa-2x text-muted mb-2"></i>
                                <p class="text-muted mb-2">点击上传图片或拖拽图片到此处</p>
                                <input type="file" class="form-control d-none" id="image-files" multiple accept="image/*">
                                <button type="button" class="btn btn-outline-primary" onclick="document.getElementById('image-files').click()">选择图片</button>
                            </div>
                            <div id="image-preview" class="mt-3"></div>
                        </div>
                        
                        <!-- 视频上传区域 -->
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
                        
                        <!-- 位置信息 -->
                        <div class="mb-3">
                            <label for="location" class="form-label">位置信息（可选）</label>
                            <input type="text" class="form-control" id="location" placeholder="请输入位置信息">
                        </div>
                        
                        <!-- 隐私设置 -->
                        <div class="mb-3">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="is-private">
                                <label class="form-check-label" for="is-private">
                                    私密发布（仅自己可见）
                                </label>
                            </div>
                        </div>
                        
                        <!-- 发布按钮 -->
                        <div class="d-grid">
                            <button type="button" class="btn btn-primary" id="publish-btn" onclick="publishContent()">
                                <i class="fas fa-paper-plane me-2"></i>发布内容
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 右侧任务列表和策略配置 -->
            <div class="col-md-6">
                <!-- 发布策略配置 -->
                <div class="card mb-3">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6>发布策略配置</h6>
                        <button type="button" class="btn btn-sm btn-outline-primary" onclick="loadCurrentStrategy()">
                            <i class="fas fa-refresh"></i> 刷新
                        </button>
                    </div>
                    <div class="card-body">
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
                    </div>
                </div>
                
                <!-- 发布任务列表 -->
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
            </div>
        </div>
    </div>
    
    <style>
    .border-dashed {{
        transition: all 0.3s ease;
    }}
    .border-dashed:hover {{
        border-color: #007bff !important;
        background-color: #f8f9fa;
    }}
    
    .task-item {{
        border-bottom: 1px solid #dee2e6;
        padding: 1rem;
        transition: background-color 0.3s ease;
    }}
    .task-item:hover {{
        background-color: #f8f9fa;
    }}
    .task-item:last-child {{
        border-bottom: none;
    }}
    
    .status-badge {{
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
        border-radius: 0.375rem;
    }}
    
    .progress-mini {{
        height: 4px;
        border-radius: 2px;
    }}
    </style>
    
    <script>
    // 内容类型切换
    document.querySelectorAll('input[name="content-type"]').forEach(radio => {{
        radio.addEventListener('change', function() {{
            const imageSection = document.getElementById('image-upload-section');
            const videoSection = document.getElementById('video-upload-section');
            
            if (this.value === 'image') {{
                imageSection.classList.remove('d-none');
                videoSection.classList.add('d-none');
            }} else {{
                imageSection.classList.add('d-none');
                videoSection.classList.remove('d-none');
            }}
        }});
    }});
    
    // 图片预览
    document.getElementById('image-files').addEventListener('change', function(e) {{
        const preview = document.getElementById('image-preview');
        preview.innerHTML = '';
        
        Array.from(e.target.files).forEach(file => {{
            if (file.type.startsWith('image/')) {{
                const reader = new FileReader();
                reader.onload = function(e) {{
                    const img = document.createElement('img');
                    img.src = e.target.result;
                    img.className = 'img-thumbnail me-2 mb-2';
                    img.style.width = '80px';
                    img.style.height = '80px';
                    img.style.objectFit = 'cover';
                    preview.appendChild(img);
                }};
                reader.readAsDataURL(file);
            }}
        }});
    }});
    
    // 视频预览
    document.getElementById('video-file').addEventListener('change', function(e) {{
        const preview = document.getElementById('video-preview');
        preview.innerHTML = '';
        
        if (e.target.files[0]) {{
            const video = document.createElement('video');
            video.src = URL.createObjectURL(e.target.files[0]);
            video.className = 'img-thumbnail';
            video.style.width = '200px';
            video.controls = true;
            preview.appendChild(video);
        }}
    }});
    
    // 发布内容
    async function publishContent() {{
        const platform = document.getElementById('platform-select').value;
        const contentType = document.querySelector('input[name="content-type"]:checked').value;
        const title = document.getElementById('title').value.trim();
        const content = document.getElementById('content').value.trim();
        const tags = document.getElementById('tags').value.split(',').map(t => t.trim()).filter(t => t);
        const topics = document.getElementById('topics').value.split(',').map(t => t.trim()).filter(t => t);
        const location = document.getElementById('location').value.trim();
        const isPrivate = document.getElementById('is-private').checked;
        
        if (!title || !content) {{
            alert('请填写标题和内容');
            return;
        }}
        
        const publishBtn = document.getElementById('publish-btn');
        publishBtn.disabled = true;
        publishBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>发布中...';
        
        try {{
            let response;
            
            if (contentType === 'image') {{
                const imageFiles = document.getElementById('image-files').files;
                if (imageFiles.length === 0) {{
                    alert('请选择图片');
                    return;
                }}
                
                // 这里简化处理，实际需要先上传文件到服务器
                const imagePaths = Array.from(imageFiles).map(file => file.name);
                
                response = await fetch('/api/publish/xhs/image', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        title, content, tags, topics, location,
                        image_paths: imagePaths,
                        is_private: isPrivate
                    }})
                }});
            }} else {{
                const videoFile = document.getElementById('video-file').files[0];
                if (!videoFile) {{
                    alert('请选择视频');
                    return;
                }}
                
                const coverFile = document.getElementById('cover-file').files[0];
                const videoPath = videoFile.name;
                const coverPath = coverFile ? coverFile.name : null;
                
                response = await fetch('/api/publish/xhs/video', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        title, content, tags, topics, location,
                        video_path: videoPath,
                        cover_path: coverPath,
                        is_private: isPrivate
                    }})
                }});
            }}
            
            const result = await response.json();
            
            if (response.ok) {{
                alert('发布任务已提交，请在右侧查看进度');
                clearForm();
                refreshTasks();
            }} else {{
                alert('发布失败: ' + (result.detail || result.error));
            }}
        }} catch (error) {{
            alert('发布失败: ' + error.message);
        }} finally {{
            publishBtn.disabled = false;
            publishBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>发布内容';
        }}
    }}
    
    // 清空表单
    function clearForm() {{
        document.getElementById('title').value = '';
        document.getElementById('content').value = '';
        document.getElementById('tags').value = '';
        document.getElementById('topics').value = '';
        document.getElementById('location').value = '';
        document.getElementById('image-files').value = '';
        document.getElementById('video-file').value = '';
        document.getElementById('cover-file').value = '';
        document.getElementById('is-private').checked = false;
        document.getElementById('image-preview').innerHTML = '';
        document.getElementById('video-preview').innerHTML = '';
    }}
    
    // 刷新任务列表
    async function refreshTasks() {{
        try {{
            const response = await fetch('/api/publish/tasks');
            const data = await response.json();
            
            const taskList = document.getElementById('task-list');
            
            if (data.tasks && data.tasks.length > 0) {{
                taskList.innerHTML = data.tasks.map(task => `
                    <div class="task-item">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div class="flex-grow-1">
                                <h6 class="mb-1">${{task.platform.toUpperCase()}} - ${{task.content_type === 'image' ? '图文' : '视频'}}</h6>
                                <p class="mb-1 text-muted small">${{task.message}}</p>
                            </div>
                            <span class="status-badge bg-${{getStatusColor(task.status)}} text-white">${{getStatusText(task.status)}}</span>
                        </div>
                        
                        ${{task.status === 'uploading' || task.status === 'processing' ? `
                            <div class="progress progress-mini mb-2">
                                <div class="progress-bar" style="width: ${{task.progress}}%"></div>
                            </div>
                        ` : ''}}
                        
                        ${{task.note_url ? `
                            <div class="mt-2">
                                <a href="${{task.note_url}}" target="_blank" class="btn btn-sm btn-outline-primary">
                                    <i class="fas fa-external-link-alt me-1"></i>查看笔记
                                </a>
                            </div>
                        ` : ''}}
                        
                        <div class="text-muted small mt-2">
                            创建时间: ${{new Date(task.created_at * 1000).toLocaleString()}}
                        </div>
                    </div>
                `).join('');
            }} else {{
                taskList.innerHTML = `
                    <div class="text-center p-4 text-muted">
                        <i class="fas fa-tasks fa-2x mb-2"></i>
                        <p>暂无发布任务</p>
                    </div>
                `;
            }}
        }} catch (error) {{
            console.error('刷新任务列表失败:', error);
        }}
    }}
    
    function getStatusColor(status) {{
        const colors = {{
            'pending': 'secondary',
            'uploading': 'info',
            'processing': 'warning',
            'success': 'success',
            'failed': 'danger'
        }};
        return colors[status] || 'secondary';
    }}
    
    function getStatusText(status) {{
        const texts = {{
            'pending': '等待中',
            'uploading': '上传中',
            'processing': '处理中',
            'success': '成功',
            'failed': '失败'
        }};
        return texts[status] || status;
    }}
    
    // 加载当前策略配置
    async function loadCurrentStrategy() {{
        try {{
            const response = await fetch('/api/publish/strategy/xhs');
            const data = await response.json();
            
            if (response.ok && data.strategy) {{
                const strategy = data.strategy;
                document.getElementById('min-interval').value = strategy.min_interval;
                document.getElementById('daily-limit').value = strategy.daily_limit;
                document.getElementById('hourly-limit').value = strategy.hourly_limit;
                document.getElementById('retry-count').value = strategy.retry_count;
            }}
        }} catch (error) {{
            console.error('加载策略配置失败:', error);
        }}
    }}
    
    // 更新策略配置
    async function updateStrategy() {{
        const minInterval = parseInt(document.getElementById('min-interval').value);
        const dailyLimit = parseInt(document.getElementById('daily-limit').value);
        const hourlyLimit = parseInt(document.getElementById('hourly-limit').value);
        const retryCount = parseInt(document.getElementById('retry-count').value);
        
        if (minInterval < 60) {{
            alert('最小间隔不能少于60秒');
            return;
        }}
        
        if (dailyLimit < 1 || hourlyLimit < 1) {{
            alert('发布限制必须大于0');
            return;
        }}
        
        try {{
            const response = await fetch('/api/publish/strategy/xhs', {{
                method: 'PUT',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    min_interval: minInterval,
                    max_concurrent: 1,
                    retry_count: retryCount,
                    retry_delay: 60,
                    daily_limit: dailyLimit,
                    hourly_limit: hourlyLimit
                }})
            }});
            
            const result = await response.json();
            
            if (response.ok) {{
                alert('策略配置已更新');
                loadCurrentStrategy(); // 重新加载确认
            }} else {{
                alert('更新失败: ' + (result.error || result.detail));
            }}
        }} catch (error) {{
            alert('更新失败: ' + error.message);
        }}
    }}
    
    // 页面加载时刷新任务列表和策略配置
    document.addEventListener('DOMContentLoaded', function() {{
        refreshTasks();
        loadCurrentStrategy();
        // 每30秒自动刷新一次
        setInterval(refreshTasks, 30000);
    }});
    </script>
    """
    
    page_html = build_page_with_nav(
        title="发布管理",
        nav_links=nav_links,
        content=content,
        js_libs=JS_LIBS
    )
    
    return HTMLResponse(content=page_html)