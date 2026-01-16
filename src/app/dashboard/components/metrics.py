"""
Metric Display Components
=========================
Components for displaying metrics and KPIs.
"""

import streamlit as st
from typing import Optional, List, Tuple
from ..utils import format_percent, format_number, get_color_for_value


def render_metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    delta_color: str = "normal",
    icon: str = "",
    help_text: Optional[str] = None
):
    """Render a styled metric card.
    
    Args:
        label: Metric label
        value: Metric value
        delta: Optional change/delta text
        delta_color: Color for delta (normal, positive, negative, inverse)
        icon: Optional emoji icon
        help_text: Optional tooltip text
    """
    delta_class = ""
    if delta_color == "positive":
        delta_class = "positive"
    elif delta_color == "negative":
        delta_class = "negative"
    elif delta_color == "inverse":
        # Inverse: positive is bad, negative is good
        if delta and delta.startswith('+'):
            delta_class = "negative"
        elif delta and delta.startswith('-'):
            delta_class = "positive"
    
    # Always include delta div for consistent height, even if empty
    if delta:
        delta_html = f'<div class="delta {delta_class}">{delta}</div>'
    else:
        delta_html = '<div class="delta delta-empty">&nbsp;</div>'
    
    icon_html = f'<span style="margin-right: 0.5rem;">{icon}</span>' if icon else ''
    
    html = f"""
    <div class="metric-card animate-fade-in">
        <h3>{icon_html}{label}</h3>
        <div class="value">{value}</div>
        {delta_html}
    </div>
    """
    
    if help_text:
        st.markdown(html, unsafe_allow_html=True)
        st.caption(help_text)
    else:
        st.markdown(html, unsafe_allow_html=True)


def render_metric_row(
    metrics: List[Tuple[str, str, Optional[str], str]],
    columns: int = 4
):
    """Render a row of metric cards.
    
    Args:
        metrics: List of (label, value, delta, delta_color) tuples
        columns: Number of columns
    """
    cols = st.columns(columns)
    
    for i, (label, value, delta, delta_color) in enumerate(metrics):
        with cols[i % columns]:
            render_metric_card(label, value, delta, delta_color)


def render_kpi_summary(
    total_return: Optional[float] = None,
    sharpe_ratio: Optional[float] = None,
    win_rate: Optional[float] = None,
    max_drawdown: Optional[float] = None,
    volatility: Optional[float] = None,
    sortino_ratio: Optional[float] = None,
):
    """Render a summary row of key performance indicators.
    
    Args:
        total_return: Total return (0.1 = 10%)
        sharpe_ratio: Sharpe ratio
        win_rate: Win rate (0.5 = 50%)
        max_drawdown: Max drawdown (0.1 = 10%)
        volatility: Volatility (0.2 = 20%)
        sortino_ratio: Sortino ratio
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        ret_str = format_percent(total_return) if total_return is not None else "N/A"
        delta_color = "positive" if total_return and total_return > 0 else "negative" if total_return else "normal"
        render_metric_card("Total Return", ret_str, delta_color=delta_color, icon="📈")
    
    with col2:
        sharpe_str = format_number(sharpe_ratio) if sharpe_ratio is not None else "N/A"
        delta_color = "positive" if sharpe_ratio and sharpe_ratio > 1 else "normal"
        render_metric_card("Sharpe Ratio", sharpe_str, delta_color=delta_color, icon="⚡")
    
    with col3:
        win_str = format_percent(win_rate, with_sign=False) if win_rate is not None else "N/A"
        delta_color = "positive" if win_rate and win_rate > 0.5 else "normal"
        render_metric_card("Win Rate", win_str, delta_color=delta_color, icon="🎯")
    
    with col4:
        dd_str = format_percent(max_drawdown) if max_drawdown is not None else "N/A"
        render_metric_card("Max Drawdown", dd_str, delta_color="negative", icon="📉")


def render_mini_metrics(metrics: dict, cols_per_row: int = 3):
    """Render smaller inline metrics.
    
    Args:
        metrics: Dictionary of {label: value}
        cols_per_row: Columns per row
    """
    items = list(metrics.items())
    
    for i in range(0, len(items), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, (label, value) in enumerate(items[i:i + cols_per_row]):
            with cols[j]:
                st.metric(label, value)
