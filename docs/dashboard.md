# Dashboard Guide

The Streamlit dashboard provides a comprehensive web interface for running analyses, building portfolios, and viewing results.

## Launching the Dashboard

```bash
streamlit run src/app/dashboard.py
```

Access at: http://localhost:8501

## Navigation

The sidebar provides navigation organized into logical groups with visual section headers:

### Main Workflow (Sequential)
These pages follow the typical analysis workflow, displayed in order:

| Page | Description |
|------|-------------|
| 🏠 **Overview** | Summary metrics and recent runs |
| 🎮 **Run Analysis** | 4-stage analysis pipeline |
| 🎯 **Portfolio Builder** | Personalized portfolio construction |
| 📄 **Reports** | Browse generated reports |
| 💼 **Portfolio Analysis** | Detailed portfolio view |
| 📊 **Comprehensive Analysis** | Performance attribution, benchmark comparison, factor exposure, rebalancing, style analysis |
| 🔍 **Purchase Triggers** | Purchase triggers and selection logic |
| 📊 **Analysis Runs** | Filter and explore runs |
| 🤖 **AI Insights** | Generate AI commentary |

### Tools (Standalone)
Independent tools for specific tasks:

| Page | Description |
|------|-------------|
| 📋 **Watchlist Manager** | Create and manage watchlists |
| 🔎 **Stock Explorer** | Individual stock analysis |
| 📈 **Compare Runs** | Side-by-side comparison of two runs |
| 🔀 **Advanced Comparison** | Multiple runs, time periods, factor weights comparison |

### Advanced Analytics (NEW)
Advanced analysis modules with dedicated pages:

| Page | Description |
|------|-------------|
| 📅 **Event Analysis** | Analyze portfolio performance around Fed meetings, earnings, macro data |
| 💰 **Tax Optimization** | Tax-loss harvesting, wash sale detection, tax-efficient rebalancing |
| 🎲 **Monte Carlo** | Portfolio risk simulation, VaR, CVaR, confidence intervals |
| 🔄 **Turnover Analysis** | Portfolio turnover, churn rate, holding periods, position stability |
| 📅 **Earnings Calendar** | Earnings exposure, upcoming earnings, earnings impact analysis |
| ⚡ **Real-Time Monitoring** | Portfolio alerts, daily summaries, performance tracking |

### Utilities
System utilities and configuration:

| Page | Description |
|------|-------------|
| 📚 **Documentation** | Browse project documentation |
| ⚙️ **Settings** | Configuration options |

**Navigation Features:**
- Visual section headers for each group
- Horizontal dividers between sections
- Button-based navigation with clear selection state
- Only one item can be selected at a time across all groups
- Selected items highlighted with primary button style
- Dark button backgrounds for better text visibility

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

### 📊 Comprehensive Analysis

Deep dive into portfolio performance with comprehensive analysis modules:

#### Features
- **Run All Analyses**: One-click button to run all analysis modules for a selected run
- **Data Loading**: Automatically loads portfolio data from run output files
- **Database Storage**: All analysis results saved to database for historical tracking
- **Tabbed Interface**: Separate tabs for each analysis type

#### Analysis Modules

**1. Performance Attribution Tab**
- Decomposes portfolio returns into components:
  - Factor attribution (value, growth, quality, momentum)
  - Sector attribution (which sectors added/subtracted value)
  - Stock selection attribution (did we pick the right stocks?)
  - Timing attribution (did rebalancing help or hurt?)
- Summary metrics for each attribution component
- Detailed breakdown charts and tables

**2. Benchmark Comparison Tab**
- Compares portfolio vs benchmarks (SPY, QQQ, sector ETFs)
- Metrics displayed:
  - Alpha (excess return)
  - Beta (market sensitivity)
  - Information ratio
  - Tracking error
  - Up/Down capture ratios
- Side-by-side comparison of portfolio vs benchmark metrics

**3. Factor Exposure Tab**
- Analyzes portfolio factor loadings:
  - Market (beta)
  - Size (small vs large cap)
  - Value (cheap vs expensive)
  - Momentum
  - Quality
  - Low volatility
- Factor exposure chart (positive/negative exposures)
- Factor contribution to return and risk

**4. Rebalancing Analysis Tab**
- Analyzes portfolio drift from target weights
- Metrics:
  - Current drift
  - Average turnover
  - Total transaction costs
  - Number of rebalancing events
- Drift over time chart
- Rebalancing recommendations (when to rebalance)

**5. Style Analysis Tab**
- Classifies portfolio style:
  - Growth vs Value (based on PE ratios)
  - Large vs Small cap (based on market cap)
- Portfolio PE vs market average
- Market cap classification
- Overall style summary

**6. AI Insights Tab**
- Displays all AI-generated insights for the run
- Grouped by insight type (executive summary, sector analysis, etc.)
- Shows generation timestamp
- Links to full AI Insights page

**7. Recommendations Tab**
- Displays all investment recommendations for the run
- Grouped by action (BUY, SELL, HOLD)
- Shows:
  - Ticker, date, reason, confidence
  - Target price, stop loss
  - Actual return (if tracked)
  - Whether target/stop-loss was hit

#### Usage

1. **Select Run**: Choose an analysis run from the dropdown
2. **Run Analysis**: Click "🔄 Run All Analyses" to generate all analysis modules
3. **View Results**: Navigate through tabs to see different analysis types
4. **Export**: Export results (coming soon)

#### Data Requirements

- **Portfolio Returns**: Required for attribution and benchmark comparison
- **Portfolio Weights**: Required for rebalancing and style analysis
- **Stock Features**: Required for factor exposure and style analysis
- **Stock Returns**: Optional, enhances attribution analysis

If data is missing, the analysis will show an error message indicating what's needed.

See [Comprehensive Analysis System Documentation](comprehensive-analysis-system.md) for details.

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

Generate AI-powered analysis with automatic data quality validation:

- **Data Validation**: Automatic checks before generating insights
  - Validates data completeness, score distribution, sector differentiation
  - Blocks generation if critical errors detected (with override option)
  - Shows warnings for data quality concerns
  
- **Generated Content**:
  - **Executive Summary**: Overall portfolio overview
  - **Top Picks**: Detailed stock analysis
  - **Sector Analysis**: Sector commentary (only if data is valid)
  - **Risk Assessment**: Warnings and recommendations
  
- **Data Quality Protection**: AI refuses to provide recommendations when data quality issues are detected (e.g., all sectors have 0.000 scores)

See [AI Insights Documentation](ai-insights.md) and [Data Validation Guide](data-validation.md) for details.

### 📚 Documentation

Browse and view all project documentation directly in the GUI:

- **Document Browser**: View all markdown files from the `docs/` folder
- **Category Navigation**: Documents organized by category (Getting Started, Configuration, Analysis, etc.)
- **Interactive Links**: Relative markdown links (e.g., `[design.md](design.md)`) are converted to clickable navigation
- **Document Selector**: Dropdown to quickly find and switch between documents
- **Download**: Download any document as a markdown file

Features:
- Automatic title extraction from markdown files
- Category-based organization
- Clickable document links within the GUI
- Full markdown rendering support

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