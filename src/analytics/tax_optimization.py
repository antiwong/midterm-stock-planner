"""
Tax Optimization Analysis
=========================
Tax-loss harvesting, wash sale detection, and tax-efficient rebalancing.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


class TaxOptimizer:
    """Analyze and optimize tax implications of portfolio decisions."""
    
    def __init__(self, wash_sale_window_days: int = 30):
        """
        Initialize tax optimizer.
        
        Args:
            wash_sale_window_days: Days before/after sale to check for wash sale (default 30)
        """
        self.wash_sale_window = timedelta(days=wash_sale_window_days)
    
    def detect_wash_sales(
        self,
        trades: pd.DataFrame,
        cost_basis: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Detect wash sales in trading history.
        
        Args:
            trades: DataFrame with columns: date, ticker, action (buy/sell), shares, price
            cost_basis: Optional dictionary of ticker -> cost basis per share
            
        Returns:
            Dictionary with wash sale analysis
        """
        if trades.empty:
            return {'wash_sales': [], 'total_wash_sale_loss': 0.0, 'count': 0}
        
        wash_sales = []
        ticker_trades = defaultdict(list)
        
        # Group trades by ticker
        for _, trade in trades.iterrows():
            ticker_trades[trade['ticker']].append({
                'date': pd.to_datetime(trade['date']),
                'action': trade['action'].lower(),
                'shares': trade.get('shares', 0),
                'price': trade.get('price', 0.0)
            })
        
        # Check each ticker for wash sales
        for ticker, ticker_trade_list in ticker_trades.items():
            # Sort by date
            ticker_trade_list.sort(key=lambda x: x['date'])
            
            for i, trade in enumerate(ticker_trade_list):
                if trade['action'] == 'sell':
                    # Check for purchases within wash sale window
                    sale_date = trade['date']
                    window_start = sale_date - self.wash_sale_window
                    window_end = sale_date + self.wash_sale_window
                    
                    # Check previous trades in window
                    for prev_trade in ticker_trade_list[:i]:
                        if window_start <= prev_trade['date'] <= sale_date:
                            if prev_trade['action'] == 'buy':
                                # Potential wash sale
                                loss = (prev_trade['price'] - trade['price']) * min(
                                    prev_trade['shares'], trade['shares']
                                )
                                
                                if loss > 0:  # Only if it's a loss
                                    wash_sales.append({
                                        'ticker': ticker,
                                        'sale_date': sale_date.isoformat(),
                                        'purchase_date': prev_trade['date'].isoformat(),
                                        'shares': min(prev_trade['shares'], trade['shares']),
                                        'loss_amount': float(loss),
                                        'sale_price': float(trade['price']),
                                        'purchase_price': float(prev_trade['price'])
                                    })
                    
                    # Check future trades in window
                    for next_trade in ticker_trade_list[i+1:]:
                        if sale_date <= next_trade['date'] <= window_end:
                            if next_trade['action'] == 'buy':
                                # Potential wash sale (replacement purchase)
                                loss = (trade['price'] - next_trade['price']) * min(
                                    trade['shares'], next_trade['shares']
                                )
                                
                                if loss > 0:  # Only if it's a loss
                                    wash_sales.append({
                                        'ticker': ticker,
                                        'sale_date': sale_date.isoformat(),
                                        'replacement_date': next_trade['date'].isoformat(),
                                        'shares': min(trade['shares'], next_trade['shares']),
                                        'loss_amount': float(loss),
                                        'sale_price': float(trade['price']),
                                        'replacement_price': float(next_trade['price']),
                                        'is_replacement': True
                                    })
        
        total_loss = sum(ws['loss_amount'] for ws in wash_sales)
        
        return {
            'wash_sales': wash_sales,
            'total_wash_sale_loss': float(total_loss),
            'count': len(wash_sales),
            'affected_tickers': list(set(ws['ticker'] for ws in wash_sales))
        }
    
    def suggest_tax_loss_harvesting(
        self,
        positions: pd.DataFrame,
        current_prices: Dict[str, float],
        cost_basis: Dict[str, float],
        min_loss_threshold: float = 100.0,
        max_harvest_pct: float = 0.3
    ) -> Dict[str, Any]:
        """
        Suggest tax-loss harvesting opportunities.
        
        Args:
            positions: DataFrame with columns: ticker, shares
            current_prices: Dictionary of ticker -> current price
            cost_basis: Dictionary of ticker -> cost basis per share
            min_loss_threshold: Minimum loss amount to consider harvesting
            max_harvest_pct: Maximum percentage of portfolio to harvest
            
        Returns:
            Dictionary with harvesting suggestions
        """
        suggestions = []
        total_portfolio_value = 0.0
        total_harvestable_loss = 0.0
        
        for _, pos in positions.iterrows():
            ticker = pos['ticker']
            shares = pos.get('shares', 0)
            
            if ticker not in current_prices or ticker not in cost_basis:
                continue
            
            current_price = current_prices[ticker]
            basis = cost_basis[ticker]
            position_value = shares * current_price
            total_portfolio_value += position_value
            
            # Calculate unrealized loss
            unrealized_loss = (basis - current_price) * shares
            
            if unrealized_loss >= min_loss_threshold:
                loss_pct = (basis - current_price) / basis if basis > 0 else 0
                
                suggestions.append({
                    'ticker': ticker,
                    'shares': shares,
                    'current_price': float(current_price),
                    'cost_basis': float(basis),
                    'unrealized_loss': float(unrealized_loss),
                    'loss_percentage': float(loss_pct),
                    'position_value': float(position_value),
                    'harvest_recommended': True
                })
                
                total_harvestable_loss += unrealized_loss
        
        # Sort by loss amount
        suggestions.sort(key=lambda x: x['unrealized_loss'], reverse=True)
        
        # Limit to max_harvest_pct of portfolio
        harvest_value_limit = total_portfolio_value * max_harvest_pct
        limited_suggestions = []
        cumulative_value = 0.0
        
        for suggestion in suggestions:
            if cumulative_value + suggestion['position_value'] <= harvest_value_limit:
                limited_suggestions.append(suggestion)
                cumulative_value += suggestion['position_value']
            else:
                # Partial harvest
                remaining_value = harvest_value_limit - cumulative_value
                if remaining_value > 0:
                    partial_shares = int((remaining_value / suggestion['current_price']) * 0.9)  # 90% to be safe
                    if partial_shares > 0:
                        partial_suggestion = suggestion.copy()
                        partial_suggestion['shares'] = partial_shares
                        partial_suggestion['position_value'] = partial_shares * suggestion['current_price']
                        partial_suggestion['unrealized_loss'] = (suggestion['cost_basis'] - suggestion['current_price']) * partial_shares
                        limited_suggestions.append(partial_suggestion)
                break
        
        return {
            'suggestions': limited_suggestions,
            'total_harvestable_loss': float(total_harvestable_loss),
            'recommended_harvest_loss': sum(s['unrealized_loss'] for s in limited_suggestions),
            'portfolio_value': float(total_portfolio_value),
            'harvest_percentage': float(cumulative_value / total_portfolio_value) if total_portfolio_value > 0 else 0.0,
            'count': len(limited_suggestions)
        }
    
    def analyze_tax_efficiency(
        self,
        portfolio_returns: pd.Series,
        trades: pd.DataFrame,
        turnover_by_period: Optional[Dict[str, float]] = None,
        long_term_threshold_days: int = 365
    ) -> Dict[str, Any]:
        """
        Analyze tax efficiency of portfolio.
        
        Args:
            portfolio_returns: Portfolio returns time series
            trades: Trading history DataFrame
            turnover_by_period: Optional turnover by period (annual, quarterly, etc.)
            long_term_threshold_days: Days to qualify for long-term capital gains
            
        Returns:
            Dictionary with tax efficiency metrics
        """
        results = {
            'holding_periods': {},
            'short_term_trades': 0,
            'long_term_trades': 0,
            'estimated_tax_impact': {},
            'turnover_analysis': {}
        }
        
        if trades.empty:
            return results
        
        # Analyze holding periods
        ticker_holdings = defaultdict(list)
        
        for _, trade in trades.iterrows():
            ticker = trade['ticker']
            date = pd.to_datetime(trade['date'])
            action = trade['action'].lower()
            
            if action == 'buy':
                ticker_holdings[ticker].append({
                    'date': date,
                    'shares': trade.get('shares', 0),
                    'price': trade.get('price', 0.0),
                    'type': 'buy'
                })
            elif action == 'sell':
                # Match with earliest buy
                for holding in ticker_holdings[ticker]:
                    if holding['type'] == 'buy':
                        holding_period = (date - holding['date']).days
                        is_long_term = holding_period >= long_term_threshold_days
                        
                        if is_long_term:
                            results['long_term_trades'] += 1
                        else:
                            results['short_term_trades'] += 1
                        
                        if ticker not in results['holding_periods']:
                            results['holding_periods'][ticker] = []
                        
                        results['holding_periods'][ticker].append({
                            'holding_period_days': holding_period,
                            'is_long_term': is_long_term,
                            'buy_date': holding['date'].isoformat(),
                            'sell_date': date.isoformat()
                        })
                        
                        holding['type'] = 'matched'
                        break
        
        # Calculate tax impact estimates (assuming 20% long-term, 37% short-term)
        long_term_rate = 0.20
        short_term_rate = 0.37
        
        # Estimate based on portfolio returns and turnover
        if turnover_by_period:
            annual_turnover = turnover_by_period.get('annual', 0.0)
            results['estimated_tax_impact'] = {
                'annual_turnover': float(annual_turnover),
                'estimated_short_term_pct': min(annual_turnover, 1.0),  # Assume high turnover = more short-term
                'estimated_long_term_pct': max(0, 1.0 - annual_turnover),
            }
        
        # Average holding periods
        all_holding_periods = []
        for ticker_periods in results['holding_periods'].values():
            all_holding_periods.extend([p['holding_period_days'] for p in ticker_periods])
        
        if all_holding_periods:
            results['avg_holding_period_days'] = float(np.mean(all_holding_periods))
            results['median_holding_period_days'] = float(np.median(all_holding_periods))
        
        # Turnover analysis
        if turnover_by_period:
            results['turnover_analysis'] = {
                'annual_turnover': turnover_by_period.get('annual', 0.0),
                'quarterly_turnover': turnover_by_period.get('quarterly', 0.0),
                'tax_efficiency_score': max(0, 1.0 - turnover_by_period.get('annual', 1.0))  # Lower turnover = more efficient
            }
        
        return results
    
    def optimize_rebalancing_timing(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        unrealized_gains: Dict[str, float],
        unrealized_losses: Dict[str, float],
        rebalance_threshold: float = 0.05
    ) -> Dict[str, Any]:
        """
        Suggest tax-efficient rebalancing timing.
        
        Args:
            current_weights: Current portfolio weights
            target_weights: Target portfolio weights
            unrealized_gains: Unrealized gains by ticker
            unrealized_losses: Unrealized losses by ticker
            rebalance_threshold: Weight deviation threshold to trigger rebalance
            
        Returns:
            Dictionary with rebalancing recommendations
        """
        recommendations = {
            'sell_recommendations': [],
            'buy_recommendations': [],
            'hold_recommendations': [],
            'tax_impact_estimate': 0.0
        }
        
        all_tickers = set(current_weights.keys()) | set(target_weights.keys())
        
        for ticker in all_tickers:
            current_w = current_weights.get(ticker, 0.0)
            target_w = target_weights.get(ticker, 0.0)
            deviation = current_w - target_w
            
            if abs(deviation) < rebalance_threshold:
                recommendations['hold_recommendations'].append({
                    'ticker': ticker,
                    'current_weight': float(current_w),
                    'target_weight': float(target_w),
                    'deviation': float(deviation),
                    'reason': 'Within threshold'
                })
            elif deviation > 0:  # Overweight - consider selling
                # Prefer selling positions with losses (tax-loss harvesting)
                has_loss = ticker in unrealized_losses and unrealized_losses[ticker] > 0
                has_gain = ticker in unrealized_gains and unrealized_gains[ticker] > 0
                
                priority = 'high' if has_loss else ('low' if has_gain else 'medium')
                
                recommendations['sell_recommendations'].append({
                    'ticker': ticker,
                    'current_weight': float(current_w),
                    'target_weight': float(target_w),
                    'deviation': float(deviation),
                    'unrealized_loss': float(unrealized_losses.get(ticker, 0)),
                    'unrealized_gain': float(unrealized_gains.get(ticker, 0)),
                    'priority': priority,
                    'reason': 'Tax-loss harvesting opportunity' if has_loss else 'Rebalancing needed'
                })
            else:  # Underweight - consider buying
                recommendations['buy_recommendations'].append({
                    'ticker': ticker,
                    'current_weight': float(current_w),
                    'target_weight': float(target_w),
                    'deviation': float(deviation),
                    'priority': 'medium',
                    'reason': 'Rebalancing needed'
                })
        
        # Sort by priority
        recommendations['sell_recommendations'].sort(
            key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x['priority']]
        )
        
        # Estimate tax impact (only on sells with gains)
        total_tax_impact = sum(
            rec['unrealized_gain'] * 0.20  # Assume long-term rate
            for rec in recommendations['sell_recommendations']
            if rec['unrealized_gain'] > 0
        )
        recommendations['tax_impact_estimate'] = float(total_tax_impact)
        
        return recommendations
