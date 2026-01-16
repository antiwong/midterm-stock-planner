"""
Enhanced Chart Components
==========================
Advanced visualizations: waterfall charts, heatmaps, comparison charts.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional


def create_attribution_waterfall(
    attribution_data: Dict[str, float],
    title: str = "Performance Attribution",
    height: int = 400
) -> go.Figure:
    """
    Create a waterfall chart for performance attribution.
    
    Args:
        attribution_data: Dictionary with attribution components
        title: Chart title
        height: Chart height
        
    Returns:
        Plotly figure
    """
    components = []
    values = []
    colors_list = []
    
    # Base
    components.append("Base")
    values.append(0)
    colors_list.append("rgba(0,0,0,0)")
    
    # Factor attribution
    if 'factor_attribution' in attribution_data:
        components.append("Factor")
        values.append(attribution_data['factor_attribution'] * 100)
        colors_list.append("#6366f1" if attribution_data['factor_attribution'] >= 0 else "#ef4444")
    
    # Sector attribution
    if 'sector_attribution' in attribution_data:
        components.append("Sector")
        values.append(attribution_data['sector_attribution'] * 100)
        colors_list.append("#8b5cf6" if attribution_data['sector_attribution'] >= 0 else "#ef4444")
    
    # Stock selection
    if 'stock_selection_attribution' in attribution_data:
        components.append("Stock Selection")
        values.append(attribution_data['stock_selection_attribution'] * 100)
        colors_list.append("#06b6d4" if attribution_data['stock_selection_attribution'] >= 0 else "#ef4444")
    
    # Timing
    if 'timing_attribution' in attribution_data:
        components.append("Timing")
        values.append(attribution_data['timing_attribution'] * 100)
        colors_list.append("#10b981" if attribution_data['timing_attribution'] >= 0 else "#ef4444")
    
    # Total
    total = sum(values)
    components.append("Total Return")
    values.append(total)
    colors_list.append("#1e1e2e")
    
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "relative", "total"],
        x=components,
        textposition="outside",
        text=[f"{v:.2f}%" if i > 0 and i < len(values)-1 else f"{v:.2f}%" for i, v in enumerate(values)],
        y=values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#10b981"}},
        decreasing={"marker": {"color": "#ef4444"}},
        totals={"marker": {"color": "#1e1e2e"}}
    ))
    
    fig.update_layout(
        title=title,
        height=height,
        showlegend=False,
        xaxis_title="Component",
        yaxis_title="Contribution (%)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1e1e2e")
    )
    
    return fig


def create_factor_exposure_heatmap(
    factor_exposures: Dict[str, Dict[str, float]],
    title: str = "Factor Exposure Heatmap",
    height: int = 400
) -> go.Figure:
    """
    Create a heatmap for factor exposures.
    
    Args:
        factor_exposures: Dictionary mapping factor names to exposure data
        title: Chart title
        height: Chart height
        
    Returns:
        Plotly figure
    """
    factors = list(factor_exposures.keys())
    metrics = ['exposure', 'contribution_to_return', 'contribution_to_risk']
    
    data = []
    for factor in factors:
        row = []
        for metric in metrics:
            value = factor_exposures[factor].get(metric, 0)
            if metric == 'exposure':
                row.append(value)
            elif metric == 'contribution_to_return':
                # Already in percentage from factor_exposure.py
                row.append(value)
            elif metric == 'contribution_to_risk':
                # Already in percentage from factor_exposure.py
                row.append(value)
            else:
                row.append(value * 100)  # Convert to percentage for other metrics
        data.append(row)
    
    fig = go.Figure(data=go.Heatmap(
        z=data,
        x=['Exposure', 'Return Contribution (%)', 'Risk Contribution (%)'],
        y=factors,
        colorscale='RdYlGn',
        zmid=0,
        text=[[f"{val:.3f}" if i == 0 else f"{val:.2f}%" for i, val in enumerate(row)] for row in data],
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="Value")
    ))
    
    fig.update_layout(
        title=title,
        height=height,
        xaxis_title="Metric",
        yaxis_title="Factor",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1e1e2e")
    )
    
    return fig


def create_comparison_chart(
    runs_data: List[Dict[str, Any]],
    metric: str = 'total_return',
    title: str = "Run Comparison",
    height: int = 400
) -> go.Figure:
    """
    Create a comparison chart for multiple runs.
    
    Args:
        runs_data: List of run dictionaries with metrics
        metric: Metric to compare
        title: Chart title
        height: Chart height
        
    Returns:
        Plotly figure
    """
    run_names = [r.get('name', r.get('run_id', 'Unknown'))[:20] for r in runs_data]
    values = [r.get(metric, 0) * 100 if metric in ['total_return', 'sharpe_ratio'] else r.get(metric, 0) 
              for r in runs_data]
    
    colors_list = ['#6366f1' if v >= 0 else '#ef4444' for v in values]
    
    fig = go.Figure(data=go.Bar(
        x=run_names,
        y=values,
        marker_color=colors_list,
        text=[f"{v:.2f}{'%' if metric in ['total_return'] else ''}" for v in values],
        textposition='outside'
    ))
    
    fig.update_layout(
        title=title,
        height=height,
        xaxis_title="Run",
        yaxis_title=metric.replace('_', ' ').title(),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1e1e2e"),
        xaxis=dict(tickangle=-45)
    )
    
    return fig


def create_multi_metric_comparison(
    runs_data: List[Dict[str, Any]],
    metrics: List[str],
    title: str = "Multi-Metric Comparison",
    height: int = 500
) -> go.Figure:
    """
    Create a radar/spider chart comparing multiple metrics across runs.
    
    Args:
        runs_data: List of run dictionaries
        metrics: List of metrics to compare
        title: Chart title
        height: Chart height
        
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    for run in runs_data:
        run_name = run.get('name', run.get('run_id', 'Unknown'))[:15]
        values = []
        for metric in metrics:
            value = run.get(metric, 0)
            # Normalize values to 0-100 scale for comparison
            if metric == 'total_return':
                values.append(value * 100)
            elif metric == 'sharpe_ratio':
                values.append(value * 20)  # Scale Sharpe ratio
            elif metric == 'max_drawdown':
                values.append(abs(value) * 100)
            else:
                values.append(value)
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=metrics,
            fill='toself',
            name=run_name
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=True,
        title=title,
        height=height,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1e1e2e")
    )
    
    return fig


def create_time_period_comparison(
    returns_data: Dict[str, pd.Series],
    title: str = "Time Period Comparison",
    height: int = 400
) -> go.Figure:
    """
    Compare performance across different time periods.
    
    Args:
        returns_data: Dictionary mapping period names to return series
        title: Chart title
        height: Chart height
        
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    for period_name, returns in returns_data.items():
        cumulative = (1 + returns).cumprod()
        fig.add_trace(go.Scatter(
            x=cumulative.index,
            y=cumulative.values,
            mode='lines',
            name=period_name,
            line=dict(width=2)
        ))
    
    fig.update_layout(
        title=title,
        height=height,
        xaxis_title="Date",
        yaxis_title="Cumulative Return",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1e1e2e"),
        hovermode='x unified'
    )
    
    return fig
