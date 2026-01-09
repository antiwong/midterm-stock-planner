#!/usr/bin/env python3
"""Test script for sentiment module."""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def test_sentiment_module():
    """Test the sentiment module components."""
    print("=" * 60)
    print("Testing Sentiment Module")
    print("=" * 60)
    
    # Test 1: News Loader
    print("\n1. Testing news_loader.py")
    print("-" * 40)
    
    from src.sentiment.news_loader import (
        create_sample_news_data,
        filter_news_to_asof,
        validate_news_data,
    )
    
    # Create sample news data
    tickers = ["AAPL", "MSFT", "GOOGL", "AMD", "AMZN"]
    news_df = create_sample_news_data(
        tickers=tickers,
        start_date="2024-01-01",
        end_date="2024-03-01",
        items_per_ticker_per_day=1.5,
    )
    print(f"Created {len(news_df)} sample news items")
    print(f"Date range: {news_df['timestamp'].min()} to {news_df['timestamp'].max()}")
    print(f"Sample headlines:")
    for idx, row in news_df.head(3).iterrows():
        print(f"  - {row['headline'][:60]}...")
    
    # Test filtering
    as_of = pd.Timestamp("2024-02-01")
    filtered = filter_news_to_asof(news_df, as_of=as_of)
    print(f"\nFiltered to as_of={as_of}: {len(filtered)} items")
    
    # Test 2: Sentiment Model
    print("\n2. Testing sentiment_model.py")
    print("-" * 40)
    
    from src.sentiment.sentiment_model import (
        LexiconSentimentModel,
        DummySentimentModel,
        score_news_items,
    )
    
    # Test lexicon model
    model = LexiconSentimentModel()
    
    test_texts = [
        "Apple beats earnings expectations",
        "Microsoft misses revenue targets",
        "Amazon announces new product launch",
        "Google faces regulatory scrutiny",
        "AMD reports strong revenue growth",
    ]
    
    scores = model.score_texts(test_texts)
    print("Lexicon model scores:")
    for text, score in zip(test_texts, scores):
        sentiment = "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
        print(f"  [{score:+.2f}] ({sentiment}) {text[:50]}...")
    
    # Score all news items
    scored_df = score_news_items(news_df, model=model, text_col="headline")
    print(f"\nScored {len(scored_df)} news items")
    print(f"Sentiment distribution:")
    print(f"  Mean:   {scored_df['sentiment_raw'].mean():.4f}")
    print(f"  Std:    {scored_df['sentiment_raw'].std():.4f}")
    print(f"  Min:    {scored_df['sentiment_raw'].min():.4f}")
    print(f"  Max:    {scored_df['sentiment_raw'].max():.4f}")
    
    # Test 3: Aggregator
    print("\n3. Testing aggregator.py")
    print("-" * 40)
    
    from src.sentiment.aggregator import (
        align_to_trading_dates,
        aggregate_daily_sentiment,
        compute_sentiment_features,
        prepare_sentiment_features,
    )
    
    # Align to trading dates
    aligned_df = align_to_trading_dates(scored_df)
    print(f"Aligned news to trading dates")
    
    # Aggregate to daily
    daily_df = aggregate_daily_sentiment(aligned_df, date_col="trading_date")
    print(f"Aggregated to {len(daily_df)} daily records")
    
    # Compute rolling features
    feature_df = compute_sentiment_features(daily_df, lookbacks=[1, 7, 14])
    print(f"Computed rolling features")
    print(f"Feature columns: {[c for c in feature_df.columns if 'sentiment' in c]}")
    
    # Show sample
    print(f"\nSample features for AAPL:")
    aapl_features = feature_df[feature_df['ticker'] == 'AAPL'].tail(5)
    print(aapl_features[['date', 'ticker', 'sentiment_mean_7d', 'sentiment_trend_7d']].to_string())
    
    # Test 4: Feature Engineering Integration
    print("\n4. Testing feature engineering integration")
    print("-" * 40)
    
    from src.features.engineering import (
        get_sentiment_feature_columns,
        add_sentiment_features,
    )
    
    # Get expected column names
    sentiment_cols = get_sentiment_feature_columns(lookbacks=[1, 7, 14])
    print(f"Expected sentiment feature columns: {sentiment_cols}")
    
    # Create mock price data
    dates = pd.date_range("2024-01-15", "2024-02-28", freq="D")
    price_df = pd.DataFrame([
        {"date": date, "ticker": ticker, "close": 100 + np.random.randn()}
        for date in dates
        for ticker in tickers
    ])
    
    # Merge sentiment features
    merged_df = add_sentiment_features(price_df, feature_df, fillna_value=0.0)
    print(f"Merged features: {len(merged_df)} rows")
    n_sentiment_cols = sum(1 for c in merged_df.columns if c.startswith('sentiment_'))
    print(f"Sentiment columns added: {n_sentiment_cols}")
    
    # Test 5: SHAP Feature Grouping
    print("\n5. Testing SHAP feature grouping")
    print("-" * 40)
    
    from src.explain.shap_explain import (
        get_feature_group,
        group_features,
    )
    
    test_features = [
        "return_1m", "return_3m",
        "vol_20d", "vol_60d",
        "pe_ratio", "pb_ratio",
        "sentiment_mean_1d", "sentiment_mean_7d", "sentiment_trend_7d",
        "rsi_14", "macd",
    ]
    
    print("Feature groupings:")
    for feat in test_features:
        group = get_feature_group(feat)
        print(f"  {feat} -> {group}")
    
    groups = group_features(test_features)
    print(f"\nGrouped features: {groups}")
    
    # Test 6: A/B Comparison utilities
    print("\n6. Testing A/B comparison utilities")
    print("-" * 40)
    
    from src.backtest.comparison import (
        compare_backtests,
        format_comparison_report,
        get_sentiment_feature_columns as get_sentiment_cols,
    )
    
    # Mock backtest results
    baseline_results = {
        "metrics": {
            "total_return": 0.12,
            "sharpe": 0.85,
            "max_drawdown": -0.15,
            "volatility": 0.18,
        }
    }
    variant_results = {
        "metrics": {
            "total_return": 0.15,
            "sharpe": 0.92,
            "max_drawdown": -0.14,
            "volatility": 0.17,
        }
    }
    
    comparison = compare_backtests(
        baseline_results=baseline_results,
        variant_results=variant_results,
    )
    
    print("Comparison results:")
    print(f"  Sharpe diff: {comparison.metric_differences.get('sharpe', 'N/A'):.4f}")
    print(f"  Return diff: {comparison.metric_differences.get('total_return', 'N/A'):.2%}")
    
    report = format_comparison_report(comparison, format="text")
    print("\nFormatted report:")
    print(report[:500] + "...")
    
    print("\n" + "=" * 60)
    print("All sentiment module tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    test_sentiment_module()
