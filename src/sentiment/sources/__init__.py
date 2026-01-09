"""Sentiment data sources module.

This module provides integrations with various news and sentiment data sources.
"""

from .alpha_vantage import AlphaVantageNewsSource
from .newsapi import NewsAPISource
from .rss_feeds import RSSFeedSource
from .base import SentimentSource, NewsArticle

__all__ = [
    "SentimentSource",
    "NewsArticle",
    "AlphaVantageNewsSource",
    "NewsAPISource",
    "RSSFeedSource",
]
