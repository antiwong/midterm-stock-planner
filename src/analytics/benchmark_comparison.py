"""
Benchmark Comparison Analysis
=============================
Compare portfolio performance vs benchmarks (S&P 500, NASDAQ, etc.)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
import yfinance as yf


class BenchmarkComparator:
    """Compare portfolio performance against benchmarks."""
    
    def __init__(self):
        self.benchmark_cache = {}
    
    def get_benchmark_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.Series:
        """Get benchmark price data."""
        cache_key = f"{symbol}_{start_date}_{end_date}"
        if cache_key in self.benchmark_cache:
            return self.benchmark_cache[cache_key]
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            if len(data) == 0:
                return pd.Series(dtype=float)
            returns = data['Close'].pct_change().dropna()
            self.benchmark_cache[cache_key] = returns
            return returns
        except Exception as e:
            print(f"Error fetching benchmark {symbol}: {e}")
            return pd.Series(dtype=float)
    
    def compare(
        self,
        portfolio_returns: pd.Series,
        benchmark_symbol: str,
        benchmark_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Compare portfolio vs benchmark.
        
        Args:
            portfolio_returns: Portfolio returns time series
            benchmark_symbol: Benchmark ticker (e.g., 'SPY', 'QQQ')
            benchmark_name: Human-readable benchmark name
            start_date: Start date for comparison
            end_date: End date for comparison
            
        Returns:
            Dictionary with comparison metrics
        """
        if start_date is None:
            start_date = portfolio_returns.index[0]
        if end_date is None:
            end_date = portfolio_returns.index[-1]
        if benchmark_name is None:
            benchmark_name = benchmark_symbol
        
        # Get benchmark returns
        benchmark_returns = self.get_benchmark_data(benchmark_symbol, start_date, end_date)
        
        # Normalize timezones before alignment
        # Portfolio returns may be timezone-naive, benchmark may be timezone-aware
        portfolio_index = portfolio_returns.index
        benchmark_index = benchmark_returns.index
        
        # Remove timezone from both indices for comparison
        if hasattr(portfolio_index, 'tz') and portfolio_index.tz is not None:
            portfolio_index_normalized = portfolio_index.tz_localize(None)
        else:
            portfolio_index_normalized = portfolio_index
        
        if hasattr(benchmark_index, 'tz') and benchmark_index.tz is not None:
            benchmark_index_normalized = benchmark_index.tz_localize(None)
        else:
            benchmark_index_normalized = benchmark_index
        
        # Align dates using normalized indices
        common_dates_normalized = portfolio_index_normalized.intersection(benchmark_index_normalized)
        if len(common_dates_normalized) == 0:
            return {'error': 'No overlapping dates between portfolio and benchmark'}
        
        # Align both series to common dates
        # Create a mapping from normalized dates to original portfolio indices
        portfolio_date_map = pd.Series(portfolio_index, index=portfolio_index_norm)
        benchmark_date_map = pd.Series(benchmark_index, index=benchmark_index_norm)
        
        # Get original indices for common dates
        portfolio_common_orig = portfolio_date_map.loc[common_dates_norm].values
        benchmark_common_orig = benchmark_date_map.loc[common_dates_norm].values
        
        # Align using original indices, then set normalized index
        portfolio_aligned = portfolio_returns.loc[portfolio_common_orig].copy()
        benchmark_aligned = benchmark_returns.loc[benchmark_common_orig].copy()
        
        # Set both to use normalized (timezone-naive) common dates
        portfolio_aligned.index = common_dates_norm
        benchmark_aligned.index = common_dates_norm
        
        common_dates = common_dates_norm
        
        # Calculate metrics
        portfolio_metrics = self._calculate_metrics(portfolio_aligned)
        benchmark_metrics = self._calculate_metrics(benchmark_aligned)
        relative_metrics = self._calculate_relative_metrics(
            portfolio_aligned, benchmark_aligned
        )
        
        return {
            'benchmark_symbol': benchmark_symbol,
            'benchmark_name': benchmark_name,
            'start_date': start_date,
            'end_date': end_date,
            'portfolio_metrics': portfolio_metrics,
            'benchmark_metrics': benchmark_metrics,
            'relative_metrics': relative_metrics,
            'comparison_period_days': len(common_dates)
        }
    
    def _calculate_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate performance metrics."""
        if len(returns) == 0:
            return {}
        
        total_return = (1 + returns).prod() - 1
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1 if len(returns) > 0 else 0
        volatility = returns.std() * np.sqrt(252) if len(returns) > 1 else 0
        sharpe = annualized_return / volatility if volatility > 0 else 0
        
        # Max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        return {
            'return': float(total_return),
            'annualized_return': float(annualized_return),
            'volatility': float(volatility),
            'sharpe': float(sharpe),
            'max_drawdown': float(max_drawdown)
        }
    
    def _calculate_relative_metrics(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> Dict[str, float]:
        """Calculate relative metrics (alpha, beta, etc.)."""
        if len(portfolio_returns) == 0 or len(benchmark_returns) == 0:
            return {}
        
        # Align
        common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
        portfolio_aligned = portfolio_returns.loc[common_dates]
        benchmark_aligned = benchmark_returns.loc[common_dates]
        
        # Alpha and Beta (CAPM)
        covariance = np.cov(portfolio_aligned, benchmark_aligned)[0, 1]
        benchmark_variance = benchmark_aligned.var()
        beta = covariance / benchmark_variance if benchmark_variance > 0 else 1.0
        
        portfolio_mean = portfolio_aligned.mean() * 252
        benchmark_mean = benchmark_aligned.mean() * 252
        alpha = portfolio_mean - (beta * benchmark_mean)
        
        # Tracking error
        active_returns = portfolio_aligned - benchmark_aligned
        tracking_error = active_returns.std() * np.sqrt(252) if len(active_returns) > 1 else 0
        
        # Information ratio
        active_mean = active_returns.mean() * 252
        information_ratio = active_mean / tracking_error if tracking_error > 0 else 0
        
        # Up/Down capture
        up_periods = benchmark_aligned > 0
        down_periods = benchmark_aligned < 0
        
        if up_periods.sum() > 0:
            up_capture = (portfolio_aligned[up_periods].sum() / benchmark_aligned[up_periods].sum()) * 100
        else:
            up_capture = 0
        
        if down_periods.sum() > 0:
            down_capture = (portfolio_aligned[down_periods].sum() / benchmark_aligned[down_periods].sum()) * 100
        else:
            down_capture = 0
        
        return {
            'alpha': float(alpha),
            'beta': float(beta),
            'tracking_error': float(tracking_error),
            'information_ratio': float(information_ratio),
            'up_capture': float(up_capture),
            'down_capture': float(down_capture)
        }
