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
        stock_features: pd.DataFrame  # Ticker x Features
    ) -> Dict[str, Any]:
        """
        Analyze portfolio style.
        
        Args:
            portfolio_weights: Portfolio weights
            stock_features: Stock features (PE, market_cap, etc.)
            
        Returns:
            Dictionary with style analysis
        """
        # Align tickers
        common_tickers = portfolio_weights.index.intersection(stock_features.index)
        weights_aligned = portfolio_weights.loc[common_tickers]
        features_aligned = stock_features.loc[common_tickers]
        
        # Normalize weights
        weights_aligned = weights_aligned / weights_aligned.sum()
        
        # Growth vs Value
        growth_value = self._classify_growth_value(weights_aligned, features_aligned)
        
        # Size classification
        size_class = self._classify_size(weights_aligned, features_aligned)
        
        # Style consistency
        consistency = self._calculate_consistency(weights_aligned, features_aligned)
        
        return {
            'growth_value': growth_value,
            'size': size_class,
            'consistency': consistency,
            'overall_style': self._determine_overall_style(growth_value, size_class)
        }
    
    def _classify_growth_value(
        self,
        weights: pd.Series,
        features: pd.DataFrame
    ) -> Dict[str, Any]:
        """Classify growth vs value."""
        # Check for PE ratio
        pe_col = None
        for col in ['pe_ratio', 'pe', 'price_to_earnings']:
            if col in features.columns:
                pe_col = col
                break
        
        if pe_col:
            pe_values = features[pe_col].dropna()
            if len(pe_values) > 0:
                # Weighted average PE
                portfolio_pe = (weights.loc[pe_values.index] * pe_values).sum()
                avg_pe = pe_values.mean()
                
                if portfolio_pe < avg_pe * 0.8:
                    classification = 'value'
                    score = 0.3
                elif portfolio_pe > avg_pe * 1.2:
                    classification = 'growth'
                    score = 0.7
                else:
                    classification = 'blend'
                    score = 0.5
                
                return {
                    'classification': classification,
                    'score': score,
                    'portfolio_pe': float(portfolio_pe),
                    'market_avg_pe': float(avg_pe)
                }
        
        return {'classification': 'unknown', 'score': 0.5}
    
    def _classify_size(
        self,
        weights: pd.Series,
        features: pd.DataFrame
    ) -> Dict[str, Any]:
        """Classify large vs small cap."""
        # Check for market cap
        mcap_col = None
        for col in ['market_cap', 'marketcap', 'mcap']:
            if col in features.columns:
                mcap_col = col
                break
        
        if mcap_col:
            mcap_values = features[mcap_col].dropna()
            if len(mcap_values) > 0:
                # Weighted average market cap
                portfolio_mcap = (weights.loc[mcap_values.index] * mcap_values).sum()
                median_mcap = mcap_values.median()
                
                if portfolio_mcap > median_mcap * 2:
                    classification = 'large_cap'
                elif portfolio_mcap < median_mcap * 0.5:
                    classification = 'small_cap'
                else:
                    classification = 'mid_cap'
                
                return {
                    'classification': classification,
                    'portfolio_mcap': float(portfolio_mcap),
                    'median_mcap': float(median_mcap)
                }
        
        return {'classification': 'unknown'}
    
    def _calculate_consistency(
        self,
        weights: pd.Series,
        features: pd.DataFrame
    ) -> Dict[str, float]:
        """Calculate style consistency over time."""
        # Simplified - would need time series data
        return {
            'consistency_score': 0.8,  # Placeholder
            'style_drift': 0.1
        }
    
    def _determine_overall_style(
        self,
        growth_value: Dict,
        size: Dict
    ) -> str:
        """Determine overall style."""
        gv = growth_value.get('classification', 'blend')
        sz = size.get('classification', 'mid_cap')
        
        return f"{gv.title()} {sz.replace('_', ' ').title()}"
