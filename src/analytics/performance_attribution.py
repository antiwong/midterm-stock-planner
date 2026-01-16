"""
Performance Attribution Analysis
=================================
Decompose portfolio returns into components: factor, sector, stock selection, timing.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path


class PerformanceAttributionAnalyzer:
    """Analyze performance attribution for portfolio returns."""
    
    def __init__(self):
        pass
    
    def analyze(
        self,
        portfolio_returns: pd.Series,
        portfolio_weights: pd.DataFrame,  # Date x Ticker weights
        stock_returns: pd.DataFrame,  # Date x Ticker returns
        factor_returns: Optional[pd.DataFrame] = None,  # Date x Factor returns
        sector_mapping: Optional[Dict[str, str]] = None,  # Ticker -> Sector
        benchmark_returns: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive performance attribution.
        
        Args:
            portfolio_returns: Portfolio returns time series
            portfolio_weights: Portfolio weights over time (Date x Ticker)
            stock_returns: Individual stock returns (Date x Ticker)
            factor_returns: Factor returns if available (Date x Factor)
            sector_mapping: Ticker to sector mapping
            benchmark_returns: Benchmark returns for comparison
            
        Returns:
            Dictionary with attribution results
        """
        results = {
            'total_return': float(portfolio_returns.sum()),
            'attributions': {},
            'breakdown': {}
        }
        
        # 1. Factor Attribution (if factor returns available)
        if factor_returns is not None and len(factor_returns) > 0:
            factor_attr = self._calculate_factor_attribution(
                portfolio_weights, stock_returns, factor_returns
            )
            results['attributions']['factor'] = factor_attr['total']
            results['breakdown']['factor'] = factor_attr['by_factor']
        
        # 2. Sector Attribution
        if sector_mapping:
            sector_attr = self._calculate_sector_attribution(
                portfolio_weights, stock_returns, sector_mapping
            )
            results['attributions']['sector'] = sector_attr['total']
            results['breakdown']['sector'] = sector_attr['by_sector']
        
        # 3. Stock Selection Attribution
        stock_attr = self._calculate_stock_selection_attribution(
            portfolio_weights, stock_returns, sector_mapping
        )
        results['attributions']['stock_selection'] = stock_attr['total']
        results['breakdown']['stock_selection'] = stock_attr['by_sector']
        
        # 4. Timing Attribution (rebalancing effects)
        timing_attr = self._calculate_timing_attribution(
            portfolio_weights, stock_returns
        )
        results['attributions']['timing'] = timing_attr
        
        # 5. Interaction Effects (residual)
        total_attributed = sum([
            results['attributions'].get('factor', 0),
            results['attributions'].get('sector', 0),
            results['attributions'].get('stock_selection', 0),
            results['attributions'].get('timing', 0)
        ])
        results['attributions']['interaction'] = results['total_return'] - total_attributed
        
        return results
    
    def _calculate_factor_attribution(
        self,
        weights: pd.DataFrame,
        stock_returns: pd.DataFrame,
        factor_returns: pd.DataFrame
    ) -> Dict[str, Any]:
        """Calculate factor attribution."""
        # Align dates
        common_dates = weights.index.intersection(stock_returns.index).intersection(factor_returns.index)
        weights_aligned = weights.loc[common_dates]
        stock_returns_aligned = stock_returns.loc[common_dates]
        factor_returns_aligned = factor_returns.loc[common_dates]
        
        # Only use common tickers that exist in both DataFrames
        common_tickers = weights_aligned.columns.intersection(stock_returns_aligned.columns)
        weights_common = weights_aligned[common_tickers]
        stock_returns_common = stock_returns_aligned[common_tickers]
        
        # Calculate factor loadings (simplified - using correlation as proxy)
        factor_loadings = {}
        for factor in factor_returns_aligned.columns:
            # Calculate portfolio's exposure to this factor
            # Simplified: use correlation between portfolio returns and factor returns
            portfolio_returns = (weights_common * stock_returns_common).sum(axis=1)
            correlation = portfolio_returns.corr(factor_returns_aligned[factor])
            factor_loadings[factor] = correlation if not np.isnan(correlation) else 0
        
        # Calculate attribution
        by_factor = {}
        total = 0.0
        
        for factor, loading in factor_loadings.items():
            factor_contribution = (factor_returns_aligned[factor] * loading).sum()
            by_factor[factor] = float(factor_contribution)
            total += factor_contribution
        
        return {
            'total': float(total),
            'by_factor': by_factor,
            'loadings': factor_loadings
        }
    
    def _calculate_sector_attribution(
        self,
        weights: pd.DataFrame,
        stock_returns: pd.DataFrame,
        sector_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Calculate sector allocation attribution."""
        # Align dates
        common_dates = weights.index.intersection(stock_returns.index)
        weights_aligned = weights.loc[common_dates]
        stock_returns_aligned = stock_returns.loc[common_dates]
        
        # Calculate sector weights and returns
        sector_weights = {}
        sector_returns = {}
        
        # Only process tickers that exist in both weights and stock_returns
        common_tickers = weights_aligned.columns.intersection(stock_returns_aligned.columns)
        
        for ticker in common_tickers:
            if ticker in sector_mapping:
                sector = sector_mapping[ticker]
                if sector not in sector_weights:
                    sector_weights[sector] = pd.Series(0, index=weights_aligned.index)
                    sector_returns[sector] = pd.Series(0, index=stock_returns_aligned.index)
                
                sector_weights[sector] += weights_aligned[ticker]
                # Weighted sector return
                sector_returns[sector] += weights_aligned[ticker] * stock_returns_aligned[ticker]
        
        # Calculate attribution
        by_sector = {}
        total = 0.0
        
        for sector in sector_weights.keys():
            # Sector contribution = weighted return
            sector_contribution = sector_returns[sector].sum()
            by_sector[sector] = float(sector_contribution)
            total += sector_contribution
        
        return {
            'total': float(total),
            'by_sector': by_sector
        }
    
    def _calculate_stock_selection_attribution(
        self,
        weights: pd.DataFrame,
        stock_returns: pd.DataFrame,
        sector_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Calculate stock selection attribution (within-sector picking)."""
        # Align dates
        common_dates = weights.index.intersection(stock_returns.index)
        weights_aligned = weights.loc[common_dates]
        stock_returns_aligned = stock_returns.loc[common_dates]
        
        # Only use common tickers that exist in both DataFrames
        common_tickers = weights_aligned.columns.intersection(stock_returns_aligned.columns)
        weights_common = weights_aligned[common_tickers]
        stock_returns_common = stock_returns_aligned[common_tickers]
        
        # Calculate portfolio return
        portfolio_returns = (weights_common * stock_returns_common).sum(axis=1)
        
        if sector_mapping:
            # Calculate by sector
            by_sector = {}
            for sector in set(sector_mapping.values()):
                sector_tickers = [t for t, s in sector_mapping.items() if s == sector]
                # Only include tickers that exist in both DataFrames (use common_tickers)
                common_sector_tickers = [t for t in sector_tickers if t in common_tickers]
                sector_weights = weights_common[common_sector_tickers] if common_sector_tickers else pd.DataFrame()
                sector_returns_data = stock_returns_common[common_sector_tickers] if common_sector_tickers else pd.DataFrame()
                
                if len(sector_weights.columns) > 0:
                    sector_portfolio_return = (sector_weights * sector_returns_data).sum(axis=1)
                    # Average sector return (equal-weighted benchmark)
                    sector_benchmark_return = sector_returns_data.mean(axis=1)
                    # Selection effect = portfolio return - benchmark return
                    selection_effect = (sector_portfolio_return - sector_benchmark_return).sum()
                    by_sector[sector] = float(selection_effect)
            
            total = sum(by_sector.values())
        else:
            # Overall selection effect
            # Compare to equal-weighted benchmark
            benchmark_returns = stock_returns_common.mean(axis=1)
            selection_effect = (portfolio_returns - benchmark_returns).sum()
            total = float(selection_effect)
            by_sector = {'overall': total}
        
        return {
            'total': float(total),
            'by_sector': by_sector
        }
    
    def _calculate_timing_attribution(
        self,
        weights: pd.DataFrame,
        stock_returns: pd.DataFrame
    ) -> float:
        """Calculate timing attribution (rebalancing effects)."""
        # Align dates
        common_dates = weights.index.intersection(stock_returns.index)
        weights_aligned = weights.loc[common_dates]
        stock_returns_aligned = stock_returns.loc[common_dates]
        
        # Only use common tickers that exist in both DataFrames
        common_tickers = weights_aligned.columns.intersection(stock_returns_aligned.columns)
        weights_common = weights_aligned[common_tickers]
        stock_returns_common = stock_returns_aligned[common_tickers]
        
        # Calculate buy-and-hold return (no rebalancing)
        initial_weights = weights_common.iloc[0]
        buy_hold_returns = (initial_weights * stock_returns_common).sum(axis=1)
        buy_hold_total = buy_hold_returns.sum()
        
        # Calculate rebalanced return
        rebalanced_returns = (weights_common * stock_returns_common).sum(axis=1)
        rebalanced_total = rebalanced_returns.sum()
        
        # Timing effect = rebalanced - buy-and-hold
        timing_effect = rebalanced_total - buy_hold_total
        
        return float(timing_effect)
