// 发布管理页面JavaScript

// ============================================================================
// 模式切换
// ============================================================================

// 图片上传模式切换
document.querySelectorAll('input[name="image-upload-mode"]').forEach(radio => {
    radio.addEventListener('change', function() {
        const pathInput = document.getElementById('image-path-input');
        const fileInput = document.getElementById('image-file-input');

        if (this.value === 'path') {
            pathInput.classList.remove('d-none');
            fileInput.classList.add('d-none');
        } else {
            pathInput.classList.add('d-none');
            fileInput.classList.remove('d-none');
        }
    });
});

// 内容类型切换
document.querySelectorAll('input[name="content-type"]').forEach(radio => {
    radio.addEventListener('change', function() {
        const imageSection = document.getElementById('image-upload-section');
        const videoSection = document.getElementById('video-upload-section');

        if (this.value === 'image') {
            imageSection.classList.remove('d-none');
            videoSection.classList.add('d-none');
        } else {
            imageSection.classList.add('d-none');
            videoSection.classList.remove('d-none');
        }
    });
});

// ============================================================================
// 文件预览
// ============================================================================

// 图片预览
document.getElementById('image-files').addEventListener('change', function(e) {
    const preview = document.getElementById('image-preview');
    preview.innerHTML = '';

    if (e.target.files.length > 9) {
        alert('最多只能选择9张图片');
        e.target.value = '';
        return;
    }

    Array.from(e.target.files).forEach((file, index) => {
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const div = document.createElement('div');
                div.className = 'd-inline-block position-relative me-2 mb-2';
                div.innerHTML = `
                    <img src="${e.target.result}" class="img-thumbnail"
                         style="width: 80px; height: 80px; object-fit: cover;">
                    <button type="button" class="btn btn-sm btn-danger position-absolute top-0 end-0 m-1"
                            style="padding: 0.1rem 0.3rem;"
                            onclick="this.parentElement.remove()">
                        <i class="fas fa-times"></i>
                    </button>
                `;
                preview.appendChild(div);
            };
            reader.readAsDataURL(file);
        }
    });
});

// 视频预览
document.getElementById('video-file').addEventListener('change', function(e) {
    const preview = document.getElementById('video-preview');
    preview.innerHTML = '';

    if (e.target.files[0]) {
        const video = document.createElement('video');
        video.src = URL.createObjectURL(e.target.files[0]);
        video.className = 'img-thumbnail';
        video.style.width = '200px';
        video.controls = true;
        preview.appendChild(video);
    }
});

// ============================================================================
// 发布功能
// ============================================================================

// 发布内容
async function publishContent() {
    const platform = document.getElementById('platform-select').value;
    const contentType = document.querySelector('input[name="content-type"]:checked').value;
    const title = document.getElementById('title').value.trim();
    const content = document.getElementById('content').value.trim();
    const tags = document.getElementById('tags').value.split(',').map(t => t.trim()).filter(t => t);

    if (!title || !content) {
        alert('请填写标题和内容');
        return;
    }

    const publishBtn = document.getElementById('publish-btn');
    publishBtn.disabled = true;
    publishBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>发布中...';

    try {
        let response;

        if (contentType === 'image') {
            const uploadMode = document.querySelector('input[name="image-upload-mode"]:checked').value;
            let imagePaths = [];

            if (uploadMode === 'path') {
                const pathText = document.getElementById('image-paths').value.trim();
                if (!pathText) {
                    alert('请输入图片路径');
                    return;
                }
                imagePaths = pathText.split('\n').map(p => p.trim()).filter(p => p);
                if (imagePaths.length === 0) {
                    alert('请输入至少一张图片路径');
                    return;
                }
                if (imagePaths.length > 9) {
                    alert('最多支持9张图片');
                    return;
                }
            } else {
                const imageFiles = document.getElementById('image-files').files;
                if (imageFiles.length === 0) {
                    alert('请选择图片');
                    return;
                }
                alert('文件上传模式暂未实现，请使用本地路径模式');
                return;
            }

            response = await fetch('/api/publish/xhs/image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title, content, tags,
                    image_paths: imagePaths
                })
            });
        } else {
            const videoFile = document.getElementById('video-file').files[0];
            if (!videoFile) {
                alert('请选择视频');
                return;
            }

            const coverFile = document.getElementById('cover-file').files[0];
            const videoPath = videoFile.name;
            const coverPath = coverFile ? coverFile.name : null;

            response = await fetch('/api/publish/xhs/video', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title, content, tags,
                    video_path: videoPath,
                    cover_path: coverPath
                })
            });
        }

        const result = await response.json();

        if (response.ok) {
            alert('发布任务已提交，请在右侧查看进度');
            clearForm();
            refreshTasks();
        } else {
            alert('发布失败: ' + (result.detail || result.error));
        }
    } catch (error) {
        alert('发布失败: ' + error.message);
    } finally {
        publishBtn.disabled = false;
        publishBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>发布内容';
    }
}

// 清空表单
function clearForm() {
    document.getElementById('title').value = '';
    document.getElementById('content').value = '';
    document.getElementById('tags').value = '';
    document.getElementById('topics').value = '';
    document.getElementById('location').value = '';
    document.getElementById('image-paths').value = '';
    document.getElementById('image-files').value = '';
    document.getElementById('video-file').value = '';
    document.getElementById('cover-file').value = '';
    document.getElementById('is-private').checked = false;
    document.getElementById('image-preview').innerHTML = '';
    document.getElementById('video-preview').innerHTML = '';
}

// ============================================================================
// 任务列表
// ============================================================================

// 刷新任务列表
async function refreshTasks() {
    try {
        const response = await fetch('/api/publish/tasks');
        const data = await response.json();

        const taskList = document.getElementById('task-list');

        if (data.tasks && data.tasks.length > 0) {
            taskList.innerHTML = data.tasks.map(task => `
                <div class="task-item">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${task.platform.toUpperCase()} - ${task.content_type === 'image' ? '图文' : '视频'}</h6>
                            <p class="mb-1 text-muted small">${task.message}</p>
                        </div>
                        <span class="status-badge bg-${getStatusColor(task.status)} text-white">${getStatusText(task.status)}</span>
                    </div>

                    ${task.status === 'uploading' || task.status === 'processing' ? `
                        <div class="progress progress-mini mb-2">
                            <div class="progress-bar" style="width: ${task.progress}%"></div>
                        </div>
                    ` : ''}

                    ${task.note_url ? `
                        <div class="mt-2">
                            <a href="${task.note_url}" target="_blank" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-external-link-alt me-1"></i>查看笔记
                            </a>
                        </div>
                    ` : ''}

                    <div class="text-muted small mt-2">
                        创建时间: ${new Date(task.created_at * 1000).toLocaleString()}
                    </div>
                </div>
            `).join('');
        } else {
            taskList.innerHTML = `
                <div class="text-center p-4 text-muted">
                    <i class="fas fa-tasks fa-2x mb-2"></i>
                    <p>暂无发布任务</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('刷新任务列表失败:', error);
    }
}

function getStatusColor(status) {
    const colors = {
        'pending': 'secondary',
        'uploading': 'info',
        'processing': 'warning',
        'success': 'success',
        'failed': 'danger'
    };
    return colors[status] || 'secondary';
}

function getStatusText(status) {
    const texts = {
        'pending': '等待中',
        'uploading': '上传中',
        'processing': '处理中',
        'success': '成功',
        'failed': '失败'
    };
    return texts[status] || status;
}

// ============================================================================
// 发布策略
// ============================================================================

// 加载当前策略配置
async function loadCurrentStrategy() {
    try {
        const response = await fetch('/api/publish/strategy/xhs');
        const data = await response.json();

        if (response.ok && data.strategy) {
            const strategy = data.strategy;
            document.getElementById('min-interval').value = strategy.min_interval;
            document.getElementById('daily-limit').value = strategy.daily_limit;
            document.getElementById('hourly-limit').value = strategy.hourly_limit;
            document.getElementById('retry-count').value = strategy.retry_count;
        }
    } catch (error) {
        console.error('加载策略配置失败:', error);
    }
}

// 更新策略配置
async function updateStrategy() {
    const minInterval = parseInt(document.getElementById('min-interval').value);
    const dailyLimit = parseInt(document.getElementById('daily-limit').value);
    const hourlyLimit = parseInt(document.getElementById('hourly-limit').value);
    const retryCount = parseInt(document.getElementById('retry-count').value);

    if (minInterval < 60) {
        alert('最小间隔不能少于60秒');
        return;
    }

    if (dailyLimit < 1 || hourlyLimit < 1) {
        alert('发布限制必须大于0');
        return;
    }

    try {
        const response = await fetch('/api/publish/strategy/xhs', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                min_interval: minInterval,
                max_concurrent: 1,
                retry_count: retryCount,
                retry_delay: 60,
                daily_limit: dailyLimit,
                hourly_limit: hourlyLimit
            })
        });

        const result = await response.json();

        if (response.ok) {
            alert('策略配置已更新');
            loadCurrentStrategy();
        } else {
            alert('更新失败: ' + (result.error || result.detail));
        }
    } catch (error) {
        alert('更新失败: ' + error.message);
    }
}

// ============================================================================
// 页面初始化
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    refreshTasks();
    loadCurrentStrategy();
    // 每30秒自动刷新一次任务列表
    setInterval(refreshTasks, 30000);
});
