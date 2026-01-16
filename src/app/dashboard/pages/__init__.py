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
from .event_analysis import render_event_analysis
from .tax_optimization import render_tax_optimization
from .monte_carlo import render_monte_carlo
from .turnover_analysis import render_turnover_analysis
from .earnings_calendar import render_earnings_calendar
from .realtime_monitoring import render_realtime_monitoring
from .recommendation_tracking import render_recommendation_tracking
from .alert_management import render_alert_management
from .report_templates import render_report_templates
from .fundamentals_status import render_fundamentals_status

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
    'render_event_analysis',
    'render_tax_optimization',
    'render_monte_carlo',
    'render_turnover_analysis',
    'render_earnings_calendar',
    'render_realtime_monitoring',
    'render_recommendation_tracking',
    'render_alert_management',
    'render_report_templates',
    'render_fundamentals_status',
]
