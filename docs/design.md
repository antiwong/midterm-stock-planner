# DESIGN.md – Mid-term Stock Planner

> **Main Design Document** - This document provides the high-level overview of the system.
> For detailed specifications, see the linked documents below.

## Document Index

| Document | Description |
|----------|-------------|
| [design.md](design.md) | Main overview, goals, architecture (this document) |
| [data-engineering.md](data-engineering.md) | Data loading, feature engineering, dataset assembly |
| [model-training.md](model-training.md) | Model training, prediction, persistence |
| [backtesting.md](backtesting.md) | Walk-forward backtest, performance metrics, costs |
| [explainability.md](explainability.md) | SHAP explanations, interpretability |
| [risk-management.md](risk-management.md) | Risk metrics, position sizing, portfolio risk |
| [risk-parity.md](risk-parity.md) | Volatility-aware allocation, risk parity, beta control |
| [technical-indicators.md](technical-indicators.md) | Technical indicators, strategy features |
| [visualization-analytics.md](visualization-analytics.md) | Charts, performance visualization, analytics |
| [fundamental-data.md](fundamental-data.md) | SEC filings, fundamental data fetching |
| [sentiment.md](sentiment.md) | News sentiment analysis, A/B comparison |
| [comparison.md](comparison.md) | Feature comparison: Stockbot vs Mid-term Stock Planner |
| [configuration-cli.md](configuration-cli.md) | Configuration, CLI commands, run tracking |
| **New in v3.0** | |
| [portfolio-builder.md](portfolio-builder.md) | **NEW** Personalized portfolio construction |
| [domain-analysis.md](domain-analysis.md) | **NEW** Vertical/horizontal stock selection |
| [ai-insights.md](ai-insights.md) | Gemini-powered AI analysis and recommendations |
| [dashboard.md](dashboard.md) | Streamlit web dashboard for browsing results |
| [analytics-database.md](analytics-database.md) | SQLite database schema and management |
| [api-configuration.md](api-configuration.md) | API key setup and configuration |
| [data-validation.md](data-validation.md) | Data quality validation for AI insights |
| [portfolio-comparison.md](portfolio-comparison.md) | Comparison of Purchase Triggers vs Portfolio Builder methods |
| [analysis-improvements.md](analysis-improvements.md) | Roadmap for enhancing analytical capabilities |

---

## 1. Goal & Investment Spec

### 1.1 Goal

Build an interpretable stock ranking and backtesting system for a ~3‑month horizon, suitable for a mid‑term investor who rebalances monthly and cares about:

- Reasonable risk (controlled drawdown, diversification).
- Transparent drivers of performance (explainable factors, not black‑box noise).

### 1.2 Investment Profile

```
┌─────────────────────────────────────────────────────────────────────┐
│                    INVESTMENT PROFILE                                │
├─────────────────────────────────────────────────────────────────────┤
│  Horizon:        3 months forward return                            │
│  Rebalance:      Monthly (option for bi-weekly)                     │
│  Universe:       Liquid large/mid-cap US stocks                     │
│  Benchmark:      S&P 500 / MSCI World                               │
│  Objective:      Risk-adjusted outperformance (Sharpe/Sortino)      │
└─────────────────────────────────────────────────────────────────────┘
```

- **Horizon**: 3 months forward return
- **Rebalance frequency**: Monthly (with option for bi-weekly)
- **Universe**: Liquid large/mid‑cap stocks (configurable)
- **Benchmark**: Broad equity index (S&P 500, MSCI World)
- **Objective**: Risk-adjusted outperformance with controlled drawdowns

### 1.3 Risk & Portfolio Constraints

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PORTFOLIO CONSTRAINTS                             │
├───────────────────────────┬─────────────────────────────────────────┤
│  Max Single Stock Weight  │  ≤ 5%                                   │
│  Max Sector Weight        │  ≤ 25%                                  │
│  Max Turnover/Rebalance   │  ≤ 30%                                  │
│  Max Drawdown Tolerance   │  Configurable threshold                 │
│  Cash Buffer (optional)   │  ~5%                                    │
└───────────────────────────┴─────────────────────────────────────────┘
```

> **See Also**: [risk-management.md](risk-management.md) for detailed risk metrics and position sizing.

---

## 2. Core Use‑Cases

### Use Case Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              USE CASES                                        │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   UC1: RANK     │       │ UC2: PORTFOLIO  │       │  UC3: EXPLAIN   │
│    STOCKS       │       │  SUGGESTION     │       │    FACTORS      │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ Predict 3-month │       │ Long-only top N │       │ Per-stock SHAP  │
│ excess return   │       │ or top decile   │       │ contributions   │
│ vs benchmark    │       │ equal-weight    │       │                 │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  UC4: BACKTEST  │       │  UC5: TRACK     │       │  UC6: COMPARE   │
│   WALK-FORWARD  │       │    RUNS         │       │   STRATEGIES    │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ Sharpe, Sortino │       │ Store configs,  │       │ Multiple model  │
│ Max DD, turnover│       │ metrics, equity │       │ versions side   │
│ hit rate        │       │ curves          │       │ by side         │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

| Use Case | Description | Related Document |
|----------|-------------|------------------|
| UC1: Rank Stocks | Predict 3‑month excess return vs benchmark | [model-training.md](model-training.md) |
| UC2: Portfolio Suggestion | Long‑only top N equal‑weight | [risk-management.md](risk-management.md) |
| UC3: Explain Factors | Per‑stock SHAP contributions | [explainability.md](explainability.md) |
| UC4: Backtest | Walk‑forward evaluation | [backtesting.md](backtesting.md) |
| UC5: Track Runs | Store configs, metrics | [configuration-cli.md](configuration-cli.md) |
| UC6: Compare Strategies | Side‑by‑side model comparison | [visualization-analytics.md](visualization-analytics.md) |

---

## 3. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SYSTEM ARCHITECTURE OVERVIEW                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLI LAYER                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  run-backtest              score-latest              compare-runs    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  See: configuration-cli.md                                                   │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PIPELINE LAYER                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │ prepare_train() │    │prepare_infer()  │    │ run_backtest()  │          │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘          │
│                                                                              │
│  See: data-engineering.md, backtesting.md                                    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CORE MODULES                                      │
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │  Loader  │   │ Engineer │   │ Trainer  │   │Predictor │   │  SHAP    │  │
│  │          │   │          │   │          │   │          │   │ Explain  │  │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘  │
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐                  │
│  │ Backtest │   │   Risk   │   │Analytics │   │ Visualize│                  │
│  │          │   │          │   │          │   │          │                  │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘                  │
│                                                                              │
│  See: model-training.md, explainability.md, risk-management.md               │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTENDED MODULES                                    │
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐                  │
│  │Technical │   │ Strategy │   │ Position │   │Fundament │                  │
│  │Indicators│   │ Features │   │  Sizing  │   │  (SEC)   │                  │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘                  │
│                                                                              │
│  See: technical-indicators.md, fundamental-data.md                           │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                        │
│                                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                     │
│  │  prices.csv  │   │ fundament.csv│   │benchmark.csv │                     │
│  └──────────────┘   └──────────────┘   └──────────────┘                     │
│                                                                              │
│  ┌──────────────┐   ┌──────────────┐                                        │
│  │    models/   │   │    runs/     │                                        │
│  └──────────────┘   └──────────────┘                                        │
│                                                                              │
│  See: data-engineering.md                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Module Directory Structure

```
src/
├── __init__.py
├── exceptions.py              # Custom exceptions
├── pipeline.py                # Pipeline helpers
│
├── data/                      # Data loading
│   ├── __init__.py            # See: data-engineering.md
│   └── loader.py
│
├── features/                  # Feature engineering
│   ├── __init__.py            # See: data-engineering.md
│   └── engineering.py
│
├── models/                    # Model training & prediction
│   ├── __init__.py            # See: model-training.md
│   ├── trainer.py
│   └── predictor.py
│
├── backtest/                  # Backtesting
│   ├── __init__.py            # See: backtesting.md
│   └── rolling.py
│
├── explain/                   # Explainability
│   ├── __init__.py            # See: explainability.md
│   └── shap_explain.py
│
├── risk/                      # Risk management
│   ├── __init__.py            # See: risk-management.md
│   ├── metrics.py
│   ├── position_sizing.py
│   └── portfolio.py
│
├── indicators/                # Technical indicators
│   ├── __init__.py            # See: technical-indicators.md
│   └── technical.py
│
├── strategies/                # Strategy features
│   ├── __init__.py            # See: technical-indicators.md
│   ├── momentum.py
│   └── mean_reversion.py
│
├── fundamental/               # Fundamental data
│   ├── __init__.py            # See: fundamental-data.md
│   ├── sec_filings.py
│   └── data_fetcher.py
│
├── visualization/             # Visualization
│   ├── __init__.py            # See: visualization-analytics.md
│   ├── charts.py
│   └── performance.py
│
├── analytics/                 # Analytics
│   ├── __init__.py            # See: visualization-analytics.md
│   └── performance.py
│
├── config/                    # Configuration
│   ├── __init__.py            # See: configuration-cli.md
│   └── config.py
│
└── app/                       # CLI Application
    ├── __init__.py            # See: configuration-cli.md
    └── cli.py
```

---

## 5. Data Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         END-TO-END DATA FLOW                                 │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │ prices.csv  │     │fundament.csv│     │benchmark.csv│
    └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
           │                   │                   │
           └───────────────────┼───────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    DATA LOADER      │  ← data-engineering.md
                    │   (loader.py)       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ FEATURE ENGINEERING │  ← data-engineering.md
                    │  (engineering.py)   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ TRAINING DATASET    │  ← data-engineering.md
                    │ (features + target) │
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   TRAIN     │     │   PREDICT   │     │  BACKTEST   │
    │   MODEL     │     │   SCORES    │     │   WALK-FWD  │
    │             │     │             │     │             │
    │ model-      │     │ model-      │     │ backtesting │
    │ training.md │     │ training.md │     │ .md         │
    └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
           │                   │                   │
           ▼                   ▼                   ▼
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   MODEL     │     │   RANKED    │     │  BACKTEST   │
    │   + META    │     │   STOCKS    │     │   RESULTS   │
    └─────────────┘     └──────┬──────┘     └──────┬──────┘
                               │                   │
                               ▼                   ▼
                    ┌─────────────────────┐ ┌─────────────────┐
                    │      EXPLAIN        │ │    VISUALIZE    │
                    │   (SHAP values)     │ │   (charts)      │
                    │                     │ │                 │
                    │  explainability.md  │ │ visualization-  │
                    │                     │ │ analytics.md    │
                    └─────────────────────┘ └─────────────────┘
```

---

## 6. Prediction Model Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CROSS-SECTIONAL PREDICTION MODEL                          │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────┐
                    │    FOR EACH (date, ticker)  │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         FEATURE VECTOR                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Returns  │ │Volatility│ │  Volume  │ │Valuation │ │Technical │        │
│  │ 1,3,6,12M│ │ 20d, 60d │ │ $ Volume │ │ PE, PB   │ │ RSI,MACD │        │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘        │
│       │            │            │            │            │               │
│  data-engineering.md       data-engineering.md      technical-indicators.md│
│       └────────────┴────────────┴────────────┴────────────┘              │
│                                 │                                         │
└─────────────────────────────────┼─────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │      LIGHTGBM MODEL         │  ← model-training.md
                    │   (Gradient Boosted Trees)  │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │     PREDICTED SCORE         │
                    │  (3-month excess return)    │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │   CROSS-SECTIONAL RANK      │
                    │   (1 = best, N = worst)     │
                    └─────────────────────────────┘
```

> **See Also**: [model-training.md](model-training.md) for full training pipeline details.

---

## 7. Scope & Priorities

### Development Roadmap

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEVELOPMENT ROADMAP                                  │
└─────────────────────────────────────────────────────────────────────────────┘

         MVP (Phase 1)              Phase 2                  Phase 3
              │                        │                        │
              ▼                        ▼                        ▼
┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────┐
│ ✅ Data loading         │ │ ✅ Extended indicators  │ │ ☐ Time-series       │
│ ✅ Core features        │ │ ✅ Portfolio SHAP       │ │   overlay           │
│ ✅ LightGBM model       │ │ ✅ Regime analysis      │ │ ☐ Live data         │
│ ✅ Walk-forward BT      │ │ ✅ Risk module         │ │   integration       │
│ ✅ SHAP explanations    │ │ ✅ Position sizing     │ │ ☐ Broker connect    │
│ ✅ CLI                  │ │ ✅ Sentiment module    │ │                      │
│ ✅ Run tracking         │ │ ✅ Risk Parity         │ │                      │
│                         │ │ ✅ AI Insights         │ │                      │
│                         │ │ ✅ Web Dashboard       │ │                      │
│                         │ │ ✅ Analytics DB        │ │                      │
└─────────────────────────┘ └─────────────────────────┘ └─────────────────────┘

              │                        │                        │
              │     CURRENT STATE      │                        │
              └────────────────────────┼────────────────────────┘
                                       │
                                Phase 2 complete ✅
```

### Phase Details

| Phase | Features | Status | Documents |
|-------|----------|--------|-----------|
| **MVP (Phase 1)** | Data loading, Core features, LightGBM, Walk-forward BT, SHAP, CLI, Run tracking | ✅ Complete | [data-engineering.md](data-engineering.md), [model-training.md](model-training.md), [backtesting.md](backtesting.md) |
| **Phase 2** | Extended indicators, Portfolio SHAP, Risk module, Position sizing, Risk Parity, AI Insights, Dashboard, Analytics DB | ✅ Complete | [technical-indicators.md](technical-indicators.md), [risk-management.md](risk-management.md), [risk-parity.md](risk-parity.md), [ai-insights.md](ai-insights.md), [dashboard.md](dashboard.md) |
| **Phase 3** | Time-series overlay, Live data integration, Broker connection | ☐ Planned | - |

---

## 8. Non‑functional Constraints

- **Performance**:
  - Training: may take minutes for thousands of stocks over years
  - Scoring: must finish within ~10 seconds for a few hundred stocks
- **Code Quality**:
  - Modular, testable functions
  - Clear interfaces and type hints
- **Safety**:
  - No live trading or broker integration in MVP
  - Outputs are research signals only

---

## 9. Quick Start Guide

### 1. Run a Backtest

```bash
python -m src.app.cli run-backtest --config config/config.yaml
```

> See [configuration-cli.md](configuration-cli.md) for CLI details.

### 2. Score Current Universe

```bash
python -m src.app.cli score-latest \
    --config config/config.yaml \
    --model models/latest \
    --date 2024-01-15
```

### 3. Generate Visualizations

```python
from src.visualization.performance import plot_equity_curve
from src.visualization.charts import plot_price_with_indicators

# See visualization-analytics.md for full API
```

---

## 10. Related Documents

### Core Documentation
- **[data-engineering.md](data-engineering.md)** - Data loading, feature engineering, dataset assembly
- **[model-training.md](model-training.md)** - Model training, prediction, persistence
- **[backtesting.md](backtesting.md)** - Walk-forward backtest, performance metrics, costs
- **[explainability.md](explainability.md)** - SHAP explanations, interpretability
- **[risk-management.md](risk-management.md)** - Risk metrics, position sizing, portfolio risk
- **[technical-indicators.md](technical-indicators.md)** - Technical indicators, strategy features
- **[visualization-analytics.md](visualization-analytics.md)** - Charts, performance visualization
- **[fundamental-data.md](fundamental-data.md)** - SEC filings, fundamental data fetching
- **[sentiment.md](sentiment.md)** - News sentiment analysis, A/B comparison
- **[configuration-cli.md](configuration-cli.md)** - Configuration, CLI commands, run tracking

### New Features (Phase 2)
- **[risk-parity.md](risk-parity.md)** - Volatility-aware allocation, risk parity, sector constraints
- **[ai-insights.md](ai-insights.md)** - Gemini-powered AI analysis and recommendations
- **[dashboard.md](dashboard.md)** - Streamlit web dashboard for browsing results
- **[analytics-database.md](analytics-database.md)** - SQLite database schema and management
- **[api-configuration.md](api-configuration.md)** - API key setup and configuration
