#!/usr/bin/env python3
"""Compare ML-only vs Ensemble (ML + trigger) signal generation.

Runs both methods over historical walk-forward windows and compares:
1. Sharpe ratio
2. Cumulative return
3. Max drawdown
4. Turnover / holding period
5. Win/loss rate per method
6. Trade timeline — time between rebalances

Usage:
    python scripts/compare_ensemble.py --watchlist tech_giants
    python scripts/compare_ensemble.py --watchlist tech_giants --top-n 5
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from src.config.config import load_config, load_ticker_config
from src.features.engineering import (
    compute_all_features_extended,
    make_training_dataset,
    get_feature_columns,
)
from src.data.loader import load_price_data
from src.backtest.rolling import run_walk_forward_backtest
from src.backtest.trigger_backtest import TriggerConfig, run_trigger_backtest

PROJECT_ROOT = Path(__file__).parent.parent


def get_ml_rankings(results) -> pd.DataFrame:
    """Extract per-window ML rankings from walk-forward results."""
    if results.window_results is None:
        return pd.DataFrame()

    all_rankings = []
    for wr in results.window_results:
        if wr.get("predictions") is not None:
            preds = wr["predictions"]
            if isinstance(preds, pd.DataFrame) and "prediction" in preds.columns:
                window_df = preds[["ticker", "prediction"]].copy()
                window_df["test_start"] = wr.get("test_start", "")
                window_df["test_end"] = wr.get("test_end", "")
                window_df = window_df.sort_values("prediction", ascending=False)
                window_df["ml_rank"] = range(1, len(window_df) + 1)
                all_rankings.append(window_df)

    if all_rankings:
        return pd.concat(all_rankings, ignore_index=True)
    return pd.DataFrame()


def get_trigger_scores(price_df: pd.DataFrame, tickers: List[str]) -> Dict[str, float]:
    """Run trigger backtest for each ticker using per-ticker optimized params."""
    scores = {}
    for ticker in tickers:
        ticker_cfg = load_ticker_config(ticker)
        if not ticker_cfg or "trigger" not in ticker_cfg:
            scores[ticker] = 0.0
            continue

        t = ticker_cfg["trigger"]
        config = TriggerConfig(
            signal_type="combined",
            combined_use_rsi=True,
            combined_use_macd=True,
            combined_use_bollinger=False,
            macd_fast=int(t.get("macd_fast", 12)),
            macd_slow=int(t.get("macd_slow", 26)),
            macd_signal=int(t.get("macd_signal", 9)),
            rsi_period=int(t.get("rsi_period", 14)),
            rsi_overbought=float(t.get("rsi_overbought", 70)),
            rsi_oversold=float(t.get("rsi_oversold", 30)),
        )

        sub = price_df[price_df["ticker"] == ticker].copy()
        if len(sub) < 100:
            scores[ticker] = 0.0
            continue

        try:
            res = run_trigger_backtest(sub, config)
            scores[ticker] = res.metrics.get("sharpe_ratio", 0.0) or 0.0
        except Exception:
            scores[ticker] = 0.0

    return scores


def simulate_portfolio(rankings_df: pd.DataFrame, price_df: pd.DataFrame,
                       top_n: int, method_col: str) -> Dict:
    """Simulate a long-only portfolio based on rankings over time.

    For each rebalance window, pick top_n stocks, equal weight, hold until next window.
    Returns performance metrics.
    """
    # Get unique windows
    windows = rankings_df.groupby(["test_start", "test_end"]).first().reset_index()
    windows = windows.sort_values("test_start")

    daily_returns = []
    trades = []
    holdings_by_window = []
    hold_days = 7  # hold for 7 days after each rebalance

    for _, window in windows.iterrows():
        test_start = window["test_start"]

        # Get top_n for this window
        window_rankings = rankings_df[
            rankings_df["test_start"] == test_start
        ].sort_values(method_col).head(top_n)

        selected = window_rankings["ticker"].tolist()
        holdings_by_window.append({
            "test_start": test_start,
            "holdings": selected,
        })

        # Calculate 7-day forward return from rebalance date
        start_dt = pd.to_datetime(test_start)
        for ticker in selected:
            ticker_prices = price_df[
                (price_df["ticker"] == ticker) &
                (price_df["date"] >= start_dt)
            ].sort_values("date")

            if len(ticker_prices) < 2:
                continue

            entry_price = ticker_prices.iloc[0]["close"]
            # Exit after hold_days or at last available
            exit_idx = min(hold_days, len(ticker_prices) - 1)
            exit_price = ticker_prices.iloc[exit_idx]["close"]
            ret = (exit_price / entry_price) - 1

            daily_returns.append({
                "test_start": test_start,
                "ticker": ticker,
                "return": ret,
            })

    if not daily_returns:
        return {"sharpe": 0, "total_return": 0, "max_drawdown": 0, "n_windows": 0}

    returns_df = pd.DataFrame(daily_returns)

    # Per-window portfolio return (equal weight)
    window_returns = returns_df.groupby("test_start")["return"].mean()

    # Metrics
    avg_ret = window_returns.mean()
    std_ret = window_returns.std()
    sharpe = avg_ret / std_ret * np.sqrt(52) if std_ret > 0 else 0  # annualize (~weekly windows)

    cumulative = (1 + window_returns).cumprod()
    peak = cumulative.cummax()
    drawdown = (cumulative / peak) - 1
    max_dd = drawdown.min()

    total_return = cumulative.iloc[-1] - 1 if len(cumulative) > 0 else 0

    # Win rate
    win_rate = (window_returns > 0).mean()

    # Turnover
    turnover_count = 0
    prev_holdings = set()
    for h in holdings_by_window:
        curr = set(h["holdings"])
        if prev_holdings:
            changed = len(curr - prev_holdings) + len(prev_holdings - curr)
            turnover_count += changed
        prev_holdings = curr

    avg_turnover = turnover_count / max(len(holdings_by_window) - 1, 1)

    return {
        "sharpe": float(sharpe),
        "total_return": float(total_return),
        "max_drawdown": float(max_dd),
        "win_rate": float(win_rate),
        "avg_window_return": float(avg_ret),
        "n_windows": len(window_returns),
        "avg_turnover_per_rebalance": float(avg_turnover),
        "n_holdings_changes": int(turnover_count),
    }


def main():
    parser = argparse.ArgumentParser(description="Compare ML-only vs Ensemble signals")
    parser.add_argument("--watchlist", "-w", default="tech_giants")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--ml-weight", type=float, default=0.7)
    parser.add_argument("--trigger-weight", type=float, default=0.3)
    args = parser.parse_args()

    config = load_config(PROJECT_ROOT / "config" / "config.yaml")

    # Load data
    print("Loading data...")
    daily_price_path = PROJECT_ROOT / config.data.price_data_path_daily
    bench_path = PROJECT_ROOT / getattr(config.data, "benchmark_data_path_daily", "data/benchmark_daily.csv")
    price_df = pd.read_csv(daily_price_path, parse_dates=["date"])
    benchmark_df = pd.read_csv(bench_path, parse_dates=["date"])

    # Filter by watchlist
    import yaml
    with open(PROJECT_ROOT / "config" / "watchlists.yaml") as f:
        watchlists = yaml.safe_load(f)
    wls = watchlists.get("watchlists", watchlists)
    wl = wls.get(args.watchlist, {})
    tickers = wl.get("symbols", [])
    price_df = price_df[price_df["ticker"].isin(tickers)]
    print(f"Watchlist: {args.watchlist} ({len(tickers)} tickers, {len(price_df)} rows)")

    # Compute features
    print("Computing features...")
    feature_cfg = config.features
    from src.config.config import bars_per_day_from_interval
    bpd = bars_per_day_from_interval("1d")

    feature_df = compute_all_features_extended(
        price_df=price_df,
        benchmark_df=benchmark_df,
        include_technical=getattr(feature_cfg, 'include_technical', True),
        include_rsi=getattr(feature_cfg, 'include_rsi', False),
        include_obv=getattr(feature_cfg, 'include_obv', False),
        include_momentum=getattr(feature_cfg, 'include_momentum', False),
        include_mean_reversion=getattr(feature_cfg, 'include_mean_reversion', False),
        bars_per_day=bpd,
    )

    training_data = make_training_dataset(
        feature_df=feature_df,
        benchmark_df=benchmark_df,
        horizon_days=feature_cfg.horizon_days,
        target_col=config.model.target_col,
        bars_per_day=bpd,
    )
    feature_cols = get_feature_columns(training_data)

    # Run walk-forward backtest
    print(f"Running walk-forward backtest ({len(feature_cols)} features)...")
    t0 = time.time()
    results = run_walk_forward_backtest(
        training_data=training_data,
        benchmark_data=benchmark_df,
        price_data=price_df,
        feature_cols=feature_cols,
        config=config.backtest,
        model_config=config.model,
        verbose=False,
    )
    elapsed = time.time() - t0
    print(f"Backtest complete in {elapsed:.0f}s. Overall Sharpe={results.metrics.get('sharpe_ratio', 0):.3f}")

    # Extract per-date predictions from walk-forward
    print("Extracting per-date ML predictions...")
    all_preds = results.predictions
    if all_preds is None or all_preds.empty:
        print("ERROR: No predictions data. Cannot compare.")
        return 1

    all_preds["date"] = pd.to_datetime(all_preds["date"], format="mixed")

    # Sample to weekly rebalance dates (every 7th unique date)
    unique_dates = sorted(all_preds["date"].unique())
    rebalance_dates = unique_dates[::7]  # weekly rebalance
    ml_rankings = all_preds[all_preds["date"].isin(rebalance_dates)].copy()

    # Rank per date
    ml_rankings["ml_rank"] = ml_rankings.groupby("date")["prediction"].rank(
        ascending=False, method="first"
    ).astype(int)

    # Use date as window identifier
    ml_rankings["test_start"] = ml_rankings["date"].dt.strftime("%Y-%m-%d")
    ml_rankings["test_end"] = ml_rankings["date"].dt.strftime("%Y-%m-%d")

    n_dates = ml_rankings["date"].nunique()
    print(f"  {len(ml_rankings)} predictions across {n_dates} rebalance dates")

    # Get trigger scores
    print("Running trigger backtests for ensemble...")
    trigger_scores = get_trigger_scores(price_df, tickers)
    n_with_config = sum(1 for v in trigger_scores.values() if v != 0.0)
    print(f"  {n_with_config}/{len(tickers)} tickers have per-ticker trigger configs")

    # Create ensemble rankings
    print("Computing ensemble rankings...")
    ml_rankings["trigger_score"] = ml_rankings["ticker"].map(trigger_scores).fillna(0.0)

    # Normalize per window
    def normalize_col(group, col):
        vals = group[col].values
        mn, mx = vals.min(), vals.max()
        rng = mx - mn
        return (vals - mn) / rng if rng > 0 else np.full_like(vals, 0.5)

    ml_rankings["ml_norm"] = ml_rankings.groupby(["test_start", "test_end"])["prediction"].transform(
        lambda x: (x - x.min()) / (x.max() - x.min()) if x.max() != x.min() else 0.5
    )

    # Trigger scores are static (same for all windows), normalize globally
    t_vals = ml_rankings["trigger_score"].values
    t_min, t_max = t_vals.min(), t_vals.max()
    t_range = t_max - t_min
    ml_rankings["trigger_norm"] = (t_vals - t_min) / t_range if t_range > 0 else 0.5

    ml_rankings["ensemble_score"] = (
        args.ml_weight * ml_rankings["ml_norm"] +
        args.trigger_weight * ml_rankings["trigger_norm"]
    )

    # Rank by ensemble per window
    ml_rankings["ensemble_rank"] = ml_rankings.groupby(
        ["test_start", "test_end"]
    )["ensemble_score"].rank(ascending=False, method="first").astype(int)

    # Simulate both portfolios
    print(f"\nSimulating portfolios (top_n={args.top_n})...")

    ml_metrics = simulate_portfolio(ml_rankings, price_df, args.top_n, "ml_rank")
    print(f"  ML-only:  Sharpe={ml_metrics['sharpe']:.3f}, Return={ml_metrics['total_return']*100:.1f}%, "
          f"MaxDD={ml_metrics['max_drawdown']*100:.1f}%, WinRate={ml_metrics['win_rate']:.1%}")

    ens_metrics = simulate_portfolio(ml_rankings, price_df, args.top_n, "ensemble_rank")
    print(f"  Ensemble: Sharpe={ens_metrics['sharpe']:.3f}, Return={ens_metrics['total_return']*100:.1f}%, "
          f"MaxDD={ens_metrics['max_drawdown']*100:.1f}%, WinRate={ens_metrics['win_rate']:.1%}")

    # Comparison
    print("\n" + "=" * 70)
    print("COMPARISON: ML-Only vs Ensemble (ML {:.0%} + Trigger {:.0%})".format(
        args.ml_weight, args.trigger_weight))
    print("=" * 70)

    print(f"\n{'Metric':<30} {'ML-Only':>12} {'Ensemble':>12} {'Delta':>12}")
    print("-" * 66)

    metrics_to_compare = [
        ("Sharpe Ratio", "sharpe", "{:.3f}"),
        ("Total Return", "total_return", "{:.1%}"),
        ("Max Drawdown", "max_drawdown", "{:.1%}"),
        ("Win Rate", "win_rate", "{:.1%}"),
        ("Avg Window Return", "avg_window_return", "{:.2%}"),
        ("Avg Turnover/Rebalance", "avg_turnover_per_rebalance", "{:.1f}"),
        ("Windows Evaluated", "n_windows", "{:.0f}"),
    ]

    for label, key, fmt in metrics_to_compare:
        ml_val = ml_metrics[key]
        ens_val = ens_metrics[key]
        delta = ens_val - ml_val
        print(f"{label:<30} {fmt.format(ml_val):>12} {fmt.format(ens_val):>12} {fmt.format(delta):>12}")

    # Verdict
    print("\n" + "-" * 66)
    if ens_metrics["sharpe"] > ml_metrics["sharpe"] * 1.05:
        verdict = "ENSEMBLE WINS — Sharpe improved by {:.1%}".format(
            (ens_metrics["sharpe"] - ml_metrics["sharpe"]) / ml_metrics["sharpe"]
        )
    elif ml_metrics["sharpe"] > ens_metrics["sharpe"] * 1.05:
        verdict = "ML-ONLY WINS — Ensemble hurts Sharpe by {:.1%}".format(
            (ml_metrics["sharpe"] - ens_metrics["sharpe"]) / ml_metrics["sharpe"]
        )
    else:
        verdict = "NO SIGNIFICANT DIFFERENCE — within 5% of each other"
    print(f"VERDICT: {verdict}")

    # Save report
    report = {
        "watchlist": args.watchlist,
        "top_n": args.top_n,
        "ml_weight": args.ml_weight,
        "trigger_weight": args.trigger_weight,
        "n_tickers": len(tickers),
        "n_with_trigger_config": n_with_config,
        "ml_metrics": ml_metrics,
        "ensemble_metrics": ens_metrics,
        "verdict": verdict,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    report_path = PROJECT_ROOT / "output" / "reports" / f"ensemble_comparison_{args.watchlist}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
