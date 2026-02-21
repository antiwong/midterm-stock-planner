#!/usr/bin/env python3
"""
Diversified Strategy Backtest (QuantaAlpha-inspired).

Runs N strategy templates in parallel, reports correlation matrix of portfolio
returns, and selects a diversified subset for the evolution pool. Ensures low
correlation between seed strategies to avoid local optima.

Usage:
    python scripts/diversified_backtest.py
    python scripts/diversified_backtest.py --templates value_tilt momentum_tilt quality_tilt
    python scripts/diversified_backtest.py --watchlist tech_giants --max-correlation 0.7
    python scripts/diversified_backtest.py --output output/diversified_report.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_template(template_path: Path) -> dict:
    """Load YAML template."""
    import yaml
    with open(template_path) as f:
        return yaml.safe_load(f) or {}


def _apply_template_to_config(base_config: "AppConfig", template: dict) -> "AppConfig":
    """Merge template overrides into base config. Returns new AppConfig."""
    from dataclasses import replace
    from src.config.config import BacktestConfig

    cfg = base_config
    bt = template.get("backtest", {})
    if bt:
        cfg = replace(
            cfg,
            backtest=BacktestConfig(
                train_years=bt.get("train_years", cfg.backtest.train_years),
                test_years=bt.get("test_years", cfg.backtest.test_years),
                step_value=bt.get("step_value", cfg.backtest.step_value),
                step_unit=bt.get("step_unit", cfg.backtest.step_unit),
                rebalance_freq=bt.get("rebalance_freq", cfg.backtest.rebalance_freq),
                top_n=bt.get("top_n", cfg.backtest.top_n),
                top_pct=bt.get("top_pct", cfg.backtest.top_pct),
                min_stocks=bt.get("min_stocks", cfg.backtest.min_stocks),
                transaction_cost=bt.get("transaction_cost", cfg.backtest.transaction_cost),
                start_date=bt.get("start_date", cfg.backtest.start_date),
                end_date=bt.get("end_date", cfg.backtest.end_date),
            ),
        )
    return cfg


def _run_template_backtest(
    config: "AppConfig",
    template_name: str,
    universe: Optional[List[str]],
    verbose: bool,
) -> Tuple[Optional["pd.Series"], Dict[str, float], Optional[Exception]]:
    """Run backtest for one template. Returns (returns_series, metrics, error)."""
    import pandas as pd
    from src.pipeline import run_full_pipeline

    try:
        results = run_full_pipeline(
            config=config,
            save_model=False,
            verbose=verbose,
            universe=universe,
        )
        bt = results["backtest_results"]
        returns = bt.portfolio_returns
        metrics = bt.metrics
        return returns, metrics, None
    except Exception as e:
        return None, {}, e


def _align_returns(returns_dict: Dict[str, "pd.Series"]) -> "pd.DataFrame":
    """Align return series to common dates, forward-fill missing."""
    import pandas as pd

    if not returns_dict:
        return pd.DataFrame()
    df = pd.concat(returns_dict, axis=1, sort=True)
    df = df.sort_index()
    df = df.ffill().bfill()
    return df


def _select_diversified(
    corr_matrix: "pd.DataFrame",
    max_correlation: float,
    min_strategies: int = 2,
) -> List[str]:
    """
    Greedy selection: pick strategies so max pairwise correlation <= max_correlation.
    Start with first strategy, add others that keep max corr with selected below limit.
    """
    names = list(corr_matrix.columns)
    if len(names) <= 1:
        return names
    selected = [names[0]]
    for name in names[1:]:
        if name in selected:
            continue
        max_corr_with_selected = max(
            abs(corr_matrix.loc[s, name]) for s in selected
        )
        if max_corr_with_selected <= max_correlation:
            selected.append(name)
    if len(selected) < min_strategies and len(names) >= min_strategies:
        for name in names:
            if name not in selected and len(selected) < min_strategies:
                selected.append(name)
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run diversified strategy backtest: N templates, correlation matrix, select diverse subset"
    )
    parser.add_argument("--config", "-c", default="config/config.yaml", help="Base config")
    parser.add_argument(
        "--templates", "-t",
        nargs="*",
        default=None,
        help="Template names (e.g. value_tilt momentum_tilt). Default: all in config/strategy_templates/",
    )
    parser.add_argument("--watchlist", "-w", help="Watchlist name")
    parser.add_argument(
        "--max-correlation",
        type=float,
        default=0.85,
        help="Max pairwise correlation for diversified subset (default 0.85)",
    )
    parser.add_argument("--output", "-o", help="Output JSON path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose backtest output")
    args = parser.parse_args()

    from src.config.config import load_config
    from src.data.watchlists import WatchlistManager
    import pandas as pd
    import numpy as np

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config not found: {config_path}")
        return 1

    base_config = load_config(config_path)
    base_config.cli.save_results = False
    base_config.features.use_sentiment = False

    # Resolve universe
    universe = None
    if args.watchlist:
        wl_manager = WatchlistManager.from_config_dir("config")
        wl = wl_manager.get_watchlist(args.watchlist)
        if wl:
            universe = wl.symbols
            print(f"Watchlist: {wl.name} ({len(universe)} tickers)")
        else:
            print(f"Warning: Watchlist '{args.watchlist}' not found")

    # Resolve templates
    templates_dir = PROJECT_ROOT / "config" / "strategy_templates"
    if args.templates:
        template_names = args.templates
        template_paths = [templates_dir / f"{n}.yaml" for n in template_names]
    else:
        template_paths = sorted(templates_dir.glob("*.yaml"))
        template_names = [p.stem for p in template_paths]

    if not template_paths:
        print("Error: No templates found")
        return 1

    print("=" * 60)
    print("Diversified Strategy Backtest")
    print("=" * 60)
    print(f"Templates: {', '.join(template_names)}")
    print("=" * 60)

    returns_dict: Dict[str, pd.Series] = {}
    metrics_dict: Dict[str, Dict[str, float]] = {}
    errors: Dict[str, str] = {}

    for name, path in zip(template_names, template_paths):
        if not path.exists():
            print(f"  Skip {name}: not found")
            continue
        template = _load_template(path)
        merged_config = _apply_template_to_config(base_config, template)
        desc = template.get("description", name)
        print(f"\nRunning {name}: {desc[:50]}...")
        ret, metrics, err = _run_template_backtest(
            merged_config, name, universe, args.verbose
        )
        if err:
            print(f"  Failed: {err}")
            errors[name] = str(err)
            continue
        returns_dict[name] = ret
        metrics_dict[name] = metrics
        sharpe = metrics.get("sharpe_ratio", 0) or 0
        total_ret = metrics.get("total_return", 0) or 0
        print(f"  Sharpe: {sharpe:.3f}  Total Return: {total_ret:.2%}")

    if len(returns_dict) < 2:
        print("\nNeed at least 2 successful templates for correlation matrix")
        if errors:
            print("Errors:", errors)
        return 1

    # Align returns and compute correlation
    aligned = _align_returns(returns_dict)
    corr_matrix = aligned.corr()

    print("\n" + "=" * 60)
    print("Correlation Matrix (portfolio returns)")
    print("=" * 60)
    print(corr_matrix.round(3).to_string())

    # Select diversified subset
    selected = _select_diversified(corr_matrix, args.max_correlation)
    print(f"\nDiversified subset (max_corr<={args.max_correlation}): {', '.join(selected)}")

    # Build report
    report = {
        "templates_run": list(returns_dict.keys()),
        "templates_failed": list(errors.keys()),
        "errors": errors,
        "metrics": metrics_dict,
        "correlation_matrix": corr_matrix.round(4).to_dict(),
        "diversified_subset": selected,
        "max_correlation_threshold": args.max_correlation,
    }

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nReport saved to: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
