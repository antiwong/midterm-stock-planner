"""EODHD Financial Data API integration for sentiment and news.

EODHD provides:
- News articles with pre-computed sentiment (polarity, pos/neg/neutral)
- Daily aggregated sentiment scores (normalized 0-1, article count)
- EOD prices (free plan: any US ticker)
- Fundamentals (paid plan only: $59.99/mo)

Free plan: 20 API calls/day, news costs 5 calls each = 4 news requests/day.
Sentiment endpoint cost TBD.

API docs: https://eodhd.com/financial-apis/stock-market-financial-news-api
"""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class EODHDClient:
    """Client for EODHD Financial Data API."""

    BASE_URL = "https://eodhd.com/api"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("EODHD_API_KEY", "")
        if not self.api_key:
            # Handle the space in env var name
            for key in ["EODHD API", "EODHD_API"]:
                val = os.environ.get(key, "").strip().strip('"')
                if val:
                    self.api_key = val
                    break
        if not self.api_key:
            raise ValueError(
                "EODHD API key not found. Set EODHD_API_KEY in .env or environment."
            )
        self.call_count = 0
        self.daily_limit = 20  # free plan

    def _get(self, endpoint: str, params: Dict) -> Optional[any]:
        """Make rate-limited API call."""
        params["api_token"] = self.api_key
        params.setdefault("fmt", "json")
        self.call_count += 1

        try:
            r = requests.get(f"{self.BASE_URL}/{endpoint}", params=params, timeout=30)
            if r.status_code == 429:
                print("  EODHD rate limited, waiting 60s...")
                time.sleep(62)
                r = requests.get(f"{self.BASE_URL}/{endpoint}", params=params, timeout=30)
            if r.ok:
                return r.json()
            elif r.status_code == 403:
                return None  # paid plan required
            else:
                return None
        except Exception as e:
            print(f"  EODHD error: {e}")
            return None

    # --- News + Sentiment ---

    def fetch_news(self, ticker: str, limit: int = 50) -> List[Dict]:
        """Fetch news articles with pre-scored sentiment for a ticker.

        Each article includes: title, date, content, sentiment {polarity, neg, neu, pos}.
        Free plan: 5 API calls per news request, so 4 requests/day max.
        """
        # EODHD uses format: AAPL.US
        symbol = f"{ticker}.US" if "." not in ticker else ticker
        data = self._get("news", {"s": symbol, "limit": limit})
        if not data or not isinstance(data, list):
            return []
        return data

    def fetch_daily_sentiment(self, ticker: str,
                               start_date: str = None,
                               end_date: str = None) -> pd.DataFrame:
        """Fetch daily aggregated sentiment scores for a ticker.

        Returns DataFrame with columns: date, count, normalized (0-1 score).
        Score > 0.5 = positive sentiment, < 0.5 = negative.
        """
        symbol = f"{ticker}.US" if "." not in ticker else ticker
        params = {"s": symbol}
        if start_date:
            params["from"] = start_date
        if end_date:
            params["to"] = end_date

        data = self._get("sentiments", params)
        if not data or not isinstance(data, dict):
            return pd.DataFrame()

        # Response format: {"AAPL.US": [{"date": "...", "count": N, "normalized": 0.X}, ...]}
        records = list(data.values())[0] if data else []
        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df["ticker"] = ticker
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date")

    # --- Batch Operations ---

    def fetch_sentiment_for_tickers(self, tickers: List[str],
                                     start_date: str = None,
                                     end_date: str = None) -> pd.DataFrame:
        """Fetch daily sentiment for multiple tickers.

        Returns combined DataFrame with columns: date, ticker, count, normalized.
        """
        all_dfs = []
        for ticker in tickers:
            df = self.fetch_daily_sentiment(ticker, start_date, end_date)
            if not df.empty:
                all_dfs.append(df)
                print(f"  {ticker}: {len(df)} days of sentiment")
            else:
                print(f"  {ticker}: no sentiment data")
            time.sleep(0.5)  # rate limiting

        if all_dfs:
            return pd.concat(all_dfs, ignore_index=True)
        return pd.DataFrame()

    def fetch_news_for_tickers(self, tickers: List[str],
                                limit_per_ticker: int = 20) -> pd.DataFrame:
        """Fetch news with sentiment for multiple tickers.

        Warning: Each news request costs 5 API calls. Free plan allows ~4 total.
        """
        all_articles = []
        for ticker in tickers:
            articles = self.fetch_news(ticker, limit=limit_per_ticker)
            for a in articles:
                sentiment = a.get("sentiment", {})
                all_articles.append({
                    "date": a.get("date", ""),
                    "ticker": ticker,
                    "headline": a.get("title", ""),
                    "summary": (a.get("content", "") or "")[:500],
                    "source": a.get("source", "eodhd"),
                    "category": ", ".join(a.get("tags", [])),
                    "url": a.get("link", ""),
                    "sentiment_score": sentiment.get("polarity", 0),
                    "sentiment_pos": sentiment.get("pos", 0),
                    "sentiment_neg": sentiment.get("neg", 0),
                    "sentiment_neu": sentiment.get("neu", 0),
                })
            if articles:
                print(f"  {ticker}: {len(articles)} articles")
            time.sleep(1.0)  # news costs 5 calls each

        if all_articles:
            df = pd.DataFrame(all_articles)
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values(["ticker", "date"])
        return pd.DataFrame()


def download_eodhd_sentiment(tickers: List[str],
                              start_date: str = None,
                              end_date: str = None,
                              output_dir: str = "data/sentiment") -> Dict[str, pd.DataFrame]:
    """Download EODHD sentiment data and save to CSV.

    Downloads:
    1. Daily aggregated sentiment (all tickers, no API call limit concern)
    2. News articles (limited by free plan: ~4 tickers max)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    client = EODHDClient()
    results = {}

    # 1. Daily sentiment (lightweight, 1 call per ticker)
    print(f"\nEODHD Daily Sentiment ({start_date} to {end_date}):")
    sentiment_df = client.fetch_sentiment_for_tickers(tickers, start_date, end_date)
    if not sentiment_df.empty:
        path = output_path / "eodhd_daily_sentiment.csv"
        # Merge with existing
        if path.exists():
            existing = pd.read_csv(path, parse_dates=["date"])
            sentiment_df = pd.concat([existing, sentiment_df], ignore_index=True)
            sentiment_df = sentiment_df.drop_duplicates(subset=["date", "ticker"], keep="last")
            sentiment_df = sentiment_df.sort_values(["ticker", "date"])
        sentiment_df.to_csv(path, index=False)
        results["daily_sentiment"] = sentiment_df
        print(f"  Saved {len(sentiment_df)} records to {path}")

    # 2. News (expensive: 5 calls each, only do top tickers)
    # On free plan, only fetch news for top 3 tickers to stay under limit
    news_tickers = tickers[:3]
    print(f"\nEODHD News (top {len(news_tickers)} tickers):")
    news_df = client.fetch_news_for_tickers(news_tickers, limit_per_ticker=10)
    if not news_df.empty:
        path = output_path / "eodhd_news.csv"
        if path.exists():
            existing = pd.read_csv(path, parse_dates=["date"])
            news_df = pd.concat([existing, news_df], ignore_index=True)
            news_df = news_df.drop_duplicates(subset=["ticker", "headline"], keep="last")
            news_df = news_df.sort_values(["ticker", "date"])
        news_df.to_csv(path, index=False)
        results["news"] = news_df
        print(f"  Saved {len(news_df)} articles to {path}")

    return results
