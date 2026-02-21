#!/usr/bin/env python3
"""
Download / Extend Benchmark Data
================================
Downloads SPY (S&P 500 ETF) as benchmark and extends data/benchmark.csv
to cover the full history needed for walk-forward backtests (default: from 2010).

Usage:
    python scripts/download_benchmark.py
    python scripts/download_benchmark.py --start 2015-01-01
    python scripts/download_benchmark.py --output data/benchmark.csv
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    print("⚠️ yfinance required. Run: pip install yfinance")
    sys.exit(1)


def download_benchmark(
    ticker: str = "SPY",
    start: str = "2010-01-01",
    end: str | None = None,
    interval: str = "1d",
    output_path: str = "data/benchmark.csv",
    merge_with_existing: bool = True,
) -> pd.DataFrame:
    """
    Download benchmark (SPY) data and optionally merge with existing file.

    Args:
        ticker: Benchmark ticker (default SPY for S&P 500)
        start: Start date
        end: End date (default: today)
        output_path: Output CSV path
        merge_with_existing: If True, merge with existing benchmark preserving other tickers

    Returns:
        Full benchmark DataFrame (single or merged)
    """
    end = end or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    output = Path(output_path)

    print(f"📥 Downloading {ticker} ({interval}) from {start} to {end}...")
    data = yf.download(ticker, start=start, end=end, interval=interval, auto_adjust=True, progress=False)

    if data.empty:
        print(f"❌ No data returned for {ticker}")
        sys.exit(1)

    # Normalize to expected format (handle multi-level columns from yfinance)
    data = data.reset_index()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [c[0] for c in data.columns]  # Use first level (Datetime, Close, etc.)
    # Date/Datetime column
    date_col = "Datetime" if "Datetime" in data.columns else "Date"
    data = data.rename(columns={date_col: "date"})
    data["ticker"] = ticker
    close_col = "Close" if "Close" in data.columns else "close"
    if close_col != "close":
        data["close"] = data[close_col]

    new_df = data[["date", "ticker", "close"]].copy()
    new_df["date"] = pd.to_datetime(new_df["date"], errors="coerce")
    new_df = new_df.dropna(subset=["date", "close"])
    new_df["date"] = new_df["date"].dt.tz_localize(None)

    if merge_with_existing and output.exists():
        existing = pd.read_csv(output)
        existing["date"] = pd.to_datetime(existing["date"])
        if "ticker" in existing.columns:
            # Keep other tickers, update/add SPY
            other = existing[existing["ticker"] != ticker]
            combined = pd.concat([new_df, other], ignore_index=True)
        else:
            # Legacy format: date, close — replace with new
            combined = new_df
        # Deduplicate by (date, ticker), prefer new data
        combined = combined.drop_duplicates(subset=["date", "ticker"] if "ticker" in combined.columns else ["date"], keep="last")
        combined = combined.sort_values("date").reset_index(drop=True)
    else:
        combined = new_df.sort_values("date").reset_index(drop=True)

    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output, index=False)
    print(f"✅ Saved {len(combined)} rows to {output}")
    print(f"   Date range: {combined['date'].min().date()} to {combined['date'].max().date()}")
    return combined


def main():
    import argparse
    p = argparse.ArgumentParser(description="Download/extend benchmark data")
    p.add_argument("--ticker", default="SPY", help="Benchmark ticker")
    p.add_argument("--start", default="2010-01-01", help="Start date")
    p.add_argument("--end", default=None, help="End date")
    p.add_argument("--interval", "-i", default="1d", help="1d or 1h (1h limited to ~730 days)")
    p.add_argument("--output", default="data/benchmark.csv", help="Output path")
    p.add_argument("--no-merge", action="store_true", help="Replace file instead of merging")
    args = p.parse_args()
    download_benchmark(
        ticker=args.ticker,
        start=args.start,
        end=args.end,
        interval=args.interval,
        output_path=args.output,
        merge_with_existing=not args.no_merge,
    )


if __name__ == "__main__":
    main()
