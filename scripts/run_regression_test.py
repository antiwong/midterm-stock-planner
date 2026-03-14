#!/usr/bin/env python3
"""Feature Regression Testing Script.

Adds features one-by-one, measures marginal contribution, tunes parameters,
and generates reports with statistical significance tests.

Usage:
    # Test all features sequentially (default order)
    python scripts/run_regression_test.py --watchlist tech_giants

    # Test specific features in order
    python scripts/run_regression_test.py --features rsi macd bollinger gap momentum

    # With parameter tuning
    python scripts/run_regression_test.py --watchlist tech_giants --tune --tuning-trials 50

    # With model tuning at the end
    python scripts/run_regression_test.py --tune --tune-model --tuning-trials 30

    # Custom baseline
    python scripts/run_regression_test.py --baseline returns volatility volume valuation

    # List previous regression tests
    python scripts/run_regression_test.py --list

    # Generate report for a previous test
    python scripts/run_regression_test.py --report <regression_id>
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config import load_config, bars_per_day_from_interval
from src.regression.feature_registry import FeatureRegistry, DEFAULT_BASELINE, DEFAULT_FEATURE_ORDER
from src.regression.orchestrator import RegressionOrchestrator, RegressionTestConfig
from src.regression.database import RegressionDatabase
from src.regression.reporting import RegressionReporter


def load_data(config, watchlist_name=None):
    """Load price, benchmark, and training data.

    Prefers daily data paths (10yr, 114 tickers) when available, falling back
    to the default hourly paths.
    """
    import pandas as pd
    from src.features.engineering import (
        compute_all_features_extended,
        make_training_dataset,
    )

    # Prefer daily data (10yr, more tickers) over hourly for regression testing
    daily_price_path = Path(getattr(config.data, "price_data_path_daily", "data/prices_daily.csv"))
    hourly_price_path = Path(config.data.price_data_path)
    if daily_price_path.exists():
        price_path = daily_price_path
        print(f"Using daily data: {daily_price_path}")
    else:
        price_path = hourly_price_path
        print(f"Using hourly data: {hourly_price_path}")

    price_df = pd.read_csv(price_path, parse_dates=["date"])

    # Filter by watchlist if specified
    if watchlist_name:
        try:
            import yaml
            wl_path = Path(__file__).parent.parent / "config" / "watchlists.yaml"
            with open(wl_path) as f:
                watchlists = yaml.safe_load(f)
            if watchlist_name in watchlists:
                tickers = watchlists[watchlist_name].get("tickers", [])
                if tickers:
                    price_df = price_df[price_df["ticker"].isin(tickers)]
                    print(f"Filtered to {len(tickers)} tickers from watchlist '{watchlist_name}'")
        except Exception as e:
            print(f"Warning: Could not load watchlist '{watchlist_name}': {e}")

    # Load benchmark — prefer daily
    daily_bench_path = Path(getattr(config.data, "benchmark_data_path_daily", "data/benchmark_daily.csv"))
    hourly_bench_path = Path(config.data.benchmark_data_path)
    if daily_bench_path.exists():
        bench_path = daily_bench_path
        print(f"Using daily benchmark: {daily_bench_path}")
    else:
        bench_path = hourly_bench_path
        print(f"Using hourly benchmark: {hourly_bench_path}")

    benchmark_df = pd.read_csv(bench_path, parse_dates=["date"])

    # Load fundamentals
    fundamental_df = None
    if config.data.fundamental_data_path:
        fund_path = Path(config.data.fundamental_data_path)
        if fund_path.exists():
            fundamental_df = pd.read_csv(fund_path, parse_dates=["date"])

    bpd = bars_per_day_from_interval(config.data.interval)

    # Compute ALL features (so we can selectively use subsets)
    print("Computing all features...")
    feature_df = compute_all_features_extended(
        price_df=price_df,
        fundamental_df=fundamental_df,
        benchmark_df=benchmark_df,
        include_technical=True,
        include_momentum=True,
        include_mean_reversion=True,
        bars_per_day=bpd,
        rsi_period=config.features.rsi_period,
        macd_fast=config.features.macd_fast,
        macd_slow=config.features.macd_slow,
        macd_signal=config.features.macd_signal,
    )

    # Create training dataset
    print("Creating training dataset...")
    training_data = make_training_dataset(
        feature_df=feature_df,
        benchmark_df=benchmark_df,
        horizon_days=config.features.horizon_days,
        bars_per_day=bpd,
    )

    n_tickers = training_data["ticker"].nunique()
    n_dates = training_data["date"].nunique()
    print(f"Training data: {len(training_data)} rows, {n_tickers} tickers, {n_dates} dates")

    return training_data, price_df, benchmark_df


def cmd_run(args, config):
    """Run a regression test."""
    training_data, price_df, benchmark_df = load_data(config, args.watchlist)

    registry = FeatureRegistry()

    # Determine features to test
    if args.features:
        features_to_test = args.features
    else:
        features_to_test = registry.get_default_order()

    # Filter out sentinel if present
    if args.exclude_sentiment and "sentiment" in features_to_test:
        features_to_test.remove("sentiment")

    reg_config = RegressionTestConfig(
        name=args.name or f"Regression {args.watchlist or 'default'}",
        description=args.description or "",
        baseline_features=args.baseline or list(DEFAULT_BASELINE),
        features_to_test=features_to_test,
        tune_on_add=args.tune,
        tune_model_params=args.tune_model,
        tuning_trials=args.tuning_trials,
        model_tuning_trials=args.model_tuning_trials,
        objective_metric=args.objective,
        db_path="data/runs.db",
    )

    from src.config.config import BacktestConfig, ModelConfig

    orchestrator = RegressionOrchestrator(
        config=reg_config,
        registry=registry,
        training_data=training_data,
        benchmark_data=benchmark_df,
        price_data=price_df,
        backtest_config=config.backtest,
        model_config=config.model,
    )

    results = orchestrator.run(verbose=True)

    # Generate reports
    output_dir = f"output/regression/{orchestrator.regression_id}"
    print(f"\nGenerating reports to {output_dir}...")
    reporter = RegressionReporter(
        db=orchestrator.db,
        regression_id=orchestrator.regression_id,
    )
    paths = reporter.generate_all(output_dir)
    for fmt, path in paths.items():
        print(f"  {fmt}: {path}")

    return results


def cmd_list(args):
    """List previous regression tests."""
    db = RegressionDatabase("data/runs.db")
    tests = db.list_regression_tests(status=args.status)

    if not tests:
        print("No regression tests found.")
        return

    print(f"\n{'ID':<30} {'Name':<30} {'Status':<10} {'Steps':<6} {'Sharpe':<8} {'Best Feature':<15}")
    print("-" * 100)
    for t in tests:
        print(
            f"{t['regression_id']:<30} "
            f"{(t.get('name') or '')[:29]:<30} "
            f"{t['status']:<10} "
            f"{t.get('total_steps', 0):<6} "
            f"{t.get('final_sharpe', 0) or 0:<8.4f} "
            f"{(t.get('best_feature') or '-'):<15}"
        )


def cmd_report(args):
    """Generate report for a previous test."""
    db = RegressionDatabase("data/runs.db")
    test = db.get_regression_test(args.regression_id)
    if not test:
        print(f"Regression test '{args.regression_id}' not found.")
        return

    output_dir = args.output or f"output/regression/{args.regression_id}"
    reporter = RegressionReporter(db=db, regression_id=args.regression_id)
    paths = reporter.generate_all(output_dir)
    for fmt, path in paths.items():
        print(f"  {fmt}: {path}")


def cmd_leaderboard(args):
    """Show feature leaderboard across all tests."""
    db = RegressionDatabase("data/runs.db")
    leaderboard = db.get_feature_leaderboard(
        regression_id=args.regression_id if hasattr(args, "regression_id") else None
    )

    if not leaderboard:
        print("No feature contributions found.")
        return

    print(f"\n{'Rank':<5} {'Feature':<20} {'Marginal Sharpe':<16} {'Marginal IC':<12} {'Significant':<12}")
    print("-" * 65)
    for rank, feat in enumerate(leaderboard, 1):
        ms = feat.get("marginal_sharpe", 0) or 0
        mi = feat.get("marginal_rank_ic", 0) or 0
        sig = "YES" if feat.get("is_significant") or feat.get("times_significant", 0) > 0 else "no"
        print(f"{rank:<5} {feat['feature_name']:<20} {ms:+.4f}{'':>8} {mi:+.4f}{'':>4} {sig}")


def main():
    parser = argparse.ArgumentParser(
        description="Feature Regression Testing for Backtesting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a regression test")
    run_parser.add_argument("--watchlist", "-w", help="Watchlist name")
    run_parser.add_argument("--config", "-c", default="config/config.yaml", help="Config path")
    run_parser.add_argument("--features", nargs="+", help="Features to test (in order)")
    run_parser.add_argument("--baseline", nargs="+", help="Baseline features")
    run_parser.add_argument("--tune", action="store_true", help="Tune feature params")
    run_parser.add_argument("--tune-model", action="store_true", help="Tune model hyperparams")
    run_parser.add_argument("--tuning-trials", type=int, default=30, help="Trials per feature")
    run_parser.add_argument("--model-tuning-trials", type=int, default=50, help="Model tuning trials")
    run_parser.add_argument("--objective", default="mean_rank_ic", help="Tuning objective metric")
    run_parser.add_argument("--name", "-n", help="Name for this test")
    run_parser.add_argument("--description", help="Description")
    run_parser.add_argument("--exclude-sentiment", action="store_true", help="Exclude sentiment features")

    # List command
    list_parser = subparsers.add_parser("list", help="List regression tests")
    list_parser.add_argument("--status", help="Filter by status")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate report")
    report_parser.add_argument("regression_id", help="Regression test ID")
    report_parser.add_argument("--output", "-o", help="Output directory")

    # Leaderboard command
    lb_parser = subparsers.add_parser("leaderboard", help="Show feature leaderboard")
    lb_parser.add_argument("--regression-id", help="Filter by regression test")

    args = parser.parse_args()

    if not args.command:
        # Default to "run" if no subcommand
        parser.print_help()
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.command == "run":
        config = load_config(args.config)
        cmd_run(args, config)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "leaderboard":
        cmd_leaderboard(args)


if __name__ == "__main__":
    main()
