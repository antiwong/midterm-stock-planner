"""Portfolio endpoints: summary, positions, trades, snapshots, signals."""

from fastapi import APIRouter, Query
from typing import Optional
from ..db import WATCHLISTS, query_paper

router = APIRouter(prefix="/api/portfolios", tags=["portfolios"])


@router.get("/summary")
def get_summary():
    """Overview of all 4 portfolios."""
    portfolios = []
    for wl in WATCHLISTS:
        state = query_paper(wl, "SELECT * FROM portfolio_state WHERE id = 1")
        snap = query_paper(
            wl,
            "SELECT portfolio_value, cash, daily_return, cumulative_return, "
            "benchmark_cumulative FROM daily_snapshots ORDER BY date DESC LIMIT 1",
        )
        pos_count = query_paper(
            wl, "SELECT COUNT(*) as cnt FROM positions WHERE is_active = 1"
        )

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
            })
        else:
            portfolios.append({"watchlist": wl, "portfolio_value": 0, "mode": "no_data"})

    return {"portfolios": portfolios}


@router.get("/{watchlist}/positions")
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
def get_trades(watchlist: str, limit: int = Query(50, le=500)):
    """Trade history."""
    rows = query_paper(
        watchlist,
        "SELECT date, ticker, action, shares, price, value, cost "
        "FROM trades ORDER BY date DESC, id DESC LIMIT ?",
        (limit,),
    )
    return {"trades": rows}


@router.get("/{watchlist}/snapshots")
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
