#!/usr/bin/env python3
"""Quick script to check database contents."""

import sys
sys.path.insert(0, '.')

from src.analytics import get_db, Run, StockScore

db = get_db('data/analysis.db')
session = db.get_session()

# Get latest run
run = session.query(Run).order_by(Run.created_at.desc()).first()
if run:
    print(f'Latest Run: {run.run_id}')
    print(f'Name: {run.name}')
    print(f'Status: {run.status}')
    print()
    
    # Get scores
    scores = session.query(StockScore).filter_by(run_id=run.run_id).order_by(StockScore.rank).all()
    print(f'Total Scores: {len(scores)}')
    print()
    print('Top 10 Scores:')
    print('-' * 70)
    print(f'{"Ticker":<8} {"Score":>10} {"Rank":>6} {"Percentile":>12} {"Pred Return":>15}')
    print('-' * 70)
    for s in scores[:10]:
        score = s.score if s.score is not None else 0
        rank = s.rank if s.rank is not None else 0
        pct = s.percentile if s.percentile is not None else 0
        pred = s.predicted_return if s.predicted_return is not None else 0
        print(f'{s.ticker:<8} {score:>10.4f} {rank:>6} {pct:>12.1f} {pred:>15.4f}')
else:
    print('No runs found in database')

session.close()
