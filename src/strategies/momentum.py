"""Momentum-based features and signals for panel data (date, ticker)."""

import pandas as pd
import numpy as np
from typing import Optional, List


def calculate_momentum_score(
    df: pd.DataFrame,
    lookback_periods: List[int] = None,
    weights: List[float] = None
) -> pd.DataFrame:
    """
    Calculate composite momentum score per ticker.
    
    Combines returns over multiple lookback periods into a single score.
    Higher score = stronger momentum.
    
    Args:
        df: DataFrame with columns ['date', 'ticker', 'close']
        lookback_periods: List of lookback periods in days (default [21, 63, 126, 252])
        weights: Weights for each period (default equal weights)
    
    Returns:
        DataFrame with added 'momentum_score' column
    """
    if lookback_periods is None:
        lookback_periods = [21, 63, 126, 252]  # 1M, 3M, 6M, 12M
    
    if weights is None:
        weights = [1.0 / len(lookback_periods)] * len(lookback_periods)
    
    if len(weights) != len(lookback_periods):
        raise ValueError("weights must have same length as lookback_periods")
    
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    # Calculate return for each period
    momentum_cols = []
    for period, weight in zip(lookback_periods, weights):
        col_name = f"_mom_{period}"
        df[col_name] = df.groupby("ticker")["close"].pct_change(period)
        momentum_cols.append((col_name, weight))
    
    # Composite score (weighted average of returns, normalized by cross-sectional rank)
    def _rank_score(group: pd.DataFrame) -> pd.Series:
        score = pd.Series(0.0, index=group.index)
        for col_name, weight in momentum_cols:
            # Rank within each date (cross-sectional)
            rank = group[col_name].rank(pct=True)
            score += weight * rank
        return score
    
    df["momentum_score"] = df.groupby("date", group_keys=False).apply(_rank_score)
    
    # Clean up intermediate columns
    for col_name, _ in momentum_cols:
        df = df.drop(columns=[col_name])
    
    return df


def calculate_relative_strength(
    df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    lookback_days: int = 63
) -> pd.DataFrame:
    """
    Calculate relative strength vs benchmark per ticker.
    
    RS = (stock return - benchmark return) over lookback period
    
    Args:
        df: DataFrame with columns ['date', 'ticker', 'close']
        benchmark_df: DataFrame with columns ['date', 'close'] (or 'price', 'value')
        lookback_days: Lookback period in days
    
    Returns:
        DataFrame with added 'relative_strength' column
    """
    df = df.copy()
    benchmark = benchmark_df.copy()
    df = df.sort_values(["ticker", "date"])
    
    # Identify benchmark price column
    price_cols = ["close", "price", "value"]
    benchmark_price_col = None
    for col in price_cols:
        if col in benchmark.columns:
            benchmark_price_col = col
            break
    
    if benchmark_price_col is None:
        raise ValueError(f"benchmark_df must contain one of {price_cols}")
    
    # Calculate stock returns
    df["_stock_return"] = df.groupby("ticker")["close"].pct_change(lookback_days)
    
    # Calculate benchmark returns
    benchmark = benchmark.sort_values("date")
    benchmark["_benchmark_return"] = benchmark[benchmark_price_col].pct_change(lookback_days)
    
    # Merge benchmark returns
    df = df.merge(
        benchmark[["date", "_benchmark_return"]],
        on="date",
        how="left"
    )
    
    # Relative strength
    df["relative_strength"] = df["_stock_return"] - df["_benchmark_return"]
    
    # Clean up
    df = df.drop(columns=["_stock_return", "_benchmark_return"])
    
    return df


def calculate_price_momentum_features(
    df: pd.DataFrame,
    benchmark_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Calculate comprehensive price momentum features per ticker.
    
    Features added:
    - mom_1m, mom_3m, mom_6m, mom_12m: Raw momentum (returns)
    - mom_1m_rank, mom_3m_rank, etc.: Cross-sectional momentum ranks
    - momentum_score: Composite momentum score
    - relative_strength: Relative strength vs benchmark (if provided)
    - acceleration: Rate of change of momentum (mom_1m - mom_3m/3)
    - trend_strength: Consistency of momentum direction
    
    Args:
        df: DataFrame with columns ['date', 'ticker', 'close']
        benchmark_df: Optional benchmark DataFrame for relative strength
    
    Returns:
        DataFrame with all momentum features added
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    # Raw momentum (returns)
    periods = {"1m": 21, "3m": 63, "6m": 126, "12m": 252}
    for name, days in periods.items():
        df[f"mom_{name}"] = df.groupby("ticker")["close"].pct_change(days)
    
    # Cross-sectional ranks
    for name in periods.keys():
        df[f"mom_{name}_rank"] = df.groupby("date")[f"mom_{name}"].rank(pct=True)
    
    # Composite momentum score
    df = calculate_momentum_score(df)
    
    # Acceleration (short-term momentum vs medium-term momentum)
    df["momentum_acceleration"] = df["mom_1m"] - (df["mom_3m"] / 3.0)
    
    # Trend strength (how consistent is the momentum direction)
    def _trend_strength(group: pd.DataFrame) -> pd.Series:
        close = group["close"]
        # Count positive vs negative daily returns over past 63 days
        daily_ret = close.pct_change()
        pos_ratio = daily_ret.rolling(63, min_periods=21).apply(
            lambda x: (x > 0).sum() / len(x)
        )
        return pos_ratio
    
    df["trend_strength"] = df.groupby("ticker", group_keys=False).apply(
        lambda g: _trend_strength(g)
    ).reset_index(level=0, drop=True)
    
    # Relative strength vs benchmark
    if benchmark_df is not None:
        df = calculate_relative_strength(df, benchmark_df, lookback_days=63)
    
    return df


def calculate_52w_high_low_distance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate distance from 52-week high and low per ticker.
    
    These are classic momentum indicators used by O'Neil (CANSLIM) and others.
    
    Args:
        df: DataFrame with columns ['date', 'ticker', 'close']
    
    Returns:
        DataFrame with added 'distance_52w_high', 'distance_52w_low' columns
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    # 252 trading days ≈ 1 year
    df["_52w_high"] = df.groupby("ticker")["close"].transform(
        lambda x: x.rolling(252, min_periods=126).max()
    )
    df["_52w_low"] = df.groupby("ticker")["close"].transform(
        lambda x: x.rolling(252, min_periods=126).min()
    )
    
    # Distance from high (negative = below high)
    df["distance_52w_high"] = (df["close"] / df["_52w_high"]) - 1.0
    
    # Distance from low (positive = above low)
    df["distance_52w_low"] = (df["close"] / df["_52w_low"]) - 1.0
    
    # Clean up
    df = df.drop(columns=["_52w_high", "_52w_low"])
    
    return df
