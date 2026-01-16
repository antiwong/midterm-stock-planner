#!/usr/bin/env python3
"""
Check Failed Symbols
====================
Check why symbols failed to download and suggest fixes.
"""

import sys
from pathlib import Path
import yfinance as yf
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_symbol(ticker: str) -> dict:
    """Check a single symbol and suggest alternatives."""
    result = {
        'original': ticker,
        'status': 'unknown',
        'suggestion': None,
        'error': None,
        'alternatives': []
    }
    
    # Try original symbol
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if info and len(info) > 1:
            # Check if it has historical data
            hist = stock.history(period="1mo")
            if not hist.empty:
                result['status'] = 'valid'
                result['suggestion'] = 'Symbol is valid - may have been a temporary download issue'
            else:
                result['status'] = 'no_data'
                result['error'] = 'Symbol exists but has no historical data'
        else:
            result['status'] = 'invalid'
            result['error'] = 'Symbol does not exist'
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    # Try alternative formats
    alternatives = []
    
    # BRK.B -> BRK-B
    if '.' in ticker:
        alt = ticker.replace('.', '-')
        alternatives.append(alt)
        try:
            stock = yf.Ticker(alt)
            info = stock.info
            if info and len(info) > 1:
                hist = stock.history(period="1mo")
                if not hist.empty:
                    result['alternatives'].append({
                        'symbol': alt,
                        'valid': True,
                        'name': info.get('longName') or info.get('shortName', 'N/A')
                    })
        except:
            pass
    
    # Try uppercase
    if ticker != ticker.upper():
        alt = ticker.upper()
        alternatives.append(alt)
        try:
            stock = yf.Ticker(alt)
            info = stock.info
            if info and len(info) > 1:
                hist = stock.history(period="1mo")
                if not hist.empty:
                    result['alternatives'].append({
                        'symbol': alt,
                        'valid': True,
                        'name': info.get('longName') or info.get('shortName', 'N/A')
                    })
        except:
            pass
    
    # Generate suggestion
    if result['alternatives']:
        result['suggestion'] = f"Use: {result['alternatives'][0]['symbol']}"
    elif result['status'] in ['invalid', 'error', 'no_data']:
        result['suggestion'] = 'Remove from watchlist - symbol is invalid or delisted'
    
    return result


def main():
    """Check failed symbols."""
    failed_symbols = ['ANSS', 'ATVI', 'BRK.B', 'DM', 'MAG', 'PXD', 'SAND', 'SPLK', 'SQ', 'WBA']
    
    print("=" * 70)
    print("CHECKING FAILED SYMBOLS")
    print("=" * 70)
    print()
    
    results = []
    for symbol in failed_symbols:
        print(f"Checking {symbol}...", end=" ", flush=True)
        result = check_symbol(symbol)
        results.append(result)
        
        if result['status'] == 'valid':
            print("✅ Valid (may have been temporary issue)")
        elif result['alternatives']:
            print(f"⚠️  Invalid, but alternative found: {result['alternatives'][0]['symbol']}")
        else:
            print(f"❌ Invalid: {result['error']}")
    
    print()
    print("=" * 70)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 70)
    print()
    
    # Symbols with alternatives
    with_alternatives = [r for r in results if r['alternatives']]
    if with_alternatives:
        print("📝 Symbols with alternative formats:")
        for r in with_alternatives:
            alt = r['alternatives'][0]
            print(f"   {r['original']:10s} → {alt['symbol']:10s} ({alt['name']})")
        print()
    
    # Invalid symbols to remove
    invalid = [r for r in results if not r['alternatives'] and r['status'] != 'valid']
    if invalid:
        print("🗑️  Symbols to remove (invalid/delisted):")
        for r in invalid:
            print(f"   {r['original']:10s} - {r['error']}")
        print()
    
    # Valid symbols (temporary issues)
    valid = [r for r in results if r['status'] == 'valid']
    if valid:
        print("✅ Symbols that are valid (may have been temporary download issue):")
        for r in valid:
            print(f"   {r['original']}")
        print()
    
    # Generate fix script
    print("=" * 70)
    print("AUTO-FIX RECOMMENDATIONS")
    print("=" * 70)
    print()
    
    if with_alternatives:
        print("# Replace symbols with correct format:")
        for r in with_alternatives:
            alt = r['alternatives'][0]
            print(f"# {r['original']} → {alt['symbol']}")
        print()
    
    if invalid:
        print("# Remove these invalid symbols:")
        for r in invalid:
            print(f"# {r['original']} - {r['error']}")
        print()


if __name__ == '__main__':
    main()
