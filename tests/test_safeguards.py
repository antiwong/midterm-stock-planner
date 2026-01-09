"""
Safeguards Validation Tests

Tests for the automated validation safeguards that ensure
backtest runs meet quality and risk criteria.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import json
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.validation.safeguards import (
    check_weights_sum_to_one,
    check_position_count,
    check_volatility_bounds,
    check_drawdown_bounds,
    check_return_sanity,
    check_sector_concentration,
    check_no_negative_weights,
    check_no_excessive_single_position,
    ValidationResult,
    RISK_PROFILE_BOUNDS,
)


class TestWeightsSumToOne:
    """Tests for weight sum validation."""
    
    def test_valid_weights(self):
        """Weights summing to 1.0 should pass."""
        positions = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 3),
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'weight': [0.4, 0.35, 0.25]
        })
        
        result = check_weights_sum_to_one(positions)
        assert result.passed
    
    def test_invalid_weights(self):
        """Weights not summing to 1.0 should fail."""
        positions = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 3),
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'weight': [0.4, 0.35, 0.20]  # Sum = 0.95
        })
        
        result = check_weights_sum_to_one(positions)
        assert not result.passed
        assert result.severity == "error"
    
    def test_multiple_dates(self):
        """Multiple dates with valid weights should pass."""
        positions = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 2 + ['2024-02-01'] * 2),
            'ticker': ['AAPL', 'MSFT', 'AAPL', 'GOOGL'],
            'weight': [0.5, 0.5, 0.6, 0.4]
        })
        
        result = check_weights_sum_to_one(positions)
        assert result.passed


class TestPositionCount:
    """Tests for position count validation."""
    
    def test_correct_count(self):
        """Correct position count should pass."""
        positions = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 10),
            'ticker': [f'STOCK{i}' for i in range(10)],
            'weight': [0.1] * 10
        })
        
        result = check_position_count(positions, expected_count=10)
        assert result.passed
    
    def test_incorrect_count(self):
        """Incorrect position count should fail."""
        positions = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 5),
            'ticker': [f'STOCK{i}' for i in range(5)],
            'weight': [0.2] * 5
        })
        
        result = check_position_count(positions, expected_count=10)
        assert not result.passed
        assert result.severity == "error"


class TestVolatilityBounds:
    """Tests for volatility bounds validation."""
    
    def test_within_conservative_bounds(self):
        """Volatility within conservative bounds should pass."""
        metrics = {'volatility': 0.20}  # 20%
        result = check_volatility_bounds(metrics, 'conservative')
        assert result.passed
    
    def test_exceeds_conservative_bounds(self):
        """Volatility exceeding conservative bounds should warn."""
        metrics = {'volatility': 0.40}  # 40%
        result = check_volatility_bounds(metrics, 'conservative')
        assert not result.passed
        assert result.severity == "warning"
    
    def test_within_aggressive_bounds(self):
        """High volatility within aggressive bounds should pass."""
        metrics = {'volatility': 0.70}  # 70%
        result = check_volatility_bounds(metrics, 'aggressive')
        assert result.passed


class TestDrawdownBounds:
    """Tests for drawdown bounds validation."""
    
    def test_within_bounds(self):
        """Drawdown within bounds should pass."""
        metrics = {'max_drawdown': -0.15}  # -15%
        result = check_drawdown_bounds(metrics, 'conservative')
        assert result.passed
    
    def test_exceeds_bounds(self):
        """Drawdown exceeding bounds should warn."""
        metrics = {'max_drawdown': -0.50}  # -50%
        result = check_drawdown_bounds(metrics, 'conservative')
        assert not result.passed
        assert result.severity == "warning"


class TestReturnSanity:
    """Tests for return sanity validation."""
    
    def test_sane_returns(self):
        """Reasonable returns should pass."""
        metrics = {
            'total_return': 0.50,       # 50%
            'annualized_return': 0.15   # 15%
        }
        result = check_return_sanity(metrics)
        assert result.passed
    
    def test_insane_total_return(self):
        """Unrealistic total return should fail."""
        metrics = {
            'total_return': 100.0,      # 10000% - suspicious
            'annualized_return': 0.50
        }
        result = check_return_sanity(metrics)
        assert not result.passed
        assert result.severity == "error"
    
    def test_insane_annualized_return(self):
        """Unrealistic annualized return should fail."""
        metrics = {
            'total_return': 2.0,
            'annualized_return': 5.0    # 500% annual - suspicious
        }
        result = check_return_sanity(metrics)
        assert not result.passed


class TestSectorConcentration:
    """Tests for sector concentration validation."""
    
    def test_diversified_portfolio(self):
        """Diversified portfolio should pass."""
        positions = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 5),
            'ticker': ['AAPL', 'JPM', 'UNH', 'XOM', 'WMT'],
            'weight': [0.2] * 5
        })
        
        sector_map = {
            'AAPL': 'Technology',
            'JPM': 'Financial',
            'UNH': 'Healthcare',
            'XOM': 'Energy',
            'WMT': 'Consumer'
        }
        
        result = check_sector_concentration(positions, sector_map, 'moderate')
        assert result.passed
    
    def test_concentrated_portfolio(self):
        """Concentrated portfolio should warn."""
        positions = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 5),
            'ticker': ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'XOM'],
            'weight': [0.2] * 5
        })
        
        sector_map = {
            'AAPL': 'Technology',
            'MSFT': 'Technology',
            'GOOGL': 'Technology',
            'NVDA': 'Technology',
            'XOM': 'Energy'
        }  # 80% tech
        
        result = check_sector_concentration(positions, sector_map, 'moderate')
        assert not result.passed
        assert result.severity == "warning"


class TestNoNegativeWeights:
    """Tests for negative weight validation."""
    
    def test_all_positive(self):
        """All positive weights should pass."""
        positions = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 3),
            'ticker': ['A', 'B', 'C'],
            'weight': [0.4, 0.35, 0.25]
        })
        
        result = check_no_negative_weights(positions)
        assert result.passed
    
    def test_negative_weight(self):
        """Negative weights should fail."""
        positions = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 3),
            'ticker': ['A', 'B', 'C'],
            'weight': [0.5, 0.6, -0.1]  # Short position
        })
        
        result = check_no_negative_weights(positions)
        assert not result.passed
        assert result.severity == "error"


class TestNoExcessivePosition:
    """Tests for excessive position concentration."""
    
    def test_balanced_positions(self):
        """Balanced positions should pass."""
        positions = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 4),
            'ticker': ['A', 'B', 'C', 'D'],
            'weight': [0.25] * 4
        })
        
        result = check_no_excessive_single_position(positions, max_weight=0.5)
        assert result.passed
    
    def test_excessive_position(self):
        """Excessive single position should fail."""
        positions = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 3),
            'ticker': ['A', 'B', 'C'],
            'weight': [0.7, 0.2, 0.1]  # 70% in one stock
        })
        
        result = check_no_excessive_single_position(positions, max_weight=0.5)
        assert not result.passed
        assert result.severity == "error"


class TestRiskProfileBounds:
    """Tests for risk profile configurations."""
    
    def test_conservative_strictest(self):
        """Conservative should have strictest bounds."""
        assert RISK_PROFILE_BOUNDS['conservative']['max_volatility'] < \
               RISK_PROFILE_BOUNDS['moderate']['max_volatility']
        assert RISK_PROFILE_BOUNDS['conservative']['max_drawdown'] > \
               RISK_PROFILE_BOUNDS['moderate']['max_drawdown']  # Less negative = stricter
    
    def test_aggressive_loosest(self):
        """Aggressive should have loosest bounds."""
        assert RISK_PROFILE_BOUNDS['aggressive']['max_volatility'] > \
               RISK_PROFILE_BOUNDS['moderate']['max_volatility']
        assert RISK_PROFILE_BOUNDS['aggressive']['max_drawdown'] < \
               RISK_PROFILE_BOUNDS['moderate']['max_drawdown']  # More negative = looser
    
    def test_all_profiles_have_required_keys(self):
        """All profiles should have required bound keys."""
        required_keys = ['max_volatility', 'max_drawdown', 'min_sharpe', 'max_sector_weight']
        
        for profile in ['conservative', 'moderate', 'aggressive']:
            for key in required_keys:
                assert key in RISK_PROFILE_BOUNDS[profile], \
                    f"Missing {key} in {profile} profile"
