"""
Pytest Configuration
=====================
Shared fixtures and configuration for tests.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_directory():
    """Create a temporary directory for tests."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def sample_portfolio_data():
    """Create sample portfolio data."""
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    return {
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


@pytest.fixture
def sample_stock_data():
    """Create sample stock data."""
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    
    stock_features = pd.DataFrame({
        'ticker': ['AAPL', 'MSFT', 'GOOGL'],
        'score': [80, 75, 70],
        'beta': [1.1, 1.2, 0.9],
        'pe_ratio': [25.0, 30.0, 20.0],
        'pb_ratio': [5.0, 6.0, 4.0],
        'roe': [0.15, 0.18, 0.12]
    })
    
    stock_returns = pd.DataFrame({
        'AAPL': np.random.normal(0.001, 0.02, 100),
        'MSFT': np.random.normal(0.001, 0.02, 100),
        'GOOGL': np.random.normal(0.001, 0.02, 100)
    }, index=dates)
    
    return {
        'features': stock_features,
        'data': stock_features,
        'returns': stock_returns
    }


@pytest.fixture
def sample_run_directory(temp_directory):
    """Create a sample run directory with all required files."""
    run_dir = temp_directory / 'test_run'
    run_dir.mkdir()
    
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    
    # Portfolio returns
    returns_df = pd.DataFrame({
        'date': dates,
        'portfolio_return': np.random.normal(0.001, 0.02, 100)
    })
    returns_df.to_csv(run_dir / 'backtest_returns.csv', index=False)
    
    # Portfolio positions
    positions = []
    for date in dates:
        positions.append({'date': date, 'ticker': 'AAPL', 'weight': 0.4})
        positions.append({'date': date, 'ticker': 'MSFT', 'weight': 0.35})
        positions.append({'date': date, 'ticker': 'GOOGL', 'weight': 0.25})
    positions_df = pd.DataFrame(positions)
    positions_df.to_csv(run_dir / 'backtest_positions.csv', index=False)
    
    # Price data
    price_data = []
    for date in dates:
        for ticker in ['AAPL', 'MSFT', 'GOOGL']:
            price_data.append({
                'date': date,
                'ticker': ticker,
                'close': 100 * (1 + np.random.normal(0.001, 0.02))
            })
    price_df = pd.DataFrame(price_data)
    price_df.to_csv(run_dir / 'prices.csv', index=False)
    
    # Portfolio enriched
    enriched_df = pd.DataFrame({
        'ticker': ['AAPL', 'MSFT', 'GOOGL'],
        'score': [80, 75, 70],
        'beta': [1.1, 1.2, 0.9],
        'pe_ratio': [25.0, 30.0, 20.0],
        'sector': ['Technology', 'Technology', 'Technology']
    })
    enriched_df.to_csv(run_dir / 'portfolio_enriched.csv', index=False)
    
    return run_dir
