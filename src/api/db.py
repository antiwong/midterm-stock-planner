"""Database helpers for the trading API. Read-only access to SQLite DBs and CSV files."""

import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

DATA_DIR = Path(__file__).parent.parent.parent / "data"

WATCHLISTS = ["moby_picks", "tech_giants", "semiconductors", "precious_metals"]


def get_paper_db(watchlist: str) -> Optional[sqlite3.Connection]:
    """Get read-only connection to a paper trading DB."""
    db_path = DATA_DIR / f"paper_trading_{watchlist}.db"
    if not db_path.exists():
        return None
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_forward_db() -> Optional[sqlite3.Connection]:
    """Get read-only connection to forward journal DB."""
    db_path = DATA_DIR / "forward_journal.db"
    if not db_path.exists():
        return None
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def query_paper(watchlist: str, sql: str, params=()) -> List[Dict[str, Any]]:
    """Run a query against a paper trading DB."""
    conn = get_paper_db(watchlist)
    if conn is None:
        return []
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_forward(sql: str, params=()) -> List[Dict[str, Any]]:
    """Run a query against the forward journal DB."""
    conn = get_forward_db()
    if conn is None:
        return []
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# Cache prices in memory (~50MB for 280K rows)
_prices_cache: Optional[pd.DataFrame] = None
_prices_mtime: float = 0


def get_prices() -> pd.DataFrame:
    """Get cached prices DataFrame. Reloads if file changed."""
    global _prices_cache, _prices_mtime
    path = DATA_DIR / "prices_daily.csv"
    if not path.exists():
        return pd.DataFrame()
    mtime = path.stat().st_mtime
    if _prices_cache is None or mtime > _prices_mtime:
        _prices_cache = pd.read_csv(path)
        _prices_cache["date"] = pd.to_datetime(_prices_cache["date"], format="mixed")
        _prices_mtime = mtime
    return _prices_cache


def get_moby_analysis() -> pd.DataFrame:
    """Load Moby analysis CSV."""
    path = DATA_DIR / "sentiment" / "moby_analysis.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)
