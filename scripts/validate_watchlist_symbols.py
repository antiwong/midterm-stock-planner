#!/usr/bin/env python3
"""
Validate Watchlist Symbols
==========================
Check if all symbols in a watchlist are valid and can be fetched.
"""

import sys
from pathlib import Path
import yfinance as yf
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.app.dashboard.data import (
    load_watchlists,
    get_all_available_watchlists,
    load_custom_watchlist_by_id
)
from src.app.dashboard.data import load_watchlists


def validate_symbol(ticker: str, timeout: int = 5) -> dict:
    """Validate a single symbol.
    
    Args:
        ticker: Stock ticker symbol
        timeout: Timeout in seconds
    
    Returns:
        Dictionary with validation results
    """
    result = {
        'ticker': ticker,
        'valid': False,
        'exists': False,
        'has_data': False,
        'error': None,
        'info': {}
    }
    
    try:
        # Try to fetch basic info
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if info and len(info) > 1:  # Valid ticker has info
            result['exists'] = True
            result['valid'] = True
            result['info'] = {
                'name': info.get('longName') or info.get('shortName', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'market_cap': info.get('marketCap', 'N/A'),
                'currency': info.get('currency', 'N/A'),
            }
            
            # Try to fetch historical data
            try:
                hist = stock.history(period="1mo")
                if not hist.empty:
                    result['has_data'] = True
                else:
                    result['error'] = "No historical data available"
            except Exception as e:
                result['error'] = f"Could not fetch history: {str(e)}"
        else:
            result['error'] = "No info returned (invalid ticker?)"
            result['valid'] = False
            
    except Exception as e:
        result['error'] = str(e)
        result['valid'] = False
    
    return result


def validate_watchlist(watchlist_id: str):
    """Validate all symbols in a watchlist.
    
    Args:
        watchlist_id: Watchlist ID or name
    """
    print("=" * 70)
    print(f"VALIDATING WATCHLIST: {watchlist_id}")
    print("=" * 70)
    print()
    
    # Load watchlist - try custom watchlist first
    watchlist = None
    try:
        custom_wl = load_custom_watchlist_by_id(watchlist_id)
        if custom_wl:
            watchlist = {
                'id': custom_wl['watchlist_id'],
                'name': custom_wl['name'],
                'symbols': custom_wl.get('symbols', [])
            }
    except:
        pass
    
    # If not found, try standard watchlists
    if not watchlist:
        watchlists = load_watchlists()
        for wl_id, wl_symbols in watchlists.items():
            if wl_id == watchlist_id:
                watchlist = {
                    'id': wl_id,
                    'name': wl_id,
                    'symbols': wl_symbols
                }
                break
    
    if not watchlist:
        # Try custom watchlist
        try:
            custom_wl = load_custom_watchlist_by_id(watchlist_id)
            if custom_wl:
                watchlist = {
                    'id': custom_wl['watchlist_id'],
                    'name': custom_wl['name'],
                    'symbols': custom_wl.get('symbols', [])
                }
        except:
            pass
    
    if not watchlist:
        print(f"❌ ERROR: Watchlist '{watchlist_id}' not found")
        print()
        print("Available watchlists:")
        for wl in watchlists:
            print(f"   - {wl.get('id')} ({wl.get('name', 'N/A')})")
        return
    
    symbols = watchlist.get('symbols', [])
    if not symbols:
        print(f"⚠️  WARNING: Watchlist has no symbols")
        return
    
    print(f"✅ Watchlist found: {watchlist.get('name', watchlist_id)}")
    print(f"   Total symbols: {len(symbols)}")
    print()
    print("Validating symbols...")
    print()
    
    # Validate each symbol
    results = []
    valid_count = 0
    invalid_count = 0
    no_data_count = 0
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] Checking {symbol}...", end=" ", flush=True)
        result = validate_symbol(symbol)
        results.append(result)
        
        if result['valid'] and result['has_data']:
            print("✅ Valid")
            valid_count += 1
        elif result['exists'] and not result['has_data']:
            print(f"⚠️  Exists but no data: {result.get('error', 'Unknown')}")
            no_data_count += 1
        else:
            print(f"❌ Invalid: {result.get('error', 'Unknown error')}")
            invalid_count += 1
    
    print()
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print()
    print(f"Total symbols: {len(symbols)}")
    print(f"✅ Valid with data: {valid_count} ({valid_count/len(symbols)*100:.1f}%)")
    print(f"⚠️  Exists but no data: {no_data_count} ({no_data_count/len(symbols)*100:.1f}%)")
    print(f"❌ Invalid: {invalid_count} ({invalid_count/len(symbols)*100:.1f}%)")
    print()
    
    # Show invalid symbols
    if invalid_count > 0:
        print("❌ INVALID SYMBOLS:")
        for result in results:
            if not result['valid']:
                print(f"   - {result['ticker']}: {result.get('error', 'Unknown error')}")
        print()
    
    # Show symbols with no data
    if no_data_count > 0:
        print("⚠️  SYMBOLS WITH NO DATA:")
        for result in results:
            if result['exists'] and not result['has_data']:
                print(f"   - {result['ticker']}: {result.get('error', 'No data')}")
        print()
    
    # Show some valid symbols as examples
    valid_results = [r for r in results if r['valid'] and r['has_data']]
    if valid_results:
        print("✅ SAMPLE VALID SYMBOLS (first 5):")
        for result in valid_results[:5]:
            info = result.get('info', {})
            print(f"   - {result['ticker']}: {info.get('name', 'N/A')} ({info.get('sector', 'N/A')})")
        print()
    
    print("=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_watchlist_symbols.py <watchlist_id>")
        print()
        print("Example: python scripts/validate_watchlist_symbols.py my_combined_list_1")
        sys.exit(1)
    
    watchlist_id = sys.argv[1]
    validate_watchlist(watchlist_id)
