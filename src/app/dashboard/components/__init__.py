"""
Dashboard UI Components
=======================
Reusable UI components for the dashboard.
"""

from .metrics import render_metric_card, render_metric_row
from .charts import (
    create_equity_curve,
    create_sector_pie,
    create_score_distribution,
    create_performance_bar,
    create_correlation_heatmap,
)
from .cards import (
    render_stock_card,
    render_run_card,
    render_info_card,
    render_progress_steps,
)
from .tables import render_styled_dataframe, render_score_table
from .sidebar import render_sidebar

__all__ = [
    'render_metric_card',
    'render_metric_row',
    'create_equity_curve',
    'create_sector_pie',
    'create_score_distribution',
    'create_performance_bar',
    'create_correlation_heatmap',
    'render_stock_card',
    'render_run_card',
    'render_info_card',
    'render_progress_steps',
    'render_styled_dataframe',
    'render_score_table',
    'render_sidebar',
]
