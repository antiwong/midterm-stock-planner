"""Regression testing framework for systematic feature evaluation.

Adds features one at a time to a baseline, measures marginal contribution,
tunes parameters via Bayesian optimization, and reports results with
statistical significance tests.
"""

from .feature_registry import FeatureRegistry, FeatureSpec, FeatureGroup, FeatureSet
from .metrics import (
    MetricClassification,
    METRICS_REGISTRY,
    compute_extended_metrics,
    compute_marginal_significance,
    compute_feature_contribution,
)
from .orchestrator import RegressionOrchestrator, RegressionTestConfig, RegressionStepResult

__all__ = [
    "FeatureRegistry",
    "FeatureSpec",
    "FeatureGroup",
    "FeatureSet",
    "MetricClassification",
    "METRICS_REGISTRY",
    "compute_extended_metrics",
    "compute_marginal_significance",
    "compute_feature_contribution",
    "RegressionOrchestrator",
    "RegressionTestConfig",
    "RegressionStepResult",
]
