"""
Factor Complexity & Redundancy Control (QuantaAlpha-inspired).

Penalize overly complex configs and redundant factor exposures to avoid
overfitting and improve robustness. Used in optimization loops (evolutionary,
diversified) to reject or penalize configs exceeding thresholds.

Complexity: C(f) = α₁·param_count + α₂·model_depth + α₃·log(1+|features|)
Redundancy: Cross-sectional correlation of domain_scores / factor exposure.
"""

from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd


def compute_config_complexity(
    config: Union[Any, Dict[str, Any]],
    alpha_param: float = 0.3,
    alpha_model: float = 0.4,
    alpha_features: float = 0.3,
) -> float:
    """
    Compute config complexity score. Higher = more complex.

    For AppConfig: uses model params (max_depth, num_leaves), feature config
    (return_periods, volatility_windows), analysis filters.
    For dict (param_vector): uses param count and value diversity.

    Args:
        config: AppConfig or dict (e.g. evolutionary param_vector)
        alpha_param: Weight for param count
        alpha_model: Weight for model depth
        alpha_features: Weight for feature/log term

    Returns:
        Non-negative complexity score (typically 0–10 range)
    """
    param_count = 0.0
    model_depth = 0.0
    feature_term = 0.0

    if hasattr(config, "backtest"):
        # AppConfig
        bt = config.backtest
        param_count += 8  # train_years, test_years, step_value, step_unit, rebalance_freq, top_n, top_pct, transaction_cost
        if hasattr(config, "model") and config.model and hasattr(config.model, "params"):
            params = config.model.params or {}
            md = params.get("max_depth", -1)
            nl = params.get("num_leaves", 31)
            ne = params.get("n_estimators", 300)
            model_depth = (
                (10 if md == -1 else min(md, 10)) * 0.3
                + min(nl / 10, 10) * 0.3
                + min(ne / 100, 10) * 0.4
            )
        if hasattr(config, "features") and config.features:
            f = config.features
            n_return = len(getattr(f, "return_periods", []) or [])
            n_vol = len(getattr(f, "volatility_windows", []) or [])
            n_sent = len(getattr(f, "sentiment_lookbacks", []) or [])
            feature_term = np.log1p(n_return + n_vol + n_sent + (10 if getattr(f, "include_fundamentals", True) else 0))
        if hasattr(config, "analysis") and config.analysis:
            # Analysis config from YAML (dict)
            a = config.analysis if isinstance(config.analysis, dict) else {}
            filters = a.get("filters", {}) or {}
            n_filters = sum(1 for v in filters.values() if v is not None)
            param_count += n_filters
    elif isinstance(config, dict):
        # Param vector (evolutionary)
        param_count = len(config)
        # Rebalance freq diversity: MS, M, 2W, W = different complexity
        rf = config.get("rebalance_freq", "MS")
        freq_complexity = {"MS": 1, "M": 1, "ME": 1, "2W": 2, "W": 3}.get(str(rf).upper(), 2)
        model_depth = freq_complexity * 0.5
        feature_term = np.log1p(param_count)

    total = alpha_param * min(param_count / 5, 5) + alpha_model * min(model_depth, 5) + alpha_features * min(feature_term, 5)
    return float(max(0, total))


def compute_factor_redundancy(
    score_matrix: pd.DataFrame,
    score_columns: Optional[list] = None,
) -> float:
    """
    Compute redundancy from cross-sectional correlation of domain/factor scores.

    High pairwise correlation between score columns indicates redundant factors
    (e.g. value_score and quality_score highly correlated across stocks).

    Args:
        score_matrix: DataFrame with stocks as rows, score columns as columns
        score_columns: Columns to use (default: model_score, value_score, quality_score if present)

    Returns:
        Redundancy score 0–1: mean of absolute pairwise correlations (excluding diagonal)
    """
    if score_matrix is None or len(score_matrix) < 2:
        return 0.0
    cols = score_columns or ["model_score", "value_score", "quality_score"]
    available = [c for c in cols if c in score_matrix.columns]
    if len(available) < 2:
        return 0.0
    sub = score_matrix[available].dropna(how="all")
    if len(sub) < 2:
        return 0.0
    corr = sub.corr()
    if corr is None or corr.empty:
        return 0.0
    # Mean of absolute off-diagonal correlations
    n = len(corr)
    total = 0.0
    count = 0
    for i in range(n):
        for j in range(n):
            if i != j:
                v = corr.iloc[i, j]
                if not (v != v):  # not NaN
                    total += abs(v)
                    count += 1
    return total / count if count > 0 else 0.0


def compute_penalty(
    complexity: float,
    redundancy: float,
    complexity_threshold: float = 5.0,
    redundancy_threshold: float = 0.8,
    penalty_per_unit: float = 0.1,
) -> float:
    """
    Compute penalty for fitness when complexity or redundancy exceeds thresholds.

    penalty = penalty_per_unit * (max(0, complexity - complexity_threshold) + max(0, redundancy - redundancy_threshold))

    Args:
        complexity: From compute_config_complexity
        redundancy: From compute_factor_redundancy
        complexity_threshold: Reject/penalize above this
        redundancy_threshold: Reject/penalize above this
        penalty_per_unit: Penalty per unit excess

    Returns:
        Non-negative penalty to subtract from fitness
    """
    excess_c = max(0, complexity - complexity_threshold)
    excess_r = max(0, redundancy - redundancy_threshold)
    return penalty_per_unit * (excess_c + excess_r)


def exceeds_thresholds(
    complexity: float,
    redundancy: float,
    max_complexity: float = 8.0,
    max_redundancy: float = 0.9,
) -> bool:
    """Return True if config should be rejected (exceeds thresholds)."""
    return complexity > max_complexity or redundancy > max_redundancy
