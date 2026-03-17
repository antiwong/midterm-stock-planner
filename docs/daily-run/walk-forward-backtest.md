# Walk-Forward Backtest

> [← Daily Run Index](README.md) | [← Documentation Index](../README.md)

The walk-forward backtest is the core validation and signal generation engine. It trains a fresh LightGBM model on each rolling window of historical data, tests it on out-of-sample data, and extracts the latest predictions for trading.

**Source:** `run_walk_forward_backtest()` in `src/backtest/rolling.py`

---

## How It Works

```
Data timeline:  ══════════════════════════════════════════════════════►

Window 1:  [═══ Train (3yr) ═══][─── Test (6mo) ───]
Window 2:       [═══ Train (3yr) ═══][─── Test (6mo) ───]         ← step 7 days
Window 3:            [═══ Train (3yr) ═══][─── Test (6mo) ───]
  ...                     ...
Window N:                                    [═══ Train (3yr) ═══][─── Test (6mo) ───]
                                                                          ↑
                                                                   Latest predictions
                                                                   used for trading
```

1. Slide a window across the data in 7-day steps
2. For each window: train LightGBM on 3 years, predict on 6 months
3. Compute IC, Sharpe, feature importance per window
4. The **last window's test predictions** become today's trading signals

---

## Window Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `train_years` | 3.0 | Training window length |
| `test_years` | 0.5 | Test window length (6 months) |
| `step_value` | 7 | Days between window starts |
| `step_unit` | days | Step unit |
| `rebalance_freq` | 4h | Portfolio rebalance frequency within test window |
| `min_train_samples` | 1000 | Skip window if fewer training samples |
| `min_test_samples` | 100 | Skip window if fewer test samples |

With 10 years of daily data and 7-day steps, this produces ~265-336 overlapping windows.

**Source:** `config/config.yaml` → `backtest` section

---

## Per-Window Processing

Each window runs through `_mp_process_window()`:

```python
# 1. Split data
train_data = data[train_start : test_start]
test_data  = data[test_start : test_end]

# 2. Train model
model = train_lgbm_regressor(
    X_train = train_data[feature_columns],
    y_train = train_data['target'],      # 63-day excess return
    params  = {n_estimators=200, lr=0.03, max_depth=6, ...}
)

# 3. Generate predictions
train_preds = model.predict(X_train)
test_preds  = model.predict(X_test)

# 4. Compute IC
ic, rank_ic = spearman_corr(test_preds, test_actuals)

# 5. Construct portfolio (on test window)
portfolio = _construct_portfolio(test_preds, top_n=5, max_weight=0.25)

# 6. Calculate returns
portfolio_returns, benchmark_returns = _calculate_portfolio_returns(portfolio, price_data)

# 7. Calculate Sharpe, max drawdown, turnover
metrics = _calculate_metrics(portfolio_returns, benchmark_returns)
```

---

## Information Coefficient (IC)

IC measures how well model predictions correlate with actual future returns.

### Pearson IC

```
IC = corr(predictions, actual_excess_returns)
```

Standard linear correlation. Sensitive to outliers.

### Rank IC (Spearman)

```
Rank_IC = corr(rank(predictions), rank(actual_excess_returns))
```

More robust — only cares about ranking order, not magnitude. **This is the primary optimization metric** (`objective_metric: mean_rank_ic`).

### Interpretation

| Rank IC | Signal Quality |
|---------|---------------|
| > 0.10 | Strong (rare, excellent) |
| 0.05 - 0.10 | Useful (good for production) |
| 0.02 - 0.05 | Weak but potentially profitable with low costs |
| < 0.02 | Too weak to trade |
| < 0 | Model predicts wrong direction |

**Source:** `_compute_ic()` in `src/backtest/rolling.py`

---

## IC Regime Detection

Detects when model predictive power is degrading over time.

```
recent_IC    = mean(IC[-lookback_windows:])      # Recent window ICs
historical_IC = mean(all_IC)                      # All-time average
historical_std = std(all_IC)

z_score = (recent_IC - historical_IC) / (historical_std / sqrt(lookback_windows))
```

| Z-Score | Status | Action |
|---------|--------|--------|
| > -1.5 | Stable | Normal operation |
| -2.0 to -1.5 | Warning | Monitor closely |
| < -2.0 | Degraded | Consider pausing, re-running regression test |

**Source:** `detect_ic_regime_shift()` in `src/regression/metrics.py`

---

## Portfolio Construction per Window

Within each test window, the backtest constructs a portfolio at each rebalance point:

```python
def _construct_portfolio(predictions, top_n=5, max_weight=0.25, exposure_scale=1.0):
    # 1. Find prediction for rebalance date
    date_preds = predictions[rebalance_date]

    # 2. Rank and select
    ranked = date_preds.sort_values(ascending=False)
    selected = ranked.head(top_n)

    # 3. Score-weighted allocation
    shifted = selected - selected.min() + 1e-8
    weights = shifted / shifted.sum()

    # 4. Apply concentration cap
    weights = weights.clip(upper=max_weight)
    weights = weights / weights.sum()

    # 5. Apply VIX exposure scaling
    weights = weights * exposure_scale   # Remaining = cash
```

**Rebalancing:** Every 4 hours within the test window (configurable). The system generates rebalance dates and constructs a fresh portfolio at each one.

---

## Return Calculation

```python
def _calculate_portfolio_returns(portfolios, price_data, benchmark_data):
    for each trading_day:
        # Get active weights from most recent rebalance
        weights = latest_rebalance_weights

        # Compute weighted return
        stock_returns = daily_price_returns[trading_day]
        port_return = sum(weight[i] * stock_return[i])

        # Normalize by total weight (handles overlapping windows)
        port_return /= total_weight

        # Get benchmark return
        bench_return = spy_daily_return[trading_day]

    return portfolio_returns, benchmark_returns
```

**Stop-loss handling:** If a stock drops below -15% from its entry price, it's excluded from subsequent return calculations until the next rebalance.

---

## Metrics Aggregation

Computed across all windows:

| Metric | Formula |
|--------|---------|
| **Total Return** | `prod(1 + daily_returns) - 1` |
| **Annualized Return** | `(1 + total_return) ^ (252 / n_days) - 1` |
| **Volatility** | `std(daily_returns) * sqrt(252)` |
| **Sharpe Ratio** | `annualized_return / volatility` (risk-free = 0%) |
| **Max Drawdown** | `min(cumulative / cummax - 1)` |
| **Hit Rate** | `mean(excess_return > 0)` |
| **Turnover** | `mean(sum(abs(weight_changes)))` per rebalance |

---

## Overfitting Detection

The system monitors the ratio of train-period Sharpe to test-period Sharpe:

```
train_sharpe = sharpe(portfolio_returns on training data)
test_sharpe  = sharpe(portfolio_returns on test data)
ratio        = train_sharpe / test_sharpe
```

| Ratio | Assessment |
|-------|-----------|
| < 2.5 | Acceptable |
| 2.5 - 5.0 | Suspicious — consider more regularization |
| > 5.0 | Severe overfitting — model memorizes training data |

**Guard metric:** `train_test_sharpe_ratio` uses **median** across windows (more robust than max to outlier windows).

**Source:** Overfitting checks in `src/backtest/rolling.py`, guard thresholds in `src/regression/metrics.py`

---

## Parallelization

Windows are processed in parallel using Python `multiprocessing`:

```python
with Pool(processes=n_workers) as pool:    # Default: 11 workers
    results = pool.map(_mp_process_window, window_args)
```

Data is shared via module-level `_MP_SHARED` dict (avoids serialization overhead for large DataFrames). Uses `fork` context on macOS/Linux.

---

## See Also

- [LightGBM Model](lightgbm-model.md) — model trained per window
- [Feature Engineering](feature-engineering.md) — features used for training
- [Signal Generation](signal-generation.md) — how final predictions become signals
- [Risk Controls](risk-controls.md) — VIX scaling applied during backtest
- [Regression Testing Guide](../regression-testing-guide.md) — validating feature selection
- [Backtesting](../backtesting.md) — extended backtesting reference
