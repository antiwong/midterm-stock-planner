#!/usr/bin/env python3
"""
Check Symbol Alternative Formats
==================================
Check if invalid symbols exist in alternative formats (e.g., BRK.B -> BRK-B).
"""

import sys
from pathlib import Path
import yfinance as yf

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_alternative_formats(ticker: str) -> dict:
    """Check if a ticker exists in alternative formats.
    
    Args:
        ticker: Original ticker symbol
    
    Returns:
        Dictionary with validation results for all formats
    """
    # Generate alternative formats
    alternatives = [ticker]
    
    # Common format variations
    if '.' in ticker:
        # BRK.B -> BRK-B
        alternatives.append(ticker.replace('.', '-'))
        # BRK.B -> BRKB
        alternatives.append(ticker.replace('.', ''))
    
    if '-' in ticker:
        # BRK-B -> BRK.B
        alternatives.append(ticker.replace('-', '.'))
        # BRK-B -> BRKB
        alternatives.append(ticker.replace('-', ''))
    
    # Try uppercase/lowercase
    alternatives.append(ticker.upper())
    alternatives.append(ticker.lower())
    
    # Remove duplicates while preserving order
    seen = set()
    unique_alternatives = []
    for alt in alternatives:
        if alt not in seen:
            seen.add(alt)
            unique_alternatives.append(alt)
    
    results = {}
    
    for alt in unique_alternatives:
        result = {
            'ticker': alt,
            'valid': False,
            'exists': False,
            'has_data': False,
            'error': None,
            'info': {}
        }
        
        try:
            stock = yf.Ticker(alt)
            info = stock.info
            
            if info and len(info) > 1:
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
                except Exception as e:
                    result['error'] = f"No history: {str(e)}"
            else:
                result['error'] = "No info returned"
                
        except Exception as e:
            result['error'] = str(e)
        
        results[alt] = result
    
    return results


def main():
    """Check alternative formats for problematic symbols."""
    # Invalid symbols
    invalid_symbols = ['ANSS', 'WBA', 'MAG']
    
    # Symbols with no data
    no_data_symbols = ['SPLK', 'ATVI', 'K', 'PXD', 'BRK.B', 'SQ', 'SAND']
    
    print("=" * 70)
    print("CHECKING ALTERNATIVE FORMATS FOR PROBLEMATIC SYMBOLS")
    print("=" * 70)
    print()
    
    all_results = {}
    
    # Check invalid symbols
    print("🔍 Checking INVALID symbols:")
    print()
    for symbol in invalid_symbols:
        print(f"   {symbol}:")
        results = check_alternative_formats(symbol)
        all_results[symbol] = results
        
        valid_found = False
        for alt, result in results.items():
            if result['valid'] and result['has_data']:
                print(f"      ✅ {alt}: {result['info'].get('name', 'N/A')} ({result['info'].get('sector', 'N/A')})")
                valid_found = True
            elif result['exists']:
                print(f"      ⚠️  {alt}: Exists but {result.get('error', 'no data')}")
            else:
                if alt != symbol:  # Don't show original if it's the same
                    print(f"      ❌ {alt}: {result.get('error', 'Invalid')}")
        
        if not valid_found:
            print(f"      ❌ No valid alternative found")
        print()
    
    # Check symbols with no data
    print("🔍 Checking symbols with NO DATA:")
    print()
    for symbol in no_data_symbols:
        print(f"   {symbol}:")
        results = check_alternative_formats(symbol)
        all_results[symbol] = results
        
        valid_found = False
        for alt, result in results.items():
            if result['valid'] and result['has_data']:
                print(f"      ✅ {alt}: {result['info'].get('name', 'N/A')} ({result['info'].get('sector', 'N/A')})")
                valid_found = True
            elif result['exists']:
                print(f"      ⚠️  {alt}: Exists but {result.get('error', 'no data')}")
            else:
                if alt != symbol:
                    print(f"      ❌ {alt}: {result.get('error', 'Invalid')}")
        
        if not valid_found:
            print(f"      ⚠️  No alternative with data found")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 70)
    print()
    
    fixes = {}
    removals = []
    
    for symbol, results in all_results.items():
        # Find best alternative
        best_alt = None
        best_result = None
        
        for alt, result in results.items():
            if result['valid'] and result['has_data']:
                if best_result is None or (best_result and not best_result['has_data']):
                    best_alt = alt
                    best_result = result
        
        if best_alt and best_alt != symbol:
            fixes[symbol] = best_alt
            print(f"✅ {symbol} -> {best_alt} ({best_result['info'].get('name', 'N/A')})")
        elif best_result and best_result['exists']:
            print(f"⚠️  {symbol}: Exists but no data - may need manual check")
        else:
            removals.append(symbol)
            print(f"❌ {symbol}: Should be removed (no valid format found)")
    
    print()
    print("=" * 70)
    print("FIXES TO APPLY")
    print("=" * 70)
    print()
    
    if fixes:
        print("Symbols to replace:")
        for old, new in fixes.items():
            print(f"   {old} -> {new}")
        print()
    
    if removals:
        print("Symbols to remove:")
        for symbol in removals:
            print(f"   {symbol}")
        print()
    
    # Generate fix script
    if fixes or removals:
        print("=" * 70)
        print("GENERATING FIX SCRIPT")
        print("=" * 70)
        print()
        
        script_content = f"""#!/usr/bin/env python3
\"\"\"
Fix Watchlist Symbols
=====================
Replace invalid symbols with correct formats and remove truly invalid ones.
\"\"\"

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.watchlists import WatchlistManager

# Symbol replacements
REPLACEMENTS = {fixes}

# Symbols to remove
REMOVALS = {removals}

def fix_watchlist(watchlist_id: str):
    \"\"\"Fix symbols in a watchlist.\"\"\"
    config_dir = project_root / "config"
    manager = WatchlistManager.from_config_dir(str(config_dir))
    
    # Also load from database
    from src.app.dashboard.data import load_custom_watchlist_by_id
    
    # Try custom watchlist first
    try:
        custom_wl = load_custom_watchlist_by_id(watchlist_id)
        if custom_wl:
            symbols = custom_wl.get('symbols', [])
            print(f"Found custom watchlist: {{watchlist_id}}")
            print(f"Original symbols: {{len(symbols)}}")
            
            # Apply fixes
            fixed_symbols = []
            removed_count = 0
            replaced_count = 0
            
            for symbol in symbols:
                if symbol in REMOVALS:
                    removed_count += 1
                    print(f"   Removing: {{symbol}}")
                    continue
                elif symbol in REPLACEMENTS:
                    new_symbol = REPLACEMENTS[symbol]
                    fixed_symbols.append(new_symbol)
                    replaced_count += 1
                    print(f"   Replacing: {{symbol}} -> {{new_symbol}}")
                else:
                    fixed_symbols.append(symbol)
            
            print()
            print(f"Summary:")
            print(f"   Removed: {{removed_count}}")
            print(f"   Replaced: {{replaced_count}}")
            print(f"   Final count: {{len(fixed_symbols)}}")
            print()
            
            # Update in database
            from src.analytics.models import get_db, CustomWatchlist
            db = get_db()
            session = db.get_session()
            try:
                watchlist = session.query(CustomWatchlist).filter_by(watchlist_id=watchlist_id).first()
                if watchlist:
                    import json
                    watchlist.symbols_json = json.dumps(fixed_symbols)
                    session.commit()
                    print(f"✅ Updated watchlist in database")
                else:
                    print(f"⚠️  Watchlist not found in database")
            finally:
                session.close()
            
            return fixed_symbols
    
    except Exception as e:
        print(f"Error: {{e}}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/fix_watchlist_symbols.py <watchlist_id>")
        sys.exit(1)
    
    watchlist_id = sys.argv[1]
    fix_watchlist(watchlist_id)
"""
        
        fix_script_path = project_root / "scripts" / "fix_watchlist_symbols.py"
        with open(fix_script_path, 'w') as f:
            f.write(script_content)
        
        print(f"✅ Fix script created: {fix_script_path}")
        print()
        print("To apply fixes, run:")
        print(f"   python scripts/fix_watchlist_symbols.py my_combined_list_1")


if __name__ == "__main__":
    main()
