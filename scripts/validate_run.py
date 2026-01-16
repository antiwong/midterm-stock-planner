#!/usr/bin/env python3
"""
Validate Run Results
====================
Check a specific run for data quality issues, missing fundamentals, and result validity.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from src.app.dashboard.data import (
    load_run_by_id,
    load_run_scores,
    load_backtest_metrics,
    load_backtest_returns,
    get_run_folder
)
from src.analytics.fundamentals_status import FundamentalsStatusChecker


def validate_run(run_id: str):
    """Validate a specific run and report issues."""
    print("=" * 70)
    print(f"VALIDATING RUN: {run_id}")
    print("=" * 70)
    print()
    
    # Load run data
    run = load_run_by_id(run_id)
    if not run:
        print(f"❌ ERROR: Run '{run_id}' not found in database")
        return
    
    print(f"✅ Run found in database")
    print(f"   Status: {run.get('status')}")
    print(f"   Watchlist: {run.get('watchlist')}")
    print(f"   Created: {run.get('created_at')}")
    print()
    
    # Check run folder
    run_folder = get_run_folder(run_id)
    print(f"📁 Run folder: {run_folder}")
    if run_folder.exists():
        print(f"   ✅ Folder exists")
        files = list(run_folder.glob("*"))
        print(f"   Files: {len(files)}")
        for f in sorted(files)[:10]:
            print(f"      - {f.name}")
        if len(files) > 10:
            print(f"      ... and {len(files) - 10} more")
    else:
        print(f"   ❌ Folder does not exist!")
    print()
    
    # Load scores
    scores = load_run_scores(run_id)
    print(f"📊 Stock Scores: {len(scores)} stocks")
    
    if not scores:
        print("   ❌ ERROR: No scores found!")
        return
    
    scores_df = pd.DataFrame(scores)
    print(f"   Columns: {', '.join(scores_df.columns)}")
    print()
    
    # Check score statistics
    print("📈 Score Statistics:")
    if 'domain_score' in scores_df.columns:
        print(f"   Domain Score: min={scores_df['domain_score'].min():.2f}, "
              f"max={scores_df['domain_score'].max():.2f}, "
              f"mean={scores_df['domain_score'].mean():.2f}")
    
    if 'model_score' in scores_df.columns:
        print(f"   Model Score: min={scores_df['model_score'].min():.2f}, "
              f"max={scores_df['model_score'].max():.2f}, "
              f"mean={scores_df['model_score'].mean():.2f}")
    
    if 'value_score' in scores_df.columns:
        print(f"   Value Score: min={scores_df['value_score'].min():.2f}, "
              f"max={scores_df['value_score'].max():.2f}, "
              f"mean={scores_df['value_score'].mean():.2f}")
        # Check for penalty scores (30)
        penalty_count = (scores_df['value_score'] == 30).sum()
        if penalty_count > 0:
            print(f"   ⚠️  WARNING: {penalty_count} stocks have penalty value score (30) - missing fundamental data")
    
    if 'quality_score' in scores_df.columns:
        print(f"   Quality Score: min={scores_df['quality_score'].min():.2f}, "
              f"max={scores_df['quality_score'].max():.2f}, "
              f"mean={scores_df['quality_score'].mean():.2f}")
        # Check for penalty scores (30)
        penalty_count = (scores_df['quality_score'] == 30).sum()
        if penalty_count > 0:
            print(f"   ⚠️  WARNING: {penalty_count} stocks have penalty quality score (30) - missing fundamental data")
    
    print()
    
    # Check for missing fundamental data
    print("🔍 Fundamental Data Check:")
    tickers = scores_df['ticker'].tolist() if 'ticker' in scores_df.columns else []
    
    if tickers:
        try:
            checker = FundamentalsStatusChecker()
            # Check individual stocks instead of watchlist
            complete_count = 0
            incomplete_list = []
            
            for ticker in tickers[:50]:  # Check first 50 to avoid timeout
                status = checker.check_stock_fundamentals(ticker)
                if status.get('is_complete', False):
                    complete_count += 1
                else:
                    incomplete_list.append(ticker)
            
            total_checked = len(tickers[:50])
            if total_checked > 0:
                pct = (complete_count / total_checked) * 100
                print(f"   Checked {total_checked} stocks (sample)")
                print(f"   Complete: {complete_count} ({pct:.1f}%)")
                print(f"   Incomplete: {len(incomplete_list)} ({100-pct:.1f}%)")
                
                if incomplete_list:
                    print(f"   ⚠️  Missing fundamentals for: {', '.join(incomplete_list[:20])}")
                    if len(incomplete_list) > 20:
                        print(f"      ... and {len(incomplete_list) - 20} more")
        except Exception as e:
            print(f"   ⚠️  Could not check fundamentals: {e}")
    print()
    
    # Check backtest metrics
    print("📊 Backtest Metrics:")
    metrics = load_backtest_metrics(run_id)
    if metrics:
        print(f"   ✅ Metrics file found")
        print(f"   Total Return: {metrics.get('total_return', 'N/A')}")
        print(f"   Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A')}")
        print(f"   Max Drawdown: {metrics.get('max_drawdown', 'N/A')}")
        print(f"   Win Rate: {metrics.get('win_rate', 'N/A')}")
    else:
        print(f"   ❌ No metrics file found")
    print()
    
    # Check returns data
    print("📈 Returns Data:")
    returns_df = load_backtest_returns(run_id)
    if returns_df is not None and not returns_df.empty:
        print(f"   ✅ Returns data found")
        print(f"   Shape: {returns_df.shape}")
        print(f"   Columns: {', '.join(returns_df.columns)}")
        if 'portfolio_return' in returns_df.columns:
            total_return = (1 + returns_df['portfolio_return']).prod() - 1
            print(f"   Calculated Total Return: {total_return:.2%}")
    else:
        print(f"   ❌ No returns data found")
    print()
    
    # Check for suspicious patterns
    print("🔎 Data Quality Checks:")
    issues = []
    
    # Check if all scores are the same
    if 'domain_score' in scores_df.columns:
        if scores_df['domain_score'].nunique() == 1:
            issues.append("All domain scores are identical - possible data issue")
    
    if 'value_score' in scores_df.columns:
        if scores_df['value_score'].nunique() == 1:
            issues.append("All value scores are identical - possible data issue")
        # Check if too many penalty scores
        penalty_pct = (scores_df['value_score'] == 30).sum() / len(scores_df) * 100
        if penalty_pct > 50:
            issues.append(f"High percentage ({penalty_pct:.1f}%) of stocks have penalty value scores")
    
    if 'quality_score' in scores_df.columns:
        if scores_df['quality_score'].nunique() == 1:
            issues.append("All quality scores are identical - possible data issue")
        # Check if too many penalty scores
        penalty_pct = (scores_df['quality_score'] == 30).sum() / len(scores_df) * 100
        if penalty_pct > 50:
            issues.append(f"High percentage ({penalty_pct:.1f}%) of stocks have penalty quality scores")
    
    # Check for zero scores
    if 'domain_score' in scores_df.columns:
        zero_count = (scores_df['domain_score'] == 0).sum()
        if zero_count > 0:
            issues.append(f"{zero_count} stocks have zero domain score")
    
    if issues:
        print("   ⚠️  ISSUES FOUND:")
        for issue in issues:
            print(f"      - {issue}")
    else:
        print("   ✅ No obvious data quality issues detected")
    print()
    
    print("=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_run.py <run_id>")
        sys.exit(1)
    
    run_id = sys.argv[1]
    validate_run(run_id)
