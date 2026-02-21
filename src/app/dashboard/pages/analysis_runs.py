"""
Analysis Runs Page
==================
Browse and manage analysis runs.
"""

import os
import subprocess

import streamlit as st
import pandas as pd
from datetime import datetime

from ..components.sidebar import render_page_header, render_section_header
from ..utils import get_project_root
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
    
    # Filters and Search
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "completed", "running", "failed", "pending"],
            index=0,
            key="runs_status_filter"
        )
    
    with col2:
        run_type_filter = st.selectbox(
            "Type",
            ["All"] + sorted(list(set(r.get('run_type', 'backtest') for r in runs))),
            index=0,
            key="runs_type_filter"
        )
    
    with col3:
        search = st.text_input(
            "🔍 Search", 
            placeholder="Run ID, name, or watchlist...",
            key="runs_search"
        )
    
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        clear_filters = st.button("Clear", key="clear_runs_filters", use_container_width=True)
        if clear_filters:
            st.session_state.runs_status_filter = "All"
            st.session_state.runs_type_filter = "All"
            st.session_state.runs_search = ""
            st.rerun()
    
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
               (r.get('name') and search_lower in r.get('name', '').lower()) or
               (r.get('watchlist') and search_lower in r.get('watchlist', '').lower())
        ]
    
    # Pagination
    items_per_page = st.slider("Items per page", 10, 100, 25, key="runs_per_page")
    total_pages = (len(filtered_runs) + items_per_page - 1) // items_per_page if filtered_runs else 1
    page_num = st.number_input("Page", min_value=1, max_value=max(1, total_pages), value=1, key="runs_page")
    
    start_idx = (page_num - 1) * items_per_page
    end_idx = start_idx + items_per_page
    paginated_runs = filtered_runs[start_idx:end_idx]
    
    # Display summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Runs", len(filtered_runs))
    with col2:
        st.metric("Showing", f"{start_idx + 1}-{min(end_idx, len(filtered_runs))}")
    with col3:
        st.metric("Page", f"{page_num}/{total_pages}")
    
    st.markdown("---")
    
    # Bulk export section
    if filtered_runs:
        st.markdown("### Bulk Export")
        
        # Multi-select runs for export
        run_options = {f"{r.get('name', r['run_id'][:16])} ({r['run_id'][:8]})": r['run_id'] 
                      for r in filtered_runs}
        selected_for_export = st.multiselect(
            "Select Runs to Export",
            options=list(run_options.keys()),
            default=[],
            help="Select multiple runs to export together"
        )
        
        if selected_for_export:
            export_col1, export_col2, export_col3 = st.columns([1, 1, 2])
            
            with export_col1:
                if st.button("📥 Export Selected (CSV)", key="export_selected_csv", use_container_width=True):
                    selected_run_ids = [run_options[label] for label in selected_for_export]
                    selected_runs_data = [r for r in filtered_runs if r['run_id'] in selected_run_ids]
                    df_export = pd.DataFrame(selected_runs_data)
                    csv = df_export.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"runs_bulk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="download_selected_csv"
                    )
            
            with export_col2:
                if st.button("📥 Export Selected (ZIP)", key="export_selected_zip", use_container_width=True):
                    import zipfile
                    import io
                    from ..data import get_run_folder
                    from pathlib import Path
                    
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        selected_run_ids = [run_options[label] for label in selected_for_export]
                        for run_id in selected_run_ids:
                            run_folder = get_run_folder(run_id)
                            if run_folder and run_folder.exists():
                                # Add all files from run folder
                                for file_path in run_folder.glob("*"):
                                    if file_path.is_file():
                                        zip_file.write(file_path, f"{run_id}/{file_path.name}")
                    
                    zip_buffer.seek(0)
                    st.download_button(
                        label="Download ZIP",
                        data=zip_buffer.read(),
                        file_name=f"runs_bulk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip",
                        key="download_selected_zip"
                    )
        
        # Single export buttons (all filtered runs)
        st.markdown("---")
        export_col1, export_col2, export_col3 = st.columns([1, 1, 2])
        with export_col1:
            if st.button("📥 Export All (CSV)", key="export_runs_csv", use_container_width=True):
                df_export = pd.DataFrame(filtered_runs)
                csv = df_export.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"runs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_runs_csv"
                )
        with export_col2:
            if st.button("📥 Export All (JSON)", key="export_runs_json", use_container_width=True):
                import json
                json_data = json.dumps(filtered_runs, indent=2, default=str)
                st.download_button(
                    label="Download JSON",
                    data=json_data,
                    file_name=f"runs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    key="download_runs_json"
                )
    
    # Display runs
    if not paginated_runs:
        st.info("No runs match your filters")
        return
    
    # Convert to DataFrame for table view
    df = pd.DataFrame(paginated_runs)
    
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
        
        # Backtest config (from run_info.json)
        run_info = summary.get('run_info', {})
        config_cfg = run_info.get('config', {})
        if config_cfg:
            step_val = config_cfg.get('step_value')
            step_unit = config_cfg.get('step_unit')
            step_str = f"{step_val} {step_unit}" if step_val is not None and step_unit else None
            if step_str:
                st.markdown("**Backtest Config**")
                st.write(f"- Train: {config_cfg.get('train_years', 'N/A')}y · Test: {config_cfg.get('test_years', 'N/A')}y")
                st.write(f"- **Step: {step_str}**")
        
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
        
        # Actions: Strengthen, Delete
        st.markdown("---")
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if st.button("🛡️ Strengthen Recommendations", key="analysis_runs_strengthen", use_container_width=True):
                _run_strengthen(selected_run_id)
        with action_col2:
            if st.button("🗑️ Delete This Run", type="secondary"):
                if st.checkbox("I confirm I want to delete this run"):
                    try:
                        delete_run(selected_run_id)
                        st.success("Run deleted successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete run: {e}")


def _run_strengthen(run_id: str):
    """Run strengthen_recommendations.py for the given run."""
    output_area = st.empty()
    cwd = str(get_project_root())
    env = os.environ.copy()
    env['PYTHONPATH'] = cwd + os.pathsep + env.get('PYTHONPATH', '')
    cmd = ["python", "scripts/strengthen_recommendations.py", "--run-id", run_id]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=cwd,
        env=env,
    )
    output_lines = []
    for line in iter(process.stdout.readline, ''):
        output_lines.append(line)
        output_area.code(''.join(output_lines[-30:]), language='text')
    process.wait()
    if process.returncode == 0:
        st.success("✅ Strengthen analysis completed! Report saved to run folder.")
    else:
        st.error(f"❌ Failed with code {process.returncode}")
