#!/usr/bin/env python3
"""
Download Sentiment & Alternative Data from Finnhub
====================================================
Downloads news, insider transactions, analyst recommendations, and earnings
for all tickers in a watchlist.

Free tier endpoints used:
- /company-news — news articles with headlines, summaries, URLs
- /stock/insider-transactions — insider buys/sells with amounts
- /stock/recommendation — analyst buy/hold/sell consensus
- /stock/earnings — actual vs estimate EPS

Usage:
    python scripts/download_sentiment.py --watchlist tech_giants
    python scripts/download_sentiment.py --tickers AMD SLV NVDA
    python scripts/download_sentiment.py --watchlist focus_optimization --days 365
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class FinnhubSentiment:
    """Downloads sentiment and alternative data from Finnhub."""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FINNHUB_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "FINNHUB_API_KEY not set. Add to .env or export FINNHUB_API_KEY=your_key"
            )
        self.request_count = 0
        self.rate_limit = 55  # stay under 60/min free tier

    def _get(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Make rate-limited API call."""
        self.request_count += 1
        if self.request_count % self.rate_limit == 0:
            print("    (rate limit pause...)")
            time.sleep(62)

        params["token"] = self.api_key
        try:
            r = requests.get(f"{self.BASE_URL}{endpoint}", params=params, timeout=30)
            if r.status_code == 429:
                print("    Rate limited, waiting 60s...")
                time.sleep(62)
                r = requests.get(f"{self.BASE_URL}{endpoint}", params=params, timeout=30)
            if r.ok:
                return r.json()
            else:
                return None
        except Exception as e:
            print(f"    Error: {e}")
            return None

    def download_news(self, tickers: List[str], days: int = 90) -> pd.DataFrame:
        """Download company news for tickers."""
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        print(f"\n  News articles ({start} to {end}):")
        all_news = []

        for t in tickers:
            data = self._get("/company-news", {"symbol": t, "from": start, "to": end})
            if data:
                for article in data:
                    all_news.append({
                        "date": datetime.fromtimestamp(article.get("datetime", 0)).strftime("%Y-%m-%d %H:%M:%S"),
                        "ticker": t,
                        "headline": article.get("headline", ""),
                        "summary": article.get("summary", "")[:500],
                        "source": article.get("source", ""),
                        "category": article.get("category", ""),
                        "url": article.get("url", ""),
                    })
                print(f"    + {t}: {len(data)} articles")
            else:
                print(f"    x {t}: no data")
            time.sleep(0.3)

        if all_news:
            df = pd.DataFrame(all_news)
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values(["ticker", "date"])
        return pd.DataFrame()

    def download_insider_transactions(self, tickers: List[str]) -> pd.DataFrame:
        """Download insider buy/sell transactions."""
        print("\n  Insider transactions:")
        all_txns = []

        for t in tickers:
            data = self._get("/stock/insider-transactions", {"symbol": t})
            if data and "data" in data:
                for txn in data["data"]:
                    all_txns.append({
                        "date": txn.get("transactionDate", ""),
                        "ticker": t,
                        "insider_name": txn.get("name", ""),
                        "transaction_type": txn.get("transactionType", ""),
                        "shares": txn.get("share", 0),
                        "price": txn.get("transactionPrice", 0),
                        "value": (txn.get("share", 0) or 0) * (txn.get("transactionPrice", 0) or 0),
                        "filing_date": txn.get("filingDate", ""),
                    })
                print(f"    + {t}: {len(data['data'])} transactions")
            else:
                print(f"    x {t}: no data")
            time.sleep(0.3)

        if all_txns:
            df = pd.DataFrame(all_txns)
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values(["ticker", "date"])
        return pd.DataFrame()

    def download_recommendations(self, tickers: List[str]) -> pd.DataFrame:
        """Download analyst recommendations (buy/hold/sell consensus)."""
        print("\n  Analyst recommendations:")
        all_recs = []

        for t in tickers:
            data = self._get("/stock/recommendation", {"symbol": t})
            if data:
                for rec in data:
                    all_recs.append({
                        "date": rec.get("period", ""),
                        "ticker": t,
                        "strong_buy": rec.get("strongBuy", 0),
                        "buy": rec.get("buy", 0),
                        "hold": rec.get("hold", 0),
                        "sell": rec.get("sell", 0),
                        "strong_sell": rec.get("strongSell", 0),
                    })
                print(f"    + {t}: {len(data)} periods")
            else:
                print(f"    x {t}: no data")
            time.sleep(0.3)

        if all_recs:
            df = pd.DataFrame(all_recs)
            df["date"] = pd.to_datetime(df["date"])
            # Compute sentiment score: (strongBuy*2 + buy - sell - strongSell*2) / total
            total = df[["strong_buy", "buy", "hold", "sell", "strong_sell"]].sum(axis=1)
            df["analyst_score"] = (
                df["strong_buy"] * 2 + df["buy"] - df["sell"] - df["strong_sell"] * 2
            ) / total.replace(0, 1)
            return df.sort_values(["ticker", "date"])
        return pd.DataFrame()

    def download_earnings(self, tickers: List[str]) -> pd.DataFrame:
        """Download earnings surprises (actual vs estimate)."""
        print("\n  Earnings surprises:")
        all_earnings = []

        for t in tickers:
            data = self._get("/stock/earnings", {"symbol": t})
            if data:
                for e in data:
                    actual = e.get("actual")
                    estimate = e.get("estimate")
                    surprise = None
                    if actual is not None and estimate is not None and estimate != 0:
                        surprise = (actual - estimate) / abs(estimate)
                    all_earnings.append({
                        "date": e.get("period", ""),
                        "ticker": t,
                        "actual_eps": actual,
                        "estimate_eps": estimate,
                        "surprise_pct": surprise,
                        "quarter": e.get("quarter"),
                        "year": e.get("year"),
                    })
                print(f"    + {t}: {len(data)} quarters")
            else:
                print(f"    x {t}: no data")
            time.sleep(0.3)

        if all_earnings:
            df = pd.DataFrame(all_earnings)
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values(["ticker", "date"])
        return pd.DataFrame()

    def download_all(self, tickers: List[str], days: int = 90, output_dir: str = "data/sentiment") -> Dict[str, pd.DataFrame]:
        """Download all available sentiment data."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"Downloading Finnhub sentiment for {len(tickers)} tickers")
        print("=" * 50)

        results = {}

        # News
        news_df = self.download_news(tickers, days=days)
        if not news_df.empty:
            news_df.to_csv(output_path / "news.csv", index=False)
            results["news"] = news_df
            print(f"    Saved {len(news_df)} articles to {output_path}/news.csv")

        # Insider transactions
        insider_df = self.download_insider_transactions(tickers)
        if not insider_df.empty:
            insider_df.to_csv(output_path / "insider_transactions.csv", index=False)
            results["insider"] = insider_df
            print(f"    Saved {len(insider_df)} transactions to {output_path}/insider_transactions.csv")

        # Analyst recommendations
        rec_df = self.download_recommendations(tickers)
        if not rec_df.empty:
            rec_df.to_csv(output_path / "analyst_recommendations.csv", index=False)
            results["recommendations"] = rec_df
            print(f"    Saved {len(rec_df)} records to {output_path}/analyst_recommendations.csv")

        # Earnings
        earn_df = self.download_earnings(tickers)
        if not earn_df.empty:
            earn_df.to_csv(output_path / "earnings_surprises.csv", index=False)
            results["earnings"] = earn_df
            print(f"    Saved {len(earn_df)} records to {output_path}/earnings_surprises.csv")

        # Summary
        print("\n" + "=" * 50)
        print("Summary:")
        for name, df in results.items():
            print(f"  {name}: {len(df)} rows, {df['ticker'].nunique()} tickers")

        return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download sentiment data from Finnhub")
    parser.add_argument("--watchlist", "-w", type=str, default=None)
    parser.add_argument("--tickers", "-t", nargs="+", type=str, default=None)
    parser.add_argument("--days", "-d", type=int, default=90, help="Days of news history (default: 90)")
    parser.add_argument("--output", "-o", type=str, default="data/sentiment")
    args = parser.parse_args()

    if args.tickers:
        tickers = [t.upper() for t in args.tickers]
    elif args.watchlist:
        from src.data.watchlists import WatchlistManager
        wm = WatchlistManager.from_config_dir("config")
        watchlist = wm.get_watchlist(args.watchlist)
        if not watchlist:
            print(f"Watchlist '{args.watchlist}' not found")
            return 1
        tickers = watchlist.symbols
    else:
        # Default: focus tickers + key names
        tickers = ["AMD", "SLV", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "TSLA"]

    client = FinnhubSentiment()
    client.download_all(tickers, days=args.days, output_dir=args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
