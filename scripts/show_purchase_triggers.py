#!/usr/bin/env python3
"""
Purchase Triggers Display Script
=================================
Shows why stocks were selected or excluded from portfolios.

Displays:
- Hard filter status (ROE, margins, debt)
- Domain score breakdown (model, value, quality)
- Sector rankings
- Final portfolio selection

Usage:
    python scripts/show_purchase_triggers.py [--run-id <run_id>] [--sector <sector>] [--top-n <n>]
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

import pandas as pd
import numpy as np
import yaml

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.models import get_db, Run, StockScore
from src.analysis.domain_analysis import DomainAnalyzer, AnalysisConfig


def load_run_data(run_id: Optional[str] = None):
    """Load run and scores from database."""
    db = get_db("data/analysis.db")
    session = db.get_session()
    
    try:
        if run_id:
            run = session.query(Run).filter_by(run_id=run_id).first()
            if not run:
                raise ValueError(f"Run not found: {run_id}")
        else:
            run = session.query(Run).order_by(Run.created_at.desc()).first()
            if not run:
                raise ValueError("No runs found in database")
        
        scores = session.query(StockScore).filter_by(run_id=run.run_id).all()
        scores_data = [s.to_dict() for s in scores]
        
        return run.to_dict(), scores_data
    finally:
        session.close()


def load_fundamentals() -> pd.DataFrame:
    """Load fundamentals data."""
    fundamentals_path = Path("data/fundamentals.csv")
    if not fundamentals_path.exists():
        print("⚠️  Warning: fundamentals.csv not found. Value/quality scores will be limited.")
        return pd.DataFrame()
    
    df = pd.read_csv(fundamentals_path)
    return df


def format_score(value: float, max_val: float = 100.0) -> str:
    """Format score with color coding."""
    if pd.isna(value):
        return "N/A"
    
    pct = value / max_val
    if pct >= 0.8:
        return f"{value:.1f} 🟢"
    elif pct >= 0.6:
        return f"{value:.1f} 🟡"
    elif pct >= 0.4:
        return f"{value:.1f} 🟠"
    else:
        return f"{value:.1f} 🔴"


def format_filter_status(passed: bool, reason: str = "") -> str:
    """Format filter status."""
    if passed:
        return "✅ PASS"
    else:
        return f"❌ FAIL ({reason})"


def check_filters(row: pd.Series, config: AnalysisConfig) -> Dict[str, bool]:
    """Check if stock passes all filters."""
    filters = {}
    
    # ROE filter
    if 'roe' in row.index and config.min_roe is not None:
        filters['roe'] = pd.isna(row['roe']) or row['roe'] >= config.min_roe
    else:
        filters['roe'] = True
    
    # Net margin filter
    if 'net_margin' in row.index and config.min_net_margin is not None:
        filters['net_margin'] = pd.isna(row['net_margin']) or row['net_margin'] >= config.min_net_margin
    else:
        filters['net_margin'] = True
    
    # Debt-to-equity filter
    if 'debt_to_equity' in row.index and config.max_debt_to_equity is not None:
        filters['debt_to_equity'] = pd.isna(row['debt_to_equity']) or row['debt_to_equity'] <= config.max_debt_to_equity
    else:
        filters['debt_to_equity'] = True
    
    # Market cap filter
    if 'market_cap' in row.index and config.min_market_cap is not None:
        filters['market_cap'] = pd.isna(row['market_cap']) or row['market_cap'] >= config.min_market_cap
    else:
        filters['market_cap'] = True
    
    # Volume filter
    if 'avg_volume' in row.index and config.min_avg_volume is not None:
        filters['avg_volume'] = pd.isna(row['avg_volume']) or row['avg_volume'] >= config.min_avg_volume
    else:
        filters['avg_volume'] = True
    
    return filters


def get_filter_failures(filters: Dict[str, bool], row: pd.Series, config: AnalysisConfig) -> List[str]:
    """Get list of failed filters."""
    failures = []
    
    if not filters.get('roe', True):
        failures.append(f"ROE < {config.min_roe}")
    if not filters.get('net_margin', True):
        failures.append(f"Net Margin < {config.min_net_margin}")
    if not filters.get('debt_to_equity', True):
        failures.append(f"Debt/Equity > {config.max_debt_to_equity}")
    if not filters.get('market_cap', True):
        failures.append(f"Market Cap < {config.min_market_cap}")
    if not filters.get('avg_volume', True):
        failures.append(f"Avg Volume < {config.min_avg_volume}")
    
    return failures


def display_purchase_triggers(
    run_id: Optional[str] = None,
    sector_filter: Optional[str] = None,
    top_n: int = 20,
    show_all: bool = False
):
    """Display purchase triggers for a run."""
    
    print("=" * 80)
    print("PURCHASE TRIGGERS ANALYSIS")
    print("=" * 80)
    print()
    
    # Load config
    config_path = Path("config/config.yaml")
    if config_path.exists():
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)
    else:
        config_dict = {}
    
    analysis_config = AnalysisConfig.from_dict(config_dict.get('analysis', {}))
    
    # Load run data
    print("📥 Loading run data...")
    run, scores_data = load_run_data(run_id)
    scores_df = pd.DataFrame(scores_data)
    
    print(f"   Run ID: {run['run_id']}")
    print(f"   Name: {run.get('name', 'N/A')}")
    print(f"   Created: {run.get('created_at', 'N/A')}")
    print(f"   Stocks: {len(scores_df)}")
    print()
    
    # Load fundamentals
    print("📥 Loading fundamentals...")
    fundamentals_df = load_fundamentals()
    
    if not fundamentals_df.empty:
        # Merge fundamentals
        if 'ticker' in fundamentals_df.columns:
            # Remove duplicates from fundamentals (keep first)
            fundamentals_df_unique = fundamentals_df.drop_duplicates(subset=['ticker'], keep='first')
            scores_df = scores_df.merge(
                fundamentals_df_unique,
                on='ticker',
                how='left',
                suffixes=('', '_fund')
            )
        print(f"   Merged fundamentals for {scores_df['ticker'].notna().sum()} stocks")
    else:
        print("   ⚠️  No fundamentals data available")
    
    print()
    
    # Create analyzer to compute domain scores
    print("🔢 Computing domain scores...")
    analyzer = DomainAnalyzer(analysis_config, output_dir="output")
    
    # Prepare model scores
    model_scores = None
    if 'score' in scores_df.columns:
        # Handle duplicate tickers by taking the first occurrence
        scores_df_unique = scores_df.drop_duplicates(subset=['ticker'], keep='first')
        model_scores = pd.Series(
            scores_df_unique['score'].values,
            index=scores_df_unique['ticker'].values
        )
    
    # Compute domain scores
    scored_df = analyzer.compute_domain_score(scores_df, model_scores)
    
    print(f"   Computed scores for {len(scored_df)} stocks")
    print()
    
    # Display configuration
    print("=" * 80)
    print("CONFIGURATION")
    print("=" * 80)
    print(f"Domain Score Weights:")
    print(f"  • Model Score:   {analysis_config.w_model*100:.0f}%")
    print(f"  • Value Score:   {analysis_config.w_value*100:.0f}%")
    print(f"  • Quality Score: {analysis_config.w_quality*100:.0f}%")
    print()
    print(f"Hard Filters:")
    print(f"  • Min ROE:           {analysis_config.min_roe or 'None'}")
    print(f"  • Min Net Margin:   {analysis_config.min_net_margin or 'None'}")
    print(f"  • Max Debt/Equity:   {analysis_config.max_debt_to_equity or 'None'}")
    print(f"  • Min Market Cap:    {analysis_config.min_market_cap or 'None'}")
    print(f"  • Min Avg Volume:    {analysis_config.min_avg_volume or 'None'}")
    print()
    print(f"Selection Settings:")
    print(f"  • Top K per Sector:  {analysis_config.top_k_per_sector}")
    print(f"  • Portfolio Size:     {analysis_config.portfolio_size}")
    print()
    
    # Apply filters and show results
    print("=" * 80)
    print("FILTER STATUS")
    print("=" * 80)
    
    filter_results = []
    for idx, row in scored_df.iterrows():
        filters = check_filters(row, analysis_config)
        all_passed = all(filters.values())
        failures = get_filter_failures(filters, row, analysis_config) if not all_passed else []
        
        filter_results.append({
            'ticker': row.get('ticker', 'N/A'),
            'sector': row.get('sector', 'N/A'),
            'passed': all_passed,
            'failures': ', '.join(failures) if failures else 'None',
            'domain_score': row.get('domain_score', 0),
            'model_score': row.get('model_score', 0),
            'value_score': row.get('value_score', 0),
            'quality_score': row.get('quality_score', 0),
        })
    
    filter_df = pd.DataFrame(filter_results)
    
    passed_count = filter_df['passed'].sum()
    failed_count = (~filter_df['passed']).sum()
    
    print(f"✅ Passed Filters: {passed_count} stocks")
    print(f"❌ Failed Filters: {failed_count} stocks")
    print()
    
    # Show failed stocks
    if failed_count > 0 and show_all:
        failed_df = filter_df[~filter_df['passed']].sort_values('domain_score', ascending=False)
        print("Failed Stocks (Top 10 by Domain Score):")
        print("-" * 80)
        print(f"{'Ticker':<8} {'Sector':<20} {'Domain':>8} {'Failures':<40}")
        print("-" * 80)
        for _, row in failed_df.head(10).iterrows():
            print(f"{row['ticker']:<8} {row['sector']:<20} {row['domain_score']:>8.1f} {row['failures']:<40}")
        print()
    
    # Filter to passed stocks
    passed_df = scored_df[filter_df['passed']].copy()
    
    if len(passed_df) == 0:
        print("❌ No stocks passed filters!")
        return
    
    # Display by sector
    print("=" * 80)
    print("SECTOR RANKINGS (Top Candidates)")
    print("=" * 80)
    
    sectors = sorted(passed_df['sector'].unique()) if 'sector' in passed_df.columns else ['Unknown']
    
    if sector_filter:
        sectors = [s for s in sectors if sector_filter.lower() in s.lower()]
        if not sectors:
            print(f"❌ No sectors match filter: {sector_filter}")
            return
    
    for sector in sectors:
        sector_df = passed_df[passed_df['sector'] == sector].copy()
        if len(sector_df) == 0:
            continue
        
        sector_df = sector_df.sort_values('domain_score', ascending=False)
        top_k = sector_df.head(analysis_config.top_k_per_sector)
        
        print(f"\n📊 {sector} (Top {len(top_k)} of {len(sector_df)} candidates)")
        print("-" * 80)
        print(f"{'Rank':<6} {'Ticker':<8} {'Domain':>8} {'Model':>8} {'Value':>8} {'Quality':>8} {'Status':<10}")
        print("-" * 80)
        
        for rank, (idx, row) in enumerate(top_k.iterrows(), 1):
            ticker = row.get('ticker', 'N/A')
            domain_score = row.get('domain_score', 0)
            model_score = row.get('model_score', 0)
            value_score = row.get('value_score', 0)
            quality_score = row.get('quality_score', 0)
            
            # Mark if in top K
            status = "✅ SELECTED" if rank <= analysis_config.top_k_per_sector else "⏳ CANDIDATE"
            
            print(f"{rank:<6} {ticker:<8} {format_score(domain_score):>12} "
                  f"{format_score(model_score):>12} {format_score(value_score):>12} "
                  f"{format_score(quality_score):>12} {status:<10}")
    
    print()
    
    # Display overall top stocks
    print("=" * 80)
    print(f"OVERALL TOP {top_n} STOCKS (All Sectors)")
    print("=" * 80)
    
    top_stocks = passed_df.sort_values('domain_score', ascending=False).head(top_n)
    
    print(f"{'Rank':<6} {'Ticker':<8} {'Sector':<20} {'Domain':>8} {'Model':>8} {'Value':>8} {'Quality':>8}")
    print("-" * 80)
    
    for rank, (idx, row) in enumerate(top_stocks.iterrows(), 1):
        ticker = row.get('ticker', 'N/A')
        sector = row.get('sector', 'N/A')
        domain_score = row.get('domain_score', 0)
        model_score = row.get('model_score', 0)
        value_score = row.get('value_score', 0)
        quality_score = row.get('quality_score', 0)
        
        print(f"{rank:<6} {ticker:<8} {sector:<20} {format_score(domain_score):>12} "
              f"{format_score(model_score):>12} {format_score(value_score):>12} "
              f"{format_score(quality_score):>12}")
    
    print()
    
    # Show score distribution
    print("=" * 80)
    print("SCORE DISTRIBUTION")
    print("=" * 80)
    
    if 'domain_score' in passed_df.columns:
        print(f"\nDomain Score Statistics:")
        print(f"  Mean:   {passed_df['domain_score'].mean():.1f}")
        print(f"  Median: {passed_df['domain_score'].median():.1f}")
        print(f"  Std:    {passed_df['domain_score'].std():.1f}")
        print(f"  Min:    {passed_df['domain_score'].min():.1f}")
        print(f"  Max:    {passed_df['domain_score'].max():.1f}")
    
    print()
    
    # Show portfolio size estimate
    print("=" * 80)
    print("PORTFOLIO SELECTION ESTIMATE")
    print("=" * 80)
    
    # Simulate vertical + horizontal selection
    vertical_candidates = {}
    for sector in sectors:
        sector_df = passed_df[passed_df['sector'] == sector].copy()
        sector_df = sector_df.sort_values('domain_score', ascending=False)
        top_k = sector_df.head(analysis_config.top_k_per_sector)
        if len(top_k) > 0:
            vertical_candidates[sector] = top_k
    
    # Combine all vertical candidates
    all_candidates = pd.concat(vertical_candidates.values(), ignore_index=True)
    all_candidates = all_candidates.sort_values('domain_score', ascending=False)
    
    final_portfolio = all_candidates.head(analysis_config.portfolio_size)
    
    print(f"\nEstimated Final Portfolio ({len(final_portfolio)} stocks):")
    print("-" * 80)
    print(f"{'Rank':<6} {'Ticker':<8} {'Sector':<20} {'Domain':>8} {'Weight Est':>12}")
    print("-" * 80)
    
    # Estimate weights (score-weighted)
    domain_scores = final_portfolio['domain_score'].values
    weights = domain_scores / domain_scores.sum()
    
    for rank, (idx, row) in enumerate(final_portfolio.iterrows(), 1):
        ticker = row.get('ticker', 'N/A')
        sector = row.get('sector', 'N/A')
        domain_score = row.get('domain_score', 0)
        weight = weights[rank - 1] * 100
        
        print(f"{rank:<6} {ticker:<8} {sector:<20} {format_score(domain_score):>12} {weight:>11.1f}%")
    
    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Display purchase triggers for a backtest run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show triggers for latest run
  python scripts/show_purchase_triggers.py
  
  # Show triggers for specific run
  python scripts/show_purchase_triggers.py --run-id 20241231_123456_abc
  
  # Filter by sector
  python scripts/show_purchase_triggers.py --sector Technology
  
  # Show top 30 stocks
  python scripts/show_purchase_triggers.py --top-n 30
  
  # Show all stocks including failed filters
  python scripts/show_purchase_triggers.py --show-all
        """
    )
    
    parser.add_argument("--run-id", type=str, help="Specific run ID (default: latest)")
    parser.add_argument("--sector", type=str, help="Filter by sector name")
    parser.add_argument("--top-n", type=int, default=20, help="Number of top stocks to show (default: 20)")
    parser.add_argument("--show-all", action="store_true", help="Show all stocks including failed filters")
    
    args = parser.parse_args()
    
    try:
        display_purchase_triggers(
            run_id=args.run_id,
            sector_filter=args.sector,
            top_n=args.top_n,
            show_all=args.show_all
        )
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
