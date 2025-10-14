// Admin Interface JavaScript

// 全局配置
const API_BASE = '/admin/api';
const PLATFORM_LABELS = {
    bili: '哔哩哔哩',
    xhs: '小红书',
    dy: '抖音',
    ks: '快手',
    wb: '微博',
    tieba: '贴吧',
    zhihu: '知乎'
};

let platformNames = {};
let availablePlatformCodes = [];
let loginSessionsCache = [];

// 工具函数
function showMessage(message, type = 'info') {
    const messageDiv = document.getElementById('message');
    if (!messageDiv) {
        return;
    }
    messageDiv.className = `status status-${type}`;
    messageDiv.textContent = message;
    messageDiv.style.display = 'block';

    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 3000);
}

function showError(message) {
    showMessage(message, 'error');
}

function showSuccess(message) {
    showMessage(message, 'success');
}

function showWarning(message) {
    showMessage(message, 'warning');
}

// HTTP 请求封装
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };

    try {
        const response = await fetch(url, { ...defaultOptions, ...options });

        if (!response.ok) {
            let detailMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorBody = await response.json();
                if (errorBody && errorBody.detail) {
                    detailMessage = typeof errorBody.detail === 'string'
                        ? errorBody.detail
                        : JSON.stringify(errorBody.detail);
                }
            } catch (parseError) {
                // ignore parse error, fall back to default message
            }
            throw new Error(detailMessage);
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        }
        return await response.text();
    } catch (error) {
        console.error('API 请求失败:', error);
        throw error;
    }
}

function getPlatformDisplayName(code) {
    if (!code) {
        return '';
    }
    return platformNames[code] || PLATFORM_LABELS[code] || code;
}

function populatePlatformSelectOptions(codes = []) {
    const select = document.getElementById('platform');
    if (!select) {
        return;
    }

    const currentValue = select.value;
    const options = ['<option value=\"\">请选择平台</option>'];
    codes.forEach((code) => {
        options.push(`<option value="${code}">${getPlatformDisplayName(code)}</option>`);
    });

    select.innerHTML = options.join('');
    if (currentValue && codes.includes(currentValue)) {
        select.value = currentValue;
    }

    const tip = document.getElementById('platform-tip');
    if (tip) {
        tip.textContent = codes.length
            ? '请选择需要登录的平台'
            : '当前没有可登录的平台';
    }
}

async function loadPlatforms() {
    try {
        const platforms = await apiRequest('/login/platforms');
        availablePlatformCodes = Array.isArray(platforms) ? platforms : [];
        populatePlatformSelectOptions(availablePlatformCodes);
    } catch (error) {
        console.error('加载平台列表失败:', error);
        const tip = document.getElementById('platform-tip');
        if (tip) {
            tip.textContent = '平台列表加载失败，请稍后重试';
        }
    }
}

class LoginManager {
    constructor() {
        this.currentSession = null;
        this.currentSessionPlatform = null;
        this.pollInterval = null;
        this.pollTimeout = null;
        this.pollStartTime = null;
        this.maxPollTime = 5 * 60 * 1000; // 5分钟超时
        this.qrCodeDisplayed = false;
        this.qrCountdownInterval = null;
        this.qrExpirySeconds = 180;
        this.autoRefreshTimer = null;
    }

    async startLogin(platform, loginType, phone = '', cookie = '') {
        if (!platform) {
            showWarning('请先选择需要登录的平台');
            return;
        }

        this.stopPolling();
        this.resetQRCode();
        this.setLoading(true);
        this.currentSession = null;
        this.currentSessionPlatform = null;

        try {
            if (loginType === 'qrcode') {
                this.toggleRefreshQrButton(true);
            } else {
                this.toggleRefreshQrButton(false);
            }

            showMessage('正在启动登录流程...', 'info');
            const response = await apiRequest('/login/start', {
                method: 'POST',
                body: JSON.stringify({
                    platform,
                    login_type: loginType,
                    phone,
                    cookie
                })
            });

            this.currentSession = response.session_id;
            this.currentSessionPlatform = platform;

            if (loginType === 'qrcode') {
                this.startPolling();
                this.displayQRCode(response);
                this.toggleRefreshQrButton(true);
            } else {
                await this.checkStatus();
            }
        } catch (error) {
            showError(`启动登录失败: ${error.message}`);
            this.toggleRefreshQrButton(false);
        } finally {
            this.setLoading(false);
        }
    }

    setLoading(isLoading) {
        const submitBtn = document.getElementById('login-submit-btn');
        if (!submitBtn) {
            return;
        }
        submitBtn.dataset.loading = isLoading ? 'true' : 'false';
        if (!submitBtn.dataset.defaultLabel) {
            submitBtn.dataset.defaultLabel = submitBtn.textContent || '开始登录';
        }

        if (isLoading) {
            submitBtn.disabled = true;
            submitBtn.textContent = '处理中...';
            submitBtn.classList.remove('btn-primary');
            submitBtn.classList.add('btn-secondary');
        } else {
            submitBtn.disabled = false;
            submitBtn.textContent = submitBtn.dataset.defaultLabel;
            submitBtn.classList.remove('btn-secondary');
            submitBtn.classList.add('btn-primary');
        }
    }

    toggleRefreshQrButton(visible) {
        const refreshBtn = document.getElementById('refresh-qr-btn');
        if (!refreshBtn) {
            return;
        }
        if (visible) {
            refreshBtn.classList.remove('d-none');
        } else {
            refreshBtn.classList.add('d-none');
        }
    }

    resetQRCode() {
        this.clearQrCountdown();
        const qrContainer = document.getElementById('qr-code-container');
        const qrWrapper = document.getElementById('qr-image-wrapper');
        const countdown = document.getElementById('qr-countdown');

        if (qrWrapper) {
            qrWrapper.innerHTML = '';
        }
        if (countdown) {
            countdown.textContent = '';
        }
        if (qrContainer) {
            qrContainer.classList.add('d-none');
        }
        this.qrCodeDisplayed = false;
    }

    displayQRCode(response) {
        if (!response.qr_code_base64) {
            return;
        }

        const qrContainer = document.getElementById('qr-code-container');
        if (!qrContainer) {
            return;
        }

        let wrapper = document.getElementById('qr-image-wrapper');
        if (!wrapper) {
            wrapper = document.createElement('div');
            wrapper.id = 'qr-image-wrapper';
            qrContainer.appendChild(wrapper);
        }

        wrapper.innerHTML = `
            <div class="text-center mb-3">
                <h4>请扫描二维码登录</h4>
            </div>
            <div class="text-center">
                <img src="data:image/png;base64,${response.qr_code_base64}"
                     class="qr-code-img" alt="登录二维码"
                     style="max-width: 300px; border: 2px solid #ddd; padding: 10px; border-radius: 8px;">
            </div>
            <div class="text-center mt-3">
                <p class="status status-info">请使用 ${getPlatformDisplayName(response.platform)} 客户端扫描上方二维码</p>
            </div>
        `;

        qrContainer.classList.remove('d-none');
        this.qrCodeDisplayed = true;
        this.startQrCountdown(response.qrcode_timestamp);
    }

    startQrCountdown(qrTimestamp) {
        const countdown = document.getElementById('qr-countdown');
        if (!countdown) {
            return;
        }

        const timestampMs = qrTimestamp ? Number(qrTimestamp) * 1000 : Date.now();
        const expireMs = timestampMs + this.qrExpirySeconds * 1000;

        this.clearQrCountdown();
        const updateCountdown = () => {
            const remaining = Math.floor((expireMs - Date.now()) / 1000);
            if (remaining <= 0) {
                countdown.textContent = '二维码已过期，请点击刷新二维码重新获取';
                this.clearQrCountdown();
                this.toggleRefreshQrButton(true);
                return;
            }
            countdown.textContent = `二维码将在 ${remaining} 秒后过期`;
        };

        updateCountdown();
        this.qrCountdownInterval = setInterval(updateCountdown, 1000);
    }

    clearQrCountdown() {
        if (this.qrCountdownInterval) {
            clearInterval(this.qrCountdownInterval);
            this.qrCountdownInterval = null;
        }
    }

    startPolling() {
        this.stopPolling();
        this.pollStartTime = Date.now();

        this.pollInterval = setInterval(() => {
            if (this.pollStartTime && Date.now() - this.pollStartTime > this.maxPollTime) {
                showWarning('登录超时（5分钟），请重新尝试');
                this.stopPolling();
                this.toggleRefreshQrButton(true);
                return;
            }
            this.checkStatus();
        }, 2000);

        this.pollTimeout = setTimeout(() => {
            showWarning('登录超时（5分钟），请重新尝试');
            this.stopPolling();
            this.toggleRefreshQrButton(true);
        }, this.maxPollTime);
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        if (this.pollTimeout) {
            clearTimeout(this.pollTimeout);
            this.pollTimeout = null;
        }
        this.pollStartTime = null;
    }

    async checkStatus() {
        if (!this.currentSession) {
            return;
        }

        try {
            const response = await apiRequest(`/login/session/${this.currentSession}`);
            this.renderStatus(response);

            if (!this.qrCodeDisplayed && response.qr_code_base64) {
                this.displayQRCode(response);
            }

            if (response.status === 'success') {
                showSuccess('登录成功！');
                this.stopPolling();
                this.resetQRCode();
                this.toggleRefreshQrButton(false);
                this.currentSession = null;
                this.currentSessionPlatform = null;
                await refreshLoginStatus(false);
            } else if (response.status === 'failed') {
                showError(response.message || '登录失败，请重试');
                this.stopPolling();
                this.clearQrCountdown();
                this.toggleRefreshQrButton(true);
            } else if (response.status === 'expired') {
                showWarning(response.message || '二维码已过期，请重新获取');
                this.stopPolling();
                this.clearQrCountdown();
                this.toggleRefreshQrButton(true);
            } else if (response.status === 'waiting' || response.status === 'processing') {
                if (response.qrcode_timestamp) {
                    this.startQrCountdown(response.qrcode_timestamp);
                }
            }
        } catch (error) {
            console.error('检查登录状态失败:', error);
        }
    }

    renderStatus(response) {
        const statusElement = document.getElementById('login-status');
        if (!statusElement) {
            return;
        }

        statusElement.textContent = response.message || '检查中...';
        statusElement.classList.remove('status-info', 'status-success', 'status-error', 'status-warning');

        let statusClass = 'status-info';
        if (response.status === 'success') {
            statusClass = 'status-success';
        } else if (response.status === 'failed') {
            statusClass = 'status-error';
        } else if (response.status === 'expired') {
            statusClass = 'status-warning';
        }
        statusElement.classList.add(statusClass);
    }
}

async function refreshLoginStatus(silent = false) {
    if (!silent) {
        showMessage('正在刷新登录状态...', 'info');
    }

    try {
        const response = await apiRequest('/login/sessions');
        const sessions = Array.isArray(response) ? response : [];
        loginSessionsCache = sessions;

        sessions.forEach((session) => {
            if (session.platform && session.platform_name) {
                platformNames[session.platform] = session.platform_name;
            }
        });

        const platformCodes = sessions.map((session) => session.platform).filter(Boolean);
        if (!availablePlatformCodes.length && platformCodes.length) {
            availablePlatformCodes = platformCodes;
        }
        populatePlatformSelectOptions(availablePlatformCodes.length ? availablePlatformCodes : platformCodes);

        const container = document.getElementById('platform-sessions');
        if (container) {
            if (!sessions.length) {
                container.innerHTML = '<div class="text-center"><p style="color: #6c757d;">暂无登录会话</p></div>';
            } else {
                container.innerHTML = sessions.map((session) => `
                    <div class="platform-item ${session.is_logged_in ? 'enabled' : 'disabled'}">
                        <h4>${getPlatformDisplayName(session.platform)}</h4>
                        <div class="status ${session.is_logged_in ? 'status-success' : 'status-info'}" style="margin-top: 0.5rem;">
                            ${session.is_logged_in ? '已登录' : '未登录'}
                        </div>
                        <div style="margin-top: 0.5rem; font-size: 0.875rem; color: #6c757d;">
                            ${session.last_login || (session.is_logged_in ? '最近登录' : '从未登录')}
                        </div>
                        <button class="btn btn-sm ${session.is_logged_in ? 'btn-danger' : 'btn-primary'}"
                                onclick="${session.is_logged_in ? `logoutPlatform('${session.platform}')` : `quickLogin('${session.platform}')`}"
                                style="margin-top: 0.5rem; width: 100%;">
                            ${session.is_logged_in ? '退出登录' : '开始登录'}
                        </button>
                    </div>
                `).join('');
            }
        }

        updateLoginButtonState(sessions);
        if (!silent) {
            showSuccess('登录状态已刷新');
        }
    } catch (error) {
        if (!silent) {
            showError('刷新失败: ' + error.message);
        } else {
            console.error('刷新失败:', error);
        }
    }
}

function updateLoginButtonState(sessions) {
    const platformSelect = document.getElementById('platform');
    const submitBtn = document.getElementById('login-submit-btn');

    if (!platformSelect || !submitBtn) {
        return;
    }

    if (!submitBtn.dataset.defaultLabel) {
        submitBtn.dataset.defaultLabel = submitBtn.textContent || '开始登录';
    }

    if (submitBtn.dataset.loading === 'true') {
        return;
    }

    const selectedPlatform = platformSelect.value;
    if (!selectedPlatform) {
        submitBtn.disabled = true;
        submitBtn.textContent = submitBtn.dataset.defaultLabel;
        submitBtn.classList.remove('btn-secondary');
        submitBtn.classList.add('btn-primary');
        return;
    }

    const platformSession = sessions.find((session) => session.platform === selectedPlatform);
    if (platformSession && platformSession.is_logged_in) {
        submitBtn.disabled = true;
        submitBtn.textContent = '已登录';
        submitBtn.classList.remove('btn-primary');
        submitBtn.classList.add('btn-secondary');
    } else {
        submitBtn.disabled = false;
        submitBtn.textContent = submitBtn.dataset.defaultLabel;
        submitBtn.classList.remove('btn-secondary');
        submitBtn.classList.add('btn-primary');
    }
}

async function logoutPlatform(platform) {
    if (!platform) {
        return;
    }
    const displayName = getPlatformDisplayName(platform);
    if (!confirm(`确定要退出 ${displayName} 的登录吗？`)) {
        return;
    }

    try {
        showMessage('正在退出登录...', 'info');
        await apiRequest(`/login/logout/${platform}`, { method: 'POST' });
        showSuccess('退出登录成功');
        loginManager.resetQRCode();
        await refreshLoginStatus(false);
    } catch (error) {
        showError('退出登录失败: ' + error.message);
    }
}

function quickLogin(platform) {
    const platformSelect = document.getElementById('platform');
    if (platformSelect) {
        platformSelect.value = platform;
        platformSelect.dispatchEvent(new Event('change'));
    }
    const loginTypeSelect = document.getElementById('login_type');
    if (loginTypeSelect) {
        loginTypeSelect.value = 'qrcode';
    }
    toggleLoginFields();
    const form = document.getElementById('login-form');
    if (form) {
        form.scrollIntoView({ behavior: 'smooth' });
    }
}

function toggleLoginFields() {
    const loginTypeSelect = document.getElementById('login_type');
    const loginType = loginTypeSelect ? loginTypeSelect.value : 'qrcode';
    const phoneField = document.getElementById('phone-field');
    const cookieField = document.getElementById('cookie-field');

    if (phoneField) {
        phoneField.classList.toggle('d-none', loginType !== 'phone');
    }
    if (cookieField) {
        cookieField.classList.toggle('d-none', loginType !== 'cookie');
    }

    if (loginType !== 'qrcode') {
        loginManager.toggleRefreshQrButton(false);
    } else if (loginManager.qrCodeDisplayed) {
        loginManager.toggleRefreshQrButton(true);
    }
}

// 配置管理
class ConfigManager {
    async loadConfig() {
        try {
            const config = await apiRequest('/config/current');
            this.displayConfig(config);
        } catch (error) {
            showError(`加载配置失败: ${error.message}`);
        }
    }

    displayConfig(config) {
        const configContainer = document.getElementById('config-display');
        if (configContainer) {
            configContainer.innerHTML = `<pre>${JSON.stringify(config, null, 2)}</pre>`;
        }
    }

    async saveConfig(configData) {
        try {
            showMessage('正在保存配置...', 'info');
            await apiRequest('/config/update', {
                method: 'POST',
                body: JSON.stringify(configData)
            });
            showSuccess('配置保存成功');
        } catch (error) {
            showError(`保存配置失败: ${error.message}`);
        }
    }
}

// 状态监控
class StatusMonitor {
    constructor() {
        this.monitorInterval = null;
    }

    startMonitoring() {
        this.updateStatus();
        this.monitorInterval = setInterval(() => {
            this.updateStatus();
        }, 5000);
    }

    stopMonitoring() {
        if (this.monitorInterval) {
            clearInterval(this.monitorInterval);
            this.monitorInterval = null;
        }
    }

    async updateStatus() {
        try {
            const status = await apiRequest('/status/summary');
            this.displayStatus(status);
        } catch (error) {
            console.error('获取状态失败:', error);
        }
    }

    displayStatus(status) {
        const statusContainer = document.getElementById('status-display');
        if (statusContainer) {
            statusContainer.innerHTML = this.formatStatus(status);
        }
    }

    formatStatus(status) {
        return `
            <div class="row">
                <div class="col">
                    <h5>服务状态</h5>
                    <p class="status ${status.service_healthy ? 'status-success' : 'status-error'}">
                        ${status.service_healthy ? '运行正常' : '服务异常'}
                    </p>
                </div>
                <div class="col">
                    <h5>活跃连接</h5>
                    <p>${status.active_connections || 0}</p>
                </div>
            </div>
        `;
    }
}

// 全局实例
const loginManager = new LoginManager();
const configManager = new ConfigManager();
const statusMonitor = new StatusMonitor();

// 页面初始化
function initLoginPage() {
    const loginForm = document.getElementById('login-form');
    const platformSelect = document.getElementById('platform');
    const loginTypeSelect = document.getElementById('login_type');
    const submitBtn = document.getElementById('login-submit-btn');
    const refreshQrBtn = document.getElementById('refresh-qr-btn');

    if (submitBtn && !submitBtn.dataset.defaultLabel) {
        submitBtn.dataset.defaultLabel = submitBtn.textContent || '开始登录';
    }

    toggleLoginFields();

    loadPlatforms().then(() => {
        refreshLoginStatus(false);
    });

    if (loginForm) {
        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const formData = new FormData(loginForm);
            const platform = formData.get('platform');
            const loginType = formData.get('login_type');
            const phone = formData.get('phone') || '';
            const cookie = formData.get('cookie') || '';

            await loginManager.startLogin(platform, loginType, phone, cookie);
        });
    }

    if (platformSelect) {
        platformSelect.addEventListener('change', () => {
            updateLoginButtonState(loginSessionsCache);
        });
    }

    if (loginTypeSelect) {
        loginTypeSelect.addEventListener('change', toggleLoginFields);
    }

    if (refreshQrBtn) {
        refreshQrBtn.addEventListener('click', () => {
            const currentPlatform = document.getElementById('platform')?.value;
            if (!currentPlatform) {
                showWarning('请选择需要登录的平台');
                return;
            }
            const loginType = document.getElementById('login_type')?.value || 'qrcode';
            const phone = document.getElementById('phone')?.value || '';
            const cookie = document.getElementById('cookie')?.value || '';
            loginManager.startLogin(currentPlatform, loginType, phone, cookie);
        });
    }

    if (!loginManager.autoRefreshTimer) {
        loginManager.autoRefreshTimer = setInterval(() => {
            refreshLoginStatus(true);
        }, 30000);
    }
}

function initConfigPage() {
    configManager.loadConfig();

    const configForm = document.getElementById('config-form');
    if (configForm) {
        configForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const formData = new FormData(configForm);
            const configData = Object.fromEntries(formData);
            await configManager.saveConfig(configData);
        });
    }
}

function initStatusPage() {
    statusMonitor.startMonitoring();
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('login-form')) {
        initLoginPage();
    }

    if (document.getElementById('config-form')) {
        initConfigPage();
    }

    if (document.getElementById('status-display')) {
        initStatusPage();
    }
});

window.addEventListener('beforeunload', () => {
    loginManager.stopPolling();
    loginManager.clearQrCountdown();
    if (loginManager.autoRefreshTimer) {
        clearInterval(loginManager.autoRefreshTimer);
        loginManager.autoRefreshTimer = null;
    }
    statusMonitor.stopMonitoring();
});

// 暴露给模板使用的全局函数
window.logoutPlatform = logoutPlatform;
window.quickLogin = quickLogin;
window.toggleLoginFields = toggleLoginFields;
window.refreshLoginStatus = refreshLoginStatus;
