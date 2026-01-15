#!/usr/bin/env python3
"""
Validate Watchlist Symbols
===========================
Check if symbols in a watchlist actually exist.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.dashboard.data import load_custom_watchlist_by_id, load_watchlists
from src.app.dashboard.symbol_validator import validate_symbols_batch


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_watchlist.py <watchlist_id>")
        print("\nExample:")
        print("  python scripts/validate_watchlist.py jan_26")
        print("  python scripts/validate_watchlist.py tech_giants")
        return 1
    
    watchlist_id = sys.argv[1]
    
    # Try custom watchlist first
    watchlist = load_custom_watchlist_by_id(watchlist_id)
    
    if not watchlist:
        # Try standard watchlist
        watchlists = load_watchlists()
        watchlist = watchlists.get(watchlist_id)
        if watchlist:
            symbols = watchlist.get('symbols', [])
        else:
            print(f"Error: Watchlist '{watchlist_id}' not found")
            return 1
    else:
        symbols = watchlist.get('symbols', [])
    
    print(f"\n{'='*60}")
    print(f"Validating Watchlist: {watchlist.get('name', watchlist_id)}")
    print(f"{'='*60}")
    print(f"Watchlist ID: {watchlist_id}")
    print(f"Total symbols: {len(symbols)}")
    print(f"\nSymbols: {', '.join(symbols[:20])}{'...' if len(symbols) > 20 else ''}")
    print()
    
    # Validate symbols
    print("Validating symbols...")
    result = validate_symbols_batch(symbols)
    
    print(f"\n{'='*60}")
    print("Validation Results")
    print(f"{'='*60}")
    print(f"✅ Valid symbols: {len(result['valid_symbols'])}")
    print(f"❌ Invalid symbols: {len(result['invalid_symbols'])}")
    print(f"⚠️  Unknown (validation error): {len(result['unknown_symbols'])}")
    print()
    
    if result['valid_symbols']:
        print(f"✅ Valid symbols ({len(result['valid_symbols'])}):")
        for symbol in result['valid_symbols'][:20]:
            info = result['validation_details'][symbol].get('info', {})
            name = info.get('name', symbol) if info else symbol
            print(f"   {symbol:8} - {name}")
        if len(result['valid_symbols']) > 20:
            print(f"   ... and {len(result['valid_symbols']) - 20} more")
        print()
    
    if result['invalid_symbols']:
        print(f"❌ Invalid symbols ({len(result['invalid_symbols'])}):")
        for symbol in result['invalid_symbols']:
            error = result['validation_details'][symbol].get('error', 'Unknown error')
            print(f"   {symbol:8} - {error}")
        print()
    
    if result['unknown_symbols']:
        print(f"⚠️  Unknown symbols ({len(result['unknown_symbols'])}):")
        for symbol in result['unknown_symbols']:
            error = result['validation_details'][symbol].get('error', 'Unknown error')
            print(f"   {symbol:8} - {error}")
        print()
    
    # Summary
    print(f"{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"Total: {result['summary']['total']}")
    print(f"Valid: {result['summary']['valid']} ({result['summary']['valid_pct']:.1f}%)")
    print(f"Invalid: {result['summary']['invalid']}")
    print(f"Unknown: {result['summary']['unknown']}")
    print()
    
    if result['invalid_symbols']:
        print("⚠️  WARNING: Some symbols do not exist and should be removed!")
        return 1
    elif result['unknown_symbols']:
        print("⚠️  WARNING: Some symbols could not be validated (network error?)")
        return 1
    else:
        print("✅ All symbols are valid!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
