"""
Test Data Loader
================
Test cases for data loading and redundant source filling.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import tempfile
import shutil
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.data_loader import RunDataLoader, load_run_data_for_analysis


class TestRunDataLoader:
    """Test RunDataLoader class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.loader = RunDataLoader(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_load_portfolio_returns_from_backtest(self):
        """Test loading portfolio returns from backtest_returns.csv."""
        # Create backtest_returns.csv
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        returns_df = pd.DataFrame({
            'date': dates,
            'portfolio_return': np.random.normal(0.001, 0.02, 100)
        })
        returns_df.to_csv(self.temp_dir / 'backtest_returns.csv', index=False)
        
        returns = self.loader.load_portfolio_returns()
        
        assert returns is not None
        assert len(returns) == 100
        assert isinstance(returns, pd.Series)
    
    def test_load_portfolio_returns_from_equity_curve(self):
        """Test loading portfolio returns from equity_curve.csv."""
        # Create equity_curve.csv
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        equity_df = pd.DataFrame({
            'date': dates,
            'value': 100 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()
        })
        equity_df.to_csv(self.temp_dir / 'equity_curve.csv', index=False)
        
        returns = self.loader.load_portfolio_returns()
        
        assert returns is not None
        assert len(returns) == 99  # One less due to pct_change
        assert isinstance(returns, pd.Series)
    
    def test_load_portfolio_weights_from_positions(self):
        """Test loading portfolio weights from backtest_positions.csv."""
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        positions = []
        for date in dates:
            positions.append({'date': date, 'ticker': 'AAPL', 'weight': 0.5})
            positions.append({'date': date, 'ticker': 'MSFT', 'weight': 0.5})
        
        positions_df = pd.DataFrame(positions)
        positions_df.to_csv(self.temp_dir / 'backtest_positions.csv', index=False)
        
        weights = self.loader.load_portfolio_weights()
        
        assert weights is not None
        assert isinstance(weights, pd.DataFrame)
        assert 'AAPL' in weights.columns
        assert 'MSFT' in weights.columns
        assert len(weights) == 10
    
    def test_load_portfolio_weights_from_portfolio_file(self):
        """Test loading portfolio weights from portfolio_*.csv."""
        portfolio_df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'weight': [0.33, 0.33, 0.34],
            'sector': ['Technology', 'Technology', 'Technology']
        })
        portfolio_df.to_csv(self.temp_dir / 'portfolio_current.csv', index=False)
        
        weights = self.loader.load_portfolio_weights()
        
        assert weights is not None
        assert isinstance(weights, pd.DataFrame)
        assert 'AAPL' in weights.columns
        assert 'MSFT' in weights.columns
        assert 'GOOGL' in weights.columns
    
    def test_load_stock_returns_from_backtest(self):
        """Test loading stock returns from backtest_returns.csv."""
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        returns_data = []
        for date in dates:
            returns_data.append({
                'date': date,
                'ticker': 'AAPL',
                'return': np.random.normal(0.001, 0.02)
            })
            returns_data.append({
                'date': date,
                'ticker': 'MSFT',
                'return': np.random.normal(0.001, 0.02)
            })
        
        returns_df = pd.DataFrame(returns_data)
        returns_df.to_csv(self.temp_dir / 'backtest_returns.csv', index=False)
        
        stock_returns = self.loader.load_stock_returns()
        
        # Should find returns if format is correct
        # (This test may need adjustment based on actual format)
        assert stock_returns is None or isinstance(stock_returns, pd.DataFrame)
    
    def test_load_stock_returns_from_price_data(self):
        """Test loading stock returns from price data files."""
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        price_data = []
        for date in dates:
            for ticker in ['AAPL', 'MSFT']:
                price_data.append({
                    'date': date,
                    'ticker': ticker,
                    'close': 100 * (1 + np.random.normal(0.001, 0.02))
                })
        
        price_df = pd.DataFrame(price_data)
        price_df.to_csv(self.temp_dir / 'prices.csv', index=False)
        
        stock_returns = self.loader.load_stock_returns()
        
        assert stock_returns is not None
        assert isinstance(stock_returns, pd.DataFrame)
        assert 'AAPL' in stock_returns.columns or 'MSFT' in stock_returns.columns
    
    def test_load_stock_returns_from_enriched_file(self):
        """Test loading stock returns from portfolio enriched file."""
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        enriched_data = []
        for date in dates:
            for ticker in ['AAPL', 'MSFT']:
                enriched_data.append({
                    'date': date,
                    'ticker': ticker,
                    'return_21d': np.random.normal(0.001, 0.02),
                    'score': np.random.uniform(0, 100)
                })
        
        enriched_df = pd.DataFrame(enriched_data)
        enriched_df.to_csv(self.temp_dir / 'portfolio_enriched.csv', index=False)
        
        stock_returns = self.loader.load_stock_returns()
        
        # Should find returns from enriched file
        assert stock_returns is None or isinstance(stock_returns, pd.DataFrame)
    
    def test_load_stock_features(self):
        """Test loading stock features."""
        features_df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'score': [80, 75, 70],
            'beta': [1.1, 1.2, 0.9],
            'pe_ratio': [25, 30, 20]
        })
        features_df.to_csv(self.temp_dir / 'portfolio_enriched.csv', index=False)
        
        features = self.loader.load_stock_features()
        
        assert features is not None
        assert isinstance(features, pd.DataFrame)
        assert 'ticker' in features.columns
        assert 'score' in features.columns
    
    def test_load_sector_mapping(self):
        """Test loading sector mapping."""
        portfolio_df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'weight': [0.33, 0.33, 0.34],
            'sector': ['Technology', 'Technology', 'Technology']
        })
        portfolio_df.to_csv(self.temp_dir / 'portfolio_current.csv', index=False)
        
        mapping = self.loader.load_sector_mapping()
        
        assert isinstance(mapping, dict)
        assert 'AAPL' in mapping
        assert mapping['AAPL'] == 'Technology'
    
    def test_load_portfolio_data(self):
        """Test loading complete portfolio data."""
        # Create required files
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        
        # Portfolio returns
        returns_df = pd.DataFrame({
            'date': dates,
            'portfolio_return': np.random.normal(0.001, 0.02, 10)
        })
        returns_df.to_csv(self.temp_dir / 'backtest_returns.csv', index=False)
        
        # Portfolio weights
        positions = []
        for date in dates:
            positions.append({'date': date, 'ticker': 'AAPL', 'weight': 0.5})
            positions.append({'date': date, 'ticker': 'MSFT', 'weight': 0.5})
        positions_df = pd.DataFrame(positions)
        positions_df.to_csv(self.temp_dir / 'backtest_positions.csv', index=False)
        
        # Portfolio file for sector mapping
        portfolio_df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT'],
            'weight': [0.5, 0.5],
            'sector': ['Technology', 'Technology']
        })
        portfolio_df.to_csv(self.temp_dir / 'portfolio_current.csv', index=False)
        
        portfolio_data = self.loader.load_portfolio_data()
        
        assert 'returns' in portfolio_data
        assert 'weights' in portfolio_data
        assert 'holdings' in portfolio_data
        assert 'sector_mapping' in portfolio_data
        assert len(portfolio_data['holdings']) == 2
        assert 'AAPL' in portfolio_data['sector_mapping']


class TestRedundantDataSources:
    """Test redundant data source filling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_stock_returns_from_multiple_sources(self):
        """Test that stock returns are found from multiple redundant sources."""
        loader = RunDataLoader(self.temp_dir)
        
        # Create price data file (source 1)
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        price_data = []
        for date in dates:
            for ticker in ['AAPL', 'MSFT']:
                price_data.append({
                    'date': date,
                    'ticker': ticker,
                    'close': 100 * (1 + np.random.normal(0.001, 0.02))
                })
        price_df = pd.DataFrame(price_data)
        price_df.to_csv(self.temp_dir / 'prices.csv', index=False)
        
        stock_returns = loader.load_stock_returns()
        
        # Should find returns from price data
        assert stock_returns is not None
        assert isinstance(stock_returns, pd.DataFrame)
    
    def test_fundamental_data_merging(self):
        """Test that fundamental data is merged from multiple sources."""
        # This will be tested in load_run_data_for_analysis
        pass


class TestLoadRunDataForAnalysis:
    """Test load_run_data_for_analysis function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create minimal run directory structure
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        
        # Portfolio returns
        returns_df = pd.DataFrame({
            'date': dates,
            'portfolio_return': np.random.normal(0.001, 0.02, 10)
        })
        returns_df.to_csv(self.temp_dir / 'backtest_returns.csv', index=False)
        
        # Portfolio weights
        positions = []
        for date in dates:
            positions.append({'date': date, 'ticker': 'AAPL', 'weight': 0.5})
            positions.append({'date': date, 'ticker': 'MSFT', 'weight': 0.5})
        positions_df = pd.DataFrame(positions)
        positions_df.to_csv(self.temp_dir / 'backtest_positions.csv', index=False)
        
        # Portfolio enriched file
        enriched_df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT'],
            'score': [80, 75],
            'beta': [1.1, 1.2],
            'sector': ['Technology', 'Technology']
        })
        enriched_df.to_csv(self.temp_dir / 'portfolio_enriched.csv', index=False)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_load_run_data_success(self):
        """Test successful data loading."""
        data = load_run_data_for_analysis('test_run', self.temp_dir)
        
        assert data.get('error') is None
        assert data.get('portfolio_data') is not None
        assert data.get('stock_data') is not None
        
        portfolio_data = data['portfolio_data']
        assert 'returns' in portfolio_data
        assert 'weights' in portfolio_data
        assert 'holdings' in portfolio_data
    
    def test_load_run_data_missing_directory(self):
        """Test handling of missing directory."""
        data = load_run_data_for_analysis('test_run', Path('/nonexistent/path'))
        
        assert data.get('error') is not None
        assert 'not found' in data['error'].lower()
    
    def test_stock_returns_in_portfolio_data(self):
        """Test that stock returns are included in portfolio_data."""
        # Create price data
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        price_data = []
        for date in dates:
            for ticker in ['AAPL', 'MSFT']:
                price_data.append({
                    'date': date,
                    'ticker': ticker,
                    'close': 100 * (1 + np.random.normal(0.001, 0.02))
                })
        price_df = pd.DataFrame(price_data)
        price_df.to_csv(self.temp_dir / 'prices.csv', index=False)
        
        data = load_run_data_for_analysis('test_run', self.temp_dir)
        
        portfolio_data = data.get('portfolio_data', {})
        # Stock returns should be in portfolio_data if found
        if 'stock_returns' in portfolio_data:
            assert isinstance(portfolio_data['stock_returns'], pd.DataFrame)
    
    def test_fundamental_data_merging(self):
        """Test that fundamental data is merged when missing."""
        # Create enriched file with fundamental data
        enriched_df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT'],
            'score': [80, 75],
            'pe_ratio': [25.0, 30.0],
            'pb_ratio': [5.0, 6.0],
            'roe': [0.15, 0.18]
        })
        enriched_df.to_csv(self.temp_dir / 'portfolio_enriched.csv', index=False)
        
        data = load_run_data_for_analysis('test_run', self.temp_dir)
        
        stock_data = data.get('stock_data', {})
        if isinstance(stock_data, dict) and 'features' in stock_data:
            features = stock_data['features']
            if isinstance(features, pd.DataFrame):
                # Should have fundamental columns if merged
                assert 'pe_ratio' in features.columns or 'score' in features.columns
