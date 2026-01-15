"""
Sidebar Component
=================
Navigation sidebar with quick stats.
"""

import streamlit as st
from typing import Optional

from ..config import PAGES, MAIN_WORKFLOW, STANDALONE_TOOLS, ADVANCED_ANALYTICS, UTILITIES, COLORS
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
    
    # Initialize session state for navigation
    if 'selected_nav_item' not in st.session_state:
        st.session_state.selected_nav_item = MAIN_WORKFLOW[0][0]
    
    # Track all pages for lookup
    all_pages = MAIN_WORKFLOW + STANDALONE_TOOLS + ADVANCED_ANALYTICS + UTILITIES
    
    # Find current selection across all groups
    current_selection = st.session_state.selected_nav_item
    
    # Determine which group the current selection belongs to
    current_group = None
    if current_selection in [p[0] for p in MAIN_WORKFLOW]:
        current_group = 'main'
    elif current_selection in [p[0] for p in STANDALONE_TOOLS]:
        current_group = 'tools'
    elif current_selection in [p[0] for p in ADVANCED_ANALYTICS]:
        current_group = 'advanced'
    elif current_selection in [p[0] for p in UTILITIES]:
        current_group = 'utils'
    else:
        current_group = 'main'  # Default
    
    # Main Workflow Section
    st.sidebar.markdown("""
    <div style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.5); margin-bottom: 0.5rem; margin-top: 0.5rem;">
        Main Workflow
    </div>
    """, unsafe_allow_html=True)
    
    # Main Workflow Section - Use buttons for better control
    for label, identifier in MAIN_WORKFLOW:
        is_selected = (label == current_selection)
        button_type = "primary" if is_selected else "secondary"
        if st.sidebar.button(
            label,
            key=f"nav_btn_{identifier}",
            use_container_width=True,
            type=button_type
        ):
            st.session_state.selected_nav_item = label
            st.rerun()
    
    # Standalone Tools Section
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.5); margin-bottom: 0.5rem; margin-top: 0.5rem;">
        Tools
    </div>
    """, unsafe_allow_html=True)
    
    # Tools Section - Use buttons
    for label, identifier in STANDALONE_TOOLS:
        is_selected = (label == current_selection)
        button_type = "primary" if is_selected else "secondary"
        if st.sidebar.button(
            label,
            key=f"nav_btn_{identifier}",
            use_container_width=True,
            type=button_type
        ):
            st.session_state.selected_nav_item = label
            st.rerun()
    
    # Advanced Analytics Section
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.5); margin-bottom: 0.5rem; margin-top: 0.5rem;">
        Advanced Analytics
    </div>
    """, unsafe_allow_html=True)
    
    # Advanced Analytics Section - Use buttons
    for label, identifier in ADVANCED_ANALYTICS:
        is_selected = (label == current_selection)
        button_type = "primary" if is_selected else "secondary"
        if st.sidebar.button(
            label,
            key=f"nav_btn_{identifier}",
            use_container_width=True,
            type=button_type
        ):
            st.session_state.selected_nav_item = label
            st.rerun()
    
    # Utilities Section
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.5); margin-bottom: 0.5rem; margin-top: 0.5rem;">
        Utilities
    </div>
    """, unsafe_allow_html=True)
    
    # Utilities Section - Use buttons
    for label, identifier in UTILITIES:
        is_selected = (label == current_selection)
        button_type = "primary" if is_selected else "secondary"
        if st.sidebar.button(
            label,
            key=f"nav_btn_{identifier}",
            use_container_width=True,
            type=button_type
        ):
            st.session_state.selected_nav_item = label
            st.rerun()
    
    # Get the final selected label (this is what app.py expects)
    selected_label = st.session_state.selected_nav_item
    
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
