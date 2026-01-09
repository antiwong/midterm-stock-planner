#!/usr/bin/env python3
"""
Diagnose Value/Quality Score Issues
====================================
Checks why value and quality scores aren't differentiating.
"""

import sys
from pathlib import Path
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.models import get_db, Run, StockScore
from src.analysis.domain_analysis import DomainAnalyzer, AnalysisConfig


def diagnose_scores(run_id: str = None):
    """Diagnose value/quality score calculation issues."""
    
    print("=" * 80)
    print("VALUE/QUALITY SCORE DIAGNOSTICS")
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
        print(f"📈 Stocks in run: {len(scores_df)}")
        print(f"   Tickers: {', '.join(scores_df['ticker'].head(10).tolist())}...")
        print()
        
        # Load fundamentals
        fund_path = Path("data/fundamentals.csv")
        if fund_path.exists():
            fund_df = pd.read_csv(fund_path)
            print(f"📄 Fundamentals file:")
            print(f"   Total rows: {len(fund_df)}")
            print(f"   Columns: {list(fund_df.columns)}")
            
            if 'date' in fund_df.columns:
                fund_df['date'] = pd.to_datetime(fund_df['date'], errors='coerce')
                fund_df = fund_df.sort_values('date', ascending=False)
                fund_latest = fund_df.drop_duplicates(subset=['ticker'], keep='first')
                print(f"   Unique tickers: {fund_latest['ticker'].nunique()}")
                print(f"   Tickers: {', '.join(fund_latest['ticker'].head(10).tolist())}...")
                print()
                
                # Check overlap
                run_tickers = set(scores_df['ticker'].unique())
                fund_tickers = set(fund_latest['ticker'].unique())
                overlap = run_tickers & fund_tickers
                
                print(f"🔍 Ticker Overlap:")
                print(f"   Run tickers: {len(run_tickers)}")
                print(f"   Fund tickers: {len(fund_tickers)}")
                print(f"   Overlap: {len(overlap)} ({len(overlap)/len(run_tickers)*100:.1f}%)")
                print()
                
                if len(overlap) < len(run_tickers) * 0.5:
                    print(f"⚠️  WARNING: Less than 50% of run tickers have fundamental data!")
                    print(f"   Missing: {len(run_tickers) - len(overlap)} tickers")
                    print(f"   Example missing: {', '.join(list(run_tickers - fund_tickers)[:5])}")
                    print()
                
                # Merge simulation
                rename_map = {}
                if 'pe' in fund_latest.columns:
                    rename_map['pe'] = 'pe_ratio'
                if 'pb' in fund_latest.columns:
                    rename_map['pb'] = 'pb_ratio'
                
                if rename_map:
                    fund_latest = fund_latest.rename(columns=rename_map)
                
                merged_df = scores_df.merge(
                    fund_latest[['ticker', 'pe_ratio', 'pb_ratio']],
                    on='ticker',
                    how='left'
                )
                
                print(f"📊 After Merge:")
                print(f"   Stocks with PE data: {merged_df['pe_ratio'].notna().sum()}")
                print(f"   Stocks with PB data: {merged_df['pb_ratio'].notna().sum()}")
                print()
                
                if merged_df['pe_ratio'].notna().sum() > 0:
                    pe_data = merged_df[merged_df['pe_ratio'].notna()]['pe_ratio']
                    print(f"   PE stats: min={pe_data.min():.2f}, max={pe_data.max():.2f}, unique={pe_data.nunique()}")
                
                if merged_df['pb_ratio'].notna().sum() > 0:
                    pb_data = merged_df[merged_df['pb_ratio'].notna()]['pb_ratio']
                    print(f"   PB stats: min={pb_data.min():.2f}, max={pb_data.max():.2f}, unique={pb_data.nunique()}")
                print()
                
                # Test value score calculation
                print("🧮 Testing Value Score Calculation:")
                analyzer = DomainAnalyzer(analysis_config, output_dir="output")
                
                # Use only stocks with data
                test_df = merged_df[merged_df['pe_ratio'].notna() | merged_df['pb_ratio'].notna()].copy()
                if len(test_df) > 0:
                    value_scores = analyzer.compute_value_score(test_df)
                    print(f"   Stocks tested: {len(test_df)}")
                    print(f"   Value score range: {value_scores.min():.1f} to {value_scores.max():.1f}")
                    print(f"   Unique value scores: {value_scores.nunique()}")
                    print(f"   Mean value score: {value_scores.mean():.1f}")
                    print()
                    
                    if value_scores.nunique() == 1:
                        print("❌ PROBLEM: All value scores are identical!")
                        print("   This suggests a bug in the ranking logic.")
                    elif value_scores.nunique() < len(test_df) * 0.5:
                        print("⚠️  WARNING: Limited differentiation in value scores")
                    else:
                        print("✅ Value scores are differentiating correctly")
                else:
                    print("❌ No stocks with PE/PB data to test")
        else:
            print("❌ Fundamentals file not found: data/fundamentals.csv")
        
        # Check quality data
        print()
        print("🔍 Quality Data Check:")
        if fund_path.exists():
            has_roe = 'roe' in fund_df.columns
            has_margin = 'net_margin' in fund_df.columns or 'gross_margin' in fund_df.columns
            print(f"   Has ROE: {has_roe}")
            print(f"   Has margins: {has_margin}")
            if not has_roe and not has_margin:
                print("❌ PROBLEM: No quality data (ROE/margins) in fundamentals file!")
                print("   Quality scores will all default to 50.0")
                print("   Solution: Download fundamentals with ROE and margin data")
        
    finally:
        session.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", type=str, help="Specific run ID")
    args = parser.parse_args()
    
    diagnose_scores(args.run_id)
