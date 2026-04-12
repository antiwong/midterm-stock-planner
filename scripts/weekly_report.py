#!/usr/bin/env python3
"""Weekly quantstats report for all paper-trading portfolios.

Runs as the last step of the Sunday retrain cron. Reads daily_snapshots
(populated by run_daily_fast.py + backfill_snapshots.py), generates:
  - per-portfolio HTML tear sheets  -> reports/weekly_YYYY-MM-DD/<wl>.html
  - combined comparison HTML         -> reports/weekly_YYYY-MM-DD/comparison.html
  - weekly Slack summary to #stock-planner with W-o-W deltas
  - stats.json                       -> for next week's diff

Usage:
    python scripts/weekly_report.py               # dry-run (print Slack payload, no post)
    python scripts/weekly_report.py --post        # post to Slack
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
load_dotenv(ROOT / ".env")

# watchlist -> benchmark ticker. Matches backfill_snapshots.PORTFOLIOS.
PORTFOLIOS: dict[str, str] = {
    "moby_picks":        "SPY",
    "tech_giants":       "SPY",
    "semiconductors":    "SPY",
    "precious_metals":   "SPY",
    "sg_reits":          "ES3.SI",
    "sg_blue_chips":     "ES3.SI",
    "anthony_watchlist": "SPY",
    "sp500":             "SPY",
    "clean_energy":      "SPY",
    "etfs":              "SPY",
}

SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL") or os.environ.get("slack_webhook")


@dataclass
class PortfolioStats:
    watchlist: str
    benchmark: str
    days: int
    cum_return: float
    cum_benchmark: float
    vs_benchmark: float   # cum_return - cum_benchmark
    sharpe: float
    sortino: float
    max_dd: float
    win_rate: float
    jensen_alpha: Optional[float]  # annualised; nullable at small samples
    beta: Optional[float]


def load_returns(wl: str) -> Optional[pd.Series]:
    """Return daily returns series (pct_change of portfolio_value) keyed by date.

    Returns None if fewer than 2 snapshots exist (can't compute a return).
    """
    db = DATA_DIR / f"paper_trading_{wl}.db"
    if not db.exists():
        return None
    with sqlite3.connect(db) as conn:
        df = pd.read_sql_query(
            "SELECT date, portfolio_value FROM daily_snapshots "
            "WHERE portfolio_value > 0 ORDER BY date",
            conn,
            parse_dates=["date"],
        )
    if len(df) < 2:
        return None
    df = df.set_index("date").sort_index()
    # tz-naive for quantstats
    df.index = df.index.tz_localize(None) if df.index.tz else df.index
    returns = df["portfolio_value"].pct_change().dropna()
    returns.name = wl
    return returns


def fetch_bench_returns(benchmark: str, index: pd.DatetimeIndex) -> pd.Series:
    start = index.min() - pd.Timedelta(days=5)
    end = index.max() + pd.Timedelta(days=1)
    data = yf.download(
        benchmark,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        auto_adjust=False,
        progress=False,
    )
    closes = data["Close"]
    if isinstance(closes, pd.DataFrame):
        closes = closes.iloc[:, 0]
    closes.index = pd.to_datetime(closes.index).tz_localize(None)
    returns = closes.pct_change().dropna()
    returns.name = benchmark
    # Align to portfolio's return index
    return returns.reindex(index).dropna()


def compute_stats(wl: str, benchmark: str, returns: pd.Series,
                  bench_returns: pd.Series) -> PortfolioStats:
    import quantstats as qs
    idx = returns.index.intersection(bench_returns.index)
    r = returns.loc[idx]
    b = bench_returns.loc[idx]

    cum_r = float((1 + r).prod() - 1)
    cum_b = float((1 + b).prod() - 1)
    sharpe = float(qs.stats.sharpe(r)) if len(r) >= 2 else float("nan")
    sortino = float(qs.stats.sortino(r)) if len(r) >= 2 else float("nan")
    max_dd = float(qs.stats.max_drawdown(r))
    win_rate = float(qs.stats.win_rate(r))

    # Jensen's alpha / beta via CAPM regression — only meaningful with variance
    alpha = beta = None
    if len(r) >= 5 and b.std() > 0:
        try:
            greeks = qs.stats.greeks(r, b)
            alpha = float(greeks["alpha"])
            beta = float(greeks["beta"])
        except Exception:
            pass

    return PortfolioStats(
        watchlist=wl, benchmark=benchmark, days=len(r),
        cum_return=cum_r, cum_benchmark=cum_b, vs_benchmark=cum_r - cum_b,
        sharpe=sharpe, sortino=sortino, max_dd=max_dd, win_rate=win_rate,
        jensen_alpha=alpha, beta=beta,
    )


def generate_tearsheet(wl: str, benchmark: str, returns: pd.Series,
                       bench_returns: pd.Series, out_path: Path) -> None:
    import quantstats as qs
    qs.extend_pandas()
    idx = returns.index.intersection(bench_returns.index)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    qs.reports.html(
        returns.loc[idx],
        benchmark=bench_returns.loc[idx],
        output=str(out_path),
        title=f"{wl} — weekly tear sheet vs {benchmark}",
    )


def generate_comparison_html(stats: list[PortfolioStats], report_date: str,
                             out_path: Path) -> None:
    rows = []
    for s in sorted(stats, key=lambda x: -x.cum_return):
        alpha_disp = f"{s.jensen_alpha*100:+.2f}%" if s.jensen_alpha is not None else "—"
        beta_disp = f"{s.beta:.2f}" if s.beta is not None else "—"
        rows.append(f"""
          <tr>
            <td><a href="{s.watchlist}.html">{s.watchlist}</a></td>
            <td>{s.benchmark}</td>
            <td>{s.days}</td>
            <td class="{'pos' if s.cum_return >= 0 else 'neg'}">{s.cum_return*100:+.2f}%</td>
            <td>{s.cum_benchmark*100:+.2f}%</td>
            <td class="{'pos' if s.vs_benchmark >= 0 else 'neg'}">{s.vs_benchmark*100:+.2f}%</td>
            <td>{s.sharpe:.2f}</td>
            <td>{s.sortino:.2f}</td>
            <td class="neg">{s.max_dd*100:+.2f}%</td>
            <td>{s.win_rate*100:.0f}%</td>
            <td>{alpha_disp}</td>
            <td>{beta_disp}</td>
          </tr>""")
    html = f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>Weekly comparison — {report_date}</title>
<style>
body {{ font-family: -apple-system,system-ui,sans-serif; max-width: 1100px; margin: 2em auto; padding: 0 1em; }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
th, td {{ padding: 8px 12px; text-align: right; border-bottom: 1px solid #ddd; }}
th {{ background: #f5f5f5; text-align: left; }}
td:first-child, th:first-child {{ text-align: left; }}
td:nth-child(2), td:nth-child(3) {{ text-align: center; }}
.pos {{ color: #0a7a0a; }}
.neg {{ color: #b71c1c; }}
.note {{ color: #666; font-size: 12px; margin-top: 2em; }}
</style></head><body>
<h1>Weekly portfolio comparison — {report_date}</h1>
<p>Sorted by cumulative return (descending).</p>
<table>
  <thead><tr>
    <th>Portfolio</th><th>Bench</th><th>Days</th>
    <th>Return</th><th>Bench Ret</th><th>vs Bench</th>
    <th>Sharpe</th><th>Sortino</th><th>MaxDD</th><th>Win%</th>
    <th>Alpha</th><th>Beta</th>
  </tr></thead>
  <tbody>{"".join(rows)}</tbody>
</table>
<p class="note">
Sample sizes are tiny (typically &lt; 20 trading days). Sharpe/Sortino/Alpha are
annualised and not statistically meaningful at this horizon — directional only.
Click a portfolio name for its full quantstats tear sheet.
</p>
</body></html>"""
    out_path.write_text(html)


def format_slack_message(stats: list[PortfolioStats], report_date: str,
                         prev_stats: dict[str, dict], excluded: list[str]) -> str:
    def fmt_delta(curr: float, prev: Optional[float], pct: bool = True,
                  digits: int = 2) -> str:
        if prev is None or not np.isfinite(prev):
            return ""
        delta = curr - prev
        if pct:
            return f" ({delta*100:+.{digits}f}pp)"
        return f" ({delta:+.{digits}f})"

    # Sort for table: best excess vs benchmark first
    sorted_stats = sorted(stats, key=lambda s: -s.vs_benchmark)
    # Column widths chosen so it renders cleanly in Slack's monospace
    header = (
        f"| {'Portfolio':<17} | {'Return':>8} | {'vs Bench':>8} | "
        f"{'Sharpe':>6} | {'MaxDD':>6} | {'Win%':>5} |"
    )
    sep = "|" + "-" * (len(header) - 2) + "|"
    lines = [header, sep]
    for s in sorted_stats:
        prev = prev_stats.get(s.watchlist, {})
        ret_d = fmt_delta(s.cum_return, prev.get("cum_return"))
        vs_d = fmt_delta(s.vs_benchmark, prev.get("vs_benchmark"))
        sh_d = fmt_delta(s.sharpe, prev.get("sharpe"), pct=False, digits=2)
        lines.append(
            f"| {s.watchlist:<17} | {s.cum_return*100:>+7.2f}% | "
            f"{s.vs_benchmark*100:>+7.2f}% | {s.sharpe:>6.2f} | "
            f"{s.max_dd*100:>+5.1f}% | {s.win_rate*100:>4.0f}% |"
        )

    table = "\n".join(lines)

    beating = sum(1 for s in stats if s.vs_benchmark > 0)
    losing = len(stats) - beating
    best = max(stats, key=lambda s: s.cum_return) if stats else None
    worst = min(stats, key=lambda s: s.cum_return) if stats else None
    bottom = (
        f"*Bottom line:* {beating} beating benchmark, {losing} underperforming.\n"
        f"*Best:* {best.watchlist} {best.cum_return*100:+.2f}%  "
        f"*Worst:* {worst.watchlist} {worst.cum_return*100:+.2f}%"
    ) if best and worst else ""

    ex_line = ""
    if excluded:
        ex_line = "\n_" + ", ".join(excluded) + ": insufficient data (< 2 snapshots) — will resume next Sunday_"

    header_line = f"*Weekly Portfolio Summary — {report_date}*"
    return f"{header_line}\n```\n{table}\n```\n{bottom}{ex_line}"


def post_slack(text: str) -> bool:
    if not SLACK_WEBHOOK:
        print("  [slack] no webhook configured — skipping post")
        return False
    try:
        r = requests.post(SLACK_WEBHOOK, json={"text": text, "channel": "#stock-planner"},
                          timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"  [slack] post failed: {e}")
        return False


def find_previous_stats(current_dir: Path) -> dict[str, dict]:
    """Load the most recent prior week's stats.json, if any."""
    weeklies = sorted(REPORTS_DIR.glob("weekly_*/stats.json"))
    weeklies = [w for w in weeklies if w.parent != current_dir]
    if not weeklies:
        return {}
    latest = weeklies[-1]
    print(f"  [diff] comparing vs {latest.parent.name}")
    with open(latest) as f:
        data = json.load(f)
    return {s["watchlist"]: s for s in data.get("stats", [])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", action="store_true",
                    help="Actually post to Slack (default: dry-run print only)")
    ap.add_argument("--date", default=None,
                    help="Report date YYYY-MM-DD (default: today)")
    args = ap.parse_args()

    report_date = args.date or datetime.now().strftime("%Y-%m-%d")
    out_dir = REPORTS_DIR / f"weekly_{report_date}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Weekly report — {report_date} ===")
    print(f"  output dir: {out_dir.relative_to(ROOT)}")

    prev_stats = find_previous_stats(out_dir)

    all_stats: list[PortfolioStats] = []
    excluded: list[str] = []
    for wl, bench in PORTFOLIOS.items():
        returns = load_returns(wl)
        if returns is None or len(returns) < 2:
            print(f"  {wl:20s} excluded (insufficient snapshots)")
            excluded.append(wl)
            continue
        bench_r = fetch_bench_returns(bench, returns.index)
        idx = returns.index.intersection(bench_r.index)
        if len(idx) < 2:
            print(f"  {wl:20s} excluded (no overlapping benchmark days)")
            excluded.append(wl)
            continue

        stats = compute_stats(wl, bench, returns, bench_r)
        all_stats.append(stats)

        tearsheet_path = out_dir / f"{wl}.html"
        try:
            generate_tearsheet(wl, bench, returns, bench_r, tearsheet_path)
            tear_ok = "✓"
        except Exception as e:
            tear_ok = f"tearsheet-FAIL ({e})"
        print(f"  {wl:20s} days={stats.days:2d}  cum={stats.cum_return*100:+5.2f}%  "
              f"vs {bench}={stats.vs_benchmark*100:+5.2f}%  Sharpe={stats.sharpe:5.2f}  {tear_ok}")

    if not all_stats:
        print("\nNo portfolios to report on. Exiting.")
        return

    # Combined comparison HTML
    generate_comparison_html(all_stats, report_date, out_dir / "comparison.html")
    print(f"\n  wrote comparison.html")

    # Save stats.json for next week's diff
    with open(out_dir / "stats.json", "w") as f:
        json.dump(
            {"report_date": report_date, "stats": [asdict(s) for s in all_stats]},
            f, indent=2, default=lambda x: None if isinstance(x, float) and not np.isfinite(x) else x,
        )

    # Slack
    msg = format_slack_message(all_stats, report_date, prev_stats, excluded)
    print("\n--- Slack payload ---")
    print(msg)
    print("--- end payload ---")

    if args.post:
        if post_slack(msg):
            print("\n  [slack] posted ✓")
    else:
        print("\n  [dry-run] NOT posted — pass --post to fire for real")


if __name__ == "__main__":
    main()
