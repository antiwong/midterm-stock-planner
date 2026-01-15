#!/usr/bin/env python3
"""
Run Comprehensive Analysis
==========================
Run all analysis modules for a given run and save results to database.
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.comprehensive_analysis import ComprehensiveAnalysisRunner, load_run_data_for_analysis
from src.analytics.models import get_db, Run
from src.app.dashboard.utils import get_run_folder


def main():
    parser = argparse.ArgumentParser(description='Run comprehensive analysis for a run')
    parser.add_argument('--run-id', type=str, required=True, help='Run ID to analyze')
    parser.add_argument('--run-dir', type=Path, help='Run directory path (auto-detected if not provided)')
    parser.add_argument('--skip-ai', action='store_true', help='Skip AI insights generation')
    parser.add_argument('--db-path', type=str, default='data/analysis.db', help='Database path')
    
    args = parser.parse_args()
    
    # Get run from database
    db = get_db(args.db_path)
    session = db.get_session()
    
    try:
        run = session.query(Run).filter_by(run_id=args.run_id).first()
        if not run:
            print(f"Error: Run {args.run_id} not found in database")
            return 1
        
        print(f"Running comprehensive analysis for run: {run.name or args.run_id}")
        print(f"  Run ID: {args.run_id}")
        print(f"  Created: {run.created_at}")
        print()
        
        # Load portfolio data (simplified - would need to load from run output files)
        portfolio_data = {
            'returns': None,  # Would load from backtest results
            'weights': None,  # Would load from portfolio files
            'holdings': [],  # Would load from portfolio
            'start_date': run.started_at or run.created_at,
            'end_date': run.completed_at or datetime.now(),
            'sector_mapping': {}  # Would load from stock data
        }
        
        # Run comprehensive analysis
        runner = ComprehensiveAnalysisRunner(db_path=args.db_path)
        
        results = runner.run_all_analysis(
            run_id=args.run_id,
            portfolio_data=portfolio_data,
            stock_data=stock_data,
            save_ai_insights=not args.skip_ai
        )
        
        print("\n✅ Analysis complete!")
        print(f"  Analyses run: {len(results['analyses'])}")
        for analysis_type, result in results['analyses'].items():
            if 'error' in result:
                print(f"  ❌ {analysis_type}: {result['error']}")
            else:
                print(f"  ✅ {analysis_type}: Success")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()


if __name__ == '__main__':
    sys.exit(main())
