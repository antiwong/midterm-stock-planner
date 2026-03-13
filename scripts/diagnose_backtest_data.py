#!/usr/bin/env python3
"""
Diagnose Backtest Data Issues
==============================
Checks why backtest might fail with "No predictions generated" error.

Usage:
    python scripts/diagnose_backtest_data.py
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import prepare_data_from_config
from src.config.config import load_config


def diagnose_backtest_data():
    """Diagnose potential backtest data issues."""
    
    print("=" * 80)
    print("BACKTEST DATA DIAGNOSTICS")
    print("=" * 80)
    print()
    
    # Load config
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    config = load_config(config_path if config_path.exists() else None)
    
    print("📊 Configuration:")
    print(f"   Training years: {config.backtest.train_years}")
    print(f"   Test years: {config.backtest.test_years}")
    print(f"   Step: {config.backtest.step_value} {config.backtest.step_unit}")
    print(f"   Rebalance frequency: {config.backtest.rebalance_freq}")
    print()
    
    # Load data
    print("📥 Loading data...")
    try:
        training_data, feature_cols, price_data, benchmark_data = prepare_data_from_config(
            config, for_training=True
        )
        print(f"   ✅ Price data: {len(price_data)} rows")
        print(f"   ✅ Benchmark data: {len(benchmark_data)} rows")
        print(f"   ✅ Training data: {len(training_data)} rows, {len(feature_cols)} features")
    except Exception as e:
        print(f"   ❌ Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    
    # Check date ranges
    print("📅 Date Ranges:")
    if 'date' in price_data.columns:
        price_data['date'] = pd.to_datetime(price_data['date'])
        price_min = price_data['date'].min()
        price_max = price_data['date'].max()
        price_span = (price_max - price_min).total_seconds() / (365.25 * 86400)
        print(f"   Price data: {price_min} to {price_max} ({price_span:.1f} years)")
    
    if 'date' in benchmark_data.columns:
        benchmark_data['date'] = pd.to_datetime(benchmark_data['date'])
        bench_min = benchmark_data['date'].min()
        bench_max = benchmark_data['date'].max()
        bench_span = (bench_max - bench_min).total_seconds() / (365.25 * 86400)
        print(f"   Benchmark data: {bench_min} to {bench_max} ({bench_span:.1f} years)")
    
    print()
    
    # Check if date range is sufficient
    train_years = config.backtest.train_years
    test_years = config.backtest.test_years
    min_required = train_years + test_years
    
    print(f"📏 Window Requirements:")
    print(f"   Training window: {train_years} years")
    print(f"   Test window: {test_years} years")
    print(f"   Minimum data needed: {min_required:.1f} years")
    
    if 'date' in price_data.columns:
        if price_span < min_required:
            print(f"   ⚠️  WARNING: Data span ({price_span:.1f} years) is less than minimum required ({min_required:.1f} years)")
            print(f"      This will cause all windows to be skipped!")
        else:
            print(f"   ✅ Data span ({price_span:.1f} years) is sufficient")
    
    print()
    
    # Training dataset already created above
    print("🔧 Training dataset:")
    if 'date' in training_data.columns:
            training_data['date'] = pd.to_datetime(training_data['date'])
            train_min = training_data['date'].min()
            train_max = training_data['date'].max()
            train_span = (train_max - train_min).total_seconds() / (365.25 * 86400)
            print(f"   Date range: {train_min} to {train_max} ({train_span:.1f} years)")
            
            if train_span < min_required:
                print(f"   ⚠️  WARNING: Training data span ({train_span:.1f} years) is insufficient!")
                print(f"      Need at least {min_required:.1f} years for walk-forward backtest")
    
    print()
    
    # Check for date filtering
    if config.backtest.start_date or config.backtest.end_date:
        print("📅 Date Filtering:")
        if config.backtest.start_date:
            print(f"   Start date filter: {config.backtest.start_date}")
        if config.backtest.end_date:
            print(f"   End date filter: {config.backtest.end_date}")
        print("   ⚠️  Date filters may reduce available data range")
    
    print()
    print("💡 Recommendations:")
    print()
    
    if 'date' in price_data.columns and price_span < min_required:
        print("   1. Reduce training window size:")
        print(f"      Current: {train_years} years → Try: {max(1.0, train_years * 0.7):.1f} years")
        print()
        print("   2. Reduce test window size:")
        print(f"      Current: {test_years} years → Try: {max(0.5, test_years * 0.7):.1f} years")
        print()
        print("   3. Download more historical data")
        print()
    
    print("   4. Check date filters in config.yaml:")
    print("      backtest.start_date: null  # Remove if set")
    print("      backtest.end_date: null    # Remove if set")
    print()


if __name__ == "__main__":
    diagnose_backtest_data()
