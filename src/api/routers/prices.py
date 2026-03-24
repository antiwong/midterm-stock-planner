"""Price data endpoints for charting."""

from fastapi import APIRouter, Query
from typing import List
from datetime import datetime, timedelta
from ..db import cached_response, get_prices

router = APIRouter(prefix="/api/prices", tags=["prices"])


@router.get("/{ticker}")
@cached_response(ttl=60)
def get_ticker_prices(ticker: str, days: int = Query(90, le=3650)):
    """OHLCV data for a single ticker."""
    df = get_prices()
    if df.empty:
        return {"ticker": ticker, "prices": []}

    cutoff = datetime.now() - timedelta(days=days)
    mask = (df["ticker"] == ticker.upper()) & (df["date"] >= cutoff)
    filtered = df.loc[mask].sort_values("date").copy()

    filtered["date"] = filtered["date"].dt.strftime("%Y-%m-%d")
    filtered["open"] = filtered["open"].round(2)
    filtered["high"] = filtered["high"].round(2)
    filtered["low"] = filtered["low"].round(2)
    filtered["close"] = filtered["close"].round(2)
    filtered["volume"] = filtered["volume"].fillna(0).astype(int)

    prices = filtered[["date", "open", "high", "low", "close", "volume"]].to_dict("records")

    return {"ticker": ticker.upper(), "count": len(prices), "prices": prices}


@router.get("/multi/batch")
@cached_response(ttl=60)
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
        filtered = df.loc[mask].sort_values("date").copy()
        filtered["date"] = filtered["date"].dt.strftime("%Y-%m-%d")
        filtered["close"] = filtered["close"].round(2)
        result[ticker] = filtered[["date", "close"]].to_dict("records")

    return {"tickers": result}
