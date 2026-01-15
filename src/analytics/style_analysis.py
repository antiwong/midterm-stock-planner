"""
Style Analysis
==============
Classify portfolio style (growth vs value, large vs small, etc.)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime


class StyleAnalyzer:
    """Analyze portfolio style characteristics."""
    
    def __init__(self):
        pass
    
    def analyze(
        self,
        portfolio_weights: pd.Series,  # Ticker -> Weight
        stock_features: pd.DataFrame,  # Ticker x Feature
        market_cap_data: Optional[pd.Series] = None  # Ticker -> Market Cap
    ) -> Dict[str, Any]:
        """
        Analyze portfolio style.
        
        Args:
            portfolio_weights: Portfolio weights
            stock_features: Stock features (PE, PB, growth rates, etc.)
            market_cap_data: Market capitalization data
            
        Returns:
            Dictionary with style analysis
        """
        # Align tickers
        common_tickers = portfolio_weights.index.intersection(stock_features.index)
        if len(common_tickers) == 0:
            return {'error': 'No common tickers between weights and features'}
        
        weights_aligned = portfolio_weights.loc[common_tickers]
        features_aligned = stock_features.loc[common_tickers]
        
        # Normalize weights
        weights_aligned = weights_aligned / weights_aligned.sum()
        
        results = {
            'growth_value': {},
            'size': {},
            'style_consistency': {},
            'style_drift': None
        }
        
        # Growth vs Value
        pe_col = None
        for col in ['pe_ratio', 'pe', 'price_to_earnings']:
            if col in features_aligned.columns:
                pe_col = col
                break
        
        if pe_col:
            pe_values = features_aligned[pe_col].dropna()
            if len(pe_values) > 0:
                # Weighted average PE
                portfolio_pe = (weights_aligned.loc[pe_values.index] * pe_values).sum()
                
                # Classify
                if portfolio_pe > 25:
                    growth_value_class = 'Growth'
                elif portfolio_pe < 15:
                    growth_value_class = 'Value'
                else:
                    growth_value_class = 'Blend'
                
                results['growth_value'] = {
                    'classification': growth_value_class,
                    'portfolio_pe': float(portfolio_pe),
                    'weighted_avg_pe': float(portfolio_pe)
                }
        
        # Size (Large vs Small)
        if market_cap_data is not None:
            market_caps = market_cap_data.loc[common_tickers].dropna()
            if len(market_caps) > 0:
                # Weighted average market cap
                portfolio_market_cap = (weights_aligned.loc[market_caps.index] * market_caps).sum()
                
                # Classify (billions)
                if portfolio_market_cap > 50:
                    size_class = 'Large Cap'
                elif portfolio_market_cap > 10:
                    size_class = 'Mid Cap'
                else:
                    size_class = 'Small Cap'
                
                results['size'] = {
                    'classification': size_class,
                    'portfolio_market_cap_billions': float(portfolio_market_cap / 1e9),
                    'weighted_avg_market_cap': float(portfolio_market_cap)
                }
        else:
            # Try to infer from features
            mc_col = None
            for col in ['market_cap', 'market_capitalization']:
                if col in features_aligned.columns:
                    mc_col = col
                    break
            
            if mc_col:
                market_caps = features_aligned[mc_col].dropna()
                if len(market_caps) > 0:
                    portfolio_market_cap = (weights_aligned.loc[market_caps.index] * market_caps).sum()
                    
                    if portfolio_market_cap > 50e9:
                        size_class = 'Large Cap'
                    elif portfolio_market_cap > 10e9:
                        size_class = 'Mid Cap'
                    else:
                        size_class = 'Small Cap'
                    
                    results['size'] = {
                        'classification': size_class,
                        'portfolio_market_cap_billions': float(portfolio_market_cap / 1e9)
                    }
        
        # Style consistency (how consistent is the style over time)
        # This would require historical data - placeholder for now
        results['style_consistency'] = {
            'growth_value_consistency': 'High',  # Would calculate from history
            'size_consistency': 'High',
            'overall_consistency': 'High'
        }
        
        return results
