# Frequently Asked Questions (FAQ)

## General Questions

### What is the Mid-term Stock Planner?

The Mid-term Stock Planner is an ML-powered portfolio optimization and analysis system designed for 3-month investment horizons. It uses ensemble machine learning models, technical indicators, fundamental analysis, and sentiment analysis to rank stocks and build optimized portfolios.

### What makes this different from other stock analysis tools?

- **ML-Powered**: Uses LightGBM/XGBoost ensemble models trained on historical data
- **Comprehensive Analysis**: Combines technical, fundamental, and sentiment analysis
- **Portfolio Optimization**: Builds risk-adjusted portfolios with multiple allocation strategies
- **AI Insights**: Generates natural language commentary and recommendations using Gemini
- **Advanced Analytics**: Event analysis, tax optimization, Monte Carlo simulation, and more

### What is the investment horizon?

The system is optimized for **3-month (mid-term) investment horizons** with monthly rebalancing. This is different from:
- **Day trading**: Very short-term (minutes to days)
- **Long-term investing**: Years to decades

## Installation & Setup

### What are the system requirements?

- Python 3.11 or higher
- 4GB+ RAM (8GB+ recommended)
- Internet connection (for data fetching and AI insights)
- Google API key (optional, for AI insights)

### Do I need a Google API key?

The Google API key is **optional but highly recommended**. Without it:
- ✅ You can still run all analysis
- ✅ You can still build portfolios
- ✅ You can still view all metrics
- ❌ You won't get AI-generated insights and recommendations

Get a free API key at: https://makersuite.google.com/app/apikey

### How do I set up the Google API key?

1. Get your API key from Google
2. Edit `config/config.yaml`
3. Add your key under `api_keys.google.api_key`
4. Restart the dashboard

### What data do I need?

**Required:**
- Price data (`data/prices.csv`) - Historical stock prices

**Recommended:**
- Sector mapping (`data/sectors.csv` or `sectors.json`) - For sector analysis
- Fundamental data (`data/fundamentals.csv`) - For value/quality scores

**Optional:**
- Benchmark data (`data/benchmark.csv`) - For comparison (or fetched automatically)

## Usage

### How do I run an analysis?

**Option 1: Dashboard (Recommended)**
1. Start dashboard: `streamlit run run_dashboard.py`
2. Go to "🎮 Run Analysis"
3. Select watchlist and dates
4. Click "Run Analysis"

**Option 2: Command Line**
```bash
python scripts/analyze_portfolio.py --watchlist tech_giants
```

### What is a watchlist?

A watchlist is a collection of stock symbols you want to analyze. Predefined watchlists include:
- Tech Giants (AAPL, MSFT, GOOGL, etc.)
- Blue-chip stocks
- Nuclear/Energy stocks
- Clean Energy stocks
- ETFs

You can create custom watchlists in "📋 Watchlist Manager".

### How do I create a custom watchlist?

1. Go to "📋 Watchlist Manager" in the dashboard
2. Click "Create New Watchlist"
3. Enter watchlist name and symbols (comma-separated)
4. Click "Save"

Or edit `config/watchlists.yaml` directly.

**New Features (v3.10.1+):**
- Stocks are automatically color-coded by sector
- Use "Update Sectors" tab to fetch sector data for unknown stocks
- One-click sector assignment from Yahoo Finance
- Dark mode support (Settings → Styles)

**Performance Features (v3.11+):**
- Lazy loading for charts and large tables
- Automatic chart optimization for 1000+ data points
- Query caching (5-minute TTL)
- Request batching for API calls
- Data compression for cached results
- Mobile-responsive design
- Performance monitoring dashboard

### What's the difference between Portfolio Builder and Run Analysis?

- **Run Analysis**: Analyzes an existing watchlist and ranks stocks
- **Portfolio Builder**: Builds a personalized portfolio based on your risk tolerance and goals

### How do I interpret the scores?

Scores range from 0-100 (or 0-1 in some views):

- **90-100**: Excellent - Strong buy signal
- **70-89**: Good - Buy signal
- **50-69**: Neutral - Hold
- **30-49**: Poor - Consider selling
- **0-29**: Very Poor - Strong sell signal

**Note**: Scores are relative to the watchlist, not absolute.

## Data & Analysis

### Why are some stocks missing fundamental data?

Fundamental data (PE, PB, ROE, etc.) must be downloaded separately:

```bash
python scripts/download_fundamentals.py
```

Stocks without fundamental data receive a penalty score (30) instead of neutral (50) to encourage data completeness.

### How often should I update price data?

For accurate analysis, update price data:
- **Daily**: For active trading
- **Weekly**: For regular monitoring
- **Monthly**: For long-term analysis

### What if I see "Data quality issues detected"?

This means the AI detected problems with your data:
- All sectors have identical scores (0.000)
- Missing critical data fields
- Unrealistic values

**Fix it:**
1. Check data completeness in "⚙️ Settings" → "Data Completeness"
2. Download missing fundamental data
3. Verify price data is up to date
4. Re-run analysis

### Why is benchmark comparison showing errors?

If you see "No overlapping dates" errors:
1. Check that your price data and benchmark data have overlapping date ranges
2. The system will try to fetch benchmark data from yfinance automatically
3. Ensure your internet connection is working

## Performance & Results

### What is a good Sharpe ratio?

- **> 2.0**: Excellent
- **1.0 - 2.0**: Good
- **0.5 - 1.0**: Acceptable
- **< 0.5**: Poor

**Note**: Sharpe ratio is risk-adjusted return. Higher is better.

### What is max drawdown?

Max drawdown is the largest peak-to-trough decline in portfolio value. For example:
- **-10%**: Lost 10% from peak
- **-20%**: Lost 20% from peak

Lower (less negative) is better.

### How do I compare different strategies?

1. Run multiple analyses with different configurations
2. Go to "📈 Compare Runs" for side-by-side comparison
3. Or use "🔀 Advanced Comparison" for multi-run analysis

### What is performance attribution?

Performance attribution breaks down returns into:
- **Factor Exposure**: How much did value/growth/quality contribute?
- **Sector Allocation**: Which sectors added/subtracted value?
- **Stock Selection**: Did you pick the right stocks within sectors?
- **Timing**: Did rebalancing help or hurt?

## Advanced Features

### How does tax optimization work?

The tax optimization module:
- Identifies tax-loss harvesting opportunities
- Detects wash sales (30-day window)
- Suggests tax-efficient rebalancing
- Calculates tax efficiency scores

**Note**: This is for informational purposes only. Consult a tax professional for actual tax advice.

### What is Monte Carlo simulation?

Monte Carlo simulation runs thousands of random scenarios to estimate:
- Probability distributions of returns
- Value at Risk (VaR)
- Confidence intervals
- Worst-case scenarios

### How do I set up alerts?

Currently, alerts are shown in the "⚡ Real-Time Monitoring" page. Email/SMS notifications are planned for future releases.

### What is event-driven analysis?

Event-driven analysis shows how your portfolio performs around:
- Fed meetings
- Earnings announcements
- Macro data releases (CPI, GDP, etc.)

This helps identify if your portfolio is sensitive to specific events.

## Performance & Optimization (v3.11+)

### Why are charts loading slowly?

**Large Datasets:**
- Charts with 1000+ data points are automatically optimized
- Use "Lazy Load" mode in Portfolio Analysis for faster initial load
- Charts load progressively (one at a time or in batches)

**Solutions:**
1. Enable "Lazy Load" mode in chart settings
2. Filter data before generating charts
3. Use pagination for large tables
4. Clear cache if performance degrades (Performance Monitoring page)

### How does query caching work?

**Automatic Caching:**
- Frequently accessed queries are cached for 5 minutes
- Cache includes: run lists, scores, sector mappings
- Cache is automatically cleared when data changes

**Manual Control:**
- View cache stats in Performance Monitoring page
- Clear cache manually if needed
- Cache compression reduces memory usage by 20-40%

### What is request batching?

**API Request Batching:**
- Multiple API requests are grouped and sent together
- Improves performance (parallel execution)
- Respects rate limits automatically
- Reduces API costs

**Configuration:**
- Batch size: 10 requests per batch (default)
- Rate limit: Configurable per API provider
- Automatic fallback if batching fails

### How do I optimize for large datasets?

**Best Practices:**
1. Use pagination for tables (10-100 items per page)
2. Enable lazy loading for charts
3. Filter data before analysis
4. Use virtual scrolling for very large lists (1000+ items)
5. Clear cache periodically

**Performance Tips:**
- Close unused browser tabs
- Use "Lazy Load" mode when exploring multiple runs
- Export large datasets instead of viewing in browser
- Use filters to reduce data size before analysis

## Troubleshooting

### The dashboard won't start

1. Check Python version: `python --version` (need 3.11+)
2. Install dependencies: `pip install -r requirements.txt`
3. Check for port conflicts (default port 8501)

### I'm getting "Module not found" errors

Install missing dependencies:
```bash
pip install -r requirements.txt
```

### Analysis is taking too long

- Reduce watchlist size
- Use shorter date ranges
- Disable AI insights (faster)
- Check system resources (RAM, CPU)

### Charts are not loading

- Check browser console for errors
- Try refreshing the page
- Use "Lazy Load" mode in Portfolio Analysis
- Clear browser cache

### Database errors

If you see SQLite errors:
1. Check database file permissions
2. Ensure `data/analysis.db` exists
3. Try running the migration script: `python scripts/migrate_database_indexes.py`

## Best Practices

### For Best Results

1. **Use Quality Data**: Ensure price data is complete and accurate
2. **Download Fundamentals**: Better value/quality scores
3. **Regular Updates**: Keep data current
4. **Review Warnings**: Pay attention to data quality warnings
5. **Compare Strategies**: Test different configurations
6. **Understand Scores**: Scores are relative, not absolute
7. **Diversify**: Don't put all eggs in one basket

### Common Mistakes to Avoid

1. **Ignoring Data Quality Warnings**: Always fix data issues first
2. **Over-optimizing**: Past performance doesn't guarantee future results
3. **Ignoring Risk**: High returns often come with high risk
4. **Not Rebalancing**: Portfolios drift over time
5. **Chasing Performance**: What worked yesterday may not work tomorrow

## Getting Help

### Where can I find more documentation?

- Browse all docs in the "📚 Documentation" page in the dashboard
- Check the `docs/` folder in the repository
- See [Quick Start Guide](quick-start-guide.md)

### How do I report bugs?

Open an issue on GitHub with:
- Description of the problem
- Steps to reproduce
- Error messages (if any)
- System information (OS, Python version)

### Can I contribute?

Yes! Contributions are welcome. Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Still have questions?** Check the [User Guide](user-guide.md) or open an issue on GitHub.
