"""
Progressive Chart Loading Components
====================================
Components for progressively loading charts to improve performance.
"""

import streamlit as st
import plotly.graph_objects as go
from typing import Callable, Any, Optional, List, Dict
import time


def progressive_chart_loader(
    chart_key: str,
    chart_funcs: List[Callable[[], go.Figure]],
    chart_labels: List[str],
    loading_strategy: str = "sequential",
    batch_size: int = 2
) -> List[Optional[go.Figure]]:
    """
    Load multiple charts progressively to improve performance.
    
    Args:
        chart_key: Base key for session state
        chart_funcs: List of functions that return chart figures
        chart_labels: List of labels for each chart
        loading_strategy: "sequential" (one at a time) or "batch" (load in batches)
        batch_size: Number of charts to load per batch (for batch strategy)
        
    Returns:
        List of chart figures (None for charts not yet loaded)
    """
    if len(chart_funcs) != len(chart_labels):
        raise ValueError("chart_funcs and chart_labels must have same length")
    
    num_charts = len(chart_funcs)
    
    # Initialize session state
    if f"{chart_key}_loaded_count" not in st.session_state:
        st.session_state[f"{chart_key}_loaded_count"] = 0
    
    loaded_count = st.session_state[f"{chart_key}_loaded_count"]
    
    results = []
    
    if loading_strategy == "sequential":
        # Load charts one at a time
        for i, (chart_func, label) in enumerate(zip(chart_funcs, chart_labels)):
            if i < loaded_count:
                # Already loaded
                with st.spinner(f"Loading {label}..."):
                    try:
                        fig = chart_func()
                        st.plotly_chart(fig, use_container_width=True)
                        results.append(fig)
                    except Exception as e:
                        st.error(f"Error loading {label}: {e}")
                        results.append(None)
            elif i == loaded_count:
                # Current chart to load
                if st.button(f"Load {label}", key=f"{chart_key}_load_{i}"):
                    with st.spinner(f"Loading {label}..."):
                        try:
                            fig = chart_func()
                            st.plotly_chart(fig, use_container_width=True)
                            results.append(fig)
                            st.session_state[f"{chart_key}_loaded_count"] = i + 1
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error loading {label}: {e}")
                            results.append(None)
                else:
                    st.info(f"Click to load {label}")
                    results.append(None)
            else:
                # Not yet loaded
                results.append(None)
    
    elif loading_strategy == "batch":
        # Load charts in batches
        current_batch = loaded_count // batch_size
        batch_start = current_batch * batch_size
        batch_end = min(batch_start + batch_size, num_charts)
        
        # Load charts in current batch
        for i in range(batch_start, batch_end):
            if i < loaded_count:
                # Already loaded
                with st.spinner(f"Loading {chart_labels[i]}..."):
                    try:
                        fig = chart_funcs[i]()
                        st.plotly_chart(fig, use_container_width=True)
                        results.append(fig)
                    except Exception as e:
                        st.error(f"Error loading {chart_labels[i]}: {e}")
                        results.append(None)
            else:
                # Load now
                with st.spinner(f"Loading {chart_labels[i]}..."):
                    try:
                        fig = chart_funcs[i]()
                        st.plotly_chart(fig, use_container_width=True)
                        results.append(fig)
                        st.session_state[f"{chart_key}_loaded_count"] = i + 1
                    except Exception as e:
                        st.error(f"Error loading {chart_labels[i]}: {e}")
                        results.append(None)
        
        # Load more button if there are more charts
        if batch_end < num_charts:
            remaining = num_charts - batch_end
            next_batch_size = min(batch_size, remaining)
            if st.button(f"Load Next {next_batch_size} Chart(s)", key=f"{chart_key}_load_batch_{current_batch + 1}"):
                st.session_state[f"{chart_key}_loaded_count"] = batch_end
                st.rerun()
    
    return results


def optimized_chart(
    chart_func: Callable[[], go.Figure],
    data_points: int,
    max_points: int = 1000,
    downsample: bool = True,
    downsample_func: Optional[Callable] = None
) -> go.Figure:
    """
    Optimize chart rendering for large datasets by downsampling if needed.
    
    Args:
        chart_func: Function that returns the chart figure
        data_points: Number of data points in the dataset
        max_points: Maximum number of points to render (for performance)
        downsample: Whether to downsample if data_points > max_points
        downsample_func: Custom downsampling function (optional)
        
    Returns:
        Optimized chart figure
    """
    if not downsample or data_points <= max_points:
        # No downsampling needed
        return chart_func()
    
    # Downsample if needed
    if downsample_func:
        # Use custom downsampling function
        return downsample_func()
    
    # Default: show warning and render anyway (let Plotly handle it)
    st.warning(f"⚠️ Large dataset ({data_points:,} points). Chart may render slowly. Consider filtering data.")
    return chart_func()
