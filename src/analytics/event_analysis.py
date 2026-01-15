"""
Event-Driven Analysis
=====================
Analyze portfolio performance around market events (Fed meetings, earnings, macro data).
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import yfinance as yf


class EventAnalyzer:
    """Analyze portfolio performance around market events."""
    
    def __init__(self):
        self.event_types = {
            'fed_meeting': self._get_fed_meetings,
            'earnings': self._get_earnings_dates,
            'macro_data': self._get_macro_releases,
        }
    
    def analyze_event_impact(
        self,
        portfolio_returns: pd.Series,
        event_type: str,
        event_dates: Optional[List[datetime]] = None,
        lookback_days: int = 5,
        lookforward_days: int = 5,
        benchmark_returns: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        """
        Analyze portfolio performance around events.
        
        Args:
            portfolio_returns: Portfolio returns time series
            event_type: Type of event ('fed_meeting', 'earnings', 'macro_data')
            event_dates: List of event dates (if None, will fetch automatically)
            lookback_days: Days before event to analyze
            lookforward_days: Days after event to analyze
            benchmark_returns: Optional benchmark returns for comparison
            
        Returns:
            Dictionary with event analysis results
        """
        if event_dates is None:
            event_dates = self._fetch_event_dates(event_type, portfolio_returns.index)
        
        if not event_dates:
            return {
                'error': f'No {event_type} events found in the analysis period',
                'events_analyzed': 0
            }
        
        results = {
            'event_type': event_type,
            'events_analyzed': len(event_dates),
            'lookback_days': lookback_days,
            'lookforward_days': lookforward_days,
            'event_performance': [],
            'summary': {}
        }
        
        # Analyze each event
        event_returns = []
        benchmark_event_returns = [] if benchmark_returns is not None else None
        
        for event_date in event_dates:
            if event_date not in portfolio_returns.index:
                continue
            
            # Get window around event
            start_date = event_date - timedelta(days=lookback_days)
            end_date = event_date + timedelta(days=lookforward_days)
            
            window_returns = portfolio_returns.loc[
                (portfolio_returns.index >= start_date) & 
                (portfolio_returns.index <= end_date)
            ]
            
            if len(window_returns) == 0:
                continue
            
            # Calculate cumulative return in window
            cumulative_return = (1 + window_returns).prod() - 1
            
            event_result = {
                'event_date': event_date.isoformat(),
                'cumulative_return': float(cumulative_return),
                'volatility': float(window_returns.std()),
                'max_gain': float(window_returns.max()),
                'max_loss': float(window_returns.min()),
                'days_analyzed': len(window_returns)
            }
            
            # Compare to benchmark if available
            if benchmark_returns is not None:
                bench_window = benchmark_returns.loc[
                    (benchmark_returns.index >= start_date) & 
                    (benchmark_returns.index <= end_date)
                ]
                if len(bench_window) > 0:
                    bench_cumulative = (1 + bench_window).prod() - 1
                    event_result['benchmark_return'] = float(bench_cumulative)
                    event_result['excess_return'] = float(cumulative_return - bench_cumulative)
                    benchmark_event_returns.append(bench_cumulative)
            
            event_returns.append(cumulative_return)
            results['event_performance'].append(event_result)
        
        if not event_returns:
            return {
                'error': 'No valid events found in portfolio returns period',
                'events_analyzed': 0
            }
        
        # Summary statistics
        event_returns_array = np.array(event_returns)
        results['summary'] = {
            'avg_return': float(np.mean(event_returns_array)),
            'median_return': float(np.median(event_returns_array)),
            'std_return': float(np.std(event_returns_array)),
            'positive_events': int(np.sum(event_returns_array > 0)),
            'negative_events': int(np.sum(event_returns_array < 0)),
            'win_rate': float(np.mean(event_returns_array > 0)),
            'avg_positive_return': float(np.mean(event_returns_array[event_returns_array > 0])) if np.any(event_returns_array > 0) else 0.0,
            'avg_negative_return': float(np.mean(event_returns_array[event_returns_array < 0])) if np.any(event_returns_array < 0) else 0.0,
        }
        
        # Benchmark comparison
        if benchmark_event_returns:
            benchmark_array = np.array(benchmark_event_returns)
            results['summary']['benchmark_avg_return'] = float(np.mean(benchmark_array))
            results['summary']['avg_excess_return'] = float(np.mean(event_returns_array - benchmark_array))
            results['summary']['outperformance_rate'] = float(np.mean(event_returns_array > benchmark_array))
        
        return results
    
    def _fetch_event_dates(self, event_type: str, date_range: pd.DatetimeIndex) -> List[datetime]:
        """Fetch event dates for the given type and date range."""
        if event_type in self.event_types:
            return self.event_types[event_type](date_range)
        return []
    
    def _get_fed_meetings(self, date_range: pd.DatetimeIndex) -> List[datetime]:
        """Get Federal Reserve meeting dates (approximate schedule)."""
        # FOMC typically meets 8 times per year
        # This is a simplified implementation - in production, use actual Fed calendar
        meetings = []
        start_year = date_range.min().year
        end_year = date_range.max().year
        
        # Typical FOMC meeting months (approximate)
        meeting_months = [1, 3, 5, 6, 7, 9, 11, 12]
        
        for year in range(start_year, end_year + 1):
            for month in meeting_months:
                # Typically around mid-month (15th-20th)
                meeting_date = datetime(year, month, 15)
                if date_range.min() <= meeting_date <= date_range.max():
                    meetings.append(meeting_date)
        
        return sorted(meetings)
    
    def _get_earnings_dates(self, date_range: pd.DatetimeIndex, tickers: Optional[List[str]] = None) -> List[datetime]:
        """Get earnings announcement dates for portfolio tickers."""
        # This is a placeholder - in production, use earnings calendar API
        # For now, return empty list (will be populated by earnings calendar integration)
        return []
    
    def _get_macro_releases(self, date_range: pd.DatetimeIndex) -> List[datetime]:
        """Get macroeconomic data release dates (CPI, GDP, employment, etc.)."""
        # Typical release dates (first Friday of month for employment, mid-month for CPI)
        releases = []
        start_year = date_range.min().year
        end_year = date_range.max().year
        
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                # Employment report: First Friday
                first_friday = self._get_first_friday(year, month)
                if date_range.min() <= first_friday <= date_range.max():
                    releases.append(first_friday)
                
                # CPI: Typically around 10th-15th
                cpi_date = datetime(year, month, 12)
                if date_range.min() <= cpi_date <= date_range.max():
                    releases.append(cpi_date)
        
        return sorted(releases)
    
    def _get_first_friday(self, year: int, month: int) -> datetime:
        """Get first Friday of a month."""
        first_day = datetime(year, month, 1)
        days_ahead = 4 - first_day.weekday()  # Friday is 4
        if days_ahead <= 0:
            days_ahead += 7
        return first_day + timedelta(days=days_ahead)
    
    def analyze_portfolio_events(
        self,
        portfolio_returns: pd.Series,
        tickers: List[str],
        benchmark_returns: Optional[pd.Series] = None,
        lookback_days: int = 5,
        lookforward_days: int = 5
    ) -> Dict[str, Any]:
        """
        Analyze portfolio performance around all event types.
        
        Returns:
            Dictionary with analysis for each event type
        """
        results = {
            'fed_meetings': None,
            'earnings': None,
            'macro_data': None,
            'summary': {}
        }
        
        # Fed meetings
        fed_result = self.analyze_event_impact(
            portfolio_returns,
            'fed_meeting',
            lookback_days=lookback_days,
            lookforward_days=lookforward_days,
            benchmark_returns=benchmark_returns
        )
        results['fed_meetings'] = fed_result
        
        # Earnings (will be enhanced by earnings calendar integration)
        earnings_result = self.analyze_event_impact(
            portfolio_returns,
            'earnings',
            event_dates=self._get_earnings_dates(portfolio_returns.index, tickers),
            lookback_days=lookback_days,
            lookforward_days=lookforward_days,
            benchmark_returns=benchmark_returns
        )
        results['earnings'] = earnings_result
        
        # Macro data releases
        macro_result = self.analyze_event_impact(
            portfolio_returns,
            'macro_data',
            lookback_days=lookback_days,
            lookforward_days=lookforward_days,
            benchmark_returns=benchmark_returns
        )
        results['macro_data'] = macro_result
        
        # Overall summary
        all_events = []
        for event_type in ['fed_meetings', 'earnings', 'macro_data']:
            event_data = results[event_type]
            if event_data and 'summary' in event_data:
                all_events.append(event_data['summary'].get('avg_return', 0))
        
        if all_events:
            results['summary'] = {
                'total_events_analyzed': sum(
                    r.get('events_analyzed', 0) 
                    for r in [results['fed_meetings'], results['earnings'], results['macro_data']]
                    if r and 'events_analyzed' in r
                ),
                'avg_event_return': float(np.mean(all_events)),
            }
        
        return results
