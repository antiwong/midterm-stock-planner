"""
Lazy DataFrame Loading Components
==================================
Components for lazy-loading large dataframes to improve performance.
"""

import streamlit as st
import pandas as pd
from typing import Optional, Callable, Any
import time


def lazy_dataframe(
    df_key: str,
    df_func: Callable[[], pd.DataFrame],
    label: str = "📊 View Data",
    default_expanded: bool = False,
    max_rows_preview: int = 10,
    loading_message: str = "Loading data..."
) -> Optional[pd.DataFrame]:
    """
    Render a dataframe lazily inside an expander.
    
    Args:
        df_key: Unique key for this dataframe (for session state)
        df_func: Function that returns the dataframe
        label: Label for the expander
        default_expanded: Whether to expand by default
        max_rows_preview: Number of rows to show in preview
        loading_message: Message to show while loading
        
    Returns:
        The dataframe if expanded, None otherwise
    """
    # Initialize session state
    if df_key not in st.session_state:
        st.session_state[df_key] = default_expanded
    
    # Expander for lazy loading
    with st.expander(label, expanded=st.session_state[df_key]):
        if st.session_state[df_key] or st.session_state.get(f"{df_key}_force_load", False):
            with st.spinner(loading_message):
                try:
                    df = df_func()
                    if df is not None and not df.empty:
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        st.caption(f"Showing {len(df)} rows")
                        return df
                    else:
                        st.info("No data available")
                        return None
                except Exception as e:
                    st.error(f"Error loading data: {e}")
                    return None
        else:
            # Show preview
            try:
                df = df_func()
                if df is not None and not df.empty:
                    preview_df = df.head(max_rows_preview)
                    st.dataframe(preview_df, use_container_width=True, hide_index=True)
                    st.caption(f"Preview: {max_rows_preview} of {len(df)} rows. Expand to see full data.")
                    if st.button(f"Load Full Data ({len(df)} rows)", key=f"{df_key}_load_btn"):
                        st.session_state[df_key] = True
                        st.rerun()
                else:
                    st.info("No data available")
            except Exception as e:
                st.warning(f"Could not load preview: {e}")
                if st.button(f"Try Loading Data", key=f"{df_key}_load_btn"):
                    st.session_state[df_key] = True
                    st.rerun()
    
    return None


def paginated_dataframe(
    df: pd.DataFrame,
    page_size: int = 50,
    key_prefix: str = "df_paginated"
) -> pd.DataFrame:
    """
    Render a dataframe with pagination.
    
    Args:
        df: DataFrame to paginate
        page_size: Number of rows per page
        key_prefix: Prefix for session state keys
        
    Returns:
        DataFrame slice for current page
    """
    if df is None or df.empty:
        return df
    
    total_rows = len(df)
    total_pages = (total_rows + page_size - 1) // page_size
    
    # Page selector
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.caption(f"Total: {total_rows} rows")
    
    with col2:
        page_num = st.number_input(
            "Page",
            min_value=1,
            max_value=max(1, total_pages),
            value=1,
            key=f"{key_prefix}_page"
        )
    
    with col3:
        st.caption(f"Page {page_num} of {total_pages}")
    
    # Calculate slice
    start_idx = (page_num - 1) * page_size
    end_idx = min(start_idx + page_size, total_rows)
    
    return df.iloc[start_idx:end_idx]


def virtual_scroll_dataframe(
    df: pd.DataFrame,
    chunk_size: int = 100,
    initial_rows: int = 50,
    key_prefix: str = "df_virtual"
) -> pd.DataFrame:
    """
    Render a dataframe with virtual scrolling (loads more as user scrolls).
    
    Note: Streamlit doesn't support true virtual scrolling, so this implements
    a "load more" pattern that simulates virtual scrolling.
    
    Args:
        df: DataFrame to display
        chunk_size: Number of rows to load per chunk
        initial_rows: Number of rows to show initially
        key_prefix: Prefix for session state keys
        
    Returns:
        DataFrame slice for current view
    """
    if df is None or df.empty:
        return df
    
    total_rows = len(df)
    
    # Initialize loaded rows count
    if f"{key_prefix}_loaded_rows" not in st.session_state:
        st.session_state[f"{key_prefix}_loaded_rows"] = initial_rows
    
    loaded_rows = st.session_state[f"{key_prefix}_loaded_rows"]
    
    # Display current slice
    display_df = df.iloc[:loaded_rows]
    
    # Show dataframe
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Load more button if there are more rows
    if loaded_rows < total_rows:
        remaining = total_rows - loaded_rows
        load_more = min(chunk_size, remaining)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"Showing {loaded_rows} of {total_rows} rows")
        with col2:
            if st.button(f"Load {load_more} More", key=f"{key_prefix}_load_more"):
                st.session_state[f"{key_prefix}_loaded_rows"] = min(
                    loaded_rows + chunk_size,
                    total_rows
                )
                st.rerun()
    else:
        st.caption(f"Showing all {total_rows} rows")
    
    return display_df
