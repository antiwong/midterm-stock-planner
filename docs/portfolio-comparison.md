# Portfolio Generation Methods Comparison

## Overview

This document compares two different portfolio generation approaches in the Mid-term Stock Planner:

1. **Purchase Triggers** - Rule-based selection with domain scoring
2. **Portfolio Builder** - Optimization-based selection with risk targeting

## Methodology Comparison

### Purchase Triggers Approach

**Scoring System:**
- **Domain Score Formula**: `(49% × Model) + (20% × Value) + (31% × Quality)`
- **Model Score**: ML prediction of 3-month excess return (0-100 scale)
- **Value Score**: PE/PB ranking (0-100 scale)
- **Quality Score**: ROE/margins ranking (0-100 scale)

**Selection Process:**
1. **Hard Filters**: Min ROE=0.03, Min Net Margin=0.02, Max Debt/Equity=1.8
2. **Vertical Analysis**: Top K stocks per sector (default: 5-8)
3. **Horizontal Analysis**: Top N overall (default: 10)
4. **Weighting**: Score-weighted (domain scores normalized to sum to 100%)

**Constraints:**
- Max position weight: 15%
- Max sector weight: 30-35%
- Portfolio size: 10 stocks

### Portfolio Builder Approach

**Scoring System:**
- **Primary Score**: Raw model prediction (0-1 scale, not normalized to 0-100)
- **Tech Score**: Technical indicators (appears to be maxed at 100.0 in this run)
- **Fund Score**: Fundamental metrics (mostly 50.0 default, except DIS=69.8)
- **Sent Score**: Sentiment analysis (50.0 default)

**Selection Process:**
1. **Profile-Based Filters**: Risk tolerance, quality thresholds, style preferences
2. **Vertical Analysis**: Top K per sector (configurable)
3. **Optimization**: Weight optimization to meet risk/return targets
4. **Weighting**: Optimized weights (not simply score-weighted)

**Constraints:**
- Risk tolerance: Conservative/Moderate/Aggressive
- Target return: User-defined (e.g., 12% annual)
- Max drawdown: User-defined (e.g., 15%)
- Portfolio size: Configurable (default: 10)

## Portfolio Comparison: Purchase Triggers vs Portfolio Builder

### Purchase Triggers Portfolio (from commentary)

**Characteristics:**
- **Size**: 10 stocks
- **Sectors**: 6 sectors represented
- **Top Stocks**: BAC (74.7), XLP, JPM, ICLN, TAN, etc.
- **Domain Scores**: Range 60.2-74.7
- **Average Domain Score**: 67.7
- **Issues Identified**:
  - 3 positions in "ETF - Other" sector (30% concentration)
  - Limited diversification
  - Sector concentration in Financial Services, Basic Materials, ETFs

**Strengths:**
- Balanced scoring (Model + Value + Quality)
- Clear filter-based quality screening
- Transparent selection process

**Weaknesses:**
- ETF bias (filters favor ETFs)
- Sector concentration risk
- Simple score-weighting may not optimize risk/return

### Portfolio Builder Portfolio (from optimized_portfolio_moderate.csv)

**Characteristics:**
- **Size**: 10 stocks
- **Sectors**: 7 sectors represented
- **Top Stocks**: PLUG (0.374), K (0.339), SMCI (0.284), XPEV (0.124), RUN (0.117), etc.
- **Model Scores**: Range 0.045-0.374 (raw predictions, mean=0.164)
- **Weights**: Range 8.2%-13.2% (mean=10.0%, std=1.8% - very balanced)
- **Sector Distribution**:
  - Technology: 3 stocks (30% - SMCI, RUN, SEDG)
  - Communication Services: 2 stocks (20% - DIS, WBD)
  - Industrials: 1 stock (13.2% - PLUG, largest position)
  - Consumer Defensive: 1 stock (12.6% - K, second largest)
  - Consumer Cyclical: 1 stock (9.4% - XPEV)
  - Basic Materials: 1 stock (9.1% - BTG)
  - Energy: 1 stock (8.2% - LEU, smallest position)

**Strengths:**
- Better sector diversification (7 sectors vs 6)
- Optimized weights (not just score-weighted)
- No ETF bias (all individual stocks)
- More balanced position sizing

**Weaknesses:**
- All tech_scores maxed at 100.0 (potential data issue)
- Most fund_scores at 50.0 default (fundamental data missing)
- Lower overall scores (raw model predictions vs normalized domain scores)

## Key Differences

### 1. Scoring Methodology

| Aspect | Purchase Triggers | Portfolio Builder |
|--------|------------------|-------------------|
| **Score Scale** | 0-100 (normalized) | 0-1 (raw predictions) |
| **Score Components** | Model 49%, Value 20%, Quality 31% | Model-focused, tech/fund/sent scores |
| **Value Integration** | Explicit 20% weight | Implicit (if available) |
| **Quality Integration** | Explicit 31% weight | Implicit (if available) |

### 2. Selection Process

| Aspect | Purchase Triggers | Portfolio Builder |
|--------|------------------|-------------------|
| **Filter Approach** | Hard filters (ROE, margins, debt) | Profile-based filters (risk, quality thresholds) |
| **Vertical Analysis** | Top K per sector | Top K per sector |
| **Horizontal Analysis** | Top N overall | Top N overall |
| **Weight Calculation** | Score-weighted (simple) | Optimized (risk/return targeting) |

### 3. Portfolio Characteristics

| Aspect | Purchase Triggers | Portfolio Builder |
|--------|------------------|-------------------|
| **Diversification** | 6 sectors, ETF bias | 7 sectors, no ETFs |
| **Position Sizing** | Score-weighted (can be concentrated) | Optimized (more balanced) |
| **Risk Management** | Implicit (via filters) | Explicit (risk tolerance, drawdown limits) |
| **Return Targeting** | Not explicit | Target return specified |

### 4. Data Quality Issues

**Purchase Triggers:**
- Quality scores at 50.0 for many stocks (data limitation)
- Value scores variable (some differentiation)

**Portfolio Builder:**
- All tech_scores at 100.0 (likely data normalization issue)
- Most fund_scores at 50.0 (fundamental data missing)
- Only DIS has fund_score=69.8 (has PE/PB data)

## Recommendations

### For Purchase Triggers

1. **Address ETF Bias**: Review filters to ensure they don't favor ETFs
2. **Improve Sector Diversification**: Add max sector weight constraints
3. **Enhance Weighting**: Consider optimization instead of simple score-weighting
4. **Fix Quality Scores**: Investigate why many stocks have Quality=50.0

### For Portfolio Builder

1. **Fix Tech Score Normalization**: Investigate why all tech_scores are 100.0
2. **Improve Fundamental Data**: Download comprehensive fundamentals to enable fund_score differentiation
3. **Integrate Value/Quality**: Consider adding explicit Value and Quality components to scoring
4. **Risk-Adjusted Selection**: Already good, but could add more constraints

### Hybrid Approach (Recommended)

Combine the best of both:

1. **Use Purchase Triggers scoring** (Model + Value + Quality) for stock ranking
2. **Use Portfolio Builder optimization** for weight allocation
3. **Apply both filter systems** (hard filters + profile-based filters)
4. **Explicit sector diversification** constraints from Portfolio Builder
5. **Risk targeting** from Portfolio Builder

## Detailed Analysis

### Weight Distribution Comparison

**Purchase Triggers:**
- Weighting: Score-weighted (domain scores normalized)
- Distribution: Likely more concentrated (top stocks get higher weights)
- Risk: Higher concentration risk if top stocks are similar

**Portfolio Builder:**
- Weighting: Optimized (mean=10.0%, std=1.8%)
- Distribution: Very balanced (8.2%-13.2% range)
- Risk: Lower concentration risk, better diversification

### Sector Concentration

**Purchase Triggers:**
- 6 sectors, but 30% in "ETF - Other" (3 positions)
- Potential bias toward ETFs
- Limited individual stock diversification

**Portfolio Builder:**
- 7 sectors, no ETFs
- Technology sector has 3 stocks (30%), but all individual stocks
- Better sector balance across different industries
- No single sector dominates excessively

### Stock Quality

**Purchase Triggers:**
- Higher domain scores (60-75 range)
- Explicit Value and Quality components
- But: Quality scores at 50.0 for many stocks (data issue)

**Portfolio Builder:**
- Lower raw scores (0.045-0.374 range)
- All tech_scores maxed at 100.0 (normalization issue)
- Most fund_scores at 50.0 default (missing data)
- Only DIS has real fundamental data (fund_score=69.8)

### Risk Characteristics

**Purchase Triggers:**
- Implicit risk management via filters
- No explicit risk targeting
- Score-weighted may not optimize Sharpe ratio

**Portfolio Builder:**
- Explicit risk tolerance (moderate profile)
- Target return and max drawdown constraints
- Optimized weights likely improve risk-adjusted returns

## Conclusion

**Purchase Triggers** provides:
- ✅ Better fundamental integration (Value + Quality scores)
- ✅ Transparent, rule-based selection
- ✅ Higher overall scores (better stock quality)
- ❌ ETF bias and sector concentration
- ❌ Simple weighting may not optimize risk/return
- ❌ Quality score data issues (many at 50.0)

**Portfolio Builder** provides:
- ✅ Better diversification (no ETF bias, 7 sectors)
- ✅ Optimized weights (very balanced 8-13% range)
- ✅ Explicit risk management (risk tolerance, drawdown limits)
- ✅ Better sector balance
- ❌ Missing fundamental data (fund_scores defaulting to 50.0)
- ❌ Tech score normalization issues (all at 100.0)
- ❌ Lower raw scores (but may be due to different scale)

**Best Practice**: 
1. Use **Purchase Triggers** for stock selection (better scoring with Value + Quality)
2. Apply **Portfolio Builder optimization** for weight allocation (better risk management)
3. Fix data quality issues in both systems (fundamental data, score normalization)
4. Consider a hybrid approach that combines both methodologies
