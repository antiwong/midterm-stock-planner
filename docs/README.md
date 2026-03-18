# Documentation Index

**Mid-term Stock Planner v3.11.2** — Complete documentation for the ML-powered stock ranking and portfolio optimization system.

---

## Contents

- [Start Here](#start-here)
- [Getting Started](#getting-started)
- [Architecture & Design](#architecture--design)
- [Risk & Portfolio Management](#risk--portfolio-management)
- [Features & Indicators](#features--indicators)
- [Dashboard & UI](#dashboard--ui)
- [Analytics & Reports](#analytics--reports)
- [API & Configuration](#api--configuration)
- [Daily Run Pipeline (Technical Deep-Dive)](#daily-run-pipeline-technical-deep-dive)
- [Trading & Execution](#trading--execution)
- [Data & Setup Guides](#data--setup-guides)
- [Testing & Validation](#testing--validation)
- [Reference & Decisions](#reference--decisions)
- [Release Notes & Roadmap](#release-notes--roadmap)
- [Archive](#archive)

---

## Start Here

| If you want to... | Read this |
|---|---|
| Get up and running quickly | [Quick Start Guide](quick-start-guide.md) |
| Learn the full workflow | [User Guide](user-guide.md) |
| Understand the architecture | [Design Overview](design.md) |
| Run the daily trading pipeline | [Daily Run Guide](daily-run.md) |
| Use the API programmatically | [API Documentation](api-documentation.md) |
| See common questions | [FAQ](faq.md) |

---

## Getting Started [Guide]

| Document | Description |
|----------|-------------|
| [Quick Start Guide](quick-start-guide.md) | [Guide] Installation, first analysis, 5-minute setup |
| [User Guide](user-guide.md) | [Guide] Complete workflows, advanced features, best practices |
| [FAQ](faq.md) | [Reference] Common questions and answers |
| [Common Workflows](common-workflows.md) | [Guide] Step-by-step recipes for daily tasks |
| [Troubleshooting](troubleshooting.md) | [Guide] Consolidated troubleshooting for all components |
| [Developer Guide](developer-guide.md) | [Guide] Dev environment setup, module structure, testing |
| [Migration Guide v3.11](migration-guide-v3.11.md) | [Guide] Upgrading from v3.10 to v3.11 |

## Architecture & Design [Architecture]

| Document | Description |
|----------|-------------|
| [Design Overview](design.md) | [Architecture] System architecture, module structure, data flow |
| [Data Engineering](data-engineering.md) | [Architecture] Data loading, feature engineering, dataset assembly |
| [Model Training](model-training.md) | [Reference] LightGBM training, prediction, model persistence |
| [Backtesting](backtesting.md) | [Reference] Walk-forward backtest, performance metrics, IC and overfitting detection, transaction costs |
| [Explainability](explainability.md) | [Reference] SHAP explanations, per-stock interpretability |
| [Comparison](comparison.md) | [Reference] Feature comparison: Stockbot vs Mid-term Stock Planner |

## Risk & Portfolio Management [Reference]

| Document | Description |
|----------|-------------|
| [Risk Management](risk-management.md) | [Reference] Risk metrics, position sizing, portfolio risk |
| [Risk Parity](risk-parity.md) | [Reference] Volatility-aware allocation, risk parity, beta control |
| [Risk Analysis Guide](risk-analysis-guide.md) | [Guide] Tail risk, VaR, stress testing, conscience filters |
| [Portfolio Builder](portfolio-builder.md) | [Guide] Personalized portfolio construction |
| [Domain Analysis](domain-analysis.md) | [Reference] Vertical/horizontal stock selection |
| [Portfolio Comparison](portfolio-comparison.md) | [Reference] Purchase Triggers vs Portfolio Builder methods |

## Features & Indicators [Reference]

| Document | Description |
|----------|-------------|
| [Technical Indicators](technical-indicators.md) | [Reference] RSI, MACD, Bollinger Bands, ATR, ADX, OBV, relative strength, gap features |
| [Macro Indicators](macro-indicators.md) | [Reference] DXY, VIX, GSR, institutional filter for Trigger Backtester |
| [Feature Importance Methods](feature-importance-methods.md) | [Reference] Multi-method walk-forward importance analysis (LightGBM gain, IC, SHAP) |
| [Cross-Asset Rotation](cross-asset-rotation-features.md) | [Reference] Gold/silver/BTC rotation signals for capital flow detection |
| [Purchase Triggers](purchase-triggers.md) | [Reference] Entry point identification and trigger logic |
| [Sentiment Analysis](sentiment.md) | [Architecture] Multi-source news sentiment with Gemini LLM |
| [Fundamental Data](fundamental-data.md) | [Reference] SEC filings, PE/PB/ROE data fetching |
| [AI Insights](ai-insights.md) | [Reference] Gemini-powered analysis and recommendations |
| [GARCH Design](garch-design.md) | [Architecture] GARCH volatility modeling design |

### QuantaAlpha Research

| Document | Description |
|----------|-------------|
| [QuantaAlpha Feature Proposal](quantaalpha-feature-proposal.md) | [Architecture] Gap features, evolutionary optimizer, diversified templates, lineage |
| [QuantaAlpha Implementation Guide](quantaalpha-implementation-guide.md) | [Guide] Factor formulas, parameter tables, codebase mapping, transfer learning |
| [QuantaAlpha Paper Summary](quantaalpha-paper-summary.md) | [Reference] Summary of arXiv:2602.07085 — IC, ARR, MDD benchmarks |
| [QuantaAlpha Integration Analysis](quantaalpha-integration-analysis.md) | [Reference] Integration analysis and feasibility assessment |

## Dashboard & UI [Guide]

| Document | Description |
|----------|-------------|
| [Dashboard](dashboard.md) | [Guide] Streamlit web interface overview |
| [Visualization & Analytics](visualization-analytics.md) | [Reference] Charts, performance visualization |

## Analytics & Reports [Reference]

| Document | Description |
|----------|-------------|
| [Comprehensive Analysis System](comprehensive-analysis-system.md) | [Architecture] Performance attribution, benchmark, factor exposure, style |
| [Comprehensive System Guide](comprehensive-system-guide.md) | [Guide] End-to-end system guide |
| [Run vs Comprehensive Analysis](run-vs-comprehensive-analysis.md) | [Guide] When to use each analysis type |
| [Running Comprehensive Analysis](running-comprehensive-analysis.md) | [Guide] Step-by-step guide |
| [Turnover & Churn Analysis](turnover-churn-analysis-guide.md) | [Guide] Portfolio turnover, holding periods, position stability |
| [Report Templates Guide](report-templates-guide.md) | [Guide] Custom report generation with templates |
| [Alert System Guide](alert-system-guide.md) | [Guide] Email/SMS notifications, portfolio alerts |
| [Analytics Database](analytics-database.md) | [Reference] Analytics database schema and usage |

## API & Configuration [Reference]

| Document | Description |
|----------|-------------|
| [API Documentation](api-documentation.md) | [Reference] Complete API reference for all modules |
| [Configuration Reference](configuration-reference.md) | [Reference] Complete config.yaml key reference with types, defaults, valid ranges |
| [Configuration & CLI](configuration-cli.md) | [Reference] Config file, CLI commands, run tracking |
| [API Configuration](api-configuration.md) | [Guide] API key setup (NewsAPI, Gemini, etc.) |
| [Data Validation](data-validation.md) | [Reference] Data quality checks for AI insights |
| [config/tickers/README.md](../config/tickers/README.md) | [Reference] Per-ticker YAML schema (RSI, MACD, macro) |
| [config/strategy_templates/README.md](../config/strategy_templates/README.md) | [Reference] Strategy templates (value_tilt, momentum_tilt, etc.) |

## Daily Run Pipeline (Technical Deep-Dive) [Architecture]

The [`docs/daily-run/`](daily-run/README.md) folder contains detailed technique documentation for every method used in the daily paper trading pipeline.

| Document | Technique |
|----------|-----------|
| [Pipeline Overview](daily-run/pipeline-overview.md) | [Architecture] End-to-end execution flow, data flow diagram |
| [Feature Engineering](daily-run/feature-engineering.md) | [Reference] MACD, Bollinger, ATR, ADX formulas, feature toggle rationale |
| [Walk-Forward Backtest](daily-run/walk-forward-backtest.md) | [Reference] Rolling window methodology, IC computation, overfitting detection |
| [LightGBM Model](daily-run/lightgbm-model.md) | [Reference] Hyperparameters, training process, SHAP explanations |
| [Signal Generation](daily-run/signal-generation.md) | [Reference] ML + trigger ensemble, per-ticker optimization |
| [Position Sizing](daily-run/position-sizing.md) | [Reference] Confidence-based, inverse-vol, Kelly, ATR-based methods |
| [Risk Controls](daily-run/risk-controls.md) | [Reference] Drawdown close, stop-loss, VIX scaling, daily loss limit |
| [Alpaca Execution](daily-run/alpaca-execution.md) | [Reference] Rebalancing algorithm, order types, state sync |
| [Accuracy Calibration](daily-run/accuracy-calibration.md) | [Reference] Adaptive exposure from signal hit rate |
| [Daily Routine Orchestrator](daily-run/orchestrator.md) | [Reference] Single script managing all 4 portfolios, data downloads, notifications |
| [Forward Testing Journal](daily-run/forward-testing.md) | [Reference] Prediction logging, 5d/63d horizon evaluation, accuracy tracking |
| [React Trading Dashboard](daily-run/react-dashboard.md) | [Reference] React SPA (port 5000) + FastAPI (port 9000) for daily trading |

## Trading & Execution [Guide]

| Document | Description |
|----------|-------------|
| [Daily Run Guide](daily-run.md) | [Guide] Daily paper trading pipeline — commands, automation, quick start |
| [Daily Run Technical Reference](daily-run/README.md) | [Reference] Deep-dive into every technique used |
| [Alpaca Paper Trading](alpaca-paper-trading.md) | [Guide] Alpaca integration setup, API keys, live paper execution |
| [Cross-Asset Rotation Features](cross-asset-rotation-features.md) | [Reference] Gold/silver/BTC rotation signals for capital flow detection |
| [Sentiment Integration Plan](sentiment-integration.md) | [Architecture] Phased sentiment approach (A/B/C/D), data sources, feature pipeline |
| [Sentiment Data Audit](sentiment-data-audit.md) | [Reference] Data quality assessment, coverage gaps, source documentation |
| [Reference Project Analysis](../reference/analysis.md) | [Reference] NoFx + daily_stock_analysis — ideas borrowed for risk, calibration, sizing |

## Data & Setup Guides [Guide]

| Document | Description |
|----------|-------------|
| [Adding Symbols Guide](adding-symbols-guide.md) | [Guide] How to add new stock symbols |
| [Download Fundamentals Guide](download-fundamentals-guide.md) | [Guide] Downloading PE, PB, ROE data |
| [Fundamentals Data Sources](fundamentals-data-sources.md) | [Reference] Available fundamental data providers |
| [Data Providers Guide](data-providers-guide.md) | [Reference] All stock market data providers |
| [Data Quality](data-quality.md) | [Reference] Data quality tracking and monitoring |
| [Watchlist Validation Guide](watchlist-validation-guide.md) | [Guide] Validating watchlist symbols |
| [Failed Symbols Guide](failed-symbols-guide.md) | [Guide] Handling failed symbol downloads |
| [Filter Optimization Guide](filter-optimization-guide.md) | [Guide] Optimizing stock filters |

## Testing & Validation [Reference]

| Document | Description |
|----------|-------------|
| [Test Suite Documentation](test-suite-documentation.md) | [Reference] 208+ test cases across all components |
| [Regression Testing Guide](regression-testing-guide.md) | [Guide] Walk-forward regression testing workflow |
| [Validation Report v3.9.0](validation-report-v3.9.0.md) | [Reference] v3.9.0 release validation |
| [Analysis Validation Results](analysis-validation-results.md) | [Reference] Analysis module validation |
| [Data Completeness Validation](data-completeness-validation.md) | [Reference] Data completeness checks |
| [Export & Visualization Validation](export-visualization-validation.md) | [Reference] Export feature validation |
| [Performance & UX Validation](performance-ux-validation.md) | [Reference] Performance and UX testing |
| [Recommendation Tracking Validation](recommendation-tracking-validation.md) | [Reference] Recommendation system validation |
| [Benchmark Comparison Fix](benchmark-comparison-fix.md) | [Reference] Timezone mismatch fix documentation |
| [Quality Score Fix](quality-score-fix.md) | [Reference] Quality score calculation fix |

## Optimization Reports [Reference]

| Document | Description |
|----------|-------------|
| [Semiconductors Bayesian Optimization](../output/reports/bayesian_optimization_semiconductors_20260316.md) | 22 tickers, avg Sharpe=0.517, best TSM (2.01) |
| [Precious Metals Bayesian Optimization](../output/reports/bayesian_optimization_precious_metals_20260316.md) | 31 tickers, avg Sharpe=0.871, best HMY (2.82) |

## Reference & Decisions [Reference]

| Document | Description |
|----------|-------------|
| [Decision Log](decision-log.md) | [Reference] Architectural decisions with rationale |
| [Requirements](REQUIREMENTS.md) | [Reference] System and project requirements |

## Release Notes & Roadmap [Reference]

| Document | Description |
|----------|-------------|
| [v3.11 Complete Summary](v3.11-complete-summary.md) | [Reference] Full v3.11 release notes |
| [Roadmap v3.11](roadmap-v3.11.md) | [Reference] v3.11 development roadmap |
| [Implementation Progress v3.11](implementation-progress-v3.11.md) | [Reference] v3.11 implementation tracking |
| [Next Steps v3.11](next-steps-v3.11.md) | [Reference] Post-v3.11 priorities |
| [Analysis Improvements](analysis-improvements.md) | [Reference] Analytical capability roadmap |

---

## Archive

Older or superseded documentation moved here for reference.

| Document | Description |
|----------|-------------|
| [Validation Test Plan](archive/validation-test-plan.md) | Validation strategy and test plan |
| [Validation Results](archive/validation-results.md) | System validation results |
| [Test Results Summary](archive/test-results-summary.md) | Test execution results and pass rates |
| [Test Execution Results](archive/test-execution-results.md) | Latest test run details |
| [Comprehensive Update v3.10.5](archive/comprehensive-update-v3.10.5.md) | v3.10.5 update details |
| [UI Improvements v3.10.3](archive/ui-improvements-v3.10.3.md) | Sector colors, watchlist manager enhancements |
| [Next Steps](archive/next-steps.md) | General development priorities (superseded by next-steps-v3.11.md) |
