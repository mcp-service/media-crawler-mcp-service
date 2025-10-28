// Config page JS extracted from inline script
// App mounted at /mcp
const API_BASE = '/api';

async function apiRequest(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    const ct = res.headers.get('content-type') || '';
    return ct.includes('application/json') ? res.json() : res.text();
  } catch (error) {
    console.error('API Request failed:', endpoint, error);
    throw error;
  }
}

async function loadPlatformConfig() {
  try {
    const r = await apiRequest('/config/platforms');
    const c = document.getElementById('platform-checkboxes');
    // all_platforms is an array of platform codes (strings). Some older shapes may use objects.
    const platforms = Array.isArray(r.platforms)
      ? r.platforms
      : Array.isArray(r.all_platforms)
      ? r.all_platforms
      : [];
    const enabled = Array.isArray(r.enabled_platforms) ? r.enabled_platforms : [];
    const names = r.platform_names || {};

    if (!platforms.length) {
      c.innerHTML = '<div style="color: #718096; padding: 1rem;">暂无可配置的平台</div>';
      return;
    }

    c.innerHTML = platforms
      .map((p) => {
        const code = typeof p === 'string' ? p : p?.code;
        if (!code) return '';
        const label = names[code] || code;
        return `
          <div style="margin: 0.75rem 0;">
            <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
              <input type='checkbox' name='platforms' value='${code}' ${enabled.includes(code) ? 'checked' : ''}>
              <span style="font-weight: 500;">${label}</span>
            </label>
          </div>
        `;
      })
      .join('');
  } catch (e) {
    console.error('加载平台配置失败:', e);
    document.getElementById('platform-checkboxes').innerHTML =
      '<div style="color: #dc2626; padding: 1rem;">加载平台配置失败</div>';
  }
}

async function loadCurrentConfig() {
  try {
    const [crawler, platform] = await Promise.all([
      apiRequest('/config/crawler'),
      apiRequest('/config/platforms'),
    ]);

    // 填充表单
    if (crawler.max_notes !== undefined)
      document.getElementById('max_notes').value = crawler.max_notes;
    if (crawler.max_comments_per_note !== undefined)
      document.getElementById('max_comments_per_note').value = crawler.max_comments_per_note;
    document.getElementById('enable_comments').checked = crawler.enable_comments !== false;
    document.getElementById('headless').checked = crawler.headless || false;
    if (crawler.save_data_option)
      document.getElementById('save_data_option').value = crawler.save_data_option;

    // 显示配置预览
    document.getElementById('config-display').innerHTML = `<pre style="font-size: 0.875rem; overflow-x: auto;">${JSON.stringify(
      { crawler, platform },
      null,
      2
    )}</pre>`;
  } catch (e) {
    console.error('加载配置失败:', e);
    document.getElementById('config-display').innerHTML = '<div style="color: #dc2626;">加载配置失败</div>';
  }
}

async function savePlatformConfig() {
  try {
    const selected = Array.from(document.querySelectorAll("input[name='platforms']:checked")).map((el) => el.value);
    const r = await apiRequest('/config/platforms', {
      method: 'PUT',
      body: JSON.stringify({ enabled_platforms: selected }),
    });

    if (r.need_restart) {
      document.getElementById('restart-warning').style.display = 'block';
    }

    // 刷新配置显示
    await loadCurrentConfig();

    alert('平台配置保存成功！');
  } catch (e) {
    alert('保存平台配置失败: ' + e.message);
  }
}

async function saveCrawlerConfig(form) {
  try {
    const fd = new FormData(form);
    const payload = {
      max_notes: parseInt(fd.get('max_notes'), 10),
      max_comments_per_note: parseInt(fd.get('max_comments_per_note'), 10),
      enable_comments: fd.get('enable_comments') === 'on',
      headless: fd.get('headless') === 'on',
      save_data_option: fd.get('save_data_option'),
    };

    const r = await apiRequest('/config/crawler', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });

    if (r.need_restart) {
      document.getElementById('restart-warning').style.display = 'block';
    }

    // 刷新配置显示
    await loadCurrentConfig();

    alert('爬虫配置保存成功！');
  } catch (e) {
    alert('保存爬虫配置失败: ' + e.message);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadPlatformConfig();
  loadCurrentConfig();

  const form = document.getElementById('crawler-config-form');
  form.addEventListener('submit', (ev) => {
    ev.preventDefault();
    saveCrawlerConfig(ev.target);
  });
});
