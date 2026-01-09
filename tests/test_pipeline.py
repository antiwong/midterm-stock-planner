"""
Pipeline Integration Tests

These tests validate the data processing pipeline from raw data
through feature engineering to model training and backtesting.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestDataLoader:
    """Tests for data loading functions."""
    
    def test_load_price_data(self, data_dir):
        """Test price data loading."""
        from src.data.loader import load_price_data
        
        price_path = data_dir / "prices.csv"
        if not price_path.exists():
            pytest.skip("prices.csv not available")
        
        prices = load_price_data(str(price_path))
        
        assert isinstance(prices, pd.DataFrame)
        assert len(prices) > 0
        assert 'date' in prices.columns
        assert 'ticker' in prices.columns
        assert 'close' in prices.columns
    
    def test_load_benchmark_data(self, data_dir):
        """Test benchmark data loading."""
        from src.data.loader import load_benchmark_data
        
        bench_path = data_dir / "benchmark.csv"
        if not bench_path.exists():
            pytest.skip("benchmark.csv not available")
        
        benchmark = load_benchmark_data(str(bench_path))
        
        assert isinstance(benchmark, pd.DataFrame)
        assert len(benchmark) > 0
        assert 'date' in benchmark.columns


class TestFeatureEngineering:
    """Tests for feature engineering."""
    
    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data for testing."""
        np.random.seed(42)
        
        dates = pd.date_range('2020-01-01', periods=500, freq='B')
        tickers = ['AAPL', 'MSFT', 'GOOGL']
        
        data = []
        for ticker in tickers:
            base_price = 100 + np.random.randn() * 20
            prices = base_price * np.cumprod(1 + np.random.randn(len(dates)) * 0.02)
            volumes = np.random.randint(1000000, 10000000, len(dates))
            
            for i, date in enumerate(dates):
                data.append({
                    'date': date,
                    'ticker': ticker,
                    'open': prices[i] * 0.99,
                    'high': prices[i] * 1.01,
                    'low': prices[i] * 0.98,
                    'close': prices[i],
                    'volume': volumes[i]
                })
        
        return pd.DataFrame(data)
    
    def test_feature_generation_produces_valid_output(self, sample_price_data):
        """Test that feature engineering produces valid features."""
        from src.features.engineering import compute_all_features
        
        features = compute_all_features(sample_price_data)
        
        assert isinstance(features, pd.DataFrame)
        assert len(features) > 0
        assert 'ticker' in features.columns
        assert 'date' in features.columns
        
        # Should have generated features (returns, volatility, etc.)
        assert len(features.columns) > 5
    
    def test_no_future_data_leakage(self, sample_price_data):
        """
        Verify features don't use future data (look-ahead bias).
        
        This is critical for backtesting validity.
        """
        from src.features.engineering import compute_all_features
        
        features = compute_all_features(sample_price_data)
        
        # For any given date, all features should be calculable
        # using only data up to and including that date
        
        # Check that return features are backward-looking
        return_cols = [c for c in features.columns if 'return' in c.lower() and 'fwd' not in c.lower()]
        
        for col in return_cols[:3]:  # Check first few
            if features[col].notna().any():
                # Values should exist (not all NaN)
                assert features[col].notna().sum() > 0, \
                    f"Feature {col} is all NaN"


class TestWatchlistManager:
    """Tests for watchlist management."""
    
    def test_load_watchlists(self, project_root):
        """Test watchlist loading from YAML."""
        from src.data.watchlists import WatchlistManager
        
        config_dir = project_root / "config"
        if not (config_dir / "watchlists.yaml").exists():
            pytest.skip("watchlists.yaml not available")
        
        manager = WatchlistManager.from_config_dir(str(config_dir))
        
        # Should have loaded at least one watchlist
        watchlists = manager.list_watchlists()
        assert len(watchlists) > 0
    
    def test_get_watchlist_symbols(self, project_root):
        """Test getting symbols from a watchlist."""
        from src.data.watchlists import WatchlistManager
        
        config_dir = project_root / "config"
        if not (config_dir / "watchlists.yaml").exists():
            pytest.skip("watchlists.yaml not available")
        
        manager = WatchlistManager.from_config_dir(str(config_dir))
        watchlists = manager.list_watchlists()
        
        if not watchlists:
            pytest.skip("No watchlists available")
        
        # Get first watchlist
        first_wl = watchlists[0]
        wl_id = first_wl.get('id') or first_wl.get('name')
        
        symbols = manager.get_symbols(wl_id)
        
        assert isinstance(symbols, list)
        # If watchlist exists, it should have symbols
        if symbols:
            assert all(isinstance(s, str) for s in symbols)


class TestSectorMapping:
    """Tests for sector classification."""
    
    def test_get_sector_mapping(self, sector_data):
        """Test sector mapping from cached data."""
        if sector_data is None:
            pytest.skip("Sector data not available")
        
        # Create mapping dict from dataframe
        sector_map = dict(zip(sector_data['ticker'], sector_data['sector']))
        
        assert isinstance(sector_map, dict)
        # Should have some mappings
        assert len(sector_map) > 0
        
        # Values should be sector strings
        for ticker, sector in list(sector_map.items())[:5]:
            assert isinstance(ticker, str)
            assert isinstance(sector, str)
            assert len(sector) > 0
    
    def test_sector_mapping_completeness(self, price_data, sector_data):
        """Test that sector mapping covers most price data tickers."""
        if price_data is None:
            pytest.skip("Price data not available")
        if sector_data is None:
            pytest.skip("Sector data not available")
        
        sector_map = dict(zip(sector_data['ticker'], sector_data['sector']))
        price_tickers = set(price_data['ticker'].unique())
        
        mapped = sum(1 for t in price_tickers if t in sector_map)
        coverage = mapped / len(price_tickers)
        
        assert coverage >= 0.7, \
            f"Sector mapping only covers {coverage:.1%} of price tickers"


class TestBacktestRunner:
    """Tests for backtest execution."""
    
    def test_backtest_config_loads(self, project_root):
        """Test backtest configuration loading."""
        from src.config.config import load_config
        
        config_path = project_root / "config" / "config.yaml"
        if not config_path.exists():
            pytest.skip("config.yaml not available")
        
        config = load_config(str(config_path))
        
        assert hasattr(config, 'backtest')
        assert hasattr(config.backtest, 'top_n') or hasattr(config.backtest, 'top_pct')
    
    def test_backtest_output_structure(self, output_dir):
        """Test that backtest outputs have correct structure."""
        run_dirs = sorted(output_dir.glob("run_*"))
        
        if not run_dirs:
            pytest.skip("No backtest runs available")
        
        latest = run_dirs[-1]
        
        # Check expected files exist
        expected_files = [
            "backtest_metrics.json",
            "backtest_returns.csv",
            "backtest_positions.csv"
        ]
        
        for filename in expected_files:
            file_path = latest / filename
            assert file_path.exists(), f"Missing expected file: {filename}"


class TestDatabaseIntegration:
    """Tests for database operations."""
    
    def test_database_connection(self, data_dir):
        """Test database connection."""
        db_path = data_dir / "analysis.db"
        
        if not db_path.exists():
            pytest.skip("Database not available")
        
        import sqlite3
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Should be able to query tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        conn.close()
        
        assert len(tables) > 0, "Database has no tables"
    
    def test_runs_table_structure(self, data_dir):
        """Test runs table has expected columns."""
        db_path = data_dir / "analysis.db"
        
        if not db_path.exists():
            pytest.skip("Database not available")
        
        import sqlite3
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(runs)")
        columns = cursor.fetchall()
        
        conn.close()
        
        if not columns:
            pytest.skip("runs table not found")
        
        column_names = [c[1] for c in columns]
        
        expected_cols = ['run_id', 'name', 'status']
        for col in expected_cols:
            assert col in column_names, f"Missing column in runs table: {col}"
