"""Parameter tuning for regression testing.

Bayesian optimization for feature-specific parameters and model hyperparameters.
Uses skopt (scikit-optimize) with Expected Improvement acquisition.
"""

import logging
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..config.config import BacktestConfig, ModelConfig
from .feature_registry import FeatureRegistry, TunableParam

logger = logging.getLogger(__name__)


def _build_search_space(params: Dict[str, TunableParam]):
    """Build skopt search space from TunableParam definitions."""
    from skopt.space import Integer, Real

    dimensions = []
    names = []
    for name, p in params.items():
        names.append(name)
        if p.type == "int":
            dimensions.append(Integer(int(p.min_val), int(p.max_val), name=name))
        elif p.type == "float":
            dimensions.append(
                Real(p.min_val, p.max_val, name=name, prior=p.prior)
            )
    return dimensions, names


class FeatureParamTuner:
    """Bayesian optimization for feature-specific parameters.

    Objective: mean_rank_ic on walk-forward windows (not Sharpe, to reduce overfitting).
    """

    def __init__(
        self,
        run_backtest_fn: Callable[..., Any],
        training_data: pd.DataFrame,
        benchmark_data: pd.DataFrame,
        price_data: pd.DataFrame,
        base_feature_columns: List[str],
        backtest_config: BacktestConfig,
        model_config: ModelConfig,
    ):
        """
        Args:
            run_backtest_fn: Callable that runs walk-forward backtest.
                Signature: (training_data, benchmark_data, price_data,
                           feature_cols, config, model_config, verbose) -> BacktestResults
            training_data: Full training dataset (with all features pre-computed).
            benchmark_data: Benchmark price data.
            price_data: Stock price data.
            base_feature_columns: Currently active feature columns.
            backtest_config: Backtest configuration.
            model_config: Model configuration.
        """
        self.run_backtest = run_backtest_fn
        self.training_data = training_data
        self.benchmark_data = benchmark_data
        self.price_data = price_data
        self.base_columns = base_feature_columns
        self.backtest_config = backtest_config
        self.model_config = model_config

    def tune(
        self,
        feature_name: str,
        registry: FeatureRegistry,
        recompute_fn: Callable[..., pd.DataFrame],
        n_calls: int = 30,
        n_initial: int = 8,
        objective_metric: str = "mean_rank_ic",
    ) -> Tuple[Dict[str, Any], float]:
        """Tune feature-specific parameters via Bayesian optimization.

        Args:
            feature_name: FeatureSpec name to tune.
            registry: Feature registry.
            recompute_fn: Function to recompute features with new params.
                Signature: (param_dict) -> pd.DataFrame (updated training_data).
            n_calls: Total optimization calls.
            n_initial: Initial random exploration points.
            objective_metric: Metric to optimize.

        Returns:
            Tuple of (best_params_dict, best_metric_value).
        """
        from skopt import gp_minimize

        params = registry.get_tunable_params(feature_name)
        if not params:
            logger.info(f"No tunable params for {feature_name}, skipping tuning")
            return {}, 0.0

        dimensions, param_names = _build_search_space(params)

        best_metric = [float("-inf")]
        call_count = [0]

        def objective(values):
            call_count[0] += 1
            param_dict = dict(zip(param_names, values))
            logger.info(
                f"  Tuning trial {call_count[0]}/{n_calls}: {param_dict}"
            )
            try:
                # Recompute features with candidate params
                updated_data = recompute_fn(param_dict)

                # Get feature columns available
                feature_cols = [
                    c for c in self.base_columns
                    if c in updated_data.columns
                ]
                if not feature_cols:
                    return 1e6  # No features available

                # Run backtest
                results = self.run_backtest(
                    updated_data,
                    self.benchmark_data,
                    self.price_data,
                    feature_cols,
                    self.backtest_config,
                    self.model_config,
                    False,  # verbose=False
                )

                metric_val = results.metrics.get(objective_metric, 0.0)
                if metric_val is None or np.isnan(metric_val):
                    return 1e6

                if metric_val > best_metric[0]:
                    best_metric[0] = metric_val
                    logger.info(f"    New best {objective_metric}={metric_val:.6f}")

                return -metric_val  # Minimize negative metric

            except Exception as e:
                logger.warning(f"  Trial failed: {e}")
                return 1e6

        result = gp_minimize(
            objective,
            dimensions,
            n_calls=n_calls,
            n_initial_points=n_initial,
            acq_func="EI",
            random_state=42,
        )

        best_params = dict(zip(param_names, result.x))
        best_val = -result.fun if result.fun < 1e5 else 0.0

        logger.info(f"Best params for {feature_name}: {best_params} ({objective_metric}={best_val:.6f})")
        return best_params, best_val


class ModelParamTuner:
    """Bayesian optimization for LightGBM hyperparameters."""

    SEARCH_SPACE = {
        "n_estimators": TunableParam("int", 50, 300, 200),
        "learning_rate": TunableParam("float", 0.01, 0.1, 0.03, prior="log-uniform"),
        "num_leaves": TunableParam("int", 7, 31, 15),
        "max_depth": TunableParam("int", 3, 8, 6),
        "min_child_samples": TunableParam("int", 30, 100, 50),
        "reg_alpha": TunableParam("float", 0.1, 1.0, 0.3),
        "reg_lambda": TunableParam("float", 0.1, 1.0, 0.5),
        "subsample": TunableParam("float", 0.5, 0.9, 0.7),
        "colsample_bytree": TunableParam("float", 0.5, 0.9, 0.7),
    }

    def tune(
        self,
        run_backtest_fn: Callable[..., Any],
        training_data: pd.DataFrame,
        feature_columns: List[str],
        benchmark_data: pd.DataFrame,
        price_data: pd.DataFrame,
        backtest_config: BacktestConfig,
        n_calls: int = 50,
        n_initial: int = 10,
        objective_metric: str = "mean_rank_ic",
        complexity_penalty: float = 0.01,
    ) -> Tuple[ModelConfig, float]:
        """Tune LightGBM hyperparameters with complexity penalty.

        Args:
            run_backtest_fn: Walk-forward backtest function.
            training_data: Full training dataset.
            feature_columns: Feature columns to use.
            benchmark_data: Benchmark price data.
            price_data: Stock price data.
            backtest_config: Backtest configuration.
            n_calls: Total optimization calls.
            n_initial: Initial random exploration points.
            objective_metric: Metric to optimize.
            complexity_penalty: Penalty coefficient for model complexity.

        Returns:
            Tuple of (best ModelConfig, best metric value).
        """
        from skopt import gp_minimize

        dimensions, param_names = _build_search_space(self.SEARCH_SPACE)

        best_metric = [float("-inf")]
        call_count = [0]

        def objective(values):
            call_count[0] += 1
            param_dict = dict(zip(param_names, values))
            logger.info(f"  Model tuning trial {call_count[0]}/{n_calls}: {param_dict}")

            try:
                model_config = ModelConfig(
                    params={
                        "n_estimators": int(param_dict["n_estimators"]),
                        "learning_rate": param_dict["learning_rate"],
                        "num_leaves": int(param_dict["num_leaves"]),
                        "max_depth": int(param_dict["max_depth"]),
                        "min_child_samples": int(param_dict["min_child_samples"]),
                        "reg_alpha": param_dict["reg_alpha"],
                        "reg_lambda": param_dict["reg_lambda"],
                        "subsample": param_dict["subsample"],
                        "colsample_bytree": param_dict["colsample_bytree"],
                    }
                )

                results = run_backtest_fn(
                    training_data,
                    benchmark_data,
                    price_data,
                    feature_columns,
                    backtest_config,
                    model_config,
                    False,  # verbose
                )

                metric_val = results.metrics.get(objective_metric, 0.0)
                if metric_val is None or np.isnan(metric_val):
                    return 1e6

                # Complexity penalty
                penalty = complexity_penalty * (
                    int(param_dict["num_leaves"])
                    * int(param_dict["n_estimators"])
                    / 1000.0
                )
                adjusted = metric_val - penalty

                if adjusted > best_metric[0]:
                    best_metric[0] = adjusted
                    logger.info(
                        f"    New best {objective_metric}={metric_val:.6f} "
                        f"(adjusted={adjusted:.6f})"
                    )

                return -adjusted

            except Exception as e:
                logger.warning(f"  Model tuning trial failed: {e}")
                return 1e6

        result = gp_minimize(
            objective,
            dimensions,
            n_calls=n_calls,
            n_initial_points=n_initial,
            acq_func="EI",
            random_state=42,
        )

        best_params = dict(zip(param_names, result.x))
        best_config = ModelConfig(
            params={
                "n_estimators": int(best_params["n_estimators"]),
                "learning_rate": best_params["learning_rate"],
                "num_leaves": int(best_params["num_leaves"]),
                "max_depth": int(best_params["max_depth"]),
                "min_child_samples": int(best_params["min_child_samples"]),
                "reg_alpha": best_params["reg_alpha"],
                "reg_lambda": best_params["reg_lambda"],
                "subsample": best_params["subsample"],
                "colsample_bytree": best_params["colsample_bytree"],
            }
        )
        best_val = -result.fun if result.fun < 1e5 else 0.0

        logger.info(f"Best model params: {best_config.params} ({objective_metric}={best_val:.6f})")
        return best_config, best_val
