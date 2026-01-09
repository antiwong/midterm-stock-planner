"""Mean reversion features and signals for panel data (date, ticker)."""

import pandas as pd
import numpy as np
from typing import Optional, List


def calculate_zscore(
    df: pd.DataFrame,
    lookback_days: int = 60,
    price_col: str = "close"
) -> pd.DataFrame:
    """
    Calculate z-score of price relative to its rolling mean per ticker.
    
    Z-score = (price - mean) / std
    High positive z-score = overbought (potential mean reversion short)
    High negative z-score = oversold (potential mean reversion long)
    
    Args:
        df: DataFrame with columns ['date', 'ticker', price_col]
        lookback_days: Lookback period for mean and std calculation
        price_col: Column name for price data
    
    Returns:
        DataFrame with added 'zscore' column
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    def _zscore_for_ticker(group: pd.DataFrame) -> pd.Series:
        price = group[price_col]
        rolling_mean = price.rolling(window=lookback_days, min_periods=lookback_days // 2).mean()
        rolling_std = price.rolling(window=lookback_days, min_periods=lookback_days // 2).std()
        zscore = (price - rolling_mean) / rolling_std.replace(0, np.nan)
        return zscore
    
    df["zscore"] = df.groupby("ticker", group_keys=False).apply(
        lambda g: _zscore_for_ticker(g)
    ).reset_index(level=0, drop=True)
    
    return df


def calculate_mean_reversion_score(
    df: pd.DataFrame,
    short_lookback: int = 20,
    long_lookback: int = 60
) -> pd.DataFrame:
    """
    Calculate mean reversion score per ticker.
    
    Combines short-term and long-term z-scores to identify mean reversion opportunities.
    Negative score = oversold (buy signal), Positive score = overbought (sell signal)
    
    Args:
        df: DataFrame with columns ['date', 'ticker', 'close']
        short_lookback: Short-term lookback period
        long_lookback: Long-term lookback period
    
    Returns:
        DataFrame with added 'mean_reversion_score' column
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    # Calculate short and long-term z-scores
    def _zscore(group: pd.DataFrame, lookback: int) -> pd.Series:
        price = group["close"]
        rolling_mean = price.rolling(window=lookback, min_periods=lookback // 2).mean()
        rolling_std = price.rolling(window=lookback, min_periods=lookback // 2).std()
        return (price - rolling_mean) / rolling_std.replace(0, np.nan)
    
    df["_zscore_short"] = df.groupby("ticker", group_keys=False).apply(
        lambda g: _zscore(g, short_lookback)
    ).reset_index(level=0, drop=True)
    
    df["_zscore_long"] = df.groupby("ticker", group_keys=False).apply(
        lambda g: _zscore(g, long_lookback)
    ).reset_index(level=0, drop=True)
    
    # Mean reversion score: average of z-scores (more negative = more oversold)
    df["mean_reversion_score"] = (df["_zscore_short"] + df["_zscore_long"]) / 2.0
    
    # Rank across stocks (lower score = better mean reversion buy candidate)
    df["mean_reversion_rank"] = df.groupby("date")["mean_reversion_score"].rank(pct=True)
    
    # Clean up
    df = df.drop(columns=["_zscore_short", "_zscore_long"])
    
    return df


def calculate_mean_reversion_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate comprehensive mean reversion features per ticker.
    
    Features added:
    - zscore_20d, zscore_60d: Price z-scores at different lookbacks
    - distance_to_sma20, distance_to_sma50: Distance from moving averages
    - mean_reversion_score: Composite mean reversion score
    - mean_reversion_rank: Cross-sectional rank
    - oversold_indicator: Binary indicator for extreme oversold
    - overbought_indicator: Binary indicator for extreme overbought
    
    Args:
        df: DataFrame with columns ['date', 'ticker', 'close']
    
    Returns:
        DataFrame with all mean reversion features added
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    # Z-scores at multiple lookbacks
    df = calculate_zscore(df, lookback_days=20)
    df = df.rename(columns={"zscore": "zscore_20d"})
    
    df = calculate_zscore(df, lookback_days=60)
    df = df.rename(columns={"zscore": "zscore_60d"})
    
    # Distance from moving averages (as percentage)
    df["sma_20"] = df.groupby("ticker")["close"].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )
    df["sma_50"] = df.groupby("ticker")["close"].transform(
        lambda x: x.rolling(50, min_periods=25).mean()
    )
    
    df["distance_to_sma20"] = (df["close"] / df["sma_20"]) - 1.0
    df["distance_to_sma50"] = (df["close"] / df["sma_50"]) - 1.0
    
    # Clean up SMA columns (we only want the distance)
    df = df.drop(columns=["sma_20", "sma_50"])
    
    # Composite mean reversion score
    df = calculate_mean_reversion_score(df)
    
    # Extreme indicators
    df["oversold_indicator"] = (df["zscore_20d"] < -2.0).astype(float)
    df["overbought_indicator"] = (df["zscore_20d"] > 2.0).astype(float)
    
    return df


def calculate_rsi_divergence(
    df: pd.DataFrame,
    rsi_col: str = "rsi",
    lookback_days: int = 21
) -> pd.DataFrame:
    """
    Identify price/RSI divergence (classic mean reversion signal).
    
    Bullish divergence: Price makes lower low, RSI makes higher low
    Bearish divergence: Price makes higher high, RSI makes lower high
    
    Args:
        df: DataFrame with columns ['date', 'ticker', 'close', rsi_col]
        rsi_col: Name of RSI column
        lookback_days: Lookback period for finding highs/lows
    
    Returns:
        DataFrame with added 'bullish_divergence', 'bearish_divergence' columns
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    if rsi_col not in df.columns:
        raise ValueError(f"Column '{rsi_col}' not found. Calculate RSI first.")
    
    def _divergence_for_ticker(group: pd.DataFrame) -> pd.DataFrame:
        close = group["close"]
        rsi = group[rsi_col]
        
        # Rolling min/max
        price_low = close.rolling(lookback_days, min_periods=lookback_days // 2).min()
        price_high = close.rolling(lookback_days, min_periods=lookback_days // 2).max()
        rsi_low = rsi.rolling(lookback_days, min_periods=lookback_days // 2).min()
        rsi_high = rsi.rolling(lookback_days, min_periods=lookback_days // 2).max()
        
        # Previous period values
        prev_price_low = price_low.shift(lookback_days)
        prev_price_high = price_high.shift(lookback_days)
        prev_rsi_low = rsi_low.shift(lookback_days)
        prev_rsi_high = rsi_high.shift(lookback_days)
        
        # Bullish divergence: price lower low, RSI higher low
        bullish = ((price_low < prev_price_low) & (rsi_low > prev_rsi_low)).astype(float)
        
        # Bearish divergence: price higher high, RSI lower high
        bearish = ((price_high > prev_price_high) & (rsi_high < prev_rsi_high)).astype(float)
        
        return pd.DataFrame({
            "bullish_divergence": bullish,
            "bearish_divergence": bearish
        }, index=group.index)
    
    div_df = df.groupby("ticker", group_keys=False).apply(_divergence_for_ticker)
    df["bullish_divergence"] = div_df["bullish_divergence"]
    df["bearish_divergence"] = div_df["bearish_divergence"]
    
    return df
