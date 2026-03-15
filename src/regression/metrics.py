"""Metrics framework for regression testing.

Defines PRIMARY, SECONDARY, and GUARD metrics with statistical significance
tests for measuring marginal feature contribution.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd


class MetricClassification(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    GUARD = "guard"


@dataclass
class MetricDef:
    """Definition of a metric."""
    name: str
    classification: MetricClassification
    direction: str  # "higher_is_better" or "lower_is_better"
    description: str
    formula: str = ""
    threshold: Optional[float] = None  # Guard threshold


# Complete metrics registry
METRICS_REGISTRY: Dict[str, MetricDef] = {
    # --- PRIMARY (optimize these) ---
    "mean_rank_ic": MetricDef(
        "mean_rank_ic", MetricClassification.PRIMARY, "higher_is_better",
        "Mean Spearman rank IC across walk-forward windows",
        "mean(rank_corr(predicted, actual) per window)",
    ),
    "sharpe_ratio": MetricDef(
        "sharpe_ratio", MetricClassification.PRIMARY, "higher_is_better",
        "Annualized Sharpe ratio of portfolio returns",
        "ann_return / ann_volatility",
    ),
    "excess_return": MetricDef(
        "excess_return", MetricClassification.PRIMARY, "higher_is_better",
        "Annualized excess return over benchmark",
        "ann(cumulative(portfolio - benchmark))",
    ),
    # --- SECONDARY (monitor these) ---
    "mean_ic": MetricDef(
        "mean_ic", MetricClassification.SECONDARY, "higher_is_better",
        "Mean Pearson IC across windows",
        "mean(corr(predicted, actual) per window)",
    ),
    "ic_std": MetricDef(
        "ic_std", MetricClassification.SECONDARY, "lower_is_better",
        "Standard deviation of IC across windows (stability)",
        "std(ic_per_window)",
    ),
    "ic_ir": MetricDef(
        "ic_ir", MetricClassification.SECONDARY, "higher_is_better",
        "IC Information Ratio (consistency)",
        "mean_ic / ic_std",
    ),
    "total_return": MetricDef(
        "total_return", MetricClassification.SECONDARY, "higher_is_better",
        "Cumulative total return",
    ),
    "annualized_return": MetricDef(
        "annualized_return", MetricClassification.SECONDARY, "higher_is_better",
        "Compound annual growth rate",
    ),
    "hit_rate": MetricDef(
        "hit_rate", MetricClassification.SECONDARY, "higher_is_better",
        "Percentage of periods beating benchmark",
    ),
    "volatility": MetricDef(
        "volatility", MetricClassification.SECONDARY, "lower_is_better",
        "Annualized standard deviation of returns",
    ),
    "sortino_ratio": MetricDef(
        "sortino_ratio", MetricClassification.SECONDARY, "higher_is_better",
        "Annualized return / downside volatility",
    ),
    "calmar_ratio": MetricDef(
        "calmar_ratio", MetricClassification.SECONDARY, "higher_is_better",
        "Annualized return / abs(max drawdown)",
    ),
    # --- GUARD (must not degrade) ---
    "max_drawdown": MetricDef(
        "max_drawdown", MetricClassification.GUARD, "higher_is_better",
        "Maximum peak-to-trough drawdown (less negative is better)",
        threshold=-0.30,
    ),
    "turnover": MetricDef(
        "turnover", MetricClassification.GUARD, "lower_is_better",
        "Average absolute weight change per rebalance",
        threshold=0.80,
    ),
    "train_test_sharpe_ratio": MetricDef(
        "train_test_sharpe_ratio", MetricClassification.GUARD, "lower_is_better",
        "Max ratio of train Sharpe to test Sharpe (overfitting detector)",
        threshold=2.5,
    ),
    "ic_pct_positive": MetricDef(
        "ic_pct_positive", MetricClassification.GUARD, "higher_is_better",
        "Fraction of windows with positive IC",
        threshold=0.50,
    ),
}


def compute_extended_metrics(
    backtest_metrics: Dict[str, float],
    window_results: List[Dict[str, Any]],
    portfolio_returns: Optional[pd.Series] = None,
) -> Dict[str, float]:
    """Compute all metrics (primary + secondary + guard) from backtest results.

    Extends the base backtest metrics with IC stability, sortino, calmar,
    overfitting detection, and guard metrics.

    Args:
        backtest_metrics: Metrics dict from BacktestResults.metrics.
        window_results: Per-window results list from BacktestResults.window_results.
        portfolio_returns: Daily portfolio return series (optional, for sortino/calmar).

    Returns:
        Dict with all metrics including extended ones.
    """
    metrics = dict(backtest_metrics)

    # IC stability metrics
    ics = [w.get("ic") for w in window_results if w.get("ic") is not None]
    rank_ics = [w.get("rank_ic") for w in window_results if w.get("rank_ic") is not None]

    if ics:
        ic_arr = np.array(ics)
        metrics["ic_std"] = float(np.std(ic_arr))
        metrics["ic_ir"] = (
            float(np.mean(ic_arr) / np.std(ic_arr))
            if np.std(ic_arr) > 0 else 0.0
        )
        metrics["ic_pct_positive"] = float(np.mean(ic_arr > 0))

    if rank_ics:
        ric_arr = np.array(rank_ics)
        metrics["rank_ic_std"] = float(np.std(ric_arr))
        metrics["rank_ic_ir"] = (
            float(np.mean(ric_arr) / np.std(ric_arr))
            if np.std(ric_arr) > 0 else 0.0
        )

    # Sortino and Calmar from portfolio returns
    if portfolio_returns is not None and len(portfolio_returns) > 0:
        port_ret = portfolio_returns.dropna()
        downside = port_ret[port_ret < 0]
        downside_vol = downside.std() * np.sqrt(252) if len(downside) > 1 else 0.0
        ann_ret = metrics.get("annualized_return", 0.0)
        metrics["sortino_ratio"] = (
            float(ann_ret / downside_vol) if downside_vol > 0 else 0.0
        )
        max_dd = abs(metrics.get("max_drawdown", -0.01))
        metrics["calmar_ratio"] = float(ann_ret / max_dd) if max_dd > 0 else 0.0

    # Overfitting detection
    train_sharpes = [w.get("train_sharpe") for w in window_results
                     if w.get("train_sharpe") is not None]
    test_sharpes = [w.get("test_sharpe") for w in window_results
                    if w.get("test_sharpe") is not None]
    if train_sharpes and test_sharpes:
        ratios = [
            t / s for t, s in zip(train_sharpes, test_sharpes)
            if s is not None and s > 0
        ]
        if ratios:
            metrics["train_test_sharpe_ratio"] = float(np.max(ratios))
            metrics["mean_train_test_sharpe_ratio"] = float(np.mean(ratios))

    return metrics


def check_guard_metrics(metrics: Dict[str, float]) -> List[Dict[str, Any]]:
    """Check guard metrics against thresholds.

    Returns list of violations: [{metric, value, threshold, message}].
    """
    violations = []
    for name, defn in METRICS_REGISTRY.items():
        if defn.classification != MetricClassification.GUARD:
            continue
        if defn.threshold is None:
            continue
        value = metrics.get(name)
        if value is None:
            continue

        violated = False
        if defn.direction == "higher_is_better" and value < defn.threshold:
            violated = True
        elif defn.direction == "lower_is_better" and value > defn.threshold:
            violated = True

        if violated:
            violations.append({
                "metric": name,
                "value": value,
                "threshold": defn.threshold,
                "direction": defn.direction,
                "message": f"{name}={value:.4f} violates threshold {defn.threshold}",
            })
    return violations


def compute_marginal_significance(
    baseline_window_rank_ics: List[float],
    variant_window_rank_ics: List[float],
    baseline_window_test_sharpes: List[float],
    variant_window_test_sharpes: List[float],
    baseline_sharpe: float,
    variant_sharpe: float,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> Dict[str, Dict[str, Any]]:
    """Statistical significance tests for marginal feature contribution.

    Tests:
    1. Paired t-test on per-window Rank ICs
    2. Paired t-test on per-window test Sharpes
    3. Diebold-Mariano test on forecast accuracy
    4. Bootstrap CI for Sharpe difference

    Args:
        baseline_window_rank_ics: Per-window Rank IC from baseline step.
        variant_window_rank_ics: Per-window Rank IC from variant step.
        baseline_window_test_sharpes: Per-window test Sharpe from baseline.
        variant_window_test_sharpes: Per-window test Sharpe from variant.
        baseline_sharpe: Overall Sharpe from baseline.
        variant_sharpe: Overall Sharpe from variant.
        n_bootstrap: Number of bootstrap resamples.
        confidence: Confidence level for bootstrap CI.

    Returns:
        Dict with test results.
    """
    from scipy import stats

    results: Dict[str, Dict[str, Any]] = {}

    # 1. Paired t-test on Rank ICs
    b_ics = np.array([x for x in baseline_window_rank_ics if x is not None], dtype=float)
    v_ics = np.array([x for x in variant_window_rank_ics if x is not None], dtype=float)
    n = min(len(b_ics), len(v_ics))
    if n >= 3:
        t_stat, p_val = stats.ttest_rel(v_ics[:n], b_ics[:n])
        diff = v_ics[:n] - b_ics[:n]
        results["rank_ic_paired_ttest"] = {
            "t_stat": float(t_stat),
            "p_value": float(p_val),
            "significant": bool(p_val < (1 - confidence)),
            "mean_diff": float(np.mean(diff)),
            "n_windows": n,
        }

    # 2. Paired t-test on test Sharpes
    b_sharpes = np.array([x for x in baseline_window_test_sharpes if x is not None], dtype=float)
    v_sharpes = np.array([x for x in variant_window_test_sharpes if x is not None], dtype=float)
    n = min(len(b_sharpes), len(v_sharpes))
    if n >= 3:
        t_stat, p_val = stats.ttest_rel(v_sharpes[:n], b_sharpes[:n])
        diff = v_sharpes[:n] - b_sharpes[:n]
        results["sharpe_paired_ttest"] = {
            "t_stat": float(t_stat),
            "p_value": float(p_val),
            "significant": bool(p_val < (1 - confidence)),
            "mean_diff": float(np.mean(diff)),
            "n_windows": n,
        }

    # 3. Diebold-Mariano test on forecast accuracy (Rank IC as proxy)
    if n >= 3:
        # Use squared forecast error proxy: (1 - rank_ic)^2
        e_base = (1.0 - b_ics[:n]) ** 2
        e_var = (1.0 - v_ics[:n]) ** 2
        d = e_base - e_var  # positive = variant is more accurate
        d_mean = np.mean(d)
        d_var = np.var(d, ddof=1)
        if d_var > 0:
            dm_stat = float(d_mean / np.sqrt(d_var / n))
            dm_p_val = float(2 * (1 - stats.t.cdf(abs(dm_stat), df=n - 1)))
        else:
            dm_stat = 0.0
            dm_p_val = 1.0
        results["diebold_mariano"] = {
            "dm_stat": dm_stat,
            "p_value": dm_p_val,
            "significant": bool(dm_p_val < (1 - confidence)),
            "mean_loss_diff": float(d_mean),
            "n_windows": n,
        }

    # 4. Bootstrap CI for Sharpe difference
    sharpe_diff = variant_sharpe - baseline_sharpe
    if n >= 3:
        # Bootstrap the per-window Sharpe differences
        diffs = v_sharpes[:n] - b_sharpes[:n]
        boot_means = []
        rng = np.random.RandomState(42)
        for _ in range(n_bootstrap):
            sample = rng.choice(diffs, size=len(diffs), replace=True)
            boot_means.append(float(np.mean(sample)))
        boot_means = np.array(boot_means)
        alpha = 1 - confidence
        ci_lower = float(np.percentile(boot_means, 100 * alpha / 2))
        ci_upper = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
        p_val_boot = float(np.mean(boot_means <= 0)) if sharpe_diff > 0 else float(np.mean(boot_means >= 0))
        results["sharpe_diff_bootstrap"] = {
            "sharpe_diff": float(sharpe_diff),
            "mean_bootstrap": float(np.mean(boot_means)),
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "p_value": p_val_boot,
            "significant": bool(ci_lower > 0 or ci_upper < 0),
            "n_bootstrap": n_bootstrap,
        }

    return results


def compute_feature_contribution(
    step_metrics: Dict[str, float],
    prev_metrics: Optional[Dict[str, float]],
    step_feature_importance: Dict[str, float],
    feature_added: str,
    feature_columns: Optional[List[str]] = None,
) -> Dict[str, float]:
    """Compute marginal contribution metrics for the newly added feature.

    Args:
        step_metrics: Metrics from the current step.
        prev_metrics: Metrics from the previous step (None for baseline).
        step_feature_importance: LightGBM feature importance dict.
        feature_added: Name of the feature added in this step.
        feature_columns: Column names produced by this feature (e.g.,
            ["macd", "macd_signal", "macd_histogram"]).  When provided,
            importance is summed across all matching columns instead of
            doing a single key lookup on feature_added.

    Returns:
        Dict with marginal contribution metrics.
    """
    if prev_metrics is None:
        return {
            "marginal_sharpe": step_metrics.get("sharpe_ratio", 0.0),
            "marginal_rank_ic": step_metrics.get("mean_rank_ic", 0.0),
            "marginal_excess_return": step_metrics.get("excess_return", 0.0),
            "marginal_hit_rate": step_metrics.get("hit_rate", 0.0),
            "feature_importance_pct": 0.0,
            "feature_importance_rank": 0,
        }

    # Marginal deltas
    contribution = {
        "marginal_sharpe": (
            step_metrics.get("sharpe_ratio", 0.0)
            - prev_metrics.get("sharpe_ratio", 0.0)
        ),
        "marginal_rank_ic": (
            step_metrics.get("mean_rank_ic", 0.0)
            - prev_metrics.get("mean_rank_ic", 0.0)
        ),
        "marginal_excess_return": (
            step_metrics.get("excess_return", 0.0)
            - prev_metrics.get("excess_return", 0.0)
        ),
        "marginal_hit_rate": (
            step_metrics.get("hit_rate", 0.0)
            - prev_metrics.get("hit_rate", 0.0)
        ),
    }

    # Feature importance of the new feature
    # feature_importance keys are column names (e.g. "macd_signal"), not spec
    # names (e.g. "macd").  Sum importance across all columns that belong to
    # the added feature.
    total_importance = sum(step_feature_importance.values()) if step_feature_importance else 0.0
    cols = feature_columns or [feature_added]
    feature_imp = sum(
        step_feature_importance.get(c, 0.0) for c in cols
    )
    if total_importance > 0:
        contribution["feature_importance_pct"] = feature_imp / total_importance
    else:
        contribution["feature_importance_pct"] = 0.0

    # Rank of this feature (summed importance) among all per-column importances
    if step_feature_importance:
        sorted_features = sorted(
            step_feature_importance.values(), reverse=True
        )
        # Count how many individual column importances exceed our summed value
        contribution["feature_importance_rank"] = (
            sum(1 for v in sorted_features if v > feature_imp) + 1
        )
    else:
        contribution["feature_importance_rank"] = 0

    return contribution
