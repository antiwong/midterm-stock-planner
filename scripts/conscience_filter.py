#!/usr/bin/env python3
"""
Conscience Filter Module
=========================

Apply ethical/conscience-based filters to portfolio holdings:

1. INDUSTRY EXCLUSIONS: Weapons, gambling, tobacco, alcohol, etc.
2. ESG CONSIDERATIONS: Environmental, social, governance factors
3. PERSONAL VALUES: Custom exclusion lists
4. SECTOR CAPS: Limit exposure to specific sectors/themes

Usage:
    python scripts/conscience_filter.py --run-dir output/run_everything_20260102_160327_
    python scripts/conscience_filter.py --exclude-sectors "Energy,Basic Materials"
    python scripts/conscience_filter.py --exclude-tickers "XOM,CVX,MO"
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import json


# =============================================================================
# CONSCIENCE FILTER DEFINITIONS
# =============================================================================

# Industry exclusion categories
EXCLUSION_CATEGORIES = {
    'weapons': {
        'name': 'Defense & Weapons',
        'description': 'Companies primarily engaged in weapons manufacturing',
        'tickers': ['LMT', 'RTX', 'NOC', 'GD', 'BA', 'HII', 'LHX', 'TXT', 'KTOS', 'AVAV'],
    },
    'tobacco': {
        'name': 'Tobacco & Nicotine',
        'description': 'Tobacco and nicotine product manufacturers',
        'tickers': ['MO', 'PM', 'BTI', 'IMBBY', 'TPB', 'VGR'],
    },
    'alcohol': {
        'name': 'Alcohol & Spirits',
        'description': 'Alcoholic beverage producers',
        'tickers': ['BUD', 'DEO', 'STZ', 'BF.B', 'TAP', 'SAM', 'ABEV'],
    },
    'gambling': {
        'name': 'Gambling & Casinos',
        'description': 'Gaming, gambling, and casino operators',
        'tickers': ['LVS', 'WYNN', 'MGM', 'CZR', 'DKNG', 'PENN', 'BYD', 'GDEN', 'RRR'],
    },
    'adult_entertainment': {
        'name': 'Adult Entertainment',
        'description': 'Adult content and entertainment',
        'tickers': [],  # Generally not publicly traded
    },
    'predatory_finance': {
        'name': 'Predatory Finance',
        'description': 'Payday loans, subprime lending, high-interest consumer finance',
        'tickers': ['CURO', 'ENVA', 'OMF', 'SYF'],  # Some controversial names
    },
    'fossil_fuels': {
        'name': 'Fossil Fuels',
        'description': 'Oil, gas, and coal extraction',
        'tickers': ['XOM', 'CVX', 'COP', 'EOG', 'OXY', 'DVN', 'HAL', 'SLB', 'MPC', 'VLO',
                    'PSX', 'FANG', 'HES', 'APA', 'MRO', 'BTU', 'ARCH', 'CEIX'],
    },
    'private_prisons': {
        'name': 'Private Prisons',
        'description': 'Private prison and detention operators',
        'tickers': ['GEO', 'CXW'],
    },
}

# ESG concern flags (informational, not automatic exclusion)
ESG_CONCERNS = {
    'environmental': {
        'high_emissions': ['XOM', 'CVX', 'COP', 'AA', 'NUE', 'X'],
        'deforestation_risk': [],
        'water_intensive': ['NEM', 'GOLD', 'FCX'],
    },
    'social': {
        'labor_concerns': [],
        'data_privacy': ['META', 'GOOGL', 'AMZN'],
        'controversial_products': ['MO', 'PM', 'LMT'],
    },
    'governance': {
        'dual_class_shares': ['GOOGL', 'META', 'SNAP', 'PINS'],
        'executive_pay_concerns': [],
    }
}


# =============================================================================
# FILTER FUNCTIONS
# =============================================================================

def get_exclusion_set(categories: List[str]) -> Set[str]:
    """
    Build set of excluded tickers from category names.
    """
    excluded = set()
    for cat in categories:
        cat_lower = cat.lower().replace(' ', '_')
        if cat_lower in EXCLUSION_CATEGORIES:
            excluded.update(EXCLUSION_CATEGORIES[cat_lower]['tickers'])
    return excluded


def apply_conscience_filter(
    positions: pd.DataFrame,
    exclude_categories: List[str] = None,
    exclude_tickers: List[str] = None,
    exclude_sectors: List[str] = None,
    sector_map: Dict[str, str] = None,
) -> Dict:
    """
    Apply conscience filters to portfolio positions.
    
    Returns:
    - filtered_positions: Positions after exclusions
    - exclusion_report: Details of what was excluded
    """
    # Get latest positions
    latest_date = positions['date'].max()
    latest_pos = positions[positions['date'] == latest_date].copy()
    
    # Build exclusion set
    excluded_tickers = set()
    exclusion_reasons = {}
    
    # Category-based exclusions
    if exclude_categories:
        for cat in exclude_categories:
            cat_lower = cat.lower().replace(' ', '_')
            if cat_lower in EXCLUSION_CATEGORIES:
                cat_info = EXCLUSION_CATEGORIES[cat_lower]
                for ticker in cat_info['tickers']:
                    if ticker in latest_pos['ticker'].values:
                        excluded_tickers.add(ticker)
                        exclusion_reasons[ticker] = f"Category: {cat_info['name']}"
    
    # Direct ticker exclusions
    if exclude_tickers:
        for ticker in exclude_tickers:
            ticker_upper = ticker.upper()
            if ticker_upper in latest_pos['ticker'].values:
                excluded_tickers.add(ticker_upper)
                exclusion_reasons[ticker_upper] = "Direct exclusion"
    
    # Sector-based exclusions
    if exclude_sectors and sector_map:
        for _, row in latest_pos.iterrows():
            ticker = row['ticker']
            sector = sector_map.get(ticker, 'Other')
            if sector in exclude_sectors:
                excluded_tickers.add(ticker)
                exclusion_reasons[ticker] = f"Sector: {sector}"
    
    # Calculate impact
    excluded_weight = 0
    excluded_details = []
    
    for ticker in excluded_tickers:
        pos = latest_pos[latest_pos['ticker'] == ticker]
        if not pos.empty:
            weight = pos['weight'].values[0]
            excluded_weight += weight
            excluded_details.append({
                'ticker': ticker,
                'weight': float(weight),
                'reason': exclusion_reasons.get(ticker, 'Unknown'),
                'sector': sector_map.get(ticker, 'Other') if sector_map else 'Unknown',
            })
    
    # Create filtered positions
    filtered_pos = latest_pos[~latest_pos['ticker'].isin(excluded_tickers)].copy()
    
    # Renormalize weights
    if len(filtered_pos) > 0:
        total_remaining = filtered_pos['weight'].sum()
        filtered_pos['weight'] = filtered_pos['weight'] / total_remaining
    
    return {
        'original_positions': len(latest_pos),
        'filtered_positions': len(filtered_pos),
        'excluded_count': len(excluded_tickers),
        'excluded_weight': float(excluded_weight),
        'exclusion_details': sorted(excluded_details, key=lambda x: -x['weight']),
        'filtered_df': filtered_pos,
    }


def check_esg_concerns(positions: pd.DataFrame) -> Dict:
    """
    Check positions against ESG concern flags (informational).
    """
    latest_date = positions['date'].max()
    latest_pos = positions[positions['date'] == latest_date]
    
    concerns = {}
    
    for category, subcats in ESG_CONCERNS.items():
        concerns[category] = {}
        for subcat, tickers in subcats.items():
            flagged = []
            for ticker in tickers:
                pos = latest_pos[latest_pos['ticker'] == ticker]
                if not pos.empty:
                    flagged.append({
                        'ticker': ticker,
                        'weight': float(pos['weight'].values[0]),
                    })
            if flagged:
                concerns[category][subcat] = flagged
    
    return concerns


def run_conscience_analysis(
    run_dir: Path,
    exclude_categories: List[str] = None,
    exclude_tickers: List[str] = None,
    exclude_sectors: List[str] = None,
) -> Dict:
    """
    Run conscience filter analysis on a portfolio.
    """
    print("\n" + "=" * 70)
    print("CONSCIENCE FILTER ANALYSIS")
    print("=" * 70)
    print(f"Run: {run_dir.name}")
    
    # Load positions
    positions = pd.read_csv(run_dir / 'backtest_positions.csv', parse_dates=['date'])
    
    # Load sector data
    sector_map = {}
    if Path('data/sectors.csv').exists():
        sectors_df = pd.read_csv('data/sectors.csv')
        sector_map = dict(zip(sectors_df['ticker'], sectors_df['sector']))
    
    # Default exclusions (can be customized)
    if exclude_categories is None:
        exclude_categories = []
    
    # Show available categories
    print("\n📋 AVAILABLE EXCLUSION CATEGORIES:")
    print("-" * 50)
    for cat_id, cat_info in EXCLUSION_CATEGORIES.items():
        print(f"  • {cat_id}: {cat_info['name']}")
    
    # Check for concerning positions (without filtering)
    print("\n🔍 SCANNING FOR POTENTIALLY CONCERNING HOLDINGS:")
    print("-" * 70)
    
    latest_date = positions['date'].max()
    latest_pos = positions[positions['date'] == latest_date]
    
    found_concerns = False
    for cat_id, cat_info in EXCLUSION_CATEGORIES.items():
        cat_holdings = []
        for ticker in cat_info['tickers']:
            pos = latest_pos[latest_pos['ticker'] == ticker]
            if not pos.empty:
                cat_holdings.append({
                    'ticker': ticker,
                    'weight': float(pos['weight'].values[0]),
                })
        
        if cat_holdings:
            found_concerns = True
            total_weight = sum(h['weight'] for h in cat_holdings)
            print(f"\n  ⚠️ {cat_info['name']} ({total_weight*100:.1f}% total):")
            for h in sorted(cat_holdings, key=lambda x: -x['weight']):
                print(f"     {h['ticker']}: {h['weight']*100:.1f}%")
    
    if not found_concerns:
        print("  ✅ No holdings in predefined exclusion categories")
    
    # ESG Concerns (informational)
    print("\n📊 ESG CONCERN FLAGS (Informational):")
    print("-" * 70)
    
    esg = check_esg_concerns(positions)
    has_esg = False
    
    for category, subcats in esg.items():
        if subcats:
            has_esg = True
            print(f"\n  {category.upper()}:")
            for subcat, holdings in subcats.items():
                print(f"    • {subcat.replace('_', ' ').title()}:")
                for h in holdings:
                    print(f"        {h['ticker']}: {h['weight']*100:.1f}%")
    
    if not has_esg:
        print("  ✅ No significant ESG flags")
    
    # Apply filters if specified
    results = {}
    if exclude_categories or exclude_tickers or exclude_sectors:
        print("\n" + "=" * 70)
        print("APPLYING FILTERS")
        print("=" * 70)
        
        filter_result = apply_conscience_filter(
            positions,
            exclude_categories=exclude_categories,
            exclude_tickers=exclude_tickers,
            exclude_sectors=exclude_sectors,
            sector_map=sector_map,
        )
        results['filter_result'] = filter_result
        
        print(f"\n📊 FILTER IMPACT:")
        print("-" * 50)
        print(f"  Original positions:  {filter_result['original_positions']}")
        print(f"  Excluded positions:  {filter_result['excluded_count']}")
        print(f"  Remaining positions: {filter_result['filtered_positions']}")
        print(f"  Excluded weight:     {filter_result['excluded_weight']*100:.1f}%")
        
        if filter_result['exclusion_details']:
            print("\n  Excluded holdings:")
            for ex in filter_result['exclusion_details'][:10]:
                print(f"    {ex['ticker']:<8} ({ex['weight']*100:.1f}%): {ex['reason']}")
        
        # Save filtered positions
        if len(filter_result['filtered_df']) > 0:
            filtered_path = run_dir / 'filtered_positions_conscience.csv'
            filter_result['filtered_df'].to_csv(filtered_path, index=False)
            print(f"\n📁 Filtered positions saved: {filtered_path}")
    
    results['esg_concerns'] = esg
    
    # Save report
    report = {
        'timestamp': datetime.now().isoformat(),
        'run_id': run_dir.name,
        'esg_concerns': esg,
    }
    if 'filter_result' in results:
        report['filter_result'] = {
            k: v for k, v in results['filter_result'].items() 
            if k != 'filtered_df'
        }
    
    report_path = run_dir / 'conscience_filter_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\n📁 Report saved: {report_path}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Conscience filter analysis")
    parser.add_argument("--run-dir", help="Run directory to analyze")
    parser.add_argument("--run-id", help="Run ID to find")
    parser.add_argument("--exclude-categories", type=str,
                        help="Comma-separated categories to exclude (e.g., 'weapons,tobacco,gambling')")
    parser.add_argument("--exclude-tickers", type=str,
                        help="Comma-separated tickers to exclude (e.g., 'XOM,CVX,MO')")
    parser.add_argument("--exclude-sectors", type=str,
                        help="Comma-separated sectors to exclude (e.g., 'Energy,Basic Materials')")
    
    args = parser.parse_args()
    
    # Find run directory
    if args.run_dir:
        run_dir = Path(args.run_dir)
    elif args.run_id:
        matches = list(Path('output').glob(f"*{args.run_id}*"))
        if not matches:
            print(f"No run found: {args.run_id}")
            return 1
        run_dir = matches[0]
    else:
        runs = sorted(Path('output').glob("run_*"))
        if not runs:
            print("No runs found")
            return 1
        run_dir = runs[-1]
    
    # Parse exclusions
    exclude_cats = args.exclude_categories.split(',') if args.exclude_categories else None
    exclude_tickers = args.exclude_tickers.split(',') if args.exclude_tickers else None
    exclude_sectors = args.exclude_sectors.split(',') if args.exclude_sectors else None
    
    run_conscience_analysis(
        run_dir,
        exclude_categories=exclude_cats,
        exclude_tickers=exclude_tickers,
        exclude_sectors=exclude_sectors,
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
