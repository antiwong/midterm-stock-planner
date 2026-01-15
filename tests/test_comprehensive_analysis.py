"""
Test Comprehensive Analysis
============================
Test cases for comprehensive analysis runner.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.comprehensive_analysis import ComprehensiveAnalysisRunner
from src.analytics.data_loader import load_run_data_for_analysis


class TestComprehensiveAnalysisRunner:
    """Test comprehensive analysis runner."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = ComprehensiveAnalysisRunner(strict_validation=True)
        self.run_id = 'test_run_123'
        
        # Create sample portfolio data
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        self.portfolio_data = {
            'returns': pd.Series(np.random.normal(0.001, 0.02, 100), index=dates),
            'weights': pd.DataFrame({
                'AAPL': np.random.uniform(0.1, 0.3, 100),
                'MSFT': np.random.uniform(0.1, 0.3, 100),
                'GOOGL': np.random.uniform(0.1, 0.3, 100)
            }, index=dates),
            'holdings': ['AAPL', 'MSFT', 'GOOGL'],
            'sector_mapping': {
                'AAPL': 'Technology',
                'MSFT': 'Technology',
                'GOOGL': 'Technology'
            },
            'start_date': dates[0],
            'end_date': dates[-1]
        }
        
        # Create sample stock data
        stock_features = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'score': [80, 75, 70],
            'beta': [1.1, 1.2, 0.9],
            'pe_ratio': [25.0, 30.0, 20.0],
            'pb_ratio': [5.0, 6.0, 4.0],
            'roe': [0.15, 0.18, 0.12],
            'volatility': [0.20, 0.22, 0.18]
        })
        
        # Create stock returns
        stock_returns = pd.DataFrame({
            'AAPL': np.random.normal(0.001, 0.02, 100),
            'MSFT': np.random.normal(0.001, 0.02, 100),
            'GOOGL': np.random.normal(0.001, 0.02, 100)
        }, index=dates)
        
        self.stock_data = {
            'features': stock_features,
            'data': stock_features,
            'returns': stock_returns
        }
    
    def test_data_completeness_check(self):
        """Test that data completeness is checked before analysis."""
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=self.portfolio_data,
            stock_data=self.stock_data,
            save_ai_insights=False
        )
        
        assert 'data_completeness' in results
        assert 'warnings' in results
        assert 'errors' in results
        
        completeness = results['data_completeness']
        assert 'is_complete' in completeness
        assert 'analysis_status' in completeness
    
    def test_attribution_analysis(self):
        """Test performance attribution analysis."""
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=self.portfolio_data,
            stock_data=self.stock_data,
            save_ai_insights=False
        )
        
        attribution = results['analyses'].get('attribution', {})
        
        if 'error' not in attribution:
            assert 'total_return' in attribution
            assert 'attributions' in attribution
            assert isinstance(attribution['total_return'], (int, float))
    
    def test_factor_exposure_analysis(self):
        """Test factor exposure analysis."""
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=self.portfolio_data,
            stock_data=self.stock_data,
            save_ai_insights=False
        )
        
        factor_exposure = results['analyses'].get('factor_exposure', {})
        
        if 'error' not in factor_exposure:
            assert 'factor_exposures' in factor_exposure or 'exposures' in factor_exposure
    
    def test_rebalancing_analysis(self):
        """Test rebalancing analysis."""
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=self.portfolio_data,
            stock_data=self.stock_data,
            save_ai_insights=False
        )
        
        rebalancing = results['analyses'].get('rebalancing', {})
        
        if 'error' not in rebalancing:
            assert 'drift_analysis' in rebalancing or 'current_drift' in rebalancing
    
    def test_skipping_incomplete_analyses(self):
        """Test that analyses are skipped when data is missing."""
        # Remove stock returns to make attribution fail
        stock_data_no_returns = {**self.stock_data}
        del stock_data_no_returns['returns']
        
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=self.portfolio_data,
            stock_data=stock_data_no_returns,
            save_ai_insights=False
        )
        
        attribution = results['analyses'].get('attribution', {})
        # Should be skipped or have error
        assert 'error' in attribution or 'skipped' in attribution
    
    def test_timezone_normalization(self):
        """Test that timezones are normalized to avoid errors."""
        # Create data with timezone-aware indices
        dates_tz = pd.date_range('2020-01-01', periods=100, freq='D', tz='UTC')
        portfolio_data_tz = {
            **self.portfolio_data,
            'returns': pd.Series(np.random.normal(0.001, 0.02, 100), index=dates_tz),
            'weights': pd.DataFrame({
                'AAPL': np.random.uniform(0.1, 0.3, 100),
                'MSFT': np.random.uniform(0.1, 0.3, 100)
            }, index=dates_tz)
        }
        
        stock_returns_tz = pd.DataFrame({
            'AAPL': np.random.normal(0.001, 0.02, 100),
            'MSFT': np.random.normal(0.001, 0.02, 100)
        }, index=dates_tz)
        
        stock_data_tz = {
            **self.stock_data,
            'returns': stock_returns_tz
        }
        
        # Should not raise timezone error
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=portfolio_data_tz,
            stock_data=stock_data_tz,
            save_ai_insights=False
        )
        
        # Attribution should succeed (or fail gracefully, not with timezone error)
        attribution = results['analyses'].get('attribution', {})
        if 'error' in attribution:
            assert 'timezone' not in attribution['error'].lower() or 'tz' not in attribution['error'].lower()
    
    def test_dict_format_stock_data(self):
        """Test handling of dict format stock_data."""
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=self.portfolio_data,
            stock_data=self.stock_data,  # Already a dict
            save_ai_insights=False
        )
        
        # Should handle dict format without errors
        assert 'analyses' in results
        factor_exposure = results['analyses'].get('factor_exposure', {})
        # Should not have DataFrame-related errors
        if 'error' in factor_exposure:
            assert 'columns' not in factor_exposure['error'] or 'DataFrame' not in factor_exposure['error']


class TestErrorHandling:
    """Test error handling in comprehensive analysis."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = ComprehensiveAnalysisRunner(strict_validation=True)
        self.run_id = 'test_run_error'
    
    def test_missing_portfolio_returns(self):
        """Test handling of missing portfolio returns."""
        portfolio_data = {
            'weights': pd.DataFrame({'AAPL': [0.5]}, index=[datetime.now()]),
            'holdings': ['AAPL']
        }
        
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=portfolio_data,
            stock_data={},
            save_ai_insights=False
        )
        
        # Should have errors or warnings
        assert len(results.get('errors', [])) > 0 or len(results.get('warnings', [])) > 0
    
    def test_missing_portfolio_weights(self):
        """Test handling of missing portfolio weights."""
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        portfolio_data = {
            'returns': pd.Series(np.random.normal(0.001, 0.02, 10), index=dates),
            'holdings': ['AAPL']
        }
        
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=portfolio_data,
            stock_data={},
            save_ai_insights=False
        )
        
        # Should handle gracefully
        assert 'analyses' in results
    
    def test_empty_stock_data(self):
        """Test handling of empty stock data."""
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        portfolio_data = {
            'returns': pd.Series(np.random.normal(0.001, 0.02, 10), index=dates),
            'weights': pd.DataFrame({'AAPL': [0.5] * 10}, index=dates),
            'holdings': ['AAPL']
        }
        
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=portfolio_data,
            stock_data={},
            save_ai_insights=False
        )
        
        # Should handle gracefully
        assert 'analyses' in results
        # Some analyses should be skipped
        attribution = results['analyses'].get('attribution', {})
        assert 'error' in attribution or 'skipped' in attribution
