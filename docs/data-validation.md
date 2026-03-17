# Data Validation for AI Insights

> [← Back to Documentation Index](README.md)

## Overview

The AI Insights feature now includes comprehensive data validation to catch data quality issues before generating insights. This prevents misleading or unreliable AI-generated commentary and recommendations.

## What Gets Validated

### 1. Data Completeness
- Checks for required columns (`ticker`, `score`)
- Identifies missing or null values
- Verifies minimum data points (recommends 20+ stocks)

### 2. Score Distribution
- Detects if all scores are identical (critical error)
- Checks score variance (low variance = poor differentiation)
- Identifies narrow score ranges
- Flags excessive clustering at boundaries

### 3. Sector Score Differentiation
- **Critical Check**: Detects if all sectors have identical average scores
- Checks sector score variance
- Identifies sectors with too few stocks (< 3)

### 4. Score Ranges
- Validates scores are in expected ranges
- Flags extreme values
- Detects boundary clustering issues

### 5. Missing Critical Fields
- Checks for optional but important fields:
  - `sector`: Sector information
  - `tech_score`: Technical scores
  - `fund_score`: Fundamental scores
  - `sent_score`: Sentiment scores
  - `rsi`: RSI indicators
  - `return_21d`: 21-day returns

### 6. Data Diversity
- Verifies sector diversity (minimum 3 sectors)
- Checks top/bottom score differentiation
- Identifies excessive concentration

## Validation Results

### Error Level
**Blocks AI generation** (user can override):
- All scores identical
- Extremely low score variance (< 0.001)
- All sector averages identical
- Missing required columns

### Warning Level
**Allows generation but flags issues**:
- Low score variance (< 0.01)
- Low sector variance
- Missing optional fields
- Few stocks (< 10)
- Small sectors (< 3 stocks)
- Boundary clustering

### Pass Level
**All checks passed**:
- Data quality is good
- Scores are properly differentiated
- Sectors show meaningful differences
- Critical fields present

## Usage

### In Dashboard

When generating AI insights in the dashboard:

1. **Validation runs automatically** before generating insights
2. **Results displayed** with color-coded status:
   - ✅ Green: All checks passed
   - ⚠️ Yellow: Warnings detected
   - ❌ Red: Errors detected

3. **Error handling**:
   - If errors found: User must explicitly check box to proceed
   - If warnings found: User can proceed but is informed
   - Validation details available in expandable section

### Example Output

```
### Data Quality Validation

⚠️ Validation PASSED with 2 warning(s). 
AI insights may be generated but quality may be reduced.

**Warnings (recommended to fix):**
1. All 12 sectors have identical average scores (0.000). 
   This indicates a data normalization or calculation issue.
2. Low score variance (std=0.0023). 
   Scores may not be sufficiently differentiated.

**Checks Passed:**
  • Data completeness: ✓
  • Required columns present: ✓
  • Score distribution: 319 unique values ✓
  • Critical fields present: ✓
```

## Integration with AI Prompts

When data quality issues are detected, they are automatically included in the AI prompt context:

```
⚠️ CRITICAL DATA QUALITY ERRORS DETECTED:
  - All 12 sectors have identical average scores (0.000)
  - Score variance is extremely low (std=0.000123)

IMPORTANT: The analysis below may be unreliable due to data quality issues. 
Please verify all conclusions independently and interpret results with extreme caution.
```

This ensures the AI:
1. **Acknowledges** data quality limitations
2. **Cautions** users about reliability
3. **Focuses** on what can be reliably analyzed
4. **Avoids** making strong claims based on poor data

## Common Issues and Solutions

### Issue: All Sector Scores Are 0.000

**Cause**: Data normalization issue or score calculation problem

**Solution**:
1. Check score calculation in `src/analysis/domain_analysis.py`
2. Verify model scores are being properly normalized
3. Check if value/quality scores are defaulting to neutral (50.0)
4. Run `scripts/diagnose_value_quality_scores.py` to investigate

### Issue: Low Score Variance

**Cause**: Scores not properly differentiated

**Solution**:
1. Review score weights in `config/config.yaml`
2. Check if model predictions have sufficient spread
3. Verify value/quality score calculations
4. Run `scripts/analyze_factor_variance.py` to optimize weights

### Issue: Missing Critical Fields

**Cause**: Incomplete data loading or processing

**Solution**:
1. Ensure all data sources are properly loaded
2. Check data pipeline in `src/pipeline.py`
3. Verify fundamental data download: `scripts/download_fundamentals.py`

## Technical Details

### Validation Module

Location: `src/analytics/data_validation.py`

Key Classes:
- `InsightsDataValidator`: Main validation class
- `DataValidationError`: Exception for validation failures

### Integration Points

1. **Dashboard**: `src/app/dashboard/pages/ai_insights.py`
   - Runs validation before generating insights
   - Displays results to user
   - Passes validation context to AI generator

2. **AI Generator**: `src/analytics/ai_insights.py`
   - Receives validation context
   - Includes warnings in prompts
   - Adjusts analysis based on data quality

## Best Practices

1. **Always review validation results** before trusting AI insights
2. **Fix errors** before generating insights (don't override)
3. **Address warnings** when possible for better quality
4. **Use validation** as a diagnostic tool to find data issues
5. **Document** any data quality limitations in your analysis

## Future Enhancements

Potential improvements:
- Historical validation tracking
- Automated data quality fixes
- Validation thresholds configurable per use case
- Integration with data pipeline for proactive validation
- Validation reports saved with insights

---

## See Also

- [AI-powered analysis](ai-insights.md)
- [Data quality tracking](data-quality.md)
- [Data completeness checks](data-completeness-validation.md)
