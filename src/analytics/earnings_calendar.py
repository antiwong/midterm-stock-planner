"""
Earnings Calendar Integration
=============================
Fetch earnings calendar data, analyze portfolio earnings exposure, and earnings impact.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import yfinance as yf
from collections import defaultdict


class EarningsCalendarAnalyzer:
    """Analyze earnings calendar and portfolio exposure."""
    
    def __init__(self):
        self.earnings_cache = {}
    
    def fetch_earnings_dates(
        self,
        tickers: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True
    ) -> Dict[str, List[datetime]]:
        """
        Fetch earnings announcement dates for tickers.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date for earnings period
            end_date: End date for earnings period
            use_cache: Whether to use cached data
            
        Returns:
            Dictionary mapping ticker -> list of earnings dates
        """
        earnings_dates = {}
        
        for ticker in tickers:
            cache_key = f"{ticker}_{start_date}_{end_date}"
            
            if use_cache and cache_key in self.earnings_cache:
                earnings_dates[ticker] = self.earnings_cache[cache_key]
                continue
            
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # Try to get earnings dates from info
                if 'earningsDates' in info:
                    dates = info['earningsDates']
                    if isinstance(dates, list):
                        earnings_dates[ticker] = [
                            pd.to_datetime(d) for d in dates
                            if (start_date is None or pd.to_datetime(d) >= start_date) and
                               (end_date is None or pd.to_datetime(d) <= end_date)
                        ]
                    else:
                        earnings_dates[ticker] = []
                else:
                    # Fallback: try calendar
                    try:
                        calendar = stock.calendar
                        if calendar is not None and len(calendar) > 0:
                            # Extract earnings date from calendar
                            earnings_dates[ticker] = []
                    except:
                        earnings_dates[ticker] = []
                
                # Cache result
                if use_cache:
                    self.earnings_cache[cache_key] = earnings_dates.get(ticker, [])
                    
            except Exception as e:
                print(f"Warning: Could not fetch earnings for {ticker}: {e}")
                earnings_dates[ticker] = []
        
        return earnings_dates
    
    def analyze_portfolio_earnings_exposure(
        self,
        portfolio_weights: pd.DataFrame,
        earnings_dates: Dict[str, List[datetime]],
        lookforward_days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze portfolio exposure to upcoming earnings announcements.
        
        Args:
            portfolio_weights: Current portfolio weights (Date x Ticker)
            earnings_dates: Dictionary of ticker -> earnings dates
            lookforward_days: Days ahead to look for earnings
            
        Returns:
            Dictionary with earnings exposure analysis
        """
        if portfolio_weights.empty:
            return {'error': 'No portfolio data'}
        
        # Get latest weights
        latest_date = portfolio_weights.index[-1]
        latest_weights = portfolio_weights.iloc[-1]
        
        # Find upcoming earnings
        cutoff_date = latest_date + timedelta(days=lookforward_days)
        upcoming_earnings = []
        
        for ticker, dates in earnings_dates.items():
            if ticker not in latest_weights:
                continue
            
            weight = latest_weights[ticker]
            if abs(weight) < 0.001:  # Skip negligible positions
                continue
            
            for earnings_date in dates:
                if latest_date <= earnings_date <= cutoff_date:
                    upcoming_earnings.append({
                        'ticker': ticker,
                        'earnings_date': earnings_date,
                        'weight': float(weight),
                        'days_until': (earnings_date - latest_date).days
                    })
        
        # Sort by date
        upcoming_earnings.sort(key=lambda x: x['earnings_date'])
        
        # Calculate exposure metrics
        total_exposure = sum(e['weight'] for e in upcoming_earnings)
        
        # Group by time periods
        exposure_by_period = {
            'next_7_days': sum(e['weight'] for e in upcoming_earnings if e['days_until'] <= 7),
            'next_14_days': sum(e['weight'] for e in upcoming_earnings if e['days_until'] <= 14),
            'next_30_days': total_exposure
        }
        
        # Group by ticker
        exposure_by_ticker = defaultdict(float)
        for e in upcoming_earnings:
            exposure_by_ticker[e['ticker']] += e['weight']
        
        results = {
            'analysis_date': latest_date.isoformat() if isinstance(latest_date, datetime) else str(latest_date),
            'lookforward_days': lookforward_days,
            'upcoming_earnings': [
                {
                    'ticker': e['ticker'],
                    'earnings_date': e['earnings_date'].isoformat() if isinstance(e['earnings_date'], datetime) else str(e['earnings_date']),
                    'weight': e['weight'],
                    'days_until': e['days_until']
                }
                for e in upcoming_earnings
            ],
            'total_exposure': float(total_exposure),
            'exposure_by_period': exposure_by_period,
            'exposure_by_ticker': {k: float(v) for k, v in exposure_by_ticker.items()},
            'count': len(upcoming_earnings),
            'unique_tickers': len(exposure_by_ticker)
        }
        
        return results
    
    def analyze_earnings_impact(
        self,
        ticker: str,
        earnings_date: datetime,
        stock_returns: pd.Series,
        lookback_days: int = 5,
        lookforward_days: int = 5
    ) -> Dict[str, Any]:
        """
        Analyze stock price impact around earnings announcement.
        
        Args:
            ticker: Stock ticker
            earnings_date: Earnings announcement date
            stock_returns: Stock returns time series
            lookback_days: Days before earnings to analyze
            lookforward_days: Days after earnings to analyze
            
        Returns:
            Dictionary with earnings impact analysis
        """
        if earnings_date not in stock_returns.index:
            # Find nearest date
            nearest_idx = stock_returns.index.get_indexer([earnings_date], method='nearest')[0]
            earnings_date = stock_returns.index[nearest_idx]
        
        # Get window around earnings
        start_date = earnings_date - timedelta(days=lookback_days)
        end_date = earnings_date + timedelta(days=lookforward_days)
        
        window_returns = stock_returns.loc[
            (stock_returns.index >= start_date) & 
            (stock_returns.index <= end_date)
        ]
        
        if len(window_returns) == 0:
            return {'error': 'No data available for earnings window'}
        
        # Calculate metrics
        pre_earnings = window_returns[window_returns.index < earnings_date]
        post_earnings = window_returns[window_returns.index >= earnings_date]
        
        results = {
            'ticker': ticker,
            'earnings_date': earnings_date.isoformat() if isinstance(earnings_date, datetime) else str(earnings_date),
            'window': {
                'start': start_date.isoformat() if isinstance(start_date, datetime) else str(start_date),
                'end': end_date.isoformat() if isinstance(end_date, datetime) else str(end_date),
                'days': len(window_returns)
            },
            'pre_earnings': {
                'return': float(pre_earnings.sum()) if len(pre_earnings) > 0 else 0.0,
                'volatility': float(pre_earnings.std()) if len(pre_earnings) > 0 else 0.0,
                'days': len(pre_earnings)
            },
            'post_earnings': {
                'return': float(post_earnings.sum()) if len(post_earnings) > 0 else 0.0,
                'volatility': float(post_earnings.std()) if len(post_earnings) > 0 else 0.0,
                'days': len(post_earnings)
            },
            'total_window': {
                'return': float(window_returns.sum()),
                'volatility': float(window_returns.std()),
                'max_gain': float(window_returns.max()),
                'max_loss': float(window_returns.min())
            },
            'earnings_day_return': float(window_returns.loc[earnings_date]) if earnings_date in window_returns.index else None
        }
        
        return results
    
    def analyze_portfolio_earnings_impact(
        self,
        portfolio_weights: pd.DataFrame,
        stock_returns: pd.DataFrame,
        earnings_dates: Dict[str, List[datetime]],
        lookback_days: int = 5,
        lookforward_days: int = 5
    ) -> Dict[str, Any]:
        """
        Analyze portfolio-wide earnings impact.
        
        Args:
            portfolio_weights: Portfolio weights over time
            stock_returns: Stock returns (Date x Ticker)
            earnings_dates: Dictionary of ticker -> earnings dates
            lookback_days: Days before earnings to analyze
            lookforward_days: Days after earnings to analyze
            
        Returns:
            Dictionary with portfolio earnings impact analysis
        """
        all_earnings_impacts = []
        
        for ticker, dates in earnings_dates.items():
            if ticker not in stock_returns.columns:
                continue
            
            ticker_returns = stock_returns[ticker]
            
            for earnings_date in dates:
                if earnings_date not in ticker_returns.index:
                    continue
                
                # Get weight at earnings date
                weight_at_date = portfolio_weights.loc[
                    portfolio_weights.index <= earnings_date
                ].iloc[-1][ticker] if len(portfolio_weights) > 0 else 0.0
                
                if abs(weight_at_date) < 0.001:
                    continue
                
                # Analyze impact
                impact = self.analyze_earnings_impact(
                    ticker,
                    earnings_date,
                    ticker_returns,
                    lookback_days,
                    lookforward_days
                )
                
                if 'error' not in impact:
                    impact['portfolio_weight'] = float(weight_at_date)
                    impact['weighted_return'] = float(impact['total_window']['return'] * weight_at_date)
                    all_earnings_impacts.append(impact)
        
        if not all_earnings_impacts:
            return {'error': 'No earnings impacts found'}
        
        # Aggregate statistics
        weighted_returns = [e['weighted_return'] for e in all_earnings_impacts]
        unweighted_returns = [e['total_window']['return'] for e in all_earnings_impacts]
        
        results = {
            'earnings_events_analyzed': len(all_earnings_impacts),
            'unique_tickers': len(set(e['ticker'] for e in all_earnings_impacts)),
            'aggregate_impact': {
                'avg_weighted_return': float(np.mean(weighted_returns)),
                'median_weighted_return': float(np.median(weighted_returns)),
                'total_weighted_return': float(np.sum(weighted_returns)),
                'avg_unweighted_return': float(np.mean(unweighted_returns)),
                'positive_events': int(np.sum(np.array(unweighted_returns) > 0)),
                'negative_events': int(np.sum(np.array(unweighted_returns) < 0)),
                'win_rate': float(np.mean(np.array(unweighted_returns) > 0))
            },
            'by_ticker': {}
        }
        
        # Group by ticker
        by_ticker = defaultdict(list)
        for e in all_earnings_impacts:
            by_ticker[e['ticker']].append(e)
        
        for ticker, events in by_ticker.items():
            ticker_returns = [e['total_window']['return'] for e in events]
            results['by_ticker'][ticker] = {
                'count': len(events),
                'avg_return': float(np.mean(ticker_returns)),
                'win_rate': float(np.mean(np.array(ticker_returns) > 0))
            }
        
        return results
