#!/usr/bin/env python3
"""
Transfer & Robustness Testing (QuantaAlpha-inspired).

Runs backtest on primary universe, then on a transfer universe with the same
config (zero-shot, no re-optimization). Outputs side-by-side metrics to
evaluate robustness under distribution shift.

Usage:
    python scripts/transfer_report.py --config config/config.yaml \\
        --watchlist nasdaq_100 --transfer-watchlist sp500
    python scripts/transfer_report.py --config config.yaml \\
        --transfer-watchlist semiconductors  # primary = default universe
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run backtest on primary and transfer universes, compare metrics"
    )
    parser.add_argument(
        "--config", "-c",
        default="config/config.yaml",
        help="Path to config file",
    )
    parser.add_argument(
        "--watchlist", "-w",
        help="Primary watchlist (default: use universe.txt)",
    )
    parser.add_argument(
        "--transfer-watchlist", "-t",
        required=True,
        help="Transfer watchlist for robustness testing",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON path for comparison",
    )
    args = parser.parse_args()

    from src.config.config import load_config
    from src.pipeline import run_full_pipeline
    from src.data.watchlists import WatchlistManager
    from src.data.loaders import load_universe

    config = load_config(args.config)
    wl_manager = WatchlistManager.from_config_dir("config")

    # Resolve primary universe
    primary_universe = None
    primary_name = "Default (universe.txt)"
    if args.watchlist:
        wl = wl_manager.get_watchlist(args.watchlist)
        if wl:
            primary_universe = wl.symbols
            primary_name = wl.name
        else:
            print(f"Warning: Watchlist '{args.watchlist}' not found, using default universe")
    elif config.data.universe_path:
        primary_universe = load_universe(config.data.universe_path)
        primary_name = "universe.txt"

    # Resolve transfer universe
    transfer_wl = wl_manager.get_watchlist(args.transfer_watchlist)
    if not transfer_wl:
        print(f"Error: Transfer watchlist '{args.transfer_watchlist}' not found")
        return 1
    transfer_universe = transfer_wl.symbols
    transfer_name = transfer_wl.name

    print("=" * 70)
    print("Transfer & Robustness Testing")
    print("=" * 70)
    print(f"Primary:  {primary_name} ({len(primary_universe) if primary_universe else 'all'} tickers)")
    print(f"Transfer: {transfer_name} ({len(transfer_universe)} tickers)")
    print("Same config, zero-shot transfer (no re-optimization)")
    print("=" * 70)

    def _run_and_metrics(universe, label: str) -> dict:
        print(f"\nRunning backtest on {label}...")
        results = run_full_pipeline(
            config=config,
            save_model=False,
            verbose=False,
            universe=universe,
        )
        return results["backtest_results"].metrics

    primary_metrics = _run_and_metrics(primary_universe, primary_name)
    transfer_metrics = _run_and_metrics(transfer_universe, transfer_name)

    # Side-by-side table
    key_metrics = [
        ("total_return", "Total Return", lambda x: f"{x:.2%}"),
        ("annualized_return", "Ann. Return", lambda x: f"{x:.2%}"),
        ("sharpe_ratio", "Sharpe", lambda x: f"{x:.2f}"),
        ("max_drawdown", "Max DD", lambda x: f"{x:.2%}"),
        ("excess_return", "Excess Return", lambda x: f"{x:.2%}"),
        ("volatility", "Volatility", lambda x: f"{x:.2%}"),
        ("hit_rate", "Hit Rate", lambda x: f"{x:.1%}"),
    ]
    primary_vals = []
    transfer_vals = []
    for key, label, fmt in key_metrics:
        pv = primary_metrics.get(key)
        tv = transfer_metrics.get(key)
        primary_vals.append(fmt(pv) if pv is not None else "N/A")
        transfer_vals.append(fmt(tv) if tv is not None else "N/A")

    print("\n" + "=" * 70)
    print("Side-by-Side Metrics")
    print("=" * 70)
    print(f"{'Metric':<20} {primary_name[:22]:>24} {transfer_name[:22]:>24}")
    print("-" * 70)
    for (_, label, _), pv, tv in zip(key_metrics, primary_vals, transfer_vals):
        print(f"{label:<20} {pv:>24} {tv:>24}")
    print("=" * 70)

    out_data = {
        "primary": {"name": primary_name, "metrics": primary_metrics},
        "transfer": {"name": transfer_name, "metrics": transfer_metrics},
    }
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(out_data, f, indent=2)
        print(f"\nSaved to: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
