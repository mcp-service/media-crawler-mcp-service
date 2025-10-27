# -*- coding: utf-8 -*-
from starlette.responses import HTMLResponse

from .ui_base import (
    build_page,
    create_logo,
    create_info_box,
    create_detail_box,
    create_button_group,
    create_status_message,
    render_nav,
)


def render_admin_login() -> HTMLResponse:
    header = (
        create_logo(None, "登录中心") 
        + "<h1>多平台登录中心</h1>" 
        + create_info_box("支持二维码、Cookie、手机号等方式触发登录，并通过同一面板查看状态")
    )
    nav = render_nav()

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
                {create_button_group([
                    ("开始登录", "#", "primary"),
                    ("刷新状态", "#", "secondary"),
                    ("刷新二维码", "#", "secondary")
                ]).replace("开始登录", "开始登录' type='submit' id='login-submit-btn").replace("刷新状态", "刷新状态' type='button' id='refresh-login-status").replace("刷新二维码", "刷新二维码' type='button' id='refresh-qr-btn' style='display:none;")}
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
    const API_BASE = '/api';
    const optimisticLoggedPlatforms = new Set();
    let availablePlatformCodes = [];
    let loginSessionsCache = [];
    
    function toggleLoginFields(){
        const t=document.getElementById('login_type').value;
        document.getElementById('phone-field').style.display=(t==='phone')?'block':'none';
        document.getElementById('cookie-field').style.display=(t==='cookie')?'block':'none';
    }
    
    async function apiRequest(endpoint, options = {}){
        const res=await fetch(`${API_BASE}${endpoint}`,{headers:{'Content-Type':'application/json'},...options});
        if(!res.ok)throw new Error(`HTTP ${res.status}`);
        const ct=res.headers.get('content-type')||'';
        return ct.includes('application/json')?res.json():res.text();
    }
    
    function populatePlatformSelectOptions(codes){
        const select=document.getElementById('platform');
        const options=["<option value=''>请选择平台</option>"];
        codes.forEach(code=>options.push(`<option value='${code}'>${code}</option>`));
        select.innerHTML=options.join('');
        const tip=document.getElementById('platform-tip');
        tip.textContent=codes.length?'请选择需要登录的平台':'当前没有可登录的平台';
    }
    
    async function loadPlatforms(){
        try{
            const platforms=await apiRequest('/login/platforms');
            availablePlatformCodes=Array.isArray(platforms)?platforms:[];
            populatePlatformSelectOptions(availablePlatformCodes);
        }catch(e){
            document.getElementById('platform-tip').textContent='平台列表加载失败';
        }
    }
    
    function renderPlatformSessions(sessions){
        const c=document.getElementById('platform-sessions');
        if(!sessions.length){
            c.innerHTML='<div>暂无登录会话</div>';
            return;
        }
        c.innerHTML=sessions.map(s=>`
            <div class="mc-status-item">
                <strong>${s.platform_name||s.platform}</strong> 
                <span class="badge" style="color: ${s.is_logged_in ? '#22c55e' : '#ef4444'}">${s.is_logged_in?'在线':'离线'}</span>
            </div>
        `).join('');
    }
    
    async function refreshLoginStatus(){
        try{
            const r=await apiRequest('/login/sessions');
            let s=Array.isArray(r)?r:[];
            s=s.map(x=>{
                if(optimisticLoggedPlatforms.has(x.platform)&&!x.is_logged_in){
                    return {...x,is_logged_in:true,last_login:x.last_login||new Date().toLocaleString()};
                }
                if(x.is_logged_in)optimisticLoggedPlatforms.delete(x.platform);
                return x;
            });
            loginSessionsCache=s;
            renderPlatformSessions(s);
        }catch(e){
            console.error('刷新失败',e);
        }
    }
    
    class LoginManager{
        constructor(){
            this.currentSession=null;
            this.currentSessionPlatform=null;
            this.qrCountdownInterval=null;
            this.qrExpirySeconds=180;
        }
        
        async startLogin(platform,loginType,phone='',cookie=''){
            if(!platform){
                alert('请选择需要登录的平台');
                return;
            }
            try{
                const resp=await apiRequest('/login/start',{
                    method:'POST',
                    body:JSON.stringify({platform,login_type:loginType,phone,cookie})
                });
                this.currentSession=resp.session_id;
                this.currentSessionPlatform=platform;
                if(loginType==='qrcode'){
                    this.displayQRCode(resp);
                }
                await this.checkStatus();
            }catch(e){
                alert('启动登录失败: '+e.message);
            }
        }
        
        async checkStatus(){
            if(!this.currentSession)return;
            try{
                const r=await apiRequest(`/login/session/${this.currentSession}`);
                this.renderStatus(r);
                if(r.qr_code_base64)this.displayQRCode(r);
                if(r.status==='success'){
                    alert('登录成功！');
                    optimisticLoggedPlatforms.add(this.currentSessionPlatform);
                    this.currentSession=null;
                    this.currentSessionPlatform=null;
                    await refreshLoginStatus();
                }
            }catch(e){
                console.error('检查登录状态失败',e);
            }
        }
        
        renderStatus(r){
            const el=document.getElementById('login-status');
            el.innerHTML = r.message ? `<div class="mc-status-item">${r.message}</div>` : '<div>检查中...</div>';
        }
        
        displayQRCode(resp){
            const c=document.getElementById('qr-code-container');
            c.style.display='block';
            document.getElementById('qr-image-wrapper').innerHTML=`
                <img src='data:image/png;base64,${resp.qr_code_base64}' 
                     alt='登录二维码' 
                     style='max-width:300px; border:1px solid var(--border-color, #e2e8f0); 
                            padding:12px; border-radius:12px; background: white;'>
            `;
            this.startQrCountdown(resp.qrcode_timestamp);
            document.getElementById('refresh-qr-btn').style.display='inline-block';
        }
        
        startQrCountdown(ts){
            const countdown=document.getElementById('qr-countdown');
            const t=ts?Number(ts)*1000:Date.now();
            const expire=t+this.qrExpirySeconds*1000;
            if(this.qrCountdownInterval)clearInterval(this.qrCountdownInterval);
            
            const tick=()=>{
                const r=Math.floor((expire-Date.now())/1000);
                countdown.textContent=r<=0?'二维码已过期，请点击刷新二维码重新获取':`二维码将在 ${r} 秒后过期`;
            };
            tick();
            this.qrCountdownInterval=setInterval(tick,1000);
        }
    }
    
    const loginManager=new LoginManager();
    
    document.addEventListener('DOMContentLoaded',()=>{
        toggleLoginFields();
        loadPlatforms().then(()=>refreshLoginStatus());
        
        document.getElementById('login_type').addEventListener('change',toggleLoginFields);
        document.getElementById('refresh-login-status').addEventListener('click',refreshLoginStatus);
        
        const form=document.getElementById('login-form');
        form.addEventListener('submit',async (ev)=>{
            ev.preventDefault();
            const fd=new FormData(form);
            await loginManager.startLogin(
                fd.get('platform'),
                fd.get('login_type'),
                fd.get('phone')||'',
                fd.get('cookie')||''
            );
        });
        
        document.getElementById('refresh-qr-btn').addEventListener('click',()=>{
            const platform=document.getElementById('platform').value;
            const loginType=document.getElementById('login_type').value;
            const phone=document.getElementById('phone')?.value||'';
            const cookie=document.getElementById('cookie')?.value||'';
            loginManager.startLogin(platform,loginType,phone,cookie);
        });
    });
    """

    parts = [
        "<div class='mc-container'>",
        header,
        nav,
        "<div class='mc-dashboard-grid'>",
        login_form_card,
        status_card,
        "</div>",
        sessions_card,
        "<script>" + login_js + "</script>",
        "</div>",
    ]
    return build_page("".join(parts), title="登录管理 · MediaCrawler MCP Service")