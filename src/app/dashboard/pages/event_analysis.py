"""
Event-Driven Analysis Page
==========================
Display event-driven analysis results.
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


def render_event_analysis():
    """Render event-driven analysis page."""
    render_page_header("Event-Driven Analysis", "Analyze portfolio performance around market events")
    
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
        key="event_analysis_run"
    )
    selected_run_id = run_options[selected_run_label]
    
    # Initialize service
    service = AnalysisService()
    
    # Load analysis results
    analysis_result = service.get_analysis_result(selected_run_id, 'event_analysis')
    
    if not analysis_result:
        st.info("No event analysis found. Run comprehensive analysis first.")
        if st.button("🔄 Run Analysis"):
            st.info("Go to Comprehensive Analysis page to run all analyses.")
        return
    
    results = analysis_result.get_results()
    
    if 'error' in results:
        st.error(f"Error: {results['error']}")
        return
    
    # Display results
    st.markdown("### 📊 Event Analysis Summary")
    
    summary = results.get('summary', {})
    if summary:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Events", summary.get('total_events_analyzed', 0))
        with col2:
            st.metric("Avg Event Return", format_percent(summary.get('avg_event_return', 0)))
        with col3:
            st.metric("Win Rate", format_percent(summary.get('win_rate', 0)))
        with col4:
            st.metric("Avg Excess Return", format_percent(summary.get('avg_excess_return', 0)))
    
    # Tabs for different event types
    tabs = st.tabs(["Fed Meetings", "Earnings", "Macro Data", "All Events"])
    
    with tabs[0]:
        _render_event_type(results.get('fed_meetings', {}), "Federal Reserve Meetings")
    
    with tabs[1]:
        _render_event_type(results.get('earnings', {}), "Earnings Announcements")
    
    with tabs[2]:
        _render_event_type(results.get('macro_data', {}), "Macroeconomic Data Releases")
    
    with tabs[3]:
        _render_all_events(results)


def _render_event_type(event_data: dict, title: str):
    """Render analysis for a specific event type."""
    if not event_data or 'error' in event_data:
        st.info(f"No {title.lower()} data available.")
        return
    
    st.markdown(f"### {title}")
    
    summary = event_data.get('summary', {})
    if summary:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Events Analyzed", event_data.get('events_analyzed', 0))
        with col2:
            st.metric("Avg Return", format_percent(summary.get('avg_return', 0)))
        with col3:
            st.metric("Win Rate", format_percent(summary.get('win_rate', 0)))
    
    # Event performance table
    event_performance = event_data.get('event_performance', [])
    if event_performance:
        df = pd.DataFrame(event_performance)
        st.markdown("#### Event Performance Details")
        st.dataframe(df, use_container_width=True)
        
        # Chart
        if 'cumulative_return' in df.columns:
            fig = px.bar(
                df,
                x='event_date',
                y='cumulative_return',
                title='Event Returns',
                labels={'cumulative_return': 'Return', 'event_date': 'Event Date'}
            )
            fig.update_traces(marker_color='#6366f1')
            st.plotly_chart(fig, use_container_width=True)


def _render_all_events(results: dict):
    """Render combined view of all events."""
    st.markdown("### Combined Event Analysis")
    
    all_events = []
    for event_type in ['fed_meetings', 'earnings', 'macro_data']:
        event_data = results.get(event_type, {})
        if event_data and 'event_performance' in event_data:
            for event in event_data['event_performance']:
                event['event_type'] = event_type.replace('_', ' ').title()
                all_events.append(event)
    
    if all_events:
        df = pd.DataFrame(all_events)
        
        # Summary by event type
        summary_df = df.groupby('event_type').agg({
            'cumulative_return': ['mean', 'count']
        }).round(4)
        st.dataframe(summary_df, use_container_width=True)
        
        # Distribution chart
        fig = px.histogram(
            df,
            x='cumulative_return',
            color='event_type',
            title='Return Distribution by Event Type',
            nbins=30
        )
        st.plotly_chart(fig, use_container_width=True)
