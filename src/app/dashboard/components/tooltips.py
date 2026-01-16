"""
Tooltip Utilities
=================
Helper functions for adding consistent tooltips across the dashboard.
"""

from typing import Optional


def get_tooltip(key: str) -> Optional[str]:
    """Get tooltip text for a given key.
    
    Args:
        key: Tooltip key identifier
    
    Returns:
        Tooltip text or None
    """
    tooltips = {
        # Run Analysis
        'watchlist_select': "Select the stock universe to analyze. Custom watchlists can be created in Watchlist Manager.",
        'date_range': "Analysis period. Longer periods provide more data but take longer to process.",
        'run_analysis': "Runs the complete 4-stage analysis pipeline: data loading, scoring, portfolio construction, and backtesting.",
        
        # Comprehensive Analysis
        'run_select': "Select a completed run to analyze with advanced modules (attribution, benchmark, factor exposure, etc.)",
        'run_all_analyses': "Runs all advanced analysis modules: Performance Attribution, Benchmark Comparison, Factor Exposure, Rebalancing, and Style Analysis.",
        'export_results': "Export analysis results in your preferred format. PDF includes charts, Excel includes all data tables.",
        
        # Portfolio Builder
        'risk_tolerance': "Conservative: Lower risk, stable returns. Moderate: Balanced risk/return. Aggressive: Higher risk, higher potential returns.",
        'target_return': "Expected annual return target. Higher targets may require more risk.",
        'portfolio_size': "Number of stocks in the portfolio. More stocks = more diversification but potentially lower returns.",
        'max_position': "Maximum weight for any single stock. Prevents over-concentration.",
        'max_sector': "Maximum weight for any sector. Ensures diversification across sectors.",
        
        # Watchlist Manager
        'create_watchlist': "Create a new custom watchlist. Use lowercase IDs and descriptive names.",
        'add_symbols': "Add symbols separated by commas. Invalid symbols will be rejected automatically.",
        'fetch_sectors': "Fetches sector data from Yahoo Finance for unknown stocks. May take a few minutes for large watchlists.",
        'update_sectors': "Updates sector classifications for all stocks. Use 'Update All' for missing sectors, 'Force Refresh' to re-fetch all.",
        
        # Portfolio Analysis
        'select_run': "Choose a completed run to view detailed portfolio metrics, charts, and AI analysis.",
        'lazy_load': "Lazy loading renders charts on-demand for faster page load. Disable for immediate chart display.",
        
        # AI Insights
        'generate_insights': "Generates AI-powered commentary and recommendations using Gemini. Requires API key.",
        'generate_recommendations': "Creates actionable buy/sell recommendations based on current portfolio analysis.",
        
        # Purchase Triggers
        'purchase_triggers': "Shows stocks that meet your purchase criteria based on current scores and filters.",
        'score_filters': "Adjust score weights and filters to customize which stocks appear in purchase triggers.",
        
        # Stock Explorer
        'stock_search': "Search by ticker symbol. Use filters to narrow down results.",
        'sector_filter': "Filter stocks by sector. 'All' shows all sectors.",
        'score_range': "Filter stocks by score range. Higher scores indicate better investment potential.",
        
        # Settings
        'dark_mode': "Switch to dark theme for better viewing in low-light conditions. Reduces eye strain.",
        'api_keys': "Configure API keys for external services. Some features require API keys to function.",
        'database_optimize': "Optimizes database indexes for faster queries. Run periodically for best performance.",
        
        # Performance Monitoring
        'system_metrics': "Real-time system resource usage. Monitor CPU, memory, and disk usage.",
        'execution_times': "Track how long operations take. Helps identify performance bottlenecks.",
        
        # Export
        'export_format': "Choose export format: PDF for reports, Excel for data analysis, CSV for simple data, JSON for programmatic access.",
        
        # General
        'refresh': "Refresh the current page to load latest data.",
        'help': "Show help and keyboard shortcuts.",
    }
    
    return tooltips.get(key)
