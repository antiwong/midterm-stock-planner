"""
Watchlist management for Mid-term Stock Planner.

Provides utilities to load, filter, and manage stock watchlists.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


def _load_custom_watchlists_from_db() -> Dict[str, dict]:
    """Load custom watchlists from the database.
    
    Returns:
        Dictionary of watchlist_id -> watchlist data
    """
    try:
        from src.analytics.models import CustomWatchlist, get_db
        db = get_db("data/analysis.db")
        session = db.get_session()
        try:
            watchlists = session.query(CustomWatchlist).all()
            return {wl.watchlist_id: wl.to_dict() for wl in watchlists}
        finally:
            session.close()
    except Exception as e:
        logger.debug(f"Could not load custom watchlists from database: {e}")
        return {}


@dataclass
class Watchlist:
    """A named collection of stock symbols."""
    name: str
    description: str
    symbols: List[str]
    category: str = "custom"
    
    def __len__(self) -> int:
        return len(self.symbols)
    
    def __iter__(self):
        return iter(self.symbols)
    
    def __contains__(self, ticker: str) -> bool:
        return ticker.upper() in [s.upper() for s in self.symbols]


@dataclass
class WatchlistManager:
    """Manages multiple watchlists and provides utilities for stock selection."""
    
    watchlists: Dict[str, Watchlist] = field(default_factory=dict)
    default_watchlist: str = "tech_giants"
    
    @classmethod
    def from_yaml(cls, path: str | Path) -> "WatchlistManager":
        """Load watchlists from a YAML file."""
        path = Path(path)
        if not path.exists():
            logger.warning(f"Watchlist file not found: {path}")
            return cls()
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        watchlists = {}
        for key, wl_data in data.get('watchlists', {}).items():
            # Ensure all symbols are strings (YAML might parse ON as True, etc.)
            raw_symbols = wl_data.get('symbols', []) or []
            symbols = [str(s).upper() for s in raw_symbols if s is not None]
            
            watchlists[key] = Watchlist(
                name=wl_data.get('name', key),
                description=wl_data.get('description', ''),
                symbols=symbols,
                category=wl_data.get('category', 'custom'),
            )
        
        return cls(
            watchlists=watchlists,
            default_watchlist=data.get('default_watchlist', 'tech_giants'),
        )
    
    @classmethod
    def from_config_dir(cls, config_dir: str | Path = "config", include_custom: bool = True) -> "WatchlistManager":
        """Load watchlists from the default config directory and optionally from database.
        
        Args:
            config_dir: Path to config directory
            include_custom: Whether to also load custom watchlists from database
        """
        config_dir = Path(config_dir)
        watchlist_path = config_dir / "watchlists.yaml"
        manager = cls.from_yaml(watchlist_path)
        
        # Also load custom watchlists from database
        if include_custom:
            custom_watchlists = _load_custom_watchlists_from_db()
            for wl_id, wl_data in custom_watchlists.items():
                manager.watchlists[wl_id] = Watchlist(
                    name=wl_data.get('name', wl_id),
                    description=wl_data.get('description', ''),
                    symbols=wl_data.get('symbols', []),
                    category=wl_data.get('category', 'custom'),
                )
        
        return manager
    
    def get_watchlist(self, name: str) -> Optional[Watchlist]:
        """Get a specific watchlist by name."""
        return self.watchlists.get(name)
    
    def get_symbols(self, name: str) -> List[str]:
        """Get symbols from a specific watchlist."""
        wl = self.get_watchlist(name)
        return wl.symbols if wl else []
    
    def get_default_symbols(self) -> List[str]:
        """Get symbols from the default watchlist."""
        return self.get_symbols(self.default_watchlist)
    
    def get_all_symbols(self) -> List[str]:
        """Get all unique symbols across all watchlists."""
        all_symbols: Set[str] = set()
        for wl in self.watchlists.values():
            # Ensure all symbols are strings (YAML might parse some as bool/int)
            all_symbols.update(str(s).upper() for s in wl.symbols if s)
        return sorted(all_symbols)
    
    def get_symbols_by_category(self, category: str) -> List[str]:
        """Get all unique symbols from watchlists in a specific category."""
        symbols: Set[str] = set()
        for wl in self.watchlists.values():
            if wl.category == category:
                symbols.update(wl.symbols)
        return sorted(symbols)
    
    def list_watchlists(self) -> List[Dict[str, str]]:
        """List all available watchlists with metadata."""
        return [
            {
                "key": key,
                "name": wl.name,
                "description": wl.description,
                "category": wl.category,
                "count": len(wl.symbols),
            }
            for key, wl in self.watchlists.items()
        ]
    
    def list_categories(self) -> List[str]:
        """List all unique categories."""
        return sorted(set(wl.category for wl in self.watchlists.values()))
    
    def find_ticker(self, ticker: str) -> List[str]:
        """Find which watchlists contain a specific ticker."""
        ticker = ticker.upper()
        return [
            key for key, wl in self.watchlists.items()
            if ticker in wl
        ]
    
    def combine_watchlists(self, names: List[str]) -> List[str]:
        """Combine multiple watchlists into a single list of unique symbols."""
        symbols: Set[str] = set()
        for name in names:
            wl = self.get_watchlist(name)
            if wl:
                symbols.update(wl.symbols)
            else:
                logger.warning(f"Watchlist not found: {name}")
        return sorted(symbols)


def load_universe(path: str | Path = "data/universe.txt") -> List[str]:
    """
    Load stock universe from a text file.
    
    Args:
        path: Path to universe file (one ticker per line, # for comments)
        
    Returns:
        List of ticker symbols
    """
    path = Path(path)
    if not path.exists():
        logger.warning(f"Universe file not found: {path}")
        return []
    
    symbols = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Handle inline comments
            ticker = line.split('#')[0].strip()
            if ticker:
                symbols.append(ticker.upper())
    
    return symbols


def save_universe(symbols: List[str], path: str | Path = "data/universe.txt") -> None:
    """
    Save stock universe to a text file.
    
    Args:
        symbols: List of ticker symbols
        path: Path to output file
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w') as f:
        f.write("# Stock Universe\n")
        f.write(f"# Generated by Mid-term Stock Planner\n")
        f.write(f"# Total tickers: {len(symbols)}\n\n")
        for symbol in sorted(set(symbols)):
            f.write(f"{symbol}\n")
    
    logger.info(f"Saved {len(symbols)} symbols to {path}")


# Convenience function for quick access
def get_watchlist_symbols(
    watchlist_name: Optional[str] = None,
    config_dir: str = "config",
) -> List[str]:
    """
    Get symbols from a watchlist or the default watchlist.
    
    Args:
        watchlist_name: Name of watchlist (None for default)
        config_dir: Path to config directory
        
    Returns:
        List of ticker symbols
    """
    manager = WatchlistManager.from_config_dir(config_dir)
    
    if watchlist_name:
        return manager.get_symbols(watchlist_name)
    return manager.get_default_symbols()


if __name__ == "__main__":
    # Demo usage
    manager = WatchlistManager.from_config_dir()
    
    print("=" * 60)
    print("WATCHLIST MANAGER")
    print("=" * 60)
    
    print("\nAvailable watchlists:")
    for wl in manager.list_watchlists():
        print(f"  - {wl['key']:20s} ({wl['count']:3d} symbols) - {wl['name']}")
    
    print(f"\nCategories: {manager.list_categories()}")
    print(f"\nTotal unique symbols: {len(manager.get_all_symbols())}")
    
    print("\n--- Tech Giants ---")
    for symbol in manager.get_symbols("tech_giants"):
        print(f"  {symbol}")
    
    print("\n--- Find NVDA ---")
    print(f"  NVDA is in: {manager.find_ticker('NVDA')}")
