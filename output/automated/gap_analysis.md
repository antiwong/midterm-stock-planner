# Data Gap Analysis Report

**Generated**: 2026-03-14T06:15:28.940555

## Overall Data Quality: C (75/100)

## Data Summary

| Property | Value |
|----------|-------|
| Total Rows | 50,850 |
| Tickers | 14 (AAPL, ADBE, AMD, AMZN, CRM, GOOGL, INTC, META, MSFT, NFLX, NVDA, ORCL, SLV, TSLA) |
| Date Range | 2023-02-22 00:00:00 to 2026-03-13 19:30:00 |
| Span | 1115 days |

## Resolution Analysis

| Property | Value |
|----------|-------|
| Detected Interval | 1h |
| Median Interval | 60.0 minutes |
| Bars/Day | ~24.0 |
| Higher Res Needed | 5m, 15m |
| Recommended Source | Alpaca Markets (alpaca-py) — free, 7+ years of 1m/5m/15m data |

## Ticker Coverage

- **Loaded**: 14 tickers

## Data Quality per Ticker

| Ticker | Issues | Completeness | Details |
|--------|--------|-------------|---------|
| AAPL | 1 | 100.0% | price_outliers_3std(42) |
| ADBE | 1 | 100.0% | price_outliers_3std(63) |
| AMD | 1 | 100.0% | price_outliers_3std(5) |
| AMZN | 1 | 100.0% | price_outliers_3std(43) |
| CRM | 1 | 100.0% | price_outliers_3std(61) |
| GOOGL | 1 | 100.0% | price_outliers_3std(48) |
| INTC | 1 | 100.0% | price_outliers_3std(55) |
| META | 1 | 100.0% | price_outliers_3std(40) |
| MSFT | 1 | 100.0% | price_outliers_3std(48) |
| NFLX | 1 | 100.0% | price_outliers_3std(56) |
| NVDA | 1 | 100.0% | price_outliers_3std(37) |
| ORCL | 1 | 100.0% | price_outliers_3std(63) |
| SLV | 1 | 100.0% | price_outliers_3std(6) |
| TSLA | 1 | 100.0% | price_outliers_3std(37) |

## Date Range Gaps

| Ticker | Suspicious Gaps | Largest Gap (hours) |
|--------|----------------|---------------------|
| AAPL | 20 | 94.0h |
| ADBE | 30 | 94.0h |
| AMD | 31 | 96.0h |
| AMZN | 20 | 94.0h |
| CRM | 30 | 94.0h |
| GOOGL | 20 | 94.0h |
| INTC | 30 | 94.0h |
| META | 20 | 94.0h |
| MSFT | 20 | 94.0h |
| NFLX | 30 | 94.0h |
| NVDA | 20 | 94.0h |
| ORCL | 30 | 94.0h |
| SLV | 31 | 96.0h |
| TSLA | 20 | 94.0h |

## Benchmark Alignment

| Property | Value |
|----------|-------|
| Price Dates | 767 |
| Benchmark Dates | 801 |
| Overlap | 100.0% |
| Missing in Benchmark | 0 dates |

## Recommendations

### [HIGH] data_resolution

Current data is 1h. Higher resolution (5m/15m) via Alpaca Markets would enable better intraday signal detection and more walk-forward windows.

**Action**: Install alpaca-py and run download with --interval 5m or 15m
