# Documentation Index

**Mid-term Stock Planner v3.11.2** - Complete documentation for the ML-powered stock ranking and portfolio optimization system.

## Start Here

| If you want to... | Read this |
|---|---|
| Get up and running quickly | [Quick Start Guide](quick-start-guide.md) |
| Learn the full workflow | [User Guide](user-guide.md) |
| Understand the architecture | [Design Overview](design.md) |
| Use the API programmatically | [API Documentation](api-documentation.md) |
| See common questions | [FAQ](faq.md) |

---

## Getting Started

| Document | Description |
|----------|-------------|
| [Quick Start Guide](quick-start-guide.md) | Installation, first analysis, 5-minute setup |
| [User Guide](user-guide.md) | Complete workflows, advanced features, best practices |
| [FAQ](faq.md) | Common questions and answers |
| [Migration Guide v3.11](migration-guide-v3.11.md) | Upgrading from v3.10 to v3.11 |

## Architecture & Design

| Document | Description |
|----------|-------------|
| [Design Overview](design.md) | System architecture, module structure, data flow |
| [Data Engineering](data-engineering.md) | Data loading, feature engineering, dataset assembly |
| [Model Training](model-training.md) | LightGBM training, prediction, model persistence |
| [Backtesting](backtesting.md) | Walk-forward backtest, performance metrics, transaction costs |
| [Explainability](explainability.md) | SHAP explanations, per-stock interpretability |
| [Comparison](comparison.md) | Feature comparison: Stockbot vs Mid-term Stock Planner |

## Risk & Portfolio Management

| Document | Description |
|----------|-------------|
| [Risk Management](risk-management.md) | Risk metrics, position sizing, portfolio risk |
| [Risk Parity](risk-parity.md) | Volatility-aware allocation, risk parity, beta control |
| [Risk Analysis Guide](risk-analysis-guide.md) | Tail risk, VaR, stress testing, conscience filters |
| [Portfolio Builder](portfolio-builder.md) | Personalized portfolio construction |
| [Domain Analysis](domain-analysis.md) | Vertical/horizontal stock selection |
| [Portfolio Comparison](portfolio-comparison.md) | Purchase Triggers vs Portfolio Builder methods |

## Features & Indicators

| Document | Description |
|----------|-------------|
| [QuantaAlpha Feature Proposal](quantaalpha-feature-proposal.md) | Gap/overnight features, transfer testing, evolutionary roadmap |
| [Technical Indicators](technical-indicators.md) | RSI, MACD, Bollinger Bands, ATR, ADX, OBV, gap features |
| [Sentiment Analysis](sentiment.md) | Multi-source news sentiment with Gemini LLM |
| [Fundamental Data](fundamental-data.md) | SEC filings, PE/PB/ROE data fetching |
| [AI Insights](ai-insights.md) | Gemini-powered analysis and recommendations |
| [Purchase Triggers](purchase-triggers.md) | Entry point identification and trigger logic |
| [Purchase Trigger Improvements](purchase-triggers-improvements.md) | Enhancement roadmap for trigger system |

## Dashboard & UI

| Document | Description |
|----------|-------------|
| [Dashboard](dashboard.md) | Streamlit web interface overview |
| [Visualization & Analytics](visualization-analytics.md) | Charts, performance visualization |
| [UI Improvements v3.10.3](ui-improvements-v3.10.3.md) | Sector colors, watchlist manager enhancements |

## Analytics & Reports

| Document | Description |
|----------|-------------|
| [Comprehensive Analysis System](comprehensive-analysis-system.md) | Performance attribution, benchmark, factor exposure, style |
| [Turnover & Churn Analysis](turnover-churn-analysis-guide.md) | Portfolio turnover, holding periods, position stability |
| [Report Templates Guide](report-templates-guide.md) | Custom report generation with templates |
| [Alert System Guide](alert-system-guide.md) | Email/SMS notifications, portfolio alerts |
| [Run vs Comprehensive Analysis](run-vs-comprehensive-analysis.md) | When to use each analysis type |

## API & Configuration

| Document | Description |
|----------|-------------|
| [API Documentation](api-documentation.md) | Complete API reference for all modules |
| [Configuration & CLI](configuration-cli.md) | Config file, CLI commands, run tracking |
| [API Configuration](api-configuration.md) | API key setup (NewsAPI, Gemini, etc.) |
| [Data Validation](data-validation.md) | Data quality checks for AI insights |
| [GARCH Design](garch-design.md) | GARCH volatility modeling design |

## Data & Setup Guides

| Document | Description |
|----------|-------------|
| [Adding Symbols Guide](adding-symbols-guide.md) | How to add new stock symbols |
| [Download Fundamentals Guide](download-fundamentals-guide.md) | Downloading PE, PB, ROE data |
| [Fundamentals Data Sources](fundamentals-data-sources.md) | Available fundamental data providers |
| [Watchlist Validation Guide](watchlist-validation-guide.md) | Validating watchlist symbols |
| [Failed Symbols Guide](failed-symbols-guide.md) | Handling failed symbol downloads |
| [Filter Optimization Guide](filter-optimization-guide.md) | Optimizing stock filters |
| [Running Comprehensive Analysis](running-comprehensive-analysis.md) | Step-by-step comprehensive analysis |

## Testing & Validation

| Document | Description |
|----------|-------------|
| [Test Suite Documentation](test-suite-documentation.md) | 208+ test cases across all components |
| [Test Results Summary](test-results-summary.md) | Test execution results and pass rates |
| [Test Execution Results](test-execution-results.md) | Latest test run details |
| [Validation Test Plan](validation-test-plan.md) | Validation strategy and test plan |
| [Validation Results](validation-results.md) | System validation results |
| [Validation Report v3.9.0](validation-report-v3.9.0.md) | v3.9.0 release validation |
| [Analysis Validation Results](analysis-validation-results.md) | Analysis module validation |
| [Data Completeness Validation](data-completeness-validation.md) | Data completeness checks |
| [Export & Visualization Validation](export-visualization-validation.md) | Export feature validation |
| [Performance & UX Validation](performance-ux-validation.md) | Performance and UX testing |
| [Recommendation Tracking Validation](recommendation-tracking-validation.md) | Recommendation system validation |
| [Benchmark Comparison Fix](benchmark-comparison-fix.md) | Timezone mismatch fix documentation |
| [Quality Score Fix](quality-score-fix.md) | Quality score calculation fix |

## Release Notes & Roadmap

| Document | Description |
|----------|-------------|
| [v3.11 Complete Summary](v3.11-complete-summary.md) | Full v3.11 release notes |
| [Roadmap v3.11](roadmap-v3.11.md) | v3.11 development roadmap |
| [Implementation Progress v3.11](implementation-progress-v3.11.md) | v3.11 implementation tracking |
| [Next Steps v3.11](next-steps-v3.11.md) | Post-v3.11 priorities |
| [Comprehensive Update v3.10.5](comprehensive-update-v3.10.5.md) | v3.10.5 update details |
| [Next Steps](next-steps.md) | General development priorities |
| [Analysis Improvements](analysis-improvements.md) | Analytical capability roadmap |
| [Requirements](REQUIREMENTS.md) | System and project requirements |
