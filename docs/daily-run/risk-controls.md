# Risk Controls

> [← Daily Run Index](README.md) | [← Documentation Index](../README.md)

The daily pipeline enforces multiple layers of risk management before, during, and after trade execution. These rules protect against catastrophic losses and adapt exposure to market conditions.

**Source:** `RiskManager` in `scripts/paper_trading.py`, `src/risk/metrics.py`

---

## Risk Control Summary

```
                    ┌─────────────────────────────┐
                    │    RISK CONTROL LAYERS       │
                    ├─────────────────────────────┤
  Portfolio-level → │  Drawdown-from-peak close    │ ← Liquidate all if 30% retracement
                    │  Daily loss limit (-5%)       │ ← Halt trading for the day
                    │  VIX exposure scaling         │ ← Reduce exposure in high-vol regimes
                    ├─────────────────────────────┤
  Position-level → │  Concentration cap (25%)      │ ← No single stock > 25%
                    │  Stop-loss (-15%)             │ ← Exit if stock drops 15% from entry
                    ├─────────────────────────────┤
  Adaptive       → │  Accuracy calibration         │ ← Scale exposure by signal accuracy
                    └─────────────────────────────┘
```

---

## Drawdown-from-Peak Liquidation

Protects against large drawdowns by closing all positions when the portfolio retraces significantly from its peak.

```python
def check_drawdown(current_value, peak_value, initial_value):
    profit_pct = (peak_value - initial_value) / initial_value
    drawdown_pct = (current_value - peak_value) / peak_value

    if profit_pct > 0.05 and drawdown_pct < -0.30:
        # Liquidate all positions
        return "LIQUIDATE_ALL"
```

| Parameter | Value | Description |
|-----------|-------|-------------|
| Min profit threshold | 5% | Only enforce after portfolio has profited ≥5% |
| Max drawdown | 30% | Liquidate if portfolio drops 30% from peak |

**Why the profit threshold:** Without it, a new portfolio that dips 2% would immediately trigger liquidation (from $100K peak, a drop to $97K is a 3% drawdown from peak). The 5% profit requirement ensures the rule only activates after meaningful gains.

**Example:**
- Portfolio grows to $115K (peak, +15% profit) → profit threshold met
- Portfolio drops to $80.5K → drawdown = (80.5 - 115) / 115 = -30% → **LIQUIDATE ALL**

---

## Daily Loss Limit

Prevents cascading losses on a single day.

```python
def check_daily_loss(today_return):
    if today_return < -0.05:     # -5% daily return
        return "HALT_TRADING"    # No new trades today
```

| Parameter | Value |
|-----------|-------|
| Daily loss threshold | -5% |

**What happens:** Trading is halted for the rest of the day. Existing positions are NOT liquidated (the drawdown rule handles that). This prevents the model from placing new trades during a crash when signals are unreliable.

---

## Per-Position Stop-Loss

Exits individual positions that drop below a threshold from their entry price.

```python
def check_stop_loss(current_price, entry_price, stop_loss_pct=-0.15):
    pnl_pct = (current_price - entry_price) / entry_price
    if pnl_pct <= stop_loss_pct:
        return "SELL"     # Close this position
```

| Parameter | Value |
|-----------|-------|
| Stop-loss threshold | -15% from entry |

**In walk-forward backtest:** The stop-loss is applied during return calculation — stopped-out stocks are excluded from portfolio returns until the next rebalance.

**In live trading:** The position is sold at market price. The freed capital is redistributed at the next rebalance.

---

## VIX-Based Exposure Scaling

Dynamically reduces total portfolio exposure during high-volatility market regimes.

```python
def compute_exposure_scale(spy_returns_21d):
    # Approximate VIX using realized volatility
    realized_vol = spy_returns_21d.std() * sqrt(252) * 100

    if realized_vol >= 40.0:      # Extreme stress
        return 0.30               # Hold only 30% of normal position sizes
    elif realized_vol >= 30.0:    # High stress
        return 0.60               # Hold only 60% of normal position sizes
    else:
        return 1.00               # Full exposure
```

| VIX Proxy Level | Exposure Scale | Cash Held |
|-----------------|---------------|-----------|
| < 30 | 100% | 0% |
| 30-40 | 60% | 40% |
| > 40 | 30% | 70% |

**Why realized vol instead of actual VIX:** Using realized volatility avoids requiring a separate VIX data feed. The 21-day annualized SPY volatility approximates VIX closely for this purpose.

**Impact:** During the COVID crash (VIX > 80), this would have reduced exposure to 30%, preserving 70% of capital in cash. The model's predictions are less reliable during extreme market stress because historical patterns break down.

---

## Risk Events Logging

All risk rule triggers are logged to the `risk_events` table in `paper_trading.db`:

| Column | Description |
|--------|-------------|
| `date` | When the event occurred |
| `event_type` | `drawdown_close`, `daily_loss_halt`, `stop_loss`, `concentration_cap` |
| `details` | JSON with threshold values and trigger details |
| `action_taken` | What the system did (liquidate, halt, sell, redistribute) |

This provides an audit trail for understanding why positions were closed or trading was paused.

---

## Risk Metrics (Reference)

The system can compute these metrics on demand for portfolio analysis:

| Metric | Formula | Source |
|--------|---------|--------|
| **Sharpe Ratio** | `(ann_return - rf_rate) / ann_vol` | `src/risk/metrics.py` |
| **Sortino Ratio** | `ann_return / downside_vol` (only negative returns) | `src/risk/metrics.py` |
| **Calmar Ratio** | `ann_return / abs(max_drawdown)` | `src/risk/metrics.py` |
| **Value at Risk (95%)** | `percentile(returns, 5)` — worst expected daily loss | `src/risk/metrics.py` |
| **CVaR (Expected Shortfall)** | `mean(returns where returns ≤ VaR)` — avg loss in worst 5% | `src/risk/metrics.py` |
| **Max Drawdown** | `min(cumulative / cummax - 1)` | `src/risk/metrics.py` |
| **Beta** | `cov(portfolio, market) / var(market)` | `src/risk/metrics.py` |
| **Information Ratio** | `ann_excess_return / tracking_error` | `src/risk/metrics.py` |

---

## See Also

- [Position Sizing](position-sizing.md) — concentration cap and VIX scaling in sizing context
- [Accuracy Calibration](accuracy-calibration.md) — adaptive exposure scaling
- [Walk-Forward Backtest](walk-forward-backtest.md) — overfitting detection
- [Risk Management](../risk-management.md) — full risk management reference
- [Risk Analysis Guide](../risk-analysis-guide.md) — VaR, stress testing, tail risk
