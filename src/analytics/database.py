"""
Database module for storing and managing analysis runs.

Uses SQLite for simplicity and portability.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
import hashlib
import logging

logger = logging.getLogger(__name__)


# Database schema version for migrations
SCHEMA_VERSION = 1


@dataclass
class RunRecord:
    """Represents a single analysis/backtest run."""
    run_id: str
    run_type: str  # "backtest", "score", "ab_comparison"
    created_at: str
    status: str  # "running", "completed", "failed"
    
    # Configuration
    config_json: str = ""
    
    # Results summary
    metrics_json: str = ""
    
    # Universe info
    universe: str = ""  # comma-separated tickers
    universe_count: int = 0
    
    # Key metrics (for quick filtering/sorting)
    total_return: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    
    # Timing
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_seconds: Optional[float] = None
    
    # Metadata
    name: Optional[str] = None
    description: Optional[str] = None
    tags: str = ""  # comma-separated tags
    
    # Paths to saved artifacts
    model_path: Optional[str] = None
    report_path: Optional[str] = None
    chart_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "RunRecord":
        """Create from database row."""
        return cls(**dict(row))


@dataclass 
class StockScore:
    """Represents a stock score from a run."""
    run_id: str
    ticker: str
    score: float
    rank: int
    
    # Feature values (optional)
    features_json: str = ""
    
    # SHAP explanations (optional)
    shap_json: str = ""
    
    # Additional metrics
    predicted_return: Optional[float] = None
    actual_return: Optional[float] = None


class RunDatabase:
    """SQLite database for storing analysis runs."""
    
    def __init__(self, db_path: str | Path = "data/runs.db"):
        """
        Initialize the database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Schema version table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)
        
        # Check schema version
        cursor.execute("SELECT version FROM schema_version LIMIT 1")
        row = cursor.fetchone()
        current_version = row['version'] if row else 0
        
        if current_version < SCHEMA_VERSION:
            self._migrate_schema(conn, current_version)
        
        # Runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                run_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                
                config_json TEXT,
                metrics_json TEXT,
                
                universe TEXT,
                universe_count INTEGER DEFAULT 0,
                
                -- Watchlist info
                watchlist TEXT,
                watchlist_display_name TEXT,
                
                total_return REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                win_rate REAL,
                
                start_date TEXT,
                end_date TEXT,
                duration_seconds REAL,
                
                name TEXT,
                description TEXT,
                tags TEXT,
                
                model_path TEXT,
                report_path TEXT,
                chart_path TEXT
            )
        """)
        
        # Stock scores table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                ticker TEXT NOT NULL,
                score REAL NOT NULL,
                rank INTEGER,
                features_json TEXT,
                shap_json TEXT,
                predicted_return REAL,
                actual_return REAL,
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
                UNIQUE(run_id, ticker)
            )
        """)
        
        # Trade history table (for backtests)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                date TEXT NOT NULL,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity REAL,
                price REAL,
                value REAL,
                commission REAL,
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
        """)
        
        # Portfolio history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                date TEXT NOT NULL,
                portfolio_value REAL,
                benchmark_value REAL,
                cash REAL,
                positions_json TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )
        """)
        
        # Indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_type ON runs(run_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scores_run ON stock_scores(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scores_ticker ON stock_scores(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_run ON trades(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_run ON portfolio_history(run_id)")
        
        # Update schema version
        cursor.execute("DELETE FROM schema_version")
        cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    def _migrate_schema(self, conn: sqlite3.Connection, from_version: int) -> None:
        """Run schema migrations."""
        logger.info(f"Migrating database from v{from_version} to v{SCHEMA_VERSION}")
        cursor = conn.cursor()
        
        # Check if watchlist columns exist, add if not
        try:
            cursor.execute("SELECT watchlist FROM runs LIMIT 1")
        except sqlite3.OperationalError:
            logger.info("Adding watchlist columns to runs table")
            cursor.execute("ALTER TABLE runs ADD COLUMN watchlist TEXT")
            cursor.execute("ALTER TABLE runs ADD COLUMN watchlist_display_name TEXT")
            conn.commit()
    
    # =========================================================================
    # Run CRUD Operations
    # =========================================================================
    
    def create_run(
        self,
        run_type: str,
        config: Optional[Dict] = None,
        universe: Optional[List[str]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        watchlist: Optional[str] = None,
        watchlist_display_name: Optional[str] = None,
    ) -> str:
        """
        Create a new run record.
        
        Args:
            run_type: Type of run (backtest, score, ab_comparison)
            config: Configuration dictionary
            universe: List of ticker symbols
            name: Optional run name
            description: Optional description
            tags: Optional list of tags
            watchlist: Watchlist identifier (e.g., 'tech_giants')
            watchlist_display_name: Human-readable watchlist name
            
        Returns:
            run_id: Unique identifier for the run
        """
        # Generate unique run ID with watchlist prefix if provided
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_input = f"{timestamp}_{run_type}_{config}_{watchlist}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        run_id = f"{timestamp}_{hash_suffix}"
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO runs (
                run_id, run_type, created_at, status,
                config_json, universe, universe_count,
                name, description, tags, watchlist, watchlist_display_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            run_type,
            datetime.now().isoformat(),
            "running",
            json.dumps(config) if config else None,
            ",".join(universe) if universe else None,
            len(universe) if universe else 0,
            name,
            description,
            ",".join(tags) if tags else None,
            watchlist,
            watchlist_display_name,
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created run {run_id} ({run_type}, watchlist={watchlist})")
        return run_id
    
    def update_run(
        self,
        run_id: str,
        status: Optional[str] = None,
        metrics: Optional[Dict] = None,
        total_return: Optional[float] = None,
        sharpe_ratio: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        win_rate: Optional[float] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        model_path: Optional[str] = None,
        report_path: Optional[str] = None,
        chart_path: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Update an existing run record."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if metrics is not None:
            updates.append("metrics_json = ?")
            values.append(json.dumps(metrics))
        if total_return is not None:
            updates.append("total_return = ?")
            values.append(total_return)
        if sharpe_ratio is not None:
            updates.append("sharpe_ratio = ?")
            values.append(sharpe_ratio)
        if max_drawdown is not None:
            updates.append("max_drawdown = ?")
            values.append(max_drawdown)
        if win_rate is not None:
            updates.append("win_rate = ?")
            values.append(win_rate)
        if start_date is not None:
            updates.append("start_date = ?")
            values.append(start_date)
        if end_date is not None:
            updates.append("end_date = ?")
            values.append(end_date)
        if duration_seconds is not None:
            updates.append("duration_seconds = ?")
            values.append(duration_seconds)
        if model_path is not None:
            updates.append("model_path = ?")
            values.append(model_path)
        if report_path is not None:
            updates.append("report_path = ?")
            values.append(report_path)
        if chart_path is not None:
            updates.append("chart_path = ?")
            values.append(chart_path)
        if name is not None:
            updates.append("name = ?")
            values.append(name)
        if description is not None:
            updates.append("description = ?")
            values.append(description)
        if tags is not None:
            updates.append("tags = ?")
            values.append(",".join(tags))
        
        if not updates:
            return False
        
        values.append(run_id)
        query = f"UPDATE runs SET {', '.join(updates)} WHERE run_id = ?"
        cursor.execute(query, values)
        
        conn.commit()
        conn.close()
        
        return cursor.rowcount > 0
    
    def get_run(self, run_id: str) -> Optional[RunRecord]:
        """Get a run by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        return RunRecord.from_row(row) if row else None
    
    def list_runs(
        self,
        run_type: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        ascending: bool = False,
    ) -> List[RunRecord]:
        """List runs with optional filtering."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM runs WHERE 1=1"
        params = []
        
        if run_type:
            query += " AND run_type = ?"
            params.append(run_type)
        if status:
            query += " AND status = ?"
            params.append(status)
        if tags:
            for tag in tags:
                query += " AND tags LIKE ?"
                params.append(f"%{tag}%")
        
        order_dir = "ASC" if ascending else "DESC"
        query += f" ORDER BY {order_by} {order_dir} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        conn.close()
        
        return [RunRecord.from_row(row) for row in rows]
    
    def delete_run(self, run_id: str) -> bool:
        """Delete a run and all associated data."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Delete with cascading (handled by foreign keys)
        cursor.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if deleted:
            logger.info(f"Deleted run {run_id}")
        
        return deleted
    
    def delete_runs(self, run_ids: List[str]) -> int:
        """Delete multiple runs."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        placeholders = ",".join("?" * len(run_ids))
        cursor.execute(f"DELETE FROM runs WHERE run_id IN ({placeholders})", run_ids)
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted {deleted} runs")
        return deleted
    
    # =========================================================================
    # Stock Scores Operations
    # =========================================================================
    
    def add_stock_scores(
        self,
        run_id: str,
        scores: List[Dict[str, Any]],
    ) -> int:
        """
        Add stock scores for a run.
        
        Args:
            run_id: Run identifier
            scores: List of score dictionaries with keys:
                    ticker, score, rank, features, shap, predicted_return, actual_return
                    
        Returns:
            Number of scores added
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for score in scores:
            cursor.execute("""
                INSERT OR REPLACE INTO stock_scores (
                    run_id, ticker, score, rank,
                    features_json, shap_json,
                    predicted_return, actual_return
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                score.get('ticker'),
                score.get('score'),
                score.get('rank'),
                json.dumps(score.get('features')) if score.get('features') else None,
                json.dumps(score.get('shap')) if score.get('shap') else None,
                score.get('predicted_return'),
                score.get('actual_return'),
            ))
        
        conn.commit()
        conn.close()
        
        return len(scores)
    
    def get_stock_scores(
        self,
        run_id: str,
        top_n: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get stock scores for a run."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT * FROM stock_scores 
            WHERE run_id = ? 
            ORDER BY rank ASC
        """
        if top_n:
            query += f" LIMIT {top_n}"
        
        cursor.execute(query, (run_id,))
        rows = cursor.fetchall()
        
        conn.close()
        
        results = []
        for row in rows:
            record = dict(row)
            if record.get('features_json'):
                record['features'] = json.loads(record['features_json'])
            if record.get('shap_json'):
                record['shap'] = json.loads(record['shap_json'])
            results.append(record)
        
        return results
    
    # =========================================================================
    # Trade History Operations
    # =========================================================================
    
    def add_trades(self, run_id: str, trades: List[Dict[str, Any]]) -> int:
        """Add trade records for a run."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for trade in trades:
            cursor.execute("""
                INSERT INTO trades (
                    run_id, date, ticker, action,
                    quantity, price, value, commission
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                trade.get('date'),
                trade.get('ticker'),
                trade.get('action'),
                trade.get('quantity'),
                trade.get('price'),
                trade.get('value'),
                trade.get('commission'),
            ))
        
        conn.commit()
        conn.close()
        
        return len(trades)
    
    def get_trades(self, run_id: str) -> List[Dict[str, Any]]:
        """Get trades for a run."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM trades WHERE run_id = ? ORDER BY date",
            (run_id,)
        )
        rows = cursor.fetchall()
        
        conn.close()
        return [dict(row) for row in rows]
    
    # =========================================================================
    # Portfolio History Operations
    # =========================================================================
    
    def add_portfolio_history(
        self,
        run_id: str,
        history: List[Dict[str, Any]],
    ) -> int:
        """Add portfolio history for a run."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for record in history:
            cursor.execute("""
                INSERT INTO portfolio_history (
                    run_id, date, portfolio_value, benchmark_value,
                    cash, positions_json
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                record.get('date'),
                record.get('portfolio_value'),
                record.get('benchmark_value'),
                record.get('cash'),
                json.dumps(record.get('positions')) if record.get('positions') else None,
            ))
        
        conn.commit()
        conn.close()
        
        return len(history)
    
    def get_portfolio_history(self, run_id: str) -> List[Dict[str, Any]]:
        """Get portfolio history for a run."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM portfolio_history WHERE run_id = ? ORDER BY date",
            (run_id,)
        )
        rows = cursor.fetchall()
        
        conn.close()
        
        results = []
        for row in rows:
            record = dict(row)
            if record.get('positions_json'):
                record['positions'] = json.loads(record['positions_json'])
            results.append(record)
        
        return results
    
    # =========================================================================
    # Statistics & Analytics
    # =========================================================================
    
    def get_run_stats(self) -> Dict[str, Any]:
        """Get overall statistics about runs."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total counts
        cursor.execute("SELECT COUNT(*) as count FROM runs")
        stats['total_runs'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM runs WHERE status = 'completed'")
        stats['completed_runs'] = cursor.fetchone()['count']
        
        # By type
        cursor.execute("""
            SELECT run_type, COUNT(*) as count 
            FROM runs GROUP BY run_type
        """)
        stats['by_type'] = {row['run_type']: row['count'] for row in cursor.fetchall()}
        
        # Best performing runs
        cursor.execute("""
            SELECT run_id, name, total_return, sharpe_ratio 
            FROM runs 
            WHERE status = 'completed' AND total_return IS NOT NULL
            ORDER BY total_return DESC LIMIT 5
        """)
        stats['top_returns'] = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT run_id, name, total_return, sharpe_ratio 
            FROM runs 
            WHERE status = 'completed' AND sharpe_ratio IS NOT NULL
            ORDER BY sharpe_ratio DESC LIMIT 5
        """)
        stats['top_sharpe'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return stats
    
    def compare_runs(self, run_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple runs."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        placeholders = ",".join("?" * len(run_ids))
        cursor.execute(f"""
            SELECT run_id, name, run_type, created_at,
                   total_return, sharpe_ratio, max_drawdown, win_rate,
                   start_date, end_date, universe_count, tags
            FROM runs 
            WHERE run_id IN ({placeholders})
        """, run_ids)
        
        runs = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        if not runs:
            return {"error": "No runs found"}
        
        # Calculate comparison metrics
        comparison = {
            "runs": runs,
            "metrics": {},
        }
        
        for metric in ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']:
            values = [r[metric] for r in runs if r[metric] is not None]
            if values:
                comparison['metrics'][metric] = {
                    'min': min(values),
                    'max': max(values),
                    'mean': sum(values) / len(values),
                    'best_run': max(runs, key=lambda x: x[metric] or float('-inf'))['run_id'],
                }
        
        return comparison
