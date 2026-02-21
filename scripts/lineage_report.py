#!/usr/bin/env python3
"""
Lineage Report: DAG of backtest runs with config lineage and best-branch highlighting.

Scans output/run_* folders, loads run_info.json from each, builds a DAG from
parent_run_ids, and reports lineage with optional best-branch highlighting by
Sharpe, total_return, or hit_rate.

Usage:
  python scripts/lineage_report.py [--output-dir output] [--format text|json] [--metric sharpe|total_return|hit_rate]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_run_infos(output_dir: Path) -> List[Dict[str, Any]]:
    """Load run_info.json from each run_* folder. Skip missing/invalid."""
    infos: List[Dict[str, Any]] = []
    for folder in sorted(output_dir.iterdir()):
        if not folder.is_dir() or not folder.name.startswith("run_"):
            continue
        run_info_path = folder / "run_info.json"
        if not run_info_path.exists():
            continue
        try:
            with open(run_info_path) as f:
                data = json.load(f)
            data["_folder"] = folder.name
            # Fallback: if run_info has no metrics, load from backtest_metrics.json
            if not data.get("metrics") and (folder / "backtest_metrics.json").exists():
                try:
                    with open(folder / "backtest_metrics.json") as mf:
                        data["metrics"] = json.load(mf)
                except (json.JSONDecodeError, OSError):
                    pass
            infos.append(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: skip {folder.name}: {e}", file=sys.stderr)
    return infos


def load_evolutionary_trajectories(output_dir: Path) -> List[Dict[str, Any]]:
    """Load evolutionary trajectory JSON files (run_info compatible format)."""
    infos: List[Dict[str, Any]] = []
    evo_dir = output_dir / "evolutionary"
    if not evo_dir.exists():
        return infos
    for path in sorted(evo_dir.glob("evolutionary_*.json")):
        try:
            with open(path) as f:
                trajectories = json.load(f)
            if not isinstance(trajectories, list):
                continue
            for t in trajectories:
                run_id = t.get("run_id")
                if not run_id:
                    continue
                # Convert to run_info-like format
                info = {
                    "run_id": run_id,
                    "name": f"Evolutionary gen {t.get('generation', 0)}",
                    "metrics": t.get("metrics") or {},
                    "config_hash": t.get("config_hash"),
                    "parent_run_ids": t.get("parent_run_ids") or [],
                    "mutation_type": t.get("mutation_type") or "initial",
                    "_folder": f"evolutionary/{path.name}",
                }
                infos.append(info)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: skip {path.name}: {e}", file=sys.stderr)
    return infos


def build_dag(infos: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict], Dict[str, List[str]]]:
    """
    Build run_id -> info map and parent -> children adjacency.
    Returns (run_map, children_map).
    """
    run_map: Dict[str, Dict] = {}
    children_map: Dict[str, List[str]] = {}

    for info in infos:
        run_id = info.get("run_id")
        if not run_id:
            continue
        run_map[run_id] = info
        parent_ids = info.get("parent_run_ids") or []
        for pid in parent_ids:
            children_map.setdefault(pid, []).append(run_id)
        if run_id not in children_map:
            children_map[run_id] = []

    return run_map, children_map


def get_metric(info: Dict[str, Any], metric: str) -> Optional[float]:
    """Extract metric from run_info (metrics dict or legacy fields)."""
    metrics = info.get("metrics") or {}
    val = metrics.get(metric)
    if val is None:
        val = info.get(metric)
    if val is None:
        return None
    try:
        f = float(val)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


def find_roots(run_map: Dict[str, Dict], children_map: Dict[str, List[str]]) -> List[str]:
    """Return run_ids with no parents (roots of DAG)."""
    roots = []
    for run_id in run_map:
        parents = (run_map[run_id].get("parent_run_ids") or [])
        if not parents:
            roots.append(run_id)
    return roots


def find_best_branches(
    run_map: Dict[str, Dict],
    children_map: Dict[str, List[str]],
    metric: str,
    top_n: int = 5,
) -> List[Tuple[str, float]]:
    """
    Rank runs by metric and return top N (run_id, value).
    Uses sharpe_ratio, total_return, or hit_rate.
    """
    scored: List[Tuple[str, float]] = []
    for run_id, info in run_map.items():
        val = get_metric(info, metric)
        if val is not None:
            scored.append((run_id, val))
    # Sort descending (higher is better for all three)
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]


def format_text_report(
    run_map: Dict[str, Dict],
    children_map: Dict[str, List[str]],
    best: List[Tuple[str, float]],
    metric: str,
) -> str:
    """Produce human-readable text report."""
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("Lineage Report: DAG of Backtest Runs")
    lines.append("=" * 60)
    lines.append("")

    roots = find_roots(run_map, children_map)
    lines.append(f"Root runs (no parents): {len(roots)}")
    for rid in roots[:10]:
        info = run_map.get(rid, {})
        name = info.get("name") or info.get("watchlist", "?")
        lines.append(f"  - {rid}  {name}")
    if len(roots) > 10:
        lines.append(f"  ... and {len(roots) - 10} more")
    lines.append("")

    lines.append(f"Best runs by {metric}:")
    for i, (rid, val) in enumerate(best, 1):
        info = run_map.get(rid, {})
        name = info.get("name") or info.get("watchlist", "?")
        folder = info.get("_folder", "?")
        lines.append(f"  {i}. {rid}  {metric}={val:.4f}  {name}  [{folder}]")
    lines.append("")

    lines.append("Lineage (parent -> children):")
    for rid in sorted(run_map.keys())[:20]:
        children = children_map.get(rid, [])
        if children:
            lines.append(f"  {rid}")
            for c in children[:5]:
                lines.append(f"    -> {c}")
            if len(children) > 5:
                lines.append(f"    ... +{len(children) - 5} more")
    if len(run_map) > 20:
        lines.append("  ... (truncated)")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_json_report(
    run_map: Dict[str, Dict],
    children_map: Dict[str, List[str]],
    best: List[Tuple[str, float]],
    metric: str,
) -> str:
    """Produce JSON report."""
    report = {
        "run_count": len(run_map),
        "roots": find_roots(run_map, children_map),
        "best_by_metric": metric,
        "best_runs": [{"run_id": rid, "value": val} for rid, val in best],
        "runs": {
            rid: {
                "run_id": rid,
                "name": info.get("name"),
                "watchlist": info.get("watchlist"),
                "config_hash": info.get("config_hash"),
                "parent_run_ids": info.get("parent_run_ids") or [],
                "mutation_type": info.get("mutation_type"),
                "children": children_map.get(rid, []),
                "folder": info.get("_folder"),
                "metrics": info.get("metrics"),
            }
            for rid, info in run_map.items()
        },
    }
    return json.dumps(report, indent=2, default=str)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lineage report: DAG of backtest runs with best-branch highlighting."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="Directory containing run_* folders",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--metric",
        choices=["sharpe_ratio", "total_return", "hit_rate"],
        default="sharpe_ratio",
        help="Metric for best-branch ranking",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of best runs to highlight",
    )
    args = parser.parse_args()

    if not args.output_dir.exists():
        print(f"Error: output dir not found: {args.output_dir}", file=sys.stderr)
        return 1

    infos = load_run_infos(args.output_dir)
    evo_infos = load_evolutionary_trajectories(args.output_dir)
    infos = infos + evo_infos
    if not infos:
        print("No run_info.json found in run_* folders.", file=sys.stderr)
        return 0

    run_map, children_map = build_dag(infos)
    best = find_best_branches(run_map, children_map, args.metric, top_n=args.top)

    if args.format == "text":
        print(format_text_report(run_map, children_map, best, args.metric))
    else:
        print(format_json_report(run_map, children_map, best, args.metric))

    return 0


if __name__ == "__main__":
    sys.exit(main())
