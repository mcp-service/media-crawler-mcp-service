# -*- coding: utf-8 -*-
"""Shared UI helpers for admin pages built on FastMCP UI.

Provides:
- FastMCP UI imports with safe fallbacks
- Default CSP policy and `build_page` wrapper
- Navigation button group `render_nav`
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
    "script-src 'unsafe-inline' 'self'; connect-src 'self'; base-uri 'none'"
)


# Enhanced styles using FastMCP UI foundation with modern improvements
FASTMCP_PAGE_STYLES = f"""
{BASE_STYLES}
{BUTTON_STYLES}
{INFO_BOX_STYLES}
{DETAIL_BOX_STYLES}
{STATUS_MESSAGE_STYLES}

/* Custom enhancements */
.mc-container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
.mc-nav {{ margin: 1.5rem 0; display: flex; gap: 0.5rem; flex-wrap: wrap; }}
h1 {{ font-size: 2rem; margin: 1rem 0; font-weight: 600; }}
h3 {{ font-size: 1.25rem; margin: 1.5rem 0 0.75rem; font-weight: 500; }}

/* Form styling */
.mc-form {{ max-width: 600px; }}
.mc-form-group {{ margin-bottom: 1.5rem; }}
.mc-form-group label {{ display: block; margin-bottom: 0.5rem; font-weight: 500; }}
.mc-form-group input, .mc-form-group select, .mc-form-group textarea {{
  width: 100%; padding: 0.75rem; border-radius: 0.5rem;
  border: 1px solid var(--border-color, #e2e8f0);
  background: var(--input-bg, #ffffff);
  transition: border-color 0.2s, box-shadow 0.2s;
}}
.mc-form-group input:focus, .mc-form-group select:focus, .mc-form-group textarea:focus {{
  outline: none; border-color: var(--accent-color, #3b82f6);
  box-shadow: 0 0 0 3px var(--accent-color-alpha, rgba(59, 130, 246, 0.1));
}}
.mc-form-group small {{
  display: block; margin-top: 0.25rem; color: var(--text-muted, #6b7280); font-size: 0.875rem;
}}

/* Dashboard grids */
.mc-dashboard-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin: 1.5rem 0; }}
.mc-status-card {{ padding: 1.5rem; border-radius: 0.75rem; border: 1px solid var(--border-color, #e2e8f0);
  background: var(--card-bg, #ffffff); transition: box-shadow 0.2s; }}
.mc-status-card:hover {{ box-shadow: 0 4px 12px var(--shadow-color, rgba(0, 0, 0, 0.1)); }}
.mc-status-card h3 {{ margin-top: 0; margin-bottom: 1rem; }}

/* Status items */
.mc-status-item {{ 
  padding: 0.75rem; margin: 0.5rem 0; border-radius: 0.5rem;
  border: 1px solid var(--border-color, #e2e8f0);
  background: var(--item-bg, #f8fafc);
  display: flex; justify-content: space-between; align-items: center;
}}

/* Inspector layout */
.inspector-layout {{ display: grid; grid-template-columns: 300px 1fr; gap: 2rem; margin-top: 1.5rem; }}
.inspector-sidebar {{ background: var(--card-bg, #ffffff); border-radius: 0.75rem;
  border: 1px solid var(--border-color, #e2e8f0); padding: 1.5rem; }}
.inspector-main {{ background: var(--card-bg, #ffffff); border-radius: 0.75rem;
  border: 1px solid var(--border-color, #e2e8f0); padding: 1.5rem; }}

/* Code styling */
pre {{ background: var(--code-bg, #f8fafc); border: 1px solid var(--border-color, #e2e8f0);
  border-radius: 0.5rem; padding: 1rem; overflow-x: auto; font-size: 0.875rem; }}
code {{ background: var(--code-bg, #f1f5f9); padding: 0.25rem 0.5rem;
  border-radius: 0.25rem; font-size: 0.875rem; }}

/* Badge styling */
.badge {{ 
  display: inline-block; padding: 0.25rem 0.75rem; border-radius: 999px;
  font-size: 0.75rem; font-weight: 500; border: 1px solid var(--border-color, #e2e8f0);
}}

/* Responsive design */
@media (max-width: 768px) {{
  .mc-container {{ padding: 1rem; }}
  .inspector-layout {{ grid-template-columns: 1fr; }}
  .mc-dashboard-grid {{ grid-template-columns: 1fr; }}
}}
"""


def build_page(content: str, title: str, additional_styles: str | None = FASTMCP_PAGE_STYLES) -> HTMLResponse:
    styles = additional_styles or ""
    html = create_page(content=content, title=title, csp_policy=DEFAULT_CSP, additional_styles=styles)
    return create_secure_html_response(html)


def render_nav() -> str:
    """渲染导航按钮组 (旧版兼容)"""
    buttons: List[Tuple[str, str, str]] = [
        ("状态监控", "/dashboard", "primary"),
        ("登录管理", "/login", "secondary"),
        ("配置管理", "/config", "secondary"),
        ("MCP 调试", "/inspector", "secondary"),
    ]
    return "<nav class='mc-nav'>" + create_button_group(buttons) + "</nav>"


def create_sidebar_nav(items: List[Tuple[str, str, str, bool]]) -> str:
    """创建侧边栏导航
    Args:
        items: List of (title, url, icon, is_active) tuples
    """
    nav_items = []
    for title, url, icon, is_active in items:
        active_class = " is-active" if is_active else ""
        nav_items.append(f"""
            <a href="{url}" class="sidebar-nav__item{active_class}">
                <span class="sidebar-nav__icon">{icon}</span>
                <span class="sidebar-nav__text">{title}</span>
            </a>
        """)
    
    return f"""
        <nav class="sidebar-nav">
            {''.join(nav_items)}
        </nav>
    """


def create_stat_card(title: str, value: str, icon: str, trend: str = None) -> str:
    """创建统计卡片"""
    trend_html = f'<div class="stat-trend">{trend}</div>' if trend else ''
    return f"""
        <div class="stat-card">
            <div class="stat-card__icon">{icon}</div>
            <div class="stat-card__content">
                <h3 class="stat-card__title">{title}</h3>
                <div class="stat-card__value">{value}</div>
                {trend_html}
            </div>
        </div>
    """


def create_data_table(headers: List[str], rows: List[List[str]], table_id: str = "") -> str:
    """创建数据表格"""
    id_attr = f' id="{table_id}"' if table_id else ''
    header_html = ''.join(f'<th>{h}</th>' for h in headers)
    rows_html = []
    for row in rows:
        cells = ''.join(f'<td>{cell}</td>' for cell in row)
        rows_html.append(f'<tr>{cells}</tr>')
    
    return f"""
        <div class="data-table-wrapper">
            <table class="data-table"{id_attr}>
                <thead><tr>{header_html}</tr></thead>
                <tbody>{''.join(rows_html)}</tbody>
            </table>
        </div>
    """


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


def create_grid_layout(items: List[str], cols: str = "auto") -> str:
    """创建网格布局
    Args:
        items: HTML内容列表
        cols: 网格列数 ('auto', '1', '2', '3', '4', 'auto-sm', 'auto-lg')
    """
    grid_class = f"grid grid-cols-{cols}" if cols in ['1', '2', '3', '4'] else f"grid grid-{cols}"
    return f"""
        <div class="{grid_class}">
            {''.join(items)}
        </div>
    """


def create_card_with_header(title: str, content: str, subtitle: str = "", actions: str = "") -> str:
    """创建带头部的卡片"""
    subtitle_html = f'<p class="card-subtitle">{subtitle}</p>' if subtitle else ''
    actions_html = f'<div class="card-actions">{actions}</div>' if actions else ''
    
    return f"""
        <div class="card">
            <div class="card-header">
                <div>
                    <h3>{title}</h3>
                    {subtitle_html}
                </div>
                {actions_html}
            </div>
            <div class="card-body">
                {content}
            </div>
        </div>
    """


def create_loading_overlay() -> str:
    """创建加载遮罩"""
    return """
        <div class="loading-overlay">
            <div class="loading-spinner"></div>
        </div>
    """


def build_sidebar_layout(sidebar_content: str, main_content: str, title: str) -> HTMLResponse:
    """构建新的侧边栏布局页面"""
    page_html = f"""
        <div class="admin-shell">
            <aside class="admin-sidebar">
                {sidebar_content}
            </aside>
            <main class="admin-main">
                <div class="page-content page-transition">
                    {main_content}
                </div>
            </main>
        </div>
    """
    
    html = create_page(
        content=page_html, 
        title=title, 
        csp_policy=DEFAULT_CSP, 
        additional_styles=FASTMCP_PAGE_STYLES
    )
    return create_secure_html_response(html)