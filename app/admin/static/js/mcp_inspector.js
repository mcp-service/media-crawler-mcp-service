// MCP Tools Inspector

const apiBase = '/mcp';

const defaultPayloads = {
    bili_search: { keywords: "sample keyword", page_size: 1, page_num: 5 },
    bili_detail: { video_ids: ["BV1xx411c7mD"] },
    bili_creator: { creator_ids: ["123456"], creator_mode: true },
    bili_search_time_range: {
        keywords: "sample keyword",
        start_day: "2024-01-01",
        end_day: "2024-01-07",
        page_size: 1,
        page_num: 5
    },
    bili_comments: { video_ids: ["BV1xx411c7mD"], max_comments: 20, fetch_sub_comments: false }
};

const toolListElement = document.getElementById('tool-list');
const toolNameElement = document.getElementById('tool-name');
const toolDescriptionElement = document.getElementById('tool-description');
const toolPathElement = document.getElementById('tool-path');
const toolMethodsElement = document.getElementById('tool-methods');
const toolRequestBodyElement = document.getElementById('tool-request-body');
const executeButton = document.getElementById('execute-tool');
const resetButton = document.getElementById('reset-body');
const responseStatusElement = document.getElementById('response-status');
const responseBodyElement = document.getElementById('response-body');
const refreshButton = document.getElementById('refresh-tools');

let toolsCache = [];
let activeTool = null;
let defaultPayload = '{}';

function clearActiveState() {
    document.querySelectorAll('.inspector-tool.is-active').forEach((el) => el.classList.remove('is-active'));
}

function safeJsonParse(value) {
    if (!value || !value.trim()) {
        return {}
    }
    return JSON.parse(value);
}

function formatJSON(value) {
    return JSON.stringify(value, null, 2);
}

function renderToolList(items) {
    if (!items.length) {
        toolListElement.innerHTML = '<div class="status-placeholder">暂无可用工具</div>';
        return;
    }

    const fragments = items.map((group) => {
        const tools = (group.tools || []).map((tool) => {
            const path = tool.http_path || (group.prefix ? `${group.prefix}/${tool.name}` : '');
            const methods = tool.http_methods || [];
            const routeLabel = methods.length ? `${methods.join(', ')} ${path}` : path;
            return `
                <button class="inspector-tool" data-tool='${encodeURIComponent(JSON.stringify({
                    name: tool.name,
                    description: tool.description,
                    path,
                    methods,
                }))}'>
                    <span class="tool-name">${tool.name}</span>
                    <span class="tool-meta">${routeLabel || 'No HTTP route'}</span>
                </button>`;
        }).join('');

        const routes = (group.http_routes || []).map((route) => {
            const methods = route.methods ? route.methods.join(', ') : 'GET';
            return `<li><code>${methods} ${route.path}</code>${route.label ? ` · ${route.label}` : ''}</li>`;
        }).join('');

        return `
            <section class="inspector-group">
                <header class="inspector-group__header">
                    <h3>${group.category}</h3>
                    <span>${group.tools.length} tools</span>
                </header>
                <div class="inspector-group__tools">
                    ${tools}
                </div>
                ${routes ? `<div class="inspector-group__routes"><ul>${routes}</ul></div>` : ''}
            </section>
        `;
    });

    toolListElement.innerHTML = fragments.join('');
}

async function loadTools() {
    toolListElement.innerHTML = '<div class="status-placeholder">加载?..</div>';
    try {
        const response = await fetch(`${apiBase}/tools`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        toolsCache = data.items || [];
        renderToolList(toolsCache);
    } catch (error) {
        toolListElement.innerHTML = `<div class="status-placeholder">加载失败: ${error.message}</div>`;
    }
}

function selectTool(tool, triggerBtn) {
    activeTool = tool;
    toolNameElement.textContent = tool.name;
    toolDescriptionElement.textContent = tool.description || 'No description';
    toolPathElement.textContent = tool.path || '-';
    toolMethodsElement.textContent = tool.methods && tool.methods.length ? tool.methods.join(', ') : 'POST';
    const sample = defaultPayloads[tool.name] || {};
    defaultPayload = formatJSON(sample);
    toolRequestBodyElement.value = defaultPayload;
    responseStatusElement.textContent = '尚未执行';
    responseBodyElement.textContent = '{}';
    executeButton.disabled = !tool.path;
    resetButton.disabled = false;

    clearActiveState();
    if (triggerBtn) {
        triggerBtn.classList.add('is-active');
    }
}

async function executeTool() {
    if (!activeTool || !activeTool.path) {
        return;
    }

    const method = (activeTool.methods && activeTool.methods[0]) || 'POST';
    let payload;
    try {
        payload = safeJsonParse(toolRequestBodyElement.value || '{}');
    } catch (error) {
        responseStatusElement.textContent = 'JSON 解析失败';
        responseBodyElement.textContent = error.message;
        return;
    }

    responseStatusElement.textContent = '请求?..';
    responseBodyElement.textContent = '';

    try {
        const response = await fetch(activeTool.path, {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: ['GET', 'HEAD'].includes(method.toUpperCase()) ? undefined : JSON.stringify(payload),
        });

        const text = await response.text();
        let parsed;
        try {
            parsed = JSON.parse(text);
            responseBodyElement.textContent = formatJSON(parsed);
        } catch (_) {
            responseBodyElement.textContent = text || '<empty response>';
        }
        responseStatusElement.textContent = `${response.status} ${response.statusText}`;
    } catch (error) {
        responseStatusElement.textContent = '请求失败';
        responseBodyElement.textContent = error.message;
    }
}

function resetPayload() {
    toolRequestBodyElement.value = defaultPayload;
}

toolListElement.addEventListener('click', (event) => {
    const button = event.target.closest('.inspector-tool');
    if (!button) return;
    clearActiveState();
    button.classList.add('is-active');
    const encoded = button.getAttribute('data-tool');
    if (!encoded) return;
    const tool = JSON.parse(decodeURIComponent(encoded));
    selectTool(tool, button);
});

executeButton.addEventListener('click', executeTool);
resetButton.addEventListener('click', resetPayload);
refreshButton.addEventListener('click', loadTools);

loadTools();
