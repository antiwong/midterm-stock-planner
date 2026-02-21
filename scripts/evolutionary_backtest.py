#!/usr/bin/env python3
"""
Evolutionary Strategy Optimizer (QuantaAlpha-inspired).

Treats backtest runs as trajectories and evolves them via mutation and crossover
on config params. Fitness = Sharpe (or configurable). Stores trajectory history,
exports best configs to YAML.

Mutable params: train_years, test_years, step_value, step_unit, rebalance_freq,
top_n, top_pct, transaction_cost.

Note: With limited data (~600 days), use train_years ≤ 1.5 and test_years ≤ 0.5.
Extend benchmark with: python scripts/download_benchmark.py --start 2010-01-01

Usage:
    python scripts/evolutionary_backtest.py --watchlist tech_giants --generations 5
    python scripts/evolutionary_backtest.py --watchlist nasdaq_100 --population 8 --metric total_return
    python scripts/evolutionary_backtest.py --config config/config.yaml --save output/evolutionary_best.yaml
"""

import argparse
import copy
import hashlib
import json
import random
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# Param bounds and options for mutation
# train_years min 1.0 allows runs with ~500 days of data (1y train + 0.25y test)
PARAM_SCHEMA = {
    "train_years": {"type": "float", "min": 1.0, "max": 8.0, "default": 2.0},
    "test_years": {"type": "float", "min": 0.25, "max": 2.0, "default": 0.5},
    "step_value": {"type": "float", "min": 0.5, "max": 2.0, "default": 1.0},
    "step_unit": {"type": "choice", "options": ["years", "months", "days"], "default": "years"},
    "rebalance_freq": {"type": "choice", "options": ["MS", "M", "2W", "W"], "default": "MS"},
    "top_n": {"type": "int_or_none", "min": 5, "max": 20, "default": 10},
    "top_pct": {"type": "float", "min": 0.05, "max": 0.25, "default": 0.1},
    "transaction_cost": {"type": "float", "min": 0.0005, "max": 0.002, "default": 0.001},
}


@dataclass
class Trajectory:
    """Single trajectory (config + metrics) for lineage."""
    run_id: str
    param_vector: Dict[str, Any]
    config_hash: str
    fitness: float
    metrics: Dict[str, float]
    parent_run_ids: List[str] = field(default_factory=list)
    mutation_type: str = "initial"
    generation: int = 0


def _param_vector_to_backtest_config(params: Dict[str, Any]) -> "BacktestConfig":
    """Convert param vector to BacktestConfig."""
    from src.config.config import BacktestConfig

    top_n = params.get("top_n")
    if top_n is not None and isinstance(top_n, float):
        top_n = int(top_n) if not (top_n != top_n) else None  # handle NaN

    return BacktestConfig(
        train_years=float(params.get("train_years", 5.0)),
        test_years=float(params.get("test_years", 1.0)),
        step_value=float(params.get("step_value", 1.0)),
        step_unit=str(params.get("step_unit", "years")),
        rebalance_freq=str(params.get("rebalance_freq", "MS")),
        top_n=top_n,
        top_pct=float(params.get("top_pct", 0.1)),
        min_stocks=5,
        transaction_cost=float(params.get("transaction_cost", 0.001)),
    )


def _default_param_vector() -> Dict[str, Any]:
    """Return default param vector from schema."""
    return {k: v["default"] for k, v in PARAM_SCHEMA.items()}


def _random_param_vector() -> Dict[str, Any]:
    """Generate random param vector within bounds."""
    params = {}
    for key, schema in PARAM_SCHEMA.items():
        if schema["type"] == "float":
            params[key] = random.uniform(schema["min"], schema["max"])
        elif schema["type"] == "choice":
            params[key] = random.choice(schema["options"])
        elif schema["type"] == "int_or_none":
            if random.random() < 0.5:
                params[key] = random.randint(schema["min"], schema["max"])
            else:
                params[key] = None
    return params


def _mutate(params: Dict[str, Any], strength: float = 0.2) -> Dict[str, Any]:
    """Mutate params with given strength (0=no change, 1=full range)."""
    new_params = copy.deepcopy(params)
    for key, schema in PARAM_SCHEMA.items():
        if random.random() > 0.5:  # 50% chance to mutate each param
            continue
        if schema["type"] == "float":
            delta = (schema["max"] - schema["min"]) * strength * (random.random() - 0.5) * 2
            new_params[key] = max(schema["min"], min(schema["max"], params[key] + delta))
        elif schema["type"] == "choice":
            new_params[key] = random.choice(schema["options"])
        elif schema["type"] == "int_or_none":
            if random.random() < 0.3:
                new_params[key] = None
            else:
                new_params[key] = random.randint(schema["min"], schema["max"])
    return new_params


def _crossover(p1: Dict[str, Any], p2: Dict[str, Any]) -> Dict[str, Any]:
    """Crossover: take each param from p1 or p2 with 50% probability."""
    keys = list(PARAM_SCHEMA.keys())
    mid = len(keys) // 2
    from_p1 = set(random.sample(keys, mid))
    new_params = {}
    for k in keys:
        new_params[k] = p1[k] if k in from_p1 else p2[k]
    return new_params


def _compute_config_hash(params: Dict[str, Any]) -> str:
    """Deterministic hash of param vector for lineage."""
    canonical = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _run_backtest_with_params(
    config_path: Optional[Path],
    params: Dict[str, Any],
    universe: Optional[List[str]],
    verbose: bool = False,
) -> Tuple[Dict[str, float], Optional[Any]]:
    """Run full pipeline with overridden backtest params. Returns (metrics, backtest_results)."""
    from src.config.config import load_config, BacktestConfig
    from src.pipeline import run_full_pipeline
    from src.backtest.rolling import BacktestConfig as RollingBacktestConfig

    config = load_config(config_path)
    backtest_cfg = _param_vector_to_backtest_config(params)
    # Override config.backtest
    config.backtest = BacktestConfig(
        train_years=backtest_cfg.train_years,
        test_years=backtest_cfg.test_years,
        step_value=backtest_cfg.step_value,
        step_unit=backtest_cfg.step_unit,
        rebalance_freq=backtest_cfg.rebalance_freq,
        top_n=backtest_cfg.top_n,
        top_pct=backtest_cfg.top_pct,
        min_stocks=backtest_cfg.min_stocks,
        transaction_cost=backtest_cfg.transaction_cost,
    )
    config.cli.save_results = False  # Don't write CSVs for each eval
    config.features.use_sentiment = False  # Faster, deterministic

    try:
        results = run_full_pipeline(
            config=config,
            save_model=False,
            verbose=verbose,
            universe=universe,
        )
        metrics = results["backtest_results"].metrics
        return metrics, results["backtest_results"]
    except Exception as e:
        if verbose:
            print(f"  Backtest failed: {e}")
        return {}, None


def _fitness_from_metrics(
    metrics: Dict[str, float],
    metric: str,
    params: Optional[Dict[str, Any]] = None,
    complexity_penalty: float = 0.0,
    reject_complexity_above: Optional[float] = None,
) -> float:
    """Extract fitness from metrics. Higher is better. Invalid/NaN -> -1e9.
    Optionally penalize by config complexity or reject if too complex."""
    val = metrics.get(metric)
    if val is None:
        return -1e9
    try:
        f = float(val)
        if f != f:  # NaN
            return -1e9
    except (TypeError, ValueError):
        return -1e9

    if params is not None and (complexity_penalty > 0 or reject_complexity_above is not None):
        from src.risk.complexity import compute_config_complexity, exceeds_thresholds
        complexity = compute_config_complexity(params)
        if reject_complexity_above is not None and complexity > reject_complexity_above:
            return -1e9
        f = f - complexity_penalty * complexity
    return f


def _export_config_yaml(params: Dict[str, Any], path: Path) -> None:
    """Export param vector as YAML snippet for backtest config."""
    import yaml

    # Map to standard config structure
    doc = {
        "backtest": {
            "train_years": params["train_years"],
            "test_years": params["test_years"],
            "step_value": params["step_value"],
            "step_unit": params["step_unit"],
            "rebalance_freq": params["rebalance_freq"],
            "top_n": params["top_n"],
            "top_pct": params["top_pct"],
            "transaction_cost": params["transaction_cost"],
        }
    }
    with open(path, "w") as f:
        yaml.dump(doc, f, default_flow_style=False, sort_keys=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evolutionary strategy optimizer: mutate/crossover config params, fitness=Sharpe"
    )
    parser.add_argument("--config", "-c", default="config/config.yaml", help="Config file")
    parser.add_argument("--watchlist", "-w", help="Watchlist name (default: universe.txt)")
    parser.add_argument("--generations", "-g", type=int, default=5, help="Number of generations")
    parser.add_argument("--population", "-p", type=int, default=6, help="Population size")
    parser.add_argument("--elite", "-e", type=int, default=2, help="Elite to keep each generation")
    parser.add_argument("--metric", "-m", default="sharpe_ratio",
                       choices=["sharpe_ratio", "total_return", "hit_rate"],
                       help="Fitness metric")
    parser.add_argument("--mutate-strength", type=float, default=0.2,
                       help="Mutation strength (0-1)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--save", "-s", help="Save best config to YAML path")
    parser.add_argument("--output-dir", "-o", default=None,
                        help="Directory for trajectory history (default: output/evolutionary)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose backtest output")
    parser.add_argument("--complexity-penalty", type=float, default=0.0,
                        help="Penalty per unit config complexity (fitness -= penalty * complexity)")
    parser.add_argument("--reject-complexity-above", type=float, default=None,
                        help="Reject configs with complexity above this threshold")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # Resolve universe
    universe = None
    watchlist_name = args.watchlist or "default"
    if args.watchlist:
        from src.data.watchlists import WatchlistManager
        wl_manager = WatchlistManager.from_config_dir("config")
        wl = wl_manager.get_watchlist(args.watchlist)
        if wl:
            universe = wl.symbols
            watchlist_name = wl.name
        else:
            print(f"Warning: Watchlist '{args.watchlist}' not found, using default universe")

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config not found: {config_path}")
        return 1

    output_dir = Path(args.output_dir or "output/evolutionary")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Evolutionary Strategy Optimizer")
    print("=" * 60)
    print(f"Watchlist: {watchlist_name} ({len(universe) if universe else 'default'} tickers)")
    print(f"Generations: {args.generations}, Population: {args.population}, Elite: {args.elite}")
    print(f"Fitness metric: {args.metric}")
    print("=" * 60)

    # Initial population: 1 default + rest random
    population: List[Trajectory] = []
    default_params = _default_param_vector()
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    metrics, _ = _run_backtest_with_params(config_path, default_params, universe, args.verbose)
    fitness = _fitness_from_metrics(
        metrics, args.metric,
        params=default_params,
        complexity_penalty=args.complexity_penalty,
        reject_complexity_above=args.reject_complexity_above,
    )
    population.append(Trajectory(
        run_id=run_id,
        param_vector=default_params,
        config_hash=_compute_config_hash(default_params),
        fitness=fitness,
        metrics=metrics,
        parent_run_ids=[],
        mutation_type="initial",
        generation=0,
    ))
    print(f"Gen 0: default  fitness={fitness:.4f}  sharpe={metrics.get('sharpe_ratio', 0):.3f}")

    for i in range(args.population - 1):
        params = _random_param_vector()
        run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        metrics, _ = _run_backtest_with_params(config_path, params, universe, args.verbose)
        fitness = _fitness_from_metrics(
            metrics, args.metric,
            params=params,
            complexity_penalty=args.complexity_penalty,
            reject_complexity_above=args.reject_complexity_above,
        )
        population.append(Trajectory(
            run_id=run_id,
            param_vector=params,
            config_hash=_compute_config_hash(params),
            fitness=fitness,
            metrics=metrics,
            parent_run_ids=[],
            mutation_type="initial",
            generation=0,
        ))
        print(f"Gen 0: random {i+1}  fitness={fitness:.4f}  sharpe={metrics.get('sharpe_ratio', 0):.3f}")

    # Evolution loop
    all_trajectories: List[Dict[str, Any]] = [
        {
            "run_id": t.run_id,
            "param_vector": t.param_vector,
            "config_hash": t.config_hash,
            "fitness": t.fitness,
            "metrics": t.metrics,
            "parent_run_ids": t.parent_run_ids,
            "mutation_type": t.mutation_type,
            "generation": t.generation,
        }
        for t in population
    ]

    for gen in range(1, args.generations):
        # Sort by fitness (descending)
        population.sort(key=lambda t: t.fitness, reverse=True)
        elite = population[: args.elite]
        # Selection: keep elite + fill with offspring
        offspring: List[Trajectory] = list(elite)
        while len(offspring) < args.population:
            if random.random() < 0.5 and len(elite) >= 2:
                # Crossover
                p1, p2 = random.sample(elite, 2)
                params = _crossover(p1.param_vector, p2.param_vector)
                parent_ids = [p1.run_id, p2.run_id]
                mut_type = "crossover"
            else:
                # Mutation
                parent = random.choice(elite)
                params = _mutate(parent.param_vector, args.mutate_strength)
                parent_ids = [parent.run_id]
                mut_type = "mutation"
            run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            metrics, _ = _run_backtest_with_params(config_path, params, universe, args.verbose)
            fitness = _fitness_from_metrics(
                metrics, args.metric,
                params=params,
                complexity_penalty=args.complexity_penalty,
                reject_complexity_above=args.reject_complexity_above,
            )
            traj = Trajectory(
                run_id=run_id,
                param_vector=params,
                config_hash=_compute_config_hash(params),
                fitness=fitness,
                metrics=metrics,
                parent_run_ids=parent_ids,
                mutation_type=mut_type,
                generation=gen,
            )
            offspring.append(traj)
            all_trajectories.append({
                "run_id": traj.run_id,
                "param_vector": traj.param_vector,
                "config_hash": traj.config_hash,
                "fitness": traj.fitness,
                "metrics": traj.metrics,
                "parent_run_ids": traj.parent_run_ids,
                "mutation_type": traj.mutation_type,
                "generation": traj.generation,
            })
        population = offspring
        best = population[0]
        print(f"Gen {gen}: best fitness={best.fitness:.4f}  sharpe={best.metrics.get('sharpe_ratio', 0):.3f}  "
              f"({best.mutation_type})")

    # Final sort and output
    population.sort(key=lambda t: t.fitness, reverse=True)
    best = population[0]

    print("\n" + "=" * 60)
    print("Best Configuration")
    print("=" * 60)
    print(f"Fitness ({args.metric}): {best.fitness:.4f}")
    print(f"Sharpe: {best.metrics.get('sharpe_ratio', 0):.3f}")
    print(f"Total Return: {best.metrics.get('total_return', 0):.2%}")
    print(f"Max Drawdown: {best.metrics.get('max_drawdown', 0):.2%}")
    print("\nParams:")
    for k, v in best.param_vector.items():
        print(f"  {k}: {v}")

    # Save trajectory history
    history_path = output_dir / f"evolutionary_{watchlist_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(history_path, "w") as f:
        json.dump(all_trajectories, f, indent=2, default=str)
    print(f"\nTrajectory history saved to: {history_path}")

    # Export best config
    if args.save:
        save_path = Path(args.save)
        _export_config_yaml(best.param_vector, save_path)
        print(f"Best config exported to: {save_path}")
    else:
        default_save = output_dir / "best_config.yaml"
        _export_config_yaml(best.param_vector, default_save)
        print(f"Best config exported to: {default_save}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
