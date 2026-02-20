"""Overnight and gap-based features (QuantaAlpha-inspired).

Robust under regime shifts: gap factors capture information released during
non-trading hours and auction-driven price discovery. See QuantaAlpha paper
(arXiv:2602.07085) for empirical support.

Features:
- overnight_gap_pct: (open - prev_close) / prev_close
- gap_vs_true_range: overnight gap normalized by true range (GapZ-style)
- gap_acceptance_score: intraday direction accepts (1) or rejects (-1) the gap
- gap_acceptance_vol_weighted: volume-weighted gap acceptance
"""

import pandas as pd
import numpy as np
from typing import Optional


def add_overnight_gap_pct(
    df: pd.DataFrame,
    open_col: str = "open",
    close_col: str = "close",
) -> pd.DataFrame:
    """
    Add overnight gap as percentage of previous close.

    overnight_gap_pct = (open - prev_close) / prev_close
    Stored as decimal (e.g. 0.02 = 2%).

    Args:
        df: DataFrame with ['date', 'ticker', open_col, close_col]
        open_col: Open price column
        close_col: Close price column

    Returns:
        DataFrame with added 'overnight_gap_pct'
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])

    prev_close = df.groupby("ticker")[close_col].shift(1)
    df["overnight_gap_pct"] = (df[open_col] - prev_close) / prev_close.replace(0, np.nan)

    return df


def add_gap_vs_true_range(
    df: pd.DataFrame,
    lookback: int = 10,
    open_col: str = "open",
    close_col: str = "close",
    high_col: str = "high",
    low_col: str = "low",
) -> pd.DataFrame:
    """
    Overnight gap normalized by rolling true range (GapZ-style).

    gap_vs_true_range = (open - prev_close) / rolling_mean(true_range, lookback)
    True range = max(high - low, |high - prev_close|, |low - prev_close|)

    Robust: scales gap by recent volatility so large gaps in volatile regimes
    are not over-weighted.

    Args:
        df: DataFrame with OHLC
        lookback: Rolling window for true range (default 10)
        open_col, close_col, high_col, low_col: Column names

    Returns:
        DataFrame with added 'gap_vs_true_range'
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])

    def _tr_and_gap(group: pd.DataFrame) -> pd.DataFrame:
        close = group[close_col]
        high = group[high_col]
        low = group[low_col]
        open_ = group[open_col]
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        tr_mean = true_range.rolling(window=lookback, min_periods=lookback).mean()
        overnight_gap = open_ - prev_close
        gap_vs_tr = overnight_gap / tr_mean.replace(0, np.nan)

        return pd.DataFrame(
            {"gap_vs_true_range": gap_vs_tr},
            index=group.index,
        )

    out = df.groupby("ticker", group_keys=False).apply(_tr_and_gap)
    df["gap_vs_true_range"] = out["gap_vs_true_range"]

    return df


def add_gap_acceptance_score(
    df: pd.DataFrame,
    open_col: str = "open",
    close_col: str = "close",
) -> pd.DataFrame:
    """
    Intraday acceptance/rejection of overnight gap.

    Logic:
    - Gap up (open > prev_close): accept=1 if close > open (continued up), -1 if close < open
    - Gap down (open < prev_close): accept=1 if close < open (continued down), -1 if close > open
    - No gap: 0

    Stored as -1, 0, or 1. Use rolling mean for smoothed score.

    Args:
        df: DataFrame with ['date', 'ticker', open_col, close_col]

    Returns:
        DataFrame with added 'gap_acceptance_raw'
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])

    prev_close = df.groupby("ticker")[close_col].shift(1)
    overnight_gap = df[open_col] - prev_close
    intraday_move = df[close_col] - df[open_col]

    # Same sign = acceptance (gap and intraday move in same direction)
    # Gap up + close>open = accept; gap down + close<open = accept
    accept = np.sign(overnight_gap) * np.sign(intraday_move)
    df["gap_acceptance_raw"] = accept.replace(0, np.nan)  # 0 only when no gap

    return df


def add_gap_acceptance_rolling(
    df: pd.DataFrame,
    window: int = 20,
    raw_col: str = "gap_acceptance_raw",
) -> pd.DataFrame:
    """
    Rolling mean of gap acceptance score.

    gap_acceptance_score_20d = mean(gap_acceptance_raw) over 20d
    """
    df = df.copy()
    if raw_col not in df.columns:
        raise ValueError(f"Column '{raw_col}' required. Run add_gap_acceptance_score first.")

    df["gap_acceptance_score_" + str(window) + "d"] = (
        df.groupby("ticker")[raw_col]
        .transform(lambda x: x.rolling(window=window, min_periods=window).mean())
    )
    return df


def add_gap_acceptance_vol_weighted(
    df: pd.DataFrame,
    window: int = 20,
    raw_col: str = "gap_acceptance_raw",
    volume_col: str = "volume",
) -> pd.DataFrame:
    """
    Volume-weighted gap acceptance score.

    Weights each day's acceptance by volume_ratio = volume / avg_volume_20d
    to emphasize information-rich openings with high participation.
    """
    df = df.copy()
    if raw_col not in df.columns:
        raise ValueError(f"Column '{raw_col}' required. Run add_gap_acceptance_score first.")
    if volume_col not in df.columns:
        df["gap_acceptance_vol_weighted_" + str(window) + "d"] = np.nan
        return df

    col_name = "gap_acceptance_vol_weighted_" + str(window) + "d"
    vals = []
    for _, group in df.groupby("ticker"):
        vol = group[volume_col]
        avg_vol = vol.rolling(window=window, min_periods=window).mean()
        vol_ratio = vol / avg_vol.replace(0, np.nan)
        raw = group[raw_col]
        weighted = (raw * vol_ratio).rolling(window=window, min_periods=window).sum()
        denom = vol_ratio.rolling(window=window, min_periods=window).sum()
        s = weighted / denom.replace(0, np.nan)
        vals.append(s)
    df[col_name] = pd.concat(vals, axis=0)

    return df


def add_gap_features(
    df: pd.DataFrame,
    gap_vs_tr_lookback: int = 10,
    acceptance_window: int = 20,
    include_vol_weighted: bool = True,
) -> pd.DataFrame:
    """
    Add all gap-based features in one call.

    Features added:
    - overnight_gap_pct
    - gap_vs_true_range (if high, low available)
    - gap_acceptance_raw
    - gap_acceptance_score_{window}d
    - gap_acceptance_vol_weighted_{window}d (if volume available)

    Args:
        df: DataFrame with ['date', 'ticker', 'open', 'high', 'low', 'close', 'volume']
        gap_vs_tr_lookback: Lookback for true range normalization
        acceptance_window: Window for rolling acceptance
        include_vol_weighted: Whether to add volume-weighted acceptance

    Returns:
        DataFrame with gap features
    """
    df = add_overnight_gap_pct(df)
    df = add_gap_acceptance_score(df)

    if all(c in df.columns for c in ["high", "low"]):
        df = add_gap_vs_true_range(df, lookback=gap_vs_tr_lookback)

    df = add_gap_acceptance_rolling(df, window=acceptance_window)

    if include_vol_weighted and "volume" in df.columns:
        df = add_gap_acceptance_vol_weighted(df, window=acceptance_window)

    return df
