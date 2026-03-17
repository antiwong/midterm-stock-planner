# Signal Generation

> [← Daily Run Index](README.md) | [← Documentation Index](../README.md)

The pipeline produces trading signals by combining two independent signal sources: an ML-based cross-sectional ranking model and a rule-based trigger system. An ensemble module blends them into final BUY/SELL decisions.

**Source:** `EnsembleSignalGenerator` in `scripts/paper_trading.py`

---

## Two Signal Sources

| Source | Method | Strengths | Weaknesses |
|--------|--------|-----------|------------|
| **ML Walk-Forward** | LightGBM trained on rolling windows | Adapts to changing markets, captures non-linear patterns | Requires sufficient data, can overfit |
| **Trigger Backtest** | Per-ticker optimized RSI/MACD rules | Transparent logic, per-ticker tuned | Rigid rules, no multi-factor interaction |

---

## ML Signal Generation

The walk-forward backtest produces a prediction score for each stock on the latest date:

```
Walk-Forward Backtest
    └─► Final window predictions
          └─► scores = {NVDA: 0.084, AMD: 0.078, META: 0.069, ...}
                └─► Rank: NVDA=1, AMD=2, META=3, ...
                      └─► Top 5 → BUY, Rest → SELL/HOLD
```

**Scoring:** Continuous value representing predicted 63-day excess return vs SPY. Higher = more likely to outperform.

**Ranking:** Cross-sectional rank within the universe on each date. Rank 1 = highest predicted outperformance.

---

## Trigger Signal Generation

Per-ticker rules based on Bayesian-optimized RSI and MACD parameters:

### RSI Signals

```
BUY  when RSI crosses above oversold threshold from below
SELL when RSI crosses below overbought threshold from above
```

### MACD Signals

```
BUY  when MACD line crosses above signal line (histogram goes positive)
SELL when MACD line crosses below signal line (histogram goes negative)
```

### Per-Ticker Optimization

Each ticker has independently optimized parameters stored in `config/tickers/*.yaml`:

| Ticker | MACD (fast/slow/signal) | RSI (period/OB/OS) | Sharpe |
|--------|------------------------|---------------------|--------|
| NVDA | 15/20/7 | 14/80/40 | 1.126 |
| META | 9/37/12 | 17/65/26 | 2.059 |
| AMZN | 17/60/17 | 7/71/31 | 1.573 |
| SLV | 5/51/5 | 14/80/39 | 2.470 |
| AMD | 18/37/5 | 15/70/20 | 1.780 |

Optimization via `scripts/optimize_all_tickers.py` using Bayesian optimization (scikit-optimize).

### Macro Filters (Optional)

Trigger signals can be filtered by macro conditions:

| Filter | BUY When | SELL When |
|--------|----------|-----------|
| VIX | VIX ≤ 25 | VIX ≥ 30 |
| DXY (Dollar Index) | DXY ≤ 102 | DXY ≥ 106 |
| GSR (Gold/Silver Ratio) | GSR ≥ 90 (silver cheap) | GSR ≤ 70 |
| Volume Surge | volume / avg_20d ≥ 2.0 | — |
| OBV Slope | obv_slope_20d > 0 | — |

**Source:** `generate_signals()` in `src/backtest/trigger_backtest.py`

---

## Ensemble Blending

The two signal sources are combined using a weighted average:

```python
def generate_ensemble_signals(ml_scores, trigger_scores, ml_weight=0.7):
    # 1. Normalize both to [0, 1]
    ml_norm = (ml_scores - min) / (max - min)
    trig_norm = (trigger_scores - min) / (max - min)

    # 2. Weighted combination
    ensemble = ml_weight * ml_norm + (1 - ml_weight) * trig_norm    # 70% ML + 30% trigger

    # 3. Re-rank by ensemble score
    ranks = ensemble.rank(ascending=False)

    # 4. Assign actions
    for stock in universe:
        if rank <= top_n:
            action = "BUY"
        else:
            action = "SELL"

    return ensemble_scores, ranks, actions
```

**Default weights:** 70% ML, 30% trigger. The ML model gets higher weight because it captures multi-factor interactions and adapts to regime changes.

---

## Signal Output

Each run produces a signal table stored in `paper_trading.db`:

| Column | Description |
|--------|-------------|
| `date` | Signal generation date |
| `ticker` | Stock symbol |
| `ml_score` | Raw ML prediction score |
| `trigger_score` | Trigger backtest Sharpe |
| `ensemble_score` | Blended score |
| `rank` | Final cross-sectional rank |
| `percentile` | Percentile rank (100 = best) |
| `action` | BUY or SELL |

Example output:

```
Date        Ticker  ML_Score  Trig_Score  Ensemble  Rank  Action
2026-03-15  NVDA    0.0842    1.126       0.927     1     BUY
2026-03-15  AMD     0.0783    1.780       0.889     2     BUY
2026-03-15  META    0.0691    2.059       0.867     3     BUY
2026-03-15  MSFT    0.0650    1.004       0.751     4     BUY
2026-03-15  AAPL    0.0589    0.822       0.694     5     BUY
2026-03-15  CRM     0.0312    0.722       0.421     6     SELL
2026-03-15  INTC    0.0198    0.868       0.345     7     SELL
...
```

---

## See Also

- [Walk-Forward Backtest](walk-forward-backtest.md) — how ML scores are generated
- [LightGBM Model](lightgbm-model.md) — ML model details
- [Feature Engineering](feature-engineering.md) — input features for both signal sources
- [Position Sizing](position-sizing.md) — how signals become portfolio weights
- [Purchase Triggers](../purchase-triggers.md) — trigger logic reference
