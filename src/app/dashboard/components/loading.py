"""
Loading Indicators and Progress Components
==========================================
Enhanced loading indicators and progress feedback for better UX.
"""

import streamlit as st
import time
from typing import Optional, Callable, Any
from contextlib import contextmanager


@contextmanager
def loading_spinner(message: str = "Loading...", show_progress: bool = False):
    """Context manager for showing loading spinner with optional progress.
    
    Args:
        message: Loading message to display
        show_progress: Whether to show progress bar
    """
    if show_progress:
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text(message)
        
        try:
            yield progress_bar, status_text
        finally:
            progress_bar.empty()
            status_text.empty()
    else:
        with st.spinner(message):
            yield None, None


def render_progress_bar(current: int, total: int, label: str = "Progress"):
    """Render a progress bar with percentage.
    
    Args:
        current: Current progress value
        total: Total value
        label: Label to display
    """
    progress = current / total if total > 0 else 0
    st.progress(progress)
    st.caption(f"{label}: {current}/{total} ({progress*100:.1f}%)")


def render_loading_card(message: str, icon: str = "⏳"):
    """Render a styled loading card.
    
    Args:
        message: Loading message
        icon: Icon to display
    """
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        color: white;
        margin: 1rem 0;
    ">
        <div style="font-size: 3rem; margin-bottom: 1rem;">{icon}</div>
        <div style="font-size: 1.2rem; font-weight: 500;">{message}</div>
        <div style="margin-top: 1rem;">
            <div class="spinner" style="
                border: 4px solid rgba(255, 255, 255, 0.3);
                border-top: 4px solid white;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            "></div>
        </div>
    </div>
    <style>
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
    """, unsafe_allow_html=True)


def render_stage_progress(stage: str, current_stage: int, total_stages: int):
    """Render progress for multi-stage operations.
    
    Args:
        stage: Current stage name
        current_stage: Current stage number (1-indexed)
        total_stages: Total number of stages
    """
    progress = current_stage / total_stages if total_stages > 0 else 0
    
    st.markdown(f"""
    <div style="
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <span style="font-weight: 600;">Stage {current_stage}/{total_stages}: {stage}</span>
            <span style="color: #667eea; font-weight: 600;">{progress*100:.0f}%</span>
        </div>
        <div style="
            background: #e9ecef;
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
        ">
            <div style="
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                height: 100%;
                width: {progress*100}%;
                transition: width 0.3s ease;
            "></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


@contextmanager
def operation_with_feedback(operation_name: str, show_progress: bool = True):
    """Context manager for operations with loading feedback.
    
    Args:
        operation_name: Name of the operation
        show_progress: Whether to show progress indicator
    """
    start_time = time.time()
    
    if show_progress:
        status_placeholder = st.empty()
        status_placeholder.info(f"🔄 {operation_name}...")
    
    try:
        yield
        elapsed = time.time() - start_time
        
        if show_progress:
            status_placeholder.success(f"✅ {operation_name} completed in {elapsed:.1f}s")
            time.sleep(0.5)  # Show success message briefly
            status_placeholder.empty()
    except Exception as e:
        if show_progress:
            status_placeholder.error(f"❌ {operation_name} failed: {str(e)}")
        raise
