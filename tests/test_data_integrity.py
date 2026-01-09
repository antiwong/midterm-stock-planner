"""
Data Integrity Tests

These tests validate the integrity of price data, benchmark data,
and sector classifications to ensure the backtest produces reliable results.

Tests cover:
- Price data format and ranges
- No corrupt/extreme daily returns
- Benchmark data alignment
- Sector mapping completeness
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path


class TestPriceDataIntegrity:
    """Tests for price data integrity and quality."""
    
    def test_price_data_exists(self, data_dir):
        """Verify price data file exists."""
        price_path = data_dir / "prices.csv"
        assert price_path.exists(), "prices.csv not found in data directory"
    
    def test_price_data_has_required_columns(self, price_data):
        """Verify price data has required columns."""
        if price_data is None:
            pytest.skip("Price data not available")
        
        required_cols = ['date', 'ticker', 'close']
        for col in required_cols:
            assert col in price_data.columns, f"Missing required column: {col}"
    
    def test_price_data_no_negative_prices(self, price_data):
        """Verify no negative prices exist."""
        if price_data is None:
            pytest.skip("Price data not available")
        
        negative_prices = price_data[price_data['close'] <= 0]
        assert len(negative_prices) == 0, \
            f"Found {len(negative_prices)} rows with non-positive prices"
    
    def test_price_data_date_range(self, price_data):
        """Verify price data covers expected date range."""
        if price_data is None:
            pytest.skip("Price data not available")
        
        min_date = price_data['date'].min()
        max_date = price_data['date'].max()
        
        # Should have at least 5 years of data for training
        date_range_years = (max_date - min_date).days / 365.25
        assert date_range_years >= 5, \
            f"Price data only covers {date_range_years:.1f} years (need >= 5)"
    
    def test_no_extreme_daily_returns(self, price_data):
        """
        Verify no unrealistic daily returns exist.
        
        Extreme returns (>100% in a day) typically indicate data corruption,
        stock splits not adjusted, or other data quality issues.
        """
        if price_data is None:
            pytest.skip("Price data not available")
        
        # Calculate daily returns per ticker
        price_data = price_data.sort_values(['ticker', 'date'])
        price_data['daily_return'] = price_data.groupby('ticker')['close'].pct_change()
        
        # Check for extreme returns (>100% or <-90% in a single day)
        extreme_returns = price_data[
            (price_data['daily_return'].abs() > 1.0) |  # >100% move
            (price_data['daily_return'] < -0.9)         # >90% drop
        ]
        
        # Allow a small number of extreme moves (legitimate for volatile stocks)
        extreme_pct = len(extreme_returns) / len(price_data) * 100
        assert extreme_pct < 0.1, \
            f"Found {len(extreme_returns)} extreme daily returns ({extreme_pct:.3f}% of data)"
    
    def test_no_duplicate_date_ticker_pairs(self, price_data):
        """Verify no duplicate (date, ticker) pairs exist."""
        if price_data is None:
            pytest.skip("Price data not available")
        
        duplicates = price_data.duplicated(subset=['date', 'ticker'], keep=False)
        duplicate_count = duplicates.sum()
        assert duplicate_count == 0, \
            f"Found {duplicate_count} duplicate (date, ticker) pairs"
    
    def test_sufficient_tickers(self, price_data):
        """Verify sufficient number of tickers for diversified analysis."""
        if price_data is None:
            pytest.skip("Price data not available")
        
        unique_tickers = price_data['ticker'].nunique()
        assert unique_tickers >= 50, \
            f"Only {unique_tickers} tickers found (need >= 50 for diversified analysis)"


class TestBenchmarkDataIntegrity:
    """Tests for benchmark data integrity."""
    
    def test_benchmark_data_exists(self, data_dir):
        """Verify benchmark data file exists."""
        bench_path = data_dir / "benchmark.csv"
        assert bench_path.exists(), "benchmark.csv not found in data directory"
    
    def test_benchmark_has_required_columns(self, benchmark_data):
        """Verify benchmark data has required columns."""
        if benchmark_data is None:
            pytest.skip("Benchmark data not available")
        
        assert 'date' in benchmark_data.columns, "Missing 'date' column"
        assert 'close' in benchmark_data.columns or 'price' in benchmark_data.columns, \
            "Missing price column (close or price)"
    
    def test_benchmark_aligns_with_price_data(self, price_data, benchmark_data):
        """Verify benchmark date range covers price data range."""
        if price_data is None or benchmark_data is None:
            pytest.skip("Data not available")
        
        price_min = price_data['date'].min()
        price_max = price_data['date'].max()
        bench_min = benchmark_data['date'].min()
        bench_max = benchmark_data['date'].max()
        
        # Benchmark should start on or before price data
        assert bench_min <= price_min + pd.Timedelta(days=5), \
            f"Benchmark starts too late: {bench_min} vs price start {price_min}"
        
        # Benchmark should extend to at least the same end date
        # (within a few days tolerance for weekends/holidays)
        assert bench_max >= price_max - pd.Timedelta(days=5), \
            f"Benchmark ends too early: {bench_max} vs price end {price_max}"
    
    def test_benchmark_no_gaps(self, benchmark_data):
        """Verify no significant gaps in benchmark data."""
        if benchmark_data is None:
            pytest.skip("Benchmark data not available")
        
        benchmark_data = benchmark_data.sort_values('date')
        date_diffs = benchmark_data['date'].diff().dt.days
        
        # Max gap should be ~4 days (weekends + holidays)
        max_gap = date_diffs.max()
        assert max_gap <= 10, \
            f"Found gap of {max_gap} days in benchmark data"


class TestSectorDataIntegrity:
    """Tests for sector classification data."""
    
    def test_sector_data_exists(self, data_dir):
        """Verify sector data file exists."""
        sector_path = data_dir / "sectors.csv"
        assert sector_path.exists(), "sectors.csv not found in data directory"
    
    def test_sector_has_required_columns(self, sector_data):
        """Verify sector data has required columns."""
        if sector_data is None:
            pytest.skip("Sector data not available")
        
        assert 'ticker' in sector_data.columns, "Missing 'ticker' column"
        assert 'sector' in sector_data.columns, "Missing 'sector' column"
    
    def test_no_duplicate_tickers_in_sectors(self, sector_data):
        """Verify no duplicate tickers in sector mapping."""
        if sector_data is None:
            pytest.skip("Sector data not available")
        
        duplicates = sector_data['ticker'].duplicated().sum()
        assert duplicates == 0, \
            f"Found {duplicates} duplicate tickers in sector data"
    
    def test_other_sector_percentage(self, sector_data):
        """
        Verify 'Other' sector doesn't dominate classifications.
        
        High 'Other' percentage indicates incomplete sector mapping.
        """
        if sector_data is None:
            pytest.skip("Sector data not available")
        
        other_count = (sector_data['sector'] == 'Other').sum()
        other_pct = other_count / len(sector_data) * 100
        
        assert other_pct < 20, \
            f"'Other' sector is {other_pct:.1f}% of stocks (should be < 20%)"
    
    def test_sector_coverage_of_price_data(self, price_data, sector_data):
        """Verify sector data covers most tickers in price data."""
        if price_data is None or sector_data is None:
            pytest.skip("Data not available")
        
        price_tickers = set(price_data['ticker'].unique())
        sector_tickers = set(sector_data['ticker'].unique())
        
        coverage = len(price_tickers & sector_tickers) / len(price_tickers) * 100
        assert coverage >= 80, \
            f"Sector coverage is only {coverage:.1f}% (should be >= 80%)"


class TestDataConsistency:
    """Tests for data consistency across different files."""
    
    def test_prices_not_empty(self, price_data):
        """Verify price data is not empty."""
        if price_data is None:
            pytest.skip("Price data not available")
        
        assert len(price_data) > 0, "Price data is empty"
    
    def test_benchmark_not_empty(self, benchmark_data):
        """Verify benchmark data is not empty."""
        if benchmark_data is None:
            pytest.skip("Benchmark data not available")
        
        assert len(benchmark_data) > 0, "Benchmark data is empty"
    
    def test_data_types_correct(self, price_data):
        """Verify data types are correct."""
        if price_data is None:
            pytest.skip("Price data not available")
        
        assert pd.api.types.is_datetime64_any_dtype(price_data['date']), \
            "Date column is not datetime type"
        assert pd.api.types.is_numeric_dtype(price_data['close']), \
            "Close column is not numeric type"
