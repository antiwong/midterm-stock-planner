"""
Fundamentals Status Page
========================
Display fundamentals data completeness and status for stocks.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import List, Dict, Any

from ..components.sidebar import render_page_header
from ..data import (
    load_watchlists,
    get_all_available_watchlists
)
from src.analytics.fundamentals_status import FundamentalsStatusChecker
from src.config.api_keys import load_api_keys

try:
    from src.fundamental.multi_source_fetcher import MultiSourceFundamentalsFetcher
    MULTI_SOURCE_AVAILABLE = True
except ImportError:
    MULTI_SOURCE_AVAILABLE = False
    MultiSourceFundamentalsFetcher = None


def render_fundamentals_status():
    """Render fundamentals status page."""
    render_page_header(
        "Fundamentals Status",
        "Check which stocks have fundamentals data and identify missing data"
    )
    
    checker = FundamentalsStatusChecker()
    
    # Show API keys and data sources status
    _render_api_sources_status()
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋 Watchlist Status", "🔍 Stock Details", "📈 Overall Summary"])
    
    with tab1:
        _render_watchlist_status(checker)
    
    with tab2:
        _render_stock_details(checker)
    
    with tab3:
        _render_overall_summary(checker)


def _render_api_sources_status():
    """Render API keys status and available data sources."""
    st.subheader("🔑 API Keys & Data Sources Status")
    
    # Load API keys
    api_keys = load_api_keys()
    
    # Check multi-source fetcher availability
    if MULTI_SOURCE_AVAILABLE:
        try:
            fetcher = MultiSourceFundamentalsFetcher()
            available_sources = fetcher._get_available_sources()
        except Exception as e:
            available_sources = ['yfinance']  # Fallback
            st.warning(f"⚠️ Could not initialize multi-source fetcher: {e}")
    else:
        available_sources = ['yfinance']  # Only yfinance available
    
    # Define source information
    sources_info = {
        'yfinance': {
            'name': 'Yahoo Finance',
            'status': 'yfinance' in available_sources,
            'api_key_required': False,
            'api_key': None,
            'rate_limit': 'Unlimited',
            'description': 'Primary source, no API key needed'
        },
        'alpha_vantage': {
            'name': 'Alpha Vantage',
            'status': 'alpha_vantage' in available_sources,
            'api_key_required': True,
            'api_key': api_keys.get('ALPHA_VANTAGE_API_KEY'),
            'rate_limit': '5 req/min, 500/day (free)',
            'description': 'Free tier: 500 requests per day',
            'signup_url': 'https://www.alphavantage.co/support/#api-key'
        },
        'massive': {
            'name': 'Massive (formerly Polygon.io)',
            'status': 'massive' in available_sources,
            'api_key_required': True,
            'api_key': api_keys.get('MASSIVE_API_KEY') or api_keys.get('POLYGON_API_KEY'),
            'rate_limit': '5 req/min (free tier)',
            'description': 'Free tier: 5 requests per minute',
            'signup_url': 'https://massive.com/'
        },
        'finnhub': {
            'name': 'Finnhub',
            'status': 'finnhub' in available_sources,
            'api_key_required': True,
            'api_key': api_keys.get('FINNHUB_API_KEY'),
            'rate_limit': '60 req/min (free tier)',
            'description': 'Free tier: 60 requests per minute',
            'signup_url': 'https://finnhub.io/'
        }
    }
    
    # Display sources in columns
    cols = st.columns(4)
    
    for idx, (source_id, info) in enumerate(sources_info.items()):
        with cols[idx % 4]:
            # Status icon
            if info['status']:
                status_icon = "✅"
                status_color = "green"
            elif info['api_key_required'] and not info['api_key']:
                status_icon = "🔑"
                status_color = "orange"
            else:
                status_icon = "❌"
                status_color = "red"
            
            # Card
            st.markdown(f"""
            <div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin-bottom: 10px; background-color: #f9f9f9;">
                <h4 style="margin: 0; color: {status_color};">{status_icon} {info['name']}</h4>
                <p style="margin: 5px 0; font-size: 0.9em; color: #666;">{info['description']}</p>
                <p style="margin: 5px 0; font-size: 0.8em;"><strong>Rate Limit:</strong> {info['rate_limit']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if info['api_key_required']:
                if info['api_key']:
                    st.success(f"✅ API Key: {info['api_key'][:8]}...")
                else:
                    st.warning("⚠️ No API key")
                    if 'signup_url' in info:
                        st.markdown(f"[Get API Key →]({info['signup_url']})")
    
    # Summary
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        active_count = sum(1 for info in sources_info.values() if info['status'])
        st.metric("Active Sources", f"{active_count}/{len(sources_info)}")
    
    with col2:
        configured_keys = sum(1 for info in sources_info.values() 
                            if info['api_key_required'] and info['api_key'])
        total_required = sum(1 for info in sources_info.values() if info['api_key_required'])
        st.metric("API Keys Configured", f"{configured_keys}/{total_required}")
    
    # Instructions
    if configured_keys < total_required:
        with st.expander("📝 How to Add API Keys", expanded=False):
            st.markdown("""
            **To improve fundamentals data completeness, add API keys:**
            
            1. **Get free API keys:**
               - Alpha Vantage: [Get Key](https://www.alphavantage.co/support/#api-key) (500/day free)
               - Finnhub: [Get Key](https://finnhub.io/) (60/min free)
               - Massive (formerly Polygon.io): [Get Key](https://massive.com/) (free tier: 5/min)
            
            2. **Add to `.env` file** (in project root):
               ```
               ALPHA_VANTAGE_API_KEY=your-key-here
               FINNHUB_API_KEY=your-key-here
               MASSIVE_API_KEY=your-key-here
               ```
            
            3. **Restart the dashboard** for changes to take effect.
            
            **Benefits:**
            - Higher data completeness (90-95% vs 70-80%)
            - Automatic fallback if one source fails
            - More reliable data fetching
            
            See `docs/fundamentals-data-sources.md` for detailed instructions.
            """)
    
    # Current download behavior
    st.info(f"""
    **Current Download Behavior:**
    - The download script will use: **{', '.join(available_sources)}**
    - Data from all available sources will be merged automatically
    - Missing fields from one source will be filled from others
    """)


def _render_watchlist_status(checker: FundamentalsStatusChecker):
    """Render watchlist-level status."""
    st.subheader("Watchlist Fundamentals Status")
    
    # Watchlist selector
    watchlists = get_all_available_watchlists()
    
    if not watchlists:
        st.warning("No watchlists found.")
        return
    
    watchlist_options = list(watchlists.keys())
    selected_watchlist = st.selectbox(
        "Select Watchlist",
        options=watchlist_options,
        format_func=lambda x: f"{watchlists[x].get('name', x)} ({watchlists[x].get('count', 0)} stocks)",
        key="fundamentals_watchlist_select"
    )
    
    if not selected_watchlist:
        return
    
    # Get watchlist symbols
    wl_data = watchlists[selected_watchlist]
    symbols = wl_data.get('symbols', [])
    
    if not symbols:
        st.info("This watchlist has no symbols.")
        return
    
    # Check status
    with st.spinner("Checking fundamentals status..."):
        status = checker.check_watchlist_fundamentals(
            watchlist_id=selected_watchlist,
            watchlist_symbols=symbols
        )
    
    if 'error' in status:
        st.error(f"Error: {status['error']}")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Stocks", status['total_stocks'])
    
    with col2:
        st.metric(
            "With Data",
            status['stocks_with_data'],
            delta=f"{status['completeness_rate']*100:.1f}%"
        )
    
    with col3:
        st.metric(
            "Complete",
            status['stocks_complete'],
            delta=f"{status['required_completeness_rate']*100:.1f}%"
        )
    
    with col4:
        status_icon = {
            'complete': '✅',
            'incomplete': '⚠️',
            'missing': '❌',
            'no_file': '❌'
        }.get(status['status'], '❓')
        st.metric("Status", f"{status_icon} {status['status'].title()}")
    
    # File status
    if not status['fundamentals_file_exists']:
        st.error("❌ Fundamentals file not found at `data/fundamentals.csv`")
        st.info("💡 Run: `python scripts/download_fundamentals.py --watchlist <watchlist_name>`")
        return
    
    st.success(f"✅ Fundamentals file found")
    
    # Visualizations
    st.markdown("---")
    st.subheader("Coverage Visualization")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart: With/Without data
        fig_pie = px.pie(
            values=[
                status['stocks_with_data'],
                status['stocks_without_data']
            ],
            names=['With Data', 'Without Data'],
            title='Fundamentals Coverage',
            color_discrete_sequence=['#10b981', '#ef4444']
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Bar chart: Complete/Incomplete/Missing
        fig_bar = px.bar(
            x=['Complete', 'Incomplete', 'Missing'],
            y=[
                status['stocks_complete'],
                status['stocks_incomplete'],
                status['stocks_missing']
            ],
            title='Data Completeness Breakdown',
            color=['Complete', 'Incomplete', 'Missing'],
            color_discrete_map={
                'Complete': '#10b981',
                'Incomplete': '#f59e0b',
                'Missing': '#ef4444'
            }
        )
        fig_bar.update_layout(showlegend=False, yaxis_title="Number of Stocks")
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Field-level statistics
    st.markdown("---")
    st.subheader("Field Coverage")
    
    field_stats = status.get('field_stats', {})
    if field_stats:
        field_data = []
        for field, stats in field_stats.items():
            field_data.append({
                'Field': field.replace('_', ' ').title(),
                'Present': stats['present'],
                'Missing': stats['missing'],
                'Coverage': f"{stats['coverage']*100:.1f}%"
            })
        
        df_fields = pd.DataFrame(field_data)
        df_fields = df_fields.sort_values('Coverage', ascending=False)
        
        st.dataframe(df_fields, use_container_width=True, hide_index=True)
        
        # Field coverage chart
        fig_fields = px.bar(
            df_fields,
            x='Field',
            y=['Present', 'Missing'],
            title='Field Coverage by Stock',
            barmode='stack',
            color_discrete_sequence=['#10b981', '#ef4444']
        )
        fig_fields.update_layout(yaxis_title="Number of Stocks", xaxis_tickangle=-45)
        st.plotly_chart(fig_fields, use_container_width=True)
    
    # Missing stocks
    missing_list = status.get('stocks_missing', [])
    if missing_list and isinstance(missing_list, list) and len(missing_list) > 0:
        st.markdown("---")
        st.subheader("⚠️ Stocks Without Fundamentals")
        
        missing_df = pd.DataFrame({
            'Ticker': missing_list
        })
        st.dataframe(missing_df, use_container_width=True, hide_index=True)
        
        st.info(f"💡 To download fundamentals for these stocks, run:\n```bash\npython scripts/download_fundamentals.py --watchlist {selected_watchlist}\n```")
    
    # Incomplete stocks
    if status.get('stocks_incomplete', 0) > 0:
        st.markdown("---")
        st.subheader("⚠️ Stocks With Incomplete Fundamentals")
        
        incomplete_list = status.get('stocks_incomplete_list', [])
        incomplete_details = [
            s for s in status.get('stock_details', [])
            if s['ticker'] in incomplete_list
        ]
        
        incomplete_data = []
        for detail in incomplete_details:
            incomplete_data.append({
                'Ticker': detail['ticker'],
                'Completeness': f"{detail['completeness']*100:.1f}%",
                'Missing Required': ', '.join(detail['required_missing']) if detail['required_missing'] else 'None',
                'Status': detail['status']
            })
        
        df_incomplete = pd.DataFrame(incomplete_data)
        st.dataframe(df_incomplete, use_container_width=True, hide_index=True)


def _render_stock_details(checker: FundamentalsStatusChecker):
    """Render detailed stock-by-stock status."""
    st.subheader("Stock-Level Fundamentals Details")
    
    # Watchlist selector
    watchlists = get_all_available_watchlists()
    
    if not watchlists:
        st.warning("No watchlists found.")
        return
    
    watchlist_options = list(watchlists.keys())
    selected_watchlist = st.selectbox(
        "Select Watchlist",
        options=watchlist_options,
        format_func=lambda x: f"{watchlists[x].get('name', x)} ({watchlists[x].get('count', 0)} stocks)",
        key="fundamentals_stock_watchlist"
    )
    
    if not selected_watchlist:
        return
    
    # Get symbols
    wl_data = watchlists[selected_watchlist]
    symbols = wl_data.get('symbols', [])
    
    if not symbols:
        st.info("This watchlist has no symbols.")
        return
    
    # Check status
    with st.spinner("Checking fundamentals status..."):
        status = checker.check_watchlist_fundamentals(
            watchlist_id=selected_watchlist,
            watchlist_symbols=symbols
        )
    
    if 'error' in status:
        st.error(f"Error: {status['error']}")
        return
    
    # Stock details table
    stock_details = status.get('stock_details', [])
    
    if not stock_details:
        st.info("No stock details available.")
        return
    
    # Create detailed table
    details_data = []
    for detail in stock_details:
        status_icon = {
            'complete': '✅',
            'incomplete': '⚠️',
            'missing': '❌'
        }.get(detail['status'], '❓')
        
        details_data.append({
            'Ticker': detail['ticker'],
            'Status': f"{status_icon} {detail['status'].title()}",
            'Has Data': 'Yes' if detail['has_data'] else 'No',
            'Completeness': f"{detail['completeness']*100:.1f}%",
            'Required Fields': len(detail.get('required_present', [])),
            'Missing Required': ', '.join(detail.get('required_missing', []))[:50] + '...' if len(detail.get('required_missing', [])) > 0 else 'None',
            'Last Updated': detail.get('last_updated', 'Unknown')
        })
    
    df_details = pd.DataFrame(details_data)
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.multiselect(
            "Filter by Status",
            options=['complete', 'incomplete', 'missing'],
            default=['complete', 'incomplete', 'missing'],
            key="stock_status_filter"
        )
    
    with col2:
        search_ticker = st.text_input("Search Ticker", key="stock_search_ticker")
    
    # Apply filters
    filtered_df = df_details[df_details['Status'].str.contains('|'.join([s.title() for s in status_filter]), case=False, na=False)]
    
    if search_ticker:
        filtered_df = filtered_df[filtered_df['Ticker'].str.contains(search_ticker.upper(), case=False, na=False)]
    
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    
    # Download button
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Status Report (CSV)",
        data=csv,
        file_name=f"fundamentals_status_{selected_watchlist}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )


def _render_overall_summary(checker: FundamentalsStatusChecker):
    """Render overall summary across all watchlists."""
    st.subheader("Overall Fundamentals Summary")
    
    if st.button("🔄 Refresh All Watchlists Status", use_container_width=True):
        with st.spinner("Checking all watchlists..."):
            all_statuses = checker.get_all_watchlists_status()
            
            if not all_statuses:
                st.info("No watchlists found.")
                return
            
            # Summary statistics
            total_watchlists = len(all_statuses)
            total_stocks = sum(s['total_stocks'] for s in all_statuses.values())
            total_with_data = sum(s['stocks_with_data'] for s in all_statuses.values())
            total_complete = sum(s['stocks_complete'] for s in all_statuses.values())
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Watchlists", total_watchlists)
            
            with col2:
                st.metric("Total Stocks", total_stocks)
            
            with col3:
                overall_coverage = total_with_data / total_stocks if total_stocks > 0 else 0.0
                st.metric(
                    "With Data",
                    total_with_data,
                    delta=f"{overall_coverage*100:.1f}%"
                )
            
            with col4:
                overall_complete = total_complete / total_stocks if total_stocks > 0 else 0.0
                st.metric(
                    "Complete",
                    total_complete,
                    delta=f"{overall_complete*100:.1f}%"
                )
            
            # Watchlist comparison table
            st.markdown("---")
            st.subheader("Watchlist Comparison")
            
            comparison_data = []
            for wl_id, status in all_statuses.items():
                comparison_data.append({
                    'Watchlist': wl_id,
                    'Total Stocks': status['total_stocks'],
                    'With Data': status['stocks_with_data'],
                    'Complete': status['stocks_complete'],
                    'Coverage': f"{status['completeness_rate']*100:.1f}%",
                    'Required Coverage': f"{status['required_completeness_rate']*100:.1f}%",
                    'Status': status['status'].title()
                })
            
            df_comparison = pd.DataFrame(comparison_data)
            df_comparison = df_comparison.sort_values('Coverage', ascending=False)
            
            st.dataframe(df_comparison, use_container_width=True, hide_index=True)
            
            # Visualization
            fig = px.bar(
                df_comparison,
                x='Watchlist',
                y=['With Data', 'Complete'],
                title='Fundamentals Coverage by Watchlist',
                barmode='group',
                color_discrete_sequence=['#3b82f6', '#10b981']
            )
            fig.update_layout(
                yaxis_title="Number of Stocks",
                xaxis_tickangle=-45,
                legend=dict(title="Data Status")
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Click 'Refresh All Watchlists Status' to see summary across all watchlists.")
