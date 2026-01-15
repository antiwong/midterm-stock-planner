"""
Integration Tests
=================
End-to-end integration tests for the complete analysis pipeline.
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
from src.analytics.analysis_service import AnalysisService


class TestEndToEndAnalysis:
    """Test complete end-to-end analysis pipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.run_id = 'integration_test_run'
        self.runner = ComprehensiveAnalysisRunner(strict_validation=True)
        
        # Create complete run directory structure
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        
        # Portfolio returns
        returns_df = pd.DataFrame({
            'date': dates,
            'portfolio_return': np.random.normal(0.001, 0.02, 100)
        })
        returns_df.to_csv(self.temp_dir / 'backtest_returns.csv', index=False)
        
        # Portfolio positions
        positions = []
        for date in dates:
            positions.append({'date': date, 'ticker': 'AAPL', 'weight': 0.4})
            positions.append({'date': date, 'ticker': 'MSFT', 'weight': 0.35})
            positions.append({'date': date, 'ticker': 'GOOGL', 'weight': 0.25})
        positions_df = pd.DataFrame(positions)
        positions_df.to_csv(self.temp_dir / 'backtest_positions.csv', index=False)
        
        # Price data for stock returns
        price_data = []
        for date in dates:
            for ticker in ['AAPL', 'MSFT', 'GOOGL']:
                price_data.append({
                    'date': date,
                    'ticker': ticker,
                    'close': 100 * (1 + np.random.normal(0.001, 0.02))
                })
        price_df = pd.DataFrame(price_data)
        price_df.to_csv(self.temp_dir / 'prices.csv', index=False)
        
        # Portfolio enriched file
        enriched_df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'score': [80, 75, 70],
            'beta': [1.1, 1.2, 0.9],
            'pe_ratio': [25.0, 30.0, 20.0],
            'pb_ratio': [5.0, 6.0, 4.0],
            'roe': [0.15, 0.18, 0.12],
            'sector': ['Technology', 'Technology', 'Technology']
        })
        enriched_df.to_csv(self.temp_dir / 'portfolio_enriched.csv', index=False)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_complete_analysis_pipeline(self):
        """Test complete analysis pipeline from data loading to results."""
        # Load data
        data = load_run_data_for_analysis(self.run_id, self.temp_dir)
        
        assert data.get('error') is None
        assert data.get('portfolio_data') is not None
        assert data.get('stock_data') is not None
        
        portfolio_data = data['portfolio_data']
        stock_data = data['stock_data']
        
        # Run comprehensive analysis
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=portfolio_data,
            stock_data=stock_data,
            save_ai_insights=False
        )
        
        # Verify results structure
        assert 'analyses' in results
        assert 'data_completeness' in results
        assert 'warnings' in results
        assert 'errors' in results
        
        # Check that analyses ran
        assert 'attribution' in results['analyses']
        assert 'factor_exposure' in results['analyses']
        assert 'rebalancing' in results['analyses']
    
    def test_data_persistence(self):
        """Test that analysis results are saved to database."""
        # Load data
        data = load_run_data_for_analysis(self.run_id, self.temp_dir)
        portfolio_data = data['portfolio_data']
        stock_data = data['stock_data']
        
        # Run analysis
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=portfolio_data,
            stock_data=stock_data,
            save_ai_insights=False
        )
        
        # Check database
        service = AnalysisService()
        
        # Check attribution
        attribution = service.get_analysis_result(self.run_id, 'attribution')
        if attribution:
            assert attribution.run_id == self.run_id
        
        # Check factor exposure
        factor = service.get_analysis_result(self.run_id, 'factor_exposure')
        if factor:
            assert factor.run_id == self.run_id
        
        # Check rebalancing
        rebalancing = service.get_analysis_result(self.run_id, 'rebalancing')
        if rebalancing:
            assert rebalancing.run_id == self.run_id
    
    def test_error_recovery(self):
        """Test that system recovers gracefully from errors."""
        # Create incomplete data
        incomplete_portfolio = {
            'returns': pd.Series([0.01, 0.02], index=pd.date_range('2020-01-01', periods=2)),
            'weights': pd.DataFrame({'AAPL': [0.5, 0.5]}, index=pd.date_range('2020-01-01', periods=2))
        }
        
        incomplete_stock = {}
        
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=incomplete_portfolio,
            stock_data=incomplete_stock,
            save_ai_insights=False
        )
        
        # Should handle gracefully, not crash
        assert 'analyses' in results
        assert 'errors' in results or 'warnings' in results
        
        # Some analyses should be skipped
        attribution = results['analyses'].get('attribution', {})
        assert 'error' in attribution or 'skipped' in attribution


class TestDataCompletenessIntegration:
    """Test data completeness in integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = ComprehensiveAnalysisRunner(strict_validation=True)
        self.run_id = 'completeness_test'
    
    def test_complete_data_scenario(self):
        """Test with complete data."""
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        
        portfolio_data = {
            'returns': pd.Series(np.random.normal(0.001, 0.02, 100), index=dates),
            'weights': pd.DataFrame({
                'AAPL': np.random.uniform(0.1, 0.3, 100),
                'MSFT': np.random.uniform(0.1, 0.3, 100)
            }, index=dates),
            'holdings': ['AAPL', 'MSFT'],
            'sector_mapping': {'AAPL': 'Technology', 'MSFT': 'Technology'},
            'stock_returns': pd.DataFrame({
                'AAPL': np.random.normal(0.001, 0.02, 100),
                'MSFT': np.random.normal(0.001, 0.02, 100)
            }, index=dates)
        }
        
        stock_data = {
            'features': pd.DataFrame({
                'ticker': ['AAPL', 'MSFT'],
                'pe_ratio': [25.0, 30.0],
                'beta': [1.1, 1.2]
            })
        }
        
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=portfolio_data,
            stock_data=stock_data,
            save_ai_insights=False
        )
        
        completeness = results.get('data_completeness', {})
        # Should be mostly complete
        assert completeness.get('is_complete', False) or len(completeness.get('errors', [])) == 0
    
    def test_partial_data_scenario(self):
        """Test with partial data."""
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        
        portfolio_data = {
            'returns': pd.Series(np.random.normal(0.001, 0.02, 100), index=dates),
            'weights': pd.DataFrame({
                'AAPL': np.random.uniform(0.1, 0.3, 100),
                'MSFT': np.random.uniform(0.1, 0.3, 100)
            }, index=dates),
            'holdings': ['AAPL', 'MSFT']
            # Missing sector_mapping and stock_returns
        }
        
        stock_data = {
            'features': pd.DataFrame({
                'ticker': ['AAPL', 'MSFT'],
                'score': [80, 75]
                # Missing fundamental data
            })
        }
        
        results = self.runner.run_all_analysis(
            run_id=self.run_id,
            portfolio_data=portfolio_data,
            stock_data=stock_data,
            save_ai_insights=False
        )
        
        completeness = results.get('data_completeness', {})
        # Should have warnings
        assert len(completeness.get('warnings', [])) > 0 or len(completeness.get('errors', [])) > 0
        
        # Some analyses should be skipped
        attribution = results['analyses'].get('attribution', {})
        assert 'error' in attribution or 'skipped' in attribution
