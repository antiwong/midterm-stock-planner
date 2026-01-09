"""NewsAPI sentiment source."""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from .base import SentimentSource, NewsArticle

logger = logging.getLogger(__name__)


class NewsAPISource(SentimentSource):
    """Fetch news from NewsAPI.org."""
    
    BASE_URL = "https://newsapi.org/v2/everything"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize NewsAPI source.
        
        Args:
            api_key: NewsAPI API key. If not provided, reads from 
                     NEWS_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv("NEWS_API_KEY")
        
    @property
    def name(self) -> str:
        return "newsapi"
    
    def is_available(self) -> bool:
        return self.api_key is not None
    
    def fetch_news(
        self,
        ticker: str,
        days: int = 7,
        max_articles: int = 50,
    ) -> List[NewsArticle]:
        """
        Fetch news from NewsAPI.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back
            max_articles: Maximum articles to return
            
        Returns:
            List of NewsArticle objects (sentiment not included, needs scoring)
        """
        if not self.is_available():
            logger.warning("NewsAPI API key not configured")
            return []
        
        try:
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # Build search query
            query = f"{ticker} stock OR {ticker} shares OR {ticker} earnings"
            
            params = {
                "q": query,
                "from": from_date,
                "sortBy": "relevancy",
                "apiKey": self.api_key,
                "language": "en",
                "pageSize": min(max_articles, 100),  # API max is 100
            }
            
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "ok" or "articles" not in data:
                logger.warning(f"NewsAPI returned no articles for {ticker}")
                return []
            
            articles = []
            for item in data["articles"][:max_articles]:
                # Parse timestamp
                pub_date = item.get("publishedAt", "")
                try:
                    timestamp = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    timestamp = datetime.now()
                
                article = NewsArticle(
                    title=item.get("title", "") or "",
                    url=item.get("url", "") or "",
                    timestamp=timestamp,
                    ticker=ticker,
                    body=item.get("description", "") or item.get("content", "") or "",
                    source=item.get("source", {}).get("name", "NewsAPI"),
                    sentiment_score=None,  # Will be scored separately
                    metadata={
                        "author": item.get("author"),
                        "image_url": item.get("urlToImage"),
                    }
                )
                articles.append(article)
            
            logger.info(f"Fetched {len(articles)} articles from NewsAPI for {ticker}")
            return articles
            
        except requests.RequestException as e:
            logger.error(f"NewsAPI request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error processing NewsAPI news: {e}")
            return []
