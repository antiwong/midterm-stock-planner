"""Alpha Vantage news sentiment source."""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from .base import SentimentSource, NewsArticle

logger = logging.getLogger(__name__)


class AlphaVantageNewsSource(SentimentSource):
    """Fetch news sentiment from Alpha Vantage News API."""
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Alpha Vantage news source.
        
        Args:
            api_key: Alpha Vantage API key. If not provided, reads from 
                     ALPHA_VANTAGE_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        
    @property
    def name(self) -> str:
        return "alpha_vantage"
    
    def is_available(self) -> bool:
        return self.api_key is not None
    
    def fetch_news(
        self,
        ticker: str,
        days: int = 7,
        max_articles: int = 50,
    ) -> List[NewsArticle]:
        """
        Fetch news from Alpha Vantage News Sentiment API.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back (not directly supported by API)
            max_articles: Maximum articles to return
            
        Returns:
            List of NewsArticle objects with sentiment scores
        """
        if not self.is_available():
            logger.warning("Alpha Vantage API key not configured")
            return []
        
        try:
            params = {
                "function": "NEWS_SENTIMENT",
                "tickers": ticker,
                "apikey": self.api_key,
                "limit": min(max_articles, 200),  # API max is 200
            }
            
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "feed" not in data:
                logger.warning(f"No news feed in Alpha Vantage response for {ticker}")
                return []
            
            articles = []
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for item in data["feed"][:max_articles]:
                # Parse timestamp
                time_str = item.get("time_published", "")
                try:
                    timestamp = datetime.strptime(time_str[:15], "%Y%m%dT%H%M%S")
                except (ValueError, IndexError):
                    timestamp = datetime.now()
                
                # Skip if older than cutoff
                if timestamp < cutoff_date:
                    continue
                
                # Get ticker-specific sentiment
                sentiment_score = None
                relevance_score = None
                ticker_sentiments = item.get("ticker_sentiment", [])
                for ts in ticker_sentiments:
                    if ts.get("ticker", "").upper() == ticker.upper():
                        sentiment_score = float(ts.get("ticker_sentiment_score", 0))
                        relevance_score = float(ts.get("relevance_score", 0))
                        break
                
                # Fallback to overall sentiment
                if sentiment_score is None:
                    sentiment_score = float(item.get("overall_sentiment_score", 0))
                
                article = NewsArticle(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    timestamp=timestamp,
                    ticker=ticker,
                    body=item.get("summary", ""),
                    source=item.get("source", "Alpha Vantage"),
                    sentiment_score=sentiment_score,
                    relevance_score=relevance_score,
                    metadata={
                        "overall_sentiment_label": item.get("overall_sentiment_label"),
                        "topics": [t.get("topic") for t in item.get("topics", [])],
                    }
                )
                articles.append(article)
            
            logger.info(f"Fetched {len(articles)} articles from Alpha Vantage for {ticker}")
            return articles
            
        except requests.RequestException as e:
            logger.error(f"Alpha Vantage API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error processing Alpha Vantage news: {e}")
            return []
