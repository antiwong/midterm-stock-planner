"""Sentiment analysis module for mid-term stock planner.

This module provides comprehensive sentiment analysis from multiple sources:
- Alpha Vantage News API
- NewsAPI
- RSS Feeds
- LLM-powered analysis (OpenAI, Gemini)

Features:
- Multiple sentiment models (Lexicon, TextBlob, FinBERT)
- Rolling sentiment features for ML models
- Look-ahead bias prevention
- A/B testing support
"""

# News loading and filtering
from .news_loader import (
    load_news_data,
    filter_news_to_asof,
    validate_news_data,
    create_sample_news_data,
)

# Sentiment models
from .sentiment_model import (
    SentimentModel,
    DummySentimentModel,
    LexiconSentimentModel,
    TextBlobSentimentModel,
    FinBERTSentimentModel,
    get_sentiment_model,
    score_texts,
    score_news_items,
)

# Aggregation and feature engineering
from .aggregator import (
    align_to_trading_dates,
    aggregate_daily_sentiment,
    compute_sentiment_features,
    prepare_sentiment_features,
)

# Data sources
from .sources import (
    SentimentSource,
    NewsArticle,
    AlphaVantageNewsSource,
    NewsAPISource,
    RSSFeedSource,
)

# LLM analysis
from .llm_analyzer import (
    LLMSentimentAnalyzer,
    LLMAnalysisResult,
)

# Multi-source analyzer
from .multi_source_analyzer import MultiSourceSentimentAnalyzer

__all__ = [
    # News loading
    "load_news_data",
    "filter_news_to_asof",
    "validate_news_data",
    "create_sample_news_data",
    # Sentiment models
    "SentimentModel",
    "DummySentimentModel",
    "LexiconSentimentModel",
    "TextBlobSentimentModel",
    "FinBERTSentimentModel",
    "get_sentiment_model",
    "score_texts",
    "score_news_items",
    # Aggregation
    "align_to_trading_dates",
    "aggregate_daily_sentiment",
    "compute_sentiment_features",
    "prepare_sentiment_features",
    # Data sources
    "SentimentSource",
    "NewsArticle",
    "AlphaVantageNewsSource",
    "NewsAPISource",
    "RSSFeedSource",
    # LLM
    "LLMSentimentAnalyzer",
    "LLMAnalysisResult",
    # Multi-source
    "MultiSourceSentimentAnalyzer",
]
