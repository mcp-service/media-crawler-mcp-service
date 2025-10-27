# -*- coding: utf-8 -*-
from starlette.responses import HTMLResponse

from .ui_base import (
    build_page,
    create_logo,
    create_info_box,
    create_detail_box,
    create_button_group,
    render_nav,
)


def render_admin_dashboard() -> HTMLResponse:
    header = (
        create_logo(None, "MediaCrawler MCP")
        + "<h1>实时状态监控中心</h1>"
        + create_info_box("聚合后台服务、浏览器会话与数据落盘状况，30 秒自动刷新")
    )

    nav = render_nav()

    # 系统指标卡片
    metrics_card = f"""
    <div class="mc-status-card">
        <h3>系统资源监控</h3>
        {create_detail_box([
            ("CPU 使用率", "<span id='cpu-percent'>--%</span>"),
            ("内存使用率", "<span id='memory-percent'>--%</span>"),
            ("磁盘使用率", "<span id='disk-percent'>--%</span>"),
            ("累计数据文件", "<span id='total-files'>--</span>"),
        ])}
    </div>
    """

    # 服务状态卡片
    services_card = f"""
    <div class="mc-status-card">
        <h3>核心服务状态</h3>
        {create_detail_box([
            ("MCP 服务", "<span id='mcp-service-status'>检查中...</span>"),
            ("数据库", "<span id='database-status'>检查中...</span>"),
            ("Redis", "<span id='redis-status'>检查中...</span>"),
        ])}
    </div>
    """

    # 平台状态卡片
    platforms_card = f"""
    <div class="mc-status-card">
        <h3>平台会话面板</h3>
        <div id='platforms-status'>{create_info_box("正在加载平台状态...")}</div>
    </div>
    """

    # 数据状态卡片
    data_card = f"""
    <div class="mc-status-card">
        <h3>数据持久化概览</h3>
        {create_detail_box([("数据目录", "<span id='data-path'>--</span>")])}
        <div id='platform-data-stats'></div>
    </div>
    """

    # 操作按钮组
    refresh_buttons = create_button_group([
        ("立即刷新", "#", "primary"),
    ]).replace("href='#'", "id='refresh-btn' type='button' onclick='refreshAllData()'")

    dashboard_js = """
    const API_BASE = '/api';
    function showMessage(m){console.log(m)}
    function showSuccess(m){console.log(m)}
    async function apiRequest(endpoint, options = {}){
      const res = await fetch(`${API_BASE}${endpoint}`, {headers:{'Content-Type':'application/json'},...options});
      if(!res.ok) throw new Error(`HTTP ${res.status}`);
      const ct = res.headers.get('content-type')||'';
      return ct.includes('application/json')?res.json():res.text();
    }
    function updateServiceStatus(id,s){const el=document.getElementById(id);if(!el||!s)return;el.textContent=(s.status==='running'?'运行中':(s.status==='down'?'异常':'未知'))}
    async function loadSystemStatus(){try{const r=await apiRequest('/status/system');document.getElementById('cpu-percent').textContent=`${r.cpu_percent||0}%`;document.getElementById('memory-percent').textContent=`${r.memory_percent||0}%`;document.getElementById('disk-percent').textContent=`${r.disk_usage_percent||0}%`}catch(e){console.error('系统状态失败',e)}}
    async function loadServicesStatus(){try{const r=await apiRequest('/status/services');updateServiceStatus('mcp-service-status',r.mcp_service);updateServiceStatus('database-status',r.database);updateServiceStatus('redis-status',r.redis)}catch(e){console.error('服务状态失败',e)}}
    async function loadPlatformsStatus(){try{const list=await apiRequest('/status/platforms');const c=document.getElementById('platforms-status');if(!list.length){c.innerHTML='<div>暂无平台状态</div>';return;}c.innerHTML=list.map(p=>`<div class="mc-status-item"><strong>${p.name}</strong> · ${p.enabled?'已启用':'停用'} · ${p.tools_available?'工具可用':'工具受限'} · ${p.is_logged_in?'在线':'离线'}</div>`).join('')}catch(e){console.error('平台状态失败',e)}}
    async function loadDataStatus(){try{const r=await apiRequest('/status/data');document.getElementById('data-path').textContent=r.data_path||'--';document.getElementById('total-files').textContent=r.total_files||0;const c=document.getElementById('platform-data-stats');if(r.platforms&&Object.keys(r.platforms).length){c.innerHTML=Object.entries(r.platforms).map(([k,s])=>`<div class="mc-status-item"><strong>${k}</strong> · ${s.files_count} 个文件 · 容量 ${s.total_size_mb} MB · 最新 ${s.latest_file||'未知'}</div>`).join('')}else{c.innerHTML='<div>暂无爬取数据</div>'}}catch(e){console.error('数据状态失败',e)}}
    async function refreshAllData(){showMessage('正在刷新数据...');await Promise.all([loadSystemStatus(),loadServicesStatus(),loadPlatformsStatus(),loadDataStatus()]);showSuccess('数据已刷新')}
    document.addEventListener('DOMContentLoaded',()=>{refreshAllData();setInterval(refreshAllData,30000)});
    """

    parts = [
        "<div class='mc-container'>",
        header,
        nav,
        f"<div style='margin: 1rem 0;'>{refresh_buttons}</div>",
        "<div class='mc-dashboard-grid'>",
        metrics_card,
        services_card,
        platforms_card,
        data_card,
        "</div>",
        "<script>" + dashboard_js + "</script>",
        "</div>",
    ]

    return build_page("".join(parts), title="MediaCrawler MCP Service · Dashboard")