> [← Back to Documentation Index](README.md)

# Configuration Reference

All configuration is defined in YAML files. Settings are resolved in priority order:

1. **Environment variables** (`STOCKPLANNER_*`)
2. **Per-ticker overrides** (`config/tickers/<TICKER>.yaml`)
3. **Config file** (passed via `--config`)
4. **Defaults** (shown below)

---

## Model Configuration (`model`)

| Key | Type | Default | Valid Range | Description |
|-----|------|---------|-------------|-------------|
| `model.target_col` | string | `"target"` | — | Column name for prediction target |
| `model.test_size` | float | `0.2` | 0.0–1.0 | Train/validation split ratio |
| `model.random_state` | int | `42` | — | Reproducibility seed |
| `model.model_type` | string | `"lightgbm"` | — | ML algorithm |

### Model Parameters (`model.params`)

| Key | Type | Default | Valid Range | Description |
|-----|------|---------|-------------|-------------|
| `n_estimators` | int | `200` | 1–10000 | Number of boosting rounds |
| `learning_rate` | float | `0.03` | 0.001–1.0 | Shrinkage rate |
| `max_depth` | int | `6` | 1–20 | Maximum tree depth |
| `num_leaves` | int | `15` | 2–1000 | Maximum leaves per tree |
| `min_child_samples` | int | `50` | 1–1000 | Minimum samples per leaf node |
| `reg_alpha` | float | `0.3` | 0.0–10.0 | L1 regularization |
| `reg_lambda` | float | `0.5` | 0.0–10.0 | L2 regularization |
| `subsample` | float | `0.7` | 0.1–1.0 | Row subsampling ratio |
| `colsample_bytree` | float | `0.7` | 0.1–1.0 | Feature subsampling ratio |
| `early_stopping_rounds` | int | `30` | — | Patience for early stopping |

---

## Backtest Configuration (`backtest`)

| Key | Type | Default | Valid Range | Description |
|-----|------|---------|-------------|-------------|
| `backtest.train_years` | float | `3.0` | — | Training window in years |
| `backtest.test_years` | float | `0.5` | — | Test window in years |
| `backtest.step_value` | float | `7` | — | Walk-forward step size |
| `backtest.step_unit` | string | `"days"` | `days`, `weeks`, `months`, `years`, `hours` | Step unit |
| `backtest.rebalance_freq` | string | `"4h"` | `1h`, `4h`, `MS`, `M`, `Q`, `Y` | Rebalancing frequency |
| `backtest.top_n` | int | `5` | — | Number of top stocks to select |
| `backtest.top_pct` | float | `0.1` | 0.0–1.0 | Percentile threshold (alternative to `top_n`) |
| `backtest.min_stocks` | int | `5` | — | Minimum portfolio size |
| `backtest.transaction_cost` | float | `0.001` | — | Cost per trade (0.1%) |
| `backtest.start_date` | string | `null` | ISO date | Optional backtest start date |
| `backtest.end_date` | string | `null` | ISO date | Optional backtest end date |
| `backtest.max_position_weight` | float | `0.20` | 0.0–1.0 | Maximum weight per stock |
| `backtest.stop_loss_pct` | float | `-0.15` | — | Stop-loss threshold |

### VIX Scaling (`backtest.vix_*`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `backtest.vix_scale_enabled` | bool | `true` | Enable VIX-based position scaling |
| `backtest.vix_high_threshold` | float | `30.0` | VIX level considered high |
| `backtest.vix_extreme_threshold` | float | `40.0` | VIX level considered extreme |
| `backtest.vix_high_scale` | float | `0.6` | Position scale factor at high VIX |
| `backtest.vix_extreme_scale` | float | `0.3` | Position scale factor at extreme VIX |

---

## Data Configuration (`data`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `data.interval` | string | `"1h"` | Data granularity |
| `data.price_data_path` | string | `"data/prices.csv"` | Hourly price data |
| `data.price_data_path_daily` | string | `"data/prices_daily.csv"` | Daily price data (preferred) |
| `data.price_data_path_15m` | string | `"data/prices_15m.csv"` | 15-minute price data |
| `data.fundamental_data_path` | string | `null` | Fundamental data path |
| `data.benchmark_data_path` | string | `"data/benchmark.csv"` | Hourly SPY benchmark |
| `data.benchmark_data_path_daily` | string | `"data/benchmark_daily.csv"` | Daily SPY benchmark |
| `data.macro_data_path` | string | `"data/macro_fred.csv"` | FRED macro indicators |
| `data.output_dir` | string | `"output"` | Results output directory |
| `data.models_dir` | string | `"models"` | Model artifacts directory |

---

## Feature Configuration (`features`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `features.rsi_period` | int | `14` | RSI lookback period |
| `features.macd_fast` | int | `12` | MACD fast EMA period |
| `features.macd_slow` | int | `26` | MACD slow EMA period |
| `features.macd_signal` | int | `9` | MACD signal line period |
| `features.return_periods` | list[int] | `[21, 63, 126, 252]` | Return lookback periods |
| `features.volatility_windows` | list[int] | `[20, 60]` | Volatility rolling windows |
| `features.volume_window` | int | `20` | Volume rolling window |
| `features.horizon_days` | int | `63` | Prediction horizon in days |

### Feature Toggles

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `features.include_technical` | bool | `true` | MACD, Bollinger Bands, ATR, ADX |
| `features.include_rsi` | bool | `false` | RSI features (hurts model, -0.28 Sharpe) |
| `features.include_obv` | bool | `true` | On-balance volume (conditional) |
| `features.include_momentum` | bool | `false` | Momentum features (hurts model, -0.24 Sharpe) |
| `features.include_mean_reversion` | bool | `false` | Mean-reversion features |
| `features.use_cross_asset` | bool | `false` | Cross-asset rotation features |
| `features.use_sentiment` | bool | `false` | Sentiment features |
| `features.include_fundamentals` | bool | `true` | Fundamental data features |

---

## Trigger Configuration (`trigger`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `trigger.macd_fast` | int | `12` | MACD fast period |
| `trigger.macd_slow` | int | `26` | MACD slow period |
| `trigger.macd_signal` | int | `9` | MACD signal period |
| `trigger.rsi_period` | int | `14` | RSI lookback period |
| `trigger.rsi_overbought` | float | `70` | RSI overbought threshold |
| `trigger.rsi_oversold` | float | `30` | RSI oversold threshold |
| `trigger.optimized_params_path` | string | `"output/best_params.json"` | Path to Bayesian-optimized parameters |

---

## Regression Configuration (`regression`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `regression.baseline_features` | list | `[returns, volatility, volume]` | Baseline feature set |
| `regression.default_feature_order` | list | `[macd, bollinger, adx, ...]` | Default feature evaluation order |
| `regression.recommended_features` | list | `[macd, bollinger, adx]` | Recommended feature set |
| `regression.objective_metric` | string | `"mean_rank_ic"` | Optimization objective |
| `regression.significance_alpha` | float | `0.05` | Statistical significance level |
| `regression.n_bootstrap` | int | `1000` | Bootstrap iterations |
| `regression.max_drawdown_threshold` | float | `-0.30` | Maximum acceptable drawdown |
| `regression.turnover_threshold` | float | `0.80` | Maximum portfolio turnover |
| `regression.overfit_sharpe_ratio_threshold` | float | `2.5` | Sharpe ratio overfitting flag |
| `regression.ic_pct_positive_threshold` | float | `0.50` | Minimum % of positive IC periods |

---

## Analysis Configuration (`analysis`)

### Score Weights (`analysis.weights`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `analysis.weights.model_score` | float | `0.49` | Weight for model prediction score |
| `analysis.weights.value_score` | float | `0.20` | Weight for value/fundamental score |
| `analysis.weights.quality_score` | float | `0.31` | Weight for quality score |

### Fundamental Filters (`analysis.filters`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `analysis.filters.min_roe` | float | `0.03` | Minimum return on equity |
| `analysis.filters.min_net_margin` | float | `0.02` | Minimum net profit margin |
| `analysis.filters.max_debt_to_equity` | float | `1.8` | Maximum debt-to-equity ratio |

### Portfolio Construction (`analysis.horizontal`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `analysis.horizontal.portfolio_size` | int | `10` | Target portfolio size |
| `analysis.horizontal.max_position_weight` | float | `0.15` | Maximum single-position weight |
| `analysis.horizontal.min_position_weight` | float | `0.02` | Minimum single-position weight |
| `analysis.horizontal.max_sector_weight` | float | `0.30` | Maximum sector concentration |

---

## Per-Ticker Configuration

Per-ticker overrides live in `config/tickers/<TICKER>.yaml`. These files are merged on top of the global config for that ticker, allowing customized parameters (e.g., from Bayesian optimization).

Any top-level config key can be overridden. Example `config/tickers/NVDA.yaml`:

```yaml
ticker: NVDA
trigger:
  rsi_period: 14
  rsi_oversold: 40
  rsi_overbought: 80
  macd_fast: 15
  macd_slow: 20
  macd_signal: 7
  bb_period: 20
  bb_std: 2.0
  macro_factors:
    vix_enabled: true
    vix_buy_max: 25
    vix_sell_min: 30
    volume_surge_min: 2.0
    obv_slope_positive: true
horizon_days: 63
return_periods: [21, 63, 126, 252]
volatility_windows: [20, 60]
volume_window: 20
backtest:
  train_years: 1.0
  test_years: 0.25
  step_value: 0.5
  step_unit: days
  rebalance_freq: 4h
```

---

## Environment Variables

All config keys can be overridden via environment variables using the `STOCKPLANNER_` prefix. The key is uppercased and dots are replaced with underscores.

| Variable | Maps To | Example |
|----------|---------|---------|
| `STOCKPLANNER_MODEL_TYPE` | `model.model_type` | `lightgbm` |
| `STOCKPLANNER_TEST_SIZE` | `model.test_size` | `0.3` |
| `STOCKPLANNER_LEARNING_RATE` | `model.params.learning_rate` | `0.01` |
| `STOCKPLANNER_TRAIN_YEARS` | `backtest.train_years` | `5.0` |
| `STOCKPLANNER_REBALANCE_FREQ` | `backtest.rebalance_freq` | `1h` |
| `STOCKPLANNER_INTERVAL` | `data.interval` | `1d` |
| `STOCKPLANNER_OUTPUT_DIR` | `data.output_dir` | `/tmp/output` |
| `STOCKPLANNER_HORIZON_DAYS` | `features.horizon_days` | `126` |

Type conversion is automatic based on the default value's type (bool, int, float, string).

---

## See Also

- [CLI Configuration](configuration-cli.md) -- command-line flags and argument reference
- [API Configuration](api-configuration.md) -- programmatic configuration via Python
- [Daily Run Guide](daily-run.md) -- production run configuration and scheduling
