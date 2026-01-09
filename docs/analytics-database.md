# Analytics Database

This document describes the SQLite database used for storing analysis runs, stock scores, and related data.

## Overview

The analytics database provides persistent storage for:

1. **Analysis runs** - Backtest and scoring run metadata
2. **Stock scores** - Per-stock scores and rankings
3. **Trades** - Backtest trade history
4. **Portfolio snapshots** - Portfolio state over time
5. **Watchlists** - User-defined stock lists

## Database Location

```
data/analysis.db
```

## Module Location

```
src/analytics/models.py
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
