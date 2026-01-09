"""Pipeline module for mid-term stock planner.

This module provides convenience functions that orchestrate common
data processing and analysis workflows.
"""

from pathlib import Path
from typing import List, Optional, Tuple, Union

import pandas as pd

from .data.loader import (
    load_price_data,
    load_fundamental_data,
    load_benchmark_data,
    load_universe,
)
from .features.engineering import (
    compute_all_features,
    compute_all_features_extended,
    make_training_dataset,
    get_feature_columns,
)
from .config.config import AppConfig, DataConfig, FeatureConfig


def prepare_training_data(
    price_path: Union[str, Path],
    benchmark_path: Union[str, Path],
    fundamental_path: Optional[Union[str, Path]] = None,
    universe: Optional[List[str]] = None,
    horizon_days: int = 63,
    target_col: str = "target",
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Prepare training data by loading, computing features, and creating labels.
    
    Orchestrates: load → compute features → make training dataset
    
    Args:
        price_path: Path to price data CSV/Parquet.
        benchmark_path: Path to benchmark data CSV/Parquet.
        fundamental_path: Optional path to fundamental data.
        universe: Optional list of tickers to include. If None, uses all.
        horizon_days: Prediction horizon in trading days.
        target_col: Name for target column.
    
    Returns:
        Tuple of (training_data DataFrame, list of feature column names)
    """
    # Load data
    price_df = load_price_data(price_path)
    benchmark_df = load_benchmark_data(benchmark_path)
    
    fundamental_df = None
    if fundamental_path is not None:
        fundamental_df = load_fundamental_data(fundamental_path)
    
    # Filter to universe if specified
    if universe is not None:
        price_df = price_df[price_df['ticker'].isin(universe)]
        if fundamental_df is not None:
            fundamental_df = fundamental_df[fundamental_df['ticker'].isin(universe)]
    
    # Compute features with technical indicators (RSI, MACD, etc.)
    feature_df = compute_all_features_extended(
        price_df, 
        fundamental_df,
        benchmark_df=benchmark_df,
        include_technical=True,
        include_momentum=True,
        include_mean_reversion=True,
    )
    
    # Create training dataset
    training_df = make_training_dataset(
        feature_df,
        benchmark_df,
        horizon_days=horizon_days,
        target_col=target_col,
    )
    
    # Get feature columns
    feature_cols = get_feature_columns(training_df)
    
    return training_df, feature_cols


def prepare_inference_data(
    price_path: Union[str, Path],
    fundamental_path: Optional[Union[str, Path]] = None,
    universe: Optional[List[str]] = None,
    date: Optional[str] = None,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Prepare data for inference (scoring stocks).
    
    Unlike training data, this doesn't compute targets - only features.
    
    Args:
        price_path: Path to price data CSV/Parquet.
        fundamental_path: Optional path to fundamental data.
        universe: Optional list of tickers to include. If None, uses all.
        date: Optional specific date to filter to. If None, includes all dates.
    
    Returns:
        Tuple of (feature DataFrame, list of feature column names)
    """
    # Load data
    price_df = load_price_data(price_path)
    
    fundamental_df = None
    if fundamental_path is not None:
        fundamental_df = load_fundamental_data(fundamental_path)
    
    # Filter to universe if specified
    if universe is not None:
        price_df = price_df[price_df['ticker'].isin(universe)]
        if fundamental_df is not None:
            fundamental_df = fundamental_df[fundamental_df['ticker'].isin(universe)]
    
    # Compute features
    feature_df = compute_all_features(price_df, fundamental_df)
    
    # Filter to specific date if provided
    if date is not None:
        feature_df['date'] = pd.to_datetime(feature_df['date'])
        date = pd.to_datetime(date)
        feature_df = feature_df[feature_df['date'] == date]
    
    # Get feature columns
    feature_cols = get_feature_columns(feature_df)
    
    return feature_df, feature_cols


def prepare_data_from_config(
    config: AppConfig,
    for_training: bool = True,
    override_universe: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[pd.DataFrame, List[str], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Prepare data using configuration object.
    
    Args:
        config: Application configuration.
        for_training: Whether preparing for training (True) or inference (False).
        override_universe: Optional list of tickers that overrides config.data.universe_path.
                          Use this when a watchlist is provided to bypass universe.txt filtering.
        start_date: Optional start date (YYYY-MM-DD) to filter data.
        end_date: Optional end date (YYYY-MM-DD) to filter data.
    
    Returns:
        If for_training:
            Tuple of (training_data, feature_cols, price_data, benchmark_data)
        If for inference:
            Tuple of (feature_data, feature_cols, price_data, None)
    """
    data_cfg = config.data
    feature_cfg = config.features
    
    # Use override_universe if provided, otherwise load from config
    universe = None
    if override_universe is not None:
        universe = override_universe
    elif data_cfg.universe_path is not None:
        universe = load_universe(data_cfg.universe_path)
    
    # Get date range from config if not provided
    if start_date is None:
        start_date = getattr(config.backtest, 'start_date', None)
    if end_date is None:
        end_date = getattr(config.backtest, 'end_date', None)
    
    if for_training:
        # Prepare training data
        training_df, feature_cols = prepare_training_data(
            price_path=data_cfg.price_data_path,
            benchmark_path=data_cfg.benchmark_data_path,
            fundamental_path=data_cfg.fundamental_data_path,
            universe=universe,
            horizon_days=feature_cfg.horizon_days,
            target_col=config.model.target_col,
        )
        
        # Also load raw data for backtest
        price_df = load_price_data(data_cfg.price_data_path)
        benchmark_df = load_benchmark_data(data_cfg.benchmark_data_path)
        
        if universe is not None:
            price_df = price_df[price_df['ticker'].isin(universe)]
        
        # Apply date filtering
        if start_date is not None:
            start_dt = pd.to_datetime(start_date)
            training_df = training_df[training_df['date'] >= start_dt]
            price_df = price_df[price_df['date'] >= start_dt]
            benchmark_df = benchmark_df[benchmark_df['date'] >= start_dt]
        
        if end_date is not None:
            end_dt = pd.to_datetime(end_date)
            training_df = training_df[training_df['date'] <= end_dt]
            price_df = price_df[price_df['date'] <= end_dt]
            benchmark_df = benchmark_df[benchmark_df['date'] <= end_dt]
        
        return training_df, feature_cols, price_df, benchmark_df
    else:
        # Prepare inference data
        feature_df, feature_cols = prepare_inference_data(
            price_path=data_cfg.price_data_path,
            fundamental_path=data_cfg.fundamental_data_path,
            universe=universe,
        )
        
        price_df = load_price_data(data_cfg.price_data_path)
        if universe is not None:
            price_df = price_df[price_df['ticker'].isin(universe)]
        
        return feature_df, feature_cols, price_df, None


def run_full_pipeline(
    config: AppConfig,
    save_model: bool = True,
    verbose: bool = True,
    universe: Optional[List[str]] = None,
) -> dict:
    """
    Run the full training and backtest pipeline.
    
    Args:
        config: Application configuration.
        save_model: Whether to save the trained model.
        verbose: Whether to print progress.
        universe: Optional list of tickers to filter. Overrides config.data.universe_path
                  completely (not just filtering within it).
    
    Returns:
        Dictionary with results:
        - 'backtest_results': BacktestResults object
        - 'model_path': Path to saved model (if save_model=True)
        - 'feature_cols': List of feature columns used
    """
    from .backtest.rolling import run_walk_forward_backtest, BacktestConfig
    from .models.trainer import ModelConfig
    
    if verbose:
        print("Preparing training data...")
    
    # Prepare data - pass universe directly to override config's universe_path
    # This ensures watchlist symbols aren't limited by universe.txt
    training_df, feature_cols, price_df, benchmark_df = prepare_data_from_config(
        config, for_training=True, override_universe=universe
    )
    
    if universe is not None and verbose:
        print(f"  Using watchlist with {len(universe)} tickers (bypassing universe.txt)")
    
    if verbose:
        print(f"  Loaded {len(training_df)} training samples")
        print(f"  Features: {len(feature_cols)}")
    
    # Convert config objects
    model_cfg = ModelConfig(
        target_col=config.model.target_col,
        test_size=config.model.test_size,
        random_state=config.model.random_state,
        params=config.model.params,
    )
    
    backtest_cfg = BacktestConfig(
        train_years=config.backtest.train_years,
        test_years=config.backtest.test_years,
        step_years=config.backtest.step_years,
        rebalance_freq=config.backtest.rebalance_freq,
        top_n=config.backtest.top_n,
        top_pct=config.backtest.top_pct,
        min_stocks=config.backtest.min_stocks,
        transaction_cost=config.backtest.transaction_cost,
    )
    
    if verbose:
        print("\nRunning backtest...")
    
    # Run backtest
    results = run_walk_forward_backtest(
        training_data=training_df,
        benchmark_data=benchmark_df,
        price_data=price_df,
        feature_cols=feature_cols,
        config=backtest_cfg,
        model_config=model_cfg,
        verbose=verbose,
    )
    
    return {
        'backtest_results': results,
        'feature_cols': feature_cols,
    }
