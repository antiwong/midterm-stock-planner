# Data Gap Analysis Report

**Generated**: 2026-03-13T23:22:01.279269

## Overall Data Quality: D (68.1/100)

## Data Summary

| Property | Value |
|----------|-------|
| Total Rows | 24,548 |
| Tickers | 9 (AAPL, AMD, AMZN, GOOGL, META, MSFT, NVDA, SLV, TSLA) |
| Date Range | 2023-02-22 00:00:00 to 2026-02-20 20:30:00 |
| Span | 1094 days |

## Resolution Analysis

| Property | Value |
|----------|-------|
| Detected Interval | 1h |
| Median Interval | 60.0 minutes |
| Bars/Day | ~24.0 |
| Higher Res Needed | 5m, 15m |
| Recommended Source | Alpaca Markets (alpaca-py) — free, 7+ years of 1m/5m/15m data |

## Ticker Coverage

- **Loaded**: 9 tickers

## Data Quality per Ticker

| Ticker | Issues | Completeness | Details |
|--------|--------|-------------|---------|
| AAPL | 2 | 100.0% | zero_volume(2); price_outliers_3std(41) |
| AMD | 1 | 100.0% | price_outliers_3std(5) |
| AMZN | 1 | 100.0% | price_outliers_3std(40) |
| GOOGL | 1 | 100.0% | price_outliers_3std(45) |
| META | 2 | 100.0% | zero_volume(1); price_outliers_3std(40) |
| MSFT | 2 | 100.0% | zero_volume(1); price_outliers_3std(46) |
| NVDA | 2 | 100.0% | zero_volume(3); price_outliers_3std(37) |
| SLV | 1 | 100.0% | price_outliers_3std(6) |
| TSLA | 2 | 100.0% | zero_volume(1); price_outliers_3std(34) |

## Date Range Gaps

| Ticker | Suspicious Gaps | Largest Gap (hours) |
|--------|----------------|---------------------|
| AAPL | 20 | 94.0h |
| AMD | 31 | 96.0h |
| AMZN | 20 | 94.0h |
| GOOGL | 20 | 94.0h |
| META | 20 | 94.0h |
| MSFT | 20 | 94.0h |
| NVDA | 20 | 94.0h |
| SLV | 31 | 96.0h |
| TSLA | 20 | 94.0h |

## Benchmark Alignment

| Property | Value |
|----------|-------|
| Price Dates | 752 |
| Benchmark Dates | 494 |
| Overlap | 65.7% |
| Missing in Benchmark | 258 dates |

## Recommendations

### [HIGH] data_resolution

Current data is 1h. Higher resolution (5m/15m) via Alpaca Markets would enable better intraday signal detection and more walk-forward windows.

**Action**: Install alpaca-py and run download with --interval 5m or 15m

### [MEDIUM] benchmark_alignment

Benchmark-price date overlap is 65.7%. Misaligned dates cause NaN in excess return calculations.

**Action**: Re-download benchmark data to match price date range
