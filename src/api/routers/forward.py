"""Forward testing endpoints: predictions and accuracy."""

from fastapi import APIRouter, Query
from typing import Optional
from ..db import cached_response, query_forward

router = APIRouter(prefix="/api/forward", tags=["forward"])


@router.get("/predictions")
@cached_response(ttl=120)
def get_predictions(
    watchlist: Optional[str] = Query(None),
    horizon: Optional[int] = Query(None),
    status: str = Query("all", pattern="^(all|active|evaluated)$"),
    limit: int = Query(200, le=2000),
):
    """Forward journal predictions."""
    conditions = ["1=1"]
    params: list = []

    if watchlist and watchlist != "all":
        conditions.append("watchlist = ?")
        params.append(watchlist)
    if horizon:
        conditions.append("horizon_days = ?")
        params.append(horizon)
    if status == "active":
        conditions.append("evaluated_at IS NULL AND maturity_date > date('now')")
    elif status == "evaluated":
        conditions.append("evaluated_at IS NOT NULL")

    where = " AND ".join(conditions)
    params.append(limit)

    rows = query_forward(f"""
        SELECT id, prediction_date, maturity_date, ticker, watchlist, horizon_days,
               predicted_score, predicted_rank, predicted_action, entry_price,
               actual_price, actual_return, hit, evaluated_at
        FROM predictions
        WHERE {where}
        ORDER BY prediction_date DESC, watchlist, predicted_rank
        LIMIT ?
    """, params)

    return {"predictions": rows, "count": len(rows)}


@router.get("/accuracy")
@cached_response(ttl=120)
def get_accuracy(watchlist: Optional[str] = Query(None)):
    """Aggregated hit rates."""
    # By watchlist + horizon
    conditions = ["evaluated_at IS NOT NULL", "predicted_action = 'BUY'"]
    params: list = []
    if watchlist and watchlist != "all":
        conditions.append("watchlist = ?")
        params.append(watchlist)

    where = " AND ".join(conditions)

    by_watchlist = query_forward(f"""
        SELECT watchlist, horizon_days,
               COUNT(*) as total,
               SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits,
               AVG(actual_return) as avg_return
        FROM predictions WHERE {where}
        GROUP BY watchlist, horizon_days
        ORDER BY watchlist, horizon_days
    """, params)

    # Overall
    overall = query_forward(f"""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits,
               AVG(actual_return) as avg_return
        FROM predictions WHERE {where}
    """, params)

    # Summary stats
    stats = query_forward("""
        SELECT
            COUNT(*) as total_predictions,
            COUNT(CASE WHEN evaluated_at IS NOT NULL THEN 1 END) as evaluated,
            COUNT(CASE WHEN evaluated_at IS NULL AND maturity_date > date('now') THEN 1 END) as active,
            COUNT(CASE WHEN evaluated_at IS NULL AND maturity_date <= date('now') THEN 1 END) as pending_eval
        FROM predictions
    """)

    return {
        "overall": overall[0] if overall else {},
        "by_watchlist": by_watchlist,
        "stats": stats[0] if stats else {},
    }


@router.get("/trend")
@cached_response(ttl=120)
def get_accuracy_trend(
    watchlist: Optional[str] = Query(None),
    horizon: int = Query(5),
):
    """Rolling hit rate over time for trend charts."""
    conditions = [
        "evaluated_at IS NOT NULL",
        "predicted_action = 'BUY'",
        "horizon_days = ?",
    ]
    params: list = [horizon]

    if watchlist and watchlist != "all":
        conditions.append("watchlist = ?")
        params.append(watchlist)

    where = " AND ".join(conditions)

    rows = query_forward(f"""
        SELECT prediction_date,
               COUNT(*) as total,
               SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits,
               AVG(actual_return) as avg_return
        FROM predictions WHERE {where}
        GROUP BY prediction_date
        ORDER BY prediction_date
    """, params)

    return {"trend": rows}
