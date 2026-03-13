# Data Quality Tracking — QuantaAlpha Midterm Stock Planner

## Current Quality Score: C (75/100)

**Last Updated**: 2026-03-14

---

## Quality Score History

| Date | Score | Grade | Change | Notes |
|------|-------|-------|--------|-------|
| 2026-03-14 | 75.0 | C | +6.9 | Benchmark alignment fixed (100%), 5 tickers added, zero-volume cleaned |
| 2026-03-13 | 68.1 | D | — | Initial assessment. Benchmark 65.7% overlap, 9 tickers, zero-volume bars |

---

## Current State

### Data Coverage

| Property | Value | Target | Status |
|----------|-------|--------|--------|
| Tickers | 14 | 50+ (nasdaq_100) | Below target |
| Date Range | 2023-02-22 to 2026-03-13 | 2015+ (10yr daily) | Below target |
| Resolution | 1h only | 1h + daily (10yr) | Below target |
| Total Rows | 50,850 | — | — |
| Bars/Day | ~24 | — | OK |

### Tickers Available

**Tech Giants (13)**: AAPL, ADBE, AMD, AMZN, CRM, GOOGL, INTC, META, MSFT, NFLX, NVDA, ORCL, TSLA
**Precious Metals (1)**: SLV

### Benchmark Alignment

| Property | Value | Target | Status |
|----------|-------|--------|--------|
| Price Dates | 767 | — | — |
| Benchmark Dates | 801 | — | — |
| Overlap | 100.0% | 100% | OK |
| Missing in Benchmark | 0 | 0 | OK |

### Data Quality per Ticker

| Ticker | Completeness | Issues | Status |
|--------|-------------|--------|--------|
| AAPL | 100.0% | 42 price outliers (3std) | OK |
| ADBE | 100.0% | 63 price outliers (3std) | OK |
| AMD | 100.0% | 5 price outliers (3std) | OK |
| AMZN | 100.0% | 43 price outliers (3std) | OK |
| CRM | 100.0% | 61 price outliers (3std) | OK |
| GOOGL | 100.0% | 48 price outliers (3std) | OK |
| INTC | 100.0% | 55 price outliers (3std) | OK |
| META | 100.0% | 40 price outliers (3std) | OK |
| MSFT | 100.0% | 48 price outliers (3std) | OK |
| NFLX | 100.0% | 56 price outliers (3std) | OK |
| NVDA | 100.0% | 37 price outliers (3std) | OK |
| ORCL | 100.0% | 63 price outliers (3std) | OK |
| SLV | 100.0% | 6 price outliers (3std) | OK |
| TSLA | 100.0% | 37 price outliers (3std) | OK |

### Date Range Gaps (Suspicious)

All tickers have 20-31 suspicious gaps with largest gap 94-96h (long weekends/holidays — expected).

---

## Quality Benchmarks

### Grading Criteria

| Grade | Score | Description |
|-------|-------|-------------|
| A+ | 95-100 | Production-ready: 10yr+ daily, 50+ tickers, multi-resolution, sentiment |
| A | 90-94 | Excellent: 5yr+ daily, 30+ tickers, benchmark aligned, no quality issues |
| B+ | 85-89 | Good: 3yr+ data, 20+ tickers, benchmark aligned, minor gaps |
| B | 80-84 | Adequate: 2yr+ data, 15+ tickers, benchmark aligned |
| C | 70-79 | Fair: Limited history, adequate tickers, some quality issues |
| D | 60-69 | Poor: Short history, few tickers, alignment issues |
| F | <60 | Unusable: Major data gaps, broken alignment, missing tickers |

### Scoring Components (weighted)

| Component | Weight | Current Score | Notes |
|-----------|--------|---------------|-------|
| History Depth | 25% | 40/100 | 22 months (1h). Need 5yr+ daily |
| Ticker Coverage | 20% | 60/100 | 14 tickers. Need 50+ for cross-sectional |
| Data Quality | 20% | 95/100 | 100% completeness, no nulls, zero-volume fixed |
| Benchmark Alignment | 15% | 100/100 | 100% overlap after fix |
| Resolution Options | 10% | 30/100 | 1h only. Need 5m/15m + daily |
| Cross-Asset Data | 10% | 20/100 | No GLD, GDX, QQQ, SMH, VIX, DXY in prices.csv |

---

## Improvement Roadmap

### Phase 1: Grade B (target: 80+)

- [ ] Download 10yr daily data via Alpaca Markets for all 14 tickers
- [ ] Add cross-asset tickers: GLD, GDX, QQQ, SMH, VIX, DXY
- [ ] Expand to 20+ tickers (add NASDAQ-100 subset)

### Phase 2: Grade A (target: 90+)

- [ ] Download full nasdaq_100 watchlist (100 tickers)
- [ ] Add 5m/15m resolution data for intraday signals
- [ ] Add fundamental data (PE, PB, earnings yield) via FMP or similar
- [ ] Integrate Finnhub sentiment data

### Phase 3: Grade A+ (target: 95+)

- [ ] 10yr+ daily history for all tickers
- [ ] Multi-resolution: daily + 1h + 15m + 5m
- [ ] Macro data: FRED (yields, inflation, unemployment)
- [ ] Geopolitical risk index (Caldara-Iacoviello GPR)
- [ ] Real-time news sentiment pipeline

---

## Change Log

### 2026-03-14 — Benchmark Fix + Ticker Expansion

**Changes**:
1. **Benchmark alignment fixed**: Re-downloaded SPY with daily (2023-01-03 to 2024-03-24) + hourly (2024-03-25 onward) merge. Overlap: 65.7% → 100%.
2. **Price data refreshed**: All 9 existing tickers updated through 2026-03-13 (+959 rows).
3. **5 tickers added**: INTC, ORCL, CRM, ADBE, NFLX (~5,068 rows each). Total: 9 → 14 tickers.
4. **Zero-volume cleaned**: 51 zero-volume bars forward-filled across all tickers.
5. **Gap analysis automated**: `scripts/automate_regression.py` with `DataGapAnalyzer` class.

**Impact**: Quality score D (68.1) → C (75.0)

### 2026-03-13 — Initial Assessment

**State**: 9 tickers, 22 months of 1h data, 65.7% benchmark overlap, some zero-volume bars.
**Score**: D (68.1)
