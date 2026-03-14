#!/usr/bin/env python3
"""
Download Macro Data from FRED
==============================
Downloads economic indicators from Federal Reserve Economic Data (FRED).

Series downloaded:
- DGS10: 10-Year Treasury Yield
- DGS2: 2-Year Treasury Yield (for yield curve)
- T10YIE: 10-Year Breakeven Inflation
- UNRATE: Unemployment Rate
- CPIAUCSL: Consumer Price Index
- FEDFUNDS: Federal Funds Rate
- DTWEXBGS: Trade-Weighted USD Index (broad)

Setup:
    Sign up (free): https://fred.stlouisfed.org/docs/api/api_key.html
    export FRED_API_KEY=your_key

Usage:
    python scripts/download_macro.py
    python scripts/download_macro.py --start 2010-01-01
"""

import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# FRED series we want
FRED_SERIES = {
    "DGS10": "treasury_10y",
    "DGS2": "treasury_2y",
    "T10YIE": "breakeven_inflation_10y",
    "UNRATE": "unemployment_rate",
    "CPIAUCSL": "cpi",
    "FEDFUNDS": "fed_funds_rate",
    "DTWEXBGS": "usd_index_broad",
}


def download_fred(start: str = "2016-01-01", output: str = "data/macro_fred.csv"):
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        print("FRED_API_KEY not set. Sign up (free): https://fred.stlouisfed.org/docs/api/api_key.html")
        print("Then: export FRED_API_KEY=your_key")
        return None

    try:
        from fredapi import Fred
    except ImportError:
        print("fredapi not installed. Run: pip install fredapi")
        return None

    fred = Fred(api_key=api_key)
    end = datetime.now().strftime("%Y-%m-%d")

    print(f"Downloading FRED macro data: {start} to {end}")
    print("=" * 50)

    all_series = []
    for series_id, name in FRED_SERIES.items():
        try:
            data = fred.get_series(series_id, observation_start=start, observation_end=end)
            df = pd.DataFrame({"date": data.index, name: data.values})
            df["date"] = pd.to_datetime(df["date"]).dt.normalize()
            all_series.append(df)
            print(f"  + {name} ({series_id}): {len(df)} observations")
        except Exception as e:
            print(f"  x {name} ({series_id}): {e}")

    if not all_series:
        print("No data downloaded")
        return None

    # Merge all series on date
    result = all_series[0]
    for df in all_series[1:]:
        result = pd.merge(result, df, on="date", how="outer")

    result = result.sort_values("date")

    # Derived features
    if "treasury_10y" in result.columns and "treasury_2y" in result.columns:
        result["yield_curve_10y_2y"] = result["treasury_10y"] - result["treasury_2y"]

    if "treasury_10y" in result.columns and "breakeven_inflation_10y" in result.columns:
        result["real_yield_10y"] = result["treasury_10y"] - result["breakeven_inflation_10y"]

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print(f"\nSaved {len(result)} rows to {output_path}")
    print(f"Columns: {list(result.columns)}")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download macro data from FRED")
    parser.add_argument("--start", default="2016-01-01", help="Start date")
    parser.add_argument("--output", default="data/macro_fred.csv", help="Output CSV path")
    args = parser.parse_args()

    download_fred(start=args.start, output=args.output)
