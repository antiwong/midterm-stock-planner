"""
Recommendation Tracking Page
============================
View and track AI recommendation performance over time.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

from ..components.sidebar import render_page_header, render_section_header
from ..data import load_runs
from ..utils import format_percent, format_number
from src.analytics.recommendation_tracker import RecommendationTracker
from src.analytics.models import get_db, Run
from src.analytics.analysis_models import Recommendation


def render_recommendation_tracking():
    """Render the recommendation tracking page."""
    render_page_header(
        "📊 Recommendation Performance Tracking",
        "Track AI recommendation performance over time"
    )
    
    tracker = RecommendationTracker()
    
    # Run selector
    runs = load_runs()
    completed_runs = [r for r in runs if r['status'] == 'completed']
    
    if not completed_runs:
        st.warning("No completed runs found. Run an analysis first!")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_run_id = st.selectbox(
            "Select Analysis Run",
            options=[None] + [r['run_id'] for r in completed_runs],
            format_func=lambda x: "All Runs" if x is None else f"{x[:12]}... - {next((r.get('name') or 'Unnamed' for r in completed_runs if r['run_id'] == x), 'Unknown')}",
            key="rec_tracking_run"
        )
    
    with col2:
        min_days = st.number_input(
            "Min Days Old",
            min_value=1,
            max_value=365,
            value=7,
            help="Only show recommendations older than this many days"
        )
    
    # Action filter
    action_filter = st.radio(
        "Action Type",
        ["All", "BUY", "SELL", "HOLD", "AVOID"],
        horizontal=True,
        key="rec_tracking_action"
    )
    
    # Update recommendations button
    if st.button("🔄 Update All Recommendations", use_container_width=True):
        with st.spinner("Updating recommendation performance..."):
            summary = tracker.update_all_recommendations(
                run_id=selected_run_id,
                days_old=1
            )
            st.success(f"Updated {summary['updated']} recommendations. Average return: {summary['avg_return']*100:.2f}%")
            st.rerun()
    
    st.markdown("---")
    
    # Performance summary
    _render_performance_summary(tracker, selected_run_id, action_filter, min_days)
    
    st.markdown("---")
    
    # Detailed recommendations
    _render_detailed_recommendations(tracker, selected_run_id, action_filter, min_days)
    
    st.markdown("---")
    
    # Performance charts
    _render_performance_charts(tracker, selected_run_id, action_filter, min_days)


def _render_performance_summary(
    tracker: RecommendationTracker,
    run_id: Optional[str],
    action: str,
    min_days: int
):
    """Render performance summary metrics."""
    render_section_header("Performance Summary", "📊")
    
    action_filter = None if action == "All" else action
    summary = tracker.get_recommendation_performance_summary(
        run_id=run_id,
        action=action_filter,
        min_days_old=min_days
    )
    
    if summary['total'] == 0:
        st.info("No recommendations found matching criteria.")
        return
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Recommendations", summary['total'])
    
    with col2:
        st.metric("With Tracking", summary['with_tracking'])
    
    with col3:
        st.metric(
            "Avg Return",
            f"{summary['avg_return']*100:+.2f}%",
            delta=f"{summary['median_return']*100:+.2f}% median"
        )
    
    with col4:
        st.metric("Win Rate", f"{summary['win_rate']*100:.1f}%")
    
    with col5:
        st.metric("Hit Target Rate", f"{summary['hit_target_rate']*100:.1f}%")
    
    if summary['with_tracking'] > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Best Return", f"{summary['best_return']*100:+.2f}%")
        
        with col2:
            st.metric("Worst Return", f"{summary['worst_return']*100:+.2f}%")
        
        if summary['hit_stop_loss_rate'] > 0:
            st.warning(f"⚠️ {summary['hit_stop_loss_rate']*100:.1f}% of recommendations hit stop loss")


def _render_detailed_recommendations(
    tracker: RecommendationTracker,
    run_id: Optional[str],
    action: str,
    min_days: int
):
    """Render detailed recommendations table."""
    render_section_header("Detailed Recommendations", "📋")
    
    action_filter = None if action == "All" else action
    
    # Get recommendations
    db = get_db()
    session = db.get_session()
    try:
        query = session.query(Recommendation)
        
        if run_id:
            query = query.filter_by(run_id=run_id)
        
        if action_filter:
            query = query.filter_by(action=action_filter)
        
        cutoff_date = datetime.now() - timedelta(days=min_days)
        query = query.filter(Recommendation.recommendation_date <= cutoff_date)
        query = query.order_by(Recommendation.recommendation_date.desc())
        
        recommendations = query.limit(100).all()
        
        if not recommendations:
            st.info("No recommendations found.")
            return
        
        # Convert to DataFrame
        data = []
        for rec in recommendations:
            data.append({
                'Ticker': rec.ticker,
                'Action': rec.action,
                'Date': rec.recommendation_date.strftime('%Y-%m-%d') if rec.recommendation_date else 'N/A',
                'Price': f"${rec.current_price:.2f}" if rec.current_price else 'N/A',
                'Target': f"${rec.target_price:.2f}" if rec.target_price else 'N/A',
                'Return': f"{rec.actual_return*100:+.2f}%" if rec.actual_return is not None else "N/A",
                'Hit Target': "✅" if rec.hit_target else "❌" if rec.hit_target is False else "—",
                'Confidence': f"{rec.confidence*100:.0f}%" if rec.confidence else 'N/A',
            })
        
        df = pd.DataFrame(data)
        
        # Filter by return if needed
        return_filter = st.selectbox(
            "Filter by Performance",
            ["All", "Winners (>0%)", "Losers (<0%)", "Top 10%", "Bottom 10%"],
            key="rec_return_filter"
        )
        
        if return_filter == "Winners (>0%)":
            df = df[df['Return'].str.contains(r'\+', na=False)]
        elif return_filter == "Losers (<0%)":
            df = df[df['Return'].str.contains(r'\-', na=False) & ~df['Return'].str.contains('N/A')]
        elif return_filter == "Top 10%":
            # This would need actual return values, simplified for now
            pass
        elif return_filter == "Bottom 10%":
            pass
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    finally:
        session.close()


def _render_performance_charts(
    tracker: RecommendationTracker,
    run_id: Optional[str],
    action: str,
    min_days: int
):
    """Render performance charts."""
    render_section_header("Performance Charts", "📈")
    
    action_filter = None if action == "All" else action
    
    # Get recommendations with returns
    db = get_db()
    session = db.get_session()
    try:
        query = session.query(Recommendation)
        
        if run_id:
            query = query.filter_by(run_id=run_id)
        
        if action_filter:
            query = query.filter_by(action=action_filter)
        
        cutoff_date = datetime.now() - timedelta(days=min_days)
        query = query.filter(Recommendation.recommendation_date <= cutoff_date)
        query = query.filter(Recommendation.actual_return.isnot(None))
        query = query.order_by(Recommendation.recommendation_date)
        
        recommendations = query.all()
        
        if not recommendations:
            st.info("No recommendations with tracking data found.")
            return
        
        # Prepare data
        returns = [r.actual_return * 100 for r in recommendations]
        dates = [r.recommendation_date for r in recommendations]
        actions = [r.action for r in recommendations]
        
        # Return distribution
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Return Distribution")
            fig = px.histogram(
                x=returns,
                nbins=30,
                labels={'x': 'Return (%)', 'y': 'Count'},
                title="Distribution of Recommendation Returns"
            )
            fig.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Break Even")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### Returns Over Time")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates,
                y=returns,
                mode='markers',
                marker=dict(
                    size=8,
                    color=returns,
                    colorscale='RdYlGn',
                    showscale=True,
                    colorbar=dict(title="Return %")
                ),
                text=[f"{r.ticker}: {r.actual_return*100:.1f}%" for r in recommendations],
                hovertemplate='%{text}<br>Date: %{x}<br>Return: %{y:.2f}%<extra></extra>'
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="red")
            fig.update_layout(
                title="Recommendation Returns Over Time",
                xaxis_title="Date",
                yaxis_title="Return (%)",
                hovermode='closest'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Performance by action type
        if len(set(actions)) > 1:
            st.markdown("### Performance by Action Type")
            action_data = pd.DataFrame({
                'Action': actions,
                'Return': returns
            })
            
            fig = px.box(
                action_data,
                x='Action',
                y='Return',
                title="Return Distribution by Action Type"
            )
            fig.add_hline(y=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)
        
    finally:
        session.close()
