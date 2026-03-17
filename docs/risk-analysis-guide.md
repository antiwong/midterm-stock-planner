# Risk Analysis Guide

> [← Back to Documentation Index](README.md)

Comprehensive guide to the risk analysis tools for portfolio evaluation and recommendation strengthening.

## Quick Start

```bash
# Run all analyses on latest run
python scripts/strengthen_recommendations.py --full

# Run specific analysis
python scripts/comprehensive_risk_analysis.py --run-dir output/run_everything_20260102_160327_

# Stress test scenarios
python scripts/stress_testing.py --run-dir output/run_everything_20260102_160327_

# Apply conscience filters
python scripts/conscience_filter.py --exclude-categories "weapons,tobacco,gambling"
```

---

## 1. Downside & Tail Risk Analysis

**Purpose**: Understand what happens in worst-case scenarios, not just averages.

### Metrics Generated

| Metric | Description | Where to Find |
|--------|-------------|---------------|
| Return Percentiles | Worst 1%, 5%, 10% outcomes | Daily, monthly, quarterly |
| VaR (95%, 99%) | Value at Risk thresholds | Daily basis |
| CVaR / ES | Expected loss when VaR breached | Average of worst outcomes |
| Worst Month | Largest monthly decline | Date identified |
| Worst Quarter | Largest quarterly decline | Date identified |

### Interpretation

```
VaR 95% = -2.5% daily
→ On 5% of trading days, expect loss of 2.5% or more

CVaR 95% = -4.0% daily
→ When VaR is breached, average loss is 4.0%

Worst Month = -18.3% (March 2020)
→ COVID crash impact on portfolio
```

### Risk Tolerance Check

Ask yourself:
- Can I accept a -20% quarter without panicking?
- Can I hold through a 12-24 month recovery?
- Size allocation so capital isn't needed during recovery

---

## 2. Drawdown Duration Analysis

**Purpose**: How long does it take to recover from losses?

### Metrics Generated

| Metric | Description |
|--------|-------------|
| Max Drawdown | Largest peak-to-trough decline |
| Drawdown Date | When max drawdown occurred |
| Current Drawdown | How far below peak now |
| Underwater % | % of time in drawdown |
| Avg Recovery Days | Average time to recover |
| Max Recovery Days | Longest recovery period |

### Example Output

```
📉 DRAWDOWN ANALYSIS:
--------------------------------------------------
Max Drawdown: -64.2% (2022-10-15)
Current Drawdown: -12.3%
Time Underwater: 68% of period

Recovery Statistics:
  Average recovery: 145 days (4.8 months)
  Longest recovery: 387 days (12.9 months)
```

### Interpretation

- High underwater % (>50%) = Strategy spends more time in decline than at peaks
- Long recovery times = Need long investment horizon
- Size position so you don't need capital during recovery window

---

## 3. Scenario & Regime Analysis

**Purpose**: Test if strategy works across different market conditions or is a "one-regime wonder."

### Sub-Period Analysis

Automatically segments backtest into:
- 2020 (COVID Crash & Recovery)
- 2021 (Bull Market)
- 2022 (Rate Hike Crash)
- 2023 (AI Rally)
- 2024 (Current)

### Regime Classification

Markets are classified as:
- **Trend**: Bull (rolling return >5%), Bear (<-5%), Sideways
- **Volatility**: High Vol (>1.2× median), Low Vol (<0.8× median), Normal

### Example Output

```
🔄 REGIME PERFORMANCE:
----------------------------------------------------------------------
Regime                    Days  % Time     Return   Sharpe
----------------------------------------------------------------------
Bull / Low Vol             312   28.5%      45.2%     1.85
Bull / Normal Vol          198   18.1%      22.3%     0.92
Sideways / Normal Vol      234   21.4%       5.1%     0.31
Bear / High Vol            156   14.3%     -18.7%    -0.45
----------------------------------------------------------------------
⚠️  HIGH REGIME DEPENDENCY: Strategy is a 'regime wonder'
```

### Red Flags

- ❌ High returns only in bull + low vol regimes
- ❌ Large negative returns in any regime
- ✅ Positive returns across all regimes

---

## 4. Position-Level Risk Diagnostics

**Purpose**: Identify individual stocks that could blow up the portfolio.

### Risk Flags

| Flag | Trigger | Action |
|------|---------|--------|
| High Weight + Severe Loss | >8% weight AND worst month <-30% | Reduce position or add stop |
| Extreme Volatility | >80% annual volatility | Size down or cap |
| Negative Momentum | >8% weight AND 3mo return <-20% | Review thesis |

### Example Output

```
⚠️  HIGH-RISK POSITION FLAGS:
----------------------------------------------------------------------
  UPST:
    ❌ High weight (12%) with -48% worst month
    ❌ Extreme volatility (95%)
  RIVN:
    ❌ Negative momentum (-32%) in large position
```

### Position Summary Table

```
Ticker   Weight      Vol  Worst Mo   Worst 3Mo    Mom 3Mo
----------------------------------------------------------------------
NVDA       15.0%    48.2%    -25.3%     -35.2%      28.5%
PLTR       12.0%    62.1%    -32.1%     -45.0%      15.2%
...
```

---

## 5. Thematic & Sector Dependence

**Purpose**: Identify hidden concentration in themes or correlated stocks.

### Theme Categories Tracked

| Theme | Example Tickers |
|-------|-----------------|
| Nuclear/Uranium | UEC, LEU, CCJ, SMR |
| Clean Energy/EV | PLUG, ENPH, RIVN, LCID |
| High-Beta Tech/AI | PLTR, UPST, COIN, HOOD |
| Traditional Energy | XOM, CVX, OXY, HAL |

### Concentration Warning

```
🎯 THEMATIC EXPOSURE:
----------------------------------------------------------------------
Theme                      Weight    # Stocks   Status
----------------------------------------------------------------------
Nuclear/Uranium             28.5%          6    ❌ HIGH
High-Beta Tech/AI           18.2%          4    ⚠️ Elevated
Clean Energy/EV              8.5%          3    ✅ OK
----------------------------------------------------------------------
⚠️  CONCENTRATION WARNING: Nuclear/Uranium exceed 30% combined weight
```

### Correlation Clusters

Identifies groups of stocks that move together:
- Correlation >0.70 = "Fake diversification"
- Should reduce redundant positions within clusters

---

## 6. Stress Testing

**Purpose**: Simulate hypothetical crashes and their portfolio impact.

### Predefined Scenarios

| Scenario | Description | Typical Impact |
|----------|-------------|----------------|
| Tech Crash | -30% technology | High-growth portfolios |
| Energy Crash | -40% energy/uranium | Commodity-heavy |
| Rate Spike | Growth stocks crushed | Duration-sensitive |
| Broad Bear | -25% market | All portfolios |
| AI Bubble Pop | -50% AI names | NVDA, PLTR heavy |
| EV Washout | -50% EV/clean energy | Green theme |
| Inflation Surge | Commodities up, growth down | Mixed |

### Example Output

```
📊 SCENARIO IMPACT SUMMARY:
----------------------------------------------------------------------
Scenario                        Impact       Status
----------------------------------------------------------------------
Tech Crash (-30%)               -22.5%       ⚠️ HIGH
Energy Crash (-40%)             -12.3%       ⚠️ MODERATE
AI Bubble Pop                   -35.8%       ❌ SEVERE
----------------------------------------------------------------------
⚡ WORST CASE: AI Bubble Pop
   Portfolio impact: -35.8%
```

### Position Size Reduction

```
📊 IMPACT OF POSITION REDUCTION:
------------------------------------------------------------
Metric                      Original        Reduced
------------------------------------------------------------
Exposure                        100%            50%
Ann. Return                    45.2%          22.6%
Ann. Volatility                62.1%          31.1%
Max Drawdown                  -64.2%         -32.1%
Sharpe Ratio                    0.73           0.73
------------------------------------------------------------
💡 Consider 50% allocation to limit drawdown to -32.1%
```

---

## 7. Conscience Filters

**Purpose**: Exclude stocks that don't align with personal values.

### Available Exclusion Categories

| Category | Description | Example Tickers |
|----------|-------------|-----------------|
| `weapons` | Defense contractors | LMT, RTX, NOC, GD |
| `tobacco` | Tobacco/nicotine | MO, PM, BTI |
| `alcohol` | Spirits/beer | BUD, DEO, STZ |
| `gambling` | Casinos, betting | LVS, WYNN, DKNG |
| `fossil_fuels` | Oil, gas, coal | XOM, CVX, COP |
| `private_prisons` | For-profit prisons | GEO, CXW |
| `predatory_finance` | Payday loans | CURO, OMF |

### Usage

```bash
# Exclude specific categories
python scripts/conscience_filter.py --exclude-categories "weapons,tobacco,gambling"

# Exclude specific sectors
python scripts/conscience_filter.py --exclude-sectors "Energy,Basic Materials"

# Exclude specific tickers
python scripts/conscience_filter.py --exclude-tickers "XOM,CVX,MO,PM"
```

### Filter Impact Report

```
📊 FILTER IMPACT:
--------------------------------------------------
  Original positions:  25
  Excluded positions:   4
  Remaining positions: 21
  Excluded weight:     12.5%

  Excluded holdings:
    XOM      (8.5%): Sector: Energy
    CVX      (3.2%): Sector: Energy
    MO       (0.8%): Category: Tobacco & Nicotine
```

---

## 8. Sizing Recommendations

**Purpose**: Translate risk analysis into practical capital allocation.

### Allocation Framework

Based on max drawdown and recovery time:

| Drawdown Risk | Recovery Risk | Suggested Allocation |
|--------------|---------------|---------------------|
| >60% | Long (>12 mo) | 25% of investable |
| 40-60% | Medium (6-12 mo) | 50% of investable |
| <40% | Short (<6 mo) | 75% of investable |

### By Risk Profile

```
💰 RECOMMENDED ALLOCATION:
--------------------------------------------------
Basis: High drawdown risk (-64%)

  Conservative profile: 12% of investable assets
  Moderate profile:     19% of investable assets
  Aggressive profile:   25% of investable assets

  Remainder should be in safer exposures (broad ETFs, bonds, cash)
```

---

## Putting It All Together

### Complete Analysis Command

```bash
# Run full strengthening analysis
python scripts/strengthen_recommendations.py \
    --full \
    --exclude-sectors "Energy" \
    --exclude-tickers "LMT,RTX" \
    --run-dir output/run_everything_20260102_160327_
```

### Generated Reports

| File | Content |
|------|---------|
| `strengthening_analysis.json` | Combined analysis results |
| `comprehensive_risk_analysis.json` | Tail risk, drawdown, regimes |
| `stress_test_results.json` | Scenario impacts |
| `conscience_filter_report.json` | Exclusions and ESG flags |

### Decision Framework

1. **Review tail risk**: Can you accept the worst 1% outcomes?
2. **Check regime dependency**: Does it work in bear markets?
3. **Flag risky positions**: Any single stock too dangerous?
4. **Verify diversification**: Are holdings truly diversified or correlated?
5. **Apply conscience filters**: Remove stocks that conflict with values
6. **Size appropriately**: Allocate based on your risk tolerance
7. **Document and commit**: Write down rules before acting

---

## Integration with Workflow

The risk analysis integrates into the standard analysis workflow:

```
Full Analysis Workflow
├── Step 1-7: Standard analysis
├── Step 8: Automated Safeguards
└── Step 9: Risk Analysis (--full flag)
    ├── Tail Risk
    ├── Regime Analysis
    ├── Position Diagnostics
    ├── Stress Testing
    ├── Conscience Filters
    └── Sizing Recommendations
```

Run with workflow:
```bash
python scripts/full_analysis_workflow.py \
    --watchlist everything \
    --run-domain-analysis \
    --run-portfolio-optimizer \
    --profile moderate \
    --start-date 2020-01-01 \
    --end-date 2024-12-31
```

Then strengthen:
```bash
python scripts/strengthen_recommendations.py --full
```

---

## Related Documentation

- [Risk Management](risk-management.md) - Core risk metrics, complexity control
- [Backtesting](backtesting.md) - Performance evaluation
- [Macro Indicators](macro-indicators.md) - DXY, VIX, regime analysis
- [Documentation Index](README.md)

---

## See Also

- [Core risk metrics](risk-management.md)
- [Risk parity allocation](risk-parity.md)
- [Performance evaluation](backtesting.md)
- [GARCH volatility modeling](garch-design.md)
