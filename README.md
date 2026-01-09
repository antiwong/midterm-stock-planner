# Mid-term Stock Planner

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
- **Sector Analysis**: Rotation and allocation guidance
- **Risk Assessment**: Automated warning generation
- **Investment Recommendations**: Actionable buy/sell suggestions
- **Portfolio Commentary**: Natural-language explanation of portfolio characteristics

### Interactive Dashboard
- **Analysis Pipeline**: Clear 4-stage workflow with guards and status indicators
- **Portfolio Builder**: Interactive UI for personalized portfolio construction
- **Run Browser**: Filter and explore analysis history
- **Stock Explorer**: Search, filter, and analyze individual stocks
- **AI Insights Tab**: Generate and view AI analysis
- **Run Comparison**: Side-by-side comparison of two runs
- **Reports Browser**: View all generated reports per run
- **Database Management**: SQLite-backed run tracking

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

\`\`\`bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
\`\`\`

### Launch Web Dashboard (Recommended)

\`\`\`bash
# Start interactive dashboard at http://localhost:8501
streamlit run src/app/dashboard.py
\`\`\`

The dashboard provides a complete UI for:
- Running backtests
- Building personalized portfolios
- Viewing analysis results
- Generating AI insights

### Command Line Usage

\`\`\`bash
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
\`\`\`

## Analysis Pipeline

The system follows a 4-stage pipeline:

\`\`\`
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  STAGE 1    │───▶│  STAGE 2    │───▶│  STAGE 3    │───▶│  STAGE 4    │
│  Backtest   │    │  Enrichment │    │  Domain     │    │  AI Analysis│
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
\`\`\`

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

\`\`\`
midterm-stock-planner/
├── config/
│   ├── config.yaml          # Main configuration
│   └── watchlists.yaml      # Stock watchlists
├── data/
│   ├── prices.csv           # Historical price data
│   ├── fundamentals.csv     # Fundamental data
│   ├── benchmark.csv        # Benchmark prices
│   ├── analysis.db          # SQLite database for runs
│   ├── sectors.csv          # Cached sector/industry data
│   ├── sectors.json         # Ticker→Sector mapping
│   └── universe.txt         # Active stock universe
├── docs/                    # Documentation
├── src/
│   ├── analytics/           # Run tracking & reporting
│   │   ├── models.py        # Database models
│   │   ├── manager.py       # Run management API
│   │   └── ai_insights.py   # AI analysis generation
│   ├── analysis/            # Analysis modules
│   │   ├── domain_analysis.py    # Vertical/horizontal analysis
│   │   ├── portfolio_optimizer.py # Personalized portfolios
│   │   └── gemini_commentary.py  # AI commentary
│   ├── app/
│   │   ├── cli.py           # Command-line interface
│   │   └── dashboard.py     # Streamlit web dashboard
│   ├── config/
│   │   └── api_keys.py      # API key management
│   ├── sentiment/           # Sentiment analysis
│   ├── features/            # Feature engineering
│   ├── models/              # Model training/prediction
│   ├── backtest/            # Walk-forward backtest
│   └── risk/                # Risk management
├── scripts/
│   ├── full_analysis_workflow.py  # Complete pipeline
│   ├── run_portfolio_optimizer.py # Build portfolios
│   ├── run_domain_analysis.py     # Domain analysis
│   ├── analyze_portfolio.py       # Portfolio enrichment
│   ├── show_purchase_triggers.py  # Display purchase triggers & selection logic
│   ├── fetch_sector_data.py       # Fetch sectors from yfinance
│   ├── download_prices.py         # Download/validate price data
│   ├── strengthen_recommendations.py # Full risk analysis suite
│   ├── comprehensive_risk_analysis.py # Tail/drawdown/regime analysis
│   ├── stress_testing.py          # Scenario-based stress tests
│   └── conscience_filter.py        # Ethical exclusion filters
└── output/                  # Analysis results
    └── run_{run_id}/        # Per-run output folder
        ├── backtest_*.csv/json
        ├── portfolio_*.csv
        ├── vertical_*.csv
        ├── commentary_*.md
        └── recommendations_*.md
\`\`\`

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

\`\`\`bash
# Quick setup - load default API keys
source scripts/setup_env.sh

# Check API key status
python -m src.config.api_keys
\`\`\`

### Default Keys (Included)

| API | Status | Purpose |
|-----|--------|---------|
| **NewsAPI** | ✅ Configured | Financial news articles (100 req/day) |
| **Gemini** | ✅ Configured | LLM sentiment analysis (free tier) |
| **OpenAI** | ❌ Optional | GPT-based analysis (pay-per-use) |
| **Alpha Vantage** | ❌ Optional | Market data + news (25 req/day) |

### Custom Keys (Optional)

To use your own API keys:

\`\`\`bash
# Option 1: Export in terminal
export NEWS_API_KEY="your_key"
export GEMINI_API_KEY="your_key"

# Option 2: Add to .env file
echo 'GEMINI_API_KEY=your_key' >> .env
\`\`\`

## Configuration

Edit \`config/config.yaml\` to customize:

\`\`\`yaml
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
\`\`\`

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

## Recent Changes (v3.4)

See [CHANGELOG.md](CHANGELOG.md) for full details.

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
- ✅ **Comprehensive Test Suite**: 76 automated tests

**v3.1.0 Highlights (2026-01-02):**
- ✅ **Automatic Sector Classification**: Fetches sector data from Yahoo Finance
- ✅ **Data Validation**: Pre-flight checks before running analysis
- ✅ **Enhanced Portfolio Analysis**: New charts, AI insights per chart

## License

For personal research use only. Not financial advice.
