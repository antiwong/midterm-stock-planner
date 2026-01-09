"""Sentiment aggregation for feature engineering.

This module provides functions to:
- Align news sentiment to trading dates
- Aggregate per-article sentiment to per-ticker daily sentiment
- Compute rolling sentiment features suitable for model input
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Union
import warnings


def align_to_trading_dates(
    news_df: pd.DataFrame,
    trading_calendar: Optional[pd.DatetimeIndex] = None,
    market_close_hour: int = 16,
) -> pd.DataFrame:
    """
    Align news timestamps to trading dates.
    
    News published before market close is assigned to that trading day.
    News published after market close is assigned to the next trading day.
    
    Args:
        news_df: News DataFrame with 'timestamp' column.
        trading_calendar: Optional trading calendar. If None, uses all dates.
        market_close_hour: Hour at which market closes (default: 4pm).
    
    Returns:
        DataFrame with added 'trading_date' column.
    """
    df = news_df.copy()
    
    # Ensure timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    # Extract date and hour
    df["_date"] = df["timestamp"].dt.normalize()
    df["_hour"] = df["timestamp"].dt.hour
    
    # Assign trading date based on publication time
    # News after market close -> next trading day
    df["trading_date"] = df["_date"]
    after_close_mask = df["_hour"] >= market_close_hour
    df.loc[after_close_mask, "trading_date"] = df.loc[after_close_mask, "_date"] + pd.Timedelta(days=1)
    
    # If trading calendar provided, snap to next valid trading day
    if trading_calendar is not None:
        # Sort calendar
        trading_calendar = trading_calendar.sort_values()
        
        def snap_to_trading_day(date):
            # Find next trading day >= date
            valid_days = trading_calendar[trading_calendar >= date]
            if len(valid_days) > 0:
                return valid_days[0]
            return date  # Fallback to original date
        
        df["trading_date"] = df["trading_date"].apply(snap_to_trading_day)
    
    # Clean up
    df = df.drop(columns=["_date", "_hour"])
    
    return df


def aggregate_daily_sentiment(
    news_df: pd.DataFrame,
    sentiment_col: str = "sentiment_raw",
    date_col: str = "trading_date",
    ticker_col: str = "ticker",
    min_count: int = 1,
) -> pd.DataFrame:
    """
    Aggregate per-article sentiment to daily per-ticker sentiment.
    
    Args:
        news_df: News DataFrame with sentiment scores.
        sentiment_col: Column containing sentiment scores.
        date_col: Column containing trading dates.
        ticker_col: Column containing stock tickers.
        min_count: Minimum number of articles to compute aggregates.
    
    Returns:
        DataFrame with columns:
        - date
        - ticker
        - sentiment_daily_mean: Mean sentiment for the day
        - sentiment_daily_std: Std of sentiment for the day
        - sentiment_daily_count: Number of articles
        - sentiment_daily_min: Min sentiment
        - sentiment_daily_max: Max sentiment
    """
    df = news_df.copy()
    
    # Ensure required columns exist
    required_cols = [date_col, ticker_col, sentiment_col]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Ensure date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])
    
    # Remove timezone for grouping
    if df[date_col].dt.tz is not None:
        df[date_col] = df[date_col].dt.tz_localize(None)
    
    # Group by date and ticker
    grouped = df.groupby([date_col, ticker_col])[sentiment_col]
    
    # Compute aggregates
    agg_df = grouped.agg(
        sentiment_daily_mean="mean",
        sentiment_daily_std="std",
        sentiment_daily_count="count",
        sentiment_daily_min="min",
        sentiment_daily_max="max",
    ).reset_index()
    
    # Rename columns
    agg_df = agg_df.rename(columns={date_col: "date", ticker_col: "ticker"})
    
    # Filter by minimum count
    agg_df = agg_df[agg_df["sentiment_daily_count"] >= min_count].copy()
    
    # Fill NaN std with 0 (when count=1)
    agg_df["sentiment_daily_std"] = agg_df["sentiment_daily_std"].fillna(0)
    
    # Sort
    agg_df = agg_df.sort_values(["ticker", "date"]).reset_index(drop=True)
    
    return agg_df


def compute_sentiment_features(
    daily_sentiment_df: pd.DataFrame,
    lookbacks: List[int] = [1, 3, 7, 14],
    min_periods: Optional[Dict[int, int]] = None,
) -> pd.DataFrame:
    """
    Compute rolling sentiment features from daily aggregates.
    
    For each lookback period, computes:
    - sentiment_mean_{lookback}d: Rolling mean sentiment
    - sentiment_std_{lookback}d: Rolling std of sentiment
    - sentiment_count_{lookback}d: Rolling sum of article counts
    - sentiment_trend_{lookback}d: Recent vs older sentiment (momentum)
    
    Args:
        daily_sentiment_df: Daily sentiment DataFrame from aggregate_daily_sentiment.
        lookbacks: List of lookback periods in days.
        min_periods: Dict mapping lookback to minimum periods required.
                    Defaults to lookback // 2 for each.
    
    Returns:
        DataFrame with rolling sentiment features added.
    """
    df = daily_sentiment_df.copy()
    
    # Ensure date is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])
    
    # Sort by ticker and date
    df = df.sort_values(["ticker", "date"])
    
    # Default min_periods
    if min_periods is None:
        min_periods = {lb: max(1, lb // 2) for lb in lookbacks}
    
    # Process each lookback
    for lookback in lookbacks:
        min_p = min_periods.get(lookback, max(1, lookback // 2))
        
        # Rolling mean of daily sentiment
        df[f"sentiment_mean_{lookback}d"] = df.groupby("ticker")["sentiment_daily_mean"].transform(
            lambda x: x.rolling(lookback, min_periods=min_p).mean()
        )
        
        # Rolling std of daily sentiment
        df[f"sentiment_std_{lookback}d"] = df.groupby("ticker")["sentiment_daily_mean"].transform(
            lambda x: x.rolling(lookback, min_periods=min_p).std()
        )
        
        # Rolling sum of article counts (news volume)
        df[f"sentiment_count_{lookback}d"] = df.groupby("ticker")["sentiment_daily_count"].transform(
            lambda x: x.rolling(lookback, min_periods=min_p).sum()
        )
        
        # Sentiment trend: compare recent half to older half
        half_lookback = max(1, lookback // 2)
        recent_mean = df.groupby("ticker")["sentiment_daily_mean"].transform(
            lambda x: x.rolling(half_lookback, min_periods=1).mean()
        )
        older_mean = df.groupby("ticker")["sentiment_daily_mean"].transform(
            lambda x: x.shift(half_lookback).rolling(half_lookback, min_periods=1).mean()
        )
        df[f"sentiment_trend_{lookback}d"] = recent_mean - older_mean
    
    # Fill NaN std with 0
    for lookback in lookbacks:
        df[f"sentiment_std_{lookback}d"] = df[f"sentiment_std_{lookback}d"].fillna(0)
    
    return df


def prepare_sentiment_features(
    news_df: pd.DataFrame,
    sentiment_col: str = "sentiment_raw",
    lookbacks: List[int] = [1, 7, 14],
    trading_calendar: Optional[pd.DatetimeIndex] = None,
    market_close_hour: int = 16,
    min_daily_count: int = 1,
) -> pd.DataFrame:
    """
    End-to-end pipeline to prepare sentiment features from raw news data.
    
    Steps:
    1. Align news to trading dates
    2. Aggregate to daily per-ticker sentiment
    3. Compute rolling features
    
    Args:
        news_df: News DataFrame with sentiment_raw column.
        sentiment_col: Column containing raw sentiment scores.
        lookbacks: Lookback periods for rolling features.
        trading_calendar: Optional trading calendar for date alignment.
        market_close_hour: Hour at which market closes.
        min_daily_count: Minimum articles per day to include.
    
    Returns:
        DataFrame with sentiment features ready to merge with price data.
    """
    df = news_df.copy()
    
    # Step 1: Align to trading dates
    df = align_to_trading_dates(
        df,
        trading_calendar=trading_calendar,
        market_close_hour=market_close_hour,
    )
    
    # Step 2: Aggregate to daily
    daily_df = aggregate_daily_sentiment(
        df,
        sentiment_col=sentiment_col,
        date_col="trading_date",
        min_count=min_daily_count,
    )
    
    # Step 3: Compute rolling features
    feature_df = compute_sentiment_features(
        daily_df,
        lookbacks=lookbacks,
    )
    
    return feature_df


def merge_sentiment_features(
    price_df: pd.DataFrame,
    sentiment_feature_df: pd.DataFrame,
    fillna_value: Optional[float] = 0.0,
) -> pd.DataFrame:
    """
    Merge sentiment features into price DataFrame.
    
    Args:
        price_df: Price DataFrame with 'date' and 'ticker' columns.
        sentiment_feature_df: Sentiment features from prepare_sentiment_features.
        fillna_value: Value to fill missing sentiment (None to keep NaN).
    
    Returns:
        Price DataFrame with sentiment features merged.
    """
    df = price_df.copy()
    
    # Ensure date columns are datetime
    df["date"] = pd.to_datetime(df["date"])
    sentiment_feature_df = sentiment_feature_df.copy()
    sentiment_feature_df["date"] = pd.to_datetime(sentiment_feature_df["date"])
    
    # Remove timezone if present
    if df["date"].dt.tz is not None:
        df["date"] = df["date"].dt.tz_localize(None)
    if sentiment_feature_df["date"].dt.tz is not None:
        sentiment_feature_df["date"] = sentiment_feature_df["date"].dt.tz_localize(None)
    
    # Get sentiment feature columns (exclude date and ticker)
    sentiment_cols = [c for c in sentiment_feature_df.columns 
                      if c not in ["date", "ticker"]]
    
    # Merge
    df = df.merge(
        sentiment_feature_df[["date", "ticker"] + sentiment_cols],
        on=["date", "ticker"],
        how="left",
    )
    
    # Fill missing values
    if fillna_value is not None:
        for col in sentiment_cols:
            df[col] = df[col].fillna(fillna_value)
    
    return df


def get_sentiment_feature_names(lookbacks: List[int] = [1, 7, 14]) -> List[str]:
    """
    Get list of sentiment feature column names for given lookbacks.
    
    Args:
        lookbacks: Lookback periods.
    
    Returns:
        List of feature column names.
    """
    features = []
    for lookback in lookbacks:
        features.extend([
            f"sentiment_mean_{lookback}d",
            f"sentiment_std_{lookback}d",
            f"sentiment_count_{lookback}d",
            f"sentiment_trend_{lookback}d",
        ])
    return features
