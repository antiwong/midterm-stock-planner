# Bayesian Optimization Report: Semiconductors

**Date**: 2026-03-16
**Watchlist**: semiconductors (22 tickers)
**Method**: Bayesian optimization (scikit-optimize, gp_minimize)
**Settings**: n_calls=40, n_initial=8, acq_func=EI, metric=sharpe, seed=42
**Data**: Hourly prices, 2023-03-15 to 2026-03-13
**Total Duration**: 1,952s (~32 min)

---

## Summary

- **22/22 tickers optimized** — all successful
- **Average Sharpe**: 0.517
- **Average Return**: 478.8%
- **Top performer**: TSM (Sharpe=2.01, 264% return, -29% drawdown)
- **Worst performer**: MCHP (Sharpe=0.12, 28% return, -53% drawdown)

---

## Results (sorted by Sharpe ratio)

| Rank | Ticker | Sharpe | Return | MaxDD | Trades | MACD (F/S/Sig) | RSI (Len/Hi/Lo) |
|------|--------|--------|--------|-------|--------|----------------|------------------|
| 1 | **TSM** | 2.012 | 263.8% | -29.1% | 32 | 20/36/5 | 7/80/34 |
| 2 | **ASML** | 1.368 | 156.0% | -22.7% | 29 | 19/29/18 | 12/60/40 |
| 3 | **AVGO** | 1.151 | 4629.8% | -43.0% | 79 | 15/60/20 | 14/80/34 |
| 4 | MRVL | 0.817 | 1181.0% | -50.1% | 159 | 8/56/7 | 7/63/27 |
| 5 | ON | 0.787 | 76.7% | -26.0% | 27 | 12/54/20 | 11/60/20 |
| 6 | MU | 0.737 | 1008.4% | -55.9% | 142 | 15/20/11 | 10/60/39 |
| 7 | QCOM | 0.557 | 282.5% | -38.1% | 115 | 18/37/6 | 8/80/22 |
| 8 | WDC | 0.482 | 782.0% | -59.4% | 44 | 20/20/17 | 21/80/38 |
| 9 | SMH | 0.385 | -14.3% | -57.8% | 57 | 20/20/15 | 17/80/40 |
| 10 | STX | 0.379 | 196.8% | -32.3% | 159 | 17/60/20 | 21/80/21 |
| 11 | TXN | 0.338 | 1064.6% | -38.3% | 714 | 20/60/6 | 7/80/40 |
| 12 | KLAC | 0.334 | 133.4% | -29.5% | 181 | 20/48/12 | 12/79/28 |
| 13 | TEL | 0.264 | 59.8% | -17.5% | 151 | 17/47/16 | 19/80/40 |
| 14 | TER | 0.263 | 118.6% | -46.1% | 305 | 5/39/13 | 21/62/37 |
| 15 | ARM | 0.245 | 150.6% | -46.6% | 277 | 17/53/8 | 21/80/20 |
| 16 | LRCX | 0.232 | 87.5% | -32.5% | 250 | 15/45/12 | 14/67/30 |
| 17 | SMCI | 0.208 | 148.3% | -66.1% | 339 | 20/60/5 | 19/75/21 |
| 18 | NXPI | 0.201 | 53.7% | -30.2% | 256 | 20/60/5 | 15/60/31 |
| 19 | AMAT | 0.187 | 68.8% | -38.4% | 229 | 14/60/16 | 21/68/40 |
| 20 | SWKS | 0.172 | 28.8% | -30.4% | 33 | 20/20/17 | 18/60/20 |
| 21 | ADI | 0.136 | 28.4% | -31.6% | 264 | 9/20/17 | 11/79/36 |
| 22 | MCHP | 0.120 | 28.1% | -52.6% | 195 | 15/56/20 | 17/80/21 |

---

## Analysis

### Tier Classification

**Tier 1 — Strong (Sharpe > 1.0)**:
- TSM (2.01): Dominant — slow MACD(20/36), fast RSI(7). Low trade count (32) = high conviction signals.
- ASML (1.37): Clean risk profile — lowest max drawdown (-22.7%) of any ticker. Moderate MACD(19/29).
- AVGO (1.15): Massive return (4630%) but higher drawdown (-43%). Slow MACD(15/60) for trend following.

**Tier 2 — Good (Sharpe 0.5–1.0)**:
- MRVL (0.82): Very fast MACD(8/56) captures semiconductor cycle swings. High drawdown (-50%).
- ON (0.79): Best risk-adjusted in Tier 2 — low drawdown (-26%), low trades (27).
- MU (0.74): Memory cycle play — high return (1008%) but volatile (-56% drawdown).
- QCOM (0.56): Moderate performer across all metrics.

**Tier 3 — Marginal (Sharpe 0.1–0.5)**:
- WDC through MCHP: Trigger backtest doesn't work well on these names. Consider ML-only signals.

### MACD Parameter Patterns

- **Trend-followers** (slow MACD slow period 50-60): TXN, SMCI, NXPI, AVGO, MU — semiconductor stocks with long cycles
- **Responsive** (fast MACD slow period 20-36): TSM, ASML, SWKS, ADI — react to shorter-term moves
- **Signal period**: Most use 5-20 signal period; no clear pattern

### RSI Parameter Patterns

- **Wide RSI bands** (80/20-40): TSM, QCOM, TXN, ARM, SMH — less frequent signals, higher conviction
- **Narrow RSI bands** (60-67/20-40): ON, ASML, SWKS, MRVL — more frequent rebalancing

### Risk Observations

- **Best risk-adjusted**: ASML (-22.7% MaxDD), TEL (-17.5% MaxDD), ON (-26.0% MaxDD)
- **Most volatile**: SMCI (-66.1%), WDC (-59.4%), MU (-55.9%), SMH (-57.8%)
- **Highest trade count**: TXN (714 trades) — likely overtrades on hourly data. Consider increasing RSI thresholds.

---

## Comparison with Tech Giants

| Metric | Semiconductors (22) | Tech Giants (13) |
|--------|-------------------|-----------------|
| Avg Sharpe | 0.517 | 1.235 |
| Best Sharpe | 2.012 (TSM) | 2.059 (META) |
| Avg Return | 478.8% | 1297.5% |
| Avg MaxDD | -38.6% | -31.4% |

Tech giants have higher average Sharpe, but semiconductors have deeper sector-specific coverage. TSM is comparable to META as a top performer.

---

## Files Generated

- Per-ticker configs: `config/tickers/{TICKER}.yaml` (22 files)
- Per-ticker params: `output/best_params_{TICKER}.json` (22 files)
- Batch summary: `output/batch_optimization_summary.json`
- This report: `output/reports/bayesian_optimization_semiconductors_20260316.md`
