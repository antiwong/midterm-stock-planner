# Adding Symbols to Watchlist Guide

> [← Back to Documentation Index](README.md)

This guide shows you how to add symbols to your watchlists, including special cases like Singapore stocks (e.g., ME8U.SI).

## Quick Answer: Adding ME8U.SI

**ME8U.SI** is a valid Singapore stock (Mapletree Industrial Trust). You can add it in any of these ways:

### Option 1: GUI (Easiest)
1. Open dashboard: `streamlit run run_dashboard.py`
2. Go to **"📋 Watchlist Manager"**
3. Create or edit a watchlist
4. Enter: `ME8U.SI` (trailing slash will be auto-removed)
5. Click "Create Watchlist" or "Save"

### Option 2: YAML File
Edit `config/watchlists.yaml`:
```yaml
singapore_reits:
  name: "Singapore REITs"
  symbols:
    - ME8U.SI  # Mapletree Industrial Trust
```

### Option 3: Tiger Trading Format
If you're using Tiger Trading, you can use:
- `ME8U.SG` (Tiger format) - will be auto-converted to `ME8U.SI`

## Symbol Format Notes

### Singapore Stocks
- **Standard format**: `ME8U.SI` (yfinance format)
- **Tiger Trading format**: `ME8U.SG` (auto-converts to `.SI`)
- Both formats work - the system automatically converts Tiger format

### Other Exchanges
- **Hong Kong**: `0700.HK` (both formats use `.HK`)
- **Australia**: `BHP.AU` (Tiger) → `BHP.AX` (yfinance)
- **US**: `AAPL`, `MSFT` (no suffix)

## Common Issues

### Trailing Slash
- **Problem**: `ME8U.SI/` has trailing slash
- **Solution**: Automatically cleaned to `ME8U.SI`
- **Action**: No action needed, just enter it normally

### Wrong Format
- **Problem**: Symbol not found
- **Solution**: Check if you need exchange suffix
- **Example**: Singapore stocks need `.SI` or `.SG`

### Symbol Not Found
- **Problem**: Validation says symbol doesn't exist
- **Solution**: 
  1. Check spelling
  2. Verify exchange suffix
  3. Check if stock is delisted
  4. Try validating: `python scripts/validate_watchlist.py <watchlist_id>`

## Validation

After adding symbols, validate them:

```bash
# Validate a watchlist
python scripts/validate_watchlist.py <watchlist_id>

# Convert Tiger symbols
python scripts/convert_tiger_symbols.py ME8U.SG --validate
```

## Examples

### Adding Multiple Singapore Stocks
```yaml
singapore_stocks:
  name: "Singapore Stocks"
  symbols:
    - ME8U.SI  # Mapletree Industrial Trust
    - D05.SI   # DBS Group
    - O39.SI   # Oversea-Chinese Banking Corp
```

### Mixed Exchanges
```yaml
asia_pacific:
  name: "Asia Pacific Portfolio"
  symbols:
    - AAPL      # US
    - MSFT      # US
    - 0700.HK   # Hong Kong (Tencent)
    - ME8U.SI   # Singapore
    - BHP.AU    # Australia (Tiger format, auto-converts)
```

## Tips

1. **Use GUI for convenience**: Automatic validation and format conversion
2. **Use YAML for bulk**: Easier to add many symbols at once
3. **Validate after editing**: Always validate watchlists after manual edits
4. **Check format**: Singapore stocks need `.SI` or `.SG` suffix
5. **Trailing characters**: Slashes, spaces are automatically cleaned

## Related

- **Per-ticker config** (RSI, MACD, VIX, volume/OBV filters for trigger backtest): [config/tickers/README.md](../config/tickers/README.md)

---

## See Also

- [Validating watchlist symbols](watchlist-validation-guide.md)
- [Downloading fundamental data](download-fundamentals-guide.md)
- [Handling failed downloads](failed-symbols-guide.md)
- [Full user workflows](user-guide.md)
