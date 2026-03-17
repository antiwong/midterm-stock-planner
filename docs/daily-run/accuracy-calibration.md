# Accuracy Calibration

> [← Daily Run Index](README.md) | [← Documentation Index](../README.md)

The accuracy calibration system tracks how well the model's BUY signals actually perform, and adjusts portfolio exposure accordingly. It's a feedback loop that makes the pipeline self-correcting.

**Source:** `PaperTradingEngine` in `scripts/paper_trading.py`

---

## How It Works

```
Day 1: Generate signals → BUY NVDA, AMD, META, MSFT, AAPL

Day 6: Evaluate Day 1's signals:
  NVDA: predicted BUY → actual 5-day return +2.3% → HIT ✓
  AMD:  predicted BUY → actual 5-day return -0.8% → MISS ✗
  META: predicted BUY → actual 5-day return +1.1% → HIT ✓
  MSFT: predicted BUY → actual 5-day return +0.4% → HIT ✓
  AAPL: predicted BUY → actual 5-day return +0.2% → HIT ✓

Hit rate: 4/5 = 80%
Historical hit rate (all signals): 62%
Calibration factor: 62% / 50% = 1.24
```

---

## Calibration Factor Formula

```
calibration_factor = historical_hit_rate / 0.50
```

| Component | Description |
|-----------|-------------|
| `historical_hit_rate` | Fraction of BUY signals with positive 5-day return (rolling all-time) |
| `0.50` | Baseline — a random model would be right 50% of the time |
| `calibration_factor` | Multiplier applied to total portfolio exposure |

### Bounds

```
calibration_factor = clamp(factor, min=0.5, max=1.5)
```

| Hit Rate | Factor | Meaning |
|----------|--------|---------|
| 75% | 1.50 (capped) | Model is excellent — max exposure |
| 60% | 1.20 | Model is above average — increase exposure 20% |
| 50% | 1.00 | Model is random — no adjustment |
| 40% | 0.80 | Model is underperforming — reduce exposure 20% |
| 25% | 0.50 (floored) | Model is poor — minimum exposure |

### Minimum Sample Requirement

The calibration factor only activates after **30+ evaluated signals**. Before that, it returns 1.0 (no adjustment). This prevents early noise from causing wild swings.

---

## Evaluation Process

Each day, the system evaluates BUY signals from ~5 trading days ago:

```python
def evaluate_accuracy(signals_db, current_date):
    # 1. Get signals from 5 trading days ago
    eval_date = current_date - 5_trading_days
    past_signals = signals_db.query(date=eval_date, action='BUY')

    # 2. Get actual returns
    for signal in past_signals:
        actual_return = (price_today[signal.ticker] / price_eval_date[signal.ticker]) - 1
        hit = 1 if actual_return > 0 else 0

        # 3. Log to accuracy_log table
        accuracy_db.insert(
            signal_date=eval_date,
            eval_date=current_date,
            ticker=signal.ticker,
            predicted_rank=signal.rank,
            predicted_score=signal.score,
            actual_return=actual_return,
            hit=hit
        )

    # 4. Compute rolling hit rate
    all_hits = accuracy_db.query_all()
    hit_rate = sum(h.hit for h in all_hits) / len(all_hits)

    return hit_rate / 0.5  # calibration factor
```

---

## How Calibration Affects Position Sizing

The calibration factor scales all position weights:

```python
# In confidence-based sizing:
raw_weights = score_proportional_weights(predictions)
scaled_weights = raw_weights * calibration_factor
final_weights = scaled_weights / scaled_weights.sum()
```

**When factor > 1.0:** Model is accurate → increase total exposure → larger positions
**When factor < 1.0:** Model is struggling → decrease total exposure → smaller positions, more cash

This works alongside VIX exposure scaling. The two multipliers stack:
```
effective_exposure = calibration_factor * vix_scale
```

---

## Database Schema

The `accuracy_log` table in `paper_trading.db`:

| Column | Type | Description |
|--------|------|-------------|
| `signal_date` | DATE | When the signal was generated |
| `eval_date` | DATE | When accuracy was evaluated (signal_date + 5 days) |
| `ticker` | TEXT | Stock symbol |
| `predicted_rank` | INT | Model's rank for this stock |
| `predicted_score` | FLOAT | Model's prediction score |
| `actual_return` | FLOAT | Actual 5-day return |
| `hit` | INT | 1 if actual_return > 0, else 0 |

---

## Relationship to Regression Testing

| Aspect | Accuracy Calibration | Regression Testing |
|--------|---------------------|-------------------|
| **Scope** | Live, ongoing | Offline, periodic |
| **Frequency** | Every trading day | Quarterly or on-demand |
| **Duration** | Milliseconds | 40-120 minutes |
| **What it tests** | Signal accuracy (hit rate) | Feature selection (Sharpe, IC) |
| **Action** | Adjusts exposure automatically | Informs feature set changes |
| **Lookback** | All-time rolling | Full walk-forward (10 years) |

Calibration is the **live equivalent** of regression testing — it detects degradation in real-time and responds automatically, while regression tests require manual analysis and code changes.

---

## See Also

- [Position Sizing](position-sizing.md) — how calibration factor scales weights
- [Risk Controls](risk-controls.md) — other risk management layers
- [Signal Generation](signal-generation.md) — how signals are produced
- [Walk-Forward Backtest](walk-forward-backtest.md) — IC regime detection (offline equivalent)
