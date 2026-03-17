# Data Validation Report

**Generated:** 2026-03-16 22:05:29
**Watchlist:** None
**Status:** ✅ PASSED

---

## Summary

✅ Data validation PASSED
⚠️ 2 warning(s) detected

Coverage: 21/21 tickers (100.0%)
Date Range: 2014-01-02 to 2026-03-13
Total Rows: 451,154

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
      "open": 1860,
      "high": 1860,
      "low": 1860,
      "close": 1860,
      "volume": 1860
    }
  }
]
```

## 📊 Statistics

- **Available Tickers:** 21
- **Missing Tickers:** 0
- **Total Required:** 21
- **Coverage Pct:** 100.0
- **Data Start:** 2014-01-02
- **Data End:** 2026-03-13
- **Required Start:** 2023-03-15
- **Required End:** 2026-03-16
- **Tickers With Gaps:** 0
- **Quality Issues:** 1
- **Total Rows:** 451154
- **Unique Tickers:** 158
- **Date Range Days:** 4453
- **Avg Rows Per Ticker:** 2855.0

## 📥 Download Report

- **Successful:** 21
- **Failed:** 0
