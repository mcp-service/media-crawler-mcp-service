// Inspector page JS extracted from inline script
// App is mounted at /mcp, ensure API calls include the prefix
const API_BASE = '/api';
let TARGET_BASE_URL = '';
let currentTool = null;
let MODE = 'tools';

// 示例请求体（用于“恢复默认”与初次展示）。
// 与 /api/admin/tools 返回的 tool.name 对齐。
const DEFAULT_PAYLOADS = {
  // B站 tools
  bili_search: { keywords: '纯圆大嬛嬛', page_size: 5, page_num: 1 },
  bili_crawler_detail: { video_ids: ['115285696846946'] },
  bili_crawler_creator: { creator_id: '99801185', page_num: 1, page_size: 30 },
  bili_search_time_range_http: {
    keywords: '纯圆大嬛嬛',
    start_day: '2024-01-01',
    end_day: '2024-01-07',
    page_size: 5,
    page_num: 1,
  },
  bili_crawler_comments: { video_ids: ['115285696846946'], max_comments: 20, fetch_sub_comments: false },

  // 小红书 tools
  xhs_search: { keywords: '纯圆大嬛嬛', page_num: 1, page_size: 20 },
  xhs_crawler_detail: { note_id: '68f9b8b20000000004010353', xsec_token: '<xsec_token>', xsec_source: '' },
  xhs_crawler_creator: { creator_id: 'user123', page_num: 1, page_size: 20 },
  xhs_crawler_comments: { note_id: '68f9b8b20000000004010353', xsec_token: '<xsec_token>', page_num: 1, page_size: 20 },
};

async function apiRequest(endpoint, options = {}) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
}

function renderSidebar({ groups = [], prompts = [], resources = [] }) {
  const el = document.getElementById('tool-list');
  const html = [];

  const renderGroup = (group) => {
    const tools = (group.tools || []).map((tool) => {
      const label = tool.display_name || tool.name;
      const route = (tool.http_methods?.length ? tool.http_methods.join(', ') : 'POST') + ' ' + (tool.http_path || '');
      
      // 直接使用工具中的 sampleKey，如果没有则生成
      const sampleKey = tool.sampleKey || tool.name;
      
      const payload = encodeURIComponent(
        JSON.stringify({ name: tool.name, sampleKey, description: tool.description, path: tool.http_path, methods: tool.http_methods }, null, 0)
      );
      return `
        <button class="inspector-tool" data-kind="tool" data-selected="${payload}">
          <span class="tool-name">${label}</span>
          <span class="tool-meta" title="${route}">${route}</span>
        </button>
      `;
    }).join('');
    const routes = (group.http_routes || [])
      .map((r) => {
        const label = r.label ? ` · ${r.label}` : '';
        const methods = (r.methods || ['GET']).join(', ');
        return `<li><a href="#" data-kind="route" data-path="${r.path}" data-methods="${methods}"><code title="${methods} ${r.path}">${methods} ${r.path}</code>${label}</a></li>`;
      })
      .join('');
    const displayName = group.category === 'bili' ? 'Bilibili' : group.category === 'xhs' ? '小红书' : group.category;
    return `
      <section class="inspector-group">
        <header class="inspector-group__header">
          <h3>${displayName}</h3>
          <span>${(group.tools || []).length} tools</span>
        </header>
        <div class="inspector-group__tools">${tools}</div>
        ${routes ? `<div class="inspector-group__routes"><ul>${routes}</ul></div>` : ''}
      </section>
    `;
  };

  const renderPrompt = (p) => {
    const payload = encodeURIComponent(JSON.stringify({ name: p.name, description: p.description, path: p.http_path, methods: p.http_methods }, null, 0));
    return `
      <button class="inspector-tool" data-kind="prompt" data-selected="${payload}">
        <span class="tool-name">${p.name}</span>
        <span class="tool-meta">GET ${p.http_path}</span>
      </button>
    `;
  };

  const renderResource = (r) => {
    const payload = encodeURIComponent(JSON.stringify({ name: r.uri, description: r.description, path: r.http_path, methods: r.http_methods }, null, 0));
    return `
      <button class="inspector-tool" data-kind="resource" data-selected="${payload}">
        <span class="tool-name">${r.uri}</span>
        <span class="tool-meta">GET ${r.http_path}</span>
      </button>
    `;
  };

  // Tools
  if (MODE === 'tools') (groups || []).forEach((g) => html.push(renderGroup(g)));

  // Prompts
  if (MODE === 'prompts' && prompts && prompts.length) {
    html.push(`
      <section class="inspector-group">
        <header class="inspector-group__header">
          <h3>Prompts</h3>
          <span>${prompts.length}</span>
        </header>
        <div class="inspector-group__tools">${prompts.map(renderPrompt).join('')}</div>
      </section>
    `);
  }

  // Resources
  if (MODE === 'resources' && resources && resources.length) {
    html.push(`
      <section class="inspector-group">
        <header class="inspector-group__header">
          <h3>Resources</h3>
          <span>${resources.length}</span>
        </header>
        <div class="inspector-group__tools">${resources.map(renderResource).join('')}</div>
      </section>
    `);
  }

  el.innerHTML = html.join('');
}

function bindSidebarClicks() {
  const container = document.getElementById('tool-list');
  container.addEventListener('click', (e) => {
    const btn = e.target.closest('.inspector-tool');
    const routeLink = e.target.closest('a[data-kind="route"]');
    if (!btn && !routeLink) return;

    document.querySelectorAll('#tool-list .inspector-tool').forEach((el) => el.classList.remove('is-active'));
    if (btn) btn.classList.add('is-active');

    let data;
    if (routeLink) {
      // 从路由反查工具：在已渲染的按钮中找匹配 path 的项
      const path = routeLink.getAttribute('data-path');
      const toolBtn = container.querySelector(`.inspector-tool[data-selected*="\"path\":\"${path}\""]`);
      if (!toolBtn) return;
      data = JSON.parse(decodeURIComponent(toolBtn.getAttribute('data-selected')));
    } else {
      const raw = btn.getAttribute('data-selected');
      if (!raw) return;
      data = JSON.parse(decodeURIComponent(raw));
    }

    // 更新 UI
    currentTool = { name: data.name, path: data.path, methods: data.methods, sampleKey: data.sampleKey };
    const methods = data.methods && data.methods.length ? data.methods.join(', ') : 'POST';
    document.getElementById('tool-name').textContent = data.name;
    document.getElementById('tool-description').textContent = data.description || '—';
    document.getElementById('tool-path').textContent = data.path || '-';
    document.getElementById('tool-methods').textContent = methods;

    const sample = DEFAULT_PAYLOADS[data.sampleKey] || DEFAULT_PAYLOADS[data.name] || {};
    document.getElementById('tool-request-body').value = JSON.stringify(sample, null, 2);
    document.getElementById('execute-tool').disabled = !(data.path || data.name);
    document.getElementById('reset-body').disabled = false;
    document.getElementById('response-status').textContent = '选择完成，可以执行请求';
    // 不清空之前的响应结果，让用户可以对比不同工具的结果
    // document.getElementById('response-body').textContent = '{}';
    // document.getElementById('copy-response').style.display = 'none';
  });
  // Filter select
  const fk = document.getElementById('filter-kind');
  if (fk) {
    fk.addEventListener('change', () => {
      MODE = fk.value || 'tools';
      renderSidebar(window.__INSPECTOR_CACHE__ || { groups: [], prompts: [], resources: [] });
    });
  }
}

async function executeCurrentTool() {
  if (!currentTool) return;

  const path = currentTool.path || '';
  const bodyText = document.getElementById('tool-request-body').value || '{}';

  try {
    document.getElementById('response-status').textContent = '请求中...';
    document.getElementById('response-status').style.color = 'var(--text-warning, #f59e0b)';

    const method = (currentTool.methods && currentTool.methods[0]) || 'POST';
    const res = await fetch(`${API_BASE}/admin/inspector/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tool: currentTool.sampleKey || currentTool.name, // 使用 sampleKey 作为完整的工具名称 (如 bili_search)
        params: JSON.parse(bodyText || '{}'), // 传递参数
      }),
    });

    const responseText = await res.text();

    // 更新状态
    document.getElementById('response-status').textContent = `HTTP ${res.status} ${res.statusText}`;
    document.getElementById('response-status').style.color = res.ok
      ? 'var(--text-success, #22c55e)'
      : 'var(--text-error, #ef4444)';

    // 尝试格式化 JSON 响应
    try {
      const jsonData = JSON.parse(responseText);
      let displayData = jsonData;
      if (displayData && typeof displayData === 'object' && !Array.isArray(displayData)) {
        // 隐藏不必要的元字段
        if ('id' in displayData) delete displayData.id;
        if ('tool' in displayData) delete displayData.tool;
      }
      document.getElementById('response-body').textContent = JSON.stringify(displayData, null, 2);
    } catch {
      document.getElementById('response-body').textContent = responseText;
    }

    document.getElementById('copy-response').style.display = 'inline-block';
  } catch (err) {
    document.getElementById('response-status').textContent = '请求失败';
    document.getElementById('response-status').style.color = 'var(--text-error, #ef4444)';
    document.getElementById('response-body').textContent = String(err);
  }
}

function resetRequestBody() {
  if (!currentTool) return;
  // 使用 sampleKey 而不是 name 来匹配示例参数
  const sampleKey = currentTool.sampleKey || currentTool.name;
  const sample = DEFAULT_PAYLOADS[sampleKey] || DEFAULT_PAYLOADS[currentTool.name] || {};
  document.getElementById('tool-request-body').value = JSON.stringify(sample, null, 2);
}

function copyResponse() {
  const responseText = document.getElementById('response-body').textContent;
  navigator.clipboard.writeText(responseText).then(() => {
    const btn = document.getElementById('copy-response');
    const originalText = btn.textContent;
    btn.textContent = '已复制!';
    setTimeout(() => {
      btn.textContent = originalText;
    }, 2000);
  });
}

function getQueryParam(name) {
  const params = new URLSearchParams(location.search);
  return params.get(name) || '';
}

async function init() {
  try {
    // 通过 AJAX 获取 MCP 数据，与其他页面保持一致
    const data = await apiRequest('/mcp/data');
    console.log('MCP Client Data:', data);
    
    // 转换新格式为旧格式兼容
    const groups = [];
    
    // 处理 tools 数据，按平台分组
    if (data.tools && data.tools.tools && Array.isArray(data.tools.tools)) {
      const platformGroups = {};
      
      data.tools.tools.forEach(tool => {
        const platform = tool.platform || 'unknown';
        if (!platformGroups[platform]) {
          platformGroups[platform] = {
            category: platform === 'xhs' ? '小红书' : platform === 'bili' ? 'Bilibili' : platform,
            tools: []
          };
        }
        
        // 构造完整的工具名称作为 sampleKey
        const fullToolName = `${platform}_${tool.name}`;
        
        platformGroups[platform].tools.push({
          name: tool.name,
          description: tool.description,
          http_path: `/${platform}/${tool.name}`,
          http_methods: ['POST'],
          sampleKey: fullToolName // 使用完整的工具名称，如 bili_search
        });
        console.log(`Tool registered: ${tool.name}, sampleKey: ${fullToolName}`);
      });
      
      groups.push(...Object.values(platformGroups));
    }
    
    const prompts = [];
    if (data.prompts && data.prompts.prompts && Array.isArray(data.prompts.prompts)) {
      data.prompts.prompts.forEach(p => {
        prompts.push({
          name: p.name,
          description: p.description,
          http_path: `/prompts/${p.name}`,
          http_methods: ['GET']
        });
      });
    }
    
    const resources = [];
    if (data.resources && data.resources.resources && Array.isArray(data.resources.resources)) {
      data.resources.resources.forEach(r => {
        resources.push({
          uri: r.uri,
          description: r.description,
          http_path: `/resources/${r.uri.replace('://', '/')}`,
          http_methods: ['GET']
        });
      });
    }
    
    console.log('Processed data:', { groups, prompts, resources });
    
    window.__INSPECTOR_CACHE__ = { groups, prompts, resources };
    renderSidebar(window.__INSPECTOR_CACHE__);
    bindSidebarClicks();
  } catch (e) {
    console.error('Init error:', e);
    document.getElementById('tool-list').innerHTML = '<div>加载工具失败：' + e.message + '</div>';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  init();

  // 绑定按钮事件
  document.getElementById('execute-tool').addEventListener('click', executeCurrentTool);
  document.getElementById('reset-body').addEventListener('click', resetRequestBody);
  document.getElementById('copy-response').addEventListener('click', copyResponse);
});
