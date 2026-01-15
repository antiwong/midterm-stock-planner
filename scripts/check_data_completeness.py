#!/usr/bin/env python3
"""
Check Data Completeness
=======================
Check if all required data is available before running analysis.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.data_completeness import DataCompletenessChecker
from src.analytics.data_loader import load_run_data_for_analysis
from src.app.dashboard.utils import get_run_folder
from src.app.dashboard.data import load_runs


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_data_completeness.py <run_id>")
        print("\nExample:")
        print("  python scripts/check_data_completeness.py 20260115_185037_e08e49ae")
        return 1
    
    run_id = sys.argv[1]
    
    # Get run directory
    runs = load_runs()
    run = next((r for r in runs if r['run_id'] == run_id), None)
    
    if not run:
        print(f"Error: Run {run_id} not found")
        return 1
    
    run_dir = get_run_folder(run_id, run.get('watchlist'))
    if not run_dir or not run_dir.exists():
        print(f"Error: Run directory not found: {run_dir}")
        return 1
    
    print(f"Checking data completeness for run: {run.get('name', run_id)}")
    print(f"Run ID: {run_id}")
    print(f"Directory: {run_dir}")
    print()
    
    # Load data
    print("Loading data...")
    data = load_run_data_for_analysis(run_id, run_dir)
    
    if data.get('error'):
        print(f"Error loading data: {data['error']}")
        return 1
    
    portfolio_data = data.get('portfolio_data', {})
    stock_data = data.get('stock_data', {})
    
    # Check completeness
    checker = DataCompletenessChecker()
    completeness = checker.check_data_completeness(portfolio_data, stock_data)
    
    # Print report
    report = checker.generate_report(completeness)
    print(report)
    
    # Return exit code based on results
    if completeness.get('errors'):
        return 1
    elif completeness.get('warnings'):
        return 0  # Warnings are OK, but return 0 to indicate partial success
    else:
        return 0


if __name__ == '__main__':
    sys.exit(main())
