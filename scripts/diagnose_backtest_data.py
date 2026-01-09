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

from src.pipeline import load_data, make_training_dataset
from src.config.config import load_config


def diagnose_backtest_data():
    """Diagnose potential backtest data issues."""
    
    print("=" * 80)
    print("BACKTEST DATA DIAGNOSTICS")
    print("=" * 80)
    print()
    
    # Load config
    config = load_config()
    
    print("📊 Configuration:")
    print(f"   Training years: {config.backtest.train_years}")
    print(f"   Test years: {config.backtest.test_years}")
    print(f"   Step years: {config.backtest.step_years}")
    print(f"   Rebalance frequency: {config.backtest.rebalance_freq}")
    print()
    
    # Load data
    print("📥 Loading data...")
    try:
        price_data, benchmark_data, fundamentals_data = load_data(config)
        print(f"   ✅ Price data: {len(price_data)} rows")
        print(f"   ✅ Benchmark data: {len(benchmark_data)} rows")
        print(f"   ✅ Fundamentals data: {len(fundamentals_data) if fundamentals_data is not None else 0} rows")
    except Exception as e:
        print(f"   ❌ Error loading data: {e}")
        return
    
    print()
    
    # Check date ranges
    print("📅 Date Ranges:")
    if 'date' in price_data.columns:
        price_data['date'] = pd.to_datetime(price_data['date'])
        price_min = price_data['date'].min()
        price_max = price_data['date'].max()
        price_span = (price_max - price_min).days / 365.25
        print(f"   Price data: {price_min.date()} to {price_max.date} ({price_span:.1f} years)")
    
    if 'date' in benchmark_data.columns:
        benchmark_data['date'] = pd.to_datetime(benchmark_data['date'])
        bench_min = benchmark_data['date'].min()
        bench_max = benchmark_data['date'].max()
        bench_span = (bench_max - bench_min).days / 365.25
        print(f"   Benchmark data: {bench_min.date()} to {bench_max.date()} ({bench_span:.1f} years)")
    
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
    
    # Try to create training dataset
    print("🔧 Creating training dataset...")
    try:
        training_data, feature_cols = make_training_dataset(
            price_data,
            benchmark_data,
            fundamentals_data,
            config
        )
        print(f"   ✅ Training data created: {len(training_data)} rows, {len(feature_cols)} features")
        
        if 'date' in training_data.columns:
            training_data['date'] = pd.to_datetime(training_data['date'])
            train_min = training_data['date'].min()
            train_max = training_data['date'].max()
            train_span = (train_max - train_min).days / 365.25
            print(f"   Date range: {train_min.date()} to {train_max.date()} ({train_span:.1f} years)")
            
            if train_span < min_required:
                print(f"   ⚠️  WARNING: Training data span ({train_span:.1f} years) is insufficient!")
                print(f"      Need at least {min_required:.1f} years for walk-forward backtest")
    except Exception as e:
        print(f"   ❌ Error creating training dataset: {e}")
        import traceback
        traceback.print_exc()
        return
    
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
