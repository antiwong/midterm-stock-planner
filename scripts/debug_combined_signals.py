#!/usr/bin/env python3
"""
Debug script for Combined signal logic.
Run: python scripts/debug_combined_signals.py (or use venv)
"""

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
import src.backtest.trigger_backtest as tb
from src.backtest.trigger_backtest import TriggerConfig, generate_signals, run_trigger_backtest


def main():
    # Load price data
    prices_path = project_root / "data" / "prices.csv"
    if not prices_path.exists():
        print(f"ERROR: {prices_path} not found")
        return 1

    df = pd.read_csv(prices_path, parse_dates=["date"])
    df["ticker"] = df["ticker"].str.upper().str.strip()

    # Get first available ticker with enough data
    ticker_counts = df.groupby("ticker").size()
    ticker = ticker_counts[ticker_counts >= 300].index[0]
    price_df = df[df["ticker"] == ticker].copy().sort_values("date").reset_index(drop=True)
    price_df = price_df.head(500)  # ~2 years

    print(f"Testing ticker: {ticker}, rows: {len(price_df)}")
    print("=" * 60)

    # 1. Individual indicators
    for stype, label in [("rsi", "RSI"), ("macd", "MACD"), ("bollinger", "Bollinger")]:
        cfg = TriggerConfig(signal_type=stype)
        sig = generate_signals(price_df, cfg)
        buys = (sig["signal"] == 1).sum()
        sells = (sig["signal"] == -1).sum()
        print(f"{label} alone: {buys} buys, {sells} sells")

    # 2. Combined - RSI + MACD, "any"
    print("\n--- Combined: RSI + MACD, agreement='any' ---")
    cfg = TriggerConfig(signal_type="combined")
    cfg.combined_use_rsi = True
    cfg.combined_use_macd = True
    cfg.combined_use_bollinger = False
    cfg.combined_agreement = "any"

    sig = generate_signals(price_df, cfg)
    buys = (sig["signal"] == 1).sum()
    sells = (sig["signal"] == -1).sum()
    print(f"Signals: {buys} buys, {sells} sells")

    # Debug: show raw sig_rsi and sig_macd by recomputing
    df2 = price_df.copy().sort_values("date").reset_index(drop=True)
    close = df2["close"]

    # RSI
    df2["rsi"] = tb._compute_rsi(close, period=14)
    rsi_prev = df2["rsi"].shift(1)
    sig_rsi = np.zeros(len(df2), dtype=int)
    sig_rsi[(rsi_prev >= 30) & (df2["rsi"] < 30)] = 1
    sig_rsi[(rsi_prev <= 70) & (df2["rsi"] > 70)] = -1
    rsi_buys = (sig_rsi == 1).sum()
    rsi_sells = (sig_rsi == -1).sum()

    # MACD
    macd_df = tb._compute_macd(close, 12, 26, 9)
    df2["macd"] = macd_df["macd"].values
    df2["macd_signal"] = macd_df["macd_signal"].values
    macd_prev = df2["macd"].shift(1)
    sig_prev = df2["macd_signal"].shift(1)
    sig_macd = np.zeros(len(df2), dtype=int)
    sig_macd[(macd_prev <= sig_prev) & (df2["macd"] > df2["macd_signal"])] = 1
    sig_macd[(macd_prev >= sig_prev) & (df2["macd"] < df2["macd_signal"])] = -1
    macd_buys = (sig_macd == 1).sum()
    macd_sells = (sig_macd == -1).sum()

    print(f"  Raw RSI: {rsi_buys} buys, {rsi_sells} sells")
    print(f"  Raw MACD: {macd_buys} buys, {macd_sells} sells")

    # Check overlap: bars where both have a signal (any direction)
    rsi_any = (sig_rsi != 0)
    macd_any = (sig_macd != 0)
    both_fire = rsi_any & macd_any
    same_bar_both = both_fire.sum()
    # Among those, how many conflict (one buy, one sell)?
    conflict_count = ((sig_rsi == 1) & (sig_macd == -1) | (sig_rsi == -1) & (sig_macd == 1)).sum()
    print(f"  Bars where BOTH fire: {same_bar_both}, conflicts (1 buy + 1 sell): {conflict_count}")

    # Run backtest
    results = run_trigger_backtest(price_df, cfg)
    print(f"  Backtest trades: {len(results.trades)}")
    if len(results.trades) > 0:
        print(results.trades[["date", "type", "price"]].head(10).to_string())

    # 3. Test with yfinance-style data (simulate Live Data)
    print("\n--- Combined with yfinance data (AAPL, ~1yr) ---")
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        end = datetime.now().date()
        start = end - timedelta(days=365)
        data = yf.download("AAPL", start=start, end=end, auto_adjust=True, progress=False)
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            data = data.reset_index()
            data.columns = [c.lower() for c in data.columns]
            data["ticker"] = "AAPL"
            yf_df = data[["date", "ticker", "open", "high", "low", "close", "volume"]].copy()
            yf_results = run_trigger_backtest(yf_df, cfg)
            print(f"  Trades: {len(yf_results.trades)}")
        else:
            print("  (yfinance returned empty - skip)")
    except Exception as e:
        print(f"  (yfinance test skipped: {e})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
