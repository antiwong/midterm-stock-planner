"""
Turnover & Churn Analysis
=========================
Detailed turnover analysis, churn rate calculations, and position holding period analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


class TurnoverAnalyzer:
    """Analyze portfolio turnover and churn."""
    
    def __init__(self):
        pass
    
    def calculate_turnover(
        self,
        portfolio_weights: pd.DataFrame,
        method: str = 'sum_of_abs_changes'
    ) -> Dict[str, Any]:
        """
        Calculate portfolio turnover over time.
        
        Args:
            portfolio_weights: DataFrame with Date index and Ticker columns (weights)
            method: Calculation method:
                - 'sum_of_abs_changes': Sum of absolute weight changes
                - 'one_way': One-way turnover (buys or sells)
                - 'two_way': Two-way turnover (total trading)
                
        Returns:
            Dictionary with turnover metrics
        """
        if portfolio_weights.empty or len(portfolio_weights) < 2:
            return {'error': 'Insufficient data for turnover calculation'}
        
        # Sort by date
        portfolio_weights = portfolio_weights.sort_index()
        
        # Calculate period-over-period changes
        weight_changes = portfolio_weights.diff().abs()
        
        if method == 'sum_of_abs_changes':
            # Sum of absolute changes (most common)
            turnover = weight_changes.sum(axis=1)
        elif method == 'one_way':
            # One-way: only increases (buys) or decreases (sells)
            increases = portfolio_weights.diff().clip(lower=0).sum(axis=1)
            decreases = (-portfolio_weights.diff()).clip(lower=0).sum(axis=1)
            turnover = pd.DataFrame({
                'buys': increases,
                'sells': decreases,
                'total': increases + decreases
            })
        elif method == 'two_way':
            # Two-way: total trading volume
            turnover = weight_changes.sum(axis=1) * 2  # Count both buys and sells
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Calculate statistics
        if isinstance(turnover, pd.Series):
            turnover_series = turnover
        else:
            turnover_series = turnover['total'] if 'total' in turnover.columns else turnover.iloc[:, 0]
        
        results = {
            'method': method,
            'turnover_by_period': turnover_series.to_dict() if isinstance(turnover_series.index[0], datetime) else {
                str(k): float(v) for k, v in turnover_series.to_dict().items()
            },
            'statistics': {
                'mean': float(turnover_series.mean()),
                'median': float(turnover_series.median()),
                'std': float(turnover_series.std()),
                'min': float(turnover_series.min()),
                'max': float(turnover_series.max()),
                'total_turnover': float(turnover_series.sum()),
            }
        }
        
        # Annualize if we have enough data
        if len(turnover_series) > 0:
            # Estimate frequency
            date_diff = (turnover_series.index[-1] - turnover_series.index[0]).days
            if date_diff > 0:
                periods_per_year = 365.25 / (date_diff / len(turnover_series))
                results['statistics']['annualized_turnover'] = float(
                    turnover_series.mean() * periods_per_year
                )
        
        # Add breakdown if one-way method
        if isinstance(turnover, pd.DataFrame) and 'buys' in turnover.columns:
            results['buys'] = turnover['buys'].to_dict()
            results['sells'] = turnover['sells'].to_dict()
        
        return results
    
    def calculate_churn_rate(
        self,
        portfolio_weights: pd.DataFrame,
        threshold: float = 0.01
    ) -> Dict[str, Any]:
        """
        Calculate portfolio churn rate (how often positions change significantly).
        
        Args:
            portfolio_weights: DataFrame with Date index and Ticker columns
            threshold: Minimum weight change to count as churn (default 1%)
            
        Returns:
            Dictionary with churn metrics
        """
        if portfolio_weights.empty or len(portfolio_weights) < 2:
            return {'error': 'Insufficient data for churn calculation'}
        
        portfolio_weights = portfolio_weights.sort_index()
        
        # Calculate changes
        weight_changes = portfolio_weights.diff().abs()
        
        # Count positions that changed significantly
        churned_positions = (weight_changes > threshold).sum(axis=1)
        total_positions = (portfolio_weights.abs() > threshold).sum(axis=1)
        
        # Calculate churn rate
        churn_rate = churned_positions / total_positions.replace(0, np.nan)
        
        results = {
            'threshold': threshold,
            'churn_rate_by_period': {
                str(k): float(v) if not pd.isna(v) else 0.0
                for k, v in churn_rate.to_dict().items()
            },
            'statistics': {
                'mean_churn_rate': float(churn_rate.mean()),
                'median_churn_rate': float(churn_rate.median()),
                'max_churn_rate': float(churn_rate.max()),
                'min_churn_rate': float(churn_rate.min()),
            },
            'churned_positions_by_period': {
                str(k): int(v)
                for k, v in churned_positions.to_dict().items()
            },
            'total_positions_by_period': {
                str(k): int(v)
                for k, v in total_positions.to_dict().items()
            }
        }
        
        return results
    
    def analyze_holding_periods(
        self,
        portfolio_weights: pd.DataFrame,
        min_weight: float = 0.001
    ) -> Dict[str, Any]:
        """
        Analyze position holding periods.
        
        Args:
            portfolio_weights: DataFrame with Date index and Ticker columns
            min_weight: Minimum weight to consider a position "held"
            
        Returns:
            Dictionary with holding period analysis
        """
        if portfolio_weights.empty:
            return {'error': 'No portfolio data'}
        
        portfolio_weights = portfolio_weights.sort_index()
        
        holding_periods = {}
        current_holdings = {}
        
        for date, row in portfolio_weights.iterrows():
            # Check which positions are held
            for ticker, weight in row.items():
                is_held = abs(weight) >= min_weight
                
                if is_held:
                    if ticker not in current_holdings:
                        # New position
                        current_holdings[ticker] = {
                            'start_date': date,
                            'end_date': None,
                            'max_weight': abs(weight),
                            'avg_weight': abs(weight),
                            'days': 0
                        }
                    else:
                        # Update existing position
                        current_holdings[ticker]['max_weight'] = max(
                            current_holdings[ticker]['max_weight'],
                            abs(weight)
                        )
                        current_holdings[ticker]['avg_weight'] = (
                            current_holdings[ticker]['avg_weight'] + abs(weight)
                        ) / 2
                        current_holdings[ticker]['days'] += 1
                else:
                    # Position closed
                    if ticker in current_holdings:
                        holding = current_holdings[ticker]
                        holding['end_date'] = date
                        holding['days'] = (date - holding['start_date']).days
                        
                        if ticker not in holding_periods:
                            holding_periods[ticker] = []
                        holding_periods[ticker].append(holding)
                        
                        del current_holdings[ticker]
        
        # Close any remaining positions
        final_date = portfolio_weights.index[-1]
        for ticker, holding in current_holdings.items():
            holding['end_date'] = final_date
            holding['days'] = (final_date - holding['start_date']).days
            
            if ticker not in holding_periods:
                holding_periods[ticker] = []
            holding_periods[ticker].append(holding)
        
        # Calculate statistics
        all_periods = []
        for ticker_periods in holding_periods.values():
            all_periods.extend([p['days'] for p in ticker_periods])
        
        if not all_periods:
            return {'error': 'No holding periods found'}
        
        results = {
            'holding_periods_by_ticker': {
                ticker: [
                    {
                        'start_date': p['start_date'].isoformat() if isinstance(p['start_date'], datetime) else str(p['start_date']),
                        'end_date': p['end_date'].isoformat() if isinstance(p['end_date'], datetime) else str(p['end_date']),
                        'days': p['days'],
                        'max_weight': float(p['max_weight']),
                        'avg_weight': float(p['avg_weight'])
                    }
                    for p in periods
                ]
                for ticker, periods in holding_periods.items()
            },
            'statistics': {
                'mean_holding_period_days': float(np.mean(all_periods)),
                'median_holding_period_days': float(np.median(all_periods)),
                'min_holding_period_days': int(np.min(all_periods)),
                'max_holding_period_days': int(np.max(all_periods)),
                'std_holding_period_days': float(np.std(all_periods)),
            },
            'distribution': {
                'short_term_0_30_days': int(np.sum(np.array(all_periods) <= 30)),
                'medium_term_31_90_days': int(np.sum((np.array(all_periods) > 30) & (np.array(all_periods) <= 90))),
                'long_term_91_180_days': int(np.sum((np.array(all_periods) > 90) & (np.array(all_periods) <= 180))),
                'very_long_term_180_plus_days': int(np.sum(np.array(all_periods) > 180)),
            }
        }
        
        return results
    
    def calculate_position_stability(
        self,
        portfolio_weights: pd.DataFrame,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Calculate position stability (how often top positions change).
        
        Args:
            portfolio_weights: DataFrame with Date index and Ticker columns
            top_n: Number of top positions to track
            
        Returns:
            Dictionary with stability metrics
        """
        if portfolio_weights.empty:
            return {'error': 'No portfolio data'}
        
        portfolio_weights = portfolio_weights.sort_index()
        
        top_positions_by_date = {}
        position_ranks = defaultdict(list)
        
        for date, row in portfolio_weights.iterrows():
            # Get top N positions
            top_positions = row.abs().nlargest(top_n).index.tolist()
            top_positions_by_date[str(date)] = top_positions
            
            # Track rank for each ticker
            ranked = row.abs().rank(ascending=False)
            for ticker in row.index:
                position_ranks[ticker].append({
                    'date': date,
                    'rank': float(ranked[ticker]),
                    'weight': float(row[ticker])
                })
        
        # Calculate stability metrics
        all_dates = list(top_positions_by_date.keys())
        position_changes = 0
        
        for i in range(1, len(all_dates)):
            prev_positions = set(top_positions_by_date[all_dates[i-1]])
            curr_positions = set(top_positions_by_date[all_dates[i]])
            
            # Count positions that changed
            changes = len(prev_positions.symmetric_difference(curr_positions))
            position_changes += changes
        
        results = {
            'top_n': top_n,
            'total_periods': len(all_dates),
            'position_changes': position_changes,
            'avg_changes_per_period': float(position_changes / (len(all_dates) - 1)) if len(all_dates) > 1 else 0.0,
            'stability_score': float(1.0 - (position_changes / (len(all_dates) * top_n))) if len(all_dates) > 0 else 0.0,
            'top_positions_by_date': top_positions_by_date,
            'position_rank_history': {
                ticker: [
                    {
                        'date': r['date'].isoformat() if isinstance(r['date'], datetime) else str(r['date']),
                        'rank': r['rank'],
                        'weight': r['weight']
                    }
                    for r in ranks
                ]
                for ticker, ranks in position_ranks.items()
            }
        }
        
        return results
