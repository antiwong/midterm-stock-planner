# Glossary - midterm_stock_planner

**Purpose**: Define domain-specific terminology for stock analysis, portfolio management, machine learning, backtesting, and risk management.

---

## Stock Market & Trading Terminology

### **Alpha**
Excess return of a portfolio over a benchmark index:
- Positive alpha = outperformance vs benchmark
- Calculated as: portfolio return - (beta * benchmark return)
- Key metric in performance attribution

### **Beta**
Sensitivity of a portfolio or stock to market movements:
- Beta = 1.0: moves with the market
- Beta > 1.0: more volatile than market (high beta)
- Beta < 1.0: less volatile than market (low beta)
- Calculated from regression of returns against benchmark

### **Benchmark**
Reference index for performance comparison:
- **SPY**: S&P 500 ETF (primary benchmark)
- **QQQ**: Nasdaq-100 ETF (tech-heavy benchmark)
- Used for alpha, tracking error, information ratio calculations

### **Rebalancing**
Adjusting portfolio weights to match target allocation:
- midterm_stock_planner uses monthly rebalancing
- Incurs transaction costs
- Analysed via `RebalancingAnalyzer` for drift and optimal frequency

### **Watchlist**
Curated list of stock tickers for analysis:
- Defined in `config/watchlists.yaml`
- Categories: blue_chip, nuclear, clean_energy, semiconductors, etc.
- Managed via Watchlist Manager dashboard page

### **Ticker / Symbol**
Stock exchange identifier for a company:
- Format: uppercase letters (e.g., AAPL, MSFT, GOOGL)
- Yahoo Finance format used (BRK-B not BRK.B)
- Validated by `symbol_validator.py`

---

## Portfolio Management Terminology

### **Position**
A holding in a specific stock within the portfolio:
- **Weight**: Fraction of total portfolio value allocated (e.g., 0.10 = 10%)
- **Long-only**: midterm_stock_planner only supports long positions (no shorting)
- Tracked in `backtest_positions.csv`

### **Concentration**
Measure of how diversified a portfolio is:
- **HHI (Herfindahl-Hirschman Index)**: Sum of squared weights; lower = more diversified
- **Effective N**: 1/HHI; represents equivalent number of equally-weighted positions
- Flagged by safeguards when excessive

### **Sector Allocation**
Distribution of portfolio weight across market sectors:
- Sectors: Technology, Healthcare, Financials, Energy, etc.
- Sector data cached in `data/sectors.json`
- Max sector weight configurable (default: 35%)

### **Risk Parity**
Portfolio allocation where each position contributes equally to total risk:
- **Inverse volatility weighting**: Weight inversely proportional to volatility
- **Equal risk contribution**: Iterative optimization for equal risk per position
- Implemented in `RiskParityAllocator`

### **Concentration Cap**
Maximum allowed weight for any single stock in the portfolio (default 25%). Prevents catastrophic single-stock risk.

### **Position Sizing**
Determining how much capital to allocate per stock:
- **Equal weight**: 1/N allocation
- **Volatility-weighted**: Less weight to more volatile stocks
- **Score-weighted**: More weight to higher-scored stocks
- **Kelly criterion**: Optimal sizing based on expected return and variance
- **ATR-based**: Based on Average True Range

---

## Risk Metrics Terminology

### **Calibration Factor**
Multiplier that adjusts portfolio exposure based on historical signal accuracy. Formula: hit_rate / 0.50, clamped to [0.5, 1.5].

### **Daily Loss Limit**
Maximum daily portfolio loss before trading is halted (-5%). Prevents cascading losses during crashes.

### **Drawdown-from-Peak**
Risk rule that liquidates all positions when portfolio retraces 30% from its peak equity (only active after 5% profit).

### **Sharpe Ratio**
Risk-adjusted return metric:
- Formula: (Portfolio Return - Risk-Free Rate) / Portfolio Volatility
- Higher is better (>1.0 considered good, >2.0 excellent)
- Annualised from monthly or daily returns

### **Sortino Ratio**
Like Sharpe but only penalises downside volatility:
- Uses downside deviation instead of total standard deviation
- Better measure when return distribution is skewed
- Higher values preferred

### **Maximum Drawdown (Max DD)**
Largest peak-to-trough decline in portfolio value:
- Expressed as a percentage (e.g., -25%)
- Duration: time from peak to recovery
- Key risk metric for investor tolerance

### **VaR (Value at Risk)**
Worst expected loss at a given confidence level:
- VaR(95%) = worst 5% scenario
- VaR(99%) = worst 1% scenario
- Calculated via historical, parametric, or Monte Carlo methods

### **CVaR (Conditional VaR / Expected Shortfall)**
Average loss beyond the VaR threshold:
- Also called Expected Shortfall (ES)
- CVaR(95%) = average of worst 5% of returns
- More conservative than VaR; accounts for tail risk

### **Tracking Error**
Standard deviation of the difference between portfolio and benchmark returns:
- Lower tracking error = closer to benchmark
- Used with information ratio: alpha / tracking error

### **Hit Rate**
Fraction of BUY signals that produce positive returns over a 5-day evaluation window. Used for accuracy calibration.

### **Information Ratio**
Risk-adjusted active return vs benchmark:
- Formula: Alpha / Tracking Error
- Measures consistency of outperformance
- >0.5 is good, >1.0 is excellent

### **Stop-Loss**
Per-position rule that sells a stock if it drops 15% from its entry price.

### **Z-Score**
Number of standard deviations from the mean. Used in IC regime detection: z = (recent_mean - historical_mean) / (historical_std / sqrt(n)).

### **Calmar Ratio**
Annualised return divided by maximum drawdown:
- Measures return per unit of drawdown risk
- Higher values preferred

---

## Machine Learning Terminology

### **LightGBM (Light Gradient Boosting Machine)**
Primary ML model used in midterm_stock_planner:
- Gradient-boosted decision tree framework
- Used for cross-sectional stock ranking
- Configured in `config/config.yaml` under `model` section
- Trained per walk-forward window

### **Cross-Sectional Ranking**
Ranking stocks relative to each other at each point in time:
- Predicts forward excess return for each stock
- Top-N stocks selected for portfolio
- Different from time-series prediction (absolute returns)

### **Early Stopping**
Training technique that halts model fitting when validation loss stops improving (patience=30 rounds). Prevents overfitting.

### **Feature Importance (Gain)**
LightGBM's built-in measure of how much each feature contributes to reducing the loss function during tree splitting.

### **IC (Information Coefficient)**
Pearson correlation between model predictions and actual future excess returns. Measures predictive power.

### **IC Regime Detection**
Z-score test comparing recent IC to historical IC to detect model degradation. Z < -2.0 = degraded.

### **Marginal IC**
Spearman rank correlation between a single feature and the target variable. Model-free measure of feature predictive power.

### **Rank IC (Spearman)**
Spearman rank correlation between predicted and actual rankings. More robust than Pearson IC to outliers.

### **Regime Detection**
See IC Regime Detection.

### **Regularization (L1/L2)**
Penalty terms added to the loss function to prevent overfitting. L1 (alpha=0.3) drives small weights to zero; L2 (lambda=0.5) shrinks all weights.

### **SHAP (SHapley Additive exPlanations)**
Model interpretability framework:
- Explains individual stock predictions
- Shows which features drive each prediction
- Feature importance across entire model
- Implemented in `src/explain/shap_explain.py`

### **TreeSHAP**
Efficient algorithm for computing Shapley values on tree-based models. Decomposes each prediction into per-feature contributions.

### **Feature Engineering**
Creating input variables for the ML model:
- **Technical features**: RSI, MACD, ADX, Bollinger Bands, ATR, volume metrics
- **Fundamental features**: PE ratio, PB ratio, ROE, margins, market cap
- **Sentiment features**: Daily sentiment scores from news and LLM analysis
- **Momentum features**: Various lookback period returns
- Computed in `src/features/engineering.py`

### **Walk-Forward Backtest**
Rolling window approach for model validation:
- Train on historical window (e.g., 3 years)
- Test on forward period (e.g., 3 months)
- Slide window forward (e.g., 1 month step)
- Prevents look-ahead bias
- Implemented in `src/backtest/rolling.py`

### **Walk-Forward Step**
The number of days (default 7) the walk-forward window advances between iterations. Controls the number of evaluation windows.

### **Window (Walk-Forward)**
A single train/test split in the walk-forward backtest. Train = 3 years, Test = 6 months.

### **Overfitting**
Model memorises training data instead of learning generalisable patterns:
- Walk-forward testing helps detect overfitting
- SHAP analysis reveals if model relies on noise
- Cross-validation within training windows

---

## Technical Analysis Terminology

### **RSI (Relative Strength Index)**
Momentum oscillator measuring speed and change of price movements:
- Range: 0-100
- >70 = overbought, <30 = oversold
- Default period: 14 days

### **MACD (Moving Average Convergence Divergence)**
Trend-following momentum indicator:
- MACD line = 12-period EMA - 26-period EMA
- Signal line = 9-period EMA of MACD line
- Crossovers indicate trend changes

### **ADX (Average Directional Index)**
Trend strength indicator:
- Range: 0-100
- >25 = strong trend, <20 = weak trend
- Does not indicate direction, only strength

### **ATR (Average True Range)**
Volatility indicator measuring trading range:
- Used for position sizing and stop-loss placement
- Higher ATR = more volatile
- Default period: 14 days

### **Bollinger Bands**
Volatility bands around a moving average:
- Middle band: 20-period SMA
- Upper/lower bands: SMA +/- 2 standard deviations
- Price near upper band = potentially overbought
- Width indicates volatility

### **Moving Averages**
- **SMA**: Simple Moving Average (equal weight to all periods)
- **EMA**: Exponential Moving Average (more weight to recent periods)
- Common periods: 20, 50, 100, 200 days

---

## Fundamental Analysis Terminology

### **PE Ratio (Price-to-Earnings)**
Stock price divided by earnings per share:
- Lower PE = potentially undervalued (value)
- Higher PE = growth expectations (growth)
- Sector-dependent benchmarks

### **PB Ratio (Price-to-Book)**
Stock price divided by book value per share:
- <1.0 may indicate undervaluation
- Used in value/growth style classification

### **ROE (Return on Equity)**
Net income divided by shareholder equity:
- Measures profitability relative to equity
- Higher ROE = more efficient use of capital
- Used as quality factor in factor exposure analysis

### **Market Capitalisation (Market Cap)**
Total market value of a company's outstanding shares:
- **Large cap**: >$10B
- **Mid cap**: $2B-$10B
- **Small cap**: <$2B
- Used for size factor in factor exposure analysis

### **Dividend Yield**
Annual dividend per share divided by stock price:
- Used in `InvestorProfile` dividend preference
- Income preference targets higher yields
- Growth preference accepts lower yields

---

## Analytics & Reporting Terminology

### **Performance Attribution**
Decomposing portfolio returns into contributing factors:
- **Factor contribution**: Returns from systematic factor exposures
- **Sector contribution**: Returns from sector allocation decisions
- **Stock selection**: Returns from individual stock picks
- **Timing**: Returns from rebalancing timing
- Implemented in `performance_attribution.py`

### **Factor Exposure**
Portfolio sensitivity to systematic risk factors:
- **Market factor**: Overall market exposure (beta)
- **Size factor**: Small vs large cap tilt
- **Value factor**: Value vs growth tilt
- **Momentum factor**: Exposure to momentum effect
- **Quality factor**: Exposure to quality characteristics
- **Low volatility factor**: Exposure to low-vol anomaly

### **Monte Carlo Simulation**
Statistical method using random sampling:
- Simulates portfolio returns using historical distributions
- Methods: bootstrap, normal, t-distribution
- Outputs: VaR, CVaR, confidence intervals, probability metrics
- Stress testing via extreme scenarios

### **Tax-Loss Harvesting**
Selling losing positions to offset capital gains:
- Identifies positions with unrealised losses
- Detects wash sales (30-day rebuy window)
- Estimates tax savings
- Implemented in `tax_optimization.py`

### **Style Analysis**
Classifying portfolio investment style:
- **Growth vs Value**: Based on PE, PB, earnings growth
- **Large vs Small Cap**: Based on market capitalisation
- Style drift detection over time
- Style consistency scoring

---

## Data & Infrastructure Terminology

### **yfinance**
Python library for accessing Yahoo Finance data:
- Used for stock prices, fundamental data, sector classification
- Primary data source for midterm_stock_planner
- Rate-limited; uses parallel downloads with `ThreadPoolExecutor`

### **Google Gemini**
Google's large language model API:
- Used for AI-generated portfolio insights
- Models: gemini-2.0-flash-exp, gemini-1.5-flash-latest (fallbacks)
- Configured via `GEMINI_API_KEY` environment variable
- Used in `ai_insights.py` and `llm_analyzer.py`

### **Streamlit**
Python web framework for data applications:
- Powers the interactive dashboard
- Session state for user preferences
- `@st.cache_data` for performance caching
- Custom CSS for theming and dark mode

### **SQLAlchemy**
Python ORM (Object-Relational Mapper):
- Used for `data/analysis.db` SQLite database
- Models: RunRecord, StockScore, AnalysisResult, AIInsight
- Connection pooling for thread-safe access

### **SQLite**
Lightweight file-based relational database:
- `data/analysis.db` stores all analysis results
- No server required; embedded in application
- Tables: runs, stock_scores, analysis_results, ai_insights, recommendations, etc.

---

## Configuration Terminology

### **config.yaml**
Main application configuration file:
- `model`: LightGBM parameters (n_estimators, learning_rate, max_depth)
- `backtest`: Window sizes, rebalance frequency, top_n
- `data`: Data paths and sources
- `features`: Feature engineering settings
- `sentiment`: Sentiment analysis configuration

### **watchlists.yaml**
Stock watchlist definitions:
- Named collections of stock tickers
- Categories: blue_chip, nuclear, clean_energy, etc.
- Used to define analysis universe

### **InvestorProfile**
User preference configuration for portfolio construction:
- Risk tolerance: conservative / moderate / aggressive
- Target return, max drawdown, max volatility
- Portfolio size, position limits, sector limits
- Style and dividend preferences

---

## Acronyms

- **ADX**: Average Directional Index
- **API**: Application Programming Interface
- **ATR**: Average True Range
- **CLI**: Command-Line Interface
- **CRF**: not used (from video encoding — not applicable)
- **CSV**: Comma-Separated Values
- **CVaR**: Conditional Value at Risk
- **DB**: Database
- **DD**: Drawdown
- **EMA**: Exponential Moving Average
- **ESG**: Environmental, Social, Governance
- **ETF**: Exchange-Traded Fund
- **HHI**: Herfindahl-Hirschman Index
- **IC**: Information Coefficient
- **JSON**: JavaScript Object Notation
- **LLM**: Large Language Model
- **LOC**: Lines of Code
- **MACD**: Moving Average Convergence Divergence
- **ML**: Machine Learning
- **OBV**: On-Balance Volume
- **ORM**: Object-Relational Mapper
- **PB**: Price-to-Book
- **PE**: Price-to-Earnings
- **ROE**: Return on Equity
- **RSI**: Relative Strength Index
- **SHAP**: SHapley Additive exPlanations
- **SMA**: Simple Moving Average
- **SQL**: Structured Query Language
- **UI**: User Interface
- **VaR**: Value at Risk
- **YAML**: YAML Ain't Markup Language

---

## Related Documentation

- **Comprehensive Context**: See [`AGENT_PROMPT.md`](AGENT_PROMPT.md) for detailed project overview
- **Module Overviews**: See [`module_summaries.md`](module_summaries.md) for module responsibilities
- **Technical Indicators**: See [`../docs/technical-indicators.md`](../docs/technical-indicators.md)
- **Risk Management**: See [`../docs/risk-management.md`](../docs/risk-management.md)
- **AI Insights**: See [`../docs/ai-insights.md`](../docs/ai-insights.md)

---

**Last Updated**: 2026-03-17
**Version**: 3.11.2
