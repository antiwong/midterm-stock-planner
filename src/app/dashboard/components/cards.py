"""
Card Components
===============
Styled card components for displaying information.
"""

import streamlit as st
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..config import COLORS
from ..utils import format_percent, format_number, format_date, truncate_string


def render_stock_card(
    ticker: str,
    score: float,
    sector: str = "",
    rank: Optional[int] = None,
    change: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None,
    expanded: bool = False
):
    """Render a stock information card.
    
    Args:
        ticker: Stock ticker symbol
        score: Overall score
        sector: Sector name
        rank: Optional rank
        change: Price change percentage
        details: Additional details to show
        expanded: Whether to show in expanded mode
    """
    # Determine card style based on score/change
    card_class = "stock-card"
    if change is not None:
        card_class += " positive" if change > 0 else " negative" if change < 0 else ""
    elif score > 70:
        card_class += " positive"
    elif score < 30:
        card_class += " negative"
    
    # Build change indicator
    change_html = ""
    if change is not None:
        change_class = "positive" if change > 0 else "negative" if change < 0 else "neutral"
        change_html = f'<span class="{change_class}" style="margin-left: 1rem;">{change:+.2f}%</span>'
    
    # Rank badge
    rank_html = ""
    if rank is not None:
        rank_html = f'<span style="background: {COLORS["primary"]}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; margin-left: 0.5rem;">#{rank}</span>'
    
    html = f"""
    <div class="{card_class}">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <span class="ticker">{ticker}</span>{rank_html}
                <div class="sector">{sector}</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 1.5rem; font-weight: 700; color: {COLORS['dark']};">{score:.1f}</div>
                {change_html}
            </div>
        </div>
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)
    
    # Show details in expander if provided
    if details and expanded:
        with st.expander("View Details"):
            for key, value in details.items():
                st.write(f"**{key}:** {value}")


def render_run_card(
    run: Dict[str, Any],
    show_metrics: bool = True,
    clickable: bool = False,
    on_click: Optional[callable] = None
):
    """Render a run summary card.
    
    Args:
        run: Run dictionary
        show_metrics: Whether to show performance metrics
        clickable: Whether the card is clickable
        on_click: Click callback
    """
    run_id = run.get('run_id', '')[:12]
    name = run.get('name') or run_id
    status = run.get('status', 'unknown')
    created = format_date(run.get('created_at'), "%Y-%m-%d %H:%M")
    
    # Status badge
    status_class = status.lower()
    status_emoji = {
        'completed': '✅',
        'running': '🔄',
        'failed': '❌',
        'pending': '⏳'
    }.get(status_class, '❓')
    
    # Build header HTML (without metrics - those will be rendered separately)
    header_html = f'''<div class="info-card animate-fade-in" style="cursor: {'pointer' if clickable else 'default'};"><div style="display: flex; justify-content: space-between; align-items: flex-start;"><div><div style="font-size: 1.1rem; font-weight: 600; color: {COLORS['dark']};">{name}</div><div style="font-size: 0.8rem; color: {COLORS['muted']}; margin-top: 0.25rem;">{created} · {run_id}</div></div><div class="status-badge {status_class}">{status_emoji} {status}</div></div>'''
    
    # Add metrics if requested
    if show_metrics:
        ret = run.get('total_return')
        sharpe = run.get('sharpe_ratio')
        win = run.get('win_rate')
        
        ret_str = format_percent(ret) if ret is not None else "N/A"
        sharpe_str = format_number(sharpe) if sharpe is not None else "N/A"
        win_str = format_percent(win, with_sign=False) if win is not None else "N/A"
        
        ret_class = "positive" if ret and ret > 0 else "negative" if ret and ret < 0 else ""
        
        # Inline metrics HTML (all on one line to avoid whitespace issues)
        metrics_html = f'<div style="display: flex; gap: 1.5rem; margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid {COLORS["card_border"]};"><div><div style="font-size: 0.75rem; color: {COLORS["muted"]}; text-transform: uppercase;">Return</div><div class="{ret_class}" style="font-size: 1rem; font-weight: 600;">{ret_str}</div></div><div><div style="font-size: 0.75rem; color: {COLORS["muted"]}; text-transform: uppercase;">Sharpe</div><div style="font-size: 1rem; font-weight: 600;">{sharpe_str}</div></div><div><div style="font-size: 0.75rem; color: {COLORS["muted"]}; text-transform: uppercase;">Win Rate</div><div style="font-size: 1rem; font-weight: 600;">{win_str}</div></div></div>'
        header_html += metrics_html
    
    # Close the card
    header_html += '</div>'
    
    st.markdown(header_html, unsafe_allow_html=True)
    
    if clickable and on_click:
        if st.button(f"View Details", key=f"run_{run.get('run_id')}"):
            on_click(run)


def render_info_card(
    title: str,
    content: str,
    icon: str = "",
    color: str = "primary",
    footer: Optional[str] = None
):
    """Render a general information card.
    
    Args:
        title: Card title
        content: Card content
        icon: Optional emoji icon
        color: Border color key from COLORS
        footer: Optional footer text
    """
    border_color = COLORS.get(color, COLORS['primary'])
    
    footer_html = ""
    if footer:
        footer_html = f'<div style="font-size: 0.75rem; color: {COLORS["muted"]}; margin-top: 0.75rem; padding-top: 0.5rem; border-top: 1px solid {COLORS["card_border"]};">{footer}</div>'
    
    icon_html = f'<span style="margin-right: 0.5rem;">{icon}</span>' if icon else ''
    
    html = f"""
    <div class="info-card" style="border-left: 4px solid {border_color};">
        <div style="font-size: 0.875rem; font-weight: 600; color: {COLORS['dark']}; margin-bottom: 0.5rem;">
            {icon_html}{title}
        </div>
        <div style="color: {COLORS['dark']};">
            {content}
        </div>
        {footer_html}
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)


def render_progress_steps(
    steps: List[Dict[str, Any]],
    current_step: int = 0
):
    """Render progress steps.
    
    Args:
        steps: List of step dictionaries with 'label', 'status' keys
        current_step: Index of current step
    """
    steps_html = ""
    
    for i, step in enumerate(steps):
        status = step.get('status', 'pending')
        if i < current_step:
            status = 'complete'
        elif i == current_step:
            status = 'active'
        
        icon = "✓" if status == 'complete' else str(i + 1)
        label = step.get('label', f'Step {i + 1}')
        description = step.get('description', '')
        
        desc_html = f'<div style="font-size: 0.75rem; color: {COLORS["muted"]};">{description}</div>' if description else ''
        
        steps_html += f"""
        <div class="progress-step {status}">
            <div class="step-icon">{icon}</div>
            <div>
                <div style="font-weight: 500; color: {COLORS['dark']};">{label}</div>
                {desc_html}
            </div>
        </div>
        """
    
    st.markdown(steps_html, unsafe_allow_html=True)


def render_stat_card(
    stats: List[Dict[str, str]],
    columns: int = 3
):
    """Render a row of stat cards.
    
    Args:
        stats: List of dicts with 'label' and 'value' keys
        columns: Number of columns
    """
    cols = st.columns(columns)
    
    for i, stat in enumerate(stats):
        with cols[i % columns]:
            st.markdown(f"""
            <div style="background: {COLORS['light']}; padding: 1rem; border-radius: 8px; text-align: center;">
                <div style="font-size: 0.75rem; color: {COLORS['muted']}; text-transform: uppercase; letter-spacing: 0.05em;">{stat['label']}</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: {COLORS['dark']}; margin-top: 0.25rem;">{stat['value']}</div>
            </div>
            """, unsafe_allow_html=True)


def render_alert(
    message: str,
    alert_type: str = "info",
    icon: Optional[str] = None
):
    """Render a styled alert.
    
    Args:
        message: Alert message
        alert_type: Type (info, success, warning, danger)
        icon: Optional icon override
    """
    colors = {
        'info': (COLORS['info'], 'rgba(59, 130, 246, 0.1)'),
        'success': (COLORS['success'], 'rgba(16, 185, 129, 0.1)'),
        'warning': (COLORS['warning'], 'rgba(245, 158, 11, 0.1)'),
        'danger': (COLORS['danger'], 'rgba(239, 68, 68, 0.1)'),
    }
    
    icons = {
        'info': 'ℹ️',
        'success': '✅',
        'warning': '⚠️',
        'danger': '❌',
    }
    
    border_color, bg_color = colors.get(alert_type, colors['info'])
    icon = icon or icons.get(alert_type, 'ℹ️')
    
    st.markdown(f"""
    <div style="
        background: {bg_color};
        border-left: 4px solid {border_color};
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
    ">
        <span style="margin-right: 0.5rem;">{icon}</span>
        {message}
    </div>
    """, unsafe_allow_html=True)
