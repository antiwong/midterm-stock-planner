#!/usr/bin/env python3
"""
Run trigger backtests with live data from yfinance.
===================================================

Usage:
    python scripts/run_trigger_backtest_live.py
    python scripts/run_trigger_backtest_live.py --tickers AMD SLV
    python scripts/run_trigger_backtest_live.py --tickers AMD SLV --days 365

Fetches real-time price data from yfinance and runs the trigger backtest
(RSI + MACD combined) for each ticker. Uses per-ticker YAML from config/tickers/{TICKER}.yaml
if present; otherwise falls back to output/best_params.json or defaults.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from src.backtest.trigger_backtest import TriggerConfig, run_trigger_backtest
from src.config.config import load_ticker_config


def _fetch_macro_price_df(
    gold_ticker: str, start: str, end: str
) -> pd.DataFrame:
    """Fetch gold (or other macro) price data for GSR. Returns [date, close]."""
    df = fetch_yfinance_data(gold_ticker, start, end)
    if df.empty or "close" not in df.columns:
        return pd.DataFrame()
    return df[["date", "close"]].copy()


def _fetch_macro_series(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Fetch macro index (DXY, VIX) from yfinance. Returns [date, close]."""
    df = fetch_yfinance_data(ticker, start, end)
    if df.empty or "close" not in df.columns:
        return pd.DataFrame()
    return df[["date", "close"]].copy()


def fetch_yfinance_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Fetch OHLCV data from yfinance for a single ticker."""
    import yfinance as yf

    data = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data.reset_index()
    data.columns = [c.lower() for c in data.columns]
    data["ticker"] = ticker.upper()
    return data[["date", "ticker", "open", "high", "low", "close", "volume"]].copy()


def load_params(path: Path) -> Optional[dict]:
    """Load best_params from JSON if file exists."""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("best_params", {})
    except Exception:
        return None


def _build_trigger_config(
    ticker: str,
    signal_type: str,
    ticker_config: Optional[dict],
    fallback_params: Optional[dict],
) -> TriggerConfig:
    """Build TriggerConfig for a ticker: per-ticker YAML > fallback JSON > defaults."""
    cfg = TriggerConfig(signal_type=signal_type)
    if signal_type == "combined":
        cfg.combined_use_rsi = True
        cfg.combined_use_macd = True
        cfg.combined_use_bollinger = False

    # Priority 1: per-ticker YAML
    if ticker_config and "trigger" in ticker_config:
        t = ticker_config["trigger"]
        for key in ("rsi_period", "rsi_oversold", "rsi_overbought", "macd_fast", "macd_slow", "macd_signal", "bb_period", "bb_std"):
            if key in t:
                setattr(cfg, key, t[key])
        if "volume_trigger" in t:
            vt = t["volume_trigger"]
            for k in ("cmf_window", "cmf_buy_threshold", "cmf_sell_threshold"):
                if k in vt:
                    setattr(cfg, k, vt[k])
        if "combined_use_cmf" in t:
            cfg.combined_use_cmf = bool(t["combined_use_cmf"])
        if "macro_factors" in t:
            mf = t["macro_factors"]
            if mf.get("gsr_enabled"):
                cfg.macro_gsr_enabled = True
                cfg.macro_gsr_gold_ticker = str(mf.get("gold_ticker", cfg.macro_gsr_gold_ticker))
                cfg.macro_gsr_buy_threshold = float(mf.get("gsr_buy_threshold", cfg.macro_gsr_buy_threshold))
                cfg.macro_gsr_sell_threshold = float(mf.get("gsr_sell_threshold", cfg.macro_gsr_sell_threshold))
            if mf.get("dxy_enabled"):
                cfg.macro_dxy_enabled = True
                cfg.macro_dxy_buy_max = float(mf.get("dxy_buy_max", cfg.macro_dxy_buy_max))
                cfg.macro_dxy_sell_min = float(mf.get("dxy_sell_min", cfg.macro_dxy_sell_min))
            if mf.get("vix_enabled"):
                cfg.macro_vix_enabled = True
                cfg.macro_vix_buy_max = float(mf.get("vix_buy_max", cfg.macro_vix_buy_max))
                cfg.macro_vix_sell_min = float(mf.get("vix_sell_min", cfg.macro_vix_sell_min))
        return cfg

    # Priority 2: fallback JSON (best_params)
    if fallback_params:
        cfg.macd_fast = int(fallback_params.get("macd_fast", cfg.macd_fast))
        cfg.macd_slow = int(fallback_params.get("macd_slow", cfg.macd_slow))
        cfg.macd_signal = int(fallback_params.get("macd_signal", cfg.macd_signal))
        cfg.rsi_period = int(fallback_params.get("rsi_period", fallback_params.get("rsi_len", cfg.rsi_period)))
        cfg.rsi_overbought = float(fallback_params.get("rsi_overbought", fallback_params.get("rsi_hi", cfg.rsi_overbought)))
        cfg.rsi_oversold = float(fallback_params.get("rsi_oversold", fallback_params.get("rsi_lo", cfg.rsi_oversold)))
        if "bb_period" in fallback_params:
            cfg.bb_period = int(fallback_params["bb_period"])
        if "bb_std" in fallback_params:
            cfg.bb_std = float(fallback_params["bb_std"])
        if fallback_params.get("macro_vix_enabled") and "vix_buy_max" in fallback_params:
            cfg.macro_vix_enabled = True
            cfg.macro_vix_buy_max = float(fallback_params.get("vix_buy_max", cfg.macro_vix_buy_max))
            cfg.macro_vix_sell_min = float(fallback_params.get("vix_sell_min", cfg.macro_vix_sell_min))
        if fallback_params.get("macro_dxy_enabled") and "dxy_buy_max" in fallback_params:
            cfg.macro_dxy_enabled = True
            cfg.macro_dxy_buy_max = float(fallback_params.get("dxy_buy_max", cfg.macro_dxy_buy_max))
            cfg.macro_dxy_sell_min = float(fallback_params.get("dxy_sell_min", cfg.macro_dxy_sell_min))

    return cfg


def main():
    parser = argparse.ArgumentParser(
        description="Run trigger backtests with live yfinance data"
    )
    parser.add_argument(
        "--tickers", "-t",
        nargs="+",
        default=["AMD", "SLV"],
        help="Ticker symbols (default: AMD SLV)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days of history (default: 365)",
    )
    parser.add_argument(
        "--params",
        default="output/best_params.json",
        help="Path to best_params.json for optimized params (default: output/best_params.json)",
    )
    parser.add_argument(
        "--signal",
        choices=["rsi", "macd", "bollinger", "cmf", "combined"],
        default="combined",
        help="Signal type (default: combined)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    params_path = project_root / args.params
    fallback_params = load_params(params_path)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=args.days)
    start_str = str(start_date)
    end_str = str(end_date + timedelta(days=1))

    print(f"\nFetching live data: {start_str} to {end_str} ({args.days} days)")
    print("=" * 60)

    for ticker in args.tickers:
        print(f"\n--- {ticker} ---")
        ticker_config = load_ticker_config(ticker)
        cfg = _build_trigger_config(ticker, args.signal, ticker_config, fallback_params)
        if ticker_config:
            print(f"  Config: config/tickers/{ticker.upper()}.yaml")
        elif fallback_params:
            print(f"  Config: fallback from {params_path}")
        else:
            print(f"  Config: defaults")

        price_df = fetch_yfinance_data(ticker, start_str, end_str)
        if len(price_df) < 50:
            print(f"  Skipped: insufficient data ({len(price_df)} rows)")
            continue

        macro_price_df = _fetch_macro_price_df(cfg.macro_gsr_gold_ticker, start_str, end_str) if cfg.macro_gsr_enabled else None
        macro_dxy_df = _fetch_macro_series("DX-Y.NYB", start_str, end_str) if cfg.macro_dxy_enabled else None
        macro_vix_df = _fetch_macro_series("^VIX", start_str, end_str) if cfg.macro_vix_enabled else None
        if cfg.macro_gsr_enabled and (macro_price_df is None or macro_price_df.empty):
            print(f"  Warning: GSR enabled but no data for {cfg.macro_gsr_gold_ticker}; running without GSR filter")
        kwargs = {}
        if macro_price_df is not None and not macro_price_df.empty:
            kwargs["macro_price_df"] = macro_price_df
        if macro_dxy_df is not None and not macro_dxy_df.empty:
            kwargs["macro_dxy_df"] = macro_dxy_df
        if macro_vix_df is not None and not macro_vix_df.empty:
            kwargs["macro_vix_df"] = macro_vix_df

        try:
            results = run_trigger_backtest(price_df, cfg, **kwargs) if kwargs else run_trigger_backtest(price_df, cfg)
            m = results.metrics
            sharpe = m.get("sharpe_ratio", 0) or 0
            total_ret = m.get("total_return", 0) or 0
            max_dd = m.get("max_drawdown", 0) or 0
            n_trades = len(results.trades)

            print(f"  Sharpe:     {sharpe:.3f}")
            print(f"  Return:     {total_ret * 100:.2f}%")
            print(f"  Max DD:     {max_dd * 100:.2f}%")
            print(f"  Trades:     {n_trades}")
            if n_trades > 0:
                print(results.trades[["date", "type", "price"]].head(10).to_string(index=False))
                if n_trades > 10:
                    print(f"  ... and {n_trades - 10} more")
        except Exception as e:
            print(f"  Error: {e}")

    print("\n" + "=" * 60)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
