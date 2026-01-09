#!/usr/bin/env python3
"""
Portfolio Analysis Script
=========================
Analyzes a backtest run's portfolios and generates enriched CSVs with:
- Sector breakdown per rebalance
- Diversification scores
- Risk contributions
- Cross-sectional distribution of value/quality scores

Usage:
    python scripts/analyze_portfolio.py [--run-id <run_id>] [--output <dir>]
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.models import get_db, Run, StockScore


def load_run_data(run_id: str = None):
    """Load data for a specific run or the latest run."""
    db = get_db("data/analysis.db")
    session = db.get_session()
    
    try:
        if run_id:
            run = session.query(Run).filter_by(run_id=run_id).first()
        else:
            run = session.query(Run).order_by(Run.created_at.desc()).first()
        
        if not run:
            raise ValueError(f"Run not found: {run_id or 'latest'}")
        
        # Get scores
        scores = session.query(StockScore).filter_by(run_id=run.run_id).order_by(StockScore.rank).all()
        scores_data = [s.to_dict() for s in scores]
        
        return run.to_dict(), scores_data
    finally:
        session.close()


def load_positions_data(run_id: str = None):
    """Load positions from backtest output."""
    # Try run-specific folder first
    if run_id:
        run_folder = Path("output") / f"run_{run_id[:16]}"
        positions_path = run_folder / "backtest_positions.csv"
        if positions_path.exists():
            return pd.read_csv(positions_path, parse_dates=['date'])
    
    # Fallback to legacy path
    positions_path = Path("output/backtest_positions.csv")
    if not positions_path.exists():
        return None
    return pd.read_csv(positions_path, parse_dates=['date'])


def load_returns_data(run_id: str = None):
    """Load returns from backtest output."""
    # Try run-specific folder first
    if run_id:
        run_folder = Path("output") / f"run_{run_id[:16]}"
        returns_path = run_folder / "backtest_returns.csv"
        if returns_path.exists():
            return pd.read_csv(returns_path, parse_dates=['date'])
    
    # Fallback to legacy path
    returns_path = Path("output/backtest_returns.csv")
    if not returns_path.exists():
        return None
    return pd.read_csv(returns_path, parse_dates=['date'])


def load_price_data():
    """Load price data for volatility calculations."""
    price_path = Path("data/prices.csv")
    if not price_path.exists():
        return None
    df = pd.read_csv(price_path, parse_dates=['date'])
    return df


def calculate_diversification_score(weights: pd.Series, correlation_matrix: pd.DataFrame = None) -> float:
    """
    Calculate diversification score.
    
    Simple version: 1 - HHI (Herfindahl-Hirschman Index)
    Values closer to 1 = more diversified
    """
    if len(weights) == 0:
        return 0.0
    
    hhi = (weights ** 2).sum()
    return 1 - hhi


def calculate_effective_n(weights: pd.Series) -> float:
    """Calculate effective number of holdings (inverse HHI)."""
    if len(weights) == 0:
        return 0.0
    hhi = (weights ** 2).sum()
    return 1 / hhi if hhi > 0 else 0


def calculate_risk_contributions(weights: pd.Series, volatilities: pd.Series) -> pd.Series:
    """
    Calculate marginal risk contributions (simplified, assuming no correlation).
    
    Risk contribution = weight * volatility / portfolio_vol
    """
    if len(weights) == 0:
        return pd.Series()
    
    # Simple weighted volatility
    weighted_vol = weights * volatilities
    total_vol = weighted_vol.sum()
    
    if total_vol == 0:
        return pd.Series(0, index=weights.index)
    
    risk_contrib = weighted_vol / total_vol
    return risk_contrib


def get_sector_mapping():
    """
    Get sector mapping for stocks.
    
    Priority:
    1. Cached sector data from data/sectors.json (fetched via yfinance)
    2. Fallback hardcoded mapping for common tickers
    
    Run `python scripts/fetch_sector_data.py` to populate the cache.
    """
    # Start with hardcoded fallback mapping
    fallback_mapping = {
        'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 
        'AMZN': 'Consumer Cyclical', 'META': 'Technology', 'NVDA': 'Technology',
        'TSLA': 'Consumer Cyclical', 'AMD': 'Technology', 'INTC': 'Technology',
        'CRM': 'Technology', 'ADBE': 'Technology', 'NFLX': 'Communication Services',
        'JPM': 'Financial Services', 'BAC': 'Financial Services', 'WFC': 'Financial Services',
        'GS': 'Financial Services', 'MS': 'Financial Services', 'C': 'Financial Services',
        'V': 'Financial Services', 'MA': 'Financial Services', 'AXP': 'Financial Services',
        'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare',
        'MRK': 'Healthcare', 'ABBV': 'Healthcare', 'LLY': 'Healthcare',
        'PG': 'Consumer Defensive', 'KO': 'Consumer Defensive', 'PEP': 'Consumer Defensive',
        'WMT': 'Consumer Defensive', 'COST': 'Consumer Defensive', 'TGT': 'Consumer Cyclical',
        'HD': 'Consumer Cyclical', 'NKE': 'Consumer Cyclical', 'MCD': 'Consumer Cyclical',
        'DIS': 'Communication Services', 'CMCSA': 'Communication Services',
        'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy',
        'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities',
        'URA': 'Energy', 'NLR': 'Energy', 'URNM': 'Energy',
        'BA': 'Industrials', 'CAT': 'Industrials', 'GE': 'Industrials',
        'MMM': 'Industrials', 'HON': 'Industrials', 'UPS': 'Industrials',
    }
    
    # Try to load cached sector data
    sector_cache_path = Path(__file__).parent.parent / "data" / "sectors.json"
    if sector_cache_path.exists():
        try:
            with open(sector_cache_path, 'r') as f:
                cached_mapping = json.load(f)
            # Merge: cached data takes precedence over fallback
            merged = {**fallback_mapping, **cached_mapping}
            return merged
        except Exception as e:
            import warnings
            warnings.warn(f"Failed to load sector cache: {e}")
    
    return fallback_mapping


def analyze_portfolio(run_id: str = None, output_dir: str = "output"):
    """
    Main analysis function.
    
    Args:
        run_id: Specific run ID or None for latest
        output_dir: Output directory for enriched CSVs
    """
    print("=" * 70)
    print("PORTFOLIO ANALYSIS")
    print("=" * 70)
    
    # Load run data
    print("\n📥 Loading run data...")
    run_data, scores_data = load_run_data(run_id)
    run_id = run_data['run_id']
    print(f"   Run: {run_id}")
    print(f"   Name: {run_data.get('name', 'N/A')}")
    print(f"   Stocks: {len(scores_data)}")
    
    # Load positions (from run-specific folder or legacy path)
    positions_df = load_positions_data(run_id)
    if positions_df is None:
        print("   ⚠️ No positions data found, using scores only")
        positions_df = pd.DataFrame()
    else:
        print(f"   Positions: {len(positions_df)} rows")
    
    # Load price data for volatility
    price_df = load_price_data()
    volatilities = {}
    if price_df is not None:
        # Calculate 20-day volatility for each ticker
        for ticker in price_df['ticker'].unique():
            ticker_prices = price_df[price_df['ticker'] == ticker].sort_values('date')
            if len(ticker_prices) > 20:
                returns = ticker_prices['close'].pct_change()
                volatilities[ticker] = returns.tail(252).std()  # Use last year
    
    # Get sector mapping
    sector_map = get_sector_mapping()
    
    # Create scores DataFrame with features
    scores_df = pd.DataFrame(scores_data)
    
    # Extract features into columns
    if 'features' in scores_df.columns:
        feature_cols = []
        for idx, row in scores_df.iterrows():
            features = row.get('features', {})
            if isinstance(features, str):
                try:
                    features = json.loads(features)
                except:
                    features = {}
            feature_cols.append(features)
        
        features_df = pd.DataFrame(feature_cols)
        scores_df = pd.concat([scores_df.drop(columns=['features']), features_df], axis=1)
    
    # Always map sector from current cache (overrides database values)
    # This ensures latest sector classifications are always used
    scores_df['sector'] = scores_df['ticker'].map(sector_map).fillna('Other')
    
    # Add volatility
    scores_df['volatility_annual'] = scores_df['ticker'].map(volatilities)
    scores_df['volatility_annual'] = scores_df['volatility_annual'].fillna(scores_df['volatility_annual'].mean())
    
    print("\n📊 Analyzing portfolio composition...")
    
    # ========== PORTFOLIO ENRICHMENT ==========
    
    # Calculate equal weights
    n_stocks = len(scores_df)
    scores_df['equal_weight'] = 1 / n_stocks
    
    # Calculate risk-parity weights (inverse volatility)
    inv_vol = 1 / scores_df['volatility_annual'].replace(0, 0.01)
    scores_df['risk_parity_weight'] = inv_vol / inv_vol.sum()
    
    # Calculate risk contributions
    scores_df['risk_contrib_ew'] = calculate_risk_contributions(
        scores_df['equal_weight'],
        scores_df['volatility_annual']
    )
    scores_df['risk_contrib_rp'] = calculate_risk_contributions(
        scores_df['risk_parity_weight'],
        scores_df['volatility_annual']
    )
    
    # Calculate value score (from PE/PB if available)
    if 'pe_ratio' in scores_df.columns:
        pe_median = scores_df['pe_ratio'].median()
        scores_df['value_score'] = np.where(
            scores_df['pe_ratio'] > 0,
            100 * (pe_median / scores_df['pe_ratio']),  # Higher score = lower PE = better value
            50
        )
        scores_df['value_score'] = scores_df['value_score'].clip(0, 100)
    else:
        scores_df['value_score'] = scores_df.get('fund_score', 50)
    
    # Quality score (using fund_score or derived)
    if 'fund_score' in scores_df.columns:
        scores_df['quality_score'] = scores_df['fund_score']
    else:
        scores_df['quality_score'] = 50
    
    # ========== SECTOR ANALYSIS ==========
    
    print("\n🏢 Sector Breakdown:")
    sector_analysis = scores_df.groupby('sector').agg({
        'ticker': 'count',
        'equal_weight': 'sum',
        'risk_parity_weight': 'sum',
        'volatility_annual': 'mean',
        'risk_contrib_ew': 'sum',
        'risk_contrib_rp': 'sum',
        'value_score': 'mean',
        'quality_score': 'mean',
    }).rename(columns={
        'ticker': 'count',
        'volatility_annual': 'avg_volatility'
    })
    
    sector_analysis['ew_pct'] = sector_analysis['equal_weight'] * 100
    sector_analysis['rp_pct'] = sector_analysis['risk_parity_weight'] * 100
    sector_analysis['risk_ew_pct'] = sector_analysis['risk_contrib_ew'] * 100
    sector_analysis['risk_rp_pct'] = sector_analysis['risk_contrib_rp'] * 100
    
    print(sector_analysis[['count', 'ew_pct', 'rp_pct', 'avg_volatility', 'value_score', 'quality_score']].to_string())
    
    # ========== DIVERSIFICATION METRICS ==========
    
    print("\n📈 Diversification Metrics:")
    
    div_score_ew = calculate_diversification_score(scores_df['equal_weight'])
    div_score_rp = calculate_diversification_score(scores_df['risk_parity_weight'])
    eff_n_ew = calculate_effective_n(scores_df['equal_weight'])
    eff_n_rp = calculate_effective_n(scores_df['risk_parity_weight'])
    
    # Sector-level diversification
    sector_weights_ew = sector_analysis['equal_weight']
    sector_weights_rp = sector_analysis['risk_parity_weight']
    sector_div_ew = calculate_diversification_score(sector_weights_ew)
    sector_div_rp = calculate_diversification_score(sector_weights_rp)
    
    print(f"   Stock-Level Diversification (EW): {div_score_ew:.4f}")
    print(f"   Stock-Level Diversification (RP): {div_score_rp:.4f}")
    print(f"   Effective N Stocks (EW): {eff_n_ew:.1f}")
    print(f"   Effective N Stocks (RP): {eff_n_rp:.1f}")
    print(f"   Sector-Level Diversification (EW): {sector_div_ew:.4f}")
    print(f"   Sector-Level Diversification (RP): {sector_div_rp:.4f}")
    
    # ========== SCORE DISTRIBUTIONS ==========
    
    print("\n📊 Score Distributions:")
    
    score_stats = {
        'Value Score': {
            'mean': scores_df['value_score'].mean(),
            'std': scores_df['value_score'].std(),
            'min': scores_df['value_score'].min(),
            'max': scores_df['value_score'].max(),
            'median': scores_df['value_score'].median(),
        },
        'Quality Score': {
            'mean': scores_df['quality_score'].mean(),
            'std': scores_df['quality_score'].std(),
            'min': scores_df['quality_score'].min(),
            'max': scores_df['quality_score'].max(),
            'median': scores_df['quality_score'].median(),
        },
    }
    
    if 'tech_score' in scores_df.columns:
        score_stats['Tech Score'] = {
            'mean': scores_df['tech_score'].mean(),
            'std': scores_df['tech_score'].std(),
            'min': scores_df['tech_score'].min(),
            'max': scores_df['tech_score'].max(),
            'median': scores_df['tech_score'].median(),
        }
    
    for score_name, stats in score_stats.items():
        print(f"\n   {score_name}:")
        print(f"      Mean: {stats['mean']:.2f}, Std: {stats['std']:.2f}")
        print(f"      Range: [{stats['min']:.2f}, {stats['max']:.2f}], Median: {stats['median']:.2f}")
    
    # ========== OUTPUT ENRICHED CSV ==========
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Portfolio enriched CSV
    enriched_cols = [
        'ticker', 'rank', 'score', 'sector',
        'equal_weight', 'risk_parity_weight',
        'volatility_annual', 'risk_contrib_ew', 'risk_contrib_rp',
        'value_score', 'quality_score',
    ]
    
    # Add optional columns if they exist
    for col in ['tech_score', 'fund_score', 'sent_score', 'rsi', 'pe_ratio', 'pb_ratio']:
        if col in scores_df.columns:
            enriched_cols.append(col)
    
    enriched_df = scores_df[[c for c in enriched_cols if c in scores_df.columns]].copy()
    
    enriched_file = output_path / f"portfolio_enriched_{run_id[:16]}.csv"
    enriched_df.to_csv(enriched_file, index=False)
    print(f"\n✅ Saved enriched portfolio: {enriched_file}")
    
    # Sector analysis CSV
    sector_file = output_path / f"sector_analysis_{run_id[:16]}.csv"
    sector_analysis.to_csv(sector_file)
    print(f"✅ Saved sector analysis: {sector_file}")
    
    # Summary metrics JSON
    summary = {
        'run_id': run_id,
        'run_name': run_data.get('name'),
        'n_stocks': n_stocks,
        'n_sectors': len(sector_analysis),
        'diversification': {
            'stock_level_ew': div_score_ew,
            'stock_level_rp': div_score_rp,
            'sector_level_ew': sector_div_ew,
            'sector_level_rp': sector_div_rp,
            'effective_n_ew': eff_n_ew,
            'effective_n_rp': eff_n_rp,
        },
        'score_distributions': score_stats,
        'sector_breakdown': sector_analysis[['count', 'ew_pct', 'rp_pct']].to_dict(),
        'top_sectors': sector_analysis.nlargest(3, 'count').index.tolist(),
        'generated_at': datetime.now().isoformat(),
    }
    
    summary_file = output_path / f"portfolio_summary_{run_id[:16]}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"✅ Saved summary metrics: {summary_file}")
    
    # ========== PER-REBALANCE ANALYSIS (if positions available) ==========
    
    if len(positions_df) > 0:
        print("\n📅 Per-Rebalance Analysis:")
        
        rebalance_data = []
        for date in positions_df['date'].unique():
            date_positions = positions_df[positions_df['date'] == date]
            tickers = date_positions['ticker'].tolist()
            weights = date_positions['weight'].values
            
            # Get sectors for these tickers
            sectors = [sector_map.get(t, 'Other') for t in tickers]
            
            # Calculate metrics
            n_holdings = len(tickers)
            div_score = calculate_diversification_score(pd.Series(weights))
            eff_n = calculate_effective_n(pd.Series(weights))
            
            # Sector concentration
            sector_df = pd.DataFrame({'sector': sectors, 'weight': weights})
            sector_weights = sector_df.groupby('sector')['weight'].sum()
            top_sector = sector_weights.idxmax()
            top_sector_weight = sector_weights.max()
            
            rebalance_data.append({
                'date': date,
                'n_holdings': n_holdings,
                'diversification_score': div_score,
                'effective_n': eff_n,
                'top_sector': top_sector,
                'top_sector_weight': top_sector_weight,
                'n_sectors': len(sector_weights),
            })
        
        rebalance_df = pd.DataFrame(rebalance_data)
        rebalance_file = output_path / f"rebalance_analysis_{run_id[:16]}.csv"
        rebalance_df.to_csv(rebalance_file, index=False)
        print(f"✅ Saved rebalance analysis: {rebalance_file}")
        
        print(f"\n   Rebalance dates: {len(rebalance_df)}")
        print(f"   Avg Holdings: {rebalance_df['n_holdings'].mean():.1f}")
        print(f"   Avg Diversification: {rebalance_df['diversification_score'].mean():.4f}")
        print(f"   Avg Effective N: {rebalance_df['effective_n'].mean():.1f}")
    
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    
    return enriched_df, sector_analysis, summary


def main():
    parser = argparse.ArgumentParser(description="Analyze backtest portfolio composition")
    parser.add_argument("--run-id", type=str, help="Specific run ID (default: latest)")
    parser.add_argument("--output", type=str, default="output", help="Output directory")
    
    args = parser.parse_args()
    
    try:
        analyze_portfolio(run_id=args.run_id, output_dir=args.output)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
