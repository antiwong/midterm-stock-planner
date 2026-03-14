#!/usr/bin/env python3
"""
Regression Test Monitor
=======================
Simple terminal monitor that shows live progress of running regression tests.

Usage:
    python scripts/monitor.py          # Auto-refresh every 10s
    python scripts/monitor.py --once   # Print once and exit
    python scripts/monitor.py -i 5     # Refresh every 5s
"""

import os
import sys
import time
import sqlite3
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "runs.db"

CLEAR = "\033[2J\033[H"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"

STATUS_COLORS = {
    "running": CYAN,
    "completed": GREEN,
    "failed": RED,
}


def get_process_info():
    """Get running regression test processes."""
    try:
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5
        )
        procs = []
        for line in result.stdout.split("\n"):
            if "run_regression" in line and "grep" not in line and "monitor" not in line:
                parts = line.split()
                if len(parts) >= 11:
                    procs.append({
                        "pid": parts[1],
                        "cpu": parts[2],
                        "mem": parts[3],
                        "time": parts[9],
                    })
        return procs
    except Exception:
        return []


def query_db():
    """Query regression test data from SQLite."""
    if not DB_PATH.exists():
        return [], {}

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Get tests
    tests = conn.execute(
        "SELECT * FROM regression_tests ORDER BY created_at DESC LIMIT 10"
    ).fetchall()

    # Get steps grouped by regression_id
    steps_by_test = {}
    for t in tests:
        rid = t["regression_id"]
        rows = conn.execute(
            "SELECT * FROM regression_steps WHERE regression_id = ? ORDER BY step_number",
            (rid,),
        ).fetchall()
        steps_by_test[rid] = rows

    conn.close()
    return tests, steps_by_test


def fmt_duration(seconds):
    """Format seconds into human-readable duration."""
    if seconds is None:
        return "—"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def fmt_float(v, width=8, decimals=4):
    if v is None:
        return "—".rjust(width)
    return f"{v:+.{decimals}f}".rjust(width)


def render(tests, steps_by_test, procs):
    lines = []
    now = datetime.now().strftime("%H:%M:%S")
    lines.append(f"{BOLD}QuantaAlpha Regression Monitor{RESET}  {DIM}{now}{RESET}")
    lines.append("")

    # Process info
    if procs:
        for p in procs:
            lines.append(
                f"  {GREEN}●{RESET} PID {p['pid']}  "
                f"CPU {p['cpu']}%  MEM {p['mem']}%  TIME {p['time']}"
            )
    else:
        lines.append(f"  {DIM}No regression processes running{RESET}")
    lines.append("")

    # Tests
    for t in tests:
        rid = t["regression_id"]
        status = t["status"]
        color = STATUS_COLORS.get(status, RESET)
        name = t["name"] or rid[:20]
        total = t["total_steps"] or "?"
        steps = steps_by_test.get(rid, [])
        done = len(steps)

        # Status line
        icon = {"running": "⟳", "completed": "✓", "failed": "✗"}.get(status, "?")
        dur = fmt_duration(t["duration_seconds"])
        lines.append(
            f"  {color}{icon} {name}{RESET}  "
            f"{DIM}[{status}]{RESET}  "
            f"steps {done}/{total}  {DIM}{dur}{RESET}"
        )
        lines.append(f"    {DIM}{rid}{RESET}")

        # Progress bar for running tests
        if status == "running" and isinstance(total, int) and total > 0:
            bar_width = 30
            filled = int(bar_width * done / total)
            bar = "█" * filled + "░" * (bar_width - filled)
            pct = done * 100 // total
            lines.append(f"    [{bar}] {pct}%")

        # Step table
        if steps:
            lines.append(
                f"    {BOLD}{'Step':>4}  {'Feature':<22} {'Sharpe':>9} {'RankIC':>9} {'MargIC':>9}{RESET}"
            )
            for s in steps:
                sh = fmt_float(s["sharpe_ratio"], 9, 3)
                ric = fmt_float(s["mean_rank_ic"], 9, 4)
                mic = fmt_float(s["marginal_rank_ic"], 9, 4)

                # Color marginal IC
                mic_val = s["marginal_rank_ic"]
                if mic_val is not None:
                    if mic_val > 0.005:
                        mic = f"{GREEN}{mic}{RESET}"
                    elif mic_val < -0.005:
                        mic = f"{RED}{mic}{RESET}"

                lines.append(
                    f"    {s['step_number']:>4}  {s['feature_added']:<22} {sh} {ric} {mic}"
                )

            # Summary
            if len(steps) > 1:
                best = max(steps, key=lambda s: s["mean_rank_ic"] or 0)
                lines.append(
                    f"    {MAGENTA}Best: +{best['feature_added']} "
                    f"(RankIC={best['mean_rank_ic']:.4f}){RESET}"
                )

        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Monitor regression tests")
    parser.add_argument("--once", action="store_true", help="Print once and exit")
    parser.add_argument("-i", "--interval", type=int, default=10, help="Refresh interval in seconds")
    args = parser.parse_args()

    if args.once:
        tests, steps = query_db()
        procs = get_process_info()
        print(render(tests, steps, procs))
        return

    try:
        while True:
            tests, steps = query_db()
            procs = get_process_info()
            output = render(tests, steps, procs)
            print(CLEAR + output, flush=True)

            # Auto-exit if nothing is running
            running = [t for t in tests if t["status"] == "running"]
            if not running and not procs:
                print(f"{DIM}No running tests. Exiting.{RESET}")
                break

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\n{DIM}Stopped.{RESET}")


if __name__ == "__main__":
    main()
