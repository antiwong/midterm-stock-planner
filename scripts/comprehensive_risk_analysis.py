#!/usr/bin/env python3
"""
Comprehensive Risk Analysis
============================

Deep-dive risk analysis for portfolio recommendations:

1. DOWNSIDE & TAIL RISK: Worst-case outcomes, drawdown duration
2. SCENARIO & REGIME ANALYSIS: Sub-period and regime-based performance
3. POSITION-LEVEL DIAGNOSTICS: Individual stock risk flags
4. THEMATIC DEPENDENCE: Sector/theme concentration and correlations
5. SIZING RECOMMENDATIONS: Capital allocation guidance

Usage:
    python scripts/comprehensive_risk_analysis.py --run-dir output/run_everything_20260102_160327_
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import json


# =============================================================================
# 1. DOWNSIDE & TAIL RISK ANALYSIS
# =============================================================================

def analyze_tail_risk(returns: pd.Series) -> Dict:
    """
    Analyze downside and tail risk from returns.
    
    Computes:
    - Return distribution percentiles
    - VaR and CVaR (Expected Shortfall)
    - Worst outcomes at various frequencies
    """
    # Daily percentiles
    daily_pct = {
        'p1': returns.quantile(0.01),
        'p5': returns.quantile(0.05),
        'p10': returns.quantile(0.10),
        'p25': returns.quantile(0.25),
        'median': returns.quantile(0.50),
    }
    
    # Resample to monthly and quarterly
    returns_series = returns.copy()
    returns_series.index = pd.to_datetime(returns_series.index) if not isinstance(returns_series.index, pd.DatetimeIndex) else returns_series.index
    
    monthly = (1 + returns_series).resample('M').prod() - 1
    quarterly = (1 + returns_series).resample('Q').prod() - 1
    
    monthly_pct = {
        'p1': monthly.quantile(0.01) if len(monthly) > 10 else None,
        'p5': monthly.quantile(0.05) if len(monthly) > 10 else None,
        'p10': monthly.quantile(0.10) if len(monthly) > 10 else None,
        'worst': monthly.min(),
        'worst_date': str(monthly.idxmin().date()) if len(monthly) > 0 else None,
    }
    
    quarterly_pct = {
        'p1': quarterly.quantile(0.01) if len(quarterly) > 4 else None,
        'p5': quarterly.quantile(0.05) if len(quarterly) > 4 else None,
        'worst': quarterly.min(),
        'worst_date': str(quarterly.idxmin().date()) if len(quarterly) > 0 else None,
    }
    
    # VaR and CVaR (Expected Shortfall)
    var_95 = returns.quantile(0.05)  # 95% VaR
    var_99 = returns.quantile(0.01)  # 99% VaR
    cvar_95 = returns[returns <= var_95].mean()  # Expected loss given VaR breach
    cvar_99 = returns[returns <= var_99].mean()
    
    return {
        'daily': daily_pct,
        'monthly': monthly_pct,
        'quarterly': quarterly_pct,
        'var': {
            'var_95_daily': float(var_95),
            'var_99_daily': float(var_99),
            'cvar_95_daily': float(cvar_95) if pd.notna(cvar_95) else None,
            'cvar_99_daily': float(cvar_99) if pd.notna(cvar_99) else None,
        }
    }


def analyze_drawdown_duration(returns: pd.Series) -> Dict:
    """
    Analyze drawdown depth and duration.
    
    Returns:
    - Max drawdown and date
    - Recovery time from major drawdowns
    - Underwater periods
    """
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    
    # Find all drawdown periods
    underwater = drawdown < 0
    
    # Identify drawdown periods
    periods = []
    in_dd = False
    start_idx = None
    peak_val = None
    
    for i, (idx, val) in enumerate(drawdown.items()):
        if val < 0 and not in_dd:
            # Start of drawdown
            in_dd = True
            start_idx = idx
            peak_val = running_max.iloc[i]
        elif val >= 0 and in_dd:
            # End of drawdown (recovered)
            in_dd = False
            dd_depth = drawdown.loc[start_idx:idx].min()
            trough_idx = drawdown.loc[start_idx:idx].idxmin()
            
            periods.append({
                'start': str(start_idx.date()) if hasattr(start_idx, 'date') else str(start_idx),
                'trough': str(trough_idx.date()) if hasattr(trough_idx, 'date') else str(trough_idx),
                'end': str(idx.date()) if hasattr(idx, 'date') else str(idx),
                'depth': float(dd_depth),
                'duration_to_trough': (trough_idx - start_idx).days if hasattr(start_idx, 'date') else None,
                'duration_to_recovery': (idx - start_idx).days if hasattr(start_idx, 'date') else None,
            })
    
    # Handle ongoing drawdown
    if in_dd:
        dd_depth = drawdown.loc[start_idx:].min()
        trough_idx = drawdown.loc[start_idx:].idxmin()
        periods.append({
            'start': str(start_idx.date()) if hasattr(start_idx, 'date') else str(start_idx),
            'trough': str(trough_idx.date()) if hasattr(trough_idx, 'date') else str(trough_idx),
            'end': 'ongoing',
            'depth': float(dd_depth),
            'duration_to_trough': (trough_idx - start_idx).days if hasattr(start_idx, 'date') else None,
            'duration_to_recovery': None,
        })
    
    # Sort by depth
    periods = sorted(periods, key=lambda x: x['depth'])
    
    # Summary stats
    recovered_periods = [p for p in periods if p['end'] != 'ongoing' and p['duration_to_recovery']]
    
    return {
        'max_drawdown': float(drawdown.min()),
        'max_drawdown_date': str(drawdown.idxmin().date()) if hasattr(drawdown.idxmin(), 'date') else str(drawdown.idxmin()),
        'current_drawdown': float(drawdown.iloc[-1]),
        'underwater_pct': float(underwater.mean() * 100),
        'worst_periods': periods[:5],  # Top 5 worst drawdowns
        'avg_recovery_days': np.mean([p['duration_to_recovery'] for p in recovered_periods]) if recovered_periods else None,
        'max_recovery_days': max([p['duration_to_recovery'] for p in recovered_periods]) if recovered_periods else None,
    }


def run_tail_risk_analysis(run_dir: Path) -> Dict:
    """Run complete tail risk analysis."""
    
    print("\n" + "=" * 70)
    print("1. DOWNSIDE & TAIL RISK ANALYSIS")
    print("=" * 70)
    
    # Load returns
    returns_file = run_dir / 'backtest_returns.csv'
    returns_df = pd.read_csv(returns_file, parse_dates=['date'], index_col='date')
    returns = returns_df['portfolio_return']
    
    # Tail risk
    tail = analyze_tail_risk(returns)
    
    print("\n📊 RETURN DISTRIBUTION:")
    print("-" * 50)
    print(f"{'Percentile':<15} {'Daily':>12} {'Monthly':>12} {'Quarterly':>12}")
    print("-" * 50)
    print(f"{'Worst (1%)':>15} {tail['daily']['p1']*100:>11.1f}% {tail['monthly']['p1']*100 if tail['monthly']['p1'] else 'N/A':>11} {tail['quarterly']['p1']*100 if tail['quarterly']['p1'] else 'N/A':>11}")
    print(f"{'5th percentile':>15} {tail['daily']['p5']*100:>11.1f}% {tail['monthly']['p5']*100 if tail['monthly']['p5'] else 'N/A':>11} {tail['quarterly']['p5']*100 if tail['quarterly']['p5'] else 'N/A':>11}")
    print(f"{'10th percentile':>15} {tail['daily']['p10']*100:>11.1f}%")
    print("-" * 50)
    print(f"Worst month: {tail['monthly']['worst']*100:.1f}% ({tail['monthly']['worst_date']})")
    print(f"Worst quarter: {tail['quarterly']['worst']*100:.1f}% ({tail['quarterly']['worst_date']})")
    
    print("\n📉 VALUE AT RISK:")
    print("-" * 50)
    print(f"Daily VaR (95%):  {tail['var']['var_95_daily']*100:>8.2f}% (5% chance of worse)")
    print(f"Daily VaR (99%):  {tail['var']['var_99_daily']*100:>8.2f}% (1% chance of worse)")
    print(f"Daily CVaR (95%): {tail['var']['cvar_95_daily']*100:>8.2f}% (avg loss when VaR breached)")
    
    # Drawdown analysis
    dd = analyze_drawdown_duration(returns)
    
    print("\n📉 DRAWDOWN ANALYSIS:")
    print("-" * 50)
    print(f"Max Drawdown: {dd['max_drawdown']*100:.1f}% ({dd['max_drawdown_date']})")
    print(f"Current Drawdown: {dd['current_drawdown']*100:.1f}%")
    print(f"Time Underwater: {dd['underwater_pct']:.0f}% of period")
    
    if dd['avg_recovery_days']:
        print(f"\nRecovery Statistics:")
        print(f"  Average recovery: {dd['avg_recovery_days']:.0f} days ({dd['avg_recovery_days']/30:.1f} months)")
        print(f"  Longest recovery: {dd['max_recovery_days']:.0f} days ({dd['max_recovery_days']/30:.1f} months)")
    
    print("\n⚡ WORST DRAWDOWN PERIODS:")
    print("-" * 70)
    for i, p in enumerate(dd['worst_periods'][:3], 1):
        recovery = f"{p['duration_to_recovery']} days" if p['duration_to_recovery'] else "ongoing"
        print(f"  {i}. {p['depth']*100:.1f}% ({p['start']} to {p['end']}) - Recovery: {recovery}")
    
    return {'tail_risk': tail, 'drawdown': dd}


# =============================================================================
# 2. SCENARIO & REGIME ANALYSIS
# =============================================================================

def analyze_sub_periods(returns: pd.Series) -> Dict:
    """
    Analyze performance across different market sub-periods.
    """
    periods = {
        '2020 (COVID Crash & Recovery)': ('2020-01-01', '2020-12-31'),
        '2021 (Bull Market)': ('2021-01-01', '2021-12-31'),
        '2022 (Rate Hike Crash)': ('2022-01-01', '2022-12-31'),
        '2023 (AI Rally)': ('2023-01-01', '2023-12-31'),
        '2024 (Current)': ('2024-01-01', '2024-12-31'),
    }
    
    results = {}
    for name, (start, end) in periods.items():
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        
        period_returns = returns[(returns.index >= start_dt) & (returns.index <= end_dt)]
        
        if len(period_returns) < 20:
            continue
        
        cum = (1 + period_returns).cumprod()
        total = cum.iloc[-1] - 1
        days = len(period_returns)
        ann = (1 + total) ** (252/days) - 1 if days > 0 else 0
        vol = period_returns.std() * np.sqrt(252)
        sharpe = ann / vol if vol > 0 else 0
        max_dd = (cum / cum.cummax() - 1).min()
        
        results[name] = {
            'total_return': float(total),
            'annualized_return': float(ann),
            'volatility': float(vol),
            'sharpe': float(sharpe),
            'max_drawdown': float(max_dd),
            'days': days,
        }
    
    return results


def classify_regimes_detailed(benchmark_returns: pd.Series, returns: pd.Series) -> Dict:
    """
    Classify market into detailed regimes and analyze performance.
    """
    # Rolling metrics
    bench_rolling_ret = benchmark_returns.rolling(63).mean() * 252  # 3-month rolling
    bench_rolling_vol = benchmark_returns.rolling(21).std() * np.sqrt(252)  # 1-month vol
    
    # Regime classification
    regimes = pd.DataFrame(index=benchmark_returns.index)
    regimes['trend'] = np.where(bench_rolling_ret > 0.05, 'Bull', 
                                np.where(bench_rolling_ret < -0.05, 'Bear', 'Sideways'))
    regimes['vol'] = np.where(bench_rolling_vol > bench_rolling_vol.median() * 1.2, 'High Vol',
                              np.where(bench_rolling_vol < bench_rolling_vol.median() * 0.8, 'Low Vol', 'Normal Vol'))
    regimes['regime'] = regimes['trend'] + ' / ' + regimes['vol']
    
    # Align with portfolio returns
    aligned = pd.DataFrame({
        'portfolio': returns,
        'benchmark': benchmark_returns,
        'regime': regimes['regime']
    }).dropna()
    
    results = {}
    for regime in aligned['regime'].unique():
        regime_rets = aligned[aligned['regime'] == regime]['portfolio']
        
        if len(regime_rets) < 20:
            continue
        
        total = (1 + regime_rets).prod() - 1
        ann = (1 + total) ** (252/len(regime_rets)) - 1
        vol = regime_rets.std() * np.sqrt(252)
        sharpe = ann / vol if vol > 0 else 0
        
        results[regime] = {
            'days': len(regime_rets),
            'pct_of_period': len(regime_rets) / len(aligned) * 100,
            'annualized_return': float(ann),
            'volatility': float(vol),
            'sharpe': float(sharpe),
            'hit_rate': float((regime_rets > 0).mean()),
        }
    
    return results


def run_scenario_analysis(run_dir: Path) -> Dict:
    """Run scenario and regime analysis."""
    
    print("\n" + "=" * 70)
    print("2. SCENARIO & REGIME ANALYSIS")
    print("=" * 70)
    
    # Load data
    returns_df = pd.read_csv(run_dir / 'backtest_returns.csv', parse_dates=['date'], index_col='date')
    returns = returns_df['portfolio_return']
    bench_returns = returns_df['benchmark_return']
    
    # Sub-period analysis
    sub_periods = analyze_sub_periods(returns)
    
    print("\n📅 SUB-PERIOD PERFORMANCE:")
    print("-" * 70)
    print(f"{'Period':<30} {'Return':>10} {'Vol':>8} {'Sharpe':>8} {'MaxDD':>10}")
    print("-" * 70)
    
    for period, metrics in sub_periods.items():
        print(f"{period:<30} {metrics['annualized_return']*100:>9.1f}% "
              f"{metrics['volatility']*100:>7.1f}% "
              f"{metrics['sharpe']:>8.2f} "
              f"{metrics['max_drawdown']*100:>9.1f}%")
    
    # Regime analysis
    regimes = classify_regimes_detailed(bench_returns, returns)
    
    print("\n🔄 REGIME PERFORMANCE:")
    print("-" * 70)
    print(f"{'Regime':<25} {'Days':>6} {'% Time':>8} {'Return':>10} {'Sharpe':>8}")
    print("-" * 70)
    
    for regime, metrics in sorted(regimes.items(), key=lambda x: -x[1]['annualized_return']):
        print(f"{regime:<25} {metrics['days']:>6} {metrics['pct_of_period']:>7.1f}% "
              f"{metrics['annualized_return']*100:>9.1f}% {metrics['sharpe']:>8.2f}")
    
    # Regime dependency check
    print("\n" + "-" * 70)
    if regimes:
        returns_by_regime = [m['annualized_return'] for m in regimes.values()]
        best = max(returns_by_regime)
        worst = min(returns_by_regime)
        
        if worst < -0.10 and best > 0.30:
            print("⚠️  HIGH REGIME DEPENDENCY: Strategy is a 'regime wonder'")
            print(f"   Best regime: {best*100:.1f}%, Worst regime: {worst*100:.1f}%")
        elif all(r > -0.05 for r in returns_by_regime):
            print("✅ ROBUST: Strategy performs reasonably across all regimes")
        else:
            print("⚠️  MODERATE DEPENDENCY: Mixed regime performance")
    
    return {'sub_periods': sub_periods, 'regimes': regimes}


# =============================================================================
# 3. POSITION-LEVEL RISK DIAGNOSTICS
# =============================================================================

def analyze_position_risk(positions: pd.DataFrame, prices: pd.DataFrame) -> Dict:
    """
    Analyze risk at the position level.
    """
    # Get unique tickers from latest positions
    latest_date = positions['date'].max()
    latest_pos = positions[positions['date'] == latest_date].copy()
    
    position_risks = []
    
    for _, row in latest_pos.iterrows():
        ticker = row['ticker']
        weight = row['weight']
        
        # Get price history for this ticker
        ticker_prices = prices[prices['ticker'] == ticker].sort_values('date')
        if len(ticker_prices) < 63:  # Need at least 3 months
            continue
        
        ticker_prices = ticker_prices.set_index('date')
        daily_ret = ticker_prices['close'].pct_change().dropna()
        
        # Monthly returns
        monthly_ret = (1 + daily_ret).resample('M').prod() - 1
        
        # Risk metrics
        worst_month = monthly_ret.min()
        worst_3month = monthly_ret.rolling(3).apply(lambda x: (1+x).prod()-1, raw=False).min()
        volatility = daily_ret.std() * np.sqrt(252)
        
        # Momentum (3-month return)
        if len(daily_ret) >= 63:
            momentum_3m = (1 + daily_ret.iloc[-63:]).prod() - 1
        else:
            momentum_3m = None
        
        position_risks.append({
            'ticker': ticker,
            'weight': float(weight),
            'worst_month': float(worst_month) if pd.notna(worst_month) else None,
            'worst_3month': float(worst_3month) if pd.notna(worst_3month) else None,
            'volatility': float(volatility),
            'momentum_3m': float(momentum_3m) if momentum_3m else None,
        })
    
    return position_risks


def run_position_diagnostics(run_dir: Path) -> Dict:
    """Run position-level risk diagnostics."""
    
    print("\n" + "=" * 70)
    print("3. POSITION-LEVEL RISK DIAGNOSTICS")
    print("=" * 70)
    
    # Load data
    positions = pd.read_csv(run_dir / 'backtest_positions.csv', parse_dates=['date'])
    prices = pd.read_csv('data/prices.csv', parse_dates=['date'])
    
    # Load enriched data if available
    enriched_files = list(run_dir.glob('portfolio_enriched_*.csv'))
    enriched = pd.read_csv(enriched_files[0]) if enriched_files else None
    
    # Analyze positions
    position_risks = analyze_position_risk(positions, prices)
    
    # Flag high-risk positions
    print("\n⚠️  HIGH-RISK POSITION FLAGS:")
    print("-" * 70)
    
    flags = []
    for pos in position_risks:
        issues = []
        
        # Flag: High weight + severe worst month
        if pos['weight'] > 0.08 and pos['worst_month'] and pos['worst_month'] < -0.30:
            issues.append(f"High weight ({pos['weight']*100:.0f}%) with {pos['worst_month']*100:.0f}% worst month")
        
        # Flag: Very high volatility
        if pos['volatility'] > 0.80:
            issues.append(f"Extreme volatility ({pos['volatility']*100:.0f}%)")
        
        # Flag: Negative 3-month momentum in top position
        if pos['weight'] > 0.08 and pos['momentum_3m'] and pos['momentum_3m'] < -0.20:
            issues.append(f"Negative momentum ({pos['momentum_3m']*100:.0f}%) in large position")
        
        if issues:
            flags.append({'ticker': pos['ticker'], 'issues': issues})
            print(f"  {pos['ticker']}:")
            for issue in issues:
                print(f"    ❌ {issue}")
    
    if not flags:
        print("  ✅ No critical position-level flags")
    
    # Summary table
    print("\n📊 POSITION RISK SUMMARY:")
    print("-" * 70)
    print(f"{'Ticker':<8} {'Weight':>8} {'Vol':>8} {'Worst Mo':>10} {'Worst 3Mo':>10} {'Mom 3Mo':>10}")
    print("-" * 70)
    
    for pos in sorted(position_risks, key=lambda x: -x['weight'])[:15]:
        worst_mo = f"{pos['worst_month']*100:.1f}%" if pos['worst_month'] else 'N/A'
        worst_3mo = f"{pos['worst_3month']*100:.1f}%" if pos['worst_3month'] else 'N/A'
        mom = f"{pos['momentum_3m']*100:.1f}%" if pos['momentum_3m'] else 'N/A'
        
        print(f"{pos['ticker']:<8} {pos['weight']*100:>7.1f}% "
              f"{pos['volatility']*100:>7.1f}% "
              f"{worst_mo:>10} {worst_3mo:>10} {mom:>10}")
    
    return {'position_risks': position_risks, 'flags': flags}


# =============================================================================
# 4. THEMATIC & SECTOR DEPENDENCE
# =============================================================================

# Theme definitions
THEMES = {
    'Nuclear/Uranium': ['UEC', 'LEU', 'CCJ', 'SMR', 'NXE', 'DNN', 'URG', 'UUUU'],
    'Clean Energy/EV': ['STEM', 'PLUG', 'ENPH', 'SEDG', 'RUN', 'EVGO', 'BLNK', 'CHPT', 'LCID', 'RIVN', 'NIO', 'XPEV', 'LAZR'],
    'High-Beta Tech/AI': ['PLTR', 'UPST', 'COIN', 'HOOD', 'AFRM', 'SOFI', 'RBLX', 'SNAP', 'PINS'],
    'Meme/Speculative': ['AMC', 'GME', 'BBBY', 'SPCE', 'OPEN'],
    'Traditional Energy': ['XOM', 'CVX', 'OXY', 'HAL', 'SLB', 'DVN', 'EOG', 'COP', 'MPC', 'VLO', 'FANG'],
}


def analyze_thematic_exposure(positions: pd.DataFrame) -> Dict:
    """
    Analyze exposure to specific investment themes.
    """
    latest_date = positions['date'].max()
    latest_pos = positions[positions['date'] == latest_date]
    
    theme_weights = {}
    for theme, tickers in THEMES.items():
        theme_pos = latest_pos[latest_pos['ticker'].isin(tickers)]
        theme_weights[theme] = {
            'weight': float(theme_pos['weight'].sum()),
            'count': len(theme_pos),
            'tickers': theme_pos['ticker'].tolist(),
        }
    
    return theme_weights


def analyze_correlations(positions: pd.DataFrame, prices: pd.DataFrame) -> Dict:
    """
    Analyze correlation clusters among holdings.
    """
    latest_date = positions['date'].max()
    latest_pos = positions[positions['date'] == latest_date]
    tickers = latest_pos['ticker'].tolist()
    
    # Get returns for each ticker
    returns_dict = {}
    for ticker in tickers:
        ticker_prices = prices[prices['ticker'] == ticker].sort_values('date')
        if len(ticker_prices) > 60:
            ticker_prices = ticker_prices.set_index('date')
            returns_dict[ticker] = ticker_prices['close'].pct_change().dropna()
    
    if len(returns_dict) < 2:
        return {}
    
    # Create returns dataframe
    returns_df = pd.DataFrame(returns_dict)
    returns_df = returns_df.dropna()
    
    if len(returns_df) < 30:
        return {}
    
    # Correlation matrix
    corr_matrix = returns_df.corr()
    
    # Find highly correlated pairs
    high_corr_pairs = []
    for i, t1 in enumerate(corr_matrix.columns):
        for t2 in corr_matrix.columns[i+1:]:
            corr = corr_matrix.loc[t1, t2]
            if corr > 0.70:
                high_corr_pairs.append({
                    'pair': (t1, t2),
                    'correlation': float(corr),
                })
    
    # Identify clusters
    clusters = []
    remaining = set(tickers)
    
    while remaining:
        ticker = remaining.pop()
        cluster = {ticker}
        
        for other in list(remaining):
            if ticker in corr_matrix.columns and other in corr_matrix.columns:
                if corr_matrix.loc[ticker, other] > 0.60:
                    cluster.add(other)
                    remaining.discard(other)
        
        if len(cluster) > 1:
            clusters.append(list(cluster))
    
    return {
        'high_corr_pairs': high_corr_pairs[:10],
        'clusters': clusters[:5],
        'avg_correlation': float(corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean()),
    }


def run_thematic_analysis(run_dir: Path) -> Dict:
    """Run thematic and sector dependence analysis."""
    
    print("\n" + "=" * 70)
    print("4. THEMATIC & SECTOR DEPENDENCE")
    print("=" * 70)
    
    # Load data
    positions = pd.read_csv(run_dir / 'backtest_positions.csv', parse_dates=['date'])
    prices = pd.read_csv('data/prices.csv', parse_dates=['date'])
    
    # Load sector data
    sector_map = {}
    if Path('data/sectors.csv').exists():
        sectors_df = pd.read_csv('data/sectors.csv')
        sector_map = dict(zip(sectors_df['ticker'], sectors_df['sector']))
    
    # Theme analysis
    themes = analyze_thematic_exposure(positions)
    
    print("\n🎯 THEMATIC EXPOSURE:")
    print("-" * 70)
    print(f"{'Theme':<25} {'Weight':>10} {'# Stocks':>10} {'Status':<15}")
    print("-" * 70)
    
    theme_flags = []
    for theme, data in sorted(themes.items(), key=lambda x: -x[1]['weight']):
        if data['weight'] > 0:
            status = "❌ HIGH" if data['weight'] > 0.30 else ("⚠️ Elevated" if data['weight'] > 0.20 else "✅ OK")
            print(f"{theme:<25} {data['weight']*100:>9.1f}% {data['count']:>10} {status}")
            
            if data['weight'] > 0.30:
                theme_flags.append(theme)
    
    if theme_flags:
        print(f"\n⚠️  CONCENTRATION WARNING: {', '.join(theme_flags)} exceed 30% combined weight")
    
    # Correlation analysis
    correlations = analyze_correlations(positions, prices)
    
    if correlations:
        print("\n🔗 CORRELATION CLUSTERS:")
        print("-" * 70)
        print(f"Average pairwise correlation: {correlations['avg_correlation']:.2f}")
        
        if correlations['high_corr_pairs']:
            print("\nHighly correlated pairs (>0.70):")
            for pair in correlations['high_corr_pairs'][:5]:
                print(f"  {pair['pair'][0]} ↔ {pair['pair'][1]}: {pair['correlation']:.2f}")
        
        if correlations['clusters']:
            print("\nCorrelation clusters (redundant diversification):")
            for i, cluster in enumerate(correlations['clusters'][:3], 1):
                print(f"  Cluster {i}: {', '.join(cluster)}")
    
    return {'themes': themes, 'correlations': correlations}


# =============================================================================
# 5. SIZING RECOMMENDATIONS
# =============================================================================

def generate_sizing_recommendations(
    tail_risk: Dict,
    drawdown: Dict,
    regime_data: Dict,
) -> Dict:
    """
    Generate position sizing recommendations based on risk analysis.
    """
    recommendations = {}
    
    # Base on drawdown
    max_dd = abs(drawdown['max_drawdown'])
    
    if max_dd > 0.60:
        recommendations['base_allocation'] = 0.25
        recommendations['reason'] = f"High drawdown risk ({max_dd*100:.0f}%)"
    elif max_dd > 0.40:
        recommendations['base_allocation'] = 0.50
        recommendations['reason'] = f"Moderate-high drawdown ({max_dd*100:.0f}%)"
    else:
        recommendations['base_allocation'] = 0.75
        recommendations['reason'] = f"Acceptable drawdown ({max_dd*100:.0f}%)"
    
    # Adjust for recovery time
    if drawdown.get('avg_recovery_days') and drawdown['avg_recovery_days'] > 180:
        recommendations['base_allocation'] *= 0.80
        recommendations['recovery_adj'] = "Reduced 20% due to long recovery times"
    
    # Scaled allocations
    base = recommendations['base_allocation']
    recommendations['allocations'] = {
        'conservative': base * 0.50,
        'moderate': base * 0.75,
        'aggressive': base * 1.00,
    }
    
    return recommendations


def run_full_risk_analysis(run_dir: Path) -> Dict:
    """
    Run comprehensive risk analysis.
    """
    print("=" * 70)
    print("COMPREHENSIVE RISK ANALYSIS")
    print("=" * 70)
    print(f"Run: {run_dir.name}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    results = {'run_id': run_dir.name, 'timestamp': datetime.now().isoformat()}
    
    # 1. Tail Risk
    tail_results = run_tail_risk_analysis(run_dir)
    results['tail_risk'] = tail_results
    
    # 2. Scenario/Regime
    scenario_results = run_scenario_analysis(run_dir)
    results['scenarios'] = scenario_results
    
    # 3. Position Diagnostics
    position_results = run_position_diagnostics(run_dir)
    results['positions'] = position_results
    
    # 4. Thematic Analysis
    thematic_results = run_thematic_analysis(run_dir)
    results['thematic'] = thematic_results
    
    # 5. Sizing Recommendations
    print("\n" + "=" * 70)
    print("5. SIZING RECOMMENDATIONS")
    print("=" * 70)
    
    sizing = generate_sizing_recommendations(
        tail_results['tail_risk'],
        tail_results['drawdown'],
        scenario_results.get('regimes', {})
    )
    results['sizing'] = sizing
    
    print(f"\n💰 RECOMMENDED ALLOCATION:")
    print("-" * 50)
    print(f"Basis: {sizing['reason']}")
    print()
    print(f"  Conservative profile: {sizing['allocations']['conservative']*100:.0f}% of investable assets")
    print(f"  Moderate profile:     {sizing['allocations']['moderate']*100:.0f}% of investable assets")
    print(f"  Aggressive profile:   {sizing['allocations']['aggressive']*100:.0f}% of investable assets")
    print()
    print("  Remainder should be in safer exposures (broad ETFs, bonds, cash)")
    
    # Final summary
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    
    # Save report
    report_path = run_dir / 'comprehensive_risk_analysis.json'
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n📁 Report saved: {report_path}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Comprehensive risk analysis")
    parser.add_argument("--run-dir", help="Run directory to analyze")
    parser.add_argument("--run-id", help="Run ID to find")
    
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
    
    run_full_risk_analysis(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
