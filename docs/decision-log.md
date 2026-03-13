# Decision Log — QuantaAlpha Midterm Stock Planner

## Decision 001: Feature Selection Strategy

**Date**: 2026-03-14
**Status**: ACCEPTED
**Decision**: Use **baseline (returns, volatility, volume) + MACD only** for the prediction model.

### Evidence (Regression Testing Results)

Two full regression tests completed (total 800+ minutes of computation):

**Test 1: SLV+AMD (2 tickers, 11 steps, 378 min)**
**Test 2: Tech Giants (9 tickers, 12 steps, 412 min)**

Both produced identical results:

| Rank | Feature | Peak Rank IC | Marginal IC | Verdict |
|------|---------|-------------|-------------|---------|
| 1 | **MACD** | **0.3526** | **+0.0136** | **KEEP — only feature that improves signal** |
| 2 | ATR | 0.2127 | +0.0282 | Partial recovery after bollinger damage |
| 3 | Gap | 0.1607 | +0.0021 | Negligible positive |
| - | Baseline (returns/vol/volume) | 0.3405 | - | Strong starting signal |
| - | Valuation | 0.3405 | 0.0000 | No impact |
| - | RSI | 0.3389 | -0.0016 | Negligible negative |
| - | ADX | 0.2117 | -0.0010 | Negligible negative |
| - | Mean Reversion | 0.1298 | -0.0005 | Negligible negative |
| - | Momentum | 0.1304 | -0.0304 | **Harmful** |
| - | OBV | 0.1586 | -0.0530 | **Harmful** |
| - | **Bollinger** | 0.1845 | **-0.1681** | **Most harmful — causes overfitting** |
| - | Sentiment | 0.1298 | 0.0000 | No data available |

### Key Findings

1. **Rank IC degrades from 0.35 to 0.13** as features are added beyond MACD
2. **Bollinger Bands are the most damaging** feature (-0.168 IC), likely causing overfitting
3. **MACD is the only feature with statistically meaningful positive contribution**
4. The model has good signal quality (IC=0.35) but the portfolio isn't capturing it (Sharpe -0.35) — portfolio construction needs separate attention
5. Results are consistent across both 2-ticker and 9-ticker universes

### Recommended Feature Set

```
ACTIVE FEATURES:
  - returns (return_1m, return_3m, return_6m, return_12m)
  - volatility (vol_20d, vol_60d)
  - volume (dollar_volume_20d, volume_ratio, turnover_20d)
  - macd (macd, macd_signal, macd_histogram)

REMOVED (harmful or neutral):
  - valuation (no impact)
  - rsi (redundant with MACD)
  - bollinger (causes overfitting)
  - atr (marginal, net negative with other features)
  - adx (negligible)
  - obv (harmful)
  - gap (negligible)
  - momentum (harmful)
  - mean_reversion (harmful)
```

---

## Decision 002: Optimal MACD Parameters per Stock

**Date**: 2026-03-14
**Status**: ACCEPTED
**Decision**: Use stock-specific MACD parameters found via Bayesian optimization.

### AMD Optimal Parameters

| Parameter | Old | New (Sharpe) | New (Risk-Adj) |
|-----------|-----|-------------|----------------|
| MACD Fast | 7 | **18** | 20 |
| MACD Slow | 46 | **37** | 48 |
| MACD Signal | 6 | **5** | 20 |
| RSI Period | 17 | **15** | 15 |
| RSI Overbought | 79 | **70** | 70 |
| RSI Oversold | 20 | **20** | 20 |
| **Sharpe** | 0.86 | **1.78 (+107%)** | 1.70 |
| **Return** | - | 216.9% | 152.7% |
| **Max Drawdown** | - | -26.0% | **-20.3%** |
| **Trades** | - | 31 | 13 |

**Insight**: AMD benefits from **faster MACD** (18/37 vs standard 12/26) — responsive to semiconductor cycle swings.

### SLV Optimal Parameters

| Parameter | Old | New (Sharpe) | New (Risk-Adj) |
|-----------|-----|-------------|----------------|
| MACD Fast | 5 | 5 | **5** |
| MACD Slow | 51 | 60 | **59** |
| MACD Signal | 5 | 5 | **5** |
| RSI Period | 14 | 14 | **13** |
| RSI Overbought | 79 | 80 | **80** |
| RSI Oversold | 40 | 40 | **39** |
| **Sharpe** | 2.33 | 2.38 | **2.47 (+6%)** |
| **Return** | - | 433.1% | 407.2% |
| **Max Drawdown** | - | -13.3% | **-12.1%** |
| **Trades** | - | 43 | 44 |

**Insight**: SLV benefits from **very slow MACD** (5/59 vs standard 12/26) — silver is a trend-following asset that rewards patience.

---

## Decision 003: Portfolio Construction Needs Fixing

**Date**: 2026-03-14
**Status**: OPEN — needs investigation
**Decision**: The walk-forward backtest produces negative Sharpe (-0.35) despite good signal quality (Rank IC 0.35).

### Problem

- Rank IC of 0.35 means the model correctly ranks stocks ~68% of the time
- But the long-short portfolio consistently loses money (Sharpe -0.35)
- This gap suggests the portfolio construction layer (position sizing, rebalancing, transaction costs) is destroying the signal

### Possible Causes

1. **Transaction costs at 4h rebalancing** — too frequent rebalancing erodes returns
2. **Position sizing** — equal weight may not be optimal
3. **Universe too small** — 2-9 tickers insufficient for cross-sectional ranking
4. **Short leg** — shorting the bottom quintile may not work in a bull market
5. **Benchmark mismatch** — 65.7% date overlap between price and benchmark data

### Next Steps

- Fix benchmark-price alignment (P1 bug)
- Test with larger universe (nasdaq_100 or sp500)
- Test longer rebalancing intervals (1d, 1w)
- Consider long-only portfolio construction

---

## Decision 004: Correlation-Based Feature Additions

**Date**: 2026-03-14
**Status**: PROPOSED
**Decision**: Add cross-asset correlation features for AMD and SLV.

### AMD Correlation Findings

| Peer | Pearson | Stability (20d rolling std) | Verdict |
|------|---------|---------------------------|---------|
| NVDA | 0.5520 | 0.2610 (Unstable) | **Strongest peer — add as feature** |
| GOOGL | 0.4150 | 0.2484 (Moderate) | Moderate |
| TSLA | 0.4140 | 0.2506 (Unstable) | Moderate |
| META | 0.4023 | 0.2804 (Unstable) | Moderate |
| AMZN | 0.4011 | 0.2845 (Unstable) | Moderate |
| MSFT | 0.3970 | 0.2763 (Unstable) | Moderate |
| AAPL | 0.3761 | 0.2544 (Unstable) | Weakest tech peer |

All correlations are **synchronous** (no lead-lag detected). Rolling correlations are **unstable** — swinging from -0.65 to +0.95 — meaning correlation itself could be a predictive feature.

### Proposed Features for AMD

| Feature | Source | Priority |
|---------|--------|----------|
| `nvda_relative_strength` | NVDA price data | HIGH |
| `semiconductor_breadth` | SMH ETF data | MEDIUM |
| `qqq_relative_performance` | QQQ price data | MEDIUM |
| `ai_news_sentiment` | Finnhub API | HIGH (requires integration) |

### Proposed Features for SLV

| Feature | Source | Priority |
|---------|--------|----------|
| `gold_silver_ratio` | GLD/SLV prices | HIGH |
| `dxy_momentum` | DXY price data | HIGH |
| `vix_regime` | VIX levels | MEDIUM |
| `geopolitical_risk_index` | Caldara-Iacoviello GPR | HIGH |
| `real_yield_10y` | FRED API | HIGH |
| `mining_breadth` | GDX/GDXJ data | MEDIUM |

---

## Decision 005: Critical Backtesting Time Periods

**Date**: 2026-03-14
**Status**: ACCEPTED
**Decision**: Any serious backtest must cover these periods to validate robustness.

### Tier 1 — Must Include (regime diversity)

| Period | Dates | Event | Why Critical | AMD Impact | SLV Impact |
|--------|-------|-------|-------------|------------|------------|
| **GFC** | Oct 2007 - Mar 2009 | Financial crisis | Systemic risk, correlations converge to 1.0, liquidity crisis | Severe (semis -60%) | Crashed 58% then boomed |
| **COVID Crash** | Feb-Mar 2020 | Pandemic shock | Fastest 30% drop ever, V-shaped recovery, tests signal speed | Sharp drop then massive recovery | Flash crash to $12, then $29 |
| **2022 Bear** | Jan-Oct 2022 | Fed rate hikes 0%→4.5% | Tests QT resilience, growth→value rotation | SOX -45%, devastating | Modest decline |
| **2023-2025 AI Bull** | Jan 2023 - present | AI boom + rate cuts | Current regime, sector momentum | AMD +77% (2025), AI catalyst | Silver +144% (2025), breakout >$30 |

### Tier 2 — Strongly Recommended

| Period | Dates | Event | Why Critical |
|--------|-------|-------|-------------|
| **2018 Q4 Selloff** | Oct-Dec 2018 | Trade war + Volmageddon + Fed tightening | Policy-driven 20% correction |
| **2015 China Scare** | Aug-Sep 2015 | China devaluation, VIX spike | Flash crash, emerging market contagion |
| **2011 Q3 Crisis** | Jul-Oct 2011 | European debt crisis, US downgrade | Silver crashed from $49, risk-off |
| **2025 Tariff Crash** | Apr 2-9, 2025 | "Liberation Day" tariffs | S&P -10% in 2 days, policy shock/whipsaw |

### Tier 3 — For Extended Validation

| Period | Dates | Event | Why Critical |
|--------|-------|-------|-------------|
| **Dot-Com Bust** | Mar 2000 - Oct 2002 | Tech bubble burst | NASDAQ -80%, definitive tech strategy test |
| **QE2 Commodity Boom** | Nov 2010 - Jun 2011 | Precious metals peak | Silver hit $49.51, gold to $1,920 |
| **2016 Reflation** | Nov 2016 - 2017 | Post-election regime shift | Sector rotation, bond sell-off |

### Minimum Requirements for Robust Backtesting

| Requirement | Value | Rationale |
|-------------|-------|-----------|
| **Minimum history** | 5 years (daily), 2 years (hourly) | Covers at least 1 bear + 1 bull cycle |
| **Ideal history** | 10+ years (daily) | Covers multiple rate cycles and regimes |
| **Walk-forward windows** | At least 20 | Statistical significance requires sufficient samples |
| **Training window** | 3-5 years (daily) | Must span at least one regime change |
| **Test window** | 3-6 months | Match your trading horizon |
| **Minimum trades** | 300+ total | Required for reliable Sharpe estimate |
| **Out-of-sample holdout** | 10-20% of most recent data | Final validation, never optimized on |

### VIX Regime Thresholds for Testing

| VIX Level | Regime | Historical Context |
|-----------|--------|-------------------|
| <15 | Low volatility / complacency | Normal bull market |
| 15-25 | Normal | Average conditions |
| 25-40 | Elevated / stress | Corrections, uncertainty |
| 40-60 | High fear | Crashes, policy shocks |
| >60 | Extreme panic | GFC (80), COVID (83), Tariff crash (52) |

**Test separately**: Run your strategy on low-VIX, normal, and high-VIX sub-periods. A robust strategy should not only work in one regime.

### Current Data Gap Assessment

| Requirement | Current State | Gap |
|-------------|--------------|-----|
| History depth | 22 months (1h) | Need 5+ years daily via Alpaca |
| Regime coverage | 2024-2026 only (bull) | Missing GFC, COVID, 2022 bear |
| Benchmark alignment | 65.7% overlap | Must fix (P1 bug) |
| Resolution | 1h only | Need 5m/15m for intraday signals |
| Universe size | 9 tickers | Need 50-100+ for cross-sectional strategies |

---

## Decision 006: Recommended Strategy for Serious Backtesting

**Date**: 2026-03-14
**Status**: PROPOSED
**Decision**: Before serious backtesting, address these in order.

### Phase 1: Data Foundation (Week 1)

1. **Fix benchmark alignment** — re-download SPY to match price date range
2. **Switch to daily data** — download 10+ years via Alpaca Markets for AMD, SLV, and full tech_giants watchlist
3. **Download comparison assets** — GLD, GDX, QQQ, SMH, VIX, DXY for correlation features
4. **Expand universe** — download at least nasdaq_100 for meaningful cross-sectional ranking

### Phase 2: Model Simplification (Week 2)

5. **Reduce to baseline + MACD** per regression test findings
6. **Use stock-specific MACD params** — AMD(18/37/5), SLV(5/59/5)
7. **Add cross-asset features** — NVDA relative strength (for AMD), gold/silver ratio (for SLV)
8. **Test longer rebalancing** — weekly instead of 4-hourly

### Phase 3: Walk-Forward Validation (Week 3)

9. **Run walk-forward** with train=3yr, test=6mo, step=1mo on 10+ years of daily data
10. **Sub-period analysis** — check performance in GFC, COVID, 2022 bear, AI bull separately
11. **VIX regime analysis** — stratify results by VIX level
12. **Out-of-sample holdout** — reserve 2025-2026 data, train on 2015-2024

### Phase 4: Portfolio Construction (Week 4)

13. **Test long-only** vs long-short
14. **Test universe sizes** — 10, 30, 50, 100 stocks
15. **Optimize rebalancing** — daily, weekly, monthly
16. **Add Finnhub sentiment** as an alpha signal

### Success Criteria

| Metric | Target | Rationale |
|--------|--------|-----------|
| Sharpe Ratio | > 0.5 (annualized) | Minimum viable for live trading |
| Rank IC | > 0.05 | Statistically significant signal |
| Max Drawdown | < -25% | Survivable |
| Hit Rate | > 52% | Better than random |
| Turnover | < 50% monthly | Manageable transaction costs |
| Consistent across regimes | Yes | Must work in both bull and bear |
