"""Sentiment Analysis router — DuckDB-first, with CSV fallback for news/analyst/insider/earnings."""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from src.data.shared_db import DATA_DIR, load_watchlist_config, get_active_watchlists
from src.api.db import read_csv_cached, cached_response, get_duckdb_conn

router = APIRouter(prefix="/api/sentiment", tags=["sentiment"])

SENTIMENT_DIR = DATA_DIR / "sentiment"
DUCKDB_PATH = DATA_DIR / "sentimentpulse.db"

_trends_log = logging.getLogger("trends_update")


def _safe_float(v, default=0.0) -> float:
    """Convert to float, replacing NaN/inf with default."""
    import math
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _read_csv(name: str) -> pd.DataFrame:
    path = SENTIMENT_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return read_csv_cached(str(path))


def _get_duckdb_conn():
    """Get pooled read-only DuckDB connection."""
    conn = get_duckdb_conn()
    if conn is None:
        import duckdb
        return duckdb.connect(str(DUCKDB_PATH), read_only=True)
    return conn


def _get_all_tickers() -> set:
    """All tickers across all active watchlists."""
    wl_config = load_watchlist_config()
    active = get_active_watchlists()
    tickers = set()
    for wl in active:
        tickers.update(wl_config.get(wl, {}).get("symbols", []))
    return tickers


# ---------------------------------------------------------------------------
# Overview — DuckDB composite scores + CSV analyst/earnings
# ---------------------------------------------------------------------------

@router.get("/overview")
@cached_response(ttl=120)
def sentiment_overview():
    """Aggregated sentiment overview from DuckDB SentimentPulse data.

    Per-ticker composite scores, signal breadth, conviction, regime.
    Supplemented with analyst recommendations from CSV.
    """
    tickers = _get_all_tickers()

    # Primary: DuckDB sentiment_features (latest date per ticker)
    duckdb_agg = {}
    try:
        conn = _get_duckdb_conn()
        df = conn.execute("""
            SELECT * FROM sentiment_features
            WHERE date = (SELECT MAX(date) FROM sentiment_features)
            ORDER BY composite_score DESC
        """).fetchdf()

        if not df.empty:
            for _, row in df.iterrows():
                tk = row.get("ticker", "")
                if tk not in tickers:
                    continue
                duckdb_agg[tk] = {
                    "composite_score": _safe_float(row.get("composite_score")),
                    "signal_breadth": _safe_float(row.get("signal_breadth")),
                    "signal_conviction": _safe_float(row.get("signal_conviction")),
                    "headline_count": int(_safe_float(row.get("headline_count", 0))),
                    "confidence": row.get("confidence", ""),
                    "sentiment_regime": row.get("sentiment_regime", "NOISE"),
                    "buzz_ratio": _safe_float(row.get("buzz_ratio", 1.0), 1.0),
                    "source_count": int(_safe_float(row.get("source_count", 0))),
                    "llm_score": _safe_float(row.get("llm_score")),
                    "finnhub_score": _safe_float(row.get("finnhub_score")),
                    "eodhd_score": _safe_float(row.get("eodhd_score")),
                    "options_pcr": _safe_float(row.get("options_pcr")) if row.get("options_pcr") is not None and not pd.isna(row.get("options_pcr")) else None,
                    "insider_signal": row.get("insider_signal", ""),
                    "insider_cluster_flag": bool(row.get("insider_cluster_flag")) if row.get("insider_cluster_flag") is not None and not pd.isna(row.get("insider_cluster_flag")) else False,
                    "analyst_consensus": row.get("analyst_consensus", ""),
                    "analyst_consensus_score": _safe_float(row.get("analyst_consensus_score")),
                    # ICD fields for overview table
                    "options_sentiment_signal": _safe_float(row.get("options_sentiment_signal")) if row.get("options_sentiment_signal") is not None and not pd.isna(row.get("options_sentiment_signal")) else None,
                    "iv_skew": _safe_float(row.get("iv_skew")) if row.get("iv_skew") is not None and not pd.isna(row.get("iv_skew")) else None,
                    "unusual_options_flag": bool(row.get("unusual_options_flag")) if row.get("unusual_options_flag") is not None and not pd.isna(row.get("unusual_options_flag")) else False,
                    "price_divergence": bool(row.get("price_divergence")) if row.get("price_divergence") is not None and not pd.isna(row.get("price_divergence")) else False,
                    "divergence_direction": str(row.get("divergence_direction", "none")),
                    "apewisdom_mentions": int(_safe_float(row.get("apewisdom_mentions", 0))),
                    "apewisdom_spike_flag": bool(row.get("apewisdom_spike_flag")) if row.get("apewisdom_spike_flag") is not None and not pd.isna(row.get("apewisdom_spike_flag")) else False,
                    "forward_event_type": str(row.get("forward_event_type", "")) if row.get("forward_event_type") is not None and not pd.isna(row.get("forward_event_type")) else None,
                    "earnings_date": str(row.get("earnings_date", "")) if row.get("earnings_date") is not None and not pd.isna(row.get("earnings_date")) else None,
                    "earnings_days_to": _safe_float(row.get("earnings_days_to")) if row.get("earnings_days_to") is not None and not pd.isna(row.get("earnings_days_to")) else None,
                    "market_regime": str(row.get("market_regime", "")),
                    "market_vix": _safe_float(row.get("market_vix")) if row.get("market_vix") is not None and not pd.isna(row.get("market_vix")) else None,
                    "market_spy_5d": _safe_float(row.get("market_spy_5d")) if row.get("market_spy_5d") is not None and not pd.isna(row.get("market_spy_5d")) else None,
                    "market_confidence_mult": _safe_float(row.get("market_confidence_mult")) if row.get("market_confidence_mult") is not None and not pd.isna(row.get("market_confidence_mult")) else None,
                }
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("DuckDB overview read failed: %s", e)

    # Supplement: analyst recommendations from CSV
    analyst = _read_csv("analyst_recommendations.csv")
    analyst_agg = {}
    if not analyst.empty:
        filtered = analyst[analyst["ticker"].isin(tickers)]
        if not filtered.empty:
            latest = filtered.sort_values("date").groupby("ticker").last()
            for tk, rec in latest.iterrows():
                analyst_agg[tk] = {
                    "strong_buy": int(_safe_float(rec.get("strong_buy"))),
                    "buy": int(_safe_float(rec.get("buy"))),
                    "hold": int(_safe_float(rec.get("hold"))),
                    "sell": int(_safe_float(rec.get("sell"))),
                    "strong_sell": int(_safe_float(rec.get("strong_sell"))),
                    "score": round(_safe_float(rec.get("analyst_score")), 4),
                }

    # Moby picks from DuckDB
    moby_agg = {}
    try:
        conn = _get_duckdb_conn()
        moby_df = conn.execute(
            "SELECT ticker, rating, current_price, price_target, upside_pct, article_title, date "
            "FROM moby_picks ORDER BY date DESC"
        ).fetchdf()
        if not moby_df.empty:
            for _, row in moby_df.iterrows():
                tk = row["ticker"]
                if tk not in moby_agg:
                    moby_agg[tk] = {
                        "rating": row.get("rating", ""),
                        "price_target": _safe_float(row.get("price_target")),
                        "upside_pct": _safe_float(row.get("upside_pct")),
                        "article_title": row.get("article_title", ""),
                        "date": str(row.get("date", "")),
                    }
    except Exception:
        pass

    # Compose per-ticker summary
    overview = []
    for ticker in sorted(tickers):
        entry = {"ticker": ticker}

        if ticker in duckdb_agg:
            d = duckdb_agg[ticker]
            entry["composite"] = round(d["composite_score"], 4)
            entry["signal_breadth"] = round(d["signal_breadth"], 4)
            entry["signal_conviction"] = round(d["signal_conviction"], 4)
            entry["headline_count"] = d["headline_count"]
            entry["regime"] = d["sentiment_regime"]
            entry["buzz_ratio"] = round(d["buzz_ratio"], 2)
            entry["confidence"] = d["confidence"]
            entry["source_count"] = d["source_count"]
            # Individual source scores for tooltip/detail
            entry["news"] = {
                "avg": round(d["composite_score"], 4),
                "count": d["headline_count"],
                "positive": 0, "negative": 0, "neutral": 0,
            }
            # Options flow
            if d.get("options_pcr") is not None:
                entry["options_pcr"] = round(d["options_pcr"], 3)
            # Forward events
            fwd = d.get("forward_event_type")
            if fwd:
                entry["forward_event"] = fwd
            elif d.get("earnings_days_to") is not None and d["earnings_days_to"] <= 14:
                entry["forward_event"] = f"Earnings in {int(d['earnings_days_to'])}d"
            # Divergence
            if d.get("price_divergence"):
                entry["divergence"] = d["divergence_direction"]
            # Social
            if d.get("apewisdom_mentions", 0) > 0:
                entry["apewisdom_mentions"] = d["apewisdom_mentions"]
            if d.get("apewisdom_spike_flag"):
                entry["apewisdom_spike"] = True
            # Insider
            if d.get("insider_cluster_flag"):
                entry["insider_cluster"] = True
        else:
            entry["composite"] = None
            entry["signal_breadth"] = 0.0
            entry["signal_conviction"] = None

        if ticker in analyst_agg:
            entry["analyst"] = analyst_agg[ticker]

        if ticker in moby_agg:
            entry["moby"] = moby_agg[ticker]

        if entry.get("composite") is not None or "analyst" in entry or "moby" in entry:
            overview.append(entry)

    overview.sort(key=lambda x: abs(x.get("composite") or 0), reverse=True)

    # Extract market regime from first ticker's data
    market_regime_data = None
    first_with_regime = next((d for d in duckdb_agg.values() if d.get("market_regime")), None)
    if first_with_regime:
        market_regime_data = {
            "regime": first_with_regime["market_regime"],
            "confidence_multiplier": first_with_regime.get("market_confidence_mult", 1.0),
            "vix": first_with_regime.get("market_vix"),
            "spy_5d_return": first_with_regime.get("market_spy_5d"),
        }

    # Market regime
    try:
        conn = _get_duckdb_conn()
        regime_row = conn.execute("""
            SELECT DISTINCT market_regime, market_vix, market_spy_5d, market_confidence_mult
            FROM sentiment_features
            WHERE date = (SELECT MAX(date) FROM sentiment_features)
            LIMIT 1
        """).fetchone()
        if regime_row:
            regime = {
                "regime": regime_row[0] or "UNKNOWN",
                "confidence_multiplier": _safe_float(regime_row[3], 1.0),
                "vix": _safe_float(regime_row[1]) if regime_row[1] else None,
                "spy_5d_return": _safe_float(regime_row[2]) if regime_row[2] else None,
            }
        else:
            regime = {"regime": "UNKNOWN", "confidence_multiplier": 1.0, "vix": None, "spy_5d_return": None}
    except Exception:
        regime = {"regime": "UNKNOWN", "confidence_multiplier": 1.0, "vix": None, "spy_5d_return": None}

    return {"tickers": overview, "count": len(overview), "market_regime": regime, "source": "duckdb"}


# ---------------------------------------------------------------------------
# Trend — DuckDB time series
# ---------------------------------------------------------------------------

@router.get("/trend")
@cached_response(ttl=300)
def sentiment_trend(ticker: str = "AAPL", days: int = 30):
    """Historical composite score for a ticker from DuckDB."""
    try:
        conn = _get_duckdb_conn()
        df = conn.execute(
            "SELECT date, composite_score FROM sentiment_features "
            "WHERE ticker = ? ORDER BY date DESC LIMIT ?",
            [ticker, days],
        ).fetchdf()
        if not df.empty:
            df = df.sort_values("date")
            data = [
                {"date": str(row["date"]), "score": round(_safe_float(row["composite_score"]), 4)}
                for _, row in df.iterrows()
            ]
            return {"ticker": ticker, "data": data}
    except Exception:
        pass

    # Fallback to EODHD CSV
    df = _read_csv("eodhd_daily_sentiment.csv")
    if df.empty:
        return {"ticker": ticker, "data": []}
    filtered = df[df["ticker"] == ticker].copy()
    if filtered.empty:
        return {"ticker": ticker, "data": []}
    filtered["date"] = pd.to_datetime(filtered["date"], format="mixed")
    filtered = filtered.sort_values("date").tail(days)
    data = [
        {"date": str(row["date"].date()), "score": round(_safe_float(row.get("normalized", 0.0)), 4)}
        for _, row in filtered.iterrows()
    ]
    return {"ticker": ticker, "data": data}


@router.get("/trend/multi")
@cached_response(ttl=300)
def sentiment_trend_multi(tickers: str = "AAPL,MSFT,GOOG", days: int = 30):
    """Historical sentiment scores for multiple tickers from DuckDB."""
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    result = {}
    available = []

    try:
        conn = _get_duckdb_conn()
        for tk in ticker_list:
            df = conn.execute(
                "SELECT date, composite_score FROM sentiment_features "
                "WHERE ticker = ? ORDER BY date DESC LIMIT ?",
                [tk, days],
            ).fetchdf()
            if not df.empty:
                df = df.sort_values("date")
                result[tk] = [
                    {"date": str(row["date"]), "score": round(_safe_float(row["composite_score"]), 4)}
                    for _, row in df.iterrows()
                ]
        # Get all available tickers
        avail_df = conn.execute("SELECT DISTINCT ticker FROM sentiment_features ORDER BY ticker").fetchdf()
        available = avail_df["ticker"].tolist() if not avail_df.empty else []
    except Exception:
        pass

    return {"tickers": result, "available_tickers": available}


# ---------------------------------------------------------------------------
# SentimentPulse (was "Blog") — full DuckDB feature set
# ---------------------------------------------------------------------------

@router.get("/blog")
@cached_response(ttl=300)
def sentimentpulse(days: int = 7):
    """SentimentPulse data from DuckDB — full feature set per ticker per day."""
    try:
        conn = _get_duckdb_conn()
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = conn.execute(
            "SELECT * FROM sentiment_features WHERE date >= ? ORDER BY date DESC, composite_score DESC",
            [cutoff],
        ).fetchdf()

        if df.empty:
            return {"tickers": [], "count": 0, "source": "duckdb"}

        # Replace NaN with None for JSON serialization
        df = df.where(df.notna(), None)

        records = []
        for _, row in df.iterrows():
            records.append({
                "date": str(row.get("date", "")),
                "ticker": str(row.get("ticker", "") or ""),
                "composite_score": round(_safe_float(row.get("composite_score")), 4),
                "confidence": str(row.get("confidence") or "low"),
                "headline_count": int(_safe_float(row.get("headline_count", 0))),
                "buzz_ratio": round(_safe_float(row.get("buzz_ratio", 1.0), 1.0), 2),
                "regime": str(row.get("sentiment_regime") or "NOISE"),
                "category": str(row.get("category") or "other"),
                "source_count": int(_safe_float(row.get("source_count", 0))),
                "options_pcr": round(_safe_float(row.get("options_pcr")), 2) if row.get("options_pcr") is not None else None,
                "options_iv_pct": round(_safe_float(row.get("iv_percentile")), 1) if row.get("iv_percentile") is not None else None,
                "forward_event": str(row.get("forward_event_type")) if row.get("forward_event_detected") is True else None,
                "signal_breadth": round(_safe_float(row.get("signal_breadth")), 4),
                "signal_conviction": round(_safe_float(row.get("signal_conviction")), 4),
                "signal_label": "",
                "llm_score": round(_safe_float(row.get("llm_score")), 4),
                "finnhub_score": round(_safe_float(row.get("finnhub_score")), 4),
                "eodhd_score": round(_safe_float(row.get("eodhd_score")), 4),
                "insider_signal": _safe_float(row.get("insider_signal")),
                "watchlist": str(row.get("watchlist") or ""),
            })

        records.sort(key=lambda x: abs(x.get("signal_conviction", 0)), reverse=True)
        return {"tickers": records, "count": len(records), "source": "duckdb"}
    except Exception as e:
        return {"tickers": [], "count": 0, "source": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# News, Analyst, Insiders, Earnings — still CSV (not in DuckDB)
# ---------------------------------------------------------------------------

@router.get("/news")
@cached_response(ttl=120)
def recent_news(ticker: Optional[str] = None, limit: int = 50):
    """Recent news headlines with sentiment scores."""
    # Try DuckDB articles table first
    try:
        conn = _get_duckdb_conn()
        if ticker:
            df = conn.execute(
                "SELECT * FROM articles WHERE ticker = ? ORDER BY date DESC LIMIT ?",
                [ticker, limit],
            ).fetchdf()
        else:
            df = conn.execute(
                "SELECT * FROM articles ORDER BY date DESC LIMIT ?",
                [limit],
            ).fetchdf()

        if not df.empty:
            articles = []
            for _, row in df.iterrows():
                sent = row.get("sentiment")
                sent_val = round(_safe_float(sent), 4) if sent is not None and not pd.isna(sent) else None
                cred = row.get("credibility_tier")
                cred_tier = str(cred) if cred is not None and not pd.isna(cred) and str(cred) else None
                articles.append({
                    "date": str(row.get("date", "")),
                    "ticker": str(row.get("ticker", "")),
                    "headline": str(row.get("headline", "")),
                    "one_line": str(row.get("one_line", "")) if row.get("one_line") is not None and not pd.isna(row.get("one_line")) else None,
                    "source": str(row.get("source", "")),
                    "credibility_tier": cred_tier,
                    "sentiment": sent_val,
                    "confidence": str(row.get("confidence", "")) if row.get("confidence") is not None and not pd.isna(row.get("confidence")) else None,
                    "category": str(row.get("category", "")) if row.get("category") is not None and not pd.isna(row.get("category")) else None,
                    "impact_horizon": str(row.get("impact_horizon", "")) if row.get("impact_horizon") is not None and not pd.isna(row.get("impact_horizon")) else None,
                    "analyst_firm": str(row.get("analyst_firm", "")) if row.get("analyst_firm") is not None and not pd.isna(row.get("analyst_firm")) else None,
                    "analyst_action": str(row.get("analyst_action", "")) if row.get("analyst_action") is not None and not pd.isna(row.get("analyst_action")) else None,
                    "is_sponsored": bool(row.get("is_sponsored")) if row.get("is_sponsored") is not None and not pd.isna(row.get("is_sponsored")) else False,
                    "url": str(row.get("url", "")),
                })
            return {"articles": articles, "count": len(articles)}
    except Exception:
        pass

    return {"articles": [], "count": 0}


@router.get("/analyst")
@cached_response(ttl=120)
def analyst_recommendations(ticker: Optional[str] = None):
    """Analyst recommendation consensus from DuckDB sentiment_features."""
    try:
        conn = _get_duckdb_conn()
        query = """
            SELECT DISTINCT ON (ticker) ticker, date, analyst_consensus, analyst_consensus_score,
                   analyst_action_detected, analyst_firm, analyst_action_type
            FROM sentiment_features
            WHERE date = (SELECT MAX(date) FROM sentiment_features)
              AND analyst_consensus IS NOT NULL
        """
        if ticker:
            query += f" AND ticker = '{ticker}'"
        query += " ORDER BY analyst_consensus_score DESC"
        df = conn.execute(query).fetchdf()

        if df.empty:
            return {"recommendations": [], "count": 0}

        recs = []
        for _, row in df.iterrows():
            recs.append({
                "ticker": str(row["ticker"]),
                "date": str(row["date"]),
                "analyst_consensus": str(row.get("analyst_consensus", "")),
                "score": round(_safe_float(row.get("analyst_consensus_score")), 4),
                "analyst_action_detected": bool(row.get("analyst_action_detected")) if row.get("analyst_action_detected") is not None and not pd.isna(row.get("analyst_action_detected")) else False,
                "analyst_firm": str(row.get("analyst_firm", "")) if row.get("analyst_firm") is not None and not pd.isna(row.get("analyst_firm")) else None,
                "analyst_action_type": str(row.get("analyst_action_type", "")) if row.get("analyst_action_type") is not None and not pd.isna(row.get("analyst_action_type")) else None,
            })
        return {"recommendations": recs, "count": len(recs)}
    except Exception:
        return {"recommendations": [], "count": 0}


@router.get("/insiders")
@cached_response(ttl=120)
def insider_transactions(ticker: Optional[str] = None, limit: int = 50):
    """Insider activity from DuckDB sentiment_features."""
    try:
        conn = _get_duckdb_conn()
        query = """
            SELECT DISTINCT ON (ticker) ticker, date, insider_signal, insider_cluster_flag,
                   insider_net_30d, insider_buy_count_30d
            FROM sentiment_features
            WHERE date = (SELECT MAX(date) FROM sentiment_features)
              AND insider_buy_count_30d > 0
        """
        if ticker:
            query += f" AND ticker = '{ticker}'"
        query += " ORDER BY ABS(insider_net_30d) DESC"
        query += f" LIMIT {min(limit, 200)}"
        df = conn.execute(query).fetchdf()

        if df.empty:
            return {"transactions": [], "count": 0}

        txns = []
        signals = {}
        for _, row in df.iterrows():
            net_val = _safe_float(row.get("insider_net_30d"))
            tk = str(row["ticker"])
            txns.append({
                "date": str(row["date"]),
                "ticker": tk,
                "insider": "Multiple insiders",
                "type": "BUY" if net_val > 0 else "SELL",
                "shares": int(abs(_safe_float(row.get("insider_buy_count_30d")))),
                "price": 0.0,
                "value": round(abs(net_val), 2),
            })
            signals[tk] = {
                "insider_cluster_flag": bool(row.get("insider_cluster_flag")) if row.get("insider_cluster_flag") is not None and not pd.isna(row.get("insider_cluster_flag")) else False,
                "insider_tx_count_30d": int(_safe_float(row.get("insider_buy_count_30d"))),
                "insider_unique_30d": int(_safe_float(row.get("insider_buy_count_30d"))),
                "insider_value_30d": round(net_val, 2),
            }
        return {"transactions": txns, "signals": signals, "count": len(txns)}
    except Exception:
        return {"transactions": [], "count": 0}


@router.get("/earnings")
@cached_response(ttl=120)
def earnings_surprises(ticker: Optional[str] = None):
    """Earnings data from DuckDB sentiment_features."""
    try:
        conn = _get_duckdb_conn()
        query = """
            SELECT ticker, date, earnings_date, earnings_days_to,
                   eps_surprise_pct, earnings_season_flag, report_hour
            FROM sentiment_features
            WHERE date = (SELECT MAX(date) FROM sentiment_features)
              AND earnings_date IS NOT NULL
        """
        if ticker:
            query += f" AND ticker = '{ticker}'"
        query += " ORDER BY earnings_days_to ASC NULLS LAST"
        df = conn.execute(query).fetchdf()

        if df.empty:
            return {"earnings": [], "count": 0}

        # Deduplicate (multiple runs per day)
        df = df.drop_duplicates(subset=["ticker"], keep="first")

        earnings = []
        for _, row in df.iterrows():
            surprise = _safe_float(row.get("eps_surprise_pct"))
            earnings.append({
                "date": str(row["date"]),
                "ticker": str(row["ticker"]),
                "earnings_date": str(row.get("earnings_date", "")) if row.get("earnings_date") is not None and not pd.isna(row.get("earnings_date")) else None,
                "earnings_days_to": round(_safe_float(row.get("earnings_days_to")), 1) if row.get("earnings_days_to") is not None and not pd.isna(row.get("earnings_days_to")) else None,
                "eps_surprise_pct": round(surprise, 4) if surprise != 0 else None,
                "beat": bool(surprise > 0) if surprise != 0 else None,
                "earnings_season_flag": str(row.get("earnings_season_flag", "")) if row.get("earnings_season_flag") is not None and not pd.isna(row.get("earnings_season_flag")) else None,
                "report_hour": str(row.get("report_hour", "")) if row.get("report_hour") is not None and not pd.isna(row.get("report_hour")) else None,
            })
        return {"earnings": earnings, "count": len(earnings)}
    except Exception:
        return {"earnings": [], "count": 0}


# ---------------------------------------------------------------------------
# Trigger layer
# ---------------------------------------------------------------------------

@router.get("/trigger/log")
@cached_response(ttl=60)
def trigger_log(days: int = Query(30, ge=1, le=365)):
    """Return recent trigger evaluations from DuckDB trigger_log table."""
    try:
        conn = _get_duckdb_conn()
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = conn.execute(
            "SELECT * FROM trigger_log WHERE evaluated_at >= ? ORDER BY evaluated_at DESC",
            [cutoff],
        ).fetchdf()

        if not df.empty:
            import math
            records = df.to_dict("records")
            for rec in records:
                for k, v in list(rec.items()):
                    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                        rec[k] = None
            return {"evaluations": records, "count": len(records), "stats": {}}
    except Exception:
        pass

    # Fallback to CSV logger
    try:
        from src.trigger.trigger_logger import TriggerLogger
        tlog = TriggerLogger()
        stats = tlog.compute_trigger_stats(days=days)
        df = tlog.load_log()
        if df.empty:
            return {"evaluations": [], "stats": stats, "count": 0}
        df["eval_date"] = pd.to_datetime(df["eval_date"], format="mixed")
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
        df = df[df["eval_date"] >= cutoff].copy()
        df["eval_date"] = df["eval_date"].dt.strftime("%Y-%m-%d")
        for col in ["composite_score", "conviction", "breadth", "regime_multiplier"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        records = df.sort_values("eval_date", ascending=False).to_dict("records")
        import math
        for rec in records:
            for k, v in list(rec.items()):
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    rec[k] = None
        return {"evaluations": records, "stats": stats, "count": len(records)}
    except Exception as e:
        return {"evaluations": [], "stats": {}, "count": 0, "error": str(e)}


@router.get("/trigger")
@cached_response(ttl=120)
def trigger_status():
    """Current sentiment trigger layer status and evaluations."""
    try:
        from src.trigger.sentiment_trigger import SentimentTriggerLayer
        trigger = SentimentTriggerLayer()
        if not trigger.config.enabled:
            return {"enabled": False, "evaluations": []}
        sentiment_data = trigger._load_sentiment_data()
        tickers = _get_all_tickers()
        mock_signals = pd.DataFrame({
            "ticker": list(tickers),
            "prediction": [0.5] * len(tickers),
            "rank": list(range(1, len(tickers) + 1)),
            "action": ["BUY"] * len(tickers),
        })
        results = trigger.evaluate(mock_signals)
        evaluations = []
        for ticker, result in sorted(results.items()):
            evaluations.append({
                "ticker": ticker,
                "signal": result.signal.value,
                "composite_score": round(result.composite_score, 4) if result.composite_score else None,
                "conviction": round(result.adjusted_conviction, 4) if result.adjusted_conviction else None,
                "breadth": round(result.signal_breadth, 4) if result.signal_breadth else None,
                "regime": result.market_regime,
                "regime_multiplier": result.regime_multiplier,
                "insider_cluster": result.insider_cluster,
                "reasons": result.reasons,
            })
        return {"enabled": True, "count": len(evaluations), "evaluations": evaluations}
    except Exception as e:
        return {"enabled": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Full overview, Deep Analysis, Crawl Health — new endpoints
# ---------------------------------------------------------------------------

def _non_null_dict(pairs):
    """Build dict excluding None/NaN values."""
    out = {}
    for k, v in pairs:
        if v is None:
            continue
        if isinstance(v, float) and pd.isna(v):
            continue
        out[k] = v
    return out


def _safe_bool(v):
    """Convert a value to bool, handling pandas NA."""
    try:
        if v is None or pd.isna(v):
            return None
    except (ValueError, TypeError):
        pass
    return bool(v)







@router.get("/overview/full/{ticker}")
def sentiment_overview_full(ticker: str):
    """Full sentiment feature set for a single ticker (latest date), grouped by category."""
    conn = _get_duckdb_conn()
    try:
        row_df = conn.execute(
            "SELECT * FROM sentiment_features "
            "WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            [ticker.upper()],
        ).fetchdf()

        if row_df.empty:
            return {"error": f"No data for {ticker.upper()}", "ticker": ticker.upper()}

        r = row_df.iloc[0]

        # Deep analysis check
        da_df = conn.execute(
            "SELECT trigger_reason FROM deep_analysis "
            "WHERE ticker = ? ORDER BY date DESC LIMIT 1",
            [ticker.upper()],
        ).fetchdf()
        has_deep = not da_df.empty
        da_trigger = str(da_df.iloc[0]["trigger_reason"]) if has_deep and pd.notna(da_df.iloc[0]["trigger_reason"]) else None
    finally:
        pass
    # Moby picks from CSV
    moby_data = None
    try:
        moby_csv = _read_csv("moby_analysis.csv")
        if not moby_csv.empty:
            moby_tk = moby_csv[moby_csv["ticker"] == ticker.upper()].sort_values("date", ascending=False)
            if not moby_tk.empty:
                mr = moby_tk.iloc[0]
                moby_data = _non_null_dict([
                    ("rating", mr.get("rating") if pd.notna(mr.get("rating")) else None),
                    ("price_target", _safe_float(mr.get("price_target")) if pd.notna(mr.get("price_target")) else None),
                    ("upside_pct", _safe_float(mr.get("upside_pct")) if pd.notna(mr.get("upside_pct")) else None),
                    ("article_title", str(mr.get("article_title")) if pd.notna(mr.get("article_title")) else None),
                    ("thesis_summary", str(mr.get("thesis_summary")) if "thesis_summary" in mr.index and pd.notna(mr.get("thesis_summary")) else None),
                ])
                if not moby_data:
                    moby_data = None
    except Exception:
        pass

    result = {
        "ticker": ticker.upper(),
        "date": str(r["date"]),
        "crawled_at": str(r["crawled_at"]) if pd.notna(r.get("crawled_at")) else None,
        "core": _non_null_dict([
            ("composite_score", round(_safe_float(r.get("composite_score")), 4)),
            ("signal_breadth", round(_safe_float(r.get("signal_breadth")), 4)),
            ("signal_conviction", round(_safe_float(r.get("signal_conviction")), 4)),
            ("sentiment_regime", str(r.get("sentiment_regime")) if pd.notna(r.get("sentiment_regime")) else None),
            ("market_regime", str(r.get("market_regime")) if pd.notna(r.get("market_regime")) else None),
            ("market_vix", round(_safe_float(r.get("market_vix")), 2) if pd.notna(r.get("market_vix")) else None),
            ("confidence", str(r.get("confidence")) if pd.notna(r.get("confidence")) else None),
        ]),
        "sources": _non_null_dict([
            ("llm_score", round(_safe_float(r.get("llm_score")), 4) if pd.notna(r.get("llm_score")) else None),
            ("finnhub_score", round(_safe_float(r.get("finnhub_score")), 4) if pd.notna(r.get("finnhub_score")) else None),
            ("eodhd_score", round(_safe_float(r.get("eodhd_score")), 4) if pd.notna(r.get("eodhd_score")) else None),
            ("av_score", round(_safe_float(r.get("av_score")), 4) if pd.notna(r.get("av_score")) else None),
            ("massive_score", round(_safe_float(r.get("massive_score")), 4) if pd.notna(r.get("massive_score")) else None),
            ("marketaux_score", round(_safe_float(r.get("marketaux_score")), 4) if pd.notna(r.get("marketaux_score")) else None),
            ("fmp_social_score", round(_safe_float(r.get("fmp_social_score")), 4) if pd.notna(r.get("fmp_social_score")) else None),
            ("finnhub_social_score", round(_safe_float(r.get("finnhub_social_score")), 4) if pd.notna(r.get("finnhub_social_score")) else None),
        ]),
        "social": _non_null_dict([
            ("stocktwits_bullish_pct", round(_safe_float(r.get("stocktwits_bullish_pct")), 2) if pd.notna(r.get("stocktwits_bullish_pct")) else None),
            ("stocktwits_message_volume", int(_safe_float(r.get("stocktwits_message_volume"))) if pd.notna(r.get("stocktwits_message_volume")) else None),
            ("apewisdom_mentions", int(_safe_float(r.get("apewisdom_mentions"))) if pd.notna(r.get("apewisdom_mentions")) else None),
            ("apewisdom_rank", int(_safe_float(r.get("apewisdom_rank"))) if pd.notna(r.get("apewisdom_rank")) else None),
            ("apewisdom_rank_change", int(_safe_float(r.get("apewisdom_rank_change"))) if pd.notna(r.get("apewisdom_rank_change")) else None),
            ("apewisdom_spike_flag", _safe_bool(r.get("apewisdom_spike_flag"))),
            ("x_social_score", round(_safe_float(r.get("x_social_score")), 4) if pd.notna(r.get("x_social_score")) else None),
            ("x_post_count_24h", int(_safe_float(r.get("x_post_count_24h"))) if pd.notna(r.get("x_post_count_24h")) else None),
        ]),
        "insider": _non_null_dict([
            ("insider_cluster_flag", _safe_bool(r.get("insider_cluster_flag"))),
            ("insider_net_30d", round(_safe_float(r.get("insider_net_30d")), 2) if pd.notna(r.get("insider_net_30d")) else None),
            ("insider_buy_count_30d", int(_safe_float(r.get("insider_buy_count_30d"))) if pd.notna(r.get("insider_buy_count_30d")) else None),
            ("insider_signal", round(_safe_float(r.get("insider_signal")), 4) if pd.notna(r.get("insider_signal")) else None),
        ]),
        "quality": _non_null_dict([
            ("source_agreement", round(_safe_float(r.get("source_agreement")), 4) if pd.notna(r.get("source_agreement")) else None),
            ("conviction_asymmetry", round(_safe_float(r.get("conviction_asymmetry")), 4) if pd.notna(r.get("conviction_asymmetry")) else None),
            ("organic_score", round(_safe_float(r.get("organic_score")), 4) if pd.notna(r.get("organic_score")) else None),
            ("has_primary_source", _safe_bool(r.get("has_primary_source"))),
            ("propagation_flag", _safe_bool(r.get("propagation_flag"))),
            ("propagation_source", str(r.get("propagation_source")) if pd.notna(r.get("propagation_source")) else None),
        ]),
        "divergence": _non_null_dict([
            ("price_return_5d", round(_safe_float(r.get("price_return_5d")), 4) if pd.notna(r.get("price_return_5d")) else None),
            ("price_divergence", _safe_bool(r.get("price_divergence"))),
            ("divergence_direction", str(r.get("divergence_direction")) if pd.notna(r.get("divergence_direction")) else None),
        ]),
        "events": _non_null_dict([
            ("forward_event_detected", _safe_bool(r.get("forward_event_detected"))),
            ("forward_event_type", str(r.get("forward_event_type")) if pd.notna(r.get("forward_event_type")) else None),
            ("forward_event_date", str(r.get("forward_event_date")) if pd.notna(r.get("forward_event_date")) else None),
            ("earnings_days_to", round(_safe_float(r.get("earnings_days_to")), 0) if pd.notna(r.get("earnings_days_to")) else None),
            ("earnings_season_flag", str(r.get("earnings_season_flag")) if pd.notna(r.get("earnings_season_flag")) else None),
            ("eps_surprise_pct", round(_safe_float(r.get("eps_surprise_pct")), 2) if pd.notna(r.get("eps_surprise_pct")) else None),
        ]),
        "analyst": _non_null_dict([
            ("analyst_action_detected", _safe_bool(r.get("analyst_action_detected"))),
            ("analyst_firm", str(r.get("analyst_firm")) if pd.notna(r.get("analyst_firm")) else None),
            ("analyst_action_type", str(r.get("analyst_action_type")) if pd.notna(r.get("analyst_action_type")) else None),
            ("analyst_consensus", str(r.get("analyst_consensus")) if pd.notna(r.get("analyst_consensus")) else None),
            ("analyst_consensus_score", round(_safe_float(r.get("analyst_consensus_score")), 4) if pd.notna(r.get("analyst_consensus_score")) else None),
        ]),
        "trends": _non_null_dict([
            ("trends_interest_7d", round(_safe_float(r.get("trends_interest_7d")), 2) if pd.notna(r.get("trends_interest_7d")) else None),
            ("trends_interest_30d", round(_safe_float(r.get("trends_interest_30d")), 2) if pd.notna(r.get("trends_interest_30d")) else None),
            ("trends_7d_change", round(_safe_float(r.get("trends_7d_change")), 2) if pd.notna(r.get("trends_7d_change")) else None),
            ("trends_spike_flag", _safe_bool(r.get("trends_spike_flag"))),
        ]),
        "has_deep_analysis": has_deep,
        "deep_analysis_trigger": da_trigger,
        "moby": moby_data,
    }

    # Options: only include if options_data_available
    if _safe_bool(r.get("options_data_available")):
        result["options"] = _non_null_dict([
            ("pcr", round(_safe_float(r.get("options_pcr")), 4) if pd.notna(r.get("options_pcr")) else None),
            ("iv_percentile", round(_safe_float(r.get("iv_percentile")), 2) if pd.notna(r.get("iv_percentile")) else None),
            ("iv_skew", round(_safe_float(r.get("iv_skew")), 4) if pd.notna(r.get("iv_skew")) else None),
            ("iv_current", round(_safe_float(r.get("iv_current")), 4) if pd.notna(r.get("iv_current")) else None),
            ("unusual_options_flag", _safe_bool(r.get("unusual_options_flag"))),
            ("unusual_options_direction", str(r.get("unusual_options_direction")) if pd.notna(r.get("unusual_options_direction")) else None),
            ("options_sentiment_signal", round(_safe_float(r.get("options_sentiment_signal")), 4) if pd.notna(r.get("options_sentiment_signal")) else None),
            ("dark_pool_volume", int(_safe_float(r.get("dark_pool_volume"))) if pd.notna(r.get("dark_pool_volume")) else None),
        ])

    return result


@router.get("/deep-analysis/recent")
@cached_response(ttl=120)
def deep_analysis_recent(limit: int = Query(20, ge=1, le=100)):
    """Most recent deep analysis entries (HTML truncated for list view)."""
    conn = _get_duckdb_conn()
    try:
        df = conn.execute(
            "SELECT ticker, date, trigger_reason, composite_score, sentiment_regime, "
            "headline_count, LEFT(html_content, 500) AS html_preview "
            "FROM deep_analysis ORDER BY date DESC LIMIT ?",
            [limit],
        ).fetchdf()
    finally:
        pass
    if df.empty:
        return {"analyses": [], "count": 0}

    records = []
    for _, row in df.iterrows():
        records.append({
            "ticker": row["ticker"],
            "date": str(row["date"]),
            "trigger_reason": str(row["trigger_reason"]) if pd.notna(row.get("trigger_reason")) else None,
            "composite_score": round(_safe_float(row.get("composite_score")), 4) if pd.notna(row.get("composite_score")) else None,
            "sentiment_regime": str(row.get("sentiment_regime")) if pd.notna(row.get("sentiment_regime")) else None,
            "article_count": int(_safe_float(row.get("headline_count", 0))),
            "html_preview": str(row.get("html_preview", "")) if pd.notna(row.get("html_preview")) else "",
        })
    return {"analyses": records, "count": len(records)}


@router.get("/deep-analysis/{ticker}")
def deep_analysis_detail(ticker: str, date: Optional[str] = Query(None)):
    """Full Gemini Pro HTML deep analysis for a ticker."""
    conn = _get_duckdb_conn()
    try:
        if date:
            df = conn.execute(
                "SELECT * FROM deep_analysis WHERE ticker = ? AND date = ? LIMIT 1",
                [ticker.upper(), date],
            ).fetchdf()
        else:
            df = conn.execute(
                "SELECT * FROM deep_analysis WHERE ticker = ? ORDER BY date DESC LIMIT 1",
                [ticker.upper()],
            ).fetchdf()
    finally:
        pass
    if df.empty:
        return {"error": f"No deep analysis found for {ticker.upper()}", "ticker": ticker.upper()}

    row = df.iloc[0]
    return {
        "ticker": ticker.upper(),
        "date": str(row["date"]),
        "analysis_html": str(row.get("html_content", "")) if pd.notna(row.get("html_content")) else "",
        "trigger_reason": str(row.get("trigger_reason")) if pd.notna(row.get("trigger_reason")) else None,
        "composite_score": round(_safe_float(row.get("composite_score")), 4) if pd.notna(row.get("composite_score")) else None,
        "sentiment_regime": str(row.get("sentiment_regime")) if pd.notna(row.get("sentiment_regime")) else None,
        "article_count": int(_safe_float(row.get("headline_count", 0))),
    }


@router.get("/crawl-health")
@cached_response(ttl=60)
def crawl_health():
    """Last 5 crawl runs for health monitoring."""
    conn = _get_duckdb_conn()
    try:
        df = conn.execute(
            "SELECT run_id, started_at, duration_s, tickers_scored, articles_total, "
            "scoring_failures, market_regime, market_vix "
            "FROM crawl_runs ORDER BY started_at DESC LIMIT 5"
        ).fetchdf()
    finally:
        pass
    if df.empty:
        return {"runs": [], "count": 0}

    records = []
    for _, row in df.iterrows():
        records.append({
            "run_id": str(row["run_id"]) if pd.notna(row.get("run_id")) else None,
            "started_at": str(row["started_at"]) if pd.notna(row.get("started_at")) else None,
            "duration_s": round(_safe_float(row.get("duration_s")), 1) if pd.notna(row.get("duration_s")) else None,
            "tickers_scored": int(_safe_float(row.get("tickers_scored", 0))),
            "articles_total": int(_safe_float(row.get("articles_total", 0))),
            "scoring_failures": int(_safe_float(row.get("scoring_failures", 0))),
            "market_regime": str(row.get("market_regime")) if pd.notna(row.get("market_regime")) else None,
            "market_vix": round(_safe_float(row.get("market_vix")), 2) if pd.notna(row.get("market_vix")) else None,
        })
    return {"runs": records, "count": len(records)}


# ---------------------------------------------------------------------------
# Google Trends push endpoint — receives data from Mac local fetcher
# ---------------------------------------------------------------------------

TRENDS_API_TOKEN = os.environ.get("TRENDS_API_TOKEN", "")


class TrendsUpdatePayload(BaseModel):
    data: Dict[str, Dict[str, Any]]   # ticker -> trends dict
    fetched_at: str
    ticker_count: int
    spike_count: int = 0


class TrendsUpdateResponse(BaseModel):
    status: str
    updated_rows: int
    spike_count: int
    received_at: str


def _verify_trends_token(authorization: Optional[str]) -> None:
    """Verify Bearer token for trends-update endpoint."""
    if not TRENDS_API_TOKEN:
        return  # No token configured — allow (dev mode)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    if authorization.split(" ", 1)[1] != TRENDS_API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


@router.post("/trends-update", response_model=TrendsUpdateResponse)
async def update_trends(
    payload: TrendsUpdatePayload,
    authorization: Optional[str] = Header(None),
):
    """
    Receive Google Trends data from local Mac fetcher and update DuckDB.

    Updates the most recent sentiment_features row per ticker with the
    4 trends columns. Called by scripts/fetch_google_trends_local.py.
    """
    _verify_trends_token(authorization)

    import duckdb

    db_path = str(DUCKDB_PATH)
    updated = 0

    try:
        conn = duckdb.connect(db_path, config={"lock_timeout": 30_000})

        for ticker, trends in payload.data.items():
            # Only update rows with non-zero interest (don't overwrite with zeros)
            if trends.get("trends_interest_7d", 0) <= 0:
                continue

            conn.execute(
                """
                UPDATE sentiment_features
                SET trends_interest_7d  = ?,
                    trends_interest_30d = ?,
                    trends_7d_change    = ?,
                    trends_spike_flag   = ?
                WHERE ticker = ?
                  AND date = (
                      SELECT MAX(date) FROM sentiment_features
                      WHERE ticker = ?
                  )
                """,
                [
                    trends["trends_interest_7d"],
                    trends["trends_interest_30d"],
                    trends["trends_7d_change"],
                    bool(trends["trends_spike_flag"]),
                    ticker,
                    ticker,
                ],
            )

            rows_changed = conn.execute("SELECT changes()").fetchone()
            if rows_changed and rows_changed[0] > 0:
                updated += 1

        conn.commit()
        conn.close()

        spike_count = sum(
            1 for v in payload.data.values() if v.get("trends_spike_flag")
        )
        _trends_log.info(
            f"Trends update: {updated}/{payload.ticker_count} rows updated, "
            f"{spike_count} spikes"
        )

        return TrendsUpdateResponse(
            status="ok",
            updated_rows=updated,
            spike_count=spike_count,
            received_at=datetime.now().isoformat(),
        )

    except Exception as e:
        _trends_log.error(f"Trends update failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
