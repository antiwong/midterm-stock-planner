"""A/B backtest comparison utilities.

This module provides functions to compare backtests with and without
sentiment features to evaluate the impact of sentiment on strategy
performance.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import json


@dataclass
class BacktestComparisonResult:
    """Results from comparing two backtests (A/B test)."""
    
    # Names
    baseline_name: str
    variant_name: str
    
    # Performance metrics for each
    baseline_metrics: Dict[str, float]
    variant_metrics: Dict[str, float]
    
    # Differences
    metric_differences: Dict[str, float]
    
    # Statistical significance (optional)
    significance_tests: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Feature analysis (optional)
    baseline_feature_importance: Optional[Dict[str, float]] = None
    variant_feature_importance: Optional[Dict[str, float]] = None
    
    # Sentiment-specific analysis
    sentiment_contribution: Optional[float] = None
    
    def __repr__(self) -> str:
        return (
            f"BacktestComparisonResult(\n"
            f"  baseline={self.baseline_name}, variant={self.variant_name}\n"
            f"  sharpe_diff={self.metric_differences.get('sharpe', 'N/A'):.4f}\n"
            f"  return_diff={self.metric_differences.get('total_return', 'N/A'):.2%}\n"
            f")"
        )


def compare_backtests(
    baseline_results: Dict[str, Any],
    variant_results: Dict[str, Any],
    baseline_name: str = "Without Sentiment",
    variant_name: str = "With Sentiment",
    metrics_to_compare: Optional[List[str]] = None,
) -> BacktestComparisonResult:
    """
    Compare two backtest results.
    
    Args:
        baseline_results: Results from baseline backtest (e.g., without sentiment).
        variant_results: Results from variant backtest (e.g., with sentiment).
        baseline_name: Name for baseline.
        variant_name: Name for variant.
        metrics_to_compare: List of metrics to compare. Uses defaults if None.
    
    Returns:
        BacktestComparisonResult with comparison data.
    """
    if metrics_to_compare is None:
        metrics_to_compare = [
            "total_return",
            "annual_return",
            "sharpe",
            "sortino",
            "max_drawdown",
            "volatility",
            "win_rate",
            "turnover",
            "hit_rate",
        ]
    
    # Extract metrics
    baseline_metrics = {}
    variant_metrics = {}
    
    for metric in metrics_to_compare:
        baseline_metrics[metric] = baseline_results.get("metrics", {}).get(metric, np.nan)
        variant_metrics[metric] = variant_results.get("metrics", {}).get(metric, np.nan)
    
    # Compute differences
    metric_differences = {}
    for metric in metrics_to_compare:
        baseline_val = baseline_metrics.get(metric, np.nan)
        variant_val = variant_metrics.get(metric, np.nan)
        if not np.isnan(baseline_val) and not np.isnan(variant_val):
            metric_differences[metric] = variant_val - baseline_val
        else:
            metric_differences[metric] = np.nan
    
    return BacktestComparisonResult(
        baseline_name=baseline_name,
        variant_name=variant_name,
        baseline_metrics=baseline_metrics,
        variant_metrics=variant_metrics,
        metric_differences=metric_differences,
    )


def run_ab_backtest(
    training_data: pd.DataFrame,
    benchmark_data: pd.DataFrame,
    price_data: pd.DataFrame,
    feature_cols_baseline: List[str],
    feature_cols_variant: List[str],
    backtest_config: Any,
    model_config: Optional[Any] = None,
) -> BacktestComparisonResult:
    """
    Run A/B comparison of backtests with different feature sets.
    
    This is typically used to compare:
    - Baseline: Features without sentiment
    - Variant: Features with sentiment
    
    Args:
        training_data: Full training dataset with all features.
        benchmark_data: Benchmark price data.
        price_data: Stock price data.
        feature_cols_baseline: Feature columns for baseline (without sentiment).
        feature_cols_variant: Feature columns for variant (with sentiment).
        backtest_config: Backtest configuration.
        model_config: Optional model configuration.
    
    Returns:
        BacktestComparisonResult comparing the two backtests.
    """
    try:
        from .rolling import run_walk_forward_backtest
    except ImportError:
        raise ImportError("Rolling backtest module not available")
    
    # Run baseline backtest
    print("Running baseline backtest (without sentiment)...")
    baseline_results = run_walk_forward_backtest(
        training_data=training_data,
        benchmark_data=benchmark_data,
        price_data=price_data,
        feature_cols=feature_cols_baseline,
        config=backtest_config,
        model_config=model_config,
    )
    
    # Run variant backtest
    print("Running variant backtest (with sentiment)...")
    variant_results = run_walk_forward_backtest(
        training_data=training_data,
        benchmark_data=benchmark_data,
        price_data=price_data,
        feature_cols=feature_cols_variant,
        config=backtest_config,
        model_config=model_config,
    )
    
    # Convert results to dict format
    baseline_dict = {
        "metrics": baseline_results.metrics if hasattr(baseline_results, "metrics") else {},
    }
    variant_dict = {
        "metrics": variant_results.metrics if hasattr(variant_results, "metrics") else {},
    }
    
    # Compare
    comparison = compare_backtests(
        baseline_results=baseline_dict,
        variant_results=variant_dict,
        baseline_name="Without Sentiment",
        variant_name="With Sentiment",
    )
    
    return comparison


def format_comparison_report(
    comparison: BacktestComparisonResult,
    format: str = "text",
) -> str:
    """
    Format comparison results as a readable report.
    
    Args:
        comparison: BacktestComparisonResult from compare_backtests.
        format: Output format ("text" or "markdown").
    
    Returns:
        Formatted report string.
    """
    lines = []
    
    if format == "markdown":
        lines.append(f"# A/B Backtest Comparison")
        lines.append(f"")
        lines.append(f"**Baseline:** {comparison.baseline_name}")
        lines.append(f"**Variant:** {comparison.variant_name}")
        lines.append(f"")
        lines.append(f"## Performance Metrics")
        lines.append(f"")
        lines.append(f"| Metric | Baseline | Variant | Difference |")
        lines.append(f"|--------|----------|---------|------------|")
        
        for metric in comparison.baseline_metrics.keys():
            baseline_val = comparison.baseline_metrics.get(metric, np.nan)
            variant_val = comparison.variant_metrics.get(metric, np.nan)
            diff = comparison.metric_differences.get(metric, np.nan)
            
            # Format based on metric type
            if "return" in metric.lower() or "drawdown" in metric.lower():
                baseline_str = f"{baseline_val:.2%}" if not np.isnan(baseline_val) else "N/A"
                variant_str = f"{variant_val:.2%}" if not np.isnan(variant_val) else "N/A"
                diff_str = f"{diff:+.2%}" if not np.isnan(diff) else "N/A"
            else:
                baseline_str = f"{baseline_val:.4f}" if not np.isnan(baseline_val) else "N/A"
                variant_str = f"{variant_val:.4f}" if not np.isnan(variant_val) else "N/A"
                diff_str = f"{diff:+.4f}" if not np.isnan(diff) else "N/A"
            
            lines.append(f"| {metric} | {baseline_str} | {variant_str} | {diff_str} |")
        
        lines.append(f"")
        lines.append(f"## Summary")
        lines.append(f"")
        
        # Determine winner
        sharpe_diff = comparison.metric_differences.get("sharpe", 0)
        if sharpe_diff > 0.05:
            lines.append(f"✅ **Sentiment improves Sharpe ratio by {sharpe_diff:.4f}**")
        elif sharpe_diff < -0.05:
            lines.append(f"❌ **Sentiment hurts Sharpe ratio by {abs(sharpe_diff):.4f}**")
        else:
            lines.append(f"➖ **Sentiment has minimal impact on Sharpe ratio ({sharpe_diff:+.4f})**")
    
    else:  # text format
        lines.append(f"=" * 60)
        lines.append(f"A/B BACKTEST COMPARISON")
        lines.append(f"=" * 60)
        lines.append(f"")
        lines.append(f"Baseline: {comparison.baseline_name}")
        lines.append(f"Variant:  {comparison.variant_name}")
        lines.append(f"")
        lines.append(f"-" * 60)
        lines.append(f"{'Metric':<20} {'Baseline':>12} {'Variant':>12} {'Diff':>12}")
        lines.append(f"-" * 60)
        
        for metric in comparison.baseline_metrics.keys():
            baseline_val = comparison.baseline_metrics.get(metric, np.nan)
            variant_val = comparison.variant_metrics.get(metric, np.nan)
            diff = comparison.metric_differences.get(metric, np.nan)
            
            if "return" in metric.lower() or "drawdown" in metric.lower():
                baseline_str = f"{baseline_val:.2%}" if not np.isnan(baseline_val) else "N/A"
                variant_str = f"{variant_val:.2%}" if not np.isnan(variant_val) else "N/A"
                diff_str = f"{diff:+.2%}" if not np.isnan(diff) else "N/A"
            else:
                baseline_str = f"{baseline_val:.4f}" if not np.isnan(baseline_val) else "N/A"
                variant_str = f"{variant_val:.4f}" if not np.isnan(variant_val) else "N/A"
                diff_str = f"{diff:+.4f}" if not np.isnan(diff) else "N/A"
            
            lines.append(f"{metric:<20} {baseline_str:>12} {variant_str:>12} {diff_str:>12}")
        
        lines.append(f"-" * 60)
        lines.append(f"")
        
        sharpe_diff = comparison.metric_differences.get("sharpe", 0)
        if sharpe_diff > 0.05:
            lines.append(f"RESULT: Sentiment IMPROVES Sharpe by {sharpe_diff:.4f}")
        elif sharpe_diff < -0.05:
            lines.append(f"RESULT: Sentiment HURTS Sharpe by {abs(sharpe_diff):.4f}")
        else:
            lines.append(f"RESULT: Sentiment has MINIMAL impact ({sharpe_diff:+.4f})")
    
    return "\n".join(lines)


def save_comparison_results(
    comparison: BacktestComparisonResult,
    output_path: Path,
) -> None:
    """
    Save comparison results to JSON file.
    
    Args:
        comparison: Comparison results to save.
        output_path: Path to save JSON file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "baseline_name": comparison.baseline_name,
        "variant_name": comparison.variant_name,
        "baseline_metrics": comparison.baseline_metrics,
        "variant_metrics": comparison.variant_metrics,
        "metric_differences": comparison.metric_differences,
        "sentiment_contribution": comparison.sentiment_contribution,
    }
    
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def get_sentiment_feature_columns(all_features: List[str]) -> Tuple[List[str], List[str]]:
    """
    Split features into sentiment and non-sentiment columns.
    
    Args:
        all_features: List of all feature column names.
    
    Returns:
        Tuple of (non_sentiment_features, sentiment_features).
    """
    sentiment_features = [f for f in all_features if f.startswith("sentiment_")]
    non_sentiment_features = [f for f in all_features if not f.startswith("sentiment_")]
    return non_sentiment_features, sentiment_features
