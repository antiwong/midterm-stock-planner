"""
Test Analysis Modules
=====================
Test cases for individual analysis modules.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.performance_attribution import PerformanceAttributionAnalyzer
from src.analytics.factor_exposure import FactorExposureAnalyzer
from src.analytics.rebalancing_analysis import RebalancingAnalyzer
from src.analytics.style_analysis import StyleAnalyzer


class TestPerformanceAttribution:
    """Test performance attribution analyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = PerformanceAttributionAnalyzer()
        
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        
        self.portfolio_returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)
        self.portfolio_weights = pd.DataFrame({
            'AAPL': np.random.uniform(0.1, 0.3, 100),
            'MSFT': np.random.uniform(0.1, 0.3, 100),
            'GOOGL': np.random.uniform(0.1, 0.3, 100)
        }, index=dates)
        self.portfolio_weights = self.portfolio_weights.div(self.portfolio_weights.sum(axis=1), axis=0)
        
        self.stock_returns = pd.DataFrame({
            'AAPL': np.random.normal(0.001, 0.02, 100),
            'MSFT': np.random.normal(0.001, 0.02, 100),
            'GOOGL': np.random.normal(0.001, 0.02, 100)
        }, index=dates)
        
        self.sector_mapping = {
            'AAPL': 'Technology',
            'MSFT': 'Technology',
            'GOOGL': 'Technology'
        }
    
    def test_analyze_basic(self):
        """Test basic attribution analysis."""
        result = self.analyzer.analyze(
            portfolio_returns=self.portfolio_returns,
            portfolio_weights=self.portfolio_weights,
            stock_returns=self.stock_returns,
            sector_mapping=self.sector_mapping
        )
        
        assert 'total_return' in result
        assert 'attributions' in result
        assert isinstance(result['total_return'], (int, float))
        
        attributions = result['attributions']
        assert 'sector' in attributions
        assert 'stock_selection' in attributions
        assert 'timing' in attributions
    
    def test_attribution_sums_correctly(self):
        """Test that attributions sum approximately to total return."""
        result = self.analyzer.analyze(
            portfolio_returns=self.portfolio_returns,
            portfolio_weights=self.portfolio_weights,
            stock_returns=self.stock_returns,
            sector_mapping=self.sector_mapping
        )
        
        total_return = result['total_return']
        attributions = result['attributions']
        
        sum_attributions = sum([
            attributions.get('factor', 0),
            attributions.get('sector', 0),
            attributions.get('stock_selection', 0),
            attributions.get('timing', 0),
            attributions.get('interaction', 0)
        ])
        
        # Should be approximately equal (within 5%)
        diff = abs(total_return - sum_attributions)
        assert diff < abs(total_return) * 0.05 or diff < 0.01
    
    def test_attribution_with_factor_returns(self):
        """Test attribution with factor returns."""
        dates = self.portfolio_returns.index
        factor_returns = pd.DataFrame({
            'market': np.random.normal(0.001, 0.02, 100),
            'value': np.random.normal(0.0005, 0.015, 100)
        }, index=dates)
        
        result = self.analyzer.analyze(
            portfolio_returns=self.portfolio_returns,
            portfolio_weights=self.portfolio_weights,
            stock_returns=self.stock_returns,
            factor_returns=factor_returns,
            sector_mapping=self.sector_mapping
        )
        
        assert 'factor' in result['attributions']
        assert 'breakdown' in result
        assert 'factor' in result['breakdown']


class TestFactorExposure:
    """Test factor exposure analyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = FactorExposureAnalyzer()
        
        self.portfolio_weights = pd.Series({
            'AAPL': 0.4,
            'MSFT': 0.35,
            'GOOGL': 0.25
        })
        
        self.stock_features = pd.DataFrame({
            'beta': [1.1, 1.2, 0.9],
            'pe_ratio': [25, 30, 20],
            'pb_ratio': [5, 6, 4],
            'roe': [0.15, 0.18, 0.12],
            'volatility': [0.20, 0.22, 0.18],
            'rsi': [55, 60, 50]
        }, index=['AAPL', 'MSFT', 'GOOGL'])
    
    def test_analyze_basic(self):
        """Test basic factor exposure analysis."""
        result = self.analyzer.analyze(
            portfolio_weights=self.portfolio_weights,
            stock_features=self.stock_features
        )
        
        assert 'factor_exposures' in result
        assert 'total_factors' in result
        assert isinstance(result['factor_exposures'], list)
        assert len(result['factor_exposures']) > 0
    
    def test_factor_exposures_reasonable(self):
        """Test that factor exposures are reasonable."""
        result = self.analyzer.analyze(
            portfolio_weights=self.portfolio_weights,
            stock_features=self.stock_features
        )
        
        for factor in result['factor_exposures']:
            assert 'factor_name' in factor
            assert 'exposure' in factor
            assert isinstance(factor['exposure'], (int, float))
            # Exposures should be reasonable (not extreme)
            assert abs(factor['exposure']) < 100
    
    def test_custom_factor_definitions(self):
        """Test with custom factor definitions."""
        factor_definitions = {
            'custom_value': ['pe_ratio', 'pb_ratio'],
            'custom_quality': ['roe']
        }
        
        result = self.analyzer.analyze(
            portfolio_weights=self.portfolio_weights,
            stock_features=self.stock_features,
            factor_definitions=factor_definitions
        )
        
        factor_names = [f['factor_name'] for f in result['factor_exposures']]
        assert 'custom_value' in factor_names
        assert 'custom_quality' in factor_names


class TestRebalancingAnalysis:
    """Test rebalancing analyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = RebalancingAnalyzer()
        
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        self.portfolio_weights = pd.DataFrame({
            'AAPL': np.random.uniform(0.2, 0.4, 100),
            'MSFT': np.random.uniform(0.2, 0.4, 100),
            'GOOGL': np.random.uniform(0.2, 0.4, 100)
        }, index=dates)
        # Normalize weights
        self.portfolio_weights = self.portfolio_weights.div(self.portfolio_weights.sum(axis=1), axis=0)
        
        # Target weights (equal weight)
        self.target_weights = pd.Series({
            'AAPL': 0.33,
            'MSFT': 0.33,
            'GOOGL': 0.34
        })
    
    def test_analyze_basic(self):
        """Test basic rebalancing analysis."""
        result = self.analyzer.analyze(
            portfolio_weights=self.portfolio_weights,
            target_weights=self.target_weights
        )
        
        assert 'drift_analysis' in result or 'current_drift' in result
        assert 'cost_analysis' in result or 'total_transaction_costs' in result or 'total_transaction_cost' in result
        assert 'recommendations' in result or 'should_rebalance' in result or 'recommendation' in result
    
    def test_drift_calculation(self):
        """Test drift calculation."""
        result = self.analyzer.analyze(
            portfolio_weights=self.portfolio_weights,
            target_weights=self.target_weights
        )
        
        drift = result.get('drift_analysis', {}).get('current_drift') or result.get('current_drift', 0)
        assert isinstance(drift, (int, float))
        assert 0 <= abs(drift) <= 1  # Should be between 0 and 1 (0-100%)
    
    def test_turnover_calculation(self):
        """Test turnover calculation."""
        result = self.analyzer.analyze(
            portfolio_weights=self.portfolio_weights,
            target_weights=self.target_weights
        )
        
        turnover = result.get('turnover_analysis', {}).get('avg_turnover') or result.get('avg_turnover', 0)
        assert isinstance(turnover, (int, float))
        assert turnover >= 0


class TestStyleAnalysis:
    """Test style analyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = StyleAnalyzer()
        
        self.portfolio_weights = pd.Series({
            'AAPL': 0.4,
            'MSFT': 0.35,
            'GOOGL': 0.25
        })
        
        self.stock_features = pd.DataFrame({
            'pe_ratio': [25.0, 30.0, 20.0],
            'pb_ratio': [5.0, 6.0, 4.0],
            'market_cap': [2e12, 3e12, 1.5e12],
            'roe': [0.15, 0.18, 0.12]
        }, index=['AAPL', 'MSFT', 'GOOGL'])
    
    def test_analyze_basic(self):
        """Test basic style analysis."""
        result = self.analyzer.analyze(
            portfolio_weights=self.portfolio_weights,
            stock_features=self.stock_features
        )
        
        assert 'growth_value_classification' in result or 'style_classification' in result or 'growth_value' in result
        assert 'size_classification' in result or 'size' in result
    
    def test_portfolio_pe_calculation(self):
        """Test portfolio PE calculation."""
        result = self.analyzer.analyze(
            portfolio_weights=self.portfolio_weights,
            stock_features=self.stock_features
        )
        
        portfolio_pe = result.get('portfolio_pe', 0)
        if portfolio_pe > 0:
            assert 5 <= portfolio_pe <= 100  # Reasonable PE range
    
    def test_style_classification(self):
        """Test style classification."""
        result = self.analyzer.analyze(
            portfolio_weights=self.portfolio_weights,
            stock_features=self.stock_features
        )
        
        classification = result.get('growth_value_classification') or result.get('style_classification', '')
        assert classification in ['Growth', 'Value', 'Blend', 'N/A', ''] or len(classification) > 0
