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
        this.setupNotifications();
        this.setupMobileNavigation();
        this.initializeTooltips();
        this.setupRealTimeUpdates();
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
        if (this.updateIntervals) {
            this.updateIntervals.forEach(intervalId => {
                clearInterval(intervalId);
            });
            this.updateIntervals.clear();
        }
        
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

// API 请求函数
async function apiRequest(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    };

    try {
        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API请求失败:', error);
        throw error;
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