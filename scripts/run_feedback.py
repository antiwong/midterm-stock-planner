#!/usr/bin/env python3
"""Forward test feedback — evaluate matured predictions against actual returns.

Reads paper trading positions from the portfolio DB. After 63 trading days,
compares exit/current price to entry price and logs actual return vs predicted
score for each position.

Runs daily at 7:00 PM SGT (11:00 UTC) via cron.

Usage:
    python scripts/run_feedback.py
    python scripts/run_feedback.py --watchlist sg_blue_chips
    python scripts/run_feedback.py --all
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

import pandas as pd
import numpy as np

DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

# Trading days horizon for evaluation
HORIZON_TRADING_DAYS = 63
# Calendar days approximation (63 trading days ≈ 90 calendar days)
HORIZON_CALENDAR_DAYS = 90

PORTFOLIOS = [
    "moby_picks", "tech_giants", "semiconductors", "precious_metals",
    "sg_reits", "sg_blue_chips", "anthony_watchlist", "sp500",
    "clean_energy", "etfs",
]


def ensure_feedback_table(conn: sqlite3.Connection):
    """Create feedback table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            entry_price REAL NOT NULL,
            predicted_score REAL,
            predicted_rank INTEGER,
            eval_date TEXT NOT NULL,
            eval_price REAL NOT NULL,
            actual_return REAL NOT NULL,
            horizon_days INTEGER NOT NULL,
            hit INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, entry_date, horizon_days)
        )
    """)
    conn.commit()


def get_matured_positions(conn: sqlite3.Connection, latest_prices: dict) -> List[dict]:
    """Find positions whose entry date is >= HORIZON_CALENDAR_DAYS ago."""
    cutoff = (datetime.now() - timedelta(days=HORIZON_CALENDAR_DAYS)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    # Get all positions (active and closed) with entry_date before cutoff
    positions = conn.execute("""
        SELECT id, ticker, shares, entry_price, entry_date, weight, is_active
        FROM positions
        WHERE entry_date <= ?
    """, (cutoff,)).fetchall()

    # Check which ones already have feedback
    existing = set()
    try:
        rows = conn.execute(
            "SELECT ticker, entry_date FROM feedback WHERE horizon_days = ?",
            (HORIZON_TRADING_DAYS,)
        ).fetchall()
        existing = {(r[0], r[1]) for r in rows}
    except Exception:
        pass

    matured = []
    for p in positions:
        key = (p["ticker"], p["entry_date"])
        if key in existing:
            continue

        tk = p["ticker"]
        entry_price = p["entry_price"]
        if entry_price <= 0:
            continue

        # Use current price for evaluation
        eval_price = latest_prices.get(tk, 0)
        if eval_price <= 0:
            continue

        actual_return = (eval_price / entry_price) - 1.0

        matured.append({
            "ticker": tk,
            "entry_date": p["entry_date"],
            "entry_price": entry_price,
            "eval_price": eval_price,
            "eval_date": today,
            "actual_return": actual_return,
            "is_active": p["is_active"],
        })

    return matured


def get_signal_score(conn: sqlite3.Connection, ticker: str, entry_date: str) -> dict:
    """Look up the predicted score and rank for a ticker on its entry date."""
    try:
        row = conn.execute(
            "SELECT prediction, rank FROM signals WHERE ticker = ? AND date <= ? ORDER BY date DESC LIMIT 1",
            (ticker, entry_date)
        ).fetchone()
        if row:
            return {"score": row[0], "rank": row[1]}
    except Exception:
        pass
    return {"score": None, "rank": None}


def evaluate_watchlist(wl: str, latest_prices: dict) -> dict:
    """Evaluate matured positions for one watchlist."""
    db_path = DATA_DIR / "paper_trading_{}.db".format(wl)
    if not db_path.exists():
        return {"watchlist": wl, "status": "no_db", "evaluated": 0}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    ensure_feedback_table(conn)

    matured = get_matured_positions(conn, latest_prices)
    if not matured:
        conn.close()
        return {"watchlist": wl, "status": "ok", "evaluated": 0, "message": "no matured positions"}

    evaluated = []
    for pos in matured:
        sig = get_signal_score(conn, pos["ticker"], pos["entry_date"])
        hit = 1 if pos["actual_return"] > 0 else 0

        conn.execute(
            "INSERT OR IGNORE INTO feedback "
            "(ticker, entry_date, entry_price, predicted_score, predicted_rank, "
            "eval_date, eval_price, actual_return, horizon_days, hit) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (pos["ticker"], pos["entry_date"], pos["entry_price"],
             sig["score"], sig["rank"],
             pos["eval_date"], pos["eval_price"], pos["actual_return"],
             HORIZON_TRADING_DAYS, hit)
        )
        evaluated.append({
            "ticker": pos["ticker"],
            "entry": pos["entry_date"],
            "entry_price": pos["entry_price"],
            "eval_price": pos["eval_price"],
            "return": pos["actual_return"],
            "predicted_score": sig["score"],
            "predicted_rank": sig["rank"],
            "hit": hit,
        })

    conn.commit()

    # Compute summary stats
    returns = [e["return"] for e in evaluated]
    hits = sum(e["hit"] for e in evaluated)
    scores = [e["predicted_score"] for e in evaluated if e["predicted_score"] is not None]
    actuals = [e["return"] for e in evaluated if e["predicted_score"] is not None]

    # Rank correlation (if enough data)
    rank_ic = None
    if len(scores) >= 3 and len(set(scores)) > 1 and len(set(actuals)) > 1:
        rank_ic = float(pd.Series(scores).corr(pd.Series(actuals), method="spearman"))

    summary = {
        "watchlist": wl,
        "status": "ok",
        "evaluated": len(evaluated),
        "hit_rate": hits / len(evaluated) if evaluated else 0,
        "avg_return": float(np.mean(returns)),
        "rank_ic": rank_ic,
        "positions": evaluated,
    }

    conn.close()
    return summary


def print_report(results: List[dict]):
    """Print feedback report."""
    print("=" * 60)
    print("FEEDBACK REPORT — {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")))
    print("  Horizon: {} trading days (~{} calendar days)".format(
        HORIZON_TRADING_DAYS, HORIZON_CALENDAR_DAYS))
    print("=" * 60)

    total_evaluated = 0
    for r in results:
        wl = r["watchlist"]
        if r.get("status") == "no_db":
            continue
        n = r["evaluated"]
        if n == 0:
            continue

        total_evaluated += n
        print("\n  {} — {} positions evaluated".format(wl, n))
        print("    Hit rate:   {:.0%}".format(r["hit_rate"]))
        print("    Avg return: {:+.2%}".format(r["avg_return"]))
        if r.get("rank_ic") is not None:
            print("    Rank IC:    {:.4f}".format(r["rank_ic"]))

        for pos in r["positions"]:
            marker = "+" if pos["hit"] else "-"
            score_str = "{:+.4f}".format(pos["predicted_score"]) if pos["predicted_score"] is not None else "n/a"
            print("    {} {:12s} entry={} ${:.2f} → ${:.2f} ({:+.1%})  score={}".format(
                marker, pos["ticker"], pos["entry"], pos["entry_price"],
                pos["eval_price"], pos["return"], score_str))

    if total_evaluated == 0:
        print("\n  No matured positions to evaluate.")
        print("  (Positions need {} calendar days to mature)".format(HORIZON_CALENDAR_DAYS))

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Evaluate matured forward test predictions")
    parser.add_argument("--watchlist", default=None, help="Single watchlist to evaluate")
    parser.add_argument("--all", action="store_true", help="Evaluate all portfolios")
    args = parser.parse_args()

    try:
        from utils.slack_notifier import SlackNotifier
        notifier = SlackNotifier(job_name="feedback-eval")
    except Exception:
        notifier = None

    metrics = {}
    try:
        # Load latest prices
        price_df = pd.read_csv(DATA_DIR / "prices_daily.csv")
        latest_prices = price_df.sort_values("date").groupby("ticker").last()["close"].to_dict()

        if args.watchlist:
            watchlists = [args.watchlist]
        elif args.all:
            watchlists = PORTFOLIOS
        else:
            watchlists = [wl for wl in PORTFOLIOS if (DATA_DIR / "paper_trading_{}.db".format(wl)).exists()]

        results = []
        for wl in watchlists:
            r = evaluate_watchlist(wl, latest_prices)
            results.append(r)

        print_report(results)

        # Save daily feedback log
        log_path = LOG_DIR / "feedback_{}.json".format(datetime.now().strftime("%Y%m%d"))
        log_data = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "horizon_days": HORIZON_TRADING_DAYS,
            "results": [
                {k: v for k, v in r.items() if k != "positions"}
                for r in results
            ],
        }
        with open(log_path, "w") as f:
            json.dump(log_data, f, indent=2, default=str)

        total_resolved = sum(r.get("resolved", 0) for r in results)
        total_pending = sum(r.get("pending", 0) for r in results)
        metrics = {
            'watchlists': len(watchlists),
            'resolved': total_resolved,
            'pending': total_pending,
        }
        if notifier:
            notifier.completed(metrics=metrics)

    except Exception as e:
        if notifier:
            notifier.failed(error=str(e), context=metrics, exc=e)
        raise


if __name__ == "__main__":
    main()
