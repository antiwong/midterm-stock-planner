"""
Sentiment adapter — bridges SentimentPulse DuckDB to the engine and trigger layer.

Primary (and only) source: DuckDB database (data/sentimentpulse.db),
synced from the office Mac via rsync every 30 minutes.

Delivers data to:
  1. SentimentTriggerLayer.evaluate() — full feature set (new architecture)
  2. Engine feature pipeline via load_sentimentpulse_features()
  3. Weight calibrator via build_calibration_dataset()

IMPORTANT: Feedback columns (actual_return_*, signal_correct_*) are stripped
on read. They live in the feedback table and must NEVER leak into features.
"""

import logging
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DUCKDB_PATH = PROJECT_ROOT / "data" / "sentimentpulse.db"

# Columns that are feedback / outcomes — must never appear in features
_FEEDBACK_COLUMNS = {
    "actual_return_5d", "actual_return_10d", "actual_return_20d",
    "signal_correct_5d", "signal_correct_10d", "signal_correct_20d",
    "trigger_alpha", "trigger_gate_alpha",
}

# SentimentPulse columns that map to engine features
_SCORE_COLUMNS = [
    "finnhub_score", "av_score", "massive_score", "eodhd_score",
    "marketaux_score", "llm_score", "stocktwits_score", "apewisdom_score",
    "fmp_score",
]


def _get_conn(db_path: Optional[Path] = None):
    """Open a read-only DuckDB connection."""
    import duckdb
    path = str(db_path or DUCKDB_PATH)
    return duckdb.connect(path, read_only=True)


def _strip_feedback_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Remove feedback columns that must never appear in feature data."""
    leak = _FEEDBACK_COLUMNS & set(df.columns)
    if leak:
        warnings.warn(f"Feedback columns {sorted(leak)} found — dropping them.")
        df = df.drop(columns=list(leak))
    return df


# ---------------------------------------------------------------------------
# Core readers — used by trigger layer and engine
# ---------------------------------------------------------------------------

def load_sentimentpulse_raw(
    days: int = 90,
    db_path: Optional[Path] = None,
) -> pd.DataFrame:
    """Load raw SentimentPulse feature rows from DuckDB.

    Returns all columns from sentiment_features table, with feedback
    columns stripped to prevent look-ahead bias.

    Args:
        days: How many days of history to load
        db_path: Override default DuckDB path

    Returns:
        DataFrame sorted by (ticker, date), or empty DataFrame if no data
    """
    conn = _get_conn(db_path)
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = conn.execute(
            "SELECT * FROM sentiment_features WHERE date >= ? ORDER BY ticker, date",
            [cutoff],
        ).fetchdf()
        if df.empty:
            logger.warning("No sentiment_features found in DuckDB for last %d days", days)
            return pd.DataFrame()
        df["date"] = pd.to_datetime(df["date"])
        df = _strip_feedback_cols(df)
        logger.debug("Loaded %d sentiment rows from DuckDB (%d days)", len(df), days)
        return df.reset_index(drop=True)
    except Exception as e:
        logger.error("Failed to read sentiment_features from DuckDB: %s", e)
        return pd.DataFrame()
    finally:
        conn.close()


def load_sentimentpulse_for_trigger(
    ticker: str,
    lookback_days: int = 30,
    db_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Load SentimentPulse feature rows for a single ticker (trigger layer).

    Args:
        ticker: Stock symbol (e.g., AAPL, D05.SI)
        lookback_days: How many days of history to load
        db_path: Override default DuckDB path

    Returns:
        DataFrame sorted by date desc, or empty DataFrame if no data
    """
    conn = _get_conn(db_path)
    try:
        cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        df = conn.execute(
            "SELECT * FROM sentiment_features WHERE ticker = ? AND date >= ? ORDER BY date DESC",
            [ticker, cutoff],
        ).fetchdf()
        if df.empty:
            return pd.DataFrame()
        df["date"] = pd.to_datetime(df["date"])
        df = _strip_feedback_cols(df)
        return df.reset_index(drop=True)
    except Exception as e:
        logger.error("Failed to read sentiment for %s: %s", ticker, e)
        return pd.DataFrame()
    finally:
        conn.close()


def prepare_sentiment_from_sentimentpulse(
    raw_df: pd.DataFrame,
    lookbacks: List[int] = [1, 7, 14],
) -> pd.DataFrame:
    """Convert SentimentPulse raw data to engine-compatible sentiment features.

    Maps SentimentPulse's rich schema to the aggregator's expected format,
    then computes rolling features.

    Produces columns:
        - sentiment_daily_mean  (from composite_score)
        - sentiment_daily_std   (from source_agreement, or 0 if unavailable)
        - sentiment_daily_count (from headline_count)
        - sentiment_has_data    (True where data exists)
        - sentiment_mean_{N}d, sentiment_std_{N}d, sentiment_count_{N}d, sentiment_trend_{N}d
        - Plus SentimentPulse-native columns: composite_score, signal_breadth,
          signal_conviction, sentiment_regime, buzz_ratio, confidence
    """
    from .aggregator import compute_sentiment_features

    if raw_df.empty:
        return pd.DataFrame(columns=["date", "ticker"])

    df = raw_df.copy()

    # Map SentimentPulse columns → aggregator schema
    df["sentiment_daily_mean"] = df.get("composite_score", pd.Series(dtype=float)).fillna(0.0)
    df["sentiment_daily_std"] = df.get("source_agreement", pd.Series(dtype=float)).fillna(0.0)
    df["sentiment_daily_count"] = df.get("headline_count", pd.Series(dtype=float)).fillna(0).astype(int)
    df["sentiment_daily_min"] = df["sentiment_daily_mean"]
    df["sentiment_daily_max"] = df["sentiment_daily_mean"]

    # Compute rolling features using existing aggregator
    features = compute_sentiment_features(df, lookbacks=lookbacks)

    # Carry forward SentimentPulse-native columns that the trigger layer uses
    native_cols = [
        "composite_score", "signal_breadth", "signal_conviction",
        "sentiment_regime", "sentiment_regime_encoded",
        "buzz_ratio", "confidence", "headline_count",
        "divergence_flag", "divergence_direction",
        "forward_event_detected", "forward_event_type",
        "analyst_action_detected", "analyst_firm", "analyst_action_type",
        "conviction_asymmetry", "source_agreement",
    ]
    for col in native_cols:
        if col in df.columns and col not in features.columns:
            features[col] = df[col].values

    features["sentiment_has_data"] = features["sentiment_daily_count"] > 0
    return features


def load_sentimentpulse_features(
    days: int = 90,
    lookbacks: List[int] = [1, 7, 14],
    db_path: Optional[Path] = None,
) -> pd.DataFrame:
    """End-to-end: load from DuckDB and produce engine-ready sentiment features.

    This is the primary entry point for the feature pipeline,
    replacing the legacy ``prepare_sentiment_from_news()`` path.

    Args:
        days: How many days of data to load.
        lookbacks: Rolling window sizes for sentiment features.
        db_path: Override default DuckDB path.

    Returns:
        DataFrame ready to merge with price data via ``add_sentiment_features()``.
    """
    raw = load_sentimentpulse_raw(days=days, db_path=db_path)
    if raw.empty:
        return pd.DataFrame(columns=["date", "ticker"])
    return prepare_sentiment_from_sentimentpulse(raw, lookbacks=lookbacks)


# ---------------------------------------------------------------------------
# Multi-ticker loader (used by trigger layer batch evaluation)
# ---------------------------------------------------------------------------

def load_sentimentpulse_for_tickers(
    tickers: list,
    as_of_date: pd.Timestamp,
    lookback_days: int = 30,
    db_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Load SentimentPulse features for multiple tickers up to as_of_date.

    Prevents look-ahead by filtering date <= as_of_date.

    Args:
        tickers: List of ticker symbols to load
        as_of_date: Load data up to this date (prevents look-ahead)
        lookback_days: How many days of history
        db_path: Override default DuckDB path

    Returns:
        DataFrame with all SentimentPulse feature columns
    """
    conn = _get_conn(db_path)
    try:
        cutoff = (as_of_date - pd.Timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        as_of_str = as_of_date.strftime("%Y-%m-%d")
        placeholders = ", ".join(["?"] * len(tickers))
        df = conn.execute(
            f"SELECT * FROM sentiment_features "
            f"WHERE ticker IN ({placeholders}) AND date >= ? AND date <= ? "
            f"ORDER BY ticker, date",
            tickers + [cutoff, as_of_str],
        ).fetchdf()
        if df.empty:
            return pd.DataFrame(columns=["ticker", "date"])
        df["date"] = pd.to_datetime(df["date"])
        df = _strip_feedback_cols(df)
        logger.info("Loaded %d sentiment rows for %d tickers from DuckDB", len(df), len(tickers))
        return df.reset_index(drop=True)
    except Exception as e:
        logger.error("Failed to read sentiment for tickers: %s", e)
        return pd.DataFrame(columns=["ticker", "date"])
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Data availability check
# ---------------------------------------------------------------------------

def has_sentimentpulse_data(
    min_days: int = 7,
    db_path: Optional[Path] = None,
) -> bool:
    """Check if SentimentPulse DuckDB has enough data to enable the trigger."""
    path = db_path or DUCKDB_PATH
    if not path.exists():
        return False
    try:
        import duckdb
        con = duckdb.connect(str(path), read_only=True)
        distinct_dates = con.execute(
            "SELECT COUNT(DISTINCT date) FROM sentiment_features"
        ).fetchone()[0]
        con.close()
        return distinct_dates >= min_days
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Calibration dataset builder
# ---------------------------------------------------------------------------

def build_calibration_dataset(
    db_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Join features with feedback on run_id — the ONLY safe way to combine them.

    Used by weight_calibrator.py for monthly recalibration.
    """
    conn = _get_conn(db_path)
    try:
        features_df = conn.execute("SELECT * FROM sentiment_features").fetchdf()
        feedback_df = conn.execute("SELECT * FROM feedback").fetchdf()
        if features_df.empty or feedback_df.empty:
            logger.info("Calibration: features=%d rows, feedback=%d rows",
                        len(features_df), len(feedback_df))
            return pd.DataFrame()
        labeled = features_df.merge(
            feedback_df, on=["run_id", "ticker", "date"], how="inner",
            suffixes=("", "_feedback"),
        )
        logger.info("Built calibration dataset: %d labeled rows", len(labeled))
        return labeled
    except Exception as e:
        logger.error("Failed to build calibration dataset: %s", e)
        return pd.DataFrame()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# DuckDB stats (used by API health endpoint)
# ---------------------------------------------------------------------------

def get_table_stats(db_path: Optional[Path] = None) -> dict:
    """Return row counts and latest dates for all tables."""
    conn = _get_conn(db_path)
    try:
        tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
        stats = {}
        for t in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            stats[t] = {"rows": count}
            try:
                latest = conn.execute(f"SELECT MAX(date) FROM {t}").fetchone()[0]
                stats[t]["latest"] = str(latest) if latest else None
            except Exception:
                pass
        return stats
    finally:
        conn.close()
