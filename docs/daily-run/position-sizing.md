# Position Sizing

> [← Daily Run Index](README.md) | [← Documentation Index](../README.md)

Position sizing determines how much capital to allocate to each stock. The daily pipeline uses **confidence-based sizing** — stocks with higher prediction scores get larger positions, subject to concentration caps and exposure scaling.

**Source:** `src/risk/position_sizing.py`, `scripts/paper_trading.py`

---

## Confidence-Based Sizing (Default)

The primary method used by the daily pipeline:

```python
def confidence_based_sizing(predictions, calibration_factor, max_weight=0.25):
    # 1. Shift scores to ensure all positive
    shifted = predictions - predictions.min() + 0.01

    # 2. Normalize to sum to 1.0
    raw_weights = shifted / shifted.sum()

    # 3. Scale by calibration factor (adaptive exposure)
    scaled_weights = raw_weights * calibration_factor

    # 4. Re-normalize
    weights = scaled_weights / scaled_weights.sum()

    # 5. Apply concentration cap
    weights = weights.clip(upper=max_weight)
    weights = weights / weights.sum()

    return weights
```

### Example

| Stock | Prediction | Shifted | Raw Weight | After Calibration (1.2x) | After Cap (25%) |
|-------|-----------|---------|------------|--------------------------|-----------------|
| NVDA | 0.084 | 0.075 | 0.268 | 0.322 | **0.250** |
| AMD | 0.078 | 0.069 | 0.246 | 0.296 | **0.250** |
| META | 0.069 | 0.060 | 0.214 | 0.257 | **0.250** |
| MSFT | 0.065 | 0.056 | 0.200 | 0.240 | 0.168 |
| AAPL | 0.059 | 0.050 | 0.179 | 0.214 | 0.082 |

**Why confidence-based:** Equal-weight ignores the model's conviction. If NVDA scores much higher than AAPL, we should invest more in NVDA. The calibration factor adjusts total exposure based on historical accuracy (see [Accuracy Calibration](accuracy-calibration.md)).

---

## Concentration Cap

No single stock can exceed 25% of the portfolio:

```python
if weight > max_position_weight:
    weight = max_position_weight  # Clip to 25%
# Redistribute excess weight proportionally to remaining positions
weights = weights / weights.sum()
```

**Why 25%:** Limits single-stock risk. Even if the model is very confident in one stock, a single adverse event (earnings miss, lawsuit) can't destroy more than 25% of the portfolio.

---

## Alternative Sizing Methods

Available in `src/risk/position_sizing.py` but not used by default in the daily pipeline:

### Equal Weight

```
weight[i] = 1 / n_stocks
```

Simple and robust. Used as fallback when prediction scores are unavailable.

### Inverse Volatility (Risk Parity)

```
weight[i] = (1 / vol[i]) / sum(1 / vol[j] for all j)
```

Less volatile stocks get larger positions. Equalizes each stock's risk contribution.

**When to use:** When you want to minimize portfolio volatility regardless of return predictions.

### Kelly Criterion

```
f* = (p * b - q) / b

where:
  p = win probability (historical hit rate)
  b = win/loss ratio (avg winning trade / avg losing trade)
  q = 1 - p (loss probability)
  f* = optimal fraction of capital to bet
```

Theoretically optimal for maximizing long-term growth. In practice, full Kelly is too aggressive — the system caps at 25% of Kelly.

**When to use:** When you have high-confidence estimates of win rate and payoff ratio.

### ATR-Based

```
shares = (capital * risk_per_trade) / (ATR * multiplier)
position_value = shares * price
weight = position_value / total_capital
```

Sizes positions so that a 1-ATR adverse move equals a fixed dollar loss. More volatile stocks get smaller positions.

**When to use:** When you want to risk a fixed dollar amount per position regardless of stock volatility.

---

## VIX Exposure Scaling

Applied after position sizing, before trade execution:

```python
def apply_vix_scaling(weights, realized_vol):
    if realized_vol >= 40:       # Extreme volatility
        scale = 0.30             # Reduce to 30% exposure
    elif realized_vol >= 30:     # High volatility
        scale = 0.60             # Reduce to 60% exposure
    else:
        scale = 1.00             # Full exposure

    return weights * scale       # Remaining capital held as cash
```

**How VIX is estimated:** The system uses 21-day annualized realized volatility of SPY returns as a VIX proxy (doesn't require an actual VIX data feed).

```
realized_vol = std(spy_daily_returns[-21:]) * sqrt(252) * 100
```

**Why:** During market stress (VIX > 30), correlations increase and diversification breaks down. Reducing exposure preserves capital.

---

## See Also

- [Risk Controls](risk-controls.md) — drawdown limits, stop-loss
- [Accuracy Calibration](accuracy-calibration.md) — how calibration factor is computed
- [Signal Generation](signal-generation.md) — how prediction scores are generated
- [Risk Management](../risk-management.md) — extended risk metrics reference
- [Risk Parity](../risk-parity.md) — risk parity allocation details
