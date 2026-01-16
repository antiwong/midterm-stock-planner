# Turnover & Churn Analysis Guide

Comprehensive guide to understanding portfolio turnover, churn rates, and position holding periods.

## Overview

Turnover & Churn Analysis helps you understand:
- **How often your portfolio changes** (turnover rate)
- **Which positions are frequently traded** (churn analysis)
- **How long you hold positions** (holding period analysis)
- **Portfolio stability** (position stability metrics)

High turnover can indicate:
- Excessive trading costs
- Lack of conviction in positions
- Over-optimization or over-trading
- Strategy drift

Low turnover can indicate:
- Buy-and-hold strategy
- Strong conviction
- Lower transaction costs
- Potential for missed opportunities

---

## Quick Start

### GUI Method (Recommended)

1. **Open Dashboard**
   ```bash
   streamlit run run_dashboard.py
   ```

2. **Navigate to Turnover Analysis**
   - Click **"Turnover & Churn Analysis"** in the sidebar (under Advanced Analytics)

3. **Select Your Run**
   - Use the dropdown to select the run you want to analyze

4. **View Results**
   - The page automatically displays turnover metrics if analysis has been run
   - If not, go to Comprehensive Analysis page and click "Run All Analyses"

### Command-Line Method

Turnover analysis is automatically included when running comprehensive analysis:

```bash
python scripts/run_comprehensive_analysis.py --run-id <run_id>
```

---

## Metrics Explained

### 1. Portfolio Turnover Rate

**What it measures**: How much of your portfolio is traded over a given period.

**Calculation Methods**:

#### Sum of Absolute Changes (Default)
```
Turnover = Σ |New Weight - Old Weight| / 2
```
- Most common method
- Measures total portfolio change
- Example: 25% turnover means 25% of portfolio value was rebalanced

#### One-Way Turnover
- Separates **buys** (increases) from **sells** (decreases)
- Useful for understanding trading direction
- Example: 15% buys + 10% sells = 25% total turnover

#### Two-Way Turnover
```
Turnover = Σ |New Weight - Old Weight|
```
- Counts both buy and sell sides
- Higher than sum-of-abs method
- Example: 25% sum-of-abs = 50% two-way

**Interpretation**:

| Turnover Rate | Interpretation | Typical Strategy |
|--------------|----------------|------------------|
| < 20% | Low turnover | Buy-and-hold, long-term |
| 20-50% | Moderate turnover | Quarterly rebalancing |
| 50-100% | High turnover | Active trading, monthly rebalancing |
| > 100% | Very high turnover | Day trading, high-frequency |

**Annualized Turnover**:
- Converts period turnover to annual rate
- Example: 5% monthly turnover ≈ 60% annual turnover
- Useful for comparing strategies with different rebalancing frequencies

---

### 2. Churn Rate

**What it measures**: How often positions change significantly (not just weight adjustments).

**Calculation**:
```
Churn Rate = (Positions Changed > Threshold) / Total Positions
```

**Parameters**:
- **Threshold**: Minimum weight change to count as "churn" (default: 1%)
- A 0.5% weight change doesn't count, but a 2% change does

**Interpretation**:

| Churn Rate | Interpretation |
|------------|----------------|
| < 10% | Very stable portfolio |
| 10-30% | Moderate position changes |
| 30-50% | Frequent position changes |
| > 50% | Very active portfolio |

**Example**:
```
Portfolio: 20 positions
Period 1: 3 positions changed by >1%
Churn Rate = 3/20 = 15%
```

---

### 3. Holding Period Analysis

**What it measures**: How long you hold positions before selling.

**Metrics**:

| Metric | Description |
|--------|-------------|
| Mean Holding Period | Average days a position is held |
| Median Holding Period | Middle value (less affected by outliers) |
| Min/Max Holding Period | Shortest and longest holdings |
| Distribution | Breakdown by time buckets |

**Time Buckets**:
- **Short-term (0-30 days)**: Day trading, swing trading
- **Medium-term (31-90 days)**: Quarterly rebalancing
- **Long-term (91-180 days)**: Semi-annual rebalancing
- **Very long-term (180+ days)**: Annual or buy-and-hold

**Interpretation**:

| Average Holding Period | Strategy Type |
|------------------------|---------------|
| < 30 days | Day trading, high-frequency |
| 30-90 days | Active trading, monthly rebalancing |
| 90-180 days | Mid-term trading, quarterly rebalancing |
| > 180 days | Long-term investing, buy-and-hold |

**Example**:
```
Mean Holding Period: 45 days
Distribution:
  - Short-term (0-30 days): 20%
  - Medium-term (31-90 days): 60%
  - Long-term (91-180 days): 15%
  - Very long-term (180+ days): 5%

Interpretation: Active trading strategy with quarterly rebalancing
```

---

### 4. Position Stability

**What it measures**: How often your top positions change.

**Metrics**:
- **Stability Score**: 0-1 (1 = completely stable, 0 = constantly changing)
- **Position Changes**: Number of times top N positions changed
- **Average Changes per Period**: How many positions change each rebalance

**Interpretation**:

| Stability Score | Interpretation |
|-----------------|----------------|
| > 0.8 | Very stable core positions |
| 0.6-0.8 | Moderately stable |
| 0.4-0.6 | Frequent changes |
| < 0.4 | Very unstable, constantly changing |

**Example**:
```
Top 10 Positions:
  - Stability Score: 0.75
  - Position Changes: 12 over 20 periods
  - Avg Changes per Period: 0.6

Interpretation: Core positions are relatively stable, 
but 2-3 positions change each rebalance
```

---

## Understanding the Results

### Turnover Statistics

```
Mean Turnover: 25.3%
Median Turnover: 24.1%
Std Deviation: 8.2%
Min Turnover: 12.5%
Max Turnover: 45.8%
Annualized: 303.6%
```

**What this tells you**:
- Average monthly turnover is 25% (moderate)
- Some months have very high turnover (45.8%)
- Annualized turnover of 303% means portfolio turns over ~3x per year
- High standard deviation (8.2%) indicates inconsistent rebalancing

### Churn Analysis

```
Mean Churn Rate: 18.5%
Churned Positions by Period:
  - Period 1: 3 positions
  - Period 2: 5 positions
  - Period 3: 2 positions
```

**What this tells you**:
- On average, 18.5% of positions change significantly each period
- Some periods have more churn than others
- If you have 20 positions, ~3-4 change each period

### Holding Period Distribution

```
Mean: 67 days
Median: 45 days
Distribution:
  - Short-term (0-30 days): 25%
  - Medium-term (31-90 days): 50%
  - Long-term (91-180 days): 20%
  - Very long-term (180+ days): 5%
```

**What this tells you**:
- Most positions are held for 1-3 months (medium-term)
- 25% are very short-term (< 30 days)
- Only 5% are truly long-term holdings
- Strategy is active, not buy-and-hold

---

## Best Practices

### 1. Monitor Turnover vs. Performance

**Question**: Is high turnover generating alpha?

**Check**:
- Compare turnover to excess returns
- Calculate net returns after transaction costs
- If turnover > 100% but alpha < 2%, reconsider strategy

**Rule of Thumb**:
```
Net Alpha = Gross Alpha - (Turnover × Transaction Cost)
If Net Alpha < 0, turnover is hurting performance
```

### 2. Set Turnover Targets

**Conservative Strategy**:
- Target: < 30% annual turnover
- Rebalancing: Quarterly or semi-annually
- Transaction costs: Minimal

**Moderate Strategy**:
- Target: 30-100% annual turnover
- Rebalancing: Monthly or quarterly
- Transaction costs: Moderate

**Active Strategy**:
- Target: > 100% annual turnover
- Rebalancing: Weekly or monthly
- Transaction costs: Significant (must be justified by alpha)

### 3. Analyze Churn by Sector

**Question**: Which sectors are you trading most?

**Check**:
- Sector-level churn rates
- Are you churning tech stocks more than utilities?
- Does this align with your strategy?

**Example**:
```
Technology: 35% churn rate (high)
Utilities: 5% churn rate (low)
Healthcare: 20% churn rate (moderate)

Interpretation: Active trading in tech, stable utilities
```

### 4. Review Holding Periods

**Question**: Are you holding winners or cutting losers too quickly?

**Check**:
- Average holding period for winners vs. losers
- Are you selling winners too early?
- Are you holding losers too long?

**Red Flags**:
- Winners held < 30 days (selling too early)
- Losers held > 180 days (holding too long)
- High short-term turnover (overtrading)

### 5. Position Stability Analysis

**Question**: Is your portfolio core stable?

**Check**:
- Top 10 positions stability score
- How often do your largest positions change?
- Is there a stable core?

**Good Signs**:
- Stability score > 0.7
- Top 5 positions rarely change
- Changes are in smaller positions

**Warning Signs**:
- Stability score < 0.4
- Top positions change every period
- No stable core portfolio

---

## Common Issues & Solutions

### Issue 1: Very High Turnover (> 200% annual)

**Symptoms**:
- High transaction costs eating into returns
- Portfolio constantly changing
- No stable core positions

**Solutions**:
1. **Increase rebalancing threshold**: Only rebalance if drift > 5% (instead of 2%)
2. **Reduce position count**: Fewer positions = less turnover
3. **Use bands instead of fixed weights**: Rebalance only when outside bands
4. **Review strategy**: Is high turnover generating alpha?

### Issue 2: Very Low Turnover (< 10% annual)

**Symptoms**:
- Portfolio drifts significantly
- Missed rebalancing opportunities
- Positions become too concentrated

**Solutions**:
1. **Set minimum rebalancing frequency**: Rebalance at least quarterly
2. **Use drift thresholds**: Rebalance when drift exceeds threshold
3. **Review positions**: Are you holding losers too long?

### Issue 3: Inconsistent Turnover

**Symptoms**:
- High standard deviation in turnover
- Some periods very high, others very low
- Unpredictable trading patterns

**Solutions**:
1. **Standardize rebalancing**: Use fixed schedule (e.g., monthly)
2. **Set clear rules**: Define when to rebalance
3. **Automate decisions**: Remove emotion from rebalancing

### Issue 4: High Churn in Core Positions

**Symptoms**:
- Top positions change frequently
- Low stability score (< 0.5)
- No conviction in largest holdings

**Solutions**:
1. **Separate core and satellite**: Keep core stable, trade satellite
2. **Increase conviction threshold**: Only add to top positions with high confidence
3. **Review selection criteria**: Are you picking the right stocks?

---

## Integration with Other Analyses

### Turnover + Transaction Costs

**Use Case**: Calculate net returns after transaction costs

```
Net Return = Gross Return - (Turnover × Transaction Cost Rate)

Example:
  Gross Return: 12%
  Annual Turnover: 150%
  Transaction Cost: 0.1%
  Net Return = 12% - (150% × 0.1%) = 11.85%
```

### Turnover + Tax Optimization

**Use Case**: Minimize tax impact of high turnover

**Strategy**:
- Hold positions > 1 year for long-term capital gains
- Use tax-loss harvesting for losers
- Minimize short-term trades (< 1 year)

**Check**:
- Average holding period vs. 365 days
- Percentage of positions held > 1 year
- Short-term vs. long-term gains

### Turnover + Performance Attribution

**Use Case**: Understand if turnover is adding value

**Questions**:
- Is high turnover generating alpha?
- Are you trading at the right times?
- Is timing attribution positive?

**Analysis**:
- Compare turnover to timing attribution
- High turnover + positive timing = good
- High turnover + negative timing = bad

---

## Example Workflow

### Step 1: Run Analysis

1. Go to **Comprehensive Analysis** page
2. Select your run
3. Click **"Run All Analyses"**
4. Wait for completion

### Step 2: Review Turnover Metrics

1. Go to **Turnover & Churn Analysis** page
2. Review turnover statistics:
   - Is annual turnover reasonable? (< 100% for most strategies)
   - Is standard deviation low? (consistent rebalancing)
   - Are there outlier periods?

### Step 3: Analyze Churn

1. Review churn rate:
   - Is churn rate stable?
   - Which periods had high churn?
   - Are you churning too many positions?

### Step 4: Check Holding Periods

1. Review holding period distribution:
   - Are you holding positions long enough?
   - Too many short-term trades?
   - Too many long-term positions?

### Step 5: Assess Stability

1. Review position stability:
   - Is your core portfolio stable?
   - Are top positions changing too often?
   - Do you have conviction in your largest holdings?

### Step 6: Take Action

**If turnover is too high**:
- Increase rebalancing threshold
- Reduce position count
- Review strategy

**If turnover is too low**:
- Set minimum rebalancing frequency
- Use drift thresholds
- Review positions

**If churn is high**:
- Review selection criteria
- Increase conviction threshold
- Separate core and satellite

---

## Technical Details

### Calculation Formulas

**Turnover (Sum of Absolute Changes)**:
```
T_t = Σ |w_i,t - w_i,t-1| / 2

Where:
  w_i,t = weight of position i at time t
  T_t = turnover at time t
```

**Churn Rate**:
```
C_t = (Σ I(|w_i,t - w_i,t-1| > threshold)) / N_t

Where:
  I() = indicator function (1 if true, 0 if false)
  N_t = number of positions at time t
  C_t = churn rate at time t
```

**Annualized Turnover**:
```
T_annual = T_period × (365 / days_per_period)

Where:
  T_period = average period turnover
  days_per_period = average days between rebalances
```

### Data Requirements

- **Portfolio Weights**: DataFrame with Date index and Ticker columns
- **Minimum Periods**: At least 2 periods for turnover calculation
- **Weight Format**: Decimal weights (0.05 = 5%), should sum to ~1.0

### Performance Considerations

- **Calculation Time**: < 0.1s for typical portfolios (20-50 positions, 12-24 periods)
- **Memory**: Minimal (only stores summary statistics)
- **Scalability**: Handles portfolios with 100+ positions and 100+ periods

---

## Related Documentation

- **Comprehensive Analysis System**: `docs/comprehensive-analysis-system.md`
- **Running Comprehensive Analysis**: `docs/running-comprehensive-analysis.md`
- **Risk Analysis Guide**: `docs/risk-analysis-guide.md`
- **Rebalancing Analysis**: Part of Comprehensive Analysis

---

## Summary

Turnover & Churn Analysis helps you:
1. **Understand trading frequency**: How often you're rebalancing
2. **Identify overtrading**: High turnover without corresponding alpha
3. **Assess portfolio stability**: Are core positions stable?
4. **Optimize transaction costs**: Balance turnover with costs
5. **Improve strategy**: Use data to refine rebalancing rules

**Key Metrics to Monitor**:
- Annual turnover (target: 30-100% for most strategies)
- Churn rate (target: 10-30% for moderate strategies)
- Average holding period (target: 60-120 days for mid-term)
- Position stability score (target: > 0.7 for stable core)

**Red Flags**:
- Turnover > 200% without corresponding alpha
- Churn rate > 50%
- Stability score < 0.4
- Very short average holding period (< 30 days)
