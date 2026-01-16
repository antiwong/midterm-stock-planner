# User Guide

**Complete guide to using the Mid-term Stock Planner application.**

## Table of Contents

1. [Getting Started](#getting-started)
2. [Core Workflows](#core-workflows)
3. [Advanced Features](#advanced-features)
4. [Best Practices](#best-practices)
5. [Troubleshooting](#troubleshooting)

---

## Getting Started

### First-Time Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Keys**
   - Edit `config/config.yaml`
   - Add your Google API key for AI insights (optional but recommended)

3. **Prepare Data**
   - Ensure `data/prices.csv` exists with historical price data
   - Optional: Download fundamentals with `scripts/download_fundamentals.py`

4. **Launch Dashboard**
   ```bash
   streamlit run run_dashboard.py
   ```

### Understanding the Interface

The dashboard is organized into four main sections:

- **Main Workflow**: Sequential steps from analysis to insights
- **Standalone Tools**: Independent analysis tools
- **Advanced Analytics**: Specialized analysis modules
- **Utilities**: Documentation and settings

---

## Core Workflows

### Workflow 1: Basic Stock Analysis

**Goal**: Analyze a watchlist and get stock rankings.

1. **Select or Create Watchlist**
   - Go to "📋 Watchlist Manager"
   - Choose existing watchlist or create new one
   - Ensure all symbols are valid

2. **Run Analysis**
   - Navigate to "🎮 Run Analysis"
   - Select your watchlist
   - Set date range (start and end dates)
   - Choose whether to include AI insights
   - Click "Run Analysis"

3. **View Results**
   - Go to "💼 Portfolio Analysis"
   - Select the completed run
   - Review:
     - Top-ranked stocks
     - Score breakdowns
     - Sector allocation
     - Performance metrics

**Expected Time**: 2-5 minutes

### Workflow 2: Portfolio Building

**Goal**: Build a personalized portfolio based on risk tolerance.

1. **Run Initial Analysis**
   - Complete Workflow 1 first

2. **Build Portfolio**
   - Go to "🎯 Portfolio Builder"
   - Select the analysis run
   - Choose risk tolerance:
     - **Conservative**: Lower risk, stable returns
     - **Moderate**: Balanced risk/return
     - **Aggressive**: Higher risk, potential for higher returns
   - Set target return (optional)
   - Set portfolio size (number of stocks)
   - Click "Build Portfolio"

3. **Review Portfolio**
   - Check portfolio allocation
   - Review sector diversification
   - Export portfolio as CSV

**Expected Time**: 1-2 minutes

### Workflow 3: Comprehensive Analysis

**Goal**: Get deep insights into portfolio performance.

1. **Run Comprehensive Analysis**
   - Go to "📊 Comprehensive Analysis"
   - Select a completed run
   - Click "Run All Analyses"
   - Wait for all modules to complete

2. **Explore Results**
   - **Performance Attribution**: See what drove returns
   - **Benchmark Comparison**: Compare to SPY/QQQ
   - **Factor Exposure**: Understand risk factors
   - **Rebalancing Analysis**: See impact of rebalancing
   - **Style Analysis**: Growth vs. value classification

3. **Generate AI Insights**
   - Click "Quick Generate AI Insights"
   - Review executive summary
   - Check sector analysis
   - Read recommendations

**Expected Time**: 5-10 minutes

### Workflow 4: Purchase Triggers

**Goal**: Identify optimal entry points for stocks.

1. **Run Purchase Triggers**
   - Go to "🔍 Purchase Triggers"
   - Select a watchlist
   - Set trigger parameters:
     - Score threshold
     - Technical indicators
     - Fundamental filters
   - Click "Generate Triggers"

2. **Review Triggers**
   - See stocks with buy signals
   - Check trigger reasons
   - Review confidence scores
   - Export trigger list

**Expected Time**: 2-3 minutes

---

## Advanced Features

### Recommendation Performance Tracking

**Purpose**: Track how well AI recommendations performed over time.

1. **Access Tracking**
   - Go to "📊 Recommendation Tracking"
   - Select an analysis run (or "All Runs")
   - Set minimum days old (recommendations must be at least this old)

2. **Update Performance**
   - Click "🔄 Update All Recommendations"
   - System fetches current prices and calculates returns
   - Updates hit/miss statistics

3. **Review Metrics**
   - **Performance Summary**: Average return, win rate, hit target rate
   - **Detailed Recommendations**: See individual stock performance
   - **Performance Charts**: Visualize return distributions

**Key Metrics**:
- **Avg Return**: Average return of all recommendations
- **Win Rate**: Percentage of profitable recommendations
- **Hit Target Rate**: Percentage that reached target price
- **Hit Stop Loss Rate**: Percentage that hit stop loss

**Best Practices**:
- Update recommendations weekly for active tracking
- Focus on recommendations older than 7 days for meaningful results
- Compare performance across different action types (BUY vs SELL)

### Event-Driven Analysis

**Purpose**: Understand how your portfolio reacts to market events.

1. **Run Event Analysis**
   - Go to "📅 Event Analysis"
   - Select a run
   - Choose event types:
     - Fed meetings
     - Earnings announcements
     - Macro data releases
   - Click "Analyze Events"

2. **Review Results**
   - See portfolio performance around events
   - Identify event-sensitive stocks
   - Review pre/post event returns

### Tax Optimization

**Purpose**: Get tax-efficient trading suggestions.

1. **Run Tax Analysis**
   - Go to "💰 Tax Optimization"
   - Select a run
   - Set tax parameters (if applicable)
   - Click "Analyze"

2. **Review Suggestions**
   - Tax-loss harvesting opportunities
   - Wash sale warnings
   - Tax-efficient rebalancing suggestions

**Note**: This is for informational purposes only. Consult a tax professional.

### Monte Carlo Simulation

**Purpose**: Understand potential future scenarios.

1. **Run Simulation**
   - Go to "🎲 Monte Carlo"
   - Select a run
   - Set simulation parameters:
     - Number of scenarios (default: 1000)
     - Time horizon
   - Click "Run Simulation"

2. **Review Results**
   - Probability distributions
   - Value at Risk (VaR)
   - Confidence intervals
   - Worst-case scenarios

### Turnover Analysis

**Purpose**: Analyze portfolio churn and holding periods.

1. **Run Analysis**
   - Go to "🔄 Turnover Analysis"
   - Select a run
   - Click "Analyze Turnover"

2. **Review Metrics**
   - Portfolio turnover rate
   - Average holding period
   - Buy/sell frequency
   - Churn by period

### Earnings Calendar

**Purpose**: Track upcoming earnings dates.

1. **View Calendar**
   - Go to "📅 Earnings Calendar"
   - Select a run
   - View upcoming earnings dates

2. **Analyze Impact**
   - See portfolio exposure to earnings
   - Review historical earnings performance
   - Plan around earnings dates

### Real-Time Monitoring

**Purpose**: Daily portfolio updates and alerts.

1. **Set Up Monitoring**
   - Go to "⚡ Real-Time Monitoring"
   - Select a run
   - Configure alert thresholds

2. **Review Updates**
   - Daily performance changes
   - Alert notifications
   - Performance tracking

---

## Best Practices

### Data Management

1. **Keep Data Current**
   - Update price data regularly (daily/weekly)
   - Download fundamentals quarterly
   - Validate watchlists periodically

2. **Data Quality**
   - Always check data completeness warnings
   - Fix missing data before making decisions
   - Verify symbol formats (especially for international stocks)

3. **Watchlist Management**
   - Use descriptive watchlist names
   - Keep watchlists focused (20-50 stocks ideal)
   - Validate symbols before adding

### Analysis Workflow

1. **Start Simple**
   - Begin with basic analysis
   - Add comprehensive analysis after initial review
   - Use AI insights to guide deeper investigation

2. **Compare Strategies**
   - Run multiple analyses with different configurations
   - Use "📈 Compare Runs" to see differences
   - Track what works best for your style

3. **Regular Review**
   - Review recommendations weekly
   - Update performance tracking monthly
   - Rebalance portfolios quarterly

### Risk Management

1. **Diversification**
   - Don't concentrate in one sector
   - Use sector allocation charts to verify
   - Aim for 5-10 sectors minimum

2. **Position Sizing**
   - Don't put more than 10-15% in one stock
   - Use portfolio builder for balanced allocation
   - Review position sizes regularly

3. **Stop Losses**
   - Set stop losses for all positions
   - Review stop loss triggers in recommendations
   - Adjust based on volatility

### AI Insights Usage

1. **Always Review Data Quality**
   - Check for data quality warnings
   - Don't act on recommendations if data is incomplete
   - Fix data issues before making decisions

2. **Understand Context**
   - Read executive summaries for context
   - Review sector analysis for trends
   - Consider multiple recommendations together

3. **Track Performance**
   - Use recommendation tracking to see what works
   - Learn from past recommendations
   - Adjust strategy based on results

---

## Troubleshooting

### Common Issues

#### "No runs available"
**Solution**: Run an analysis first in "🎮 Run Analysis"

#### "Data quality issues detected"
**Solution**:
1. Check data completeness in "⚙️ Settings"
2. Download missing fundamental data
3. Verify price data is up to date
4. Re-run analysis

#### "Benchmark comparison not yet calculated"
**Solution**:
1. Click "Run All Analyses" in Comprehensive Analysis
2. Ensure internet connection (for fetching benchmark data)
3. Check date ranges overlap

#### "Style analysis not yet calculated"
**Solution**:
1. Download fundamental data: `scripts/download_fundamentals.py`
2. Re-run comprehensive analysis
3. Check that fundamental data includes PE, PB, market cap

#### Charts not loading
**Solution**:
1. Refresh the page
2. Use "Lazy Load" mode in Portfolio Analysis
3. Clear browser cache
4. Check browser console for errors

#### Database errors
**Solution**:
1. Check database file permissions
2. Run migration script: `python scripts/migrate_database_indexes.py`
3. Ensure `data/analysis.db` exists

### Performance Issues

#### Analysis taking too long
- Reduce watchlist size
- Use shorter date ranges
- Disable AI insights (faster)
- Check system resources (RAM, CPU)

#### Dashboard slow to load
- Use pagination (already enabled)
- Use lazy loading for charts
- Clear cache: Settings → Clear Cache

### Getting Help

1. **Check Documentation**
   - Browse "📚 Documentation" in dashboard
   - See FAQ: `docs/faq.md`
   - Review Quick Start: `docs/quick-start-guide.md`

2. **Validate Data**
   - Use "⚙️ Settings" → "Data Completeness"
   - Check watchlist validation
   - Verify symbol formats

3. **Report Issues**
   - Open GitHub issue with:
     - Description of problem
     - Steps to reproduce
     - Error messages
     - System information

---

## Advanced Tips

### Custom Configurations

Edit `config/config.yaml` to customize:
- Factor weights (model, value, quality)
- Filter thresholds
- Score calculations
- AI prompt settings

### Export and Reporting

All analysis results can be exported:
- **CSV**: For Excel analysis
- **JSON**: For programmatic access
- **PDF**: For presentations
- **Excel**: Comprehensive reports

### Automation

Use command-line scripts for automation:
```bash
# Run analysis
python scripts/analyze_portfolio.py --watchlist tech_giants

# Download fundamentals
python scripts/download_fundamentals.py

# Convert Tiger symbols
python scripts/convert_tiger_symbols.py
```

### Integration

The application uses SQLite database (`data/analysis.db`) for persistence:
- All analysis results are stored
- AI insights are cached
- Recommendations are tracked
- Access programmatically via `AnalysisService`

---

## Next Steps

1. **Explore Advanced Analytics**: Try all 6 advanced modules
2. **Track Recommendations**: Set up recommendation tracking
3. **Compare Strategies**: Run multiple analyses and compare
4. **Customize**: Adjust config.yaml for your preferences
5. **Automate**: Set up scripts for regular analysis

---

**For more help**: See [FAQ](faq.md) or [Quick Start Guide](quick-start-guide.md)
