# Running Comprehensive Analysis Guide

This guide explains how to run comprehensive analysis to generate benchmark comparison, performance attribution, factor exposure, and other advanced analytics.

## Overview

The Comprehensive Analysis system generates:
- **Performance Attribution**: Decompose returns into factor, sector, stock selection, and timing
- **Benchmark Comparison**: Compare vs SPY, QQQ with alpha, beta, tracking error
- **Factor Exposure**: Analyze market, size, value, momentum, quality exposures
- **Rebalancing Analysis**: Analyze drift, turnover, transaction costs
- **Style Analysis**: Classify growth/value and size characteristics
- **Advanced Analytics**: Event analysis, tax optimization, Monte Carlo, turnover, earnings, real-time monitoring

## Method 1: GUI Dashboard (Recommended)

### Steps

1. **Open Dashboard**
   ```bash
   streamlit run run_dashboard.py
   ```

2. **Navigate to Comprehensive Analysis**
   - Click **"📊 Comprehensive Analysis"** in the sidebar

3. **Select Your Run**
   - Use the dropdown to select the run you want to analyze
   - Example: `jan 2026 (run_jan_26_...)`

4. **Run All Analyses**
   - Click the **"🔄 Run All Analyses"** button (primary button at the top)
   - The system will:
     - Load portfolio data from the run
     - Run all analysis modules
     - Save results to the database
     - Display progress with loading indicators

5. **View Results**
   - After completion, the page will automatically refresh
   - Navigate through the tabs:
     - **Attribution**: Performance attribution waterfall chart
     - **Benchmark**: Comparison vs benchmarks
     - **Factor Exposure**: Factor exposure heatmap
     - **Rebalancing**: Turnover and drift analysis
     - **Style**: Growth/value classification
     - **Advanced Analytics**: Event, tax, Monte Carlo, etc.

### What Happens

When you click "Run All Analyses":
1. **Data Loading**: Loads portfolio returns, weights, stock returns, and other data
2. **Data Validation**: Checks data completeness before running analyses
3. **Analysis Execution**: Runs all 12 analysis modules:
   - Performance Attribution
   - Benchmark Comparison
   - Factor Exposure
   - Rebalancing Analysis
   - Style Analysis
   - Event-Driven Analysis
   - Tax Optimization
   - Monte Carlo Simulation
   - Turnover & Churn Analysis
   - Earnings Calendar
   - Real-Time Monitoring
4. **Database Storage**: Saves all results to the database
5. **Display**: Shows results in interactive tabs

## Method 2: Command Line

### Basic Usage

```bash
python scripts/run_comprehensive_analysis.py --run-id <run_id>
```

### Example

```bash
# Run for jan_26 watchlist run
python scripts/run_comprehensive_analysis.py --run-id run_jan_26_20260115_185037_

# Skip AI insights (faster)
python scripts/run_comprehensive_analysis.py --run-id <run_id> --skip-ai

# Specify run directory manually
python scripts/run_comprehensive_analysis.py --run-id <run_id> --run-dir output/run_jan_26_20260115_185037_/
```

### Finding Your Run ID

**Option 1: From Dashboard**
1. Go to "📊 Analysis Runs" in the dashboard
2. Find your run in the list
3. Copy the Run ID

**Option 2: From Output Folder**
```bash
ls output/
# Look for folders like: run_jan_26_20260115_185037_/
# The folder name is your run_id
```

**Option 3: From Database**
```python
from src.app.dashboard.data import load_runs
runs = load_runs()
for run in runs:
    print(f"{run['name']}: {run['run_id']}")
```

## Prerequisites

### Required Data

The comprehensive analysis requires:
- ✅ **Portfolio Returns**: `backtest_returns.csv` or `portfolio_returns.csv`
- ✅ **Portfolio Weights**: `backtest_positions.csv` or `portfolio_weights.csv`
- ✅ **Stock Returns**: `backtest_returns.csv` or price data
- ✅ **Sector Mapping**: From portfolio files or `sectors.csv`
- ⚠️ **Benchmark Data**: `benchmark.csv` (for benchmark comparison)
- ⚠️ **Stock Features**: For factor exposure analysis

### Data Validation

The system automatically validates data before running:
- Missing data will show clear error messages
- Incomplete analyses will be skipped (not fail)
- You'll see which analyses ran successfully

## Understanding Results

### Performance Attribution Tab
- **Waterfall Chart**: Visual breakdown of return sources
- **Metrics**: Factor, sector, stock selection, timing contributions
- **Breakdown**: Detailed by-factor and by-sector attribution

### Benchmark Comparison Tab
- **Metrics**: Alpha, beta, tracking error, up/down capture
- **Comparison**: Portfolio vs benchmark performance
- **Relative Metrics**: Excess return, information ratio

### Factor Exposure Tab
- **Heatmap**: Visual factor exposure matrix
- **Exposures**: Market, size, value, momentum, quality, low vol
- **Contributions**: Factor contributions to return and risk

### Rebalancing Tab
- **Turnover**: Portfolio turnover metrics
- **Drift**: How much portfolio drifts from target
- **Costs**: Transaction cost analysis
- **Recommendations**: Optimal rebalancing frequency

### Style Analysis Tab
- **Classification**: Growth vs Value, Large vs Small
- **Metrics**: PE, PB, market cap analysis
- **Style Score**: Quantitative style classification

## Troubleshooting

### "No analysis runs found"
**Solution**: Run an analysis first via "🎮 Run Analysis" page

### "Run directory not found"
**Solution**: 
- Check if the run folder exists in `output/`
- Verify the run ID is correct
- Try specifying `--run-dir` manually

### "Benchmark comparison not yet calculated" or "Style analysis not yet calculated"
**Solution**: 
1. Click "🔄 Run All Analyses" button in Comprehensive Analysis page
2. If still showing, check data completeness:
   - **Benchmark**: Requires `benchmark.csv` file
   - **Style**: Requires fundamental data (PE, PB, market cap)
3. For missing fundamental data:
   ```bash
   python scripts/download_fundamentals.py --watchlist <watchlist>
   ```
   Then re-run comprehensive analysis

### "Data loading error"
**Solution**:
- Verify required files exist in run folder
- Check file names match expected format
- Ensure data covers the required date range

### "Analysis failed" or "Analysis skipped"
**Solution**:
- Check error message for specific issue
- Verify data completeness (see data requirements below)
- For missing fundamental data:
  ```bash
  python scripts/download_fundamentals.py --watchlist <watchlist>
  python scripts/analyze_portfolio.py --run-id <run_id>
  ```
- Try running individual analysis modules
- Check configuration settings

### Missing Fundamental Data (for Style Analysis)
**Symptoms**: Style analysis shows "not yet calculated" even after running
**Solution**:
1. Download fundamentals:
   ```bash
   python scripts/download_fundamentals.py --watchlist jan_26
   ```
2. Re-run portfolio enrichment:
   ```bash
   python scripts/analyze_portfolio.py --run-id <run_id>
   ```
3. Re-run comprehensive analysis from dashboard

## Advanced Options

### Skip AI Insights
```bash
python scripts/run_comprehensive_analysis.py --run-id <run_id> --skip-ai
```
Faster execution, skips AI commentary generation.

### Custom Database Path
```bash
python scripts/run_comprehensive_analysis.py --run-id <run_id> --db-path data/custom.db
```

### Run Individual Modules
You can also run individual analysis modules:
```python
from src.analytics.comprehensive_analysis import ComprehensiveAnalysisRunner

runner = ComprehensiveAnalysisRunner()
# Run specific analysis
result = runner._run_attribution(run_id, portfolio_data, stock_data)
```

## Export Results

After running analysis, you can export results:

1. **From GUI**: Click "📥 Export Results" button
   - Choose PDF or Excel format
   - Download the report

2. **From Code**:
```python
from src.app.dashboard.export import export_to_pdf, export_to_excel

# Export to PDF
pdf_bytes = export_to_pdf(all_results, run_info)

# Export to Excel
excel_bytes = export_to_excel(all_results, run_info)
```

## Performance Tips

1. **First Run**: May take 5-10 minutes (all modules)
2. **Subsequent Runs**: Faster if data is cached
3. **Skip AI**: Use `--skip-ai` for faster execution
4. **Large Portfolios**: May take longer for factor exposure analysis

## Next Steps

After running comprehensive analysis:
1. Review results in each tab
2. Export reports for documentation
3. Compare multiple runs
4. Use insights for portfolio optimization
5. Generate AI insights for recommendations
