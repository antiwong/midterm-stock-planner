"""
Portfolio Analysis Page
=======================
Comprehensive portfolio analysis with stunning visualizations.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from ..components.sidebar import render_page_header, render_section_header
from ..components.metrics import render_metric_card, render_kpi_summary
from ..components.charts import (
    create_sector_pie, create_weight_bar, create_equity_curve,
    create_returns_chart, create_score_distribution, create_drawdown_chart,
    create_scatter_plot, create_performance_bar, get_chart_template
)
from ..components.tables import render_portfolio_table
from ..components.cards import render_info_card, render_stock_card
from ..data import (
    load_runs, load_run_scores, load_backtest_returns, load_backtest_positions,
    load_horizontal_portfolio, load_ai_recommendations, get_run_folder
)
from ..utils import format_percent, format_number
from ..config import COLORS

# Custom color palette for beautiful charts
CHART_COLORS = {
    'primary': '#6366f1',      # Indigo
    'secondary': '#8b5cf6',    # Purple  
    'accent': '#06b6d4',       # Cyan
    'success': '#10b981',      # Emerald
    'warning': '#f59e0b',      # Amber
    'danger': '#ef4444',       # Red
    'dark': '#1e1e2e',
    'light': '#f8fafc',
    'muted': '#94a3b8',
}

HEATMAP_SCALE = [
    [0, '#ef4444'],
    [0.5, '#1e1e2e'],
    [1, '#10b981']
]


def render_portfolio_analysis():
    """Render the portfolio analysis page."""
    # Use standard page header
    render_page_header("Portfolio Analysis", "Comprehensive insights and performance metrics")
    
    runs = load_runs()
    completed_runs = [r for r in runs if r['status'] == 'completed']
    
    if not completed_runs:
        st.warning("No completed runs found. Run an analysis first!")
        return
    
    # Run selector
    def format_run(run_id):
        run = next((r for r in completed_runs if r['run_id'] == run_id), None)
        if not run:
            return run_id[:12]
        name = run.get('name') or 'Unnamed'
        watchlist = run.get('watchlist_display_name') or run.get('watchlist')
        if watchlist:
            return f"[{watchlist}] {name}"
        return name
    
    selected_run_id = st.selectbox(
        "Select Analysis Run",
        options=[r['run_id'] for r in completed_runs],
        format_func=format_run,
        key="portfolio_run_selector",
        help="Pick a completed run to explore portfolio metrics and charts"
    )
    
    if not selected_run_id:
        return
    
    run = next((r for r in completed_runs if r['run_id'] == selected_run_id), None)
    
    # Key metrics section using standard components
    _render_key_metrics(run)
    
    # Tabs for different views
    tabs = st.tabs([
        "Overview", 
        "Performance", 
        "Sectors", 
        "Risk", 
        "Holdings",
        "AI Analysis"
    ])
    
    with tabs[0]:
        _render_overview_tab(run, selected_run_id)
    
    with tabs[1]:
        _render_performance_tab(run, selected_run_id)
    
    with tabs[2]:
        _render_sector_tab(selected_run_id)
    
    with tabs[3]:
        _render_risk_tab(run, selected_run_id)
    
    with tabs[4]:
        _render_holdings_tab(selected_run_id)
    
    with tabs[5]:
        _render_ai_tab(selected_run_id)


def _render_key_metrics(run: dict):
    """Render key metrics using standard components."""
    total_return = run.get('total_return', 0) or 0
    sharpe = run.get('sharpe_ratio', 0) or 0
    win_rate = run.get('win_rate', 0) or 0
    max_dd = run.get('max_drawdown', 0) or 0
    
    # Use standard metric cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_metric_card(
            label="Total Return",
            value=format_percent(total_return),
            delta=None,
            help_text="Total portfolio return over the analysis period"
        )
    
    with col2:
        render_metric_card(
            label="Sharpe Ratio",
            value=format_number(sharpe, decimals=2),
            delta=None,
            help_text="Risk-adjusted return metric"
        )
    
    with col3:
        render_metric_card(
            label="Win Rate",
            value=format_percent(win_rate),
            delta=None,
            help_text="Percentage of winning periods"
        )
    
    with col4:
        render_metric_card(
            label="Max Drawdown",
            value=format_percent(max_dd),
            delta=None,
            help_text="Maximum peak-to-trough decline"
        )


def _render_overview_tab(run: dict, run_id: str):
    """Render overview tab with portfolio details, charts, and AI insights."""
    
    returns_df = load_backtest_returns(run_id)
    scores = load_run_scores(run_id)
    scores_df = pd.DataFrame(scores) if scores else pd.DataFrame()
    
    # ==========================================
    # PORTFOLIO DETAILS PANEL
    # ==========================================
    _render_portfolio_details_panel(run, scores_df)
    
    st.markdown("---")
    
    # ==========================================
    # HOLDINGS LIST
    # ==========================================
    _render_holdings_pills(scores_df)
    
    st.markdown("---")
    
    # ==========================================
    # CHARTS WITH INSIGHTS (Lazy Loaded)
    # ==========================================
    
    # Chart loading mode selector
    default_lazy = False
    if returns_df is not None and not returns_df.empty and len(returns_df) > 800:
        default_lazy = True
    if scores_df is not None and not scores_df.empty and len(scores_df) > 200:
        default_lazy = True

    chart_options = ["All Charts", "Lazy Load"]
    chart_mode = st.radio(
        "Chart Loading Mode",
        chart_options,
        horizontal=True,
        index=1 if default_lazy else 0,
        key=f"chart_mode_{run_id}",
        help="Lazy Load renders charts on demand for faster performance"
    )
    
    if chart_mode == "All Charts":
        # Load all charts immediately
        _render_all_charts(returns_df, scores_df, run, run_id)
    else:
        # Lazy load charts
        _render_lazy_charts(returns_df, scores_df, run, run_id)


def _render_all_charts(returns_df: pd.DataFrame, scores_df: pd.DataFrame, run: dict, run_id: str):
    """Render all charts immediately."""
    
    if returns_df is None or returns_df.empty:
        st.info("No returns data available for charts")
        return
    
    if scores_df.empty:
        st.info("No scores data available for charts")
        return
    
    # Prepare returns data
    returns_df = returns_df.copy()
    if 'date' in returns_df.columns:
        returns_df['date'] = pd.to_datetime(returns_df['date'])
    if 'portfolio_return' in returns_df.columns:
        returns_df['cumulative'] = (1 + returns_df['portfolio_return']).cumprod()
    
    # Row 1: Equity Curve and Sector Allocation
    col1, col2 = st.columns(2)
    
    with col1:
        render_section_header("Equity Curve")
        if 'portfolio_return' in returns_df.columns and 'date' in returns_df.columns:
            dates = returns_df['date'].tolist()
            values = returns_df['cumulative'].tolist() if 'cumulative' in returns_df.columns else (1 + returns_df['portfolio_return']).cumprod().tolist()
            fig = create_equity_curve(dates, values)
            st.plotly_chart(fig, use_container_width=True)
            _render_chart_insight("equity_curve", returns_df, scores_df, run)
    
    with col2:
        render_section_header("Sector Allocation")
        if 'sector' in scores_df.columns:
            sector_counts = scores_df['sector'].value_counts().to_dict()
            fig = create_sector_pie(sector_counts)
            st.plotly_chart(fig, use_container_width=True)
            _render_chart_insight("sector_allocation", returns_df, scores_df, run)
    
    st.markdown("---")
    
    # Row 2: Score Distribution and Top Performers
    col1, col2 = st.columns(2)
    
    with col1:
        render_section_header("Score Distribution")
        if 'score' in scores_df.columns:
            fig = create_score_distribution(scores_df['score'].dropna().tolist())
            st.plotly_chart(fig, use_container_width=True)
            _render_chart_insight("score_distribution", returns_df, scores_df, run)
    
    with col2:
        render_section_header("Top Performers")
        if 'score' in scores_df.columns:
            top10 = scores_df.nlargest(10, 'score')
            if 'ticker' in top10.columns and 'score' in top10.columns:
                # Create a simple bar chart for top performers
                fig = go.Figure(data=[go.Bar(
                    x=top10['ticker'].tolist(),
                    y=top10['score'].tolist(),
                    marker_color=CHART_COLORS['primary'],
                    text=[f"{s:.1f}" for s in top10['score'].tolist()],
                    textposition='outside'
                )])
                fig.update_layout(
                    title="Top 10 Stocks by Score",
                    xaxis_title="Ticker",
                    yaxis_title="Score",
                    height=350,
                    **get_chart_template()['layout']
                )
                st.plotly_chart(fig, use_container_width=True)
                _render_chart_insight("top_performers", returns_df, scores_df, run)
    
    st.markdown("---")
    
    # Row 3: Drawdown Chart
    if 'portfolio_return' in returns_df.columns and 'date' in returns_df.columns:
        render_section_header("Drawdown Analysis")
        # Calculate drawdown
        cumulative = (1 + returns_df['portfolio_return']).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative / running_max - 1) * 100
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=returns_df['date'],
            y=drawdown,
            fill='tozeroy',
            fillcolor='rgba(239, 68, 68, 0.3)',
            line=dict(color=CHART_COLORS['danger'], width=2),
            name='Drawdown'
        ))
        fig.update_layout(
            title="Portfolio Drawdown",
            xaxis_title="Date",
            yaxis_title="Drawdown (%)",
            height=350,
            **get_chart_template()['layout']
        )
        st.plotly_chart(fig, use_container_width=True)
        _render_chart_insight("drawdown", returns_df, scores_df, run)


def _render_lazy_charts(returns_df: pd.DataFrame, scores_df: pd.DataFrame, run: dict, run_id: str):
    """Render charts with lazy loading (in expanders)."""
    
    if returns_df is None or returns_df.empty:
        st.info("No returns data available for charts")
        return
    
    if scores_df.empty:
        st.info("No scores data available for charts")
        return
    
    # Prepare returns data
    returns_df = returns_df.copy()
    if 'date' in returns_df.columns:
        returns_df['date'] = pd.to_datetime(returns_df['date'])
    if 'portfolio_return' in returns_df.columns:
        returns_df['cumulative'] = (1 + returns_df['portfolio_return']).cumprod()
    
    # Equity Curve
    with st.expander("Equity Curve", expanded=True):
        if 'portfolio_return' in returns_df.columns and 'date' in returns_df.columns:
            # Calculate cumulative values from returns
            cumulative_values = (1 + returns_df['portfolio_return']).cumprod().tolist()
            dates = returns_df['date'].tolist()
            fig = create_equity_curve(dates, cumulative_values)
            st.plotly_chart(fig, use_container_width=True)
            _render_chart_insight("equity_curve", returns_df, scores_df, run)
    
    # Sector Allocation
    with st.expander("🏭 Sector Allocation", expanded=False):
        if 'sector' in scores_df.columns:
            sector_counts = scores_df['sector'].value_counts().to_dict()
            fig = create_sector_pie(sector_counts)
            st.plotly_chart(fig, use_container_width=True)
            _render_chart_insight("sector_allocation", returns_df, scores_df, run)
    
    # Score Distribution
    with st.expander("📊 Score Distribution", expanded=False):
        if 'score' in scores_df.columns:
            fig = create_score_distribution(scores_df['score'].dropna().tolist())
            st.plotly_chart(fig, use_container_width=True)
            _render_chart_insight("score_distribution", returns_df, scores_df, run)
    
    # Top Performers
    with st.expander("⭐ Top Performers", expanded=False):
        if 'score' in scores_df.columns:
            top10 = scores_df.nlargest(10, 'score')
            if 'ticker' in top10.columns and 'score' in top10.columns:
                # Create a simple bar chart for top performers
                fig = go.Figure(data=[go.Bar(
                    x=top10['ticker'].tolist(),
                    y=top10['score'].tolist(),
                    marker_color=CHART_COLORS['primary'],
                    text=[f"{s:.1f}" for s in top10['score'].tolist()],
                    textposition='outside'
                )])
                fig.update_layout(
                    title="Top 10 Stocks by Score",
                    xaxis_title="Ticker",
                    yaxis_title="Score",
                    height=350,
                    **get_chart_template()['layout']
                )
                st.plotly_chart(fig, use_container_width=True)
                _render_chart_insight("top_performers", returns_df, scores_df, run)
    
    # Drawdown Chart
    with st.expander("📉 Drawdown Analysis", expanded=False):
        if 'portfolio_return' in returns_df.columns and 'date' in returns_df.columns:
            # Calculate drawdown
            cumulative = (1 + returns_df['portfolio_return']).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative / running_max - 1) * 100
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=returns_df['date'],
                y=drawdown,
                fill='tozeroy',
                fillcolor='rgba(239, 68, 68, 0.3)',
                line=dict(color=CHART_COLORS['danger'], width=2),
                name='Drawdown'
            ))
            fig.update_layout(
                title="Portfolio Drawdown",
                xaxis_title="Date",
                yaxis_title="Drawdown (%)",
                height=350,
                **get_chart_template()['layout']
            )
            st.plotly_chart(fig, use_container_width=True)
            _render_chart_insight("drawdown", returns_df, scores_df, run)
    
    # ==========================================
    # AI SUMMARY (Optional - requires API)
    # ==========================================
    st.markdown("---")
    _render_ai_portfolio_summary(run, scores_df, returns_df)


def _render_portfolio_details_panel(run: dict, scores_df: pd.DataFrame):
    """Render portfolio details panel with key information."""
    
    # Get portfolio info
    portfolio_name = run.get('name') or 'Unnamed Portfolio'
    watchlist = run.get('watchlist_display_name') or run.get('watchlist') or 'Default'
    num_stocks = len(scores_df) if not scores_df.empty else 0
    run_date = run.get('created_at', 'N/A')
    
    # Calculate additional stats
    sectors = scores_df['sector'].nunique() if not scores_df.empty and 'sector' in scores_df.columns else 0
    avg_score = scores_df['score'].mean() if not scores_df.empty and 'score' in scores_df.columns else 0
    # Normalize score to 0-100 for display
    if avg_score <= 1.0 and avg_score > 0:
        avg_score = avg_score * 100
    top_sector = scores_df['sector'].value_counts().index[0] if not scores_df.empty and 'sector' in scores_df.columns else 'N/A'
    
    st.markdown(f"""
    <div style="background: #ffffff; border-radius: 20px; 
                padding: 2rem; margin-bottom: 1rem; border: 1px solid #cbd5e1;
                box-shadow: 0 4px 16px rgba(0,0,0,0.08);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
            <div style="flex: 2; min-width: 300px;">
                <h2 style="margin: 0; color: #1e293b; font-size: 1.75rem; font-weight: 700;">
                    📁 {portfolio_name}
                </h2>
                <p style="color: #475569; margin: 0.5rem 0 0 0; font-size: 0.9rem;">
                    📋 Watchlist: <span style="color: #4f46e5; font-weight: 600;">{watchlist}</span>
                    &nbsp;•&nbsp;
                    🗓️ Run ID: <span style="color: #64748b;">{run.get('run_id', 'N/A')[:16]}...</span>
                </p>
            </div>
            <div style="display: flex; gap: 2rem; flex-wrap: wrap; margin-top: 1rem;">
                <div style="text-align: center;">
                    <div style="font-size: 2rem; font-weight: 800; color: #4f46e5;">{num_stocks}</div>
                    <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px;">Holdings</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 2rem; font-weight: 800; color: #7c3aed;">{sectors}</div>
                    <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px;">Sectors</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 2rem; font-weight: 800; color: #059669;">{avg_score:.1f}</div>
                    <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px;">Avg Score</div>
                </div>
            </div>
        </div>
        <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #cbd5e1;">
            <span style="color: #475569; font-size: 0.85rem;">
                🏆 Top Sector: <span style="color: #d97706; font-weight: 600;">{top_sector}</span>
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_holdings_pills(scores_df: pd.DataFrame):
    """Render all holdings as interactive pills."""
    if scores_df.empty:
        return
    
    render_section_header("All Holdings")
    
    # Sort by score descending
    sorted_df = scores_df.sort_values('score', ascending=False).copy()
    
    # Detect score scale (0-1 vs 0-100) and normalize
    max_score = sorted_df['score'].max()
    if max_score <= 1.0:
        # Scores are in 0-1 scale, convert to 0-100
        sorted_df['display_score'] = sorted_df['score'] * 100
        score_scale = "0-1"
    else:
        sorted_df['display_score'] = sorted_df['score']
        score_scale = "0-100"
    
    # Build pills using native Streamlit columns for proper rendering
    num_stocks = len(sorted_df)
    cols_per_row = 6
    
    rows = (num_stocks + cols_per_row - 1) // cols_per_row
    
    for row_idx in range(rows):
        cols = st.columns(cols_per_row)
        for col_idx in range(cols_per_row):
            stock_idx = row_idx * cols_per_row + col_idx
            if stock_idx >= num_stocks:
                break
            
            row = sorted_df.iloc[stock_idx]
            ticker = row['ticker']
            score = row['display_score']
            sector = row.get('sector', '')
            
            # Color based on score (0-100 scale)
            if score >= 70:
                bg_color = '#10b981'
                emoji = '🟢'
            elif score >= 50:
                bg_color = '#6366f1'
                emoji = '🟣'
            elif score >= 30:
                bg_color = '#f59e0b'
                emoji = '🟡'
            else:
                bg_color = '#ef4444'
                emoji = '🔴'
            
            with cols[col_idx]:
                st.markdown(f"""
                <div style="background: #f8fafc; 
                            border: 2px solid {bg_color}; border-radius: 12px; 
                            padding: 0.6rem 0.8rem; text-align: center; margin: 0.2rem 0;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <div style="font-weight: 700; color: {bg_color}; font-size: 1rem;">{ticker}</div>
                    <div style="font-size: 0.85rem; color: #1e293b; font-weight: 600;">{score:.1f}</div>
                    <div style="font-size: 0.7rem; color: #64748b; margin-top: 0.2rem;">{sector[:15]}</div>
                </div>
                """, unsafe_allow_html=True)
    
    # Legend
    st.markdown("""
    <div style="display: flex; gap: 1.5rem; margin-top: 1rem; font-size: 0.8rem; color: #475569; flex-wrap: wrap;">
        <span>🟢 Score ≥70 (Strong)</span>
        <span>🟣 Score ≥50 (Good)</span>
        <span>🟡 Score ≥30 (Hold)</span>
        <span>🔴 Score <30 (Weak)</span>
    </div>
    """, unsafe_allow_html=True)


def _render_chart_insight(chart_type: str, returns_df: pd.DataFrame, scores_df: pd.DataFrame, run: dict):
    """Render contextual insight for each chart."""
    
    insight = _generate_chart_insight(chart_type, returns_df, scores_df, run)
    
    st.markdown(f"""
    <div style="background: #f1f5f9; border-left: 3px solid #6366f1; 
                padding: 0.75rem 1rem; border-radius: 0 8px 8px 0; margin-top: 0.5rem;
                border: 1px solid #e2e8f0;">
        <div style="display: flex; align-items: flex-start; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">💡</span>
            <span style="color: #1e293b; font-size: 0.85rem; line-height: 1.5;">{insight}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _generate_chart_insight(chart_type: str, returns_df: pd.DataFrame, scores_df: pd.DataFrame, run: dict) -> str:
    """Generate contextual insight based on chart type and data."""
    
    if chart_type == "equity_curve":
        if returns_df is not None and 'portfolio_return' in returns_df.columns:
            total_return = run.get('total_return', 0) or 0
            if total_return > 0.15:
                return f"<b>Strong Performance!</b> The portfolio gained {total_return*100:.1f}%, showing consistent upward momentum. Watch for potential mean reversion if gains accelerate too quickly."
            elif total_return > 0:
                return f"<b>Positive Returns.</b> The portfolio returned {total_return*100:.1f}%. Look for periods of consolidation before breakouts - these often signal the next move."
            else:
                return f"<b>Challenging Period.</b> The portfolio declined {total_return*100:.1f}%. Review drawdown duration and recovery patterns. Extended flat periods may indicate stabilization."
        return "Track portfolio value over time. Steep drops indicate risk events; steady climbs show momentum."
    
    elif chart_type == "sector_allocation":
        if not scores_df.empty and 'sector' in scores_df.columns:
            sector_counts = scores_df['sector'].value_counts()
            top_sector = sector_counts.index[0]
            top_pct = (sector_counts.iloc[0] / len(scores_df)) * 100
            num_sectors = len(sector_counts)
            
            if top_pct > 40:
                return f"<b>High Concentration Risk!</b> {top_sector} represents {top_pct:.0f}% of holdings. Consider diversifying to reduce sector-specific risk."
            elif num_sectors < 4:
                return f"<b>Limited Diversification.</b> Only {num_sectors} sectors represented. Adding exposure to other sectors could improve risk-adjusted returns."
            else:
                return f"<b>Well Diversified.</b> Spread across {num_sectors} sectors with {top_sector} leading at {top_pct:.0f}%. Good sector balance reduces concentration risk."
        return "Monitor sector weights to avoid overconcentration. No single sector should exceed 35% for balanced portfolios."
    
    elif chart_type == "score_distribution":
        if not scores_df.empty and 'score' in scores_df.columns:
            mean_score = scores_df['score'].mean()
            std_score = scores_df['score'].std()
            
            # Normalize to 0-100 scale for display
            if mean_score <= 1.0:
                display_mean = mean_score * 100
                display_std = std_score * 100
                threshold = 0.6
                std_threshold = 0.2
            else:
                display_mean = mean_score
                display_std = std_score
                threshold = 60
                std_threshold = 20
            
            high_score_pct = (scores_df['score'] >= threshold).mean() * 100
            
            if display_mean > 60:
                return f"<b>High Quality Universe!</b> Average score of {display_mean:.1f} indicates strong stock selection. {high_score_pct:.0f}% of holdings score 60+."
            elif display_std > 20:
                return f"<b>Wide Score Spread.</b> High variability (σ={display_std:.1f}) suggests mixed conviction. Consider focusing on top-quartile scores for concentrated portfolio."
            else:
                return f"<b>Consistent Scoring.</b> Tight distribution around {display_mean:.1f} shows uniform quality. The model has similar conviction across holdings."
        return "The violin shows score distribution. Wider shapes indicate more variability; look for clustering near high scores."
    
    elif chart_type == "top_performers":
        if not scores_df.empty and 'score' in scores_df.columns:
            top5 = scores_df.nlargest(5, 'score')
            top_ticker = top5.iloc[0]['ticker']
            top_score = top5.iloc[0]['score']
            score_gap = top5.iloc[0]['score'] - top5.iloc[-1]['score'] if len(top5) > 1 else 0
            
            # Normalize to 0-100 scale for display
            if top_score <= 1.0:
                display_score = top_score * 100
                display_gap = score_gap * 100
                gap_threshold = 5
            else:
                display_score = top_score
                display_gap = score_gap
                gap_threshold = 5
            
            if display_gap < gap_threshold:
                return f"<b>Tight Competition.</b> Top 5 stocks are closely scored (gap: {display_gap:.1f}). Multiple strong candidates suggest robust opportunity set."
            else:
                return f"<b>{top_ticker} Leads.</b> Highest conviction pick with score {display_score:.1f}. Consider overweighting top scorers while maintaining diversification."
        return "These are the model's highest-conviction picks. Higher scores indicate stronger predicted outperformance."
    
    elif chart_type == "monthly_heatmap":
        if returns_df is not None and 'portfolio_return' in returns_df.columns:
            returns_df['date'] = pd.to_datetime(returns_df['date'])
            returns_df['month'] = returns_df['date'].dt.to_period('M')
            monthly = returns_df.groupby('month')['portfolio_return'].apply(lambda x: (1 + x).prod() - 1)
            
            positive_months = (monthly > 0).sum()
            total_months = len(monthly)
            best_month = monthly.max() * 100
            worst_month = monthly.min() * 100
            
            if positive_months / total_months > 0.6:
                return f"<b>Consistent Winner.</b> {positive_months}/{total_months} positive months. Best: +{best_month:.1f}%, Worst: {worst_month:.1f}%. Look for seasonal patterns."
            else:
                return f"<b>Mixed Results.</b> {positive_months}/{total_months} positive months. Range: {worst_month:.1f}% to +{best_month:.1f}%. Volatility requires position sizing discipline."
        return "Green cells = positive months, Red = negative. Watch for seasonal patterns and consecutive losing months."
    
    return "Analyze this chart for patterns and anomalies that might inform portfolio decisions."


def _render_ai_portfolio_summary(run: dict, scores_df: pd.DataFrame, returns_df: pd.DataFrame):
    """Render AI-generated portfolio summary."""
    
    render_section_header("AI Portfolio Summary")
    
    # Generate summary using local analysis (no API call needed)
    summary = _generate_portfolio_summary(run, scores_df, returns_df)
    
    st.markdown(f"""
    <div style="background: #ffffff; 
                border-radius: 16px; padding: 1.5rem; border: 1px solid #6366f1;
                box-shadow: 0 4px 16px rgba(0,0,0,0.08);">
        <div style="display: flex; align-items: flex-start; gap: 1rem;">
            <div style="font-size: 2rem;">🤖</div>
            <div>
                <h4 style="margin: 0 0 0.75rem 0; color: #1e293b;">Portfolio Intelligence</h4>
                <div style="color: #334155; line-height: 1.7; font-size: 0.95rem;">
                    {summary}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Option to get AI-powered deep analysis
    with st.expander("🔮 Get AI-Powered Deep Analysis"):
        if st.button("Generate AI Analysis", key="ai_summary_btn"):
            with st.spinner("Generating AI insights..."):
                ai_summary = _get_gemini_portfolio_analysis(run, scores_df, returns_df)
                st.markdown(ai_summary)


def _generate_portfolio_summary(run: dict, scores_df: pd.DataFrame, returns_df: pd.DataFrame) -> str:
    """Generate a comprehensive portfolio summary."""
    
    parts = []
    
    # Performance summary
    total_return = run.get('total_return', 0) or 0
    sharpe = run.get('sharpe_ratio', 0) or 0
    max_dd = run.get('max_drawdown', 0) or 0
    
    if total_return > 0.1:
        parts.append(f"<b>Strong returns</b> of {total_return*100:.1f}% demonstrate effective stock selection.")
    elif total_return > 0:
        parts.append(f"The portfolio achieved <b>positive returns</b> of {total_return*100:.1f}%.")
    else:
        parts.append(f"The portfolio experienced a <b>drawdown</b> of {total_return*100:.1f}%, requiring review.")
    
    if sharpe > 1.5:
        parts.append(f"With a <b>Sharpe ratio of {sharpe:.2f}</b>, risk-adjusted returns are excellent.")
    elif sharpe > 1:
        parts.append(f"A <b>Sharpe ratio of {sharpe:.2f}</b> indicates good risk-adjusted performance.")
    elif sharpe > 0:
        parts.append(f"The <b>Sharpe ratio of {sharpe:.2f}</b> suggests room for improvement in risk management.")
    
    # Holdings analysis
    if not scores_df.empty:
        num_stocks = len(scores_df)
        avg_score = scores_df['score'].mean()
        # Normalize to 0-100 scale for display
        if avg_score <= 1.0 and avg_score > 0:
            avg_score = avg_score * 100
        
        parts.append(f"<br><br>The universe contains <b>{num_stocks} holdings</b> with an average score of <b>{avg_score:.1f}</b>.")
        
        if 'sector' in scores_df.columns:
            sectors = scores_df['sector'].nunique()
            top_sector = scores_df['sector'].value_counts().index[0]
            parts.append(f"Diversification spans <b>{sectors} sectors</b>, led by {top_sector}.")
        
        # Top picks
        if 'score' in scores_df.columns:
            top3 = scores_df.nlargest(3, 'score')
            top_tickers = ', '.join(top3['ticker'].tolist())
            parts.append(f"<br><br><b>Top conviction picks:</b> {top_tickers}. These represent the model's strongest signals.")
    
    # Risk commentary
    if abs(max_dd) > 0.15:
        parts.append(f"<br><br>⚠️ <b>Risk Alert:</b> Max drawdown of {max_dd*100:.1f}% exceeded typical tolerance. Consider tighter stops or reduced position sizing.")
    elif abs(max_dd) > 0.10:
        parts.append(f"<br><br>Drawdown of {max_dd*100:.1f}% is within normal range but warrants monitoring.")
    
    return ' '.join(parts)


def _get_gemini_portfolio_analysis(run: dict, scores_df: pd.DataFrame, returns_df: pd.DataFrame) -> str:
    """Get AI-powered portfolio analysis from Gemini."""
    try:
        import google.generativeai as genai
        import os
        
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return "⚠️ AI analysis requires GEMINI_API_KEY. Set it in your environment to enable this feature."
        
        genai.configure(api_key=api_key)
        
        # Try different model names
        model_names = ['gemini-2.0-flash-exp', 'gemini-1.5-flash-latest', 'gemini-1.5-pro-latest', 'gemini-pro']
        model = None
        
        for name in model_names:
            try:
                model = genai.GenerativeModel(name)
                break
            except:
                continue
        
        if model is None:
            return "⚠️ Could not connect to AI model. Please try again later."
        
        # Build context
        total_return = run.get('total_return', 0) or 0
        sharpe = run.get('sharpe_ratio', 0) or 0
        max_dd = run.get('max_drawdown', 0) or 0
        win_rate = run.get('win_rate', 0) or 0
        
        holdings_summary = ""
        if not scores_df.empty:
            top10 = scores_df.nlargest(10, 'score')[['ticker', 'score', 'sector']].to_string()
            sector_dist = scores_df['sector'].value_counts().to_string()
            holdings_summary = f"""
Top 10 Holdings:
{top10}

Sector Distribution:
{sector_dist}
"""
        
        prompt = f"""You are a professional portfolio analyst. Provide a concise but insightful analysis of this portfolio.

PORTFOLIO METRICS:
- Total Return: {total_return*100:.2f}%
- Sharpe Ratio: {sharpe:.2f}
- Max Drawdown: {max_dd*100:.2f}%
- Win Rate: {win_rate*100:.1f}%
- Number of Holdings: {len(scores_df)}

{holdings_summary}

Please provide:
1. **Performance Assessment** (2-3 sentences on overall performance)
2. **Strengths** (2-3 key positives)
3. **Areas of Concern** (2-3 risks or weaknesses)
4. **Actionable Recommendations** (2-3 specific suggestions)

Keep the response focused and actionable. Use bullet points for clarity.
"""
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"⚠️ AI analysis error: {str(e)}"


def _render_performance_tab(run: dict, run_id: str):
    """Render detailed performance analysis with beautiful charts."""
    
    returns_df = load_backtest_returns(run_id)
    
    if returns_df is None or returns_df.empty:
        st.info("No returns data available")
        return
    
    if 'portfolio_return' not in returns_df.columns:
        st.info("Portfolio returns not found")
        return
    
    returns_df['date'] = pd.to_datetime(returns_df['date'])
    returns_df['cumulative'] = (1 + returns_df['portfolio_return']).cumprod()
    
    # Row 1: Cumulative vs Drawdown
    col1, col2 = st.columns(2)
    
    with col1:
        render_section_header("Cumulative Returns")
        fig = _create_area_returns(returns_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        render_section_header("Underwater Plot")
        fig = _create_underwater_chart(returns_df)
        st.plotly_chart(fig, use_container_width=True)
    
    # Row 2: Rolling metrics
    col1, col2 = st.columns(2)
    
    with col1:
        render_section_header("Rolling 20-Day Returns")
        fig = _create_rolling_returns(returns_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        render_section_header("Rolling Volatility")
        fig = _create_rolling_volatility(returns_df)
        st.plotly_chart(fig, use_container_width=True)
    
    # Row 3: Returns distribution
    col1, col2 = st.columns(2)
    
    with col1:
        render_section_header("Returns Distribution")
        fig = _create_returns_histogram(returns_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        render_section_header("Performance Statistics")
        _render_performance_stats(returns_df)
    
    # Monthly returns calendar
    render_section_header("Monthly Performance Calendar")
    fig = _create_monthly_calendar(returns_df)
    st.plotly_chart(fig, use_container_width=True)


def _render_sector_tab(run_id: str):
    """Render sector analysis with beautiful visualizations."""
    
    scores = load_run_scores(run_id)
    if not scores:
        st.info("No data available")
        return
    
    scores_df = pd.DataFrame(scores)
    
    if 'sector' not in scores_df.columns:
        st.info("No sector data available")
        return
    
    # Row 1: Treemap + Radar
    col1, col2 = st.columns(2)
    
    with col1:
        render_section_header("Sector Treemap")
        fig = _create_sector_treemap(scores_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        render_section_header("Sector Scores Radar")
        fig = _create_sector_radar(scores_df)
        st.plotly_chart(fig, use_container_width=True)
    
    # Row 2: Bar chart + Stats
    col1, col2 = st.columns(2)
    
    with col1:
        render_section_header("Holdings by Sector")
        fig = _create_sector_bar(scores_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        render_section_header("Sector Statistics")
        _render_sector_stats(scores_df)
    
    # Top stocks by sector
    render_section_header("Top Stocks by Sector")
    _render_sector_top_stocks(scores_df)


def _render_risk_tab(run: dict, run_id: str):
    """Render risk analysis with beautiful visualizations."""
    
    returns_df = load_backtest_returns(run_id)
    scores = load_run_scores(run_id)
    
    # Risk metrics cards
    render_section_header("Risk Metrics")
    _render_risk_metrics_cards(run)
    
    # Row 1: VaR + Risk-Return scatter
    col1, col2 = st.columns(2)
    
    with col1:
        render_section_header("Value at Risk Analysis")
        if returns_df is not None and 'portfolio_return' in returns_df.columns:
            fig = _create_var_chart(returns_df)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No returns data")
    
    with col2:
        render_section_header("Risk-Return Scatter")
        if scores:
            scores_df = pd.DataFrame(scores)
            fig = _create_risk_return_scatter(scores_df)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No scores data")
    
    # Risk gauge
    if returns_df is not None:
        render_section_header("Portfolio Risk Gauge")
        col1, col2, col3 = st.columns(3)
        
        ret = returns_df['portfolio_return'].dropna()
        vol = ret.std() * np.sqrt(252)
        
        with col1:
            fig = _create_gauge_chart("Volatility", vol * 100, 0, 50)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            sharpe = (ret.mean() * 252) / vol if vol > 0 else 0
            fig = _create_gauge_chart("Sharpe Ratio", sharpe, -1, 3)
            st.plotly_chart(fig, use_container_width=True)
        
        with col3:
            max_dd = abs(run.get('max_drawdown', 0) or 0) * 100
            fig = _create_gauge_chart("Max Drawdown", max_dd, 0, 50)
            st.plotly_chart(fig, use_container_width=True)


def _render_holdings_tab(run_id: str):
    """Render holdings analysis."""
    
    scores = load_run_scores(run_id)
    if not scores:
        st.info("No holdings data available")
        return
    
    scores_df = pd.DataFrame(scores)
    
    # Row 1: Score distribution + Weight bar
    col1, col2 = st.columns(2)
    
    with col1:
        render_section_header("Score Distribution")
        fig = _create_score_histogram(scores_df)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        render_section_header("Top 10 by Score")
        fig = _create_top10_lollipop(scores_df)
        st.plotly_chart(fig, use_container_width=True)
    
    # Holdings table
    render_section_header("All Holdings")
    _render_holdings_table(scores_df)


def _render_ai_tab(run_id: str):
    """Render AI analysis tab with beautiful cards."""
    
    recommendations_data = load_ai_recommendations(run_id)
    
    if not recommendations_data:
        st.info("No AI recommendations available for this run")
        st.markdown("""
        To generate AI analysis:
        1. Go to **Run Analysis** page
        2. Select this run under "Continue Existing Run"  
        3. Click **Run AI Analysis**
        """)
        return
    
    # Handle different data formats
    profiles = recommendations_data.get('recommendations') or recommendations_data.get('profiles', {})
    
    # If profiles is a string, try to parse it as JSON
    if isinstance(profiles, str):
        try:
            import json
            profiles = json.loads(profiles)
        except (json.JSONDecodeError, TypeError):
            # If it's not JSON, treat as plain text and create a simple structure
            profiles = {}
    
    # Ensure profiles is a dict before calling .items()
    if not isinstance(profiles, dict):
        profiles = {}
    
    portfolio_profiles = {k: v for k, v in profiles.items() if isinstance(v, dict)}
    
    if not portfolio_profiles:
        st.info("No portfolio profiles found")
        return
    
    # Beautiful profile cards
    profile_styles = {
        'conservative': {'emoji': '🛡️', 'background': '#e8f7ef', 'color': '#10b981'},
        'balanced': {'emoji': '⚖️', 'background': '#eef4ff', 'color': '#6366f1'},
        'aggressive': {'emoji': '🚀', 'background': '#ffecec', 'color': '#ef4444'},
    }
    
    cols = st.columns(len(portfolio_profiles))
    
    for i, (profile_name, profile_data) in enumerate(portfolio_profiles.items()):
        style = profile_styles.get(profile_name.lower(), profile_styles['balanced'])
        
        exp_ret = profile_data.get('expected_return', 'N/A')
        if isinstance(exp_ret, dict):
            exp_ret = f"{exp_ret.get('low', '?')}-{exp_ret.get('high', '?')}%"
        
        holdings = profile_data.get('holdings', [])
        holdings_str = ', '.join([h.get('ticker', '') if isinstance(h, dict) else str(h) for h in holdings[:5]])
        
        with cols[i]:
            st.markdown(f"""
            <div style="background: {style['background']}; padding: 2rem; border-radius: 20px; 
                        box-shadow: 0 12px 32px rgba(0,0,0,0.08); color: #0b0b0f; height: 100%;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">{style['emoji']}</div>
                <h2 style="margin: 0; font-weight: 800;">{profile_data.get('name', profile_name.title())}</h2>
                <div style="margin-top: 1.5rem;">
                    <div style="opacity: 0.9; margin: 0.5rem 0;">
                        <span style="opacity: 0.7;">Expected Return</span><br/>
                        <span style="font-size: 1.5rem; font-weight: 700;">{exp_ret}</span>
                    </div>
                    <div style="opacity: 0.9; margin: 0.5rem 0;">
                        <span style="opacity: 0.7;">Risk Level</span><br/>
                        <span style="font-size: 1.2rem; font-weight: 600;">{profile_data.get('risk_level', 'N/A')}</span>
                    </div>
                    <div style="opacity: 0.9; margin: 0.5rem 0;">
                        <span style="opacity: 0.7;">Time Horizon</span><br/>
                        <span style="font-size: 1.2rem; font-weight: 600;">{profile_data.get('time_horizon', 'N/A')}</span>
                    </div>
                    <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(15, 23, 42, 0.1);">
                        <span style="opacity: 0.7; font-size: 0.85rem;">Top Holdings</span><br/>
                        <span style="font-size: 0.9rem;">{holdings_str}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Overall assessment
    overall = profiles.get('overall_assessment')
    if overall and isinstance(overall, str):
        render_section_header("Overall Assessment")
        st.markdown(f"""
        <div style="background: #ffffff; padding: 1.5rem; 
                    border-radius: 16px; border-left: 4px solid #667eea; color: #334155;
                    border: 1px solid #e2e8f0;">
            {overall}
        </div>
        """, unsafe_allow_html=True)
    
    # Detailed holdings tables
    render_section_header("Portfolio Holdings Comparison")
    
    for profile_name, profile_data in portfolio_profiles.items():
        style = profile_styles.get(profile_name.lower(), profile_styles['balanced'])
        holdings = profile_data.get('holdings', [])
        
        if holdings:
            with st.expander(f"{style['emoji']} {profile_data.get('name', profile_name.title())} Holdings"):
                holdings_df = pd.DataFrame([
                    {
                        'Ticker': h.get('ticker', 'N/A'),
                        'Weight': f"{h.get('weight', 0)}%",
                        'Rationale': h.get('rationale', '')
                    } for h in holdings if isinstance(h, dict)
                ])
                st.dataframe(holdings_df, use_container_width=True, hide_index=True)
    
    generated_at = recommendations_data.get('generated_at')
    if generated_at:
        st.caption(f"🕐 Generated: {generated_at}")


# ============================================================================
# BEAUTIFUL CHART HELPERS
# ============================================================================

def _create_beautiful_equity_curve(returns_df: pd.DataFrame) -> go.Figure:
    """Create a clean equity curve."""
    returns_df['cumulative'] = (1 + returns_df['portfolio_return']).cumprod()
    returns_df['portfolio_value'] = returns_df['cumulative'] * 100000
    
    fig = go.Figure()
    
    # Area fill
    fig.add_trace(go.Scatter(
        x=returns_df['date'],
        y=returns_df['portfolio_value'],
        fill='tozeroy',
        fillcolor='rgba(99, 102, 241, 0.2)',
        line=dict(color='#6366f1', width=3),
        name='Portfolio Value'
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', zeroline=False, tickformat='$,.0f'),
        showlegend=False,
        hovermode='x unified'
    )
    
    return fig


def _create_sunburst_chart(scores_df: pd.DataFrame) -> go.Figure:
    """Create a sunburst chart for sector allocation."""
    sector_counts = scores_df['sector'].value_counts()
    
    fig = go.Figure(go.Sunburst(
        labels=['Portfolio'] + list(sector_counts.index),
        parents=[''] + ['Portfolio'] * len(sector_counts),
        values=[sector_counts.sum()] + list(sector_counts.values),
        marker=dict(colors=px.colors.qualitative.Set3),
        branchvalues='total',
        insidetextorientation='radial'
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
    )
    
    return fig


def _create_score_violin(scores_df: pd.DataFrame) -> go.Figure:
    """Create violin plot for score distribution."""
    fig = go.Figure()
    
    fig.add_trace(go.Violin(
        y=scores_df['score'],
        box_visible=True,
        meanline_visible=True,
        fillcolor='rgba(99, 102, 241, 0.5)',
        line_color='#6366f1',
        name='Score'
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        showlegend=False
    )
    
    return fig


def _create_top_performers_bar(scores_df: pd.DataFrame) -> go.Figure:
    """Create horizontal bar chart for top performers."""
    top10 = scores_df.nlargest(10, 'score').sort_values('score')
    
    colors = ['#10b981' if i >= 7 else '#6366f1' if i >= 4 else '#8b5cf6' 
              for i in range(len(top10))]
    
    fig = go.Figure(go.Bar(
        y=top10['ticker'],
        x=top10['score'],
        orientation='h',
        marker=dict(color=colors, cornerradius=5),
        text=[f'{s:.1f}' for s in top10['score']],
        textposition='outside'
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=80, r=50, t=30, b=20),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=False),
        showlegend=False
    )
    
    return fig


def _create_monthly_heatmap(returns_df: pd.DataFrame) -> go.Figure:
    """Create monthly returns heatmap."""
    returns_df['date'] = pd.to_datetime(returns_df['date'])
    returns_df['year'] = returns_df['date'].dt.year
    returns_df['month'] = returns_df['date'].dt.month
    
    monthly = returns_df.groupby(['year', 'month'])['portfolio_return'].apply(
        lambda x: (1 + x).prod() - 1
    ).unstack()
    
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    fig = go.Figure(data=go.Heatmap(
        z=monthly.values * 100,
        x=month_names[:monthly.shape[1]],
        y=monthly.index.astype(str),
        colorscale=[[0, '#ef4444'], [0.5, '#1e1e2e'], [1, '#10b981']],
        zmid=0,
        text=[[f'{v:.1f}%' if not np.isnan(v) else '' for v in row] for row in monthly.values * 100],
        texttemplate='%{text}',
        textfont=dict(color='white'),
        hovertemplate='%{y} %{x}: %{z:.2f}%<extra></extra>',
        colorbar=dict(title='Return %')
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        height=250,
        margin=dict(l=60, r=20, t=30, b=40),
    )
    
    return fig


def _create_area_returns(returns_df: pd.DataFrame) -> go.Figure:
    """Create area chart for cumulative returns."""
    fig = go.Figure()
    
    pos_mask = returns_df['cumulative'] >= 1
    
    fig.add_trace(go.Scatter(
        x=returns_df['date'],
        y=(returns_df['cumulative'] - 1) * 100,
        fill='tozeroy',
        fillcolor='rgba(16, 185, 129, 0.3)',
        line=dict(color='#10b981', width=2),
        name='Cumulative Return'
    ))
    
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis=dict(ticksuffix='%', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        xaxis=dict(showgrid=False),
        showlegend=False
    )
    
    return fig


def _create_underwater_chart(returns_df: pd.DataFrame) -> go.Figure:
    """Create underwater/drawdown chart."""
    returns_df['peak'] = returns_df['cumulative'].cummax()
    returns_df['drawdown'] = (returns_df['cumulative'] - returns_df['peak']) / returns_df['peak']
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=returns_df['date'],
        y=returns_df['drawdown'] * 100,
        fill='tozeroy',
        fillcolor='rgba(239, 68, 68, 0.4)',
        line=dict(color='#ef4444', width=2),
        name='Drawdown'
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis=dict(ticksuffix='%', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        xaxis=dict(showgrid=False),
        showlegend=False
    )
    
    return fig


def _create_rolling_returns(returns_df: pd.DataFrame) -> go.Figure:
    """Create rolling returns chart."""
    returns_df['rolling_20d'] = returns_df['portfolio_return'].rolling(20).mean() * 252 * 100
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=returns_df['date'],
        y=returns_df['rolling_20d'],
        line=dict(color='#6366f1', width=2),
        fill='tozeroy',
        fillcolor='rgba(99, 102, 241, 0.2)'
    ))
    
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=300,
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis=dict(ticksuffix='%', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        xaxis=dict(showgrid=False),
        showlegend=False
    )
    
    return fig


def _create_rolling_volatility(returns_df: pd.DataFrame) -> go.Figure:
    """Create rolling volatility chart."""
    returns_df['rolling_vol'] = returns_df['portfolio_return'].rolling(20).std() * np.sqrt(252) * 100
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=returns_df['date'],
        y=returns_df['rolling_vol'],
        line=dict(color='#f59e0b', width=2),
        fill='tozeroy',
        fillcolor='rgba(245, 158, 11, 0.2)'
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=300,
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis=dict(ticksuffix='%', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        xaxis=dict(showgrid=False),
        showlegend=False
    )
    
    return fig


def _create_returns_histogram(returns_df: pd.DataFrame) -> go.Figure:
    """Create returns distribution histogram."""
    returns = returns_df['portfolio_return'].dropna() * 100
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=returns,
        nbinsx=50,
        marker=dict(color='#6366f1', line=dict(color='#8b5cf6', width=1)),
        opacity=0.8
    ))
    
    # Add normal curve
    mean, std = returns.mean(), returns.std()
    x_range = np.linspace(returns.min(), returns.max(), 100)
    y_normal = (1/(std * np.sqrt(2*np.pi))) * np.exp(-0.5*((x_range-mean)/std)**2)
    y_normal = y_normal * len(returns) * (returns.max() - returns.min()) / 50
    
    fig.add_trace(go.Scatter(
        x=x_range,
        y=y_normal,
        line=dict(color='#f59e0b', width=2, dash='dot'),
        name='Normal'
    ))
    
    fig.add_vline(x=0, line_dash="dash", line_color="rgba(255,255,255,0.5)")
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=300,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(title='Daily Return %', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=False),
        showlegend=False,
        bargap=0.1
    )
    
    return fig


def _render_performance_stats(returns_df: pd.DataFrame):
    """Render performance statistics in beautiful cards."""
    ret = returns_df['portfolio_return'].dropna()
    
    stats = {
        'Mean Daily': f"{ret.mean()*100:.3f}%",
        'Std Dev': f"{ret.std()*100:.3f}%",
        'Annualized Return': f"{ret.mean()*252*100:.1f}%",
        'Annualized Vol': f"{ret.std()*np.sqrt(252)*100:.1f}%",
        'Best Day': f"{ret.max()*100:+.2f}%",
        'Worst Day': f"{ret.min()*100:+.2f}%",
        'Skewness': f"{ret.skew():.2f}",
        'Kurtosis': f"{ret.kurtosis():.2f}",
    }
    
    for label, value in stats.items():
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; padding: 0.75rem 1rem; 
                    background: #f8fafc; border-radius: 8px; margin: 0.5rem 0;
                    border-left: 3px solid #6366f1; border: 1px solid #e2e8f0;">
            <span style="color: #475569;">{label}</span>
            <span style="color: #1e293b; font-weight: 600;">{value}</span>
        </div>
        """, unsafe_allow_html=True)


def _create_monthly_calendar(returns_df: pd.DataFrame) -> go.Figure:
    """Create monthly performance calendar."""
    returns_df['date'] = pd.to_datetime(returns_df['date'])
    returns_df['month'] = returns_df['date'].dt.to_period('M')
    
    monthly = returns_df.groupby('month')['portfolio_return'].apply(
        lambda x: (1 + x).prod() - 1
    ).reset_index()
    monthly.columns = ['Month', 'Return']
    monthly['Month'] = monthly['Month'].astype(str)
    
    colors = ['#10b981' if r >= 0 else '#ef4444' for r in monthly['Return']]
    
    fig = go.Figure(go.Bar(
        x=monthly['Month'],
        y=monthly['Return'] * 100,
        marker=dict(color=colors, cornerradius=5),
        text=[f'{r*100:+.1f}%' for r in monthly['Return']],
        textposition='outside'
    ))
    
    fig.add_hline(y=0, line_color="rgba(255,255,255,0.3)")
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=300,
        margin=dict(l=20, r=20, t=30, b=40),
        yaxis=dict(ticksuffix='%', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        xaxis=dict(showgrid=False),
        showlegend=False
    )
    
    return fig


def _create_sector_treemap(scores_df: pd.DataFrame) -> go.Figure:
    """Create sector treemap."""
    fig = px.treemap(
        scores_df,
        path=['sector', 'ticker'],
        values=[1] * len(scores_df),
        color='score',
        color_continuous_scale='Viridis'
    )
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        height=400,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    
    return fig


def _create_sector_radar(scores_df: pd.DataFrame) -> go.Figure:
    """Create sector scores radar chart."""
    sector_avg = scores_df.groupby('sector')['score'].mean()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=sector_avg.values,
        theta=sector_avg.index,
        fill='toself',
        fillcolor='rgba(99, 102, 241, 0.3)',
        line=dict(color='#6366f1', width=2)
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        height=400,
        margin=dict(l=80, r=80, t=30, b=30),
        polar=dict(
            radialaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            angularaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
        )
    )
    
    return fig


def _create_sector_bar(scores_df: pd.DataFrame) -> go.Figure:
    """Create sector holdings bar chart."""
    sector_counts = scores_df['sector'].value_counts().sort_values()
    
    fig = go.Figure(go.Bar(
        y=sector_counts.index,
        x=sector_counts.values,
        orientation='h',
        marker=dict(
            color=sector_counts.values,
            colorscale='Viridis',
            cornerradius=5
        ),
        text=sector_counts.values,
        textposition='outside'
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        margin=dict(l=150, r=50, t=30, b=20),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=False),
        showlegend=False
    )
    
    return fig


def _render_sector_stats(scores_df: pd.DataFrame):
    """Render sector statistics."""
    sector_stats = scores_df.groupby('sector').agg({
        'score': ['count', 'mean', 'std', 'min', 'max']
    }).round(2)
    sector_stats.columns = ['Count', 'Avg', 'Std', 'Min', 'Max']
    sector_stats = sector_stats.sort_values('Avg', ascending=False)
    
    st.dataframe(sector_stats, use_container_width=True)


def _render_sector_top_stocks(scores_df: pd.DataFrame):
    """Render top stocks by sector in expandable sections."""
    sectors = scores_df.groupby('sector')['score'].mean().sort_values(ascending=False).index[:6]
    
    cols = st.columns(3)
    
    for i, sector in enumerate(sectors):
        sector_df = scores_df[scores_df['sector'] == sector].nlargest(3, 'score')
        
        with cols[i % 3]:
            st.markdown(f"""
            <div style="background: #ffffff; 
                        border-radius: 12px; padding: 1rem; margin: 0.5rem 0;
                        border: 1px solid #cbd5e1; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h4 style="color: #4f46e5; margin: 0 0 0.75rem 0; font-size: 1rem;">📂 {sector}</h4>
            """, unsafe_allow_html=True)
            
            for _, row in sector_df.iterrows():
                score = row['score']
                # Normalize score to 0-100 for display
                display_score = score * 100 if score <= 1.0 else score
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; padding: 0.5rem 0;
                            border-bottom: 1px solid #e2e8f0;">
                    <span style="font-weight: 600; color: #1e293b;">{row['ticker']}</span>
                    <span style="color: #059669; font-weight: 600;">{display_score:.1f}</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)


def _render_risk_metrics_cards(run: dict):
    """Render risk metrics in beautiful cards."""
    metrics = [
        ('Total Return', format_percent(run.get('total_return')), '📈', '#10b981'),
        ('Volatility', format_percent(run.get('volatility'), with_sign=False), '📊', '#f59e0b'),
        ('Sharpe Ratio', format_number(run.get('sharpe_ratio')), '⚡', '#6366f1'),
        ('Max Drawdown', format_percent(run.get('max_drawdown')), '📉', '#ef4444'),
        ('Sortino Ratio', format_number(run.get('sortino_ratio')), '🎯', '#8b5cf6'),
        ('Win Rate', format_percent(run.get('win_rate'), with_sign=False), '🏆', '#06b6d4'),
    ]
    
    cols = st.columns(6)
    
    for i, (label, value, icon, color) in enumerate(metrics):
        with cols[i]:
            st.markdown(f"""
            <div style="background: #ffffff; 
                        border-radius: 16px; padding: 1.25rem; text-align: center;
                        border-top: 3px solid {color}; border: 1px solid #e2e8f0;">
                <div style="font-size: 1.5rem;">{icon}</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: {color}; margin: 0.5rem 0;">{value}</div>
                <div style="font-size: 0.75rem; color: #475569; text-transform: uppercase;">{label}</div>
            </div>
            """, unsafe_allow_html=True)


def _create_var_chart(returns_df: pd.DataFrame) -> go.Figure:
    """Create Value at Risk visualization."""
    returns = returns_df['portfolio_return'].dropna() * 100
    var_95 = np.percentile(returns, 5)
    var_99 = np.percentile(returns, 1)
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=returns,
        nbinsx=50,
        marker=dict(color='#6366f1'),
        opacity=0.7
    ))
    
    fig.add_vline(x=var_95, line_color="#f59e0b", line_width=2, line_dash="dash",
                  annotation_text=f"VaR 95%: {var_95:.2f}%", annotation_position="top")
    fig.add_vline(x=var_99, line_color="#ef4444", line_width=2, line_dash="dash",
                  annotation_text=f"VaR 99%: {var_99:.2f}%", annotation_position="top")
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(title='Daily Return %', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=False),
        showlegend=False
    )
    
    return fig


def _create_risk_return_scatter(scores_df: pd.DataFrame) -> go.Figure:
    """Create risk-return scatter plot."""
    if 'volatility' not in scores_df.columns or 'predicted_return' not in scores_df.columns:
        # Create mock data if not available
        fig = go.Figure()
        fig.add_annotation(text="Risk-return data not available", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', height=350)
        return fig
    
    df = scores_df.dropna(subset=['volatility', 'predicted_return'])
    
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', height=350)
        return fig
    
    fig = px.scatter(
        df,
        x=df['volatility'] * 100,
        y=df['predicted_return'] * 100,
        color='sector' if 'sector' in df.columns else None,
        hover_data=['ticker'],
        labels={'x': 'Volatility %', 'y': 'Predicted Return %'}
    )
    
    fig.update_traces(marker=dict(size=10, line=dict(width=1, color='white')))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
    )
    
    return fig


def _create_gauge_chart(title: str, value: float, min_val: float, max_val: float) -> go.Figure:
    """Create a gauge chart."""
    # Determine color based on value
    if 'Drawdown' in title or 'Volatility' in title:
        color = '#ef4444' if value > (max_val * 0.6) else '#f59e0b' if value > (max_val * 0.3) else '#10b981'
    else:
        color = '#10b981' if value > (max_val * 0.6) else '#f59e0b' if value > (max_val * 0.3) else '#ef4444'
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title, 'font': {'color': '#1e293b', 'size': 14}},
        number={'suffix': '%' if 'Ratio' not in title else '', 'font': {'color': color}},
        gauge={
            'axis': {'range': [min_val, max_val], 'tickcolor': '#64748b'},
            'bar': {'color': color},
            'bgcolor': '#f1f5f9',
            'borderwidth': 0,
            'steps': [
                {'range': [min_val, max_val * 0.33], 'color': 'rgba(239, 68, 68, 0.15)'},
                {'range': [max_val * 0.33, max_val * 0.66], 'color': 'rgba(245, 158, 11, 0.15)'},
                {'range': [max_val * 0.66, max_val], 'color': 'rgba(16, 185, 129, 0.15)'},
            ],
        }
    ))
    
    fig.update_layout(
        template='plotly_white',
        paper_bgcolor='rgba(0,0,0,0)',
        height=200,
        margin=dict(l=30, r=30, t=50, b=20),
    )
    
    return fig


def _create_score_histogram(scores_df: pd.DataFrame) -> go.Figure:
    """Create score distribution histogram."""
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=scores_df['score'],
        nbinsx=20,
        marker=dict(
            color='#6366f1',
            line=dict(color='#8b5cf6', width=1)
        )
    ))
    
    mean_score = scores_df['score'].mean()
    fig.add_vline(x=mean_score, line_color="#f59e0b", line_width=2, line_dash="dash",
                  annotation_text=f"Mean: {mean_score:.1f}")
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(title='Score', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title='Count', showgrid=False),
        showlegend=False
    )
    
    return fig


def _create_top10_lollipop(scores_df: pd.DataFrame) -> go.Figure:
    """Create lollipop chart for top 10 stocks."""
    top10 = scores_df.nlargest(10, 'score').sort_values('score')
    
    fig = go.Figure()
    
    # Lines
    for i, (_, row) in enumerate(top10.iterrows()):
        fig.add_trace(go.Scatter(
            x=[0, row['score']],
            y=[row['ticker'], row['ticker']],
            mode='lines',
            line=dict(color='#6366f1', width=2),
            showlegend=False
        ))
    
    # Dots
    fig.add_trace(go.Scatter(
        x=top10['score'],
        y=top10['ticker'],
        mode='markers',
        marker=dict(color='#6366f1', size=12, line=dict(color='white', width=2)),
        showlegend=False
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=80, r=20, t=30, b=20),
        xaxis=dict(title='Score', showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(showgrid=False),
    )
    
    return fig


def _render_holdings_table(scores_df: pd.DataFrame):
    """Render beautiful holdings table."""
    display_cols = ['ticker', 'score', 'rank', 'sector']
    if 'predicted_return' in scores_df.columns:
        display_cols.append('predicted_return')
    if 'volatility' in scores_df.columns:
        display_cols.append('volatility')
    
    display_df = scores_df[display_cols].copy()
    display_df = display_df.sort_values('rank')
    
    # Format
    display_df['score'] = display_df['score'].apply(lambda x: f"{x:.1f}")
    if 'predicted_return' in display_df.columns:
        display_df['predicted_return'] = display_df['predicted_return'].apply(
            lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "N/A"
        )
    if 'volatility' in display_df.columns:
        display_df['volatility'] = display_df['volatility'].apply(
            lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A"
        )
    
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
