"""
Sidebar Component
=================
Navigation sidebar with quick stats.
"""

import streamlit as st
from typing import Optional

from ..config import PAGES, COLORS
from ..data import load_runs, get_available_run_folders
from ..utils import get_project_root


def render_sidebar() -> str:
    """Render sidebar navigation and return selected page.
    
    Returns:
        Selected page identifier
    """
    # Logo/Title
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <div style="font-size: 2rem;">📈</div>
        <div style="font-size: 1.25rem; font-weight: 700; color: white; margin-top: 0.5rem;">
            Stock Analysis
        </div>
        <div style="font-size: 0.75rem; color: rgba(255,255,255,0.6);">
            ML-Powered Portfolio Optimizer
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    
    # Navigation
    page_labels = [p[0] for p in PAGES]
    selected_label = st.sidebar.radio(
        "Navigation",
        page_labels,
        label_visibility="collapsed"
    )
    
    # Get page identifier
    selected_page = None
    for label, identifier in PAGES:
        if label == selected_label:
            selected_page = identifier
            break
    
    st.sidebar.markdown("---")
    
    # Quick Stats Section
    st.sidebar.markdown("""
    <div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.5); margin-bottom: 0.5rem;">
        Quick Stats
    </div>
    """, unsafe_allow_html=True)
    
    runs = load_runs()
    
    if runs:
        # Total runs
        st.sidebar.metric("Total Runs", len(runs))
        
        # Completed runs
        completed = sum(1 for r in runs if r['status'] == 'completed')
        st.sidebar.metric("Completed", completed)
        
        # Latest run
        latest = runs[0]
        latest_name = latest.get('name') or latest['run_id'][:8]
        st.sidebar.markdown(f"""
        <div style="background: rgba(255,255,255,0.05); padding: 0.75rem; border-radius: 8px; margin-top: 0.5rem;">
            <div style="font-size: 0.7rem; color: rgba(255,255,255,0.5); text-transform: uppercase;">Latest Run</div>
            <div style="font-size: 0.9rem; color: white; font-weight: 500; margin-top: 0.25rem;">{latest_name}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Run folders
        run_folders = get_available_run_folders()
        if run_folders:
            st.sidebar.metric("Output Folders", len(run_folders))
    else:
        st.sidebar.info("No runs yet")
    
    st.sidebar.markdown("---")
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()
    
    # Version info
    st.sidebar.markdown("""
    <div style="position: absolute; bottom: 1rem; left: 1rem; right: 1rem;">
        <div style="font-size: 0.7rem; color: rgba(255,255,255,0.4); text-align: center;">
            v3.0.0 · Mid-term Stock Planner
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    return selected_label


def render_page_header(title: str, subtitle: Optional[str] = None, show_refresh: bool = True):
    """Render a page header with optional refresh button.
    
    Args:
        title: Page title
        subtitle: Optional subtitle
        show_refresh: Whether to show refresh button
    """
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.markdown(f'<h1 class="main-header">{title}</h1>', unsafe_allow_html=True)
        if subtitle:
            st.markdown(f'<p style="color: {COLORS["muted"]}; margin-top: -0.5rem;">{subtitle}</p>', 
                       unsafe_allow_html=True)
    
    with col2:
        if show_refresh:
            if st.button("🔄 Refresh", use_container_width=True, key=f"refresh_{title}"):
                st.cache_data.clear()
                st.cache_resource.clear()
                st.rerun()


def render_section_header(title: str, icon: str = ""):
    """Render a section header.
    
    Args:
        title: Section title
        icon: Optional emoji icon
    """
    icon_html = f"{icon} " if icon else ""
    st.markdown(f'<h2 class="sub-header">{icon_html}{title}</h2>', unsafe_allow_html=True)
