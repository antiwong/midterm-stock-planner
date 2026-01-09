# Quality Score Fix: Penalty for Missing Data

## Problem

Previously, when fundamental data (ROE, margins, PE, PB) was missing, stocks would receive a **neutral score of 50.0**. This was problematic because:

1. **No Differentiation**: Stocks without data were treated the same as stocks with average fundamentals
2. **Misleading Scores**: A score of 50.0 suggested "average quality" when in fact we have no information
3. **Purchase Triggers Impact**: The purchase triggers function couldn't properly differentiate between stocks with and without fundamental data

## Solution

**Changed default score from 50.0 (neutral) to 30.0 (penalty)** for stocks without fundamental data.

### Value Score (`compute_value_score`)

- **Before**: Missing PE/PB data → score = 50.0
- **After**: Missing PE/PB data → score = 30.0

### Quality Score (`compute_quality_score`)

- **Before**: Missing ROE/margin data → score = 50.0
- **After**: Missing ROE/margin data → score = 30.0

## Impact

### Benefits

1. **Better Differentiation**: Stocks with fundamental data now rank higher than stocks without data
2. **Incentivizes Data Collection**: Lower scores for missing data encourage downloading comprehensive fundamentals
3. **More Accurate Rankings**: Purchase triggers will now properly favor stocks with complete fundamental data
4. **Clearer Signals**: A score of 30.0 clearly indicates "missing data" rather than "average quality"

### Example

**Before (all stocks get 50.0):**
```
Stock A: Quality = 50.0 (no data)
Stock B: Quality = 50.0 (no data)
Stock C: Quality = 50.0 (no data)
→ All treated equally, no differentiation
```

**After (stocks without data get 30.0):**
```
Stock A: Quality = 30.0 (no data) - penalized
Stock B: Quality = 75.0 (ROE=20%, margin=15%) - ranked
Stock C: Quality = 30.0 (no data) - penalized
→ Stock B ranks higher, clear differentiation
```

## Implementation Details

### When Penalty Applies

- **No fundamental data columns**: If `roe`, `net_margin`, `gross_margin` columns don't exist → penalty (30.0)
- **All values invalid**: If all values are NaN or out of range → penalty (30.0)
- **Single valid value**: If only 1 stock has data (can't rank) → that stock gets 50.0, others get 30.0

### When Ranking Applies

- **Multiple valid values**: If 2+ stocks have valid data → proper ranking (0-100 based on percentile)
- **Partial data**: If a stock has some metrics but not others → average of available metrics

## Migration Notes

### For Existing Runs

- Existing runs will continue to work, but scores may change if you re-run analysis
- Stocks without fundamental data will now show lower scores (30.0 instead of 50.0)
- This is **expected behavior** and indicates the need to download fundamental data

### For New Runs

1. **Download Fundamentals**: Use `scripts/download_fundamentals.py` to get comprehensive data
2. **Verify Coverage**: Check that your watchlist stocks have fundamental data
3. **Re-run Analysis**: Purchase triggers will now properly differentiate stocks

## Recommendations

1. **Download Fundamentals**: Always download fundamental data before running purchase triggers
2. **Check Coverage**: Verify that >80% of stocks have fundamental data
3. **Monitor Scores**: If many stocks have quality/value scores of 30.0, download fundamentals
4. **Use Filters**: Consider adding a filter to exclude stocks with scores < 40 (likely missing data)

## Related Documentation

- [Download Fundamentals Guide](download-fundamentals-guide.md) - How to download comprehensive fundamental data
- [Purchase Triggers](purchase-triggers.md) - How purchase triggers work
- [Domain Analysis](domain-analysis.md) - Detailed scoring methodology
