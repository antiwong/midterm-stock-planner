"""Database helpers for the trading API.

Thin wrapper over src.data.shared_db — the shared database layer used by both
myFuture (FastAPI) and QuantaAlpha (Streamlit).
"""

import time
import json
import hashlib
from functools import wraps
from typing import Any
import pandas as pd

# --- CSV caching with TTL ---
_csv_cache: dict[str, tuple[float, pd.DataFrame]] = {}
CSV_TTL = 60  # seconds

# --- API response caching with TTL ---
_response_cache: dict[str, tuple[float, Any]] = {}


def cached_response(ttl: int = 30):
    """Decorator to cache API endpoint responses for `ttl` seconds.
    Cache key is derived from the function name + arguments."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key_data = f"{func.__module__}.{func.__name__}:{args}:{sorted(kwargs.items())}"
            key = hashlib.md5(key_data.encode()).hexdigest()
            now = time.time()
            if key in _response_cache:
                cached_at, result = _response_cache[key]
                if now - cached_at < ttl:
                    return result
            result = func(*args, **kwargs)
            _response_cache[key] = (now, result)
            return result
        return wrapper
    return decorator


def read_csv_cached(path: str) -> pd.DataFrame:
    """Read a CSV with a 60-second TTL cache. Returns a copy to avoid mutation."""
    now = time.time()
    key = str(path)
    if key in _csv_cache:
        ts, df = _csv_cache[key]
        if now - ts < CSV_TTL:
            return df.copy()
    df = pd.read_csv(key)
    _csv_cache[key] = (now, df)
    return df.copy()


from src.data.shared_db import (
    DATA_DIR,
    WATCHLISTS,
    get_active_watchlists,
    get_paper_db,
    get_forward_db,
    query_paper,
    query_forward,
    get_prices,
    get_moby_analysis,
    get_analysis_db,
    load_runs_from_db,
    load_run_by_id,
    get_analysis_result,
    load_regression_results,
    load_ensemble_comparison,
    load_stress_test,
    load_watchlist_config,
    load_ticker_configs,
)

def ensure_indexes():
    """Create indexes on commonly queried columns in paper trading and forward journal DBs."""
    import sqlite3

    # Paper trading DBs
    for wl in get_active_watchlists():
        db_path = DATA_DIR / f"paper_trading_{wl}.db"
        if not db_path.exists():
            continue
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_positions_active ON positions(is_active)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_date ON daily_snapshots(date)")
            conn.commit()
        finally:
            conn.close()

    # Forward journal DB
    fwd_path = DATA_DIR / "forward_journal.db"
    if fwd_path.exists():
        conn = sqlite3.connect(str(fwd_path))
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fwd_ticker ON predictions(ticker)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fwd_date ON predictions(prediction_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fwd_evaluated ON predictions(evaluated_at)")
            conn.commit()
        finally:
            conn.close()


__all__ = [
    "DATA_DIR",
    "WATCHLISTS",
    "get_active_watchlists",
    "read_csv_cached",
    "ensure_indexes",
    "get_paper_db",
    "get_forward_db",
    "query_paper",
    "query_forward",
    "get_prices",
    "get_moby_analysis",
    "get_analysis_db",
    "load_runs_from_db",
    "load_run_by_id",
    "get_analysis_result",
    "load_regression_results",
    "load_ensemble_comparison",
    "load_stress_test",
    "load_watchlist_config",
    "load_ticker_configs",
]


# --- DuckDB per-request connection ---

DUCKDB_PATH = DATA_DIR / "sentimentpulse.db"


def get_duckdb_conn():
    """Open a fresh read-only DuckDB connection (per-request).

    DuckDB opens in ~1ms so per-request is fast. Using a persistent
    connection would hold a file lock that blocks the SentimentPulse
    crawler from writing (both run on the same server).
    """
    import duckdb

    if not DUCKDB_PATH.exists():
        return None

    return duckdb.connect(str(DUCKDB_PATH), read_only=True)
