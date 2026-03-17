# Forward Testing & Prediction Journal

> [<- Daily Run Index](README.md) | [<- Documentation Index](../README.md)

The forward prediction journal logs model predictions *before* outcomes are known and evaluates them once matured. This is the definitive test of whether the model generalizes to truly unseen data.

**Source:** `scripts/forward_journal.py`
**Database:** `data/forward_journal.db`
**Dashboard:** Forward Testing page

---

## Why Forward Testing

Walk-forward backtesting uses historical data — it shows "would have worked." Forward testing records predictions on live data and waits for the future to arrive. The difference:

| Aspect | Backtesting | Forward Testing |
|--------|------------|-----------------|
| Data | Historical (known outcomes) | Live (unknown outcomes) |
| Bias | Possible look-ahead, survivorship | None — predictions locked before outcomes |
| Feedback speed | Instant | Days to months |
| Confidence | Necessary but not sufficient | Closest to real-world proof |

---

## Two Horizons

| Horizon | Maturity | Purpose |
|---------|----------|---------|
| **5-day** | ~1 week | Fast feedback for accuracy calibration |
| **63-day** | ~3 months | Matches the model's actual prediction target |

Both horizons are logged for every signal from every portfolio, every trading day.

---

## Database Schema

```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_date TEXT NOT NULL,      -- when the prediction was made
    maturity_date TEXT NOT NULL,        -- prediction_date + horizon business days
    ticker TEXT NOT NULL,
    watchlist TEXT NOT NULL,            -- e.g., 'tech_giants', 'moby_picks'
    horizon_days INTEGER NOT NULL,     -- 5 or 63
    predicted_score REAL NOT NULL,     -- ensemble score at prediction time
    predicted_rank INTEGER NOT NULL,   -- rank within watchlist
    predicted_action TEXT NOT NULL,    -- 'BUY' or 'SELL'
    entry_price REAL NOT NULL,        -- close price on prediction_date
    model_version TEXT DEFAULT '',
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    -- Evaluation fields (NULL until matured)
    actual_price REAL,
    actual_return REAL,
    hit INTEGER,                      -- 1 if correct direction, 0 if wrong
    evaluated_at TEXT,
    UNIQUE(prediction_date, ticker, horizon_days, watchlist)
);
```

### Immutability

- The UNIQUE constraint on `(prediction_date, ticker, horizon_days, watchlist)` prevents rewriting predictions
- INSERT OR IGNORE ensures re-running the daily routine on the same day is idempotent
- Evaluation fields start as NULL and are updated once via `record_evaluation()`

### Hit Definition

- **BUY + positive return** = HIT (1)
- **BUY + negative return** = MISS (0)
- **SELL + negative return** = HIT (1)
- **SELL + positive return** = MISS (0)

---

## Prediction Lifecycle

```
Day 0: Daily routine runs
  └─> Signals generated for all 4 portfolios
  └─> Predictions logged to forward_journal.db (INSERT OR IGNORE)
       • 5-day prediction: maturity = Day 0 + 5 business days
       • 63-day prediction: maturity = Day 0 + 63 business days

Day 5: Daily routine runs
  └─> Evaluates Day 0's 5-day predictions
       • Fetches current close price
       • Computes actual_return = (current - entry) / entry
       • Sets hit = 1 if direction matches, 0 otherwise

Day 63: Daily routine runs (or monthly routine)
  └─> Evaluates Day 0's 63-day predictions
       • Same evaluation logic
```

---

## Maturity Date Calculation

Uses pandas business days (Mon-Fri):

```python
maturity = prediction_date + BDay(horizon_days)
```

This means:
- A 5-day prediction on Monday matures the following Monday
- A 63-day prediction on Monday matures ~3 calendar months later
- US holidays are NOT excluded (simplified — BDay only skips weekends)

---

## Hit Rate Interpretation

| Hit Rate | Meaning |
|----------|---------|
| > 60% | Model has predictive edge |
| 50-60% | Marginal — may not cover transaction costs |
| < 50% | Model is worse than random — investigate |

The 5-day hit rate feeds into the accuracy calibration system (see [Accuracy Calibration](accuracy-calibration.md)), which adjusts portfolio exposure.

The 63-day hit rate is the true test of the model's prediction horizon.

---

## Dashboard

The **Forward Testing** dashboard page shows:

1. **Hit Rates** — bar chart by portfolio and horizon
2. **Accuracy Trend** — cumulative hit rate over time (line chart)
3. **Active Predictions** — predictions not yet matured
4. **Full History** — searchable table with filters

---

## API (ForwardJournalDB)

```python
from scripts.forward_journal import ForwardJournalDB

journal = ForwardJournalDB()

# Log a prediction
journal.log_prediction(
    prediction_date="2026-03-17",
    ticker="NVDA",
    watchlist="tech_giants",
    horizon_days=5,
    predicted_score=0.084,
    predicted_rank=1,
    predicted_action="BUY",
    entry_price=892.40,
)

# Batch log
journal.log_predictions_batch([...])

# Get predictions ready for evaluation
matured = journal.get_matured_predictions(horizon_days=5, as_of_date="2026-03-24")

# Record evaluation
journal.record_evaluation(pred_id, actual_price=910.20, actual_return=0.020, hit=1)

# Get hit rates
rates = journal.get_hit_rates(watchlist="tech_giants", horizon_days=5, last_n_days=30)
# {'total': 25, 'hits': 16, 'hit_rate': 0.64, 'avg_return': 0.012}

# Summary stats
stats = journal.get_summary_stats()
```

---

## See Also

- [Orchestrator](orchestrator.md) — how the daily routine invokes the journal
- [Accuracy Calibration](accuracy-calibration.md) — how hit rates adjust exposure
- [Walk-Forward Backtest](walk-forward-backtest.md) — the offline equivalent
