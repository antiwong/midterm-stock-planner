"""LLM commentary for forward testing results."""

import os
import time
import logging
from fastapi import APIRouter, Query
from typing import Optional
from ..db import cached_response, query_forward

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/forward", tags=["commentary"])

# Simple in-memory cache: key -> (timestamp, text)
_cache: dict[str, tuple[float, str]] = {}
CACHE_TTL = 3600 * 6  # 6 hours


def _call_llm(prompt: str) -> str:
    """Call Gemini (preferred) or OpenAI as fallback."""
    from src.config.api_keys import get_api_key

    # Try Gemini first (free tier)
    google_key = get_api_key("GOOGLE_API_KEY")
    if google_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=google_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            return response.text or "No commentary generated."
        except Exception as e:
            logger.warning(f"Gemini failed, falling back to OpenAI: {e}")

    # Fallback to OpenAI
    openai_key = get_api_key("OPENAI_API_KEY")
    if openai_key:
        import openai
        client = openai.OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.3,
        )
        return response.choices[0].message.content or "No commentary generated."

    raise RuntimeError("No LLM API key configured (GOOGLE_API_KEY or OPENAI_API_KEY)")


def _gather_stats(horizon: Optional[int] = None) -> dict:
    """Gather forward testing stats for the LLM prompt."""
    # Overall stats
    stats_rows = query_forward("""
        SELECT
            COUNT(*) as total_predictions,
            COUNT(CASE WHEN evaluated_at IS NOT NULL THEN 1 END) as evaluated,
            COUNT(CASE WHEN evaluated_at IS NULL AND maturity_date > date('now') THEN 1 END) as active
        FROM predictions
    """)
    stats = stats_rows[0] if stats_rows else {}

    # Hit rates by watchlist + horizon
    conds = ["evaluated_at IS NOT NULL", "predicted_action = 'BUY'"]
    params: list = []
    if horizon:
        conds.append("horizon_days = ?")
        params.append(horizon)
    where = " AND ".join(conds)

    by_wl = query_forward(f"""
        SELECT watchlist, horizon_days,
               COUNT(*) as total,
               SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits,
               ROUND(AVG(actual_return) * 100, 2) as avg_return_pct
        FROM predictions WHERE {where}
        GROUP BY watchlist, horizon_days
        ORDER BY watchlist, horizon_days
    """, params)

    # Top and bottom tickers (by hit rate, min 3 predictions)
    top_tickers = query_forward(f"""
        SELECT ticker, watchlist,
               COUNT(*) as total,
               SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits,
               ROUND(AVG(actual_return) * 100, 2) as avg_return_pct
        FROM predictions WHERE {where}
        GROUP BY ticker, watchlist
        HAVING COUNT(*) >= 3
        ORDER BY CAST(SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) AS REAL) / COUNT(*) DESC
        LIMIT 5
    """, params)

    bottom_tickers = query_forward(f"""
        SELECT ticker, watchlist,
               COUNT(*) as total,
               SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits,
               ROUND(AVG(actual_return) * 100, 2) as avg_return_pct
        FROM predictions WHERE {where}
        GROUP BY ticker, watchlist
        HAVING COUNT(*) >= 3
        ORDER BY CAST(SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) AS REAL) / COUNT(*) ASC
        LIMIT 5
    """, params)

    # Recent trend (last 5 prediction dates)
    trend = query_forward(f"""
        SELECT prediction_date,
               COUNT(*) as total,
               SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits
        FROM predictions WHERE {where}
        GROUP BY prediction_date
        ORDER BY prediction_date DESC
        LIMIT 5
    """, params)

    return {
        "stats": stats,
        "by_watchlist": by_wl,
        "top_tickers": top_tickers,
        "bottom_tickers": bottom_tickers,
        "recent_trend": list(reversed(trend)),
    }


def _build_prompt(data: dict) -> str:
    stats = data["stats"]
    by_wl = data["by_watchlist"]
    top = data["top_tickers"]
    bottom = data["bottom_tickers"]
    trend = data["recent_trend"]

    lines = [
        "You are an investment analyst reviewing forward testing results for a quantitative stock prediction model.",
        "The model predicts BUY/SELL signals for stocks across multiple watchlists (portfolios).",
        "Predictions are evaluated after a set horizon (5 or 63 days) to check if the predicted direction was correct (hit) or not (miss).",
        "",
        "Here are the current forward testing statistics:",
        "",
        f"Overall: {stats.get('total_predictions', 0)} total predictions, {stats.get('evaluated', 0)} evaluated, {stats.get('active', 0)} active",
        "",
        "Hit rates by portfolio:",
    ]

    for r in by_wl:
        hit_rate = (r["hits"] / r["total"] * 100) if r["total"] > 0 else 0
        lines.append(f"  - {r['watchlist']} ({r['horizon_days']}d): {r['hits']}/{r['total']} hits ({hit_rate:.1f}%), avg return {r['avg_return_pct']}%")

    lines.append("")
    lines.append("Top performing tickers (highest hit rate, min 3 predictions):")
    for t in top:
        hr = (t["hits"] / t["total"] * 100) if t["total"] > 0 else 0
        lines.append(f"  - {t['ticker']} ({t['watchlist']}): {t['hits']}/{t['total']} ({hr:.0f}%), avg return {t['avg_return_pct']}%")

    lines.append("")
    lines.append("Worst performing tickers:")
    for t in bottom:
        hr = (t["hits"] / t["total"] * 100) if t["total"] > 0 else 0
        lines.append(f"  - {t['ticker']} ({t['watchlist']}): {t['hits']}/{t['total']} ({hr:.0f}%), avg return {t['avg_return_pct']}%")

    lines.append("")
    lines.append("Recent trend (last 5 prediction dates):")
    for t in trend:
        hr = (t["hits"] / t["total"] * 100) if t["total"] > 0 else 0
        lines.append(f"  - {t['prediction_date']}: {t['hits']}/{t['total']} ({hr:.0f}%)")

    lines.append("")
    lines.append("Write a concise analyst commentary (3-5 short paragraphs) covering:")
    lines.append("1. Overall model performance and whether it's worth trusting")
    lines.append("2. Which portfolios are strongest/weakest and why that might be")
    lines.append("3. Notable ticker patterns (consistent winners or losers)")
    lines.append("4. Recent trend direction — is accuracy improving or declining?")
    lines.append("5. One actionable recommendation")
    lines.append("")
    lines.append("Be direct and specific. Use numbers. No fluff. Write like a Bloomberg terminal note.")

    return "\n".join(lines)


@router.get("/commentary")
@cached_response(ttl=300)
def get_commentary(
    horizon: Optional[int] = Query(None),
    regenerate: bool = Query(False),
):
    """LLM-generated commentary on forward testing results."""
    cache_key = f"commentary_{horizon or 'all'}"

    # Check cache
    if not regenerate and cache_key in _cache:
        ts, text = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return {"commentary": text, "cached": True}

    # Gather data
    data = _gather_stats(horizon)

    if not data["by_watchlist"]:
        return {"commentary": "No evaluated predictions yet. Commentary will be available once predictions have matured and been evaluated.", "cached": False}

    prompt = _build_prompt(data)

    try:
        text = _call_llm(prompt)
    except Exception as e:
        logger.error(f"LLM commentary failed: {e}")
        return {"commentary": f"Commentary generation failed: {str(e)}", "cached": False}

    # Cache it
    _cache[cache_key] = (time.time(), text)

    return {"commentary": text, "cached": False}
