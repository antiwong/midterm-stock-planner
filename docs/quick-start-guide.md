# Quick Start Guide

**Welcome to the Mid-term Stock Planner!** This guide will help you get started in 5 minutes.

## Prerequisites

- Python 3.11 or higher
- Git (for cloning the repository)
- A Google API key (for AI insights - optional but recommended)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/antiwong/midterm-stock-planner.git
cd midterm-stock-planner
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Configuration

Copy the example config file:

```bash
cp config/config.yaml.example config/config.yaml
```

Edit `config/config.yaml` and add your Google API key:

```yaml
api_keys:
  google:
    api_key: "YOUR_GOOGLE_API_KEY_HERE"
```

### 4. Prepare Data

Ensure you have:
- Price data in `data/prices.csv`
- Sector mapping in `data/sectors.csv` (or `sectors.json`)
- Optional: Fundamental data in `data/fundamentals.csv`

## Running Your First Analysis

### Option 1: Using the Dashboard (Recommended)

1. **Start the Dashboard:**
   ```bash
   streamlit run run_dashboard.py
   ```

2. **Navigate to "🎮 Run Analysis"** in the sidebar

3. **Select a Watchlist:**
   - Choose from predefined watchlists (Tech Giants, Blue-chip, etc.)
   - Or create a custom watchlist in "📋 Watchlist Manager"

4. **Configure Analysis:**
   - Set start/end dates
   - Choose whether to include AI insights
   - Click "Run Analysis"

5. **View Results:**
   - Go to "💼 Portfolio Analysis" to see your portfolio
   - Check "📊 Comprehensive Analysis" for detailed metrics
   - Review "🤖 AI Insights" for recommendations

### Option 2: Using the Command Line

```bash
python scripts/analyze_portfolio.py \
  --watchlist tech_giants \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --include-ai
```

## Key Features to Try

### 1. Portfolio Builder
- Navigate to "🎯 Portfolio Builder"
- Select your risk tolerance (Conservative, Moderate, Aggressive)
- Adjust target return and portfolio size
- Build your personalized portfolio

### 2. Comprehensive Analysis
- Go to "📊 Comprehensive Analysis"
- Select a completed run
- Explore:
  - Performance Attribution
  - Benchmark Comparison
  - Factor Exposure
  - Rebalancing Analysis
  - Style Analysis

### 3. Advanced Analytics
- **Event Analysis**: See how your portfolio performs around Fed meetings and earnings
- **Tax Optimization**: Get tax-loss harvesting suggestions
- **Monte Carlo**: View risk scenarios and probability distributions
- **Turnover Analysis**: Analyze portfolio churn and holding periods
- **Earnings Calendar**: Track upcoming earnings dates
- **Real-Time Monitoring**: Daily portfolio updates and alerts

### 4. AI Insights
- Navigate to "🤖 AI Insights"
- Generate executive summaries
- Get sector rotation recommendations
- Review investment recommendations with data quality validation

## Understanding the Results

### Key Metrics

- **Total Return**: Overall portfolio performance
- **Sharpe Ratio**: Risk-adjusted return (higher is better)
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable periods
- **Hit Rate**: Percentage of periods beating benchmark

### Score Components

- **Model Score**: ML prediction of 3-month forward return
- **Value Score**: Based on PE/PB ratios (lower is better)
- **Quality Score**: Based on ROE and margins (higher is better)
- **Technical Score**: Based on RSI, momentum, etc.
- **Sentiment Score**: News sentiment analysis

## Next Steps

1. **Explore Documentation**: Check out the "📚 Documentation" page in the dashboard
2. **Create Custom Watchlists**: Use "📋 Watchlist Manager" to build your own
3. **Compare Runs**: Use "📈 Compare Runs" to compare different strategies
4. **Export Results**: Export analysis results as CSV, JSON, PDF, or Excel

## Getting Help

- **FAQ**: See `docs/faq.md` for common questions
- **Documentation**: Browse all docs in the "📚 Documentation" page
- **Issues**: Report bugs on GitHub

## Tips for Best Results

1. **Use Quality Data**: Ensure price data is complete and accurate
2. **Download Fundamentals**: Run `scripts/download_fundamentals.py` for better value/quality scores
3. **Regular Updates**: Update price data regularly for accurate analysis
4. **Review AI Insights**: Always review AI recommendations for data quality warnings
5. **Compare Strategies**: Use comparison tools to find what works best

---

**Ready to dive deeper?** Check out the [User Guide](user-guide.md) for detailed workflows and advanced features.
