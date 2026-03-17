# Daily Run Pipeline — Technical Reference

> [← Back to Documentation Index](../README.md) | [Daily Run Guide](../daily-run.md) (quick start & commands)

This folder contains detailed technical documentation for the daily paper trading pipeline.

The system is managed by a **single orchestrator** (`scripts/daily_routine.py`) that runs 4 portfolios, data downloads, forward prediction journal, and Slack/Google Chat notifications. See [orchestrator.md](orchestrator.md) for the top-level reference.

---

## Pipeline Flow

```
  Data Refresh ──► Feature Engineering ──► Walk-Forward Backtest ──► Signal Generation
                                                                          │
  Accuracy Calibration ◄──── Record & Sync ◄──── Trade Execution ◄────────┘
       │                          │
       └──► adjusts next run      └──► paper_trading.db
```

| Phase | What Happens | Technique Doc |
|-------|-------------|---------------|
| 1. Data Refresh | Download latest daily OHLCV prices | [pipeline-overview.md](pipeline-overview.md) |
| 2. Feature Engineering | Compute 24+ features from price/volume data | [feature-engineering.md](feature-engineering.md) |
| 3. Walk-Forward Backtest | Train LightGBM on rolling windows, generate predictions | [walk-forward-backtest.md](walk-forward-backtest.md) |
| 4. Model Training | LightGBM gradient boosting with regularization | [lightgbm-model.md](lightgbm-model.md) |
| 5. Signal Generation | Rank stocks, combine ML + trigger signals | [signal-generation.md](signal-generation.md) |
| 6. Position Sizing | Confidence-weighted allocation with caps | [position-sizing.md](position-sizing.md) |
| 7. Risk Controls | Drawdown limits, stop-loss, VIX scaling | [risk-controls.md](risk-controls.md) |
| 8. Trade Execution | Alpaca paper trading or local simulation | [alpaca-execution.md](alpaca-execution.md) |
| 9. Accuracy Calibration | Track signal accuracy, adjust exposure | [accuracy-calibration.md](accuracy-calibration.md) |
| 10. Forward Testing | Log predictions, evaluate at 5d/63d horizons | [forward-testing.md](forward-testing.md) |
| 11. Orchestrator | Single entry point for daily/weekly/monthly routines | [orchestrator.md](orchestrator.md) |

---

## Technique Quick Reference

### ML & Statistical Methods

| Technique | Purpose | Details |
|-----------|---------|---------|
| LightGBM Regression | Predict excess returns | [lightgbm-model.md](lightgbm-model.md) |
| Walk-Forward Validation | Out-of-sample testing | [walk-forward-backtest.md](walk-forward-backtest.md) |
| Information Coefficient (IC) | Measure predictive power | [walk-forward-backtest.md#information-coefficient](walk-forward-backtest.md#information-coefficient-ic) |
| Rank IC (Spearman) | Robust ranking correlation | [walk-forward-backtest.md#rank-ic](walk-forward-backtest.md#rank-ic-spearman) |
| TreeSHAP | Feature contribution analysis | [lightgbm-model.md#shap-explanations](lightgbm-model.md#shap-explanations) |
| IC Regime Detection | Detect model degradation | [walk-forward-backtest.md#ic-regime-detection](walk-forward-backtest.md#ic-regime-detection) |

### Technical Indicators

| Indicator | What It Measures | Details |
|-----------|-----------------|---------|
| MACD | Trend momentum (EMA crossover) | [feature-engineering.md#macd](feature-engineering.md#macd-moving-average-convergence-divergence) |
| Bollinger Bands | Volatility envelope, mean reversion | [feature-engineering.md#bollinger-bands](feature-engineering.md#bollinger-bands) |
| ATR | True range volatility | [feature-engineering.md#atr](feature-engineering.md#atr-average-true-range) |
| ADX | Trend strength (0-100) | [feature-engineering.md#adx](feature-engineering.md#adx-average-directional-index) |
| RSI | Overbought/oversold oscillator | [feature-engineering.md#rsi](feature-engineering.md#rsi-relative-strength-index) |
| OBV | Volume-price confirmation | [feature-engineering.md#obv](feature-engineering.md#obv-on-balance-volume) |

### Risk Management

| Technique | What It Does | Details |
|-----------|-------------|---------|
| Confidence-Based Sizing | Weight positions by prediction score | [position-sizing.md](position-sizing.md) |
| VIX Exposure Scaling | Reduce exposure in high volatility | [risk-controls.md#vix-scaling](risk-controls.md#vix-based-exposure-scaling) |
| Drawdown-from-Peak Close | Liquidate on large retracement | [risk-controls.md#drawdown](risk-controls.md#drawdown-from-peak-liquidation) |
| Stop-Loss | Exit individual positions at -15% | [risk-controls.md#stop-loss](risk-controls.md#per-position-stop-loss) |
| Concentration Cap | Max 25% per stock | [position-sizing.md#concentration-cap](position-sizing.md#concentration-cap) |
| Accuracy Calibration | Adaptive exposure from hit rate | [accuracy-calibration.md](accuracy-calibration.md) |

---

## Key Source Files

| File | Purpose |
|------|---------|
| `scripts/daily_routine.py` | Consolidated daily/weekly/monthly orchestrator |
| `scripts/forward_journal.py` | Forward prediction journal DB |
| `scripts/paper_trading.py` | Per-portfolio trading engine |
| `src/backtest/rolling.py` | Walk-forward backtest engine |
| `src/models/trainer.py` | LightGBM training |
| `src/models/predictor.py` | Prediction & ranking |
| `src/features/engineering.py` | Feature computation |
| `src/indicators/technical.py` | Technical indicator formulas |
| `src/risk/position_sizing.py` | Position sizing methods |
| `src/risk/risk_parity.py` | Risk parity allocation |
| `src/risk/metrics.py` | Sharpe, Sortino, VaR, drawdown |
| `src/regression/metrics.py` | IC, regime detection, significance tests |
| `src/trading/alpaca_broker.py` | Alpaca order execution |
