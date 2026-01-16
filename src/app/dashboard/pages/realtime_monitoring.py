"""
Real-Time Monitoring Page
==========================
Display real-time portfolio monitoring and alerts.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from ..components.sidebar import render_page_header
from ..components.cards import render_alert
from ..data import load_runs
from ..utils import format_percent, format_number
from src.analytics.analysis_service import AnalysisService


def render_realtime_monitoring():
    """Render real-time monitoring page."""
    render_page_header("Real-Time Monitoring", "Portfolio alerts and daily performance tracking")
    
    # Get runs
    runs = load_runs()
    if not runs:
        st.warning("No analysis runs found. Run an analysis first.")
        return
    
    # Run selector
    run_options = {f"{r['name'] or r['run_id'][:16]} ({r['run_id'][:8]})": r['run_id'] 
                   for r in runs}
    selected_run_label = st.selectbox(
        "Select Run",
        options=list(run_options.keys()),
        key="realtime_monitoring_run"
    )
    selected_run_id = run_options[selected_run_label]
    
    # Initialize service
    service = AnalysisService()
    
    # Load analysis results
    analysis_result = service.get_analysis_result(selected_run_id, 'realtime_monitoring')
    
    if not analysis_result:
        st.info("No monitoring data found. Run comprehensive analysis first.")
        if st.button("🔄 Run Analysis"):
            st.info("Go to Comprehensive Analysis page to run all analyses.")
        return
    
    results = analysis_result.get_results()
    
    if 'error' in results:
        st.error(f"Error: {results['error']}")
        return
    
    # Display alerts
    alerts = results.get('alerts', [])
    if alerts:
        st.markdown("### 🚨 Active Alerts")
        
        critical_alerts = [a for a in alerts if a.get('level') == 'critical']
        warning_alerts = [a for a in alerts if a.get('level') == 'warning']
        info_alerts = [a for a in alerts if a.get('level') == 'info']
        
        if critical_alerts:
            st.error(f"⚠️ **{len(critical_alerts)} Critical Alert(s)**")
            for alert in critical_alerts:
                render_alert(alert.get('message', ''), 'danger')
        
        if warning_alerts:
            st.warning(f"⚠️ **{len(warning_alerts)} Warning(s)**")
            for alert in warning_alerts:
                render_alert(alert.get('message', ''), 'warning')
        
        if info_alerts:
            st.info(f"ℹ️ **{len(info_alerts)} Info Alert(s)**")
            for alert in info_alerts:
                render_alert(alert.get('message', ''), 'info')
    else:
        st.success("✅ No active alerts. Portfolio is performing normally.")
    
    # Tabs
    tabs = st.tabs(["Daily Summary", "Performance Metrics", "Alert History"])
    
    with tabs[0]:
        _render_daily_summary(results.get('daily_summary', {}))
    
    with tabs[1]:
        _render_performance_metrics(results.get('performance_metrics', {}))
    
    with tabs[2]:
        _render_alert_history(alerts)


def _render_daily_summary(summary: dict):
    """Render daily summary."""
    if not summary or 'error' in summary:
        st.info("No daily summary available.")
        return
    
    st.markdown("### 📊 Daily Portfolio Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Daily Return", format_percent(summary.get('daily_return', 0)))
    with col2:
        st.metric("YTD Return", format_percent(summary.get('ytd_return', 0)))
    with col3:
        vol = summary.get('volatility_30d')
        st.metric("30d Volatility", format_percent(vol) if vol else "N/A")
    with col4:
        sharpe = summary.get('sharpe_30d')
        st.metric("30d Sharpe", f"{sharpe:.2f}" if sharpe else "N/A")
    
    # Current drawdown
    drawdown = summary.get('current_drawdown', 0)
    st.metric("Current Drawdown", format_percent(drawdown))
    
    # Top positions
    top_positions = summary.get('top_positions', {})
    if top_positions:
        st.markdown("#### Top Positions")
        pos_df = pd.DataFrame(list(top_positions.items()), columns=['Ticker', 'Weight'])
        pos_df = pos_df.sort_values('Weight', ascending=False).head(10)
        st.dataframe(pos_df, use_container_width=True)
    
    # Benchmark comparison
    if 'benchmark_return' in summary:
        st.markdown("#### Benchmark Comparison")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Portfolio Return", format_percent(summary.get('daily_return', 0)))
        with col2:
            st.metric("Benchmark Return", format_percent(summary.get('benchmark_return', 0)))
        
        excess = summary.get('excess_return', 0)
        st.metric("Excess Return", format_percent(excess))


def _render_performance_metrics(metrics: dict):
    """Render performance metrics."""
    if not metrics or 'error' in metrics:
        st.info("No performance metrics available.")
        return
    
    st.markdown("### 📈 Performance Metrics (30-Day)")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Return", format_percent(metrics.get('total_return', 0)))
    with col2:
        st.metric("Annualized Return", format_percent(metrics.get('annualized_return', 0)))
    with col3:
        st.metric("Volatility", format_percent(metrics.get('volatility', 0)))
    with col4:
        sharpe = metrics.get('sharpe_ratio')
        st.metric("Sharpe Ratio", f"{sharpe:.2f}" if sharpe else "N/A")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Max Drawdown", format_percent(metrics.get('max_drawdown', 0)))
    with col2:
        st.metric("Win Rate", format_percent(metrics.get('win_rate', 0)))
    with col3:
        st.metric("Avg Win", format_percent(metrics.get('avg_win', 0)))


def _render_alert_history(alerts: list):
    """Render alert history."""
    if not alerts:
        st.info("No alerts in history.")
        return
    
    st.markdown("### 📋 Alert History")
    
    df = pd.DataFrame(alerts)
    st.dataframe(df, use_container_width=True)
    
    # Alert distribution by type
    if 'type' in df.columns:
        type_counts = df['type'].value_counts()
        fig = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title='Alerts by Type'
        )
        st.plotly_chart(fig, use_container_width=True)
