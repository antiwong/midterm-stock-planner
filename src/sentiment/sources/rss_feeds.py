"""RSS feed sentiment source."""

import os
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
import logging

from .base import SentimentSource, NewsArticle

logger = logging.getLogger(__name__)

# Check if feedparser is available
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logger.warning("feedparser not installed. RSS feeds disabled. Install with: pip install feedparser")


# Default financial RSS feeds
DEFAULT_RSS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://www.marketwatch.com/rss/topstories",
    "https://seekingalpha.com/market_currents.xml",
]


class RSSFeedSource(SentimentSource):
    """Fetch news from RSS feeds."""
    
    def __init__(
        self,
        feeds_file: Optional[str] = None,
        feeds: Optional[List[str]] = None,
    ):
        """
        Initialize RSS feed source.
        
        Args:
            feeds_file: Path to file containing RSS feed URLs (one per line)
            feeds: List of RSS feed URLs to use
        """
        self.feeds = feeds or []
        
        # Load feeds from file if provided
        if feeds_file:
            self._load_feeds_from_file(feeds_file)
        
        # Use defaults if no feeds configured
        if not self.feeds:
            self.feeds = DEFAULT_RSS_FEEDS.copy()
            
    def _load_feeds_from_file(self, feeds_file: str) -> None:
        """Load RSS feed URLs from file."""
        path = Path(feeds_file)
        if not path.exists():
            # Try relative paths
            for base in [".", "data", "../data"]:
                alt_path = Path(base) / feeds_file
                if alt_path.exists():
                    path = alt_path
                    break
        
        if path.exists():
            try:
                with open(path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            self.feeds.append(line)
                logger.info(f"Loaded {len(self.feeds)} RSS feeds from {path}")
            except Exception as e:
                logger.warning(f"Could not load RSS feeds from {path}: {e}")
        else:
            logger.debug(f"RSS feeds file not found: {feeds_file}")
    
    @property
    def name(self) -> str:
        return "rss"
    
    def is_available(self) -> bool:
        return FEEDPARSER_AVAILABLE and len(self.feeds) > 0
    
    def fetch_news(
        self,
        ticker: str,
        days: int = 7,
        max_articles: int = 50,
        keywords: Optional[List[str]] = None,
    ) -> List[NewsArticle]:
        """
        Fetch news from RSS feeds matching ticker/keywords.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back
            max_articles: Maximum articles to return
            keywords: Additional keywords to search for
            
        Returns:
            List of NewsArticle objects (sentiment not included, needs scoring)
        """
        if not FEEDPARSER_AVAILABLE:
            logger.warning("feedparser not available. RSS news disabled.")
            return []
        
        if not self.feeds:
            logger.warning("No RSS feeds configured")
            return []
        
        # Build search terms
        search_terms = [ticker.lower()]
        if keywords:
            search_terms.extend([k.lower() for k in keywords])
        
        cutoff_date = datetime.now() - timedelta(days=days)
        articles = []
        seen_urls = set()
        
        for feed_url in self.feeds:
            try:
                feed = feedparser.parse(feed_url)
                feed_name = feed.feed.get("title", feed_url)
                
                for entry in feed.entries:
                    title = entry.get("title", "") or ""
                    summary = entry.get("summary", "") or ""
                    link = entry.get("link", "") or ""
                    
                    # Skip duplicates
                    if link in seen_urls:
                        continue
                    
                    # Check if any search term matches
                    text_lower = f"{title} {summary}".lower()
                    matched = any(term in text_lower for term in search_terms)
                    
                    if not matched:
                        continue
                    
                    # Parse published date
                    pub_parsed = entry.get("published_parsed")
                    if pub_parsed:
                        try:
                            timestamp = datetime(*pub_parsed[:6])
                        except (TypeError, ValueError):
                            timestamp = datetime.now()
                    else:
                        timestamp = datetime.now()
                    
                    # Skip if older than cutoff
                    if timestamp < cutoff_date:
                        continue
                    
                    seen_urls.add(link)
                    
                    article = NewsArticle(
                        title=title,
                        url=link,
                        timestamp=timestamp,
                        ticker=ticker,
                        body=summary,
                        source=feed_name,
                        sentiment_score=None,  # Will be scored separately
                        metadata={
                            "feed_url": feed_url,
                            "matched_terms": [t for t in search_terms if t in text_lower],
                        }
                    )
                    articles.append(article)
                    
                    if len(articles) >= max_articles:
                        break
                        
            except Exception as e:
                logger.warning(f"Error parsing RSS feed {feed_url}: {e}")
                continue
            
            if len(articles) >= max_articles:
                break
        
        # Sort by timestamp (newest first)
        articles.sort(key=lambda x: x.timestamp, reverse=True)
        
        logger.info(f"Fetched {len(articles)} articles from RSS feeds for {ticker}")
        return articles[:max_articles]
