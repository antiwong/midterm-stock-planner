"""
Alpaca Markets Data Client
===========================
Downloads historical OHLCV data from Alpaca Markets (free tier).

Advantages over yfinance:
- Reliable API (not scraping)
- 7+ years of intraday data (vs yfinance 730-day limit)
- Unlimited daily data history
- Free tier: 200 req/min

Setup:
    export ALPACA_API_KEY=your_key
    export ALPACA_SECRET_KEY=your_secret

    Or create .env file with these values.
    Sign up at: https://app.alpaca.markets/signup
"""

import os
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict

import pandas as pd
import numpy as np

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Alpaca SDK imports
try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False


# Mapping from string interval to Alpaca TimeFrame
INTERVAL_MAP = {
    "1m": TimeFrame.Minute if ALPACA_AVAILABLE else None,
    "5m": TimeFrame(5, TimeFrameUnit.Minute) if ALPACA_AVAILABLE else None,
    "15m": TimeFrame(15, TimeFrameUnit.Minute) if ALPACA_AVAILABLE else None,
    "30m": TimeFrame(30, TimeFrameUnit.Minute) if ALPACA_AVAILABLE else None,
    "1h": TimeFrame.Hour if ALPACA_AVAILABLE else None,
    "1d": TimeFrame.Day if ALPACA_AVAILABLE else None,
    "1w": TimeFrame.Week if ALPACA_AVAILABLE else None,
    "1mo": TimeFrame.Month if ALPACA_AVAILABLE else None,
}


class AlpacaClient:
    """Downloads historical stock data from Alpaca Markets."""

    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None):
        if not ALPACA_AVAILABLE:
            raise ImportError("alpaca-py not installed. Run: pip install alpaca-py")

        self.api_key = api_key or os.environ.get("ALPACA_API_KEY", "")
        self.secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY", "")

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Alpaca API keys not found. Set ALPACA_API_KEY and ALPACA_SECRET_KEY "
                "environment variables or pass them directly.\n"
                "Sign up (free) at: https://app.alpaca.markets/signup"
            )

        self.client = StockHistoricalDataClient(self.api_key, self.secret_key)
        self.download_log: List[str] = []
        self.successful_tickers: List[str] = []
        self.failed_tickers: List[str] = []
        self.failed_reasons: Dict[str, str] = {}

    def download(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
        interval: str = "1d",
        batch_size: int = 20,
    ) -> pd.DataFrame:
        """
        Download OHLCV data for a list of tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Bar interval (1m, 5m, 15m, 30m, 1h, 1d, 1w, 1mo)
            batch_size: Number of tickers per API call

        Returns:
            DataFrame with columns: date, ticker, open, high, low, close, volume
        """
        timeframe = INTERVAL_MAP.get(interval)
        if timeframe is None:
            raise ValueError(f"Unsupported interval: {interval}. Use one of: {list(INTERVAL_MAP.keys())}")

        tickers = [t.upper().strip() for t in tickers]

        # Filter known delisted tickers
        try:
            from scripts.download_prices import DELISTED_TICKERS
            before = len(tickers)
            tickers = [t for t in tickers if t not in DELISTED_TICKERS]
            skipped = before - len(tickers)
            if skipped:
                print(f"  Skipped {skipped} delisted ticker(s)")
        except ImportError:
            pass

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        print(f"\n  Downloading {len(tickers)} tickers via Alpaca [{interval}]")
        print(f"  Period: {start_date} to {end_date}")

        all_frames = []

        for i in range(0, len(tickers), batch_size):
            batch = tickers[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(tickers) + batch_size - 1) // batch_size
            print(f"  Batch {batch_num}/{total_batches}: {len(batch)} tickers...")

            try:
                request = StockBarsRequest(
                    symbol_or_symbols=batch,
                    timeframe=timeframe,
                    start=start_dt,
                    end=end_dt,
                )
                bars = self.client.get_stock_bars(request)
                df = bars.df  # MultiIndex: (symbol, timestamp)

                if df.empty:
                    for t in batch:
                        self.failed_tickers.append(t)
                        self.failed_reasons[t] = "No data returned"
                        self._log(f"  x {t}: No data")
                    continue

                # Reset multi-index to columns
                df = df.reset_index()

                # Standardise column names
                col_map = {"symbol": "ticker", "timestamp": "date"}
                df = df.rename(columns=col_map)

                # Keep only needed columns
                keep = ["date", "ticker", "open", "high", "low", "close", "volume"]
                df = df[[c for c in keep if c in df.columns]]

                # Strip timezone
                df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

                # Normalize daily dates to midnight
                if interval in ("1d", "1w", "1mo"):
                    df["date"] = df["date"].dt.normalize()

                for t in batch:
                    tdf = df[df["ticker"] == t]
                    if len(tdf) > 0:
                        all_frames.append(tdf)
                        self.successful_tickers.append(t)
                        self._log(f"  + {t}: {len(tdf)} bars")
                    else:
                        self.failed_tickers.append(t)
                        self.failed_reasons[t] = "No data in response"
                        self._log(f"  x {t}: No data in response")

            except Exception as e:
                err = str(e)
                print(f"  Batch error: {err[:100]}")
                for t in batch:
                    self.failed_tickers.append(t)
                    self.failed_reasons[t] = err[:200]

            # Rate-limit: Alpaca free = 200 req/min, be conservative
            if total_batches > 1:
                time.sleep(0.5)

        if all_frames:
            result = pd.concat(all_frames, ignore_index=True)
            result = result.sort_values(["ticker", "date"]).reset_index(drop=True)
            print(f"  Total: {len(result):,} bars for {len(self.successful_tickers)} tickers")
            return result
        else:
            print("  No data downloaded")
            return pd.DataFrame()

    def _log(self, msg: str):
        self.download_log.append(msg)

    def get_report(self) -> Dict:
        return {
            "successful": len(self.successful_tickers),
            "failed": len(self.failed_tickers),
            "failed_tickers": self.failed_tickers,
            "failed_reasons": self.failed_reasons,
            "log": self.download_log,
        }
