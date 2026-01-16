"""
Lazy Chart Loading Components
==============================
Components for lazy-loading charts to improve initial page load performance.
"""

import streamlit as st
from typing import Callable, Any, Optional
import time


def lazy_chart_container(
    chart_key: str,
    chart_func: Callable[[], Any],
    label: str = "📊 Show Chart",
    default_expanded: bool = False,
    loading_message: str = "Loading chart..."
) -> Optional[Any]:
    """
    Render a chart lazily inside an expander.
    
    Args:
        chart_key: Unique key for this chart (for session state)
        chart_func: Function that returns the chart/plotly figure
        label: Label for the expander
        default_expanded: Whether to expand by default
        loading_message: Message to show while loading
        
    Returns:
        The chart result if expanded, None otherwise
    """
    # Initialize session state
    if chart_key not in st.session_state:
        st.session_state[chart_key] = default_expanded
    
    # Expander for lazy loading
    with st.expander(label, expanded=st.session_state[chart_key]):
        if st.session_state[chart_key] or st.session_state.get(f"{chart_key}_force_load", False):
            with st.spinner(loading_message):
                try:
                    chart = chart_func()
                    return chart
                except Exception as e:
                    st.error(f"Error loading chart: {e}")
                    return None
        else:
            st.info("Click to expand and load chart")
            if st.button(f"Load {label}", key=f"{chart_key}_load_btn"):
                st.session_state[chart_key] = True
                st.rerun()
    
    return None


def lazy_chart_tab(
    chart_key: str,
    chart_func: Callable[[], Any],
    tab_label: str,
    loading_message: str = "Loading chart..."
) -> Optional[Any]:
    """
    Render a chart lazily in a tab (only loads when tab is selected).
    
    Args:
        chart_key: Unique key for this chart
        chart_func: Function that returns the chart/plotly figure
        tab_label: Label for the tab
        loading_message: Message to show while loading
        
    Returns:
        The chart result if tab is active, None otherwise
    """
    # Check if this tab was just selected
    if chart_key not in st.session_state:
        st.session_state[chart_key] = False
    
    # Only load if tab is active (checked by parent tab container)
    if st.session_state.get(f"{chart_key}_active", False):
        with st.spinner(loading_message):
            try:
                chart = chart_func()
                return chart
            except Exception as e:
                st.error(f"Error loading chart: {e}")
                return None
    
    return None


def chart_placeholder(
    chart_key: str,
    placeholder_text: str = "Chart will load when expanded",
    load_button_text: str = "Load Chart"
) -> bool:
    """
    Show a placeholder that can be clicked to load a chart.
    
    Args:
        chart_key: Unique key for this chart
        placeholder_text: Text to show in placeholder
        load_button_text: Text for load button
        
    Returns:
        True if chart should be loaded, False otherwise
    """
    if chart_key not in st.session_state:
        st.session_state[chart_key] = False
    
    if st.session_state[chart_key]:
        return True
    
    st.info(placeholder_text)
    if st.button(load_button_text, key=f"{chart_key}_placeholder_btn"):
        st.session_state[chart_key] = True
        st.rerun()
    
    return False
