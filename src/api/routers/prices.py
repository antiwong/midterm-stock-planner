"""Price data endpoints for charting."""

from fastapi import APIRouter, Query
from typing import List
from datetime import datetime, timedelta
from ..db import get_prices

router = APIRouter(prefix="/api/prices", tags=["prices"])


@router.get("/{ticker}")
def get_ticker_prices(ticker: str, days: int = Query(90, le=3650)):
    """OHLCV data for a single ticker."""
    df = get_prices()
    if df.empty:
        return {"ticker": ticker, "prices": []}

    cutoff = datetime.now() - timedelta(days=days)
    mask = (df["ticker"] == ticker.upper()) & (df["date"] >= cutoff)
    filtered = df.loc[mask].sort_values("date")

    prices = []
    for _, row in filtered.iterrows():
        prices.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "open": round(row["open"], 2),
            "high": round(row["high"], 2),
            "low": round(row["low"], 2),
            "close": round(row["close"], 2),
            "volume": int(row["volume"]) if row["volume"] == row["volume"] else 0,
        })

    return {"ticker": ticker.upper(), "count": len(prices), "prices": prices}


@router.get("/multi/batch")
def get_multi_prices(tickers: str = Query(..., description="Comma-separated tickers"),
                     days: int = Query(90, le=3650)):
    """OHLCV data for multiple tickers (close prices only for overlay charts)."""
    df = get_prices()
    if df.empty:
        return {"tickers": {}}

    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    cutoff = datetime.now() - timedelta(days=days)

    result = {}
    for ticker in ticker_list:
        mask = (df["ticker"] == ticker) & (df["date"] >= cutoff)
        filtered = df.loc[mask].sort_values("date")
        result[ticker] = [
            {"date": row["date"].strftime("%Y-%m-%d"), "close": round(row["close"], 2)}
            for _, row in filtered.iterrows()
        ]

    return {"tickers": result}
