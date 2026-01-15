"""
Stock Analysis Dashboard - Main Application
===========================================
Entry point for the Streamlit dashboard.

Run with: streamlit run src/app/dashboard/app.py
"""

import sys
import streamlit as st
from pathlib import Path

# Add project root to path BEFORE any imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config.api_keys import load_api_keys

# Import configuration (use absolute imports since we're running as script)
from src.app.dashboard.config import configure_page, inject_custom_css, PAGES

# Import components
from src.app.dashboard.components.sidebar import render_sidebar

# Import pages
from src.app.dashboard.pages import (
    render_overview,
    render_run_analysis,
    render_watchlist_manager,
    render_portfolio_builder,
    render_reports,
    render_portfolio_analysis,
    render_comprehensive_analysis,
    render_purchase_triggers,
    render_analysis_runs,
    render_stock_explorer,
    render_ai_insights,
    render_compare_runs,
    render_documentation,
    render_settings,
)


def main():
    """Main application entry point."""
    # Clear cache on first run or if explicitly requested
    # This ensures fresh data after database/reset operations
    if 'cache_cleared' not in st.session_state:
        st.cache_data.clear()
        st.cache_resource.clear()
        st.session_state['cache_cleared'] = True
    
    # Configure page settings
    configure_page()
    
    # Inject custom CSS
    inject_custom_css()
    
    # Load API keys
    load_api_keys()
    
    # Render sidebar and get selected page
    selected_page = render_sidebar()
    
    # Route to appropriate page
    page_routes = {
        "🏠 Overview": render_overview,
        "🎮 Run Analysis": render_run_analysis,
        "📋 Watchlist Manager": render_watchlist_manager,
        "🎯 Portfolio Builder": render_portfolio_builder,
        "📄 Reports": render_reports,
        "💼 Portfolio Analysis": render_portfolio_analysis,
        "📊 Comprehensive Analysis": render_comprehensive_analysis,
        "🔍 Purchase Triggers": render_purchase_triggers,
        "📊 Analysis Runs": render_analysis_runs,
        "🔎 Stock Explorer": render_stock_explorer,
        "🤖 AI Insights": render_ai_insights,
        "📈 Compare Runs": render_compare_runs,
        "📚 Documentation": render_documentation,
        "⚙️ Settings": render_settings,
    }
    
    # Render selected page
    page_func = page_routes.get(selected_page)
    if page_func:
        page_func()
    else:
        render_overview()


if __name__ == "__main__":
    main()
