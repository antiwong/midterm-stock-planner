"""
Symbol Converter for Tiger Trading Platform
============================================
Converts symbols between Tiger Trading format and standard US ticker format.
Tiger Trading uses exchange suffixes (e.g., .HK for Hong Kong stocks).
"""

import re
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


# Tiger Trading exchange suffixes and their conversions
TIGER_EXCHANGE_SUFFIXES = {
    '.HK': 'HK',  # Hong Kong
    '.SG': 'SG',  # Singapore
    '.AU': 'AU',  # Australia
    '.SH': 'SH',  # Shanghai (A-shares)
    '.SZ': 'SZ',  # Shenzhen (A-shares)
    '.SS': 'SS',  # Shanghai Stock Exchange
    '.SZSE': 'SZSE',  # Shenzhen Stock Exchange
}

# Reverse mapping for conversion back to Tiger format
EXCHANGE_TO_TIGER_SUFFIX = {v: k for k, v in TIGER_EXCHANGE_SUFFIXES.items()}


def convert_tiger_to_standard(tiger_symbol: str) -> Tuple[str, Optional[str]]:
    """
    Convert Tiger Trading symbol to standard US ticker format.
    
    Tiger Trading format examples:
    - US stocks: AAPL, MSFT (no change)
    - HK stocks: 0700.HK, 0001.HK -> 0700.HK (keep for yfinance)
    - SG stocks: D05.SG -> D05.SI (yfinance uses .SI for Singapore)
    - AU stocks: BHP.AU -> BHP.AX (yfinance uses .AX for Australia)
    
    Args:
        tiger_symbol: Symbol in Tiger Trading format
        
    Returns:
        Tuple of (standard_symbol, exchange_code)
        - standard_symbol: Symbol in format compatible with yfinance
        - exchange_code: Exchange code (HK, SG, AU, etc.) or None for US
    """
    symbol = str(tiger_symbol).strip().upper()
    
    # Check for exchange suffix
    for suffix, exchange in TIGER_EXCHANGE_SUFFIXES.items():
        if symbol.endswith(suffix):
            base_symbol = symbol[:-len(suffix)]
            
            # Convert to yfinance format
            if exchange == 'SG':
                # Singapore: Tiger uses .SG, yfinance uses .SI
                return f"{base_symbol}.SI", exchange
            elif exchange == 'AU':
                # Australia: Tiger uses .AU, yfinance uses .AX
                return f"{base_symbol}.AX", exchange
            elif exchange == 'HK':
                # Hong Kong: Both use .HK
                return symbol, exchange
            elif exchange in ['SH', 'SZ', 'SS', 'SZSE']:
                # Chinese A-shares: Keep as is for now
                return symbol, exchange
            else:
                # Other exchanges: Keep suffix
                return symbol, exchange
    
    # No suffix = US stock
    return symbol, None


def convert_standard_to_tiger(standard_symbol: str, exchange: Optional[str] = None) -> str:
    """
    Convert standard symbol back to Tiger Trading format.
    
    Args:
        standard_symbol: Symbol in standard format (yfinance compatible)
        exchange: Exchange code (HK, SG, AU, etc.) or None for US
        
    Returns:
        Symbol in Tiger Trading format
    """
    symbol = str(standard_symbol).strip().upper()
    
    # If exchange is provided, use it
    if exchange:
        suffix = EXCHANGE_TO_TIGER_SUFFIX.get(exchange)
        if suffix:
            # Remove any existing suffix first
            base = symbol
            for s in TIGER_EXCHANGE_SUFFIXES.keys():
                if base.endswith(s):
                    base = base[:-len(s)]
                    break
            # Also check for yfinance suffixes
            if base.endswith('.SI'):
                base = base[:-3]
            elif base.endswith('.AX'):
                base = base[:-3]
            
            return f"{base}{suffix}"
        return symbol
    
    # Try to detect from symbol
    # Singapore: .SI -> .SG
    if symbol.endswith('.SI'):
        base = symbol[:-3]
        return f"{base}.SG"
    
    # Australia: .AX -> .AU
    if symbol.endswith('.AX'):
        base = symbol[:-3]
        return f"{base}.AU"
    
    # Hong Kong: .HK stays .HK
    if symbol.endswith('.HK'):
        return symbol
    
    # US stock: no change
    return symbol


def normalize_tiger_symbol(symbol: str) -> str:
    """
    Normalize Tiger Trading symbol (clean and standardize format).
    
    Args:
        symbol: Raw symbol from Tiger Trading
        
    Returns:
        Normalized symbol
    """
    # Remove whitespace and convert to uppercase
    normalized = str(symbol).strip().upper()
    
    # Remove common prefixes/suffixes that might be added
    # (e.g., "US:" prefix, trailing spaces)
    normalized = re.sub(r'^US:', '', normalized)
    normalized = re.sub(r'^HK:', '', normalized)
    normalized = re.sub(r'^SG:', '', normalized)
    
    return normalized


def convert_symbols_batch(tiger_symbols: List[str]) -> Dict[str, Any]:
    """
    Convert a batch of Tiger Trading symbols to standard format.
    
    Args:
        tiger_symbols: List of symbols in Tiger Trading format
        
    Returns:
        Dictionary with:
        - converted_symbols: List of converted symbols
        - conversion_map: Dict mapping Tiger symbol -> standard symbol
        - exchange_map: Dict mapping Tiger symbol -> exchange code
        - errors: List of symbols that couldn't be converted
    """
    converted_symbols = []
    conversion_map = {}
    exchange_map = {}
    errors = []
    
    for tiger_symbol in tiger_symbols:
        try:
            normalized = normalize_tiger_symbol(tiger_symbol)
            standard_symbol, exchange = convert_tiger_to_standard(normalized)
            
            converted_symbols.append(standard_symbol)
            conversion_map[tiger_symbol] = standard_symbol
            if exchange:
                exchange_map[tiger_symbol] = exchange
        except Exception as e:
            logger.warning(f"Error converting Tiger symbol {tiger_symbol}: {e}")
            errors.append(tiger_symbol)
    
    return {
        'converted_symbols': converted_symbols,
        'conversion_map': conversion_map,
        'exchange_map': exchange_map,
        'errors': errors,
        'original_count': len(tiger_symbols),
        'converted_count': len(converted_symbols)
    }


def detect_tiger_format(symbols: List[str]) -> bool:
    """
    Detect if symbols are in Tiger Trading format.
    
    Args:
        symbols: List of symbols to check
        
    Returns:
        True if symbols appear to be in Tiger format
    """
    if not symbols:
        return False
    
    # Check if any symbols have Tiger exchange suffixes
    tiger_patterns = list(TIGER_EXCHANGE_SUFFIXES.keys())
    tiger_count = sum(1 for s in symbols if any(s.upper().endswith(suffix) for suffix in tiger_patterns))
    
    # If more than 10% have Tiger suffixes, likely Tiger format
    return (tiger_count / len(symbols)) > 0.1 if symbols else False


def validate_and_convert_tiger_symbols(
    tiger_symbols: List[str],
    check_existence: bool = True
) -> Dict[str, Any]:
    """
    Validate and convert Tiger Trading symbols to standard format.
    
    This function:
    1. Normalizes Tiger symbols
    2. Converts to standard format (yfinance compatible)
    3. Optionally validates existence via yfinance
    
    Args:
        tiger_symbols: List of symbols in Tiger Trading format
        check_existence: Whether to validate symbols exist (default: True)
        
    Returns:
        Dictionary with validation and conversion results
    """
    from .symbol_validator import validate_symbols_batch
    
    # Step 1: Normalize and convert
    conversion_result = convert_symbols_batch(tiger_symbols)
    converted_symbols = conversion_result['converted_symbols']
    
    result = {
        'tiger_symbols': tiger_symbols,
        'converted_symbols': converted_symbols,
        'conversion_map': conversion_result['conversion_map'],
        'exchange_map': conversion_result['exchange_map'],
        'conversion_errors': conversion_result['errors'],
    }
    
    # Step 2: Validate existence if requested
    if check_existence and converted_symbols:
        try:
            validation_result = validate_symbols_batch(converted_symbols)
            
            # Map validated symbols back to Tiger format
            tiger_valid = []
            tiger_invalid = []
            tiger_unknown = []
            
            for tiger_symbol, standard_symbol in conversion_result['conversion_map'].items():
                if standard_symbol in validation_result['valid_symbols']:
                    tiger_valid.append(tiger_symbol)
                elif standard_symbol in validation_result['invalid_symbols']:
                    tiger_invalid.append(tiger_symbol)
                else:
                    tiger_unknown.append(tiger_symbol)
            
            result['validation'] = validation_result
            result['tiger_valid_symbols'] = tiger_valid
            result['tiger_invalid_symbols'] = tiger_invalid
            result['tiger_unknown_symbols'] = tiger_unknown
            result['valid_standard_symbols'] = validation_result['valid_symbols']
            
        except Exception as e:
            logger.warning(f"Symbol validation failed: {e}")
            result['validation_error'] = str(e)
    
    return result
