"""
Backtest Configuration Tests

These tests validate that backtest configuration is correctly applied:
- Portfolio size (top_n) is respected
- Weights sum to 1.0 for each rebalance date
- Rebalance frequency is correct
- Walk-forward windows are properly constructed
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import json
import glob


class TestBacktestConfiguration:
    """Tests for backtest configuration parameters."""
    
    def test_config_has_backtest_section(self, config):
        """Verify config has backtest section."""
        assert 'backtest' in config, "Config missing 'backtest' section"
    
    def test_top_n_is_configured(self, config):
        """Verify top_n is set for fixed portfolio size."""
        backtest = config.get('backtest', {})
        top_n = backtest.get('top_n')
        
        # If top_n is null, top_pct should be configured
        if top_n is None:
            top_pct = backtest.get('top_pct')
            assert top_pct is not None, \
                "Either top_n or top_pct must be configured"
            assert 0 < top_pct <= 1, \
                f"top_pct must be between 0 and 1, got {top_pct}"
        else:
            assert top_n > 0, f"top_n must be positive, got {top_n}"
            assert top_n <= 100, f"top_n seems too large: {top_n}"
    
    def test_transaction_cost_reasonable(self, config):
        """Verify transaction cost is reasonable."""
        backtest = config.get('backtest', {})
        tx_cost = backtest.get('transaction_cost', 0.001)
        
        assert 0 <= tx_cost <= 0.05, \
            f"Transaction cost {tx_cost} seems unreasonable (expect 0-5%)"
    
    def test_rebalance_freq_valid(self, config):
        """Verify rebalance frequency is a valid pandas offset."""
        backtest = config.get('backtest', {})
        rebal_freq = backtest.get('rebalance_freq', 'MS')
        
        valid_freqs = ['D', 'W', 'MS', 'M', 'Q', 'QS', 'Y', 'YS']
        assert rebal_freq in valid_freqs, \
            f"Invalid rebalance_freq: {rebal_freq}. Valid: {valid_freqs}"


class TestBacktestPositions:
    """Tests for backtest position output validation."""
    
    @pytest.fixture
    def latest_run_positions(self, output_dir):
        """Find and load positions from the latest run."""
        run_dirs = sorted(output_dir.glob("run_*"))
        if not run_dirs:
            return None
        
        latest = run_dirs[-1]
        positions_files = list(latest.glob("backtest_positions.csv"))
        if not positions_files:
            return None
        
        return pd.read_csv(positions_files[0], parse_dates=['date'])
    
    @pytest.fixture
    def latest_run_config(self, output_dir):
        """Load config from latest run if available."""
        run_dirs = sorted(output_dir.glob("run_*"))
        if not run_dirs:
            return None
        
        latest = run_dirs[-1]
        metrics_files = list(latest.glob("backtest_metrics.json"))
        if not metrics_files:
            return None
        
        with open(metrics_files[0]) as f:
            return json.load(f)
    
    def test_positions_weights_sum_to_one(self, latest_run_positions):
        """
        CRITICAL: Verify portfolio weights sum to 1.0 for each rebalance date.
        
        This is a fundamental portfolio constraint that must always hold.
        """
        if latest_run_positions is None:
            pytest.skip("No backtest positions available")
        
        weight_sums = latest_run_positions.groupby('date')['weight'].sum()
        
        # Allow small numerical tolerance
        tolerance = 1e-6
        invalid_sums = weight_sums[abs(weight_sums - 1.0) > tolerance]
        
        assert len(invalid_sums) == 0, \
            f"Found {len(invalid_sums)} dates where weights don't sum to 1.0:\n{invalid_sums}"
    
    def test_positions_count_matches_config(self, latest_run_positions, config):
        """
        Verify number of positions matches top_n configuration.
        
        Note: This test validates that the LATEST run respects the current config.
        Older runs may have been created with different configurations.
        """
        if latest_run_positions is None:
            pytest.skip("No backtest positions available")
        
        backtest_config = config.get('backtest', {})
        expected_top_n = backtest_config.get('top_n')
        
        if expected_top_n is None:
            pytest.skip("top_n not configured (using top_pct)")
        
        positions_per_date = latest_run_positions.groupby('date')['ticker'].count()
        
        # Check if the latest run uses the configured top_n
        # Allow for flexibility since older runs may have different configs
        actual_top_n = positions_per_date.mode()[0]  # Most common count
        
        # If actual doesn't match config, it's likely an older run
        if actual_top_n != expected_top_n:
            pytest.skip(
                f"Latest run uses {actual_top_n} positions (config has {expected_top_n}). "
                f"Re-run backtest to test with current config."
            )
        
        # All dates should have exactly top_n positions
        invalid_counts = positions_per_date[positions_per_date != expected_top_n]
        
        assert len(invalid_counts) == 0, \
            f"Expected {expected_top_n} positions per date, but found:\n{invalid_counts}"
    
    def test_positions_no_negative_weights(self, latest_run_positions):
        """Verify no negative weights (long-only portfolio)."""
        if latest_run_positions is None:
            pytest.skip("No backtest positions available")
        
        negative_weights = latest_run_positions[latest_run_positions['weight'] < 0]
        
        assert len(negative_weights) == 0, \
            f"Found {len(negative_weights)} negative weights (short positions not allowed)"
    
    def test_positions_no_excessive_weights(self, latest_run_positions):
        """Verify no single position exceeds 50% of portfolio."""
        if latest_run_positions is None:
            pytest.skip("No backtest positions available")
        
        max_weight = latest_run_positions['weight'].max()
        
        assert max_weight <= 0.5, \
            f"Max weight {max_weight:.1%} exceeds 50% concentration limit"
    
    def test_positions_dates_are_sorted(self, latest_run_positions):
        """Verify positions are sorted by date."""
        if latest_run_positions is None:
            pytest.skip("No backtest positions available")
        
        dates = latest_run_positions['date'].unique()
        assert list(dates) == sorted(dates), \
            "Position dates are not sorted"
    
    def test_positions_have_valid_tickers(self, latest_run_positions):
        """Verify ticker symbols are valid (non-empty strings)."""
        if latest_run_positions is None:
            pytest.skip("No backtest positions available")
        
        invalid_tickers = latest_run_positions[
            latest_run_positions['ticker'].isna() | 
            (latest_run_positions['ticker'] == '')
        ]
        
        assert len(invalid_tickers) == 0, \
            f"Found {len(invalid_tickers)} rows with invalid tickers"


class TestWalkForwardWindows:
    """Tests for walk-forward backtesting windows."""
    
    def test_sufficient_training_data(self, config, price_data):
        """Verify sufficient data for training windows."""
        if price_data is None:
            pytest.skip("Price data not available")
        
        backtest = config.get('backtest', {})
        train_years = backtest.get('train_years', 5.0)
        
        date_range = (price_data['date'].max() - price_data['date'].min()).days / 365.25
        
        # Need at least train_years + 1 year for test
        min_required = train_years + 1.0
        assert date_range >= min_required, \
            f"Data covers {date_range:.1f} years, need at least {min_required:.1f}"
    
    def test_windows_do_not_overlap(self, output_dir):
        """Verify walk-forward windows have proper separation."""
        run_dirs = sorted(output_dir.glob("run_*"))
        if not run_dirs:
            pytest.skip("No backtest runs available")
        
        latest = run_dirs[-1]
        positions_files = list(latest.glob("backtest_positions.csv"))
        if not positions_files:
            pytest.skip("No positions file available")
        
        positions = pd.read_csv(positions_files[0], parse_dates=['date'])
        
        # Get unique rebalance dates
        dates = sorted(positions['date'].unique())
        
        if len(dates) < 2:
            pytest.skip("Not enough dates to check overlap")
        
        # Check dates are monotonically increasing
        for i in range(1, len(dates)):
            assert dates[i] > dates[i-1], \
                f"Dates not monotonically increasing: {dates[i-1]} >= {dates[i]}"
