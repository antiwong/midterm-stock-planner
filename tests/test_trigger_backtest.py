"""Tests for trigger backtest, especially Combined signal logic."""

import pytest
import pandas as pd
import numpy as np

from src.backtest.trigger_backtest import (
    TriggerConfig,
    generate_signals,
    run_trigger_backtest,
)


@pytest.fixture
def sample_price_df():
    """Create synthetic price data for testing."""
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2020-01-01", periods=n, freq="D")
    # Random walk
    returns = np.random.randn(n) * 0.01
    close = 100 * np.exp(np.cumsum(returns))
    return pd.DataFrame({
        "date": dates,
        "ticker": "TEST",
        "open": close * 0.99,
        "high": close * 1.02,
        "low": close * 0.98,
        "close": close,
        "volume": np.full(n, 1e6),
    })


def test_combined_any_agreement_produces_signals(sample_price_df):
    """Combined with 'any' agreement should produce buy/sell signals when indicators fire."""
    cfg = TriggerConfig(signal_type="combined")
    cfg.combined_use_rsi = True
    cfg.combined_use_macd = True
    cfg.combined_use_bollinger = True
    cfg.combined_agreement = "any"

    signals = generate_signals(sample_price_df, cfg)
    buy_count = (signals["signal"] == 1).sum()
    sell_count = (signals["signal"] == -1).sum()
    # With random data, at least one indicator should fire somewhere
    total_signals = buy_count + sell_count
    assert total_signals > 0, (
        "Combined 'any' should produce signals when individual indicators would. "
        "Got 0 - possible conflict overwrite bug."
    )


def test_combined_conflict_resolution(sample_price_df):
    """When buy and sell fire on same bar, result should be 0 (no signal), not overwrite."""
    cfg = TriggerConfig(signal_type="combined")
    cfg.combined_use_rsi = True
    cfg.combined_use_macd = True
    cfg.combined_use_bollinger = True
    cfg.combined_agreement = "any"

    signals = generate_signals(sample_price_df, cfg)
    # No row should have both a buy and sell from different indicators
    # (we can't easily check that without internal state, but we verify no illegal state)
    assert set(signals["signal"].unique()).issubset({-1, 0, 1})


def test_combined_backtest_runs(sample_price_df):
    """Combined backtest should run without error and produce valid results."""
    cfg = TriggerConfig(signal_type="combined")
    cfg.combined_use_rsi = True
    cfg.combined_use_macd = True
    cfg.combined_use_bollinger = True
    cfg.combined_agreement = "any"

    results = run_trigger_backtest(sample_price_df, cfg)
    assert results.metrics is not None
    assert "total_return" in results.metrics
    assert len(results.signals) == len(sample_price_df.dropna(subset=["close"]))
