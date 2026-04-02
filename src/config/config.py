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
        "n_estimators": 200,
        "learning_rate": 0.03,
        "max_depth": 6,
        "num_leaves": 15,
        "min_child_samples": 50,
        "reg_alpha": 0.3,
        "reg_lambda": 0.5,
        "subsample": 0.7,
        "colsample_bytree": 0.7,
        "early_stopping_rounds": 30,
    })


@dataclass
class BacktestConfig:
    """Configuration for walk-forward backtest."""
    train_years: float = 5.0
    test_years: float = 1.0
    step_value: float = 1.0  # Step size (see step_unit)
    step_unit: str = "years"  # hours, days, months, years
    rebalance_freq: str = "MS"  # MS = month start, M = month end
    top_n: Optional[int] = None
    top_pct: float = 0.1
    min_stocks: int = 5
    transaction_cost: float = 0.001
    # Optional date range constraints
    start_date: Optional[str] = None  # Format: YYYY-MM-DD (filters data before this date)
    end_date: Optional[str] = None    # Format: YYYY-MM-DD (filters data after this date)
    # IC (Information Coefficient) gating: require |IC| above threshold per window
    ic_min_threshold: Optional[float] = None  # e.g. 0.01 or 0.02; None = disabled
    ic_action: str = "warn"  # "warn" | "off" when |IC| < ic_min_threshold
    # Position sizing controls
    max_position_weight: float = 0.20   # Max weight per stock (20%)
    stop_loss_pct: float = -0.08        # Cut position at -8% from entry
    stop_loss_cooldown_days: int = 5    # Dont re-enter stopped-out ticker for 5 days
    vix_scale_enabled: bool = True      # Scale down exposure when VIX is high
    vix_high_threshold: float = 30.0    # VIX above this = reduce exposure
    vix_extreme_threshold: float = 40.0 # VIX above this = max reduction
    vix_high_scale: float = 0.6         # Scale factor when VIX > high threshold
    vix_extreme_scale: float = 0.3      # Scale factor when VIX > extreme threshold
    market_regime_filter: Optional[Any] = None  # SPY-based cash rule
    paused_watchlists: Optional[list] = None    # Watchlists with new BUY entries paused


def bars_per_day_from_interval(interval: str) -> float:
    """Convert data interval to bars per trading day (US equities ~6.5 hours)."""
    iv = (interval or "1d").lower().strip()
    if iv in ("1d", "1day", "daily"):
        return 1.0
    if iv in ("1h", "1hour", "hourly"):
        return 6.5  # US trading hours per day
    return 1.0


@dataclass
class DataConfig:
    """Configuration for data paths and sources."""
    interval: str = "1d"  # 1d (daily) or 1h (hourly). yfinance limits 1h to ~730 days
    price_data_path: str = "data/prices.csv"
    price_data_path_daily: str = "data/prices_daily.csv"  # 10yr daily for features (114 tickers)
    price_data_path_15m: str = "data/prices_15m.csv"  # 15m intraday (when available)
    fundamental_data_path: Optional[str] = None
    benchmark_data_path: str = "data/benchmark.csv"
    benchmark_data_path_daily: str = "data/benchmark_daily.csv"  # 10yr daily SPY
    macro_data_path: str = "data/macro_fred.csv"  # FRED macro data
    universe_path: Optional[str] = None
    sentiment_news_path: Optional[str] = None  # Path to news data for sentiment
    output_dir: str = "output"
    models_dir: str = "models"


@dataclass
class MacdRsiConfig:
    """Configuration for MACD/RSI (trigger backtest + feature engineering). Overridden by Bayesian-optimized params when file exists."""
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    optimized_params_path: Optional[str] = None  # JSON path; overrides above when file exists


@dataclass
class FeatureConfig:
    """Configuration for feature engineering."""
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
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
    sentiment_fillna: float = 0.0  # Numeric fill for missing sentiment. Check sentiment_has_data column to distinguish no-data from neutral.
    # Feature toggles (validated by regression test reg_20260315_152332)
    include_technical: bool = True   # MACD, Bollinger, ATR, ADX (always on)
    include_rsi: bool = False        # RSI hurts cross-sectional model (-0.28 Sharpe)
    include_obv: bool = False        # OBV hurts cross-sectional model (-0.18 Sharpe)
    include_momentum: bool = False   # Momentum hurts cross-sectional model (-0.24 Sharpe)
    include_mean_reversion: bool = False  # Mean reversion adds noise
    # Per-watchlist feature transforms (e.g. invert ATR for tech_giants)
    watchlist_overrides: Dict[str, Any] = field(default_factory=dict)
    # Cross-asset features
    use_cross_asset: bool = False
    cross_asset: Dict[str, Any] = field(default_factory=lambda: {
        'zscore_window': 60,
        'dxy_lookback': 21,
        'real_yield_lookback': 63,
        'nvda_lookback': 21,
        'breadth_lookback': 21,
        'qqq_lookback': 63,
        'rotation_lookback': 20,
        'include_btc': True,
    })


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
    fillna_value: float = 0.0  # Numeric fill for missing sentiment. Check sentiment_has_data to distinguish no-data from neutral.
    ranker_fillna_value: float = 0.0  # Alias for ranker-specific fill


@dataclass
class CLIConfig:
    """Configuration for CLI output."""
    output_format: str = "table"  # table, csv, json
    verbose: bool = True
    save_results: bool = True
    results_path: Optional[str] = None
    # When False, only save to database (reduces CSV files)
    save_backtest_csv: bool = True


@dataclass
class RegressionConfig:
    """Configuration for feature regression testing."""
    baseline_features: List[str] = field(
        default_factory=lambda: ["returns", "volatility", "volume"]
    )
    default_feature_order: List[str] = field(default_factory=lambda: [
        "macd", "bollinger", "adx", "valuation", "gap", "atr",
        "obv", "rsi", "momentum", "mean_reversion", "sentiment",
    ])
    recommended_features: List[str] = field(default_factory=lambda: [
        "macd", "bollinger", "adx",
    ])
    tune_on_add: bool = False
    tune_model_params: bool = False
    tuning_trials: int = 30
    model_tuning_trials: int = 50
    objective_metric: str = "mean_rank_ic"
    significance_alpha: float = 0.05
    n_bootstrap: int = 1000
    # Guard metric thresholds
    max_drawdown_threshold: float = -0.30
    turnover_threshold: float = 0.80
    overfit_sharpe_ratio_threshold: float = 2.5
    ic_pct_positive_threshold: float = 0.50


@dataclass
class AppConfig:
    """Main application configuration combining all configs."""
    model: ModelConfig = field(default_factory=ModelConfig)
    trigger: MacdRsiConfig = field(default_factory=MacdRsiConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    data: DataConfig = field(default_factory=DataConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    sentiment: SentimentConfig = field(default_factory=SentimentConfig)
    cli: CLIConfig = field(default_factory=CLIConfig)
    regression: RegressionConfig = field(default_factory=RegressionConfig)


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
    trigger_dict = config_dict.get('trigger', {})
    trigger_cfg = MacdRsiConfig(**trigger_dict) if trigger_dict else MacdRsiConfig()
    backtest_dict = config_dict.get('backtest', {})
    # Migrate step_years -> step_value + step_unit
    if 'step_years' in backtest_dict and 'step_value' not in backtest_dict:
        backtest_dict = {**backtest_dict, 'step_value': backtest_dict['step_years'], 'step_unit': 'years'}
        backtest_dict = {k: v for k, v in backtest_dict.items() if k != 'step_years'}
    backtest_cfg = BacktestConfig(**backtest_dict) if backtest_dict else BacktestConfig()
    data_cfg = DataConfig(**config_dict.get('data', {})) if 'data' in config_dict else DataConfig()
    features_cfg = FeatureConfig(**config_dict.get('features', {})) if 'features' in config_dict else FeatureConfig()
    sentiment_cfg = SentimentConfig(**config_dict.get('sentiment', {})) if 'sentiment' in config_dict else SentimentConfig()
    cli_cfg = CLIConfig(**config_dict.get('cli', {})) if 'cli' in config_dict else CLIConfig()
    regression_cfg = RegressionConfig(**config_dict.get('regression', {})) if 'regression' in config_dict else RegressionConfig()

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
        backtest_cfg.step_value = _get_env_value('backtest_step_value', backtest_cfg.step_value)
        backtest_cfg.step_unit = _get_env_value('backtest_step_unit', backtest_cfg.step_unit)
        
        # CLI config
        cli_cfg.verbose = _get_env_value('cli_verbose', cli_cfg.verbose)
        cli_cfg.output_format = _get_env_value('cli_output_format', cli_cfg.output_format)
    
    config = AppConfig(
        model=model_cfg,
        trigger=trigger_cfg,
        backtest=backtest_cfg,
        data=data_cfg,
        features=features_cfg,
        sentiment=sentiment_cfg,
        cli=cli_cfg,
        regression=regression_cfg,
    )
    # Override trigger params from Bayesian-optimized JSON if present
    _apply_optimized_trigger_params(config)
    return config


def _apply_optimized_trigger_params(config: AppConfig) -> None:
    """Override config.trigger with best_params from JSON if file exists."""
    path = getattr(config.trigger, 'optimized_params_path', None)
    if not path:
        return
    p = Path(path)
    if not p.is_absolute():
        p = Path(__file__).parent.parent.parent / path
    if not p.exists():
        return
    try:
        with open(p) as f:
            data = json.load(f)
        best = data.get('best_params', {})
        if best:
            config.trigger.macd_fast = int(best.get('macd_fast', config.trigger.macd_fast))
            config.trigger.macd_slow = int(best.get('macd_slow', config.trigger.macd_slow))
            config.trigger.macd_signal = int(best.get('macd_signal', config.trigger.macd_signal))
            config.trigger.rsi_period = int(best.get('rsi_period', best.get('rsi_len', config.trigger.rsi_period)))
            config.trigger.rsi_overbought = float(best.get('rsi_overbought', best.get('rsi_hi', config.trigger.rsi_overbought)))
            config.trigger.rsi_oversold = float(best.get('rsi_oversold', best.get('rsi_lo', config.trigger.rsi_oversold)))
    except Exception:
        pass


def load_ticker_config(ticker: str, config_dir: Optional[Path] = None) -> Optional[dict]:
    """Load per-ticker YAML config from config/tickers/{ticker}.yaml if it exists.

    Returns a dict with keys: trigger (RSI/MACD/Bollinger params), horizon_days,
    return_periods, volatility_windows, volume_window. Returns None if no file exists.

    Example YAML structure:
        ticker: AMD
        trigger:
          rsi_period: 15
          ...
        horizon_days: 63
        return_periods: [21, 63, 126, 252]
        backtest:
          train_years: 1.0
          test_years: 0.25
          step_value: 1.0
          step_unit: days
          rebalance_freq: 4h
    """
    if config_dir is None:
        config_dir = Path(__file__).parent.parent.parent / "config" / "tickers"
    path = config_dir / f"{ticker.upper().strip()}.yaml"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return None


def get_backtest_config_for_ticker(
    ticker: str,
    base_backtest: BacktestConfig,
    config_dir: Optional[Path] = None,
) -> BacktestConfig:
    """Return BacktestConfig with per-ticker overrides from config/tickers/{ticker}.yaml.

    If the ticker YAML has a 'backtest' section, those values override the base config.
    Otherwise returns a copy of base_backtest.
    """
    ticker_cfg = load_ticker_config(ticker, config_dir)
    if not ticker_cfg or "backtest" not in ticker_cfg:
        return BacktestConfig(
            train_years=base_backtest.train_years,
            test_years=base_backtest.test_years,
            step_value=base_backtest.step_value,
            step_unit=base_backtest.step_unit,
            rebalance_freq=base_backtest.rebalance_freq,
            top_n=base_backtest.top_n,
            top_pct=base_backtest.top_pct,
            min_stocks=base_backtest.min_stocks,
            transaction_cost=base_backtest.transaction_cost,
            start_date=base_backtest.start_date,
            end_date=base_backtest.end_date,
            ic_min_threshold=getattr(base_backtest, "ic_min_threshold", None),
            ic_action=getattr(base_backtest, "ic_action", "warn"),
        )
    b = ticker_cfg["backtest"]
    return BacktestConfig(
        train_years=float(b.get("train_years", base_backtest.train_years)),
        test_years=float(b.get("test_years", base_backtest.test_years)),
        step_value=float(b.get("step_value", base_backtest.step_value)),
        step_unit=str(b.get("step_unit", base_backtest.step_unit)),
        rebalance_freq=str(b.get("rebalance_freq", base_backtest.rebalance_freq)),
        top_n=b.get("top_n", base_backtest.top_n),
        top_pct=float(b.get("top_pct", base_backtest.top_pct)),
        min_stocks=int(b.get("min_stocks", base_backtest.min_stocks)),
        transaction_cost=float(b.get("transaction_cost", base_backtest.transaction_cost)),
        start_date=b.get("start_date", base_backtest.start_date),
        end_date=b.get("end_date", base_backtest.end_date),
        ic_min_threshold=float(b["ic_min_threshold"]) if b.get("ic_min_threshold") is not None else getattr(base_backtest, "ic_min_threshold", None),
        ic_action=str(b.get("ic_action", getattr(base_backtest, "ic_action", "warn"))),
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
        'trigger': {
            'macd_fast': config.trigger.macd_fast,
            'macd_slow': config.trigger.macd_slow,
            'macd_signal': config.trigger.macd_signal,
            'rsi_period': config.trigger.rsi_period,
            'rsi_overbought': config.trigger.rsi_overbought,
            'rsi_oversold': config.trigger.rsi_oversold,
            'optimized_params_path': config.trigger.optimized_params_path,
        },
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
            'step_value': config.backtest.step_value,
            'step_unit': config.backtest.step_unit,
            'rebalance_freq': config.backtest.rebalance_freq,
            'top_n': config.backtest.top_n,
            'top_pct': config.backtest.top_pct,
            'min_stocks': config.backtest.min_stocks,
            'transaction_cost': config.backtest.transaction_cost,
            'ic_min_threshold': getattr(config.backtest, 'ic_min_threshold', None),
            'ic_action': getattr(config.backtest, 'ic_action', 'warn'),
        },
        'data': {
            'interval': config.data.interval,
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
            'use_cross_asset': config.features.use_cross_asset,
            'cross_asset': config.features.cross_asset,
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
            'save_backtest_csv': config.cli.save_backtest_csv,
        },
        'regression': {
            'baseline_features': config.regression.baseline_features,
            'default_feature_order': config.regression.default_feature_order,
            'tune_on_add': config.regression.tune_on_add,
            'tune_model_params': config.regression.tune_model_params,
            'tuning_trials': config.regression.tuning_trials,
            'model_tuning_trials': config.regression.model_tuning_trials,
            'objective_metric': config.regression.objective_metric,
            'significance_alpha': config.regression.significance_alpha,
            'n_bootstrap': config.regression.n_bootstrap,
            'max_drawdown_threshold': config.regression.max_drawdown_threshold,
            'turnover_threshold': config.regression.turnover_threshold,
            'overfit_sharpe_ratio_threshold': config.regression.overfit_sharpe_ratio_threshold,
            'ic_pct_positive_threshold': config.regression.ic_pct_positive_threshold,
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
