"""
Test Data Completeness Validation
==================================
Test cases for data completeness checking.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.data_completeness import (
    DataCompletenessChecker,
    DataRequirement,
    AnalysisRequirement
)


class TestDataCompletenessChecker:
    """Test data completeness checker."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.checker = DataCompletenessChecker()
        
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
            'sector_mapping': {'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology'},
            'start_date': dates[0],
            'end_date': dates[-1]
        }
        
        # Create sample stock data
        self.stock_data = {
            'features': pd.DataFrame({
                'ticker': ['AAPL', 'MSFT', 'GOOGL'] * 100,
                'date': dates.repeat(3),
                'score': np.random.uniform(0, 100, 300),
                'beta': np.random.uniform(0.8, 1.2, 300),
                'pe_ratio': np.random.uniform(15, 30, 300),
                'roe': np.random.uniform(0.1, 0.2, 300)
            }),
            'returns': pd.DataFrame({
                'AAPL': np.random.normal(0.001, 0.02, 100),
                'MSFT': np.random.normal(0.001, 0.02, 100),
                'GOOGL': np.random.normal(0.001, 0.02, 100)
            }, index=dates)
        }
    
    def test_check_portfolio_returns(self):
        """Test portfolio returns requirement check."""
        result = self.checker._check_requirement(
            DataRequirement.PORTFOLIO_RETURNS,
            self.portfolio_data,
            {},
            None
        )
        assert result is True
        
        # Test missing returns
        portfolio_no_returns = {**self.portfolio_data}
        del portfolio_no_returns['returns']
        result = self.checker._check_requirement(
            DataRequirement.PORTFOLIO_RETURNS,
            portfolio_no_returns,
            {},
            None
        )
        assert result is False
    
    def test_check_portfolio_weights(self):
        """Test portfolio weights requirement check."""
        result = self.checker._check_requirement(
            DataRequirement.PORTFOLIO_WEIGHTS,
            self.portfolio_data,
            {},
            None
        )
        assert result is True
        
        # Test missing weights
        portfolio_no_weights = {**self.portfolio_data}
        del portfolio_no_weights['weights']
        result = self.checker._check_requirement(
            DataRequirement.PORTFOLIO_WEIGHTS,
            portfolio_no_weights,
            {},
            None
        )
        assert result is False
    
    def test_check_stock_returns(self):
        """Test stock returns requirement check."""
        # Test with returns in stock_data
        result = self.checker._check_requirement(
            DataRequirement.STOCK_RETURNS,
            self.portfolio_data,
            self.stock_data,
            None
        )
        assert result is True
        
        # Test with returns in portfolio_data (redundant source)
        portfolio_with_returns = {**self.portfolio_data}
        portfolio_with_returns['stock_returns'] = self.stock_data['returns']
        result = self.checker._check_requirement(
            DataRequirement.STOCK_RETURNS,
            portfolio_with_returns,
            {},
            None
        )
        assert result is True
        
        # Test missing returns
        stock_no_returns = {'features': self.stock_data['features']}
        result = self.checker._check_requirement(
            DataRequirement.STOCK_RETURNS,
            self.portfolio_data,
            stock_no_returns,
            None
        )
        assert result is False
    
    def test_check_stock_features(self):
        """Test stock features requirement check."""
        # Test with DataFrame
        result = self.checker._check_requirement(
            DataRequirement.STOCK_FEATURES,
            self.portfolio_data,
            self.stock_data['features'],
            None
        )
        assert result is True
        
        # Test with dict containing features
        result = self.checker._check_requirement(
            DataRequirement.STOCK_FEATURES,
            self.portfolio_data,
            self.stock_data,
            None
        )
        assert result is True
        
        # Test missing features
        result = self.checker._check_requirement(
            DataRequirement.STOCK_FEATURES,
            self.portfolio_data,
            {},
            None
        )
        assert result is False
    
    def test_check_fundamental_data(self):
        """Test fundamental data requirement check."""
        # Test with fundamental data
        stock_with_fundamentals = {
            'data': pd.DataFrame({
                'ticker': ['AAPL', 'MSFT', 'GOOGL'],
                'pe_ratio': [25.0, 30.0, 20.0],
                'pb_ratio': [5.0, 6.0, 4.0],
                'roe': [0.15, 0.18, 0.12]
            })
        }
        result = self.checker._check_requirement(
            DataRequirement.FUNDAMENTAL_DATA,
            self.portfolio_data,
            stock_with_fundamentals,
            None
        )
        assert result is True or result == True
        
        # Test with zero PE (missing data)
        stock_zero_pe = {
            'data': pd.DataFrame({
                'ticker': ['AAPL', 'MSFT', 'GOOGL'],
                'pe_ratio': [0.0, 0.0, 0.0]
            })
        }
        result = self.checker._check_requirement(
            DataRequirement.FUNDAMENTAL_DATA,
            self.portfolio_data,
            stock_zero_pe,
            None
        )
        assert result is False
        
        # Test missing fundamental data
        result = self.checker._check_requirement(
            DataRequirement.FUNDAMENTAL_DATA,
            self.portfolio_data,
            {'features': pd.DataFrame({'ticker': ['AAPL'], 'score': [50]})},
            None
        )
        assert result is False
    
    def test_check_sector_mapping(self):
        """Test sector mapping requirement check."""
        result = self.checker._check_requirement(
            DataRequirement.SECTOR_MAPPING,
            self.portfolio_data,
            {},
            None
        )
        assert result is True
        
        # Test missing sector mapping
        portfolio_no_sector = {**self.portfolio_data}
        del portfolio_no_sector['sector_mapping']
        result = self.checker._check_requirement(
            DataRequirement.SECTOR_MAPPING,
            portfolio_no_sector,
            {},
            None
        )
        assert result is False
    
    def test_check_benchmark_data(self):
        """Test benchmark data requirement check."""
        # Test with benchmark data
        benchmark_data = {
            'SPY': {
                'returns': pd.Series(
                    np.random.normal(0.001, 0.02, 100),
                    index=self.portfolio_data['returns'].index
                )
            }
        }
        result = self.checker._check_requirement(
            DataRequirement.BENCHMARK_DATA,
            self.portfolio_data,
            {},
            benchmark_data
        )
        assert result is True
        
        # Test missing benchmark data
        result = self.checker._check_requirement(
            DataRequirement.BENCHMARK_DATA,
            self.portfolio_data,
            {},
            None
        )
        assert result is False
        
        # Test no overlapping dates
        benchmark_no_overlap = {
            'SPY': {
                'returns': pd.Series(
                    np.random.normal(0.001, 0.02, 50),
                    index=pd.date_range('2025-01-01', periods=50, freq='D')
                )
            }
        }
        result = self.checker._check_requirement(
            DataRequirement.BENCHMARK_DATA,
            self.portfolio_data,
            {},
            benchmark_no_overlap
        )
        assert result is False
    
    def test_check_analysis_requirements(self):
        """Test analysis requirements checking."""
        # Test attribution requirements
        status = self.checker._check_analysis_requirements(
            'attribution',
            AnalysisRequirement.ATTRIBUTION.value,
            self.portfolio_data,
            self.stock_data,
            None
        )
        assert status['can_run'] is True
        assert len(status['missing']) == 0
        
        # Test with missing stock returns
        stock_no_returns = {'features': self.stock_data['features']}
        status = self.checker._check_analysis_requirements(
            'attribution',
            AnalysisRequirement.ATTRIBUTION.value,
            self.portfolio_data,
            stock_no_returns,
            None
        )
        assert status['can_run'] is False
        assert 'stock_returns' in status['missing']
        assert status['severity'] == 'error'
    
    def test_check_data_completeness(self):
        """Test full data completeness check."""
        completeness = self.checker.check_data_completeness(
            self.portfolio_data,
            self.stock_data,
            None
        )
        
        assert 'is_complete' in completeness
        assert 'analysis_status' in completeness
        assert 'errors' in completeness
        assert 'warnings' in completeness
        
        # Check attribution status
        attr_status = completeness['analysis_status'].get('attribution', {})
        assert attr_status.get('can_run', False) is True
    
    def test_get_fix_instructions(self):
        """Test fix instructions generation."""
        missing = ['stock_returns', 'fundamental_data', 'benchmark_data']
        instructions = self.checker.get_fix_instructions(missing)
        
        assert len(instructions) == 3
        assert any('stock returns' in inst.lower() for inst in instructions)
        assert any('fundamental' in inst.lower() for inst in instructions)
        assert any('benchmark' in inst.lower() for inst in instructions)
    
    def test_generate_report(self):
        """Test report generation."""
        completeness = self.checker.check_data_completeness(
            self.portfolio_data,
            self.stock_data,
            None
        )
        
        report = self.checker.generate_report(completeness)
        
        assert isinstance(report, str)
        assert 'DATA COMPLETENESS CHECK' in report
        assert 'Analysis Status' in report
        assert 'attribution' in report.lower() or 'Attribution' in report


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.checker = DataCompletenessChecker()
    
    def test_empty_portfolio_data(self):
        """Test with empty portfolio data."""
        completeness = self.checker.check_data_completeness(
            {},
            {},
            None
        )
        
        assert completeness['is_complete'] is False
        assert len(completeness['errors']) > 0
    
    def test_empty_stock_data(self):
        """Test with empty stock data."""
        portfolio_data = {
            'returns': pd.Series([0.01, 0.02], index=pd.date_range('2020-01-01', periods=2)),
            'weights': pd.DataFrame({'AAPL': [0.5, 0.5]}, index=pd.date_range('2020-01-01', periods=2))
        }
        
        completeness = self.checker.check_data_completeness(
            portfolio_data,
            {},
            None
        )
        
        assert completeness['is_complete'] is False
    
    def test_none_values(self):
        """Test with None values."""
        portfolio_data = {
            'returns': None,
            'weights': None
        }
        
        completeness = self.checker.check_data_completeness(
            portfolio_data,
            {},
            None
        )
        
        assert completeness['is_complete'] is False
    
    def test_empty_dataframes(self):
        """Test with empty DataFrames."""
        portfolio_data = {
            'returns': pd.Series(dtype=float),
            'weights': pd.DataFrame()
        }
        
        result = self.checker._check_requirement(
            DataRequirement.PORTFOLIO_RETURNS,
            portfolio_data,
            {},
            None
        )
        assert result is False
        
        result = self.checker._check_requirement(
            DataRequirement.PORTFOLIO_WEIGHTS,
            portfolio_data,
            {},
            None
        )
        assert result is False
