"""Regression tests for QuantaAlpha k2e implementations and Tier 1 feature importance.

Tests cover:
  k2e.1: IC threshold checking in rolling backtest
  k2e.2: Volume surge + OBV filter in trigger backtest
  k2e.3: Relative strength (rel_strength_21d) calculation
  k2e.4: VIX gating in trigger backtest
  k2e.5: Overfitting detection (train/test Sharpe ratio)
  Tier 1: Feature importance extraction, aggregation, and marginal contribution
"""

import sys
import os

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# k2e.1: IC Threshold Checking
# ---------------------------------------------------------------------------

class TestICThresholdChecking:
    """Tests for BacktestConfig ic_min_threshold and counting logic."""

    def test_backtest_config_has_ic_fields(self):
        """BacktestConfig should have ic_min_threshold and ic_action fields."""
        from src.config.config import BacktestConfig

        cfg = BacktestConfig()
        assert cfg.ic_min_threshold is None
        assert cfg.ic_action == "warn"

    def test_backtest_config_ic_threshold_settable(self):
        from src.config.config import BacktestConfig

        cfg = BacktestConfig(ic_min_threshold=0.02, ic_action="off")
        assert cfg.ic_min_threshold == 0.02
        assert cfg.ic_action == "off"

    def test_windows_below_ic_threshold_count(self):
        """Replicate the IC threshold counting logic from rolling.py (lines 642-646).

        Given synthetic window_results with known IC values and a threshold,
        verify the count of windows where |IC| < threshold.
        """
        window_results = [
            {"ic": 0.05},   # |0.05| >= 0.03 -> OK
            {"ic": -0.01},  # |0.01| < 0.03 -> below
            {"ic": 0.02},   # |0.02| < 0.03 -> below
            {"ic": -0.04},  # |0.04| >= 0.03 -> OK
            {"ic": None},   # skip
            {"ic": 0.001},  # |0.001| < 0.03 -> below
        ]
        ic_min_threshold = 0.03

        # Reproduce logic from rolling.py line 644-646
        count = sum(
            1
            for w in window_results
            if w.get("ic") is not None and abs(w["ic"]) < ic_min_threshold
        )
        assert count == 3

    def test_windows_below_ic_threshold_zero_when_all_pass(self):
        window_results = [
            {"ic": 0.10},
            {"ic": -0.05},
            {"ic": 0.08},
        ]
        ic_min_threshold = 0.03
        count = sum(
            1
            for w in window_results
            if w.get("ic") is not None and abs(w["ic"]) < ic_min_threshold
        )
        assert count == 0

    def test_windows_below_ic_threshold_disabled_when_none(self):
        """When ic_min_threshold is None, counting is skipped."""
        from src.config.config import BacktestConfig

        cfg = BacktestConfig()
        assert cfg.ic_min_threshold is None
        # The rolling.py code only enters the block when _ic_thresh is not None
        # so no metric would be stored.


# ---------------------------------------------------------------------------
# k2e.2: Volume Surge + OBV Filter
# ---------------------------------------------------------------------------

class TestVolumeSurgeOBVFilter:
    """Tests for institutional volume filter in trigger_backtest.py."""

    def test_trigger_config_has_volume_fields(self):
        from src.backtest.trigger_backtest import TriggerConfig

        cfg = TriggerConfig()
        assert cfg.volume_surge_min is None
        assert cfg.obv_slope_positive is False

    def test_volume_surge_blocks_buy_when_low_volume(self):
        """BUY signal should be blocked when volume_ratio < volume_surge_min."""
        from src.backtest.trigger_backtest import generate_signals, TriggerConfig

        # Build 60 rows of price data so rolling(20) has values
        n = 60
        dates = pd.date_range("2023-01-01", periods=n, freq="D")
        np.random.seed(42)
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        # Mostly flat volume, with a surge at row 50
        volume = np.full(n, 1_000_000.0)
        volume[50] = 5_000_000.0  # 5x surge

        df = pd.DataFrame({
            "date": dates,
            "ticker": "TEST",
            "open": close - 0.1,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": volume,
        })

        # Use RSI signal type with extreme thresholds to force some BUY signals
        cfg = TriggerConfig(
            signal_type="rsi",
            rsi_period=14,
            rsi_oversold=99.0,   # nearly always triggers BUY
            rsi_overbought=100.0,
            volume_surge_min=2.0,  # require 2x avg volume
            obv_slope_positive=False,
        )

        result = generate_signals(df, cfg)

        # Check that volume_ratio column was created
        assert "volume_ratio" in result.columns

        # For rows where signal_raw == 1 (BUY), check the filter
        buy_raw = result[result["signal_raw"] == 1]
        if len(buy_raw) > 0:
            # Buy signals with low volume ratio should be blocked
            low_vol_buys = buy_raw[buy_raw["volume_ratio"] < 2.0]
            for _, row in low_vol_buys.iterrows():
                assert row["signal"] == 0, (
                    f"BUY should be blocked at index {row.name} "
                    f"(volume_ratio={row['volume_ratio']:.2f} < 2.0)"
                )

    def test_obv_slope_blocks_buy_when_negative(self):
        """BUY signal should be blocked when OBV slope is negative and obv_slope_positive=True."""
        from src.backtest.trigger_backtest import generate_signals, TriggerConfig

        n = 60
        dates = pd.date_range("2023-01-01", periods=n, freq="D")
        # Declining close to produce negative OBV slope
        close = np.linspace(120, 80, n)
        volume = np.full(n, 2_000_000.0)

        df = pd.DataFrame({
            "date": dates,
            "ticker": "TEST",
            "open": close - 0.1,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": volume,
        })

        cfg = TriggerConfig(
            signal_type="rsi",
            rsi_period=14,
            rsi_oversold=99.0,
            rsi_overbought=100.0,
            obv_slope_positive=True,
        )

        result = generate_signals(df, cfg)
        assert "obv_slope_20d" in result.columns

        # Any raw BUY with negative OBV slope should be blocked
        buy_raw = result[(result["signal_raw"] == 1)]
        if len(buy_raw) > 0:
            negative_obv_buys = buy_raw[buy_raw["obv_slope_20d"] <= 0]
            for _, row in negative_obv_buys.iterrows():
                assert row["signal"] == 0, (
                    f"BUY blocked at index {row.name} due to negative OBV slope"
                )

    def test_volume_filter_allows_buy_when_conditions_met(self):
        """BUY signal should pass when volume_ratio >= surge_min and OBV slope > 0."""
        from src.backtest.trigger_backtest import generate_signals, TriggerConfig

        n = 60
        dates = pd.date_range("2023-01-01", periods=n, freq="D")
        # Rising close -> positive OBV slope
        close = np.linspace(80, 150, n)
        # Very high volume throughout -> volume_ratio near 1.0
        volume = np.full(n, 3_000_000.0)

        df = pd.DataFrame({
            "date": dates,
            "ticker": "TEST",
            "open": close - 0.1,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": volume,
        })

        cfg = TriggerConfig(
            signal_type="rsi",
            rsi_period=14,
            rsi_oversold=99.0,
            rsi_overbought=100.0,
            volume_surge_min=0.5,  # low threshold, easily met
            obv_slope_positive=True,
        )

        result = generate_signals(df, cfg)

        # Where OBV slope is positive and volume ratio >= 0.5, BUY should pass
        buy_raw = result[result["signal_raw"] == 1]
        if len(buy_raw) > 0:
            ok_buys = buy_raw[
                (buy_raw["volume_ratio"] >= 0.5) & (buy_raw["obv_slope_20d"] > 0)
            ]
            for _, row in ok_buys.iterrows():
                assert row["signal"] == 1, "BUY should be allowed"


# ---------------------------------------------------------------------------
# k2e.3: Relative Strength (rel_strength_21d)
# ---------------------------------------------------------------------------

class TestRelativeStrength:
    """Tests for calculate_relative_strength in momentum.py."""

    def test_relative_strength_basic(self):
        """Verify RS = stock_return - benchmark_return over lookback period."""
        from src.strategies.momentum import calculate_relative_strength

        # 30 days of stock and benchmark data
        dates = pd.date_range("2023-01-01", periods=30, freq="D")

        # Stock rises 10% over 21 days, benchmark rises 5%
        stock_close = np.linspace(100, 110, 30)
        bench_close = np.linspace(100, 105, 30)

        df = pd.DataFrame({
            "date": dates,
            "ticker": "AAPL",
            "close": stock_close,
        })
        benchmark_df = pd.DataFrame({
            "date": dates,
            "close": bench_close,
        })

        result = calculate_relative_strength(
            df, benchmark_df, lookback_days=21, output_col="rel_strength_21d"
        )

        assert "rel_strength_21d" in result.columns
        # First 21 rows should be NaN (not enough lookback)
        assert result["rel_strength_21d"].iloc[:21].isna().all()
        # Row 21 onward should have values
        valid = result["rel_strength_21d"].dropna()
        assert len(valid) > 0

        # Verify the actual calculation for the last row
        last_idx = len(dates) - 1
        stock_ret = (stock_close[last_idx] - stock_close[last_idx - 21]) / stock_close[last_idx - 21]
        bench_ret = (bench_close[last_idx] - bench_close[last_idx - 21]) / bench_close[last_idx - 21]
        expected_rs = stock_ret - bench_ret
        actual_rs = result["rel_strength_21d"].iloc[last_idx]
        assert abs(actual_rs - expected_rs) < 1e-6

    def test_relative_strength_negative(self):
        """Stock underperforms benchmark -> negative RS."""
        from src.strategies.momentum import calculate_relative_strength

        dates = pd.date_range("2023-01-01", periods=30, freq="D")
        # Stock drops, benchmark rises
        stock_close = np.linspace(100, 90, 30)
        bench_close = np.linspace(100, 110, 30)

        df = pd.DataFrame({"date": dates, "ticker": "BAD", "close": stock_close})
        benchmark_df = pd.DataFrame({"date": dates, "close": bench_close})

        result = calculate_relative_strength(df, benchmark_df, lookback_days=21)
        valid = result["relative_strength"].dropna()
        assert len(valid) > 0
        # All valid values should be negative (stock underperforms)
        assert (valid < 0).all()

    def test_relative_strength_multi_ticker(self):
        """Works with multiple tickers in the dataframe."""
        from src.strategies.momentum import calculate_relative_strength

        dates = pd.date_range("2023-01-01", periods=30, freq="D")
        rows = []
        for ticker, growth in [("AAPL", 1.1), ("MSFT", 0.9)]:
            close = np.linspace(100, 100 * growth, 30)
            for i, d in enumerate(dates):
                rows.append({"date": d, "ticker": ticker, "close": close[i]})

        df = pd.DataFrame(rows)
        bench_close = np.linspace(100, 100, 30)  # flat benchmark
        benchmark_df = pd.DataFrame({"date": dates, "close": bench_close})

        result = calculate_relative_strength(df, benchmark_df, lookback_days=21)
        assert "relative_strength" in result.columns

        # AAPL (rising) should have positive RS, MSFT (falling) negative
        aapl = result[result["ticker"] == "AAPL"]["relative_strength"].dropna()
        msft = result[result["ticker"] == "MSFT"]["relative_strength"].dropna()
        if len(aapl) > 0:
            assert aapl.iloc[-1] > 0
        if len(msft) > 0:
            assert msft.iloc[-1] < 0

    def test_relative_strength_custom_output_col(self):
        """output_col parameter controls the column name."""
        from src.strategies.momentum import calculate_relative_strength

        dates = pd.date_range("2023-01-01", periods=30, freq="D")
        df = pd.DataFrame({
            "date": dates, "ticker": "X", "close": np.linspace(100, 110, 30),
        })
        bench = pd.DataFrame({"date": dates, "close": np.linspace(100, 105, 30)})

        result = calculate_relative_strength(
            df, bench, lookback_days=21, output_col="my_rs"
        )
        assert "my_rs" in result.columns
        assert "relative_strength" not in result.columns


# ---------------------------------------------------------------------------
# k2e.4: VIX Gating
# ---------------------------------------------------------------------------

class TestVIXGating:
    """Tests for VIX-based signal filtering in trigger_backtest.py."""

    def _make_price_df(self, n=60):
        dates = pd.date_range("2023-01-01", periods=n, freq="D")
        close = 100 + np.cumsum(np.random.RandomState(42).randn(n) * 0.5)
        return pd.DataFrame({
            "date": dates,
            "ticker": "TEST",
            "open": close - 0.1,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": np.full(n, 1_000_000.0),
        })

    def test_trigger_config_has_vix_fields(self):
        from src.backtest.trigger_backtest import TriggerConfig

        cfg = TriggerConfig()
        assert cfg.macro_vix_enabled is False
        assert cfg.macro_vix_buy_max == 25.0
        assert cfg.macro_vix_sell_min == 30.0

    def test_vix_blocks_buy_when_high(self):
        """BUY should be blocked when VIX > vix_buy_max."""
        from src.backtest.trigger_backtest import generate_signals, TriggerConfig

        n = 60
        price_df = self._make_price_df(n)
        dates = price_df["date"]

        # VIX = 35 throughout (above buy_max=25)
        vix_df = pd.DataFrame({"date": dates, "close": np.full(n, 35.0)})

        cfg = TriggerConfig(
            signal_type="rsi",
            rsi_period=14,
            rsi_oversold=99.0,  # force BUY signals
            rsi_overbought=100.0,
            macro_vix_enabled=True,
            macro_vix_buy_max=25.0,
            macro_vix_sell_min=30.0,
        )

        result = generate_signals(price_df, cfg, macro_vix_df=vix_df)

        # All raw BUY signals should be blocked
        buy_raw = result[result["signal_raw"] == 1]
        if len(buy_raw) > 0:
            assert (buy_raw["signal"] == 0).all(), (
                "All BUY signals should be blocked when VIX=35 > buy_max=25"
            )

    def test_vix_blocks_sell_when_low(self):
        """SELL should be blocked when VIX < vix_sell_min."""
        from src.backtest.trigger_backtest import generate_signals, TriggerConfig

        n = 60
        price_df = self._make_price_df(n)
        dates = price_df["date"]

        # VIX = 15 throughout (below sell_min=30)
        vix_df = pd.DataFrame({"date": dates, "close": np.full(n, 15.0)})

        cfg = TriggerConfig(
            signal_type="rsi",
            rsi_period=14,
            rsi_oversold=0.0,
            rsi_overbought=1.0,  # force SELL signals
            macro_vix_enabled=True,
            macro_vix_buy_max=25.0,
            macro_vix_sell_min=30.0,
        )

        result = generate_signals(price_df, cfg, macro_vix_df=vix_df)

        # All raw SELL signals should be blocked
        sell_raw = result[result["signal_raw"] == -1]
        if len(sell_raw) > 0:
            assert (sell_raw["signal"] == 0).all(), (
                "All SELL signals should be blocked when VIX=15 < sell_min=30"
            )

    def test_vix_allows_buy_when_low(self):
        """BUY should be allowed when VIX <= vix_buy_max."""
        from src.backtest.trigger_backtest import generate_signals, TriggerConfig

        n = 60
        price_df = self._make_price_df(n)
        dates = price_df["date"]

        # VIX = 15 throughout (below buy_max=25)
        vix_df = pd.DataFrame({"date": dates, "close": np.full(n, 15.0)})

        cfg = TriggerConfig(
            signal_type="rsi",
            rsi_period=14,
            rsi_oversold=99.0,  # force BUY signals
            rsi_overbought=100.0,
            macro_vix_enabled=True,
            macro_vix_buy_max=25.0,
            macro_vix_sell_min=30.0,
        )

        result = generate_signals(price_df, cfg, macro_vix_df=vix_df)

        # Raw BUY signals should NOT be blocked (VIX is low)
        buy_raw = result[result["signal_raw"] == 1]
        if len(buy_raw) > 0:
            assert (buy_raw["signal"] == 1).all(), (
                "BUY signals should be allowed when VIX=15 <= buy_max=25"
            )

    def test_vix_disabled_does_not_filter(self):
        """When macro_vix_enabled=False, VIX data is ignored."""
        from src.backtest.trigger_backtest import generate_signals, TriggerConfig

        n = 60
        price_df = self._make_price_df(n)
        dates = price_df["date"]

        vix_df = pd.DataFrame({"date": dates, "close": np.full(n, 99.0)})

        cfg = TriggerConfig(
            signal_type="rsi",
            rsi_period=14,
            rsi_oversold=99.0,
            rsi_overbought=100.0,
            macro_vix_enabled=False,  # disabled
        )

        result = generate_signals(price_df, cfg, macro_vix_df=vix_df)

        # signal_raw should equal signal (no filtering applied)
        assert (result["signal_raw"] == result["signal"]).all()


# ---------------------------------------------------------------------------
# k2e.5: Overfitting Detection
# ---------------------------------------------------------------------------

class TestOverfittingDetection:
    """Tests for train/test Sharpe ratio overfitting detection in rolling.py."""

    def test_max_train_test_sharpe_ratio_calculation(self):
        """Replicate the overfitting detection logic from rolling.py (lines 648-663).

        Given window_results with known train_sharpe and test_sharpe, verify
        that max_train_test_sharpe_ratio is computed correctly.
        """
        window_results = [
            {"train_sharpe": 2.0, "test_sharpe": 1.0},   # ratio = 2.0
            {"train_sharpe": 3.0, "test_sharpe": 0.5},   # ratio = 6.0
            {"train_sharpe": 1.5, "test_sharpe": 1.5},   # ratio = 1.0
            {"train_sharpe": 4.0, "test_sharpe": -0.5},  # test <= 0, skip
            {"train_sharpe": None, "test_sharpe": 1.0},  # skip
            {"test_sharpe": 1.0},                          # no train_sharpe, skip
        ]

        # Reproduce logic from rolling.py lines 649-657
        train_test_ratios = []
        for w in window_results:
            ts = w.get("test_sharpe")
            tr = w.get("train_sharpe")
            if ts is not None and tr is not None and ts > 0:
                train_test_ratios.append(tr / ts)

        assert len(train_test_ratios) == 3
        max_ratio = float(np.max(train_test_ratios))
        assert max_ratio == 6.0

    def test_overfitting_threshold_warning(self):
        """When max ratio >= threshold, it should be flagged."""
        window_results = [
            {"train_sharpe": 5.0, "test_sharpe": 1.0},  # ratio = 5.0
        ]

        train_test_ratios = []
        for w in window_results:
            ts = w.get("test_sharpe")
            tr = w.get("train_sharpe")
            if ts is not None and tr is not None and ts > 0:
                train_test_ratios.append(tr / ts)

        max_ratio = float(np.max(train_test_ratios))
        overfit_threshold = 2.0
        assert max_ratio >= overfit_threshold

    def test_no_overfitting_when_ratios_low(self):
        """No overfitting warning when all ratios < threshold."""
        window_results = [
            {"train_sharpe": 1.0, "test_sharpe": 1.0},   # ratio = 1.0
            {"train_sharpe": 1.2, "test_sharpe": 1.0},   # ratio = 1.2
        ]

        train_test_ratios = []
        for w in window_results:
            ts = w.get("test_sharpe")
            tr = w.get("train_sharpe")
            if ts is not None and tr is not None and ts > 0:
                train_test_ratios.append(tr / ts)

        max_ratio = float(np.max(train_test_ratios))
        assert max_ratio < 2.0

    def test_empty_ratios_when_no_valid_windows(self):
        """No ratios computed when no windows have both train and test Sharpe > 0."""
        window_results = [
            {"train_sharpe": 1.0, "test_sharpe": -0.5},
            {"train_sharpe": None, "test_sharpe": 1.0},
        ]

        train_test_ratios = []
        for w in window_results:
            ts = w.get("test_sharpe")
            tr = w.get("train_sharpe")
            if ts is not None and tr is not None and ts > 0:
                train_test_ratios.append(tr / ts)

        assert len(train_test_ratios) == 0


# ---------------------------------------------------------------------------
# Tier 1: Feature Importance
# ---------------------------------------------------------------------------

class TestFeatureImportanceExtraction:
    """Tests for feature importance extraction from BacktestResults."""

    def test_get_feature_importance_from_backtest(self):
        """_get_feature_importance_from_backtest returns metrics['feature_importance_gain']."""
        from src.regression.orchestrator import _get_feature_importance_from_backtest
        from src.backtest.rolling import BacktestResults

        importance = {"rsi": 150.0, "macd": 120.0, "volume": 80.0}
        bt = BacktestResults(
            portfolio_returns=pd.Series(dtype=float),
            benchmark_returns=pd.Series(dtype=float),
            positions=pd.DataFrame(),
            metrics={"feature_importance_gain": importance, "sharpe_ratio": 1.0},
            window_results=[],
        )

        result = _get_feature_importance_from_backtest(bt)
        assert result == importance

    def test_get_feature_importance_empty_when_missing(self):
        """Returns empty dict when feature_importance_gain is not in metrics."""
        from src.regression.orchestrator import _get_feature_importance_from_backtest
        from src.backtest.rolling import BacktestResults

        bt = BacktestResults(
            portfolio_returns=pd.Series(dtype=float),
            benchmark_returns=pd.Series(dtype=float),
            positions=pd.DataFrame(),
            metrics={"sharpe_ratio": 1.0},
            window_results=[],
        )

        result = _get_feature_importance_from_backtest(bt)
        assert result == {}


class TestFeatureImportanceAggregation:
    """Tests for per-window feature importance aggregation in rolling.py."""

    def test_gain_aggregation_mean_and_std(self):
        """Replicate the gain aggregation logic from rolling.py (lines 668-672).

        Per-window feature_importance_gain dicts are averaged into
        metrics['feature_importance_gain'] and metrics['feature_importance_gain_std'].
        """
        window_results = [
            {"feature_importance_gain": {"rsi": 100.0, "macd": 200.0, "vol": 50.0}},
            {"feature_importance_gain": {"rsi": 120.0, "macd": 180.0, "vol": 70.0}},
            {"feature_importance_gain": {"rsi": 110.0, "macd": 190.0, "vol": 60.0}},
        ]

        # Reproduce aggregation
        _gain_dicts = [
            w["feature_importance_gain"]
            for w in window_results
            if "feature_importance_gain" in w
        ]
        assert len(_gain_dicts) == 3

        _gain_df = pd.DataFrame(_gain_dicts)
        mean_dict = _gain_df.mean().to_dict()
        std_dict = _gain_df.std().to_dict()

        assert abs(mean_dict["rsi"] - 110.0) < 1e-6
        assert abs(mean_dict["macd"] - 190.0) < 1e-6
        assert abs(mean_dict["vol"] - 60.0) < 1e-6

        # std of [100, 120, 110] = 10.0 (sample std)
        assert abs(std_dict["rsi"] - 10.0) < 1e-6

    def test_gain_aggregation_skips_windows_without_importance(self):
        """Windows without feature_importance_gain are skipped."""
        window_results = [
            {"feature_importance_gain": {"rsi": 100.0}},
            {"ic": 0.05},  # no feature_importance_gain
            {"feature_importance_gain": {"rsi": 200.0}},
        ]

        _gain_dicts = [
            w["feature_importance_gain"]
            for w in window_results
            if "feature_importance_gain" in w
        ]
        assert len(_gain_dicts) == 2
        _gain_df = pd.DataFrame(_gain_dicts)
        assert abs(_gain_df.mean()["rsi"] - 150.0) < 1e-6

    def test_marginal_ic_aggregation(self):
        """Per-window marginal_ic dicts are averaged similarly."""
        window_results = [
            {"marginal_ic": {"rsi": 0.05, "macd": 0.03}},
            {"marginal_ic": {"rsi": 0.07, "macd": 0.01}},
        ]

        _mic_dicts = [
            w["marginal_ic"] for w in window_results if "marginal_ic" in w
        ]
        _mic_df = pd.DataFrame(_mic_dicts)
        mean_mic = _mic_df.mean().to_dict()
        assert abs(mean_mic["rsi"] - 0.06) < 1e-6
        assert abs(mean_mic["macd"] - 0.02) < 1e-6


class TestFeatureContribution:
    """Tests for compute_feature_contribution in regression/metrics.py."""

    def test_marginal_contribution_basic(self):
        """Marginal contribution = current step metrics - previous step metrics."""
        from src.regression.metrics import compute_feature_contribution

        prev_metrics = {
            "sharpe_ratio": 0.5,
            "mean_rank_ic": 0.03,
            "excess_return": 0.02,
            "hit_rate": 0.55,
        }
        step_metrics = {
            "sharpe_ratio": 0.7,
            "mean_rank_ic": 0.05,
            "excess_return": 0.04,
            "hit_rate": 0.58,
        }
        importance = {"rsi": 100.0, "macd": 200.0, "vol": 50.0}

        result = compute_feature_contribution(
            step_metrics, prev_metrics, importance, "macd",
            feature_columns=["macd"],
        )

        assert abs(result["marginal_sharpe"] - 0.2) < 1e-6
        assert abs(result["marginal_rank_ic"] - 0.02) < 1e-6
        assert abs(result["marginal_excess_return"] - 0.02) < 1e-6
        assert abs(result["marginal_hit_rate"] - 0.03) < 1e-6

    def test_feature_importance_pct(self):
        """feature_importance_pct = feature_imp / total_importance."""
        from src.regression.metrics import compute_feature_contribution

        importance = {"rsi": 100.0, "macd": 200.0, "vol": 50.0}
        # total = 350

        result = compute_feature_contribution(
            {"sharpe_ratio": 1.0, "mean_rank_ic": 0.05, "excess_return": 0.0, "hit_rate": 0.5},
            {"sharpe_ratio": 0.5, "mean_rank_ic": 0.03, "excess_return": 0.0, "hit_rate": 0.5},
            importance,
            "macd",
            feature_columns=["macd"],
        )

        expected_pct = 200.0 / 350.0
        assert abs(result["feature_importance_pct"] - expected_pct) < 1e-6

    def test_feature_importance_rank(self):
        """feature_importance_rank: count of column importances > feature_imp + 1."""
        from src.regression.metrics import compute_feature_contribution

        importance = {"rsi": 100.0, "macd": 200.0, "vol": 50.0}
        # macd=200 is the highest -> rank 1

        result = compute_feature_contribution(
            {"sharpe_ratio": 1.0, "mean_rank_ic": 0.05, "excess_return": 0.0, "hit_rate": 0.5},
            {"sharpe_ratio": 0.5, "mean_rank_ic": 0.03, "excess_return": 0.0, "hit_rate": 0.5},
            importance,
            "macd",
            feature_columns=["macd"],
        )
        assert result["feature_importance_rank"] == 1

    def test_feature_importance_multi_column_sum(self):
        """When feature_columns has multiple columns, importance is summed."""
        from src.regression.metrics import compute_feature_contribution

        importance = {
            "macd": 80.0,
            "macd_signal": 60.0,
            "macd_histogram": 40.0,
            "rsi": 100.0,
        }
        # macd cols sum = 80 + 60 + 40 = 180; total = 280

        result = compute_feature_contribution(
            {"sharpe_ratio": 1.0, "mean_rank_ic": 0.05, "excess_return": 0.0, "hit_rate": 0.5},
            {"sharpe_ratio": 0.5, "mean_rank_ic": 0.03, "excess_return": 0.0, "hit_rate": 0.5},
            importance,
            "macd",
            feature_columns=["macd", "macd_signal", "macd_histogram"],
        )

        expected_pct = 180.0 / 280.0
        assert abs(result["feature_importance_pct"] - expected_pct) < 1e-6

    def test_baseline_contribution_no_previous(self):
        """When prev_metrics is None (baseline), metrics are returned directly."""
        from src.regression.metrics import compute_feature_contribution

        result = compute_feature_contribution(
            {"sharpe_ratio": 0.5, "mean_rank_ic": 0.03, "excess_return": 0.02, "hit_rate": 0.55},
            None,
            {},
            "BASELINE",
        )
        assert result["marginal_sharpe"] == 0.5
        assert result["marginal_rank_ic"] == 0.03
        assert result["feature_importance_pct"] == 0.0
        assert result["feature_importance_rank"] == 0

    def test_zero_importance(self):
        """When all importances are zero, pct should be 0."""
        from src.regression.metrics import compute_feature_contribution

        result = compute_feature_contribution(
            {"sharpe_ratio": 1.0, "mean_rank_ic": 0.05, "excess_return": 0.0, "hit_rate": 0.5},
            {"sharpe_ratio": 0.5, "mean_rank_ic": 0.03, "excess_return": 0.0, "hit_rate": 0.5},
            {},
            "rsi",
        )
        assert result["feature_importance_pct"] == 0.0
        assert result["feature_importance_rank"] == 0


# ---------------------------------------------------------------------------
# Guard metric checks (related to k2e.5 and Tier 1)
# ---------------------------------------------------------------------------

class TestGuardMetrics:
    """Tests for guard metric violation detection."""

    def test_check_guard_max_drawdown_violation(self):
        from src.regression.metrics import check_guard_metrics

        metrics = {"max_drawdown": -0.40}  # worse than -0.30 threshold
        violations = check_guard_metrics(metrics)
        names = [v["metric"] for v in violations]
        assert "max_drawdown" in names

    def test_check_guard_turnover_violation(self):
        from src.regression.metrics import check_guard_metrics

        metrics = {"turnover": 0.95}  # above 0.80 threshold
        violations = check_guard_metrics(metrics)
        names = [v["metric"] for v in violations]
        assert "turnover" in names

    def test_check_guard_overfitting_violation(self):
        from src.regression.metrics import check_guard_metrics

        metrics = {"train_test_sharpe_ratio": 3.0}  # above 2.5 threshold
        violations = check_guard_metrics(metrics)
        names = [v["metric"] for v in violations]
        assert "train_test_sharpe_ratio" in names

    def test_check_guard_no_violations(self):
        from src.regression.metrics import check_guard_metrics

        metrics = {
            "max_drawdown": -0.10,
            "turnover": 0.30,
            "train_test_sharpe_ratio": 1.5,
            "ic_pct_positive": 0.70,
        }
        violations = check_guard_metrics(metrics)
        assert len(violations) == 0
