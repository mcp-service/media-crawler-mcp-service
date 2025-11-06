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

    if (data.tasks && data.tasks.length > 0) {
      taskList.innerHTML = data.tasks
        .map((task) => `
          <div class="task-item">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <div class="flex-grow-1">
                <h6 class="mb-1">${task.platform.toUpperCase()} - ${task.content_type === 'image' ? '图文' : '视频'}</h6>
                <p class="mb-1 text-muted small">${task.message || ''}</p>
              </div>
              <span class="status-badge bg-${getStatusColor(task.status)} text-white">${getStatusText(task.status)}</span>
            </div>
            ${task.status === 'processing' ? `
            <div class="progress progress-mini mb-2">
              <div class="progress-bar" style="width: ${task.progress || 0}%"></div>
            </div>` : ''}
            ${task.note_url ? `
            <div class="mt-2">
              <a href="${task.note_url}" target="_blank" class="btn btn-sm btn-outline-primary">
                <i class="fas fa-external-link-alt me-1"></i>查看笔记
              </a>
            </div>` : ''}
            <div class="text-muted small mt-2">创建时间: ${new Date(task.created_at * 1000).toLocaleString()}</div>
          </div>
        `)
        .join('');
    } else {
      taskList.innerHTML = `
        <div class="text-center p-4 text-muted">
          <i class="fas fa-tasks fa-2x mb-2"></i>
          <p>暂无发布任务</p>
        </div>`;
    }
  } catch (e) {
    console.error('刷新任务列表失败:', e);
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
