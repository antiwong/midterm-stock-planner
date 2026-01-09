# Dashboard Guide

The Streamlit dashboard provides a comprehensive web interface for running analyses, building portfolios, and viewing results.

## Launching the Dashboard

```bash
streamlit run src/app/dashboard.py
```

Access at: http://localhost:8501

## Navigation

The sidebar provides navigation to all pages:

| Page | Description |
|------|-------------|
| 🏠 **Overview** | Summary metrics and recent runs |
| 🎮 **Run Analysis** | 4-stage analysis pipeline |
| 🎯 **Portfolio Builder** | Personalized portfolio construction |
| 📄 **Reports** | Browse generated reports |
| 💼 **Portfolio Analysis** | Detailed portfolio view |
| 📊 **Analysis Runs** | Filter and explore runs |
| 🔍 **Stock Explorer** | Individual stock analysis |
| 🤖 **AI Insights** | Generate AI commentary |
| 📈 **Compare Runs** | Side-by-side comparison |
| ⚙️ **Settings** | Configuration options |

## Pages

### 🏠 Overview

Dashboard home page showing:

- **Summary Metrics**: Total runs, completed count, average return/Sharpe
- **Recent Runs Table**: Latest analysis runs with key metrics
- **Performance Chart**: Return and Sharpe over time

### 🎮 Run Analysis

The main analysis control panel with a clear 4-stage pipeline:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  STAGE 1    │───▶│  STAGE 2    │───▶│  STAGE 3    │───▶│  STAGE 4    │
│  Backtest   │    │  Enrichment │    │  Domain     │    │  AI Analysis│
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

#### Quick Start: Full Analysis

At the top, run the complete pipeline in one click:
- Automatically runs backtest if none exists
- Runs all stages sequentially
- Option to include AI analysis

#### Pipeline Status

Shows completion status for each stage:
- ✅ Complete (files exist)
- ⚪ Not started
- ❌ Blocked (missing prerequisites)

#### Individual Stage Controls

Tabs for running each stage independently:

**Stage 1: Backtest**
- Run ML model training and walk-forward backtest
- Creates stock scores and predictions
- Always available

**Stage 2: Enrichment**
- Add risk metrics, weights, score breakdowns
- Requires Stage 1 complete
- Creates portfolio_enriched_*.csv

**Stage 3: Domain Analysis**
- Vertical (within-sector) ranking
- Horizontal (cross-sector) selection
- Requires Stage 1, warns if no Stage 2

**Stage 4: AI Analysis**
- Generate Gemini commentary
- Generate portfolio recommendations
- Requires Stage 1, warns if no Stage 3

#### Output Files Browser

View all generated files for the selected run.

### 🎯 Portfolio Builder

Build personalized portfolios based on your preferences:

1. **Select Run**: Choose which backtest to analyze
2. **Investor Profile**: Set your parameters
   - Risk tolerance, max drawdown, volatility
   - Target return, time horizon
   - Portfolio size, position/sector limits
   - Style preferences
3. **Build Portfolio**: Run optimization
4. **View Results**: Holdings, metrics, AI analysis

See [Portfolio Builder Documentation](portfolio-builder.md) for details.

### 📄 Reports

Browse all generated reports for a run:

1. **Select Run Folder**: Choose from available run folders
2. **Report Summary**: See which reports exist
3. **View/Download**: Preview or download any file

Report categories:
- **Backtest**: Returns, positions, metrics
- **Portfolio**: Enriched holdings, sector analysis
- **Domain**: Vertical candidates, horizontal portfolio
- **AI**: Commentary, recommendations

### 💼 Portfolio Analysis

Comprehensive portfolio view with beautiful visualizations and AI insights:

#### Hero Section
- Gradient banner with portfolio title
- Glass-morphism metric cards (Total Return, Sharpe, Max Drawdown, Holdings)

#### Overview Tab
- **Portfolio Details Panel**: Name, watchlist, run ID, holdings count, sectors, average score
- **All Holdings Display**: Color-coded pills showing all stocks with scores (green/purple/amber/red)
- **Portfolio Value Chart**: Interactive cumulative returns with AI insight
- **Sector Allocation**: Sunburst chart with nested sector breakdown
- **Score Distribution**: Violin plot showing score spread with AI analysis
- **Top Performers**: Bar chart of highest-scoring stocks
- **Monthly Returns Heatmap**: Year-over-year performance visualization
- **AI Portfolio Summary**: Local analysis + optional Gemini deep analysis

#### Performance Tab
- **Equity Curve**: Cumulative returns with drawdown overlay
- **Daily Returns**: Bar chart showing daily performance
- **Monthly Performance Calendar**: Heat-styled calendar view
- **Return Statistics**: Key metrics (CAGR, Volatility, Sharpe, Sortino, Max DD)

#### Sectors Tab
- **Interactive Treemap**: Sector allocation by weight
- **Radar Chart**: Sector scores comparison
- **Holdings by Sector**: Bar chart with sector breakdown
- **Sector Statistics Table**: Count, weight, average score per sector
- **Top Stocks by Sector**: Cards showing best performers in each sector

#### Risk Tab
- **6 Risk Metric Cards**: VaR, CVaR, Volatility, Beta, Max Drawdown, Sharpe
- **VaR Analysis Chart**: Value at Risk visualization
- **Risk-Return Scatter**: Risk vs return comparison across sectors
- **Gauge Charts**: Visual gauges for Volatility, Sharpe Ratio, Max Drawdown

#### Holdings Tab
- **Score Distribution Histogram**: Distribution of stock scores
- **Lollipop Chart**: Top 10 stocks visualization
- **Interactive Holdings Table**: Sortable, filterable holdings list

#### AI Analysis Tab
- **Portfolio Profiles**: Conservative, Balanced, Aggressive recommendations
- **Holdings Comparison**: Side-by-side view of each profile
- **Overall Assessment**: AI summary of portfolio characteristics

#### Features
- AI-generated insights for each major chart
- Responsive design with collapsible sections
- Dark theme optimized color scheme

### 📊 Analysis Runs

Filter and explore all analysis runs:

- **Filters**: Run type, status, sort order
- **Run Cards**: Detailed info per run
- **Actions**: View details, compare, delete

### 🔍 Stock Explorer

Analyze individual stocks:

1. **Select Run**: Choose analysis run
2. **Search/Filter**: Find stocks by ticker or sector
3. **Stock Details**: Scores, features, metrics
4. **AI Analysis**: Generate stock-specific insights

### 🤖 AI Insights

Generate AI-powered analysis:

- **Executive Summary**: Overall portfolio overview
- **Top Picks**: Detailed stock analysis
- **Sector Analysis**: Sector commentary
- **Risk Assessment**: Warnings and recommendations

### 📈 Compare Runs

Side-by-side comparison of two runs:

- **Metrics Comparison**: Return, Sharpe, drawdown
- **Score Correlation**: How similar are the rankings
- **Holdings Comparison**: Common and unique stocks

### ⚙️ Settings

Configure dashboard behavior:

- Theme settings
- Default parameters
- API configuration

## Features

### Refresh Data

Every page has a 🔄 Refresh button to reload data from database.

The sidebar also has a global "🔄 Refresh Data" button.

### Stage Guards

The Run Analysis page prevents running stages out of order:

- Stage 2 blocked if Stage 1 incomplete
- Stage 3 warns if Stage 2 incomplete
- Stage 4 warns if Stage 3 incomplete

### Run-Specific Folders

Each backtest creates its own folder:
```
output/
└── run_20251231_115520/
    ├── backtest_metrics.json
    ├── backtest_returns.csv
    ├── portfolio_enriched_*.csv
    ├── vertical_candidates_*.csv
    └── commentary_*.md
```

### Live Output

When running scripts, output streams to the dashboard in real-time.

### File Preview

Click the 👁️ button to preview CSV, JSON, or Markdown files directly in the dashboard.

## Risk Analysis (CLI)

After running an analysis, strengthen recommendations with deep risk analysis:

```bash
# Quick analysis (regime, factor, stress)
python scripts/strengthen_recommendations.py --run-dir output/run_xyz/

# Full analysis (adds tail risk, scenarios, correlations, sizing)
python scripts/strengthen_recommendations.py --full --run-dir output/run_xyz/

# With ethical exclusions
python scripts/strengthen_recommendations.py --full \
    --exclude-sectors "Energy,Defense" \
    --exclude-tickers "MO,PM,LMT"
```

### Generated Reports

| File | Content |
|------|---------|
| `strengthening_analysis.json` | Combined analysis results |
| `comprehensive_risk_analysis.json` | Tail risk, drawdown, regimes |
| `stress_test_results.json` | Scenario impacts |
| `conscience_filter_report.json` | Exclusions and ESG flags |

See [Risk Analysis Guide](risk-analysis-guide.md) for full documentation.

## Best Practices

### Workflow

1. Start with **🎮 Run Analysis**
2. Click **Run Complete Analysis Pipeline** for first analysis
3. View results in **💼 Portfolio Analysis**
4. Build custom portfolios in **🎯 Portfolio Builder**
5. **Run risk analysis** via CLI to validate recommendations
6. Compare different runs in **📈 Compare Runs**

### Performance

- Use **Refresh** only when needed (database queries)
- Large files may take time to load in preview
- AI generation may take 10-30 seconds

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No runs showing | Run a backtest first |
| Stage blocked | Complete prerequisite stages |
| AI not working | Check GEMINI_API_KEY in .env |
| Files not appearing | Click Refresh button |
| High "Other" sector % | Run `python scripts/fetch_sector_data.py` |
| Few stocks in analysis | Check watchlist overrides universe.txt |
| Missing price data | Run `python scripts/download_prices.py --watchlist <name>` |
| Duplicate symbols | Custom watchlists auto-deduplicate on creation |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `R` | Rerun app |
| `C` | Clear cache |
| `Esc` | Close modals |

## Related Documentation

- [Run Analysis Pipeline](run-analysis.md)
- [Portfolio Builder](portfolio-builder.md)
- [AI Insights](ai-insights.md)
- [Risk Analysis Guide](risk-analysis-guide.md)