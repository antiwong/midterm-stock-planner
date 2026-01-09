"""
Table Components
================
Styled table and dataframe components.
"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Dict, Any

from ..config import COLORS
from ..utils import format_percent, format_number, format_date


def render_styled_dataframe(
    df: pd.DataFrame,
    height: Optional[int] = None,
    hide_index: bool = True,
    column_config: Optional[Dict] = None,
    selection_mode: Optional[str] = None
):
    """Render a styled dataframe.
    
    Args:
        df: DataFrame to display
        height: Optional fixed height
        hide_index: Whether to hide index
        column_config: Column configuration dict
        selection_mode: 'single', 'multi', or None
    """
    if df.empty:
        st.info("No data to display")
        return None
    
    # Default column config
    if column_config is None:
        column_config = {}
    
    # Auto-configure percentage columns
    for col in df.columns:
        col_lower = col.lower()
        if any(x in col_lower for x in ['return', 'rate', 'percent', 'pct', 'weight']):
            if col not in column_config:
                column_config[col] = st.column_config.NumberColumn(
                    col,
                    format="%.2f%%"
                )
        elif any(x in col_lower for x in ['score', 'ratio', 'sharpe', 'sortino']):
            if col not in column_config:
                column_config[col] = st.column_config.NumberColumn(
                    col,
                    format="%.2f"
                )
        elif any(x in col_lower for x in ['date', 'created', 'updated', 'time']):
            if col not in column_config:
                column_config[col] = st.column_config.DatetimeColumn(
                    col,
                    format="YYYY-MM-DD HH:mm"
                )
    
    # Display with or without selection
    if selection_mode:
        return st.dataframe(
            df,
            height=height,
            hide_index=hide_index,
            column_config=column_config,
            use_container_width=True,
            selection_mode=selection_mode
        )
    else:
        st.dataframe(
            df,
            height=height,
            hide_index=hide_index,
            column_config=column_config,
            use_container_width=True
        )
        return None


def render_score_table(
    scores: List[Dict[str, Any]],
    show_columns: Optional[List[str]] = None,
    max_rows: int = 20,
    sort_by: str = 'rank'
):
    """Render a stock scores table.
    
    Args:
        scores: List of score dictionaries
        show_columns: Columns to display
        max_rows: Maximum rows to show
        sort_by: Column to sort by
    """
    if not scores:
        st.info("No scores to display")
        return
    
    df = pd.DataFrame(scores)
    
    # Default columns
    if show_columns is None:
        show_columns = ['rank', 'ticker', 'sector', 'score', 'tech_score', 
                        'fund_score', 'sent_score', 'return_21d']
    
    # Filter to available columns
    show_columns = [c for c in show_columns if c in df.columns]
    
    if not show_columns:
        show_columns = df.columns.tolist()[:8]
    
    display_df = df[show_columns].head(max_rows).copy()
    
    # Sort
    if sort_by in display_df.columns:
        display_df = display_df.sort_values(sort_by)
    
    # Format columns
    for col in display_df.columns:
        if col in ['score', 'tech_score', 'fund_score', 'sent_score']:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
        elif 'return' in col.lower():
            display_df[col] = display_df[col].apply(lambda x: f"{x*100:+.1f}%" if pd.notna(x) else "N/A")
    
    # Custom styling
    column_config = {
        'rank': st.column_config.NumberColumn("Rank", width="small"),
        'ticker': st.column_config.TextColumn("Ticker", width="small"),
        'sector': st.column_config.TextColumn("Sector", width="medium"),
        'score': st.column_config.TextColumn("Score", width="small"),
    }
    
    render_styled_dataframe(display_df, column_config=column_config)


def render_runs_table(
    runs: List[Dict[str, Any]],
    max_rows: int = 20,
    selectable: bool = False
) -> Optional[str]:
    """Render a runs table.
    
    Args:
        runs: List of run dictionaries
        max_rows: Maximum rows to show
        selectable: Whether rows are selectable
    
    Returns:
        Selected run_id if selectable, else None
    """
    if not runs:
        st.info("No runs to display")
        return None
    
    df = pd.DataFrame(runs).head(max_rows)
    
    # Select display columns
    display_cols = ['run_id', 'name', 'status', 'created_at', 
                    'total_return', 'sharpe_ratio', 'win_rate', 'universe_count']
    display_cols = [c for c in display_cols if c in df.columns]
    
    display_df = df[display_cols].copy()
    
    # Format
    display_df['run_id'] = display_df['run_id'].str[:12] + '...'
    if 'created_at' in display_df.columns:
        display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
    if 'total_return' in display_df.columns:
        display_df['total_return'] = display_df['total_return'].apply(lambda x: f"{x*100:+.1f}%" if pd.notna(x) else "N/A")
    if 'sharpe_ratio' in display_df.columns:
        display_df['sharpe_ratio'] = display_df['sharpe_ratio'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
    if 'win_rate' in display_df.columns:
        display_df['win_rate'] = display_df['win_rate'].apply(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A")
    
    column_config = {
        'run_id': st.column_config.TextColumn("Run ID", width="medium"),
        'name': st.column_config.TextColumn("Name", width="medium"),
        'status': st.column_config.TextColumn("Status", width="small"),
        'created_at': st.column_config.TextColumn("Created", width="medium"),
        'total_return': st.column_config.TextColumn("Return", width="small"),
        'sharpe_ratio': st.column_config.TextColumn("Sharpe", width="small"),
        'win_rate': st.column_config.TextColumn("Win Rate", width="small"),
        'universe_count': st.column_config.NumberColumn("Stocks", width="small"),
    }
    
    if selectable:
        selection = render_styled_dataframe(
            display_df,
            column_config=column_config,
            selection_mode="single-row"
        )
        if selection and selection.get('selection', {}).get('rows'):
            row_idx = selection['selection']['rows'][0]
            return runs[row_idx]['run_id']
        return None
    else:
        render_styled_dataframe(display_df, column_config=column_config)
        return None


def render_portfolio_table(
    holdings: List[Dict[str, Any]],
    show_weight: bool = True,
    show_returns: bool = True
):
    """Render a portfolio holdings table.
    
    Args:
        holdings: List of holding dictionaries
        show_weight: Whether to show weight column
        show_returns: Whether to show return column
    """
    if not holdings:
        st.info("No holdings to display")
        return
    
    df = pd.DataFrame(holdings)
    
    # Build column list
    columns = ['ticker', 'sector']
    if show_weight and 'weight' in df.columns:
        columns.append('weight')
    if 'score' in df.columns:
        columns.append('score')
    if show_returns:
        for col in ['return_1d', 'return_5d', 'return_21d']:
            if col in df.columns:
                columns.append(col)
    
    columns = [c for c in columns if c in df.columns]
    display_df = df[columns].copy()
    
    # Format
    if 'weight' in display_df.columns:
        display_df['weight'] = display_df['weight'].apply(lambda x: f"{x*100:.1f}%")
    
    for col in display_df.columns:
        if 'return' in col.lower():
            display_df[col] = display_df[col].apply(lambda x: f"{x*100:+.1f}%" if pd.notna(x) else "N/A")
    
    column_config = {
        'ticker': st.column_config.TextColumn("Ticker", width="small"),
        'sector': st.column_config.TextColumn("Sector", width="medium"),
        'weight': st.column_config.TextColumn("Weight", width="small"),
        'score': st.column_config.NumberColumn("Score", format="%.1f", width="small"),
    }
    
    render_styled_dataframe(display_df, column_config=column_config)


def render_comparison_table(
    runs: List[Dict[str, Any]],
    metrics: List[str] = None
):
    """Render a comparison table for multiple runs.
    
    Args:
        runs: List of run dictionaries
        metrics: Metrics to compare
    """
    if not runs:
        st.info("No runs to compare")
        return
    
    if metrics is None:
        metrics = ['total_return', 'sharpe_ratio', 'sortino_ratio', 'max_drawdown', 
                   'win_rate', 'volatility', 'calmar_ratio']
    
    # Build comparison data
    data = {'Metric': metrics}
    
    for run in runs:
        name = run.get('name') or run['run_id'][:8]
        values = []
        for m in metrics:
            val = run.get(m)
            if val is None:
                values.append("N/A")
            elif m in ['total_return', 'win_rate', 'max_drawdown', 'volatility']:
                values.append(f"{val*100:.2f}%")
            else:
                values.append(f"{val:.3f}")
        data[name] = values
    
    df = pd.DataFrame(data)
    
    # Style metric names
    df['Metric'] = df['Metric'].str.replace('_', ' ').str.title()
    
    st.dataframe(df, hide_index=True, use_container_width=True)
