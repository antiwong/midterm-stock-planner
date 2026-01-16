#!/usr/bin/env python3
"""
Database Index Migration Script
================================
Adds new indexes for performance optimization.

Run this script to add the new indexes:
    python scripts/migrate_database_indexes.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text, inspect
from src.analytics.models import get_db


def migrate_indexes():
    """Add new indexes to the database."""
    db_path = project_root / "data" / "analysis.db"
    db = get_db(str(db_path))
    engine = db.engine
    inspector = inspect(engine)
    
    print("=" * 70)
    print("DATABASE INDEX MIGRATION")
    print("=" * 70)
    
    with engine.connect() as conn:
        # Check existing indexes
        run_indexes = [idx['name'] for idx in inspector.get_indexes('runs')]
        score_indexes = [idx['name'] for idx in inspector.get_indexes('stock_scores')]
        
        # Add Run table indexes
        print("\n1. Adding Run table indexes...")
        
        if 'idx_run_watchlist' not in run_indexes:
            try:
                conn.execute(text("CREATE INDEX idx_run_watchlist ON runs(watchlist)"))
                conn.commit()
                print("   ✅ Created idx_run_watchlist")
            except Exception as e:
                print(f"   ⚠️  Failed to create idx_run_watchlist: {e}")
        else:
            print("   ✅ idx_run_watchlist already exists")
        
        if 'idx_run_status_created' not in run_indexes:
            try:
                conn.execute(text("CREATE INDEX idx_run_status_created ON runs(status, created_at)"))
                conn.commit()
                print("   ✅ Created idx_run_status_created")
            except Exception as e:
                print(f"   ⚠️  Failed to create idx_run_status_created: {e}")
        else:
            print("   ✅ idx_run_status_created already exists")
        
        # Add StockScore table indexes
        print("\n2. Adding StockScore table indexes...")
        
        if 'idx_score_sector' not in score_indexes:
            try:
                conn.execute(text("CREATE INDEX idx_score_sector ON stock_scores(sector)"))
                conn.commit()
                print("   ✅ Created idx_score_sector")
            except Exception as e:
                print(f"   ⚠️  Failed to create idx_score_sector: {e}")
        else:
            print("   ✅ idx_score_sector already exists")
        
        if 'idx_score_score' not in score_indexes:
            try:
                conn.execute(text("CREATE INDEX idx_score_score ON stock_scores(score)"))
                conn.commit()
                print("   ✅ Created idx_score_score")
            except Exception as e:
                print(f"   ⚠️  Failed to create idx_score_score: {e}")
        else:
            print("   ✅ idx_score_score already exists")
    
    print("\n" + "=" * 70)
    print("✅ Migration complete!")
    print("=" * 70)


if __name__ == "__main__":
    migrate_indexes()
