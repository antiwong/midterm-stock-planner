# Pipeline Overview

> [← Daily Run Index](README.md) | [← Documentation Index](../README.md)

The daily paper trading pipeline runs after market close. It refreshes data, retrains the model, generates signals, sizes positions, and executes trades — all in a single `python scripts/paper_trading.py run` invocation.

---

## Execution Sequence

```
PaperTradingEngine.run_daily()
│
├─ 1. refresh_data()
│     └─ Download latest daily OHLCV from Alpaca Historical API (yfinance fallback)
│     └─ Append to data/prices_daily.csv
│
├─ 2. _check_risk_rules()
│     ├─ Drawdown-from-peak check (liquidate if >30% retracement after >5% profit)
│     ├─ Daily loss limit (-5% halts trading)
│     └─ Concentration cap (max 25% per position)
│
├─ 3. _load_data()
│     ├─ Filter by watchlist tickers
│     ├─ compute_all_features_extended()  →  24+ features
│     └─ make_training_dataset()  →  63-day forward excess return target
│
├─ 4. run_walk_forward_backtest()
│     ├─ Split data into rolling 3yr train / 6mo test windows (7-day step)
│     ├─ Train LightGBM per window (11 parallel processes)
│     ├─ Compute IC, Rank IC, Sharpe per window
│     └─ Extract latest window predictions → stock scores
│
├─ 5. _generate_signals()
│     ├─ ML scores: rank stocks by prediction (top 5 = BUY)
│     ├─ Trigger scores: per-ticker RSI/MACD Sharpe (optional)
│     └─ Ensemble: 70% ML + 30% trigger → final ranking
│
├─ 6. _size_positions()
│     ├─ Confidence-based weights (proportional to prediction scores)
│     ├─ Apply accuracy calibration factor (adaptive exposure)
│     ├─ Enforce concentration cap (max 25%)
│     └─ Apply VIX exposure scaling (reduce in high-vol regimes)
│
├─ 7. _execute_trades()
│     ├─ Alpaca: rebalance_portfolio() → market orders, fractional shares
│     └─ Local: simulate at close price, apply 0.1% transaction cost
│
└─ 8. _record_snapshot()
      ├─ Write to paper_trading.db (trades, positions, signals, daily_snapshots)
      └─ Update accuracy_log (evaluate 5-day-old signals vs actual returns)
```

---

## Timing & Automation

| Setting | Value |
|---------|-------|
| Recommended run time | 5:30 PM ET (after market close) |
| Execution duration | ~2-3 minutes (signal generation) |
| Cron setup | `python scripts/paper_trading.py setup-cron` |
| Log file | `logs/paper_trading.log` |

---

## Data Flow

```
data/prices_daily.csv   ──► Feature Engineering ──► Walk-Forward Backtest
                                                          │
config/config.yaml      ──► Model Params ────────────────►│
config/watchlists.yaml  ──► Ticker Universe ─────────────►│
config/tickers/*.yaml   ──► Per-Ticker RSI/MACD Params ──► Trigger Backtest
                                                          │
                                              ┌───────────┘
                                              ▼
                                    Ensemble Signal Generator
                                              │
                                              ▼
                              ┌── Alpaca API ──► Live Paper Orders
                              │
            Trade Execution ──┤
                              │
                              └── Local Sim ──► SQLite (paper_trading.db)
```

---

## See Also

- [Feature Engineering](feature-engineering.md) — what features the model uses
- [Walk-Forward Backtest](walk-forward-backtest.md) — how the model is trained and validated
- [Signal Generation](signal-generation.md) — how ML and trigger signals are combined
- [Risk Controls](risk-controls.md) — drawdown, stop-loss, VIX scaling
- [Alpaca Execution](alpaca-execution.md) — order placement and sync
