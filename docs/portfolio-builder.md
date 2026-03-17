# Portfolio Builder

> [← Back to Documentation Index](README.md)

The Portfolio Builder creates personalized stock portfolios based on your investment preferences, risk tolerance, and return objectives.

## Overview

The Portfolio Builder follows a systematic approach:

1. **Vertical Analysis**: Rank stocks within each sector
2. **Horizontal Analysis**: Select across sectors to build diversified portfolio
3. **Optimization**: Adjust weights to meet risk/return targets
4. **AI Analysis**: Generate personalized recommendations

## Investor Profile Parameters

### Risk Parameters

| Parameter | Options | Description |
|-----------|---------|-------------|
| **Risk Tolerance** | Conservative, Moderate, Aggressive | Overall risk appetite |
| **Max Drawdown** | 5% - 40% | Maximum acceptable portfolio loss |
| **Volatility Preference** | Low, Medium, High | Acceptable price swings |

### Return Objectives

| Parameter | Range | Description |
|-----------|-------|-------------|
| **Target Annual Return** | 5% - 30% | Your desired annual return |
| **Min Acceptable Return** | 5% - 20% | Minimum return to consider |
| **Time Horizon** | Short, Medium, Long | Investment timeframe |
| **Holding Period** | 1-36 months | Expected holding duration |

### Portfolio Construction

| Parameter | Range | Description |
|-----------|-------|-------------|
| **Portfolio Size** | 5-20 stocks | Number of holdings |
| **Max Position Weight** | 5% - 30% | Max weight in single stock |
| **Min Position Weight** | 1% - 10% | Min weight per position |
| **Max Sector Weight** | 15% - 50% | Max weight in single sector |

### Quality Filters

| Parameter | Default | Description |
|-----------|---------|-------------|
| **Min Quality Score** | 30 | Minimum quality score (0-100) |
| **Min Value Score** | 20 | Minimum value score (0-100) |
| **Require Profitability** | Yes | Only profitable companies |
| **Max Debt/Equity** | 2.0 | Maximum leverage ratio |

### Style Preferences

| Parameter | Options | Description |
|-----------|---------|-------------|
| **Style Preference** | Value, Blend, Growth | Investment style |
| **Dividend Preference** | Income, Neutral, Growth | Dividend focus |
| **Market Cap** | Large, Mid, Small, All | Company size preference |

## Preset Profiles

### Conservative Profile

```python
InvestorProfile.conservative()
```

| Parameter | Value |
|-----------|-------|
| Risk Tolerance | Conservative |
| Target Return | 8% |
| Max Drawdown | 10% |
| Volatility | Low |
| Time Horizon | Long (12 months) |
| Portfolio Size | 15 stocks |
| Max Position | 10% |
| Max Sector | 25% |
| Min Quality | 50 |
| Style | Value |
| Dividend | Income |

### Moderate Profile

```python
InvestorProfile.moderate()
```

| Parameter | Value |
|-----------|-------|
| Risk Tolerance | Moderate |
| Target Return | 12% |
| Max Drawdown | 15% |
| Volatility | Medium |
| Time Horizon | Medium (6 months) |
| Portfolio Size | 10 stocks |
| Max Position | 15% |
| Max Sector | 35% |
| Min Quality | 30 |
| Style | Blend |
| Dividend | Neutral |

### Aggressive Profile

```python
InvestorProfile.aggressive()
```

| Parameter | Value |
|-----------|-------|
| Risk Tolerance | Aggressive |
| Target Return | 20% |
| Max Drawdown | 25% |
| Volatility | High |
| Time Horizon | Short (3 months) |
| Portfolio Size | 8 stocks |
| Max Position | 20% |
| Max Sector | 40% |
| Min Quality | 20 |
| Style | Growth |
| Dividend | Growth |

## Optimization Process

### 1. Vertical Analysis (Within-Sector)

For each sector:

1. Apply quality/value/profitability filters based on profile
2. Compute composite score with profile-adjusted weights:
   - Model score weight adjusted by risk tolerance
   - Value score weight adjusted by style preference
   - Quality score weight adjusted by time horizon
3. Rank stocks by composite score
4. Select top K candidates per sector

**Score Weight Adjustments:**

| Profile | Model | Value | Quality | Tech |
|---------|-------|-------|---------|------|
| Conservative | 0.30 | 0.25 | 0.30 | 0.15 |
| Moderate | 0.40 | 0.20 | 0.20 | 0.20 |
| Aggressive | 0.50 | 0.15 | 0.10 | 0.25 |

### 2. Horizontal Analysis (Cross-Sector)

1. Combine all sector candidates
2. Apply sector weight constraints
3. Initial score-weighted allocation
4. Optimize based on:
   - Expected return vs target
   - Volatility vs preference
   - Diversification requirements

### 3. Weight Optimization

Based on profile risk tolerance:

- **Conservative**: Reduce weight on high-volatility stocks
- **Moderate**: Balance return and risk
- **Aggressive**: Increase weight on high-return stocks

### 4. Constraint Application

Apply position and sector constraints:

```python
# Cap individual positions
weights = weights.clip(min_position, max_position)

# Cap sector weights
for sector in sectors:
    if sector_weight > max_sector:
        # Redistribute excess
        ...

# Renormalize to sum to 1
weights = weights / weights.sum()
```

## Output Files

The Portfolio Builder creates:

| File | Description |
|------|-------------|
| `optimized_portfolio_{profile}.csv` | Holdings with weights |
| `optimization_result_{profile}.json` | Full metrics and risk assessment |
| `ai_portfolio_analysis_{profile}.md` | AI-generated analysis |

### Portfolio CSV Structure

```csv
ticker,sector,weight,composite_score,value_score,quality_score
AAPL,Technology,0.12,0.85,65,78
MSFT,Technology,0.10,0.82,70,82
JNJ,Healthcare,0.08,0.78,75,85
...
```

### Result JSON Structure

```json
{
  "holdings": [...],
  "metrics": {
    "expected_return": 0.14,
    "volatility": 0.18,
    "sharpe_ratio": 0.78,
    "max_drawdown": -0.12,
    "diversification_score": 0.72
  },
  "sector_allocation": {
    "Technology": 0.30,
    "Healthcare": 0.20,
    ...
  },
  "risk_assessment": {
    "overall_risk_level": "medium",
    "meets_criteria": true,
    "warnings": [],
    "recommendations": []
  },
  "profile": {...}
}
```

## Risk Assessment

The system evaluates portfolio risk against your profile:

### Checks Performed

1. **Expected Return vs Target**: Warns if below minimum
2. **Max Drawdown vs Tolerance**: Warns if exceeds limit
3. **Volatility vs Preference**: Warns if too volatile
4. **Sector Concentration**: Warns if over limit
5. **Position Concentration**: Warns if under-diversified

### Risk Levels

| Level | Criteria |
|-------|----------|
| **Low** | No warnings, conservative profile |
| **Medium** | 0-2 warnings |
| **High** | 3+ warnings |

## Usage

### Dashboard

1. Go to **🎯 Portfolio Builder** page
2. Select a backtest run
3. Choose preset or customize parameters
4. Click **🎯 Build Optimized Portfolio**
5. Review results and AI analysis

### Command Line

```bash
# Use preset profile
python scripts/run_portfolio_optimizer.py --profile moderate

# Custom parameters
python scripts/run_portfolio_optimizer.py \
    --profile custom \
    --risk-tolerance moderate \
    --target-return 0.15 \
    --max-drawdown 0.20 \
    --portfolio-size 12 \
    --max-position 0.12 \
    --max-sector 0.30 \
    --style growth \
    --with-ai

# Analyze specific run
python scripts/run_portfolio_optimizer.py \
    --run-id 20251231_115520_abc123 \
    --profile aggressive \
    --with-ai
```

### Programmatic

```python
from src.analysis.portfolio_optimizer import (
    InvestorProfile,
    PortfolioOptimizer,
    generate_ai_analysis,
)

# Create profile
profile = InvestorProfile(
    risk_tolerance="moderate",
    target_annual_return=0.15,
    max_drawdown_tolerance=0.15,
    portfolio_size=10,
)

# Or use preset
profile = InvestorProfile.moderate()

# Create optimizer
optimizer = PortfolioOptimizer(profile)

# Run optimization
result = optimizer.optimize(
    stocks_df=scores_df,
    price_history=price_df,
    top_k_per_sector=5,
)

# Access results
print(result.holdings)
print(result.metrics)
print(result.risk_assessment)

# Generate AI analysis
ai_analysis = generate_ai_analysis(result)
print(ai_analysis)
```

## Best Practices

### Profile Selection

1. **New Investors**: Start with Conservative profile
2. **Retirement Accounts**: Conservative or Moderate
3. **Growth Accounts**: Moderate or Aggressive
4. **Short-term Trading**: Aggressive with tight stops

### Parameter Tuning

1. **Drawdown Tolerance**: Should match your ability to hold through losses
2. **Portfolio Size**: More stocks = more diversification but harder to track
3. **Sector Limits**: Higher limits = more concentrated bets
4. **Quality Filters**: Higher = fewer but safer stocks

### Interpreting Results

1. **Meets Criteria = True**: Portfolio aligns with your profile
2. **Warnings**: Address these before investing
3. **Recommendations**: Suggestions for improvement
4. **Risk Level**: Overall portfolio risk assessment

## Limitations

1. **Historical Data**: Optimization based on historical returns
2. **No Guarantees**: Past performance doesn't predict future
3. **Model Assumptions**: Assumes normal market conditions
4. **Rebalancing**: Doesn't account for taxes or transaction costs

## Related Documentation

- [Domain Analysis](domain-analysis.md) - Vertical/horizontal analysis details
- [Risk Management](risk-management.md) - Risk metrics and constraints
- [AI Insights](ai-insights.md) - AI analysis capabilities

---

## See Also

- [Risk metrics and position sizing](risk-management.md)
- [Risk-aware allocation](risk-parity.md)
- [Comparison of portfolio methods](portfolio-comparison.md)
- [Sector-based stock selection](domain-analysis.md)
- [Entry point identification](purchase-triggers.md)
