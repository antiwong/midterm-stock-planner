# Quick Start Guide

> [← Back to Documentation Index](README.md)

**Welcome to the Mid-term Stock Planner v3.11.2!** This guide will help you get started in 5 minutes.

## Prerequisites

### Required

- **Python 3.11+** (check with `python --version`)
- **pip** (check with `pip --version`)
- **Git** (for cloning the repository)
- **4GB+ RAM** (8GB+ recommended for large watchlists)
- **Internet connection** (for data fetching)

### Optional

- **Google API key** - For AI-powered insights (Gemini). Free tier available.
- **NewsAPI key** - For sentiment analysis. Included default key supports 100 req/day.

### Verify Python Version

```bash
python --version
# Must be 3.11 or higher. If not:
# macOS: brew install python@3.11
# Ubuntu: sudo apt install python3.11
# Windows: Download from python.org
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/antiwong/midterm-stock-planner.git
cd midterm-stock-planner
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs ~30 packages including pandas, numpy, lightgbm, streamlit, plotly, shap, and yfinance.

### 4. Set Up Configuration

```bash
cp config/config.yaml.example config/config.yaml
```

Edit `config/config.yaml` to add your API key (optional):

```yaml
api_keys:
  google:
    api_key: "YOUR_GOOGLE_API_KEY_HERE"
```

Or use the included default keys:

```bash
source scripts/setup_env.sh
```

### 5. Prepare Data Files

The system needs these files in the `data/` directory:

| File | Required | Format |
|------|----------|--------|
| `data/prices.csv` | Yes | Columns: `date`, `ticker`, `open`, `high`, `low`, `close`, `volume` |
| `data/benchmark.csv` | Yes | Columns: `date`, `close` (S&P 500 benchmark) |
| `data/sectors.json` | Yes | JSON mapping: `{"AAPL": "Technology", "MSFT": "Technology", ...}` |
| `data/fundamentals.csv` | Optional | Columns: `ticker`, `pe_ratio`, `pb_ratio`, `roe`, `debt_to_equity`, ... |
| `data/universe.txt` | Optional | One ticker per line |

**Example `data/prices.csv`:**
```csv
date,ticker,open,high,low,close,volume
2024-01-02,AAPL,185.50,186.20,184.80,185.90,45000000
2024-01-02,MSFT,374.10,375.50,373.00,374.80,22000000
```

**To download price data automatically:**
```bash
python scripts/download_prices.py
```

**To download fundamental data:**
```bash
python scripts/download_fundamentals.py
```

## Running Your First Analysis

### Option 1: Using the Dashboard (Recommended)

1. **Start the Dashboard:**
   ```bash
   streamlit run run_dashboard.py
   ```
   The dashboard opens at `http://localhost:8501`.

2. **Navigate to "Run Analysis"** in the sidebar

3. **Select a Watchlist:**
   - Choose from predefined watchlists (Tech Giants, Blue-chip, etc.)
   - Or create a custom watchlist in "Watchlist Manager"

4. **Configure Analysis:**
   - Set start/end dates
   - Choose whether to include AI insights
   - Click "Run Analysis"

5. **View Results:**
   - Go to "Portfolio Analysis" to see your portfolio
   - Check "Comprehensive Analysis" for detailed metrics
   - Review "AI Insights" for recommendations

**Expected output:** The analysis typically completes in 2-5 minutes. You'll see a progress bar during execution. Once complete, the Portfolio Analysis page shows ranked stocks with scores, sector allocation charts, and performance metrics.

### Option 2: Using the Command Line

```bash
# Run a backtest with the tech_giants watchlist
python -m src.app.cli run-backtest --watchlist tech_giants --name "My First Run"

# Build a personalized portfolio
python scripts/run_portfolio_optimizer.py --profile moderate --with-ai

# Run comprehensive analysis on a completed run
python scripts/run_comprehensive_analysis.py --run-id <run_id>

# Transfer & robustness testing (same config, different universe)
python scripts/transfer_report.py --watchlist nasdaq_100 --transfer-watchlist sp500
```

**Expected CLI output:**
```
[INFO] Loading configuration from config/config.yaml
[INFO] Using watchlist: tech_giants (12 symbols)
[INFO] Training period: 2019-01-01 to 2023-12-31
[INFO] Test period: 2024-01-01 to 2024-12-31
[INFO] Walk-forward window 1/5: training...
[INFO] Walk-forward window 1/5: predicting...
...
[INFO] Backtest complete. Results saved to output/run_tech_giants_20260220_143012/
[INFO] Total return: 18.5%, Sharpe: 1.42, Max DD: -8.2%
```

## Key Features to Try

### 1. Portfolio Builder
- Navigate to "Portfolio Builder"
- Select your risk tolerance (Conservative, Moderate, Aggressive)
- Adjust target return and portfolio size
- Build your personalized portfolio

### 2. Comprehensive Analysis
- Go to "Comprehensive Analysis"
- Select a completed run
- Explore: Performance Attribution, Benchmark Comparison, Factor Exposure, Rebalancing Analysis, Style Analysis

### 3. Advanced Analytics
- **Event Analysis**: Portfolio performance around Fed meetings and earnings
- **Tax Optimization**: Tax-loss harvesting suggestions
- **Monte Carlo**: Risk scenarios and probability distributions
- **Turnover Analysis**: Portfolio churn and holding periods
- **Earnings Calendar**: Upcoming earnings dates
- **Real-Time Monitoring**: Daily portfolio updates and alerts

### 4. AI Insights
- Navigate to "AI Insights"
- Generate executive summaries
- Get sector rotation recommendations
- Review investment recommendations with data quality validation

## Understanding the Results

### Key Metrics

- **Total Return**: Overall portfolio performance
- **Sharpe Ratio**: Risk-adjusted return (higher is better, >1.0 is good)
- **Max Drawdown**: Largest peak-to-trough decline (lower magnitude is better)
- **Win Rate**: Percentage of profitable periods
- **Hit Rate**: Percentage of periods beating benchmark

### Score Components

- **Model Score**: ML prediction of 3-month forward return
- **Value Score**: Based on PE/PB ratios (lower is better)
- **Quality Score**: Based on ROE and margins (higher is better)
- **Technical Score**: Based on RSI, momentum, etc.
- **Sentiment Score**: News sentiment analysis

## Troubleshooting

### "ModuleNotFoundError" on startup

```bash
# Ensure you're in the virtual environment
source venv/bin/activate
# Reinstall dependencies
pip install -r requirements.txt
```

### "No price data found" or empty results

- Verify `data/prices.csv` exists and has data for your selected date range
- Run `python scripts/download_prices.py` to fetch fresh data
- Check that ticker symbols match between prices.csv and your watchlist

### "Config file not found"

```bash
cp config/config.yaml.example config/config.yaml
```

### Dashboard won't start

```bash
# Check if port 8501 is in use
lsof -i :8501
# Try a different port
streamlit run run_dashboard.py --server.port 8502
```

### "Insufficient data for walk-forward backtest"

- Ensure you have at least 5 years of price history
- Check start/end dates in your config
- Run `python scripts/diagnose_backtest_data.py` for detailed diagnostics

### Slow performance with large watchlists

- v3.11 includes lazy loading and progressive charts - enable "Lazy Load" mode in Portfolio Analysis
- Reduce watchlist to 20-50 stocks for faster results
- Charts with 1000+ points are automatically downsampled

## Next Steps

1. **Explore Documentation**: Check out the "Documentation" page in the dashboard
2. **Create Custom Watchlists**: Use "Watchlist Manager" to build your own
3. **Compare Runs**: Use "Compare Runs" to compare different strategies
4. **Export Results**: Export analysis results as CSV, JSON, PDF, or Excel
5. **Report Templates**: Create custom report templates for recurring analysis

## Getting Help

- **FAQ**: [faq.md](faq.md) — Common questions
- **Documentation Index**: [README.md](README.md) — All 64+ docs, quick navigation
- **User Guide**: [user-guide.md](user-guide.md) — Detailed workflows
- **Backtesting**: [backtesting.md](backtesting.md) — Scripts, transfer, evolutionary
- **Issues**: Report bugs on GitHub

---

**Ready to dive deeper?** Check out the [User Guide](user-guide.md) for detailed workflows and advanced features.

---

## See Also

- [Complete workflows and advanced features](user-guide.md)
- [Configuration options and CLI commands](configuration-cli.md)
- [Common questions and answers](faq.md)
- [How to add new stock symbols](adding-symbols-guide.md)
- [Troubleshooting Guide](troubleshooting.md)
- [Common Workflows](common-workflows.md)
