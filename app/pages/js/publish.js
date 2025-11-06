// 发布管理页面 JavaScript（重新设计的折叠式渠道发布）

// 帮助：状态展示
function getStatusColor(status) {
  const colors = {
    pending: 'secondary',
    queued: 'info', 
    processing: 'warning',
    success: 'success',
    failed: 'danger',
    cancelled: 'dark',
  };
  return colors[status] || 'secondary';
}

function getStatusText(status) {
  const texts = {
    pending: '待处理',
    queued: '已入队',
    processing: '处理中',
    success: '成功',
    failed: '失败',
    cancelled: '已取消',
  };
  return texts[status] || status;
}

// 显示/隐藏发布渠道折叠框
function togglePublishCollapse(platform) {
  // 隐藏所有折叠框
  document.querySelectorAll('.publish-collapse').forEach(el => {
    el.style.display = 'none';
  });
  
  // 显示指定平台的折叠框
  const targetCollapse = document.getElementById(`${platform}-publish-collapse`);
  
  if (targetCollapse) {
    targetCollapse.style.display = 'block';
    // 滚动到折叠框位置
    setTimeout(() => {
      targetCollapse.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  }
}

// 小红书发布内容
async function publishXhsContent() {
  const contentType = document.getElementById('xhs-content-type').value || 'image';
  const title = document.getElementById('xhs-title').value.trim();
  const content = document.getElementById('xhs-content').value.trim();
  const tags = document.getElementById('xhs-tags').value.split(',').map(t => t.trim()).filter(Boolean);
  const location = document.getElementById('xhs-location').value.trim();
  const isPrivate = document.getElementById('xhs-is-private').checked;

  if (!title || !content) {
    alert('请填写标题和内容');
    return;
  }

  const publishBtn = document.getElementById('xhs-publish-btn');
  publishBtn.disabled = true;
  publishBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>发布中...';

  try {
    // 创建FormData对象用于文件上传
    const formData = new FormData();
    formData.append('title', title);
    formData.append('content', content);
    formData.append('tags', JSON.stringify(tags));
    if (location) formData.append('location', location);
    if (isPrivate) formData.append('is_private', 'true');

    let response;
    if (contentType === 'image') {
      const imageFiles = document.getElementById('xhs-image-files').files;
      if (!imageFiles || imageFiles.length === 0) {
        alert('请选择至少一张图片');
        return;
      }
      if (imageFiles.length > 9) {
        alert('最多支持9张图片');
        return;
      }
      
      // 添加图片文件到FormData
      for (let i = 0; i < imageFiles.length; i++) {
        formData.append('images', imageFiles[i]);
      }
      
      response = await fetch('/api/publish/xhs/image', {
        method: 'POST',
        body: formData, // 使用FormData，不设置Content-Type
      });
    } else {
      const videoFile = document.getElementById('xhs-video-file').files[0];
      if (!videoFile) {
        alert('请选择视频文件');
        return;
      }
      
      // 添加视频文件到FormData
      formData.append('video', videoFile);
      
      response = await fetch('/api/publish/xhs/video', {
        method: 'POST',
        body: formData, // 使用FormData，不设置Content-Type
      });
    }

    const result = await response.json();
    if (response.ok) {
      alert('发布任务已提交，正在处理中...');
      clearXhsForm();
      document.getElementById('xhs-publish-collapse').style.display = 'none';
      refreshTasks();
    } else {
      alert('发布失败: ' + (result.detail || result.error || '未知错误'));
    }
  } catch (err) {
    alert('发布失败: ' + err.message);
  } finally {
    publishBtn.disabled = false;
    publishBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>立即发布';
  }
}

// 处理图片文件
function handleImageFiles(files) {
  const preview = document.getElementById('xhs-image-preview');
  preview.innerHTML = '';

  if (files.length > 9) {
    alert('最多只能选择9张图片');
    return;
  }

  Array.from(files).forEach((file, index) => {
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = function (e) {
        const div = document.createElement('div');
        div.className = 'image-preview-item';
        div.innerHTML = `
          <img src="${e.target.result}" alt="预览图片">
          <button type="button" class="remove-btn" onclick="removeImagePreview(this, ${index})">×</button>
        `;
        preview.appendChild(div);
      };
      reader.readAsDataURL(file);
    }
  });
}

// 处理视频文件
function handleVideoFile(file) {
  const preview = document.getElementById('xhs-video-preview');
  preview.innerHTML = '';

  if (file && file.type.startsWith('video/')) {
    const video = document.createElement('video');
    video.src = URL.createObjectURL(file);
    video.className = 'img-thumbnail';
    video.style.width = '200px';
    video.style.maxHeight = '150px';
    video.controls = true;
    preview.appendChild(video);
  }
}

// 删除图片预览
function removeImagePreview(button, index) {
  const imageFiles = document.getElementById('xhs-image-files');
  const dt = new DataTransfer();
  
  // 重新构建文件列表，排除被删除的文件
  Array.from(imageFiles.files).forEach((file, i) => {
    if (i !== index) {
      dt.items.add(file);
    }
  });
  
  imageFiles.files = dt.files;
  button.parentElement.remove();
}

// 清空小红书表单
function clearXhsForm() {
  document.getElementById('xhs-title').value = '';
  document.getElementById('xhs-content').value = '';
  document.getElementById('xhs-tags').value = '';
  document.getElementById('xhs-topics').value = '';
  document.getElementById('xhs-location').value = '';
  document.getElementById('xhs-image-files').value = '';
  document.getElementById('xhs-video-file').value = '';
  document.getElementById('xhs-is-private').checked = false;
  document.getElementById('xhs-image-preview').innerHTML = '';
  document.getElementById('xhs-video-preview').innerHTML = '';
}

// 当前选中的状态过滤器
let currentFilter = 'all';

// 刷新任务列表
async function refreshTasks() {
  try {
    const response = await fetch('/api/publish/tasks');
    const data = await response.json();
    const taskList = document.getElementById('task-list');

    // 队列统计
    const statsEl = document.getElementById('queue-stats');
    if (data.stats) {
      const s = data.stats;
      statsEl.textContent = `排队中: ${s.queue_size ?? '-'} · 处理中: ${s.processing_count ?? '-'} · 最近1h发布: ${s.hourly_published ?? '-'} · 最近24h发布: ${s.daily_published ?? '-'}`;
    }

    // 保存所有任务到全局
    window.allTasks = data.tasks || [];

    // 计算状态数量
    updateStatusCounts(window.allTasks);

    // 根据当前过滤器渲染任务
    renderFilteredTasks(currentFilter);

  } catch (e) {
    console.error('刷新任务列表失败:', e);
  }
}

// 更新状态计数
function updateStatusCounts(tasks) {
  const counts = {
    all: tasks.length,
    queued: 0,
    processing: 0,
    success: 0,
    failed: 0,
    pending: 0
  };

  tasks.forEach(task => {
    if (counts[task.status] !== undefined) {
      counts[task.status]++;
    }
  });

  // 更新UI中的计数
  document.getElementById('count-all').textContent = counts.all;
  document.getElementById('count-queued').textContent = counts.queued;
  document.getElementById('count-processing').textContent = counts.processing;
  document.getElementById('count-success').textContent = counts.success;
  document.getElementById('count-failed').textContent = counts.failed;
}

// 根据过滤器渲染任务
function renderFilteredTasks(filterStatus) {
  const taskList = document.getElementById('task-list');
  const tasks = window.allTasks || [];

  // 过滤任务
  const filteredTasks = filterStatus === 'all'
    ? tasks
    : tasks.filter(task => task.status === filterStatus);

  if (filteredTasks.length > 0) {
    taskList.innerHTML = filteredTasks
      .map((task) => `
        <div class="task-item" id="task-${task.task_id}" data-status="${task.status}" onclick="toggleTaskDetails('${task.task_id}', '${task.platform}', event)">
          <div class="task-item-header">
            <div class="task-item-title">
              <i class="fas fa-chevron-down task-toggle-icon" id="toggle-icon-${task.task_id}"></i>
              <span>${task.platform.toUpperCase()} - ${task.content_type === 'image' ? '图文' : '视频'}</span>
            </div>
            <span class="task-status-badge ${task.status}">${getStatusText(task.status)}</span>
          </div>
          ${task.status === 'processing' ? `
          <div style="margin-top: 0.75rem; pointer-events: none;">
            <div class="progress" style="height: 6px;">
              <div class="progress-bar" role="progressbar" style="width: ${task.progress || 0}%" aria-valuenow="${task.progress || 0}" aria-valuemin="0" aria-valuemax="100"></div>
            </div>
          </div>` : ''}
          ${task.message ? `
          <div style="margin-top: 0.5rem; font-size: 0.875rem; color: var(--text-muted, #6b7280); pointer-events: none;">
            ${task.message}
          </div>` : ''}
          <div style="margin-top: 0.5rem; font-size: 0.75rem; color: var(--text-muted, #9ca3af); pointer-events: none;">
            创建时间: ${new Date(task.created_at * 1000).toLocaleString()}
          </div>
          ${task.note_url ? `
          <div style="margin-top: 0.75rem;" onclick="event.stopPropagation()">
            <a href="${task.note_url}" target="_blank" class="btn btn-sm btn-outline-primary">
              <i class="fas fa-external-link-alt" style="margin-right: 0.25rem;"></i>查看笔记
            </a>
          </div>` : ''}

          <!-- 任务详情（默认隐藏） -->
          <div class="task-details" id="details-${task.task_id}" style="display: none;">
            <div class="mc-spinner" style="margin: 1rem auto;"></div>
          </div>
        </div>
      `)
      .join('');
  } else {
    const filterText = filterStatus === 'all' ? '发布任务' : `${getStatusText(filterStatus)}任务`;
    taskList.innerHTML = `
      <div class="text-center p-4 text-muted" style="background: var(--card-bg, white); border-radius: 0.5rem; border: 1px dashed var(--border-color, #e2e8f0);">
        <i class="fas fa-inbox fa-2x mb-2" style="opacity: 0.5;"></i>
        <p style="margin: 0;">暂无${filterText}</p>
      </div>`;
  }
}

// 切换过滤器
function switchFilter(status) {
  currentFilter = status;

  // 更新标签active状态
  document.querySelectorAll('.filter-tab').forEach(tab => {
    if (tab.dataset.status === status) {
      tab.classList.add('is-active');
    } else {
      tab.classList.remove('is-active');
    }
  });

  // 重新渲染任务列表
  renderFilteredTasks(status);
}

// 切换任务详情显示
async function toggleTaskDetails(taskId, platform, event) {
  // 阻止事件冒泡
  if (event) {
    event.stopPropagation();
  }

  const detailsEl = document.getElementById(`details-${taskId}`);
  const iconEl = document.getElementById(`toggle-icon-${taskId}`);

  if (detailsEl.style.display === 'none') {
    // 展开：加载详情
    detailsEl.style.display = 'block';
    iconEl.classList.add('expanded');
    await loadTaskDetails(taskId, platform);
  } else {
    // 收起
    detailsEl.style.display = 'none';
    iconEl.classList.remove('expanded');
  }
}

// 加载任务详情
async function loadTaskDetails(taskId, platform) {
  const detailsEl = document.getElementById(`details-${taskId}`);

  try {
    const response = await fetch(`/api/publish/task/${taskId}?platform=${platform}`);
    if (!response.ok) {
      detailsEl.innerHTML = '<div class="alert alert-danger">加载失败</div>';
      return;
    }

    const task = await response.json();
    const payload = task.payload || {};
    // 允许排队中和失败的任务编辑
    const canEdit = task.status === 'queued' || task.status === 'failed';
    const canResubmit = task.status === 'failed';

    // 使用与发布表单一致的样式
    let detailsHtml = '<div class="publish-form-card" onclick="event.stopPropagation();">';
    detailsHtml += '<div class="publish-form-header"><h5><i class="fas fa-info-circle" style="margin-right: 0.5rem;"></i>任务详情</h5></div>';

    // 基本信息
    detailsHtml += '<div class="mc-form-group"><label>标题</label>';
    detailsHtml += `<div class="detail-value">${payload.title || '-'}</div></div>`;

    detailsHtml += '<div class="mc-form-group"><label>内容</label>';
    detailsHtml += `<div class="detail-value" style="white-space: pre-wrap;">${payload.content || '-'}</div></div>`;

    detailsHtml += '<div class="mc-form-group"><label>标签</label>';
    detailsHtml += `<div class="detail-value">${(payload.tags || []).join(', ') || '-'}</div></div>`;

    if (payload.location) {
      detailsHtml += '<div class="mc-form-group"><label>位置</label>';
      detailsHtml += `<div class="detail-value">${payload.location}</div></div>`;
    }

    // 媒体信息
    if (task.content_type === 'image' && payload.image_paths) {
      detailsHtml += '<div class="mc-form-group"><label>图片</label>';
      detailsHtml += `<div class="detail-value">共 ${payload.image_paths.length} 张图片</div></div>`;
    } else if (task.content_type === 'video' && payload.video_path) {
      detailsHtml += '<div class="mc-form-group"><label>视频</label>';
      detailsHtml += `<div class="detail-value">已上传</div></div>`;
    }

    // 任务状态信息
    if (task.error_detail) {
      detailsHtml += '<div class="mc-form-group"><label>错误详情</label>';
      detailsHtml += `<div class="alert alert-danger" style="margin-bottom: 0;">${task.error_detail}</div></div>`;
    }

    if (task.retry_count > 0) {
      detailsHtml += '<div class="mc-form-group"><label>重试次数</label>';
      detailsHtml += `<div class="detail-value">${task.retry_count} 次</div></div>`;
    }

    // 操作按钮
    if (canEdit || canResubmit || task.status === 'failed' || task.status === 'success') {
      detailsHtml += '<div class="mc-form-group"><div class="btn-group">';

      if (canEdit) {
        detailsHtml += `
          <button class="btn btn-primary" onclick="editTask('${taskId}', '${platform}'); event.stopPropagation();">
            <i class="fas fa-edit" style="margin-right: 0.5rem;"></i>编辑参数
          </button>`;
      }

      if (canResubmit) {
        detailsHtml += `
          <button class="btn btn-success" onclick="resubmitTask('${taskId}', '${platform}'); event.stopPropagation();">
            <i class="fas fa-redo" style="margin-right: 0.5rem;"></i>重新提交
          </button>`;
      }

      // 允许删除失败、成功和排队中的任务
      if (task.status === 'failed' || task.status === 'success' || task.status === 'queued') {
        detailsHtml += `
          <button class="btn btn-delete" onclick="deleteTask('${taskId}', '${platform}'); event.stopPropagation();">
            <i class="fas fa-trash" style="margin-right: 0.5rem;"></i>删除
          </button>`;
      }

      detailsHtml += '</div></div>';
    }

    detailsHtml += '</div>'; // close publish-form-card

    detailsEl.innerHTML = detailsHtml;

  } catch (e) {
    console.error('加载任务详情失败:', e);
    detailsEl.innerHTML = '<div class="alert alert-danger">加载失败: ' + e.message + '</div>';
  }
}

// 编辑任务
async function editTask(taskId, platform) {
  // 先获取最新的任务数据
  const response = await fetch(`/api/publish/task/${taskId}?platform=${platform}`);
  if (!response.ok) {
    alert('获取任务数据失败');
    return;
  }

  const task = await response.json();
  const payload = task.payload || {};

  // 创建编辑表单，使用与发布表单一致的样式
  const detailsEl = document.getElementById(`details-${taskId}`);
  detailsEl.innerHTML = `
    <div class="publish-form-card" onclick="event.stopPropagation();">
      <div class="publish-form-header">
        <h5><i class="fas fa-edit" style="margin-right: 0.5rem;"></i>编辑任务参数</h5>
      </div>
      <div class="mc-form-group">
        <label for="edit-title-${taskId}">标题</label>
        <input type="text" class="form-control" id="edit-title-${taskId}" value="${payload.title || ''}" placeholder="请输入标题">
      </div>
      <div class="mc-form-group">
        <label for="edit-content-${taskId}">内容</label>
        <textarea class="form-control" id="edit-content-${taskId}" rows="5" placeholder="请输入内容">${payload.content || ''}</textarea>
      </div>
      <div class="mc-form-group">
        <label for="edit-tags-${taskId}">标签</label>
        <input type="text" class="form-control" id="edit-tags-${taskId}" value="${(payload.tags || []).join(', ')}" placeholder="多个标签用逗号分隔">
      </div>
      <div class="mc-form-group">
        <label for="edit-location-${taskId}">位置（可选）</label>
        <input type="text" class="form-control" id="edit-location-${taskId}" value="${payload.location || ''}" placeholder="请输入地点">
      </div>
      <div class="mc-form-group">
        <div class="btn-group">
          <button class="btn btn-success" onclick="saveTaskEdit('${taskId}', '${platform}'); event.stopPropagation();">
            <i class="fas fa-check" style="margin-right: 0.5rem;"></i>保存
          </button>
          <button class="btn btn-secondary" onclick="loadTaskDetails('${taskId}', '${platform}'); event.stopPropagation();">
            <i class="fas fa-times" style="margin-right: 0.5rem;"></i>取消
          </button>
        </div>
      </div>
    </div>
  `;
}

// 保存任务编辑
async function saveTaskEdit(taskId, platform) {
  const title = document.getElementById(`edit-title-${taskId}`)?.value.trim();
  const content = document.getElementById(`edit-content-${taskId}`)?.value.trim();
  const tagsStr = document.getElementById(`edit-tags-${taskId}`)?.value.trim();
  const location = document.getElementById(`edit-location-${taskId}`)?.value.trim();

  if (!title || !content) {
    alert('标题和内容不能为空');
    return;
  }

  const tags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(Boolean) : [];

  const changes = {
    title,
    content,
    tags
  };

  if (location) {
    changes.location = location;
  }

  try {
    const response = await fetch(`/api/publish/task/${taskId}?platform=${platform}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ changes })
    });

    const result = await response.json();

    if (response.ok) {
      alert('任务已更新');
      await loadTaskDetails(taskId, platform);
      await refreshTasks(); // 刷新任务列表
    } else {
      alert('更新失败: ' + (result.error || '未知错误'));
    }
  } catch (e) {
    alert('更新失败: ' + e.message);
  }
}

// 重新提交失败的任务
async function resubmitTask(taskId, platform) {
  if (!confirm('确定要重新提交这个任务吗？')) {
    return;
  }

  try {
    // 先获取任务数据
    const getResponse = await fetch(`/api/publish/task/${taskId}?platform=${platform}`);
    if (!getResponse.ok) {
      alert('获取任务数据失败');
      return;
    }

    const task = await getResponse.json();

    // 调用重新提交API
    const response = await fetch(`/api/publish/task/${taskId}/resubmit?platform=${platform}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    const result = await response.json();

    if (response.ok) {
      alert('任务已重新提交到发布队列');
      // 关闭详情面板
      const detailsEl = document.getElementById(`details-${taskId}`);
      const iconEl = document.getElementById(`toggle-icon-${taskId}`);
      detailsEl.style.display = 'none';
      iconEl.classList.remove('expanded');
      // 刷新任务列表
      await refreshTasks();
    } else {
      alert('重新提交失败: ' + (result.error || result.detail || '未知错误'));
    }
  } catch (e) {
    alert('重新提交失败: ' + e.message);
  }
}

// 删除任务
async function deleteTask(taskId, platform) {
  if (!confirm('确定要删除这个任务吗？删除后无法恢复。')) {
    return;
  }

  try {
    const response = await fetch(`/api/publish/task/${taskId}?platform=${platform}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' }
    });

    const result = await response.json();

    if (response.ok) {
      alert('任务已删除');
      // 刷新任务列表
      await refreshTasks();
    } else {
      alert('删除失败: ' + (result.error || result.detail || '未知错误'));
    }
  } catch (e) {
    alert('删除失败: ' + e.message);
  }
}

// 绑定交互
function bindInteractions() {  
  // 渠道按钮点击事件
  const btnPublishXhs = document.getElementById('btn-publish-xhs');
  if (btnPublishXhs) {
    btnPublishXhs.addEventListener('click', () => {
      togglePublishCollapse('xhs');
    });
  }
  
  const btnPublishDy = document.getElementById('btn-publish-dy');
  if (btnPublishDy) {
    btnPublishDy.addEventListener('click', () => {
      alert('抖音发布功能暂未开放');
    });
  }

  // 小红书内容类型切换
  const xhsBtnImage = document.getElementById('xhs-btn-type-image');
  const xhsBtnVideo = document.getElementById('xhs-btn-type-video');
  const xhsContentType = document.getElementById('xhs-content-type');
  const xhsImageSection = document.getElementById('xhs-image-upload-section');
  const xhsVideoSection = document.getElementById('xhs-video-upload-section');
  
  if (xhsBtnImage && xhsBtnVideo) {
    xhsBtnImage.addEventListener('click', () => {
      xhsBtnImage.classList.add('is-active');
      xhsBtnVideo.classList.remove('is-active');
      xhsContentType.value = 'image';
      xhsImageSection.classList.remove('is-hidden');
      xhsVideoSection.classList.add('is-hidden');
    });
    xhsBtnVideo.addEventListener('click', () => {
      xhsBtnVideo.classList.add('is-active');
      xhsBtnImage.classList.remove('is-active');
      xhsContentType.value = 'video';
      xhsImageSection.classList.add('is-hidden');
      xhsVideoSection.classList.remove('is-hidden');
    });
  }

  // 小红书文件上传交互
  const xhsChooseImages = document.getElementById('xhs-choose-images');
  const xhsImageFiles = document.getElementById('xhs-image-files');
  const xhsImageDropzone = document.getElementById('xhs-image-dropzone');
  const xhsChooseVideo = document.getElementById('xhs-choose-video');
  const xhsVideoFile = document.getElementById('xhs-video-file');
  const xhsVideoDropzone = document.getElementById('xhs-video-dropzone');

  // 图片选择按钮
  if (xhsChooseImages && xhsImageFiles) {
    xhsChooseImages.addEventListener('click', () => xhsImageFiles.click());
  }

  // 视频选择按钮
  if (xhsChooseVideo && xhsVideoFile) {
    xhsChooseVideo.addEventListener('click', () => xhsVideoFile.click());
  }

  // 图片文件选择事件
  if (xhsImageFiles) {
    xhsImageFiles.addEventListener('change', (e) => {
      handleImageFiles(e.target.files);
    });
  }

  // 视频文件选择事件
  if (xhsVideoFile) {
    xhsVideoFile.addEventListener('change', (e) => {
      handleVideoFile(e.target.files[0]);
    });
  }

  // 图片拖拽事件
  if (xhsImageDropzone) {
    xhsImageDropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      xhsImageDropzone.classList.add('dragover');
    });

    xhsImageDropzone.addEventListener('dragleave', (e) => {
      e.preventDefault();
      xhsImageDropzone.classList.remove('dragover');
    });

    xhsImageDropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      xhsImageDropzone.classList.remove('dragover');
      const files = Array.from(e.dataTransfer.files).filter(file => file.type.startsWith('image/'));
      if (files.length > 0) {
        // 创建新的文件列表
        const dt = new DataTransfer();
        files.forEach(file => dt.items.add(file));
        xhsImageFiles.files = dt.files;
        handleImageFiles(files);
      }
    });

    // 点击拖拽区域也能选择文件
    xhsImageDropzone.addEventListener('click', (e) => {
      if (e.target === xhsImageDropzone || e.target.tagName === 'P') {
        xhsImageFiles.click();
      }
    });
  }

  // 视频拖拽事件
  if (xhsVideoDropzone) {
    xhsVideoDropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      xhsVideoDropzone.classList.add('dragover');
    });

    xhsVideoDropzone.addEventListener('dragleave', (e) => {
      e.preventDefault();
      xhsVideoDropzone.classList.remove('dragover');
    });

    xhsVideoDropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      xhsVideoDropzone.classList.remove('dragover');
      const files = Array.from(e.dataTransfer.files).filter(file => file.type.startsWith('video/'));
      if (files.length > 0) {
        const dt = new DataTransfer();
        dt.items.add(files[0]);
        xhsVideoFile.files = dt.files;
        handleVideoFile(files[0]);
      }
    });

    // 点击拖拽区域也能选择文件
    xhsVideoDropzone.addEventListener('click', (e) => {
      if (e.target === xhsVideoDropzone || e.target.tagName === 'P') {
        xhsVideoFile.click();
      }
    });
  }
  const xhsPublishBtn = document.getElementById('xhs-publish-btn');
  if (xhsPublishBtn) xhsPublishBtn.addEventListener('click', publishXhsContent);
  
  const xhsClearBtn = document.getElementById('xhs-clear-btn');
  if (xhsClearBtn) xhsClearBtn.addEventListener('click', clearXhsForm);
  
  const xhsCancelBtn = document.getElementById('xhs-cancel-btn');
  if (xhsCancelBtn) {
    xhsCancelBtn.addEventListener('click', () => {
      document.getElementById('xhs-publish-collapse').style.display = 'none';
    });
  }

  // 刷新按钮
  const refreshTasksBtn = document.getElementById('refresh-tasks-btn');
  if (refreshTasksBtn) refreshTasksBtn.addEventListener('click', refreshTasks);

  const headerRefresh = document.getElementById('header-refresh-btn');
  if (headerRefresh) headerRefresh.addEventListener('click', refreshTasks);

  // 状态过滤标签
  document.querySelectorAll('.filter-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const status = tab.dataset.status;
      switchFilter(status);
    });
  });

  // 策略配置按钮
  const refreshStrategy = document.getElementById('refresh-strategy-btn');
  if (refreshStrategy) refreshStrategy.addEventListener('click', loadCurrentStrategy);

  const updateStrategyBtn = document.getElementById('update-strategy-btn');
  if (updateStrategyBtn) updateStrategyBtn.addEventListener('click', updateStrategy);
}

// 策略加载/更新
async function loadCurrentStrategy() {
  try {
    const response = await fetch('/api/publish/strategy/xhs');
    const data = await response.json();
    if (response.ok && data.strategy) {
      const s = data.strategy;
      document.getElementById('min-interval').value = s.min_interval;
      document.getElementById('daily-limit').value = s.daily_limit;
      document.getElementById('hourly-limit').value = s.hourly_limit;
      document.getElementById('retry-count').value = s.retry_count;
    }
  } catch (e) {
    console.error('加载策略配置失败:', e);
  }
}

async function updateStrategy() {
  const minInterval = parseInt(document.getElementById('min-interval').value || '300');
  const dailyLimit = parseInt(document.getElementById('daily-limit').value || '10');
  const hourlyLimit = parseInt(document.getElementById('hourly-limit').value || '5');
  const retryCount = parseInt(document.getElementById('retry-count').value || '3');
  
  if (minInterval < 60) {
    alert('最小间隔不能少于60秒');
    return;
  }
  if (dailyLimit < 1 || hourlyLimit < 1) {
    alert('发布限制必须大于0');
    return;
  }
  
  try {
    const res = await fetch('/api/publish/strategy/xhs', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        min_interval: minInterval,
        max_concurrent: 1,
        retry_count: retryCount,
        retry_delay: 60,
        daily_limit: dailyLimit,
        hourly_limit: hourlyLimit,
      }),
    });
    const result = await res.json();
    if (res.ok) {
      alert('策略配置已更新');
      loadCurrentStrategy();
    } else {
      alert('更新失败: ' + (result.error || result.detail || '未知错误'));
    }
  } catch (e) {
    alert('更新失败: ' + e.message);
  }
}

// 初始化
document.addEventListener('DOMContentLoaded', function () {
  bindInteractions();
  refreshTasks();
  loadCurrentStrategy();
  
  // 每30秒自动刷新任务列表
  setInterval(refreshTasks, 30000);
});
