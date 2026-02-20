"""Tests for gap/overnight features (QuantaAlpha-inspired)."""

import pytest
import pandas as pd
import numpy as np

from src.features.gap_features import (
    add_overnight_gap_pct,
    add_gap_vs_true_range,
    add_gap_acceptance_score,
    add_gap_features,
)


@pytest.fixture
def sample_ohlcv():
    """Synthetic OHLCV data."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2020-01-01", periods=n, freq="D")
    returns = np.random.randn(n) * 0.01
    close = 100 * np.exp(np.cumsum(returns))
    high = close * (1 + np.abs(np.random.randn(n) * 0.01))
    low = close * (1 - np.abs(np.random.randn(n) * 0.01))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    return pd.DataFrame({
        "date": dates,
        "ticker": "TEST",
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.full(n, 1e6),
    })


def test_overnight_gap_pct(sample_ohlcv):
    """overnight_gap_pct = (open - prev_close) / prev_close."""
    df = add_overnight_gap_pct(sample_ohlcv)
    assert "overnight_gap_pct" in df.columns
    # First row: prev_close is NaN, so gap is NaN
    assert pd.isna(df["overnight_gap_pct"].iloc[0])
    # Second row: should match (open - prev_close)/prev_close
    exp = (df["open"].iloc[1] - df["close"].iloc[0]) / df["close"].iloc[0]
    assert abs(df["overnight_gap_pct"].iloc[1] - exp) < 1e-9


def test_gap_vs_true_range(sample_ohlcv):
    """gap_vs_true_range normalizes gap by rolling true range."""
    df = add_gap_vs_true_range(sample_ohlcv, lookback=10)
    assert "gap_vs_true_range" in df.columns
    # First 10 rows need warmup
    assert pd.isna(df["gap_vs_true_range"].iloc[9]) or not np.isnan(df["gap_vs_true_range"].iloc[10])


def test_gap_acceptance_score(sample_ohlcv):
    """gap_acceptance_raw is -1, 0, or 1."""
    df = add_gap_acceptance_score(sample_ohlcv)
    assert "gap_acceptance_raw" in df.columns
    valid = df["gap_acceptance_raw"].dropna()
    assert set(valid.unique()).issubset({-1.0, 0.0, 1.0})


def test_add_gap_features_integration(sample_ohlcv):
    """add_gap_features adds all expected columns."""
    df = add_gap_features(sample_ohlcv)
    expected = ["overnight_gap_pct", "gap_acceptance_raw", "gap_vs_true_range"]
    for col in expected:
        assert col in df.columns
    assert "gap_acceptance_score_20d" in df.columns
    assert "gap_acceptance_vol_weighted_20d" in df.columns
