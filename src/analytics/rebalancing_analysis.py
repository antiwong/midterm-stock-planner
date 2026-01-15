"""
Portfolio Rebalancing Analysis
================================
Analyze rebalancing decisions, costs, and optimal frequency.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta


class RebalancingAnalyzer:
    """Analyze portfolio rebalancing."""
    
    def __init__(self):
        pass
    
    def analyze(
        self,
        portfolio_weights: pd.DataFrame,  # Date x Ticker weights
        target_weights: Optional[pd.Series] = None,  # Target weights
        transaction_cost: float = 0.001,  # 0.1% per trade
        rebalancing_threshold: float = 0.05  # 5% drift threshold
    ) -> Dict[str, Any]:
        """
        Analyze rebalancing.
        
        Args:
            portfolio_weights: Portfolio weights over time
            target_weights: Target weights (uses first period if not provided)
            transaction_cost: Cost per rebalance (as fraction)
            rebalancing_threshold: Drift threshold to trigger rebalance
            
        Returns:
            Dictionary with rebalancing analysis
        """
        if len(portfolio_weights) == 0:
            return {'error': 'No weight data available'}
        
        # Use first period as target if not provided
        if target_weights is None:
            target_weights = portfolio_weights.iloc[0]
        
        # Calculate drift over time
        drift = portfolio_weights.sub(target_weights, axis=1).abs().sum(axis=1)
        
        # Identify rebalancing events (when drift exceeds threshold)
        rebalance_events = drift[drift > rebalancing_threshold]
        
        # Calculate turnover (how much trading needed)
        turnover = []
        for i in range(1, len(portfolio_weights)):
            prev_weights = portfolio_weights.iloc[i-1]
            curr_weights = portfolio_weights.iloc[i]
            # Turnover = sum of absolute changes
            period_turnover = (curr_weights - prev_weights).abs().sum()
            turnover.append(period_turnover)
        
        avg_turnover = np.mean(turnover) if turnover else 0
        
        # Calculate transaction costs
        total_cost = avg_turnover * transaction_cost * len(portfolio_weights)
        
        # Optimal frequency analysis
        optimal_frequency = self._calculate_optimal_frequency(
            drift, transaction_cost, rebalancing_threshold
        )
        
        return {
            'current_drift': float(drift.iloc[-1]) if len(drift) > 0 else 0,
            'avg_drift': float(drift.mean()),
            'max_drift': float(drift.max()),
            'rebalance_events': len(rebalance_events),
            'avg_turnover': float(avg_turnover),
            'total_transaction_cost': float(total_cost),
            'optimal_frequency': optimal_frequency,
            'recommendation': self._get_rebalancing_recommendation(
                drift.iloc[-1] if len(drift) > 0 else 0,
                rebalancing_threshold
            )
        }
    
    def _calculate_optimal_frequency(
        self,
        drift: pd.Series,
        transaction_cost: float,
        threshold: float
    ) -> Dict[str, Any]:
        """Calculate optimal rebalancing frequency."""
        # Simplified: compare monthly vs quarterly vs annual
        frequencies = {
            'monthly': {'periods': 12, 'cost': transaction_cost * 12},
            'quarterly': {'periods': 4, 'cost': transaction_cost * 4},
            'annual': {'periods': 1, 'cost': transaction_cost * 1}
        }
        
        # Calculate average drift for each frequency
        for freq_name, freq_data in frequencies.items():
            # Simulate rebalancing at this frequency
            # (simplified - would need actual simulation)
            freq_data['avg_drift'] = drift.mean() * 0.5  # Placeholder
        
        # Recommend frequency with best cost/drift tradeoff
        best_freq = min(frequencies.items(), 
                       key=lambda x: x[1]['cost'] + x[1]['avg_drift'] * 10)
        
        return {
            'recommended': best_freq[0],
            'frequencies': frequencies
        }
    
    def _get_rebalancing_recommendation(
        self,
        current_drift: float,
        threshold: float
    ) -> str:
        """Get rebalancing recommendation."""
        if current_drift > threshold:
            return f"Rebalance now (drift {current_drift*100:.1f}% > {threshold*100:.0f}% threshold)"
        else:
            return f"Hold current allocation (drift {current_drift*100:.1f}% within threshold)"

