# Purchase Triggers Guide

> [← Back to Documentation Index](README.md)

## Overview

The Purchase Triggers system displays **why stocks were selected or excluded** from portfolios. You can access this information through:

1. **GUI Dashboard** (Recommended): Interactive web interface with visualizations
2. **CLI Script**: Command-line tool for quick analysis

Both show:

- ✅ **Hard filter status**: Which stocks passed/failed profitability, leverage, and liquidity filters
- 📊 **Domain score breakdown**: Model score (50%), Value score (30%), Quality score (20%)
- 🏢 **Sector rankings**: Top candidates within each sector
- 🎯 **Final portfolio estimate**: Which stocks would be selected based on current configuration

## Quick Start

```bash
# Show purchase triggers for latest run
python scripts/show_purchase_triggers.py

# Show triggers for specific run
python scripts/show_purchase_triggers.py --run-id 20260102_165833_82e7b997

# Filter by sector
python scripts/show_purchase_triggers.py --sector Technology

# Show top 30 stocks
python scripts/show_purchase_triggers.py --top-n 30

# Show all stocks including failed filters
python scripts/show_purchase_triggers.py --show-all
```

## Understanding the Output

### 1. Configuration Section

Shows the current trigger weights and filters:

```
Domain Score Weights:
  • Model Score:   50%  ← ML prediction weight
  • Value Score:   30%  ← Valuation (PE/PB) weight
  • Quality Score: 20%  ← Profitability (ROE/margins) weight

Hard Filters:
  • Min ROE:          0.0
  • Min Net Margin:   0.0
  • Max Debt/Equity:  2.0
```

### 2. Filter Status

Shows how many stocks passed/failed the hard filters:

```
✅ Passed Filters: 88 stocks
❌ Failed Filters: 0 stocks
```

### 3. Sector Rankings

For each sector, shows top candidates with:
- **Rank**: Position within sector
- **Domain Score**: Composite score (0-100)
- **Model/Value/Quality**: Component scores
- **Status**: ✅ SELECTED (top K) or ⏳ CANDIDATE

```
📊 Technology (Top 5 of 25 candidates)
Rank   Ticker     Domain    Model    Value  Quality Status    
1      AAPL           85.2 🟢       95.5 🟢       80.0 🟢       75.0 🟢 ✅ SELECTED
```

### 4. Overall Top Stocks

Shows the best stocks across all sectors, ranked by domain score.

### 5. Portfolio Selection Estimate

Shows which stocks would be in the final portfolio based on:
- Vertical selection (top K per sector)
- Horizontal selection (top N overall)
- Estimated weights (score-weighted)

## Purchase Trigger Formula

Stocks are ranked using a **composite domain score**:

```
domain_score = (0.5 × model_score) + (0.3 × value_score) + (0.2 × quality_score)
```

Where:
- **Model Score**: ML prediction of 3-month excess return (percentile rank 0-100)
- **Value Score**: PE/PB ranking (lower PE/PB = higher score, 0-100)
- **Quality Score**: ROE and margins ranking (higher = better, 0-100)

## Hard Filters

Before ranking, stocks must pass these filters:

| Filter | Default | Description |
|--------|---------|-------------|
| `min_roe` | 0.0 | Minimum Return on Equity (0 = profitable) |
| `min_net_margin` | 0.0 | Minimum net profit margin |
| `max_debt_to_equity` | 2.0 | Maximum debt-to-equity ratio |
| `min_market_cap` | None | Minimum market capitalization (optional) |
| `min_avg_volume` | None | Minimum average daily volume (optional) |

## Selection Process

1. **Vertical Analysis**: Top K stocks per sector (default: 5)
2. **Horizontal Analysis**: Top N overall (default: 10)
3. **Constraints Applied**:
   - Max position weight: 15%
   - Max sector weight: 35%
   - Min diversification: 0.70

## Customizing Triggers

Edit `config/config.yaml`:

```yaml
analysis:
  weights:
    model_score: 0.5    # Increase for more ML-driven selection
    value_score: 0.3    # Increase for more value-focused
    quality_score: 0.2  # Increase for more quality-focused
  
  filters:
    min_roe: 0.10       # Stricter: require 10% ROE
    min_net_margin: 0.05  # Stricter: require 5% margin
    max_debt_to_equity: 1.5  # Stricter: lower debt tolerance
  
  vertical:
    top_k_per_sector: 5  # More candidates = more options
  
  horizontal:
    portfolio_size: 10  # Final portfolio size
```

## Score Color Coding

- 🟢 **Green**: Score ≥ 80 (excellent)
- 🟡 **Yellow**: Score 60-79 (good)
- 🟠 **Orange**: Score 40-59 (fair)
- 🔴 **Red**: Score < 40 (poor)

## Examples

### Find why a specific stock wasn't selected

```bash
python scripts/show_purchase_triggers.py | grep -A 5 "TSLA"
```

### Compare sectors

```bash
python scripts/show_purchase_triggers.py --sector Technology
python scripts/show_purchase_triggers.py --sector Healthcare
```

### See failed filters

```bash
python scripts/show_purchase_triggers.py --show-all | grep "FAIL"
```

## Integration with Other Scripts

This script complements:

- `full_analysis_workflow.py`: Run complete analysis, then check triggers
- `run_domain_analysis.py`: See detailed vertical/horizontal analysis
- `analyze_portfolio.py`: Enrich portfolio with risk metrics

## Troubleshooting

**No runs found**: Run a backtest first:
```bash
python -m src.app.cli run-backtest
```

**No fundamentals data**: Value/quality scores will be limited. Download fundamentals:
```bash
python scripts/download_prices.py --fundamentals
```

**Duplicate tickers**: The script handles duplicates automatically by keeping the first occurrence.

---

# GUI Dashboard Guide: Reading Purchase Triggers

## Accessing the Purchase Triggers Page

1. **Start the Dashboard**:
   ```bash
   streamlit run src/app/dashboard/app.py
   ```

2. **Navigate to Purchase Triggers**:
   - Open the sidebar (left panel)
   - Click on **"🔍 Purchase Triggers"** in the navigation menu

3. **Select a Run**:
   - Use the dropdown at the top to select an analysis run
   - The page will automatically load data for the selected run

## Understanding the Page Layout

The Purchase Triggers page is organized into **7 main sections**:

### 1. ⚙️ Configuration Section

**Location**: Top of the page, after run selection

**What it shows**:
- **Domain Score Weights**: How much each component contributes
  - Model Score: ML prediction weight (default: 50%)
  - Value Score: Valuation weight (default: 30%)
  - Quality Score: Profitability weight (default: 20%)
- **Hard Filters**: Minimum requirements stocks must meet
  - Min ROE, Min Net Margin, Max Debt/Equity
- **Selection Settings**: Portfolio construction parameters
  - Top K per sector, Portfolio size, Max position weight

**How to read it**:
- **Higher Model Score weight** = More reliance on ML predictions
- **Higher Value Score weight** = More focus on cheap stocks (low PE/PB)
- **Higher Quality Score weight** = More focus on profitable companies
- **Stricter filters** = Fewer stocks will pass (higher quality threshold)

**Example interpretation**:
```
Model Score: 50%  → Balanced approach between ML and fundamentals
Value Score: 30%  → Moderate emphasis on valuation
Quality Score: 20% → Some focus on profitability
```
This configuration favors stocks with strong ML predictions while still considering value and quality.

---

### 2. 🔍 Filter Status Section

**Location**: Below configuration

**What it shows**:
- **✅ Passed Filters**: Count of stocks that met all requirements
- **❌ Failed Filters**: Count of stocks that failed at least one filter

**How to read it**:
- **High pass rate (80%+)** = Filters are lenient, many stocks qualify
- **Low pass rate (<50%)** = Filters are strict, only high-quality stocks pass
- **Very low pass rate (<20%)** = Filters may be too strict, consider relaxing

**What to look for**:
- **Balance**: You want enough stocks to choose from (30-70% pass rate is ideal)
- **Quality**: If pass rate is too high, filters may not be filtering effectively
- **Opportunity**: If pass rate is too low, you may be missing good opportunities

**Example interpretation**:
```
✅ Passed: 88 stocks
❌ Failed: 0 stocks
```
This suggests filters are very lenient (or no filters are active). All stocks passed, so filtering isn't restricting the universe.

---

### 3. 📊 Sector Rankings Section

**Location**: Below filter status

**What it shows**:
- **Sector dropdown**: Filter to view specific sectors
- **Per-sector tables**: Top candidates within each sector
- **Score breakdown charts**: Visual comparison of component scores

**How to read the table**:

| Column | Meaning | How to Interpret |
|--------|---------|------------------|
| **Rank** | Position within sector | Lower = better (1 is best) |
| **Ticker** | Stock symbol | The stock being evaluated |
| **Domain Score** | Composite score (0-100) | Higher = better overall selection |
| **Model Score** | ML prediction rank (0-100) | Higher = better predicted returns |
| **Value Score** | Valuation rank (0-100) | Higher = cheaper (better value) |
| **Quality Score** | Profitability rank (0-100) | Higher = more profitable |
| **Status** | Selection status | ✅ SELECTED = In top K, ⏳ CANDIDATE = Not selected |

**Color coding**:
- **🟢 Green background**: Score ≥ 80 (excellent)
- **🟡 Yellow background**: Score 60-79 (good)
- **🟠 Orange background**: Score 40-59 (fair)
- **🔴 Red background**: Score < 40 (poor)

**How to analyze**:
1. **Check top stocks**: Look at Rank 1-3 in each sector
2. **Compare scores**: Stocks with high domain scores across all components are strongest
3. **Identify patterns**: Do top stocks have high model scores? High value scores? High quality scores?
4. **Sector balance**: Are some sectors dominating? Are others underrepresented?

**Example interpretation**:
```
Rank  Ticker  Domain  Model  Value  Quality  Status
1     AAPL    85.2    95.5   80.0   75.0     ✅ SELECTED
2     MSFT    78.3    88.2   70.0   65.0     ✅ SELECTED
```

**Analysis**:
- AAPL has excellent scores across all dimensions (all green)
- Strong model prediction (95.5) suggests ML expects good returns
- Good value (80.0) means it's reasonably priced
- High quality (75.0) indicates strong profitability
- This is a well-rounded pick

**Score Breakdown Chart**:
- **Bar chart** showing Model, Value, and Quality scores side-by-side
- **Taller bars** = Higher scores
- **Compare across stocks** to see which component drives selection
- **Balanced bars** = Well-rounded stock
- **One tall bar** = Stock excels in one area

---

### 4. 🏆 Overall Top Stocks Section

**Location**: Below sector rankings

**What it shows**:
- **Slider**: Adjust how many top stocks to display (10-50)
- **Scatter plot**: Domain Score vs Model Score visualization
- **Data table**: Complete ranking of best stocks across all sectors

**How to read the scatter plot**:
- **X-axis**: Domain Score (composite)
- **Y-axis**: Model Score (ML prediction)
- **Bubble size**: Represents domain score (larger = better)
- **Color**: Domain score gradient (darker = better)
- **Stock labels**: Ticker symbols on each point

**What to look for**:
- **Top-right quadrant**: High domain score AND high model score = Best picks
- **Clusters**: Groups of stocks with similar scores
- **Outliers**: Stocks that stand out (very high or very low)
- **Correlation**: Do high domain scores correlate with high model scores?

**How to read the table**:
- **Rank**: Overall position (1 = best stock)
- **Ticker**: Stock symbol
- **Sector**: Which sector the stock belongs to
- **Scores**: All component scores for comparison

**Example interpretation**:
```
Rank  Ticker  Sector        Domain  Model  Value  Quality
1     AAPL    Technology    85.2    95.5   80.0   75.0
2     MSFT    Technology    78.3    88.2   70.0   65.0
3     GOOGL   Technology    75.1    82.5   68.0   72.0
```

**Analysis**:
- Technology sector dominates top 3
- All have strong model scores (ML expects good returns)
- Domain scores are competitive (75-85 range)
- Consider sector diversification if building a portfolio

---

### 5. 🎯 Portfolio Selection Estimate Section

**Location**: Below overall top stocks

**What it shows**:
- **Estimated portfolio**: Which stocks would be selected
- **Portfolio table**: Rank, ticker, sector, domain score, estimated weight
- **Pie chart**: Visual weight distribution

**How to read the portfolio table**:
- **Rank**: Position in final portfolio
- **Ticker**: Selected stock
- **Sector**: Sector allocation
- **Domain Score**: Why it was selected
- **Est. Weight**: Estimated allocation percentage

**How to read the pie chart**:
- **Each slice**: Represents one stock
- **Slice size**: Proportional to estimated weight
- **Colors**: Different colors for visual distinction
- **Labels**: Ticker symbols with percentages

**What to check**:
1. **Sector diversification**: Are multiple sectors represented?
2. **Weight distribution**: Are weights balanced or concentrated?
3. **Top holdings**: Which stocks get the largest allocations?
4. **Domain scores**: Do selected stocks have consistently high scores?

**Example interpretation**:
```
Rank  Ticker  Sector        Domain  Est. Weight
1     AAPL    Technology    85.2    12.5%
2     MSFT    Technology    78.3    11.2%
3     JNJ     Healthcare    76.8    10.8%
```

**Analysis**:
- Technology has 2 stocks (23.7% combined)
- Healthcare represented (10.8%)
- Weights are relatively balanced (10-12% range)
- All have strong domain scores (75+)

**Red flags to watch for**:
- **Single sector dominance**: One sector > 50% of portfolio
- **Concentrated weights**: One stock > 20% of portfolio
- **Low domain scores**: Selected stocks with scores < 60
- **Missing sectors**: Important sectors not represented

---

### 6. 🤖 AI Commentary Section

**Location**: Bottom of the page

**What it shows**:
- **Generate button**: Create AI-powered analysis
- **Commentary display**: AI-generated insights in markdown
- **Download button**: Save commentary as markdown file

**How to use it**:

1. **Check AI availability**:
   - If you see "AI commentary requires Gemini API key", configure API key in Settings
   - If button is available, AI is ready to use

2. **Generate commentary**:
   - Click "🚀 Generate AI Commentary"
   - Wait for generation (takes 10-30 seconds)
   - Commentary appears below

3. **Read the commentary**:
   - **Filter Effectiveness**: Analysis of pass/fail rates
   - **Score Distribution**: Patterns in scoring
   - **Sector Insights**: Sector representation and biases
   - **Top Stock Analysis**: Common characteristics of winners
   - **Portfolio Composition**: Diversification assessment
   - **Recommendations**: Suggestions for improvement

4. **Download for later**:
   - Click "📥 Download Commentary"
   - Saves as markdown file with timestamp and run ID

**What the AI analyzes**:
- **Filter effectiveness**: Are filters too strict/lenient?
- **Score patterns**: What makes top stocks stand out?
- **Sector balance**: Is there over/under-representation?
- **Portfolio quality**: Is the selection well-diversified?
- **Improvement opportunities**: How to refine selection?

**Example AI commentary sections**:

```
## Filter Effectiveness
The filter results show a 100% pass rate (88 stocks passed, 0 failed), 
indicating the filters are very lenient. This suggests the system is 
prioritizing breadth over strict quality screening...

## Top Stock Analysis
The top 10 stocks share several characteristics:
- High model scores (average 87.3), indicating strong ML predictions
- Moderate value scores (average 65.2), suggesting reasonable valuations
- Strong quality scores (average 72.1), reflecting profitability
- Technology sector dominance (6 of 10 stocks)...
```

---

## Step-by-Step Analysis Workflow

### Quick Analysis (5 minutes)

1. **Select a run** from the dropdown
2. **Check filter status**: Is pass rate reasonable (30-70%)?
3. **Review top 3 stocks** in Overall Top Stocks
4. **Check portfolio estimate**: Does it look diversified?
5. **Generate AI commentary** for quick insights

### Deep Analysis (15-30 minutes)

1. **Review configuration**: Understand the selection criteria
2. **Analyze filter results**: 
   - Why did stocks fail? (if any)
   - Are filters appropriate for your risk tolerance?
3. **Examine sector rankings**:
   - Which sectors have the best candidates?
   - Are there sector biases?
   - Compare score breakdowns across sectors
4. **Study top stocks**:
   - What patterns do top stocks share?
   - Are they balanced (all scores high) or specialized (one score dominates)?
   - Use scatter plot to identify outliers
5. **Evaluate portfolio estimate**:
   - Check sector diversification
   - Verify weight distribution
   - Ensure domain scores are consistently high
6. **Read AI commentary**:
   - Compare AI insights with your own observations
   - Note any recommendations
   - Download for future reference

---

## Common Analysis Scenarios

### Scenario 1: Too Many Stocks Passing Filters

**Symptom**: Pass rate > 80%

**Analysis**:
- Check if filters are too lenient
- Review filter settings in Configuration section
- Consider tightening filters (higher ROE, lower debt)

**Action**:
- Adjust `config/config.yaml` to make filters stricter
- Re-run analysis to see impact

### Scenario 2: Too Few Stocks Passing Filters

**Symptom**: Pass rate < 20%

**Analysis**:
- Filters may be too strict
- Check which filters are causing failures
- Review if quality threshold is appropriate

**Action**:
- Relax filters slightly
- Consider if strict filtering is intentional for high-quality focus

### Scenario 3: Single Sector Dominance

**Symptom**: One sector has 5+ stocks in top 10

**Analysis**:
- Check sector rankings - is one sector consistently scoring high?
- Review if this is due to model predictions or fundamentals
- Consider sector constraints

**Action**:
- Review sector allocation in portfolio estimate
- Adjust `max_sector_weight` in config if needed
- Consider sector diversification goals

### Scenario 4: Low Domain Scores in Selected Portfolio

**Symptom**: Selected stocks have domain scores < 60

**Analysis**:
- Check if this is due to limited universe
- Review if filters eliminated better stocks
- Examine score distribution

**Action**:
- Review filter settings
- Check if more stocks should be considered
- Verify selection logic is working correctly

### Scenario 5: Unbalanced Score Components

**Symptom**: Top stocks have high model scores but low value/quality (or vice versa)

**Analysis**:
- Check score breakdown charts
- Identify which component is driving selection
- Review if this aligns with investment strategy

**Action**:
- Adjust domain score weights in config
- Increase weight for desired component (value/quality)
- Re-run analysis to see impact

---

## Best Practices

### 1. Always Check Configuration First
- Understand the selection criteria before analyzing results
- Know what the weights and filters mean
- Verify settings match your investment strategy

### 2. Use Multiple Views
- Don't just look at overall top stocks
- Check sector rankings for sector-specific insights
- Review portfolio estimate for final composition

### 3. Compare Scores, Not Just Rankings
- A stock ranked #5 with scores (85, 80, 75) may be better than #3 with scores (70, 90, 60)
- Look at score breakdowns to understand why stocks rank where they do

### 4. Use Visualizations
- Scatter plots reveal patterns and outliers
- Score breakdown charts show component contributions
- Pie charts highlight concentration risks

### 5. Generate AI Commentary
- AI provides objective analysis you might miss
- Compare AI insights with your own observations
- Use recommendations to refine your approach

### 6. Document Your Analysis
- Download AI commentary for records
- Note any patterns or concerns
- Track how changes to config affect results

### 7. Iterate and Refine
- Adjust weights/filters based on results
- Re-run analysis to see impact
- Compare multiple runs to find optimal settings

---

## Troubleshooting

### Page Won't Load
- **Check**: Is Streamlit running?
- **Solution**: Restart dashboard: `streamlit run src/app/dashboard/app.py`

### No Runs Available
- **Check**: Have you run an analysis?
- **Solution**: Go to "Run Analysis" page and create a new run

### Scores Look Wrong
- **Check**: Are fundamentals loaded?
- **Solution**: Value/quality scores require `data/fundamentals.csv`

### AI Commentary Not Working
- **Check**: Is Gemini API key configured?
- **Solution**: Go to Settings page and add `GEMINI_API_KEY`

### Charts Not Displaying
- **Check**: Are there enough stocks in the data?
- **Solution**: Ensure run has stock scores loaded

---

## Quick Reference

| Section | Key Metric | What It Tells You |
|---------|------------|-------------------|
| Configuration | Domain Score Weights | How selection is balanced |
| Filter Status | Pass Rate | Filter strictness |
| Sector Rankings | Top K per Sector | Best opportunities by sector |
| Overall Top Stocks | Domain Score | Best stocks overall |
| Portfolio Estimate | Sector Allocation | Final portfolio composition |
| AI Commentary | Recommendations | How to improve selection |

---

## Next Steps

After analyzing purchase triggers:

1. **Refine Configuration**: Adjust weights/filters based on insights
2. **Run New Analysis**: Test changes with a new run
3. **Compare Runs**: Use "Compare Runs" page to see differences
4. **Build Portfolio**: Use "Portfolio Builder" to create final portfolio
5. **Review Risk**: Check "Portfolio Analysis" for risk metrics

## Related Documentation

- [Domain Analysis](domain-analysis.md) - Vertical/horizontal selection, domain_score
- [Backtesting](backtesting.md) - Walk-forward backtest, Trigger Backtester (§12)
- [Macro Indicators](macro-indicators.md) - DXY, VIX, GSR for trigger backtest
- [Portfolio Builder](portfolio-builder.md) - Personalized portfolios
- [config/tickers/README.md](../config/tickers/README.md) - Per-ticker YAML
- [Documentation Index](README.md)

---

## Recent Improvements

The following improvements were made to the purchase triggers system based on AI analysis recommendations, addressing issues with filter effectiveness, score differentiation, and portfolio diversification.

### Issues Fixed

1. **Filter Effectiveness**: All stocks were passing filters (100% pass rate) because filters were set to 0.0 (too lenient). No quality screening was being applied.

2. **Score Distribution**: Value and Quality scores were all stuck at 50.0 (no differentiation) due to column name mismatches (`fundamentals.csv` uses `pe`/`pb`, but code expected `pe_ratio`/`pb_ratio`) and missing fundamental data (ROE, margins).

3. **Model Dominance**: Model score weight was too high at 50%, causing selection to be driven primarily by ML predictions while ignoring value/quality.

4. **Sector Concentration**: Technology and Consumer Cyclical were overrepresented, lacking diversification.

### Changes Implemented

- **Enhanced Column Name Handling** (`src/analysis/domain_analysis.py`): Added `_normalize_column_names()` method supporting multiple naming conventions for PE, PB, ROE, and margin columns.

- **Improved Value/Quality Score Calculation** (`src/analysis/domain_analysis.py`): Better handling of missing data, outlier filtering (PE < 1000, PB < 100, ROE between -100% and 1000%), and requires at least 2 valid values for meaningful ranks.

- **Stricter Default Filters** (`config/config.yaml`): Changed from `min_roe: 0.0` to `0.05`, `min_net_margin: 0.0` to `0.03`, and `max_debt_to_equity: 2.0` to `1.5`.

- **Balanced Score Weights** (`config/config.yaml`): Changed from 50/30/20 (model/value/quality) to 40/35/25, giving fundamentals 60% total influence.

- **Column Name Mapping in GUI** (`src/app/dashboard/pages/purchase_triggers.py`): Automatically maps `pe` to `pe_ratio`, `pb` to `pb_ratio` when loading fundamentals.

- **Configuration Improvement Script** (`scripts/improve_purchase_triggers.py`): Analyzes current configuration, identifies issues, provides recommendations, and can apply improvements automatically via `--apply` flag.

### Expected Results

| Metric | Before | After |
|--------|--------|-------|
| Filter Pass Rate | 100% (all stocks pass) | ~30-70% (realistic screening) |
| Value Scores | All 50.0 (no differentiation) | 0-100 range (meaningful differentiation) |
| Quality Scores | All 50.0 (no differentiation) | 0-100 range (meaningful differentiation) |
| Selection Balance | Effectively 100% model-driven | 40% model, 35% value, 25% quality |

### Verification Steps

1. Run a new analysis and check the Purchase Triggers page to verify pass rate is 30-70%
2. View Sector Rankings to verify Value and Quality scores vary (not all 50.0)
3. View Configuration section to verify weights are 40%/35%/25%
4. View Portfolio Estimate to verify multiple sectors are represented and no single sector exceeds 35%

---

## See Also

- [Portfolio construction](portfolio-builder.md)
- [Methods comparison](portfolio-comparison.md)
- [Trigger backtester](backtesting.md)
- [Macro filters for triggers](macro-indicators.md)
