"""Moby analysis endpoints: analyst picks and performance tracking."""

from fastapi import APIRouter
from ..db import get_moby_analysis, get_prices

router = APIRouter(prefix="/api/moby", tags=["moby"])


@router.get("/analysis")
def get_analysis():
    """Latest Moby analyst picks with price targets."""
    df = get_moby_analysis()
    if df.empty:
        return {"picks": []}

    picks = []
    for _, row in df.iterrows():
        picks.append({
            "date": row.get("date"),
            "company": row.get("company"),
            "ticker": row.get("ticker"),
            "current_price": row.get("current_price"),
            "price_target": row.get("price_target"),
            "upside_pct": row.get("upside_pct"),
            "rating": row.get("rating"),
            "earnings_date": row.get("earnings_date") if str(row.get("earnings_date")) != "nan" else None,
            "article_title": row.get("article_title") if str(row.get("article_title")) != "nan" else None,
        })

    return {"picks": picks}


@router.get("/performance")
def get_performance():
    """Track Moby picks vs actual prices."""
    moby_df = get_moby_analysis()
    if moby_df.empty:
        return {"performance": []}

    prices_df = get_prices()

    performance = []
    for _, row in moby_df.iterrows():
        ticker = row.get("ticker")
        entry_price = row.get("current_price", 0)
        target = row.get("price_target", 0)

        # Get latest close price
        current_price = entry_price
        if not prices_df.empty and ticker:
            ticker_prices = prices_df[prices_df["ticker"] == ticker]
            if len(ticker_prices) > 0:
                current_price = float(ticker_prices.iloc[-1]["close"])

        actual_return = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        target_return = row.get("upside_pct", 0) or 0
        progress = (actual_return / target_return * 100) if target_return > 0 else 0

        performance.append({
            "ticker": ticker,
            "company": row.get("company"),
            "entry_date": row.get("date"),
            "entry_price": round(entry_price, 2),
            "price_target": round(target, 2),
            "current_price": round(current_price, 2),
            "actual_return_pct": round(actual_return, 2),
            "target_return_pct": round(target_return, 2),
            "progress_pct": round(progress, 1),
            "rating": row.get("rating"),
        })

    return {"performance": performance}
