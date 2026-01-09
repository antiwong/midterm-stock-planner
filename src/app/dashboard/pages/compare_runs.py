"""
Compare Runs Page
=================
Side-by-side comparison of analysis runs.
"""

import streamlit as st
import pandas as pd

from ..components.sidebar import render_page_header, render_section_header
from ..components.charts import create_performance_bar
from ..components.tables import render_comparison_table
from ..data import load_runs, load_run_scores
from ..utils import format_percent, format_number
from ..config import COLORS


def render_compare_runs():
    """Render the compare runs page."""
    render_page_header(
        "Compare Runs",
        "Side-by-side comparison of analysis runs"
    )
    
    runs = load_runs()
    completed_runs = [r for r in runs if r['status'] == 'completed']
    
    if len(completed_runs) < 2:
        st.warning("Need at least 2 completed runs to compare")
        return
    
    # Run selection
    col1, col2 = st.columns(2)
    
    with col1:
        run1_id = st.selectbox(
            "Run 1",
            options=[r['run_id'] for r in completed_runs],
            format_func=lambda x: f"{x[:12]}... - {next((r.get('name') or 'Unnamed' for r in completed_runs if r['run_id'] == x), 'Unknown')}",
            key="run1"
        )
    
    with col2:
        remaining_runs = [r['run_id'] for r in completed_runs if r['run_id'] != run1_id]
        run2_id = st.selectbox(
            "Run 2",
            options=remaining_runs,
            format_func=lambda x: f"{x[:12]}... - {next((r.get('name') or 'Unnamed' for r in completed_runs if r['run_id'] == x), 'Unknown')}",
            key="run2"
        )
    
    if not run1_id or not run2_id:
        return
    
    # Load run data
    run1 = next((r for r in completed_runs if r['run_id'] == run1_id), None)
    run2 = next((r for r in completed_runs if r['run_id'] == run2_id), None)
    
    if not run1 or not run2:
        st.error("Could not load run data")
        return
    
    st.markdown("---")
    
    # Metrics comparison
    _render_metrics_comparison(run1, run2)
    
    st.markdown("---")
    
    # Stock overlap
    _render_stock_overlap(run1_id, run2_id)
    
    st.markdown("---")
    
    # Score comparison
    _render_score_comparison(run1_id, run2_id)


def _render_metrics_comparison(run1: dict, run2: dict):
    """Render metrics comparison table."""
    render_section_header("Performance Metrics", "📊")
    
    metrics = [
        ('Total Return', 'total_return', True),
        ('Sharpe Ratio', 'sharpe_ratio', False),
        ('Sortino Ratio', 'sortino_ratio', False),
        ('Win Rate', 'win_rate', True),
        ('Max Drawdown', 'max_drawdown', True),
        ('Volatility', 'volatility', True),
        ('Calmar Ratio', 'calmar_ratio', False),
        ('Excess Return', 'excess_return', True),
    ]
    
    name1 = run1.get('name') or run1['run_id'][:8]
    name2 = run2.get('name') or run2['run_id'][:8]
    
    data = []
    for label, key, is_pct in metrics:
        val1 = run1.get(key)
        val2 = run2.get(key)
        
        if is_pct:
            val1_str = format_percent(val1) if val1 is not None else "N/A"
            val2_str = format_percent(val2) if val2 is not None else "N/A"
        else:
            val1_str = format_number(val1, 3) if val1 is not None else "N/A"
            val2_str = format_number(val2, 3) if val2 is not None else "N/A"
        
        # Determine winner
        if val1 is not None and val2 is not None:
            if key == 'max_drawdown':
                winner = "1" if val1 > val2 else "2" if val2 > val1 else "="
            else:
                winner = "1" if val1 > val2 else "2" if val2 > val1 else "="
        else:
            winner = "-"
        
        data.append({
            'Metric': label,
            name1: val1_str,
            name2: val2_str,
            'Better': winner
        })
    
    df = pd.DataFrame(data)
    
    # Style the dataframe
    def highlight_better(row):
        styles = [''] * len(row)
        if row['Better'] == '1':
            styles[1] = f'background-color: rgba(16, 185, 129, 0.2)'
        elif row['Better'] == '2':
            styles[2] = f'background-color: rgba(16, 185, 129, 0.2)'
        return styles
    
    styled_df = df.style.apply(highlight_better, axis=1)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_stock_overlap(run1_id: str, run2_id: str):
    """Render stock overlap analysis."""
    render_section_header("Portfolio Overlap", "🔄")
    
    scores1 = load_run_scores(run1_id)
    scores2 = load_run_scores(run2_id)
    
    if not scores1 or not scores2:
        st.info("No score data available for comparison")
        return
    
    # Get top 20 from each
    top1 = set([s['ticker'] for s in sorted(scores1, key=lambda x: x.get('score', 0), reverse=True)[:20]])
    top2 = set([s['ticker'] for s in sorted(scores2, key=lambda x: x.get('score', 0), reverse=True)[:20]])
    
    overlap = top1.intersection(top2)
    only1 = top1 - top2
    only2 = top2 - top1
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Overlap", f"{len(overlap)}/20")
        if overlap:
            st.write("**Common Stocks:**")
            st.write(", ".join(sorted(overlap)))
    
    with col2:
        st.metric("Only in Run 1", len(only1))
        if only1:
            st.write("**Unique to Run 1:**")
            st.write(", ".join(sorted(only1)))
    
    with col3:
        st.metric("Only in Run 2", len(only2))
        if only2:
            st.write("**Unique to Run 2:**")
            st.write(", ".join(sorted(only2)))


def _render_score_comparison(run1_id: str, run2_id: str):
    """Render score comparison for common stocks."""
    render_section_header("Score Comparison", "📈")
    
    scores1 = load_run_scores(run1_id)
    scores2 = load_run_scores(run2_id)
    
    if not scores1 or not scores2:
        st.info("No score data available")
        return
    
    # Create DataFrames
    df1 = pd.DataFrame(scores1).set_index('ticker')[['score', 'rank']]
    df2 = pd.DataFrame(scores2).set_index('ticker')[['score', 'rank']]
    
    # Find common tickers
    common = df1.index.intersection(df2.index)
    
    if len(common) == 0:
        st.info("No common stocks found")
        return
    
    # Compare scores
    comparison = pd.DataFrame({
        'Score (Run 1)': df1.loc[common, 'score'],
        'Score (Run 2)': df2.loc[common, 'score'],
        'Rank (Run 1)': df1.loc[common, 'rank'],
        'Rank (Run 2)': df2.loc[common, 'rank'],
    })
    
    comparison['Score Diff'] = comparison['Score (Run 2)'] - comparison['Score (Run 1)']
    comparison['Rank Diff'] = comparison['Rank (Run 1)'] - comparison['Rank (Run 2)']
    comparison = comparison.sort_values('Score Diff', ascending=False)
    
    # Format
    display_df = comparison.copy()
    display_df['Score (Run 1)'] = display_df['Score (Run 1)'].apply(lambda x: f"{x:.1f}")
    display_df['Score (Run 2)'] = display_df['Score (Run 2)'].apply(lambda x: f"{x:.1f}")
    display_df['Score Diff'] = display_df['Score Diff'].apply(lambda x: f"{x:+.1f}")
    display_df['Rank Diff'] = display_df['Rank Diff'].apply(lambda x: f"{x:+.0f}")
    
    st.dataframe(display_df.head(20), use_container_width=True)
