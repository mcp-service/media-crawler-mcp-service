// MCP Tools Inspector

const apiBase = '/mcp';

const defaultPayloads = {
    bili_search: { keywords: "纯圆大嬛嬛", page_size: 5, page_num: 1 },
    bili_detail: { video_ids: ["115285696846946"] },
    bili_creator: { creator_ids: ["99801185"], page_num: 1, page_size: 30 },
    bili_search_time_range: {
        keywords: "纯圆大嬛嬛",
        start_day: "2024-01-01",
        end_day: "2024-01-07",
        page_size: 5,
        page_num: 1
    },
    bili_comments: { video_ids: ["115285696846946"], max_comments: 20, fetch_sub_comments: false },
    xhs_search: { keywords: "纯圆大嬛嬛", page_num: 1, page_size: 20 },
    xhs_detail: { node_id: "68f9b8b20000000004010353", xsec_token: "AB_xsec_token_here", xsec_source: "", enable_comments: true, max_comments_per_note: 50 },
    xhs_creator: { creator_ids: ["user123"], enable_comments: false, max_comments_per_note: 0 },
    xhs_comments: { note_ids: ["68f9b8b20000000004010353"], max_comments: 50 }
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
const copyButton = document.getElementById('copy-response');

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
    // 过滤掉没有工具的组，并合并相同分类的组
    const filteredItems = items.filter(group => group.tools && group.tools.length > 0);
    
    if (!filteredItems.length) {
        toolListElement.innerHTML = '<div class="status-placeholder">暂无可用工具</div>';
        return;
    }

    // 按分类合并工具组
    const mergedGroups = {};
    filteredItems.forEach(group => {
        const category = group.category;
        if (!mergedGroups[category]) {
            mergedGroups[category] = {
                category: category,
                tools: [],
                http_routes: [],
                prefix: group.prefix
            };
        }
        mergedGroups[category].tools.push(...(group.tools || []));
        mergedGroups[category].http_routes.push(...(group.http_routes || []));
    });

    const fragments = Object.values(mergedGroups).map((group) => {
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

        // 显示更友好的分类名称
        const categoryDisplayName = group.category === 'bili' ? 'Bilibili' : 
                                   group.category === 'xhs' ? '小红书' :
                                   group.category === 'dy' ? '抖音' :
                                   group.category === 'admin' ? '管理工具' : 
                                   group.category;

        return `
            <section class="inspector-group">
                <header class="inspector-group__header">
                    <h3>${categoryDisplayName}</h3>
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
    copyButton.style.display = 'none'; // 隐藏复制按钮直到有响应内容

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

    responseStatusElement.textContent = '请求中...';
    responseBodyElement.textContent = '';
    copyButton.style.display = 'none'; // 请求开始时隐藏复制按钮

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
        
        // 请求成功后显示复制按钮
        copyButton.style.display = 'inline-block';
    } catch (error) {
        responseStatusElement.textContent = '请求失败';
        responseBodyElement.textContent = error.message;
        
        // 请求失败时也显示复制按钮，方便复制错误信息
        copyButton.style.display = 'inline-block';
    }
}

function resetPayload() {
    toolRequestBodyElement.value = defaultPayload;
}

async function copyResponse() {
    const content = responseBodyElement.textContent;
    if (!content || content === '{}') {
        return;
    }
    
    try {
        await navigator.clipboard.writeText(content);
        
        // 临时显示复制成功提示
        const originalText = copyButton.textContent;
        copyButton.textContent = '已复制';
        copyButton.disabled = true;
        
        setTimeout(() => {
            copyButton.textContent = originalText;
            copyButton.disabled = false;
        }, 1500);
    } catch (error) {
        // 如果 clipboard API 不可用，使用传统方法
        try {
            const textArea = document.createElement('textarea');
            textArea.value = content;
            textArea.style.position = 'fixed';
            textArea.style.opacity = '0';
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            
            // 显示复制成功提示
            const originalText = copyButton.textContent;
            copyButton.textContent = '已复制';
            copyButton.disabled = true;
            
            setTimeout(() => {
                copyButton.textContent = originalText;
                copyButton.disabled = false;
            }, 1500);
        } catch (fallbackError) {
            console.error('复制失败:', fallbackError);
            alert('复制失败，请手动选择文本进行复制');
        }
    }
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
copyButton.addEventListener('click', copyResponse);

loadTools();
