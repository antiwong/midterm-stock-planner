# Data Validation Report

**Generated:** 2026-03-15 06:40:39
**Watchlist:** None
**Status:** ✅ PASSED

---

## Summary

✅ Data validation PASSED
⚠️ 3 warning(s) detected

Coverage: 7/7 tickers (100.0%)
Date Range: 2014-01-02 to 2026-03-13
Total Rows: 122,047

## ⚠️ Warnings

### DATE_RANGE_START
Data starts at 2014-01-02, but 2014-01-01 was requested

```json
{
  "data_start": "2014-01-02",
  "required_start": "2014-01-01"
}
```

### DATE_RANGE_END
Data ends at 2026-03-13, but 2026-03-15 was requested

```json
{
  "data_end": "2026-03-13",
  "required_end": "2026-03-15"
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

- **Available Tickers:** 7
- **Missing Tickers:** 0
- **Total Required:** 7
- **Coverage Pct:** 100.0
- **Data Start:** 2014-01-02
- **Data End:** 2026-03-13
- **Required Start:** 2014-01-01
- **Required End:** 2026-03-15
- **Tickers With Gaps:** 0
- **Quality Issues:** 1
- **Total Rows:** 122047
- **Unique Tickers:** 127
- **Date Range Days:** 4453
- **Avg Rows Per Ticker:** 961.0

## 📥 Download Report

- **Successful:** 7
- **Failed:** 0
