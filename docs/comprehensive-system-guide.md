# Comprehensive System Guide -- QuantaAlpha Midterm Stock Planner

**Version:** 3.11.2
**Last Updated:** 2026-03-13
**System:** midterm-stock-planner (QuantaAlpha)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Data Pipeline](#2-data-pipeline)
3. [Feature Engineering (76+ Features)](#3-feature-engineering-76-features)
4. [Model](#4-model)
5. [Backtesting](#5-backtesting)
6. [Regression Testing Framework](#6-regression-testing-framework)
7. [Automation Pipeline](#7-automation-pipeline)
8. [Data Gap Analysis Findings (Current State)](#8-data-gap-analysis-findings-current-state)
9. [CLI Reference](#9-cli-reference)
10. [Architecture and File Structure](#10-architecture-and-file-structure)
11. [Next Steps / Roadmap](#11-next-steps--roadmap)

---

## 1. System Overview

### Purpose

The Midterm Stock Planner is a systematic mid-term stock selection system using machine learning (LightGBM) with walk-forward backtesting. It targets a **3-month investment horizon** with configurable rebalancing frequency (default: 4 hours for intraday data).

The system ranks stocks by predicted forward excess return versus a benchmark (SPY), constructs portfolios with risk constraints, and provides explainability through SHAP values and comprehensive reporting.

### Architecture

The end-to-end pipeline follows this flow:

```
Data Acquisition  -->  Feature Engineering  -->  Model Training/Prediction
       |                      |                          |
  Alpaca (primary)      76+ features               LightGBM
  yfinance (fallback)   returns, vol,              walk-forward
  Finnhub (sentiment)   technicals, gaps,          rolling windows
  FRED (macro)          macro, sentiment
                                                       |
                                                       v
                                              Backtesting Engine
                                                       |
                                                       v
                                              Analysis Pipeline
                                              (4 stages below)
                                                       |
                                                       v
                                             Streamlit Dashboard
```

### Analysis Pipeline (4 Stages)

| Stage | Description | Output Files |
|-------|-------------|--------------|
| **1. Backtest** | ML predictions + walk-forward backtest | `backtest_*.csv/json` |
| **2. Enrichment** | Add risk metrics, weights, scores | `portfolio_enriched_*.csv` |
| **3. Domain Analysis** | Vertical + horizontal portfolio construction | `vertical_candidates_*.csv`, `portfolio_candidates_*.csv` |
| **4. AI Analysis** | Commentary + recommendations (optional, Gemini LLM) | `commentary_*.md`, `recommendations_*.md` |

### Tech Stack

- Python 3.11+
- pandas, numpy, scipy
- LightGBM (primary), XGBoost/CatBoost (optional)
- SHAP (explainability)
- Streamlit + Plotly (dashboard)
- matplotlib, seaborn (static charts)
- alpaca-py (primary data backend -- Alpaca Markets)
- yfinance (fallback data fetching)
- finnhub-python (sentiment data -- news, insider, analyst, earnings)
- fredapi (FRED macro data -- yields, inflation, spreads, employment)
- google-generativeai (Gemini LLM for AI insights)
- scikit-optimize / skopt (Bayesian optimization)
- SQLite (run tracking, regression database)

---

## 2. Data Pipeline

### Current Data State

| Attribute | Value |
|-----------|-------|
| Tickers loaded | 114 (NASDAQ-100 + cross-asset ETFs) |
| Daily data | 10 years (2016-2026) via Alpaca Markets |
| Hourly data | ~22 months (yfinance 1h limit: ~730 days) |
| Multi-resolution | daily + hourly + 15m (in progress) |
| Primary backend | Alpaca Markets (`src/data/alpaca_client.py`) |
| Fallback | yfinance |
| Benchmark | SPY (daily: 10yr, hourly: ~22mo) |
| Macro data | FRED economic indicators (yields, inflation, spreads, employment) |
| Sentiment data | Finnhub (news, insider transactions, analyst ratings, earnings surprises) |
| Data quality score | A (95/100) |
| Daily price file | `data/prices_daily.csv` (10yr, 114 tickers) |
| Daily benchmark | `data/benchmark_daily.csv` (10yr SPY) |
| Hourly price file | `data/prices.csv` |
| Hourly benchmark | `data/benchmark.csv` |
| Macro file | `data/macro_fred.csv` |
| Sentiment dir | `data/sentiment/` |
| Fundamentals | `data/fundamentals.csv` |
| Database | `data/analysis.db` (SQLite) |

### Data Download

```bash
# Download prices for a specific watchlist (uses Alpaca Markets as primary, yfinance as fallback)
python scripts/download_prices.py --watchlist <name>

# Download benchmark data
python scripts/download_benchmark.py

# Download fundamentals (PE, PB, ROE, margins)
python scripts/download_fundamentals.py

# Download FRED macro data (yields, inflation, spreads, employment)
python scripts/download_macro.py

# Download Finnhub sentiment data (news, insider, analyst, earnings)
python scripts/download_sentiment.py
```

### Watchlists

There are **16 predefined watchlists** in `config/watchlists.yaml`:

| Watchlist | Category | Description |
|-----------|----------|-------------|
| `nasdaq_100` | index | Top 100 non-financial NASDAQ companies |
| `sp500` | index | S&P 500 components |
| `tech_giants` | sector | Major tech companies (AAPL, MSFT, NVDA, GOOG, AMZN, META, etc.) |
| `semiconductors` | sector | Semiconductor companies |
| `blue_chip` | sector | Blue-chip dividend stocks |
| `nuclear_energy` | thematic | Nuclear energy plays |
| `clean_energy` | thematic | Clean/renewable energy |
| `etf_universe` | etf | Major ETFs |
| `everything` | combined | Full universe of all watchlists |
| ... | ... | (and others) |

### Data Sources

**Primary: Alpaca Markets (alpaca-py)**
- Client: `src/data/alpaca_client.py`
- 10 years of daily data (2016-2026) for 114 tickers
- 7+ years of 1m/5m/15m/1h data available
- Free tier with API key (free registration)
- Used for all production data downloads

**Fallback: yfinance (free)**
- Provides 1h data limited to ~730 days (~2 years)
- Daily data available for 20+ years
- No API key required
- Used as fallback when Alpaca is unavailable

**Macro data: FRED (fredapi)**
- Treasury yields (2Y, 10Y, 2s10s spread)
- Inflation expectations (breakeven rates)
- Employment data (initial claims, unemployment rate)
- Credit spreads (BAA-AAA)
- Downloaded via `scripts/download_macro.py`
- Stored in `data/macro_fred.csv`

**Sentiment data: Finnhub (finnhub-python)**
- Company news sentiment
- Insider transaction data
- Analyst ratings and price targets
- Earnings surprises
- Downloaded via `scripts/download_sentiment.py`
- Stored in `data/sentiment/`

See `docs/data-providers-guide.md` for full provider comparison and `docs/data-quality.md` for quality tracking.

### Data Configuration

From `config/config.yaml`:

```yaml
data:
  interval: 1d          # 1d (daily) or 1h (hourly)
  price_data_path: data/prices_daily.csv
  fundamental_data_path: data/fundamentals.csv
  benchmark_data_path: data/benchmark_daily.csv
  macro_data_path: data/macro_fred.csv
  sentiment_dir: data/sentiment
  universe_path: data/universe.txt
  output_dir: output
  models_dir: models
```

---

## 3. Feature Engineering (76+ Features)

All features are registered in `src/regression/feature_registry.py` with column mappings, dependencies, and tunable parameter search spaces.

### Returns (Baseline)

| Feature | Description |
|---------|-------------|
| `return_1m` | 1-month (21-day) forward return |
| `return_3m` | 3-month (63-day) forward return |
| `return_6m` | 6-month (126-day) forward return |
| `return_12m` | 12-month (252-day) forward return |

Configured via `features.return_periods: [21, 63, 126, 252]`.

### Volatility (Baseline)

| Feature | Description |
|---------|-------------|
| `vol_20d` | 20-day rolling volatility |
| `vol_60d` | 60-day rolling volatility |

### Volume (Baseline)

| Feature | Description |
|---------|-------------|
| `dollar_volume_20d` | 20-day average dollar volume |
| `volume_ratio` | Current volume vs. moving average |
| `turnover_20d` | 20-day turnover ratio |

### Valuation

| Feature | Description |
|---------|-------------|
| `pe_ratio` | Price-to-earnings ratio |
| `pb_ratio` | Price-to-book ratio |
| `earnings_yield` | Inverse PE (E/P) |

### Technical Indicators

**RSI** (tunable: `rsi_period` [7-28])

| Feature | Description |
|---------|-------------|
| `rsi` | Relative Strength Index |

**MACD** (tunable: `fast` [5-20], `slow` [20-60], `signal` [5-20])

| Feature | Description |
|---------|-------------|
| `macd` | MACD line |
| `macd_signal` | MACD signal line |
| `macd_histogram` | MACD histogram |

**Bollinger Bands** (tunable: `period` [10-30], `std` [1.5-3.0])

| Feature | Description |
|---------|-------------|
| `bb_upper` | Upper Bollinger Band |
| `bb_lower` | Lower Bollinger Band |
| `bb_middle` | Middle band (SMA) |
| `bb_width` | Band width |
| `bb_pct` | %B position within bands |

**ATR** (tunable: `period` [7-28])

| Feature | Description |
|---------|-------------|
| `atr` | Average True Range |

**ADX** (tunable: `period` [7-28])

| Feature | Description |
|---------|-------------|
| `adx` | Average Directional Index |
| `plus_di` | Positive Directional Indicator |
| `minus_di` | Negative Directional Indicator |

### OBV (On-Balance Volume)

| Feature | Description |
|---------|-------------|
| `obv` | On-Balance Volume |
| `obv_slope_20d` | OBV slope over 20 days (tunable: `slope_window` [10-40]) |

### Gap / Overnight Analysis (QuantaAlpha Custom)

Tunable parameters: `lookback` [5-20], `window` [10-40].

| Feature | Description |
|---------|-------------|
| `overnight_gap_pct` | Overnight gap percentage |
| `gap_vs_true_range` | Gap relative to true range |
| `gap_acceptance_score` | Gap acceptance/rejection score |

These features are inspired by the QuantaAlpha paper (arXiv:2602.07085) and are designed to be robust under regime shifts.

### Momentum

| Feature | Description |
|---------|-------------|
| `momentum_score` | Composite momentum score |
| `relative_strength` | Relative strength vs. peers |
| `rel_strength_21d` | 21-day relative strength |
| `52w_high_distance` | Distance from 52-week high |
| `52w_low_distance` | Distance from 52-week low |
| `trend_strength` | Trend strength indicator |

### Mean Reversion

| Feature | Description |
|---------|-------------|
| `zscore_20d` | 20-day Z-score |
| `zscore_60d` | 60-day Z-score |
| `sma_distance_20d` | Distance from 20-day SMA |
| `sma_distance_60d` | Distance from 60-day SMA |
| `divergence` | Price-indicator divergence detection |

### Sentiment (Planned / Optional)

When `features.use_sentiment: true`:

| Feature | Description |
|---------|-------------|
| `sentiment_mean_1d/7d/14d` | Mean sentiment over lookback windows |
| `sentiment_std_1d/7d/14d` | Sentiment standard deviation |
| `sentiment_count_1d/7d/14d` | Number of sentiment observations |
| `sentiment_trend_1d/7d/14d` | Sentiment trend direction |

---

## 4. Model

### LightGBM Configuration

From `config/config.yaml`:

```yaml
model:
  target_col: target
  test_size: 0.2
  random_state: 42
  model_type: lightgbm
  params:
    n_estimators: 300
    learning_rate: 0.05
    max_depth: -1
    num_leaves: 31
```

### Target Variable

The model predicts the **3-month forward excess return vs. SPY**. The target is constructed as:

```
target = forward_3m_return(stock) - forward_3m_return(SPY)
```

The `features.horizon_days` setting (default: 63, approximately 3 months of trading days) controls the forward-looking window.

### Walk-Forward Validation

| Parameter | Value | Notes |
|-----------|-------|-------|
| Train window | 1 year | Reduced for 1h data; use 5.0 for daily |
| Test window | 3 months (0.25 years) | One investment horizon |
| Walk-forward step | 1 day | Produces ~20 windows for 1h data |
| Min stocks | 5 | Minimum required in each window |

### Model Hyperparameter Tuning

When `--tune-model` is enabled during regression testing:
- Tunes: `n_estimators`, `learning_rate`, `num_leaves`, `max_depth`, regularization, `subsample`
- Budget: 50 trials (configurable via `--model-tuning-trials`)
- Complexity penalty applied to prevent overfitting to large model configurations

---

## 5. Backtesting

### Walk-Forward Engine

The backtesting engine (`src/backtest/rolling.py`) implements a rolling walk-forward methodology:

1. **Train**: Fit LightGBM on the trailing N years of data
2. **Predict**: Score all stocks in the test window
3. **Rank**: Select top-N stocks by predicted excess return
4. **Portfolio**: Equal-weight or risk-parity allocation
5. **Track**: Record returns, positions, IC values
6. **Step**: Advance by the configured step size and repeat

### Key Parameters

```yaml
backtest:
  train_years: 1.0       # Training window (1 yr for hourly, 5 yr for daily)
  test_years: 0.25        # Test window (3 months)
  step_value: 1.0
  step_unit: days          # Walk-forward step
  rebalance_freq: 4h       # Rebalance every 4 hours
  top_n: 10                # Top N stocks per rebalance
  top_pct: 0.1             # Alternative: top 10% of universe
  min_stocks: 5            # Minimum stocks required
  transaction_cost: 0.001  # 10 basis points per trade
```

### IC Tracking

At each walk-forward window the engine computes:
- **Pearson IC**: Linear correlation between predicted and realized returns
- **Spearman Rank IC**: Rank correlation (more robust to outliers)
- **IC Information Ratio**: `mean_rank_ic / std_rank_ic`
- **Windows below threshold**: Count of windows where `|IC| < ic_min_threshold`

Optional gating: set `backtest.ic_min_threshold` (e.g., 0.01 or 0.02) to warn or skip windows with weak signal.

### Overfitting Detection

The system tracks both in-sample (train) and out-of-sample (test) Sharpe ratios. The guard metric `train_test_sharpe_ratio` flags potential overfitting when the ratio exceeds 2.5.

### Transaction Costs

Default: 0.1% (10 basis points) per trade. Applied at each rebalance. This is configurable via `backtest.transaction_cost`.

---

## 6. Regression Testing Framework

### Overview

The regression testing framework (`src/regression/`) systematically evaluates features by adding them one at a time to a baseline model, measuring each feature's marginal contribution with statistical significance tests.

### Feature Addition Sequence

```
Step 0:  BASELINE   [returns, volatility, volume]
Step 1:  +valuation
Step 2:  +rsi
Step 3:  +macd
Step 4:  +bollinger
Step 5:  +atr
Step 6:  +adx
Step 7:  +obv
Step 8:  +gap       (QuantaAlpha overnight features)
Step 9:  +momentum
Step 10: +mean_reversion
Step 11: +sentiment  (if enabled)
Step 12: MODEL TUNING (if --tune-model)
```

At each step:
1. Add the feature's columns to the active set
2. Tune feature-specific parameters (if `--tune` is enabled)
3. Run walk-forward backtest with the cumulative feature set
4. Compute all metrics (primary, secondary, guard)
5. Run statistical significance test vs. previous step
6. Log everything to the SQLite database

### Feature Registry

All 14 feature specs with 76+ columns are registered in `src/regression/feature_registry.py` with:
- **Column mappings**: Which DataFrame columns each feature produces
- **Dependencies**: Required prerequisite features
- **Tunable parameters**: Bayesian optimization search spaces per feature

### Metrics Framework

**PRIMARY metrics** (used for ranking and optimization):

| Metric | Description |
|--------|-------------|
| `mean_rank_ic` | Mean Spearman Rank IC across windows (signal quality) |
| `sharpe_ratio` | Annualized Sharpe ratio (risk-adjusted return) |
| `excess_return` | Cumulative alpha vs. benchmark |

**SECONDARY metrics** (for deeper analysis):

| Metric | Description |
|--------|-------------|
| `ic_std` | Standard deviation of IC across windows |
| `ic_ir` | IC Information Ratio (`mean_rank_ic / ic_std`) |
| `sortino_ratio` | Downside-risk-adjusted return |
| `calmar_ratio` | Return / max drawdown |
| `hit_rate` | Percentage of windows with positive excess return |
| `volatility` | Annualized portfolio volatility |
| `total_return` | Cumulative total return |

**GUARD metrics** (hard constraints -- must pass):

| Metric | Threshold | Purpose |
|--------|-----------|---------|
| `max_drawdown` | > -30% | Must not blow up |
| `turnover` | < 80% | Must not churn excessively |
| `train_test_sharpe_ratio` | < 2.5 | Overfitting detector |
| `ic_pct_positive` | > 50% | Signal must work majority of time |

### Statistical Significance Tests

Each feature addition step runs:
1. **Paired t-test on per-window Rank ICs** -- Did IC improve?
2. **Paired t-test on per-window test Sharpes** -- Did portfolio improve?
3. **Bootstrap CI for Sharpe difference** (1000 resamples, 95% CI)

A feature is marked as "significant" if the rank_ic paired t-test has `p < 0.05`.

### Parameter Tuning

**Per-Feature Tuning (Bayesian Optimization):**
- Method: `skopt.gp_minimize` with Expected Improvement acquisition function
- Objective: `mean_rank_ic` (chosen over Sharpe because IC is more granular and less prone to overfitting)
- Budget: 30 trials per feature (configurable with `--tuning-trials`)
- Constraint: Reject configurations where guard metrics are violated

**Model Hyperparameter Tuning:**
- Triggered with `--tune-model` after all features are added
- Tunes: `n_estimators`, `learning_rate`, `num_leaves`, `max_depth`, regularization, `subsample`
- Budget: 50 trials (configurable with `--model-tuning-trials`)
- Applies a complexity penalty to discourage overly large models

### Reports

Generated to `output/regression/<regression_id>/`:

| File | Content |
|------|---------|
| `regression_report.json` | Full structured data for programmatic consumption |
| `regression_report.md` | Human-readable report with tables |
| `regression_metrics.csv` | One row per step, all metrics |
| `feature_leaderboard.csv` | Features ranked by marginal contribution |
| `tuned_params.json` | Best parameters per feature |

### Database Schema

Three tables in `data/runs.db`:

- **`regression_tests`**: One row per test session (config, summary, best feature)
- **`regression_steps`**: One row per step (metrics, significance, importance, tuned params)
- **`feature_contributions`**: Aggregated leaderboard across all tests

### Architecture

```
src/regression/
    __init__.py              # Public API
    feature_registry.py      # FeatureRegistry, FeatureSpec, tunable params
    metrics.py               # METRICS_REGISTRY, significance tests
    database.py              # SQLite schema + CRUD operations
    orchestrator.py          # RegressionOrchestrator (main engine)
    tuning.py                # FeatureParamTuner, ModelParamTuner
    reporting.py             # JSON/MD/CSV report generation

scripts/
    run_regression_test.py   # CLI entry point
```

---

## 7. Automation Pipeline

### Automated Regression Testing

The script `scripts/automate_regression.py` combines gap analysis with regression testing into a single automated workflow.

**Multi-resolution support:** 1d, 4h, 1h, 15m, 5m.

### Gap Analysis

The automation pipeline performs comprehensive data gap analysis before running regressions:

- **Date gaps**: Identifies missing dates in the price series
- **Ticker coverage**: Checks which tickers are loaded vs. expected from the watchlist
- **Data quality**: Detects anomalies such as zero-volume bars, price spikes, and stale data
- **Resolution checks**: Validates that data matches the configured interval
- **Benchmark alignment**: Ensures benchmark data covers the same date range as price data

### Automated Recommendations

After gap analysis, the system generates quality scores and automated recommendations for:
- Which tickers need additional data
- Which date ranges have gaps
- Whether higher-resolution data would improve signal detection
- Whether the benchmark needs extending

### Workflow Commands

```bash
# Gap analysis only (no regression)
python scripts/automate_regression.py --watchlist tech_giants --gap-analysis-only

# Full automated regression with tuning
python scripts/automate_regression.py --watchlist tech_giants --tune

# Specify resolution
python scripts/automate_regression.py --watchlist tech_giants --resolution 4h
```

---

## 8. Data Gap Analysis Findings (Current State)

Based on the current dataset:

| Finding | Details |
|---------|---------|
| Tickers loaded | 114 (NASDAQ-100 + cross-asset ETFs) |
| Daily data | 10 years (2016-2026) via Alpaca Markets |
| Hourly data | ~22 months (yfinance 1h limit) |
| Multi-resolution | daily + hourly + 15m (in progress) |
| Benchmark | SPY (daily: 10yr, hourly: ~22mo) |
| Macro data | FRED indicators (yields, inflation, spreads, employment) |
| Sentiment data | Finnhub (news, insider, analyst, earnings) |
| Data quality score | A (95/100) |

### Resolved Gaps

1. **Ticker coverage**: Expanded from 9 to 114 tickers (NASDAQ-100 + cross-asset ETFs) with 10 years of daily data.

2. **History depth**: Resolved by switching to Alpaca Markets as primary data backend, providing 10 years of daily data (2016-2026). Hourly data remains limited to ~730 days via yfinance.

3. **Sentiment data**: Integrated Finnhub as programmatic sentiment source, providing news sentiment, insider transactions, analyst ratings, and earnings surprises.

4. **Macro data**: Added FRED economic indicators (yields, inflation, employment, credit spreads) via `scripts/download_macro.py`.

### Remaining Gaps

1. **Multi-resolution**: 15-minute data download is in progress. Full multi-resolution pipeline (daily + hourly + 15m) not yet complete.

2. **Cross-resolution comparison**: Need to compare signal quality and portfolio performance across resolutions to identify optimal resolution for the mid-term strategy.

---

## 9. CLI Reference

### Regression Testing

```bash
# Run regression test with default settings (all features, no tuning)
python scripts/run_regression_test.py run --watchlist tech_giants

# Run specific features with Bayesian tuning
python scripts/run_regression_test.py run --watchlist tech_giants --tune --features rsi macd bollinger

# Run with model hyperparameter tuning
python scripts/run_regression_test.py run --watchlist tech_giants --tune --tune-model

# List previous regression tests
python scripts/run_regression_test.py list

# List by status
python scripts/run_regression_test.py list --status completed

# View feature leaderboard
python scripts/run_regression_test.py leaderboard

# View leaderboard for a specific test
python scripts/run_regression_test.py leaderboard --regression-id <id>

# Regenerate report for a test
python scripts/run_regression_test.py report <regression_id>
python scripts/run_regression_test.py report <regression_id> -o output/custom_dir
```

### Automation

```bash
# Gap analysis only
python scripts/automate_regression.py --watchlist tech_giants --gap-analysis-only

# Full automated regression with tuning
python scripts/automate_regression.py --watchlist tech_giants --tune

# Specify resolution
python scripts/automate_regression.py --watchlist tech_giants --resolution 1h
```

### Data Management

```bash
# Download prices for a watchlist (Alpaca Markets primary, yfinance fallback)
python scripts/download_prices.py --watchlist nasdaq_100

# Download benchmark data
python scripts/download_benchmark.py

# Download fundamentals
python scripts/download_fundamentals.py

# Download FRED macro data
python scripts/download_macro.py

# Download Finnhub sentiment data
python scripts/download_sentiment.py
```

### Backtesting

```bash
# Run walk-forward backtest
python -m src.app.cli run-backtest --config config/config.yaml

# Run with specific watchlist
python -m src.app.cli run-backtest --watchlist everything --name "Full Universe"

# Run with date range
python -m src.app.cli run-backtest --watchlist tech_giants --start-date 2015-01-01 --end-date 2023-12-31
```

### QuantaAlpha / Strategy Optimization

```bash
# Evolutionary backtest (mutate params, optimize Sharpe/return/hit_rate)
python scripts/evolutionary_backtest.py --watchlist tech_giants --generations 5 --save output/evolutionary_best.yaml

# Diversified backtest (run strategy templates, select diverse subset)
python scripts/diversified_backtest.py --templates value_tilt momentum_tilt quality_tilt --max-correlation 0.85

# Lineage report (DAG of runs and evolutionary trajectories)
python scripts/lineage_report.py --output-dir output --metric sharpe_ratio --top 5

# Transfer/robustness testing
python scripts/transfer_report.py --watchlist tech_giants --transfer-watchlist sp500
```

### Trigger Backtest (Single-Ticker)

```bash
# Run trigger backtest for specific tickers
python scripts/run_trigger_backtest_live.py --tickers AMD SLV

# Bayesian optimize RSI/MACD per ticker
python scripts/optimize_macd_rsi_bayesian.py --tickers SLV --save output/best_params_SLV.json

# Validate macro filter impact
python scripts/validate_macro_influence.py --ticker SLV
```

### Portfolio and Analysis

```bash
# Build personalized portfolio
python scripts/run_portfolio_optimizer.py --profile moderate --with-ai

# Full analysis workflow
python scripts/full_analysis_workflow.py --with-commentary --with-recommendations

# Comprehensive analysis
python scripts/run_comprehensive_analysis.py --run-id <run_id>

# Strengthen recommendations (risk analysis)
python scripts/strengthen_recommendations.py --run-dir output/run_<id>
python scripts/strengthen_recommendations.py --full
python scripts/strengthen_recommendations.py --full --exclude-sectors "Energy,Defense"

# Validate safeguards
python -m src.validation.safeguards output/run_<id> --profile moderate
```

### Diagnostics

```bash
# Diagnose backtest data issues
python scripts/diagnose_backtest_data.py

# Diagnose fundamental data coverage
python scripts/diagnose_value_quality_scores.py

# Analyze filter effectiveness
python scripts/analyze_filter_effectiveness.py
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_data_completeness.py -v

# Run comprehensive suite
python tests/run_tests.py
```

### Dashboard

```bash
# Launch Streamlit dashboard
streamlit run src/app/dashboard/app.py
```

---

## 10. Architecture and File Structure

### Top-Level Structure

```
midterm-stock-planner/
├── config/                        # Configuration files
│   ├── config.yaml                # Main configuration (model, backtest, features, analysis)
│   ├── watchlists.yaml            # 16 predefined stock watchlists
│   ├── strategy_templates/        # Strategy templates (value_tilt, momentum_tilt, etc.)
│   └── tickers/                   # Per-ticker YAML (RSI, MACD, macro overrides)
├── data/                          # Data files
│   ├── prices_daily.csv           # 10yr daily OHLCV (114 tickers, Alpaca Markets)
│   ├── benchmark_daily.csv        # 10yr daily SPY benchmark
│   ├── prices.csv                 # Hourly price data (yfinance)
│   ├── benchmark.csv              # Hourly SPY benchmark
│   ├── macro_fred.csv             # FRED economic indicators
│   ├── sentiment/                 # Finnhub sentiment (news, insider, analyst, earnings)
│   ├── fundamentals.csv           # Fundamental data (PE, PB, ROE, margins)
│   ├── analysis.db                # SQLite analytics database
│   ├── sectors.csv / sectors.json # Sector classifications
│   └── universe.txt               # Current ticker universe
├── docs/                          # 67 documentation files
├── knowledgebase/                 # AI agent knowledge base
├── src/                           # Source code (~130 files, ~49,000 LOC)
├── scripts/                       # CLI and automation scripts
├── tests/                         # Test suite (208+ tests, 19 files)
├── output/                        # Analysis results (per-run folders)
├── skills/                        # Documentation/automation skills (19 files)
├── prompt/                        # Prompt templates
├── README.md                      # Project overview
├── CONTENTS.md                    # Full file inventory
├── CHANGELOG.md                   # Version history
├── DEPLOYMENT.md                  # Deployment guide
└── requirements.txt               # Python dependencies
```

### Source Code Modules (`src/`)

| Module | Purpose |
|--------|---------|
| `src/app/` | CLI entry point and Streamlit dashboard |
| `src/analytics/` | Run tracking, reporting, database |
| `src/analysis/` | Performance attribution, factor exposure, style analysis |
| `src/backtest/` | Walk-forward backtest engine (`rolling.py`) |
| `src/config/` | Configuration management (`config.py`) |
| `src/features/` | Feature engineering (`engineering.py`) |
| `src/models/` | Model training and prediction (LightGBM) |
| `src/regression/` | Regression testing framework (6 modules) |
| `src/risk/` | Risk management (parity, inverse vol, beta control) |
| `src/sentiment/` | Sentiment analysis pipeline |
| `src/fundamental/` | Fundamental data integration |
| `src/data/` | Data loading and validation |
| `src/indicators/` | Technical indicator calculations |
| `src/validation/` | Safeguards and constraint validation |
| `src/explain/` | SHAP explainability |
| `src/visualization/` | Chart and visualization generation |
| `src/strategies/` | Strategy definitions and templates |
| `src/exceptions/` | Custom exception classes |

### Regression Testing Module (`src/regression/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Public API |
| `feature_registry.py` | FeatureRegistry, FeatureSpec, tunable parameter definitions |
| `metrics.py` | METRICS_REGISTRY, statistical significance tests |
| `database.py` | SQLite schema and CRUD operations |
| `orchestrator.py` | RegressionOrchestrator (main engine coordinating all steps) |
| `tuning.py` | FeatureParamTuner, ModelParamTuner (Bayesian optimization) |
| `reporting.py` | JSON/Markdown/CSV report generation |

### Key Scripts

| Script | Purpose |
|--------|---------|
| `scripts/run_regression_test.py` | CLI entry point for regression testing |
| `scripts/automate_regression.py` | Automated gap analysis + regression |
| `scripts/download_prices.py` | Download and validate price data (Alpaca primary, yfinance fallback) |
| `scripts/download_benchmark.py` | Download/extend benchmark series |
| `scripts/download_fundamentals.py` | Download comprehensive fundamentals |
| `scripts/download_sentiment.py` | Download Finnhub sentiment data |
| `scripts/download_macro.py` | Download FRED macro data |
| `scripts/evolutionary_backtest.py` | Evolutionary parameter optimization |
| `scripts/diversified_backtest.py` | Multi-strategy diversified backtest |
| `scripts/lineage_report.py` | Run lineage DAG and best-branch analysis |
| `scripts/transfer_report.py` | Cross-universe robustness testing |
| `scripts/run_trigger_backtest_live.py` | Single-ticker trigger backtest |
| `scripts/optimize_macd_rsi_bayesian.py` | Bayesian RSI/MACD optimization |
| `scripts/validate_macro_influence.py` | Macro filter validation |
| `scripts/full_analysis_workflow.py` | Complete pipeline (all 4 stages) |
| `scripts/run_portfolio_optimizer.py` | Portfolio construction |
| `scripts/strengthen_recommendations.py` | Risk analysis and recommendation hardening |
| `scripts/stress_testing.py` | Scenario-based stress tests |
| `scripts/diagnose_backtest_data.py` | Backtest data diagnostic |

### Configuration Deep Dive

**`config/config.yaml`** controls all system behavior:

| Section | Key Settings |
|---------|-------------|
| `model` | LightGBM params (n_estimators=300, lr=0.05, num_leaves=31) |
| `trigger` | MACD/RSI defaults and optimized params path |
| `backtest` | train_years=1.0, test_years=0.25, step=1d, rebalance=4h, top_n=10, cost=0.001 |
| `data` | interval=1h, file paths |
| `features` | return_periods, volatility_windows, sentiment settings |
| `analysis` | Composite score weights (model=0.49, value=0.20, quality=0.31), filters, portfolio constraints |

**`config/watchlists.yaml`** defines 16 watchlists with metadata (name, description, category, symbols).

**`config/tickers/{TICKER}.yaml`** provides per-ticker overrides for RSI, MACD, macro filters, and backtest parameters.

**`config/strategy_templates/`** contains strategy template definitions: `value_tilt`, `momentum_tilt`, `quality_tilt`, `balanced`, `low_vol`.

---

## 11. Next Steps / Roadmap

### Completed

| Task | Status |
|------|--------|
| Download higher-resolution data via Alpaca Markets | Done -- 10yr daily data for 114 tickers via `src/data/alpaca_client.py` |
| Download missing tickers | Done -- expanded to 114 tickers (NASDAQ-100 + cross-asset ETFs) |
| Find alternative sentiment data source | Done -- Finnhub integrated (`scripts/download_sentiment.py`) with news, insider, analyst, earnings |
| Add macro data | Done -- FRED indicators (`scripts/download_macro.py`) with yields, inflation, spreads, employment |

### HIGH Priority

| Task | Details |
|------|---------|
| Complete multi-resolution pipeline | 15-minute data download in progress. Need to finalize daily + hourly + 15m pipeline and validate signal quality across resolutions. |
| Build Streamlit dashboard page for regression results | Currently regression results are only viewable via CLI and file reports. A dashboard page would enable visual exploration of feature leaderboards, step-by-step metric progression, and tuning results. |

### MEDIUM Priority

| Task | Details |
|------|---------|
| Cross-resolution comparison analysis | Compare signal quality and portfolio performance across different data resolutions (1d vs. 4h vs. 1h vs. 15m vs. 5m) to identify optimal resolution for the mid-term strategy. |

---

## Appendix: Documentation Index

The project contains 67 documentation files across `docs/`. Key references:

| Document | Path |
|----------|------|
| Regression Testing Guide | `docs/regression-testing-guide.md` |
| System Design | `docs/design.md` |
| Backtesting Guide | `docs/backtesting.md` |
| Risk Management | `docs/risk-management.md` |
| QuantaAlpha Proposal | `docs/quantaalpha-feature-proposal.md` |
| QuantaAlpha Implementation | `docs/quantaalpha-implementation-guide.md` |
| QuantaAlpha Paper Summary | `docs/quantaalpha-paper-summary.md` |
| Dashboard Guide | `docs/dashboard.md` |
| API Documentation | `docs/api-documentation.md` |
| User Guide | `docs/user-guide.md` |
| Quick Start | `docs/quick-start-guide.md` |
| Data Quality Tracking | `docs/data-quality.md` |
| Data Providers Guide | `docs/data-providers-guide.md` |
| Decision Log | `docs/decision-log.md` |
| Full Documentation Index | `docs/README.md` |

For the complete file inventory (96 files including skills, prompts, and knowledge base), see `CONTENTS.md`.
