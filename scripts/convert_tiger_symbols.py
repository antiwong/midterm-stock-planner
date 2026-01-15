#!/usr/bin/env python3
"""
Convert Tiger Trading Symbols
==============================
Convert symbols from Tiger Trading format to standard format and validate.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.dashboard.symbol_converter import (
    convert_tiger_to_standard,
    convert_symbols_batch,
    validate_and_convert_tiger_symbols,
    detect_tiger_format
)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/convert_tiger_symbols.py <symbol1> [symbol2] ...")
        print("\nExamples:")
        print("  python scripts/convert_tiger_symbols.py AAPL MSFT")
        print("  python scripts/convert_tiger_symbols.py 0700.HK 0001.HK")
        print("  python scripts/convert_tiger_symbols.py D05.SG BHP.AU")
        print("\nOr provide symbols via stdin (one per line):")
        print("  echo -e 'AAPL\\n0700.HK\\nD05.SG' | python scripts/convert_tiger_symbols.py --stdin")
        return 1
    
    # Check for stdin mode
    if sys.argv[1] == '--stdin':
        symbols = [line.strip() for line in sys.stdin if line.strip()]
    else:
        symbols = sys.argv[1:]
    
    if not symbols:
        print("Error: No symbols provided")
        return 1
    
    print(f"\n{'='*70}")
    print("Tiger Trading Symbol Converter")
    print(f"{'='*70}")
    print(f"Input symbols: {len(symbols)}")
    print(f"Symbols: {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
    print()
    
    # Detect format
    is_tiger_format = detect_tiger_format(symbols)
    print(f"Format detected: {'Tiger Trading' if is_tiger_format else 'Standard'}")
    print()
    
    # Convert symbols
    print("Converting symbols...")
    conversion_result = convert_symbols_batch(symbols)
    
    print(f"\n{'='*70}")
    print("Conversion Results")
    print(f"{'='*70}")
    print(f"✅ Converted: {conversion_result['converted_count']}/{conversion_result['original_count']}")
    
    if conversion_result['errors']:
        print(f"❌ Errors: {len(conversion_result['errors'])}")
        for error in conversion_result['errors']:
            print(f"   {error}")
    
    print()
    print("Conversion Map:")
    for tiger_symbol, standard_symbol in conversion_result['conversion_map'].items():
        exchange = conversion_result['exchange_map'].get(tiger_symbol, 'US')
        print(f"  {tiger_symbol:15} -> {standard_symbol:15} ({exchange})")
    
    # Validate if requested
    if '--validate' in sys.argv:
        print()
        print("Validating converted symbols...")
        validation_result = validate_and_convert_tiger_symbols(symbols, check_existence=True)
        
        print(f"\n{'='*70}")
        print("Validation Results")
        print(f"{'='*70}")
        
        if 'validation' in validation_result:
            valid = validation_result.get('tiger_valid_symbols', [])
            invalid = validation_result.get('tiger_invalid_symbols', [])
            unknown = validation_result.get('tiger_unknown_symbols', [])
            
            print(f"✅ Valid: {len(valid)}")
            print(f"❌ Invalid: {len(invalid)}")
            print(f"⚠️  Unknown: {len(unknown)}")
            
            if valid:
                print(f"\n✅ Valid symbols:")
                for symbol in valid[:20]:
                    print(f"   {symbol}")
                if len(valid) > 20:
                    print(f"   ... and {len(valid) - 20} more")
            
            if invalid:
                print(f"\n❌ Invalid symbols:")
                for symbol in invalid:
                    print(f"   {symbol}")
    
    print()
    print(f"{'='*70}")
    print("✅ Conversion complete!")
    print(f"{'='*70}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
