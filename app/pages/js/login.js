// Login page JS extracted from inline script
// App mounted at /mcp
const API_BASE = '/api';
const optimisticLoggedPlatforms = new Set();
let availablePlatformCodes = [];
let loginSessionsCache = [];

// 平台代码到中文名称的映射
const PLATFORM_NAMES = {
  bili: 'B站 (Bilibili)',
  xhs: '小红书',
  dy: '抖音',
  ks: '快手',
  wb: '微博',
  tieba: '贴吧',
  zhihu: '知乎',
};

function getPlatformName(code) {
  return PLATFORM_NAMES[code] || code;
}

function toggleLoginFields() {
  const t = document.getElementById('login_type').value;
  document.getElementById('phone-field').style.display = t === 'phone' ? 'block' : 'none';
  document.getElementById('cookie-field').style.display = t === 'cookie' ? 'block' : 'none';
}

async function apiRequest(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const ct = res.headers.get('content-type') || '';
    return ct.includes('application/json') ? res.json() : res.text();
  } catch (error) {
    console.error('API Request failed:', endpoint, error);
    throw error;
  }
}

function populatePlatformSelectOptions(codes) {
  const select = document.getElementById('platform');
  const options = ["<option value=''>请选择平台</option>"];
  codes.forEach((code) => options.push(`<option value='${code}'>${getPlatformName(code)}</option>`));
  select.innerHTML = options.join('');
  const tip = document.getElementById('platform-tip');
  tip.textContent = codes.length ? '请选择需要登录的平台' : '当前没有可登录的平台';
}

async function loadPlatforms() {
  try {
    const platforms = await apiRequest('/login/platforms');
    availablePlatformCodes = Array.isArray(platforms) ? platforms : [];
    populatePlatformSelectOptions(availablePlatformCodes);
  } catch (e) {
    console.error('加载平台列表失败:', e);
    document.getElementById('platform-tip').textContent = '平台列表加载失败';
  }
}

function renderPlatformSessions(sessions) {
  const c = document.getElementById('platform-sessions');
  if (!sessions || !sessions.length) {
    c.innerHTML = '<div style="color: #718096; text-align: center; padding: 1rem;">暂无登录会话</div>';
    return;
  }
  c.innerHTML = sessions
    .map((s) => {
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
    })
    .join('');
}

async function refreshLoginStatus(force = false) {
  try {
    const r = await apiRequest(`/login/sessions${force ? '?force=1' : ''}`);
    let s = Array.isArray(r) ? r : [];
    s = s.map((x) => {
      if (optimisticLoggedPlatforms.has(x.platform) && !x.is_logged_in) {
        return { ...x, is_logged_in: true, last_login: x.last_login || new Date().toLocaleString() };
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
  const status = document.getElementById('login-status');
  status.innerHTML = `<div class="mc-status-item">正在退出 ${getPlatformName(platform)} ...</div>`;
  try {
    await apiRequest(`/login/logout/${platform}`, { method: 'POST' });
    optimisticLoggedPlatforms.delete(platform);
    status.innerHTML = `<div class=\"mc-status-item\">已退出 ${getPlatformName(platform)}，状态已更新</div>`;
    await refreshLoginStatus();
  } catch (e) {
    status.innerHTML = `<div class=\"mc-status-item\" style=\"color:#b91c1c;\">退出失败：${e.message}</div>`;
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
    const status = document.getElementById('login-status');
    if (!platform) {
      status.innerHTML = '<div class="mc-status-item" style="color:#92400e;">请选择需要登录的平台</div>';
      return;
    }

    // 停止之前的轮询
    this.stopPolling();

    try {
      // 二维码生成/刷新时展示 loading
      const qrContainer = document.getElementById('qr-code-container');
      const qrWrapper = document.getElementById('qr-image-wrapper');
      const refreshQrBtn = document.getElementById('refresh-qr-btn');
      if (loginType === 'qrcode') {
        qrContainer.style.display = 'block';
        qrWrapper.innerHTML = '<div style="text-align:center;color:#6b7280;">二维码生成中...</div>';
      }
      if (refreshQrBtn) refreshQrBtn.disabled = true;
      const submitBtn = document.getElementById('login-submit-btn');
      if (submitBtn) submitBtn.disabled = true;
      status.innerHTML = '<div class="mc-status-item">正在启动登录流程...</div>';

      const resp = await apiRequest('/login/start', {
        method: 'POST',
        body: JSON.stringify({ platform, login_type: loginType, phone, cookie }),
      });

      this.currentSession = resp.session_id;
      this.currentSessionPlatform = platform;

      // 立即检查一次状态
      await this.checkStatus();

      // 开始轮询状态（每2秒检查一次）
      this.startPolling();
    } catch (e) {
      status.innerHTML = `<div class=\"mc-status-item\" style=\"color:#b91c1c;\">启动登录失败：${e.message}</div>`;
      this.stopPolling();
    } finally {
      const refreshQrBtn = document.getElementById('refresh-qr-btn');
      if (refreshQrBtn) refreshQrBtn.disabled = false;
      const submitBtn = document.getElementById('login-submit-btn');
      if (submitBtn) submitBtn.disabled = false;
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
    const msg = r && r.message ? r.message : '检查中...';
    el.innerHTML = `<div class=\"mc-status-item\">${msg}</div>`;
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
    const status = document.getElementById('login-status');
    status.innerHTML = '<div class="mc-status-item">二维码已生成，请使用手机扫码登录</div>';
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
      // 手动刷新：强制实时 pong，更新缓存为真实状态
      refreshLoginStatus(true);
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
