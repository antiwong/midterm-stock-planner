# Analytics Database

> [← Back to Documentation Index](README.md)

This document describes the SQLite database used for storing analysis runs, stock scores, and related data.

## Overview

The analytics database provides persistent storage for:

1. **Analysis runs** - Backtest and scoring run metadata
2. **Stock scores** - Per-stock scores and rankings
3. **Trades** - Backtest trade history
4. **Portfolio snapshots** - Portfolio state over time
5. **Watchlists** - User-defined stock lists
6. **Analysis results** - Performance attribution, benchmark comparison, factor exposure, rebalancing, style analysis
7. **AI insights** - AI-generated analysis and recommendations with deduplication
8. **Recommendations** - Investment recommendations with performance tracking

## Database Location

```
data/analysis.db
```

## Module Location

```
src/analytics/models.py
src/analytics/analysis_models.py  # Extended models for comprehensive analysis
src/analytics/analysis_service.py  # Service layer for analysis results
src/analytics/manager.py
```

## Schema

### runs

Analysis run metadata.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | VARCHAR(50) | Unique run identifier |
| name | VARCHAR(200) | Human-readable name |
| run_type | VARCHAR(50) | Type: backtest, analysis, etc. |
| status | VARCHAR(20) | pending, running, completed, failed |
| description | TEXT | Optional description |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |
| total_return | FLOAT | Total portfolio return |
| sharpe_ratio | FLOAT | Sharpe ratio |
| max_drawdown | FLOAT | Maximum drawdown |
| win_rate | FLOAT | Win rate |
| hit_rate | FLOAT | Hit rate |
| spearman_corr | FLOAT | Spearman correlation |
| universe_count | INTEGER | Number of stocks analyzed |
| config_json | TEXT | Configuration as JSON |
| tags_json | TEXT | Tags as JSON array |

### stock_scores

Per-stock scores for each run.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | VARCHAR(50) | Foreign key to runs |
| ticker | VARCHAR(20) | Stock symbol |
| score | FLOAT | Overall score |
| rank | INTEGER | Rank within run |
| tech_score | FLOAT | Technical score |
| fund_score | FLOAT | Fundamental score |
| sent_score | FLOAT | Sentiment score |
| rsi | FLOAT | RSI value |
| return_21d | FLOAT | 21-day return |
| return_63d | FLOAT | 63-day return |
| volatility | FLOAT | Volatility |
| sector | VARCHAR(50) | Sector classification |
| features_json | TEXT | Additional features as JSON |

### trades

Trade history from backtests.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | VARCHAR(50) | Foreign key to runs |
| ticker | VARCHAR(20) | Stock symbol |
| date | DATETIME | Trade date |
| action | VARCHAR(10) | BUY or SELL |
| quantity | INTEGER | Number of shares |
| price | FLOAT | Execution price |
| value | FLOAT | Trade value |

### portfolio_snapshots

Portfolio state at points in time.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | VARCHAR(50) | Foreign key to runs |
| date | DATETIME | Snapshot date |
| total_value | FLOAT | Total portfolio value |
| cash | FLOAT | Cash balance |
| holdings_json | TEXT | Holdings as JSON |

### watchlist_stocks

User-defined watchlists.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| watchlist_name | VARCHAR(100) | Watchlist name |
| ticker | VARCHAR(20) | Stock symbol |
| added_at | DATETIME | When added |
| notes | TEXT | Optional notes |

### analysis_results

Stores all comprehensive analysis results.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | VARCHAR(50) | Foreign key to runs |
| analysis_type | VARCHAR(50) | Type: attribution, benchmark_comparison, factor_exposure, rebalancing, style |
| results_json | TEXT | Full analysis results as JSON |
| summary_json | TEXT | Summary metrics as JSON |
| created_at | DATETIME | Creation timestamp |

### ai_insights

Stores AI-generated insights with deduplication.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | VARCHAR(50) | Foreign key to runs |
| insight_type | VARCHAR(50) | Type: executive_summary, sector_analysis, recommendations, etc. |
| content | TEXT | Insight text content |
| content_json | TEXT | Structured content as JSON (optional) |
| context_json | TEXT | Context used for generation as JSON |
| model | VARCHAR(50) | Model used (gemini, openai, etc.) |
| prompt_hash | VARCHAR(64) | Hash of prompt for deduplication |
| created_at | DATETIME | Creation timestamp |

### recommendations

Tracks investment recommendations and their performance.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | VARCHAR(50) | Foreign key to runs |
| ticker | VARCHAR(20) | Stock symbol |
| action | VARCHAR(10) | BUY, SELL, HOLD |
| recommendation_date | DATETIME | When recommendation was made |
| reason | TEXT | Reason for recommendation |
| confidence | FLOAT | Confidence score (0-1) |
| target_price | FLOAT | Target price (optional) |
| stop_loss | FLOAT | Stop loss price (optional) |
| current_price | FLOAT | Price at recommendation time |
| actual_return | FLOAT | Actual return achieved (updated over time) |
| hit_target | BOOLEAN | Whether target was hit |
| hit_stop_loss | BOOLEAN | Whether stop loss was hit |
| tracking_updated_at | DATETIME | Last performance update |

### benchmark_comparisons

Stores benchmark comparison results.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | VARCHAR(50) | Foreign key to runs |
| benchmark_symbol | VARCHAR(20) | Benchmark ticker (SPY, QQQ, etc.) |
| benchmark_name | VARCHAR(100) | Human-readable benchmark name |
| start_date | DATETIME | Comparison start date |
| end_date | DATETIME | Comparison end date |
| portfolio_metrics_json | TEXT | Portfolio metrics as JSON |
| benchmark_metrics_json | TEXT | Benchmark metrics as JSON |
| relative_metrics_json | TEXT | Relative metrics (alpha, beta, etc.) as JSON |
| created_at | DATETIME | Creation timestamp |

### factor_exposures

Stores factor exposure analysis results.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | VARCHAR(50) | Foreign key to runs |
| factor_name | VARCHAR(50) | Factor name (market, size, value, momentum, quality, low_vol) |
| factor_type | VARCHAR(50) | Factor type (market, style, risk) |
| exposure | FLOAT | Factor exposure value |
| contribution_to_return | FLOAT | Contribution to portfolio return |
| contribution_to_risk | FLOAT | Contribution to portfolio risk |
| created_at | DATETIME | Creation timestamp |

### backtest_returns

Daily portfolio and benchmark returns (reduces reliance on CSV).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | VARCHAR(50) | Foreign key to runs |
| date | DATETIME | Trading date |
| portfolio_return | FLOAT | Daily portfolio return |
| benchmark_return | FLOAT | Daily benchmark return |

### backtest_positions

Portfolio positions per rebalance date (reduces reliance on CSV).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | VARCHAR(50) | Foreign key to runs |
| date | DATETIME | Rebalance date |
| ticker | VARCHAR(20) | Stock symbol |
| weight | FLOAT | Position weight |

**Config:** Set `cli.save_backtest_csv: false` in config.yaml to store returns/positions only in DB.

### performance_attributions

Stores performance attribution breakdowns.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | VARCHAR(50) | Foreign key to runs |
| total_return | FLOAT | Total portfolio return |
| factor_attribution | FLOAT | Factor contribution |
| sector_attribution | FLOAT | Sector allocation contribution |
| stock_selection_attribution | FLOAT | Stock selection contribution |
| timing_attribution | FLOAT | Timing/rebalancing contribution |
| breakdown_json | TEXT | Detailed breakdown as JSON |
| created_at | DATETIME | Creation timestamp |

## Usage

### DatabaseManager

```python
from src.analytics.models import get_db, DatabaseManager

# Get singleton instance
db = get_db("data/analysis.db")

# Get session for queries
session = db.get_session()
try:
    # ... queries
finally:
    session.close()
```

### RunManager

High-level API for managing runs:

```python
from src.analytics import RunManager

manager = RunManager()

# Create a new run
run_id = manager.create_run(
    name="Q1 2025 Analysis",
    run_type="backtest",
    description="Diversified portfolio backtest",
    config={"model": "lightgbm", "features": [...]}
)

# Update run metrics
manager.update_run(
    run_id=run_id,
    status="completed",
    total_return=0.12,
    sharpe_ratio=0.55,
    max_drawdown=-0.08,
    hit_rate=0.62,
    spearman_corr=0.18,
    universe_count=54,
)

# Add stock scores
manager.add_stock_score(
    run_id=run_id,
    ticker="AAPL",
    score=0.75,
    rank=3,
    tech_score=0.80,
    fund_score=0.70,
    sent_score=0.65,
    rsi=55,
    sector="Technology",
    features={"return_21d": 0.05, "volatility": 0.25},
)

# List runs
runs = manager.list_runs(limit=10)

# Get specific run
run = manager.get_run(run_id)

# Delete run
manager.delete_run(run_id)
```

### RunContext

Context manager for run lifecycle:

```python
from src.analytics import RunManager, RunContext

manager = RunManager()
run_id = manager.create_run(name="Test Run")

with RunContext(manager, run_id) as ctx:
    # Add scores
    ctx.add_score("AAPL", 0.75, rank=1, tech_score=0.8)
    ctx.add_score("NVDA", 0.70, rank=2, tech_score=0.85)
    
    # Update metrics
    ctx.update(total_return=0.12, sharpe_ratio=0.55)
    
    # If exception occurs, status set to 'failed'
    # Otherwise, status set to 'completed'
```

### Direct Queries

```python
from src.analytics.models import get_db, Run, StockScore

db = get_db()
session = db.get_session()

try:
    # Get all completed runs
    runs = session.query(Run)\
        .filter_by(status='completed')\
        .order_by(Run.created_at.desc())\
        .all()
    
    # Get top 10 stocks from a run
    scores = session.query(StockScore)\
        .filter_by(run_id='20251231_091426_abc123')\
        .order_by(StockScore.rank)\
        .limit(10)\
        .all()
    
    # Get all scores for a ticker across runs
    ticker_scores = session.query(StockScore)\
        .filter_by(ticker='AAPL')\
        .join(Run)\
        .filter(Run.status == 'completed')\
        .all()
        
finally:
    session.close()
```

## Model Methods

### Run.to_dict()

Convert run to dictionary:

```python
run = session.query(Run).first()
data = run.to_dict()
# {
#     'run_id': '...',
#     'name': '...',
#     'status': 'completed',
#     'total_return': 0.12,
#     ...
# }
```

### Run.get_config() / set_config()

Access configuration:

```python
run.set_config({"model": "lightgbm", "features": [...]})
session.commit()

config = run.get_config()
print(config['model'])  # 'lightgbm'
```

### StockScore.get_features()

Access additional features:

```python
score = session.query(StockScore).first()
features = score.get_features()
print(features.get('return_21d'))
```

## Migrations

The database is created automatically on first use:

```python
Base.metadata.create_all(self.engine)
```

To add new columns:

```python
from sqlalchemy import text

db = get_db()
with db.engine.connect() as conn:
    conn.execute(text("ALTER TABLE runs ADD COLUMN new_metric FLOAT"))
    conn.commit()
```

## Backup

```bash
# Create backup
cp data/analysis.db data/analysis.db.backup

# Restore
cp data/analysis.db.backup data/analysis.db
```

## Export

Export to CSV:

```python
import pandas as pd
from src.analytics.models import get_db, Run, StockScore

db = get_db()
session = db.get_session()

# Export runs
runs = session.query(Run).all()
runs_df = pd.DataFrame([r.to_dict() for r in runs])
runs_df.to_csv("output/runs_export.csv", index=False)

# Export scores
scores = session.query(StockScore).all()
scores_df = pd.DataFrame([s.to_dict() for s in scores])
scores_df.to_csv("output/scores_export.csv", index=False)
```

## Performance Tips

1. **Use indexes** - run_id and ticker are indexed
2. **Close sessions** - Always close sessions after use
3. **Batch inserts** - Add multiple scores before commit
4. **Limit queries** - Use `.limit()` for large result sets

```python
# Batch insert
session = db.get_session()
try:
    for ticker, score in scores.items():
        ss = StockScore(run_id=run_id, ticker=ticker, score=score)
        session.add(ss)
    session.commit()  # Single commit
finally:
    session.close()
```

## Troubleshooting

### Database locked
- Close all sessions before operations
- Ensure only one process writes at a time

### Missing tables
- Delete database file and restart
- Tables are auto-created on connection

### Slow queries
- Add indexes for frequently filtered columns
- Use pagination for large result sets

---

## See Also

- [Analysis system](comprehensive-analysis-system.md)
- [Configuration options](configuration-cli.md)
- [Data pipeline](data-engineering.md)
