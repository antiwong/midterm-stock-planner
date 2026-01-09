"""
Validation Module

Provides automated safeguards and validation checks for backtest runs.
"""

from .safeguards import (
    ValidationError,
    ValidationResult,
    ValidationReport,
    validate_backtest_run,
    validate_before_recommendations,
    check_weights_sum_to_one,
    check_position_count,
    check_volatility_bounds,
    check_drawdown_bounds,
    check_return_sanity,
    check_sector_concentration,
    check_factor_concentration,
    RISK_PROFILE_BOUNDS,
)

__all__ = [
    'ValidationError',
    'ValidationResult', 
    'ValidationReport',
    'validate_backtest_run',
    'validate_before_recommendations',
    'check_weights_sum_to_one',
    'check_position_count',
    'check_volatility_bounds',
    'check_drawdown_bounds',
    'check_return_sanity',
    'check_sector_concentration',
    'check_factor_concentration',
    'RISK_PROFILE_BOUNDS',
]
