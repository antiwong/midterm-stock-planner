"""Database schema and CRUD operations for regression testing.

Extends the existing SQLite database with tables:
- regression_tests: One row per regression test session
- regression_steps: One row per feature addition step
- feature_contributions: Aggregated feature leaderboard
- optimization_runs: Bayesian optimization run results
- correlation_analysis: Pairwise ticker correlation snapshots
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_DB_PATH = "data/runs.db"


def _ensure_regression_tables(db_path: str = DEFAULT_DB_PATH) -> None:
    """Create regression testing tables if they don't exist."""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS regression_tests (
                regression_id    TEXT PRIMARY KEY,
                name             TEXT NOT NULL,
                description      TEXT,
                created_at       TEXT NOT NULL,
                status           TEXT NOT NULL DEFAULT 'running',
                config_json      TEXT,
                baseline_features_json TEXT,
                features_tested_json   TEXT,
                total_steps      INTEGER DEFAULT 0,
                best_feature     TEXT,
                best_marginal_sharpe REAL,
                final_sharpe     REAL,
                final_rank_ic    REAL,
                baseline_run_id  TEXT,
                final_run_id     TEXT,
                duration_seconds REAL
            );

            CREATE TABLE IF NOT EXISTS regression_steps (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                regression_id    TEXT NOT NULL,
                step_number      INTEGER NOT NULL,
                feature_added    TEXT NOT NULL,
                feature_set_json TEXT,
                feature_columns_json TEXT,
                sharpe_ratio     REAL,
                mean_rank_ic     REAL,
                excess_return    REAL,
                max_drawdown     REAL,
                hit_rate         REAL,
                turnover         REAL,
                marginal_sharpe  REAL,
                marginal_rank_ic REAL,
                metrics_json     TEXT,
                marginal_metrics_json TEXT,
                significance_json TEXT,
                feature_importance_json TEXT,
                window_ics_json  TEXT,
                window_rank_ics_json TEXT,
                window_test_sharpes_json TEXT,
                tuned_params_json TEXT,
                model_config_json TEXT,
                run_id           TEXT,
                duration_seconds REAL,
                created_at       TEXT NOT NULL,
                FOREIGN KEY (regression_id) REFERENCES regression_tests(regression_id) ON DELETE CASCADE,
                UNIQUE(regression_id, step_number)
            );

            CREATE TABLE IF NOT EXISTS feature_contributions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_name     TEXT NOT NULL,
                regression_id    TEXT NOT NULL,
                marginal_sharpe  REAL,
                marginal_rank_ic REAL,
                marginal_excess_return REAL,
                feature_importance_pct REAL,
                rank_ic_p_value  REAL,
                sharpe_p_value   REAL,
                is_significant   INTEGER DEFAULT 0,
                step_number      INTEGER,
                total_features_at_step INTEGER,
                created_at       TEXT NOT NULL,
                FOREIGN KEY (regression_id) REFERENCES regression_tests(regression_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_regsteps_regid ON regression_steps(regression_id);
            CREATE INDEX IF NOT EXISTS idx_regsteps_feature ON regression_steps(feature_added);
            CREATE INDEX IF NOT EXISTS idx_featcontrib_name ON feature_contributions(feature_name);
            CREATE INDEX IF NOT EXISTS idx_featcontrib_regid ON feature_contributions(regression_id);

            CREATE TABLE IF NOT EXISTS optimization_runs (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id           TEXT UNIQUE,
                ticker           TEXT NOT NULL,
                metric           TEXT NOT NULL,
                best_score       REAL,
                n_calls          INTEGER,
                n_initial        INTEGER,
                seed             INTEGER,
                optimize_vix     INTEGER DEFAULT 0,
                optimize_dxy     INTEGER DEFAULT 0,
                best_params_json TEXT,
                all_scores_json  TEXT,
                sharpe_ratio     REAL,
                total_return     REAL,
                max_drawdown     REAL,
                num_trades       INTEGER,
                created_at       TEXT NOT NULL,
                duration_seconds REAL,
                notes            TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_optrun_ticker ON optimization_runs(ticker);
            CREATE INDEX IF NOT EXISTS idx_optrun_metric ON optimization_runs(metric);
            CREATE INDEX IF NOT EXISTS idx_optrun_created ON optimization_runs(created_at);

            CREATE TABLE IF NOT EXISTS correlation_analysis (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id      TEXT UNIQUE,
                ticker           TEXT NOT NULL,
                peer_ticker      TEXT NOT NULL,
                pearson_corr     REAL,
                spearman_corr    REAL,
                rolling_20d_mean REAL,
                rolling_20d_std  REAL,
                rolling_60d_mean REAL,
                rolling_60d_std  REAL,
                lead_lag_json    TEXT,
                created_at       TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_corr_ticker ON correlation_analysis(ticker);
            CREATE INDEX IF NOT EXISTS idx_corr_peer ON correlation_analysis(peer_ticker);
        """)
        conn.commit()
    finally:
        conn.close()


class RegressionDatabase:
    """CRUD operations for regression testing tables."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _ensure_regression_tables(db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # --- regression_tests ---

    def create_regression_test(
        self,
        regression_id: str,
        name: str,
        description: str = "",
        config: Optional[Dict] = None,
        baseline_features: Optional[List[str]] = None,
        features_to_test: Optional[List[str]] = None,
    ) -> None:
        """Create a new regression test session."""
        conn = self._connect()
        try:
            conn.execute(
                """INSERT INTO regression_tests
                   (regression_id, name, description, created_at, status,
                    config_json, baseline_features_json, features_tested_json)
                   VALUES (?, ?, ?, ?, 'running', ?, ?, ?)""",
                (
                    regression_id,
                    name,
                    description,
                    datetime.now().isoformat(),
                    json.dumps(config) if config else None,
                    json.dumps(baseline_features) if baseline_features else None,
                    json.dumps(features_to_test) if features_to_test else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def complete_regression_test(
        self,
        regression_id: str,
        total_steps: int,
        best_feature: Optional[str],
        best_marginal_sharpe: Optional[float],
        final_sharpe: Optional[float],
        final_rank_ic: Optional[float],
        baseline_run_id: Optional[str] = None,
        final_run_id: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        status: str = "completed",
    ) -> None:
        """Mark regression test as completed with summary data."""
        conn = self._connect()
        try:
            conn.execute(
                """UPDATE regression_tests SET
                   status=?, total_steps=?, best_feature=?, best_marginal_sharpe=?,
                   final_sharpe=?, final_rank_ic=?,
                   baseline_run_id=?, final_run_id=?, duration_seconds=?
                   WHERE regression_id=?""",
                (
                    status, total_steps, best_feature, best_marginal_sharpe,
                    final_sharpe, final_rank_ic,
                    baseline_run_id, final_run_id, duration_seconds,
                    regression_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_regression_test(self, regression_id: str) -> Optional[Dict]:
        """Get a regression test by ID."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM regression_tests WHERE regression_id=?",
                (regression_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_regression_tests(self, status: Optional[str] = None) -> List[Dict]:
        """List regression tests, optionally filtered by status."""
        conn = self._connect()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM regression_tests WHERE status=? ORDER BY created_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM regression_tests ORDER BY created_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- regression_steps ---

    def add_regression_step(
        self,
        regression_id: str,
        step_number: int,
        feature_added: str,
        feature_set: List[str],
        feature_columns: List[str],
        metrics: Dict[str, float],
        marginal_metrics: Optional[Dict[str, float]] = None,
        significance: Optional[Dict] = None,
        feature_importance: Optional[Dict[str, float]] = None,
        window_ics: Optional[List[float]] = None,
        window_rank_ics: Optional[List[float]] = None,
        window_test_sharpes: Optional[List[float]] = None,
        tuned_params: Optional[Dict] = None,
        model_config: Optional[Dict] = None,
        run_id: Optional[str] = None,
        duration_seconds: float = 0.0,
    ) -> None:
        """Record a single regression step."""
        conn = self._connect()
        try:
            conn.execute(
                """INSERT INTO regression_steps
                   (regression_id, step_number, feature_added,
                    feature_set_json, feature_columns_json,
                    sharpe_ratio, mean_rank_ic, excess_return,
                    max_drawdown, hit_rate, turnover,
                    marginal_sharpe, marginal_rank_ic,
                    metrics_json, marginal_metrics_json, significance_json,
                    feature_importance_json,
                    window_ics_json, window_rank_ics_json, window_test_sharpes_json,
                    tuned_params_json, model_config_json,
                    run_id, duration_seconds, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    regression_id,
                    step_number,
                    feature_added,
                    json.dumps(feature_set),
                    json.dumps(feature_columns),
                    metrics.get("sharpe_ratio"),
                    metrics.get("mean_rank_ic"),
                    metrics.get("excess_return"),
                    metrics.get("max_drawdown"),
                    metrics.get("hit_rate"),
                    metrics.get("turnover"),
                    marginal_metrics.get("marginal_sharpe") if marginal_metrics else None,
                    marginal_metrics.get("marginal_rank_ic") if marginal_metrics else None,
                    json.dumps(metrics),
                    json.dumps(marginal_metrics) if marginal_metrics else None,
                    json.dumps(significance) if significance else None,
                    json.dumps(feature_importance) if feature_importance else None,
                    json.dumps(window_ics) if window_ics else None,
                    json.dumps(window_rank_ics) if window_rank_ics else None,
                    json.dumps(window_test_sharpes) if window_test_sharpes else None,
                    json.dumps(tuned_params) if tuned_params else None,
                    json.dumps(model_config) if model_config else None,
                    run_id,
                    duration_seconds,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_regression_steps(self, regression_id: str) -> List[Dict]:
        """Get all steps for a regression test, ordered by step number."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM regression_steps WHERE regression_id=? ORDER BY step_number",
                (regression_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- feature_contributions ---

    def add_feature_contribution(
        self,
        feature_name: str,
        regression_id: str,
        marginal_sharpe: Optional[float] = None,
        marginal_rank_ic: Optional[float] = None,
        marginal_excess_return: Optional[float] = None,
        feature_importance_pct: Optional[float] = None,
        rank_ic_p_value: Optional[float] = None,
        sharpe_p_value: Optional[float] = None,
        is_significant: bool = False,
        step_number: Optional[int] = None,
        total_features_at_step: Optional[int] = None,
    ) -> None:
        """Record a feature's contribution."""
        conn = self._connect()
        try:
            conn.execute(
                """INSERT INTO feature_contributions
                   (feature_name, regression_id, marginal_sharpe, marginal_rank_ic,
                    marginal_excess_return, feature_importance_pct,
                    rank_ic_p_value, sharpe_p_value, is_significant,
                    step_number, total_features_at_step, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    feature_name, regression_id,
                    marginal_sharpe, marginal_rank_ic, marginal_excess_return,
                    feature_importance_pct,
                    rank_ic_p_value, sharpe_p_value,
                    1 if is_significant else 0,
                    step_number, total_features_at_step,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_feature_leaderboard(
        self, regression_id: Optional[str] = None
    ) -> List[Dict]:
        """Get feature contributions ranked by marginal Sharpe.

        If regression_id is None, aggregates across all regression tests.
        """
        conn = self._connect()
        try:
            if regression_id:
                rows = conn.execute(
                    """SELECT * FROM feature_contributions
                       WHERE regression_id=?
                       ORDER BY marginal_sharpe DESC""",
                    (regression_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT feature_name,
                              AVG(marginal_sharpe) as marginal_sharpe,
                              AVG(marginal_rank_ic) as marginal_rank_ic,
                              AVG(feature_importance_pct) as feature_importance_pct,
                              SUM(is_significant) as times_significant,
                              COUNT(*) as times_tested
                       FROM feature_contributions
                       GROUP BY feature_name
                       ORDER BY marginal_sharpe DESC""",
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- optimization_runs ---

    def log_optimization_run(
        self,
        run_id: str,
        ticker: str,
        metric: str,
        best_score: float,
        n_calls: int,
        n_initial: int,
        seed: int,
        optimize_vix: bool = False,
        optimize_dxy: bool = False,
        best_params: Optional[Dict] = None,
        all_scores: Optional[List[float]] = None,
        sharpe_ratio: Optional[float] = None,
        total_return: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        num_trades: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Insert a new optimization run record."""
        conn = self._connect()
        try:
            conn.execute(
                """INSERT INTO optimization_runs
                   (run_id, ticker, metric, best_score, n_calls, n_initial, seed,
                    optimize_vix, optimize_dxy, best_params_json, all_scores_json,
                    sharpe_ratio, total_return, max_drawdown, num_trades,
                    created_at, duration_seconds, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id, ticker, metric, best_score,
                    n_calls, n_initial, seed,
                    1 if optimize_vix else 0,
                    1 if optimize_dxy else 0,
                    json.dumps(best_params) if best_params else None,
                    json.dumps(all_scores) if all_scores else None,
                    sharpe_ratio, total_return, max_drawdown, num_trades,
                    datetime.now().isoformat(),
                    duration_seconds, notes,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_optimization_runs(
        self, ticker: Optional[str] = None, metric: Optional[str] = None
    ) -> List[Dict]:
        """List optimization runs with optional ticker/metric filters."""
        conn = self._connect()
        try:
            clauses: List[str] = []
            params: List[Any] = []
            if ticker:
                clauses.append("ticker = ?")
                params.append(ticker)
            if metric:
                clauses.append("metric = ?")
                params.append(metric)
            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
            rows = conn.execute(
                f"SELECT * FROM optimization_runs{where} ORDER BY created_at DESC",
                params,
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_best_optimization(
        self, ticker: str, metric: Optional[str] = None
    ) -> Optional[Dict]:
        """Get the best optimization run for a ticker (highest best_score)."""
        conn = self._connect()
        try:
            if metric:
                row = conn.execute(
                    """SELECT * FROM optimization_runs
                       WHERE ticker = ? AND metric = ?
                       ORDER BY best_score DESC LIMIT 1""",
                    (ticker, metric),
                ).fetchone()
            else:
                row = conn.execute(
                    """SELECT * FROM optimization_runs
                       WHERE ticker = ?
                       ORDER BY best_score DESC LIMIT 1""",
                    (ticker,),
                ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def compare_optimizations(self, ticker: str) -> List[Dict]:
        """Return all optimization runs for a ticker, ordered by score descending."""
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT * FROM optimization_runs
                   WHERE ticker = ?
                   ORDER BY best_score DESC""",
                (ticker,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- correlation_analysis ---

    def log_correlation_analysis(
        self,
        analysis_id: str,
        ticker: str,
        peer_ticker: str,
        pearson_corr: Optional[float] = None,
        spearman_corr: Optional[float] = None,
        rolling_20d_mean: Optional[float] = None,
        rolling_20d_std: Optional[float] = None,
        rolling_60d_mean: Optional[float] = None,
        rolling_60d_std: Optional[float] = None,
        lead_lag: Optional[Dict] = None,
    ) -> None:
        """Insert a correlation analysis record."""
        conn = self._connect()
        try:
            conn.execute(
                """INSERT INTO correlation_analysis
                   (analysis_id, ticker, peer_ticker, pearson_corr, spearman_corr,
                    rolling_20d_mean, rolling_20d_std, rolling_60d_mean, rolling_60d_std,
                    lead_lag_json, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    analysis_id, ticker, peer_ticker,
                    pearson_corr, spearman_corr,
                    rolling_20d_mean, rolling_20d_std,
                    rolling_60d_mean, rolling_60d_std,
                    json.dumps(lead_lag) if lead_lag else None,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_correlations(
        self, ticker: Optional[str] = None
    ) -> List[Dict]:
        """Get correlation analyses, optionally filtered by ticker."""
        conn = self._connect()
        try:
            if ticker:
                rows = conn.execute(
                    """SELECT * FROM correlation_analysis
                       WHERE ticker = ? OR peer_ticker = ?
                       ORDER BY created_at DESC""",
                    (ticker, ticker),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM correlation_analysis ORDER BY created_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
