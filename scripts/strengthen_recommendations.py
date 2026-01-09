#!/usr/bin/env python3
"""
Recommendation Strengthening Analysis
======================================

Comprehensive analysis to validate and strengthen portfolio recommendations:

1. DOWNSIDE & TAIL RISK: Worst-case outcomes, drawdown duration
2. SCENARIO & REGIME ANALYSIS: Sub-period and regime-based performance
3. POSITION-LEVEL DIAGNOSTICS: Individual stock risk flags
4. THEMATIC & SECTOR DEPENDENCE: Theme concentration and correlations
5. CONSCIENCE FILTERS: Exclude sectors/stocks based on values
6. SIZING RECOMMENDATIONS: Capital allocation guidance

Usage:
    python scripts/strengthen_recommendations.py --run-id <RUN_ID>
    python scripts/strengthen_recommendations.py --run-id <RUN_ID> --exclude-sectors "Energy,Defense"
    python scripts/strengthen_recommendations.py --run-id <RUN_ID> --full (runs all analyses)
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import json
import yaml


# =============================================================================
# 1. REGIME ANALYSIS
# =============================================================================

def classify_market_regime(
    benchmark_returns: pd.Series,
    lookback: int = 252
) -> pd.DataFrame:
    """
    Classify market into regimes based on trend and volatility.
    
    Regimes:
    - Bull/Bear: Based on rolling return (positive/negative)
    - High/Low Vol: Based on rolling volatility vs median
    """
    # Rolling metrics
    rolling_return = benchmark_returns.rolling(lookback).mean() * 252  # Annualized
    rolling_vol = benchmark_returns.rolling(lookback).std() * np.sqrt(252)
    
    # Classification
    regimes = pd.DataFrame(index=benchmark_returns.index)
    regimes['trend'] = np.where(rolling_return > 0, 'Bull', 'Bear')
    regimes['volatility'] = np.where(
        rolling_vol > rolling_vol.median(), 
        'High Vol', 
        'Low Vol'
    )
    regimes['regime'] = regimes['trend'] + ' / ' + regimes['volatility']
    regimes['benchmark_return'] = benchmark_returns
    regimes['rolling_vol'] = rolling_vol
    
    return regimes


def analyze_regime_performance(
    portfolio_returns: pd.Series,
    regimes: pd.DataFrame
) -> Dict[str, Dict[str, float]]:
    """
    Analyze portfolio performance across different market regimes.
    """
    results = {}
    
    # Align returns with regimes
    aligned = pd.DataFrame({
        'portfolio': portfolio_returns,
        'regime': regimes['regime']
    }).dropna()
    
    for regime in aligned['regime'].unique():
        regime_returns = aligned[aligned['regime'] == regime]['portfolio']
        
        if len(regime_returns) < 20:  # Minimum sample size
            continue
        
        total_ret = (1 + regime_returns).prod() - 1
        ann_ret = (1 + total_ret) ** (252 / len(regime_returns)) - 1
        vol = regime_returns.std() * np.sqrt(252)
        sharpe = ann_ret / vol if vol > 0 else 0
        
        # Max drawdown in regime
        cum = (1 + regime_returns).cumprod()
        max_dd = (cum / cum.cummax() - 1).min()
        
        results[regime] = {
            'days': len(regime_returns),
            'total_return': float(total_ret),
            'annualized_return': float(ann_ret),
            'volatility': float(vol),
            'sharpe': float(sharpe),
            'max_drawdown': float(max_dd),
            'win_rate': float((regime_returns > 0).mean())
        }
    
    return results


def run_regime_analysis(run_dir: Path) -> Dict:
    """Run complete regime analysis for a backtest run."""
    
    print("\n" + "=" * 70)
    print("1. REGIME ANALYSIS")
    print("=" * 70)
    
    # Load returns
    returns_file = run_dir / 'backtest_returns.csv'
    returns = pd.read_csv(returns_file, parse_dates=['date'], index_col='date')
    
    # Load benchmark
    bench = pd.read_csv('data/benchmark.csv', parse_dates=['date'], index_col='date')
    bench_returns = bench['close'].pct_change().dropna()
    
    # Classify regimes
    regimes = classify_market_regime(bench_returns)
    
    # Get portfolio returns
    port_returns = returns['portfolio_return']
    
    # Analyze by regime
    regime_perf = analyze_regime_performance(port_returns, regimes)
    
    # Display results
    print("\nPerformance by Market Regime:")
    print("-" * 70)
    print(f"{'Regime':<25} {'Days':>6} {'Return':>10} {'Vol':>8} {'Sharpe':>8} {'MaxDD':>10}")
    print("-" * 70)
    
    for regime, metrics in sorted(regime_perf.items()):
        print(f"{regime:<25} {metrics['days']:>6} "
              f"{metrics['annualized_return']*100:>9.1f}% "
              f"{metrics['volatility']*100:>7.1f}% "
              f"{metrics['sharpe']:>8.2f} "
              f"{metrics['max_drawdown']*100:>9.1f}%")
    
    # Check for one-regime wonder
    print("\n" + "-" * 70)
    returns_by_regime = [m['annualized_return'] for m in regime_perf.values()]
    if returns_by_regime:
        best = max(returns_by_regime)
        worst = min(returns_by_regime)
        
        if worst < 0 and best > 0.20:
            print("⚠️  WARNING: Strategy is regime-dependent")
            print(f"   Best regime: {best*100:.1f}%, Worst regime: {worst*100:.1f}%")
        elif all(r > 0 for r in returns_by_regime):
            print("✅ Strategy is profitable across all regimes")
        else:
            print("⚠️  Mixed regime performance - review before allocating")
    
    return {'regime_performance': regime_perf}


# =============================================================================
# 2. FACTOR EXPOSURE ANALYSIS (SHAP-based)
# =============================================================================

def calculate_factor_contributions(
    enriched_df: pd.DataFrame,
    score_cols: List[str] = None
) -> Dict[str, float]:
    """
    Calculate factor contributions to portfolio scores using variance decomposition.
    
    This is a SHAP-like analysis that shows how much each factor contributes
    to the overall score variation.
    """
    if score_cols is None:
        score_cols = ['value_score', 'quality_score', 'momentum_score', 
                      'tech_score', 'model_score']
    
    available = [c for c in score_cols if c in enriched_df.columns]
    
    if not available:
        return {}
    
    contributions = {}
    total_var = 0
    
    for col in available:
        var = enriched_df[col].var()
        if pd.notna(var) and var > 0:
            contributions[col] = var
            total_var += var
    
    # Normalize to percentages
    if total_var > 0:
        contributions = {k: v/total_var for k, v in contributions.items()}
    
    return contributions


def analyze_factor_exposure(run_dir: Path) -> Dict:
    """Run factor exposure analysis."""
    
    print("\n" + "=" * 70)
    print("2. FACTOR EXPOSURE ANALYSIS (SHAP-like)")
    print("=" * 70)
    
    # Load enriched portfolio
    enriched_files = list(run_dir.glob('portfolio_enriched_*.csv'))
    if not enriched_files:
        print("⚠️  No enriched portfolio data available")
        return {}
    
    enriched = pd.read_csv(enriched_files[0])
    
    # Calculate contributions
    contributions = calculate_factor_contributions(enriched)
    
    if not contributions:
        print("⚠️  No factor scores available for analysis")
        return {}
    
    print("\nFactor Contributions to Portfolio:")
    print("-" * 50)
    print(f"{'Factor':<25} {'Contribution':>12} {'Status':>10}")
    print("-" * 50)
    
    max_contrib = max(contributions.values())
    dominant_factor = max(contributions, key=contributions.get)
    
    for factor, contrib in sorted(contributions.items(), key=lambda x: -x[1]):
        status = "❌ HIGH" if contrib > 0.50 else ("⚠️" if contrib > 0.35 else "✅")
        bar = "█" * int(contrib * 30)
        print(f"{factor:<25} {contrib*100:>10.1f}% {status}")
        print(f"  {bar}")
    
    print("-" * 50)
    
    if max_contrib > 0.50:
        print(f"\n❌ FAIL: Factor '{dominant_factor}' contributes {max_contrib*100:.1f}%")
        print("   Consider diversifying factor exposures")
    elif max_contrib > 0.35:
        print(f"\n⚠️  WARNING: Factor '{dominant_factor}' is dominant ({max_contrib*100:.1f}%)")
    else:
        print("\n✅ PASS: No single factor dominates (all <35%)")
    
    return {'factor_contributions': contributions, 'dominant_factor': dominant_factor}


# =============================================================================
# 3. STRESS TESTING
# =============================================================================

def stress_test_position_sizing(
    returns: pd.Series,
    scaling_factors: List[float] = [1.0, 0.75, 0.50, 0.25]
) -> Dict[str, Dict[str, float]]:
    """
    Stress test portfolio by simulating different position sizes.
    
    Scaling factor of 0.5 means investing only 50% of capital,
    keeping 50% in cash (assumed 0% return).
    """
    results = {}
    
    for scale in scaling_factors:
        # Scale returns (rest in cash at 0%)
        scaled_returns = returns * scale
        
        # Calculate metrics
        cum = (1 + scaled_returns).cumprod()
        total_ret = cum.iloc[-1] - 1
        years = len(scaled_returns) / 252
        ann_ret = (1 + total_ret) ** (1/years) - 1 if years > 0 else 0
        vol = scaled_returns.std() * np.sqrt(252)
        sharpe = ann_ret / vol if vol > 0 else 0
        max_dd = (cum / cum.cummax() - 1).min()
        
        results[f"{int(scale*100)}%"] = {
            'scale': scale,
            'total_return': float(total_ret),
            'annualized_return': float(ann_ret),
            'volatility': float(vol),
            'sharpe': float(sharpe),
            'max_drawdown': float(max_dd),
            'capital_at_risk': float(scale)
        }
    
    return results


def run_stress_testing(run_dir: Path) -> Dict:
    """Run stress testing analysis."""
    
    print("\n" + "=" * 70)
    print("3. STRESS TESTING (Position Sizing)")
    print("=" * 70)
    
    # Load returns
    returns_file = run_dir / 'backtest_returns.csv'
    returns = pd.read_csv(returns_file, parse_dates=['date'])
    port_returns = returns['portfolio_return']
    
    # Run stress tests
    stress_results = stress_test_position_sizing(port_returns)
    
    print("\nPosition Sizing Impact:")
    print("-" * 70)
    print(f"{'Allocation':>10} {'Return':>10} {'Vol':>8} {'Sharpe':>8} {'MaxDD':>10} {'Capital':>10}")
    print("-" * 70)
    
    for alloc, metrics in stress_results.items():
        print(f"{alloc:>10} "
              f"{metrics['annualized_return']*100:>9.1f}% "
              f"{metrics['volatility']*100:>7.1f}% "
              f"{metrics['sharpe']:>8.2f} "
              f"{metrics['max_drawdown']*100:>9.1f}% "
              f"{metrics['capital_at_risk']*100:>9.0f}%")
    
    print("-" * 70)
    
    # Recommendation
    full_dd = stress_results['100%']['max_drawdown']
    half_dd = stress_results['50%']['max_drawdown']
    half_sharpe = stress_results['50%']['sharpe']
    
    print(f"\n💡 SIZING RECOMMENDATION:")
    print(f"   Full allocation: {full_dd*100:.1f}% max drawdown")
    print(f"   Half allocation: {half_dd*100:.1f}% max drawdown (Sharpe: {half_sharpe:.2f})")
    
    if abs(full_dd) > 0.50:
        print(f"   ⚠️  Consider 50% allocation to limit drawdown to {half_dd*100:.1f}%")
    else:
        print(f"   ✅ Full allocation acceptable if you can tolerate {full_dd*100:.1f}% drawdown")
    
    return {'stress_test': stress_results}


# =============================================================================
# 4. CONSCIENCE FILTERS
# =============================================================================

# Default exclusion lists (can be customized)
DEFAULT_EXCLUSIONS = {
    'sectors': [],  # e.g., ['Defense', 'Tobacco', 'Gambling']
    'industries': [],  # e.g., ['Weapons', 'Adult Entertainment']
    'tickers': [],  # Specific tickers to exclude
}

SECTOR_DESCRIPTIONS = {
    'Defense': 'Weapons manufacturers, defense contractors',
    'Tobacco': 'Cigarette and tobacco products',
    'Gambling': 'Casinos, sports betting, lottery',
    'Alcohol': 'Beer, wine, spirits producers',
    'Fossil Fuels': 'Oil, gas, coal extraction',
    'Private Prisons': 'For-profit incarceration',
    'Controversial': 'Stocks with ESG concerns',
}


def apply_conscience_filters(
    positions: pd.DataFrame,
    enriched: pd.DataFrame,
    exclude_sectors: List[str] = None,
    exclude_tickers: List[str] = None,
    sector_map: Dict[str, str] = None
) -> Tuple[pd.DataFrame, Dict]:
    """
    Apply conscience-based filters to exclude certain stocks.
    
    Returns filtered positions and exclusion report.
    """
    exclude_sectors = exclude_sectors or []
    exclude_tickers = exclude_tickers or []
    
    # Merge sector info
    if 'sector' not in positions.columns and sector_map:
        positions = positions.copy()
        positions['sector'] = positions['ticker'].map(sector_map).fillna('Other')
    
    original_count = positions['ticker'].nunique()
    excluded = []
    
    # Filter by sector
    if exclude_sectors and 'sector' in positions.columns:
        sector_excluded = positions[positions['sector'].isin(exclude_sectors)]
        excluded.extend([
            {'ticker': row['ticker'], 'reason': f"Sector: {row['sector']}"}
            for _, row in sector_excluded.drop_duplicates('ticker').iterrows()
        ])
        positions = positions[~positions['sector'].isin(exclude_sectors)]
    
    # Filter by specific tickers
    if exclude_tickers:
        ticker_excluded = positions[positions['ticker'].isin(exclude_tickers)]
        excluded.extend([
            {'ticker': row['ticker'], 'reason': 'Explicit exclusion'}
            for _, row in ticker_excluded.drop_duplicates('ticker').iterrows()
        ])
        positions = positions[~positions['ticker'].isin(exclude_tickers)]
    
    # Renormalize weights
    if len(positions) > 0:
        positions = positions.copy()
        for date in positions['date'].unique():
            mask = positions['date'] == date
            date_sum = positions.loc[mask, 'weight'].sum()
            if date_sum > 0:
                positions.loc[mask, 'weight'] = positions.loc[mask, 'weight'] / date_sum
    
    filtered_count = positions['ticker'].nunique()
    
    report = {
        'original_count': original_count,
        'filtered_count': filtered_count,
        'excluded_count': len(excluded),
        'excluded': excluded,
        'sectors_excluded': exclude_sectors,
        'tickers_excluded': exclude_tickers
    }
    
    return positions, report


def recalculate_metrics(positions: pd.DataFrame, price_data: pd.DataFrame) -> Dict:
    """
    Recalculate portfolio metrics after filtering.
    """
    # Merge prices
    merged = positions.merge(
        price_data[['date', 'ticker', 'close']],
        on=['date', 'ticker'],
        how='left'
    )
    
    # Calculate returns
    merged = merged.sort_values(['ticker', 'date'])
    merged['price_return'] = merged.groupby('ticker')['close'].pct_change()
    
    # Portfolio return per date
    daily_returns = merged.groupby('date').apply(
        lambda x: (x['weight'] * x['price_return']).sum()
    ).dropna()
    
    if len(daily_returns) == 0:
        return {}
    
    # Calculate metrics
    cum = (1 + daily_returns).cumprod()
    total_ret = cum.iloc[-1] - 1
    years = len(daily_returns) / 252
    ann_ret = (1 + total_ret) ** (1/years) - 1 if years > 0 else 0
    vol = daily_returns.std() * np.sqrt(252)
    sharpe = ann_ret / vol if vol > 0 else 0
    max_dd = (cum / cum.cummax() - 1).min()
    
    return {
        'total_return': float(total_ret),
        'annualized_return': float(ann_ret),
        'volatility': float(vol),
        'sharpe': float(sharpe),
        'max_drawdown': float(max_dd)
    }


def run_conscience_analysis(
    run_dir: Path,
    exclude_sectors: List[str] = None,
    exclude_tickers: List[str] = None
) -> Dict:
    """Run conscience filter analysis."""
    
    print("\n" + "=" * 70)
    print("4. CONSCIENCE FILTERS")
    print("=" * 70)
    
    # Load data
    positions = pd.read_csv(run_dir / 'backtest_positions.csv', parse_dates=['date'])
    
    # Load sector mapping
    sector_map = {}
    if Path('data/sectors.csv').exists():
        sectors = pd.read_csv('data/sectors.csv')
        sector_map = dict(zip(sectors['ticker'], sectors['sector']))
    
    # Apply filters
    filtered_pos, report = apply_conscience_filters(
        positions,
        None,  # enriched not needed if we have sector_map
        exclude_sectors=exclude_sectors,
        exclude_tickers=exclude_tickers,
        sector_map=sector_map
    )
    
    print(f"\nExclusion Criteria:")
    print(f"   Sectors: {exclude_sectors or 'None'}")
    print(f"   Tickers: {exclude_tickers or 'None'}")
    
    print(f"\nImpact:")
    print(f"   Original unique stocks: {report['original_count']}")
    print(f"   After filtering: {report['filtered_count']}")
    print(f"   Excluded: {report['excluded_count']}")
    
    if report['excluded']:
        print(f"\n   Excluded stocks:")
        for exc in report['excluded'][:10]:
            print(f"      - {exc['ticker']}: {exc['reason']}")
        if len(report['excluded']) > 10:
            print(f"      ... and {len(report['excluded']) - 10} more")
    
    # Recalculate metrics if we have price data
    if Path('data/prices.csv').exists() and len(filtered_pos) > 0:
        prices = pd.read_csv('data/prices.csv', parse_dates=['date'])
        
        # Original metrics
        orig_metrics = recalculate_metrics(positions, prices)
        
        # Filtered metrics
        filt_metrics = recalculate_metrics(filtered_pos, prices)
        
        if orig_metrics and filt_metrics:
            print(f"\nPerformance Comparison:")
            print("-" * 50)
            print(f"{'Metric':<20} {'Original':>12} {'Filtered':>12} {'Change':>10}")
            print("-" * 50)
            
            for key in ['annualized_return', 'volatility', 'sharpe', 'max_drawdown']:
                orig = orig_metrics.get(key, 0)
                filt = filt_metrics.get(key, 0)
                change = filt - orig
                
                if 'return' in key or 'vol' in key or 'draw' in key:
                    print(f"{key:<20} {orig*100:>11.1f}% {filt*100:>11.1f}% {change*100:>+9.1f}%")
                else:
                    print(f"{key:<20} {orig:>12.2f} {filt:>12.2f} {change:>+10.2f}")
            
            print("-" * 50)
            
            report['original_metrics'] = orig_metrics
            report['filtered_metrics'] = filt_metrics
    
    return report


# =============================================================================
# MAIN ANALYSIS RUNNER
# =============================================================================

def run_full_strengthening(
    run_dir: Path,
    exclude_sectors: List[str] = None,
    exclude_tickers: List[str] = None,
    save_report: bool = True,
    full_analysis: bool = False
) -> Dict:
    """
    Run all strengthening analyses.
    
    Args:
        run_dir: Path to the run directory
        exclude_sectors: Sectors to exclude in conscience filter
        exclude_tickers: Tickers to exclude in conscience filter
        save_report: Whether to save the report JSON
        full_analysis: Run extended analyses (tail risk, stress scenarios)
    """
    print("=" * 70)
    print("RECOMMENDATION STRENGTHENING ANALYSIS")
    print("=" * 70)
    print(f"Run: {run_dir.name}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    results = {
        'run_id': run_dir.name,
        'timestamp': datetime.now().isoformat(),
        'analyses': {}
    }
    
    # 1. Regime Analysis
    try:
        regime_results = run_regime_analysis(run_dir)
        results['analyses']['regime'] = regime_results
    except Exception as e:
        print(f"\n⚠️  Regime analysis failed: {e}")
        results['analyses']['regime'] = {'error': str(e)}
    
    # 2. Factor Exposure
    try:
        factor_results = analyze_factor_exposure(run_dir)
        results['analyses']['factor_exposure'] = factor_results
    except Exception as e:
        print(f"\n⚠️  Factor analysis failed: {e}")
        results['analyses']['factor_exposure'] = {'error': str(e)}
    
    # 3. Position Sizing Stress Test
    try:
        stress_results = run_stress_testing(run_dir)
        results['analyses']['stress_test'] = stress_results
    except Exception as e:
        print(f"\n⚠️  Stress testing failed: {e}")
        results['analyses']['stress_test'] = {'error': str(e)}
    
    # 4. Conscience Filters
    try:
        conscience_results = run_conscience_analysis(
            run_dir,
            exclude_sectors=exclude_sectors,
            exclude_tickers=exclude_tickers
        )
        results['analyses']['conscience_filters'] = conscience_results
    except Exception as e:
        print(f"\n⚠️  Conscience filter analysis failed: {e}")
        results['analyses']['conscience_filters'] = {'error': str(e)}
    
    # Extended analyses (--full flag)
    if full_analysis:
        # 5. Comprehensive Risk Analysis (Tail Risk & Drawdown)
        try:
            from scripts.comprehensive_risk_analysis import run_full_risk_analysis
            risk_results = run_full_risk_analysis(run_dir)
            results['analyses']['comprehensive_risk'] = risk_results
        except Exception as e:
            print(f"\n⚠️  Comprehensive risk analysis failed: {e}")
            results['analyses']['comprehensive_risk'] = {'error': str(e)}
        
        # 6. Scenario-based Stress Testing
        try:
            from scripts.stress_testing import run_all_scenarios, simulate_position_reduction
            scenario_results = run_all_scenarios(run_dir)
            reduction_results = simulate_position_reduction(run_dir, reduction_pct=0.50)
            results['analyses']['scenario_stress'] = {
                'scenarios': scenario_results,
                'position_reduction': reduction_results
            }
        except Exception as e:
            print(f"\n⚠️  Scenario stress testing failed: {e}")
            results['analyses']['scenario_stress'] = {'error': str(e)}
        
        # 7. Detailed Conscience Analysis
        try:
            from scripts.conscience_filter import run_conscience_analysis as run_detailed_conscience
            detailed_conscience = run_detailed_conscience(
                run_dir,
                exclude_categories=None,  # Scan only, don't filter
                exclude_tickers=exclude_tickers,
                exclude_sectors=exclude_sectors,
            )
            results['analyses']['detailed_conscience'] = detailed_conscience
        except Exception as e:
            print(f"\n⚠️  Detailed conscience analysis failed: {e}")
            results['analyses']['detailed_conscience'] = {'error': str(e)}
    
    # Final Summary
    print("\n" + "=" * 70)
    print("STRENGTHENING ANALYSIS COMPLETE")
    print("=" * 70)
    
    # Generate overall assessment
    issues = []
    warnings = []
    
    # Check regime dependency
    regime_data = results['analyses'].get('regime', {}).get('regime_performance', {})
    if regime_data:
        returns = [m['annualized_return'] for m in regime_data.values()]
        if returns and min(returns) < -0.10:
            issues.append("Strategy underperforms significantly in some regimes")
        elif returns and min(returns) < 0:
            warnings.append("Strategy has negative returns in some regimes")
    
    # Check factor concentration
    factor_data = results['analyses'].get('factor_exposure', {})
    if factor_data.get('factor_contributions', {}):
        max_factor = max(factor_data['factor_contributions'].values())
        if max_factor > 0.50:
            issues.append(f"Factor concentration too high ({max_factor*100:.0f}%)")
        elif max_factor > 0.35:
            warnings.append(f"Factor concentration elevated ({max_factor*100:.0f}%)")
    
    # Check drawdown
    stress_data = results['analyses'].get('stress_test', {}).get('stress_test', {})
    if stress_data.get('100%', {}):
        dd = stress_data['100%'].get('max_drawdown', 0)
        if dd < -0.50:
            issues.append(f"High drawdown risk ({dd*100:.0f}%)")
        elif dd < -0.30:
            warnings.append(f"Moderate drawdown risk ({dd*100:.0f}%)")
    
    # Check tail risk (if full analysis)
    if full_analysis:
        tail_data = results['analyses'].get('comprehensive_risk', {}).get('tail_risk', {})
        if tail_data:
            var99 = tail_data.get('var', {}).get('var_99_daily', 0)
            if var99 < -0.05:
                warnings.append(f"High daily VaR (99%): {var99*100:.1f}%")
    
    # Display issues and warnings
    if issues:
        print("\n❌ CRITICAL ISSUES:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
    
    if not issues and not warnings:
        print("\n✅ All strengthening checks passed")
    
    print("\n💡 RECOMMENDATION:")
    if len(issues) == 0 and len(warnings) <= 1:
        print("   This strategy appears robust for implementation.")
    elif len(issues) == 0:
        print("   Strategy is usable with awareness of the warnings above.")
    elif len(issues) <= 2:
        print("   Consider the issues above, but strategy is usable with caution.")
    else:
        print("   Multiple concerns - recommend further investigation before allocating.")
    
    results['summary'] = {
        'issues': issues,
        'warnings': warnings,
        'overall_status': 'PASS' if not issues else ('CAUTION' if len(issues) <= 2 else 'REVIEW'),
    }
    
    # Save report
    if save_report:
        report_file = run_dir / 'strengthening_analysis.json'
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📁 Report saved: {report_file}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Strengthen portfolio recommendations with additional analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis on latest run
  python scripts/strengthen_recommendations.py
  
  # Full analysis with all modules
  python scripts/strengthen_recommendations.py --full
  
  # Analysis with exclusions
  python scripts/strengthen_recommendations.py --exclude-sectors "Energy,Defense" --exclude-tickers "XOM,CVX"
  
  # Analyze specific run
  python scripts/strengthen_recommendations.py --run-dir output/run_everything_20260102_160327_
        """
    )
    
    parser.add_argument(
        "--run-id",
        help="Run ID to analyze (uses latest if not specified)"
    )
    parser.add_argument(
        "--run-dir",
        help="Direct path to run directory"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run extended analyses: tail risk, scenario stress tests, detailed conscience"
    )
    parser.add_argument(
        "--exclude-sectors",
        help="Comma-separated sectors to exclude (e.g., 'Energy,Defense')"
    )
    parser.add_argument(
        "--exclude-tickers",
        help="Comma-separated tickers to exclude"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save the analysis report"
    )
    
    args = parser.parse_args()
    
    # Find run directory
    if args.run_dir:
        run_dir = Path(args.run_dir)
    elif args.run_id:
        # Search for run
        output = Path('output')
        matches = list(output.glob(f"*{args.run_id}*"))
        if not matches:
            print(f"❌ No run found matching: {args.run_id}")
            return 1
        run_dir = matches[0]
    else:
        # Use latest
        output = Path('output')
        runs = sorted(output.glob("run_*"))
        if not runs:
            print("❌ No runs found in output/")
            return 1
        run_dir = runs[-1]
    
    print(f"📁 Analyzing: {run_dir}")
    
    # Parse exclusions
    exclude_sectors = args.exclude_sectors.split(',') if args.exclude_sectors else None
    exclude_tickers = args.exclude_tickers.split(',') if args.exclude_tickers else None
    
    # Run analysis
    run_full_strengthening(
        run_dir=run_dir,
        exclude_sectors=exclude_sectors,
        exclude_tickers=exclude_tickers,
        save_report=not args.no_save,
        full_analysis=args.full
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
