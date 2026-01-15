"""
Test Enhanced Charts
====================
Test cases for enhanced visualization components.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.dashboard.components.enhanced_charts import (
    create_attribution_waterfall,
    create_factor_exposure_heatmap,
    create_comparison_chart,
    create_multi_metric_comparison,
    create_time_period_comparison
)


class TestAttributionWaterfall:
    """Test attribution waterfall chart."""
    
    def test_create_waterfall_basic(self):
        """Test basic waterfall chart creation."""
        attribution_data = {
            'factor_attribution': 0.05,
            'sector_attribution': 0.04,
            'stock_selection_attribution': 0.03,
            'timing_attribution': 0.03,
            'total_return': 0.15
        }
        
        fig = create_attribution_waterfall(attribution_data)
        
        assert fig is not None
        assert hasattr(fig, 'data')
        assert len(fig.data) > 0
    
    def test_create_waterfall_negative_attributions(self):
        """Test waterfall with negative attributions."""
        attribution_data = {
            'factor_attribution': -0.02,
            'sector_attribution': 0.04,
            'stock_selection_attribution': -0.01,
            'timing_attribution': 0.03,
            'total_return': 0.04
        }
        
        fig = create_attribution_waterfall(attribution_data)
        
        assert fig is not None
    
    def test_create_waterfall_missing_components(self):
        """Test waterfall with missing components."""
        attribution_data = {
            'factor_attribution': 0.05,
            'total_return': 0.15
        }
        
        fig = create_attribution_waterfall(attribution_data)
        
        assert fig is not None


class TestFactorExposureHeatmap:
    """Test factor exposure heatmap."""
    
    def test_create_heatmap_basic(self):
        """Test basic heatmap creation."""
        factor_exposures = {
            'Market': {'exposure': 0.95, 'contribution_to_return': 0.10, 'contribution_to_risk': 0.12},
            'Value': {'exposure': 0.25, 'contribution_to_return': 0.02, 'contribution_to_risk': 0.03},
            'Growth': {'exposure': -0.15, 'contribution_to_return': -0.01, 'contribution_to_risk': -0.02}
        }
        
        fig = create_factor_exposure_heatmap(factor_exposures)
        
        assert fig is not None
        assert hasattr(fig, 'data')
        assert len(fig.data) > 0
    
    def test_create_heatmap_empty(self):
        """Test heatmap with empty data."""
        factor_exposures = {}
        
        fig = create_factor_exposure_heatmap(factor_exposures)
        
        assert fig is not None


class TestComparisonChart:
    """Test comparison chart."""
    
    def test_create_comparison_basic(self):
        """Test basic comparison chart."""
        runs_data = [
            {'name': 'Run 1', 'run_id': 'r1', 'total_return': 0.15, 'sharpe_ratio': 0.8},
            {'name': 'Run 2', 'run_id': 'r2', 'total_return': 0.12, 'sharpe_ratio': 0.7},
            {'name': 'Run 3', 'run_id': 'r3', 'total_return': 0.18, 'sharpe_ratio': 0.9}
        ]
        
        fig = create_comparison_chart(runs_data, 'total_return')
        
        assert fig is not None
        assert hasattr(fig, 'data')
        assert len(fig.data) > 0
    
    def test_create_comparison_empty(self):
        """Test comparison chart with empty data."""
        runs_data = []
        
        fig = create_comparison_chart(runs_data, 'total_return')
        
        assert fig is not None


class TestMultiMetricComparison:
    """Test multi-metric comparison chart."""
    
    def test_create_radar_basic(self):
        """Test basic radar chart."""
        runs_data = [
            {'name': 'Run 1', 'total_return': 0.15, 'sharpe_ratio': 0.8, 'max_drawdown': -0.10},
            {'name': 'Run 2', 'total_return': 0.12, 'sharpe_ratio': 0.7, 'max_drawdown': -0.08}
        ]
        
        fig = create_multi_metric_comparison(runs_data, ['total_return', 'sharpe_ratio', 'max_drawdown'])
        
        assert fig is not None
        assert hasattr(fig, 'data')
        assert len(fig.data) > 0


class TestTimePeriodComparison:
    """Test time period comparison chart."""
    
    def test_create_time_period_basic(self):
        """Test basic time period comparison."""
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        returns_data = {
            'Full Period': pd.Series(np.random.normal(0.001, 0.02, 100), index=dates),
            'First Half': pd.Series(np.random.normal(0.001, 0.02, 50), index=dates[:50]),
            'Second Half': pd.Series(np.random.normal(0.001, 0.02, 50), index=dates[50:])
        }
        
        fig = create_time_period_comparison(returns_data)
        
        assert fig is not None
        assert hasattr(fig, 'data')
        assert len(fig.data) == len(returns_data)
    
    def test_create_time_period_empty(self):
        """Test time period comparison with empty data."""
        returns_data = {}
        
        fig = create_time_period_comparison(returns_data)
        
        assert fig is not None
