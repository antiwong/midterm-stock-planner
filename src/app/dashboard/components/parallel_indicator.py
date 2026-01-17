"""
Parallel Processing Indicator
=============================
GUI component to show parallel processing status.
"""

import streamlit as st
from typing import Optional


def render_parallel_indicator(
    is_parallel: bool,
    max_workers: Optional[int] = None,
    current_batch: Optional[int] = None,
    total_batches: Optional[int] = None
):
    """
    Render parallel processing indicator.
    
    Args:
        is_parallel: Whether parallel processing is enabled
        max_workers: Maximum number of workers
        current_batch: Current batch number (if processing in batches)
        total_batches: Total number of batches
    """
    if is_parallel:
        col1, col2 = st.columns([3, 1])
        with col1:
            if current_batch and total_batches:
                st.info(f"⚡ Parallel processing: Batch {current_batch}/{total_batches} (max_workers: {max_workers or 'auto'})")
            else:
                st.info(f"⚡ Parallel processing enabled (max_workers: {max_workers or 'auto'})")
        with col2:
            st.metric("Workers", max_workers or "Auto")


def render_parallel_progress(
    completed: int,
    total: int,
    failed: int = 0
):
    """
    Render parallel processing progress.
    
    Args:
        completed: Number of items completed
        total: Total number of items
        failed: Number of items that failed
    """
    progress = completed / total if total > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Progress", f"{completed}/{total}", f"{progress*100:.1f}%")
    with col2:
        st.metric("Completed", completed)
    with col3:
        st.metric("Failed", failed, delta_color="inverse" if failed > 0 else "normal")
    
    st.progress(progress)
