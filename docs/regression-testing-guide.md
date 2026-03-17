# Regression Testing Guide

> [← Back to Documentation Index](README.md)

## Overview

The regression testing framework systematically evaluates features by adding them **one at a time** to a baseline model, measuring each feature's marginal contribution with statistical significance tests, and optionally tuning parameters via Bayesian optimization.

## Quick Start

```bash
# Run with default settings (all features, no tuning)
python scripts/run_regression_test.py run --watchlist tech_giants

# Run specific features with tuning
python scripts/run_regression_test.py run --watchlist tech_giants --tune --features rsi macd bollinger

# List previous tests
python scripts/run_regression_test.py list

# View feature leaderboard
python scripts/run_regression_test.py leaderboard

# Regenerate report for a test
python scripts/run_regression_test.py report <regression_id>
```

## How It Works

### Feature Addition Sequence

The system follows this default order:

```
Step 0:  BASELINE  [returns, volatility, volume]
Step 1:  +valuation
Step 2:  +rsi
Step 3:  +macd
Step 4:  +bollinger
Step 5:  +atr
Step 6:  +adx
Step 7:  +obv
Step 8:  +gap (QuantaAlpha overnight features)
Step 9:  +momentum
Step 10: +mean_reversion
Step 11: +sentiment (if enabled)
Step 12: MODEL TUNING (if --tune-model)
```

At each step:
1. Add the feature's columns to the active set
2. Tune feature-specific parameters (if `--tune`)
3. Run walk-forward backtest with the cumulative feature set
4. Compute all metrics (primary, secondary, guard)
5. Statistical significance test vs. previous step
6. Log everything to SQLite database

### Feature Registry

All 76+ features are registered in `src/regression/feature_registry.py` with:
- **Column mappings**: Which DataFrame columns each feature produces
- **Dependencies**: Features that must be included (e.g., momentum depends on returns)
- **Tunable parameters**: Bayesian optimization search spaces

### 14 Registered Feature Specs

| Name | Group | Columns | Tunable Params |
|------|-------|---------|---------------|
| returns | RETURNS | return_1m/3m/6m/12m | - |
| volatility | VOLATILITY | vol_20d, vol_60d | - |
| volume | VOLUME | dollar_volume_20d, volume_ratio, turnover_20d | - |
| valuation | VALUATION | pe_ratio, pb_ratio, earnings_yield | - |
| rsi | TECHNICAL | rsi | rsi_period [7-28] |
| macd | TECHNICAL | macd, macd_signal, macd_histogram | fast [5-20], slow [20-60], signal [5-20] |
| bollinger | TECHNICAL | bb_upper/lower/middle/width/pct | period [10-30], std [1.5-3.0] |
| atr | TECHNICAL | atr | period [7-28] |
| adx | TECHNICAL | adx, plus_di, minus_di | period [7-28] |
| obv | TECHNICAL | obv, obv_slope_20d | slope_window [10-40] |
| gap | GAP | overnight_gap_pct, gap_vs_true_range, gap_acceptance_* | lookback [5-20], window [10-40] |
| momentum | MOMENTUM | momentum_score, relative_strength, 52w distance, etc. | - |
| mean_reversion | MEAN_REVERSION | zscore_20d/60d, sma distance, divergence, etc. | - |
| sentiment | SENTIMENT | sentiment_mean/std/count/trend for 1d/7d/14d | - |

## Metrics Framework

### Classification

| Class | Metric | Why |
|-------|--------|-----|
| **PRIMARY** | `mean_rank_ic` | Signal quality (Spearman IC) |
| **PRIMARY** | `sharpe_ratio` | Risk-adjusted return |
| **PRIMARY** | `excess_return` | Alpha vs benchmark |
| **SECONDARY** | `ic_std`, `ic_ir` | Signal stability |
| **SECONDARY** | `sortino_ratio`, `calmar_ratio` | Downside-adjusted returns |
| **SECONDARY** | `hit_rate`, `volatility`, `total_return` | Portfolio characteristics |
| **GUARD** | `max_drawdown` (> -30%) | Must not blow up |
| **GUARD** | `turnover` (< 80%) | Must not churn |
| **GUARD** | `train_test_sharpe_ratio` (< 2.5) | Overfitting detector |
| **GUARD** | `ic_pct_positive` (> 50%) | Signal must work majority of time |

### Statistical Significance Tests

Each step runs:
1. **Paired t-test on per-window Rank ICs** — Did IC improve?
2. **Paired t-test on per-window test Sharpes** — Did portfolio improve?
3. **Bootstrap CI for Sharpe difference** (1000 resamples, 95% CI)

A feature is marked "significant" if rank_ic paired t-test p < 0.05.

## Parameter Tuning

### Per-Feature Tuning (Bayesian Optimization)

When `--tune` is enabled:
- **Method**: `skopt.gp_minimize` with Expected Improvement
- **Objective**: `mean_rank_ic` (NOT Sharpe — IC is more granular, less prone to overfitting)
- **Budget**: 30 trials per feature (configurable with `--tuning-trials`)
- **Constraint**: Reject if guard metrics violated

### Model Hyperparameter Tuning

When `--tune-model` is enabled (runs after all features added):
- Tunes: n_estimators, learning_rate, num_leaves, max_depth, regularization, subsample
- **Budget**: 50 trials (configurable with `--model-tuning-trials`)
- **Complexity penalty**: Penalizes large models

## Reports

Generated to `output/regression/<regression_id>/`:

| File | Content |
|------|---------|
| `regression_report.json` | Full structured data |
| `regression_report.md` | Human-readable with tables |
| `regression_metrics.csv` | One row per step, all metrics |
| `feature_leaderboard.csv` | Features ranked by contribution |
| `tuned_params.json` | Best params per feature |

## Database Schema

Three tables in `data/runs.db`:

- **`regression_tests`**: One row per test session (config, summary, best feature)
- **`regression_steps`**: One row per step (metrics, significance, importance, tuned params)
- **`feature_contributions`**: Aggregated leaderboard across tests

## CLI Reference

```bash
# Run
python scripts/run_regression_test.py run [options]
  --watchlist, -w       Watchlist name
  --config, -c          Config file path (default: config/config.yaml)
  --features            Features to test in order
  --baseline            Baseline features (default: returns volatility volume)
  --tune                Enable per-feature parameter tuning
  --tune-model          Tune LightGBM hyperparams after all features
  --tuning-trials       Trials per feature (default: 30)
  --model-tuning-trials Model tuning trials (default: 50)
  --objective           Tuning objective (default: mean_rank_ic)
  --name, -n            Test name
  --exclude-sentiment   Skip sentiment features

# List
python scripts/run_regression_test.py list [--status completed|running|failed]

# Report
python scripts/run_regression_test.py report <regression_id> [-o output_dir]

# Leaderboard
python scripts/run_regression_test.py leaderboard [--regression-id <id>]
```

## Architecture

```
src/regression/
    __init__.py              # Public API
    feature_registry.py      # FeatureRegistry, FeatureSpec, tunable params
    metrics.py               # METRICS_REGISTRY, significance tests
    database.py              # SQLite schema + CRUD
    orchestrator.py          # RegressionOrchestrator (main engine)
    tuning.py                # FeatureParamTuner, ModelParamTuner
    reporting.py             # JSON/MD/CSV report generation

scripts/
    run_regression_test.py   # CLI entry point
```

---

## See Also

- [Backtesting framework](backtesting.md)
- [Feature importance analysis](feature-importance-methods.md)
- [Test suite overview](test-suite-documentation.md)
- [Model training](model-training.md)
