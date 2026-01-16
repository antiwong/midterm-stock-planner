"""
Database Migration: Alert and Report Tables
===========================================
Creates tables for alert system and report templates.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, inspect, text
from src.analytics.models import Base
from src.analytics.alert_system import AlertConfig, AlertHistory
from src.analytics.report_templates import ReportTemplate, ReportGeneration


def run_migration(db_path: str):
    """Run database migration to create alert and report tables."""
    print("=" * 70)
    print("DATABASE MIGRATION: Alert & Report Tables")
    print("=" * 70)
    
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    inspector = inspect(engine)
    
    existing_tables = inspector.get_table_names()
    
    # Create tables
    tables_to_create = {
        'alert_configs': AlertConfig,
        'alert_history': AlertHistory,
        'report_templates': ReportTemplate,
        'report_generations': ReportGeneration
    }
    
    with engine.connect() as conn:
        for table_name, model_class in tables_to_create.items():
            if table_name in existing_tables:
                print(f"✅ Table '{table_name}' already exists")
            else:
                try:
                    model_class.__table__.create(engine, checkfirst=True)
                    print(f"✅ Created table '{table_name}'")
                except Exception as e:
                    print(f"❌ Failed to create table '{table_name}': {e}")
        
        conn.commit()
    
    engine.dispose()
    print("\n" + "=" * 70)
    print("✅ Migration complete!")
    print("=" * 70)


if __name__ == "__main__":
    db_path = project_root / "data" / "analysis.db"
    run_migration(str(db_path))
