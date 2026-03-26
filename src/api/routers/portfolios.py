"""Portfolio endpoints: summary, positions, trades, snapshots, signals."""

import math
import time
import logging
from fastapi import APIRouter, Query
from typing import Optional
from ..db import cached_response, get_paper_db, query_paper
from src.data.shared_db import get_active_watchlists

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolios", tags=["portfolios"])

# LLM commentary cache
_commentary_cache: dict[str, tuple[float, str]] = {}
_COMMENTARY_TTL = 3600 * 6  # 6 hours


def _call_llm(prompt: str) -> str:
    """Call Gemini (preferred) or OpenAI as fallback."""
    from src.config.api_keys import get_api_key

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


def _query_summary(conn):
    """Run all 3 summary queries on a single open connection."""
    state = [dict(r) for r in conn.execute(
        "SELECT * FROM portfolio_state WHERE id = 1"
    ).fetchall()]
    snap = [dict(r) for r in conn.execute(
        "SELECT portfolio_value, cash, daily_return, cumulative_return, "
        "benchmark_cumulative FROM daily_snapshots ORDER BY date DESC LIMIT 1"
    ).fetchall()]
    pos_count = [dict(r) for r in conn.execute(
        "SELECT COUNT(*) as cnt FROM positions WHERE is_active = 1"
    ).fetchall()]
    return state, snap, pos_count


def _compute_risk_metrics(conn) -> dict:
    """Compute sharpe_ratio, max_drawdown, win_rate from last 30 snapshots."""
    rows = conn.execute(
        "SELECT daily_return FROM daily_snapshots ORDER BY date DESC LIMIT 30"
    ).fetchall()
    daily_returns = [r["daily_return"] for r in rows if r["daily_return"] is not None]
    n = len(daily_returns)

    if n < 2:
        return {"sharpe_ratio": None, "max_drawdown": 0, "win_rate": 0}

    mean_r = sum(daily_returns) / n
    var_r = sum((r - mean_r) ** 2 for r in daily_returns) / (n - 1)
    std_r = math.sqrt(var_r)

    # Sharpe (annualized)
    sharpe_ratio = (mean_r / std_r) * math.sqrt(252) if std_r > 0 else None

    # Max drawdown from cumulative returns (chronological order)
    daily_returns.reverse()
    cum = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in daily_returns:
        cum *= 1 + r
        if cum > peak:
            peak = cum
        dd = (cum / peak) - 1
        if dd < max_dd:
            max_dd = dd

    # Win rate
    wins = [r for r in daily_returns if r > 0]
    win_rate = len(wins) / n

    return {
        "sharpe_ratio": round(sharpe_ratio, 2) if sharpe_ratio is not None else None,
        "max_drawdown": round(max_dd, 4),
        "win_rate": round(win_rate, 4),
    }


@router.get("/summary")
@cached_response(ttl=60)
def get_summary():
    """Overview of all 4 portfolios."""
    portfolios = []
    for wl in get_active_watchlists():
        conn = get_paper_db(wl)
        if conn is None:
            portfolios.append({
                "watchlist": wl, "portfolio_value": 0, "cash": 0,
                "initial_value": 0, "cumulative_return": 0, "daily_return": 0,
                "benchmark_cumulative": 0, "positions_count": 0,
                "last_updated": None, "mode": "no_data",
            })
            continue
        try:
            state, snap, pos_count = _query_summary(conn)
            risk = _compute_risk_metrics(conn)
        finally:
            conn.close()

        if state:
            s = state[0]
            sn = snap[0] if snap else {}
            portfolios.append({
                "watchlist": wl,
                "portfolio_value": sn.get("portfolio_value", s.get("initial_value", 100000)),
                "cash": sn.get("cash", s.get("cash", 0)),
                "initial_value": s.get("initial_value", 100000),
                "cumulative_return": sn.get("cumulative_return", 0),
                "daily_return": sn.get("daily_return", 0),
                "benchmark_cumulative": sn.get("benchmark_cumulative", 0),
                "positions_count": pos_count[0]["cnt"] if pos_count else 0,
                "last_updated": s.get("last_updated"),
                "mode": "alpaca" if wl == "moby_picks" else "local",
                "sharpe_ratio": risk["sharpe_ratio"],
                "max_drawdown": risk["max_drawdown"],
                "win_rate": risk["win_rate"],
            })
        else:
            portfolios.append({"watchlist": wl, "portfolio_value": 0, "mode": "no_data"})

    return {"portfolios": portfolios}


@router.get("/{watchlist}/positions")
@cached_response(ttl=60)
def get_positions(watchlist: str):
    """Active positions for one portfolio."""
    rows = query_paper(
        watchlist,
        "SELECT ticker, shares, entry_price, entry_date, weight, is_active, "
        "exit_date, exit_price, realized_pnl "
        "FROM positions WHERE is_active = 1 ORDER BY weight DESC",
    )
    return {"positions": rows}


@router.get("/{watchlist}/trades")
@cached_response(ttl=60)
def get_trades(
    watchlist: str,
    limit: int = Query(50, le=500),
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
):
    """Trade history, optionally filtered by date."""
    if date:
        rows = query_paper(
            watchlist,
            "SELECT date, ticker, action, shares, price, value, cost "
            "FROM trades WHERE date LIKE ? ORDER BY date DESC, id DESC",
            (f"{date}%",),
        )
    else:
        rows = query_paper(
            watchlist,
            "SELECT date, ticker, action, shares, price, value, cost "
            "FROM trades ORDER BY date DESC, id DESC LIMIT ?",
            (limit,),
        )
    return {"trades": rows}


@router.get("/{watchlist}/snapshots")
@cached_response(ttl=60)
def get_snapshots(watchlist: str, days: int = Query(90, le=3650)):
    """Daily snapshots for equity curve."""
    rows = query_paper(
        watchlist,
        "SELECT date, portfolio_value, cash, invested, daily_return, "
        "cumulative_return, benchmark_return, benchmark_cumulative "
        "FROM daily_snapshots ORDER BY date DESC LIMIT ?",
        (days,),
    )
    rows.reverse()  # Chronological order
    return {"snapshots": rows}


@router.get("/{watchlist}/signals")
@cached_response(ttl=60)
def get_signals(watchlist: str, date: Optional[str] = Query(None)):
    """Signals for a given date (default: latest)."""
    if date:
        rows = query_paper(
            watchlist,
            "SELECT date, ticker, prediction, rank, percentile, action "
            "FROM signals WHERE date = ? ORDER BY rank",
            (date,),
        )
    else:
        rows = query_paper(
            watchlist,
            "SELECT date, ticker, prediction, rank, percentile, action "
            "FROM signals WHERE date = (SELECT MAX(date) FROM signals) ORDER BY rank",
        )
    return {"signals": rows}


@router.get("/commentary")
@cached_response(ttl=60)
def get_portfolio_commentary(regenerate: bool = Query(False)):
    """LLM-generated commentary on overall portfolio health."""
    cache_key = "portfolio_commentary"

    if not regenerate and cache_key in _commentary_cache:
        ts, text = _commentary_cache[cache_key]
        if time.time() - ts < _COMMENTARY_TTL:
            return {"commentary": text, "cached": True}

    # Gather portfolio summary data
    portfolios = []
    for wl in get_active_watchlists():
        conn = get_paper_db(wl)
        if conn is None:
            continue
        try:
            state, snap, pos_count = _query_summary(conn)
        finally:
            conn.close()

        if state:
            s = state[0]
            sn = snap[0] if snap else {}
            portfolios.append({
                "watchlist": wl,
                "portfolio_value": sn.get("portfolio_value", s.get("initial_value", 100000)),
                "initial_value": s.get("initial_value", 100000),
                "cumulative_return": sn.get("cumulative_return", 0),
                "daily_return": sn.get("daily_return", 0),
                "benchmark_cumulative": sn.get("benchmark_cumulative", 0),
                "positions_count": pos_count[0]["cnt"] if pos_count else 0,
            })

    if not portfolios:
        return {"commentary": "No portfolio data available yet.", "cached": False}

    # Build prompt
    total_value = sum(p["portfolio_value"] for p in portfolios)
    lines = [
        "You are an investment portfolio analyst reviewing a multi-portfolio trading system.",
        "The system runs paper-trading across several watchlists. Here is the current state:",
        "",
    ]
    for p in portfolios:
        cum_ret = p["cumulative_return"] or 0
        bench_cum = p.get("benchmark_cumulative") or 0
        daily_ret = p.get("daily_return") or 0
        alpha = cum_ret - bench_cum
        lines.append(
            f"- {p['watchlist']}: ${p['portfolio_value']:,.0f} "
            f"(initial ${p['initial_value']:,.0f}), "
            f"return {cum_ret * 100:+.2f}%, "
            f"daily {daily_ret * 100:+.2f}%, "
            f"vs benchmark {bench_cum * 100:+.2f}% "
            f"(alpha {alpha * 100:+.2f}%), "
            f"{p['positions_count']} active positions"
        )

    lines.append(f"\nTotal portfolio value: ${total_value:,.0f}")
    lines.append("")
    lines.append("Write a concise portfolio health assessment (3-4 short paragraphs) covering:")
    lines.append("1. Overall portfolio performance — are we beating the benchmark?")
    lines.append("2. Which portfolios are strongest/weakest and concentration risk")
    lines.append("3. Risk observations (drawdown, position count, diversification)")
    lines.append("4. One actionable recommendation for rebalancing or risk management")
    lines.append("")
    lines.append("Be direct and specific. Use numbers. No fluff. Write like a Bloomberg terminal note.")

    prompt = "\n".join(lines)

    try:
        text = _call_llm(prompt)
    except Exception as e:
        logger.error(f"Portfolio commentary failed: {e}")
        return {"commentary": f"Commentary generation failed: {str(e)}", "cached": False}

    _commentary_cache[cache_key] = (time.time(), text)
    return {"commentary": text, "cached": False}
