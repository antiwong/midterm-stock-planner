"""
Analysis Runs Page
==================
Browse and manage analysis runs.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from ..components.sidebar import render_page_header, render_section_header
from ..components.tables import render_runs_table
from ..components.cards import render_run_card, render_alert
from ..data import load_runs, delete_run, get_run_summary
from ..utils import format_percent, format_number, format_date
from ..config import COLORS


def render_analysis_runs():
    """Render the analysis runs page."""
    render_page_header(
        "Analysis Runs",
        "View and manage your backtest and analysis runs"
    )
    
    runs = load_runs()
    
    if not runs:
        st.info("No analysis runs found. Run a backtest first!")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "completed", "running", "failed", "pending"],
            index=0
        )
    
    with col2:
        run_type_filter = st.selectbox(
            "Type",
            ["All"] + list(set(r.get('run_type', 'backtest') for r in runs)),
            index=0
        )
    
    with col3:
        search = st.text_input("Search", placeholder="Run ID or name...")
    
    # Apply filters
    filtered_runs = runs
    
    if status_filter != "All":
        filtered_runs = [r for r in filtered_runs if r['status'] == status_filter]
    
    if run_type_filter != "All":
        filtered_runs = [r for r in filtered_runs if r.get('run_type') == run_type_filter]
    
    if search:
        search_lower = search.lower()
        filtered_runs = [
            r for r in filtered_runs
            if search_lower in r['run_id'].lower() or 
               (r.get('name') and search_lower in r['name'].lower())
        ]
    
    st.markdown(f"**{len(filtered_runs)}** runs found")
    st.markdown("---")
    
    # Display runs
    if not filtered_runs:
        st.info("No runs match your filters")
        return
    
    # Convert to DataFrame for table view
    df = pd.DataFrame(filtered_runs)
    
    # Select columns
    display_cols = ['run_id', 'name', 'run_type', 'status', 'created_at',
                    'total_return', 'sharpe_ratio', 'win_rate', 'max_drawdown', 'universe_count']
    display_cols = [c for c in display_cols if c in df.columns]
    
    display_df = df[display_cols].copy()
    
    # Format
    display_df['run_id_short'] = display_df['run_id'].str[:12] + '...'
    if 'created_at' in display_df.columns:
        display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
    
    for col in ['total_return', 'win_rate', 'max_drawdown']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: f"{x*100:+.1f}%" if pd.notna(x) else "N/A"
            )
    
    if 'sharpe_ratio' in display_df.columns:
        display_df['sharpe_ratio'] = display_df['sharpe_ratio'].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
        )
    
    # Display table
    st.dataframe(
        display_df.drop(columns=['run_id']).rename(columns={'run_id_short': 'run_id'}),
        use_container_width=True,
        hide_index=True
    )
    
    # Run details section
    st.markdown("---")
    render_section_header("Run Details", "🔍")
    
    selected_run_id = st.selectbox(
        "Select a run to view details",
        options=[r['run_id'] for r in filtered_runs],
        format_func=lambda x: f"{x[:12]}... - {next((r.get('name') or 'Unnamed' for r in filtered_runs if r['run_id'] == x), 'Unknown')}"
    )
    
    if selected_run_id:
        summary = get_run_summary(selected_run_id)
        run = summary.get('run', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Run Information**")
            st.write(f"- **ID:** {run.get('run_id', 'N/A')}")
            st.write(f"- **Name:** {run.get('name') or 'Unnamed'}")
            st.write(f"- **Type:** {run.get('run_type', 'backtest')}")
            st.write(f"- **Status:** {run.get('status', 'unknown')}")
            st.write(f"- **Created:** {format_date(run.get('created_at'))}")
            st.write(f"- **Stocks:** {run.get('universe_count', 'N/A')}")
        
        with col2:
            st.markdown("**Performance Metrics**")
            st.write(f"- **Total Return:** {format_percent(run.get('total_return'))}")
            st.write(f"- **Sharpe Ratio:** {format_number(run.get('sharpe_ratio'))}")
            st.write(f"- **Win Rate:** {format_percent(run.get('win_rate'), with_sign=False)}")
            st.write(f"- **Max Drawdown:** {format_percent(run.get('max_drawdown'))}")
            st.write(f"- **Volatility:** {format_percent(run.get('volatility'), with_sign=False)}")
        
        # Output folder info
        if summary.get('has_folder'):
            st.success(f"📁 Output folder exists with {len(summary.get('files', []))} files")
            
            with st.expander("View Files"):
                for f in summary.get('files', []):
                    st.write(f"- {f}")
        else:
            st.warning("📁 No output folder found for this run")
        
        # Stages status
        stages = summary.get('stages', {})
        st.markdown("**Analysis Stages**")
        stage_cols = st.columns(4)
        
        with stage_cols[0]:
            st.write("Backtest:", "✅" if stages.get('backtest') else "❌")
        with stage_cols[1]:
            st.write("Enrichment:", "✅" if stages.get('enrichment') else "❌")
        with stage_cols[2]:
            st.write("Domain Analysis:", "✅" if stages.get('domain_analysis') else "❌")
        with stage_cols[3]:
            st.write("AI Analysis:", "✅" if stages.get('ai_analysis') else "❌")
        
        # Delete button
        st.markdown("---")
        if st.button("🗑️ Delete This Run", type="secondary"):
            if st.checkbox("I confirm I want to delete this run"):
                try:
                    delete_run(selected_run_id)
                    st.success("Run deleted successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete run: {e}")
