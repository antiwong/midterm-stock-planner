# Data Validation Report

**Generated:** 2026-03-16 22:13:26
**Watchlist:** None
**Status:** ❌ FAILED

---

## Summary

❌ Data validation FAILED with 1 error(s)
⚠️ 2 warning(s) detected

Coverage: 8/9 tickers (88.9%)
Date Range: 2014-01-02 to 2026-03-13
Total Rows: 512,364

## ❌ Errors

### MISSING_TICKERS
1 tickers missing from price data

**Affected items:**
- LUMN

## ⚠️ Warnings

### DATE_RANGE_END
Data ends at 2026-03-13, but 2026-03-16 was requested

```json
{
  "data_end": "2026-03-13",
  "required_end": "2026-03-16"
}
```

### DATA_QUALITY
1 data quality issues detected

```json
[
  {
    "issue": "null_values",
    "details": {
      "open": 1859,
      "high": 1859,
      "low": 1859,
      "close": 1859,
      "volume": 1859
    }
  }
]
```

## 📊 Statistics

- **Available Tickers:** 8
- **Missing Tickers:** 1
- **Total Required:** 9
- **Coverage Pct:** 88.88888888888889
- **Data Start:** 2014-01-02
- **Data End:** 2026-03-13
- **Required Start:** 2023-03-15
- **Required End:** 2026-03-16
- **Tickers With Gaps:** 0
- **Quality Issues:** 1
- **Total Rows:** 512364
- **Unique Tickers:** 165
- **Date Range Days:** 4453
- **Avg Rows Per Ticker:** 3105.0

## 📥 Download Report

- **Successful:** 8
- **Failed:** 0
