"""
Dashboard Pages
===============
Individual page modules for the dashboard.
"""

from .overview import render_overview
from .run_analysis import render_run_analysis
from .portfolio_builder import render_portfolio_builder
from .reports import render_reports
from .portfolio_analysis import render_portfolio_analysis
from .purchase_triggers import render_purchase_triggers
from .analysis_runs import render_analysis_runs
from .stock_explorer import render_stock_explorer
from .ai_insights import render_ai_insights
from .compare_runs import render_compare_runs
from .settings import render_settings
from .watchlist_manager import render_watchlist_manager
from .documentation import render_documentation
from .comprehensive_analysis import render_comprehensive_analysis
from .advanced_comparison import render_advanced_comparison

__all__ = [
    'render_overview',
    'render_run_analysis',
    'render_portfolio_builder',
    'render_reports',
    'render_portfolio_analysis',
    'render_comprehensive_analysis',
    'render_purchase_triggers',
    'render_analysis_runs',
    'render_stock_explorer',
    'render_ai_insights',
    'render_compare_runs',
    'render_advanced_comparison',
    'render_settings',
    'render_watchlist_manager',
    'render_documentation',
]
