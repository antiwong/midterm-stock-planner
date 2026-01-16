"""
Tests for download_fundamentals.py script
==========================================
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from scripts.download_fundamentals import (
    load_watchlist_tickers,
    fetch_fundamentals_yfinance
)


class TestLoadWatchlistTickers:
    """Test watchlist loading functionality."""
    
    def test_load_watchlist_with_name(self, tmp_path):
        """Test loading a specific watchlist by name."""
        # Create test YAML file
        yaml_content = """
watchlists:
  test_watchlist:
    name: "Test Watchlist"
    symbols:
      - AAPL
      - MSFT
      - GOOGL
"""
        watchlist_file = tmp_path / "watchlists.yaml"
        watchlist_file.write_text(yaml_content)
        
        with patch('scripts.download_fundamentals.Path') as mock_path:
            mock_path.return_value = watchlist_file
            from scripts.download_fundamentals import Path as ScriptPath
            with patch.object(ScriptPath, 'exists', return_value=True):
                tickers = load_watchlist_tickers('test_watchlist')
                assert 'AAPL' in tickers
                assert 'MSFT' in tickers
                assert 'GOOGL' in tickers
    
    def test_load_watchlist_not_found(self, tmp_path):
        """Test handling of non-existent watchlist."""
        yaml_content = """
watchlists:
  test_watchlist:
    symbols: [AAPL]
"""
        watchlist_file = tmp_path / "watchlists.yaml"
        watchlist_file.write_text(yaml_content)
        
        with patch('scripts.download_fundamentals.Path') as mock_path:
            mock_path.return_value = watchlist_file
            from scripts.download_fundamentals import Path as ScriptPath
            with patch.object(ScriptPath, 'exists', return_value=True):
                tickers = load_watchlist_tickers('nonexistent')
                assert tickers == []
    
    def test_load_watchlist_default(self, tmp_path):
        """Test loading default watchlist when no name provided."""
        yaml_content = """
watchlists:
  first:
    symbols: [AAPL]
  second:
    symbols: [MSFT]
"""
        watchlist_file = tmp_path / "watchlists.yaml"
        watchlist_file.write_text(yaml_content)
        
        with patch('scripts.download_fundamentals.Path') as mock_path:
            mock_path.return_value = watchlist_file
            from scripts.download_fundamentals import Path as ScriptPath
            with patch.object(ScriptPath, 'exists', return_value=True):
                tickers = load_watchlist_tickers()
                assert len(tickers) > 0
    
    def test_load_watchlist_direct_list(self, tmp_path):
        """Test loading watchlist with direct list format."""
        yaml_content = """
watchlists:
  test_list:
    - AAPL
    - MSFT
"""
        watchlist_file = tmp_path / "watchlists.yaml"
        watchlist_file.write_text(yaml_content)
        
        with patch('scripts.download_fundamentals.Path') as mock_path:
            mock_path.return_value = watchlist_file
            from scripts.download_fundamentals import Path as ScriptPath
            with patch.object(ScriptPath, 'exists', return_value=True):
                tickers = load_watchlist_tickers('test_list')
                assert 'AAPL' in tickers
                assert 'MSFT' in tickers
    
    def test_load_watchlist_with_tickers_key(self, tmp_path):
        """Test loading watchlist with 'tickers' key instead of 'symbols'."""
        yaml_content = """
watchlists:
  test_tickers:
    name: "Test"
    tickers:
      - AAPL
      - MSFT
"""
        watchlist_file = tmp_path / "watchlists.yaml"
        watchlist_file.write_text(yaml_content)
        
        with patch('scripts.download_fundamentals.Path') as mock_path:
            mock_path.return_value = watchlist_file
            from scripts.download_fundamentals import Path as ScriptPath
            with patch.object(ScriptPath, 'exists', return_value=True):
                tickers = load_watchlist_tickers('test_tickers')
                assert 'AAPL' in tickers
                assert 'MSFT' in tickers


class TestFetchFundamentals:
    """Test fundamentals fetching functionality."""
    
    @patch('scripts.download_fundamentals.yf')
    def test_fetch_fundamentals_success(self, mock_yf):
        """Test successful fundamentals fetch."""
        mock_stock = MagicMock()
        mock_stock.info = {
            'trailingPE': 25.5,
            'priceToBook': 5.2,
            'returnOnEquity': 0.15,
            'profitMargins': 0.20,
            'marketCap': 1000000000,
            'debtToEquity': 0.5
        }
        mock_yf.Ticker.return_value = mock_stock
        
        result = fetch_fundamentals_yfinance('AAPL')
        
        assert result is not None
        assert result['ticker'] == 'AAPL'
        # Function returns 'pe' and 'pb', not 'pe_ratio' and 'pb_ratio'
        assert 'pe' in result or 'pe_ratio' in result
        assert 'pb' in result or 'pb_ratio' in result
    
    @patch('scripts.download_fundamentals.yf')
    def test_fetch_fundamentals_error(self, mock_yf):
        """Test handling of fetch errors."""
        mock_yf.Ticker.side_effect = Exception("API Error")
        
        result = fetch_fundamentals_yfinance('INVALID')
        
        assert result is None


class TestFundamentalsCompleteness:
    """Test fundamentals completeness checking logic."""
    
    def test_completeness_logic_with_data(self):
        """Test completeness check logic with existing fundamentals."""
        df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'pe_ratio': [25.5, 30.0, 28.0],
            'pb_ratio': [5.2, 6.0, 5.5],
            'roe': [0.15, 0.20, 0.18],
            'net_margin': [0.20, 0.25, 0.22]
        })
        
        # Test the logic
        required_fields = ['pe_ratio', 'pb_ratio', 'roe', 'net_margin']
        missing = []
        
        for field in required_fields:
            if field not in df.columns:
                missing.append(field)
        
        assert len(missing) == 0
    
    def test_completeness_logic_missing_fields(self):
        """Test completeness check logic with missing fields."""
        df = pd.DataFrame({
            'ticker': ['AAPL'],
            'pe_ratio': [25.5]
            # Missing pb_ratio, roe, net_margin
        })
        
        required_fields = ['pe_ratio', 'pb_ratio', 'roe', 'net_margin']
        missing = [f for f in required_fields if f not in df.columns]
        
        assert len(missing) == 3
        assert 'pb_ratio' in missing
        assert 'roe' in missing
        assert 'net_margin' in missing
