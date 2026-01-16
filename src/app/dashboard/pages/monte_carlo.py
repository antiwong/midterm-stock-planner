"""
Monte Carlo Simulation Page
============================
Display Monte Carlo simulation results and risk metrics.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from ..components.sidebar import render_page_header
from ..data import load_runs
from ..utils import format_percent, format_number
from src.analytics.analysis_service import AnalysisService


def render_monte_carlo():
    """Render Monte Carlo simulation page."""
    render_page_header("Monte Carlo Simulation", "Portfolio risk analysis and scenario modeling")
    
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
        key="monte_carlo_run"
    )
    selected_run_id = run_options[selected_run_label]
    
    # Initialize service
    service = AnalysisService()
    
    # Load analysis results
    analysis_result = service.get_analysis_result(selected_run_id, 'monte_carlo')
    
    if not analysis_result:
        st.info("No Monte Carlo simulation found. Run comprehensive analysis first.")
        if st.button("🔄 Run Analysis"):
            st.info("Go to Comprehensive Analysis page to run all analyses.")
        return
    
    results = analysis_result.get_results()
    
    if 'error' in results:
        st.error(f"Error: {results['error']}")
        return
    
    # Display key metrics
    st.markdown("### 📊 Simulation Results")
    
    sim_stats = results.get('simulation_stats', {})
    if sim_stats:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Expected Return", format_percent(sim_stats.get('mean', 0)))
        with col2:
            st.metric("Median Return", format_percent(sim_stats.get('median', 0)))
        with col3:
            st.metric("Std Deviation", format_percent(sim_stats.get('std', 0)))
        with col4:
            st.metric("Simulations", results.get('num_simulations', 0))
    
    # Tabs
    tabs = st.tabs(["Risk Metrics", "Confidence Intervals", "Probabilities", "Value at Risk"])
    
    with tabs[0]:
        _render_risk_metrics(results)
    
    with tabs[1]:
        _render_confidence_intervals(results)
    
    with tabs[2]:
        _render_probabilities(results)
    
    with tabs[3]:
        _render_var(results)


def _render_risk_metrics(results: dict):
    """Render risk metrics."""
    sim_stats = results.get('simulation_stats', {})
    
    if sim_stats:
        st.markdown("#### Risk Statistics")
        
        metrics_df = pd.DataFrame([{
            'Metric': 'Min Return',
            'Value': format_percent(sim_stats.get('min', 0))
        }, {
            'Metric': 'Max Return',
            'Value': format_percent(sim_stats.get('max', 0))
        }, {
            'Metric': '5th Percentile',
            'Value': format_percent(sim_stats.get('percentile_5', 0))
        }, {
            'Metric': '95th Percentile',
            'Value': format_percent(sim_stats.get('percentile_95', 0))
        }])
        
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)


def _render_confidence_intervals(results: dict):
    """Render confidence intervals."""
    ci = results.get('confidence_intervals', {})
    
    if ci:
        st.markdown("#### Confidence Intervals")
        
        intervals_df = pd.DataFrame([
            {
                'Confidence Level': '90%',
                'Lower Bound': format_percent(ci.get('90_pct', [0, 0])[0]),
                'Upper Bound': format_percent(ci.get('90_pct', [0, 0])[1])
            },
            {
                'Confidence Level': '95%',
                'Lower Bound': format_percent(ci.get('95_pct', [0, 0])[0]),
                'Upper Bound': format_percent(ci.get('95_pct', [0, 0])[1])
            },
            {
                'Confidence Level': '99%',
                'Lower Bound': format_percent(ci.get('99_pct', [0, 0])[0]),
                'Upper Bound': format_percent(ci.get('99_pct', [0, 0])[1])
            }
        ])
        
        st.dataframe(intervals_df, use_container_width=True, hide_index=True)
        
        # Visualize
        fig = go.Figure()
        for level, bounds in ci.items():
            level_pct = level.replace('_pct', '').replace('_', '')
            fig.add_trace(go.Bar(
                x=[level_pct],
                y=[bounds[1] - bounds[0]],
                base=bounds[0],
                name=level_pct,
                text=[f"{format_percent(bounds[0])} to {format_percent(bounds[1])}"],
                textposition='auto'
            ))
        
        fig.update_layout(
            title='Confidence Intervals',
            xaxis_title='Confidence Level',
            yaxis_title='Return Range',
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_probabilities(results: dict):
    """Render probability metrics."""
    probs = results.get('probability_metrics', {})
    
    if probs:
        st.markdown("#### Probability Metrics")
        
        prob_df = pd.DataFrame([
            {'Metric': 'Probability of Positive Return', 'Value': format_percent(probs.get('prob_positive_return', 0))},
            {'Metric': 'Probability of Negative Return', 'Value': format_percent(probs.get('prob_negative_return', 0))},
            {'Metric': 'Probability > 10%', 'Value': format_percent(probs.get('prob_exceed_10pct', 0))},
            {'Metric': 'Probability > 20%', 'Value': format_percent(probs.get('prob_exceed_20pct', 0))},
            {'Metric': 'Probability Loss > 10%', 'Value': format_percent(probs.get('prob_loss_exceed_10pct', 0))},
            {'Metric': 'Probability Loss > 20%', 'Value': format_percent(probs.get('prob_loss_exceed_20pct', 0))},
        ])
        
        st.dataframe(prob_df, use_container_width=True, hide_index=True)
        
        # Chart
        fig = px.bar(
            prob_df,
            x='Metric',
            y='Value',
            title='Probability Metrics',
            labels={'Value': 'Probability'}
        )
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)


def _render_var(results: dict):
    """Render Value at Risk metrics."""
    var = results.get('value_at_risk', {})
    cvar = results.get('conditional_var', {})
    
    if var:
        st.markdown("#### Value at Risk (VaR)")
        
        var_df = pd.DataFrame([
            {
                'Confidence Level': '90%',
                'VaR': format_percent(var.get('var_90', 0)),
                'CVaR': format_percent(cvar.get('cvar_90', 0))
            },
            {
                'Confidence Level': '95%',
                'VaR': format_percent(var.get('var_95', 0)),
                'CVaR': format_percent(cvar.get('cvar_95', 0))
            },
            {
                'Confidence Level': '99%',
                'VaR': format_percent(var.get('var_99', 0)),
                'CVaR': format_percent(cvar.get('cvar_99', 0))
            }
        ])
        
        st.dataframe(var_df, use_container_width=True, hide_index=True)
        
        # Chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=var_df['Confidence Level'],
            y=var_df['VaR'].str.rstrip('%').astype(float),
            name='VaR',
            marker_color='#ef4444'
        ))
        fig.add_trace(go.Bar(
            x=var_df['Confidence Level'],
            y=var_df['CVaR'].str.rstrip('%').astype(float),
            name='CVaR',
            marker_color='#dc2626'
        ))
        
        fig.update_layout(
            title='Value at Risk (VaR) and Conditional VaR',
            xaxis_title='Confidence Level',
            yaxis_title='Return (%)',
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)
