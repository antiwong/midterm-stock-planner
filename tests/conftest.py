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


@pytest.fixture
def config():
    """Load configuration from config.yaml."""
    import yaml
    from pathlib import Path
    
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    else:
        # Return default config if file doesn't exist
        return {
            'backtest': {
                'top_n': 10,
                'transaction_cost': 0.001,
                'rebalance_freq': 'MS'
            }
        }


@pytest.fixture
def output_dir(temp_directory):
    """Create output directory with sample run directories."""
    output_path = temp_directory / 'output'
    output_path.mkdir()
    
    # Create a sample run directory
    run_dir = output_path / 'run_test_20260101_120000_'
    run_dir.mkdir()
    
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    
    # Create backtest_positions.csv
    positions = []
    for date in dates[:10]:  # Just 10 dates for testing
        positions.append({'date': date, 'ticker': 'AAPL', 'weight': 0.4})
        positions.append({'date': date, 'ticker': 'MSFT', 'weight': 0.35})
        positions.append({'date': date, 'ticker': 'GOOGL', 'weight': 0.25})
    positions_df = pd.DataFrame(positions)
    positions_df.to_csv(run_dir / 'backtest_positions.csv', index=False)
    
    # Create backtest_metrics.json
    metrics = {
        'total_return': 0.15,
        'annualized_return': 0.12,
        'excess_return': 0.03,
        'volatility': 0.18,
        'sharpe_ratio': 0.67,
        'max_drawdown': -0.10,
        'hit_rate': 0.55
    }
    import json
    with open(run_dir / 'backtest_metrics.json', 'w') as f:
        json.dump(metrics, f)
    
    # Create backtest_returns.csv (required by test_backtest_output_structure)
    returns_df = pd.DataFrame({
        'date': dates[:10],
        'portfolio_return': np.random.normal(0.001, 0.02, 10)
    })
    returns_df.to_csv(run_dir / 'backtest_returns.csv', index=False)
    
    return output_path


@pytest.fixture
def data_dir(temp_directory):
    """Create data directory with sample data files."""
    data_path = temp_directory / 'data'
    data_path.mkdir()
    
    # Create enough data for 6+ years (required for walk-forward backtest)
    dates = pd.date_range('2015-01-01', periods=2200, freq='D')  # ~6 years
    
    # Create prices.csv with 50+ tickers for diversification tests
    price_data = []
    # Generate 50+ tickers across multiple sectors
    tech_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'INTC', 'AMD', 'CRM', 'ORCL', 'ADBE', 'CSCO', 'AVGO', 'TXN', 'QCOM']
    finance_tickers = ['JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'SCHW', 'AXP', 'COF']
    healthcare_tickers = ['JNJ', 'PFE', 'UNH', 'ABT', 'TMO', 'ABBV', 'MRK', 'LLY', 'BMY', 'GILD']
    consumer_tickers = ['WMT', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'TJX', 'COST', 'NFLX']
    industrial_tickers = ['BA', 'CAT', 'GE', 'HON', 'MMM', 'RTX', 'LMT', 'NOC', 'GD', 'TDG']
    energy_tickers = ['XOM', 'CVX', 'COP', 'SLB', 'EOG']
    
    all_tickers = tech_tickers + finance_tickers + healthcare_tickers + consumer_tickers + industrial_tickers + energy_tickers
    
    for date in dates:
        for ticker in all_tickers:
            price_data.append({
                'date': date,
                'ticker': ticker,
                'close': 100 * (1 + np.random.normal(0.001, 0.02))
            })
    price_df = pd.DataFrame(price_data)
    price_df.to_csv(data_path / 'prices.csv', index=False)
    
    # Create benchmark.csv with 'close' column (required by loader)
    benchmark_data = []
    for date in dates:
        benchmark_data.append({
            'date': date,
            'close': 100 * (1 + np.random.normal(0.0008, 0.015))  # Use 'close' instead of 'SPY'
        })
    benchmark_df = pd.DataFrame(benchmark_data)
    benchmark_df.to_csv(data_path / 'benchmark.csv', index=False)
    
    # Create sectors.csv with diverse sectors (not too many 'Other')
    sector_data = []
    sector_mapping = {
        **{t: 'Technology' for t in tech_tickers},
        **{t: 'Financial Services' for t in finance_tickers},
        **{t: 'Healthcare' for t in healthcare_tickers},
        **{t: 'Consumer Cyclical' for t in consumer_tickers},
        **{t: 'Industrial' for t in industrial_tickers},
        **{t: 'Energy' for t in energy_tickers}
    }
    
    for ticker in all_tickers:
        sector_data.append({
            'ticker': ticker,
            'sector': sector_mapping.get(ticker, 'Other')
        })
    sector_df = pd.DataFrame(sector_data)
    sector_df.to_csv(data_path / 'sectors.csv', index=False)
    
    return data_path


@pytest.fixture
def price_data(data_dir):
    """Load price data from data directory."""
    price_path = data_dir / 'prices.csv'
    if price_path.exists():
        df = pd.read_csv(price_path, parse_dates=['date'])
        return df
    return None


@pytest.fixture
def sector_data(data_dir):
    """Load sector data from data directory."""
    sector_path = data_dir / 'sectors.csv'
    if sector_path.exists():
        df = pd.read_csv(sector_path)
        return df
    return None


@pytest.fixture
def benchmark_data(data_dir):
    """Load benchmark data from data directory."""
    benchmark_path = data_dir / 'benchmark.csv'
    if benchmark_path.exists():
        df = pd.read_csv(benchmark_path, parse_dates=['date'])
        return df
    return None


@pytest.fixture
def project_root():
    """Get project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def latest_metrics(output_dir):
    """Load metrics from the latest run."""
    import json
    
    run_dirs = sorted(output_dir.glob("run_*"))
    if not run_dirs:
        return None
    
    latest = run_dirs[-1]
    metrics_files = list(latest.glob("backtest_metrics.json"))
    if not metrics_files:
        return None
    
    with open(metrics_files[0]) as f:
        return json.load(f)
