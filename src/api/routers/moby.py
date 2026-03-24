from src.api.db import cached_response
"""Moby analysis endpoints — reads from DuckDB moby_picks + moby_news tables."""

from fastapi import APIRouter, Query
import duckdb
from pathlib import Path
from src.data.shared_db import DATA_DIR

router = APIRouter(prefix="/api/moby", tags=["moby"])

DUCKDB_PATH = DATA_DIR / "sentimentpulse.db"


def _ensure_moby_tables():
    """Create moby tables if they don't exist (survives crawler DB overwrites)."""
    try:
        import duckdb as _db
        con = _db.connect(str(DUCKDB_PATH))
        con.execute("""CREATE TABLE IF NOT EXISTS moby_picks (
            ticker VARCHAR NOT NULL, company VARCHAR, date DATE NOT NULL,
            rating VARCHAR, current_price FLOAT, price_target FLOAT,
            upside_pct FLOAT, target_date VARCHAR, market_cap VARCHAR,
            eps FLOAT, pe_ratio FLOAT, earnings_date VARCHAR,
            article_title VARCHAR, thesis_summary TEXT, moby_conclusion TEXT,
            opportunities TEXT, risks TEXT, report_week VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS moby_news (
            date DATE NOT NULL, headline VARCHAR NOT NULL,
            category VARCHAR, report_week VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        con.close()
    except Exception:
        pass

_ensure_moby_tables()


def _get_conn():
    return duckdb.connect(str(DUCKDB_PATH), read_only=True)


def _safe_float(v, default=0.0):
    import math
    try:
        f = float(v)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


@router.get("/analysis")
@cached_response(ttl=120)
def get_analysis():
    """Latest Moby analyst picks with price targets and thesis from DuckDB."""
    try:
        conn = _get_conn()
        df = conn.execute(
            "SELECT * FROM moby_picks ORDER BY date DESC"
        ).fetchdf()
        conn.close()

        if df.empty:
            return {"picks": []}

        picks = []
        for _, row in df.iterrows():
            picks.append({
                "date": str(row["date"]),
                "company": row.get("company", ""),
                "ticker": row.get("ticker", ""),
                "current_price": round(_safe_float(row.get("current_price")), 2),
                "price_target": round(_safe_float(row.get("price_target")), 2),
                "upside_pct": round(_safe_float(row.get("upside_pct")), 1),
                "rating": row.get("rating", ""),
                "earnings_date": row.get("earnings_date", ""),
                "article_title": row.get("article_title", ""),
                "target_date": row.get("target_date", ""),
                "market_cap": row.get("market_cap", ""),
                "eps": round(_safe_float(row.get("eps")), 2),
                "pe_ratio": round(_safe_float(row.get("pe_ratio")), 2),
                "thesis_summary": row.get("thesis_summary", ""),
                "moby_conclusion": row.get("moby_conclusion", ""),
                "opportunities": row.get("opportunities", ""),
                "risks": row.get("risks", ""),
                "report_week": row.get("report_week", ""),
            })
        return {"picks": picks, "count": len(picks), "source": "duckdb"}
    except Exception as e:
        return {"picks": [], "count": 0, "error": str(e)}


@router.get("/performance")
@cached_response(ttl=120)
def get_performance():
    """Track Moby picks vs actual prices using DuckDB + latest prices."""
    try:
        conn = _get_conn()
        df = conn.execute("SELECT * FROM moby_picks ORDER BY date DESC").fetchdf()
        conn.close()
    except Exception:
        return {"performance": []}

    if df.empty:
        return {"performance": []}

    # Load latest prices
    import pandas as pd
    price_map = {}
    prices_path = DATA_DIR / "prices_daily.csv"
    if prices_path.exists():
        try:
            pdf = pd.read_csv(prices_path)
            ticker_col = "ticker" if "ticker" in pdf.columns else "symbol"
            for ticker in pdf[ticker_col].unique():
                tdf = pdf[pdf[ticker_col] == ticker]
                if len(tdf) > 0 and "close" in tdf.columns:
                    price_map[ticker] = float(tdf.iloc[-1]["close"])
        except Exception:
            pass

    performance = []
    for _, row in df.iterrows():
        ticker = row.get("ticker", "")
        entry_price = _safe_float(row.get("current_price"))
        target = _safe_float(row.get("price_target"))
        current_price = price_map.get(ticker, entry_price)

        actual_return = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        target_return = _safe_float(row.get("upside_pct"))
        progress = (actual_return / target_return * 100) if target_return > 0 else 0

        performance.append({
            "ticker": ticker,
            "company": row.get("company", ""),
            "entry_date": str(row.get("date", "")),
            "entry_price": round(entry_price, 2),
            "price_target": round(target, 2),
            "current_price": round(current_price, 2),
            "actual_return_pct": round(actual_return, 2),
            "target_return_pct": round(target_return, 2),
            "progress_pct": round(progress, 1),
            "rating": row.get("rating", ""),
        })

    return {"performance": performance}


@router.get("/news")
@cached_response(ttl=120)
def get_moby_news(days: int = Query(30, ge=1, le=365)):
    """Moby weekly news articles from DuckDB."""
    try:
        conn = _get_conn()
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = conn.execute(
            "SELECT * FROM moby_news WHERE date >= ? ORDER BY date DESC",
            [cutoff],
        ).fetchdf()
        conn.close()

        if df.empty:
            return {"articles": [], "count": 0}

        articles = []
        for _, row in df.iterrows():
            articles.append({
                "date": str(row["date"]),
                "headline": row.get("headline", ""),
                "category": row.get("category", ""),
                "report_week": row.get("report_week", ""),
            })
        return {"articles": articles, "count": len(articles), "source": "duckdb"}
    except Exception as e:
        return {"articles": [], "count": 0, "error": str(e)}
