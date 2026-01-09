#!/usr/bin/env python3
"""
Analyze Filter Effectiveness
============================
Analyzes why stocks are failing filters and recommends optimal thresholds.

Usage:
    python scripts/analyze_filter_effectiveness.py [--run-id RUN_ID]
"""

import sys
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.models import get_db, Run, StockScore
from src.analysis.domain_analysis import AnalysisConfig, DomainAnalyzer
from src.app.dashboard.data import load_fundamentals


def analyze_filter_failures(run_id: str = None):
    """Analyze why stocks are failing filters."""
    
    print("=" * 80)
    print("FILTER EFFECTIVENESS ANALYSIS")
    print("=" * 80)
    print()
    
    # Load config
    config_path = Path("config/config.yaml")
    with open(config_path) as f:
        config_dict = yaml.safe_load(f)
    analysis_config = AnalysisConfig.from_dict(config_dict.get('analysis', {}))
    
    # Load run
    db = get_db("data/analysis.db")
    session = db.get_session()
    
    try:
        if run_id:
            run = session.query(Run).filter_by(run_id=run_id).first()
        else:
            run = session.query(Run).order_by(Run.created_at.desc()).first()
        
        if not run:
            print("❌ No run found")
            return
        
        print(f"📊 Run: {run.run_id}")
        print(f"   Name: {run.name}")
        print()
        
        # Load scores
        scores = session.query(StockScore).filter_by(run_id=run.run_id).all()
        scores_df = pd.DataFrame([s.to_dict() for s in scores])
        print(f"📈 Total stocks: {len(scores_df)}")
        print()
        
        # Load fundamentals
        fundamentals_df = load_fundamentals()
        if not fundamentals_df.empty and 'ticker' in fundamentals_df.columns:
            if 'date' in fundamentals_df.columns:
                fundamentals_df = fundamentals_df.sort_values('date', ascending=False)
                fundamentals_df = fundamentals_df.drop_duplicates(subset=['ticker'], keep='first')
            
            # Merge
            rename_map = {}
            if 'pe' in fundamentals_df.columns:
                rename_map['pe'] = 'pe_ratio'
            if 'pb' in fundamentals_df.columns:
                rename_map['pb'] = 'pb_ratio'
            if rename_map:
                fundamentals_df = fundamentals_df.rename(columns=rename_map)
            
            scores_df = scores_df.merge(
                fundamentals_df[['ticker'] + [c for c in fundamentals_df.columns if c not in ['ticker', 'date']]],
                on='ticker',
                how='left'
            )
        
        # Apply filters
        analyzer = DomainAnalyzer(analysis_config, output_dir="output")
        
        filter_results = []
        for _, row in scores_df.iterrows():
            filters = analyzer.apply_hard_filters(row)
            passed = all(filters.values())
            filter_results.append({
                'ticker': row['ticker'],
                'passed': passed,
                'roe': row.get('roe'),
                'net_margin': row.get('net_margin'),
                'debt_to_equity': row.get('debt_to_equity'),
                **filters
            })
        
        filter_df = pd.DataFrame(filter_results)
        passed_count = filter_df['passed'].sum()
        failed_count = len(filter_df) - passed_count
        pass_rate = passed_count / len(filter_df) * 100
        
        print("📊 Filter Results:")
        print(f"   Passed: {passed_count}/{len(filter_df)} ({pass_rate:.1f}%)")
        print(f"   Failed: {failed_count}/{len(filter_df)} ({100-pass_rate:.1f}%)")
        print()
        
        # Analyze failures
        failed_df = filter_df[~filter_df['passed']].copy()
        
        if len(failed_df) > 0:
            print("🔍 Failure Analysis:")
            print()
            
            # Check which filters are causing failures
            filter_columns = [c for c in failed_df.columns if c not in ['ticker', 'passed', 'roe', 'net_margin', 'debt_to_equity']]
            failure_counts = {}
            for col in filter_columns:
                if col in failed_df.columns:
                    failure_counts[col] = (~failed_df[col]).sum()
            
            print("   Filters causing failures:")
            for filter_name, count in sorted(failure_counts.items(), key=lambda x: x[1], reverse=True):
                pct = count / len(failed_df) * 100
                print(f"      {filter_name:20s}: {count:3d} stocks ({pct:5.1f}%)")
            print()
            
            # Analyze ROE failures
            if 'roe' in failed_df.columns:
                roe_failures = failed_df[~failed_df.get('roe', pd.Series([True] * len(failed_df)))]
                if len(roe_failures) > 0 and 'roe' in roe_failures.columns:
                    roe_values = roe_failures['roe'].dropna()
                    if len(roe_values) > 0:
                        print(f"   ROE Statistics (failed stocks):")
                        print(f"      Min: {roe_values.min():.4f} ({roe_values.min()*100:.2f}%)")
                        print(f"      Max: {roe_values.max():.4f} ({roe_values.max()*100:.2f}%)")
                        print(f"      Mean: {roe_values.mean():.4f} ({roe_values.mean()*100:.2f}%)")
                        print(f"      Median: {roe_values.median():.4f} ({roe_values.median()*100:.2f}%)")
                        print(f"      Current threshold: {analysis_config.min_roe:.4f} ({analysis_config.min_roe*100:.2f}%)")
                        print()
            
            # Analyze Net Margin failures
            if 'net_margin' in failed_df.columns:
                margin_failures = failed_df[~failed_df.get('net_margin', pd.Series([True] * len(failed_df)))]
                if len(margin_failures) > 0 and 'net_margin' in margin_failures.columns:
                    margin_values = margin_failures['net_margin'].dropna()
                    if len(margin_values) > 0:
                        print(f"   Net Margin Statistics (failed stocks):")
                        print(f"      Min: {margin_values.min():.4f} ({margin_values.min()*100:.2f}%)")
                        print(f"      Max: {margin_values.max():.4f} ({margin_values.max()*100:.2f}%)")
                        print(f"      Mean: {margin_values.mean():.4f} ({margin_values.mean()*100:.2f}%)")
                        print(f"      Median: {margin_values.median():.4f} ({margin_values.median()*100:.2f}%)")
                        print(f"      Current threshold: {analysis_config.min_net_margin:.4f} ({analysis_config.min_net_margin*100:.2f}%)")
                        print()
            
            # Analyze Debt/Equity failures
            if 'debt_to_equity' in failed_df.columns:
                debt_failures = failed_df[~failed_df.get('debt_to_equity', pd.Series([True] * len(failed_df)))]
                if len(debt_failures) > 0 and 'debt_to_equity' in debt_failures.columns:
                    debt_values = debt_failures['debt_to_equity'].dropna()
                    if len(debt_values) > 0:
                        print(f"   Debt/Equity Statistics (failed stocks):")
                        print(f"      Min: {debt_values.min():.2f}")
                        print(f"      Max: {debt_values.max():.2f}")
                        print(f"      Mean: {debt_values.mean():.2f}")
                        print(f"      Median: {debt_values.median():.2f}")
                        print(f"      Current threshold: {analysis_config.max_debt_to_equity:.2f}")
                        print()
        
        # Recommendations
        print("💡 Recommendations:")
        print()
        
        if pass_rate < 10:
            print("   ⚠️  Pass rate is very low (<10%). Consider:")
            print("      - Relaxing ROE threshold (current: {:.2%})".format(analysis_config.min_roe))
            print("      - Relaxing Net Margin threshold (current: {:.2%})".format(analysis_config.min_net_margin))
            print("      - Increasing Debt/Equity threshold (current: {:.2f})".format(analysis_config.max_debt_to_equity))
            print()
        
        if pass_rate < 20:
            suggested_roe = analysis_config.min_roe * 0.7  # 30% reduction
            suggested_margin = analysis_config.min_net_margin * 0.7
            suggested_debt = analysis_config.max_debt_to_equity * 1.2  # 20% increase
            
            print("   📝 Suggested thresholds for ~20% pass rate:")
            print(f"      min_roe: {suggested_roe:.4f} ({suggested_roe*100:.2f}%)")
            print(f"      min_net_margin: {suggested_margin:.4f} ({suggested_margin*100:.2f}%)")
            print(f"      max_debt_to_equity: {suggested_debt:.2f}")
            print()
        
        if pass_rate > 50:
            print("   ⚠️  Pass rate is high (>50%). Consider tightening filters for better quality.")
            print()
        
        # Sector analysis
        if 'sector' in scores_df.columns:
            print("📊 Sector Distribution:")
            sector_counts = scores_df['sector'].value_counts()
            passed_sector_counts = filter_df[filter_df['passed']]['ticker'].map(
                scores_df.set_index('ticker')['sector']
            ).value_counts()
            
            print("   All stocks:")
            for sector, count in sector_counts.head(10).items():
                passed = passed_sector_counts.get(sector, 0)
                pct = passed / count * 100 if count > 0 else 0
                print(f"      {sector:25s}: {count:3d} stocks ({passed:2d} passed, {pct:5.1f}%)")
            print()
        
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", type=str, help="Specific run ID")
    args = parser.parse_args()
    
    analyze_filter_failures(args.run_id)
