# CURSOR Rules for Mid-term Stock Planner

You are helping build a Python project for a mid-term stock ranking and backtesting tool.

## Project context

- Horizon: ~3 months.
- Rebalance: monthly.
- Primary model: gradient-boosted trees for cross-sectional ranking.
- Secondary (optional): simple time-series overlay.

## General instructions

- Always respect `DESIGN.md` and `REQUIREMENTS.md`.
- Prefer small, composable functions and clear module boundaries.
- When editing code, avoid breaking existing interfaces unless explicitly requested.
- Use type hints where they add clarity.

## Coding guidelines

- Language: Python 3.11+.
- Use `pandas` and `numpy` for data.
- Use one of: `lightgbm`, `xgboost`, or `catboost` as the main model family.
- Use `shap` for model explainability.

## Typical tasks

- Implement data loading utilities in `src/data/loader.py`.
- Implement feature engineering in `src/features/engineering.py`.
- Implement model training and prediction in `src/models/trainer.py` and `src/models/predictor.py`.
- Implement walk-forward backtests in `src/backtest/rolling.py`.
- Implement SHAP explainability helpers in `src/explain/shap_explain.py`.
- Implement a minimal CLI in `src/app/cli.py`.

When asked to add new functionality, first:
1. Read the relevant sections of `DESIGN.md`.
2. Update or create tests where appropriate.
3. Write code in the specified module.

Do not introduce complex deep-learning architectures unless explicitly requested. Tree-based models are the default.

## Risk Analysis Scripts

Key scripts for portfolio risk analysis:

| Script | Purpose |
|--------|---------|
| `scripts/strengthen_recommendations.py` | All-in-one risk analysis (`--full` for extended) |
| `scripts/comprehensive_risk_analysis.py` | Tail risk, VaR, CVaR, drawdown duration |
| `scripts/stress_testing.py` | Scenario-based stress tests (7 predefined) |
| `scripts/conscience_filter.py` | Ethical exclusion filters |

See `docs/risk-analysis-guide.md` for full documentation.

## Diagnostic Scripts

Key scripts for diagnosing data and analysis issues:

| Script | Purpose |
|--------|---------|
| `scripts/diagnose_backtest_data.py` | Diagnose backtest data issues (date ranges, window sizes) |
| `scripts/diagnose_value_quality_scores.py` | Diagnose fundamental data coverage and score differentiation |
| `scripts/analyze_filter_effectiveness.py` | Analyze filter effectiveness and optimization |

When backtest fails with "No predictions generated", use `diagnose_backtest_data.py` to identify the issue.
