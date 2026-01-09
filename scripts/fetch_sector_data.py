#!/usr/bin/env python3
"""
Fetch and cache sector data for all watchlist stocks using yfinance.

This script:
1. Loads all tickers from watchlists
2. Fetches sector/industry info from Yahoo Finance
3. Caches results to data/sectors.csv
4. Can be run periodically to update classifications

Usage:
    python scripts/fetch_sector_data.py
    python scripts/fetch_sector_data.py --watchlist custom_list
    python scripts/fetch_sector_data.py --force  # Re-fetch all
"""

import sys
from pathlib import Path
import argparse
import json
from datetime import datetime
from typing import Dict, Optional, List
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed. Run: pip install yfinance")
    sys.exit(1)


# Default sector cache path
SECTOR_CACHE_PATH = Path("data/sectors.csv")
SECTOR_JSON_PATH = Path("data/sectors.json")


def load_existing_cache() -> pd.DataFrame:
    """Load existing sector cache if it exists."""
    if SECTOR_CACHE_PATH.exists():
        try:
            df = pd.read_csv(SECTOR_CACHE_PATH)
            if len(df) > 0:
                return df
        except Exception:
            pass
    return pd.DataFrame(columns=['ticker', 'sector', 'industry', 'name', 'market_cap', 'updated_at'])


def fetch_ticker_info(ticker: str, retries: int = 2) -> Dict:
    """Fetch sector info for a single ticker with retry logic."""
    for attempt in range(retries + 1):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return {
                'ticker': ticker.upper(),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'name': info.get('shortName', info.get('longName', '')),
                'market_cap': info.get('marketCap'),
                'quote_type': info.get('quoteType', ''),  # EQUITY, ETF, etc.
                'updated_at': datetime.now().isoformat(),
            }
        except Exception as e:
            if attempt < retries:
                time.sleep(0.5)
                continue
            return {
                'ticker': ticker.upper(),
                'sector': '',
                'industry': '',
                'name': '',
                'market_cap': None,
                'quote_type': '',
                'error': str(e),
                'updated_at': datetime.now().isoformat(),
            }


def classify_etf(ticker: str, name: str) -> str:
    """Classify ETF into a pseudo-sector based on name/ticker."""
    ticker_upper = ticker.upper()
    name_lower = (name or '').lower()
    
    # Precious metals
    if any(x in ticker_upper for x in ['GLD', 'SLV', 'GOLD', 'PALL', 'PPLT']):
        return 'Precious Metals'
    if any(x in name_lower for x in ['gold', 'silver', 'platinum', 'palladium', 'precious']):
        return 'Precious Metals'
    
    # Mining
    if any(x in ticker_upper for x in ['GDX', 'GDXJ', 'RING']):
        return 'Materials'
    
    # Energy/Uranium
    if any(x in ticker_upper for x in ['URA', 'URNM', 'NLR', 'XLE', 'OIH']):
        return 'Energy'
    
    # Technology
    if any(x in ticker_upper for x in ['QQQ', 'XLK', 'VGT', 'ARKK', 'ARKW']):
        return 'Technology'
    
    # Broad market
    if any(x in ticker_upper for x in ['SPY', 'IVV', 'VOO', 'VTI', 'IWM', 'DIA']):
        return 'Broad Market ETF'
    
    # Financials
    if any(x in ticker_upper for x in ['XLF', 'VFH', 'KRE']):
        return 'Financial Services'
    
    # Healthcare
    if any(x in ticker_upper for x in ['XLV', 'VHT', 'IBB', 'XBI']):
        return 'Healthcare'
    
    # Real Estate
    if any(x in ticker_upper for x in ['VNQ', 'XLRE', 'IYR']):
        return 'Real Estate'
    
    return 'ETF - Other'


def fetch_all_sectors(
    tickers: List[str],
    existing_cache: pd.DataFrame,
    force: bool = False,
    batch_size: int = 10,
    delay: float = 0.2,
) -> pd.DataFrame:
    """Fetch sector data for all tickers, using cache where available."""
    
    results = []
    cached_tickers = set(existing_cache['ticker'].str.upper()) if len(existing_cache) > 0 else set()
    
    # Separate tickers to fetch vs cached
    tickers_to_fetch = []
    for t in tickers:
        t_upper = t.upper()
        if force or t_upper not in cached_tickers:
            tickers_to_fetch.append(t_upper)
        else:
            # Use cached data
            cached_row = existing_cache[existing_cache['ticker'].str.upper() == t_upper].iloc[0].to_dict()
            results.append(cached_row)
    
    print(f"Using cached data for {len(results)} tickers")
    print(f"Fetching fresh data for {len(tickers_to_fetch)} tickers")
    print()
    
    # Fetch in batches
    for i, ticker in enumerate(tickers_to_fetch):
        if i > 0 and i % batch_size == 0:
            print(f"  Progress: {i}/{len(tickers_to_fetch)} ({i*100//len(tickers_to_fetch)}%)")
            time.sleep(delay)
        
        info = fetch_ticker_info(ticker)
        
        # Classify ETFs
        if info.get('quote_type') == 'ETF' and not info.get('sector'):
            info['sector'] = classify_etf(ticker, info.get('name', ''))
            info['industry'] = 'Exchange Traded Fund'
        
        results.append(info)
    
    df = pd.DataFrame(results)
    return df


def generate_sector_mapping(df: pd.DataFrame) -> Dict[str, str]:
    """Generate sector mapping dictionary from DataFrame."""
    mapping = {}
    for _, row in df.iterrows():
        ticker = row['ticker']
        sector = row.get('sector', '')
        if ticker and sector:
            mapping[ticker] = sector
    return mapping


def main():
    parser = argparse.ArgumentParser(description='Fetch and cache sector data')
    parser.add_argument('--watchlist', type=str, help='Specific watchlist to process')
    parser.add_argument('--force', action='store_true', help='Force re-fetch all tickers')
    parser.add_argument('--output', type=str, default=str(SECTOR_CACHE_PATH), help='Output CSV path')
    args = parser.parse_args()
    
    print("=" * 60)
    print("SECTOR DATA FETCHER")
    print("=" * 60)
    print()
    
    # Load watchlists
    from src.data.watchlists import WatchlistManager
    wm = WatchlistManager.from_config_dir('config')
    
    if args.watchlist:
        watchlist = wm.get_watchlist(args.watchlist)
        if not watchlist:
            print(f"Error: Watchlist '{args.watchlist}' not found")
            return 1
        tickers = list(set(s.upper() for s in watchlist.symbols))
        print(f"Processing watchlist: {args.watchlist} ({len(tickers)} tickers)")
    else:
        # Get all unique tickers from all watchlists
        all_tickers = set()
        watchlist_summaries = wm.list_watchlists()
        for summary in watchlist_summaries:
            wl_key = summary.get('key') if isinstance(summary, dict) else getattr(summary, 'key', None)
            if wl_key:
                wl = wm.get_watchlist(wl_key)
                if wl:
                    symbols = wl.symbols if hasattr(wl, 'symbols') else wl.get('symbols', [])
                    all_tickers.update(s.upper() for s in symbols)
        tickers = list(all_tickers)
        print(f"Processing all watchlists: {len(tickers)} unique tickers")
    
    print()
    
    # Load existing cache
    existing_cache = load_existing_cache()
    print(f"Existing cache: {len(existing_cache)} tickers")
    
    # Fetch sector data
    df = fetch_all_sectors(tickers, existing_cache, force=args.force)
    
    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\nSaved sector data to: {output_path}")
    
    # Also save as JSON mapping for easy use
    mapping = generate_sector_mapping(df)
    json_path = output_path.with_suffix('.json')
    with open(json_path, 'w') as f:
        json.dump(mapping, f, indent=2)
    print(f"Saved sector mapping to: {json_path}")
    
    # Print summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if len(df) > 0 and 'sector' in df.columns:
        classified = df[df['sector'] != '']
        sector_counts = classified.groupby('sector').size().sort_values(ascending=False)
        print(f"\nSector breakdown ({len(df)} total, {len(classified)} classified):")
        for sector, count in sector_counts.items():
            print(f"  {sector:30} {count:4}")
        
        unclassified = df[df['sector'] == '']
        if len(unclassified) > 0:
            print(f"\nUnclassified tickers ({len(unclassified)}):")
            print(f"  {list(unclassified['ticker'].head(20))}")
    else:
        print("\nNo data fetched.")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
