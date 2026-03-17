# Filter Optimization Guide

> [← Back to Documentation Index](README.md)

## Overview

This guide helps you optimize filter thresholds to achieve the right balance between quality and diversification.

## Current Configuration

After analysis, the filters have been adjusted to:

```yaml
filters:
  min_roe: 0.03             # 3% ROE (reduced from 5%)
  min_net_margin: 0.02      # 2% net margin (reduced from 3%)
  max_debt_to_equity: 1.8   # 1.8x debt/equity (increased from 1.5)
```

## Target Pass Rates

- **Too Strict (<10%)**: Not enough candidates, poor diversification
- **Optimal (20-40%)**: Good balance of quality and choice
- **Too Lenient (>50%)**: May include lower quality stocks

## Analyzing Filter Effectiveness

### Run Analysis

```bash
python scripts/analyze_filter_effectiveness.py [--run-id RUN_ID]
```

This will show:
- Current pass rate
- Which filters are causing most failures
- Statistics on failed stocks (ROE, margins, debt)
- Recommended threshold adjustments

### Understanding the Output

**Example Output:**
```
📊 Filter Results:
   Passed: 7/88 (8.0%)
   Failed: 81/88 (92.0%)

🔍 Failure Analysis:
   Filters causing failures:
      roe                : 45 stocks (55.6%)
      net_margin         : 38 stocks (46.9%)
      debt_to_equity     : 12 stocks (14.8%)

   ROE Statistics (failed stocks):
      Median: 0.0250 (2.50%)
      Current threshold: 0.0500 (5.00%)
```

**Interpretation:**
- ROE filter is the main culprit (55.6% of failures)
- Median ROE of failed stocks is 2.5%, but threshold is 5%
- Recommendation: Lower ROE threshold to ~3% to capture median-quality stocks

## Adjusting Filters

### Step 1: Identify the Problem

Run the analysis script to see which filter is most restrictive.

### Step 2: Adjust Thresholds

Edit `config/config.yaml`:

```yaml
filters:
  min_roe: 0.03        # Adjust based on median of failed stocks
  min_net_margin: 0.02 # Adjust based on median of failed stocks
  max_debt_to_equity: 1.8  # Adjust based on median of failed stocks
```

### Step 3: Test Impact

1. Run a new analysis
2. Check Purchase Triggers page
3. Verify pass rate is in 20-40% range
4. Ensure portfolio size reaches target (10 stocks)

## Sector Diversification

### Current Issue

Consumer Cyclical dominates (4/7 stocks = 57%). This is addressed by:

1. **Reduced max_sector_weight**: 35% → 30%
2. **Increased top_k_per_sector**: 5 → 8 (more candidates per sector)
3. **Relaxed filters**: More stocks pass, allowing better sector balance

### Monitoring Sector Balance

Check Purchase Triggers page → Sector Rankings section:
- Look for even distribution across sectors
- No single sector should exceed 30% of portfolio
- Aim for 4-6 sectors represented

## Portfolio Size

### Issue: Only 7 stocks instead of 10

**Causes:**
1. Filters too strict (only 7 pass)
2. Not enough candidates per sector

**Solutions:**
1. Relax filters (done: ROE 5%→3%, Margin 3%→2%, Debt 1.5→1.8)
2. Increase top_k_per_sector (done: 5→8)
3. Verify watchlist has enough stocks

## Quality Score Concerns

### Issue: ORLY has low quality score (46.6) despite high domain score (73.5)

**Analysis:**
- Model score is high (driving domain score)
- Quality score is low (ROE/margins may be below average)
- This is expected with current weighting (Model 40%, Quality 25%)

**Options:**
1. **Increase Quality weight**: Quality 25% → 30%, Model 40% → 35%
2. **Add quality filter**: Minimum quality score threshold
3. **Investigate ORLY**: Check if low quality is justified or data issue

## Recommended Workflow

1. **Run filter analysis**:
   ```bash
   python scripts/analyze_filter_effectiveness.py
   ```

2. **Adjust config** based on recommendations

3. **Run new analysis** with updated filters

4. **Check results**:
   - Pass rate: 20-40%
   - Portfolio size: 10 stocks
   - Sector balance: No sector > 30%
   - Score differentiation: Value/Quality scores vary

5. **Iterate** if needed

## Quick Reference

### Conservative (Stricter)
```yaml
filters:
  min_roe: 0.05
  min_net_margin: 0.03
  max_debt_to_equity: 1.5
```
**Expected pass rate**: 5-15%

### Balanced (Current)
```yaml
filters:
  min_roe: 0.03
  min_net_margin: 0.02
  max_debt_to_equity: 1.8
```
**Expected pass rate**: 20-40%

### Aggressive (Lenient)
```yaml
filters:
  min_roe: 0.0
  min_net_margin: 0.0
  max_debt_to_equity: 2.5
```
**Expected pass rate**: 50-80%

## Related Documentation

- [Purchase Triggers Guide](purchase-triggers.md)
- [Configuration Guide](configuration-cli.md)
- [Download Fundamentals Guide](download-fundamentals-guide.md)

---

## See Also

- [Trigger logic](purchase-triggers.md)
- [Backtesting framework](backtesting.md)
- [Indicator parameters](technical-indicators.md)
