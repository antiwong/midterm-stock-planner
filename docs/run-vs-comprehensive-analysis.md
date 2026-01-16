# Run Analysis vs Comprehensive Analysis: Comparison Guide

## Overview

The Mid-term Stock Planner has two distinct analysis features that serve different purposes in the workflow:

1. **Run Analysis** - Initial analysis pipeline that creates a new analysis run
2. **Comprehensive Analysis** - Advanced analytics on existing runs

## Quick Comparison Table

| Feature | Run Analysis | Comprehensive Analysis |
|---------|-------------|------------------------|
| **Purpose** | Create new analysis runs | Deep dive into existing runs |
| **When to Use** | Starting fresh analysis | Analyzing completed runs |
| **Input** | Watchlist selection | Existing run selection |
| **Output** | New run folder with basic results | Advanced analytics in database |
| **Analysis Types** | Basic portfolio analysis | Advanced performance analytics |
| **AI Features** | Optional commentary/recommendations | AI insights generation |
| **Data Storage** | Files in output folder | Database + files |

---

## Run Analysis

### Purpose
**Create and execute a new analysis run from scratch** using a selected watchlist.

### What It Does

1. **Backtest Execution**
   - Runs walk-forward backtesting
   - Generates portfolio returns and positions
   - Creates initial run folder with results

2. **Basic Analysis Workflow**
   - Portfolio enrichment (scores, weights, risk contributions)
   - Vertical analysis (within-sector ranking)
   - Horizontal analysis (cross-sector portfolio construction)
   - Generates CSV files with results

3. **Optional AI Features**
   - AI commentary (explains patterns in numeric data)
   - AI recommendations (portfolio suggestions)

### Workflow Steps

```
1. Select Watchlist
   ↓
2. Run Backtest (creates run folder)
   ↓
3. Run Analysis Workflow (enrichment, vertical, horizontal)
   ↓
4. Optional: Generate AI Commentary & Recommendations
   ↓
5. Results saved to output/run_*/ folder
```

### Key Features

- ✅ **Creates new runs** - Generates unique run IDs
- ✅ **Basic portfolio analysis** - Scores, weights, sector analysis
- ✅ **File-based storage** - Results in CSV/JSON files
- ✅ **Optional AI** - Can generate commentary/recommendations
- ✅ **Date range support** - Can specify start/end dates
- ✅ **Staged execution** - Can run individual stages

### Output Files

- `portfolio_scores.csv` - Stock scores and rankings
- `portfolio_weights.csv` - Portfolio weights over time
- `sector_breakdown.csv` - Sector-level analysis
- `backtest_results.json` - Backtest performance metrics
- `commentary_*.md` - AI-generated commentary (if enabled)
- `recommendations_*.json` - AI recommendations (if enabled)

### Use Cases

- Starting a new analysis for a watchlist
- Testing different watchlists
- Running backtests with different parameters
- Generating initial portfolio recommendations

---

## Comprehensive Analysis

### Purpose
**Perform advanced analytics on existing analysis runs** stored in the database.

### What It Does

1. **Performance Attribution**
   - Decomposes returns into factor, sector, stock selection, timing
   - Identifies sources of portfolio performance
   - Waterfall charts showing contribution breakdown

2. **Benchmark Comparison**
   - Compares portfolio vs S&P 500, NASDAQ, custom benchmarks
   - Relative performance metrics
   - Tracking error analysis

3. **Factor Exposure Analysis**
   - Quantifies sensitivity to market factors (Value, Growth, Size, Momentum)
   - Factor risk contributions
   - Heatmaps showing factor exposure

4. **Rebalancing Analysis**
   - Analyzes rebalancing impact
   - Transaction cost analysis
   - Portfolio drift measurement

5. **Style Analysis**
   - Classifies portfolio style (Growth vs Value, Large vs Small cap)
   - Style consistency over time
   - Style drift detection

6. **Advanced Analytics** (Optional)
   - Event-driven analysis (Fed meetings, earnings, macro events)
   - Tax optimization (tax-loss harvesting, wash sale detection)
   - Monte Carlo simulation (forward-looking risk scenarios)
   - Turnover & churn analysis
   - Earnings calendar integration
   - Real-time monitoring

7. **AI Insights**
   - Generates AI commentary on all analysis results
   - Provides actionable recommendations
   - Explains complex metrics in plain language

### Workflow Steps

```
1. Select Existing Run
   ↓
2. Check Data Completeness
   ↓
3. Run All Analysis Modules
   - Performance Attribution
   - Benchmark Comparison
   - Factor Exposure
   - Rebalancing Analysis
   - Style Analysis
   - (Optional) Advanced Analytics
   ↓
4. Generate AI Insights
   ↓
5. Results saved to database
```

### Key Features

- ✅ **Works on existing runs** - Analyzes completed runs
- ✅ **Advanced analytics** - Deep performance analysis
- ✅ **Database storage** - Results persisted in SQLite
- ✅ **Multiple analysis modules** - 7+ analysis types
- ✅ **Data validation** - Checks data completeness before running
- ✅ **AI-powered insights** - Explains all results
- ✅ **Visualizations** - Waterfall charts, heatmaps, comparisons

### Analysis Modules

1. **Performance Attribution**
   - Factor attribution
   - Sector attribution
   - Stock selection attribution
   - Timing attribution

2. **Benchmark Comparison**
   - vs S&P 500 (SPY)
   - vs NASDAQ (QQQ)
   - vs Custom benchmarks
   - Relative performance metrics

3. **Factor Exposure**
   - Value factor
   - Growth factor
   - Size factor
   - Momentum factor
   - Risk contributions

4. **Rebalancing Analysis**
   - Rebalancing frequency impact
   - Transaction costs
   - Portfolio drift

5. **Style Analysis**
   - Growth vs Value classification
   - Large vs Small cap
   - Style consistency

6. **Event Analysis** (Advanced)
   - Fed meeting impact
   - Earnings announcements
   - Macro data releases

7. **Tax Optimization** (Advanced)
   - Tax-loss harvesting opportunities
   - Wash sale detection
   - Tax-efficient rebalancing

8. **Monte Carlo Simulation** (Advanced)
   - Forward-looking risk scenarios
   - Probability distributions
   - Confidence intervals

9. **Turnover Analysis** (Advanced)
   - Portfolio turnover rate
   - Churn analysis
   - Holding period analysis

10. **Earnings Calendar** (Advanced)
    - Earnings date tracking
    - Portfolio exposure to earnings
    - Earnings impact analysis

11. **Real-Time Monitoring** (Advanced)
    - Daily portfolio updates
    - Alert system
    - Performance tracking

### Output Storage

- **Database** (`data/analysis.db`):
  - `analysis_results` table - All analysis results
  - `ai_insights` table - AI-generated insights
  - `recommendations` table - AI recommendations

- **Files** (in run folder):
  - Analysis results can be exported to CSV/JSON
  - Visualizations can be exported

### Use Cases

- Deep dive into portfolio performance
- Understanding return sources
- Comparing against benchmarks
- Factor exposure analysis
- Style classification
- Advanced risk analysis
- Tax optimization planning
- Forward-looking risk assessment

---

## Key Differences

### 1. **Purpose & Timing**

| Run Analysis | Comprehensive Analysis |
|-------------|----------------------|
| **When:** Start of workflow | **When:** After run is created |
| **Purpose:** Create new analysis | **Purpose:** Analyze existing run |
| **Input:** Watchlist | **Input:** Run ID |

### 2. **Analysis Depth**

| Run Analysis | Comprehensive Analysis |
|-------------|----------------------|
| Basic portfolio analysis | Advanced performance analytics |
| Scores, weights, sectors | Attribution, factors, benchmarks |
| Single analysis workflow | Multiple analysis modules |

### 3. **Data Storage**

| Run Analysis | Comprehensive Analysis |
|-------------|----------------------|
| File-based (CSV/JSON) | Database + files |
| Output folder structure | SQLite database |
| Run-specific files | Centralized storage |

### 4. **Analysis Types**

| Run Analysis | Comprehensive Analysis |
|-------------|----------------------|
| Portfolio enrichment | Performance attribution |
| Vertical analysis | Benchmark comparison |
| Horizontal analysis | Factor exposure |
| Basic AI commentary | Style analysis |
| | Rebalancing analysis |
| | Event analysis |
| | Tax optimization |
| | Monte Carlo simulation |
| | Turnover analysis |
| | Earnings calendar |
| | Real-time monitoring |

### 5. **AI Features**

| Run Analysis | Comprehensive Analysis |
|-------------|----------------------|
| Optional commentary | AI insights on all analyses |
| Optional recommendations | Comprehensive recommendations |
| Basic AI analysis | Advanced AI-powered insights |

### 6. **Workflow Integration**

| Run Analysis | Comprehensive Analysis |
|-------------|----------------------|
| **Step 1:** Create run | **Step 2:** Analyze run |
| Must run first | Requires existing run |
| Creates foundation | Builds on foundation |

---

## Typical Workflow

### Complete Analysis Workflow

```
1. Run Analysis
   ├─ Select watchlist
   ├─ Run backtest
   ├─ Run analysis workflow
   └─ Generate basic results
   
2. Comprehensive Analysis
   ├─ Select the run from step 1
   ├─ Run all analysis modules
   ├─ Generate AI insights
   └─ View advanced analytics
   
3. Portfolio Analysis (View Results)
   ├─ View portfolio details
   ├─ Explore charts
   └─ Review AI summary
```

### When to Use Each

**Use Run Analysis when:**
- Starting a new analysis
- Testing a new watchlist
- Running backtests
- Generating initial recommendations
- Creating baseline results

**Use Comprehensive Analysis when:**
- You have an existing run
- You want deep performance analysis
- You need benchmark comparisons
- You want factor exposure analysis
- You need advanced analytics
- You want AI insights on all results

---

## Example Scenarios

### Scenario 1: New Watchlist Analysis

1. **Run Analysis** → Select watchlist → Run backtest → Get basic results
2. **Comprehensive Analysis** → Select the run → Get advanced analytics
3. **Portfolio Analysis** → View all results together

### Scenario 2: Comparing Runs

1. **Run Analysis** → Create multiple runs with different watchlists
2. **Comprehensive Analysis** → Analyze each run separately
3. **Compare Runs** → Compare comprehensive results across runs

### Scenario 3: Deep Performance Analysis

1. **Run Analysis** → Create run (basic analysis)
2. **Comprehensive Analysis** → 
   - Performance attribution (where returns came from)
   - Benchmark comparison (vs market)
   - Factor exposure (risk factors)
   - Style analysis (growth vs value)
3. **AI Insights** → Get explanations of all results

---

## Summary

**Run Analysis** is the **foundation** - it creates the initial analysis run with basic portfolio analysis.

**Comprehensive Analysis** is the **enhancement** - it adds advanced analytics, deep performance insights, and AI-powered explanations to existing runs.

**Together**, they provide a complete analysis workflow:
- Run Analysis creates the data
- Comprehensive Analysis provides deep insights
- Both are needed for complete portfolio understanding

---

## Related Documentation

- [User Guide](user-guide.md) - Complete workflow guide
- [Comprehensive Analysis System](comprehensive-analysis-system.md) - Detailed comprehensive analysis docs
- [Backtesting Guide](backtesting.md) - Backtest execution details
- [AI Insights Guide](ai-insights.md) - AI features documentation
