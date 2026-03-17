# Comprehensive Analysis System - Validation Test Plan

> [← Back to Documentation Index](README.md)

## Overview

This document outlines the test plan for validating the comprehensive analysis system implementation.

## Prerequisites

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   Key dependencies:
   - `sqlalchemy>=2.0.0` (for database)
   - `pandas`, `numpy` (for data processing)
   - All other dependencies from `requirements.txt`

2. **Database Setup**
   - Database will be auto-created at `data/analysis.db` on first use
   - Ensure write permissions to `data/` directory

3. **Test Data**
   - Have at least one completed analysis run in `output/` directory
   - Run should have:
     - `backtest_returns.csv` (portfolio returns)
     - `backtest_positions.csv` (portfolio positions/weights)
     - `portfolio_enriched_*.csv` (stock features)
     - `backtest_metrics.json` (backtest metrics)

## Test Scripts

### 1. Validation Script

Run the validation script to test all components:

```bash
python scripts/validate_comprehensive_analysis.py --run-dir output/run_<run_id>/
```

This will test:
- ✅ Module imports
- ✅ Data loader functionality
- ✅ Analysis module instantiation
- ✅ Database connection
- ✅ Analysis service methods

### 2. Comprehensive Analysis Runner

Run comprehensive analysis on an existing run:

```bash
python scripts/run_comprehensive_analysis.py \
    --run-id <run_id> \
    --run-dir output/run_<run_id>/ \
    --skip-ai  # Skip AI to test faster
```

This will:
- Load portfolio data from run output files
- Run all 6 analysis modules
- Save results to database
- Print summary of results

## Manual Testing Checklist

### 1. Database Schema Validation

```python
from src.analytics.models import get_db
from sqlalchemy import inspect

db = get_db("data/analysis.db")
inspector = inspect(db.engine)
tables = inspector.get_table_names()

# Check for all required tables
required_tables = [
    'runs',
    'stock_scores',
    'analysis_results',
    'ai_insights',
    'recommendations',
    'benchmark_comparisons',
    'factor_exposures',
    'performance_attributions'
]

for table in required_tables:
    assert table in tables, f"Missing table: {table}"
```

### 2. Data Loader Test

```python
from src.analytics.data_loader import RunDataLoader
from pathlib import Path

loader = RunDataLoader(Path("output/run_<run_id>/"))

# Test loading methods
returns = loader.load_portfolio_returns()
weights = loader.load_portfolio_weights()
features = loader.load_stock_features()
sector_mapping = loader.load_sector_mapping()
metrics = loader.load_backtest_metrics()

# Test full load
portfolio_data = loader.load_portfolio_data()
assert portfolio_data['returns'] is not None, "Returns not loaded"
assert portfolio_data['weights'] is not None, "Weights not loaded"
assert len(portfolio_data['holdings']) > 0, "No holdings found"
```

### 3. Analysis Modules Test

```python
from src.analytics.performance_attribution import PerformanceAttributionAnalyzer
from src.analytics.benchmark_comparison import BenchmarkComparator
from src.analytics.factor_exposure import FactorExposureAnalyzer
from src.analytics.rebalancing_analysis import RebalancingAnalyzer
from src.analytics.style_analysis import StyleAnalyzer

# Instantiate all analyzers
attribution = PerformanceAttributionAnalyzer()
benchmark = BenchmarkComparator()
factor = FactorExposureAnalyzer()
rebalancing = RebalancingAnalyzer()
style = StyleAnalyzer()

# Test with sample data
import pandas as pd
import numpy as np

# Create sample portfolio data
portfolio_returns = pd.Series(np.random.randn(100) * 0.01, 
                             index=pd.date_range('2024-01-01', periods=100))
portfolio_weights = pd.DataFrame({
    'AAPL': [0.1] * 100,
    'MSFT': [0.15] * 100,
    'GOOGL': [0.12] * 100
}, index=portfolio_returns.index)

portfolio_data = {
    'returns': portfolio_returns,
    'weights': portfolio_weights,
    'holdings': ['AAPL', 'MSFT', 'GOOGL'],
    'start_date': portfolio_returns.index[0],
    'end_date': portfolio_returns.index[-1],
    'sector_mapping': {'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology'}
}

# Test each analyzer
try:
    attribution_result = attribution.analyze(portfolio_data)
    print("✅ Attribution analysis works")
except Exception as e:
    print(f"❌ Attribution failed: {e}")

try:
    benchmark_result = benchmark.compare(portfolio_data, benchmark_symbol='SPY')
    print("✅ Benchmark comparison works")
except Exception as e:
    print(f"❌ Benchmark comparison failed: {e}")

# ... test other modules
```

### 4. Analysis Service Test

```python
from src.analytics.analysis_service import AnalysisService

service = AnalysisService()

# Test saving analysis result
test_result = {
    'total_return': 0.12,
    'factor_attribution': 0.03,
    'sector_attribution': 0.02
}

service.save_analysis_result(
    run_id='test_run',
    analysis_type='attribution',
    results=test_result,
    summary={'total_return': 0.12}
)

# Test retrieving
retrieved = service.get_analysis_result('test_run', 'attribution')
assert retrieved is not None, "Failed to retrieve analysis result"
assert retrieved['results']['total_return'] == 0.12, "Data mismatch"
```

### 5. Comprehensive Analysis Runner Test

```python
from src.analytics.comprehensive_analysis import ComprehensiveAnalysisRunner
from src.analytics.data_loader import load_run_data_for_analysis

# Load data
data = load_run_data_for_analysis('run_<run_id>', Path('output/run_<run_id>/'))

# Run analysis
runner = ComprehensiveAnalysisRunner()
results = runner.run_all_analysis(
    run_id='run_<run_id>',
    portfolio_data=data['portfolio_data'],
    stock_data=data['stock_data'],
    save_ai_insights=False  # Skip AI for faster testing
)

# Verify results
assert 'analyses' in results
assert 'attribution' in results['analyses']
assert 'benchmark_comparison' in results['analyses']
assert 'factor_exposure' in results['analyses']
assert 'rebalancing' in results['analyses']
assert 'style' in results['analyses']

# Check for errors
for analysis_type, result in results['analyses'].items():
    if 'error' in result:
        print(f"❌ {analysis_type}: {result['error']}")
    else:
        print(f"✅ {analysis_type}: Success")
```

### 6. GUI Integration Test

1. **Start Dashboard**
   ```bash
   streamlit run src/app/dashboard/app.py
   ```

2. **Navigate to Comprehensive Analysis Page**
   - Click "📊 Comprehensive Analysis" in sidebar
   - Should see run selector dropdown

3. **Select a Run**
   - Select an existing run from dropdown
   - Should show run information

4. **Run Analysis**
   - Click "🔄 Run All Analyses" button
   - Should show progress/loading
   - Results should appear in tabs

5. **Verify Tabs**
   - Performance Attribution tab
   - Benchmark Comparison tab
   - Factor Exposure tab
   - Rebalancing Analysis tab
   - Style Analysis tab
   - AI Insights tab
   - Recommendations tab

6. **Verify Data Display**
   - Charts should render
   - Metrics should display
   - Tables should show data

## Expected Results

### Successful Test Output

```
============================================================
COMPREHENSIVE ANALYSIS SYSTEM VALIDATION
============================================================

============================================================
TEST 1: Module Imports
============================================================
  ✅ Analysis Models
  ✅ Analysis Service
  ✅ Performance Attribution
  ✅ Benchmark Comparison
  ✅ Factor Exposure
  ✅ Rebalancing Analysis
  ✅ Style Analysis
  ✅ Comprehensive Analysis Runner
  ✅ Data Loader

✅ All 9 modules imported successfully

============================================================
TEST 2: Data Loader
============================================================
  ✅ Portfolio Returns: 100 rows/items
  ✅ Portfolio Weights: 100 rows/items
  ✅ Stock Features: 50 rows/items
  ✅ Sector Mapping: 50 items
  ✅ Backtest Metrics: Loaded

  ✅ Portfolio Data Loaded:
     - Returns: ✓
     - Weights: ✓
     - Holdings: 50 stocks
     - Date Range: 2024-01-01 to 2024-12-31

============================================================
TEST 3: Analysis Module Instantiation
============================================================
  ✅ Performance Attribution
  ✅ Benchmark Comparison
  ✅ Factor Exposure
  ✅ Rebalancing Analysis
  ✅ Style Analysis

  ✅ Portfolio data available for testing

============================================================
TEST 4: Database Connection
============================================================
  ✅ Database connection successful
  ✅ Can query runs table

  Database tables (8 total):
    ✅ analysis_results
    ✅ ai_insights
    ✅ recommendations
    ✅ benchmark_comparisons
    ✅ factor_exposures
    ✅ performance_attributions

============================================================
TEST 5: Analysis Service
============================================================
  ✅ AnalysisService instantiated
  ✅ Method: save_analysis_result
  ✅ Method: get_analysis_result
  ✅ Method: save_ai_insight
  ✅ Method: get_ai_insight
  ✅ Method: save_recommendation
  ✅ Method: get_recommendations

============================================================
VALIDATION SUMMARY
============================================================
  ✅ Imports
  ✅ Data Loader
  ✅ Module Instantiation
  ✅ Database Connection
  ✅ Analysis Service

Passed: 5 | Failed: 0 | Skipped: 0

✅ All tests passed!
```

## Common Issues & Solutions

### Issue: `ModuleNotFoundError: No module named 'sqlalchemy'`

**Solution:**
```bash
pip install sqlalchemy>=2.0.0
# Or install all requirements
pip install -r requirements.txt
```

### Issue: `Run directory not found`

**Solution:**
- Ensure run directory exists in `output/`
- Use full path: `--run-dir output/run_<run_id>/`
- Or let script auto-detect from database

### Issue: `No portfolio returns data`

**Solution:**
- Ensure run has `backtest_returns.csv` or `equity_curve.csv`
- Check that backtest completed successfully
- Re-run backtest if needed

### Issue: `Database locked`

**Solution:**
- Close any other processes using the database
- Ensure only one process writes at a time
- Check file permissions

### Issue: `Analysis module returns error`

**Solution:**
- Check that portfolio data has required fields
- Verify date ranges are valid
- Check for missing dependencies (yfinance for benchmarks)

## Next Steps After Validation

1. **Fix any issues found** during testing
2. **Run on multiple runs** to ensure robustness
3. **Test GUI integration** thoroughly
4. **Performance testing** with large datasets
5. **Document any limitations** or known issues

## Reporting Issues

If you find issues during validation:

1. Note the exact error message
2. Include the run ID and data being tested
3. Check logs for detailed error information
4. Report in GitHub issues or update this document

---

## See Also

- [Validation results](validation-results.md)
- [Test suite overview](test-suite-documentation.md)
- [v3.9.0 validation](validation-report-v3.9.0.md)
