"""
Symbol Validator
================
Validates that stock symbols exist by checking with yfinance.
"""

import yfinance as yf
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging

logger = logging.getLogger(__name__)


def validate_symbol_exists(symbol: str, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Validate that a symbol exists by attempting to fetch its info.
    
    Args:
        symbol: Ticker symbol to validate
        timeout: Timeout in seconds
        
    Returns:
        Dictionary with:
        - exists: bool
        - symbol: str (normalized)
        - error: Optional[str]
        - info: Optional[dict] (if exists)
    """
    symbol = symbol.strip().upper()
    
    try:
        ticker = yf.Ticker(symbol)
        # Try to get info - this will fail quickly if symbol doesn't exist
        info = ticker.info
        
        # Check if we got valid info (not empty dict)
        if info and isinstance(info, dict) and len(info) > 0:
            # Check for common error indicators
            if 'error' in info or 'message' in info:
                return {
                    'exists': False,
                    'symbol': symbol,
                    'error': info.get('message', 'Symbol not found'),
                    'info': None
                }
            
            # Check if symbol is valid (has basic fields)
            if 'symbol' in info or 'longName' in info or 'shortName' in info:
                return {
                    'exists': True,
                    'symbol': symbol,
                    'error': None,
                    'info': {
                        'name': info.get('longName') or info.get('shortName') or symbol,
                        'exchange': info.get('exchange', 'N/A'),
                        'sector': info.get('sector', 'N/A'),
                        'industry': info.get('industry', 'N/A'),
                    }
                }
        
        # If we get here, symbol might not exist
        return {
            'exists': False,
            'symbol': symbol,
            'error': 'No data available',
            'info': None
        }
        
    except Exception as e:
        # Symbol likely doesn't exist or network error
        error_msg = str(e)
        if 'No data found' in error_msg or 'symbol may be delisted' in error_msg.lower():
            return {
                'exists': False,
                'symbol': symbol,
                'error': 'Symbol not found',
                'info': None
            }
        else:
            # Network or other error - treat as unknown
            logger.warning(f"Error validating {symbol}: {e}")
            return {
                'exists': None,  # Unknown
                'symbol': symbol,
                'error': f'Validation error: {error_msg}',
                'info': None
            }


def validate_symbols_batch(
    symbols: List[str],
    max_workers: int = 10,
    delay_between_batches: float = 0.1
) -> Dict[str, Any]:
    """
    Validate multiple symbols in parallel.
    
    Args:
        symbols: List of symbols to validate
        max_workers: Number of parallel workers
        delay_between_batches: Delay between batches to avoid rate limiting
        
    Returns:
        Dictionary with:
        - valid_symbols: List of valid symbols
        - invalid_symbols: List of invalid symbols
        - unknown_symbols: List of symbols that couldn't be validated
        - validation_details: Dict mapping symbol -> validation result
        - summary: Summary statistics
    """
    if not symbols:
        return {
            'valid_symbols': [],
            'invalid_symbols': [],
            'unknown_symbols': [],
            'validation_details': {},
            'summary': {
                'total': 0,
                'valid': 0,
                'invalid': 0,
                'unknown': 0
            }
        }
    
    # Remove duplicates and normalize
    unique_symbols = list(dict.fromkeys([s.strip().upper() for s in symbols if s.strip()]))
    
    validation_details = {}
    valid_symbols = []
    invalid_symbols = []
    unknown_symbols = []
    
    # Validate in batches to avoid rate limiting
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_symbol = {
            executor.submit(validate_symbol_exists, symbol): symbol
            for symbol in unique_symbols
        }
        
        # Process results as they complete
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                result = future.result()
                validation_details[symbol] = result
                
                if result['exists'] is True:
                    valid_symbols.append(symbol)
                elif result['exists'] is False:
                    invalid_symbols.append(symbol)
                else:
                    unknown_symbols.append(symbol)
                
                # Small delay to avoid rate limiting
                time.sleep(delay_between_batches)
                
            except Exception as e:
                logger.error(f"Error validating {symbol}: {e}")
                validation_details[symbol] = {
                    'exists': None,
                    'symbol': symbol,
                    'error': str(e),
                    'info': None
                }
                unknown_symbols.append(symbol)
    
    return {
        'valid_symbols': sorted(valid_symbols),
        'invalid_symbols': sorted(invalid_symbols),
        'unknown_symbols': sorted(unknown_symbols),
        'validation_details': validation_details,
        'summary': {
            'total': len(unique_symbols),
            'valid': len(valid_symbols),
            'invalid': len(invalid_symbols),
            'unknown': len(unknown_symbols),
            'valid_pct': (len(valid_symbols) / len(unique_symbols) * 100) if unique_symbols else 0
        }
    }


def validate_watchlist_symbols_enhanced(symbols: List[str]) -> Dict[str, Any]:
    """
    Enhanced validation that checks if symbols actually exist.
    
    This is a more thorough validation that:
    1. Cleans and deduplicates symbols
    2. Validates format
    3. Checks if symbols exist via yfinance
    
    Args:
        symbols: List of ticker symbols
        
    Returns:
        Dictionary with validation results
    """
    from .data import validate_watchlist_symbols
    
    # First do basic validation (format, duplicates)
    basic_validation = validate_watchlist_symbols(symbols)
    
    # Then check if symbols exist
    valid_symbols = basic_validation['valid_symbols']
    
    if not valid_symbols:
        return {
            **basic_validation,
            'existence_check': {
                'valid_symbols': [],
                'invalid_symbols': [],
                'unknown_symbols': [],
                'validation_details': {},
                'summary': {'total': 0, 'valid': 0, 'invalid': 0, 'unknown': 0}
            }
        }
    
    # Check existence
    existence_check = validate_symbols_batch(valid_symbols)
    
    # Combine results
    return {
        **basic_validation,
        'existence_check': existence_check,
        'final_valid_symbols': existence_check['valid_symbols'],
        'final_invalid_symbols': basic_validation['invalid'] + existence_check['invalid_symbols'],
        'warnings': basic_validation['warnings'] + [
            f"{len(existence_check['invalid_symbols'])} symbols do not exist",
            f"{len(existence_check['unknown_symbols'])} symbols could not be validated"
        ] if (existence_check['invalid_symbols'] or existence_check['unknown_symbols']) else basic_validation['warnings']
    }
