"""
Factor Exposure Analysis
========================
Deep dive into portfolio's factor loadings and exposures.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime


class FactorExposureAnalyzer:
    """Analyze portfolio factor exposures."""
    
    def __init__(self):
        pass
    
    def analyze(
        self,
        portfolio_weights: pd.Series,  # Ticker -> Weight
        stock_features: pd.DataFrame,  # Ticker x Feature
        factor_definitions: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze factor exposures.
        
        Args:
            portfolio_weights: Portfolio weights (Ticker -> Weight)
            stock_features: Stock features/characteristics (Ticker x Feature)
            factor_definitions: Factor definitions (Factor -> List of features)
            
        Returns:
            Dictionary with factor exposure results
        """
        # Align tickers
        common_tickers = portfolio_weights.index.intersection(stock_features.index)
        weights_aligned = portfolio_weights.loc[common_tickers]
        features_aligned = stock_features.loc[common_tickers]
        
        # Normalize weights
        weights_aligned = weights_aligned / weights_aligned.sum()
        
        # Default factor definitions if not provided
        if factor_definitions is None:
            factor_definitions = self._get_default_factor_definitions(features_aligned.columns)
        
        # Calculate factor exposures
        factor_exposures = []
        factor_contributions = {}
        
        for factor_name, feature_list in factor_definitions.items():
            # Get relevant features
            available_features = [f for f in feature_list if f in features_aligned.columns]
            if len(available_features) == 0:
                continue
            
            # Calculate factor score for each stock
            factor_scores = features_aligned[available_features].mean(axis=1)
            
            # Portfolio exposure = weighted average of factor scores
            exposure = (weights_aligned * factor_scores).sum()
            
            # Contribution to return (simplified - using factor score as proxy)
            # Scale to percentage (assuming factor scores are 0-100 scale)
            contribution_to_return = exposure * 0.01  # Convert to percentage
            
            # Contribution to risk (normalized and scaled)
            # Use coefficient of variation (std/mean) to normalize, then scale by exposure
            factor_mean = factor_scores.mean()
            factor_std = factor_scores.std()
            
            if factor_mean != 0 and not np.isnan(factor_mean):
                # Coefficient of variation * exposure, scaled to percentage
                contribution_to_risk = abs(exposure) * (factor_std / factor_mean) * 0.01
            else:
                contribution_to_risk = 0.0
            
            # Cap risk contribution at reasonable values (e.g., 100%)
            contribution_to_risk = min(contribution_to_risk, 1.0) * 100  # Convert to percentage
            
            factor_exposures.append({
                'factor_name': factor_name,
                'factor_type': self._classify_factor_type(factor_name),
                'exposure': float(exposure),
                'contribution_to_return': float(contribution_to_return),
                'contribution_to_risk': float(contribution_to_risk),
                'metrics': {
                    'min_exposure': float(factor_scores.min()),
                    'max_exposure': float(factor_scores.max()),
                    'avg_exposure': float(factor_scores.mean()),
                    'std_exposure': float(factor_scores.std())
                }
            })
        
        return {
            'factor_exposures': factor_exposures,
            'total_factors': len(factor_exposures),
            'portfolio_characteristics': {
                'num_positions': len(weights_aligned),
                'concentration': float((weights_aligned ** 2).sum()),  # Herfindahl index
                'effective_n': 1 / (weights_aligned ** 2).sum() if (weights_aligned ** 2).sum() > 0 else 0
            }
        }
    
    def _get_default_factor_definitions(self, available_features: List[str]) -> Dict[str, List[str]]:
        """Get default factor definitions based on available features."""
        definitions = {}
        
        # Market factor (beta proxy)
        if 'beta' in available_features:
            definitions['market'] = ['beta']
        
        # Size factor
        size_features = [f for f in available_features if 'market_cap' in f.lower() or 'size' in f.lower()]
        if size_features:
            definitions['size'] = size_features
        
        # Value factor
        value_features = [f for f in available_features if any(v in f.lower() for v in ['pe', 'pb', 'value', 'book'])]
        if value_features:
            definitions['value'] = value_features
        
        # Momentum factor
        momentum_features = [f for f in available_features if any(m in f.lower() for m in ['momentum', 'return', 'rsi'])]
        if momentum_features:
            definitions['momentum'] = momentum_features
        
        # Quality factor
        quality_features = [f for f in available_features if any(q in f.lower() for q in ['roe', 'margin', 'quality', 'profit'])]
        if quality_features:
            definitions['quality'] = quality_features
        
        # Low volatility factor
        vol_features = [f for f in available_features if any(v in f.lower() for v in ['vol', 'volatility', 'std'])]
        if vol_features:
            definitions['low_vol'] = vol_features
        
        return definitions
    
    def _classify_factor_type(self, factor_name: str) -> str:
        """Classify factor type."""
        factor_name_lower = factor_name.lower()
        if 'size' in factor_name_lower or 'market' in factor_name_lower:
            return 'style'
        elif 'value' in factor_name_lower or 'growth' in factor_name_lower or 'momentum' in factor_name_lower:
            return 'style'
        elif 'quality' in factor_name_lower or 'profit' in factor_name_lower:
            return 'quality'
        elif 'vol' in factor_name_lower:
            return 'risk'
        else:
            return 'other'
