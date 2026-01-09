"""
Chart Components
================
Reusable chart components using Plotly.
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Optional, List, Dict

from ..config import COLORS, CHART_COLORS


def get_chart_template() -> dict:
    """Get consistent chart template."""
    return {
        'layout': {
            'font': {'family': 'Inter, sans-serif'},
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'colorway': CHART_COLORS['categorical'],
            'margin': {'t': 40, 'b': 40, 'l': 40, 'r': 40},
        }
    }


def create_equity_curve(
    dates: List,
    values: List[float],
    benchmark: Optional[List[float]] = None,
    title: str = "Portfolio Value",
    height: int = 400
) -> go.Figure:
    """Create an equity curve chart.
    
    Args:
        dates: List of dates
        values: Portfolio values
        benchmark: Optional benchmark values
        title: Chart title
        height: Chart height
    
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    # Portfolio line
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        name='Portfolio',
        mode='lines',
        line=dict(color=COLORS['primary'], width=2.5),
        fill='tozeroy',
        fillcolor=f'rgba(99, 102, 241, 0.1)'
    ))
    
    # Benchmark line
    if benchmark:
        fig.add_trace(go.Scatter(
            x=dates,
            y=benchmark,
            name='Benchmark',
            mode='lines',
            line=dict(color=COLORS['muted'], width=1.5, dash='dot')
        ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['dark'])),
        xaxis_title='Date',
        yaxis_title='Value',
        height=height,
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        **get_chart_template()['layout']
    )
    
    fig.update_xaxes(gridcolor='rgba(0,0,0,0.05)', showgrid=True)
    fig.update_yaxes(gridcolor='rgba(0,0,0,0.05)', showgrid=True, tickformat='$,.0f')
    
    return fig


def create_returns_chart(
    dates: List,
    returns: List[float],
    cumulative: bool = True,
    title: str = "Returns",
    height: int = 400
) -> go.Figure:
    """Create a returns chart.
    
    Args:
        dates: List of dates
        returns: Return values
        cumulative: Whether to show cumulative returns
        title: Chart title
        height: Chart height
    
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    if cumulative:
        cum_returns = pd.Series(returns).add(1).cumprod().subtract(1).tolist()
        fig.add_trace(go.Scatter(
            x=dates,
            y=[r * 100 for r in cum_returns],
            name='Cumulative Return',
            mode='lines',
            line=dict(color=COLORS['primary'], width=2.5),
            fill='tozeroy',
            fillcolor=f'rgba(99, 102, 241, 0.1)'
        ))
        yaxis_title = 'Cumulative Return (%)'
    else:
        colors = [COLORS['success'] if r >= 0 else COLORS['danger'] for r in returns]
        fig.add_trace(go.Bar(
            x=dates,
            y=[r * 100 for r in returns],
            name='Return',
            marker_color=colors
        ))
        yaxis_title = 'Return (%)'
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['dark'])),
        xaxis_title='Date',
        yaxis_title=yaxis_title,
        height=height,
        **get_chart_template()['layout']
    )
    
    fig.update_xaxes(gridcolor='rgba(0,0,0,0.05)')
    fig.update_yaxes(gridcolor='rgba(0,0,0,0.05)', ticksuffix='%')
    
    return fig


def create_sector_pie(
    sectors: Dict[str, float],
    title: str = "Sector Allocation",
    height: int = 350,
    hole: float = 0.4
) -> go.Figure:
    """Create a sector allocation pie chart.
    
    Args:
        sectors: Dictionary of {sector: weight}
        title: Chart title
        height: Chart height
        hole: Donut hole size (0-1)
    
    Returns:
        Plotly figure
    """
    labels = list(sectors.keys())
    values = list(sectors.values())
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=hole,
        marker=dict(colors=CHART_COLORS['categorical']),
        textinfo='label+percent',
        textposition='outside',
        textfont=dict(size=11),
        hovertemplate='<b>%{label}</b><br>Weight: %{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['dark'])),
        height=height,
        showlegend=False,
        **get_chart_template()['layout']
    )
    
    return fig


def create_score_distribution(
    scores: List[float],
    bins: int = 20,
    title: str = "Score Distribution",
    height: int = 300
) -> go.Figure:
    """Create a score distribution histogram.
    
    Args:
        scores: List of scores
        bins: Number of histogram bins
        title: Chart title
        height: Chart height
    
    Returns:
        Plotly figure
    """
    fig = go.Figure(data=[go.Histogram(
        x=scores,
        nbinsx=bins,
        marker_color=COLORS['primary'],
        opacity=0.8,
        hovertemplate='Score Range: %{x}<br>Count: %{y}<extra></extra>'
    )])
    
    # Add mean line
    mean_score = np.mean(scores)
    fig.add_vline(
        x=mean_score,
        line_dash='dash',
        line_color=COLORS['accent'],
        annotation_text=f'Mean: {mean_score:.1f}',
        annotation_position='top'
    )
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['dark'])),
        xaxis_title='Score',
        yaxis_title='Count',
        height=height,
        bargap=0.1,
        **get_chart_template()['layout']
    )
    
    fig.update_xaxes(gridcolor='rgba(0,0,0,0.05)')
    fig.update_yaxes(gridcolor='rgba(0,0,0,0.05)')
    
    return fig


def create_performance_bar(
    runs: List[Dict],
    metric: str = 'total_return',
    title: str = "Performance Comparison",
    height: int = 400
) -> go.Figure:
    """Create a performance comparison bar chart.
    
    Args:
        runs: List of run dictionaries
        metric: Metric to compare
        title: Chart title
        height: Chart height
    
    Returns:
        Plotly figure
    """
    # Filter runs with valid metric
    valid_runs = [r for r in runs if r.get(metric) is not None]
    
    if not valid_runs:
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig
    
    names = [r.get('name') or r['run_id'][:8] for r in valid_runs]
    values = [r[metric] * 100 if metric in ['total_return', 'win_rate', 'max_drawdown'] else r[metric] for r in valid_runs]
    
    colors = [COLORS['success'] if v >= 0 else COLORS['danger'] for v in values]
    
    fig = go.Figure(data=[go.Bar(
        x=names,
        y=values,
        marker_color=colors,
        text=[f'{v:.1f}%' if metric in ['total_return', 'win_rate', 'max_drawdown'] else f'{v:.2f}' for v in values],
        textposition='outside'
    )])
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['dark'])),
        xaxis_title='Run',
        yaxis_title=metric.replace('_', ' ').title(),
        height=height,
        **get_chart_template()['layout']
    )
    
    fig.update_xaxes(gridcolor='rgba(0,0,0,0.05)')
    fig.update_yaxes(gridcolor='rgba(0,0,0,0.05)')
    
    return fig


def create_correlation_heatmap(
    correlation_matrix: pd.DataFrame,
    title: str = "Correlation Matrix",
    height: int = 500
) -> go.Figure:
    """Create a correlation heatmap.
    
    Args:
        correlation_matrix: Pandas DataFrame with correlation values
        title: Chart title
        height: Chart height
    
    Returns:
        Plotly figure
    """
    fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix.values,
        x=correlation_matrix.columns,
        y=correlation_matrix.index,
        colorscale='RdYlGn',
        zmid=0,
        text=correlation_matrix.round(2).values,
        texttemplate='%{text}',
        textfont=dict(size=10),
        hovertemplate='%{x} vs %{y}<br>Correlation: %{z:.3f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['dark'])),
        height=height,
        xaxis=dict(side='bottom'),
        **get_chart_template()['layout']
    )
    
    return fig


def create_scatter_plot(
    x: List[float],
    y: List[float],
    labels: Optional[List[str]] = None,
    colors: Optional[List[str]] = None,
    x_title: str = "X",
    y_title: str = "Y",
    title: str = "Scatter Plot",
    height: int = 400
) -> go.Figure:
    """Create a scatter plot.
    
    Args:
        x: X values
        y: Y values
        labels: Point labels for hover
        colors: Color for each point (categorical)
        x_title: X axis title
        y_title: Y axis title
        title: Chart title
        height: Chart height
    
    Returns:
        Plotly figure
    """
    fig = px.scatter(
        x=x,
        y=y,
        color=colors,
        hover_name=labels,
        color_discrete_sequence=CHART_COLORS['categorical']
    )
    
    fig.update_traces(
        marker=dict(size=10, opacity=0.7, line=dict(width=1, color='white'))
    )
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['dark'])),
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=height,
        **get_chart_template()['layout']
    )
    
    fig.update_xaxes(gridcolor='rgba(0,0,0,0.05)')
    fig.update_yaxes(gridcolor='rgba(0,0,0,0.05)')
    
    return fig


def create_weight_bar(
    tickers: List[str],
    weights: List[float],
    title: str = "Portfolio Weights",
    height: int = 400,
    orientation: str = 'h'
) -> go.Figure:
    """Create a portfolio weights bar chart.
    
    Args:
        tickers: List of ticker symbols
        weights: List of weights
        title: Chart title
        height: Chart height
        orientation: 'h' for horizontal, 'v' for vertical
    
    Returns:
        Plotly figure
    """
    # Sort by weight
    sorted_pairs = sorted(zip(tickers, weights), key=lambda x: x[1], reverse=True)
    tickers_sorted = [p[0] for p in sorted_pairs]
    weights_sorted = [p[1] for p in sorted_pairs]
    
    if orientation == 'h':
        fig = go.Figure(data=[go.Bar(
            y=tickers_sorted,
            x=weights_sorted,
            orientation='h',
            marker_color=COLORS['primary'],
            text=[f'{w*100:.1f}%' for w in weights_sorted],
            textposition='outside'
        )])
        fig.update_layout(
            xaxis_title='Weight',
            yaxis=dict(autorange='reversed')
        )
        fig.update_xaxes(tickformat='.0%')
    else:
        fig = go.Figure(data=[go.Bar(
            x=tickers_sorted,
            y=weights_sorted,
            marker_color=COLORS['primary'],
            text=[f'{w*100:.1f}%' for w in weights_sorted],
            textposition='outside'
        )])
        fig.update_layout(yaxis_title='Weight')
        fig.update_yaxes(tickformat='.0%')
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['dark'])),
        height=height,
        **get_chart_template()['layout']
    )
    
    return fig


def create_drawdown_chart(
    dates: List,
    drawdowns: List[float],
    title: str = "Drawdown",
    height: int = 300
) -> go.Figure:
    """Create a drawdown chart.
    
    Args:
        dates: List of dates
        drawdowns: Drawdown values (negative)
        title: Chart title
        height: Chart height
    
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=[d * 100 for d in drawdowns],
        mode='lines',
        fill='tozeroy',
        fillcolor='rgba(239, 68, 68, 0.2)',
        line=dict(color=COLORS['danger'], width=1.5),
        hovertemplate='Date: %{x}<br>Drawdown: %{y:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['dark'])),
        xaxis_title='Date',
        yaxis_title='Drawdown (%)',
        height=height,
        **get_chart_template()['layout']
    )
    
    fig.update_xaxes(gridcolor='rgba(0,0,0,0.05)')
    fig.update_yaxes(gridcolor='rgba(0,0,0,0.05)', ticksuffix='%')
    
    return fig
