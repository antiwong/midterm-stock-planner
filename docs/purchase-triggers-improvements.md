# Purchase Triggers Improvements

## Overview

This document details the improvements made to the purchase triggers system based on AI analysis recommendations. These changes address issues with filter effectiveness, score differentiation, and portfolio diversification.

## Issues Identified

### 1. Filter Effectiveness
- **Problem**: All stocks passing filters (100% pass rate)
- **Root Cause**: Filters set to 0.0 (too lenient)
- **Impact**: No quality screening, all stocks considered

### 2. Score Distribution
- **Problem**: Value and Quality scores all at 50.0 (no differentiation)
- **Root Cause**: 
  - Column name mismatches (fundamentals.csv uses `pe`/`pb`, code expects `pe_ratio`/`pb_ratio`)
  - Missing fundamental data (ROE, margins not in data)
- **Impact**: Model score dominates selection (50% weight), fundamentals ignored

### 3. Model Dominance
- **Problem**: Model score weight too high (50%)
- **Impact**: Selection driven primarily by ML predictions, ignoring value/quality

### 4. Sector Concentration
- **Problem**: Technology and Consumer Cyclical overrepresented
- **Impact**: Lack of diversification, sector-specific risk

## Improvements Implemented

### 1. Enhanced Column Name Handling ✅

**Location**: `src/analysis/domain_analysis.py`

**Changes**:
- Added `_normalize_column_names()` method to handle column name variations
- Supports multiple naming conventions:
  - PE: `pe`, `pe_ratio`, `price_to_earnings`
  - PB: `pb`, `pb_ratio`, `price_to_book`
  - ROE: `roe`, `return_on_equity`, `roe_ratio`
  - Margins: `net_margin`, `net_margin_pct`, `profit_margin`, etc.

**Impact**: Value and Quality scores now work even with different column names

### 2. Improved Value/Quality Score Calculation ✅

**Location**: `src/analysis/domain_analysis.py`

**Changes**:
- Better handling of missing data
- Outlier filtering (PE < 1000, PB < 100, ROE between -100% and 1000%)
- Requires at least 2 valid values to calculate meaningful ranks
- Warning messages when fundamental data is missing

**Impact**: More accurate and differentiated value/quality scores

### 3. Stricter Default Filters ✅

**Location**: `config/config.yaml`

**Before**:
```yaml
filters:
  min_roe: 0.0              # No filter
  min_net_margin: 0.0       # No filter
  max_debt_to_equity: 2.0   # Very lenient
```

**After**:
```yaml
filters:
  min_roe: 0.05             # 5% ROE threshold
  min_net_margin: 0.03      # 3% margin threshold
  max_debt_to_equity: 1.5   # Tighter leverage control
```

**Impact**: 
- Filters out unprofitable companies
- Requires basic profitability (5% ROE, 3% margin)
- Reduces leverage risk (max 1.5x debt/equity)

### 4. Balanced Score Weights ✅

**Location**: `config/config.yaml`

**Before**:
```yaml
weights:
  model_score: 0.5    # 50% - dominates selection
  value_score: 0.3    # 30%
  quality_score: 0.2  # 20%
```

**After**:
```yaml
weights:
  model_score: 0.40   # 40% - reduced dominance
  value_score: 0.35   # 35% - increased influence
  quality_score: 0.25 # 25% - increased influence
```

**Impact**:
- More balanced selection (fundamentals now 60% vs 50% before)
- Model still important but doesn't dominate
- Value and quality have meaningful influence

### 5. Column Name Mapping in GUI ✅

**Location**: `src/app/dashboard/pages/purchase_triggers.py`

**Changes**:
- Automatically maps `pe` → `pe_ratio`, `pb` → `pb_ratio` when loading fundamentals
- Ensures compatibility with different data formats

**Impact**: GUI correctly displays value/quality scores

### 6. Configuration Improvement Script ✅

**Location**: `scripts/improve_purchase_triggers.py`

**Features**:
- Analyzes current configuration
- Identifies issues
- Provides recommendations
- Can apply improvements automatically

**Usage**:
```bash
# Analyze current config
python scripts/improve_purchase_triggers.py

# Apply improvements
python scripts/improve_purchase_triggers.py --apply
```

## Expected Results

### Before Improvements
- **Filter Pass Rate**: 100% (all stocks pass)
- **Value Scores**: All 50.0 (no differentiation)
- **Quality Scores**: All 50.0 (no differentiation)
- **Selection**: Driven 50% by model, 50% by fundamentals (but fundamentals don't differentiate)
- **Effective Selection**: 100% model-driven

### After Improvements
- **Filter Pass Rate**: ~30-70% (realistic screening)
- **Value Scores**: 0-100 range (meaningful differentiation)
- **Quality Scores**: 0-100 range (meaningful differentiation)
- **Selection**: 40% model, 35% value, 25% quality (balanced)
- **Effective Selection**: Balanced across all three components

## Verification Steps

1. **Check Filter Status**:
   - Run new analysis
   - Check Purchase Triggers page
   - Verify pass rate is 30-70% (not 100%)

2. **Check Score Differentiation**:
   - View Sector Rankings
   - Verify Value and Quality scores vary (not all 50.0)
   - Check score breakdown charts show variation

3. **Check Weight Balance**:
   - View Configuration section
   - Verify weights: 40%/35%/25%
   - Check that top stocks have balanced scores

4. **Check Portfolio Diversification**:
   - View Portfolio Estimate
   - Verify multiple sectors represented
   - Check no single sector > 35%

## Customization

### Adjust Filter Strictness

For **stricter** filters (higher quality focus):
```yaml
filters:
  min_roe: 0.10        # 10% ROE
  min_net_margin: 0.05 # 5% margin
  max_debt_to_equity: 1.0  # Very low leverage
```

For **lenient** filters (more opportunities):
```yaml
filters:
  min_roe: 0.0         # Any profitability
  min_net_margin: 0.0  # Any margin
  max_debt_to_equity: 2.0  # Higher leverage OK
```

### Adjust Score Weights

For **value-focused** selection:
```yaml
weights:
  model_score: 0.30
  value_score: 0.50
  quality_score: 0.20
```

For **quality-focused** selection:
```yaml
weights:
  model_score: 0.30
  value_score: 0.20
  quality_score: 0.50
```

For **model-focused** selection (original):
```yaml
weights:
  model_score: 0.50
  value_score: 0.30
  quality_score: 0.20
```

## Troubleshooting

### Value/Quality Scores Still All 50.0

**Check**:
1. Does `data/fundamentals.csv` exist?
2. Does it have `pe`, `pb`, `roe`, `net_margin` columns?
3. Are the values populated (not all NaN)?

**Solution**:
```bash
# Download/update fundamentals
python scripts/download_prices.py --fundamentals

# Or fetch from API
python scripts/fetch_sector_data.py
```

### Filters Too Strict (Low Pass Rate)

**Check**: Current filter values in config

**Solution**: Relax filters slightly:
```yaml
filters:
  min_roe: 0.03        # Lower from 0.05
  min_net_margin: 0.02  # Lower from 0.03
```

### Filters Too Lenient (High Pass Rate)

**Check**: Current filter values in config

**Solution**: Tighten filters:
```yaml
filters:
  min_roe: 0.10         # Higher from 0.05
  min_net_margin: 0.05  # Higher from 0.03
  max_debt_to_equity: 1.0  # Lower from 1.5
```

## Next Steps

1. **Run New Analysis**: Create a new run with improved configuration
2. **Compare Results**: Use "Compare Runs" to see impact of changes
3. **Review AI Commentary**: Generate new AI commentary to see if issues are resolved
4. **Iterate**: Adjust weights/filters based on results

## Related Documentation

- [Purchase Triggers Guide](purchase-triggers.md) - How to read and analyze triggers
- [Domain Analysis](domain-analysis.md) - Vertical/horizontal analysis details
- [Configuration Guide](configuration-cli.md) - Config file reference
