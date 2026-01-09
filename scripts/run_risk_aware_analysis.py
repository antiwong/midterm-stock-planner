#!/usr/bin/env python3
"""
Run Risk-Aware Stock Analysis
=============================
Applies volatility-aware position sizing, risk parity, and sector constraints
to create a balanced portfolio with improved Sharpe ratio.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import json
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load API keys
from src.config.api_keys import load_api_keys
load_api_keys()

from src.risk import (
    RiskParityAllocator,
    SectorConstraints,
    generate_risk_report,
)
from src.analytics import get_db, Run, StockScore
from src.analytics.ai_insights import AIInsightsGenerator


def load_benchmark_returns(ticker: str = "SPY", days: int = 252) -> pd.Series:
    """Load benchmark returns from data."""
    try:
        prices_path = Path("data/prices.csv")
        if prices_path.exists():
            df = pd.read_csv(prices_path)
            if ticker in df['ticker'].values:
                spy_data = df[df['ticker'] == ticker].sort_values('date')
                spy_data['return'] = spy_data['close'].pct_change()
                return spy_data.set_index('date')['return'].dropna().tail(days)
    except Exception as e:
        print(f"⚠️ Could not load benchmark: {e}")
    
    # Return mock data
    return pd.Series(np.random.normal(0.0004, 0.01, days))


def calculate_stock_returns(prices_df: pd.DataFrame, tickers: list) -> pd.DataFrame:
    """Calculate returns for each ticker."""
    returns_dict = {}
    
    for ticker in tickers:
        ticker_data = prices_df[prices_df['ticker'] == ticker].sort_values('date')
        if len(ticker_data) > 1:
            ticker_data['return'] = ticker_data['close'].pct_change()
            returns_dict[ticker] = ticker_data.set_index('date')['return']
    
    if returns_dict:
        return pd.DataFrame(returns_dict).dropna()
    return pd.DataFrame()


def run_risk_aware_analysis(
    run_id: str = None,
    method: str = "risk_parity",
    capital: float = 100_000,
    target_vol: float = 0.15,
    max_position: float = 0.10,
    verbose: bool = True,
):
    """
    Run risk-aware portfolio construction on existing analysis.
    
    Args:
        run_id: ID of analysis run to optimize (uses latest if None)
        method: Allocation method ('risk_parity', 'inverse_vol', 'vol_capped')
        capital: Portfolio capital
        target_vol: Target portfolio volatility
        max_position: Maximum single position weight
        verbose: Print progress
    """
    print("=" * 70)
    print("📊 Risk-Aware Portfolio Construction")
    print("=" * 70)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"💰 Capital: ${capital:,.0f}")
    print(f"🎯 Target Vol: {target_vol*100:.0f}%")
    print(f"📏 Method: {method}")
    print()
    
    # Load analysis run
    db = get_db("data/analysis.db")
    session = db.get_session()
    
    try:
        if run_id:
            run = session.query(Run).filter_by(run_id=run_id).first()
        else:
            run = session.query(Run).order_by(Run.created_at.desc()).first()
        
        if not run:
            print("❌ No analysis runs found!")
            return
        
        print(f"📝 Using run: {run.name or run.run_id}")
        print(f"   Created: {run.created_at}")
        
        # Load scores
        scores_db = session.query(StockScore).filter_by(run_id=run.run_id).order_by(StockScore.rank).all()
        
        if not scores_db:
            print("❌ No stock scores found!")
            return
        
        print(f"   Stocks: {len(scores_db)}")
        
    finally:
        session.close()
    
    # Load price data for volatility calculation
    print("\n📥 Loading price data...")
    prices_path = Path("data/prices.csv")
    
    if prices_path.exists():
        prices_df = pd.read_csv(prices_path)
        tickers = [s.ticker for s in scores_db]
        returns_df = calculate_stock_returns(prices_df, tickers)
        print(f"   Loaded returns for {len(returns_df.columns)} tickers")
    else:
        print("⚠️ No price data found, using estimated volatilities")
        returns_df = pd.DataFrame()
    
    # Calculate volatilities
    print("\n📈 Calculating volatilities...")
    allocator = RiskParityAllocator(
        capital=capital,
        target_portfolio_vol=target_vol,
        max_position_vol_contribution=0.05,
        max_single_position=max_position,
    )
    
    if not returns_df.empty:
        volatilities = allocator.calculate_stock_volatilities(returns_df)
    else:
        # Use score-based estimates
        volatilities = {}
        for s in scores_db:
            features = s.get_features() if hasattr(s, 'get_features') else {}
            vol = features.get('volatility', features.get('vol_21d', 0.30))
            volatilities[s.ticker] = vol if vol > 0 else 0.30
    
    # Calculate betas
    print("📊 Calculating betas...")
    benchmark_returns = load_benchmark_returns()
    
    if not returns_df.empty:
        betas = allocator.calculate_stock_betas(returns_df, benchmark_returns)
    else:
        # Estimate betas based on sector
        sector_betas = {
            'Technology': 1.3, 'Semiconductors': 1.5, 'Nuclear': 1.4,
            'Energy': 1.2, 'Financials': 1.1, 'Healthcare': 0.9,
            'Consumer': 0.85, 'Utilities': 0.7, 'Other': 1.0,
        }
        betas = {}
        for s in scores_db:
            sector = s.sector or 'Other'
            betas[s.ticker] = sector_betas.get(sector, 1.0)
    
    # Build input data
    scores = {s.ticker: s.score for s in scores_db}
    sector_map = {s.ticker: s.sector or 'Other' for s in scores_db}
    
    # Get current prices (use 100 as placeholder if not available)
    prices = {}
    if not returns_df.empty and prices_path.exists():
        prices_df_latest = pd.read_csv(prices_path)
        for s in scores_db:
            ticker_data = prices_df_latest[prices_df_latest['ticker'] == s.ticker]
            if len(ticker_data) > 0:
                prices[s.ticker] = ticker_data.iloc[-1]['close']
            else:
                prices[s.ticker] = 100.0
    else:
        prices = {s.ticker: 100.0 for s in scores_db}
    
    # Define sector constraints
    constraints = SectorConstraints(
        max_weights={
            'Nuclear': 0.15,
            'Semiconductors': 0.20,
            'Technology': 0.30,
            'Energy': 0.15,
        }
    )
    
    # Run allocation
    print(f"\n🔧 Running {method} allocation...")
    positions, profile = allocator.allocate_portfolio(
        scores=scores,
        volatilities=volatilities,
        betas=betas,
        sector_map=sector_map,
        prices=prices,
        method=method,
        constraints=constraints,
        target_beta=1.0,
    )
    
    # Compare with equal weight
    print("\n⚖️ Comparing with equal weight...")
    ew_positions, ew_profile = allocator.allocate_portfolio(
        scores=scores,
        volatilities=volatilities,
        betas=betas,
        sector_map=sector_map,
        prices=prices,
        method="equal",
        constraints=None,
    )
    
    # Calculate improvement
    comparison = {
        'ew_beta': ew_profile.total_beta,
        'rp_beta': profile.total_beta,
        'ew_vol': ew_profile.portfolio_vol_estimate,
        'rp_vol': profile.portfolio_vol_estimate,
        'sharpe_improvement': (
            (ew_profile.portfolio_vol_estimate - profile.portfolio_vol_estimate) / 
            ew_profile.portfolio_vol_estimate
        ) if ew_profile.portfolio_vol_estimate > 0 else 0,
    }
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 PORTFOLIO COMPARISON")
    print("=" * 70)
    print()
    print(f"{'Metric':<30} {'Equal Weight':>15} {'Risk Parity':>15} {'Change':>12}")
    print("-" * 70)
    print(f"{'Portfolio Beta':<30} {ew_profile.total_beta:>15.2f} {profile.total_beta:>15.2f} {(profile.total_beta - ew_profile.total_beta):>+12.2f}")
    print(f"{'Est. Volatility':<30} {ew_profile.portfolio_vol_estimate*100:>14.1f}% {profile.portfolio_vol_estimate*100:>14.1f}% {(profile.portfolio_vol_estimate - ew_profile.portfolio_vol_estimate)*100:>+11.1f}%")
    print(f"{'Weighted Avg Vol':<30} {ew_profile.weighted_avg_vol*100:>14.1f}% {profile.weighted_avg_vol*100:>14.1f}% {(profile.weighted_avg_vol - ew_profile.weighted_avg_vol)*100:>+11.1f}%")
    print(f"{'Concentration (HHI)':<30} {ew_profile.concentration_hhi:>15.0f} {profile.concentration_hhi:>15.0f} {(profile.concentration_hhi - ew_profile.concentration_hhi):>+12.0f}")
    print(f"{'Effective N':<30} {ew_profile.effective_n:>15.1f} {profile.effective_n:>15.1f} {(profile.effective_n - ew_profile.effective_n):>+12.1f}")
    print(f"{'Risk Tilt':<30} {ew_profile.risk_tilt:>15} {profile.risk_tilt:>15}")
    print()
    
    # Show position changes
    print("📋 TOP 10 POSITION CHANGES (Equal Weight → Risk Parity)")
    print("-" * 70)
    print(f"{'Ticker':<8} {'EW Weight':>10} {'RP Weight':>10} {'Change':>10} {'Volatility':>12} {'Beta':>8}")
    print("-" * 70)
    
    ew_weights = {p.ticker: 1.0/len(ew_positions) for p in ew_positions}
    
    for p in positions[:10]:
        ew_wt = ew_weights.get(p.ticker, 0)
        change = p.risk_weight - ew_wt
        arrow = "↓" if change < -0.01 else "↑" if change > 0.01 else "→"
        print(f"{p.ticker:<8} {ew_wt*100:>9.1f}% {p.risk_weight*100:>9.1f}% {arrow}{abs(change)*100:>8.1f}% {p.volatility*100:>11.0f}% {p.beta:>8.2f}")
    
    print()
    
    # Sector exposure comparison
    print("🏢 SECTOR EXPOSURE COMPARISON")
    print("-" * 70)
    
    all_sectors = set(profile.sector_exposure.keys()) | set(ew_profile.sector_exposure.keys())
    for sector in sorted(all_sectors, key=lambda s: -profile.sector_exposure.get(s, 0)):
        ew_exp = ew_profile.sector_exposure.get(sector, 0) * 100
        rp_exp = profile.sector_exposure.get(sector, 0) * 100
        cap = constraints.max_weights.get(sector, 1.0) * 100
        cap_str = f"(cap: {cap:.0f}%)" if cap < 100 else ""
        print(f"  {sector:<20} {ew_exp:>6.1f}% → {rp_exp:>6.1f}% {cap_str}")
    
    print()
    
    # Warnings
    if profile.warnings:
        print("⚠️ RISK WARNINGS")
        print("-" * 70)
        for warning in profile.warnings:
            print(f"  • {warning}")
        print()
    
    # Generate report
    print("📝 Generating risk report...")
    report = generate_risk_report(positions, profile)
    
    # Save report
    output_dir = Path(f"output/{run.run_id}_risk_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = output_dir / "risk_report.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"   Saved: {report_path}")
    
    # Generate AI insights
    print("\n🤖 Generating AI risk insights...")
    ai_generator = AIInsightsGenerator()
    
    if ai_generator.is_available:
        positions_dict = [
            {
                'ticker': p.ticker,
                'risk_weight': p.risk_weight,
                'volatility': p.volatility,
                'beta': p.beta,
                'sector': p.sector,
            }
            for p in positions
        ]
        
        risk_profile_dict = {
            'total_beta': profile.total_beta,
            'weighted_avg_vol': profile.weighted_avg_vol,
            'portfolio_vol_estimate': profile.portfolio_vol_estimate,
            'sector_exposure': profile.sector_exposure,
            'beta_exposure': profile.beta_exposure,
            'concentration_hhi': profile.concentration_hhi,
            'effective_n': profile.effective_n,
            'risk_tilt': profile.risk_tilt,
        }
        
        ai_insights = ai_generator.generate_risk_aware_insights(
            positions=positions_dict,
            risk_profile=risk_profile_dict,
            comparison=comparison,
        )
        
        # Append AI insights to report
        ai_report = f"""

# 🤖 AI Risk Analysis Insights

## Allocation Rationale

{ai_insights.get('allocation_rationale', 'N/A')}

## Beta & Market Exposure Analysis

{ai_insights.get('beta_analysis', 'N/A')}

## Position Sizing Recommendations

{ai_insights.get('sizing_recommendations', 'N/A')}

---
*AI insights generated by Gemini on {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
        
        ai_report_path = output_dir / "ai_risk_insights.md"
        with open(ai_report_path, 'w') as f:
            f.write(ai_report)
        print(f"   Saved: {ai_report_path}")
    else:
        print("   ⚠️ AI not available - skipping AI insights")
    
    # Save positions JSON
    positions_json = [
        {
            'ticker': p.ticker,
            'risk_weight': p.risk_weight,
            'raw_weight': p.raw_weight,
            'shares': p.shares,
            'position_value': p.position_value,
            'volatility': p.volatility,
            'vol_contribution': p.vol_contribution,
            'beta': p.beta,
            'sector': p.sector,
            'score': p.score,
        }
        for p in positions
    ]
    
    json_path = output_dir / "risk_adjusted_positions.json"
    with open(json_path, 'w') as f:
        json.dump({
            'run_id': run.run_id,
            'method': method,
            'capital': capital,
            'profile': {
                'total_beta': profile.total_beta,
                'portfolio_vol': profile.portfolio_vol_estimate,
                'risk_tilt': profile.risk_tilt,
                'effective_n': profile.effective_n,
            },
            'comparison': comparison,
            'positions': positions_json,
        }, f, indent=2)
    print(f"   Saved: {json_path}")
    
    print("\n" + "=" * 70)
    print("✅ Risk-Aware Analysis Complete!")
    print("=" * 70)
    print(f"📁 Output: {output_dir}")
    print()
    
    return positions, profile


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run risk-aware portfolio construction"
    )
    parser.add_argument(
        "--run-id", "-r",
        default=None,
        help="Analysis run ID (uses latest if not specified)"
    )
    parser.add_argument(
        "--method", "-m",
        default="risk_parity",
        choices=["risk_parity", "inverse_vol", "vol_capped", "beta_adjusted"],
        help="Allocation method"
    )
    parser.add_argument(
        "--capital", "-c",
        type=float,
        default=100_000,
        help="Portfolio capital"
    )
    parser.add_argument(
        "--target-vol", "-v",
        type=float,
        default=0.15,
        help="Target portfolio volatility"
    )
    parser.add_argument(
        "--max-position", "-p",
        type=float,
        default=0.10,
        help="Maximum single position weight"
    )
    
    args = parser.parse_args()
    
    run_risk_aware_analysis(
        run_id=args.run_id,
        method=args.method,
        capital=args.capital,
        target_vol=args.target_vol,
        max_position=args.max_position,
    )
