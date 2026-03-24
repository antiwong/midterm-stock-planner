from src.api.db import cached_response
"""Real-time signal tracker — live positions, forward predictions, and buy/sell triggers."""

from fastapi import APIRouter, Query
from typing import Optional

from src.data.shared_db import get_active_watchlists, query_paper, query_forward, get_forward_db, get_prices

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/live")
@cached_response(ttl=60)
def live_dashboard():
    """Aggregated live dashboard: positions, latest signals, and active predictions across all watchlists."""
    result = {
        "watchlists": {},
        "trigger_summary": {"buy": 0, "sell": 0, "hold": 0},
    }

    for wl in get_active_watchlists():
        # Active positions
        positions = query_paper(wl, """
            SELECT ticker, shares, entry_price, entry_date, weight
            FROM positions WHERE is_active = 1
            ORDER BY weight DESC
        """)

        # Latest signals
        signals = query_paper(wl, """
            SELECT date, ticker, action, prediction, rank, percentile
            FROM signals
            WHERE date = (SELECT MAX(date) FROM signals)
            ORDER BY rank
        """)

        # Portfolio snapshot
        snap = query_paper(wl, """
            SELECT date, portfolio_value, cash, daily_return, cumulative_return,
                   benchmark_return, benchmark_cumulative
            FROM daily_snapshots ORDER BY date DESC LIMIT 1
        """)

        # Recent trades (last 5)
        recent_trades = query_paper(wl, """
            SELECT date, ticker, action, shares, price, value
            FROM trades ORDER BY date DESC, id DESC LIMIT 5
        """)

        # Count buy/sell signals
        buys = sum(1 for s in signals if s.get("action") == "BUY")
        sells = sum(1 for s in signals if s.get("action") == "SELL")
        result["trigger_summary"]["buy"] += buys
        result["trigger_summary"]["sell"] += sells
        result["trigger_summary"]["hold"] += len(signals) - buys - sells

        result["watchlists"][wl] = {
            "positions": positions,
            "positions_count": len(positions),
            "signals": signals[:10],  # Top 10 only
            "signals_count": len(signals),
            "snapshot": snap[0] if snap else None,
            "recent_trades": recent_trades,
            "buy_signals": buys,
            "sell_signals": sells,
        }

    return result


@router.get("/predictions/active")
@cached_response(ttl=60)
def active_predictions(watchlist: Optional[str] = None, horizon: Optional[int] = None):
    """Active forward predictions (not yet evaluated)."""
    sql = """
        SELECT prediction_date, maturity_date, ticker, watchlist, horizon_days,
               predicted_score, predicted_rank, predicted_action, entry_price
        FROM predictions
        WHERE evaluated_at IS NULL
    """
    params = []
    if watchlist:
        sql += " AND watchlist = ?"
        params.append(watchlist)
    if horizon:
        sql += " AND horizon_days = ?"
        params.append(horizon)
    sql += " ORDER BY prediction_date DESC, predicted_rank ASC LIMIT 200"

    predictions = query_forward(sql, tuple(params))
    return {"predictions": predictions, "count": len(predictions)}


@router.get("/predictions/maturing")
@cached_response(ttl=60)
def maturing_soon(days: int = 3):
    """Predictions maturing within N days — these are actionable triggers."""
    predictions = query_forward("""
        SELECT prediction_date, maturity_date, ticker, watchlist, horizon_days,
               predicted_score, predicted_rank, predicted_action, entry_price
        FROM predictions
        WHERE evaluated_at IS NULL
          AND julianday(maturity_date) - julianday('now') BETWEEN 0 AND ?
        ORDER BY maturity_date ASC, predicted_rank ASC
    """, (days,))
    return {"predictions": predictions, "count": len(predictions), "within_days": days}


@router.get("/triggers")
@cached_response(ttl=60)
def current_triggers(watchlist: Optional[str] = Query(None)):
    """Current buy/sell trigger signals across watchlists.

    Combines latest model signals with forward prediction strength.
    """
    triggers = []
    target_watchlists = [watchlist] if watchlist else get_active_watchlists()

    # Pre-load all active forward predictions in one query, keyed by (ticker, watchlist)
    fwd_by_key: dict = {}
    fwd_conn = get_forward_db()
    if fwd_conn is not None:
        try:
            fwd_rows = fwd_conn.execute("""
                SELECT ticker, watchlist, predicted_action, predicted_rank,
                       predicted_score, maturity_date, prediction_date
                FROM predictions
                WHERE evaluated_at IS NULL
                ORDER BY prediction_date DESC
            """).fetchall()
            for r in fwd_rows:
                row = dict(r)
                key = (row["ticker"], row["watchlist"])
                if key not in fwd_by_key:
                    fwd_by_key[key] = row  # keep only the latest per (ticker, watchlist)
        finally:
            fwd_conn.close()

    for wl in target_watchlists:
        signals = query_paper(wl, """
            SELECT date, ticker, action, prediction, rank, percentile
            FROM signals
            WHERE date = (SELECT MAX(date) FROM signals)
              AND action IN ('BUY', 'SELL')
            ORDER BY rank
            LIMIT 20
        """)

        for sig in signals:
            fwd = fwd_by_key.get((sig["ticker"], wl))

            forward_confirms = False
            if fwd and fwd["predicted_action"] == sig["action"]:
                forward_confirms = True

            triggers.append({
                "watchlist": wl,
                "date": sig["date"],
                "ticker": sig["ticker"],
                "action": sig["action"],
                "score": sig["prediction"],
                "rank": sig["rank"],
                "percentile": sig.get("percentile"),
                "forward_confirms": forward_confirms,
                "forward_maturity": fwd["maturity_date"] if fwd else None,
                "forward_score": fwd["predicted_score"] if fwd else None,
            })

    # Sort: confirmed signals first, then by rank
    triggers.sort(key=lambda t: (not t["forward_confirms"], t["rank"]))

    return {
        "triggers": triggers,
        "count": len(triggers),
        "confirmed": sum(1 for t in triggers if t["forward_confirms"]),
    }
