# Fundamentals Data Sources Guide

> [← Back to Documentation Index](README.md)

## Overview

The Mid-term Stock Planner supports multiple data sources for fundamental data to maximize completeness and reliability. The system automatically tries multiple sources and merges results.

## Available Data Sources

### 1. Yahoo Finance (yfinance) - Primary Source ✅

**Status:** Always available (no API key required)

**Coverage:**
- PE, PB, PS, PEG ratios
- ROE, ROA, profit margins
- Debt-to-equity, current ratio
- Revenue/earnings growth
- Market cap, enterprise value
- Dividend yield, beta

**Rate Limits:** None (but be respectful)

**Setup:** No setup required - automatically used

### 2. Alpha Vantage - Alternative Source 🔑

**Status:** Requires free API key

**Coverage:**
- Company overview data
- Financial ratios (PE, PB, PS, PEG)
- Profitability metrics (ROE, ROA, margins)
- Growth metrics
- Market capitalization

**Rate Limits:**
- Free tier: 5 requests/minute, 500 requests/day
- Paid tiers available

**Setup:**
1. Get free API key: https://www.alphavantage.co/support/#api-key
2. Add to `.env` file:
   ```
   ALPHA_VANTAGE_API_KEY=your-api-key-here
   ```

### 3. Polygon.io - Alternative Source 🔑

**Status:** Requires API key (free tier available)

**Coverage:**
- Financial statements
- Market data
- Company fundamentals

**Rate Limits:**
- Free tier: 5 requests/minute
- Paid tiers available

**Setup:**
1. Sign up: https://polygon.io/
2. Get API key from dashboard
3. Add to `.env` file:
   ```
   POLYGON_API_KEY=your-api-key-here
   ```

### 4. Finnhub - Alternative Source 🔑

**Status:** Requires API key (free tier available)

**Coverage:**
- Company profiles
- Financial metrics
- Market data

**Rate Limits:**
- Free tier: 60 requests/minute
- Paid tiers available

**Setup:**
1. Sign up: https://finnhub.io/
2. Get API key from dashboard
3. Add to `.env` file:
   ```
   FINNHUB_API_KEY=your-api-key-here
   ```

## How Multi-Source Fetching Works

The system uses a **fallback and merge strategy**:

1. **Primary:** Yahoo Finance (always tried first)
2. **Fallback:** If Yahoo Finance fails or returns incomplete data, tries Alpha Vantage
3. **Additional:** If configured, also tries Polygon.io and Finnhub
4. **Merge:** Results from all sources are merged, prioritizing non-None values

### Example Flow

```
For each stock:
  1. Try Yahoo Finance → Get PE, PB, ROE
  2. Try Alpha Vantage → Get missing PS, PEG, margins
  3. Try Finnhub → Get missing market cap
  4. Merge all results → Complete dataset
```

## Usage

### Command Line

```bash
# Download fundamentals for a watchlist (uses all available sources)
python scripts/download_fundamentals.py --watchlist jan_26

# Download for specific tickers
python scripts/download_fundamentals.py --tickers AAPL MSFT GOOGL

# Download for all watchlists
python scripts/download_fundamentals.py
```

### GUI

1. Navigate to **📊 Fundamentals Status** page
2. Select a watchlist
3. View missing/incomplete stocks
4. Use the download instructions shown

## Maximizing Data Completeness

### Strategy 1: Use Multiple Free Sources

1. **Get Alpha Vantage key** (free, 500 requests/day)
2. **Get Finnhub key** (free, 60 req/min)
3. Add both to `.env`
4. Run download script

**Result:** ~90-95% data completeness for most stocks

### Strategy 2: Stagger Downloads

If you hit rate limits:

```bash
# Download in batches
python scripts/download_fundamentals.py --watchlist batch1
# Wait 1 minute
python scripts/download_fundamentals.py --watchlist batch2
```

### Strategy 3: Focus on Missing Stocks

1. Check fundamentals status in GUI
2. Identify stocks with missing data
3. Download only those stocks:

```bash
python scripts/download_fundamentals.py --tickers MISSING1 MISSING2 MISSING3
```

## Troubleshooting

### "No data fetched" Error

**Possible causes:**
- Invalid ticker symbols
- Network connectivity issues
- All sources rate-limited

**Solutions:**
- Verify ticker symbols are correct
- Check internet connection
- Wait and retry (rate limits reset)
- Add API keys for alternative sources

### "Rate limit exceeded" Error

**Solutions:**
- Wait for rate limit window to reset
- Use fewer tickers per batch
- Add more API keys (more sources = more requests)

### Incomplete Data

**Solutions:**
- Add API keys for alternative sources
- Re-run download script (may fill gaps)
- Check if stock is listed on all exchanges
- Some stocks may genuinely lack certain metrics

## API Key Management

### Where to Put Keys

Create or edit `.env` file in project root:

```bash
# .env
ALPHA_VANTAGE_API_KEY=your-key-here
POLYGON_API_KEY=your-key-here
FINNHUB_API_KEY=your-key-here
```

### Verify Keys Are Loaded

```python
from src.config.api_keys import load_api_keys

keys = load_api_keys()
print(keys)  # Should show your keys (masked)
```

### Security

- **Never commit `.env` to git** (already in `.gitignore`)
- **Don't share API keys** publicly
- **Rotate keys** if exposed

## Best Practices

1. **Start with Yahoo Finance only** - works for most stocks
2. **Add Alpha Vantage** - best free alternative (500/day)
3. **Add Finnhub** - for high-frequency updates (60/min)
4. **Use Polygon.io** - if you need financial statements
5. **Monitor rate limits** - don't exceed free tier limits
6. **Cache results** - don't re-download unnecessarily

## Cost Comparison

| Source | Free Tier | Paid Tier |
|--------|-----------|-----------|
| Yahoo Finance | Unlimited | N/A |
| Alpha Vantage | 500/day | $49.99/month |
| Polygon.io | 5/min | $29/month |
| Finnhub | 60/min | $9/month |

**Recommendation:** Use Yahoo Finance + Alpha Vantage (both free) for most use cases.

## Support

For issues or questions:
- Check `docs/api-configuration.md` for API setup
- Review `docs/fundamentals-data.md` for data format
- See `scripts/download_fundamentals.py` for implementation

---

## See Also

- [Fundamental data overview](fundamental-data.md)
- [Download guide](download-fundamentals-guide.md)
- [All data providers](data-providers-guide.md)
- [API key setup](api-configuration.md)
