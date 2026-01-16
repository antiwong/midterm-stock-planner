"""Multi-source fundamental data fetcher with fallback support.

This module fetches fundamental data from multiple sources in order of preference:
1. Yahoo Finance (yfinance) - Primary, no API key required
2. Alpha Vantage - Free tier: 5 req/min, 500 req/day
3. Massive (formerly Polygon.io) - Free tier: 5 req/min
4. Finnhub - Free tier: 60 req/min

Data is merged from multiple sources to maximize completeness.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import warnings

import pandas as pd
import numpy as np

# Primary source (always available)
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    warnings.warn("yfinance not installed. Install with: pip install yfinance")

# Alternative sources (optional)
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    warnings.warn("requests not installed. Install with: pip install requests")

from src.config.api_keys import load_api_keys

logger = logging.getLogger(__name__)


class MultiSourceFundamentalsFetcher:
    """Fetch fundamentals from multiple sources with automatic fallback."""
    
    def __init__(self):
        """Initialize multi-source fetcher."""
        self.api_keys = load_api_keys()
        self.last_request_times = {}  # For rate limiting
        
    def fetch_fundamentals(self, ticker: str, sources: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch fundamentals from multiple sources, merging results.
        
        Args:
            ticker: Stock ticker symbol
            sources: List of sources to try (default: all available)
                    Options: 'yfinance', 'alpha_vantage', 'polygon', 'finnhub'
        
        Returns:
            Dictionary with merged fundamental data, or None if all sources fail
        """
        if sources is None:
            sources = ['yfinance', 'alpha_vantage', 'massive', 'finnhub']
        
        all_data = {}
        
        # Try each source in order
        for source in sources:
            try:
                if source == 'yfinance' and YFINANCE_AVAILABLE:
                    data = self._fetch_yfinance(ticker)
                elif source == 'alpha_vantage' and self.api_keys.get('ALPHA_VANTAGE_API_KEY'):
                    data = self._fetch_alpha_vantage(ticker)
                elif source == 'massive' and (self.api_keys.get('MASSIVE_API_KEY') or self.api_keys.get('POLYGON_API_KEY')):
                    data = self._fetch_massive(ticker)
                elif source == 'finnhub' and self.api_keys.get('FINNHUB_API_KEY'):
                    data = self._fetch_finnhub(ticker)
                else:
                    continue
                
                if data:
                    # Merge data, prioritizing non-None values
                    for key, value in data.items():
                        if value is not None and (key not in all_data or all_data[key] is None):
                            all_data[key] = value
                    
                    logger.debug(f"Fetched from {source}: {len([v for v in data.values() if v is not None])} fields")
                    
            except Exception as e:
                logger.warning(f"Error fetching from {source} for {ticker}: {e}")
                continue
        
        if not all_data:
            return None
        
        # Ensure required fields
        all_data['ticker'] = ticker
        all_data['date'] = datetime.now().strftime('%Y-%m-%d')
        
        return all_data
    
    def _fetch_yfinance(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch from Yahoo Finance."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if not info or len(info) < 5:  # Basic validation
                return None
            
            return {
                'pe': info.get('trailingPE') or info.get('forwardPE'),
                'pb': info.get('priceToBook'),
                'ps': info.get('priceToSalesTrailing12Months'),
                'peg': info.get('pegRatio'),
                'roe': info.get('returnOnEquity'),
                'roa': info.get('returnOnAssets'),
                'net_margin': info.get('profitMargins'),
                'gross_margin': info.get('grossMargins'),
                'operating_margin': info.get('operatingMargins'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'quick_ratio': info.get('quickRatio'),
                'revenue_growth': info.get('revenueGrowth'),
                'earnings_growth': info.get('earningsQuarterlyGrowth'),
                'market_cap': info.get('marketCap'),
                'enterprise_value': info.get('enterpriseValue'),
                'dividend_yield': info.get('dividendYield'),
                'beta': info.get('beta'),
            }
        except Exception as e:
            logger.debug(f"yfinance error for {ticker}: {e}")
            return None
    
    def _fetch_alpha_vantage(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch from Alpha Vantage (requires API key)."""
        api_key = self.api_keys.get('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            return None
        
        # Rate limiting: 5 requests per minute
        self._rate_limit('alpha_vantage', 12)  # 12 seconds between requests
        
        try:
            # Alpha Vantage Overview endpoint
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'OVERVIEW',
                'symbol': ticker,
                'apikey': api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'Error Message' in data or 'Note' in data:
                return None
            
            # Map Alpha Vantage fields to our format
            return {
                'pe': self._safe_float(data.get('PERatio')),
                'pb': self._safe_float(data.get('PriceToBookRatio')),
                'ps': self._safe_float(data.get('PriceToSalesRatioTTM')),
                'peg': self._safe_float(data.get('PEGRatio')),
                'roe': self._safe_float(data.get('ReturnOnEquityTTM')) / 100 if data.get('ReturnOnEquityTTM') else None,
                'roa': self._safe_float(data.get('ReturnOnAssetsTTM')) / 100 if data.get('ReturnOnAssetsTTM') else None,
                'net_margin': self._safe_float(data.get('ProfitMargin')) / 100 if data.get('ProfitMargin') else None,
                'gross_margin': self._safe_float(data.get('GrossProfitTTM')) / self._safe_float(data.get('RevenueTTM')) if data.get('GrossProfitTTM') and data.get('RevenueTTM') else None,
                'operating_margin': self._safe_float(data.get('OperatingMarginTTM')) / 100 if data.get('OperatingMarginTTM') else None,
                'debt_to_equity': self._safe_float(data.get('DebtToEquity')),
                'revenue_growth': self._safe_float(data.get('QuarterlyRevenueGrowthYOY')) / 100 if data.get('QuarterlyRevenueGrowthYOY') else None,
                'earnings_growth': self._safe_float(data.get('QuarterlyEarningsGrowthYOY')) / 100 if data.get('QuarterlyEarningsGrowthYOY') else None,
                'market_cap': self._safe_float(data.get('MarketCapitalization')),
                'enterprise_value': self._safe_float(data.get('EnterpriseValue')),
                'dividend_yield': self._safe_float(data.get('DividendYield')) / 100 if data.get('DividendYield') else None,
                'beta': self._safe_float(data.get('Beta')),
            }
        except Exception as e:
            logger.debug(f"Alpha Vantage error for {ticker}: {e}")
            return None
    
    def _fetch_massive(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch from Massive API (formerly Polygon.io) - requires API key."""
        # Check for MASSIVE_API_KEY first, fallback to POLYGON_API_KEY for backward compatibility
        api_key = self.api_keys.get('MASSIVE_API_KEY') or self.api_keys.get('POLYGON_API_KEY')
        if not api_key:
            return None
        
        # Rate limiting: 5 requests per minute (free tier)
        # Using 12 seconds between requests to stay safely under limit
        self._rate_limit('massive', 12)
        
        try:
            # Massive API Fundamentals - Ratios endpoint
            # Reference: https://massive.com/docs/rest/quickstart
            url = "https://api.massive.com/v2/reference/financials/ratios"
            params = {
                'ticker': ticker,
                'apiKey': api_key
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
            # Massive ratios endpoint provides pre-calculated ratios
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
    
    def _fetch_finnhub(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch from Finnhub (requires API key)."""
        api_key = self.api_keys.get('FINNHUB_API_KEY')
        if not api_key:
            return None
        
        # Rate limiting: 60 requests per minute
        self._rate_limit('finnhub', 1)
        
        try:
            # Finnhub Company Profile endpoint
            url = f"https://finnhub.io/api/v1/stock/profile2"
            params = {
                'symbol': ticker,
                'token': api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data or 'marketCapitalization' not in data:
                return None
            
            # Finnhub also has metrics endpoint
            metrics_url = f"https://finnhub.io/api/v1/stock/metric"
            metrics_params = {
                'symbol': ticker,
                'metric': 'all',
                'token': api_key
            }
            
            metrics_response = requests.get(metrics_url, params=metrics_params, timeout=10)
            metrics_data = metrics_response.json() if metrics_response.status_code == 200 else {}
            
            return {
                'market_cap': data.get('marketCapitalization'),
                'pe': metrics_data.get('metric', {}).get('peNormalizedAnnual'),
                'pb': metrics_data.get('metric', {}).get('pbAnnual'),
                'ps': metrics_data.get('metric', {}).get('psAnnual'),
                'roe': metrics_data.get('metric', {}).get('roeAnnual'),
                'net_margin': metrics_data.get('metric', {}).get('netMarginAnnual'),
                'beta': metrics_data.get('metric', {}).get('beta'),
            }
        except Exception as e:
            logger.debug(f"Finnhub error for {ticker}: {e}")
            return None
    
    def _rate_limit(self, source: str, delay_seconds: float):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        last_time = self.last_request_times.get(source, 0)
        
        elapsed = current_time - last_time
        if elapsed < delay_seconds:
            sleep_time = delay_seconds - elapsed
            time.sleep(sleep_time)
        
        self.last_request_times[source] = time.time()
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or value == 'None' or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def fetch_batch(self, tickers: List[str], sources: Optional[List[str]] = None, 
                   delay: float = 0.5) -> pd.DataFrame:
        """
        Fetch fundamentals for multiple tickers.
        
        Args:
            tickers: List of ticker symbols
            sources: List of sources to try
            delay: Delay between tickers (seconds)
        
        Returns:
            DataFrame with fundamental data
        """
        results = []
        failed = []
        
        print(f"📥 Fetching fundamentals from multiple sources for {len(tickers)} tickers...")
        print(f"   Available sources: {', '.join(self._get_available_sources())}")
        print()
        
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{len(tickers)}] {ticker}...", end=' ', flush=True)
            
            data = self.fetch_fundamentals(ticker, sources)
            if data:
                results.append(data)
                # Count non-None fields
                field_count = len([v for v in data.values() if v is not None and v != ticker])
                print(f"✅ ({field_count} fields)")
            else:
                failed.append(ticker)
                print("❌")
            
            if i < len(tickers):
                time.sleep(delay)
        
        print()
        print(f"✅ Successfully fetched: {len(results)}/{len(tickers)}")
        if failed:
            print(f"❌ Failed: {', '.join(failed)}")
        
        if not results:
            return pd.DataFrame()
        
        return pd.DataFrame(results)
    
    def _get_available_sources(self) -> List[str]:
        """Get list of available data sources."""
        sources = []
        if YFINANCE_AVAILABLE:
            sources.append('yfinance')
        if self.api_keys.get('ALPHA_VANTAGE_API_KEY'):
            sources.append('alpha_vantage')
        if self.api_keys.get('MASSIVE_API_KEY') or self.api_keys.get('POLYGON_API_KEY'):
            sources.append('massive')
        if self.api_keys.get('FINNHUB_API_KEY'):
            sources.append('finnhub')
        return sources
