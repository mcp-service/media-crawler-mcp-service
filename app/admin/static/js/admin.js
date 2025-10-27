// Enhanced Admin Interface JavaScript with Modern Features

// 全局配置
const API_BASE = '/api';
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
const optimisticLoggedPlatforms = new Set();
let statusClearTimer = null;

// Enhanced Admin UI Class
class AdminUI {
    constructor() {
        this.init();
    }

    init() {
        this.setupPageTransitions();
        this.setupLoadingStates();
        this.setupNotifications();
        this.setupRealTimeUpdates();
        this.setupMobileNavigation();
        this.initializeTooltips();
    }

    // 页面过渡效果
    setupPageTransitions() {
        document.addEventListener('DOMContentLoaded', () => {
            document.body.classList.add('page-transition');
        });

        // 拦截导航链接添加过渡效果
        document.querySelectorAll('a[href^="/admin"], a[href^="/dashboard"], a[href^="/login"], a[href^="/config"], a[href^="/inspector"]').forEach(link => {
            link.addEventListener('click', (e) => {
                if (e.ctrlKey || e.metaKey || e.target.target === '_blank') return;
                
                e.preventDefault();
                this.navigateWithTransition(link.href);
            });
        });
    }

    navigateWithTransition(url) {
        document.body.classList.add('page-exit');
        
        setTimeout(() => {
            window.location.href = url;
        }, 200);
    }

    // 统一的加载状态管理
    showLoading(element = document.body, message = '加载中...') {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div style="text-align: center;">
                <div class="loading-spinner"></div>
                <div style="margin-top: 1rem; color: var(--admin-text-secondary); font-size: 0.9rem;">${message}</div>
            </div>
        `;
        
        if (element === document.body) {
            element.appendChild(overlay);
        } else {
            element.style.position = 'relative';
            element.appendChild(overlay);
        }
        
        return overlay;
    }

    hideLoading(overlay) {
        if (overlay && overlay.parentNode) {
            overlay.parentNode.removeChild(overlay);
        }
    }

    // 现代化通知系统
    showNotification(message, type = 'info', duration = 4000) {
        const notification = document.createElement('div');
        notification.className = `notification notification--${type}`;
        
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ⓘ'
        };
        
        notification.innerHTML = `
            <span style="margin-right: 0.5rem; font-weight: bold;">${icons[type] || 'ⓘ'}</span>
            ${message}
        `;
        
        document.body.appendChild(notification);
        
        // 触发显示动画
        requestAnimationFrame(() => {
            notification.classList.add('notification--show');
        });
        
        // 自动隐藏
        setTimeout(() => {
            notification.classList.remove('notification--show');
            setTimeout(() => {
                if (notification.parentNode) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, duration);

        // 点击隐藏
        notification.addEventListener('click', () => {
            notification.classList.remove('notification--show');
            setTimeout(() => {
                if (notification.parentNode) {
                    document.body.removeChild(notification);
                }
            }, 300);
        });
    }

    // 移动端导航
    setupMobileNavigation() {
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'mobile-menu-toggle';
        toggleBtn.innerHTML = '☰';
        toggleBtn.setAttribute('aria-label', '切换菜单');
        
        const pageHeader = document.querySelector('.page-header');
        const sidebar = document.querySelector('.admin-sidebar');
        
        if (pageHeader && sidebar) {
            pageHeader.insertBefore(toggleBtn, pageHeader.firstChild);
            
            toggleBtn.addEventListener('click', () => {
                sidebar.classList.toggle('is-open');
            });
            
            // 点击外部关闭
            document.addEventListener('click', (e) => {
                if (window.innerWidth <= 1024 && 
                    !sidebar.contains(e.target) && 
                    !toggleBtn.contains(e.target)) {
                    sidebar.classList.remove('is-open');
                }
            });
        }
    }

    // 实时数据更新
    setupRealTimeUpdates() {
        this.updateIntervals = new Map();
        
        // 为带有 data-auto-update 属性的元素设置自动更新
        document.querySelectorAll('[data-auto-update]').forEach(element => {
            const interval = parseInt(element.dataset.autoUpdate) || 30000;
            const endpoint = element.dataset.endpoint;
            
            if (endpoint) {
                this.startAutoUpdate(element, endpoint, interval);
            }
        });
    }

    startAutoUpdate(element, endpoint, interval) {
        const updateFunction = async () => {
            try {
                const response = await fetch(endpoint);
                const data = await response.json();
                
                if (element.dataset.updateType === 'text') {
                    element.textContent = data.value || data;
                } else if (element.dataset.updateType === 'html') {
                    element.innerHTML = data.html || data;
                }
                
                // 添加更新动画
                element.classList.add('data-updated');
                setTimeout(() => {
                    element.classList.remove('data-updated');
                }, 1000);
                
            } catch (error) {
                console.warn('自动更新失败:', error);
            }
        };
        
        const intervalId = setInterval(updateFunction, interval);
        this.updateIntervals.set(element, intervalId);
    }

    // 工具提示
    initializeTooltips() {
        document.querySelectorAll('[data-tooltip]').forEach(element => {
            element.addEventListener('mouseenter', (e) => {
                this.showTooltip(e.target, e.target.dataset.tooltip);
            });
            
            element.addEventListener('mouseleave', () => {
                this.hideTooltip();
            });
        });
    }

    showTooltip(element, text) {
        if (this.tooltipElement) {
            this.hideTooltip();
        }
        
        this.tooltipElement = document.createElement('div');
        this.tooltipElement.className = 'tooltip';
        this.tooltipElement.textContent = text;
        
        document.body.appendChild(this.tooltipElement);
        
        const rect = element.getBoundingClientRect();
        this.tooltipElement.style.position = 'fixed';
        this.tooltipElement.style.top = `${rect.bottom + 8}px`;
        this.tooltipElement.style.left = `${rect.left + rect.width / 2}px`;
        this.tooltipElement.style.transform = 'translateX(-50%)';
        this.tooltipElement.style.zIndex = '3000';
        this.tooltipElement.style.background = 'var(--admin-text-primary)';
        this.tooltipElement.style.color = 'white';
        this.tooltipElement.style.padding = '0.5rem 0.75rem';
        this.tooltipElement.style.borderRadius = '6px';
        this.tooltipElement.style.fontSize = '0.8rem';
        this.tooltipElement.style.whiteSpace = 'nowrap';
        this.tooltipElement.style.opacity = '0';
        this.tooltipElement.style.transition = 'opacity 0.2s ease';
        
        requestAnimationFrame(() => {
            this.tooltipElement.style.opacity = '1';
        });
    }

    hideTooltip() {
        if (this.tooltipElement) {
            this.tooltipElement.style.opacity = '0';
            setTimeout(() => {
                if (this.tooltipElement && this.tooltipElement.parentNode) {
                    document.body.removeChild(this.tooltipElement);
                }
                this.tooltipElement = null;
            }, 200);
        }
    }

    // 清理资源
    destroy() {
        this.updateIntervals.forEach(intervalId => {
            clearInterval(intervalId);
        });
        this.updateIntervals.clear();
        
        if (this.tooltipElement) {
            this.hideTooltip();
        }
    }
}

// 向后兼容的消息函数
function showMessage(message, type = 'info') {
    if (window.adminUI) {
        window.adminUI.showNotification(message, type);
        return;
    }
    
    // 回退到原有逻辑
    const statusEl = document.getElementById('page-status');
    if (!statusEl) {
        if (type === 'error') {
            console.error(message);
        } else {
            console.log(message);
        }
        return;
    }

    if (statusClearTimer) {
        clearTimeout(statusClearTimer);
        statusClearTimer = null;
    }

    statusEl.textContent = message;
    statusEl.title = message;
    statusEl.className = `page-status status status-${type} is-visible`;

    statusClearTimer = window.setTimeout(() => {
        statusEl.textContent = '';
        statusEl.title = '';
        statusEl.className = 'page-status';
        statusClearTimer = null;
    }, 3200);
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

// 加载状态的兼容函数
function showLoading(element, message) {
    if (window.adminUI) {
        return window.adminUI.showLoading(element, message);
    }
    return null;
}

function hideLoading(overlay) {
    if (window.adminUI) {
        window.adminUI.hideLoading(overlay);
    }
}

// 初始化增强UI
document.addEventListener('DOMContentLoaded', () => {
    window.adminUI = new AdminUI();
});

// 页面卸载时清理资源
window.addEventListener('beforeunload', () => {
    if (window.adminUI) {
        window.adminUI.destroy();
    }
});

// API 请求函数

    statusClearTimer = window.setTimeout(() => {
        statusEl.textContent = '';
        statusEl.title = '';
        statusEl.className = 'page-status';
        statusClearTimer = null;
    }, 3200);
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

function renderPlatformSessions(sessions = []) {
    const container = document.getElementById('platform-sessions');
    if (!container) {
        return;
    }

    if (!sessions.length) {
        container.innerHTML = '<div class="platform-empty">暂无登录会话</div>';
        return;
    }

    const groups = [
        {
            title: '已登录',
            filter: (session) => session.is_logged_in,
            statusLabel: '在线',
            actionLabel: '退出',
            actionClass: 'platform-action platform-action--danger',
            actionHandler: (platform) => `logoutPlatform('${platform}')`
        },
        {
            title: '未登录',
            filter: (session) => !session.is_logged_in,
            statusLabel: '离线',
            actionLabel: '登录',
            actionClass: 'platform-action platform-action--highlight',
            actionHandler: (platform) => `quickLogin('${platform}')`
        }
    ];

    container.innerHTML = groups.map((group) => {
        const groupSessions = sessions.filter(group.filter);
        const groupContent = groupSessions.length
            ? groupSessions.map((session) => {
                const displayName = session.platform_name || getPlatformDisplayName(session.platform) || session.platform;

                return `
                    <div class="platform-chip ${session.is_logged_in ? 'is-active' : ''}">
                        <div class="platform-chip__details">
                            <span class="platform-chip__name">${displayName}</span>
                        </div>
                        <div class="platform-chip__actions">
                            <span class="platform-chip__status">${group.statusLabel}</span>
                            <button class="${group.actionClass}" onclick="${group.actionHandler(session.platform)}">
                                ${group.actionLabel}
                            </button>
                        </div>
                    </div>
                `;
            }).join('')
            : '<div class="platform-group__empty">暂无平台</div>';

        return `
            <section class="platform-group">
                <header class="platform-group__header">
                    <span class="platform-group__title">${group.title}</span>
                    <span class="platform-group__count">${groupSessions.length}</span>
                </header>
                <div class="platform-group__list">
                    ${groupContent}
                </div>
            </section>
        `;
    }).join('');
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

    setSubmitButtonLoggedInState(platform) {
        if (!platform) {
            return;
        }
        const platformSelect = document.getElementById('platform');
        const submitBtn = document.getElementById('login-submit-btn');
        if (!submitBtn) {
            return;
        }
        if (!submitBtn.dataset.defaultLabel) {
            submitBtn.dataset.defaultLabel = submitBtn.textContent || '开始登录';
        }
        if (platformSelect && platformSelect.value && platformSelect.value !== platform) {
            return;
        }
        submitBtn.disabled = true;
        submitBtn.textContent = '已登录';
        submitBtn.classList.remove('btn-primary');
        submitBtn.classList.add('btn-secondary');
    }

    markPlatformSessionLoggedIn(platform) {
        if (!platform) {
            return;
        }
        const displayName = getPlatformDisplayName(platform) || PLATFORM_LABELS[platform] || platform;
        platformNames[platform] = displayName;
        optimisticLoggedPlatforms.add(platform);

        let hasExisting = false;
        loginSessionsCache = loginSessionsCache.map((session) => {
            if (session.platform === platform) {
                hasExisting = true;
                return {
                    ...session,
                    platform,
                    platform_name: displayName,
                    is_logged_in: true,
                    last_login: session.last_login || new Date().toLocaleString()
                };
            }
            return session;
        });

        if (!hasExisting) {
            loginSessionsCache.push({
                platform,
                platform_name: displayName,
                is_logged_in: true,
                last_login: new Date().toLocaleString()
            });
        }

        renderPlatformSessions(loginSessionsCache);
        updateLoginButtonState(loginSessionsCache);
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
                const platform = this.currentSessionPlatform;
                showSuccess('登录成功！');
                this.stopPolling();
                this.resetQRCode();
                this.toggleRefreshQrButton(false);
                this.setSubmitButtonLoggedInState(platform);
                this.markPlatformSessionLoggedIn(platform);
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
        let sessions = Array.isArray(response) ? response : [];

        sessions.forEach((session) => {
            if (session.platform && session.platform_name) {
                platformNames[session.platform] = session.platform_name;
            }
        });

        sessions = sessions.map((session) => {
            if (!session.platform) {
                return session;
            }
            if (optimisticLoggedPlatforms.has(session.platform) && !session.is_logged_in) {
                return {
                    ...session,
                    is_logged_in: true,
                    last_login: session.last_login || new Date().toLocaleString()
                };
            }
            if (session.is_logged_in) {
                optimisticLoggedPlatforms.delete(session.platform);
            }
            return session;
        });

        loginSessionsCache = sessions;

        const platformCodes = sessions.map((session) => session.platform).filter(Boolean);
        if (!availablePlatformCodes.length && platformCodes.length) {
            availablePlatformCodes = platformCodes;
        }
        populatePlatformSelectOptions(availablePlatformCodes.length ? availablePlatformCodes : platformCodes);

        renderPlatformSessions(loginSessionsCache);

        updateLoginButtonState(loginSessionsCache);
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
        optimisticLoggedPlatforms.delete(platform);
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
        const serviceStatus = status.service_healthy ? '运行正常' : '服务异常';
        const serviceClass = status.service_healthy ? 'status-success' : 'status-error';
        const activeConnections = status.active_connections || 0;
        const pendingTasks = status.pending_tasks ?? '—';

        return `
            <div class="status-strip">
                <div class="status-strip__item">
                    <span class="status-strip__label">服务状态</span>
                    <span class="status ${serviceClass}">${serviceStatus}</span>
                </div>
                <div class="status-strip__item">
                    <span class="status-strip__label">活跃连接</span>
                    <span class="status-strip__value">${activeConnections}</span>
                </div>
                <div class="status-strip__item">
                    <span class="status-strip__label">排队任务</span>
                    <span class="status-strip__value">${pendingTasks}</span>
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
