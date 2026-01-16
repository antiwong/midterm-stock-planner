"""Massive API (formerly Polygon.io) fundamentals fetcher.

This module provides a dedicated fetcher for Massive API fundamentals data.
Reference: https://massive.com/docs/rest/quickstart
"""

import logging
import time
from typing import Dict, Optional, Any
import requests

logger = logging.getLogger(__name__)


class MassiveFundamentalsFetcher:
    """Fetch fundamentals from Massive API (formerly Polygon.io)."""
    
    BASE_URL = "https://api.massive.com/v2/reference/financials"
    RATE_LIMIT_DELAY = 12  # 12 seconds between requests (safe for 5/min limit)
    
    def __init__(self, api_key: str):
        """
        Initialize Massive API fetcher.
        
        Args:
            api_key: Massive API key
        """
        self.api_key = api_key
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.RATE_LIMIT_DELAY:
            sleep_time = self.RATE_LIMIT_DELAY - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or value == 'None' or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def fetch_ratios(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch financial ratios from Massive API.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with financial ratios, or None if error
        """
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/ratios"
            params = {
                'ticker': ticker,
                'apiKey': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'OK' or not data.get('results'):
                return None
            
            # Extract the most recent ratio data
            results = data.get('results', [])
            if not results:
                return None
            
            # Get the latest ratio data
            latest = results[0] if isinstance(results, list) else results
            
            # Map Massive API fields to our format
            return {
                'pe': self._safe_float(latest.get('priceToEarningsRatio')),
                'pb': self._safe_float(latest.get('priceToBookRatio')),
                'ps': self._safe_float(latest.get('priceToSalesRatio')),
                'peg': self._safe_float(latest.get('pegRatio')),
                'roe': self._safe_float(latest.get('returnOnEquity')),
                'roa': self._safe_float(latest.get('returnOnAssets')),
                'net_margin': self._safe_float(latest.get('netProfitMargin')),
                'gross_margin': self._safe_float(latest.get('grossProfitMargin')),
                'operating_margin': self._safe_float(latest.get('operatingProfitMargin')),
                'debt_to_equity': self._safe_float(latest.get('debtToEquity')),
                'current_ratio': self._safe_float(latest.get('currentRatio')),
                'quick_ratio': self._safe_float(latest.get('quickRatio')),
                'revenue_growth': self._safe_float(latest.get('revenueGrowth')),
                'earnings_growth': self._safe_float(latest.get('earningsGrowth')),
                'market_cap': self._safe_float(latest.get('marketCapitalization')),
                'enterprise_value': self._safe_float(latest.get('enterpriseValue')),
                'dividend_yield': self._safe_float(latest.get('dividendYield')),
                'beta': self._safe_float(latest.get('beta')),
            }
        except Exception as e:
            logger.debug(f"Massive API error for {ticker}: {e}")
            return None
