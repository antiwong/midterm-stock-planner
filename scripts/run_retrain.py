#!/usr/bin/env python3
"""Retrain walk-forward backtest model and report results.

Designed for the 32-core compute server. Runs the full walk-forward
backtest with configurable overrides, then prints a structured report.

Supports incremental training mode (Phase 4 optimization):
    python scripts/run_retrain.py --watchlist tech_giants          # incremental if model exists
    python scripts/run_retrain.py --watchlist tech_giants --full   # force full backtest
    python scripts/run_retrain.py --watchlist tech_giants --transaction-cost 0.005
    python scripts/run_retrain.py --watchlist tech_giants --non-overlapping
"""

import argparse
import json
import sys
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
from src.models.trainer import save_model, load_model

MODEL_DIR = Path("models/")
MODEL_DIR.mkdir(exist_ok=True)

# Maximum age (days) before incremental mode falls back to full retrain
INCREMENTAL_MAX_AGE_DAYS = 90
# Number of extra estimators added during incremental warm-start
INCREMENTAL_EXTRA_ESTIMATORS = 50
# Days of recent data used for incremental training
INCREMENTAL_DATA_DAYS = 35


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


def _get_latest_model_dir(watchlist: str) -> Optional[Path]:
    """Return the path to the latest model directory for a watchlist, or None."""
    latest_pointer = MODEL_DIR / f"{watchlist}_latest"
    if latest_pointer.is_symlink() or latest_pointer.is_dir():
        # Resolve symlink or direct directory
        target = latest_pointer.resolve() if latest_pointer.is_symlink() else latest_pointer
        if target.exists() and (target / "model.txt").exists():
            return target
    return None


def save_retrain_model(
    model,
    feature_cols: List[str],
    config,
    metrics: Dict,
    watchlist: str,
    train_end_date: str,
    mode: str = "full",
) -> str:
    """Save trained model after retrain with metadata and update latest pointer.

    Args:
        model: Trained LGBMRegressor.
        feature_cols: Feature column names.
        config: ModelConfig used for training.
        metrics: Performance metrics dict (sharpe, IC, etc.).
        watchlist: Watchlist name.
        train_end_date: ISO date string of the last training date.
        mode: "full" or "incremental".

    Returns:
        Path to saved model directory.
    """
    from src.config.config import ModelConfig as CfgModelConfig

    model_id = "{}_{}".format(watchlist, datetime.now().strftime("%Y%m%d_%H%M%S"))

    # Build a trainer-compatible ModelConfig for save_model
    trainer_cfg = CfgModelConfig(
        target_col=config.target_col,
        test_size=config.test_size,
        random_state=config.random_state,
        params=config.params,
    )

    data_info = {
        "watchlist": watchlist,
        "train_end_date": train_end_date,
        "n_features": len(feature_cols),
        "retrain_mode": mode,
    }

    saved_path = save_model(
        model=model,
        feature_names=feature_cols,
        config=trainer_cfg,
        metrics=metrics,
        base_dir=str(MODEL_DIR),
        model_id=model_id,
        data_info=data_info,
    )

    # Update {watchlist}_latest symlink
    latest_link = MODEL_DIR / f"{watchlist}_latest"
    target_dir = Path(saved_path)
    # Remove old symlink/file if it exists
    if latest_link.is_symlink() or latest_link.exists():
        latest_link.unlink()
    latest_link.symlink_to(target_dir.resolve())

    print("Model saved: {} (mode={})".format(saved_path, mode))
    return saved_path


def run_incremental_retrain(
    watchlist: str,
    config,
    training_data: pd.DataFrame,
    feature_cols: List[str],
) -> Optional[Tuple]:
    """Attempt incremental (warm-start) retrain on recent data.

    Returns:
        Tuple of (model, metrics_dict, train_end_date) if incremental succeeded,
        or None to signal fallback to full retrain.
    """
    latest_dir = _get_latest_model_dir(watchlist)
    if latest_dir is None:
        print("No existing model for '{}' — falling back to full retrain.".format(watchlist))
        return None

    # Load metadata and check age
    metadata_file = latest_dir / "metadata.json"
    if not metadata_file.exists():
        print("No metadata found — falling back to full retrain.")
        return None

    with open(metadata_file) as f:
        metadata = json.load(f)

    train_end_str = metadata.get("data_info", {}).get("train_end_date", "")
    if not train_end_str:
        # Use training_date as fallback
        train_end_str = metadata.get("training_date", "")[:10]

    try:
        model_date = datetime.fromisoformat(train_end_str[:10])
    except (ValueError, TypeError):
        print("Cannot parse model date '{}' — falling back to full retrain.".format(train_end_str))
        return None

    age_days = (datetime.now() - model_date).days
    if age_days > INCREMENTAL_MAX_AGE_DAYS:
        print("Model is {} days old (>{} limit) — falling back to full retrain.".format(
            age_days, INCREMENTAL_MAX_AGE_DAYS))
        return None

    # Check feature compatibility
    saved_features = metadata.get("feature_names", [])
    if set(saved_features) != set(feature_cols):
        missing = set(feature_cols) - set(saved_features)
        extra = set(saved_features) - set(feature_cols)
        print("Feature mismatch (missing={}, extra={}) — falling back to full retrain.".format(
            len(missing), len(extra)))
        return None

    # Load existing model
    print("Loading model from {} (age={} days)...".format(latest_dir, age_days))
    try:
        model, model_meta = load_model(str(latest_dir))
    except Exception as e:
        print("Failed to load model: {} — falling back to full retrain.".format(e))
        return None

    # Prepare recent data for incremental training
    cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=INCREMENTAL_DATA_DAYS)
    if "date" in training_data.columns:
        recent_data = training_data[training_data["date"] >= cutoff_date]
    else:
        recent_data = training_data.tail(INCREMENTAL_DATA_DAYS * 50)  # rough estimate

    if len(recent_data) < 100:
        print("Only {} recent rows (need >=100) — falling back to full retrain.".format(
            len(recent_data)))
        return None

    X_new = recent_data[feature_cols]
    y_new = recent_data[config.model.target_col]

    print("Incremental training: {} rows, adding {} estimators...".format(
        len(X_new), INCREMENTAL_EXTRA_ESTIMATORS))

    # Warm-start: increase n_estimators and refit
    # LGBMRegressor supports init_model for warm-starting
    from lightgbm import LGBMRegressor
    import lightgbm as lgb

    # Build fresh model with same params + extra estimators
    fit_params = dict(config.model.params)
    early_stopping = fit_params.pop("early_stopping_rounds", None)
    original_n_estimators = fit_params.get("n_estimators", 200)
    fit_params["n_estimators"] = INCREMENTAL_EXTRA_ESTIMATORS

    new_model = LGBMRegressor(**fit_params)
    callbacks = [lgb.log_evaluation(period=-1)]

    # Use init_model to warm-start from the existing booster
    new_model.fit(
        X_new, y_new,
        init_model=model.booster_,
        callbacks=callbacks,
    )

    # Restore original n_estimators on the model object for metadata consistency
    new_model.n_estimators = original_n_estimators + INCREMENTAL_EXTRA_ESTIMATORS

    # Compute validation metrics on the new data
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    y_pred = new_model.predict(X_new)
    metrics = {
        "mse": float(mean_squared_error(y_new, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_new, y_pred))),
        "mae": float(mean_absolute_error(y_new, y_pred)),
        "n_train_incremental": len(X_new),
        "incremental_age_days": age_days,
    }

    # Determine train_end_date from the data
    if "date" in recent_data.columns:
        train_end_date = str(recent_data["date"].max().date())
    else:
        train_end_date = datetime.now().strftime("%Y-%m-%d")

    print("Incremental retrain complete: RMSE={:.6f}, {} rows".format(
        metrics["rmse"], len(X_new)))

    return new_model, metrics, train_end_date


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
    parser.add_argument("--full", action="store_true",
                        help="Force full walk-forward backtest (skip incremental)")
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

    # ── Incremental vs Full retrain decision ─────────────────────────────
    incremental_result = None
    if not args.full:
        incremental_result = run_incremental_retrain(
            watchlist=args.watchlist,
            config=config,
            training_data=training_data,
            feature_cols=feature_cols,
        )

    if incremental_result is not None:
        # ── Incremental path succeeded ───────────────────────────────────
        incr_model, incr_metrics, train_end_date = incremental_result
        elapsed = 0.0  # incremental is fast, no separate timing needed

        # Save the incrementally trained model
        save_retrain_model(
            model=incr_model,
            feature_cols=feature_cols,
            config=config.model,
            metrics=incr_metrics,
            watchlist=args.watchlist,
            train_end_date=train_end_date,
            mode="incremental",
        )

        print("\n" + "=" * 70)
        print("INCREMENTAL RETRAIN COMPLETE — {}".format(args.watchlist))
        print("  RMSE: {:.6f}".format(incr_metrics.get("rmse", 0)))
        print("  MAE:  {:.6f}".format(incr_metrics.get("mae", 0)))
        print("  Rows: {}".format(incr_metrics.get("n_train_incremental", 0)))
        print("  Model age: {} days".format(incr_metrics.get("incremental_age_days", 0)))
        print("  Train end: {}".format(train_end_date))
        print("=" * 70)
    else:
        # ── Full walk-forward backtest path ──────────────────────────────
        if not args.full:
            print("Proceeding with full walk-forward backtest...")

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

        # Save model from the last window of the full backtest
        # Extract the last trained model if available in window_results
        wr = results.window_results
        if wr and len(wr) > 0:
            last_window = wr[-1]
            last_model = last_window.get("model")
            if last_model is not None:
                # Determine train_end_date from last window
                train_end = last_window.get("train_end", "")
                if hasattr(train_end, "strftime"):
                    train_end_date = train_end.strftime("%Y-%m-%d")
                elif train_end:
                    train_end_date = str(train_end)[:10]
                else:
                    train_end_date = datetime.now().strftime("%Y-%m-%d")

                save_metrics = {
                    "sharpe_ratio": results.metrics.get("sharpe_ratio", 0),
                    "annualized_return": results.metrics.get("annualized_return", 0),
                    "max_drawdown": results.metrics.get("max_drawdown", 0),
                }
                # Add mean IC if available
                ics = [w["rank_ic"] for w in wr
                       if w.get("rank_ic") is not None and not np.isnan(w.get("rank_ic", float("nan")))]
                if ics:
                    save_metrics["mean_rank_ic"] = float(np.mean(ics))

                save_retrain_model(
                    model=last_model,
                    feature_cols=feature_cols,
                    config=config.model,
                    metrics=save_metrics,
                    watchlist=args.watchlist,
                    train_end_date=train_end_date,
                    mode="full",
                )


if __name__ == "__main__":
    main()
