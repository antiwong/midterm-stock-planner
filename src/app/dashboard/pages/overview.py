"""
Overview Page
=============
Dashboard home page with summary metrics and recent activity.
"""

import streamlit as st
import pandas as pd
import numpy as np

from ..components.sidebar import render_page_header, render_section_header
from ..components.metrics import render_metric_card, render_kpi_summary
from ..components.charts import create_performance_bar, create_returns_chart
from ..components.tables import render_runs_table
from ..components.cards import render_run_card, render_info_card
from ..data import load_runs, get_available_run_folders
from ..utils import format_percent, format_number
from ..config import COLORS


def render_overview():
    """Render the overview page."""
    render_page_header(
        "Stock Analysis Dashboard",
        "ML-powered portfolio optimization and analysis"
    )
    
    runs = load_runs()
    
    if not runs:
        _render_empty_state()
        return
    
    _render_summary_metrics(runs)
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        _render_recent_runs(runs)
    
    with col2:
        _render_quick_insights(runs)
    
    if len(runs) >= 2:
        st.markdown("---")
        _render_performance_chart(runs)


def _render_empty_state():
    """Render empty state when no runs exist."""
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">📊</div>
        <h2 style="color: {dark}; margin-bottom: 0.5rem;">No Analysis Runs Yet</h2>
        <p style="color: {muted}; max-width: 400px; margin: 0 auto 2rem auto;">
            Run your first backtest to see performance metrics, stock scores, and AI-powered insights.
        </p>
    </div>
    """.format(dark=COLORS['dark'], muted=COLORS['muted']), unsafe_allow_html=True)
    
    st.code("python -m src.app.cli run-backtest --config config/config.yaml", language="bash")
    
    with st.expander("📖 Quick Start Guide"):
        st.markdown("""
        1. **Configure your watchlist** in `config/watchlists.yaml`
        2. **Set API keys** in your `.env` file
        3. **Run a backtest** using the command above
        4. **View results** in this dashboard
        5. **Build a portfolio** using the Portfolio Builder
        """)


def _render_summary_metrics(runs: list):
    """Render summary metric cards."""
    col1, col2, col3, col4 = st.columns(4)
    
    completed = [r for r in runs if r['status'] == 'completed']
    returns = [r['total_return'] for r in completed if r.get('total_return') is not None]
    sharpes = [r['sharpe_ratio'] for r in completed if r.get('sharpe_ratio') is not None]
    
    with col1:
        render_metric_card(
            "Total Runs",
            str(len(runs)),
            f"{len(completed)} completed",
            icon="📊"
        )
    
    with col2:
        avg_ret = np.mean(returns) if returns else None
        render_metric_card(
            "Avg Return",
            format_percent(avg_ret) if avg_ret is not None else "N/A",
            delta_color="positive" if avg_ret and avg_ret > 0 else "negative" if avg_ret else "normal",
            icon="📈"
        )
    
    with col3:
        avg_sharpe = np.mean(sharpes) if sharpes else None
        render_metric_card(
            "Avg Sharpe",
            format_number(avg_sharpe) if avg_sharpe is not None else "N/A",
            delta_color="positive" if avg_sharpe and avg_sharpe > 1 else "normal",
            icon="⚡"
        )
    
    with col4:
        run_folders = get_available_run_folders()
        render_metric_card(
            "Output Folders",
            str(len(run_folders)),
            "with results",
            icon="📁"
        )


def _render_recent_runs(runs: list):
    """Render recent runs section."""
    render_section_header("Recent Analysis Runs", "📋")
    
    # Show last 5 runs as cards
    for run in runs[:5]:
        render_run_card(run, show_metrics=True)
        st.markdown("")  # Spacing


def _render_quick_insights(runs: list):
    """Render quick insights panel."""
    render_section_header("Quick Insights", "💡")
    
    completed = [r for r in runs if r['status'] == 'completed']
    
    if not completed:
        render_info_card(
            "No Completed Runs",
            "Complete a backtest to see insights",
            icon="ℹ️",
            color="info"
        )
        return
    
    # Best performing run
    best_run = max(completed, key=lambda x: x.get('total_return', -float('inf')))
    if best_run.get('total_return') is not None:
        render_info_card(
            "Best Performer",
            f"**{best_run.get('name') or best_run['run_id'][:8]}**\n\n"
            f"Return: {format_percent(best_run['total_return'])}",
            icon="🏆",
            color="success"
        )
        st.markdown("")
    
    # Average stats
    returns = [r['total_return'] for r in completed if r.get('total_return') is not None]
    if returns:
        positive_rate = sum(1 for r in returns if r > 0) / len(returns)
        render_info_card(
            "Win Rate",
            f"**{positive_rate*100:.0f}%** of runs profitable",
            icon="🎯",
            color="primary"
        )
        st.markdown("")
    
    # Latest run status
    latest = runs[0]
    status_icon = {
        'completed': '✅',
        'running': '🔄',
        'failed': '❌',
        'pending': '⏳'
    }.get(latest['status'].lower(), '❓')
    
    render_info_card(
        "Latest Run",
        f"{status_icon} {latest['status'].title()}",
        icon="🕐",
        color="info",
        footer=f"ID: {latest['run_id'][:12]}..."
    )


def _render_performance_chart(runs: list):
    """Render performance over time chart."""
    render_section_header("Performance History", "📈")
    
    # Filter runs with valid data
    perf_data = []
    for r in runs:
        if r.get('created_at') and r.get('total_return') is not None:
            perf_data.append({
                'date': pd.to_datetime(r['created_at']),
                'return': r['total_return'],
                'sharpe': r.get('sharpe_ratio', 0),
                'name': r.get('name') or r['run_id'][:8]
            })
    
    if not perf_data:
        st.info("Not enough data to display performance chart")
        return
    
    perf_df = pd.DataFrame(perf_data).sort_values('date')
    
    # Create chart
    fig = create_performance_bar(
        runs=runs,
        metric='total_return',
        title="Return by Run",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
