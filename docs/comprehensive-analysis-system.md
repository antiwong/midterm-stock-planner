# Comprehensive Analysis System

> [← Back to Documentation Index](README.md)

> For a complete system overview, see [Comprehensive System Guide](comprehensive-system-guide.md).
> This document focuses specifically on the analysis subsystem (performance attribution, benchmark comparison, factor exposure, style analysis).

## Overview

A complete database-backed analysis system that stores all analysis results and AI insights for historical tracking and retrieval.

## Database Schema

### New Tables

1. **`analysis_results`** - Stores all analysis results
   - `run_id`, `analysis_type`, `results_json`, `summary_json`
   - Types: `attribution`, `benchmark_comparison`, `factor_exposure`, etc.

2. **`ai_insights`** - Stores AI-generated insights
   - `run_id`, `insight_type`, `content`, `content_json`, `context_json`
   - Types: `executive_summary`, `top_picks_analysis`, `sector_analysis`, `risk_assessment`, `recommendations`
   - Includes prompt hashing for deduplication

3. **`recommendations`** - Tracks investment recommendations
   - `ticker`, `action`, `recommendation_date`, `reason`, `confidence`
   - Tracks actual performance over time

4. **`benchmark_comparisons`** - Benchmark comparison results
   - Portfolio vs benchmark metrics (alpha, beta, Sharpe, etc.)
   - Up/down capture ratios

5. **`factor_exposures`** - Factor exposure analysis
   - Factor loadings, contributions to return/risk

6. **`performance_attributions`** - Performance attribution
   - Factor, sector, stock selection, timing attributions

## Analysis Modules

### 1. Performance Attribution (`src/analytics/performance_attribution.py`)
- Decomposes returns into:
  - Factor attribution
  - Sector attribution
  - Stock selection attribution
  - Timing attribution
  - Interaction effects

### 2. Benchmark Comparison (`src/analytics/benchmark_comparison.py`)
- Compares portfolio vs benchmarks (SPY, QQQ)
- Calculates:
  - Alpha, Beta
  - Tracking error, Information ratio
  - Up/Down capture ratios
  - Sharpe ratio comparison

### 3. Factor Exposure (`src/analytics/factor_exposure.py`)
- Analyzes factor loadings:
  - Market, Size, Value, Momentum, Quality, Low Vol
- Calculates contributions to return and risk

## Service Layer

### AnalysisService (`src/analytics/analysis_service.py`)
- Unified interface for saving/retrieving analysis results
- Methods:
  - `save_analysis_result()` - Save any analysis result
  - `get_analysis_result()` - Retrieve analysis result
  - `save_ai_insight()` - Save AI insight with deduplication
  - `get_ai_insight()` - Retrieve AI insight
  - `save_recommendations()` - Save recommendations
  - `save_benchmark_comparison()` - Save benchmark comparison
  - `save_factor_exposures()` - Save factor exposures
  - `save_performance_attribution()` - Save attribution

## AI Insights Integration

### Updated `AIInsightsGenerator`
- Now saves all insights to database automatically
- Deduplication via prompt hashing
- Stores context used for generation
- Retrieves cached insights if available

### Usage
```python
generator = AIInsightsGenerator(save_to_db=True, db_path="data/analysis.db")
insights = generator.generate_portfolio_insights(
    top_stocks=...,
    bottom_stocks=...,
    sector_breakdown=...,
    model_metrics=...,
    run_id="run_123"  # Required for DB storage
)
```

## Comprehensive Analysis Runner

### `ComprehensiveAnalysisRunner` (`src/analytics/comprehensive_analysis.py`)
- Runs all analysis modules in one call
- Saves all results to database
- Handles errors gracefully

### Usage
```python
runner = ComprehensiveAnalysisRunner()
results = runner.run_all_analysis(
    run_id="run_123",
    portfolio_data={
        'returns': portfolio_returns,
        'weights': portfolio_weights,
        'holdings': tickers,
        'start_date': start_date,
        'end_date': end_date
    },
    stock_data=stock_dataframe,
    save_ai_insights=True
)
```

## Scripts

### `scripts/run_comprehensive_analysis.py`
Command-line tool to run all analyses for a run:

```bash
python scripts/run_comprehensive_analysis.py --run-id <run_id>
```

Options:
- `--run-id`: Required run ID
- `--run-dir`: Optional run directory
- `--skip-ai`: Skip AI insights generation
- `--db-path`: Database path (default: data/analysis.db)

## Retrieval & Query

### Get Analysis Results
```python
from src.analytics.analysis_service import AnalysisService

service = AnalysisService()

# Get specific analysis
attribution = service.get_analysis_result(run_id, 'attribution')
benchmark = service.get_analysis_result(run_id, 'benchmark_comparison')

# Get all analyses for a run
all_results = service.get_all_analysis_results(run_id)

# Get AI insights
exec_summary = service.get_ai_insight(run_id, 'executive_summary')
all_insights = service.get_all_ai_insights(run_id)

# Get recommendations
recommendations = service.get_recommendations(run_id=run_id)
buy_recommendations = service.get_recommendations(run_id=run_id, action='BUY')
```

## Benefits

1. **Historical Tracking**: All analysis results stored permanently
2. **No Regeneration**: AI insights cached and retrieved
3. **Performance Tracking**: Recommendations tracked over time
4. **Comparison**: Compare analyses across different runs
5. **Audit Trail**: Full context stored for each analysis
6. **Deduplication**: Same prompts don't regenerate AI insights

## Next Steps

1. **GUI Integration**: Update dashboard to show historical analysis
2. **Recommendation Tracking**: Auto-update recommendation performance
3. **Comparison Views**: Side-by-side analysis comparison
4. **Export**: Export analysis results to PDF/Excel
5. **API**: REST API for analysis retrieval

## Migration

Existing runs will need to be re-analyzed to populate the database. Use:

```bash
python scripts/run_comprehensive_analysis.py --run-id <existing_run_id>
```

This will generate and save all analysis results for historical runs.

---

## See Also

- [When to use each analysis type](run-vs-comprehensive-analysis.md)
- [Step-by-step guide](running-comprehensive-analysis.md)
- [Report generation](report-templates-guide.md)
- [Turnover analysis](turnover-churn-analysis-guide.md)
- [Charts and visualizations](visualization-analytics.md)
