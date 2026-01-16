# Mid-term Stock Planner
**Version:** 3.10.0


An interpretable stock ranking and backtesting system for mid-term investors (3-month horizon) with monthly rebalancing.

## Features

### Core Analysis
- **Stock Ranking**: Predict 3-month forward excess return vs benchmark using ensemble ML models
- **Factor-Style Features**: Returns, volatility, volume, valuation ratios
- **Technical Indicators**: RSI, MACD, Bollinger Bands, ATR, ADX, OBV
- **Sentiment Analysis**: Multi-source news sentiment with Gemini LLM analysis
- **Walk-Forward Backtesting**: Rolling window training with realistic transaction costs
- **SHAP Explainability**: Per-stock and portfolio-level explanations

### Portfolio Optimizer (NEW)
- **Personalized Portfolios**: Build portfolios based on your risk tolerance and goals
- **Vertical Analysis**: Within-sector stock ranking with quality filters
- **Horizontal Analysis**: Cross-sector portfolio construction with diversification
- **Adjustable Parameters**: Risk tolerance, target return, time horizon, portfolio size
- **Preset Profiles**: Conservative, Moderate, Aggressive presets
- **AI-Powered Recommendations**: Gemini analysis of your personalized portfolio

### Risk Management
- **Risk Parity Allocation**: Equal risk contribution per position
- **Inverse Volatility Weighting**: Lower vol = higher weight
- **Beta Control**: Target specific portfolio beta
- **Sector Constraints**: Cap exposure to volatile sectors (e.g., nuclear, semis)
- **Portfolio Risk Profile**: Beta exposure, concentration metrics, risk warnings
- **Position Constraints**: Max position weight, max sector weight

### Automated Safeguards & Validation (NEW)
- **Portfolio Constraint Validation**: Weights sum to 1.0, position counts match config
- **Risk Profile Bounds**: Conservative/Moderate/Aggressive limits for vol, drawdown, sector concentration
- **Return Sanity Checks**: Catches data corruption and unrealistic metrics
- **Factor Concentration**: Flags if single factor dominates portfolio

### Comprehensive Risk Analysis (NEW)
- **Downside & Tail Risk**: Return percentiles, VaR, CVaR (Expected Shortfall)
- **Drawdown Duration**: Max drawdown, recovery times, underwater periods
- **Scenario Stress Tests**: Tech Crash, Energy Crash, AI Bubble Pop, Rate Spike, etc.
- **Position Diagnostics**: Per-stock volatility, worst outcomes, momentum flags
- **Thematic Dependence**: Theme concentration (Nuclear, Clean Energy, AI)
- **Correlation Clusters**: Identifies "fake diversification"
- **Regime Analysis**: Performance by Bull/Bear × High/Low Volatility
- **Factor Exposure (SHAP-like)**: Quantifies factor contributions
- **Conscience Filters**: Exclude weapons, tobacco, gambling, fossil fuels, etc.
- **Sizing Recommendations**: Capital allocation guidance based on drawdown tolerance

### AI-Powered Insights
- **Executive Summaries**: Gemini-generated analysis overview
- **Top Picks Analysis**: Detailed stock-by-stock explanations
- **Sector Analysis**: Rotation and allocation guidance with accurate sector scores
- **Risk Assessment**: Automated warning generation
- **Investment Recommendations**: Actionable buy/sell suggestions with data quality validation
- **Portfolio Commentary**: Natural-language explanation of portfolio characteristics
- **Historical Tracking**: All AI insights stored in database with deduplication
- **Data Quality Checks**: Automatic validation prevents misleading recommendations from bad data

### Comprehensive Analysis System
- **Performance Attribution**: Decompose returns into factor, sector, stock selection, and timing components
- **Benchmark Comparison**: Compare vs SPY, QQQ with alpha, beta, tracking error, up/down capture
- **Factor Exposure**: Analyze market, size, value, momentum, quality, low vol exposures
- **Rebalancing Analysis**: Analyze drift, turnover, transaction costs, optimal frequency
- **Style Analysis**: Classify growth/value and size characteristics
- **Recommendation Tracking**: Track recommendation performance over time
- **Database Storage**: All analysis results stored permanently for historical comparison

### Advanced Analytics (NEW)
- **Event-Driven Analysis**: Analyze portfolio performance around Fed meetings, earnings announcements, and macro data releases
- **Tax Optimization**: Tax-loss harvesting suggestions, wash sale detection, tax-efficient rebalancing recommendations
- **Monte Carlo Simulation**: Portfolio risk analysis with VaR, CVaR, confidence intervals, and probability metrics
- **Turnover & Churn Analysis**: Detailed turnover metrics, churn rate, holding period analysis, position stability
- **Earnings Calendar**: Portfolio earnings exposure, upcoming earnings tracking, earnings impact analysis
- **Real-Time Monitoring**: Portfolio alerts, daily summaries, performance tracking, benchmark underperformance detection
- **Alert System**: Email/SMS notifications for portfolio changes, drawdown warnings, price alerts (v3.10.0)
- **Custom Report Templates**: User-configurable report generation with multiple formats (v3.10.0)

### Interactive Dashboard
- **Analysis Pipeline**: Clear 4-stage workflow with guards and status indicators
- **Portfolio Builder**: Interactive UI for personalized portfolio construction
- **Comprehensive Analysis**: Performance attribution, benchmark comparison, factor exposure, rebalancing, style analysis
- **Advanced Analytics Pages**: 6 new dedicated pages for event analysis, tax optimization, Monte Carlo, turnover, earnings, and real-time monitoring
- **Alert Management**: Configure and manage portfolio alerts with email/SMS notifications (v3.10.0)
- **Report Templates**: Create custom report templates and generate reports on-demand (v3.10.0)
- **Enhanced UX**: Loading indicators, improved error messages with actionable guidance, keyboard shortcuts
- **Performance Optimizations**: Data caching, database indexes, lazy chart loading, pagination (v3.9.3)
- **Export Capabilities**: CSV, JSON, PDF, Excel export on all major pages (v3.9.3)
- **Run Browser**: Filter and explore analysis history with pagination
- **Stock Explorer**: Search, filter, and analyze individual stocks with pagination
- **AI Insights Tab**: Generate and view AI analysis with data validation
- **Documentation Browser**: Browse and view all project documentation in the GUI
- **Run Comparison**: Side-by-side comparison of two runs
- **Reports Browser**: View all generated reports per run
- **Database Management**: SQLite-backed run tracking with historical analysis storage

### Other Features
- **A/B Testing**: Compare strategies with and without sentiment features
- **Diversified Watchlists**: Tech, Blue-chip, Nuclear/Energy, Clean Energy, ETFs
- **Run-Specific Output**: Each backtest creates its own folder with all outputs

## Tech Stack

- Python 3.11+
- pandas, numpy, scipy
- lightgbm (or xgboost/catboost)
- shap
- streamlit, plotly
- matplotlib, seaborn
- yfinance (data fetching)
- google-generativeai (Gemini LLM)

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

### Launch Web Dashboard (Recommended)

```bash
# Start interactive dashboard at http://localhost:8501
streamlit run src/app/dashboard/app.py
```

The dashboard provides a complete UI for:
- Running backtests
- Building personalized portfolios
- Viewing analysis results
- Generating AI insights

### Deploy Online

The app can be deployed to Streamlit Cloud, Docker, or any cloud platform. See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

**Quick Deploy to Streamlit Cloud:**
1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Set main file: `src/app/dashboard/app.py`
5. Deploy!

### Command Line Usage

```bash
# Run a backtest
python -m src.app.cli run-backtest --config config/config.yaml

# Run with specific watchlist
python -m src.app.cli run-backtest --watchlist everything --name "Full Universe"

# Run with date range (filters training/test data)
python -m src.app.cli run-backtest --watchlist tech_giants --start-date 2015-01-01 --end-date 2023-12-31

# Build personalized portfolio
python scripts/run_portfolio_optimizer.py --profile moderate --with-ai

# Run full analysis workflow
python scripts/full_analysis_workflow.py --with-commentary --with-recommendations

# Run comprehensive analysis (attribution, benchmark, factor, rebalancing, style)
python scripts/run_comprehensive_analysis.py --run-id <run_id>

# Track recommendation performance
python scripts/track_recommendations.py --run-id <run_id>

# Validate a backtest run (safeguards)
python -m src.validation.safeguards output/run_everything_20260102_160327_ --profile moderate

# Strengthen recommendations (regime, factor, stress tests)
python scripts/strengthen_recommendations.py --run-dir output/run_everything_20260102_160327_

# Full risk analysis (tail risk, scenarios, correlations, sizing)
python scripts/strengthen_recommendations.py --full

# With conscience filters (exclude categories)
python scripts/strengthen_recommendations.py --full --exclude-sectors "Energy,Defense"

# Individual risk modules
python scripts/comprehensive_risk_analysis.py --run-dir output/run_everything_20260102_160327_
python scripts/stress_testing.py --run-dir output/run_everything_20260102_160327_
python scripts/conscience_filter.py --exclude-categories "weapons,tobacco,gambling"

# Diagnostic scripts
python scripts/diagnose_backtest_data.py  # Check backtest data issues
python scripts/diagnose_value_quality_scores.py  # Check fundamental data coverage

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_data_completeness.py -v

# Run all tests (comprehensive suite)
python tests/run_tests.py
```

## Analysis Pipeline

The system follows a 4-stage pipeline:

```
Stage 1: Backtest
    ↓
Stage 2: Enrichment
    ↓
Stage 3: Domain Analysis
    ↓
Stage 4: AI Analysis
```


| Stage | Description | Output Files |
|-------|-------------|--------------|
| **1. Backtest** | ML predictions + walk-forward backtest | \`backtest_*.csv/json\` |
| **2. Enrichment** | Add risk metrics, weights, scores | \`portfolio_enriched_*.csv\` |
| **3. Domain Analysis** | Vertical + horizontal portfolio construction | \`vertical_candidates_*.csv\`, \`portfolio_candidates_*.csv\` |
| **4. AI Analysis** | Commentary + recommendations (optional) | \`commentary_*.md\`, \`recommendations_*.md\` |

## Portfolio Builder

Build personalized portfolios with adjustable parameters:

### Risk Parameters
- **Risk Tolerance**: Conservative → Moderate → Aggressive
- **Max Drawdown**: 5% - 40% (maximum acceptable loss)
- **Volatility Preference**: Low → Medium → High

### Return Objectives
- **Target Annual Return**: 5% - 30%
- **Time Horizon**: Short (1-3mo) → Medium (3-12mo) → Long (1-3yr)
- **Holding Period**: 1-36 months

### Portfolio Construction
- **Portfolio Size**: 5-20 stocks
- **Max Position Weight**: 5% - 30% per stock
- **Max Sector Weight**: 15% - 50% per sector
- **Min Quality Score**: Filter threshold

### Preset Profiles

| Profile | Target Return | Max Drawdown | Holdings | Style |
|---------|--------------|--------------|----------|-------|
| **Conservative** | 8% | 10% | 15 stocks | Value |
| **Moderate** | 12% | 15% | 10 stocks | Blend |
| **Aggressive** | 20% | 25% | 8 stocks | Growth |

## Project Structure

```

midterm-stock-planner/
├── config/              # Configuration files
│   ├── config.yaml
│   └── watchlists.yaml
├── data/                # Data files
│   ├── prices.csv
│   ├── fundamentals.csv
│   ├── benchmark.csv
│   ├── analysis.db
│   ├── sectors.csv
│   ├── sectors.json
│   └── universe.txt
├── docs/                # Documentation
├── src/                 # Source code
│   ├── analytics/       # Run tracking & reporting
│   ├── analysis/       # Analysis modules
│   ├── app/            # CLI & dashboard
│   ├── backtest/       # Walk-forward backtest
│   ├── config/         # Configuration management
│   ├── features/       # Feature engineering
│   ├── models/         # Model training/prediction
│   ├── risk/           # Risk management
│   └── sentiment/      # Sentiment analysis
├── scripts/            # Analysis scripts
│   ├── full_analysis_workflow.py
│   ├── run_portfolio_optimizer.py
│   ├── show_purchase_triggers.py
│   ├── download_fundamentals.py
│   ├── strengthen_recommendations.py
│   └── ...
└── output/             # Analysis results
    └── run_{run_id}/   # Per-run output folders
```

## CLI Commands

| Command | Description |
|---------|-------------|
| \`run-backtest\` | Run walk-forward backtest |
| \`run-backtest-ab\` | A/B comparison with/without sentiment |
| \`score-latest\` | Score and rank current universe |
| \`runs list\` | List all analysis runs |
| \`runs show <id>\` | Show run details |
| \`runs compare <id1> <id2>\` | Compare two runs |

### Analysis Scripts

| Script | Description |
|--------|-------------|
| \`full_analysis_workflow.py\` | Run complete pipeline (all stages) |
| \`run_portfolio_optimizer.py\` | Build personalized portfolio |
| \`run_domain_analysis.py\` | Vertical + horizontal analysis |
| \`analyze_portfolio.py\` | Portfolio enrichment only |
| \`show_purchase_triggers.py\` | Display purchase triggers & selection logic |
| \`improve_purchase_triggers.py\` | Apply AI recommendations to improve selection |
| \`download_fundamentals.py\` | Download comprehensive fundamentals (PE, PB, ROE, margins) |
| \`fetch_sector_data.py\` | Fetch/update sector classifications |
| \`download_prices.py\` | Download and validate price data |

### Risk Analysis Scripts

| Script | Description |
|--------|-------------|
| \`strengthen_recommendations.py\` | All-in-one risk analysis (use \`--full\` for extended) |
| \`comprehensive_risk_analysis.py\` | Tail risk, drawdown duration, regime analysis |
| \`stress_testing.py\` | Scenario-based stress tests (7 predefined scenarios) |
| \`conscience_filter.py\` | Apply ethical/conscience-based exclusions |

### Diagnostic Scripts

| Script | Description |
|--------|-------------|
| \`diagnose_backtest_data.py\` | Diagnose backtest data issues (date ranges, window sizes) |
| \`diagnose_value_quality_scores.py\` | Diagnose fundamental data coverage and score differentiation |
| \`analyze_filter_effectiveness.py\` | Analyze filter effectiveness and optimization |

### Common Flags

- \`--config, -c\` - Path to configuration file
- \`--run-id\` - Specific run ID to analyze
- \`--output, -o\` - Output directory
- \`--use-sentiment\` - Enable sentiment features
- \`--with-commentary\` - Generate AI commentary
- \`--with-recommendations\` - Generate AI recommendations
- \`--profile\` - Investor profile (conservative/moderate/aggressive)

## API Keys Setup

API keys are **pre-configured** with working defaults. To verify or customize:

```bash
# Quick setup - load default API keys
source scripts/setup_env.sh

# Check API key status
python -m src.config.api_keys
```

### Default Keys (Included)

| API | Status | Purpose |
|-----|--------|---------|
| **NewsAPI** | ✅ Configured | Financial news articles (100 req/day) |
| **Gemini** | ✅ Configured | LLM sentiment analysis (free tier) |
| **OpenAI** | ❌ Optional | GPT-based analysis (pay-per-use) |
| **Alpha Vantage** | ❌ Optional | Market data + news (25 req/day) |

### Custom Keys (Optional)

To use your own API keys:

```bash
# Option 1: Export in terminal
export NEWS_API_KEY="your_key"
export GEMINI_API_KEY="your_key"

# Option 2: Add to .env file
echo 'GEMINI_API_KEY=your_key' >> .env
```

## Configuration

Edit \`config/config.yaml\` to customize:

```yaml
features:
  use_sentiment: true
  sentiment_lookbacks: [1, 7, 14]

backtest:
  train_years: 5.0
  test_years: 1.0
  rebalance_freq: "MS"
  transaction_cost: 0.001

analysis:
  weights:
    model_score: 0.5
    value_score: 0.3
    quality_score: 0.2
  filters:
    min_roe: 0.0
    max_debt_to_equity: 2.0
  horizontal:
    portfolio_size: 10
    max_position_weight: 0.15
    max_sector_weight: 0.35
```

## Testing

The project includes a comprehensive test suite with **208+ automated test cases** covering all major components.

### Test Coverage

- **Data Completeness Validation** - Tests for all data requirement checks and edge cases
- **Data Loading** - Tests for loading from multiple file formats and redundant sources
- **Comprehensive Analysis** - Tests for the complete analysis runner and all modules
- **Analysis Modules** - Individual tests for Performance Attribution, Factor Exposure, Rebalancing, Style Analysis
- **Export Functionality** - Tests for PDF and Excel export
- **Enhanced Visualizations** - Tests for all chart types
- **Integration Tests** - End-to-end pipeline tests
- **Advanced Analytics** (NEW) - 57 comprehensive tests for all 6 advanced analytics modules:
  - Event-Driven Analysis (10 tests)
  - Tax Optimization (9 tests)
  - Monte Carlo Simulation (10 tests)
  - Turnover & Churn Analysis (10 tests)
  - Earnings Calendar Integration (6 tests)
  - Real-Time Monitoring (10 tests)
  - Integration tests (2 tests)

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_data_completeness.py -v

# Run specific test class
pytest tests/test_data_completeness.py::TestDataCompletenessChecker -v

# Run only failed tests
pytest tests/ --lf
```

### Test Documentation

- [Test Suite Documentation](docs/test-suite-documentation.md) - Comprehensive test documentation (8 test files, 208+ tests)
- [Test Results Summary](docs/test-results-summary.md) - Test execution results and validation
- [Test Execution Results](docs/test-execution-results.md) - Latest test run results (100% pass rate)

### Test Status

- **Current Pass Rate:** 100% (205/205 tests passing, 3 skipped) ✅
- **New Comprehensive Suite:** ✅ 131/131 tests passing
  - Core tests: 74/74 ✅
  - Advanced Analytics: 57/57 ✅
- **Older Test Files:** ✅ 75/78 tests passing (3 skipped - database tests)
- **Coverage:** All major components tested including all 6 advanced analytics modules
- **Status:** ✅ Ready for continuous integration

## Documentation

### Core Documentation
- [Design Overview](docs/design.md) - System architecture
- [Sentiment Module](docs/sentiment.md) - News sentiment analysis
- [Backtesting](docs/backtesting.md) - Walk-forward backtest details
- [Risk Management](docs/risk-management.md) - Position sizing and risk metrics

### Feature Documentation
- [Portfolio Builder](docs/portfolio-builder.md) - Personalized portfolio construction
- [AI Insights](docs/ai-insights.md) - Gemini-powered analysis
- [Dashboard](docs/dashboard.md) - Streamlit web interface
- [Domain Analysis](docs/domain-analysis.md) - Vertical and horizontal analysis
- [Analytics Database](docs/analytics-database.md) - SQLite schema

### Risk Analysis (NEW)
- [Risk Analysis Guide](docs/risk-analysis-guide.md) - Complete guide to all risk tools
  - Tail risk & VaR analysis
  - Drawdown duration analysis  
  - Scenario stress testing
  - Position-level diagnostics
  - Thematic/correlation analysis
  - Conscience filters
  - Sizing recommendations

## Recent Changes

See [CHANGELOG.md](CHANGELOG.md) for full details.

**v3.9.2 Highlights (2026-01-16):**
- ✅ **Sector Score Display Fix**: Fixed critical bug where all sectors showed 0.000 in AI insights - now correctly displays actual sector scores
- ✅ **Factor Risk Contribution**: Fixed unrealistic momentum risk contribution (114,390%) - now shows realistic values (0-50%)
- ✅ **Data Serialization**: Fixed Timestamp key errors in tax optimization and turnover analysis
- ✅ **Style Analysis**: Fixed dict.columns error when loading stock features
- ✅ **Benchmark Comparison**: Fixed timezone mismatch errors with SPY and QQQ
- ✅ **Fundamental Data Integration**: Enhanced data loader to automatically merge PE, PB, ROE from fundamentals.csv
- ✅ **AI Insights Button**: Restored generate button in comprehensive analysis page (always visible)

**v3.5.0 Highlights (2026-01-09):**
- ✅ **Data Validation for AI Insights**: Automatic validation before generating AI recommendations
- ✅ **Documentation Browser in GUI**: Browse and view all documentation directly in the dashboard
- ✅ **Enhanced AI Prompts**: AI refuses misleading recommendations when data quality issues detected
- ✅ **Interactive Markdown Links**: Relative links in documentation work as clickable navigation
- ✅ **Sector Score Detection**: Automatic detection and warning for identical sector scores (0.000 issue)
- ✅ **Improved Dashboard Navigation**: Reorganized sidebar with logical grouping (Main Workflow, Tools, Utilities)
- ✅ **Better Visual Design**: Dark button backgrounds, section headers, and proper selection state management

**v3.4.0 Highlights (2026-01-02):**
- ✅ **Enhanced Backtest Error Diagnostics**: Detailed error messages with actionable recommendations
- ✅ **Backtest Data Diagnostic Script**: Pre-flight checks for data availability and window sizes
- ✅ **Improved Window Tracking**: All skipped windows logged with specific reasons

**v3.3.0 Highlights (2026-01-02):**
- ✅ **Comprehensive Risk Analysis**: Tail risk, VaR, CVaR, drawdown duration
- ✅ **Stress Testing Module**: 7 scenario-based stress tests (Tech Crash, AI Bubble Pop, etc.)
- ✅ **Conscience Filters**: Exclude weapons, tobacco, gambling, fossil fuels, etc.
- ✅ **Thematic Analysis**: Theme concentration and correlation cluster detection
- ✅ **Position Diagnostics**: Per-stock risk flags and momentum tracking
- ✅ **Sizing Recommendations**: Capital allocation guidance based on drawdown tolerance

**v3.2.0 Highlights (2026-01-02):**
- ✅ **Automated Safeguards**: Portfolio constraints, risk bounds, factor concentration
- ✅ **Backtest Date Range**: \`--start-date\` and \`--end-date\` CLI arguments
- ✅ **Extended Benchmark**: Data through 2025-12-31 (5 walk-forward windows)
- ✅ **Comprehensive Test Suite**: 100+ automated tests covering all major components

**v3.1.0 Highlights (2026-01-02):**
- ✅ **Automatic Sector Classification**: Fetches sector data from Yahoo Finance
- ✅ **Data Validation**: Pre-flight checks before running analysis
- ✅ **Enhanced Portfolio Analysis**: New charts, AI insights per chart

## License

For personal research use only. Not financial advice.
