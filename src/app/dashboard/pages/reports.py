"""
Reports Page
============
View and download analysis reports.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import json

from ..components.sidebar import render_page_header, render_section_header
from ..components.cards import render_info_card
from ..data import (
    load_runs, get_run_folder, get_available_run_folders,
    load_backtest_metrics, load_backtest_returns, load_backtest_positions,
    load_vertical_candidates, load_horizontal_portfolio, load_ai_commentary
)
from ..utils import format_percent, format_number, categorize_file
from ..config import COLORS


def render_reports():
    """Render the reports page."""
    render_page_header(
        "Reports",
        "View and download analysis reports"
    )
    
    # Get available run folders
    run_folders = get_available_run_folders()
    
    if not run_folders:
        st.warning("No report folders found. Run an analysis first!")
        return
    
    # Folder selector
    selected_folder = st.selectbox(
        "Select Run Folder",
        options=[f['name'] for f in run_folders],
        format_func=lambda x: f"📁 {x} ({next((f['file_count'] for f in run_folders if f['name'] == x), 0)} files)"
    )
    
    if not selected_folder:
        return
    
    # Get folder info
    folder_info = next((f for f in run_folders if f['name'] == selected_folder), None)
    
    if not folder_info:
        st.error("Could not load folder info")
        return
    
    folder_path = Path(folder_info['path'])
    run_id = folder_info['run_id']
    
    st.markdown("---")
    
    # Categorize files
    files_by_category = {}
    for f in folder_path.iterdir():
        if f.is_file():
            category = categorize_file(f.name)
            if category not in files_by_category:
                files_by_category[category] = []
            files_by_category[category].append(f)
    
    # Display tabs for each category
    categories = list(files_by_category.keys())
    
    if not categories:
        st.info("No files in this folder")
        return
    
    tabs = st.tabs([c.title() for c in categories])
    
    for tab, category in zip(tabs, categories):
        with tab:
            _render_category_files(files_by_category[category], category, run_id)


def _render_category_files(files: list, category: str, run_id: str):
    """Render files for a category."""
    render_section_header(f"{category.title()} Files", "📄")
    
    for file_path in sorted(files, key=lambda x: x.name):
        with st.expander(f"📄 {file_path.name}"):
            _render_file_preview(file_path)


def _render_file_preview(file_path: Path):
    """Render preview of a file."""
    suffix = file_path.suffix.lower()
    
    if suffix == '.csv':
        _render_csv_preview(file_path)
    elif suffix == '.json':
        _render_json_preview(file_path)
    elif suffix == '.md':
        _render_markdown_preview(file_path)
    elif suffix == '.txt':
        _render_text_preview(file_path)
    else:
        st.write(f"File type: {suffix}")
    
    # Download button
    with open(file_path, 'rb') as f:
        st.download_button(
            f"📥 Download {file_path.name}",
            f.read(),
            file_name=file_path.name,
            key=f"dl_{file_path.name}"
        )


def _render_csv_preview(file_path: Path):
    """Render CSV file preview."""
    try:
        df = pd.read_csv(file_path)
        
        st.write(f"**Rows:** {len(df)} | **Columns:** {len(df.columns)}")
        
        # Format percentage columns
        for col in df.columns:
            if any(x in col.lower() for x in ['return', 'weight', 'pct']):
                if df[col].dtype in ['float64', 'float32']:
                    df[col] = df[col].apply(lambda x: f"{x*100:.2f}%" if pd.notna(x) else "N/A")
        
        st.dataframe(df.head(50), use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.error(f"Error loading CSV: {e}")


def _render_json_preview(file_path: Path):
    """Render JSON file preview."""
    try:
        with open(file_path) as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            # Display as metrics if it looks like metrics
            if any(k in data for k in ['total_return', 'sharpe_ratio', 'win_rate']):
                _render_metrics_json(data)
            else:
                st.json(data)
        else:
            st.json(data)
            
    except Exception as e:
        st.error(f"Error loading JSON: {e}")


def _render_metrics_json(data: dict):
    """Render metrics JSON as formatted display."""
    st.markdown("**Performance Metrics**")
    
    cols = st.columns(4)
    
    # Primary metrics
    metrics = [
        ('Total Return', data.get('total_return'), True),
        ('Sharpe Ratio', data.get('sharpe_ratio'), False),
        ('Win Rate', data.get('win_rate'), True),
        ('Max Drawdown', data.get('max_drawdown'), True),
    ]
    
    for i, (label, value, is_pct) in enumerate(metrics):
        with cols[i]:
            if value is not None:
                if is_pct:
                    st.metric(label, format_percent(value))
                else:
                    st.metric(label, format_number(value))
            else:
                st.metric(label, "N/A")
    
    # Additional metrics
    st.markdown("**Additional Metrics**")
    
    additional = {k: v for k, v in data.items() 
                  if k not in ['total_return', 'sharpe_ratio', 'win_rate', 'max_drawdown']}
    
    if additional:
        cols = st.columns(3)
        for i, (key, value) in enumerate(additional.items()):
            with cols[i % 3]:
                label = key.replace('_', ' ').title()
                if isinstance(value, float):
                    if any(x in key.lower() for x in ['return', 'rate', 'pct', 'weight']):
                        st.metric(label, format_percent(value))
                    else:
                        st.metric(label, format_number(value, 3))
                else:
                    st.metric(label, str(value))


def _render_markdown_preview(file_path: Path):
    """Render Markdown file preview."""
    try:
        with open(file_path) as f:
            content = f.read()
        
        # Limit preview length
        if len(content) > 5000:
            st.markdown(content[:5000] + "\n\n*... (truncated)*")
        else:
            st.markdown(content)
            
    except Exception as e:
        st.error(f"Error loading Markdown: {e}")


def _render_text_preview(file_path: Path):
    """Render text file preview."""
    try:
        with open(file_path) as f:
            content = f.read()
        
        if len(content) > 3000:
            st.code(content[:3000] + "\n\n... (truncated)")
        else:
            st.code(content)
            
    except Exception as e:
        st.error(f"Error loading text: {e}")
