"""
Fundamentals Status Checker
===========================
Checks which stocks have fundamentals data and provides detailed status reports.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import yaml

from src.data.watchlists import WatchlistManager


class FundamentalsStatusChecker:
    """Check fundamentals data completeness for stocks."""
    
    def __init__(self, fundamentals_path: str = "data/fundamentals.csv"):
        """
        Initialize fundamentals status checker.
        
        Args:
            fundamentals_path: Path to fundamentals CSV file
        """
        self.fundamentals_path = Path(fundamentals_path)
        # Support both naming conventions: 'pe'/'pb' and 'pe_ratio'/'pb_ratio'
        self.required_fields = ['pe', 'pb', 'roe', 'net_margin', 'market_cap']
        self.required_field_aliases = {
            'pe': ['pe_ratio', 'pe'],
            'pb': ['pb_ratio', 'pb'],
            'roe': ['roe', 'return_on_equity'],
            'net_margin': ['net_margin', 'profit_margin'],
            'market_cap': ['market_cap', 'marketCap']
        }
        self.optional_fields = ['debt_to_equity', 'current_ratio', 'dividend_yield', 'eps']
    
    def load_fundamentals(self) -> Optional[pd.DataFrame]:
        """Load fundamentals data from CSV."""
        if not self.fundamentals_path.exists():
            return None
        
        try:
            df = pd.read_csv(self.fundamentals_path)
            if 'ticker' not in df.columns:
                return None
            return df
        except Exception as e:
            print(f"Error loading fundamentals: {e}")
            return None
    
    def check_stock_fundamentals(self, ticker: str, fundamentals_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Check fundamentals status for a single stock.
        
        Args:
            ticker: Stock ticker symbol
            fundamentals_df: Fundamentals DataFrame
            
        Returns:
            Dictionary with status information
        """
        ticker_upper = ticker.upper()
        stock_data = fundamentals_df[fundamentals_df['ticker'].str.upper() == ticker_upper]
        
        if stock_data.empty:
            return {
                'ticker': ticker,
                'has_data': False,
                'completeness': 0.0,
                'missing_fields': self.required_fields + self.optional_fields,
                'has_required': False,
                'status': 'missing'
            }
        
        # Check which fields are present and have valid values
        row = stock_data.iloc[0]
        present_fields = []
        missing_fields = []
        required_present = []
        required_missing = []
        
        for field in self.required_fields:
            # Check for field or its aliases
            field_found = False
            field_value = None
            
            # Try primary field name
            if field in row.index:
                field_value = row[field]
                field_found = True
            else:
                # Try aliases
                aliases = self.required_field_aliases.get(field, [])
                for alias in aliases:
                    if alias in row.index:
                        field_value = row[alias]
                        field_found = True
                        break
            
            if field_found and pd.notna(field_value) and field_value != 0 and field_value != '':
                present_fields.append(field)
                required_present.append(field)
            else:
                missing_fields.append(field)
                required_missing.append(field)
        
        for field in self.optional_fields:
            if field in row.index:
                value = row[field]
                if pd.notna(value) and value != 0 and value != '':
                    present_fields.append(field)
                else:
                    missing_fields.append(field)
            else:
                missing_fields.append(field)
        
        total_fields = len(self.required_fields) + len(self.optional_fields)
        completeness = len(present_fields) / total_fields if total_fields > 0 else 0.0
        has_required = len(required_missing) == 0
        
        status = 'complete' if has_required else 'incomplete' if len(present_fields) > 0 else 'missing'
        
        return {
            'ticker': ticker,
            'has_data': True,
            'completeness': completeness,
            'present_fields': present_fields,
            'missing_fields': missing_fields,
            'required_present': required_present,
            'required_missing': required_missing,
            'has_required': has_required,
            'status': status,
            'last_updated': row.get('date', 'Unknown') if 'date' in row.index else 'Unknown'
        }
    
    def check_watchlist_fundamentals(
        self,
        watchlist_id: Optional[str] = None,
        watchlist_symbols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Check fundamentals status for a watchlist.
        
        Args:
            watchlist_id: Watchlist ID (if None, uses watchlist_symbols)
            watchlist_symbols: List of ticker symbols
            
        Returns:
            Dictionary with comprehensive status report
        """
        # Get symbols
        if watchlist_symbols:
            symbols = watchlist_symbols
        elif watchlist_id:
            # Try custom watchlist first (lazy import to avoid circular dependency)
            try:
                from src.app.dashboard.data import load_custom_watchlist_by_id
                custom_wl = load_custom_watchlist_by_id(watchlist_id)
                if custom_wl:
                    symbols = custom_wl.get('symbols', [])
                else:
                    # Try YAML watchlist
                    manager = WatchlistManager.from_config_dir("config")
                    watchlist = manager.get_watchlist(watchlist_id)
                    symbols = watchlist.symbols if watchlist else []
            except ImportError:
                # Fallback to YAML only
                manager = WatchlistManager.from_config_dir("config")
                watchlist = manager.get_watchlist(watchlist_id)
                symbols = watchlist.symbols if watchlist else []
        else:
            return {
                'error': 'Either watchlist_id or watchlist_symbols must be provided'
            }
        
        if not symbols:
            return {
                'error': 'No symbols found in watchlist'
            }
        
        # Load fundamentals
        fundamentals_df = self.load_fundamentals()
        
        if fundamentals_df is None:
            return {
                'watchlist_id': watchlist_id,
                'total_stocks': len(symbols),
                'fundamentals_file_exists': False,
                'stocks_with_data': 0,
                'stocks_without_data': len(symbols),
                'stocks_missing': symbols,
                'completeness_rate': 0.0,
                'status': 'no_file'
            }
        
        # Check each stock
        stock_statuses = []
        stocks_with_data = []
        stocks_without_data = []
        stocks_complete = []
        stocks_incomplete = []
        stocks_missing = []
        
        for ticker in symbols:
            status = self.check_stock_fundamentals(ticker, fundamentals_df)
            stock_statuses.append(status)
            
            if status['has_data']:
                stocks_with_data.append(ticker)
                if status['has_required']:
                    stocks_complete.append(ticker)
                else:
                    stocks_incomplete.append(ticker)
            else:
                stocks_without_data.append(ticker)
                stocks_missing.append(ticker)
        
        # Calculate statistics
        total_stocks = len(symbols)
        completeness_rate = len(stocks_with_data) / total_stocks if total_stocks > 0 else 0.0
        required_completeness_rate = len(stocks_complete) / total_stocks if total_stocks > 0 else 0.0
        
        # Field-level statistics
        field_stats = {}
        for field in self.required_fields + self.optional_fields:
            present_count = sum(1 for s in stock_statuses if field in s.get('present_fields', []))
            field_stats[field] = {
                'present': present_count,
                'missing': total_stocks - present_count,
                'coverage': present_count / total_stocks if total_stocks > 0 else 0.0
            }
        
        return {
            'watchlist_id': watchlist_id,
            'total_stocks': total_stocks,
            'fundamentals_file_exists': True,
            'stocks_with_data': len(stocks_with_data),
            'stocks_without_data': len(stocks_without_data),
            'stocks_complete': len(stocks_complete),
            'stocks_incomplete': len(stocks_incomplete),
            'stocks_missing': stocks_missing,
            'stocks_with_data_list': stocks_with_data,
            'stocks_complete_list': stocks_complete,
            'stocks_incomplete_list': stocks_incomplete,
            'completeness_rate': completeness_rate,
            'required_completeness_rate': required_completeness_rate,
            'status': 'complete' if required_completeness_rate == 1.0 else 'incomplete' if completeness_rate > 0 else 'missing',
            'field_stats': field_stats,
            'stock_details': stock_statuses
        }
    
    def get_all_watchlists_status(self) -> Dict[str, Any]:
        """Get fundamentals status for all watchlists."""
        # Load all watchlists (lazy import to avoid circular dependency)
        try:
            from src.app.dashboard.data import load_custom_watchlists
            custom_watchlists = load_custom_watchlists()
        except ImportError:
            custom_watchlists = {}
        
        # Also load YAML watchlists
        manager = WatchlistManager.from_config_dir("config")
        
        all_statuses = {}
        
        # Check custom watchlists
        for wl_id, wl_data in custom_watchlists.items():
            symbols = wl_data.get('symbols', [])
            if symbols:
                status = self.check_watchlist_fundamentals(watchlist_id=wl_id, watchlist_symbols=symbols)
                all_statuses[wl_id] = status
        
        # Check YAML watchlists
        for wl_id, watchlist in manager.watchlists.items():
            if wl_id not in all_statuses:  # Don't duplicate
                status = self.check_watchlist_fundamentals(watchlist_id=wl_id, watchlist_symbols=watchlist.symbols)
                all_statuses[wl_id] = status
        
        return all_statuses
