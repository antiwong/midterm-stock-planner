#!/usr/bin/env python3
"""Retrain walk-forward backtest model and report results.

Designed for the 32-core compute server. Runs the full walk-forward
backtest with configurable overrides, then prints a structured report.

Usage:
    python scripts/run_retrain.py --watchlist tech_giants
    python scripts/run_retrain.py --watchlist tech_giants --transaction-cost 0.005
    python scripts/run_retrain.py --watchlist tech_giants --non-overlapping
"""

import argparse
import sys
import os
import time
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

import numpy as np
import pandas as pd

from dotenv import load_dotenv
load_dotenv()

from src.config.config import (
    load_config, BacktestConfig, ModelConfig,
    bars_per_day_from_interval,
)
from src.features.engineering import (
    compute_all_features_extended,
    make_training_dataset,
    get_feature_columns,
)
from src.backtest.rolling import run_walk_forward_backtest


def build_config_overrides(args, base_config) -> BacktestConfig:
    """Build a BacktestConfig with CLI overrides applied."""
    bc = base_config.backtest

    step_value = bc.step_value
    step_unit = bc.step_unit

    if args.non_overlapping:
        # Non-overlapping: step = test period length
        test_days = int(bc.test_years * 365.25)
        step_value = test_days
        step_unit = "days"

    transaction_cost = args.transaction_cost if args.transaction_cost is not None else bc.transaction_cost

    return BacktestConfig(
        train_years=bc.train_years,
        test_years=bc.test_years,
        step_value=step_value,
        step_unit=step_unit,
        rebalance_freq=bc.rebalance_freq,
        top_n=args.top_n or bc.top_n,
        top_pct=bc.top_pct,
        min_stocks=bc.min_stocks,
        transaction_cost=transaction_cost,
        start_date=bc.start_date,
        end_date=bc.end_date,
    )


def load_data(config, watchlist: str):
    """Load price data, compute features, build training dataset."""
    daily_price_path = PROJECT_ROOT / config.data.price_data_path_daily
    daily_bench_path = PROJECT_ROOT / getattr(
        config.data, "benchmark_data_path_daily", "data/benchmark_daily.csv"
    )

    price_df = pd.read_csv(daily_price_path, parse_dates=["date"])
    benchmark_df = pd.read_csv(daily_bench_path, parse_dates=["date"])

    # Load watchlist tickers
    import yaml
    wl_path = PROJECT_ROOT / "config" / "watchlists.yaml"
    with open(wl_path) as f:
        wl_data = yaml.safe_load(f)
    symbols = [str(s) for s in wl_data["watchlists"][watchlist]["symbols"]]
    price_df = price_df[price_df["ticker"].isin(symbols)]

    n_tickers = price_df["ticker"].nunique()
    feature_cfg = config.features
    bpd = bars_per_day_from_interval("1d")

    print(f"Computing features for {n_tickers} tickers...")
    feature_df = compute_all_features_extended(
        price_df=price_df,
        fundamental_df=None,
        benchmark_df=benchmark_df,
        include_technical=getattr(feature_cfg, "include_technical", True),
        include_rsi=getattr(feature_cfg, "include_rsi", False),
        include_obv=False,  # OBV disabled per request
        include_momentum=getattr(feature_cfg, "include_momentum", False),
        include_mean_reversion=getattr(feature_cfg, "include_mean_reversion", False),
        bars_per_day=bpd,
        rsi_period=feature_cfg.rsi_period,
        macd_fast=feature_cfg.macd_fast,
        macd_slow=feature_cfg.macd_slow,
        macd_signal=feature_cfg.macd_signal,
    )

    training_data = make_training_dataset(
        feature_df=feature_df,
        benchmark_df=benchmark_df,
        horizon_days=feature_cfg.horizon_days,
        target_col=config.model.target_col,
        bars_per_day=bpd,
    )

    feature_cols = get_feature_columns(training_data)
    return training_data, feature_cols, price_df, benchmark_df


def compute_trade_stats(results) -> dict:
    """Compute win rate and average return per trade from positions."""
    positions = results.positions
    price_data = None

    # Reconstruct per-rebalance returns from portfolio_returns
    port_ret = results.portfolio_returns
    if port_ret is None or len(port_ret) == 0:
        return {"win_rate": 0, "avg_return": 0, "n_trades": 0}

    # Use daily portfolio returns as proxy for trade returns
    wins = (port_ret > 0).sum()
    total = len(port_ret)
    return {
        "win_rate": float(wins / total) if total > 0 else 0,
        "avg_return": float(port_ret.mean()),
        "n_trades": total,
        "n_winning": int(wins),
        "n_losing": int(total - wins),
    }


def print_report(results, trade_stats: dict, elapsed: float, args):
    """Print structured results report."""
    m = results.metrics
    wr = results.window_results

    print("\n" + "=" * 70)
    print("RETRAIN REPORT — {} ({} tickers)".format(
        args.watchlist, len(results.final_scores) if results.final_scores is not None else 0))
    print("=" * 70)

    # Settings
    print("\nSETTINGS:")
    print("  Train: {:.1f}y, Test: {:.1f}y".format(
        args.config.train_years, args.config.test_years))
    step_desc = "non-overlapping" if args.non_overlapping else "{} {}".format(
        args.config.step_value, args.config.step_unit)
    print("  Step: {} → {} windows".format(step_desc, len(wr)))
    print("  Transaction cost: {:.1%} per side".format(args.config.transaction_cost))
    print("  OBV: disabled")
    print("  Elapsed: {:.0f}s ({} cores)".format(elapsed, os.cpu_count()))

    # 1. Sharpe ratio
    print("\n1. PERFORMANCE:")
    print("  Sharpe ratio:      {:.3f}".format(m.get("sharpe_ratio", 0)))
    print("  Annualized return: {:+.2%}".format(m.get("annualized_return", 0)))
    print("  Total return:      {:+.2%}".format(m.get("total_return", 0)))
    print("  Max drawdown:      {:.2%}".format(m.get("max_drawdown", 0)))
    print("  Volatility:        {:.2%}".format(m.get("volatility", 0)))
    print("  Excess vs SPY:     {:+.2%}".format(m.get("excess_return", 0)))

    # Overfitting check
    if "median_train_test_sharpe_ratio" in m:
        ratio = m["median_train_test_sharpe_ratio"]
        flag = " ⚠ OVERFIT" if ratio > 2.0 else ""
        print("  Train/Test Sharpe: {:.2f} (median){}".format(ratio, flag))

    # 2. IC
    print("\n2. INFORMATION COEFFICIENT:")
    ics = [w["ic"] for w in wr if w.get("ic") is not None and not np.isnan(w["ic"])]
    rank_ics = [w["rank_ic"] for w in wr if w.get("rank_ic") is not None and not np.isnan(w["rank_ic"])]
    if ics:
        print("  Mean IC (Pearson):  {:.4f} ± {:.4f}".format(np.mean(ics), np.std(ics)))
    if rank_ics:
        print("  Mean IC (Spearman): {:.4f} ± {:.4f}".format(np.mean(rank_ics), np.std(rank_ics)))
        # IC by quintile
        q = np.percentile(rank_ics, [25, 50, 75])
        print("  IC quartiles:       Q1={:.4f}  median={:.4f}  Q3={:.4f}".format(q[0], q[1], q[2]))
    else:
        print("  No IC data available")

    # 3. Feature importance
    print("\n3. TOP 10 FEATURES (by LightGBM gain):")
    gain = m.get("feature_importance_gain", {})
    if gain:
        sorted_feats = sorted(gain.items(), key=lambda x: x[1], reverse=True)[:10]
        max_val = sorted_feats[0][1] if sorted_feats else 1
        for i, (feat, val) in enumerate(sorted_feats, 1):
            bar = "█" * int(30 * val / max_val)
            print("  {:2d}. {:30s} {:>8.0f}  {}".format(i, feat, val, bar))
    else:
        print("  No feature importance data")

    # Marginal IC (model-free predictive power)
    mic = m.get("marginal_ic_mean", {})
    if mic:
        print("\n   TOP 10 FEATURES (by marginal Rank IC — model-free):")
        sorted_mic = sorted(mic.items(), key=lambda x: abs(x[1]), reverse=True)[:10]
        for i, (feat, val) in enumerate(sorted_mic, 1):
            print("  {:2d}. {:30s} {:+.4f}".format(i, feat, val))

    # 4. Trade stats
    print("\n4. TRADE STATISTICS:")
    print("  Win rate:          {:.1%} ({}/{})".format(
        trade_stats["win_rate"], trade_stats["n_winning"], trade_stats["n_trades"]))
    print("  Avg daily return:  {:+.4%}".format(trade_stats["avg_return"]))
    if trade_stats["n_trades"] > 0:
        port_ret = results.portfolio_returns
        pos_mean = port_ret[port_ret > 0].mean() if (port_ret > 0).any() else 0
        neg_mean = port_ret[port_ret <= 0].mean() if (port_ret <= 0).any() else 0
        print("  Avg winning day:   {:+.4%}".format(pos_mean))
        print("  Avg losing day:    {:+.4%}".format(neg_mean))
        if neg_mean != 0:
            print("  Profit factor:     {:.2f}".format(abs(pos_mean / neg_mean)))

    # Window-level Sharpe distribution
    test_sharpes = [w["test_sharpe"] for w in wr if w.get("test_sharpe") is not None]
    if test_sharpes:
        print("\n   Per-window Sharpe distribution:")
        print("     min={:.2f}  median={:.2f}  max={:.2f}  std={:.2f}".format(
            np.min(test_sharpes), np.median(test_sharpes),
            np.max(test_sharpes), np.std(test_sharpes)))
        n_positive = sum(1 for s in test_sharpes if s > 0)
        print("     Positive Sharpe windows: {}/{} ({:.0%})".format(
            n_positive, len(test_sharpes), n_positive / len(test_sharpes)))

    # Latest signals
    if results.final_scores is not None and len(results.final_scores) > 0:
        print("\n   LATEST SIGNALS (ranked by prediction):")
        top_n = args.config.top_n or 5
        scores = results.final_scores.head(top_n)
        for _, row in scores.iterrows():
            print("     #{:<2d} {:6s}  score={:+.4f}".format(
                int(row["rank"]), row["ticker"], row["prediction"]))

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Retrain walk-forward model")
    parser.add_argument("--watchlist", required=True, help="Watchlist name")
    parser.add_argument("--transaction-cost", type=float, default=None,
                        help="Transaction cost per side (default: from config)")
    parser.add_argument("--non-overlapping", action="store_true",
                        help="Non-overlapping windows (step = test period)")
    parser.add_argument("--top-n", type=int, default=None,
                        help="Number of top stocks to select")
    parser.add_argument("--exclude-features", nargs="+", default=[],
                        help="Features to exclude from model")
    parser.add_argument("--invert-features", nargs="+", default=[],
                        help="Features to invert (multiply by -1) before training")
    parser.add_argument("--verbose", action="store_true", help="Print per-window progress")
    args = parser.parse_args()

    config = load_config("config/config.yaml")
    bt_config = build_config_overrides(args, config)
    args.config = bt_config  # attach for report

    print("=" * 70)
    print("RETRAIN — {} | tx_cost={:.1%} | step={}".format(
        args.watchlist, bt_config.transaction_cost,
        "non-overlapping" if args.non_overlapping else "{} {}".format(
            bt_config.step_value, bt_config.step_unit)))
    print("=" * 70)

    # Load data
    training_data, feature_cols, price_df, benchmark_df = load_data(config, args.watchlist)

    # Feature exclusions
    if args.exclude_features:
        removed = [f for f in args.exclude_features if f in feature_cols]
        feature_cols = [f for f in feature_cols if f not in args.exclude_features]
        if removed:
            print("Excluded features: {}".format(", ".join(removed)))

    # Feature inversions (multiply by -1 so low values rank high)
    if args.invert_features:
        for feat in args.invert_features:
            if feat in training_data.columns:
                # Replace with per-date rank inverted (lower raw value = higher rank)
                training_data[feat] = training_data.groupby("date")[feat].rank(ascending=True)
                print("Inverted feature: {} (low-vol rank, ascending=True)".format(feat))

    print("Training data: {:,} rows, {} features".format(len(training_data), len(feature_cols)))

    # Run backtest
    t0 = time.time()
    results = run_walk_forward_backtest(
        training_data=training_data,
        benchmark_data=benchmark_df,
        price_data=price_df,
        feature_cols=feature_cols,
        config=bt_config,
        model_config=config.model,
        verbose=args.verbose,
    )
    elapsed = time.time() - t0

    # Apply transaction costs to portfolio returns (the engine doesn't deduct them)
    tx_cost = bt_config.transaction_cost
    if tx_cost > 0 and results.positions is not None and len(results.positions) > 0:
        positions_pivot = results.positions.pivot_table(
            index="date", columns="ticker", values="weight", fill_value=0.0
        )
        if len(positions_pivot) > 1:
            # Turnover per rebalance = sum of absolute weight changes
            turnover_per_rebal = positions_pivot.diff().abs().sum(axis=1)
            # Spread cost across trading days between rebalances
            rebal_dates = sorted(results.positions["date"].unique())
            port_ret = results.portfolio_returns.copy()
            for i in range(1, len(rebal_dates)):
                rebal = rebal_dates[i]
                prev = rebal_dates[i - 1]
                days_between = port_ret.index[(port_ret.index > prev) & (port_ret.index <= rebal)]
                if len(days_between) > 0 and rebal in turnover_per_rebal.index:
                    daily_cost = (turnover_per_rebal[rebal] * tx_cost) / len(days_between)
                    port_ret[days_between] -= daily_cost
            results = type(results)(
                portfolio_returns=port_ret,
                benchmark_returns=results.benchmark_returns,
                positions=results.positions,
                metrics=results.metrics,
                window_results=results.window_results,
                predictions=results.predictions,
                final_scores=results.final_scores,
            )
            # Recompute metrics with cost-adjusted returns
            from src.backtest.rolling import _calculate_metrics
            results.metrics.update(_calculate_metrics(
                port_ret, results.benchmark_returns, results.positions
            ))
            print("Transaction costs applied: {:.1%} per side on {:.2f} avg turnover".format(
                tx_cost, turnover_per_rebal.mean()))

    # Trade stats
    trade_stats = compute_trade_stats(results)

    # Report
    print_report(results, trade_stats, elapsed, args)


if __name__ == "__main__":
    main()
