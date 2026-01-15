# Feature Comparison: Stockbot vs Mid-term Stock Planner

This document provides a detailed comparison between **Stockbot** and **Mid-term Stock Planner**, two complementary stock analysis and trading systems.

## Executive Summary

| Aspect | Stockbot | Mid-term Stock Planner |
|--------|----------|------------------------|
| **Primary Focus** | Active trading with real-time signals | Research & portfolio optimization |
| **Time Horizon** | Short-term (days to weeks) | Mid-term (3 months) |
| **Trading Style** | Signal-based buy/sell execution | Monthly rebalancing |
| **Model Type** | Rule-based + multi-factor scoring | ML-based (LightGBM) cross-sectional |
| **Explainability** | Factor score breakdown | SHAP values |
| **Interface** | Web dashboard + CLI | Streamlit dashboard + CLI |
| **Live Trading** | Yes (Tiger Brokers) | No (research only) |
| **Risk Allocation** | Rules-based position limits | Risk parity, vol-weighted, personalized |
| **AI Insights** | ❌ | ✅ Gemini-powered analysis & recommendations |
| **Portfolio Builder** | ❌ | ✅ Personalized optimization |
| **Domain Analysis** | ❌ | ✅ Vertical & horizontal analysis |
| **Database** | File-based | SQLite with run tracking |
| **Comprehensive Analysis** | ❌ | ✅ Performance attribution, benchmark comparison, factor exposure |
| **Historical Tracking** | ❌ | ✅ All analysis results stored in database |
| **Recommendation Tracking** | ❌ | ✅ Track recommendation performance over time |

---

## Detailed Feature Comparison

### 1. Data Sources & Ingestion

| Feature | Stockbot | Mid-term Stock Planner |
|---------|----------|------------------------|
| **Price Data** | Alpha Vantage, Yahoo Finance (fallback) | CSV/Parquet, yfinance |
| **Real-time Data** | ✅ WebSocket support | ❌ Batch processing |
| **Fundamental Data** | ✅ Via yfinance/Alpha Vantage | ✅ Via yfinance |
| **SEC Filings** | ✅ EDGAR integration (8-K, 10-Q, 10-K) | ✅ EDGAR integration |
| **News Data** | ✅ Alpha Vantage, NewsAPI, RSS | ✅ Alpha Vantage, NewsAPI, RSS, CSV |
| **Watchlists** | ✅ YAML configuration | ✅ Universe file |
| **Auto-refresh** | ✅ 5-second dashboard refresh | ❌ Manual refresh |

### 2. Technical Indicators

| Indicator | Stockbot | Mid-term Stock Planner |
|-----------|----------|------------------------|
| **RSI** | ✅ | ✅ |
| **MACD** | ✅ | ✅ |
| **EMA/SMA** | ✅ | ✅ |
| **Bollinger Bands** | ✅ | ✅ |
| **ATR** | ✅ | ✅ |
| **ADX** | ❌ | ✅ |
| **OBV** | ❌ | ✅ |
| **Support/Resistance** | ✅ | ❌ |
| **Pivot Points** | ✅ | ❌ |

### 3. Sentiment Analysis

| Feature | Stockbot | Mid-term Stock Planner |
|---------|----------|------------------------|
| **Alpha Vantage News** | ✅ | ✅ |
| **NewsAPI** | ✅ | ✅ |
| **RSS Feeds** | ✅ Custom feeds | ✅ Custom feeds |
| **CSV/Parquet Input** | ❌ | ✅ |
| **Lexicon Model** | ❌ | ✅ |
| **TextBlob** | ✅ | ✅ |
| **FinBERT** | ❌ | ✅ (optional) |
| **LLM (OpenAI)** | ✅ GPT | ✅ GPT |
| **LLM (Gemini)** | ✅ | ✅ |
| **Rolling Features** | ❌ | ✅ (1d, 7d, 14d lookbacks) |
| **Feature Engineering** | Basic aggregation | ✅ Mean, std, count, trend |
| **Look-ahead Prevention** | ⚠️ Manual care needed | ✅ Built-in filtering |
| **Multi-source Aggregation** | ✅ | ✅ |

### 4. Fundamental Analysis

| Feature | Stockbot | Mid-term Stock Planner |
|---------|----------|------------------------|
| **CAN SLIM** | ✅ Full 7 criteria | ❌ |
| **PE Ratio** | ✅ | ✅ |
| **PB Ratio** | ✅ | ✅ |
| **Profit Margins** | ✅ | ✅ |
| **ROE/ROA** | ✅ | ✅ |
| **Revenue Growth** | ✅ | ✅ |
| **Earnings Growth** | ✅ | ✅ |
| **SEC Filings Parsing** | ✅ | ✅ |
| **Analyst Ratings** | ✅ | ✅ |

### 5. Strategy Features

| Feature | Stockbot | Mid-term Stock Planner |
|---------|----------|------------------------|
| **Momentum** | ✅ | ✅ |
| **Mean Reversion** | ✅ | ✅ |
| **Multi-timeframe** | ✅ (Long/Medium/Short) | ❌ |
| **Pattern Recognition** | ✅ (Cup & handle, double bottom) | ❌ |
| **Dow Theory** | ✅ | ❌ |
| **Market Structure** | ✅ (Higher highs/lows) | ❌ |
| **52-Week High/Low** | ✅ | ✅ |
| **Relative Strength** | ✅ | ✅ |
| **Z-Score** | ❌ | ✅ |

### 6. Model & Scoring

| Aspect | Stockbot | Mid-term Stock Planner |
|--------|----------|------------------------|
| **Model Type** | Rule-based multi-factor | ML (LightGBM/XGBoost) |
| **Score Range** | 0-100 points | Continuous (excess return) |
| **Score Breakdown** | Technical (40), Fundamental (30), Sentiment (20), Volume (10) | SHAP values per feature |
| **Cross-sectional** | ❌ (absolute scoring) | ✅ (rank within universe) |
| **Walk-forward Training** | ❌ | ✅ |
| **Hyperparameter Tuning** | Manual | ✅ (via config) |
| **Feature Selection** | Fixed | Configurable |

### 7. Backtesting

| Feature | Stockbot | Mid-term Stock Planner |
|---------|----------|------------------------|
| **Walk-forward** | Basic | ✅ Rolling windows |
| **Transaction Costs** | ✅ Commission + slippage | ✅ Configurable |
| **Performance Metrics** | Sharpe, win rate, max DD | Sharpe, Sortino, Calmar, IR |
| **Monte Carlo** | ✅ | ❌ |
| **Parameter Optimization** | ✅ | ❌ |
| **A/B Comparison** | ❌ | ✅ (with/without sentiment) |
| **Equity Curve** | ✅ | ✅ |
| **Drawdown Analysis** | ✅ | ✅ |
| **Performance Attribution** | ❌ | ✅ Factor, sector, stock selection, timing |
| **Benchmark Comparison** | ❌ | ✅ Alpha, beta, tracking error, up/down capture |
| **Factor Exposure** | ❌ | ✅ Market, size, value, momentum, quality, low vol |
| **Rebalancing Analysis** | ❌ | ✅ Drift, turnover, transaction costs, optimal frequency |
| **Style Analysis** | ❌ | ✅ Growth/value, size classification |

### 8. Risk Management

| Feature | Stockbot | Mid-term Stock Planner |
|---------|----------|------------------------|
| **Position Sizing** | ✅ (rules engine) | ✅ (multiple methods) |
| **Stop Loss** | ✅ | ❌ |
| **Volatility Targeting** | ✅ | ✅ |
| **Max Position Limits** | ✅ | ✅ Configurable per profile |
| **Sector Exposure** | ❌ | ✅ Constraints with caps |
| **VaR/CVaR** | ✅ | ✅ |
| **Beta** | ❌ | ✅ Portfolio beta control |
| **Correlation Matrix** | ❌ | ✅ |
| **Stress Testing** | ❌ | ✅ |
| **Risk Parity** | ❌ | ✅ Equal risk contribution |
| **Inverse Volatility** | ❌ | ✅ Vol-weighted allocation |
| **Concentration Metrics** | ❌ | ✅ HHI, Effective N |
| **Risk Profiles** | ❌ | ✅ Conservative/Moderate/Aggressive |
| **Max Drawdown Targeting** | ❌ | ✅ Per investor profile |

### 8.1. Portfolio Builder (Mid-term Stock Planner Only)

| Feature | Description |
|---------|-------------|
| **InvestorProfile** | Dataclass with 12+ configurable parameters |
| **Risk Tolerance** | Conservative (8%), Moderate (12%), Aggressive (18%) target returns |
| **Max Drawdown** | Configurable limits (10%/15%/25% by profile) |
| **Portfolio Size** | Configurable number of holdings (default: 10) |
| **Position Limits** | Min/max weight per stock |
| **Sector Limits** | Max weight per sector (default: 35%) |
| **Style Preferences** | Value, Growth, or Blend |
| **Dividend Preference** | Income, Neutral, or Growth |
| **Time Horizon** | Short (1yr), Medium (3yr), Long (5yr+) |
| **Preset Profiles** | One-click Conservative/Moderate/Aggressive |
| **Custom Override** | Full parameter customization |

### 8.2. Domain Analysis (Mid-term Stock Planner Only)

| Feature | Description |
|---------|-------------|
| **Vertical Analysis** | Within-sector stock selection |
| **Domain Score** | Composite of model, value, and quality scores |
| **Configurable Weights** | `w_m`, `w_v`, `w_q` in config.yaml |
| **Hard Filters** | ROE > 0, Net Margin > 0, Debt/Equity < threshold |
| **Top-K Selection** | Best N candidates per sector |
| **Horizontal Analysis** | Cross-sector portfolio construction |
| **Candidate Pool** | Union of vertical winners |
| **Portfolio Optimization** | Score-weighted with constraints |
| **Diversification Score** | Minimum threshold enforcement |
| **Export CSVs** | `vertical_candidates_*.csv`, `horizontal_portfolio_*.csv` |

### 9. Explainability

| Feature | Stockbot | Mid-term Stock Planner |
|---------|----------|------------------------|
| **Score Breakdown** | ✅ Factor categories | ✅ SHAP values |
| **Per-stock Explanation** | ✅ (factor contributions) | ✅ (SHAP per feature) |
| **Global Importance** | ❌ | ✅ (feature importance) |
| **Portfolio-level** | ❌ | ✅ (portfolio SHAP) |
| **Feature Grouping** | ✅ (4 categories) | ✅ (7+ categories) |
| **Sentiment Attribution** | ✅ (score out of 20) | ✅ (SHAP contribution) |

### 10. Visualization

| Feature | Stockbot | Mid-term Stock Planner |
|---------|----------|------------------------|
| **Price Charts** | ✅ Plotly (interactive) | ✅ Matplotlib |
| **Indicator Overlays** | ✅ | ✅ |
| **Equity Curves** | ✅ | ✅ |
| **Drawdown Charts** | ✅ | ✅ |
| **Heatmaps** | ❌ | ✅ (monthly returns) |
| **Correlation Matrix** | ❌ | ✅ |
| **Distribution Plots** | ❌ | ✅ |

### 11. Interface & Automation

| Feature | Stockbot | Mid-term Stock Planner |
|---------|----------|------------------------|
| **Web Dashboard** | ✅ Flask + Plotly | ✅ Streamlit + Plotly (7 pages) |
| **CLI** | ✅ | ✅ |
| **REST API** | ✅ (full API) | ❌ |
| **Auto Scanning** | ✅ Hourly watchlist scans | ❌ |
| **Notifications** | ✅ | ❌ |
| **Configuration** | YAML + .env | YAML + env vars |
| **Run History** | ❌ | ✅ SQLite database |
| **Run Comparison** | ❌ | ✅ Side-by-side |
| **AI Insights** | ❌ | ✅ Gemini integration |
| **Portfolio Builder UI** | ❌ | ✅ Interactive parameter sliders |
| **Run Analysis UI** | ❌ | ✅ 4-stage pipeline with guards |
| **Profile Presets** | ❌ | ✅ One-click investor profiles |
| **Run Folders** | ❌ | ✅ Per-run output organization |
| **Comprehensive Analysis UI** | ❌ | ✅ All analysis modules in one page |
| **Historical Analysis** | ❌ | ✅ Database-backed analysis storage |
| **Recommendation Tracking** | ❌ | ✅ Track recommendation performance |

### 11.1. Dashboard Pages (Mid-term Stock Planner)

| Page | Description |
|------|-------------|
| **📊 Overview** | Summary metrics, recent runs, quick insights |
| **📈 Analysis Runs** | Browse all runs with filtering |
| **🔍 Stock Explorer** | Search stocks, view score breakdowns |
| **📉 Compare Runs** | Side-by-side run comparison |
| **🤖 AI Insights** | Gemini-powered analysis and recommendations |
| **💼 Portfolio Analysis** | Fundamental + risk-aware views |
| **📊 Comprehensive Analysis** | Performance attribution, benchmark comparison, factor exposure, rebalancing, style analysis |
| **🎯 Portfolio Builder** | Personalized portfolio optimization |
| **🎮 Run Analysis** | Execute analysis pipeline with guards |
| **⚙️ Settings** | Database management, API status |

### 11.2. Analysis Pipeline (Mid-term Stock Planner)

| Stage | Description | Requires |
|-------|-------------|----------|
| **Stage 1: Backtest** | Generate base metrics, positions, returns | Nothing |
| **Stage 2: Enrichment** | Add sector breakdown, risk metrics | Stage 1 |
| **Stage 3: Domain Analysis** | Vertical/horizontal analysis | Stage 1 |
| **Stage 4: AI Analysis** | Commentary and recommendations | Stage 1 |
| **Full Analysis** | One-click all stages | Nothing |

### 12. Trading Integration

| Feature | Stockbot | Mid-term Stock Planner |
|---------|----------|------------------------|
| **Paper Trading** | ✅ | ✅ (backtest only) |
| **Live Trading** | ✅ Tiger Brokers | ❌ |
| **Order Execution** | ✅ | ❌ |
| **Portfolio Tracking** | ✅ Real-time | ❌ |
| **Position Management** | ✅ | ❌ |

---

## Sentiment Analysis Deep Dive

Both systems now support comprehensive sentiment analysis:

### Data Sources (Both Support)

| Source | Description | API Required |
|--------|-------------|--------------|
| **Alpha Vantage** | Financial news with ticker-specific sentiment | Yes (free tier) |
| **NewsAPI** | Broad news coverage | Yes (free: 100 req/day) |
| **RSS Feeds** | Custom financial news feeds | No |
| **CSV/Parquet** | Historical news files (Mid-term only) | No |

### Sentiment Models

| Model | Stockbot | Mid-term Stock Planner |
|-------|----------|------------------------|
| **TextBlob** | ✅ Primary | ✅ Supported |
| **Lexicon** | ❌ | ✅ Primary (financial-tuned) |
| **FinBERT** | ❌ | ✅ Optional (transformers) |
| **LLM (GPT)** | ✅ OpenAI | ✅ OpenAI |
| **LLM (Gemini)** | ✅ | ✅ |

### Mid-term Stock Planner Sentiment Features

```python
from src.sentiment import MultiSourceSentimentAnalyzer

# Initialize with multiple sources
analyzer = MultiSourceSentimentAnalyzer(
    alpha_vantage_api_key="YOUR_KEY",
    news_api_key="YOUR_KEY",
    rss_feeds_file="data/rss_feeds.txt",
    sentiment_model_type="lexicon",  # or "textblob", "finbert"
    use_llm=True,
    llm_provider="openai",  # or "gemini"
)

# Get aggregated sentiment
sentiment = analyzer.get_sentiment("AAPL", days=7)
# Returns: {sentiment_score, sentiment_label, article_count, sources_used, ...}

# Get rolling features for ML
features_df = analyzer.compute_features("AAPL", lookbacks=[1, 7, 14])
# Returns: DataFrame with sentiment_mean_1d, sentiment_std_7d, etc.
```

---

## Functional Details

### Stockbot Functions

#### Core Analysis (`src/dashboard/analysis.py`)
```python
# Multi-factor scoring
calculate_multifactor_score(symbol) -> Dict
  - technical_score: 0-40 (trend, patterns, indicators, S/R)
  - fundamental_score: 0-30 (CAN SLIM, metrics, growth)
  - sentiment_score: 0-20 (news, RSS, LLM)
  - volume_score: 0-10 (trend, accumulation)

# CAN SLIM analysis
calculate_canslim_score(symbol) -> Dict
  - C: Current quarterly earnings
  - A: Annual earnings growth
  - N: New products/services
  - S: Supply and demand
  - L: Leader in industry
  - I: Institutional sponsorship
  - M: Market direction

# Pattern recognition
detect_chart_patterns(df) -> List[Dict]
  - Cup and handle
  - Double bottom/top
  - Head and shoulders
  - Triangles
```

#### Sentiment Analysis (`src/sentiment/analyzer.py`)
```python
class SentimentAnalyzer:
    # Core methods
    analyze_text_sentiment(text) -> Dict[str, float]
    get_news_sentiment(symbol, days=7) -> Dict
    get_aggregate_sentiment(symbol, days=7) -> Dict
    
    # Data sources
    _get_alpha_vantage_news(symbol, days) -> Dict
    _get_newsapi_news(symbol, days) -> Dict
    fetch_rss_news(symbol, keywords, max_items) -> List[Dict]
    
    # LLM integration
    analyze_article_with_llm(headline, body, symbol) -> Dict
```

---

### Mid-term Stock Planner Functions

#### Sentiment Module (`src/sentiment/`)

```python
# Multi-source analyzer (NEW)
from src.sentiment import MultiSourceSentimentAnalyzer

analyzer = MultiSourceSentimentAnalyzer(
    alpha_vantage_api_key="...",
    news_api_key="...",
    sentiment_model_type="lexicon",
    use_llm=True,
)

# Fetch from all sources
analyzer.fetch_news(ticker, days=7) -> List[NewsArticle]
analyzer.score_articles(articles) -> List[NewsArticle]
analyzer.get_sentiment(ticker, days=7) -> Dict
analyzer.compute_features(ticker, lookbacks=[1, 7, 14]) -> pd.DataFrame
analyzer.analyze_batch(tickers, days=7) -> pd.DataFrame

# Individual sources
from src.sentiment.sources import (
    AlphaVantageNewsSource,
    NewsAPISource,
    RSSFeedSource,
)

# Sentiment models
from src.sentiment import (
    LexiconSentimentModel,      # Financial lexicon (default)
    TextBlobSentimentModel,     # TextBlob
    FinBERTSentimentModel,      # Transformer-based
    get_sentiment_model,
)

# LLM analysis
from src.sentiment import LLMSentimentAnalyzer

llm = LLMSentimentAnalyzer(provider="openai")
result = llm.analyze_article(headline, body, ticker)
# Returns: LLMAnalysisResult with sentiment_score, summary, key_themes, risks, opportunities

# Aggregation
from src.sentiment import (
    aggregate_daily_sentiment,
    compute_sentiment_features,
    prepare_sentiment_features,
)
```

#### Feature Engineering (`src/features/engineering.py`)
```python
# Core features
add_return_features(price_df) -> pd.DataFrame
add_volatility_features(price_df) -> pd.DataFrame
add_volume_features(price_df) -> pd.DataFrame
add_valuation_features(price_df, fundamental_df) -> pd.DataFrame

# Sentiment integration
add_sentiment_features(base_df, sentiment_df, fillna=0.0) -> pd.DataFrame
compute_all_features_with_sentiment(price_df, news_df, ...) -> pd.DataFrame
get_sentiment_feature_columns(lookbacks) -> List[str]
```

#### SHAP Explainability (`src/explain/shap_explain.py`)
```python
compute_shap_values(model, X) -> Tuple[np.ndarray, explainer]
summarize_feature_importance(shap_values, X) -> pd.Series
get_feature_group(feature_name) -> str  # Returns "Sentiment" for sentiment features
group_features(feature_names) -> Dict[str, List[str]]
compute_portfolio_shap(model, portfolio_features, weights) -> Dict
analyze_sentiment_impact(model, X, feature_names) -> Dict
```

#### Portfolio Optimizer (`src/analysis/portfolio_optimizer.py`)
```python
from src.analysis.portfolio_optimizer import PortfolioOptimizer, InvestorProfile, get_preset_profile

# Use preset profiles
profile = get_preset_profile("moderate")  # conservative, moderate, aggressive

# Or customize
profile = InvestorProfile(
    risk_tolerance="moderate",
    target_annual_return=0.12,
    max_drawdown=0.15,
    max_volatility=0.20,
    time_horizon="medium",
    portfolio_size=10,
    min_position_weight=0.02,
    max_position_weight=0.15,
    max_sector_weight=0.35,
    investment_style="blend",
    dividend_preference="neutral",
    min_quality_score=50.0,
)

# Run optimization
optimizer = PortfolioOptimizer(config, output_dir)
result = optimizer.optimize_portfolio(
    run_id="20251231_114808_abc123",
    profile=profile,
    with_ai_recommendations=True,
)
# Returns: Dict with portfolio, metrics, ai_recommendations, output_files
```

#### Domain Analysis (`src/analysis/domain_analysis.py`)
```python
from src.analysis.domain_analysis import DomainAnalyzer, AnalysisConfig

# Configure analysis
config = AnalysisConfig(
    vertical_weights={"model": 0.5, "value": 0.3, "quality": 0.2},
    fundamental_filters={"min_roe": 0.0, "max_debt_to_equity": 2.0},
    portfolio_size=10,
    min_diversification_score=0.3,
)

# Run analysis
analyzer = DomainAnalyzer(config, output_dir)
vertical_results, horizontal_results = analyzer.run_full_analysis(
    stocks_df=scores_df,
    returns_df=returns_df,
    date=datetime.now(),
)

# Access results
vertical_results.candidates  # Dict[sector, DataFrame]
vertical_results.domain_scores  # DataFrame with composite scores
horizontal_results.portfolio  # Final portfolio DataFrame
horizontal_results.metrics  # Portfolio metrics dict
```

#### AI Recommendations (`src/analysis/gemini_commentary.py`)
```python
from src.analysis.gemini_commentary import (
    generate_portfolio_recommendations,
    save_recommendations_to_file,
)

# Generate multi-profile recommendations
recommendations = generate_portfolio_recommendations(
    all_stocks_df=scores_df,
    portfolio_df=portfolio_df,
    metrics=metrics_dict,
    config=config_dict,
    risk_profile_params={
        "risk_tolerance": "moderate",
        "target_annual_return": 0.12,
        "max_drawdown": 0.15,
        "time_horizon": "medium",
    },
)

# Save to files
save_recommendations_to_file(recommendations, "portfolio_2025", output_dir, "md")
save_recommendations_to_file(recommendations, "portfolio_2025", output_dir, "json")
```

---

## When to Use Each System

### Use Stockbot When:
- You need **real-time monitoring** and signals
- You want an **interactive web dashboard**
- You're doing **short-term trading** (days to weeks)
- You need **live trading execution** via Tiger Brokers
- You want **CAN SLIM analysis** and pattern recognition
- You prefer **rule-based** signals with clear thresholds

### Use Mid-term Stock Planner When:
- You're a **quantitative researcher**
- You focus on **3-month horizons** with monthly rebalancing
- You need **ML-based** cross-sectional ranking
- You want **SHAP explainability** for model decisions
- You need **rigorous backtesting** with walk-forward validation
- You want to **A/B test** sentiment features
- You need **portfolio-level** risk analysis
- You want **multiple sentiment models** (Lexicon, TextBlob, FinBERT)
- You want **personalized portfolio optimization** with investor profiles
- You need **vertical/horizontal analysis** for systematic stock selection
- You want **AI-powered recommendations** with risk assessments
- You need **organized output** with per-run folders

### Use Both Together:
1. **Research Phase**: Use Mid-term Stock Planner to develop and backtest strategies
2. **Signal Generation**: Use Mid-term Stock Planner to generate monthly rankings
3. **Execution & Monitoring**: Use Stockbot dashboard for execution and real-time monitoring
4. **Sentiment Cross-check**: Compare sentiment signals from both systems

---

## Module Mapping

| Stockbot Module | Mid-term Stock Planner Equivalent |
|-----------------|----------------------------------|
| `src/api/` | `src/data/loader.py` + yfinance |
| `src/indicators/` | `src/indicators/technical.py` |
| `src/sentiment/analyzer.py` | `src/sentiment/multi_source_analyzer.py` |
| `src/fundamental/` | `src/fundamental/` |
| `src/analysis/` | `src/features/engineering.py` |
| `src/strategy/` | `src/strategies/` |
| `src/trading/` | `src/backtest/` |
| `src/dashboard/` | `src/app/dashboard.py` (Streamlit) |
| `src/visualization/` | `src/visualization/` |
| `src/risk/` | `src/risk/` |
| ❌ | `src/analysis/portfolio_optimizer.py` |
| ❌ | `src/analysis/domain_analysis.py` |
| ❌ | `src/analysis/gemini_commentary.py` |
| ❌ | `src/analytics/ai_insights.py` |
| ❌ | `src/analytics/manager.py` |

---

## Configuration

### Mid-term Stock Planner Sentiment Config

```yaml
# config/config.yaml
features:
  use_sentiment: true
  sentiment_lookbacks: [1, 7, 14]
  sentiment_min_count: 1

sentiment:
  model_type: "lexicon"  # lexicon, textblob, finbert
  use_llm: false
  llm_provider: "openai"  # openai, gemini

# API keys (can also use environment variables)
# ALPHA_VANTAGE_API_KEY, NEWS_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY
```

### Environment Variables

```bash
# Sentiment data sources
export ALPHA_VANTAGE_API_KEY="your_key"
export NEWS_API_KEY="your_key"

# LLM providers (optional)
export OPENAI_API_KEY="your_key"
export GEMINI_API_KEY="your_key"
```

---

## Future Integration Opportunities

1. **Unified Data Layer**: Share data fetching between both systems
2. **ML Signals in Stockbot**: Use Mid-term Stock Planner rankings in Stockbot dashboard
3. **Real-time Sentiment**: Stream news and compute live sentiment
4. **Combined Dashboard**: Web UI showing both short-term signals and ML rankings
5. **Unified Backtesting**: Compare rule-based vs ML strategies head-to-head
6. **Portfolio Builder in Stockbot**: Expose personalized optimization via Stockbot's REST API
7. **Domain Analysis Reports**: Generate vertical/horizontal analysis for Stockbot watchlists
8. **Cross-System AI Insights**: Use Gemini to compare signals from both systems
9. **Unified Risk Dashboard**: Combined risk metrics from both systems
10. **Automated Rebalancing**: Use Mid-term Planner portfolios as Stockbot trading signals