#!/usr/bin/env python3
"""
Forward Prediction Journal
===========================
Immutable log of model predictions with deferred evaluation against actuals.

Tracks predictions at two horizons:
- 5-day: fast feedback loop for accuracy calibration
- 63-day: matches the model's actual prediction horizon (3 months)

Predictions are logged *before* outcomes are known and evaluated once matured.
Re-runs on the same day are idempotent (INSERT OR IGNORE on UNIQUE constraint).

Usage:
    from scripts.forward_journal import ForwardJournalDB

    journal = ForwardJournalDB()
    journal.log_prediction(
        prediction_date="2026-03-17",
        ticker="NVDA",
        watchlist="tech_giants",
        horizon_days=5,
        predicted_score=0.084,
        predicted_rank=1,
        predicted_action="BUY",
        entry_price=892.40,
    )

    # Later, when predictions mature:
    matured = journal.get_matured_predictions(horizon_days=5, as_of_date="2026-03-24")
    for pred in matured:
        journal.record_evaluation(pred["id"], actual_price=910.20, actual_return=0.020, hit=1)
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


class ForwardJournalDB:
    """SQLite database for immutable forward predictions."""

    def __init__(self, db_path: str = "data/forward_journal.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """Create predictions table if it doesn't exist."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_date TEXT NOT NULL,
                maturity_date TEXT NOT NULL,
                ticker TEXT NOT NULL,
                watchlist TEXT NOT NULL,
                horizon_days INTEGER NOT NULL,
                predicted_score REAL NOT NULL,
                predicted_rank INTEGER NOT NULL,
                predicted_action TEXT NOT NULL,
                entry_price REAL NOT NULL,
                model_version TEXT DEFAULT '',
                metadata_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                actual_price REAL,
                actual_return REAL,
                hit INTEGER,
                evaluated_at TEXT,
                UNIQUE(prediction_date, ticker, horizon_days, watchlist)
            );

            CREATE INDEX IF NOT EXISTS idx_pred_maturity
                ON predictions(maturity_date, evaluated_at);
            CREATE INDEX IF NOT EXISTS idx_pred_watchlist
                ON predictions(watchlist, prediction_date);
            CREATE INDEX IF NOT EXISTS idx_pred_ticker
                ON predictions(ticker, prediction_date);
            CREATE INDEX IF NOT EXISTS idx_pred_horizon
                ON predictions(horizon_days, maturity_date);
        """)

    def log_prediction(self, prediction_date: str, ticker: str, watchlist: str,
                       horizon_days: int, predicted_score: float, predicted_rank: int,
                       predicted_action: str, entry_price: float,
                       model_version: str = "", metadata_json: str = "{}") -> bool:
        """Log an immutable prediction. Returns True if inserted, False if duplicate."""
        maturity_date = self._compute_maturity_date(prediction_date, horizon_days)
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO predictions
                    (prediction_date, maturity_date, ticker, watchlist, horizon_days,
                     predicted_score, predicted_rank, predicted_action, entry_price,
                     model_version, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (prediction_date, maturity_date, ticker, watchlist, horizon_days,
                  predicted_score, predicted_rank, predicted_action, entry_price,
                  model_version, metadata_json))
            self.conn.commit()
            return self.conn.total_changes > 0
        except sqlite3.Error:
            return False

    def log_predictions_batch(self, predictions: List[Dict]) -> int:
        """Log multiple predictions in a single transaction. Returns count inserted."""
        inserted = 0
        with self.conn:
            for pred in predictions:
                maturity_date = self._compute_maturity_date(
                    pred["prediction_date"], pred["horizon_days"]
                )
                try:
                    self.conn.execute("""
                        INSERT OR IGNORE INTO predictions
                            (prediction_date, maturity_date, ticker, watchlist, horizon_days,
                             predicted_score, predicted_rank, predicted_action, entry_price,
                             model_version, metadata_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        pred["prediction_date"], maturity_date,
                        pred["ticker"], pred["watchlist"], pred["horizon_days"],
                        pred["predicted_score"], pred["predicted_rank"],
                        pred["predicted_action"], pred["entry_price"],
                        pred.get("model_version", ""),
                        pred.get("metadata_json", "{}"),
                    ))
                    if self.conn.total_changes > 0:
                        inserted += 1
                except sqlite3.Error:
                    continue
        return inserted

    def get_matured_predictions(self, horizon_days: int, as_of_date: str) -> List[Dict]:
        """Get predictions whose maturity_date <= as_of_date and not yet evaluated."""
        rows = self.conn.execute("""
            SELECT * FROM predictions
            WHERE horizon_days = ?
              AND maturity_date <= ?
              AND evaluated_at IS NULL
            ORDER BY prediction_date, watchlist, predicted_rank
        """, (horizon_days, as_of_date)).fetchall()
        return [dict(r) for r in rows]

    def record_evaluation(self, prediction_id: int, actual_price: float,
                          actual_return: float, hit: int) -> bool:
        """Record actual outcome for a matured prediction."""
        try:
            self.conn.execute("""
                UPDATE predictions
                SET actual_price = ?, actual_return = ?, hit = ?,
                    evaluated_at = datetime('now')
                WHERE id = ? AND evaluated_at IS NULL
            """, (actual_price, actual_return, hit, prediction_id))
            self.conn.commit()
            return self.conn.total_changes > 0
        except sqlite3.Error:
            return False

    def get_hit_rates(self, watchlist: Optional[str] = None,
                      horizon_days: Optional[int] = None,
                      last_n_days: int = 30) -> Dict:
        """Aggregate hit rates by watchlist/horizon for evaluated BUY predictions."""
        conditions = ["evaluated_at IS NOT NULL", "predicted_action = 'BUY'"]
        params: list = []

        if watchlist:
            conditions.append("watchlist = ?")
            params.append(watchlist)
        if horizon_days:
            conditions.append("horizon_days = ?")
            params.append(horizon_days)
        if last_n_days:
            conditions.append("prediction_date >= date('now', ?)")
            params.append(f"-{last_n_days} days")

        where = " AND ".join(conditions)
        row = self.conn.execute(f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits,
                AVG(actual_return) as avg_return
            FROM predictions
            WHERE {where}
        """, params).fetchone()

        total = row["total"] or 0
        hits = row["hits"] or 0
        return {
            "total": total,
            "hits": hits,
            "hit_rate": hits / total if total > 0 else 0.0,
            "avg_return": row["avg_return"] or 0.0,
        }

    def get_hit_rates_by_watchlist(self, horizon_days: Optional[int] = None,
                                   last_n_days: int = 30) -> List[Dict]:
        """Get hit rates grouped by watchlist."""
        conditions = ["evaluated_at IS NOT NULL", "predicted_action = 'BUY'"]
        params: list = []

        if horizon_days:
            conditions.append("horizon_days = ?")
            params.append(horizon_days)
        if last_n_days:
            conditions.append("prediction_date >= date('now', ?)")
            params.append(f"-{last_n_days} days")

        where = " AND ".join(conditions)
        rows = self.conn.execute(f"""
            SELECT
                watchlist,
                horizon_days,
                COUNT(*) as total,
                SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits,
                AVG(actual_return) as avg_return
            FROM predictions
            WHERE {where}
            GROUP BY watchlist, horizon_days
            ORDER BY watchlist, horizon_days
        """, params).fetchall()
        return [dict(r) for r in rows]

    def get_prediction_history(self, ticker: Optional[str] = None,
                               watchlist: Optional[str] = None,
                               horizon_days: Optional[int] = None,
                               limit: int = 100) -> List[Dict]:
        """Query prediction history for dashboard display."""
        conditions = ["1=1"]
        params: list = []

        if ticker:
            conditions.append("ticker = ?")
            params.append(ticker)
        if watchlist:
            conditions.append("watchlist = ?")
            params.append(watchlist)
        if horizon_days:
            conditions.append("horizon_days = ?")
            params.append(horizon_days)

        where = " AND ".join(conditions)
        params.append(limit)
        rows = self.conn.execute(f"""
            SELECT * FROM predictions
            WHERE {where}
            ORDER BY prediction_date DESC, watchlist, predicted_rank
            LIMIT ?
        """, params).fetchall()
        return [dict(r) for r in rows]

    def get_active_predictions(self, as_of_date: Optional[str] = None) -> List[Dict]:
        """Get predictions not yet matured or evaluated."""
        date = as_of_date or datetime.now().strftime("%Y-%m-%d")
        rows = self.conn.execute("""
            SELECT * FROM predictions
            WHERE maturity_date > ? AND evaluated_at IS NULL
            ORDER BY maturity_date, watchlist, predicted_rank
        """, (date,)).fetchall()
        return [dict(r) for r in rows]

    def get_accuracy_trend(self, watchlist: Optional[str] = None,
                           horizon_days: int = 5) -> List[Dict]:
        """Get rolling hit rate over time for trend charts."""
        conditions = [
            "evaluated_at IS NOT NULL",
            "predicted_action = 'BUY'",
            "horizon_days = ?",
        ]
        params: list = [horizon_days]

        if watchlist:
            conditions.append("watchlist = ?")
            params.append(watchlist)

        where = " AND ".join(conditions)
        rows = self.conn.execute(f"""
            SELECT
                prediction_date,
                COUNT(*) as total,
                SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits,
                AVG(actual_return) as avg_return
            FROM predictions
            WHERE {where}
            GROUP BY prediction_date
            ORDER BY prediction_date
        """, params).fetchall()
        return [dict(r) for r in rows]

    def get_summary_stats(self) -> Dict:
        """Get overall journal statistics."""
        row = self.conn.execute("""
            SELECT
                COUNT(*) as total_predictions,
                COUNT(CASE WHEN evaluated_at IS NOT NULL THEN 1 END) as evaluated,
                COUNT(CASE WHEN evaluated_at IS NULL AND maturity_date <= date('now') THEN 1 END) as pending_eval,
                COUNT(CASE WHEN evaluated_at IS NULL AND maturity_date > date('now') THEN 1 END) as active,
                MIN(prediction_date) as first_prediction,
                MAX(prediction_date) as last_prediction
            FROM predictions
        """).fetchone()
        return dict(row) if row else {}

    def _compute_maturity_date(self, prediction_date: str, horizon_days: int) -> str:
        """Compute maturity date using business days (Mon-Fri)."""
        start = pd.Timestamp(prediction_date)
        maturity = start + pd.offsets.BDay(horizon_days)
        return maturity.strftime("%Y-%m-%d")

    def close(self):
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
