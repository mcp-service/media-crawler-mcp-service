# -*- coding: utf-8 -*-
"""Shared UI helpers for admin pages built on FastMCP UI.

Provides:
- FastMCP UI imports with safe fallbacks
- Default CSP policy and `build_page` wrapper
- Top navigation layout
- Enhanced layout and component helpers
"""

from __future__ import annotations

from typing import List, Tuple
from starlette.responses import HTMLResponse
from fastmcp.utilities.ui import (
        create_page,
        create_logo,
        create_status_message,
        create_info_box,
        create_detail_box,
        create_button_group,
        create_secure_html_response,
        BASE_STYLES,
        BUTTON_STYLES,
        INFO_BOX_STYLES,
        DETAIL_BOX_STYLES,
        STATUS_MESSAGE_STYLES,
    )



# Relaxed CSP to allow inline scripts and same-origin fetch used by pages
DEFAULT_CSP = (
    "default-src 'self'; style-src 'unsafe-inline'; img-src https: data:; "
    "script-src 'unsafe-inline' 'self'; connect-src 'self'; base-uri 'none'; "
    "font-src 'self' data: https: http:"
)


# Enhanced styles using FastMCP UI foundation with top navigation layout
FASTMCP_PAGE_STYLES = f"""
{BASE_STYLES}
{BUTTON_STYLES}
{INFO_BOX_STYLES}
{DETAIL_BOX_STYLES}
{STATUS_MESSAGE_STYLES}

/* Prevent layout shift from scrollbar */
html {{
  overflow-y: scroll;
}}

/* Reset body to full width layout - override FastMCP defaults */
body {{
  margin: 0;
  padding: 0;
  max-width: 100%;
  display: block !important;
  align-items: unset !important;
  justify-content: unset !important;
  min-height: 100vh;
}}

/* Top Navigation Bar */
.top-nav {{
  background: #0066cc;
  color: white;
  padding: 0 2rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}}

.top-nav__container {{
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
}}

.top-nav__brand {{
  display: flex;
  align-items: center;
  gap: 1rem;
}}

.top-nav__logo {{
  width: 40px;
  height: 40px;
  background: rgba(255,255,255,0.2);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.125rem;
}}

.top-nav__title {{
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}}

.top-nav__menu {{
  display: flex;
  gap: 0.5rem;
  list-style: none;
  margin: 0;
  padding: 0;
}}

.top-nav__item {{
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  text-decoration: none;
  color: rgba(255,255,255,0.9);
  font-weight: 500;
  transition: all 0.2s;
  cursor: pointer;
}}

.top-nav__item:hover {{
  background: rgba(255,255,255,0.15);
  color: white;
}}

.top-nav__item.is-active {{
  background: rgba(255,255,255,0.25);
  color: white;
  font-weight: 600;
}}

/* Main Content Area */
.main-content {{
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
  min-height: calc(100vh - 64px);
}}

/* Page Header */
.page-header {{
  margin-bottom: 2rem;
}}

.page-breadcrumb {{
  font-size: 0.875rem;
  color: var(--text-muted, #718096);
  margin-bottom: 0.5rem;
}}

.page-title {{
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 0.5rem;
  color: var(--text-primary, #1a202c);
}}

.page-subtitle {{
  font-size: 1rem;
  color: var(--text-secondary, #4a5568);
  margin: 0;
}}

.page-actions {{
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}}

/* Dashboard grids */
.mc-dashboard-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.5rem;
  margin: 1.5rem 0;
}}

.mc-status-card {{
  padding: 1.5rem;
  border-radius: 0.75rem;
  border: 1px solid var(--border-color, #e2e8f0);
  background: var(--card-bg, #ffffff);
  transition: box-shadow 0.2s;
}}

.mc-status-card:hover {{
  box-shadow: 0 4px 12px var(--shadow-color, rgba(0, 0, 0, 0.1));
}}

.mc-status-card h3 {{
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.125rem;
  font-weight: 600;
}}

/* Status items */
.mc-status-item {{
  padding: 0.875rem;
  margin: 0.5rem 0;
  border-radius: 0.5rem;
  border: 1px solid var(--border-color, #e2e8f0);
  background: var(--item-bg, #f8fafc);
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: background 0.2s;
}}

.mc-status-item:hover {{
  background: var(--item-hover-bg, #f1f5f9);
}}

/* Form styling */
.mc-form {{
  max-width: 600px;
}}

.mc-form-group {{
  margin-bottom: 1.5rem;
}}

.mc-form-group label {{
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}}

.mc-form-group input, .mc-form-group select, .mc-form-group textarea {{
  width: 100%;
  padding: 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid var(--border-color, #e2e8f0);
  background: var(--input-bg, #ffffff);
  transition: border-color 0.2s, box-shadow 0.2s;
}}

/* Do not force full width for checkbox/radio */
.mc-form-group input[type='checkbox'],
.mc-form-group input[type='radio'] {{
  width: auto;
  padding: 0;
}}

.mc-form-group input:focus, .mc-form-group select:focus, .mc-form-group textarea:focus {{
  outline: none;
  border-color: var(--accent-color, #667eea);
  box-shadow: 0 0 0 3px var(--accent-color-alpha, rgba(102, 126, 234, 0.1));
}}

.mc-form-group small {{
  display: block;
  margin-top: 0.25rem;
  color: var(--text-muted, #6b7280);
  font-size: 0.875rem;
}}

/* Simple spinner for loading states */
.mc-spinner {{
  width: 28px;
  height: 28px;
  border: 3px solid #e5e7eb;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: mc-spin 1s linear infinite;
  display: inline-block;
}}

@keyframes mc-spin {{
  to {{ transform: rotate(360deg); }}
}}

/* Code styling */
pre {{
  background: var(--code-bg, #f8fafc);
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: 0.5rem;
  padding: 1rem;
  overflow-x: auto;
  font-size: 0.875rem;
}}

code {{
  background: var(--code-bg, #f1f5f9);
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}}

/* Status badges */
.status-badge {{
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}}

.status-badge.status-success {{
  background: #d1fae5;
  color: #065f46;
}}

.status-badge.status-error {{
  background: #fee2e2;
  color: #991b1b;
}}

.status-badge.status-warning {{
  background: #fef3c7;
  color: #92400e;
}}

/* Responsive design */
@media (max-width: 768px) {{
  .main-content {{
    padding: 1rem;
  }}

  .mc-dashboard-grid {{
    grid-template-columns: 1fr;
  }}

  .top-nav {{
    padding: 0 1rem;
  }}

  .top-nav__menu {{
    gap: 0.25rem;
  }}

  .top-nav__item {{
    padding: 0.375rem 0.75rem;
    font-size: 0.875rem;
  }}
}}

/* Inspector minimal styles for pages UI */
.inspector-group {{
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: 0.5rem;
  padding: 0.75rem;
  margin-bottom: 1rem;
}}

.inspector-group__header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}}

.inspector-group__tools {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.5rem;
}}

.inspector-tool {{
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: 0.5rem;
  background: var(--item-bg, #f8fafc);
  text-align: left;
  cursor: pointer;
}}

.inspector-tool .tool-name {{
  font-weight: 600;
  color: var(--text-primary, #1a202c);
}}

.inspector-tool .tool-meta {{
  font-size: 12px;
  color: var(--text-muted, #6b7280);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}

.inspector-tool.is-active {{
  outline: 2px solid var(--accent-color, #667eea);
  background: #eef2ff;
}}

.inspector-group__routes ul {{
  margin: 0.5rem 0 0;
  padding-left: 1rem;
}}

.inspector-group__routes li {{
  font-size: 12px;
  color: var(--text-muted, #6b7280);
}}

.inspector-group__routes code {{
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}}
"""


def render_top_nav(current_path: str = "/dashboard") -> str:
    """渲染顶部导航栏"""
    # FastMCP 应用内部路径不需要 /mcp 前缀
    nav_items = [
        ("状态监控", "/dashboard"),
        ("登录管理", "/login"),
        ("发布管理", "/publish"),
        ("配置管理", "/config"),
        ("MCP 调试", "/inspector"),
    ]

    menu_html = []
    for title, url in nav_items:
        # 直接匹配路径
        active_class = " is-active" if (
            current_path == url or current_path.startswith(url)
        ) else ""
        menu_html.append(f'<a href="{url}" class="top-nav__item{active_class}">{title}</a>')

    return f"""
    <nav class="top-nav">
        <div class="top-nav__container">
            <div class="top-nav__brand">
                <div class="top-nav__logo">MC</div>
                <h1 class="top-nav__title">Media Crawler</h1>
            </div>
            <div class="top-nav__menu">
                {''.join(menu_html)}
            </div>
        </div>
    </nav>
    """


def build_page(content: str, title: str, additional_styles: str | None = FASTMCP_PAGE_STYLES) -> HTMLResponse:
    """构建页面 (保留向后兼容)"""
    styles = additional_styles or ""
    html = create_page(content=content, title=title, csp_policy=DEFAULT_CSP, additional_styles=styles)
    return create_secure_html_response(html)


def build_page_with_nav(main_content: str, title: str, current_path: str = "/dashboard") -> HTMLResponse:
    """构建带顶部导航的页面"""
    nav = render_top_nav(current_path)

    page_html = f"""
        {nav}
        <main class="main-content">
            {main_content}
        </main>
    """

    html = create_page(
        content=page_html,
        title=title,
        csp_policy=DEFAULT_CSP,
        additional_styles=FASTMCP_PAGE_STYLES
    )
    return create_secure_html_response(html)


def create_page_header(title: str, breadcrumb: str = "", actions: str = "") -> str:
    """创建页面头部"""
    breadcrumb_html = f'<div class="page-breadcrumb">{breadcrumb}</div>' if breadcrumb else ''
    actions_html = f'<div class="page-actions">{actions}</div>' if actions else ''

    return f"""
        <header class="page-header">
            {breadcrumb_html}
            <h1 class="page-title">{title}</h1>
            {actions_html}
        </header>
    """


def create_button(
    text: str,
    btn_type: str = "button",
    btn_id: str = "",
    btn_class: str = "btn btn-primary",
    onclick: str = "",
    style: str = "",
    disabled: bool = False,
) -> str:
    """创建按钮（更安全的方式，避免直接拼接 HTML）

    Args:
        text: 按钮文本
        btn_type: button 类型（button, submit, reset）
        btn_id: 按钮 ID
        btn_class: CSS 类名
        onclick: onclick 事件处理
        style: 内联样式
        disabled: 是否禁用

    Returns:
        按钮 HTML 字符串
    """
    attrs = [f'type="{btn_type}"']

    if btn_id:
        attrs.append(f'id="{btn_id}"')
    if btn_class:
        attrs.append(f'class="{btn_class}"')
    if onclick:
        attrs.append(f'onclick="{onclick}"')
    if style:
        attrs.append(f'style="{style}"')
    if disabled:
        attrs.append('disabled')

    return f'<button {" ".join(attrs)}>{text}</button>'


def create_button_row(*buttons: str, gap: str = "0.5rem") -> str:
    """创建按钮行容器

    Args:
        *buttons: 按钮 HTML 字符串（可变参数）
        gap: 按钮间距

    Returns:
        按钮行 HTML
    """
    return f'<div style="display: flex; gap: {gap};">{"".join(buttons)}</div>'
