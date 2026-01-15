"""
Earnings Calendar Page
=======================
Display earnings calendar and portfolio exposure.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from ..components.sidebar import render_page_header
from ..data import load_runs
from ..utils import format_percent, format_number
from src.analytics.analysis_service import AnalysisService


def render_earnings_calendar():
    """Render earnings calendar page."""
    render_page_header("📅 Earnings Calendar", "Portfolio earnings exposure and impact analysis")
    
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
        key="earnings_calendar_run"
    )
    selected_run_id = run_options[selected_run_label]
    
    # Initialize service
    service = AnalysisService()
    
    # Load analysis results
    analysis_result = service.get_analysis_result(selected_run_id, 'earnings')
    
    if not analysis_result:
        st.info("No earnings analysis found. Run comprehensive analysis first.")
        if st.button("🔄 Run Analysis"):
            st.info("Go to Comprehensive Analysis page to run all analyses.")
        return
    
    results = analysis_result.get_results()
    
    if 'error' in results:
        st.error(f"Error: {results['error']}")
        return
    
    # Display exposure summary
    exposure = results.get('exposure', {})
    if exposure and 'error' not in exposure:
        st.markdown("### 📊 Earnings Exposure Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Upcoming Earnings", exposure.get('count', 0))
        with col2:
            st.metric("Total Exposure", format_percent(exposure.get('total_exposure', 0)))
        with col3:
            st.metric("Unique Tickers", exposure.get('unique_tickers', 0))
        with col4:
            st.metric("Next 7 Days", format_percent(exposure.get('exposure_by_period', {}).get('next_7_days', 0)))
    
    # Tabs
    tabs = st.tabs(["Upcoming Earnings", "Exposure Analysis", "Impact Analysis"])
    
    with tabs[0]:
        _render_upcoming_earnings(exposure)
    
    with tabs[1]:
        _render_exposure_analysis(exposure)
    
    with tabs[2]:
        _render_impact_analysis(results.get('impact', {}))


def _render_upcoming_earnings(exposure: dict):
    """Render upcoming earnings table."""
    if not exposure or 'error' in exposure:
        st.info("No earnings data available.")
        return
    
    upcoming = exposure.get('upcoming_earnings', [])
    if not upcoming:
        st.success("✅ No upcoming earnings in the next 30 days.")
        return
    
    df = pd.DataFrame(upcoming)
    st.markdown("#### Upcoming Earnings Announcements")
    st.dataframe(df, use_container_width=True)
    
    # Calendar view
    if 'earnings_date' in df.columns:
        df['earnings_date'] = pd.to_datetime(df['earnings_date'])
        df = df.sort_values('earnings_date')
        
        fig = px.scatter(
            df,
            x='earnings_date',
            y='weight',
            size='weight',
            color='ticker',
            title='Earnings Calendar',
            labels={'earnings_date': 'Date', 'weight': 'Portfolio Weight'}
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_exposure_analysis(exposure: dict):
    """Render exposure analysis."""
    if not exposure or 'error' in exposure:
        st.info("No exposure data available.")
        return
    
    exposure_by_ticker = exposure.get('exposure_by_ticker', {})
    if exposure_by_ticker:
        df = pd.DataFrame(list(exposure_by_ticker.items()), columns=['Ticker', 'Exposure'])
        df = df.sort_values('Exposure', ascending=False)
        
        st.markdown("#### Exposure by Ticker")
        st.dataframe(df, use_container_width=True)
        
        # Chart
        fig = px.bar(
            df,
            x='Ticker',
            y='Exposure',
            title='Earnings Exposure by Ticker',
            labels={'Exposure': 'Portfolio Weight (%)'}
        )
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    # Exposure by period
    exposure_by_period = exposure.get('exposure_by_period', {})
    if exposure_by_period:
        st.markdown("#### Exposure by Time Period")
        period_df = pd.DataFrame(list(exposure_by_period.items()), columns=['Period', 'Exposure'])
        st.dataframe(period_df, use_container_width=True, hide_index=True)


def _render_impact_analysis(impact: dict):
    """Render earnings impact analysis."""
    if not impact or 'error' in impact:
        st.info("No impact analysis available. Stock returns data needed.")
        return
    
    st.markdown("### 📈 Earnings Impact Analysis")
    
    aggregate = impact.get('aggregate_impact', {})
    if aggregate:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Events Analyzed", impact.get('earnings_events_analyzed', 0))
        with col2:
            st.metric("Avg Weighted Return", format_percent(aggregate.get('avg_weighted_return', 0)))
        with col3:
            st.metric("Win Rate", format_percent(aggregate.get('win_rate', 0)))
        with col4:
            st.metric("Total Impact", format_percent(aggregate.get('total_weighted_return', 0)))
    
    # By ticker
    by_ticker = impact.get('by_ticker', {})
    if by_ticker:
        st.markdown("#### Impact by Ticker")
        ticker_df = pd.DataFrame([
            {
                'Ticker': ticker,
                'Count': data.get('count', 0),
                'Avg Return': data.get('avg_return', 0),
                'Win Rate': data.get('win_rate', 0)
            }
            for ticker, data in by_ticker.items()
        ])
        st.dataframe(ticker_df, use_container_width=True)
