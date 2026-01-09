#!/usr/bin/env python3
"""
Stress Testing Module
======================

Simulates portfolio behavior under hypothetical stress scenarios:

1. MARKET CRASHES: Tech crash, energy crash, broad market decline
2. RATE SHOCKS: Rising rates, falling rates, inverted yield curve
3. SECTOR ROTATIONS: Value to growth, growth to value
4. CUSTOM SCENARIOS: User-defined shocks

Usage:
    python scripts/stress_testing.py --run-dir output/run_everything_20260102_160327_
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import json


# =============================================================================
# SCENARIO DEFINITIONS
# =============================================================================

STRESS_SCENARIOS = {
    'tech_crash_30': {
        'name': 'Tech Crash (-30%)',
        'description': 'Technology sector drops 30%, other sectors drop 10%',
        'shocks': {
            'Technology': -0.30,
            'Communication Services': -0.25,
            'default': -0.10,
        }
    },
    'energy_crash_40': {
        'name': 'Energy Crash (-40%)',
        'description': 'Energy and uranium sectors drop 40%',
        'shocks': {
            'Energy': -0.40,
            'Utilities': -0.20,
            'default': -0.05,
        }
    },
    'rate_spike': {
        'name': 'Rate Spike',
        'description': 'Sharp rate increase crushes growth stocks',
        'shocks': {
            'Technology': -0.25,
            'Real Estate': -0.20,
            'Utilities': -0.15,
            'Financial Services': 0.05,
            'Energy': 0.10,
            'default': -0.08,
        }
    },
    'broad_bear': {
        'name': 'Broad Bear Market (-25%)',
        'description': 'General 25% market decline',
        'shocks': {
            'Consumer Defensive': -0.12,
            'Healthcare': -0.15,
            'Utilities': -0.10,
            'default': -0.25,
        }
    },
    'ai_bubble_pop': {
        'name': 'AI Bubble Pop',
        'description': 'AI-related stocks crash 50%',
        'ticker_shocks': {
            'NVDA': -0.50, 'AMD': -0.40, 'MSFT': -0.30, 'GOOGL': -0.35,
            'META': -0.35, 'PLTR': -0.55, 'UPST': -0.60, 'AI': -0.55,
        },
        'shocks': {'default': -0.10}
    },
    'ev_washout': {
        'name': 'EV/Clean Energy Washout',
        'description': 'EV and clean energy stocks crash 50%',
        'ticker_shocks': {
            'TSLA': -0.45, 'RIVN': -0.60, 'LCID': -0.65, 'NIO': -0.55,
            'PLUG': -0.60, 'ENPH': -0.50, 'SEDG': -0.55, 'RUN': -0.50,
        },
        'shocks': {'default': -0.08}
    },
    'inflation_surge': {
        'name': 'Inflation Surge',
        'description': 'Unexpected inflation spike hurts growth, helps commodities',
        'shocks': {
            'Technology': -0.20,
            'Consumer Discretionary': -0.25,
            'Consumer Cyclical': -0.25,
            'Energy': 0.15,
            'Basic Materials': 0.10,
            'default': -0.10,
        }
    },
}


# =============================================================================
# STRESS TESTING FUNCTIONS
# =============================================================================

def apply_scenario(
    positions: pd.DataFrame,
    scenario: Dict,
    sector_map: Dict[str, str]
) -> Dict:
    """
    Apply a stress scenario to portfolio positions.
    
    Returns impact on portfolio value.
    """
    # Get latest positions
    latest_date = positions['date'].max()
    latest_pos = positions[positions['date'] == latest_date].copy()
    
    # Apply shocks
    shocks = scenario.get('shocks', {})
    ticker_shocks = scenario.get('ticker_shocks', {})
    default_shock = shocks.get('default', 0)
    
    impacts = []
    for _, row in latest_pos.iterrows():
        ticker = row['ticker']
        weight = row['weight']
        
        # Check for ticker-specific shock
        if ticker in ticker_shocks:
            shock = ticker_shocks[ticker]
        else:
            # Use sector-based shock
            sector = sector_map.get(ticker, 'Other')
            shock = shocks.get(sector, default_shock)
        
        impact = weight * shock
        impacts.append({
            'ticker': ticker,
            'sector': sector_map.get(ticker, 'Other'),
            'weight': float(weight),
            'shock': float(shock),
            'impact': float(impact),
        })
    
    total_impact = sum(i['impact'] for i in impacts)
    
    return {
        'scenario': scenario['name'],
        'description': scenario['description'],
        'total_impact': float(total_impact),
        'position_impacts': sorted(impacts, key=lambda x: x['impact'])[:10],
    }


def run_all_scenarios(run_dir: Path) -> Dict:
    """
    Run all stress scenarios on a portfolio.
    """
    print("\n" + "=" * 70)
    print("STRESS TESTING ANALYSIS")
    print("=" * 70)
    print(f"Run: {run_dir.name}")
    
    # Load positions
    positions = pd.read_csv(run_dir / 'backtest_positions.csv', parse_dates=['date'])
    
    # Load sector data
    sector_map = {}
    if Path('data/sectors.csv').exists():
        sectors_df = pd.read_csv('data/sectors.csv')
        sector_map = dict(zip(sectors_df['ticker'], sectors_df['sector']))
    
    results = {}
    
    print("\n📊 SCENARIO IMPACT SUMMARY:")
    print("-" * 70)
    print(f"{'Scenario':<30} {'Impact':>12} {'Status':<15}")
    print("-" * 70)
    
    for scenario_id, scenario in STRESS_SCENARIOS.items():
        impact = apply_scenario(positions, scenario, sector_map)
        results[scenario_id] = impact
        
        pct = impact['total_impact'] * 100
        if pct < -30:
            status = "❌ SEVERE"
        elif pct < -20:
            status = "⚠️ HIGH"
        elif pct < -10:
            status = "⚠️ MODERATE"
        else:
            status = "✅ CONTAINED"
        
        print(f"{scenario['name']:<30} {pct:>11.1f}% {status}")
    
    # Worst scenario
    worst = min(results.values(), key=lambda x: x['total_impact'])
    
    print("\n" + "-" * 70)
    print(f"⚡ WORST CASE: {worst['scenario']}")
    print(f"   Portfolio impact: {worst['total_impact']*100:.1f}%")
    print(f"   Description: {worst['description']}")
    
    print("\n   Top 5 position impacts:")
    for pos in worst['position_impacts'][:5]:
        print(f"     {pos['ticker']:<8} ({pos['sector']:<20}): {pos['impact']*100:+.1f}%")
    
    # Save results
    report_path = run_dir / 'stress_test_results.json'
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n📁 Report saved: {report_path}")
    
    return results


def simulate_position_reduction(run_dir: Path, reduction_pct: float = 0.50) -> Dict:
    """
    Simulate effect of reducing position sizes by a percentage.
    """
    print("\n" + "=" * 70)
    print(f"POSITION SIZE REDUCTION SIMULATION ({reduction_pct*100:.0f}% reduction)")
    print("=" * 70)
    
    # Load metrics
    metrics_files = list(run_dir.glob('backtest_metrics.json'))
    if not metrics_files:
        print("No metrics found")
        return {}
    
    with open(metrics_files[0]) as f:
        metrics = json.load(f)
    
    # Original metrics
    orig_vol = metrics.get('annualized_volatility', 0.50)
    orig_return = metrics.get('annualized_return', 0.20)
    orig_dd = metrics.get('max_drawdown', -0.40)
    orig_sharpe = metrics.get('sharpe_ratio', 0.5)
    
    # Reduced exposure simulation
    # Assuming remainder goes to cash (0% return, 0% vol)
    reduced_vol = orig_vol * reduction_pct
    reduced_return = orig_return * reduction_pct
    reduced_dd = orig_dd * reduction_pct  # Simplified approximation
    reduced_sharpe = reduced_return / reduced_vol if reduced_vol > 0 else 0
    
    print("\n📊 IMPACT OF POSITION REDUCTION:")
    print("-" * 60)
    print(f"{'Metric':<25} {'Original':>15} {'Reduced':>15}")
    print("-" * 60)
    print(f"{'Exposure':25} {'100%':>15} {reduction_pct*100:>14.0f}%")
    print(f"{'Ann. Return':25} {orig_return*100:>14.1f}% {reduced_return*100:>14.1f}%")
    print(f"{'Ann. Volatility':25} {orig_vol*100:>14.1f}% {reduced_vol*100:>14.1f}%")
    print(f"{'Max Drawdown':25} {orig_dd*100:>14.1f}% {reduced_dd*100:>14.1f}%")
    print(f"{'Sharpe Ratio':25} {orig_sharpe:>15.2f} {reduced_sharpe:>15.2f}")
    
    return {
        'original': {
            'volatility': orig_vol,
            'return': orig_return,
            'drawdown': orig_dd,
            'sharpe': orig_sharpe,
        },
        'reduced': {
            'reduction': reduction_pct,
            'volatility': reduced_vol,
            'return': reduced_return,
            'drawdown': reduced_dd,
            'sharpe': reduced_sharpe,
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Stress testing analysis")
    parser.add_argument("--run-dir", help="Run directory to analyze")
    parser.add_argument("--run-id", help="Run ID to find")
    parser.add_argument("--reduction", type=float, default=0.50,
                        help="Position reduction percentage for simulation")
    
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
    
    # Run stress tests
    run_all_scenarios(run_dir)
    
    # Run position reduction simulation
    simulate_position_reduction(run_dir, args.reduction)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
