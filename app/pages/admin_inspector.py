# -*- coding: utf-8 -*-
from starlette.responses import HTMLResponse

from .ui_base import (
    build_page_with_nav,
    create_page_header,
    create_info_box,
    create_button_group,
)


def render_admin_inspector() -> HTMLResponse:
    # 页面头部
    header = create_page_header(
        title="MCP Tools Inspector",
        breadcrumb="首页 / 工具调试台",
    )

    info_message = create_info_box("浏览并调试已注册的 MCP 工具，直接向对应 HTTP 接口提交请求，实时查看返回数据")

    # 左侧工具列表
    tools_list = f"""
    <div class="mc-status-card">
        <h3>可用工具</h3>
        <div id='tool-list'>{create_info_box("加载工具列表...")}</div>
    </div>
    """

    # 右侧调试面板
    debug_panel = f"""
    <div class="mc-status-card">
        <div style='border-bottom: 1px solid var(--border-color, #e2e8f0); padding-bottom: 1rem; margin-bottom: 1.5rem;'>
            <h3 id='tool-name'>请选择工具</h3>
            <p id='tool-description' style='color: var(--text-muted, #6b7280); margin: 0.5rem 0;'>从左侧列表中选择一个工具进行调试。</p>
            <div style='display: flex; gap: 1rem; margin-top: 0.75rem;'>
                <div><span style='font-weight: 500;'>HTTP 路由：</span> <code id='tool-path'>-</code></div>
                <div><span style='font-weight: 500;'>请求方法：</span> <code id='tool-methods'>-</code></div>
            </div>
        </div>

        <div class='mc-form-group'>
            <label>请求体（JSON）</label>
            <textarea id='tool-request-body' rows='12' placeholder='工具参数将显示在这里...'></textarea>
            <small>修改参数后点击"执行请求"进行测试</small>
        </div>

        <div class='mc-form-group'>
            {create_button_group([
                ("执行请求", "#", "primary"),
                ("恢复默认", "#", "secondary"),
                ("复制响应", "#", "secondary")
            ]).replace("执行请求", "执行请求' id='execute-tool' disabled").replace("恢复默认", "恢复默认' id='reset-body' disabled").replace("复制响应", "复制响应' id='copy-response' style='display:none;")}
        </div>

        <div>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;'>
                <span style='font-weight: 500;'>响应结果</span>
                <span id='response-status' style='color: var(--text-muted, #6b7280);'>尚未执行</span>
            </div>
            <pre id='response-body' style='min-height: 200px; background: var(--code-bg, #f8fafc);'>{{}}</pre>
        </div>
    </div>
    """

    inspector_js = """
    <script>
    const API_BASE = '/api';
    let currentTool = null;

    async function apiRequest(endpoint, options = {}){
        const res=await fetch(`${API_BASE}${endpoint}`,{
            headers:{'Content-Type':'application/json'},
            ...options
        });
        if(!res.ok) throw new Error(`HTTP ${res.status}`);
        const ct=res.headers.get('content-type')||'';
        return ct.includes('application/json')?res.json():res.text();
    }

    function renderToolList(items){
        const el=document.getElementById('tool-list');
        if(!items?.length){
            el.innerHTML='<div>暂无工具</div>';
            return;
        }

        el.innerHTML=items.map(g=>`
            <div style='margin-bottom: 1.5rem;'>
                <h4 style='margin: 0 0 0.5rem; font-size: 0.875rem; font-weight: 600; color: var(--text-primary);'>${g.category||g.name}</h4>
                <div style='margin-left: 0.5rem;'>
                    ${g.tools.map(t=>`
                        <div style='margin: 0.25rem 0;'>
                            <a href='#' data-tool='${g.name}:${t.name}'
                               style='color: var(--link-color, #3b82f6); text-decoration: none; font-size: 0.875rem;'
                               onmouseover="this.style.textDecoration='underline'"
                               onmouseout="this.style.textDecoration='none'">
                                ${t.name}
                            </a>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
    }

    function bindToolClicks(groups){
        document.querySelectorAll('#tool-list a[data-tool]').forEach(a=>{
            a.addEventListener('click',(e)=>{
                e.preventDefault();
                const[srv,tool]=a.dataset.tool.split(':');
                const g=groups.find(x=>x.name===srv);
                const t=g?.tools.find(x=>x.name===tool);

                // 更新当前工具信息
                currentTool = {service: srv, tool: tool, config: t};
                const path=`/${srv}/${tool}`;
                const methods='POST';

                // 更新 UI
                document.getElementById('tool-name').textContent=`${srv} · ${tool}`;
                document.getElementById('tool-description').textContent=t?.description||'暂无描述';
                document.getElementById('tool-path').textContent=path;
                document.getElementById('tool-methods').textContent=methods;
                document.getElementById('tool-request-body').value=JSON.stringify(t?.example||{},null,2);
                document.getElementById('execute-tool').disabled=false;
                document.getElementById('reset-body').disabled=false;

                // 清空之前的响应
                document.getElementById('response-status').textContent='选择工具完成，可以执行请求';
                document.getElementById('response-body').textContent='{}';
                document.getElementById('copy-response').style.display='none';

                // 高亮选中的工具
                document.querySelectorAll('#tool-list a').forEach(link => {
                    link.style.backgroundColor = '';
                    link.style.padding = '';
                    link.style.borderRadius = '';
                });
                a.style.backgroundColor = 'var(--accent-color-alpha, rgba(59, 130, 246, 0.1))';
                a.style.padding = '0.25rem 0.5rem';
                a.style.borderRadius = '0.25rem';
            });
        });
    }

    async function executeCurrentTool(){
        if(!currentTool) return;

        const path = `/${currentTool.service}/${currentTool.tool}`;
        const bodyText = document.getElementById('tool-request-body').value || '{}';

        try{
            document.getElementById('response-status').textContent='请求中...';
            document.getElementById('response-status').style.color='var(--text-warning, #f59e0b)';

            const res = await fetch(path, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: bodyText
            });

            const responseText = await res.text();

            // 更新状态
            document.getElementById('response-status').textContent=`HTTP ${res.status} ${res.statusText}`;
            document.getElementById('response-status').style.color = res.ok ?
                'var(--text-success, #22c55e)' : 'var(--text-error, #ef4444)';

            // 尝试格式化 JSON 响应
            try{
                const jsonData = JSON.parse(responseText);
                document.getElementById('response-body').textContent = JSON.stringify(jsonData, null, 2);
            }catch{
                document.getElementById('response-body').textContent = responseText;
            }

            document.getElementById('copy-response').style.display='inline-block';

        }catch(err){
            document.getElementById('response-status').textContent='请求失败';
            document.getElementById('response-status').style.color='var(--text-error, #ef4444)';
            document.getElementById('response-body').textContent=String(err);
        }
    }

    function resetRequestBody(){
        if(currentTool && currentTool.config){
            document.getElementById('tool-request-body').value =
                JSON.stringify(currentTool.config.example||{}, null, 2);
        }
    }

    function copyResponse(){
        const responseText = document.getElementById('response-body').textContent;
        navigator.clipboard.writeText(responseText).then(()=>{
            const btn = document.getElementById('copy-response');
            const originalText = btn.textContent;
            btn.textContent = '已复制!';
            setTimeout(()=>{
                btn.textContent = originalText;
            }, 2000);
        });
    }

    async function init(){
        try{
            const r = await apiRequest('/admin/tools');
            const items = r.items || [];
            renderToolList(items);
            bindToolClicks(items);
        }catch(e){
            document.getElementById('tool-list').innerHTML = '<div>加载工具失败：' + e.message + '</div>';
        }
    }

    document.addEventListener('DOMContentLoaded', ()=>{
        init();

        // 绑定按钮事件
        document.getElementById('execute-tool').addEventListener('click', executeCurrentTool);
        document.getElementById('reset-body').addEventListener('click', resetRequestBody);
        document.getElementById('copy-response').addEventListener('click', copyResponse);
    });
    </script>
    """

    # 组合主内容
    main_content = f"""
        {header}
        {info_message}
        <div class="mc-dashboard-grid">
            {tools_list}
            {debug_panel}
        </div>
        {inspector_js}
    """

    return build_page_with_nav(
        main_content=main_content,
        title="工具调试台 · MediaCrawler MCP",
        current_path="/inspector"
    )
