"""
Tax Optimization Page
=====================
Display tax optimization analysis and recommendations.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from ..components.sidebar import render_page_header
from ..data import load_runs
from ..utils import format_percent, format_number, format_currency
from src.analytics.analysis_service import AnalysisService


def render_tax_optimization():
    """Render tax optimization page."""
    render_page_header("Tax Optimization", "Tax-loss harvesting and tax-efficient strategies")
    
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
        key="tax_optimization_run"
    )
    selected_run_id = run_options[selected_run_label]
    
    # Initialize service
    service = AnalysisService()
    
    # Load analysis results
    analysis_result = service.get_analysis_result(selected_run_id, 'tax_optimization')
    
    if not analysis_result:
        st.info("No tax optimization analysis found. Run comprehensive analysis first.")
        if st.button("🔄 Run Analysis"):
            st.info("Go to Comprehensive Analysis page to run all analyses.")
        return
    
    results = analysis_result.get_results()
    
    if 'error' in results:
        st.error(f"Error: {results['error']}")
        return
    
    # Tabs
    tabs = st.tabs(["Tax-Loss Harvesting", "Tax Efficiency", "Wash Sales", "Rebalancing"])
    
    with tabs[0]:
        _render_harvesting(results.get('harvest_suggestions', {}))
    
    with tabs[1]:
        _render_tax_efficiency(results.get('tax_efficiency', {}))
    
    with tabs[2]:
        st.info("Wash sale detection requires trade history data. This feature will be enhanced with trade data integration.")
    
    with tabs[3]:
        st.info("Tax-efficient rebalancing recommendations will be displayed here.")


def _render_harvesting(harvest_data: dict):
    """Render tax-loss harvesting suggestions."""
    if not harvest_data or 'error' in harvest_data:
        st.info("No tax-loss harvesting opportunities found.")
        return
    
    st.markdown("### 💡 Tax-Loss Harvesting Opportunities")
    
    suggestions = harvest_data.get('suggestions', [])
    if not suggestions:
        st.success("✅ No tax-loss harvesting opportunities at this time.")
        return
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Harvestable Loss", format_currency(harvest_data.get('total_harvestable_loss', 0)))
    with col2:
        st.metric("Recommended Harvest", format_currency(harvest_data.get('recommended_harvest_loss', 0)))
    with col3:
        st.metric("Portfolio Exposure", format_percent(harvest_data.get('harvest_percentage', 0)))
    
    # Suggestions table
    df = pd.DataFrame(suggestions)
    st.markdown("#### Harvesting Recommendations")
    st.dataframe(df, use_container_width=True)
    
    # Chart
    if len(df) > 0:
        fig = px.bar(
            df,
            x='ticker',
            y='unrealized_loss',
            title='Unrealized Losses by Position',
            labels={'unrealized_loss': 'Unrealized Loss ($)', 'ticker': 'Ticker'}
        )
        fig.update_traces(marker_color='#ef4444')
        st.plotly_chart(fig, use_container_width=True)


def _render_tax_efficiency(efficiency_data: dict):
    """Render tax efficiency metrics."""
    if not efficiency_data or 'error' in efficiency_data:
        st.info("No tax efficiency data available.")
        return
    
    st.markdown("### 📊 Tax Efficiency Analysis")
    
    turnover_analysis = efficiency_data.get('turnover_analysis', {})
    if turnover_analysis:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tax Efficiency Score", format_percent(turnover_analysis.get('tax_efficiency_score', 0)))
        with col2:
            st.metric("Annual Turnover", format_percent(turnover_analysis.get('annual_turnover', 0)))
        with col3:
            st.metric("Long-Term Trades", efficiency_data.get('long_term_trades', 0))
    
    # Holding periods
    holding_periods = efficiency_data.get('holding_periods', {})
    if holding_periods:
        stats = holding_periods.get('statistics', {})
        if stats:
            st.markdown("#### Holding Period Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Avg Holding Period", f"{stats.get('mean_holding_period_days', 0):.0f} days")
            with col2:
                st.metric("Median Holding Period", f"{stats.get('median_holding_period_days', 0):.0f} days")
            with col3:
                st.metric("Long-Term Rate", format_percent(
                    efficiency_data.get('long_term_trades', 0) / 
                    (efficiency_data.get('long_term_trades', 0) + efficiency_data.get('short_term_trades', 1))
                ))
