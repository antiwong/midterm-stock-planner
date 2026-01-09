#!/usr/bin/env python3
"""
Download Comprehensive Fundamentals Data
========================================
Downloads fundamental data (PE, PB, ROE, margins, etc.) for all tickers
in the watchlist and saves to data/fundamentals.csv

Usage:
    python scripts/download_fundamentals.py [--watchlist WATCHLIST_NAME] [--output OUTPUT_FILE]
"""

import sys
import argparse
import pandas as pd
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.fundamental.data_fetcher import FundamentalDataFetcher, fetch_fundamentals_for_universe
    FUNDAMENTAL_FETCHER_AVAILABLE = True
except ImportError:
    FUNDAMENTAL_FETCHER_AVAILABLE = False
    print("⚠️  Warning: src.fundamental.data_fetcher not available. Using yfinance directly.")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("❌ Error: yfinance not installed. Install with: pip install yfinance")


def load_watchlist_tickers(watchlist_name: Optional[str] = None) -> List[str]:
    """Load tickers from watchlist."""
    watchlist_path = Path("config/watchlists.yaml")
    
    if not watchlist_path.exists():
        print(f"❌ Watchlist file not found: {watchlist_path}")
        return []
    
    with open(watchlist_path) as f:
        watchlists = yaml.safe_load(f)
    
    if watchlist_name:
        if watchlist_name not in watchlists:
            print(f"❌ Watchlist '{watchlist_name}' not found")
            print(f"Available watchlists: {', '.join(watchlists.keys())}")
            return []
        data = watchlists[watchlist_name]
        # Support both 'tickers' and 'symbols' keys
        return data.get('tickers', data.get('symbols', []))
    else:
        # Use first watchlist or combine all
        if watchlists:
            # Try to find a default watchlist
            for name, data in watchlists.items():
                tickers = data.get('tickers', data.get('symbols', []))
                if tickers:
                    print(f"📋 Using watchlist: {name}")
                    return tickers
        return []


def fetch_fundamentals_yfinance(ticker: str) -> Optional[dict]:
    """Fetch fundamentals using yfinance directly."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Extract key metrics
        data = {
            'ticker': ticker,
            'date': datetime.now().strftime('%Y-%m-%d'),
            
            # Valuation
            'pe': info.get('trailingPE') or info.get('forwardPE'),
            'pb': info.get('priceToBook'),
            'ps': info.get('priceToSalesTrailing12Months'),
            'peg': info.get('pegRatio'),
            
            # Profitability
            'roe': info.get('returnOnEquity'),  # As decimal (e.g., 0.15 for 15%)
            'roa': info.get('returnOnAssets'),
            'net_margin': info.get('profitMargins'),  # As decimal
            'gross_margin': info.get('grossMargins'),  # As decimal
            'operating_margin': info.get('operatingMargins'),  # As decimal
            
            # Financial Health
            'debt_to_equity': info.get('debtToEquity'),
            'current_ratio': info.get('currentRatio'),
            'quick_ratio': info.get('quickRatio'),
            
            # Growth
            'revenue_growth': info.get('revenueGrowth'),
            'earnings_growth': info.get('earningsQuarterlyGrowth'),
            
            # Market
            'market_cap': info.get('marketCap'),
            'enterprise_value': info.get('enterpriseValue'),
        }
        
        return data
        
    except Exception as e:
        print(f"  ⚠️  Error fetching {ticker}: {e}")
        return None


def download_fundamentals(
    tickers: List[str],
    output_path: Path = Path("data/fundamentals.csv"),
    delay: float = 0.5
) -> pd.DataFrame:
    """
    Download fundamentals for a list of tickers.
    
    Args:
        tickers: List of stock tickers
        output_path: Path to save CSV file
        delay: Delay between requests (seconds)
    
    Returns:
        DataFrame with fundamental data
    """
    print(f"📥 Downloading fundamentals for {len(tickers)} tickers...")
    print(f"   Output: {output_path}")
    print()
    
    results = []
    failed = []
    
    for i, ticker in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] Fetching {ticker}...", end=' ', flush=True)
        
        if FUNDAMENTAL_FETCHER_AVAILABLE:
            fetcher = FundamentalDataFetcher()
            metrics = fetcher.get_financial_metrics(ticker)
            if metrics:
                data = metrics.to_dict()
                # Convert to expected format
                result = {
                    'ticker': ticker,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'pe': data.get('trailing_pe') or data.get('forward_pe'),
                    'pb': data.get('price_to_book'),
                    'roe': data.get('return_on_equity'),
                    'net_margin': data.get('profit_margin'),
                    'gross_margin': data.get('gross_margin'),
                    'operating_margin': data.get('operating_margin'),
                    'debt_to_equity': data.get('debt_to_equity'),
                    'current_ratio': data.get('current_ratio'),
                    'revenue_growth': data.get('revenue_growth'),
                    'market_cap': data.get('market_cap'),
                }
                results.append(result)
                print("✅")
            else:
                failed.append(ticker)
                print("❌")
        elif YFINANCE_AVAILABLE:
            data = fetch_fundamentals_yfinance(ticker)
            if data:
                results.append(data)
                print("✅")
            else:
                failed.append(ticker)
                print("❌")
        else:
            print("❌ No data fetcher available")
            break
        
        # Rate limiting
        if i < len(tickers):
            time.sleep(delay)
    
    print()
    if failed:
        print(f"⚠️  Failed to fetch {len(failed)} tickers: {', '.join(failed[:10])}")
        if len(failed) > 10:
            print(f"   ... and {len(failed) - 10} more")
    
    if not results:
        print("❌ No data fetched")
        return pd.DataFrame()
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Save to CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # If file exists, append or replace?
    if output_path.exists():
        existing_df = pd.read_csv(output_path)
        # Merge: keep existing data, update with new data
        # For same ticker+date, prefer new data
        existing_df = existing_df[~(
            (existing_df['ticker'].isin(df['ticker'])) & 
            (existing_df['date'] == df['date'].iloc[0] if 'date' in df.columns else False)
        )]
        df = pd.concat([existing_df, df], ignore_index=True)
        df = df.sort_values(['ticker', 'date'], ascending=[True, False])
        df = df.drop_duplicates(subset=['ticker', 'date'], keep='first')
    
    df.to_csv(output_path, index=False)
    print(f"✅ Saved {len(df)} records to {output_path}")
    
    # Show summary
    print()
    print("📊 Summary:")
    print(f"   Total records: {len(df)}")
    print(f"   Unique tickers: {df['ticker'].nunique()}")
    print(f"   Columns: {', '.join(df.columns)}")
    print()
    
    # Check data completeness
    print("📈 Data Completeness:")
    for col in ['pe', 'pb', 'roe', 'net_margin', 'gross_margin']:
        if col in df.columns:
            count = df[col].notna().sum()
            pct = count / len(df) * 100
            print(f"   {col:15s}: {count:3d}/{len(df)} ({pct:5.1f}%)")
    
    return df


def main():
    parser = argparse.ArgumentParser(
        description="Download comprehensive fundamentals data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download for default watchlist
  python scripts/download_fundamentals.py
  
  # Download for specific watchlist
  python scripts/download_fundamentals.py --watchlist nasdaq100
  
  # Download for specific tickers
  python scripts/download_fundamentals.py --tickers AAPL MSFT GOOGL
  
  # Custom output file
  python scripts/download_fundamentals.py --output data/my_fundamentals.csv
        """
    )
    
    parser.add_argument("--watchlist", type=str, help="Watchlist name from watchlists.yaml")
    parser.add_argument("--tickers", nargs="+", help="Specific tickers to download")
    parser.add_argument("--output", type=str, default="data/fundamentals.csv",
                       help="Output CSV file path")
    parser.add_argument("--delay", type=float, default=0.5,
                       help="Delay between requests (seconds)")
    
    args = parser.parse_args()
    
    # Get tickers
    if args.tickers:
        tickers = args.tickers
        print(f"📋 Using provided tickers: {len(tickers)}")
    else:
        tickers = load_watchlist_tickers(args.watchlist)
        if not tickers:
            print("❌ No tickers found. Use --watchlist or --tickers")
            return 1
    
    print(f"📋 Total tickers: {len(tickers)}")
    print()
    
    # Download
    output_path = Path(args.output)
    df = download_fundamentals(tickers, output_path, delay=args.delay)
    
    if df.empty:
        return 1
    
    print("✅ Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
