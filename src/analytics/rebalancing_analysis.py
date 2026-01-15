"""
Portfolio Rebalancing Analysis
===============================
Analyze rebalancing decisions, costs, and drift.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


class RebalancingAnalyzer:
    """Analyze portfolio rebalancing."""
    
    def __init__(self, transaction_cost: float = 0.001):
        """
        Initialize rebalancing analyzer.
        
        Args:
            transaction_cost: Transaction cost as fraction (0.001 = 0.1%)
        """
        self.transaction_cost = transaction_cost
    
    def analyze(
        self,
        portfolio_weights: pd.DataFrame,  # Date x Ticker weights
        target_weights: Optional[pd.Series] = None,  # Target weights
        stock_returns: Optional[pd.DataFrame] = None,  # Date x Ticker returns
    ) -> Dict[str, Any]:
        """
        Analyze rebalancing.
        
        Args:
            portfolio_weights: Actual portfolio weights over time
            target_weights: Target weights (if None, uses first period as target)
            stock_returns: Stock returns for cost calculation
            
        Returns:
            Dictionary with rebalancing analysis
        """
        if len(portfolio_weights) == 0:
            return {'error': 'No portfolio weights provided'}
        
        # Use first period as target if not provided
        if target_weights is None:
            target_weights = portfolio_weights.iloc[0]
        
        results = {
            'target_weights': target_weights.to_dict(),
            'rebalancing_events': [],
            'drift_analysis': {},
            'cost_analysis': {},
            'recommendations': {}
        }
        
        # Calculate drift over time
        drift_series = []
        for date, current_weights in portfolio_weights.iterrows():
            # Calculate drift (deviation from target)
            drift = (current_weights - target_weights).abs().sum()
            drift_series.append({
                'date': date,
                'drift': float(drift),
                'max_position_drift': float((current_weights - target_weights).abs().max())
            })
        
        results['drift_analysis'] = {
            'drift_series': drift_series,
            'avg_drift': float(np.mean([d['drift'] for d in drift_series])),
            'max_drift': float(np.max([d['drift'] for d in drift_series])),
            'current_drift': float(drift_series[-1]['drift']) if drift_series else 0
        }
        
        # Identify rebalancing events (significant weight changes)
        rebalance_threshold = 0.05  # 5% change triggers rebalance
        rebalancing_events = []
        
        for i in range(1, len(portfolio_weights)):
            prev_weights = portfolio_weights.iloc[i-1]
            curr_weights = portfolio_weights.iloc[i]
            
            weight_changes = (curr_weights - prev_weights).abs()
            total_change = weight_changes.sum()
            
            if total_change > rebalance_threshold:
                # Calculate turnover (sum of absolute changes)
                turnover = weight_changes.sum()
                
                # Estimate transaction cost
                if stock_returns is not None:
                    # Use portfolio value estimate
                    portfolio_value = 1.0  # Normalized
                    transaction_cost_amount = turnover * portfolio_value * self.transaction_cost
                else:
                    transaction_cost_amount = turnover * self.transaction_cost
                
                rebalancing_events.append({
                    'date': portfolio_weights.index[i],
                    'turnover': float(turnover),
                    'transaction_cost': float(transaction_cost_amount),
                    'largest_changes': weight_changes.nlargest(5).to_dict()
                })
        
        results['rebalancing_events'] = rebalancing_events
        
        # Cost analysis
        total_turnover = sum([e['turnover'] for e in rebalancing_events])
        total_cost = sum([e['transaction_cost'] for e in rebalancing_events])
        annual_cost = total_cost * (252 / len(portfolio_weights)) if len(portfolio_weights) > 0 else 0
        
        results['cost_analysis'] = {
            'total_turnover': float(total_turnover),
            'total_transaction_cost': float(total_cost),
            'annual_transaction_cost': float(annual_cost),
            'num_rebalancing_events': len(rebalancing_events),
            'avg_turnover_per_event': float(total_turnover / len(rebalancing_events)) if rebalancing_events else 0
        }
        
        # Recommendations
        current_drift = results['drift_analysis']['current_drift']
        rebalance_threshold = 0.10  # 10% drift threshold
        
        if current_drift > rebalance_threshold:
            results['recommendations'] = {
                'should_rebalance': True,
                'reason': f'Current drift ({current_drift:.1%}) exceeds threshold ({rebalance_threshold:.1%})',
                'estimated_cost': float(current_drift * self.transaction_cost),
                'priority': 'high' if current_drift > 0.20 else 'medium'
            }
        else:
            results['recommendations'] = {
                'should_rebalance': False,
                'reason': f'Current drift ({current_drift:.1%}) is within acceptable range',
                'priority': 'low'
            }
        
        return results
