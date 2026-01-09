"""Model prediction module for mid-term stock planner.

This module provides functions to load trained models and make predictions,
returning scores and rankings for stock selection.
"""

import warnings
from typing import List, Optional, Tuple

import pandas as pd
import numpy as np

from .trainer import load_model as _load_model, ModelMetadata


def load_model(model_dir: str):
    """
    Load a trained model with its metadata.
    
    This is a convenience wrapper around trainer.load_model().
    
    Args:
        model_dir: Path to the model directory.
    
    Returns:
        Tuple of (model, metadata)
    """
    return _load_model(model_dir)


def predict(
    model,
    feature_df: pd.DataFrame,
    feature_names: List[str],
    metadata: Optional[ModelMetadata] = None,
    include_rankings: bool = True,
) -> pd.DataFrame:
    """
    Make predictions using a trained model.
    
    Args:
        model: Trained LightGBM model.
        feature_df: DataFrame with columns ['date', 'ticker'] plus feature columns.
        feature_names: List of feature column names to use for prediction.
        metadata: Optional model metadata for feature validation.
        include_rankings: Whether to include ranking columns (default: True).
    
    Returns:
        DataFrame with columns:
        - date: Original date column
        - ticker: Original ticker column
        - score: Model prediction score
        - rank: Rank within each date (1 = highest score, if include_rankings=True)
        - percentile: Percentile within each date (if include_rankings=True)
    """
    df = feature_df.copy()
    
    # Validate features if metadata provided
    if metadata is not None:
        expected_features = set(metadata.feature_names)
        provided_features = set(feature_names)
        
        missing = expected_features - provided_features
        extra = provided_features - expected_features
        
        if missing:
            warnings.warn(
                f"Missing features (will use 0): {missing}",
                UserWarning
            )
        if extra:
            warnings.warn(
                f"Extra features (will be ignored): {extra}",
                UserWarning
            )
        
        # Use expected features in the correct order
        feature_names = metadata.feature_names
    
    # Prepare feature matrix
    X = df[feature_names].copy()
    
    # Handle missing features by filling with 0
    for col in feature_names:
        if col not in X.columns:
            X[col] = 0.0
    
    # Make sure columns are in the right order
    X = X[feature_names]
    
    # Handle NaN values
    X = X.fillna(0.0)
    
    # Make predictions
    scores = model.predict(X)
    
    # Build result DataFrame
    result = pd.DataFrame({
        'date': df['date'],
        'ticker': df['ticker'],
        'score': scores,
    })
    
    if include_rankings:
        # Rank within each date (higher score = better rank = lower number)
        result['rank'] = result.groupby('date')['score'].rank(
            ascending=False, method='min'
        ).astype(int)
        
        # Percentile within each date
        result['percentile'] = result.groupby('date')['score'].rank(
            pct=True
        ) * 100
    
    return result


def score_universe(
    model_dir: str,
    feature_df: pd.DataFrame,
    date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Score a universe of stocks for a given date.
    
    Convenience function that loads a model and makes predictions
    for a specific date (or the latest date in the data).
    
    Args:
        model_dir: Path to the model directory.
        feature_df: DataFrame with features for the universe.
        date: Specific date to score. If None, uses the latest date.
    
    Returns:
        DataFrame with scores and rankings, sorted by rank.
    """
    # Load model
    model, metadata = load_model(model_dir)
    
    # Filter to specific date if provided
    df = feature_df.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    if date is not None:
        date = pd.to_datetime(date)
        df = df[df['date'] == date]
    else:
        # Use latest date
        latest_date = df['date'].max()
        df = df[df['date'] == latest_date]
    
    if len(df) == 0:
        raise ValueError(f"No data found for date: {date}")
    
    # Make predictions
    result = predict(
        model=model,
        feature_df=df,
        feature_names=metadata.feature_names,
        metadata=metadata,
        include_rankings=True,
    )
    
    # Sort by rank
    result = result.sort_values(['date', 'rank'])
    
    return result


def get_top_stocks(
    predictions: pd.DataFrame,
    n: Optional[int] = None,
    top_pct: Optional[float] = None,
) -> pd.DataFrame:
    """
    Get top-ranked stocks from predictions.
    
    Args:
        predictions: DataFrame with predictions and rankings.
        n: Number of top stocks to return. If None, uses top_pct.
        top_pct: Percentage of top stocks to return (e.g., 0.1 for top 10%).
    
    Returns:
        DataFrame with top stocks.
    """
    if n is None and top_pct is None:
        # Default to top decile
        top_pct = 0.1
    
    result_dfs = []
    
    for date, group in predictions.groupby('date'):
        if n is not None:
            top = group.nsmallest(n, 'rank')
        else:
            threshold = int(len(group) * top_pct)
            threshold = max(threshold, 1)  # At least 1 stock
            top = group.nsmallest(threshold, 'rank')
        
        result_dfs.append(top)
    
    if not result_dfs:
        return pd.DataFrame()
    
    return pd.concat(result_dfs, ignore_index=True)
