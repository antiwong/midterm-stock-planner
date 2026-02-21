#!/usr/bin/env python3
"""
Bayesian Optimization for MACD/RSI Parameters
==============================================
Uses scikit-optimize (skopt) to find MACD/RSI parameters that maximize
Sharpe ratio (or return with max-drawdown penalty) on the trigger backtest.

Parameter space (tuned for 4h data):
  - MACD fast: 5–20
  - MACD slow: 20–60
  - MACD signal: 5–20
  - RSI length: 7–21
  - RSI overbought: 60–80
  - RSI oversold: 20–40
  - VIX (with --optimize-vix): vix_buy_max 18–45, vix_sell_min 22–50 (must be ≥ vix_buy_max + 2)
  - DXY (with --optimize-dxy): dxy_buy_max 98–112, dxy_sell_min 100–116 (must be ≥ dxy_buy_max + 2)
  - Minimum 3 trades required; if macro blocks all trades, optimize without macro first.

Usage:
    python scripts/optimize_macd_rsi_bayesian.py --tickers AAPL MSFT
    python scripts/optimize_macd_rsi_bayesian.py --tickers SLV AMD --n-calls 50
    python scripts/optimize_macd_rsi_bayesian.py --optimize-vix --tickers AMD --n-calls 60
    python scripts/optimize_macd_rsi_bayesian.py --optimize-dxy --tickers SLV --n-calls 60
    python scripts/optimize_macd_rsi_bayesian.py --metric sharpe_dd --save output/best_params.json

Note: Validate final parameters on a separate out-of-sample period not used in optimization.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from src.backtest.trigger_backtest import TriggerConfig, run_trigger_backtest
from src.data.loader import load_price_data
from src.config.config import load_config


def _fetch_vix(start: str, end: str) -> pd.DataFrame:
    """Fetch VIX from yfinance. Returns [date, close]."""
    try:
        import yfinance as yf
        data = yf.download("^VIX", start=start, end=end, auto_adjust=True, progress=False)
        if data.empty:
            return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data = data.reset_index()
        data.columns = [c.lower() for c in data.columns]
        if "close" not in data.columns:
            return pd.DataFrame()
        return data[["date", "close"]].copy()
    except Exception:
        return pd.DataFrame()


def _fetch_dxy(start: str, end: str) -> pd.DataFrame:
    """Fetch DXY (Dollar Index) from yfinance. Returns [date, close]."""
    try:
        import yfinance as yf
        data = yf.download("DX-Y.NYB", start=start, end=end, auto_adjust=True, progress=False)
        if data.empty:
            return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data = data.reset_index()
        data.columns = [c.lower() for c in data.columns]
        if "close" not in data.columns:
            return pd.DataFrame()
        return data[["date", "close"]].copy()
    except Exception:
        return pd.DataFrame()


def _objective(
    price_df: pd.DataFrame,
    tickers: list[str],
    metric: str,
    dd_penalty: float,
    vix_df: pd.DataFrame | None,
    optimize_vix: bool,
    dxy_df: pd.DataFrame | None,
    optimize_dxy: bool,
) -> callable:
    """Build objective function for Bayesian optimization."""

    def objective_fn_base(**kwargs):
        macd_fast = kwargs["macd_fast"]
        macd_slow = kwargs["macd_slow"]
        macd_signal = kwargs["macd_signal"]
        rsi_len = kwargs["rsi_len"]
        rsi_hi = kwargs["rsi_hi"]
        rsi_lo = kwargs["rsi_lo"]
        vix_buy_max = kwargs.get("vix_buy_max")
        vix_sell_min = kwargs.get("vix_sell_min")
        dxy_buy_max = kwargs.get("dxy_buy_max")
        dxy_sell_min = kwargs.get("dxy_sell_min")
        if optimize_vix and vix_buy_max is not None and vix_sell_min is not None:
            if vix_sell_min <= vix_buy_max or (vix_sell_min - vix_buy_max) < 2:
                return 1e6  # invalid: reject
        if optimize_dxy and dxy_buy_max is not None and dxy_sell_min is not None:
            if dxy_sell_min <= dxy_buy_max or (dxy_sell_min - dxy_buy_max) < 2:
                return 1e6  # invalid: reject
        config = TriggerConfig(
            signal_type="combined",
            combined_use_rsi=True,
            combined_use_macd=True,
            combined_use_bollinger=False,
            macd_fast=int(macd_fast),
            macd_slow=int(macd_slow),
            macd_signal=int(macd_signal),
            rsi_period=int(rsi_len),
            rsi_overbought=float(rsi_hi),
            rsi_oversold=float(rsi_lo),
        )
        if optimize_vix and vix_buy_max is not None and vix_sell_min is not None:
            config.macro_vix_enabled = True
            config.macro_vix_buy_max = float(vix_buy_max)
            config.macro_vix_sell_min = float(vix_sell_min)
        if optimize_dxy and dxy_buy_max is not None and dxy_sell_min is not None:
            config.macro_dxy_enabled = True
            config.macro_dxy_buy_max = float(dxy_buy_max)
            config.macro_dxy_sell_min = float(dxy_sell_min)
        scores = []
        run_kwargs = {}
        if optimize_vix and vix_df is not None and len(vix_df) > 0:
            run_kwargs["macro_vix_df"] = vix_df
        if optimize_dxy and dxy_df is not None and len(dxy_df) > 0:
            run_kwargs["macro_dxy_df"] = dxy_df
        for ticker in tickers:
            sub = price_df[price_df["ticker"] == ticker].copy()
            if len(sub) < 100:
                continue
            try:
                res = run_trigger_backtest(sub, config, **run_kwargs)
                m = res.metrics
                sharpe = m.get("sharpe_ratio", 0.0) or 0.0
                total_ret = m.get("total_return", 0.0) or 0.0
                max_dd = m.get("max_drawdown", 0.0) or 0.0
                num_trades = m.get("num_trades", 0) or 0
                if num_trades < 3:
                    scores.append(-1e6)  # reject: need minimum trades for valid strategy
                    continue
                if metric == "sharpe":
                    score = sharpe
                elif metric == "return":
                    score = total_ret
                elif metric == "sharpe_dd":
                    score = sharpe + dd_penalty * max_dd  # max_dd is negative
                else:
                    score = sharpe
                scores.append(score)
            except Exception:
                scores.append(-np.inf)
        if not scores:
            return 1e6  # bad (minimize)
        avg_score = np.mean(scores)
        return -avg_score  # minimize negative = maximize

    return objective_fn_base


def main():
    parser = argparse.ArgumentParser(
        description="Bayesian optimization for MACD/RSI parameters"
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=["AAPL", "MSFT"],
        help="Tickers to optimize on (default: AAPL MSFT)",
    )
    parser.add_argument(
        "--price-path",
        default=None,
        help="Path to price CSV (default: from config)",
    )
    parser.add_argument(
        "--n-calls",
        type=int,
        default=40,
        help="Number of BO evaluations (default: 40)",
    )
    parser.add_argument(
        "--n-initial",
        type=int,
        default=8,
        help="Random initial points before BO (default: 8)",
    )
    parser.add_argument(
        "--metric",
        choices=["sharpe", "return", "sharpe_dd"],
        default="sharpe",
        help="Objective: sharpe, return, or sharpe_dd (Sharpe + DD penalty)",
    )
    parser.add_argument(
        "--dd-penalty",
        type=float,
        default=0.5,
        help="Penalty weight for max drawdown when metric=sharpe_dd (default: 0.5)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--save",
        type=str,
        default="output/best_params.json",
        help="Save best params to JSON file (default: output/best_params.json)",
    )
    parser.add_argument(
        "--optimize-vix",
        action="store_true",
        help="Include VIX thresholds (vix_buy_max, vix_sell_min) in optimization",
    )
    parser.add_argument(
        "--optimize-dxy",
        action="store_true",
        help="Include DXY (USD) thresholds (dxy_buy_max, dxy_sell_min) in optimization",
    )
    args = parser.parse_args()

    try:
        from skopt import gp_minimize
        from skopt.space import Integer
        from skopt.utils import use_named_args
    except ImportError:
        print("scikit-optimize required. Run: pip install scikit-optimize")
        sys.exit(1)

    config = load_config(Path(__file__).parent.parent / "config" / "config.yaml")
    price_path = args.price_path or config.data.price_data_path
    price_path = Path(price_path)
    if not price_path.exists():
        print(f"Price file not found: {price_path}")
        sys.exit(1)

    print("Loading price data...")
    price_df = load_price_data(price_path)
    price_df["date"] = pd.to_datetime(price_df["date"])

    available = price_df["ticker"].unique().tolist()
    tickers = [t for t in args.tickers if t in available]
    if not tickers:
        print(f"No data for {args.tickers}. Available: {available[:20]}...")
        sys.exit(1)
    print(f"Optimizing on: {tickers}")

    date_min = price_df["date"].min()
    date_max = price_df["date"].max()
    start_str = str(date_min.date()) if hasattr(date_min, "date") else str(date_min)[:10]
    end_str = str(date_max.date()) if hasattr(date_max, "date") else str(date_max)[:10]

    # Fetch VIX when optimizing VIX params
    vix_df = pd.DataFrame()
    if args.optimize_vix:
        print("Fetching VIX data for optimization...")
        vix_df = _fetch_vix(start_str, end_str)
        if vix_df.empty:
            print("Warning: VIX data unavailable. Proceeding without VIX optimization.")
            args.optimize_vix = False
        else:
            print(f"  VIX: {len(vix_df)} days")

    # Fetch DXY when optimizing DXY params
    dxy_df = pd.DataFrame()
    if args.optimize_dxy:
        print("Fetching DXY (Dollar Index) data for optimization...")
        dxy_df = _fetch_dxy(start_str, end_str)
        if dxy_df.empty:
            print("Warning: DXY data unavailable. Proceeding without DXY optimization.")
            args.optimize_dxy = False
        else:
            print(f"  DXY: {len(dxy_df)} days")

    space = [
        Integer(5, 20, name="macd_fast"),
        Integer(20, 60, name="macd_slow"),
        Integer(5, 20, name="macd_signal"),
        Integer(7, 21, name="rsi_len"),
        Integer(60, 80, name="rsi_hi"),
        Integer(20, 40, name="rsi_lo"),
    ]
    if args.optimize_vix:
        space.extend([
            Integer(18, 45, name="vix_buy_max"),
            Integer(22, 50, name="vix_sell_min"),
        ])
    if args.optimize_dxy:
        space.extend([
            Integer(98, 112, name="dxy_buy_max"),
            Integer(100, 116, name="dxy_sell_min"),
        ])

    obj_fn_base = _objective(
        price_df, tickers, args.metric, args.dd_penalty,
        vix_df=vix_df if not vix_df.empty else None,
        optimize_vix=args.optimize_vix,
        dxy_df=dxy_df if not dxy_df.empty else None,
        optimize_dxy=args.optimize_dxy,
    )

    @use_named_args(space)
    def objective_bo(**kwargs):
        return obj_fn_base(**kwargs)

    n_calls = args.n_calls
    if args.optimize_vix or args.optimize_dxy:
        n_calls = max(n_calls, 55)  # more calls for larger search space
    macro_flags = []
    if args.optimize_vix:
        macro_flags.append("VIX")
    if args.optimize_dxy:
        macro_flags.append("DXY")
    macro_str = f" | {', '.join(macro_flags)}: enabled" if macro_flags else ""
    print(f"\nRunning Bayesian optimization ({n_calls} calls, {args.n_initial} random warmup)...")
    print(f"Metric: {args.metric}{macro_str}\n")

    res = gp_minimize(
        objective_bo,
        space,
        n_calls=n_calls,
        n_initial_points=args.n_initial,
        acq_func="EI",
        random_state=args.seed,
        verbose=True,
    )

    best_params = dict(zip([d.name for d in space], res.x))
    best_score = -res.fun

    print("\n" + "=" * 60)
    print("BEST PARAMETERS")
    print("=" * 60)
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    print(f"\nBest {args.metric}: {best_score:.4f}")
    print("=" * 60)

    # Build config for final run
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
    run_kwargs = {}
    if args.optimize_vix and "vix_buy_max" in best_params:
        cfg.macro_vix_enabled = True
        cfg.macro_vix_buy_max = float(best_params["vix_buy_max"])
        cfg.macro_vix_sell_min = float(best_params["vix_sell_min"])
        if not vix_df.empty:
            run_kwargs["macro_vix_df"] = vix_df
    if args.optimize_dxy and "dxy_buy_max" in best_params:
        cfg.macro_dxy_enabled = True
        cfg.macro_dxy_buy_max = float(best_params["dxy_buy_max"])
        cfg.macro_dxy_sell_min = float(best_params["dxy_sell_min"])
        if not dxy_df.empty:
            run_kwargs["macro_dxy_df"] = dxy_df
    print("\nPer-ticker metrics with best params:")
    for ticker in tickers:
        sub = price_df[price_df["ticker"] == ticker]
        if len(sub) < 100:
            continue
        r = run_trigger_backtest(sub, cfg, **run_kwargs)
        m = r.metrics
        print(f"  {ticker}: Sharpe={m.get('sharpe_ratio', 0):.3f}, "
              f"Return={m.get('total_return', 0)*100:.2f}%, "
              f"MaxDD={m.get('max_drawdown', 0)*100:.2f}%, "
              f"Trades={m.get('num_trades', 0)}")

    if args.save and args.save != "none":
        def _to_serializable(v):
            return int(v) if isinstance(v, (np.integer, np.int64)) else float(v) if isinstance(v, np.floating) else v
        canonical = {
            "macd_fast": _to_serializable(best_params["macd_fast"]),
            "macd_slow": _to_serializable(best_params["macd_slow"]),
            "macd_signal": _to_serializable(best_params["macd_signal"]),
            "rsi_period": _to_serializable(best_params["rsi_len"]),
            "rsi_overbought": _to_serializable(best_params["rsi_hi"]),
            "rsi_oversold": _to_serializable(best_params["rsi_lo"]),
        }
        if args.optimize_vix and "vix_buy_max" in best_params:
            canonical["macro_vix_enabled"] = True
            canonical["vix_buy_max"] = _to_serializable(best_params["vix_buy_max"])
            canonical["vix_sell_min"] = _to_serializable(best_params["vix_sell_min"])
        if args.optimize_dxy and "dxy_buy_max" in best_params:
            canonical["macro_dxy_enabled"] = True
            canonical["dxy_buy_max"] = _to_serializable(best_params["dxy_buy_max"])
            canonical["dxy_sell_min"] = _to_serializable(best_params["dxy_sell_min"])
        out = {
            "best_params": canonical,
            "best_score": float(best_score),
            "metric": args.metric,
            "tickers": tickers,
            "optimize_vix": args.optimize_vix,
            "optimize_dxy": args.optimize_dxy,
        }
        Path(args.save).parent.mkdir(parents=True, exist_ok=True)
        with open(args.save, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\nSaved to {args.save}")


if __name__ == "__main__":
    main()
