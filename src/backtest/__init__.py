"""Backtesting module for mid-term stock planner.

This module provides:
- Walk-forward backtesting framework
- A/B comparison utilities for evaluating feature impact
"""

from .rolling import (
    BacktestConfig,
    BacktestResults,
    run_walk_forward_backtest,
)

from .comparison import (
    BacktestComparisonResult,
    compare_backtests,
    run_ab_backtest,
    format_comparison_report,
    save_comparison_results,
    get_sentiment_feature_columns,
)

__all__ = [
    # Rolling backtest
    "BacktestConfig",
    "BacktestResults",
    "run_walk_forward_backtest",
    # A/B Comparison
    "BacktestComparisonResult",
    "compare_backtests",
    "run_ab_backtest",
    "format_comparison_report",
    "save_comparison_results",
    "get_sentiment_feature_columns",
]
