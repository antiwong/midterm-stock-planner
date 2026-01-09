"""
Metric Scaling Tests

CRITICAL: These tests ensure financial metrics are calculated and stored correctly.

The most common source of errors in backtesting is incorrect metric scaling:
- Returns should be stored as decimals (0.10 = 10%), not percentages (10)
- Volatility should be stored as decimals (0.25 = 25%)
- Sharpe ratio should be a raw number (typically -3 to +3)
- Max drawdown should be negative and in [-1, 0]

These tests catch scaling errors before they propagate to the UI.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import json


class TestReturnMetricScaling:
    """Tests for return metric calculations and scaling."""
    
    @pytest.fixture
    def latest_metrics(self, output_dir):
        """Load metrics from the latest run."""
        run_dirs = sorted(output_dir.glob("run_*"))
        if not run_dirs:
            return None
        
        latest = run_dirs[-1]
        metrics_files = list(latest.glob("backtest_metrics.json"))
        if not metrics_files:
            return None
        
        with open(metrics_files[0]) as f:
            return json.load(f)
    
    def test_total_return_is_decimal(self, latest_metrics):
        """
        Verify total return is stored as decimal.
        
        Example: 50% return should be stored as 0.50, not 50.
        """
        if latest_metrics is None:
            pytest.skip("No metrics available")
        
        total_return = latest_metrics.get('total_return')
        if total_return is None:
            pytest.skip("total_return not in metrics")
        
        # Realistic multi-year returns are typically between -0.9 and 10.0
        # (i.e., -90% to +1000%)
        assert -1.0 <= total_return <= 20.0, \
            f"total_return {total_return} seems incorrectly scaled (expect decimal form)"
        
        # If > 10, it's likely stored as percentage
        if total_return > 10:
            pytest.fail(
                f"total_return={total_return} looks like a percentage. "
                f"Should be decimal (e.g., 0.50 for 50%)"
            )
    
    def test_annualized_return_is_decimal(self, latest_metrics):
        """
        Verify annualized return is stored as decimal.
        
        Typical range: -50% to +100% annually.
        """
        if latest_metrics is None:
            pytest.skip("No metrics available")
        
        ann_return = latest_metrics.get('annualized_return')
        if ann_return is None:
            pytest.skip("annualized_return not in metrics")
        
        # Annualized returns rarely exceed 100% (1.0 in decimal)
        assert -1.0 <= ann_return <= 2.0, \
            f"annualized_return {ann_return} seems unrealistic for annual return"
        
        if ann_return > 2:
            pytest.fail(
                f"annualized_return={ann_return} ({ann_return*100:.0f}%) is unrealistic. "
                f"Check if it's stored as percentage instead of decimal."
            )
    
    def test_excess_return_is_decimal(self, latest_metrics):
        """Verify excess return (vs benchmark) is stored as decimal."""
        if latest_metrics is None:
            pytest.skip("No metrics available")
        
        excess_return = latest_metrics.get('excess_return')
        if excess_return is None:
            pytest.skip("excess_return not in metrics")
        
        # Excess return is typically between -1.0 and +1.0
        assert -2.0 <= excess_return <= 2.0, \
            f"excess_return {excess_return} seems incorrectly scaled"


class TestVolatilityMetricScaling:
    """Tests for volatility metric calculations."""
    
    @pytest.fixture
    def latest_metrics(self, output_dir):
        """Load metrics from the latest run."""
        run_dirs = sorted(output_dir.glob("run_*"))
        if not run_dirs:
            return None
        
        latest = run_dirs[-1]
        metrics_files = list(latest.glob("backtest_metrics.json"))
        if not metrics_files:
            return None
        
        with open(metrics_files[0]) as f:
            return json.load(f)
    
    def test_volatility_is_decimal(self, latest_metrics):
        """
        Verify volatility is stored as decimal.
        
        Example: 25% volatility should be stored as 0.25, not 25.
        """
        if latest_metrics is None:
            pytest.skip("No metrics available")
        
        volatility = latest_metrics.get('volatility')
        if volatility is None:
            pytest.skip("volatility not in metrics")
        
        # Annualized volatility for equities is typically 10-80%
        assert 0.05 <= volatility <= 1.5, \
            f"volatility {volatility} seems incorrectly scaled"
        
        if volatility > 1.5:
            pytest.fail(
                f"volatility={volatility} ({volatility*100:.0f}%) is unrealistic. "
                f"Check if stored as percentage instead of decimal."
            )
    
    def test_volatility_is_positive(self, latest_metrics):
        """Volatility must be positive."""
        if latest_metrics is None:
            pytest.skip("No metrics available")
        
        volatility = latest_metrics.get('volatility')
        if volatility is None:
            pytest.skip("volatility not in metrics")
        
        assert volatility > 0, f"volatility must be positive, got {volatility}"


class TestSharpeRatioScaling:
    """Tests for Sharpe ratio calculations."""
    
    @pytest.fixture
    def latest_metrics(self, output_dir):
        """Load metrics from the latest run."""
        run_dirs = sorted(output_dir.glob("run_*"))
        if not run_dirs:
            return None
        
        latest = run_dirs[-1]
        metrics_files = list(latest.glob("backtest_metrics.json"))
        if not metrics_files:
            return None
        
        with open(metrics_files[0]) as f:
            return json.load(f)
    
    def test_sharpe_ratio_in_realistic_range(self, latest_metrics):
        """
        Verify Sharpe ratio is in realistic range.
        
        Sharpe ratio is NOT a percentage. Typical values:
        - < 0: Underperforming risk-free rate
        - 0-1: Average to good
        - 1-2: Very good
        - 2-3: Excellent
        - > 3: Exceptional (rare, verify data)
        """
        if latest_metrics is None:
            pytest.skip("No metrics available")
        
        sharpe = latest_metrics.get('sharpe_ratio')
        if sharpe is None:
            pytest.skip("sharpe_ratio not in metrics")
        
        # Realistic range for long-term strategies
        assert -3.0 <= sharpe <= 5.0, \
            f"sharpe_ratio {sharpe} is outside realistic range [-3, 5]"
        
        if abs(sharpe) > 5:
            pytest.fail(
                f"sharpe_ratio={sharpe} is suspiciously high. "
                f"Verify calculation and check for data issues."
            )
    
    def test_sharpe_not_nan_or_inf(self, latest_metrics):
        """Sharpe ratio should not be NaN or infinite."""
        if latest_metrics is None:
            pytest.skip("No metrics available")
        
        sharpe = latest_metrics.get('sharpe_ratio')
        if sharpe is None:
            pytest.skip("sharpe_ratio not in metrics")
        
        assert not np.isnan(sharpe), "sharpe_ratio is NaN"
        assert not np.isinf(sharpe), "sharpe_ratio is infinite"


class TestDrawdownMetricScaling:
    """Tests for drawdown metric calculations."""
    
    @pytest.fixture
    def latest_metrics(self, output_dir):
        """Load metrics from the latest run."""
        run_dirs = sorted(output_dir.glob("run_*"))
        if not run_dirs:
            return None
        
        latest = run_dirs[-1]
        metrics_files = list(latest.glob("backtest_metrics.json"))
        if not metrics_files:
            return None
        
        with open(metrics_files[0]) as f:
            return json.load(f)
    
    def test_max_drawdown_is_negative(self, latest_metrics):
        """
        Verify max drawdown is negative (represents a loss from peak).
        
        Max drawdown should be stored as negative decimal:
        - -0.20 means 20% drawdown
        - -0.50 means 50% drawdown
        """
        if latest_metrics is None:
            pytest.skip("No metrics available")
        
        max_dd = latest_metrics.get('max_drawdown')
        if max_dd is None:
            pytest.skip("max_drawdown not in metrics")
        
        assert max_dd <= 0, \
            f"max_drawdown should be negative (loss), got {max_dd}"
    
    def test_max_drawdown_within_bounds(self, latest_metrics):
        """
        Verify max drawdown is in valid range [-1, 0].
        
        -1.0 = 100% loss (total wipeout)
        0.0 = No drawdown
        """
        if latest_metrics is None:
            pytest.skip("No metrics available")
        
        max_dd = latest_metrics.get('max_drawdown')
        if max_dd is None:
            pytest.skip("max_drawdown not in metrics")
        
        assert -1.0 <= max_dd <= 0, \
            f"max_drawdown {max_dd} outside valid range [-1, 0]"
        
        if max_dd < -1.0:
            pytest.fail(
                f"max_drawdown={max_dd} ({max_dd*100:.0f}%) exceeds -100%. "
                f"Check if stored as percentage instead of decimal."
            )


class TestHitRateScaling:
    """Tests for hit rate / win rate calculations."""
    
    @pytest.fixture
    def latest_metrics(self, output_dir):
        """Load metrics from the latest run."""
        run_dirs = sorted(output_dir.glob("run_*"))
        if not run_dirs:
            return None
        
        latest = run_dirs[-1]
        metrics_files = list(latest.glob("backtest_metrics.json"))
        if not metrics_files:
            return None
        
        with open(metrics_files[0]) as f:
            return json.load(f)
    
    def test_hit_rate_is_decimal(self, latest_metrics):
        """
        Verify hit rate is stored as decimal.
        
        Hit rate 55% should be stored as 0.55, not 55.
        """
        if latest_metrics is None:
            pytest.skip("No metrics available")
        
        hit_rate = latest_metrics.get('hit_rate')
        if hit_rate is None:
            pytest.skip("hit_rate not in metrics")
        
        assert 0 <= hit_rate <= 1, \
            f"hit_rate {hit_rate} outside valid range [0, 1]"
        
        if hit_rate > 1:
            pytest.fail(
                f"hit_rate={hit_rate} looks like percentage. "
                f"Should be decimal (e.g., 0.55 for 55%)"
            )


class TestMetricCalculationConsistency:
    """Tests for consistency between related metrics."""
    
    @pytest.fixture
    def latest_metrics(self, output_dir):
        """Load metrics from the latest run."""
        run_dirs = sorted(output_dir.glob("run_*"))
        if not run_dirs:
            return None
        
        latest = run_dirs[-1]
        metrics_files = list(latest.glob("backtest_metrics.json"))
        if not metrics_files:
            return None
        
        with open(metrics_files[0]) as f:
            return json.load(f)
    
    def test_sharpe_consistent_with_return_and_vol(self, latest_metrics):
        """
        Verify Sharpe ratio is approximately consistent with return/volatility.
        
        Sharpe ≈ (Return - RiskFreeRate) / Volatility
        """
        if latest_metrics is None:
            pytest.skip("No metrics available")
        
        ann_return = latest_metrics.get('annualized_return')
        volatility = latest_metrics.get('volatility')
        sharpe = latest_metrics.get('sharpe_ratio')
        
        if any(x is None for x in [ann_return, volatility, sharpe]):
            pytest.skip("Missing metrics for consistency check")
        
        if volatility == 0:
            pytest.skip("Zero volatility, cannot check consistency")
        
        # Approximate Sharpe (assuming 0% risk-free rate)
        approx_sharpe = ann_return / volatility
        
        # Allow some tolerance for risk-free rate adjustments
        tolerance = 0.5
        assert abs(sharpe - approx_sharpe) < tolerance, \
            f"Sharpe {sharpe} inconsistent with return/vol calculation {approx_sharpe}"
    
    def test_total_vs_annualized_return_consistent(self, latest_metrics):
        """
        Verify total and annualized returns are consistent.
        
        For n years: (1 + total_return)^(1/n) - 1 ≈ annualized_return
        """
        if latest_metrics is None:
            pytest.skip("No metrics available")
        
        total_return = latest_metrics.get('total_return')
        ann_return = latest_metrics.get('annualized_return')
        
        if total_return is None or ann_return is None:
            pytest.skip("Missing return metrics")
        
        # Sign should be consistent
        if total_return != 0:
            assert (total_return > 0) == (ann_return > 0), \
                f"Total return ({total_return}) and annualized ({ann_return}) have different signs"
