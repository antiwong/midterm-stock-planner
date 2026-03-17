# Watchlist Symbol Validation Guide

> [← Back to Documentation Index](README.md)

This guide explains how to validate symbols in your watchlists to ensure they exist and are correct.

## Overview

The system provides multiple ways to validate watchlist symbols:
1. **Command-line script** (recommended for batch validation)
2. **GUI Watchlist Manager** (built-in validation when creating/editing)
3. **Python functions** (for programmatic validation)

## Method 1: Command-Line Script

### Usage

```bash
python scripts/validate_watchlist.py <watchlist_id>
```

### Examples

```bash
# Validate a custom watchlist
python scripts/validate_watchlist.py jan_26

# Validate a standard watchlist
python scripts/validate_watchlist.py tech_giants
python scripts/validate_watchlist.py nasdaq_100
```

### Output

The script will show:
- ✅ **Valid symbols**: Symbols that exist with company names
- ❌ **Invalid symbols**: Symbols that don't exist (should be removed)
- ⚠️ **Unknown symbols**: Symbols that couldn't be validated (network errors)
- **Summary**: Total count and percentages

### Example Output

```
============================================================
Validating Watchlist: January 26 Watchlist
============================================================
Watchlist ID: jan_26
Total symbols: 25

Symbols: AAPL, MSFT, GOOGL, AMZN, NVDA, ...

Validating symbols...

============================================================
Validation Results
============================================================
✅ Valid symbols: 23
❌ Invalid symbols: 2
⚠️  Unknown (validation error): 0

✅ Valid symbols (23):
   AAPL     - Apple Inc
   MSFT     - Microsoft Corporation
   GOOGL    - Alphabet Inc
   ...

❌ Invalid symbols (2):
   INVALID  - Symbol not found
   BADSYM   - Symbol not found

============================================================
Summary
============================================================
Total: 25
Valid: 23 (92.0%)
Invalid: 2
Unknown: 0

⚠️  WARNING: Some symbols do not exist and should be removed!
```

## Method 2: GUI Watchlist Manager

### Steps

1. Open the dashboard: `streamlit run run_dashboard.py`
2. Navigate to **"📋 Watchlist Manager"** in the sidebar
3. When creating or editing a watchlist:
   - Enter symbols manually or upload a file
   - The system automatically validates symbols as you type
   - Invalid symbols are highlighted and removed
   - You'll see:
     - ✅ Valid symbols count
     - ⚠️ Invalid format symbols
     - ❌ Non-existent symbols
     - ℹ️ Unknown symbols (validation errors)

### Features

- **Real-time validation**: Symbols are checked as you enter them
- **Automatic cleanup**: Invalid symbols are automatically removed
- **Visual feedback**: Color-coded warnings and errors
- **Symbol grid**: See all valid symbols in a grid view

## Method 3: Python Functions

### Using `validate_watchlist_symbols()`

```python
from src.app.dashboard.data import validate_watchlist_symbols

# Validate symbols with existence check
symbols = ['AAPL', 'MSFT', 'INVALID', 'GOOGL']
result = validate_watchlist_symbols(symbols, check_existence=True)

print(f"Valid symbols: {result['valid_symbols']}")
print(f"Invalid format: {result['invalid']}")
print(f"Non-existent: {result['non_existent']}")
print(f"Warnings: {result['warnings']}")
```

### Using `validate_symbols_batch()`

```python
from src.app.dashboard.symbol_validator import validate_symbols_batch

# Validate multiple symbols in parallel
symbols = ['AAPL', 'MSFT', 'GOOGL', 'INVALID']
result = validate_symbols_batch(symbols)

print(f"Valid: {result['valid_symbols']}")
print(f"Invalid: {result['invalid_symbols']}")
print(f"Unknown: {result['unknown_symbols']}")

# Get detailed info for each symbol
for symbol, details in result['validation_details'].items():
    if details['exists']:
        print(f"{symbol}: {details['info']['name']}")
    else:
        print(f"{symbol}: {details['error']}")
```

### Using `validate_watchlist_symbols_enhanced()`

```python
from src.app.dashboard.symbol_validator import validate_watchlist_symbols_enhanced

# Enhanced validation (format + existence)
symbols = ['AAPL', 'MSFT', 'INVALID', 'GOOGL']
result = validate_watchlist_symbols_enhanced(symbols)

print(f"Final valid symbols: {result['final_valid_symbols']}")
print(f"Final invalid symbols: {result['final_invalid_symbols']}")
```

## Validation Process

The validation process includes:

1. **Format Validation**
   - Removes duplicates
   - Validates format (uppercase, alphanumeric, 1-10 characters)
   - Removes empty strings

2. **Existence Check** (if `check_existence=True`)
   - Checks each symbol via yfinance API
   - Verifies symbol exists and has valid data
   - Returns company name, exchange, sector, industry

3. **Error Handling**
   - Network errors are treated as "unknown" (not invalid)
   - Timeout protection (5 seconds per symbol)
   - Parallel processing for speed (10 workers by default)

## Common Issues

### Invalid Symbols

**Problem**: Symbol doesn't exist
- **Solution**: Remove the symbol from the watchlist
- **Common causes**: Typos, delisted stocks, wrong exchange

### Unknown Symbols

**Problem**: Couldn't validate (network error)
- **Solution**: Retry validation or check network connection
- **Note**: Unknown symbols are not automatically removed

### Format Issues

**Problem**: Invalid format (e.g., lowercase, special characters)
- **Solution**: Symbols are automatically cleaned (uppercase, trimmed)
- **Format**: Must match `^[A-Z0-9\.\-]{1,10}$`

## Best Practices

1. **Validate before running analysis**: Always validate watchlists before using them
2. **Regular validation**: Periodically check watchlists for delisted stocks
3. **Use the command-line script**: Fastest way to validate entire watchlists
4. **Check the GUI**: Visual feedback when creating/editing watchlists
5. **Handle unknown symbols**: Retry validation for unknown symbols

## Integration with Watchlist Creation

When creating a watchlist via:
- **GUI**: Validation happens automatically
- **API**: Use `validate_watchlist_symbols()` before saving
- **YAML file**: Run validation script after editing

## Example: Validating All Watchlists

```bash
# Validate all watchlists in config
for watchlist in jan_26 tech_giants nasdaq_100; do
    echo "Validating $watchlist..."
    python scripts/validate_watchlist.py $watchlist
    echo ""
done
```

## Troubleshooting

### "Symbol not found" but symbol exists
- Check if symbol is on a different exchange (e.g., BRK.B vs BRK-B)
- Some symbols may require different format (e.g., C3AI vs AI)

### Network errors
- Check internet connection
- yfinance API may be rate-limited (wait and retry)
- Some symbols may be temporarily unavailable

### Slow validation
- Large watchlists (>100 symbols) may take time
- Validation runs in parallel (10 workers)
- Consider validating in batches

## Related Files

- `scripts/validate_watchlist.py` - Command-line validation script
- `src/app/dashboard/symbol_validator.py` - Core validation functions
- `src/app/dashboard/data.py` - Watchlist data management
- `src/app/dashboard/pages/watchlist_manager.py` - GUI watchlist manager

---

## See Also

- [Adding new symbols](adding-symbols-guide.md)
- [Handling failed downloads](failed-symbols-guide.md)
- [Data quality tracking](data-quality.md)
