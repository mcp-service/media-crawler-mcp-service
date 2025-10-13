// Admin Interface JavaScript

// 全局配置
const API_BASE = '/admin/api';

// 工具函数
function showMessage(message, type = 'info') {
    const messageDiv = document.getElementById('message');
    if (messageDiv) {
        messageDiv.className = `status status-${type}`;
        messageDiv.textContent = message;
        messageDiv.style.display = 'block';
        
        // 3秒后自动隐藏
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 3000);
    }
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
            'Content-Type': 'application/json',
        },
    };
    
    try {
        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        } else {
            return await response.text();
        }
    } catch (error) {
        console.error('API 请求失败:', error);
        throw error;
    }
}

// 登录管理相关
class LoginManager {
    constructor() {
        this.currentSession = null;
        this.pollInterval = null;
        this.pollTimeout = null;
        this.pollStartTime = null;
        this.maxPollTime = 5 * 60 * 1000; // 5分钟超时
        this.qrCodeDisplayed = false; // 标记二维码是否已显示
    }

    async startLogin(platform, loginType, phone = '', cookie = '') {
        try {
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

            if (loginType === 'qrcode') {
                this.startPolling();
                this.displayQRCode(response);
            } else {
                this.checkStatus();
            }

        } catch (error) {
            showError(`启动登录失败: ${error.message}`);
        }
    }

    displayQRCode(response) {
        console.log('[DEBUG] displayQRCode called with:', response);
        console.log('[DEBUG] qr_code_base64 length:', response.qr_code_base64 ? response.qr_code_base64.length : 'null');

        const qrContainer = document.getElementById('qr-code-container');
        if (!qrContainer) {
            console.error('[DEBUG] qr-code-container element not found!');
            return;
        }

        if (!response.qr_code_base64) {
            console.warn('[DEBUG] No QR code base64 data received, will retry...');
            // 如果还没有二维码，继续等待
            return;
        }

        qrContainer.innerHTML = `
            <div class="text-center mb-3">
                <h4>请扫描二维码登录</h4>
            </div>
            <div class="text-center">
                <img src="data:image/png;base64,${response.qr_code_base64}"
                     class="qr-code-img" alt="登录二维码"
                     style="max-width: 300px; border: 2px solid #ddd; padding: 10px; border-radius: 8px;">
            </div>
            <div class="text-center mt-3">
                <p class="status status-info">请使用${response.platform}移动端扫描上方二维码</p>
            </div>
        `;
        qrContainer.classList.remove('d-none');  // 移除隐藏类
        console.log('[DEBUG] QR code displayed successfully');

        // 二维码已显示，标记状态
        this.qrCodeDisplayed = true;
    }

    startPolling() {
        this.stopPolling();
        this.pollStartTime = Date.now();

        this.pollInterval = setInterval(() => {
            // 检查是否超时
            if (Date.now() - this.pollStartTime > this.maxPollTime) {
                showWarning('登录超时（5分钟），请重新尝试');
                this.stopPolling();
                this.hideQRCode();
                return;
            }
            this.checkStatus();
        }, 2000); // 每2秒检查一次

        // 设置最大超时
        this.pollTimeout = setTimeout(() => {
            showWarning('登录超时（5分钟），请重新尝试');
            this.stopPolling();
            this.hideQRCode();
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
        if (!this.currentSession) return;

        try {
            const response = await apiRequest(`/login/session/${this.currentSession}`);

            const statusElement = document.getElementById('login-status');
            if (statusElement) {
                statusElement.textContent = response.message || '检查中...';
            }

            // 如果二维码还没显示，尝试显示
            if (!this.qrCodeDisplayed && response.qr_code_base64) {
                this.displayQRCode(response);
            }

            if (response.status === 'success') {
                showSuccess('登录成功！');
                this.stopPolling();
                this.hideQRCode();
                // 刷新页面或跳转到其他页面
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else if (response.status === 'failed') {
                showError(`登录失败: ${response.message}`);
                this.stopPolling();
                this.hideQRCode();
            } else if (response.status === 'expired') {
                showWarning('二维码已过期，请重新获取');
                this.stopPolling();
                this.hideQRCode();
            }
        } catch (error) {
            console.error('检查登录状态失败:', error);
        }
    }

    hideQRCode() {
        const qrContainer = document.getElementById('qr-code-container');
        if (qrContainer) {
            qrContainer.classList.add('d-none');  // 添加隐藏类
        }
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
        }, 5000); // 每5秒更新一次
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

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 根据页面内容决定启动哪些功能
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

// 登录页面初始化
function initLoginPage() {
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(loginForm);
            const platform = formData.get('platform');
            const loginType = formData.get('login_type');
            const phone = formData.get('phone') || '';
            const cookie = formData.get('cookie') || '';
            
            await loginManager.startLogin(platform, loginType, phone, cookie);
        });
    }
}

// 配置页面初始化  
function initConfigPage() {
    configManager.loadConfig();
    
    const configForm = document.getElementById('config-form');
    if (configForm) {
        configForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(configForm);
            const configData = Object.fromEntries(formData);
            
            await configManager.saveConfig(configData);
        });
    }
}

// 状态页面初始化
function initStatusPage() {
    statusMonitor.startMonitoring();
}

// 页面离开时清理
window.addEventListener('beforeunload', function() {
    loginManager.stopPolling();
    statusMonitor.stopMonitoring();
});