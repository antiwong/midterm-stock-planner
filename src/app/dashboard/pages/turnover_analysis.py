"""
Turnover & Churn Analysis Page
===============================
Display turnover, churn, and holding period analysis.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from ..components.sidebar import render_page_header
from ..data import load_runs
from ..utils import format_percent, format_number
from src.analytics.analysis_service import AnalysisService


def render_turnover_analysis():
    """Render turnover analysis page."""
    render_page_header("Turnover & Churn Analysis", "Portfolio turnover and position stability")
    
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
        key="turnover_analysis_run"
    )
    selected_run_id = run_options[selected_run_label]
    
    # Initialize service
    service = AnalysisService()
    
    # Load analysis results
    analysis_result = service.get_analysis_result(selected_run_id, 'turnover')
    
    if not analysis_result:
        st.info("No turnover analysis found. Run comprehensive analysis first.")
        if st.button("🔄 Run Analysis"):
            st.info("Go to Comprehensive Analysis page to run all analyses.")
        return
    
    results = analysis_result.get_results()
    
    if 'error' in results:
        st.error(f"Error: {results['error']}")
        return
    
    # Tabs
    tabs = st.tabs(["Turnover", "Churn Rate", "Holding Periods", "Position Stability"])
    
    with tabs[0]:
        _render_turnover(results.get('turnover', {}))
    
    with tabs[1]:
        _render_churn(results.get('churn', {}))
    
    with tabs[2]:
        _render_holding_periods(results.get('holding_periods', {}))
    
    with tabs[3]:
        _render_stability(results.get('stability', {}))


def _render_turnover(turnover_data: dict):
    """Render turnover metrics."""
    if not turnover_data or 'error' in turnover_data:
        st.info("No turnover data available.")
        return
    
    st.markdown("### 📊 Portfolio Turnover")
    
    stats = turnover_data.get('statistics', {})
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Annualized Turnover", format_percent(stats.get('annualized_turnover', 0)))
        with col2:
            st.metric("Mean Turnover", format_percent(stats.get('mean', 0)))
        with col3:
            st.metric("Max Turnover", format_percent(stats.get('max', 0)))
        with col4:
            st.metric("Total Turnover", format_percent(stats.get('total_turnover', 0)))
    
    # Turnover over time
    turnover_by_period = turnover_data.get('turnover_by_period', {})
    if turnover_by_period:
        df = pd.DataFrame(list(turnover_by_period.items()), columns=['Date', 'Turnover'])
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        
        fig = px.line(
            df,
            x='Date',
            y='Turnover',
            title='Turnover Over Time',
            labels={'Turnover': 'Turnover (%)', 'Date': 'Date'}
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_churn(churn_data: dict):
    """Render churn rate metrics."""
    if not churn_data or 'error' in churn_data:
        st.info("No churn data available.")
        return
    
    st.markdown("### 📈 Churn Rate Analysis")
    
    stats = churn_data.get('statistics', {})
    if stats:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Mean Churn Rate", format_percent(stats.get('mean_churn_rate', 0)))
        with col2:
            st.metric("Max Churn Rate", format_percent(stats.get('max_churn_rate', 0)))
        with col3:
            st.metric("Min Churn Rate", format_percent(stats.get('min_churn_rate', 0)))
    
    # Churn over time
    churn_by_period = churn_data.get('churn_rate_by_period', {})
    if churn_by_period:
        df = pd.DataFrame(list(churn_by_period.items()), columns=['Date', 'Churn Rate'])
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        
        fig = px.line(
            df,
            x='Date',
            y='Churn Rate',
            title='Churn Rate Over Time',
            labels={'Churn Rate': 'Churn Rate (%)', 'Date': 'Date'}
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_holding_periods(holding_data: dict):
    """Render holding period analysis."""
    if not holding_data or 'error' in holding_data:
        st.info("No holding period data available.")
        return
    
    st.markdown("### ⏱️ Position Holding Periods")
    
    stats = holding_data.get('statistics', {})
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Avg Holding Period", f"{stats.get('mean_holding_period_days', 0):.0f} days")
        with col2:
            st.metric("Median Holding Period", f"{stats.get('median_holding_period_days', 0):.0f} days")
        with col3:
            st.metric("Min Period", f"{stats.get('min_holding_period_days', 0)} days")
        with col4:
            st.metric("Max Period", f"{stats.get('max_holding_period_days', 0)} days")
    
    # Distribution
    distribution = holding_data.get('distribution', {})
    if distribution:
        st.markdown("#### Holding Period Distribution")
        dist_df = pd.DataFrame([
            {'Period': '0-30 days', 'Count': distribution.get('short_term_0_30_days', 0)},
            {'Period': '31-90 days', 'Count': distribution.get('medium_term_31_90_days', 0)},
            {'Period': '91-180 days', 'Count': distribution.get('long_term_91_180_days', 0)},
            {'Period': '180+ days', 'Count': distribution.get('very_long_term_180_plus_days', 0)},
        ])
        
        fig = px.pie(
            dist_df,
            values='Count',
            names='Period',
            title='Holding Period Distribution'
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_stability(stability_data: dict):
    """Render position stability metrics."""
    if not stability_data or 'error' in stability_data:
        st.info("No stability data available.")
        return
    
    st.markdown("### 🎯 Position Stability")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Stability Score", format_percent(stability_data.get('stability_score', 0)))
    with col2:
        st.metric("Position Changes", stability_data.get('position_changes', 0))
    with col3:
        st.metric("Avg Changes/Period", f"{stability_data.get('avg_changes_per_period', 0):.2f}")
