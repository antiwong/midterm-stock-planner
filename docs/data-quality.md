# Data Quality Tracking — QuantaAlpha Midterm Stock Planner

## Current Quality Score: A (91/100)

**Last Updated**: 2026-03-14

---

## Quality Score History

| Date | Score | Grade | Change | Notes |
|------|-------|-------|--------|-------|
| 2026-03-14 | 91.0 | A | +5.0 | nasdaq_100 expansion (98 tickers), FRED script ready |
| 2026-03-14 | 86.0 | B+ | +11.0 | 10yr daily data (21 tickers), cross-asset added, Alpaca integration |
| 2026-03-14 | 75.0 | C | +6.9 | Benchmark alignment fixed (100%), 5 tickers added, zero-volume cleaned |
| 2026-03-13 | 68.1 | D | — | Initial assessment. Benchmark 65.7% overlap, 9 tickers, zero-volume bars |

---

## Current State

### Data Files

| File | Resolution | Tickers | Date Range | Rows |
|------|-----------|---------|------------|------|
| `data/prices_daily.csv` | Daily | 98 | 2016-01-04 to 2026-03-13 | 237,750 |
| `data/prices.csv` | Hourly | 14 | 2024-04-01 to 2026-03-13 | 50,850 |
| `data/benchmark_daily.csv` | Daily | 1 (SPY) | 2016-01-04 to 2026-03-13 | 2,563 |
| `data/benchmark.csv` | Mixed | 1 (SPY) | 2023-01-03 to 2026-03-13 | 3,731 |

### Data Coverage (Daily — Primary)

| Property | Value | Target | Status |
|----------|-------|--------|--------|
| Tickers | 98 | 50+ (nasdaq_100) | Met |
| Date Range | 2016-01-04 to 2026-03-13 | 2015+ (10yr) | Met |
| History Depth | 10.2 years | 10yr | Met |
| Resolution | Daily + Hourly | Daily + 1h + 15m | Partial |
| Total Daily Rows | 237,750 | — | — |

### Tickers Available (Daily) — 98 total

**NASDAQ-100 (77 new)**: ADI, AEP, ALGN, AMAT, AMGN, ABNB, AVGO, BIDU, BIIB, BKNG, CDNS, CHTR, CMCSA, COST, CPRT, CRWD, CSCO, CSX, CTAS, CDW, DDOG, DLTR, DXCM, EA, EBAY, EXC, FAST, FTNT, GFS, GEHC, GILD, GOOG, HON, IDXX, ILMN, ISRG, JD, KDP, KHC, KLAC, LCID, LRCX, LULU, MAR, MDB, MDLZ, MELI, MNST, MRNA, MRVL, MU, NET, ODFL, ON, ORLY, PANW, PAYX, PCAR, PDD, PEP, QCOM, REGN, RIVN, ROST, SBUX, SNPS, SNOW, TEAM, TMUS, TTWO, TXN, VRSK, VRTX, WBD, WDAY, XEL, ZS
**Tech Giants (13)**: AAPL, ADBE, AMD, AMZN, CRM, GOOGL, INTC, META, MSFT, NFLX, NVDA, ORCL, TSLA
**Precious Metals (1)**: SLV
**Cross-Asset (4)**: GLD, GDX, QQQ, SMH
**Macro (3)**: VIX, DXY, SPY

### Benchmark Alignment (Daily)

| Property | Value | Target | Status |
|----------|-------|--------|--------|
| Price Dates | 2,563 | — | — |
| Benchmark Dates | 2,563 | — | — |
| Overlap | 100.0% | 100% | OK |

### Regime Coverage (per Decision 005)

| Period | Dates | Covered? |
|--------|-------|----------|
| 2018 Q4 Selloff | Oct-Dec 2018 | Yes |
| COVID Crash | Feb-Mar 2020 | Yes |
| 2022 Bear | Jan-Oct 2022 | Yes |
| 2023-2025 AI Bull | Jan 2023-present | Yes |
| 2025 Tariff Crash | Apr 2-9, 2025 | Upcoming |
| GFC (2007-2009) | Oct 2007-Mar 2009 | No (data starts 2016) |

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
| History Depth | 25% | 95/100 | 10.2 years daily. Covers 4 regime changes. |
| Ticker Coverage | 20% | 95/100 | 98 tickers. Full nasdaq_100 (minus 1 delisted). |
| Data Quality | 20% | 95/100 | 100% completeness, no nulls, zero-volume fixed |
| Benchmark Alignment | 15% | 100/100 | 100% overlap, daily SPY |
| Resolution Options | 10% | 60/100 | Daily + 1h. Missing 5m/15m. |
| Cross-Asset Data | 10% | 80/100 | GLD, GDX, QQQ, SMH, VIX, DXY all present |

**Weighted Score**: 0.25×95 + 0.20×95 + 0.20×95 + 0.15×100 + 0.10×60 + 0.10×80 = **91.75 → A**

---

## Improvement Roadmap

### Phase 1: Grade B+ (target: 85+) — COMPLETE

- [x] Download 10yr daily data for all tickers (2016-2026)
- [x] Add cross-asset tickers: GLD, GDX, QQQ, SMH, VIX, DXY
- [x] Expand to 20+ tickers
- [x] Integrate Alpaca Markets as primary data backend
- [x] Daily SPY benchmark (10yr)

### Phase 2: Grade A (target: 90+) — MOSTLY COMPLETE

- [x] Expand to nasdaq_100 (98 tickers) — 10yr daily
- [ ] Add fundamental data (PE, PB, earnings yield) via FMP or yfinance
- [ ] Integrate Finnhub sentiment data
- [ ] Add FRED macro data — script ready (`scripts/download_macro.py`), needs FRED_API_KEY

### Phase 3: Grade A+ (target: 95+)

- [ ] Add 5m/15m resolution data via Alpaca for intraday signals
- [ ] Geopolitical risk index (Caldara-Iacoviello GPR)
- [ ] Real-time news sentiment pipeline
- [ ] Pre-2016 data for GFC coverage (2007+)

---

## Change Log

### 2026-03-14 — NASDAQ-100 Expansion + FRED Script

**Changes**:
1. **77 new tickers downloaded**: Full NASDAQ-100 watchlist (10yr daily). Only ANSS failed (delisted).
2. **FRED macro script created**: `scripts/download_macro.py` for Treasury yields, inflation, unemployment, USD index. Needs free FRED_API_KEY.
3. **Total dataset**: 98 tickers, 237,750 rows of daily data.

**Impact**: Quality score B+ (86.0) → A (91.0). Cross-sectional ranking now viable with 98 tickers.

### 2026-03-14 — 10yr Daily Data + Cross-Asset + Alpaca Integration

**Changes**:
1. **Alpaca Markets integration**: Created `src/data/alpaca_client.py`, updated `download_prices.py` with `--backend` flag (auto/alpaca/yfinance).
2. **10yr daily data downloaded**: All 18 tickers from 2016-01-04 to 2026-03-13 (2,563 bars each). Stored in `data/prices_daily.csv`.
3. **Cross-asset tickers added**: GLD, GDX (precious metals), QQQ, SMH (tech/semi benchmarks).
4. **Macro data added**: VIX, DXY downloaded as tickers in prices_daily.csv.
5. **Daily SPY benchmark**: 10yr daily SPY saved to `data/benchmark_daily.csv`.
6. **Config updated**: Default interval switched to 1d, backtest params updated for daily data (train=3yr, test=6mo, step=30d, rebalance=weekly).
7. **Requirements updated**: Added `alpaca-py>=0.30.0`, `fredapi>=0.5.0`.

**Impact**: Quality score C (75.0) → B+ (86.0). Now covers 4 regime changes (2018 selloff, COVID, 2022 bear, AI bull).

### 2026-03-14 — Benchmark Fix + Ticker Expansion

**Changes**:
1. **Benchmark alignment fixed**: Re-downloaded SPY with daily+hourly merge. Overlap: 65.7% → 100%.
2. **Price data refreshed**: All 9 existing tickers updated through 2026-03-13 (+959 rows).
3. **5 tickers added**: INTC, ORCL, CRM, ADBE, NFLX. Total: 9 → 14 tickers.
4. **Zero-volume cleaned**: 51 zero-volume bars forward-filled.

**Impact**: Quality score D (68.1) → C (75.0)

### 2026-03-13 — Initial Assessment

**State**: 9 tickers, 22 months of 1h data, 65.7% benchmark overlap, some zero-volume bars.
**Score**: D (68.1)
