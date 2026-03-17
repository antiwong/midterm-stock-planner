# Data Validation Report

**Generated:** 2026-03-16 22:14:47
**Watchlist:** None
**Status:** ✅ PASSED

---

## Summary

✅ Data validation PASSED
⚠️ 2 warning(s) detected

Coverage: 1/1 tickers (100.0%)
Date Range: 2014-01-02 to 2026-03-13
Total Rows: 523,328

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

- **Available Tickers:** 1
- **Missing Tickers:** 0
- **Total Required:** 1
- **Coverage Pct:** 100.0
- **Data Start:** 2014-01-02
- **Data End:** 2026-03-13
- **Required Start:** 2023-03-15
- **Required End:** 2026-03-16
- **Tickers With Gaps:** 0
- **Quality Issues:** 1
- **Total Rows:** 523328
- **Unique Tickers:** 166
- **Date Range Days:** 4453
- **Avg Rows Per Ticker:** 3153.0

## 📥 Download Report

- **Successful:** 1
- **Failed:** 0
