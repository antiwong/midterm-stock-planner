"""Base classes for sentiment data sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd


@dataclass
class NewsArticle:
    """Represents a news article with sentiment data."""
    title: str
    url: str
    timestamp: datetime
    ticker: str
    body: Optional[str] = None
    source: Optional[str] = None
    sentiment_score: Optional[float] = None
    relevance_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "ticker": self.ticker,
            "body": self.body,
            "source": self.source,
            "sentiment_score": self.sentiment_score,
            "relevance_score": self.relevance_score,
            **self.metadata,
        }


class SentimentSource(ABC):
    """Abstract base class for sentiment data sources."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this source."""
        pass
    
    @abstractmethod
    def fetch_news(
        self,
        ticker: str,
        days: int = 7,
        max_articles: int = 50,
    ) -> List[NewsArticle]:
        """
        Fetch news articles for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back
            max_articles: Maximum number of articles to return
            
        Returns:
            List of NewsArticle objects
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this source is available (API key configured, etc.)."""
        pass
    
    def to_dataframe(self, articles: List[NewsArticle]) -> pd.DataFrame:
        """Convert articles to DataFrame format expected by aggregator."""
        if not articles:
            return pd.DataFrame(columns=[
                "news_id", "timestamp", "ticker", "headline", "body", "source"
            ])
        
        records = []
        for i, article in enumerate(articles):
            records.append({
                "news_id": f"{self.name}_{i}",
                "timestamp": article.timestamp,
                "ticker": article.ticker,
                "headline": article.title,
                "body": article.body or "",
                "source": article.source or self.name,
                "url": article.url,
                "sentiment_raw": article.sentiment_score,
            })
        
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df
