"""Tests for src/risk/complexity.py."""

import pytest
import pandas as pd

from src.risk.complexity import (
    compute_config_complexity,
    compute_factor_redundancy,
    compute_penalty,
    exceeds_thresholds,
)


def test_compute_config_complexity_dict():
    """Param vector (dict) produces non-negative complexity."""
    params = {
        "train_years": 2.0,
        "test_years": 0.5,
        "step_value": 1.0,
        "step_unit": "years",
        "rebalance_freq": "MS",
        "top_n": 10,
        "top_pct": 0.1,
        "transaction_cost": 0.001,
    }
    c = compute_config_complexity(params)
    assert c >= 0
    assert isinstance(c, float)


def test_compute_config_complexity_simple_vs_complex():
    """Simpler config (fewer params) has lower or equal complexity."""
    simple = {"train_years": 1.0, "test_years": 0.25}
    full = {
        "train_years": 2.0,
        "test_years": 0.5,
        "step_value": 1.0,
        "step_unit": "years",
        "rebalance_freq": "2W",
        "top_n": 10,
        "top_pct": 0.1,
        "transaction_cost": 0.001,
    }
    c_simple = compute_config_complexity(simple)
    c_full = compute_config_complexity(full)
    assert c_full >= c_simple


def test_compute_factor_redundancy_empty():
    """Empty or minimal matrix returns 0."""
    assert compute_factor_redundancy(pd.DataFrame()) == 0.0
    df = pd.DataFrame({"model_score": [50], "value_score": [50]})
    assert compute_factor_redundancy(df) == 0.0


def test_compute_factor_redundancy_high_correlation():
    """High correlation between columns yields high redundancy."""
    # Perfect correlation
    df = pd.DataFrame({
        "model_score": [10, 20, 30, 40, 50],
        "value_score": [10, 20, 30, 40, 50],
        "quality_score": [10, 20, 30, 40, 50],
    })
    r = compute_factor_redundancy(df)
    assert r >= 0.99


def test_compute_factor_redundancy_low_correlation():
    """Low correlation yields low redundancy."""
    df = pd.DataFrame({
        "model_score": [10, 20, 30, 40, 50],
        "value_score": [50, 40, 30, 20, 10],
        "quality_score": [30, 30, 30, 30, 30],
    })
    r = compute_factor_redundancy(df)
    assert 0 <= r <= 1


def test_compute_penalty():
    """Penalty increases with excess complexity/redundancy."""
    p0 = compute_penalty(3.0, 0.5, complexity_threshold=5.0, redundancy_threshold=0.8)
    p1 = compute_penalty(7.0, 0.5, complexity_threshold=5.0, redundancy_threshold=0.8)
    p2 = compute_penalty(3.0, 0.9, complexity_threshold=5.0, redundancy_threshold=0.8)
    assert p0 == 0
    assert p1 > 0
    assert p2 > 0


def test_exceeds_thresholds():
    """Reject when above thresholds."""
    assert not exceeds_thresholds(3.0, 0.5, max_complexity=8.0, max_redundancy=0.9)
    assert exceeds_thresholds(10.0, 0.5, max_complexity=8.0, max_redundancy=0.9)
    assert exceeds_thresholds(3.0, 0.95, max_complexity=8.0, max_redundancy=0.9)
