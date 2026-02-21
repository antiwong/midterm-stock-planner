#!/usr/bin/env python3
"""
Validate Macro Filter Influence on Trigger Backtest
====================================================
Compares backtest results with macro filters ON vs OFF to verify that
DXY and VIX actually influence trades (block signals when conditions are unfavorable).

Usage:
    python scripts/validate_macro_influence.py --ticker SLV
    python scripts/validate_macro_influence.py --ticker SLV --config config/tickers/SLV.yaml
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from src.backtest.trigger_backtest import TriggerConfig, run_trigger_backtest
from src.data.loader import load_price_data
from src.config.config import load_config, load_ticker_config


def _fetch_macro(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Fetch macro series from yfinance."""
    try:
        import yfinance as yf
        data = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
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


def _build_config_from_yaml(ticker: str) -> TriggerConfig:
    """Build TriggerConfig from per-ticker YAML."""
    cfg = TriggerConfig(
        signal_type="combined",
        combined_use_rsi=True,
        combined_use_macd=True,
        combined_use_bollinger=False,
    )
    tc = load_ticker_config(ticker)
    if tc and "trigger" in tc:
        t = tc["trigger"]
        for k in ("rsi_period", "rsi_oversold", "rsi_overbought", "macd_fast", "macd_slow", "macd_signal"):
            if k in t:
                setattr(cfg, k, t[k])
        if "macro_factors" in t:
            mf = t["macro_factors"]
            cfg.macro_gsr_enabled = bool(mf.get("gsr_enabled"))
            cfg.macro_gsr_gold_ticker = str(mf.get("gold_ticker", "GLD"))
            cfg.macro_gsr_buy_threshold = float(mf.get("gsr_buy_threshold", 90))
            cfg.macro_gsr_sell_threshold = float(mf.get("gsr_sell_threshold", 70))
            cfg.macro_dxy_enabled = bool(mf.get("dxy_enabled"))
            cfg.macro_dxy_buy_max = float(mf.get("dxy_buy_max", 102))
            cfg.macro_dxy_sell_min = float(mf.get("dxy_sell_min", 106))
            cfg.macro_vix_enabled = bool(mf.get("vix_enabled"))
            cfg.macro_vix_buy_max = float(mf.get("vix_buy_max", 25))
            cfg.macro_vix_sell_min = float(mf.get("vix_sell_min", 30))
    return cfg


def main():
    parser = argparse.ArgumentParser(description="Validate macro filter influence on trades")
    parser.add_argument("--ticker", default="SLV", help="Ticker to validate")
    parser.add_argument("--price-path", default=None, help="Path to price CSV")
    args = parser.parse_args()

    config = load_config(Path(__file__).parent.parent / "config" / "config.yaml")
    price_path = Path(args.price_path or config.data.price_data_path)
    if not price_path.exists():
        print(f"Price file not found: {price_path}")
        sys.exit(1)

    print("Loading price data...")
    price_df = load_price_data(price_path)
    price_df["date"] = pd.to_datetime(price_df["date"])
    sub = price_df[price_df["ticker"] == args.ticker].copy()
    if len(sub) < 100:
        print(f"Insufficient data for {args.ticker} ({len(sub)} rows)")
        sys.exit(1)

    date_min, date_max = sub["date"].min(), sub["date"].max()
    start_str = str(date_min.date()) if hasattr(date_min, "date") else str(date_min)[:10]
    end_str = str(date_max.date()) if hasattr(date_max, "date") else str(date_max)[:10]

    print(f"\n{args.ticker}: {len(sub)} days ({start_str} to {end_str})")

    # Build config from YAML (with macro enabled)
    cfg = _build_config_from_yaml(args.ticker)
    print(f"\nConfig from YAML:")
    print(f"  GSR: enabled={cfg.macro_gsr_enabled}")
    print(f"  DXY: enabled={cfg.macro_dxy_enabled}, buy_max={cfg.macro_dxy_buy_max}, sell_min={cfg.macro_dxy_sell_min}")
    print(f"  VIX: enabled={cfg.macro_vix_enabled}, buy_max={cfg.macro_vix_buy_max}, sell_min={cfg.macro_vix_sell_min}")

    # Fetch macro data
    macro_price_df = None
    if cfg.macro_gsr_enabled:
        macro_price_df = _fetch_macro("GLD", start_str, end_str)
        print(f"\n  GLD: {len(macro_price_df)} days" if not macro_price_df.empty else "  GLD: unavailable")
    macro_dxy_df = _fetch_macro("DX-Y.NYB", start_str, end_str) if cfg.macro_dxy_enabled else None
    macro_vix_df = _fetch_macro("^VIX", start_str, end_str) if cfg.macro_vix_enabled else None
    if macro_dxy_df is not None:
        print(f"  DXY: {len(macro_dxy_df)} days" if not macro_dxy_df.empty else "  DXY: unavailable")
    if macro_vix_df is not None:
        print(f"  VIX: {len(macro_vix_df)} days" if not macro_vix_df.empty else "  VIX: unavailable")

    # Run 1: Macro OFF
    cfg_off = TriggerConfig(
        signal_type=cfg.signal_type,
        combined_use_rsi=cfg.combined_use_rsi,
        combined_use_macd=cfg.combined_use_macd,
        combined_use_bollinger=cfg.combined_use_bollinger,
        rsi_period=cfg.rsi_period,
        rsi_oversold=cfg.rsi_oversold,
        rsi_overbought=cfg.rsi_overbought,
        macd_fast=cfg.macd_fast,
        macd_slow=cfg.macd_slow,
        macd_signal=cfg.macd_signal,
        macro_gsr_enabled=False,
        macro_dxy_enabled=False,
        macro_vix_enabled=False,
    )
    res_off = run_trigger_backtest(sub, cfg_off)
    n_trades_off = len(res_off.trades)
    m_off = res_off.metrics

    # Run 2: Macro ON (with YAML params)
    kwargs = {}
    if macro_price_df is not None and len(macro_price_df) > 0:
        kwargs["macro_price_df"] = macro_price_df
    if macro_dxy_df is not None and len(macro_dxy_df) > 0:
        kwargs["macro_dxy_df"] = macro_dxy_df
    if macro_vix_df is not None and len(macro_vix_df) > 0:
        kwargs["macro_vix_df"] = macro_vix_df

    res_on = run_trigger_backtest(sub, cfg, **kwargs)
    n_trades_on = len(res_on.trades)
    m_on = res_on.metrics

    # Count blocked signals
    signals_on = res_on.signals
    n_blocked_buy = 0
    n_blocked_sell = 0
    if "signal_raw" in signals_on.columns:
        blocked_buy = (signals_on["signal_raw"] == 1) & (signals_on["signal"] == 0)
        blocked_sell = (signals_on["signal_raw"] == -1) & (signals_on["signal"] == 0)
        n_blocked_buy = int(blocked_buy.sum())
        n_blocked_sell = int(blocked_sell.sum())

    # Report
    print("\n" + "=" * 60)
    print("VALIDATION: Macro Filter Influence")
    print("=" * 60)
    print(f"\n  Macro OFF: {n_trades_off} trades | Sharpe={m_off.get('sharpe_ratio', 0):.3f} | "
          f"Return={m_off.get('total_return', 0)*100:.2f}% | MaxDD={m_off.get('max_drawdown', 0)*100:.2f}%")
    print(f"  Macro ON:  {n_trades_on} trades | Sharpe={m_on.get('sharpe_ratio', 0):.3f} | "
          f"Return={m_on.get('total_return', 0)*100:.2f}% | MaxDD={m_on.get('max_drawdown', 0)*100:.2f}%")
    print(f"\n  Blocked by macro: {n_blocked_buy} BUY, {n_blocked_sell} SELL")
    print(f"  Trade difference: {n_trades_off - n_trades_on} fewer trades with macro ON")

    if n_blocked_buy > 0 or n_blocked_sell > 0:
        print("\n  ✓ Macro filters ARE influencing trades (signals were blocked)")
    elif n_trades_off != n_trades_on:
        print("\n  ✓ Macro filters ARE influencing trades (different trade count)")
    else:
        print("\n  ⚠ No blocked signals detected. Possible causes:")
        print("    - DXY/VIX conditions were favorable throughout the period")
        print("    - Date alignment issue (check macro data merge)")
        print("    - Try stricter thresholds to see blocking in action")

    print("=" * 60)
    return 0 if (n_blocked_buy > 0 or n_blocked_sell > 0 or n_trades_off != n_trades_on) else 1


if __name__ == "__main__":
    sys.exit(main())
