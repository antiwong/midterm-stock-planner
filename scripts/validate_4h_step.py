#!/usr/bin/env python3
"""
Validate Data Readiness for 4-Hour Step Backtest
================================================
Checks that price/benchmark data and config are correctly set up for
a 4-hour step walk-forward backtest with hourly data.

Usage:
    python scripts/validate_4h_step.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np


def infer_data_resolution(df: pd.DataFrame, date_col: str = "date") -> dict:
    """
    Infer whether data is daily or hourly from timestamps.
    
    Returns:
        dict with: resolution (str), has_time (bool), median_gap_hours (float),
                   sample_dates (list), n_unique_per_day (float or None)
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    dates = df[date_col].drop_duplicates().sort_values()
    
    if len(dates) < 2:
        return {
            "resolution": "unknown",
            "has_time": False,
            "median_gap_hours": None,
            "sample_dates": dates.tolist()[:5],
            "n_unique_per_day": None,
        }
    
    # Check if timestamps have time component (beyond midnight)
    has_time = (dates.dt.hour != 0).any() or (dates.dt.minute != 0).any()
    
    # Compute gaps between consecutive timestamps
    gaps = dates.diff().dropna()
    gap_hours = gaps.dt.total_seconds() / 3600
    
    median_gap = float(gap_hours.median())
    
    # For daily: typically ~24h (or 24*7 for week gaps). For hourly: ~1h
    if median_gap <= 2:
        resolution = "hourly"
    elif 20 <= median_gap <= 30:
        resolution = "daily"
    elif 160 <= median_gap <= 180:  # ~7 days
        resolution = "weekly"
    else:
        resolution = "unknown"
    
    # Count unique timestamps per calendar day (for hourly: ~6-7 per day)
    dates_series = pd.Series(dates)
    n_per_day = dates_series.dt.date.value_counts()
    n_unique_per_day = float(n_per_day.median()) if len(n_per_day) > 0 else None
    
    return {
        "resolution": resolution,
        "has_time": has_time,
        "median_gap_hours": median_gap,
        "sample_dates": [str(d) for d in dates.head(5).tolist()],
        "n_unique_per_day": n_unique_per_day,
    }


def validate_4h_step() -> bool:
    """Run all validation checks. Returns True if ready, False otherwise."""
    from src.config.config import load_config, bars_per_day_from_interval
    
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    config = load_config(config_path if config_path.exists() else None)
    
    price_path = Path(config.data.price_data_path)
    benchmark_path = Path(config.data.benchmark_data_path)
    
    print("=" * 70)
    print("4-HOUR STEP BACKTEST – DATA READINESS VALIDATION")
    print("=" * 70)
    print()
    
    all_ok = True
    
    # --- Config ---
    print("📋 CONFIG")
    print(f"   data.interval:        {config.data.interval}")
    print(f"   backtest.step_value:  {config.backtest.step_value}")
    print(f"   backtest.step_unit:   {config.backtest.step_unit}")
    print(f"   backtest.rebalance_freq: {config.backtest.rebalance_freq}")
    print()
    
    step_hours = config.backtest.step_value if config.backtest.step_unit.lower() in ("hours", "h") else None
    if step_hours != 4:
        print(f"   ⚠️  Step is {config.backtest.step_value} {config.backtest.step_unit}, not 4 hours.")
        print("      For 4h step, set: step_value: 4.0, step_unit: hours")
        if step_hours is None:
            all_ok = False
    else:
        print("   ✅ Step is 4 hours")
    
    # rebalance_freq for 4h step should be "4h" when using hourly data
    if config.data.interval == "1h" and config.backtest.rebalance_freq == "MS":
        print("   ⚠️  rebalance_freq is 'MS' (monthly) but data is hourly.")
        print("      For 4h rebalancing, set: rebalance_freq: 4h")
        all_ok = False
    elif config.data.interval == "1h" and config.backtest.rebalance_freq == "4h":
        print("   ✅ rebalance_freq '4h' matches hourly data")
    elif config.data.interval == "1d":
        print("   ℹ️  Daily data: rebalance_freq 'MS' is typical")
    print()
    
    # --- Price data ---
    print("📊 PRICE DATA")
    if not price_path.exists():
        print(f"   ❌ File not found: {price_path}")
        all_ok = False
    else:
        try:
            prices = pd.read_csv(price_path, nrows=5000)
            if "date" not in prices.columns:
                print("   ❌ No 'date' column")
                all_ok = False
            else:
                info = infer_data_resolution(prices, "date")
                print(f"   Inferred resolution: {info['resolution']}")
                print(f"   Has time component:  {info['has_time']}")
                print(f"   Median gap:          {info['median_gap_hours']:.1f} hours" if info['median_gap_hours'] else "   Median gap: N/A")
                print(f"   Sample timestamps:   {info['sample_dates'][:3]}")
                
                if config.data.interval == "1h" and info["resolution"] != "hourly":
                    print("   ❌ Config expects hourly (interval=1h) but data appears to be", info["resolution"])
                    all_ok = False
                elif config.data.interval == "1h" and info["resolution"] == "hourly":
                    print("   ✅ Hourly data matches config")
                elif config.data.interval == "1d" and info["resolution"] == "daily":
                    print("   ✅ Daily data matches config")
                elif config.data.interval == "1d" and info["resolution"] == "hourly":
                    print("   ⚠️  Data is hourly but config says daily. Set data.interval: 1h")
        except Exception as e:
            print(f"   ❌ Error reading: {e}")
            all_ok = False
    print()
    
    # --- Benchmark data ---
    print("📊 BENCHMARK DATA")
    if not benchmark_path.exists():
        print(f"   ❌ File not found: {benchmark_path}")
        all_ok = False
    else:
        try:
            bench = pd.read_csv(benchmark_path, nrows=5000)
            if "date" not in bench.columns:
                print("   ❌ No 'date' column")
                all_ok = False
            else:
                info = infer_data_resolution(bench, "date")
                print(f"   Inferred resolution: {info['resolution']}")
                print(f"   Has time component:  {info['has_time']}")
                print(f"   Sample timestamps:   {info['sample_dates'][:3]}")
                
                if config.data.interval == "1h" and info["resolution"] != "hourly":
                    print("   ❌ Config expects hourly but benchmark appears to be", info["resolution"])
                    all_ok = False
                elif config.data.interval == "1h" and info["resolution"] == "hourly":
                    print("   ✅ Hourly benchmark matches config")
        except Exception as e:
            print(f"   ❌ Error reading: {e}")
            all_ok = False
    print()
    
    # --- Resolution alignment ---
    if price_path.exists() and benchmark_path.exists():
        try:
            p = pd.read_csv(price_path, nrows=2000)
            b = pd.read_csv(benchmark_path, nrows=2000)
            p_info = infer_data_resolution(p, "date")
            b_info = infer_data_resolution(b, "date")
            if p_info["resolution"] != b_info["resolution"]:
                print("   ⚠️  Price and benchmark have different resolutions.")
                print(f"      Prices: {p_info['resolution']}, Benchmark: {b_info['resolution']}")
                all_ok = False
        except Exception:
            pass
    print()
    
    # --- Recommendations ---
    print("📌 RECOMMENDATIONS")
    if config.data.interval == "1h":
        # Check if data is actually hourly
        if price_path.exists():
            try:
                p = pd.read_csv(price_path, nrows=5000)
                info = infer_data_resolution(p, "date")
                if info["resolution"] != "hourly":
                    print("   1. Re-download with hourly interval:")
                    print("      python scripts/download_prices.py --watchlist <list> --interval 1h")
                    print("      python scripts/download_benchmark.py --interval 1h")
                    print("      (Note: yfinance limits 1h to ~730 days)")
                    print()
                    print("   2. Set rebalance_freq for 4h rebalancing in config.yaml:")
                    print("      rebalance_freq: 4h")
            except Exception:
                pass
    else:
        print("   For 4-hour step, set data.interval: 1h in config.yaml")
    print()
    
    # --- Backtest support ---
    print("🔧 BACKTEST SUPPORT")
    print("   _get_rebalance_dates() uses pd.date_range(..., freq=rebalance_freq)")
    print("   pandas supports: '4h', '1h', 'MS', 'D', etc.")
    print("   Set rebalance_freq: 4h for 4-hour rebalancing with hourly data.")
    print()
    
    print("=" * 70)
    if all_ok:
        print("✅ VALIDATION PASSED – Data appears ready for 4-hour step")
    else:
        print("❌ VALIDATION FAILED – Address issues above before running backtest")
    print("=" * 70)
    
    return all_ok


if __name__ == "__main__":
    ok = validate_4h_step()
    sys.exit(0 if ok else 1)
