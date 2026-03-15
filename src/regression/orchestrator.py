"""Regression test orchestrator.

Orchestrates sequential feature regression testing: adds features one at a time,
tunes parameters, runs backtests, computes metrics, and logs results.
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from ..config.config import BacktestConfig, ModelConfig
from ..backtest.rolling import run_walk_forward_backtest, BacktestResults
from .feature_registry import FeatureRegistry, DEFAULT_BASELINE, DEFAULT_FEATURE_ORDER
from .metrics import (
    compute_extended_metrics,
    compute_marginal_significance,
    compute_feature_contribution,
    check_guard_metrics,
)
from .database import RegressionDatabase
from .tuning import FeatureParamTuner, ModelParamTuner

logger = logging.getLogger(__name__)


@dataclass
class RegressionTestConfig:
    """Configuration for a full regression test."""
    name: str = "Regression Test"
    description: str = ""
    baseline_features: List[str] = field(
        default_factory=lambda: list(DEFAULT_BASELINE)
    )
    features_to_test: List[str] = field(
        default_factory=lambda: list(DEFAULT_FEATURE_ORDER)
    )
    tune_on_add: bool = True
    tune_model_params: bool = False
    tuning_trials: int = 30
    model_tuning_trials: int = 50
    objective_metric: str = "mean_rank_ic"
    db_path: str = "data/runs.db"


@dataclass
class RegressionStepResult:
    """Results from one step of the regression test."""
    step_number: int
    feature_added: str
    feature_set: List[str]
    feature_columns: List[str]
    metrics: Dict[str, float]
    window_ics: List[Optional[float]]
    window_rank_ics: List[Optional[float]]
    window_test_sharpes: List[Optional[float]]
    feature_importance: Dict[str, float]
    marginal_metrics: Optional[Dict[str, float]] = None
    significance_tests: Optional[Dict[str, Dict[str, Any]]] = None
    guard_violations: Optional[List[Dict]] = None
    tuned_params: Optional[Dict[str, Any]] = None
    model_config_used: Optional[Dict[str, Any]] = None
    run_id: Optional[str] = None
    duration_seconds: float = 0.0


def _generate_regression_id(name: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    h = hashlib.md5(f"{name}{ts}".encode()).hexdigest()[:8]
    return f"reg_{ts}_{h}"


def _extract_window_data(window_results: List[Dict]) -> Dict[str, List]:
    """Extract per-window arrays from window_results."""
    return {
        "ics": [w.get("ic") for w in window_results if w.get("ic") is not None],
        "rank_ics": [w.get("rank_ic") for w in window_results if w.get("rank_ic") is not None],
        "test_sharpes": [w.get("test_sharpe") for w in window_results if w.get("test_sharpe") is not None],
        "train_sharpes": [w.get("train_sharpe") for w in window_results if w.get("train_sharpe") is not None],
    }


def _get_feature_importance_from_backtest(
    backtest_results,
) -> Dict[str, float]:
    """Extract averaged feature importance from walk-forward backtest results.

    Uses the per-window LightGBM gain-based importances already computed by
    _mp_process_window and aggregated in BacktestResults.metrics.  Falls back
    to an empty dict if the backtest did not produce importance data.
    """
    return backtest_results.metrics.get('feature_importance_gain', {})


class RegressionOrchestrator:
    """Orchestrates sequential feature regression testing."""

    def __init__(
        self,
        config: RegressionTestConfig,
        registry: FeatureRegistry,
        training_data: pd.DataFrame,
        benchmark_data: pd.DataFrame,
        price_data: pd.DataFrame,
        backtest_config: Optional[BacktestConfig] = None,
        model_config: Optional[ModelConfig] = None,
        recompute_features_fn: Optional[Callable] = None,
    ):
        """
        Args:
            config: Regression test configuration.
            registry: Feature registry.
            training_data: Full training dataset with ALL features pre-computed.
            benchmark_data: Benchmark price data.
            price_data: Stock price data.
            backtest_config: Backtest configuration.
            model_config: Model configuration.
            recompute_features_fn: Optional function to recompute features with
                new parameters. Signature: (param_dict) -> pd.DataFrame.
                If None, tuning of feature params is disabled.
        """
        self.config = config
        self.registry = registry
        self.training_data = training_data
        self.benchmark_data = benchmark_data
        self.price_data = price_data
        self.backtest_config = backtest_config or BacktestConfig()
        self.model_config = model_config or ModelConfig()
        self.recompute_features_fn = recompute_features_fn
        self.db = RegressionDatabase(config.db_path)
        self.results: List[RegressionStepResult] = []
        self.regression_id: Optional[str] = None

    def run(self, verbose: bool = True) -> List[RegressionStepResult]:
        """Execute the full regression test sequence.

        Returns list of RegressionStepResult for each step.
        """
        start_time = time.time()
        self.regression_id = _generate_regression_id(self.config.name)

        if verbose:
            print(f"\n{'='*60}")
            print(f"Regression Test: {self.config.name}")
            print(f"ID: {self.regression_id}")
            print(f"Baseline: {self.config.baseline_features}")
            print(f"Features to test: {self.config.features_to_test}")
            print(f"Tuning: {'ON' if self.config.tune_on_add else 'OFF'}")
            print(f"{'='*60}\n")

        # Create regression test in DB
        self.db.create_regression_test(
            regression_id=self.regression_id,
            name=self.config.name,
            description=self.config.description,
            config=asdict(self.config),
            baseline_features=self.config.baseline_features,
            features_to_test=self.config.features_to_test,
        )

        # Step 0: Baseline
        if verbose:
            print(f"Step 0: BASELINE {self.config.baseline_features}")
        baseline_result = self._run_step(
            step_number=0,
            feature_added="BASELINE",
            cumulative_features=list(self.config.baseline_features),
            previous_result=None,
            verbose=verbose,
        )
        self.results.append(baseline_result)

        # Steps 1..N: Add features one at a time
        cumulative_features = list(self.config.baseline_features)
        for i, feature_name in enumerate(self.config.features_to_test, start=1):
            if verbose:
                print(f"\nStep {i}: +{feature_name}")

            # Resolve dependencies
            deps = self.registry.resolve_dependencies([feature_name])
            new_features = [f for f in deps if f not in cumulative_features]
            if not new_features:
                if verbose:
                    print(f"  Already included, skipping")
                continue

            cumulative_features.extend(new_features)

            # Tune feature params if enabled
            tuned_params = None
            if (
                self.config.tune_on_add
                and self.recompute_features_fn is not None
            ):
                tunable = self.registry.get_tunable_params(feature_name)
                if tunable:
                    tuned_params = self._tune_feature(
                        feature_name, cumulative_features, verbose
                    )

            step_result = self._run_step(
                step_number=i,
                feature_added=feature_name,
                cumulative_features=cumulative_features,
                previous_result=self.results[-1],
                tuned_params=tuned_params,
                verbose=verbose,
            )
            self.results.append(step_result)

        # Optional: tune model hyperparams at the end
        if self.config.tune_model_params:
            if verbose:
                print(f"\nStep {len(self.results)}: MODEL TUNING")
            best_model_config = self._tune_model(cumulative_features, verbose)
            if best_model_config:
                model_step = self._run_step(
                    step_number=len(self.results),
                    feature_added="MODEL_TUNING",
                    cumulative_features=cumulative_features,
                    previous_result=self.results[-1],
                    model_config_override=best_model_config,
                    verbose=verbose,
                )
                self.results.append(model_step)

        # Finalize
        duration = time.time() - start_time
        self._finalize(duration, verbose)

        return self.results

    def _run_step(
        self,
        step_number: int,
        feature_added: str,
        cumulative_features: List[str],
        previous_result: Optional[RegressionStepResult],
        tuned_params: Optional[Dict] = None,
        model_config_override: Optional[ModelConfig] = None,
        verbose: bool = True,
    ) -> RegressionStepResult:
        """Run a single regression step."""
        step_start = time.time()

        # Resolve to column names
        feature_columns = self.registry.resolve_columns(cumulative_features)

        # Filter to columns that exist in training data
        available_cols = [c for c in feature_columns if c in self.training_data.columns]
        if not available_cols:
            logger.warning(f"No columns available for features {cumulative_features}")
            available_cols = [
                c for c in self.training_data.columns
                if c not in {"date", "ticker", "target", "open", "high", "low", "close", "volume"}
                and not c.startswith("_")
            ]

        if verbose:
            print(f"  Features: {len(available_cols)} columns")

        # Run backtest
        model_config = model_config_override or self.model_config
        try:
            bt_results = run_walk_forward_backtest(
                training_data=self.training_data,
                benchmark_data=self.benchmark_data,
                price_data=self.price_data,
                feature_cols=available_cols,
                config=self.backtest_config,
                model_config=model_config,
                verbose=False,
            )
        except Exception as e:
            logger.error(f"  Backtest failed: {e}")
            # Return empty result
            return RegressionStepResult(
                step_number=step_number,
                feature_added=feature_added,
                feature_set=cumulative_features,
                feature_columns=available_cols,
                metrics={"sharpe_ratio": 0.0, "mean_rank_ic": 0.0},
                window_ics=[], window_rank_ics=[], window_test_sharpes=[],
                feature_importance={},
                duration_seconds=time.time() - step_start,
            )

        # Compute extended metrics
        window_data = _extract_window_data(bt_results.window_results)
        metrics = compute_extended_metrics(
            bt_results.metrics,
            bt_results.window_results,
            bt_results.portfolio_returns,
        )

        # Feature importance
        importance = _get_feature_importance_from_backtest(bt_results)

        # Marginal metrics
        marginal = None
        significance = None
        if previous_result is not None:
            # Resolve columns for the added feature so importance is summed
            # across all columns belonging to it (e.g. macd -> macd, macd_signal, macd_histogram)
            added_cols = self.registry.resolve_columns([feature_added])
            added_cols = [c for c in added_cols if c in available_cols]
            marginal = compute_feature_contribution(
                metrics, previous_result.metrics, importance, feature_added,
                feature_columns=added_cols,
            )

            # Statistical significance
            significance = compute_marginal_significance(
                baseline_window_rank_ics=previous_result.window_rank_ics,
                variant_window_rank_ics=window_data["rank_ics"],
                baseline_window_test_sharpes=previous_result.window_test_sharpes,
                variant_window_test_sharpes=window_data["test_sharpes"],
                baseline_sharpe=previous_result.metrics.get("sharpe_ratio", 0.0),
                variant_sharpe=metrics.get("sharpe_ratio", 0.0),
            )

        # Guard metric check
        guard_violations = check_guard_metrics(metrics)
        if guard_violations and verbose:
            for v in guard_violations:
                print(f"  GUARD VIOLATION: {v['message']}")

        duration = time.time() - step_start

        if verbose:
            print(f"  Sharpe: {metrics.get('sharpe_ratio', 0):.4f}", end="")
            print(f"  Rank IC: {metrics.get('mean_rank_ic', 0):.4f}", end="")
            if marginal:
                print(
                    f"  (delta Sharpe: {marginal.get('marginal_sharpe', 0):+.4f},"
                    f" delta IC: {marginal.get('marginal_rank_ic', 0):+.4f})",
                    end="",
                )
            sig_flag = ""
            if significance and "rank_ic_paired_ttest" in significance:
                p = significance["rank_ic_paired_ttest"].get("p_value", 1.0)
                sig_flag = " *" if p < 0.05 else ""
            print(f"{sig_flag}  [{duration:.1f}s]")

        result = RegressionStepResult(
            step_number=step_number,
            feature_added=feature_added,
            feature_set=cumulative_features,
            feature_columns=available_cols,
            metrics=metrics,
            window_ics=window_data["ics"],
            window_rank_ics=window_data["rank_ics"],
            window_test_sharpes=window_data["test_sharpes"],
            feature_importance=importance,
            marginal_metrics=marginal,
            significance_tests=significance,
            guard_violations=guard_violations,
            tuned_params=tuned_params,
            model_config_used=asdict(model_config) if model_config_override else None,
            duration_seconds=duration,
        )

        # Store in database
        rank_ic_p = None
        sharpe_p = None
        is_sig = False
        if significance:
            if "rank_ic_paired_ttest" in significance:
                rank_ic_p = significance["rank_ic_paired_ttest"].get("p_value")
                is_sig = significance["rank_ic_paired_ttest"].get("significant", False)
            if "sharpe_paired_ttest" in significance:
                sharpe_p = significance["sharpe_paired_ttest"].get("p_value")

        self.db.add_regression_step(
            regression_id=self.regression_id,
            step_number=step_number,
            feature_added=feature_added,
            feature_set=cumulative_features,
            feature_columns=available_cols,
            metrics=metrics,
            marginal_metrics=marginal,
            significance=significance,
            feature_importance=importance,
            window_ics=window_data["ics"],
            window_rank_ics=window_data["rank_ics"],
            window_test_sharpes=window_data["test_sharpes"],
            tuned_params=tuned_params,
            model_config=asdict(model_config) if model_config_override else None,
            duration_seconds=duration,
        )

        # Store feature contribution
        if feature_added != "BASELINE" and marginal:
            self.db.add_feature_contribution(
                feature_name=feature_added,
                regression_id=self.regression_id,
                marginal_sharpe=marginal.get("marginal_sharpe"),
                marginal_rank_ic=marginal.get("marginal_rank_ic"),
                marginal_excess_return=marginal.get("marginal_excess_return"),
                feature_importance_pct=marginal.get("feature_importance_pct"),
                rank_ic_p_value=rank_ic_p,
                sharpe_p_value=sharpe_p,
                is_significant=is_sig,
                step_number=step_number,
                total_features_at_step=len(available_cols),
            )

        return result

    def _tune_feature(
        self,
        feature_name: str,
        cumulative_features: List[str],
        verbose: bool,
    ) -> Optional[Dict[str, Any]]:
        """Tune a feature's parameters."""
        if verbose:
            print(f"  Tuning {feature_name} params ({self.config.tuning_trials} trials)...")

        feature_columns = self.registry.resolve_columns(cumulative_features)
        available_cols = [c for c in feature_columns if c in self.training_data.columns]

        tuner = FeatureParamTuner(
            run_backtest_fn=run_walk_forward_backtest,
            training_data=self.training_data,
            benchmark_data=self.benchmark_data,
            price_data=self.price_data,
            base_feature_columns=available_cols,
            backtest_config=self.backtest_config,
            model_config=self.model_config,
        )

        best_params, best_val = tuner.tune(
            feature_name=feature_name,
            registry=self.registry,
            recompute_fn=self.recompute_features_fn,
            n_calls=self.config.tuning_trials,
            objective_metric=self.config.objective_metric,
        )

        if verbose and best_params:
            print(f"  Best params: {best_params} ({self.config.objective_metric}={best_val:.6f})")

        return best_params if best_params else None

    def _tune_model(
        self,
        cumulative_features: List[str],
        verbose: bool,
    ) -> Optional[ModelConfig]:
        """Tune model hyperparameters."""
        if verbose:
            print(f"  Tuning LightGBM hyperparams ({self.config.model_tuning_trials} trials)...")

        feature_columns = self.registry.resolve_columns(cumulative_features)
        available_cols = [c for c in feature_columns if c in self.training_data.columns]

        tuner = ModelParamTuner()
        best_config, best_val = tuner.tune(
            run_backtest_fn=run_walk_forward_backtest,
            training_data=self.training_data,
            feature_columns=available_cols,
            benchmark_data=self.benchmark_data,
            price_data=self.price_data,
            backtest_config=self.backtest_config,
            n_calls=self.config.model_tuning_trials,
            objective_metric=self.config.objective_metric,
        )

        if verbose:
            print(f"  Best model: {best_config.params}")

        return best_config

    def _finalize(self, duration: float, verbose: bool) -> None:
        """Finalize the regression test and compute summary."""
        if not self.results:
            return

        # Find best feature by marginal Sharpe
        best_feature = None
        best_marginal = float("-inf")
        for r in self.results:
            if r.marginal_metrics and r.feature_added != "BASELINE":
                ms = r.marginal_metrics.get("marginal_sharpe", 0.0)
                if ms > best_marginal:
                    best_marginal = ms
                    best_feature = r.feature_added

        final = self.results[-1]
        self.db.complete_regression_test(
            regression_id=self.regression_id,
            total_steps=len(self.results),
            best_feature=best_feature,
            best_marginal_sharpe=best_marginal if best_marginal > float("-inf") else None,
            final_sharpe=final.metrics.get("sharpe_ratio"),
            final_rank_ic=final.metrics.get("mean_rank_ic"),
            duration_seconds=duration,
        )

        if verbose:
            print(f"\n{'='*60}")
            print(f"REGRESSION TEST COMPLETE")
            print(f"  ID: {self.regression_id}")
            print(f"  Steps: {len(self.results)}")
            print(f"  Baseline Sharpe: {self.results[0].metrics.get('sharpe_ratio', 0):.4f}")
            print(f"  Final Sharpe: {final.metrics.get('sharpe_ratio', 0):.4f}")
            print(f"  Best feature: {best_feature} (+{best_marginal:.4f} Sharpe)")
            print(f"  Duration: {duration:.1f}s")
            print(f"{'='*60}\n")
