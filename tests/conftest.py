"""
Pytest configuration and shared fixtures for the test suite.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import yaml
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def config_path(project_root):
    """Return the path to the main config file."""
    return project_root / "config" / "config.yaml"


@pytest.fixture
def data_dir(project_root):
    """Return the path to the data directory."""
    return project_root / "data"


@pytest.fixture
def output_dir(project_root):
    """Return the path to the output directory."""
    return project_root / "output"


@pytest.fixture
def config(config_path):
    """Load and return the configuration."""
    with open(config_path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def price_data(data_dir):
    """Load price data."""
    price_path = data_dir / "prices.csv"
    if price_path.exists():
        df = pd.read_csv(price_path, parse_dates=['date'])
        return df
    return None


@pytest.fixture
def benchmark_data(data_dir):
    """Load benchmark data."""
    bench_path = data_dir / "benchmark.csv"
    if bench_path.exists():
        df = pd.read_csv(bench_path, parse_dates=['date'])
        return df
    return None


@pytest.fixture
def sector_data(data_dir):
    """Load sector mapping data."""
    sector_path = data_dir / "sectors.csv"
    if sector_path.exists() and sector_path.stat().st_size > 0:
        df = pd.read_csv(sector_path)
        return df
    return None


@pytest.fixture
def sample_returns():
    """Generate sample returns for testing metric calculations."""
    np.random.seed(42)
    # Realistic daily returns: mean ~0.05% daily, std ~1.5%
    returns = np.random.normal(0.0005, 0.015, 252)
    return pd.Series(returns)


@pytest.fixture
def sample_positions():
    """Generate sample portfolio positions for testing."""
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 
               'META', 'TSLA', 'JPM', 'V', 'UNH']
    weights = [0.1] * 10  # Equal weight
    return pd.DataFrame({
        'ticker': tickers,
        'weight': weights
    })
