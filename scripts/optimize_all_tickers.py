#!/usr/bin/env python3
"""
Batch Bayesian Optimization for all tech_giants tickers.
=========================================================
Runs per-ticker optimization using validated feature set (MACD, Bollinger, ADX).
Saves per-ticker params to output/best_params_{TICKER}.json and config/tickers/{TICKER}.yaml.

Usage:
    python scripts/optimize_all_tickers.py
    python scripts/optimize_all_tickers.py --n-calls 50 --metric sharpe_dd
    python scripts/optimize_all_tickers.py --tickers AAPL MSFT NVDA
    python scripts/optimize_all_tickers.py --parallel 4
"""

import argparse
import json
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import yaml

from src.backtest.trigger_backtest import TriggerConfig, run_trigger_backtest
from src.data.loader import load_price_data
from src.config.config import load_config
from src.regression.database import RegressionDatabase


TECH_GIANTS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NVDA", "TSLA", "AMD", "INTC", "ORCL",
    "CRM", "ADBE", "NFLX",
]


def optimize_single_ticker(
    ticker: str,
    price_df: pd.DataFrame,
    n_calls: int,
    n_initial: int,
    metric: str,
    dd_penalty: float,
    seed: int,
) -> dict:
    """Run Bayesian optimization for a single ticker. Returns result dict."""
    from skopt import gp_minimize
    from skopt.space import Integer
    from skopt.utils import use_named_args

    sub = price_df[price_df["ticker"] == ticker].copy()
    if len(sub) < 100:
        return {"ticker": ticker, "error": f"Insufficient data ({len(sub)} rows)"}

    space = [
        Integer(5, 20, name="macd_fast"),
        Integer(20, 60, name="macd_slow"),
        Integer(5, 20, name="macd_signal"),
        Integer(7, 21, name="rsi_len"),
        Integer(60, 80, name="rsi_hi"),
        Integer(20, 40, name="rsi_lo"),
    ]

    def objective_fn(**kwargs):
        config = TriggerConfig(
            signal_type="combined",
            combined_use_rsi=True,
            combined_use_macd=True,
            combined_use_bollinger=False,
            macd_fast=int(kwargs["macd_fast"]),
            macd_slow=int(kwargs["macd_slow"]),
            macd_signal=int(kwargs["macd_signal"]),
            rsi_period=int(kwargs["rsi_len"]),
            rsi_overbought=float(kwargs["rsi_hi"]),
            rsi_oversold=float(kwargs["rsi_lo"]),
        )
        try:
            res = run_trigger_backtest(sub, config)
            m = res.metrics
            sharpe = m.get("sharpe_ratio", 0.0) or 0.0
            total_ret = m.get("total_return", 0.0) or 0.0
            max_dd = m.get("max_drawdown", 0.0) or 0.0
            num_trades = m.get("num_trades", 0) or 0
            if num_trades < 3:
                return 1e6
            if metric == "sharpe":
                score = sharpe
            elif metric == "return":
                score = total_ret
            elif metric == "sharpe_dd":
                score = sharpe + dd_penalty * max_dd
            else:
                score = sharpe
            return -score
        except Exception:
            return 1e6

    @use_named_args(space)
    def objective_bo(**kwargs):
        return objective_fn(**kwargs)

    t_start = time.time()
    res = gp_minimize(
        objective_bo,
        space,
        n_calls=n_calls,
        n_initial_points=n_initial,
        acq_func="EI",
        random_state=seed,
        verbose=False,
    )
    duration = time.time() - t_start

    best_params = dict(zip([d.name for d in space], res.x))
    best_score = -res.fun

    # Final evaluation with best params
    cfg = TriggerConfig(
        signal_type="combined",
        combined_use_rsi=True,
        combined_use_macd=True,
        combined_use_bollinger=False,
        macd_fast=int(best_params["macd_fast"]),
        macd_slow=int(best_params["macd_slow"]),
        macd_signal=int(best_params["macd_signal"]),
        rsi_period=int(best_params["rsi_len"]),
        rsi_overbought=float(best_params["rsi_hi"]),
        rsi_oversold=float(best_params["rsi_lo"]),
    )
    final_res = run_trigger_backtest(sub, cfg)
    final_m = final_res.metrics

    return {
        "ticker": ticker,
        "best_params": {k: int(v) for k, v in best_params.items()},
        "best_score": float(best_score),
        "sharpe_ratio": final_m.get("sharpe_ratio", 0.0),
        "total_return": final_m.get("total_return", 0.0),
        "max_drawdown": final_m.get("max_drawdown", 0.0),
        "num_trades": final_m.get("num_trades", 0),
        "duration_seconds": duration,
        "all_scores": [-float(v) for v in res.func_vals],
    }


def save_ticker_yaml(ticker: str, result: dict, config_dir: Path):
    """Write per-ticker YAML config with optimized params."""
    params = result["best_params"]
    existing_path = config_dir / f"{ticker}.yaml"

    # If existing config, preserve non-trigger fields
    existing = {}
    if existing_path.exists():
        with open(existing_path) as f:
            existing = yaml.safe_load(f) or {}

    config = {
        "ticker": ticker,
        "trigger": {
            "rsi_period": params["rsi_len"],
            "rsi_oversold": params["rsi_lo"],
            "rsi_overbought": params["rsi_hi"],
            "macd_fast": params["macd_fast"],
            "macd_slow": params["macd_slow"],
            "macd_signal": params["macd_signal"],
            "bb_period": existing.get("trigger", {}).get("bb_period", 20),
            "bb_std": existing.get("trigger", {}).get("bb_std", 2.0),
        },
    }

    # Preserve macro_factors if they exist
    if "macro_factors" in existing.get("trigger", {}):
        config["trigger"]["macro_factors"] = existing["trigger"]["macro_factors"]

    # Preserve other sections from existing config
    for key in ["horizon_days", "return_periods", "volatility_windows", "volume_window", "backtest"]:
        if key in existing:
            config[key] = existing[key]

    # Add default sections if new ticker
    if "horizon_days" not in config:
        config["horizon_days"] = 63
        config["backtest"] = {
            "train_years": 1.0,
            "test_years": 0.25,
            "step_unit": "days",
            "rebalance_freq": "4h",
        }

    header = (
        f"# Per-ticker configuration for {ticker}\n"
        f"# Optimized via Bayesian optimization on {time.strftime('%Y-%m-%d')}\n"
        f"# Sharpe={result['sharpe_ratio']:.3f}, Return={result['total_return']*100:.1f}%, "
        f"MaxDD={result['max_drawdown']*100:.1f}%, Trades={result['num_trades']}\n\n"
    )

    config_dir.mkdir(parents=True, exist_ok=True)
    with open(existing_path, "w") as f:
        f.write(header)
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def save_params_json(ticker: str, result: dict, output_dir: Path, metric: str):
    """Save best params JSON for a ticker."""
    params = result["best_params"]
    out = {
        "best_params": {
            "macd_fast": params["macd_fast"],
            "macd_slow": params["macd_slow"],
            "macd_signal": params["macd_signal"],
            "rsi_period": params["rsi_len"],
            "rsi_overbought": params["rsi_hi"],
            "rsi_oversold": params["rsi_lo"],
        },
        "best_score": result["best_score"],
        "metric": metric,
        "tickers": [ticker],
        "sharpe_ratio": result["sharpe_ratio"],
        "total_return": result["total_return"],
        "max_drawdown": result["max_drawdown"],
        "num_trades": result["num_trades"],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"best_params_{ticker}.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Batch Bayesian optimization for all tech_giants tickers"
    )
    parser.add_argument(
        "--tickers", nargs="+", default=None,
        help="Override ticker list (default: all tech_giants)",
    )
    parser.add_argument("--n-calls", type=int, default=40, help="BO evaluations per ticker (default: 40)")
    parser.add_argument("--n-initial", type=int, default=8, help="Random warmup points (default: 8)")
    parser.add_argument("--metric", choices=["sharpe", "return", "sharpe_dd"], default="sharpe")
    parser.add_argument("--dd-penalty", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--parallel", type=int, default=1, help="Parallel workers (default: 1, sequential)")
    parser.add_argument("--no-db", action="store_true", help="Skip database logging")
    parser.add_argument("--no-yaml", action="store_true", help="Skip writing ticker YAML configs")
    args = parser.parse_args()

    tickers = args.tickers or TECH_GIANTS

    config = load_config(Path(__file__).parent.parent / "config" / "config.yaml")
    price_path = Path(config.data.price_data_path)
    if not price_path.exists():
        print(f"Price file not found: {price_path}")
        sys.exit(1)

    print("Loading price data...")
    price_df = load_price_data(price_path)
    price_df["date"] = pd.to_datetime(price_df["date"])

    available = set(price_df["ticker"].unique())
    tickers = [t for t in tickers if t in available]
    missing = [t for t in (args.tickers or TECH_GIANTS) if t not in available]
    if missing:
        print(f"Warning: No data for {missing}")
    if not tickers:
        print("No valid tickers. Exiting.")
        sys.exit(1)

    print(f"\nOptimizing {len(tickers)} tickers: {', '.join(tickers)}")
    print(f"Settings: n_calls={args.n_calls}, metric={args.metric}, seed={args.seed}")
    print(f"Parallel workers: {args.parallel}\n")

    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config" / "tickers"
    output_dir = project_root / "output"

    results = {}
    t_total = time.time()

    if args.parallel > 1:
        with ProcessPoolExecutor(max_workers=args.parallel) as executor:
            futures = {}
            for ticker in tickers:
                f = executor.submit(
                    optimize_single_ticker,
                    ticker, price_df, args.n_calls, args.n_initial,
                    args.metric, args.dd_penalty, args.seed,
                )
                futures[f] = ticker

            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    result = future.result()
                    results[ticker] = result
                    if "error" in result:
                        print(f"  SKIP {ticker}: {result['error']}")
                    else:
                        print(f"  DONE {ticker}: Sharpe={result['sharpe_ratio']:.3f}, "
                              f"Return={result['total_return']*100:.1f}%, "
                              f"MaxDD={result['max_drawdown']*100:.1f}%, "
                              f"MACD({result['best_params']['macd_fast']}/"
                              f"{result['best_params']['macd_slow']}/"
                              f"{result['best_params']['macd_signal']}), "
                              f"RSI({result['best_params']['rsi_len']}/"
                              f"{result['best_params']['rsi_hi']}/"
                              f"{result['best_params']['rsi_lo']}) "
                              f"[{result['duration_seconds']:.0f}s]")
                except Exception as e:
                    print(f"  FAIL {ticker}: {e}")
                    results[ticker] = {"ticker": ticker, "error": str(e)}
    else:
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{len(tickers)}] Optimizing {ticker}...")
            result = optimize_single_ticker(
                ticker, price_df, args.n_calls, args.n_initial,
                args.metric, args.dd_penalty, args.seed,
            )
            results[ticker] = result
            if "error" in result:
                print(f"  SKIP {ticker}: {result['error']}")
            else:
                print(f"  DONE {ticker}: Sharpe={result['sharpe_ratio']:.3f}, "
                      f"Return={result['total_return']*100:.1f}%, "
                      f"MaxDD={result['max_drawdown']*100:.1f}%, "
                      f"MACD({result['best_params']['macd_fast']}/"
                      f"{result['best_params']['macd_slow']}/"
                      f"{result['best_params']['macd_signal']}), "
                      f"RSI({result['best_params']['rsi_len']}/"
                      f"{result['best_params']['rsi_hi']}/"
                      f"{result['best_params']['rsi_lo']}) "
                      f"[{result['duration_seconds']:.0f}s]")

    total_duration = time.time() - t_total

    # Save results
    db = RegressionDatabase()
    successful = {t: r for t, r in results.items() if "error" not in r}

    for ticker, result in successful.items():
        # Save JSON
        save_params_json(ticker, result, output_dir, args.metric)

        # Save YAML config
        if not args.no_yaml:
            save_ticker_yaml(ticker, result, config_dir)

        # Log to DB
        if not args.no_db:
            run_id = str(uuid.uuid4())
            db.log_optimization_run(
                run_id=run_id,
                ticker=ticker,
                metric=args.metric,
                best_score=result["best_score"],
                n_calls=args.n_calls,
                n_initial=args.n_initial,
                seed=args.seed,
                optimize_vix=False,
                optimize_dxy=False,
                best_params={k: int(v) for k, v in result["best_params"].items()},
                all_scores=result["all_scores"],
                sharpe_ratio=result["sharpe_ratio"],
                total_return=result["total_return"],
                max_drawdown=result["max_drawdown"],
                num_trades=result["num_trades"],
                duration_seconds=result["duration_seconds"],
                notes=f"Batch optimization: metric={args.metric}, n_calls={args.n_calls}",
            )

    # Summary table
    print("\n" + "=" * 90)
    print("OPTIMIZATION SUMMARY")
    print("=" * 90)
    print(f"{'Ticker':>6}  {'Sharpe':>7}  {'Return':>8}  {'MaxDD':>8}  {'Trades':>6}  "
          f"{'MACD':>12}  {'RSI':>12}  {'Time':>6}")
    print("-" * 90)

    sorted_results = sorted(successful.items(), key=lambda x: x[1]["sharpe_ratio"], reverse=True)
    for ticker, r in sorted_results:
        p = r["best_params"]
        print(f"{ticker:>6}  {r['sharpe_ratio']:>7.3f}  {r['total_return']*100:>7.1f}%  "
              f"{r['max_drawdown']*100:>7.1f}%  {r['num_trades']:>6}  "
              f"{p['macd_fast']:>2}/{p['macd_slow']:>2}/{p['macd_signal']:>2}    "
              f"{p['rsi_len']:>2}/{p['rsi_hi']:>2}/{p['rsi_lo']:>2}    "
              f"{r['duration_seconds']:>5.0f}s")

    print("-" * 90)
    sharpes = [r["sharpe_ratio"] for r in successful.values()]
    returns = [r["total_return"] for r in successful.values()]
    print(f"{'AVG':>6}  {np.mean(sharpes):>7.3f}  {np.mean(returns)*100:>7.1f}%")
    print(f"\nTotal: {len(successful)}/{len(tickers)} tickers optimized in {total_duration:.0f}s")
    if not args.no_yaml:
        print(f"Configs saved to: {config_dir}/")
    print(f"Params saved to: {output_dir}/best_params_*.json")

    # Save combined summary
    summary = {
        "run_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metric": args.metric,
        "n_calls": args.n_calls,
        "total_duration_seconds": total_duration,
        "results": {t: {
            "sharpe_ratio": r["sharpe_ratio"],
            "total_return": r["total_return"],
            "max_drawdown": r["max_drawdown"],
            "num_trades": r["num_trades"],
            "best_params": r["best_params"],
        } for t, r in successful.items()},
    }
    summary_path = output_dir / "batch_optimization_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
