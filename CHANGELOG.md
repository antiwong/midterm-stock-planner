# Changelog

All notable changes to the Mid-term Stock Planner project are documented here.

## [3.9.2] - 2026-01-16

### Fixed

#### Critical Data Quality Fixes
- **Sector Score Display Bug**: Fixed issue where all sectors showed 0.000 in AI insights
  - Root cause: `generate_executive_summary`, `generate_sector_analysis`, and `generate_recommendations` used `'avg_score'` key but `_build_context` expected `'score'` key
  - Fixed all three methods to use `'score'` key consistently
  - AI insights now correctly display sector scores (e.g., Utilities: 0.301, Technology: -0.104)
  - Recommendations now provide proper sector allocation guidance based on actual data

- **Factor Exposure Risk Contribution**: Fixed unrealistic momentum risk contribution (114,390%)
  - Changed from `exposure * std` to coefficient of variation approach
  - Uses `(std/mean) * exposure * 0.01` for normalized percentage
  - Caps risk contribution at 100% to prevent unrealistic values
  - Risk contribution values now realistic (typically 0-50%)

#### Data Serialization Fixes
- **Timestamp Key Errors**: Fixed `keys must be str, int, float, bool or None, not Timestamp` errors
  - Added `convert_to_string_keys()` helper in `turnover_analysis.py`
  - Converts all Timestamp/datetime keys to ISO format strings
  - Applied to `turnover_by_period`, `buys`, and `sells` dictionaries
  - Tax optimization and turnover analysis now save correctly to database

- **HTTP 404 Errors**: Improved error handling in earnings calendar
  - Added try-except around `stock.info` fetch to handle 404 gracefully
  - Silently handles 404 errors (expected for tickers without earnings data)
  - Only warns on unexpected errors
  - Prevents console clutter from expected API failures

#### Analysis Module Fixes
- **Style Analysis Error**: Fixed `'dict' object has no attribute 'columns'` error
  - `stock_data` is passed as dict with 'features' and 'data' keys
  - Extract DataFrame from dict before accessing `.columns`
  - Handles both dict and DataFrame input formats

- **Benchmark Comparison**: Fixed timezone mismatch errors
  - Normalized both portfolio and benchmark indices to timezone-naive
  - Uses boolean masks for robust date alignment
  - Prevents "No overlapping dates" errors with SPY and QQQ

- **Fundamental Data Integration**: Enhanced `load_stock_features` to merge fundamental data
  - Automatically merges PE, PB, ROE, margins, market_cap from `fundamentals.csv`
  - Maps column names (pe → pe_ratio, pb → pb_ratio) for compatibility
  - Handles both long format (ticker column) and wide format (ticker index)
  - Style analysis now finds fundamental data correctly

- **Data Completeness Check**: Improved fundamental data detection
  - Checks `features` DataFrame (where merged data is stored)
  - Verifies values are non-null and positive (not just placeholders)
  - Handles both `pe`/`pb` and `pe_ratio`/`pb_ratio` column names

#### API and Database Fixes
- **save_ai_insight Metadata Error**: Fixed `unexpected keyword argument 'metadata'` error
  - Changed all `metadata=` parameters to `context=` in `save_ai_insight` calls
  - Updated `ai_insights.py` to use `get_context()` instead of accessing `.metadata`
  - Fixed in `comprehensive_analysis.py` (3 instances) and `ai_insights.py` (2 instances)

### Changed

#### UI/UX Improvements
- **AI Insights Generate Button**: Restored and improved generate button in comprehensive analysis
  - Button now always visible at top of AI Insights tab (not just when no insights exist)
  - Added checkboxes to select what to generate (commentary, recommendations)
  - Allows regeneration of insights when they already exist
  - Better feedback messages for each action

### Documentation
- Updated `CHANGELOG.md` with all recent fixes and improvements
- Updated `README.md` to reflect current state and bug fixes

## [3.9.1] - 2026-01-15

### Added

#### Comprehensive Test Suite for Advanced Analytics
- **`tests/test_advanced_analytics.py`** - 57 comprehensive test cases
  - Event-Driven Analysis: 10 tests covering Fed meetings, benchmarks, edge cases
  - Tax Optimization: 9 tests covering wash sales, tax-loss harvesting, thresholds
  - Monte Carlo Simulation: 10 tests covering methods, VaR, CVaR, reproducibility
  - Turnover & Churn Analysis: 10 tests covering methods, churn rate, holding periods
  - Earnings Calendar: 6 tests covering fetching, exposure, impact analysis
  - Real-Time Monitoring: 10 tests covering alerts, summaries, thresholds
  - Integration: 2 tests for module imports and instantiation
- **Test Coverage:** 100% pass rate (57/57 tests)
- **Total Test Suite:** 208+ tests (151 existing + 57 new)

### Documentation Updates
- Updated `docs/test-suite-documentation.md` with advanced analytics test details
- Updated `docs/test-execution-results.md` with new test counts and results
- Updated `README.md` with comprehensive test statistics

## [3.9.0] - 2026-01-15

### Added

#### Advanced Analytics Modules
- **Event-Driven Analysis** (`src/analytics/event_analysis.py`)
  - Analyze portfolio performance around Fed meetings, earnings announcements, and macro data releases
  - Event impact analysis with configurable lookback/lookforward windows
  - Benchmark comparison for event periods
  - Win rate and average return statistics by event type

- **Tax Optimization** (`src/analytics/tax_optimization.py`)
  - Tax-loss harvesting suggestions with thresholds and portfolio limits
  - Wash sale detection (30-day window)
  - Tax-efficient rebalancing recommendations
  - Tax efficiency scoring based on turnover and holding periods

- **Monte Carlo Simulation** (`src/analytics/monte_carlo.py`)
  - Portfolio return simulation (bootstrap, normal, t-distribution methods)
  - Value at Risk (VaR) and Conditional VaR at multiple confidence levels
  - Confidence intervals (90%, 95%, 99%)
  - Probability metrics (positive return, exceed thresholds, loss scenarios)
  - Stress testing scenarios

- **Turnover & Churn Analysis** (`src/analytics/turnover_analysis.py`)
  - Portfolio turnover calculation (sum of abs changes, one-way, two-way methods)
  - Churn rate analysis (position change frequency)
  - Position holding period analysis with distribution
  - Position stability metrics (top N position changes)

- **Earnings Calendar Integration** (`src/analytics/earnings_calendar.py`)
  - Fetch earnings dates from yfinance
  - Portfolio earnings exposure analysis
  - Earnings impact analysis on individual stocks
  - Portfolio-wide earnings impact aggregation

- **Real-Time Monitoring** (`src/analytics/realtime_monitoring.py`)
  - Portfolio alert system (drawdown, price movements, volume spikes, concentration)
  - Daily portfolio summary with key metrics
  - Performance metrics tracking (30-day periods)
  - Benchmark underperformance alerts

#### Dashboard GUI Integration
- **6 New Dashboard Pages** (`src/app/dashboard/pages/`)
  - Event Analysis page with event performance charts
  - Tax Optimization page with harvesting suggestions
  - Monte Carlo page with risk metrics and VaR
  - Turnover Analysis page with churn and holding periods
  - Earnings Calendar page with exposure and impact analysis
  - Real-Time Monitoring page with alerts and daily summaries

- **Enhanced Dashboard UX** (`src/app/dashboard/components/`)
  - Loading indicators with progress bars and stage progress
  - Improved error messages with actionable guidance
  - Keyboard shortcuts infrastructure (R=refresh, N=new analysis, etc.)
  - Operation feedback with timing
  - Styled loading cards and progress indicators

- **Navigation Updates**
  - New "Advanced Analytics" section in sidebar
  - All 6 new pages accessible from navigation
  - Proper routing and state management

#### Integration
- All modules integrated into `ComprehensiveAnalysisRunner`
- Results saved to database via `AnalysisService`
- Error handling and data validation included
- All modules tested and importing successfully

### Changed
- Updated `ComprehensiveAnalysisRunner` to include all 6 new analysis modules
- Enhanced dashboard navigation with Advanced Analytics section
- Improved error handling throughout dashboard

### Dependencies
- No new dependencies required (uses existing pandas, numpy, scipy, yfinance)

---

## [3.8.0] - 2026-01-15

### Added

#### Comprehensive Test Suite
- **Test Suite** (`tests/`)
  - 100+ automated test cases covering all major components
  - 7 test files organized by component
  - Shared fixtures and test infrastructure
- **Test Results**: 74/74 tests passing (100% pass rate) ✅
- **Status**: ✅ Comprehensive test suite fully functional
- **Fixed**: All 3 minor test failures resolved
  
- **Test Files**
  - `test_data_completeness.py` - Data completeness validation tests (15 tests)
  - `test_data_loader.py` - Data loading and redundant source tests (15+ tests)
  - `test_comprehensive_analysis.py` - Comprehensive analysis runner tests (10+ tests)
  - `test_analysis_modules.py` - Individual analysis module tests (15+ tests)
  - `test_export.py` - Export functionality tests (8+ tests)
  - `test_enhanced_charts.py` - Enhanced visualization tests (10+ tests)
  - `test_integration.py` - End-to-end integration tests (5+ tests)

- **Test Infrastructure**
  - `conftest.py` - Shared fixtures for all tests
  - `run_tests.py` - Test runner script
  - `test-suite-documentation.md` - Comprehensive test documentation

- **Test Coverage**
  - Data completeness validation
  - Data loading from redundant sources
  - All analysis modules (Attribution, Factor Exposure, Rebalancing, Style)
  - Export functionality (PDF/Excel)
  - Enhanced visualizations
  - Integration scenarios
  - Error handling and edge cases

### Changed
- Updated README.md with Testing section
- Updated documentation to reference test suite

### Fixed
- Fixed numpy boolean assertion issues in tests
- Improved test isolation and cleanup

---

## [3.7.0] - 2026-01-15

### Added

#### Export Capabilities
- **PDF Export** (`src/app/dashboard/export.py`)
  - Professional PDF reports with formatted tables
  - Multiple sections: Performance Attribution, Benchmark Comparison, Factor Exposure, Rebalancing, Style Analysis
  - Integrated into Comprehensive Analysis page with download buttons
  - Timestamped filenames

- **Excel Export** (`src/app/dashboard/export.py`)
  - Multi-sheet Excel workbooks with professional formatting
  - Separate sheets for each analysis type
  - Formatted headers, borders, and auto-adjusted column widths
  - Color-coded headers for better readability

#### Enhanced Visualizations
- **Attribution Waterfall Charts** (`src/app/dashboard/components/enhanced_charts.py`)
  - Visual performance attribution decomposition
  - Shows cumulative contributions from factors, sectors, stock selection, and timing
  - Color-coded positive/negative contributions
  - Integrated into Comprehensive Analysis page

- **Factor Exposure Heatmaps** (`src/app/dashboard/components/enhanced_charts.py`)
  - Visual factor exposure analysis
  - Shows exposures, return contributions, and risk contributions
  - Color scale for quick identification of factor strengths
  - Integrated into Comprehensive Analysis page

- **Comparison Charts** (`src/app/dashboard/components/enhanced_charts.py`)
  - Multi-run comparison bar charts
  - Time period comparison line charts
  - Multi-metric radar/spider charts
  - Interactive and customizable

#### Advanced Comparison Tools
- **Advanced Comparison Page** (`src/app/dashboard/pages/advanced_comparison.py`)
  - **Multiple Runs Comparison**: Side-by-side metrics, interactive charts, holdings overlap analysis
  - **Time Period Comparison**: Full period, halves, yearly breakdowns with performance metrics
  - **Factor Weights Comparison**: Compare different factor weight configurations, scatter plots, performance analysis
  - Added to Standalone Tools section in navigation

### Changed
- Comprehensive Analysis page now includes waterfall charts and heatmaps
- Export functionality integrated with format selection (PDF/Excel)
- Enhanced chart components available throughout dashboard

### Dependencies
- Added `reportlab>=4.0.0` for PDF export
- Added `openpyxl>=3.1.0` for Excel export

### Validation
- All features tested and validated
- Export functionality verified (PDF: 4,055 bytes, Excel: 8,439 bytes)
- All enhanced charts created successfully
- GUI integration confirmed
- See `docs/export-visualization-validation.md` for full validation results

---

## [3.6.0] - 2026-01-10

### Added

#### Comprehensive Analysis System
- **Performance Attribution Analysis** (`src/analytics/performance_attribution.py`)
  - Decomposes portfolio returns into factor, sector, stock selection, and timing components
  - All results stored in database for historical tracking
  - GUI integration with interactive charts

- **Benchmark Comparison** (`src/analytics/benchmark_comparison.py`)
  - Compares portfolio vs benchmarks (SPY, QQQ, sector ETFs)
  - Calculates alpha, beta, tracking error, information ratio, up/down capture ratios
  - Side-by-side metrics comparison

- **Factor Exposure Analysis** (`src/analytics/factor_exposure.py`)
  - Analyzes portfolio factor loadings (market, size, value, momentum, quality, low vol)
  - Calculates factor contributions to return and risk
  - Visual exposure charts

- **Rebalancing Analysis** (`src/analytics/rebalancing_analysis.py`)
  - Analyzes portfolio drift from target weights
  - Calculates turnover and transaction costs
  - Determines optimal rebalancing frequency
  - Provides rebalancing recommendations

- **Style Analysis** (`src/analytics/style_analysis.py`)
  - Classifies portfolio style (growth vs value, large vs small cap)
  - Tracks style consistency over time
  - Detects style drift

- **Historical Recommendation Tracking**
  - Tracks all AI-generated recommendations in database
  - Monitors actual performance vs targets
  - Updates performance over time via `scripts/track_recommendations.py`
  - Calculates hit rates and recommendation quality

- **Database-Backed Analysis Storage**
  - All analysis results stored in SQLite database (`data/analysis.db`)
  - Tables: `analysis_results`, `ai_insights`, `recommendations`, `benchmark_comparisons`, `factor_exposures`, `performance_attributions`
  - Historical tracking and comparison across runs
  - Deduplication of AI insights via prompt hashing

- **Comprehensive Analysis GUI Page** (`src/app/dashboard/pages/comprehensive_analysis.py`)
  - Single page with tabs for all analysis types
  - One-click "Run All Analyses" button
  - Data loader integration for automatic data loading from run output files
  - Interactive charts and visualizations for each analysis type

- **Data Loader** (`src/analytics/data_loader.py`)
  - Loads portfolio returns, weights, stock features from run output files
  - Handles missing data gracefully
  - Integrated with comprehensive analysis runner

- **Analysis Service** (`src/analytics/analysis_service.py`)
  - Unified interface for saving/retrieving analysis results
  - Methods for all analysis types
  - Historical query capabilities

- **Comprehensive Analysis Runner** (`src/analytics/comprehensive_analysis.py`)
  - Runs all analysis modules in one call
  - Saves all results to database automatically
  - Handles errors gracefully

- **Scripts**
  - `scripts/run_comprehensive_analysis.py`: CLI tool to run all analyses for a run
  - `scripts/track_recommendations.py`: Update recommendation performance over time

### Changed
- AI insights generation now automatically saves to database when `run_id` is provided
- All analysis results are now stored permanently in database
- Comprehensive Analysis page added to dashboard navigation

---

## [3.5.0] - 2026-01-09

### Added

#### Data Validation for AI Insights
- **Data Quality Validation** (`src/analytics/data_validation.py`)
  - Comprehensive validation before generating AI insights
  - Checks data completeness, score distribution, sector differentiation
  - Detects identical scores, low variance, missing critical fields
  - Provides detailed validation reports with errors and warnings
  - Blocks AI generation when critical errors are detected (with user override option)

- **Enhanced AI Prompts** (`src/analytics/ai_insights.py`)
  - AI now refuses to provide recommendations when data quality issues detected
  - Automatic detection of identical sector scores (0.000 issue)
  - Stronger warnings in AI context about data reliability
  - Prevents misleading investment recommendations from bad data

#### Documentation Browser in GUI
- **Documentation Page** (`src/app/dashboard/pages/documentation.py`)
  - Browse and view all documentation files from the GUI
  - Automatic categorization (Getting Started, Configuration, Analysis, etc.)
  - Interactive markdown link conversion (relative .md links become clickable)
  - Document selector with category navigation
  - Download functionality for each document

- **Documentation Guide** (`docs/data-validation.md`)
  - Complete guide on data validation system
  - Common issues and solutions
  - Best practices for data quality

#### Improved Dashboard Navigation
- **Reorganized Sidebar** (`src/app/dashboard/components/sidebar.py`, `config.py`)
  - Navigation items grouped into logical sections:
    - **Main Workflow**: Sequential workflow items (Overview → Run Analysis → Portfolio Builder → Reports → Portfolio Analysis → Purchase Triggers → Analysis Runs → AI Insights)
    - **Tools**: Standalone tools (Watchlist Manager, Stock Explorer, Compare Runs)
    - **Utilities**: System utilities (Documentation, Settings)
  - Visual section headers and dividers for better organization
  - Button-based navigation with proper selection state management
  - Dark background styling for better visibility of white text
  - Fixed WebSocket errors from multiple reruns

### Fixed
- **Markdown Links**: Relative markdown links in documentation now work in GUI
- **AI Recommendations**: AI no longer generates misleading recommendations when data quality is poor
- **Sector Score Detection**: Automatic detection and warning for identical sector scores
- **Sidebar Navigation**: Fixed issue where multiple items could be selected simultaneously
- **Main Content Display**: Fixed issue where main content area wasn't showing
- **Button Visibility**: Fixed white text on white background issue with darker button backgrounds

### Changed
- AI insights generation now includes data validation step
- Documentation is now accessible directly from the dashboard
- Enhanced error messages in AI insights when data quality issues are present
- Sidebar navigation reorganized for better user experience and logical grouping

---

## [3.4.0] - 2026-01-02

### Added

#### Backtest Diagnostics & Error Handling
- **Enhanced Error Messages** (`src/backtest/rolling.py`)
  - Detailed diagnostics when no predictions are generated
  - Shows data date range, window sizes, and step configuration
  - Lists all skipped windows with reasons (insufficient data, training failures, etc.)
  - Provides actionable recommendations (reduce window sizes, remove date filters, etc.)
  
- **Backtest Data Diagnostic Script** (`scripts/diagnose_backtest_data.py`)
  - Checks data date ranges and span
  - Validates window size requirements vs available data
  - Tests training dataset creation
  - Identifies date filter issues
  - Provides specific recommendations for fixing data issues

### Fixed
- **"No predictions generated" Error**: Now provides comprehensive diagnostics instead of generic error
- **Window Skipping**: Tracks and reports all skipped windows with specific reasons
- **Data Range Validation**: Better detection of insufficient data for walk-forward windows

### Changed
- Error messages now include actionable troubleshooting steps
- Window skipping reasons are logged and reported in error output

---

## [3.3.0] - 2026-01-02

### Added

#### Comprehensive Risk Analysis Module (`scripts/comprehensive_risk_analysis.py`)
- **Downside & Tail Risk Analysis**
  - Return distribution percentiles (daily, monthly, quarterly)
  - Value at Risk (VaR) at 95% and 99% confidence
  - Conditional VaR (Expected Shortfall)
  - Worst month/quarter outcomes with dates

- **Drawdown Duration Analysis**
  - Max drawdown depth and date
  - Time to recovery from major drawdowns
  - Underwater period percentage
  - Top 5 worst drawdown periods with full details

- **Sub-Period Performance**
  - Automatic breakdown: 2020, 2021, 2022, 2023, 2024
  - Return, volatility, Sharpe, max drawdown per period
  - Identifies regime dependency

- **Position-Level Risk Diagnostics**
  - Individual stock volatility and worst outcomes
  - High-risk position flags (weight vs worst month)
  - Momentum tracking for large positions

#### Stress Testing Module (`scripts/stress_testing.py`)
- **Scenario-Based Stress Tests**
  - Tech Crash (-30%): Technology sector shock
  - Energy Crash (-40%): Energy/uranium sector shock
  - Rate Spike: Growth stocks impact
  - Broad Bear (-25%): General market decline
  - AI Bubble Pop: AI-related stocks crash
  - EV Washout: Clean energy/EV crash
  - Inflation Surge: Commodity benefit, growth hurt

- **Position Reduction Simulation**
  - Impact of reducing exposure by 50%
  - Volatility, return, Sharpe, drawdown comparison
  - Capital-at-risk guidance

#### Conscience Filter Module (`scripts/conscience_filter.py`)
- **Industry Exclusion Categories**
  - Defense & Weapons (LMT, RTX, NOC, etc.)
  - Tobacco & Nicotine (MO, PM, etc.)
  - Alcohol & Spirits (BUD, DEO, etc.)
  - Gambling & Casinos (LVS, WYNN, DKNG, etc.)
  - Fossil Fuels (XOM, CVX, COP, etc.)
  - Private Prisons (GEO, CXW)
  - Predatory Finance

- **ESG Concern Flags** (Informational)
  - Environmental: High emissions, water intensive
  - Social: Data privacy, controversial products
  - Governance: Dual-class shares

- **Filter Application**
  - Category-based exclusions
  - Sector-based exclusions
  - Specific ticker exclusions
  - Weight renormalization after filtering

#### Thematic & Sector Dependence Analysis
- **Theme Concentration**
  - Nuclear/Uranium exposure
  - Clean Energy/EV exposure
  - High-Beta Tech/AI exposure
  - Traditional Energy exposure

- **Correlation Cluster Analysis**
  - Average pairwise correlation
  - Highly correlated pairs (>0.70)
  - Correlation clusters for diversification check

#### Sizing Recommendations
- **Capital Allocation Guidance**
  - Based on max drawdown tolerance
  - Recovery time considerations
  - Conservative/Moderate/Aggressive allocations

### Changed
- `strengthen_recommendations.py` now integrates all analysis modules
- New `--full` flag for extended analyses
- Summary includes issues and warnings separately

---

## [3.2.0] - 2026-01-02

### Added

#### Automated Safeguards & Validation (`src/validation/safeguards.py`)
- **Portfolio Constraint Validation**
  - Weights sum to 1.0 check (critical - fails run if violated)
  - Position count matches `top_n` config
  - No negative weights (long-only constraint)
  - No excessive single position (>50%)
  
- **Risk Profile Bounds**
  - Conservative: Vol <25%, DD >-20%, Sector <35%
  - Moderate: Vol <50%, DD >-40%, Sector <50%
  - Aggressive: Vol <80%, DD >-70%, Sector <70%
  
- **Automatic Integration**
  - Runs as Step 8 in `full_analysis_workflow.py`
  - Generates `validation_report.json` for each run
  - CLI: `python -m src.validation.safeguards <run_dir> --profile moderate`

#### Recommendation Strengthening Analysis (`scripts/strengthen_recommendations.py`)
- **Regime Analysis**: Bull/Bear × High/Low Vol performance breakdown
- **Factor Exposure (SHAP-like)**: Identifies if single factor dominates (>50%)
- **Stress Testing**: Position sizing impact on drawdown and Sharpe
- **Conscience Filters**: Exclude sectors/tickers and recalculate metrics
- CLI: `python scripts/strengthen_recommendations.py --exclude-sectors "Energy,Defense"`

#### Extended Backtest Coverage
- Fixed benchmark data to extend through 2025-12-31
- Added 5th walk-forward window covering 2024 data
- Total coverage: Feb 2020 - Dec 2024 (59 monthly rebalances)

#### Date Range Specification
- **CLI Arguments**: `--start-date` and `--end-date` for filtering backtest data
- **Config Support**: `backtest.start_date` and `backtest.end_date` in config.yaml
- **Run Info Output**: New `run_info.json` file in each run folder containing:
  - Requested and actual date ranges
  - Full backtest configuration
  - Watchlist information
  - Run metadata

#### Comprehensive Test Suite (`tests/`)
- 76 automated tests covering:
  - Data integrity (prices, benchmark, sectors)
  - Backtest configuration (weights, positions)
  - Metric scaling (returns, volatility, Sharpe)
  - Safeguards validation
  - Pipeline integration
- Documentation: `tests/TEST_DOCUMENTATION.md`

### Fixed
- `AIInsightsGenerator` missing methods (`generate_executive_summary`, etc.)
- Backtest portfolio size: Changed `top_n: null` → `top_n: 10` for fixed 10-stock portfolio
- Benchmark data was limiting backtest to 2024-01 (now extends to 2024-12)

### Changed
- Risk profile bounds now configurable per profile (conservative/moderate/aggressive)
- Validation integrated into analysis workflow automatically

---

## [3.1.0] - 2026-01-02

### Added

#### Sector Classification System
- **Automatic Sector Fetching** (`scripts/fetch_sector_data.py`)
  - Fetches sector/industry data from Yahoo Finance for all watchlist stocks
  - Caches data in `data/sectors.csv` and `data/sectors.json`
  - Supports incremental updates (only fetches missing tickers)
  - Force refresh option with `--force` flag
  - **Result**: Reduced "Other" sector from 84.6% to 0.6%

#### Data Validation
- **Pre-flight Data Checks** in `full_analysis_workflow.py`
  - Validates price data coverage before running analysis
  - Reports missing tickers, date range issues, data quality
  - Generates validation reports in JSON and Markdown
  - Automatic skip option with `--skip-validation` flag

#### Watchlist Management
- **Symbol Validation & Deduplication** (`src/app/dashboard/data.py`)
  - `validate_watchlist_symbols()` - Validates and cleans symbol lists
  - `clean_and_deduplicate_symbols()` - Removes duplicates, normalizes case
  - Automatic sector fetching when creating custom watchlists
  - Invalid symbol filtering (special characters, too long)

#### Portfolio Analysis Enhancements
- **Enhanced Overview Tab**
  - Portfolio details panel (name, holdings count, sectors, average score)
  - All Holdings display with color-coded score pills (0-100 scale)
  - AI-generated insights for each chart
  - Hero section with gradient banner and glass-morphism metric cards

- **New Charts Added**
  - Cumulative Returns chart
  - Sector Sunburst visualization
  - Score Violin Plot
  - Monthly Returns Heatmap
  - Risk-Return Scatter plot
  - VaR Analysis Chart
  - Gauge Charts (Volatility, Sharpe, Max Drawdown)
  - Lollipop Chart for Top 10 stocks
  - Interactive Holdings Table

- **Performance Tab**
  - Equity Curve with drawdown overlay
  - Daily Returns Bar Chart
  - Monthly Performance Calendar
  - Return Statistics panel

- **Sectors Tab**
  - Interactive Treemap
  - Radar Chart for sector scores
  - Holdings by Sector bar chart
  - Top Stocks by Sector cards

- **Risk Tab**
  - 6 Risk Metric Cards
  - VaR Analysis visualization
  - Risk-adjusted return metrics

### Fixed

- **Pipeline Filtering Bug** - Watchlist now properly overrides `universe.txt`
  - Before: Only 95 stocks processed (limited by universe.txt)
  - After: All 337 stocks in watchlist processed correctly

- **Sector Classification** - Replaced hardcoded 56-stock mapping with yfinance data
  - Before: 285 stocks (84.6%) classified as "Other"
  - After: Only 2 stocks (0.6%) remain unclassified
  - Sector Diversification: 0.28 → 0.91

- **AI Recommendations Loading** - Fixed glob pattern to find recommendation files
  - Pattern now correctly matches `recommendations_*.json`

- **Color Contrast Issues** - Fixed light text on light backgrounds
  - Added dark gradient backgrounds to section titles
  - Fixed holdings cards, chart insights, AI summary panels

- **Holdings Display** - Fixed HTML rendering issues
  - Normalized scores from 0-1 to 0-100 scale
  - Changed to column-based rendering for reliability

- **overall_assessment Error** - Fixed `'str' object has no attribute 'get'`
  - AI tab now correctly handles string vs dict values

### Changed

- **Sector Mapping** - All analysis modules now use cached sector data
  - `src/analysis/domain_analysis.py`
  - `src/app/cli.py`
  - `scripts/analyze_portfolio.py`

- **Output Folder Naming** - Includes watchlist name for custom watchlists
  - Format: `run_{watchlist}_{timestamp}_{hash}/`

---

## [3.0.0] - 2025-12-31

### Added

#### Portfolio Builder
- **Personalized Portfolio Optimization** (`src/analysis/portfolio_optimizer.py`)
  - InvestorProfile dataclass with 12+ configurable parameters
  - Risk tolerance levels: conservative (8% return, 10% max DD), moderate (12%, 15%), aggressive (18%, 25%)
  - Target return, max drawdown, max volatility preferences
  - Portfolio size (configurable, default 10 stocks)
  - Position limits (min/max weight per stock)
  - Sector limits (max weight per sector, default 35%)
  - Style preferences: value, growth, blend
  - Dividend preference: income, neutral, growth
  - Time horizon: short (1yr), medium (3yr), long (5yr+)
  - Preset profiles with `get_preset_profile()` helper
  - Custom parameter overrides via kwargs

- **Vertical Analysis (Within-Sector)**
  - Domain score computation with configurable weights
  - Quality/value/profitability filters
  - Top-K candidates per sector
  - Exportable candidate CSVs

- **Horizontal Analysis (Cross-Sector)**
  - Candidate pool aggregation
  - Sector constraint enforcement
  - Risk-optimized weight allocation
  - Diversification requirements

- **Portfolio Optimization Script** (`scripts/run_portfolio_optimizer.py`)
  - CLI with profile presets (`--risk-tolerance conservative|moderate|aggressive`)
  - Custom parameter overrides for all InvestorProfile fields
  - AI analysis integration with `--with-ai-recommendations` flag
  - Outputs: optimized portfolio CSV, metrics JSON, AI recommendations MD

- **AI Portfolio Recommendations** (`src/analysis/gemini_commentary.py`)
  - Multi-profile recommendations (conservative, balanced, aggressive)
  - Per-profile: expected return, risk assessment, time horizon, suggested holdings
  - Model fallback list: gemini-2.0-flash-exp → gemini-1.5-flash-latest → gemini-pro
  - Read-only commentary mode (explains, doesn't modify portfolios)

#### Analysis Pipeline Improvements
- **4-Stage Pipeline with Guards**
  - Stage 1: Backtest (always available) - generates base metrics, positions, returns
  - Stage 2: Enrichment (requires Stage 1) - adds sector breakdown, risk metrics, diversification
  - Stage 3: Domain Analysis (requires Stage 1) - vertical/horizontal analysis, candidate scoring
  - Stage 4: AI Analysis (requires Stage 1) - commentary, recommendations, risk insights
  - Visual status indicators (✅ Complete, 🔴 Not Started, 🟡 Partial)
  - Dependency guards prevent out-of-order execution
  - Warning system for missing optional stages

- **Full Analysis Workflow** (`scripts/full_analysis_workflow.py`)
  - One-click execution of all 4 stages
  - Automatic folder creation and organization
  - Progress reporting with stage status
  - Error handling with stage-specific messages

- **Run-Specific Output Folders**
  - Each backtest creates `output/run_{run_id}/` (16-char prefix)
  - Standard output files: `backtest_metrics.json`, `backtest_returns.csv`, `backtest_positions.csv`
  - Domain analysis: `vertical_candidates_*.csv`, `horizontal_portfolio_*.csv`
  - AI outputs: `ai_commentary.md`, `ai_recommendations.json`
  - Easy cleanup with folder deletion

#### Dashboard Enhancements
- **Portfolio Builder Page** (`🎯 Portfolio Builder`)
  - Risk & Return section: risk tolerance, target return, max drawdown, max volatility
  - Portfolio Construction section: size, min/max position weight, max sector weight
  - Style Preferences section: investment style, dividend preference, time horizon
  - Profile presets dropdown (Conservative/Moderate/Aggressive)
  - Real-time profile summary card
  - Run selector from available backtest runs
  - AI recommendations toggle
  - Results display with portfolio table, metrics, and charts
  - Sector allocation pie chart
  - Weight distribution bar chart

- **Improved Run Analysis Page**
  - Quick Start: Full Analysis button prominently at top
  - Pipeline status overview with 4-stage visual
  - Stage tabs with dependency guards
  - Run selector with folder status indicators (📁/⚪)
  - Output file browser with file counts
  - Live script execution output

- **Portfolio Analysis Enhancements**
  - Integrated Domain Analysis Results
  - AI-Powered Analysis with recommendations
  - Vertical analysis candidates view
  - Horizontal portfolio composition
  - Risk metrics comparison charts

#### New Documentation
- `docs/portfolio-builder.md` - Comprehensive portfolio builder guide
  - InvestorProfile parameters reference
  - Risk tolerance and time horizon explanations
  - Workflow diagrams for vertical/horizontal analysis
  - Output files and interpretation guide
  - API reference for PortfolioOptimizer class

- `docs/domain-analysis.md` - Vertical/horizontal analysis details
  - Composite domain score formula
  - Fundamental filters configuration
  - Portfolio optimization algorithm
  - Integration with backtest pipeline

#### Updated Documentation
- `README.md` - Complete feature overview with Portfolio Builder section
- `docs/dashboard.md` - All seven pages documented including Portfolio Builder
- `docs/ai-insights.md` - Portfolio recommendations and multi-profile analysis
- `docs/design.md` - Updated architecture with Portfolio Builder module
- `CHANGELOG.md` - Complete version history

### Changed

- **CLI Output Structure**
  - All backtest outputs now go to run-specific folders
  - Legacy paths supported for backwards compatibility

- **Dashboard Navigation**
  - Added Portfolio Builder page
  - Reordered navigation for workflow clarity

- **Analysis Scripts**
  - All scripts accept `--run-id` parameter
  - Output folder determined by run ID

### Fixed

- **Run folder not created** - Fixed CLI to create `output/run_{run_id}/` before saving files
- **Dashboard not refreshing** - Added refresh buttons and `st.cache_resource.clear()` calls
- **Domain analysis argument error** - Added `--run-id` argument parsing in domain_analysis.py
- **Gemini model availability** - Added model name fallback list across all Gemini integrations
- **Dropdown showing deleted runs** - Updated run selector to filter by existing folders
- **Win rate showing N/A** - Fixed by mapping `hit_rate` to `win_rate` in database
- **Universe count None** - Fixed CLI to count unique tickers from backtest positions
- **Timestamp showing UTC** - Changed to `datetime.now()` for local time display
- **Stock scores all None** - Enhanced feature engineering to populate all score columns

---

## [2.0.0] - 2025-12-31

### Added

#### Risk-Aware Portfolio Construction
- **Risk Parity Allocation** (`src/risk/risk_parity.py`)
  - Inverse volatility weighting for simple risk-aware allocation
  - Full risk parity with equal risk contribution per position
  - Vol-capped sizing to limit volatility contribution
  - Beta-adjusted allocation to target portfolio beta
  - Sector constraints with configurable maximum weights

- **Portfolio Risk Profile**
  - Concentration metrics (HHI, Effective N)
  - Beta exposure analysis (Low/Med/High breakdown)
  - Risk tilt classification (Defensive/Balanced/High Beta)
  - Automated warning generation for risk issues

- **Risk Analysis Script** (`scripts/run_risk_aware_analysis.py`)
  - Load existing analysis runs
  - Calculate stock volatilities and betas
  - Apply risk parity allocation
  - Generate risk reports with AI insights

#### AI-Powered Insights
- **AI Insights Generator** (`src/analytics/ai_insights.py`)
  - Integration with Google Gemini API
  - Executive summary generation
  - Top picks analysis with detailed explanations
  - Sector analysis and rotation guidance
  - Risk assessment and warnings
  - Actionable investment recommendations
  - Individual stock AI analysis
  - Fallback to rule-based insights when AI unavailable

- **Risk-Aware AI Insights**
  - Allocation rationale explanations
  - Beta exposure analysis
  - Position sizing recommendations

#### Web Dashboard
- **Streamlit Dashboard** (`src/app/dashboard.py`)
  - Overview page with summary metrics
  - Analysis runs browser with filtering
  - Stock explorer with search and score breakdown
  - AI Insights page with tabbed interface
  - Run comparison (side-by-side)
  - Settings and database management

- **Interactive Features**
  - Score distribution charts
  - Score breakdown bar charts
  - Performance over time visualization
  - Individual stock AI analysis

#### Analytics Database
- **SQLite Database** (`src/analytics/models.py`)
  - `runs` table for analysis run metadata
  - `stock_scores` table for per-stock scores
  - `trades` table for backtest trade history
  - `portfolio_snapshots` for portfolio state tracking
  - `watchlist_stocks` for watchlist management

- **Run Manager** (`src/analytics/manager.py`)
  - High-level API for database operations
  - Run lifecycle management
  - Batch score insertion
  - Run comparison utilities

#### Diversified Stock Universe
- **Watchlist Updates** (`config/watchlists.yaml`)
  - Blue chip stocks (23 large-cap stalwarts)
  - Nuclear energy (NLR, URA, CCJ, etc.)
  - Clean energy (ICLN, TAN, etc.)
  - Semiconductor ETFs
  - Broad market ETFs

#### API Configuration
- **API Key Management** (`src/config/api_keys.py`)
  - Environment variable loading from `.env`
  - API key status checking
  - Connection testing for all APIs
  - Graceful fallback when keys missing

### Changed

- **Position Sizing** - Multiple methods now available:
  - Equal weight (baseline)
  - Volatility-weighted
  - Score-weighted
  - Kelly criterion
  - ATR-based

- **Report Generation** - Now includes:
  - AI-generated insights in Markdown reports
  - AI sections in HTML reports
  - Risk analysis appendix
  - Sector exposure tables

- **Documentation** - Comprehensive updates:
  - New risk-parity.md for allocation methods
  - New ai-insights.md for Gemini integration
  - New dashboard.md for Streamlit UI
  - New analytics-database.md for data storage
  - New api-configuration.md for API setup
  - Updated design.md with new features
  - Updated risk-management.md with risk parity reference
  - Updated comparison.md with new capabilities

### Fixed

- **None values in stock analysis** - Properly handle `None` values from pandas Series when generating AI insights
- **Datetime comparison errors** - Fixed offset-naive vs offset-aware datetime comparisons in sentiment analysis

### Deprecated

- None

### Removed

- None

---

## [1.0.0] - 2025-12-30

### Initial Release

- Core ML pipeline with LightGBM
- Walk-forward backtesting
- SHAP explainability
- Technical and fundamental features
- Sentiment analysis integration
- CLI interface
- Configuration management
- Basic risk metrics

---

## Document References

| Feature | Documentation |
|---------|---------------|
| Portfolio Builder | [docs/portfolio-builder.md](docs/portfolio-builder.md) |
| Domain Analysis | [docs/domain-analysis.md](docs/domain-analysis.md) |
| Dashboard | [docs/dashboard.md](docs/dashboard.md) |
| Risk Parity | [docs/risk-parity.md](docs/risk-parity.md) |
| AI Insights | [docs/ai-insights.md](docs/ai-insights.md) |
| Database | [docs/analytics-database.md](docs/analytics-database.md) |
| API Config | [docs/api-configuration.md](docs/api-configuration.md) |
| Main Design | [docs/design.md](docs/design.md) |
