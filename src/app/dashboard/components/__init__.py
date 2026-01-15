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

# Import new UX components
try:
    from .loading import (
        loading_spinner,
        render_progress_bar,
        render_loading_card,
        render_stage_progress,
        operation_with_feedback,
    )
    from .errors import (
        ErrorHandler,
        render_warning_with_actions,
        render_info_with_help,
    )
    from .shortcuts import (
        render_shortcuts_help,
        handle_shortcut,
        check_shortcuts,
    )
    HAS_UX_COMPONENTS = True
except ImportError:
    HAS_UX_COMPONENTS = False

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

# Add UX components if available
if HAS_UX_COMPONENTS:
    __all__.extend([
        'loading_spinner',
        'render_progress_bar',
        'render_loading_card',
        'render_stage_progress',
        'operation_with_feedback',
        'ErrorHandler',
        'render_warning_with_actions',
        'render_info_with_help',
        'render_shortcuts_help',
        'handle_shortcut',
        'check_shortcuts',
    ])
