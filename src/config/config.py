"""Configuration module for mid-term stock planner.

This module provides configuration dataclasses and loading utilities
for all components of the system.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import os
import yaml
import json


@dataclass
class ModelConfig:
    """Configuration for model training."""
    target_col: str = "target"
    test_size: float = 0.2
    random_state: int = 42
    model_type: str = "lightgbm"  # lightgbm, xgboost, catboost
    params: Dict[str, Any] = field(default_factory=lambda: {
        "n_estimators": 300,
        "learning_rate": 0.05,
        "max_depth": -1,
        "num_leaves": 31,
    })


@dataclass
class BacktestConfig:
    """Configuration for walk-forward backtest."""
    train_years: float = 5.0
    test_years: float = 1.0
    step_years: float = 1.0
    rebalance_freq: str = "MS"  # MS = month start, M = month end
    top_n: Optional[int] = None
    top_pct: float = 0.1
    min_stocks: int = 5
    transaction_cost: float = 0.001
    # Optional date range constraints
    start_date: Optional[str] = None  # Format: YYYY-MM-DD (filters data before this date)
    end_date: Optional[str] = None    # Format: YYYY-MM-DD (filters data after this date)


@dataclass
class DataConfig:
    """Configuration for data paths and sources."""
    price_data_path: str = "data/prices.csv"
    fundamental_data_path: Optional[str] = None
    benchmark_data_path: str = "data/benchmark.csv"
    universe_path: Optional[str] = None
    sentiment_news_path: Optional[str] = None  # Path to news data for sentiment
    output_dir: str = "output"
    models_dir: str = "models"


@dataclass
class FeatureConfig:
    """Configuration for feature engineering."""
    return_periods: List[int] = field(default_factory=lambda: [21, 63, 126, 252])
    volatility_windows: List[int] = field(default_factory=lambda: [20, 60])
    volume_window: int = 20
    include_fundamentals: bool = True
    horizon_days: int = 63
    # Sentiment configuration
    use_sentiment: bool = False
    sentiment_source: str = "news"  # news, social, combined
    sentiment_lookbacks: List[int] = field(default_factory=lambda: [1, 7, 14])
    sentiment_min_count: int = 1  # Minimum articles to compute sentiment
    sentiment_fillna: float = 0.0  # Value for missing sentiment (use 0 for neutral)


@dataclass
class SentimentConfig:
    """Configuration for sentiment analysis."""
    # Data paths
    news_data_path: Optional[str] = None
    
    # Model configuration
    model_type: str = "lexicon"  # dummy, lexicon, finbert
    text_column: str = "headline"  # Column to use for sentiment
    
    # Timing configuration
    market_close_hour: int = 16  # Hour at which market closes
    timezone: Optional[str] = None  # Timezone for news timestamps
    
    # Aggregation configuration
    lookbacks: List[int] = field(default_factory=lambda: [1, 7, 14])
    min_daily_count: int = 1  # Minimum articles per day
    
    # Feature options
    include_volume_features: bool = True  # Include article count features
    include_trend_features: bool = True  # Include sentiment trend features
    
    # Missing data handling
    fillna_value: float = 0.0  # Value for missing sentiment


@dataclass
class CLIConfig:
    """Configuration for CLI output."""
    output_format: str = "table"  # table, csv, json
    verbose: bool = True
    save_results: bool = True
    results_path: Optional[str] = None


@dataclass
class AppConfig:
    """Main application configuration combining all configs."""
    model: ModelConfig = field(default_factory=ModelConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    data: DataConfig = field(default_factory=DataConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    sentiment: SentimentConfig = field(default_factory=SentimentConfig)
    cli: CLIConfig = field(default_factory=CLIConfig)


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _get_env_value(key: str, default: Any = None) -> Any:
    """Get value from environment variable with type conversion."""
    env_key = f"STOCKPLANNER_{key.upper()}"
    value = os.environ.get(env_key)
    
    if value is None:
        return default
    
    # Try to convert to appropriate type
    if default is not None:
        if isinstance(default, bool):
            return value.lower() in ('true', '1', 'yes')
        elif isinstance(default, int):
            return int(value)
        elif isinstance(default, float):
            return float(value)
    
    return value


def load_config(
    config_path: Optional[Union[str, Path]] = None,
    use_env: bool = True
) -> AppConfig:
    """
    Load configuration from YAML file with environment variable overrides.
    
    Priority (highest to lowest):
    1. Environment variables (STOCKPLANNER_*)
    2. Config file
    3. Defaults
    
    Args:
        config_path: Path to YAML config file. If None, uses defaults.
        use_env: Whether to apply environment variable overrides.
    
    Returns:
        AppConfig with loaded configuration.
    """
    config_dict = {}
    
    # Load from file if provided
    if config_path is not None:
        config_path = Path(config_path)
        if config_path.exists():
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    config_dict = yaml.safe_load(f) or {}
                elif config_path.suffix.lower() == '.json':
                    config_dict = json.load(f)
    
    # Create config objects
    model_cfg = ModelConfig(**config_dict.get('model', {})) if 'model' in config_dict else ModelConfig()
    backtest_cfg = BacktestConfig(**config_dict.get('backtest', {})) if 'backtest' in config_dict else BacktestConfig()
    data_cfg = DataConfig(**config_dict.get('data', {})) if 'data' in config_dict else DataConfig()
    features_cfg = FeatureConfig(**config_dict.get('features', {})) if 'features' in config_dict else FeatureConfig()
    sentiment_cfg = SentimentConfig(**config_dict.get('sentiment', {})) if 'sentiment' in config_dict else SentimentConfig()
    cli_cfg = CLIConfig(**config_dict.get('cli', {})) if 'cli' in config_dict else CLIConfig()
    
    # Apply environment variable overrides
    if use_env:
        # Model config
        model_cfg.target_col = _get_env_value('model_target_col', model_cfg.target_col)
        model_cfg.test_size = _get_env_value('model_test_size', model_cfg.test_size)
        
        # Data config
        data_cfg.price_data_path = _get_env_value('data_price_path', data_cfg.price_data_path)
        data_cfg.benchmark_data_path = _get_env_value('data_benchmark_path', data_cfg.benchmark_data_path)
        data_cfg.output_dir = _get_env_value('data_output_dir', data_cfg.output_dir)
        
        # Backtest config
        backtest_cfg.train_years = _get_env_value('backtest_train_years', backtest_cfg.train_years)
        backtest_cfg.test_years = _get_env_value('backtest_test_years', backtest_cfg.test_years)
        
        # CLI config
        cli_cfg.verbose = _get_env_value('cli_verbose', cli_cfg.verbose)
        cli_cfg.output_format = _get_env_value('cli_output_format', cli_cfg.output_format)
    
    return AppConfig(
        model=model_cfg,
        backtest=backtest_cfg,
        data=data_cfg,
        features=features_cfg,
        sentiment=sentiment_cfg,
        cli=cli_cfg
    )


def save_config(config: AppConfig, path: Union[str, Path]) -> None:
    """
    Save configuration to YAML file.
    
    Args:
        config: AppConfig to save.
        path: Path to save config file.
    """
    path = Path(path)
    
    config_dict = {
        'model': {
            'target_col': config.model.target_col,
            'test_size': config.model.test_size,
            'random_state': config.model.random_state,
            'model_type': config.model.model_type,
            'params': config.model.params,
        },
        'backtest': {
            'train_years': config.backtest.train_years,
            'test_years': config.backtest.test_years,
            'step_years': config.backtest.step_years,
            'rebalance_freq': config.backtest.rebalance_freq,
            'top_n': config.backtest.top_n,
            'top_pct': config.backtest.top_pct,
            'min_stocks': config.backtest.min_stocks,
            'transaction_cost': config.backtest.transaction_cost,
        },
        'data': {
            'price_data_path': config.data.price_data_path,
            'fundamental_data_path': config.data.fundamental_data_path,
            'benchmark_data_path': config.data.benchmark_data_path,
            'universe_path': config.data.universe_path,
            'sentiment_news_path': config.data.sentiment_news_path,
            'output_dir': config.data.output_dir,
            'models_dir': config.data.models_dir,
        },
        'features': {
            'return_periods': config.features.return_periods,
            'volatility_windows': config.features.volatility_windows,
            'volume_window': config.features.volume_window,
            'include_fundamentals': config.features.include_fundamentals,
            'horizon_days': config.features.horizon_days,
            'use_sentiment': config.features.use_sentiment,
            'sentiment_source': config.features.sentiment_source,
            'sentiment_lookbacks': config.features.sentiment_lookbacks,
            'sentiment_min_count': config.features.sentiment_min_count,
            'sentiment_fillna': config.features.sentiment_fillna,
        },
        'sentiment': {
            'news_data_path': config.sentiment.news_data_path,
            'model_type': config.sentiment.model_type,
            'text_column': config.sentiment.text_column,
            'market_close_hour': config.sentiment.market_close_hour,
            'timezone': config.sentiment.timezone,
            'lookbacks': config.sentiment.lookbacks,
            'min_daily_count': config.sentiment.min_daily_count,
            'include_volume_features': config.sentiment.include_volume_features,
            'include_trend_features': config.sentiment.include_trend_features,
            'fillna_value': config.sentiment.fillna_value,
        },
        'cli': {
            'output_format': config.cli.output_format,
            'verbose': config.cli.verbose,
            'save_results': config.cli.save_results,
            'results_path': config.cli.results_path,
        },
    }
    
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w') as f:
        if path.suffix.lower() in ['.yaml', '.yml']:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        else:
            json.dump(config_dict, f, indent=2)


def create_example_config(path: Union[str, Path] = "config/config.yaml") -> None:
    """
    Create an example configuration file with default values.
    
    Args:
        path: Path to save the example config.
    """
    config = AppConfig()
    save_config(config, path)
