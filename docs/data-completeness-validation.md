# Data Completeness Validation

**Date:** 2026-01-15  
**Status:** ✅ Implemented

## Overview

The application now implements **strict data completeness validation** to ensure that missing data is handled seriously and proactively. This prevents wasted computation and provides clear guidance on how to fix data issues.

## Key Features

### 1. Pre-Analysis Validation

Before running any analysis, the system now:
- ✅ Checks all required data is available
- ✅ Identifies missing data with specific requirements
- ✅ Provides actionable fix instructions
- ✅ Skips analyses that cannot run (instead of failing silently)

### 2. Data Requirements by Analysis

Each analysis type has specific data requirements:

| Analysis | Required Data | Critical? |
|----------|--------------|-----------|
| **Performance Attribution** | Portfolio returns, Portfolio weights, Stock returns, Sector mapping | ✅ Yes |
| **Benchmark Comparison** | Portfolio returns, Benchmark data | ✅ Yes |
| **Factor Exposure** | Portfolio weights, Stock features | ⚠️ Partial |
| **Rebalancing Analysis** | Portfolio weights | ✅ Yes |
| **Style Analysis** | Portfolio weights, Fundamental data | ⚠️ Partial |

### 3. Error Handling

**Before (Old Behavior):**
- Analysis would run and fail with cryptic errors
- No clear indication of what data was missing
- Wasted computation on incomplete analyses

**After (New Behavior):**
- Pre-validation catches missing data upfront
- Clear error messages with specific missing data types
- Actionable fix instructions provided
- Analyses skipped gracefully when data is missing

## Usage

### Standalone Data Check

Check data completeness before running analysis:

```bash
python scripts/check_data_completeness.py <run_id>
```

**Example Output:**
```
======================================================================
DATA COMPLETENESS CHECK
======================================================================

⚠️  Some required data is missing

Analysis Status:
----------------------------------------------------------------------
  ❌ attribution: Cannot run attribution: Missing critical data (stock_returns)
  ❌ benchmark_comparison: Cannot run benchmark_comparison: Missing critical data (benchmark_data)
  ✅ factor_exposure: Can run
  ✅ rebalancing: Can run
  ⚠️ style: style may be incomplete: Missing data (fundamental_data)

❌ CRITICAL ISSUES:
----------------------------------------------------------------------
  attribution: Cannot run attribution: Missing critical data (stock_returns)
    → Stock Returns: Individual stock returns are needed for performance attribution. 
      These can be calculated from price data or loaded from backtest results.
  
  benchmark_comparison: Cannot run benchmark_comparison: Missing critical data (benchmark_data)
    → Benchmark Data: Ensure benchmark data (SPY, QQQ) is available for the portfolio's date range. 
      Check if benchmark data needs to be downloaded or updated.

RECOMMENDATIONS:
----------------------------------------------------------------------
  1. Benchmark Data: Ensure benchmark data (SPY, QQQ) is available...
  2. Fundamental Data: Run 'python scripts/download_fundamentals.py --watchlist <watchlist>'
  3. Stock Returns: Individual stock returns are needed...
```

### Integrated into Analysis Runner

The data completeness check is automatically run when using `ComprehensiveAnalysisRunner`:

```python
from src.analytics.comprehensive_analysis import ComprehensiveAnalysisRunner

runner = ComprehensiveAnalysisRunner(strict_validation=True)
results = runner.run_all_analysis(
    run_id=run_id,
    portfolio_data=portfolio_data,
    stock_data=stock_data
)

# Check for warnings/errors
if results.get('errors'):
    print("Critical issues found!")
    for error in results['errors']:
        print(f"  {error['analysis']}: {error['message']}")
```

## Fix Instructions

The system provides specific instructions for each type of missing data:

### Missing Stock Returns
```
Stock Returns: Individual stock returns are needed for performance attribution. 
These can be calculated from price data or loaded from backtest results.
```

### Missing Fundamental Data
```
Fundamental Data: Run 'python scripts/download_fundamentals.py --watchlist <watchlist>' 
to download PE ratios, ROE, margins, and other fundamental metrics.
```

### Missing Benchmark Data
```
Benchmark Data: Ensure benchmark data (SPY, QQQ) is available for the portfolio's date range. 
Check if benchmark data needs to be downloaded or updated.
```

### Missing Sector Mapping
```
Sector Mapping: Ensure portfolio holdings have sector information. 
This is usually included in portfolio output files.
```

## Implementation Details

### DataCompletenessChecker

The `DataCompletenessChecker` class:
- Defines data requirements for each analysis type
- Validates data availability
- Generates comprehensive reports
- Provides fix instructions

### Integration Points

1. **ComprehensiveAnalysisRunner**
   - Runs data completeness check before analysis
   - Skips analyses with missing critical data
   - Includes completeness results in output
   - Provides warnings/errors summary

2. **Error Messages**
   - All error messages now include:
     - What data is missing
     - Why it's needed
     - How to fix it

3. **GUI Integration** (Future)
   - Can display data completeness status
   - Show warnings before running analysis
   - Provide fix buttons/links

## Benefits

1. **Prevents Wasted Computation**
   - Catches missing data before running expensive analyses
   - Saves time and resources

2. **Clear Error Messages**
   - Users know exactly what's wrong
   - Actionable guidance on how to fix

3. **Graceful Degradation**
   - Analyses that can run still execute
   - Missing data doesn't break the entire system

4. **Better User Experience**
   - Proactive validation
   - Clear feedback
   - Helpful instructions

## Example Workflow

1. **User runs analysis:**
   ```bash
   python scripts/run_comprehensive_analysis.py --run-id 20260115_185037_e08e49ae
   ```

2. **System checks data completeness:**
   - Validates all required data
   - Identifies missing fundamental data

3. **System provides feedback:**
   ```
   ⚠️  Skipping style analysis: Missing required data (fundamental_data)
   → Fundamental Data: Run 'python scripts/download_fundamentals.py --watchlist jan_26'
   ```

4. **User fixes data:**
   ```bash
   python scripts/download_fundamentals.py --watchlist jan_26
   ```

5. **User re-runs analysis:**
   - All analyses now complete successfully

## Future Enhancements

1. **GUI Integration**
   - Display data completeness status in dashboard
   - Show warnings before running analysis
   - Provide one-click fix buttons

2. **Automatic Data Fetching**
   - Automatically download missing fundamental data
   - Fetch benchmark data if missing
   - Calculate stock returns from available price data

3. **Data Quality Metrics**
   - Track data completeness over time
   - Alert when data becomes stale
   - Suggest data refresh schedules

## Conclusion

The strict data completeness validation ensures that missing data is handled seriously and proactively. Users get clear feedback on what's missing and how to fix it, preventing wasted computation and improving the overall user experience.

---

**Related Files:**
- `src/analytics/data_completeness.py` - Data completeness checker
- `src/analytics/comprehensive_analysis.py` - Integrated validation
- `scripts/check_data_completeness.py` - Standalone checker
