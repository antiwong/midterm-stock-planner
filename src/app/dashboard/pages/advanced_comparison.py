"""
Advanced Comparison Page
=========================
Compare multiple runs, time periods, and factor weights.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from datetime import datetime

from ..components.sidebar import render_page_header, render_section_header
from ..components.charts import create_performance_bar
from ..components.enhanced_charts import (
    create_comparison_chart,
    create_multi_metric_comparison,
    create_time_period_comparison
)
from ..data import load_runs, load_backtest_returns, load_run_scores
from ..utils import format_percent, format_number
from ..config import COLORS


def render_advanced_comparison():
    """Render advanced comparison page."""
    render_page_header("Advanced Comparison", "Compare runs, periods, and configurations")
    
    # Tabs for different comparison types
    tab1, tab2, tab3 = st.tabs([
        "🔀 Multiple Runs",
        "📅 Time Periods",
        "⚖️ Factor Weights"
    ])
    
    with tab1:
        _render_multiple_runs_comparison()
    
    with tab2:
        _render_time_period_comparison()
    
    with tab3:
        _render_factor_weights_comparison()


def _render_multiple_runs_comparison():
    """Compare multiple runs side-by-side."""
    render_section_header("Multiple Runs Comparison", "🔀")
    
    runs = load_runs()
    if not runs:
        st.warning("No runs available for comparison")
        return
    
    # Multi-select runs
    run_options = {f"{r['name'] or r['run_id'][:16]} ({r['run_id'][:8]})": r['run_id'] 
                   for r in runs}
    selected_runs = st.multiselect(
        "Select Runs to Compare",
        options=list(run_options.keys()),
        default=list(run_options.keys())[:min(3, len(run_options))],
        key="multi_run_select"
    )
    
    if not selected_runs:
        st.info("Select at least one run to compare")
        return
    
    selected_run_ids = [run_options[label] for label in selected_runs]
    selected_run_data = [r for r in runs if r['run_id'] in selected_run_ids]
    
    # Comparison metrics
    st.markdown("### Metrics Comparison")
    
    metrics = ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate', 'hit_rate']
    comparison_df = pd.DataFrame({
        'Run': [r.get('name', r['run_id'][:16]) for r in selected_run_data],
        'Return (%)': [r.get('total_return', 0) * 100 for r in selected_run_data],
        'Sharpe': [r.get('sharpe_ratio', 0) for r in selected_run_data],
        'Max DD (%)': [r.get('max_drawdown', 0) * 100 for r in selected_run_data],
        'Win Rate (%)': [r.get('win_rate', 0) * 100 for r in selected_run_data],
        'Hit Rate (%)': [r.get('hit_rate', 0) * 100 for r in selected_run_data],
    })
    
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Return Comparison")
        fig = create_comparison_chart(selected_run_data, 'total_return', "Total Return Comparison")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Sharpe Ratio Comparison")
        fig = create_comparison_chart(selected_run_data, 'sharpe_ratio', "Sharpe Ratio Comparison")
        st.plotly_chart(fig, use_container_width=True)
    
    # Multi-metric radar chart
    st.markdown("### Multi-Metric Comparison")
    fig = create_multi_metric_comparison(
        selected_run_data,
        ['total_return', 'sharpe_ratio', 'max_drawdown'],
        "Performance Profile"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Holdings comparison
    st.markdown("### Holdings Comparison")
    holdings_data = {}
    for run in selected_run_data:
        scores = load_run_scores(run['run_id'])
        if scores:
            df = pd.DataFrame(scores)
            holdings_data[run.get('name', run['run_id'][:16])] = set(df['ticker'].tolist())
    
    # Find common and unique holdings
    if holdings_data:
        all_holdings = set.union(*holdings_data.values())
        common_holdings = set.intersection(*holdings_data.values())
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Common Holdings", len(common_holdings))
        with col2:
            st.metric("Total Unique", len(all_holdings))
        with col3:
            st.metric("Overlap", f"{len(common_holdings)/len(all_holdings)*100:.1f}%" if all_holdings else "0%")
        
        if common_holdings:
            st.markdown("**Common Holdings:**")
            st.write(", ".join(sorted(common_holdings)))


def _render_time_period_comparison():
    """Compare performance across different time periods."""
    render_section_header("Time Period Comparison", "📅")
    
    runs = load_runs()
    if not runs:
        st.warning("No runs available")
        return
    
    # Select run
    run_options = {f"{r['name'] or r['run_id'][:16]}": r['run_id'] for r in runs}
    selected_run_label = st.selectbox("Select Run", options=list(run_options.keys()))
    selected_run_id = run_options[selected_run_label]
    
    returns_df = load_backtest_returns(selected_run_id)
    if returns_df is None or returns_df.empty:
        st.warning("No returns data available")
        return
    
    returns_df['date'] = pd.to_datetime(returns_df['date'])
    returns_df = returns_df.set_index('date')
    
    if 'portfolio_return' not in returns_df.columns:
        st.warning("Portfolio returns not found")
        return
    
    # Define time periods
    returns_series = returns_df['portfolio_return']
    start_date = returns_series.index[0]
    end_date = returns_series.index[-1]
    mid_date = start_date + (end_date - start_date) / 2
    
    periods = {
        'Full Period': returns_series,
        'First Half': returns_series[returns_series.index <= mid_date],
        'Second Half': returns_series[returns_series.index > mid_date],
    }
    
    # Add yearly breakdown if data spans multiple years
    if (end_date - start_date).days > 365:
        for year in range(start_date.year, end_date.year + 1):
            year_returns = returns_series[returns_series.index.year == year]
            if len(year_returns) > 0:
                periods[f'{year}'] = year_returns
    
    # Period performance metrics
    st.markdown("### Period Performance")
    period_metrics = []
    for period_name, period_returns in periods.items():
        if len(period_returns) == 0:
            continue
        total_return = (1 + period_returns).prod() - 1
        annualized = (1 + total_return) ** (252 / len(period_returns)) - 1 if len(period_returns) > 0 else 0
        volatility = period_returns.std() * np.sqrt(252)
        sharpe = annualized / volatility if volatility > 0 else 0
        
        period_metrics.append({
            'Period': period_name,
            'Return (%)': total_return * 100,
            'Annualized (%)': annualized * 100,
            'Volatility (%)': volatility * 100,
            'Sharpe': sharpe,
            'Days': len(period_returns)
        })
    
    metrics_df = pd.DataFrame(period_metrics)
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)
    
    # Cumulative returns chart
    st.markdown("### Cumulative Returns by Period")
    fig = create_time_period_comparison(periods, "Time Period Comparison")
    st.plotly_chart(fig, use_container_width=True)


def _render_factor_weights_comparison():
    """Compare different factor weight configurations."""
    render_section_header("Factor Weights Comparison", "⚖️")
    
    st.info("This feature compares portfolios built with different factor weight configurations.")
    st.markdown("""
    **How it works:**
    1. Select runs that used different factor weights
    2. Compare their performance
    3. Analyze which weight configuration performed best
    """)
    
    runs = load_runs()
    if not runs:
        st.warning("No runs available")
        return
    
    # Filter runs with config info
    runs_with_config = []
    for run in runs:
        config = run.get('config_json', {})
        if isinstance(config, str):
            import json
            try:
                config = json.loads(config)
            except:
                config = {}
        
        if config and 'analysis' in config:
            runs_with_config.append(run)
    
    if not runs_with_config:
        st.info("No runs with factor weight configuration found")
        return
    
    # Display runs with their factor weights
    st.markdown("### Runs with Factor Weight Configurations")
    
    weight_data = []
    for run in runs_with_config:
        config = run.get('config_json', {})
        if isinstance(config, str):
            import json
            try:
                config = json.loads(config)
            except:
                config = {}
        
        analysis_config = config.get('analysis', {})
        weights = analysis_config.get('weights', {})
        
        weight_data.append({
            'Run': run.get('name', run['run_id'][:16]),
            'Model Weight': weights.get('model_score', 0),
            'Value Weight': weights.get('value_score', 0),
            'Quality Weight': weights.get('quality_score', 0),
            'Return (%)': run.get('total_return', 0) * 100,
            'Sharpe': run.get('sharpe_ratio', 0)
        })
    
    weights_df = pd.DataFrame(weight_data)
    st.dataframe(weights_df, use_container_width=True, hide_index=True)
    
    # Visualization
    if len(weight_data) > 0:
        st.markdown("### Performance vs Factor Weights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.scatter(
                weights_df,
                x='Model Weight',
                y='Return (%)',
                size='Sharpe',
                hover_data=['Run', 'Value Weight', 'Quality Weight'],
                title="Return vs Model Weight"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.scatter(
                weights_df,
                x='Value Weight',
                y='Return (%)',
                size='Sharpe',
                hover_data=['Run', 'Model Weight', 'Quality Weight'],
                title="Return vs Value Weight"
            )
            st.plotly_chart(fig, use_container_width=True)
