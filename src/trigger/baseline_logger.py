"""Ranker baseline logger.

Records which tickers the cross-sectional ranker selected as candidates
and their subsequent actual returns. This provides the baseline that the
trigger layer's performance is measured against.

Trigger Alpha = return_when_trigger_allowed_entry - ranker_baseline_return

If trigger_alpha > 0, the sentiment gate improved entry timing.
If trigger_alpha < 0, the gate filtered out winners — false negatives.

This baseline is computed REGARDLESS of whether the trigger layer is enabled,
so we accumulate comparison data from day 1.

Usage:
    Called by score_latest / paper_trading after the ranker produces candidates.
    Writes to: data/sentiment/feedback/ranker_baseline_YYYY-MM.csv
"""

import logging
import pandas as pd
from datetime import date
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

BASELINE_DIR = Path(__file__).parent.parent.parent / "data" / "sentiment" / "feedback"


def log_ranker_candidates(
    candidates: List[Dict],
    run_date: str,
    watchlist: str = "",
) -> None:
    """Log which tickers the ranker selected as candidates today.

    Args:
        candidates: List of dicts with at minimum {'ticker': str, 'rank': int}.
                    Optionally includes 'predicted_score' from the ranker.
        run_date: YYYY-MM-DD
        watchlist: Which watchlist these candidates are from
    """
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    for c in candidates:
        records.append({
            'date': run_date,
            'ticker': c.get('ticker', ''),
            'ranker_rank': c.get('rank', 0),
            'ranker_score': c.get('predicted_score', c.get('score', None)),
            'watchlist': watchlist,
            'was_ranker_candidate': True,
        })

    if not records:
        return

    month_key = run_date[:7]  # YYYY-MM
    baseline_path = BASELINE_DIR / f"ranker_baseline_{month_key}.csv"

    new_df = pd.DataFrame(records)

    if baseline_path.exists():
        existing = pd.read_csv(baseline_path)
        combined = pd.concat([existing, new_df]).drop_duplicates(
            subset=['date', 'ticker'], keep='last'
        )
    else:
        combined = new_df

    combined.to_csv(baseline_path, index=False)
    logger.info("Logged %d ranker candidates for %s", len(records), run_date)


def load_ranker_baseline(lookback_months: int = 3) -> pd.DataFrame:
    """Load ranker baseline data for trigger alpha computation."""
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(BASELINE_DIR.glob("ranker_baseline_*.csv"))

    if not files:
        return pd.DataFrame()

    # Only load recent months
    dfs = []
    for f in files[-lookback_months:]:
        try:
            dfs.append(pd.read_csv(f))
        except Exception:
            continue

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)


def compute_ranker_baseline_return(
    ticker: str,
    score_date: str,
    baseline_df: pd.DataFrame,
    horizon: int = 5,
) -> float | None:
    """Compute the average return of all ranker candidates on the same date.

    This is the "what if you entered every ranker candidate?" baseline.
    The trigger layer's job is to beat this by selectively timing entries.

    Returns:
        Average return of all ranker candidates on score_date, or None if no data.
    """
    if baseline_df.empty:
        return None

    same_date = baseline_df[baseline_df['date'] == score_date]
    if same_date.empty:
        return None

    # The baseline is: if you entered every candidate the ranker selected,
    # what was the average return?
    # This will be filled by run_feedback.py after actual returns are known
    return_col = f'actual_return_{horizon}d'
    if return_col not in same_date.columns:
        return None

    returns = same_date[return_col].dropna()
    if returns.empty:
        return None

    return float(returns.mean())
