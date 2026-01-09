"""
Analytics Module
================
Run tracking, reporting, and database management.
"""

from .models import (
    get_db,
    DatabaseManager,
    Run,
    StockScore,
    Trade,
    PortfolioSnapshot,
    WatchlistStock,
    CustomWatchlist,
)

from .manager import (
    RunManager,
    RunContext,
)

from .reports import ReportGenerator
from .ai_insights import AIInsightsGenerator, generate_ai_report_section

__all__ = [
    # Database
    'get_db',
    'DatabaseManager',
    # Models
    'Run',
    'StockScore',
    'Trade',
    'PortfolioSnapshot',
    'WatchlistStock',
    'CustomWatchlist',
    # Manager
    'RunManager',
    'RunContext',
    # Reports
    'ReportGenerator',
    # AI Insights
    'AIInsightsGenerator',
    'generate_ai_report_section',
]
