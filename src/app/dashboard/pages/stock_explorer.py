"""
Stock Explorer Page
==================
Explore individual stock scores and analysis.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from ..components.sidebar import render_page_header, render_section_header
from ..components.charts import create_score_distribution, create_scatter_plot
from ..components.tables import render_score_table
from ..components.cards import render_stock_card, render_info_card
from ..components.tooltips import get_tooltip
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
            format_func=lambda x: f"{x[:12]}... - {next((r.get('name') or 'Unnamed' for r in completed_runs if r['run_id'] == x), 'Unknown')}",
            help=get_tooltip('select_run') or "Choose a completed run to explore"
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
    
    # Filters and Search
    st.markdown("---")
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        sectors = ['All'] + sorted(scores_df['sector'].dropna().unique().tolist())
        sector_filter = st.selectbox(
            "Sector", 
            sectors, 
            key="stock_sector_filter",
            help=get_tooltip('sector_filter') or "Filter stocks by sector"
        )
    
    with col2:
        score_range = st.slider(
            "Score Range", 
            0.0, 
            float(scores_df['score'].max()) if len(scores_df) > 0 else 100.0,
            (0.0, float(scores_df['score'].max()) if len(scores_df) > 0 else 100.0),
            key="stock_score_range",
            help=get_tooltip('score_range') or "Filter stocks by score range"
        )
        score_min, score_max = score_range
    
    with col3:
        ticker_search = st.text_input(
            "🔍 Search Ticker",
            placeholder="Enter ticker symbol...",
            key="stock_ticker_search",
            help=get_tooltip('stock_search') or "Search by ticker symbol"
        )
    
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        clear_filters = st.button("Clear", key="clear_stock_filters", use_container_width=True)
        if clear_filters:
            st.session_state.stock_sector_filter = "All"
            st.session_state.stock_score_range = (0.0, 100.0)
            st.session_state.stock_ticker_search = ""
            st.rerun()
    
    # Apply filters
    filtered_df = scores_df.copy()
    
    if sector_filter != 'All':
        filtered_df = filtered_df[filtered_df['sector'] == sector_filter]
    
    filtered_df = filtered_df[
        (filtered_df['score'] >= score_min) & 
        (filtered_df['score'] <= score_max)
    ]
    
    if ticker_search:
        filtered_df = filtered_df[
            filtered_df['ticker'].str.contains(ticker_search.upper(), na=False)
        ]
    
    # Pagination
    items_per_page = st.slider("Items per page", 10, 100, 25, key="stocks_per_page")
    total_pages = (len(filtered_df) + items_per_page - 1) // items_per_page if len(filtered_df) > 0 else 1
    page_num = st.number_input("Page", min_value=1, max_value=max(1, total_pages), value=1, key="stocks_page")
    
    start_idx = (page_num - 1) * items_per_page
    end_idx = start_idx + items_per_page
    paginated_df = filtered_df.iloc[start_idx:end_idx]
    
    # Display summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Stocks", len(filtered_df))
    with col2:
        st.metric("Showing", f"{start_idx + 1}-{min(end_idx, len(filtered_df))}")
    with col3:
        st.metric("Page", f"{page_num}/{total_pages}")
    with col4:
        if len(filtered_df) > 0:
            avg_score = filtered_df['score'].mean()
            st.metric("Avg Score", f"{avg_score:.2f}")
    
    # Export buttons
    if len(filtered_df) > 0:
        export_col1, export_col2, export_col3 = st.columns([1, 1, 2])
        with export_col1:
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Export CSV",
                data=csv,
                file_name=f"stocks_{selected_run_id[:12]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_stocks_csv",
                use_container_width=True
            )
        with export_col2:
            import json
            json_data = json.dumps(filtered_df.to_dict('records'), indent=2, default=str)
            st.download_button(
                label="📥 Export JSON",
                data=json_data,
                file_name=f"stocks_{selected_run_id[:12]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                key="download_stocks_json",
                use_container_width=True
            )
    
    st.markdown("---")
    
    if view_mode == "Table":
        _render_table_view(paginated_df)
    elif view_mode == "Cards":
        _render_cards_view(paginated_df)
    else:
        _render_analysis_view(paginated_df)


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
