"""
Stock Explorer Page
==================
Explore individual stock scores and analysis.
"""

import streamlit as st
import pandas as pd
import numpy as np

from ..components.sidebar import render_page_header, render_section_header
from ..components.charts import create_score_distribution, create_scatter_plot
from ..components.tables import render_score_table
from ..components.cards import render_stock_card, render_info_card
from ..data import load_runs, load_run_scores, get_all_tickers, get_all_sectors
from ..utils import format_percent, format_number
from ..config import COLORS


def render_stock_explorer():
    """Render the stock explorer page."""
    render_page_header(
        "Stock Explorer",
        "Explore individual stock scores and analysis"
    )
    
    runs = load_runs()
    completed_runs = [r for r in runs if r['status'] == 'completed']
    
    if not completed_runs:
        st.warning("No completed runs found. Run a backtest first!")
        return
    
    # Run selector
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_run_id = st.selectbox(
            "Select Analysis Run",
            options=[r['run_id'] for r in completed_runs],
            format_func=lambda x: f"{x[:12]}... - {next((r.get('name') or 'Unnamed' for r in completed_runs if r['run_id'] == x), 'Unknown')}"
        )
    
    with col2:
        view_mode = st.radio(
            "View Mode",
            ["Table", "Cards", "Analysis"],
            horizontal=True
        )
    
    if not selected_run_id:
        return
    
    # Load scores
    scores = load_run_scores(selected_run_id)
    
    if not scores:
        st.warning("No scores found for this run")
        return
    
    scores_df = pd.DataFrame(scores)
    
    # Filters
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sectors = ['All'] + sorted(scores_df['sector'].dropna().unique().tolist())
        sector_filter = st.selectbox("Sector", sectors)
    
    with col2:
        score_min = st.slider("Min Score", 0, 100, 0)
    
    with col3:
        ticker_search = st.text_input("Search Ticker")
    
    # Apply filters
    filtered_df = scores_df.copy()
    
    if sector_filter != 'All':
        filtered_df = filtered_df[filtered_df['sector'] == sector_filter]
    
    filtered_df = filtered_df[filtered_df['score'] >= score_min]
    
    if ticker_search:
        filtered_df = filtered_df[
            filtered_df['ticker'].str.contains(ticker_search.upper(), na=False)
        ]
    
    st.markdown(f"**{len(filtered_df)}** stocks found")
    st.markdown("---")
    
    if view_mode == "Table":
        _render_table_view(filtered_df)
    elif view_mode == "Cards":
        _render_cards_view(filtered_df)
    else:
        _render_analysis_view(filtered_df)


def _render_table_view(df: pd.DataFrame):
    """Render table view of stocks."""
    render_section_header("Stock Scores", "📊")
    
    # Sort controls
    col1, col2 = st.columns([1, 3])
    with col1:
        sort_col = st.selectbox(
            "Sort by",
            ['score', 'rank', 'ticker', 'tech_score', 'fund_score', 'sent_score']
        )
    with col2:
        sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True)
    
    sorted_df = df.sort_values(
        sort_col, 
        ascending=(sort_order == "Ascending"),
        na_position='last'
    )
    
    # Display columns
    display_cols = ['rank', 'ticker', 'sector', 'score', 'tech_score', 
                    'fund_score', 'sent_score', 'return_21d', 'volatility']
    display_cols = [c for c in display_cols if c in sorted_df.columns]
    
    display_df = sorted_df[display_cols].head(50).copy()
    
    # Format
    for col in ['score', 'tech_score', 'fund_score', 'sent_score']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
            )
    
    for col in ['return_21d', 'volatility']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: f"{x*100:+.1f}%" if pd.notna(x) else "N/A"
            )
    
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)


def _render_cards_view(df: pd.DataFrame):
    """Render cards view of stocks."""
    render_section_header("Top Stocks", "🏆")
    
    # Show top 20 as cards
    top_df = df.nlargest(20, 'score')
    
    cols = st.columns(4)
    for i, (_, row) in enumerate(top_df.iterrows()):
        with cols[i % 4]:
            render_stock_card(
                ticker=row['ticker'],
                score=row['score'],
                sector=row.get('sector', ''),
                rank=row.get('rank'),
                change=row.get('return_21d')
            )


def _render_analysis_view(df: pd.DataFrame):
    """Render analysis view with charts."""
    col1, col2 = st.columns(2)
    
    with col1:
        render_section_header("Score Distribution", "📈")
        
        if len(df) > 0:
            fig = create_score_distribution(
                scores=df['score'].dropna().tolist(),
                title="Overall Score Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        render_section_header("By Sector", "🏭")
        
        if len(df) > 0 and 'sector' in df.columns:
            sector_stats = df.groupby('sector')['score'].agg(['mean', 'count']).reset_index()
            sector_stats.columns = ['Sector', 'Avg Score', 'Count']
            sector_stats = sector_stats.sort_values('Avg Score', ascending=False)
            
            st.dataframe(sector_stats, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    render_section_header("Score Components", "🔬")
    
    # Scatter plot: tech vs fund score
    if all(col in df.columns for col in ['tech_score', 'fund_score']):
        fig = create_scatter_plot(
            x=df['tech_score'].dropna().tolist(),
            y=df['fund_score'].dropna().tolist(),
            labels=df.loc[df['tech_score'].notna() & df['fund_score'].notna(), 'ticker'].tolist(),
            colors=df.loc[df['tech_score'].notna() & df['fund_score'].notna(), 'sector'].tolist() if 'sector' in df.columns else None,
            x_title="Technical Score",
            y_title="Fundamental Score",
            title="Technical vs Fundamental Score"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Summary statistics
    render_section_header("Summary Statistics", "📊")
    
    stat_cols = ['score', 'tech_score', 'fund_score', 'sent_score', 'return_21d', 'volatility']
    stat_cols = [c for c in stat_cols if c in df.columns]
    
    if stat_cols:
        stats_df = df[stat_cols].describe().T
        stats_df = stats_df[['mean', 'std', 'min', '50%', 'max']].round(2)
        stats_df.columns = ['Mean', 'Std', 'Min', 'Median', 'Max']
        st.dataframe(stats_df, use_container_width=True)
