# Download Fundamentals Data Guide

## Problem

When running purchase triggers analysis, you may see:
- ❌ **Critical Issue**: Only 11/88 stocks (12.5%) have fundamental data!
- ❌ **No quality data** (ROE/margins) available. All quality scores default to 50.0.

This happens because `data/fundamentals.csv` is missing:
1. **Coverage**: Not all tickers in your watchlist have fundamental data
2. **Quality metrics**: Missing ROE, net_margin, gross_margin columns

## Solution

Use the `download_fundamentals.py` script to download comprehensive fundamentals data.

## Quick Start

### 1. Download for Your Watchlist

```bash
# Download for the watchlist used in your last run
python scripts/download_fundamentals.py --watchlist nasdaq_100
```

### 2. Download for All Tickers in a Run

First, find which watchlist was used:
```bash
# Check your latest run
python scripts/diagnose_value_quality_scores.py
```

Then download fundamentals for that watchlist:
```bash
python scripts/download_fundamentals.py --watchlist <watchlist_name>
```

### 3. Download for Specific Tickers

```bash
python scripts/download_fundamentals.py --tickers AAPL MSFT GOOGL AMZN TSLA
```

## What Gets Downloaded

The script downloads the following metrics from Yahoo Finance:

### Valuation Metrics
- **PE** (Price-to-Earnings): `trailingPE` or `forwardPE`
- **PB** (Price-to-Book): `priceToBook`
- **PS** (Price-to-Sales): `priceToSalesTrailing12Months`
- **PEG** (PEG Ratio): `pegRatio`

### Profitability Metrics (Quality Scores)
- **ROE** (Return on Equity): `returnOnEquity` (as decimal, e.g., 0.15 = 15%)
- **ROA** (Return on Assets): `returnOnAssets`
- **Net Margin**: `profitMargins` (as decimal)
- **Gross Margin**: `grossMargins` (as decimal)
- **Operating Margin**: `operatingMargins` (as decimal)

### Financial Health
- **Debt-to-Equity**: `debtToEquity`
- **Current Ratio**: `currentRatio`
- **Quick Ratio**: `quickRatio`

### Growth Metrics
- **Revenue Growth**: `revenueGrowth`
- **Earnings Growth**: `earningsQuarterlyGrowth`

### Market Metrics
- **Market Cap**: `marketCap`
- **Enterprise Value**: `enterpriseValue`

## Output Format

Data is saved to `data/fundamentals.csv` with columns:
- `ticker`: Stock symbol
- `date`: Date of data (YYYY-MM-DD)
- `pe`, `pb`, `ps`, `peg`: Valuation ratios
- `roe`, `roa`: Return metrics
- `net_margin`, `gross_margin`, `operating_margin`: Margin metrics
- `debt_to_equity`, `current_ratio`, `quick_ratio`: Financial health
- `revenue_growth`, `earnings_growth`: Growth metrics
- `market_cap`, `enterprise_value`: Market metrics

## Usage Examples

### Download for Default Watchlist
```bash
python scripts/download_fundamentals.py
```

### Download for Specific Watchlist
```bash
python scripts/download_fundamentals.py --watchlist nasdaq_100
python scripts/download_fundamentals.py --watchlist sp500
python scripts/download_fundamentals.py --watchlist tech_giants
```

### Download for Specific Tickers
```bash
python scripts/download_fundamentals.py --tickers AAPL MSFT GOOGL AMZN TSLA NVDA
```

### Custom Output File
```bash
python scripts/download_fundamentals.py --output data/my_fundamentals.csv
```

### Adjust Rate Limiting
```bash
# Slower (more polite to Yahoo Finance)
python scripts/download_fundamentals.py --delay 1.0

# Faster (may hit rate limits)
python scripts/download_fundamentals.py --delay 0.2
```

## After Downloading

1. **Verify Data**:
   ```bash
   python scripts/diagnose_value_quality_scores.py
   ```
   This will show:
   - How many stocks have data
   - Coverage percentage
   - Which metrics are available

2. **Refresh Purchase Triggers**:
   - Go to Purchase Triggers page in GUI
   - Select your run
   - Check that warnings are gone and scores are differentiated

3. **Run New Analysis** (Optional):
   - Create a new analysis run with the updated fundamentals
   - Value and Quality scores should now differentiate properly

## Troubleshooting

### "No tickers found"
- Check that your watchlist name is correct
- List available watchlists:
  ```bash
  grep -A 1 "^  [a-z_]*:" config/watchlists.yaml | head -20
  ```

### "yfinance not installed"
```bash
pip install yfinance
```

### "Rate limit errors"
- Increase delay: `--delay 1.0` or `--delay 2.0`
- Download in smaller batches using `--tickers`

### "Some tickers failed"
- Some tickers may not have data on Yahoo Finance
- Check if ticker symbols are correct
- Some foreign stocks may need different symbols

### "Data still shows 50.0 scores"
- Verify fundamentals.csv was updated: `head data/fundamentals.csv`
- Check that tickers match between run and fundamentals
- Run diagnostics: `python scripts/diagnose_value_quality_scores.py`

## Expected Results

After downloading, you should see:
- ✅ **Fundamentals**: 88/88 stocks (100%) have value & quality data
- ✅ **Value scores differentiated**: 88 unique values (range: 0.0-100.0)
- ✅ **Quality scores differentiated**: 88 unique values (range: 0.0-100.0)

## Notes

- **Rate Limiting**: Yahoo Finance may rate limit requests. Default delay is 0.5 seconds.
- **Data Freshness**: Fundamentals are point-in-time. Re-download periodically (monthly/quarterly).
- **Missing Data**: Some metrics may be missing for certain stocks (e.g., new IPOs, foreign stocks).
- **Data Format**: ROE and margins are stored as decimals (0.15 = 15%), not percentages.

## Related Scripts

- `diagnose_value_quality_scores.py`: Check data coverage and score differentiation
- `download_prices.py`: Download historical price data
- `fetch_sector_data.py`: Download sector classifications
