"""Multi-source sentiment analyzer.

This module provides a unified interface for fetching and analyzing
sentiment from multiple sources (Alpha Vantage, NewsAPI, RSS feeds).
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import pandas as pd
import numpy as np

from .sources.base import SentimentSource, NewsArticle
from .sources.alpha_vantage import AlphaVantageNewsSource
from .sources.newsapi import NewsAPISource
from .sources.rss_feeds import RSSFeedSource
from .sentiment_model import SentimentModel, get_sentiment_model
from .llm_analyzer import LLMSentimentAnalyzer, LLMAnalysisResult
from .aggregator import aggregate_daily_sentiment, compute_sentiment_features

logger = logging.getLogger(__name__)


class MultiSourceSentimentAnalyzer:
    """
    Unified sentiment analyzer that combines multiple news sources.
    
    Features:
    - Fetches news from Alpha Vantage, NewsAPI, and RSS feeds
    - Scores sentiment using lexicon, TextBlob, FinBERT, or LLM
    - Aggregates results into rolling features
    - Provides both real-time and batch analysis
    """
    
    def __init__(
        self,
        # API keys
        alpha_vantage_api_key: Optional[str] = None,
        news_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        # RSS config
        rss_feeds_file: Optional[str] = None,
        rss_feeds: Optional[List[str]] = None,
        # Model config
        sentiment_model_type: str = "lexicon",
        use_llm: bool = False,
        llm_provider: str = "auto",
    ):
        """
        Initialize multi-source analyzer.
        
        Args:
            alpha_vantage_api_key: Alpha Vantage API key
            news_api_key: NewsAPI API key
            openai_api_key: OpenAI API key for LLM analysis
            gemini_api_key: Gemini API key for LLM analysis
            rss_feeds_file: Path to RSS feeds file
            rss_feeds: List of RSS feed URLs
            sentiment_model_type: Type of sentiment model ("lexicon", "textblob", "finbert")
            use_llm: Whether to use LLM for enhanced analysis
            llm_provider: LLM provider ("openai", "gemini", "auto")
        """
        # Initialize sources
        self.sources: Dict[str, SentimentSource] = {}
        
        # Alpha Vantage
        av_source = AlphaVantageNewsSource(api_key=alpha_vantage_api_key)
        if av_source.is_available():
            self.sources["alpha_vantage"] = av_source
            logger.info("Alpha Vantage news source enabled")
        
        # NewsAPI
        newsapi_source = NewsAPISource(api_key=news_api_key)
        if newsapi_source.is_available():
            self.sources["newsapi"] = newsapi_source
            logger.info("NewsAPI source enabled")
        
        # RSS Feeds
        rss_source = RSSFeedSource(feeds_file=rss_feeds_file, feeds=rss_feeds)
        if rss_source.is_available():
            self.sources["rss"] = rss_source
            logger.info(f"RSS feeds source enabled with {len(rss_source.feeds)} feeds")
        
        # Sentiment model
        self.sentiment_model = get_sentiment_model(sentiment_model_type)
        logger.info(f"Using sentiment model: {self.sentiment_model.name}")
        
        # LLM analyzer
        self.use_llm = use_llm
        self.llm_analyzer = None
        if use_llm:
            self.llm_analyzer = LLMSentimentAnalyzer(
                provider=llm_provider,
                openai_api_key=openai_api_key,
                gemini_api_key=gemini_api_key,
            )
            if self.llm_analyzer.is_available():
                logger.info(f"LLM analyzer enabled with provider: {self.llm_analyzer.provider}")
            else:
                logger.warning("LLM analyzer requested but not available")
                self.llm_analyzer = None
    
    @property
    def available_sources(self) -> List[str]:
        """Get list of available source names."""
        return list(self.sources.keys())
    
    def fetch_news(
        self,
        ticker: str,
        days: int = 7,
        max_articles: int = 50,
        sources: Optional[List[str]] = None,
    ) -> List[NewsArticle]:
        """
        Fetch news from all (or specified) sources.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back
            max_articles: Maximum articles per source
            sources: List of source names to use (None = all)
            
        Returns:
            Combined list of NewsArticle objects
        """
        all_articles = []
        seen_urls = set()
        
        sources_to_use = sources or self.available_sources
        
        for source_name in sources_to_use:
            if source_name not in self.sources:
                logger.warning(f"Source {source_name} not available")
                continue
            
            source = self.sources[source_name]
            try:
                articles = source.fetch_news(
                    ticker=ticker,
                    days=days,
                    max_articles=max_articles,
                )
                
                # Deduplicate by URL
                for article in articles:
                    if article.url and article.url not in seen_urls:
                        seen_urls.add(article.url)
                        all_articles.append(article)
                        
            except Exception as e:
                logger.error(f"Error fetching from {source_name}: {e}")
        
        # Sort by timestamp (newest first)
        all_articles.sort(key=lambda x: x.timestamp or datetime.min, reverse=True)
        
        logger.info(f"Fetched {len(all_articles)} unique articles for {ticker}")
        return all_articles
    
    def score_articles(
        self,
        articles: List[NewsArticle],
        use_llm: Optional[bool] = None,
    ) -> List[NewsArticle]:
        """
        Score articles for sentiment.
        
        Args:
            articles: List of NewsArticle objects
            use_llm: Override for LLM usage (None = use init setting)
            
        Returns:
            Articles with sentiment_score populated
        """
        use_llm = use_llm if use_llm is not None else self.use_llm
        
        scored_articles = []
        
        for article in articles:
            # Skip if already scored (e.g., from Alpha Vantage)
            if article.sentiment_score is not None:
                scored_articles.append(article)
                continue
            
            text = f"{article.title} {article.body or ''}"
            
            # Use LLM if enabled and available
            if use_llm and self.llm_analyzer and self.llm_analyzer.is_available():
                try:
                    result = self.llm_analyzer.analyze_article(
                        headline=article.title,
                        body=article.body or "",
                        ticker=article.ticker,
                    )
                    article.sentiment_score = result.sentiment_score
                    article.metadata["llm_analysis"] = {
                        "summary": result.summary,
                        "key_themes": result.key_themes,
                        "risks": result.risks,
                        "opportunities": result.opportunities,
                        "impact_score": result.impact_score,
                    }
                except Exception as e:
                    logger.warning(f"LLM analysis failed, falling back: {e}")
                    article.sentiment_score = self.sentiment_model.score_text(text)
            else:
                # Use standard sentiment model
                article.sentiment_score = self.sentiment_model.score_text(text)
            
            scored_articles.append(article)
        
        return scored_articles
    
    def get_sentiment(
        self,
        ticker: str,
        days: int = 7,
        sources: Optional[List[str]] = None,
        use_llm: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated sentiment for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back
            sources: List of source names to use
            use_llm: Override for LLM usage
            
        Returns:
            Dictionary with sentiment metrics
        """
        # Fetch and score articles
        articles = self.fetch_news(ticker, days=days, sources=sources)
        scored_articles = self.score_articles(articles, use_llm=use_llm)
        
        if not scored_articles:
            return {
                "ticker": ticker,
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "article_count": 0,
                "sources_used": [],
                "articles": [],
                "score_std": 0.0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
            }
        
        # Calculate metrics
        scores = [a.sentiment_score for a in scored_articles if a.sentiment_score is not None]
        sources_used = list(set(a.source for a in scored_articles if a.source))
        
        avg_score = float(np.mean(scores)) if scores else 0.0
        
        # Sentiment label
        if avg_score > 0.1:
            label = "positive"
        elif avg_score < -0.1:
            label = "negative"
        else:
            label = "neutral"
        
        return {
            "ticker": ticker,
            "sentiment_score": avg_score,
            "sentiment_label": label,
            "article_count": len(scored_articles),
            "sources_used": sources_used,
            "articles": [a.to_dict() for a in scored_articles[:20]],  # Top 20
            "score_std": float(np.std(scores)) if len(scores) > 1 else 0.0,
            "positive_count": sum(1 for s in scores if s > 0.1),
            "negative_count": sum(1 for s in scores if s < -0.1),
            "neutral_count": sum(1 for s in scores if -0.1 <= s <= 0.1),
        }
    
    def to_dataframe(
        self,
        ticker: str,
        days: int = 7,
        sources: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Get news as DataFrame suitable for feature engineering.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back
            sources: List of source names to use
            
        Returns:
            DataFrame with columns: news_id, timestamp, ticker, headline, body, source, sentiment_raw
        """
        articles = self.fetch_news(ticker, days=days, sources=sources)
        scored_articles = self.score_articles(articles)
        
        if not scored_articles:
            return pd.DataFrame(columns=[
                "news_id", "timestamp", "ticker", "headline", "body", "source", "sentiment_raw"
            ])
        
        records = []
        for i, article in enumerate(scored_articles):
            records.append({
                "news_id": f"multi_{ticker}_{i}",
                "timestamp": article.timestamp,
                "ticker": article.ticker,
                "headline": article.title,
                "body": article.body or "",
                "source": article.source,
                "sentiment_raw": article.sentiment_score,
                "url": article.url,
            })
        
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df
    
    def compute_features(
        self,
        ticker: str,
        days: int = 30,
        lookbacks: List[int] = [1, 7, 14],
        sources: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Compute rolling sentiment features for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days of news to fetch
            lookbacks: List of lookback periods for rolling features
            sources: List of source names to use
            
        Returns:
            DataFrame with date, ticker, and sentiment features
        """
        # Get news as DataFrame
        news_df = self.to_dataframe(ticker, days=days, sources=sources)
        
        if len(news_df) == 0:
            return pd.DataFrame(columns=["date", "ticker"])
        
        # Aggregate to daily
        daily_df = aggregate_daily_sentiment(news_df, date_col="timestamp")
        
        # Compute rolling features
        features_df = compute_sentiment_features(daily_df, lookbacks=lookbacks)
        
        return features_df
    
    def analyze_batch(
        self,
        tickers: List[str],
        days: int = 7,
        sources: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Analyze sentiment for multiple tickers.
        
        Args:
            tickers: List of stock tickers
            days: Number of days to look back
            sources: List of source names to use
            
        Returns:
            DataFrame with sentiment metrics per ticker
        """
        results = []
        
        for ticker in tickers:
            try:
                sentiment = self.get_sentiment(ticker, days=days, sources=sources)
                results.append({
                    "ticker": ticker,
                    "sentiment_score": sentiment["sentiment_score"],
                    "sentiment_label": sentiment["sentiment_label"],
                    "article_count": sentiment["article_count"],
                    "sources": ", ".join(sentiment["sources_used"]),
                    "positive_count": sentiment["positive_count"],
                    "negative_count": sentiment["negative_count"],
                })
            except Exception as e:
                logger.error(f"Error analyzing {ticker}: {e}")
                results.append({
                    "ticker": ticker,
                    "sentiment_score": 0.0,
                    "sentiment_label": "error",
                    "article_count": 0,
                    "sources": "",
                    "positive_count": 0,
                    "negative_count": 0,
                })
        
        return pd.DataFrame(results)
