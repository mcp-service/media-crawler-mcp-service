# -*- coding: utf-8 -*-
from starlette.responses import HTMLResponse

from .ui_base import (
    build_page_with_nav,
    create_page_header,
    create_info_box,
    create_button,
    create_button_row,
)


def render_admin_login() -> HTMLResponse:
    # 页面头部
    header = create_page_header(
        title="多平台登录中心",
        breadcrumb="首页 / 登录管理",
    )

    info_message = create_info_box(
        "支持二维码、Cookie、手机号等方式触发登录，并通过同一面板查看状态。"
        "智能优化：选择二维码登录时，系统会优先尝试使用缓存的 Cookie 自动登录；"
        "若 Cookie 失效，则自动降级为二维码登录。"
    )

    # 使用新的辅助函数生成按钮
    login_buttons = create_button_row(
        create_button("开始登录", btn_type="submit", btn_id="login-submit-btn", btn_class="btn btn-primary"),
        create_button("刷新状态", btn_id="refresh-login-status", btn_class="btn btn-secondary"),
        create_button("刷新二维码", btn_id="refresh-qr-btn", btn_class="btn btn-secondary", style="display:none;"),
    )

    # 登录表单卡片
    login_form_card = f"""
    <div class="mc-status-card">
        <h3>启动新的登录流程</h3>
        <form id='login-form' class='mc-form'>
            <div class='mc-form-group'>
                <label>选择平台</label>
                <select name='platform' id='platform' required>
                    <option value=''>请选择平台</option>
                </select>
                <small id='platform-tip'>正在加载可用平台...</small>
            </div>

            <div class='mc-form-group'>
                <label>登录方式</label>
                <select name='login_type' id='login_type'>
                    <option value='qrcode'>二维码扫码登录</option>
                    <option value='cookie'>Cookie 登录</option>
                    <option value='phone'>手机号登录</option>
                </select>
            </div>

            <div class='mc-form-group' id='phone-field' style='display:none;'>
                <label>手机号</label>
                <input type='tel' name='phone' id='phone' placeholder='请输入用于登录的手机号'>
            </div>

            <div class='mc-form-group' id='cookie-field' style='display:none;'>
                <label>Cookie</label>
                <textarea name='cookie' id='cookie' rows='4' placeholder='粘贴浏览器 Cookie'></textarea>
            </div>

            <div class='mc-form-group'>
                {login_buttons}
            </div>
        </form>
    </div>
    """

    # 登录状态显示卡片
    status_card = f"""
    <div class="mc-status-card">
        <h3>登录进度</h3>
        <div id='login-status'>{create_info_box("选择平台并点击 '开始登录'，进度将实时呈现")}</div>
        <div id='qr-code-container' style='display:none;'>
            <div id='qr-countdown' style='margin-bottom: 1rem; font-weight: 500;'></div>
            <div id='qr-image-wrapper' style='text-align: center;'></div>
        </div>
    </div>
    """

    # 平台会话状态卡片
    sessions_card = f"""
    <div class="mc-status-card">
        <h3>平台登录状态</h3>
        <div id='platform-sessions'>{create_info_box("正在加载平台状态...")}</div>
    </div>
    """

    login_js = """
    <script>
    const API_BASE = '/api';
    const optimisticLoggedPlatforms = new Set();
    let availablePlatformCodes = [];
    let loginSessionsCache = [];

    // 平台代码到中文名称的映射
    const PLATFORM_NAMES = {
        'bili': 'B站 (Bilibili)',
        'xhs': '小红书',
        'dy': '抖音',
        'ks': '快手',
        'wb': '微博',
        'tieba': '贴吧',
        'zhihu': '知乎'
    };

    function getPlatformName(code) {
        return PLATFORM_NAMES[code] || code;
    }

    function toggleLoginFields(){
        const t=document.getElementById('login_type').value;
        document.getElementById('phone-field').style.display=(t==='phone')?'block':'none';
        document.getElementById('cookie-field').style.display=(t==='cookie')?'block':'none';
    }

    async function apiRequest(endpoint, options = {}){
        try {
            const res = await fetch(`${API_BASE}${endpoint}`, {
                headers: {'Content-Type': 'application/json'},
                ...options
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const ct = res.headers.get('content-type') || '';
            return ct.includes('application/json') ? res.json() : res.text();
        } catch (error) {
            console.error('API Request failed:', endpoint, error);
            throw error;
        }
    }

    function populatePlatformSelectOptions(codes){
        const select = document.getElementById('platform');
        const options = ["<option value=''>请选择平台</option>"];
        codes.forEach(code => options.push(`<option value='${code}'>${getPlatformName(code)}</option>`));
        select.innerHTML = options.join('');
        const tip = document.getElementById('platform-tip');
        tip.textContent = codes.length ? '请选择需要登录的平台' : '当前没有可登录的平台';
    }

    async function loadPlatforms(){
        try {
            const platforms = await apiRequest('/login/platforms');
            availablePlatformCodes = Array.isArray(platforms) ? platforms : [];
            populatePlatformSelectOptions(availablePlatformCodes);
        } catch (e) {
            console.error('加载平台列表失败:', e);
            document.getElementById('platform-tip').textContent = '平台列表加载失败';
        }
    }

    function renderPlatformSessions(sessions){
        const c = document.getElementById('platform-sessions');
        if (!sessions || !sessions.length) {
            c.innerHTML = '<div style="color: #718096; text-align: center; padding: 1rem;">暂无登录会话</div>';
            return;
        }
        c.innerHTML = sessions.map(s => {
            const logoutBtn = s.is_logged_in
                ? `<span class="status-badge" style="background: #fee2e2; color: #991b1b; cursor: pointer;" onclick="logoutPlatform('${s.platform}')" title="点击退出登录">登出</span>`
                : '';
            return `
                <div class="mc-status-item">
                    <strong>${getPlatformName(s.platform_name || s.platform)}</strong>
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <span class="status-badge ${s.is_logged_in ? 'status-success' : 'status-error'}">${s.is_logged_in ? '在线' : '离线'}</span>
                        ${logoutBtn}
                    </div>
                </div>
            `;
        }).join('');
    }

    async function refreshLoginStatus(){
        try {
            const r = await apiRequest('/login/sessions');
            let s = Array.isArray(r) ? r : [];
            s = s.map(x => {
                if (optimisticLoggedPlatforms.has(x.platform) && !x.is_logged_in) {
                    return {...x, is_logged_in: true, last_login: x.last_login || new Date().toLocaleString()};
                }
                if (x.is_logged_in) optimisticLoggedPlatforms.delete(x.platform);
                return x;
            });
            loginSessionsCache = s;
            renderPlatformSessions(s);
        } catch (e) {
            console.error('刷新登录状态失败:', e);
        }
    }

    async function logoutPlatform(platform) {
        if (!confirm(`确定要退出 ${getPlatformName(platform)} 平台吗？`)) {
            return;
        }

        try {
            await apiRequest(`/login/logout/${platform}`, {
                method: 'POST'
            });

            alert('退出登录成功！');
            optimisticLoggedPlatforms.delete(platform);
            await refreshLoginStatus();
        } catch (e) {
            alert('退出登录失败: ' + e.message);
        }
    }

    class LoginManager {
        constructor() {
            this.currentSession = null;
            this.currentSessionPlatform = null;
            this.qrCountdownInterval = null;
            this.statusPollInterval = null;
            this.qrExpirySeconds = 180;
        }

        async startLogin(platform, loginType, phone = '', cookie = '') {
            if (!platform) {
                alert('请选择需要登录的平台');
                return;
            }

            // 停止之前的轮询
            this.stopPolling();

            try {
                const resp = await apiRequest('/login/start', {
                    method: 'POST',
                    body: JSON.stringify({platform, login_type: loginType, phone, cookie})
                });

                this.currentSession = resp.session_id;
                this.currentSessionPlatform = platform;

                // 立即检查一次状态
                await this.checkStatus();

                // 开始轮询状态（每2秒检查一次）
                this.startPolling();

            } catch (e) {
                alert('启动登录失败: ' + e.message);
                this.stopPolling();
            }
        }

        startPolling() {
            // 清除旧的轮询
            this.stopPolling();

            // 每2秒检查一次状态
            this.statusPollInterval = setInterval(async () => {
                await this.checkStatus();
            }, 2000);
        }

        stopPolling() {
            if (this.statusPollInterval) {
                clearInterval(this.statusPollInterval);
                this.statusPollInterval = null;
            }
            if (this.qrCountdownInterval) {
                clearInterval(this.qrCountdownInterval);
                this.qrCountdownInterval = null;
            }
        }

        async checkStatus() {
            if (!this.currentSession) return;

            try {
                const r = await apiRequest(`/login/session/${this.currentSession}`);
                this.renderStatus(r);

                // 如果有二维码，显示二维码
                if (r.qr_code_base64) {
                    this.displayQRCode(r);
                }

                // 检查是否完成（成功或失败）
                if (r.status === 'success') {
                    this.stopPolling();
                    // 隐藏二维码容器
                    const qrContainer = document.getElementById('qr-code-container');
                    if (qrContainer) qrContainer.style.display = 'none';
                    // 隐藏刷新二维码按钮
                    const refreshQrBtn = document.getElementById('refresh-qr-btn');
                    if (refreshQrBtn) refreshQrBtn.style.display = 'none';
                    // 标记平台为已登录
                    optimisticLoggedPlatforms.add(this.currentSessionPlatform);
                    this.currentSession = null;
                    this.currentSessionPlatform = null;
                    // 刷新登录状态列表
                    await refreshLoginStatus();
                } else if (r.status === 'failed' || r.status === 'expired') {
                    this.stopPolling();
                }

            } catch (e) {
                console.error('检查登录状态失败:', e);
            }
        }

        renderStatus(r) {
            const el = document.getElementById('login-status');
            el.innerHTML = r.message ? `<div class="mc-status-item">${r.message}</div>` : '<div>检查中...</div>';
        }

        displayQRCode(resp) {
            const c = document.getElementById('qr-code-container');
            c.style.display = 'block';
            document.getElementById('qr-image-wrapper').innerHTML = `
                <img src='data:image/png;base64,${resp.qr_code_base64}'
                     alt='登录二维码'
                     style='max-width:300px; border:1px solid var(--border-color, #e2e8f0);
                            padding:12px; border-radius:12px; background: white;'>
            `;
            this.startQrCountdown(resp.qrcode_timestamp);
            const refreshBtn = document.getElementById('refresh-qr-btn');
            if (refreshBtn) refreshBtn.style.display = 'inline-block';
        }

        startQrCountdown(ts) {
            const countdown = document.getElementById('qr-countdown');
            const t = ts ? Number(ts) * 1000 : Date.now();
            const expire = t + this.qrExpirySeconds * 1000;
            if (this.qrCountdownInterval) clearInterval(this.qrCountdownInterval);

            const tick = () => {
                const r = Math.floor((expire - Date.now()) / 1000);
                countdown.textContent = r <= 0 ? '二维码已过期，请点击刷新二维码重新获取' : `二维码将在 ${r} 秒后过期`;
            };
            tick();
            this.qrCountdownInterval = setInterval(tick, 1000);
        }
    }

    const loginManager = new LoginManager();

    document.addEventListener('DOMContentLoaded', () => {
        toggleLoginFields();
        loadPlatforms().then(() => refreshLoginStatus());

        document.getElementById('login_type').addEventListener('change', toggleLoginFields);

        const refreshStatusBtn = document.getElementById('refresh-login-status');
        if (refreshStatusBtn) {
            refreshStatusBtn.addEventListener('click', (e) => {
                e.preventDefault();
                refreshLoginStatus();
            });
        }

        const form = document.getElementById('login-form');
        form.addEventListener('submit', async (ev) => {
            ev.preventDefault();
            const fd = new FormData(form);
            await loginManager.startLogin(
                fd.get('platform'),
                fd.get('login_type'),
                fd.get('phone') || '',
                fd.get('cookie') || ''
            );
        });

        const refreshQrBtn = document.getElementById('refresh-qr-btn');
        if (refreshQrBtn) {
            refreshQrBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const platform = document.getElementById('platform').value;
                const loginType = document.getElementById('login_type').value;
                const phone = document.getElementById('phone')?.value || '';
                const cookie = document.getElementById('cookie')?.value || '';
                loginManager.startLogin(platform, loginType, phone, cookie);
            });
        }
    });
    </script>
    """

    # 组合主内容
    main_content = f"""
        {header}
        {info_message}
        <div class="mc-dashboard-grid">
            {login_form_card}
            {status_card}
        </div>
        {sessions_card}
        {login_js}
    """

    return build_page_with_nav(
        main_content=main_content,
        title="登录管理 · MediaCrawler MCP",
        current_path="/login"
    )
