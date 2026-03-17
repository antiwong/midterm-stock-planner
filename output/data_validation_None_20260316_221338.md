# Data Validation Report

**Generated:** 2026-03-16 22:13:38
**Watchlist:** None
**Status:** ❌ FAILED

---

## Summary

❌ Data validation FAILED with 1 error(s)
⚠️ 2 warning(s) detected

Coverage: 8/9 tickers (88.9%)
Date Range: 2016-01-04 to 2026-03-13
Total Rows: 367,671

## ❌ Errors

### MISSING_TICKERS
1 tickers missing from price data

**Affected items:**
- LUMN

## ⚠️ Warnings

### DATE_RANGE_START
Data starts at 2016-01-04, but 2016-01-01 was requested

```json
{
  "data_start": "2016-01-04",
  "required_start": "2016-01-01"
}
```

### DATE_RANGE_END
Data ends at 2026-03-13, but 2026-03-16 was requested

```json
{
  "data_end": "2026-03-13",
  "required_end": "2026-03-16"
}
```

## 📊 Statistics

- **Available Tickers:** 8
- **Missing Tickers:** 1
- **Total Required:** 9
- **Coverage Pct:** 88.88888888888889
- **Data Start:** 2016-01-04
- **Data End:** 2026-03-13
- **Required Start:** 2016-01-01
- **Required End:** 2026-03-16
- **Tickers With Gaps:** 0
- **Quality Issues:** 0
- **Total Rows:** 367671
- **Unique Tickers:** 150
- **Date Range Days:** 3721
- **Avg Rows Per Ticker:** 2451.0

## 📥 Download Report

- **Successful:** 8
- **Failed:** 0
