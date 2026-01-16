#!/usr/bin/env python3
"""
Fix Watchlist Symbols
=====================
Replace invalid symbols with correct formats and remove truly invalid ones.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.watchlists import WatchlistManager

# Symbol replacements
REPLACEMENTS = {'BRK.B': 'BRK-B'}

# Symbols to remove
REMOVALS = ['ANSS', 'WBA', 'MAG', 'SPLK', 'ATVI', 'K', 'PXD', 'SQ', 'SAND']

def fix_watchlist(watchlist_id: str):
    """Fix symbols in a watchlist."""
    config_dir = project_root / "config"
    manager = WatchlistManager.from_config_dir(str(config_dir))
    
    # Also load from database
    from src.app.dashboard.data import load_custom_watchlist_by_id
    
    # Try custom watchlist first
    try:
        custom_wl = load_custom_watchlist_by_id(watchlist_id)
        if custom_wl:
            symbols = custom_wl.get('symbols', [])
            print(f"Found custom watchlist: {watchlist_id}")
            print(f"Original symbols: {len(symbols)}")
            
            # Apply fixes
            fixed_symbols = []
            removed_count = 0
            replaced_count = 0
            
            for symbol in symbols:
                if symbol in REMOVALS:
                    removed_count += 1
                    print(f"   Removing: {symbol}")
                    continue
                elif symbol in REPLACEMENTS:
                    new_symbol = REPLACEMENTS[symbol]
                    fixed_symbols.append(new_symbol)
                    replaced_count += 1
                    print(f"   Replacing: {symbol} -> {new_symbol}")
                else:
                    fixed_symbols.append(symbol)
            
            print()
            print(f"Summary:")
            print(f"   Removed: {removed_count}")
            print(f"   Replaced: {replaced_count}")
            print(f"   Final count: {len(fixed_symbols)}")
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
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/fix_watchlist_symbols.py <watchlist_id>")
        sys.exit(1)
    
    watchlist_id = sys.argv[1]
    fix_watchlist(watchlist_id)
