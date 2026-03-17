# Sentiment Modelling

> [← Back to Documentation Index](README.md)

This document describes the sentiment analysis module for the Mid-term Stock Planner.

## Overview

Sentiment analysis adds news-based sentiment as additional numeric features to the existing cross-sectional model. The key design principles are:

1. **Feature Integration**: Sentiment scores are treated as additional numeric features, not a separate model
2. **No Look-Ahead**: Only news published before the as-of date is used
3. **Interpretability**: Sentiment features appear in SHAP explanations alongside other factors
4. **A/B Testable**: Easy comparison of model performance with and without sentiment

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SENTIMENT DATA FLOW                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Raw News Data                                                       │
│       │                                                              │
│       ▼                                                              │
│  ┌─────────────────┐                                                 │
│  │  news_loader.py │ ← Load, validate, filter by date               │
│  └────────┬────────┘                                                 │
│           │                                                          │
│           ▼                                                          │
│  ┌─────────────────────┐                                             │
│  │ sentiment_model.py  │ ← Score text (lexicon/FinBERT)             │
│  └────────┬────────────┘                                             │
│           │                                                          │
│           ▼                                                          │
│  ┌─────────────────┐                                                 │
│  │  aggregator.py  │ ← Aggregate to daily/rolling features          │
│  └────────┬────────┘                                                 │
│           │                                                          │
│           ▼                                                          │
│  ┌─────────────────┐                                                 │
│  │ engineering.py  │ ← Merge with price features                    │
│  └────────┬────────┘                                                 │
│           │                                                          │
│           ▼                                                          │
│  Training Dataset with Sentiment Features                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Module Structure

### `src/sentiment/`

#### `news_loader.py`

Handles loading and filtering of news data:

```python
from src.sentiment import load_news_data, filter_news_to_asof

# Load news data
news_df = load_news_data("data/news.csv")

# Filter to avoid look-ahead bias
news_as_of = filter_news_to_asof(news_df, as_of="2024-01-15")
```

**Expected News Data Format:**
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| timestamp | datetime | Yes | Publication time (timezone-aware preferred) |
| ticker | str | Yes | Stock ticker(s) mentioned |
| headline | str | Yes | Article headline |
| body | str | No | Article body text |
| source | str | No | News source |
| news_id | str | No | Unique identifier |

#### `sentiment_model.py`

Provides sentiment scoring interfaces:

```python
from src.sentiment import LexiconSentimentModel, score_news_items

# Create model
model = LexiconSentimentModel()

# Score news items
scored_df = score_news_items(news_df, text_col="headline", model=model)
# Adds 'sentiment_raw' column with scores in [-1, 1]
```

**Available Models:**
- `DummySentimentModel`: Random scores for testing
- `LexiconSentimentModel`: Dictionary-based scoring (default for MVP)
- `FinBERTSentimentModel`: Transformer-based (requires transformers + torch)

#### `aggregator.py`

Aggregates per-article sentiment to per-ticker features:

```python
from src.sentiment import (
    align_to_trading_dates,
    aggregate_daily_sentiment,
    compute_sentiment_features,
)

# Align news to trading dates
df = align_to_trading_dates(scored_df, market_close_hour=16)

# Aggregate to daily
daily_df = aggregate_daily_sentiment(df)

# Compute rolling features
feature_df = compute_sentiment_features(daily_df, lookbacks=[1, 7, 14])
```

**Generated Features:**
| Feature | Description |
|---------|-------------|
| sentiment_mean_{N}d | Rolling mean sentiment over N days |
| sentiment_std_{N}d | Rolling std of sentiment over N days |
| sentiment_count_{N}d | Number of articles over N days |
| sentiment_trend_{N}d | Recent vs older sentiment (momentum) |

## Integration with Feature Engineering

```python
from src.features.engineering import compute_all_features_with_sentiment

# Compute all features including sentiment
features_df = compute_all_features_with_sentiment(
    price_df=prices,
    fundamental_df=fundamentals,
    news_df=news,
    sentiment_lookbacks=[1, 7, 14],
    sentiment_model_type="lexicon",
    sentiment_fillna=0.0,  # Neutral for missing
)
```

## Configuration

### YAML Configuration

```yaml
features:
  use_sentiment: true
  sentiment_source: "news"
  sentiment_lookbacks: [1, 7, 14]
  sentiment_min_count: 1
  sentiment_fillna: 0.0

sentiment:
  news_data_path: "data/news.csv"
  model_type: "lexicon"  # dummy, lexicon, finbert
  text_column: "headline"
  market_close_hour: 16
  timezone: "US/Eastern"
  lookbacks: [1, 7, 14]
  min_daily_count: 1
  include_volume_features: true
  include_trend_features: true
  fillna_value: 0.0
```

### Python Configuration

```python
from src.config import FeatureConfig, SentimentConfig

feature_config = FeatureConfig(
    use_sentiment=True,
    sentiment_lookbacks=[1, 7, 14],
)

sentiment_config = SentimentConfig(
    news_data_path="data/news.csv",
    model_type="lexicon",
)
```

## A/B Backtest Comparison

Compare model performance with and without sentiment:

```python
from src.backtest.comparison import run_ab_backtest, format_comparison_report

# Get feature sets
all_features = get_feature_columns(training_data)
non_sentiment, sentiment = get_sentiment_feature_columns(all_features)

# Run comparison
comparison = run_ab_backtest(
    training_data=training_data,
    benchmark_data=benchmark,
    price_data=prices,
    feature_cols_baseline=non_sentiment,
    feature_cols_variant=all_features,
    backtest_config=backtest_config,
)

# Generate report
print(format_comparison_report(comparison))
```

**Sample Output:**
```
============================================================
A/B BACKTEST COMPARISON
============================================================

Baseline: Without Sentiment
Variant:  With Sentiment

------------------------------------------------------------
Metric               Baseline      Variant         Diff
------------------------------------------------------------
total_return           12.34%       14.56%       +2.22%
sharpe                 0.8542       0.9123      +0.0581
max_drawdown          -15.23%      -14.87%       +0.36%
------------------------------------------------------------

RESULT: Sentiment IMPROVES Sharpe by 0.0581
```

## SHAP Explainability

### Feature Grouping

Sentiment features are automatically grouped in SHAP explanations:

```python
from src.explain.shap_explain import (
    get_feature_group,
    summarize_importance_by_group,
    analyze_sentiment_impact,
)

# Get feature group
group = get_feature_group("sentiment_mean_7d")  # Returns "Sentiment"

# Group-level importance
group_importance = summarize_importance_by_group(shap_values, X)
# Returns: {"Sentiment": 0.15, "Return": 0.35, "Volatility": 0.20, ...}

# Analyze sentiment impact
impact = analyze_sentiment_impact(model, X, feature_names)
# Returns:
# {
#     "sentiment_importance": 0.15,
#     "sentiment_pct_of_total": 12.5,
#     "top_sentiment_feature": "sentiment_mean_7d",
# }
```

### Portfolio-Level SHAP

```python
from src.explain.shap_explain import compute_portfolio_shap

# Portfolio-level attribution
portfolio_shap = compute_portfolio_shap(
    model=model,
    portfolio_features=portfolio_df,
    weights=weights,
    feature_names=feature_names,
)

# Access sentiment contribution
print(f"Sentiment contribution: {portfolio_shap['sentiment_contribution']:.4f}")
print(f"Dominant factor: {portfolio_shap['dominant_factor']}")
```

## Look-Ahead Prevention

The module enforces strict no look-ahead rules:

1. **filter_news_to_asof()**: Only returns news with `timestamp <= as_of`
2. **align_to_trading_dates()**: News after market close maps to next trading day
3. **Rolling Features**: Use `shift()` to ensure only past data is used

```python
# Example: Building features for 2024-01-15
# Only news published before market close on 2024-01-15 is used
features = filter_news_to_asof(news_df, as_of="2024-01-15 16:00:00")
```

## Best Practices

### 1. Data Quality
- Ensure news timestamps are accurate and timezone-aware
- Handle multi-ticker articles appropriately (use `expand_multi_ticker_news()`)
- Monitor for gaps in news coverage

### 2. Feature Selection
- Start with short lookbacks (1, 7 days) for responsive sentiment
- Include longer lookbacks (14, 30 days) for regime detection
- Consider news volume features alongside sentiment

### 3. Model Selection
- Use `LexiconSentimentModel` for fast, interpretable baseline
- Upgrade to `FinBERTSentimentModel` for better accuracy (requires GPU)
- Test both and compare in backtests

### 4. Evaluation
- Always run A/B comparison before deploying sentiment features
- Check for overfitting: compare in-sample vs out-of-sample improvement
- Monitor sentiment's SHAP contribution over time

## Example: End-to-End Pipeline

```python
from src.sentiment import load_news_data, score_news_items, prepare_sentiment_features
from src.features.engineering import add_sentiment_features
from src.backtest.comparison import compare_backtests

# 1. Load and score news
news_df = load_news_data("data/news.csv")
news_df = score_news_items(news_df, model_type="lexicon")

# 2. Prepare sentiment features
sentiment_features = prepare_sentiment_features(
    news_df,
    lookbacks=[1, 7, 14],
)

# 3. Merge with price features
full_features = add_sentiment_features(
    base_feature_df=price_features,
    sentiment_feature_df=sentiment_features,
)

# 4. Run backtest comparison
comparison = compare_backtests(
    baseline_results=backtest_without_sentiment,
    variant_results=backtest_with_sentiment,
)

# 5. Analyze results
print(f"Sharpe improvement: {comparison.metric_differences['sharpe']:.4f}")
```

## Future Extensions

1. **Social Media Sentiment**: Twitter/Reddit integration
2. **Earnings Call Sentiment**: Transcript analysis
3. **Multi-Language Support**: Non-English news sources
4. **Real-Time Scoring**: Streaming sentiment updates
5. **Custom Lexicons**: Industry-specific word lists

## CLI Commands

### Run Backtest with Sentiment

```bash
# Enable sentiment features (overrides config)
python -m src.app.cli run-backtest --config config.yaml --use-sentiment

# Disable sentiment features (overrides config)
python -m src.app.cli run-backtest --config config.yaml --no-sentiment
```

### A/B Backtest Comparison

Run two backtests (with and without sentiment) and compare results:

```bash
python -m src.app.cli run-backtest-ab \
    --config config/config.yaml \
    --news-data data/news.csv \
    --output output/ab_comparison \
    --format text
```

Output formats:
- `text`: Plain text report
- `markdown`: Markdown-formatted report
- `json`: JSON data for further analysis

### Score Latest with Sentiment

```bash
# Score with sentiment features
python -m src.app.cli score-latest \
    --config config.yaml \
    --model models/latest \
    --use-sentiment \
    --explanations

# Score without sentiment
python -m src.app.cli score-latest \
    --config config.yaml \
    --model models/latest \
    --no-sentiment
```

### Compare Sentiment Impact

```bash
python -m src.app.cli compare-sentiment \
    --config config.yaml \
    --news-data data/news.csv \
    --format markdown \
    --output comparison_report.md
```

## Data Paths in Config

The news data path can be specified in two places in the config:

```yaml
# In data section (recommended)
data:
  sentiment_news_path: "data/news.csv"

# Or in sentiment section
sentiment:
  news_data_path: "data/news.csv"
```

The CLI `--news-data` flag overrides both config values.

---

## See Also

- [AI-powered analysis](ai-insights.md)
- [Fundamental data](fundamental-data.md)
- [API key setup for Gemini](api-configuration.md)
- [Feature engineering pipeline](data-engineering.md)
