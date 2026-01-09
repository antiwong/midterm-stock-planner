"""Feature engineering module for mid-term stock planner.

This module provides functions to compute features from raw price and fundamental
data, and to create training datasets with proper label alignment.

Features include:
- Return features (1m, 3m, 6m, 12m)
- Volatility features (20d, 60d rolling std)
- Volume features (dollar volume, turnover)
- Valuation features (PE, PB from fundamentals)
- Technical indicators (RSI, MACD, Bollinger Bands, ATR, ADX)
- Momentum features (composite score, relative strength, trend)
- Mean reversion features (z-scores, distance from MA)
- Sentiment features (news sentiment aggregates)
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Union
from pathlib import Path


def add_return_features(price_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add return-based features to price data.
    
    Features added:
    - return_1m: 1-month (21 trading days) return
    - return_3m: 3-month (63 trading days) return
    - return_6m: 6-month (126 trading days) return
    - return_12m: 12-month (252 trading days) return
    
    Args:
        price_df: DataFrame with columns ['date', 'ticker', 'close']
    
    Returns:
        DataFrame with added return features
    """
    df = price_df.copy()
    df = df.sort_values(['ticker', 'date'])
    
    df["return_1m"] = df.groupby("ticker")["close"].pct_change(21)
    df["return_3m"] = df.groupby("ticker")["close"].pct_change(63)
    df["return_6m"] = df.groupby("ticker")["close"].pct_change(126)
    df["return_12m"] = df.groupby("ticker")["close"].pct_change(252)
    
    return df


def add_volatility_features(price_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add volatility-based features to price data.
    
    Features added:
    - vol_20d: 20-day rolling standard deviation of daily returns
    - vol_60d: 60-day rolling standard deviation of daily returns
    
    Args:
        price_df: DataFrame with columns ['date', 'ticker', 'close']
    
    Returns:
        DataFrame with added volatility features
    """
    df = price_df.copy()
    df = df.sort_values(['ticker', 'date'])
    
    # Compute daily returns first
    df['daily_return'] = df.groupby('ticker')['close'].pct_change()
    
    # Rolling volatility
    df['vol_20d'] = df.groupby('ticker')['daily_return'].transform(
        lambda x: x.rolling(window=20, min_periods=10).std()
    )
    df['vol_60d'] = df.groupby('ticker')['daily_return'].transform(
        lambda x: x.rolling(window=60, min_periods=30).std()
    )
    
    # Drop intermediate column
    df = df.drop(columns=['daily_return'])
    
    return df


def add_volume_features(price_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add volume-based features to price data.
    
    Features added:
    - dollar_volume_20d: 20-day average dollar volume (close * volume)
    - turnover_20d: 20-day average turnover ratio (volume / avg volume)
    - volume_ratio: Current volume relative to 20-day average
    
    Args:
        price_df: DataFrame with columns ['date', 'ticker', 'close', 'volume']
    
    Returns:
        DataFrame with added volume features
    """
    df = price_df.copy()
    df = df.sort_values(['ticker', 'date'])
    
    # Dollar volume
    df['dollar_volume'] = df['close'] * df['volume']
    df['dollar_volume_20d'] = df.groupby('ticker')['dollar_volume'].transform(
        lambda x: x.rolling(window=20, min_periods=10).mean()
    )
    
    # Volume ratio (current vs average)
    df['avg_volume_20d'] = df.groupby('ticker')['volume'].transform(
        lambda x: x.rolling(window=20, min_periods=10).mean()
    )
    df['volume_ratio'] = df['volume'] / df['avg_volume_20d']
    
    # Turnover (relative volume change)
    df['turnover_20d'] = df.groupby('ticker')['volume'].transform(
        lambda x: x.rolling(window=20, min_periods=10).std() / x.rolling(window=20, min_periods=10).mean()
    )
    
    # Drop intermediate columns
    df = df.drop(columns=['dollar_volume', 'avg_volume_20d'])
    
    return df


def add_valuation_features(
    price_df: pd.DataFrame,
    fundamental_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Add valuation-based features by merging fundamental data.
    
    Features added (if fundamental_df provided):
    - pe_ratio: Price-to-earnings ratio
    - pb_ratio: Price-to-book ratio
    - earnings_yield: Inverse of PE ratio
    
    Fundamental values are forward-filled to handle infrequent updates.
    
    Args:
        price_df: DataFrame with columns ['date', 'ticker', 'close']
        fundamental_df: Optional DataFrame with columns ['date', 'ticker', 'pe', 'pb', ...]
    
    Returns:
        DataFrame with added valuation features
    """
    df = price_df.copy()
    
    if fundamental_df is None or len(fundamental_df) == 0:
        # No fundamental data, return as-is
        return df
    
    fund_df = fundamental_df.copy()
    
    # Ensure date columns are datetime
    df['date'] = pd.to_datetime(df['date'])
    fund_df['date'] = pd.to_datetime(fund_df['date'])
    
    # For each ticker, merge fundamentals using merge_asof
    result_dfs = []
    
    for ticker in df['ticker'].unique():
        ticker_prices = df[df['ticker'] == ticker].copy()
        ticker_fund = fund_df[fund_df['ticker'] == ticker].copy()
        
        if len(ticker_fund) == 0:
            # No fundamentals for this ticker
            result_dfs.append(ticker_prices)
            continue
        
        # Sort by date (required for merge_asof)
        ticker_prices = ticker_prices.sort_values('date')
        ticker_fund = ticker_fund.sort_values('date')
        
        # Get fundamental columns (excluding date and ticker)
        fund_cols = [c for c in ticker_fund.columns if c not in ['date', 'ticker']]
        
        # Merge using merge_asof for point-in-time accuracy
        merged = pd.merge_asof(
            ticker_prices,
            ticker_fund[['date'] + fund_cols],
            on='date',
            direction='backward'
        )
        
        result_dfs.append(merged)
    
    df = pd.concat(result_dfs, ignore_index=True)
    
    # Rename columns if they exist
    rename_map = {}
    if 'pe' in df.columns:
        rename_map['pe'] = 'pe_ratio'
    if 'pb' in df.columns:
        rename_map['pb'] = 'pb_ratio'
    
    if rename_map:
        df = df.rename(columns=rename_map)
    
    # Add earnings yield if PE exists
    if 'pe_ratio' in df.columns:
        df['earnings_yield'] = 1.0 / df['pe_ratio'].replace(0, np.nan)
    
    return df


def compute_all_features(
    price_df: pd.DataFrame,
    fundamental_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Orchestrator function that computes all features in the correct order.
    
    Args:
        price_df: DataFrame with columns ['date', 'ticker', 'open', 'high', 'low', 'close', 'volume']
        fundamental_df: Optional DataFrame with fundamental data
    
    Returns:
        DataFrame with all features computed
    """
    df = price_df.copy()
    
    # Ensure proper sorting
    df = df.sort_values(['ticker', 'date'])
    
    # Compute features in order (dependencies respected)
    df = add_return_features(df)
    df = add_volatility_features(df)
    df = add_volume_features(df)
    df = add_valuation_features(df, fundamental_df)
    
    return df


def make_training_dataset(
    feature_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    horizon_days: int = 63,
    target_col: str = "target",
) -> pd.DataFrame:
    """
    Create a training dataset with features and target (excess return).
    
    Each row is (date, ticker, features, target) where target is the
    forward excess return over the specified horizon.
    
    Target = stock forward return - benchmark forward return
    
    Args:
        feature_df: DataFrame with columns ['date', 'ticker', 'close'] plus feature columns.
                    Should be sorted by (ticker, date).
        benchmark_df: DataFrame with columns ['date'] and a price column ('close', 'price', or 'value').
                     Should be sorted by date.
        horizon_days: Number of trading days forward to compute returns (default: 63 for ~3 months).
        target_col: Name for the target column (default: "target").
    
    Returns:
        DataFrame with all original columns plus the target column.
        Rows where forward returns cannot be computed are dropped.
    """
    df = feature_df.copy()
    benchmark = benchmark_df.copy()
    
    # Ensure date columns are datetime
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
    if not pd.api.types.is_datetime64_any_dtype(benchmark['date']):
        benchmark['date'] = pd.to_datetime(benchmark['date'])
    
    # Identify the price column in benchmark_df
    price_cols = ['close', 'price', 'value']
    benchmark_price_col = None
    for col in price_cols:
        if col in benchmark.columns:
            benchmark_price_col = col
            break
    
    if benchmark_price_col is None:
        raise ValueError(
            f"benchmark_df must contain one of {price_cols}. "
            f"Found columns: {benchmark.columns.tolist()}"
        )
    
    # Sort data
    df = df.sort_values(['ticker', 'date'])
    benchmark = benchmark.sort_values('date')
    
    # Compute forward returns for each stock
    def _compute_forward_return(group: pd.DataFrame) -> pd.Series:
        """Compute forward return for a single ticker."""
        group = group.sort_values('date')
        future_price = group['close'].shift(-horizon_days)
        current_price = group['close']
        forward_return = (future_price / current_price) - 1.0
        return forward_return
    
    df['_forward_return'] = df.groupby('ticker', group_keys=False).apply(
        lambda g: _compute_forward_return(g)
    ).reset_index(level=0, drop=True)
    
    # Compute forward returns for benchmark
    benchmark['_benchmark_forward_return'] = (
        benchmark[benchmark_price_col].shift(-horizon_days) / benchmark[benchmark_price_col]
    ) - 1.0
    
    # Merge benchmark forward returns into feature dataframe
    benchmark_returns = benchmark[['date', '_benchmark_forward_return']]
    
    df = df.merge(
        benchmark_returns,
        on='date',
        how='left'
    )
    
    # Compute excess return (target)
    df[target_col] = df['_forward_return'] - df['_benchmark_forward_return']
    
    # Drop rows where we couldn't compute forward returns
    df = df.dropna(subset=[target_col, '_forward_return', '_benchmark_forward_return'])
    
    # Drop intermediate columns
    df = df.drop(columns=['_forward_return', '_benchmark_forward_return'])
    
    return df


def get_feature_columns(df: pd.DataFrame) -> List[str]:
    """
    Get list of feature column names from a DataFrame.
    
    Excludes metadata columns (date, ticker) and target column.
    
    Args:
        df: DataFrame with features
    
    Returns:
        List of feature column names
    """
    exclude_cols = {'date', 'ticker', 'target', 'open', 'high', 'low', 'close', 'volume'}
    feature_cols = [c for c in df.columns if c not in exclude_cols and not c.startswith('_')]
    return feature_cols


def add_sentiment_features(
    base_feature_df: pd.DataFrame,
    sentiment_feature_df: pd.DataFrame,
    fillna_value: Optional[float] = 0.0,
) -> pd.DataFrame:
    """
    Merge sentiment features into the main feature DataFrame.
    
    This function integrates pre-computed sentiment features (from the
    sentiment module) into the price-based feature DataFrame by matching
    on (date, ticker).
    
    Args:
        base_feature_df: DataFrame with price-based features and (date, ticker).
        sentiment_feature_df: DataFrame with sentiment features from
                             sentiment.aggregator.prepare_sentiment_features().
        fillna_value: Value to fill missing sentiment features. Use 0.0 for
                     neutral sentiment, or None to keep NaN.
    
    Returns:
        DataFrame with sentiment features merged in.
    """
    df = base_feature_df.copy()
    sent_df = sentiment_feature_df.copy()
    
    # Ensure date columns are datetime
    df['date'] = pd.to_datetime(df['date'])
    sent_df['date'] = pd.to_datetime(sent_df['date'])
    
    # Remove timezone if present
    if df['date'].dt.tz is not None:
        df['date'] = df['date'].dt.tz_localize(None)
    if sent_df['date'].dt.tz is not None:
        sent_df['date'] = sent_df['date'].dt.tz_localize(None)
    
    # Get sentiment feature columns (exclude date, ticker, and daily aggregates)
    sentiment_cols = [c for c in sent_df.columns 
                      if c.startswith('sentiment_') and c not in 
                      ['sentiment_daily_mean', 'sentiment_daily_std', 
                       'sentiment_daily_count', 'sentiment_daily_min', 
                       'sentiment_daily_max']]
    
    # If no rolling features, include daily features
    if len(sentiment_cols) == 0:
        sentiment_cols = [c for c in sent_df.columns 
                         if c.startswith('sentiment_')]
    
    # Merge on date and ticker
    merge_cols = ['date', 'ticker'] + sentiment_cols
    merge_cols = [c for c in merge_cols if c in sent_df.columns]
    
    df = df.merge(
        sent_df[merge_cols],
        on=['date', 'ticker'],
        how='left'
    )
    
    # Fill missing values
    if fillna_value is not None:
        for col in sentiment_cols:
            if col in df.columns:
                df[col] = df[col].fillna(fillna_value)
    
    return df


def prepare_sentiment_from_news(
    news_df: pd.DataFrame,
    lookbacks: List[int] = [1, 7, 14],
    model_type: str = "lexicon",
    text_col: str = "headline",
    market_close_hour: int = 16,
    min_daily_count: int = 1,
) -> pd.DataFrame:
    """
    Prepare sentiment features from raw news data.
    
    This is a convenience function that wraps the sentiment module's
    functionality for use in feature engineering.
    
    Args:
        news_df: Raw news DataFrame with timestamp, ticker, headline columns.
        lookbacks: Lookback periods for rolling sentiment features.
        model_type: Sentiment model type ("dummy", "lexicon", "finbert").
        text_col: Column containing text to analyze.
        market_close_hour: Hour at which market closes.
        min_daily_count: Minimum articles per day to compute sentiment.
    
    Returns:
        DataFrame with sentiment features ready to merge with price data.
    """
    try:
        from ..sentiment.news_loader import load_news_data
        from ..sentiment.sentiment_model import score_news_items, get_sentiment_model
        from ..sentiment.aggregator import (
            align_to_trading_dates,
            aggregate_daily_sentiment,
            compute_sentiment_features,
        )
    except ImportError as e:
        raise ImportError(
            f"Sentiment module not available: {e}. "
            "Make sure src/sentiment/ package is installed."
        )
    
    df = news_df.copy()
    
    # Score news items
    model = get_sentiment_model(model_type)
    df = score_news_items(df, text_col=text_col, model=model)
    
    # Align to trading dates
    df = align_to_trading_dates(df, market_close_hour=market_close_hour)
    
    # Aggregate to daily
    daily_df = aggregate_daily_sentiment(
        df,
        sentiment_col="sentiment_raw",
        date_col="trading_date",
        min_count=min_daily_count,
    )
    
    # Compute rolling features
    feature_df = compute_sentiment_features(daily_df, lookbacks=lookbacks)
    
    return feature_df


def compute_all_features_with_sentiment(
    price_df: pd.DataFrame,
    fundamental_df: Optional[pd.DataFrame] = None,
    benchmark_df: Optional[pd.DataFrame] = None,
    news_df: Optional[pd.DataFrame] = None,
    sentiment_lookbacks: List[int] = [1, 7, 14],
    sentiment_model_type: str = "lexicon",
    sentiment_fillna: float = 0.0,
    include_technical: bool = True,
    include_momentum: bool = True,
    include_mean_reversion: bool = True,
) -> pd.DataFrame:
    """
    Compute all features including sentiment.
    
    This is an extended version of compute_all_features_extended that
    also integrates sentiment features from news data.
    
    Args:
        price_df: DataFrame with OHLCV data.
        fundamental_df: Optional DataFrame with fundamental data.
        benchmark_df: Optional benchmark DataFrame.
        news_df: Optional news DataFrame for sentiment features.
        sentiment_lookbacks: Lookback periods for sentiment.
        sentiment_model_type: Type of sentiment model.
        sentiment_fillna: Value for missing sentiment.
        include_technical: Whether to add technical indicators.
        include_momentum: Whether to add momentum features.
        include_mean_reversion: Whether to add mean reversion features.
    
    Returns:
        DataFrame with all features including sentiment.
    """
    # Compute base features
    df = compute_all_features_extended(
        price_df=price_df,
        fundamental_df=fundamental_df,
        benchmark_df=benchmark_df,
        include_technical=include_technical,
        include_momentum=include_momentum,
        include_mean_reversion=include_mean_reversion,
    )
    
    # Add sentiment features if news data provided
    if news_df is not None and len(news_df) > 0:
        try:
            sentiment_features = prepare_sentiment_from_news(
                news_df=news_df,
                lookbacks=sentiment_lookbacks,
                model_type=sentiment_model_type,
            )
            
            df = add_sentiment_features(
                df,
                sentiment_features,
                fillna_value=sentiment_fillna,
            )
        except Exception as e:
            import warnings
            warnings.warn(f"Failed to add sentiment features: {e}")
    
    return df


def get_sentiment_feature_columns(lookbacks: List[int] = [1, 7, 14]) -> List[str]:
    """
    Get list of sentiment feature column names.
    
    Args:
        lookbacks: Lookback periods used for sentiment features.
    
    Returns:
        List of sentiment feature column names.
    """
    features = []
    for lb in lookbacks:
        features.extend([
            f"sentiment_mean_{lb}d",
            f"sentiment_std_{lb}d",
            f"sentiment_count_{lb}d",
            f"sentiment_trend_{lb}d",
        ])
    return features


def compute_all_features_extended(
    price_df: pd.DataFrame,
    fundamental_df: Optional[pd.DataFrame] = None,
    benchmark_df: Optional[pd.DataFrame] = None,
    include_technical: bool = True,
    include_momentum: bool = True,
    include_mean_reversion: bool = True,
) -> pd.DataFrame:
    """
    Compute all features including technical indicators and strategy features.
    
    This is an extended version of compute_all_features that includes:
    - Basic features (returns, volatility, volume, valuation)
    - Technical indicators (RSI, MACD, Bollinger Bands, ATR, ADX)
    - Momentum features (composite score, relative strength)
    - Mean reversion features (z-scores, distance from MA)
    
    Args:
        price_df: DataFrame with columns ['date', 'ticker', 'open', 'high', 'low', 'close', 'volume']
        fundamental_df: Optional DataFrame with fundamental data
        benchmark_df: Optional benchmark DataFrame for relative strength
        include_technical: Whether to add technical indicators
        include_momentum: Whether to add momentum features
        include_mean_reversion: Whether to add mean reversion features
    
    Returns:
        DataFrame with all features computed
    """
    df = price_df.copy()
    
    # Ensure proper sorting
    df = df.sort_values(['ticker', 'date'])
    
    # Compute basic features
    df = add_return_features(df)
    df = add_volatility_features(df)
    df = add_volume_features(df)
    df = add_valuation_features(df, fundamental_df)
    
    # Add technical indicators
    if include_technical:
        try:
            from ..indicators.technical import (
                calculate_rsi,
                calculate_macd,
                calculate_bollinger_bands,
                calculate_atr,
                calculate_adx,
            )
            
            df = calculate_rsi(df, period=14)
            df = calculate_macd(df)
            df = calculate_bollinger_bands(df)
            
            # ATR and ADX require high/low/close
            if all(col in df.columns for col in ['high', 'low', 'close']):
                df = calculate_atr(df, period=14)
                df = calculate_adx(df, period=14)
        except ImportError:
            pass  # Technical indicators module not available
    
    # Add momentum features
    if include_momentum:
        try:
            from ..strategies.momentum import (
                calculate_momentum_score,
                calculate_relative_strength,
                calculate_52w_high_low_distance,
            )
            
            df = calculate_momentum_score(df)
            df = calculate_52w_high_low_distance(df)
            
            if benchmark_df is not None:
                df = calculate_relative_strength(df, benchmark_df, lookback_days=63)
        except ImportError:
            pass  # Momentum module not available
    
    # Add mean reversion features
    if include_mean_reversion:
        try:
            from ..strategies.mean_reversion import (
                calculate_mean_reversion_score,
                calculate_zscore,
            )
            
            df = calculate_zscore(df, lookback_days=20)
            df = df.rename(columns={'zscore': 'zscore_20d'})
            
            df = calculate_zscore(df, lookback_days=60)
            df = df.rename(columns={'zscore': 'zscore_60d'})
            
            df = calculate_mean_reversion_score(df)
        except ImportError:
            pass  # Mean reversion module not available
    
    return df
