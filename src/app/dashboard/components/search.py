"""
Global Search Component
=======================
Global search functionality across all pages.
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from ..data import load_runs, load_run_scores, get_all_available_watchlists


def render_global_search() -> Optional[str]:
    """
    Render global search bar and return selected result.
    
    Returns:
        Selected page identifier or None
    """
    search_query = st.sidebar.text_input(
        "🔍 Search",
        placeholder="Search runs, stocks, watchlists...",
        key="global_search"
    )
    
    if not search_query or len(search_query) < 2:
        return None
    
    query_lower = search_query.lower()
    results = []
    
    # Search runs
    try:
        runs = load_runs()
        for run in runs:
            if (query_lower in run.get('name', '').lower() or 
                query_lower in run.get('run_id', '').lower() or
                query_lower in run.get('watchlist', '').lower()):
                results.append({
                    'type': 'run',
                    'label': f"Run: {run.get('name', run.get('run_id', 'Unknown'))}",
                    'page': 'Analysis Runs',
                    'data': run
                })
    except Exception:
        pass
    
    # Search watchlists
    try:
        watchlists = get_all_available_watchlists()
        for wl_id, wl_data in watchlists.items():
            if (query_lower in wl_id.lower() or 
                query_lower in wl_data.get('name', '').lower()):
                results.append({
                    'type': 'watchlist',
                    'label': f"Watchlist: {wl_data.get('name', wl_id)}",
                    'page': 'Watchlist Manager',
                    'data': wl_data
                })
    except Exception:
        pass
    
    # Search stocks (from recent runs)
    try:
        runs = load_runs()[:5]  # Recent runs only
        for run in runs:
            if run.get('status') == 'completed':
                scores = load_run_scores(run['run_id'])
                for score in scores:
                    ticker = score.get('ticker', '')
                    if query_lower in ticker.lower():
                        results.append({
                            'type': 'stock',
                            'label': f"Stock: {ticker}",
                            'page': 'Stock Explorer',
                            'data': {'ticker': ticker, 'run_id': run['run_id']}
                        })
                        break  # Only show once per ticker
    except Exception:
        pass
    
    # Display results
    if results:
        st.sidebar.markdown("### Search Results")
        for i, result in enumerate(results[:10]):  # Limit to 10 results
            if st.sidebar.button(
                result['label'],
                key=f"search_result_{i}",
                use_container_width=True
            ):
                st.session_state['selected_nav_item'] = result['page']
                if result['type'] == 'run':
                    st.session_state['selected_run_id'] = result['data'].get('run_id')
                elif result['type'] == 'stock':
                    st.session_state['selected_ticker'] = result['data'].get('ticker')
                return result['page']
    else:
        st.sidebar.info("No results found")
    
    return None
