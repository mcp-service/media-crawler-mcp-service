# -*- coding: utf-8 -*-
from starlette.responses import HTMLResponse

from .ui_base import (
    build_page_with_nav,
    create_page_header,
    create_detail_box,
    create_button_group,
)


def render_admin_dashboard() -> HTMLResponse:
    # 页面头部
    header = create_page_header(
        title="实时状态监控中心",
        breadcrumb="首页 / 状态监控",
        actions=create_button_group([
            ("立即刷新", "#", "primary"),
        ]).replace("href='#'", "onclick='refreshAllData()' style='cursor:pointer'")
    )

    # 系统指标卡片
    metrics_card = f"""
    <div class="mc-status-card">
        <h3>系统资源监控</h3>
        <div id="system-metrics">
            {create_detail_box([
                ("CPU 使用率", "加载中..."),
                ("内存使用率", "加载中..."),
                ("磁盘使用率", "加载中..."),
                ("累计数据文件", "加载中..."),
            ])}
        </div>
    </div>
    """

    # 服务状态卡片
    services_card = f"""
    <div class="mc-status-card">
        <h3>核心服务状态</h3>
        <div id="services-status">
            {create_detail_box([
                ("MCP 服务", "检查中..."),
                ("数据库", "检查中..."),
                ("Redis", "检查中..."),
            ])}
        </div>
    </div>
    """

    # 平台状态卡片
    platforms_card = """
    <div class="mc-status-card">
        <h3>平台会话面板</h3>
        <div id='platforms-status' style='min-height: 100px;'>
            <div style='color: #718096; text-align: center; padding: 2rem 0;'>正在加载平台状态...</div>
        </div>
    </div>
    """

    # 数据状态卡片
    data_card = """
    <div class="mc-status-card">
        <h3>数据持久化概览</h3>
        <div id='data-path-container'>
            <div class="detail-box">
                <div class="detail-row">
                    <div class="detail-label">数据目录:</div>
                    <div class="detail-value">加载中...</div>
                </div>
            </div>
        </div>
        <div id='platform-data-stats' style='margin-top: 1rem;'></div>
    </div>
    """

    # JavaScript 代码
    dashboard_js = """
    <script>
    const API_BASE = '/api';

    function showMessage(m) {
        console.log('INFO:', m);
    }

    function showSuccess(m) {
        console.log('SUCCESS:', m);
    }

    async function apiRequest(endpoint, options = {}) {
        try {
            const res = await fetch(`${API_BASE}${endpoint}`, {
                headers: {'Content-Type': 'application/json'},
                ...options
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            const ct = res.headers.get('content-type') || '';
            return ct.includes('application/json') ? res.json() : res.text();
        } catch (error) {
            console.error('API Request failed:', endpoint, error);
            throw error;
        }
    }

    async function loadSystemStatus() {
        try {
            const response = await apiRequest('/status/system');
            const container = document.getElementById('system-metrics');
            container.innerHTML = `
                <div class="detail-box">
                    <div class="detail-row">
                        <div class="detail-label">CPU 使用率:</div>
                        <div class="detail-value">${response.cpu_percent || 0}%</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">内存使用率:</div>
                        <div class="detail-value">${response.memory_percent || 0}%</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">磁盘使用率:</div>
                        <div class="detail-value">${response.disk_usage_percent || 0}%</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">累计数据文件:</div>
                        <div class="detail-value">${response.total_files || 0}</div>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('加载系统状态失败:', error);
        }
    }

    async function loadServicesStatus() {
        try {
            const response = await apiRequest('/status/services');
            const container = document.getElementById('services-status');

            const getStatusBadge = (service) => {
                if (!service) return '<span class="status-badge status-error">未知</span>';
                if (service.status === 'running') {
                    return '<span class="status-badge status-success">运行中</span>';
                } else if (service.status === 'down') {
                    return '<span class="status-badge status-error">异常</span>';
                }
                return '<span class="status-badge status-warning">未知</span>';
            };

            container.innerHTML = `
                <div class="detail-box">
                    <div class="detail-row">
                        <div class="detail-label">MCP 服务:</div>
                        <div class="detail-value">${getStatusBadge(response.mcp_service)}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">数据库:</div>
                        <div class="detail-value">${getStatusBadge(response.database)}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Redis:</div>
                        <div class="detail-value">${getStatusBadge(response.redis)}</div>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('加载服务状态失败:', error);
        }
    }

    async function loadPlatformsStatus() {
        try {
            const platforms = await apiRequest('/status/platforms');
            const container = document.getElementById('platforms-status');

            if (!platforms || !platforms.length) {
                container.innerHTML = '<div style="color: #718096; text-align: center; padding: 1rem;">暂无平台状态信息</div>';
                return;
            }

            container.innerHTML = platforms.map(p => {
                const statusClass = p.is_logged_in ? 'status-success' : 'status-error';
                const statusText = p.is_logged_in ? '在线' : '离线';
                return `
                    <div class="mc-status-item">
                        <div>
                            <strong>${p.name}</strong>
                            <div style="font-size: 0.875rem; color: #718096; margin-top: 0.25rem;">
                                ${p.enabled ? '✓ 已启用' : '✗ 停用'} ·
                                ${p.tools_available ? '工具可用' : '工具受限'}
                            </div>
                        </div>
                        <span class="status-badge ${statusClass}">${statusText}</span>
                    </div>
                `;
            }).join('');
        } catch (error) {
            console.error('加载平台状态失败:', error);
            document.getElementById('platforms-status').innerHTML =
                '<div style="color: #dc2626; padding: 1rem;">加载失败，请检查服务状态</div>';
        }
    }

    async function loadDataStatus() {
        try {
            const response = await apiRequest('/status/data');

            // 更新数据路径 detail-box
            const pathContainer = document.querySelector('#data-path-container');
            if (pathContainer) {
                pathContainer.innerHTML = `
                    <div class="detail-box">
                        <div class="detail-row">
                            <div class="detail-label">数据目录:</div>
                            <div class="detail-value">${response.data_path || '--'}</div>
                        </div>
                    </div>
                `;
            }

            const container = document.getElementById('platform-data-stats');
            if (response.platforms && Object.keys(response.platforms).length > 0) {
                container.innerHTML = Object.entries(response.platforms).map(([platform, stats]) => `
                    <div class="mc-status-item">
                        <div>
                            <strong>${platform}</strong>
                            <div style="font-size: 0.875rem; color: #718096; margin-top: 0.25rem;">
                                ${stats.files_count} 个文件 · 容量 ${stats.total_size_mb} MB
                            </div>
                        </div>
                        <div style="font-size: 0.75rem; color: #9ca3af;">
                            最新: ${stats.latest_file || '未知'}
                        </div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<div style="color: #718096; text-align: center; padding: 1rem;">暂无爬取数据</div>';
            }
        } catch (error) {
            console.error('加载数据状态失败:', error);
        }
    }

    async function refreshAllData() {
        showMessage('正在刷新数据...');
        await Promise.all([
            loadSystemStatus(),
            loadServicesStatus(),
            loadPlatformsStatus(),
            loadDataStatus()
        ]);
        showSuccess('数据已刷新');
    }

    // 页面加载完成后执行
    document.addEventListener('DOMContentLoaded', () => {
        refreshAllData();
        // 每30秒自动刷新
        setInterval(refreshAllData, 30000);
    });
    </script>
    """

    # 组合主内容
    main_content = f"""
        {header}
        <div class="mc-dashboard-grid">
            {metrics_card}
            {services_card}
            {platforms_card}
            {data_card}
        </div>
        {dashboard_js}
    """

    return build_page_with_nav(
        main_content=main_content,
        title="状态监控 · MediaCrawler MCP",
        current_path="/dashboard"
    )
