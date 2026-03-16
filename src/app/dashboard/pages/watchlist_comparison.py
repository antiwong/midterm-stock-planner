"""
Watchlist Comparison Dashboard
================================
Side-by-side performance comparison for all watchlists.
Shows regression results, Bayesian optimization, ensemble performance,
and daily signal tracking.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent


def _load_regression_results() -> Dict[str, Dict]:
    """Load regression test results for all watchlists."""
    reg_dir = PROJECT_ROOT / "output" / "regression"
    results = {}

    # Map known regression IDs to watchlists
    known = {
        "tech_giants": "reg_20260315_152332_a41646df",
        "semiconductors": "reg_20260316_231040_589d9271",
        "precious_metals": "reg_20260316_231050_b8ac8544",
        "moby_picks": "reg_20260316_231056_8f18975f",
    }

    for watchlist, reg_id in known.items():
        report_path = reg_dir / reg_id / "regression_report.json"
        if report_path.exists():
            with open(report_path) as f:
                data = json.load(f)
            results[watchlist] = data

    return results


def _load_optimization_reports() -> Dict[str, pd.DataFrame]:
    """Load Bayesian optimization reports."""
    reports_dir = PROJECT_ROOT / "output" / "reports"
    results = {}

    for path in reports_dir.glob("bayesian_optimization_*.md"):
        watchlist = path.stem.replace("bayesian_optimization_", "").replace("_20260316", "")
        results[watchlist] = path

    return results


def _load_ensemble_comparison() -> Optional[Dict]:
    """Load ensemble vs ML-only comparison results."""
    path = PROJECT_ROOT / "output" / "reports" / "ensemble_comparison_tech_giants.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def _load_stress_test() -> Optional[List[Dict]]:
    """Load stress test results."""
    path = PROJECT_ROOT / "output" / "reports" / "stress_test_risk_manager.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def _load_ticker_configs() -> Dict[str, Dict]:
    """Count per-ticker configs."""
    config_dir = PROJECT_ROOT / "config" / "tickers"
    configs = {}
    if config_dir.exists():
        for f in config_dir.glob("*.yaml"):
            if f.stem != "README":
                configs[f.stem] = True
    return configs


def render_watchlist_comparison():
    """Render the watchlist comparison dashboard."""
    st.title("Watchlist Comparison Dashboard")
    st.markdown("Side-by-side performance across all watchlists with regression, "
                "optimization, and ensemble results.")

    # --- Regression Results ---
    st.header("Regression Test Results")

    reg_results = _load_regression_results()
    if reg_results:
        # Summary table
        summary_data = []
        for wl, data in reg_results.items():
            test = data.get("test", {})
            steps = data.get("steps", [])
            baseline_sharpe = steps[0].get("sharpe_ratio", 0) if steps else 0
            summary_data.append({
                "Watchlist": wl,
                "Tickers": len(set(s.get("ticker", "") for s in steps[0].get("feature_columns_json", "[]") if isinstance(s, dict))) if steps else "?",
                "Baseline Sharpe": baseline_sharpe,
                "Peak Sharpe": max(s.get("sharpe_ratio", 0) or 0 for s in steps) if steps else 0,
                "Final Sharpe": test.get("final_sharpe", 0),
                "Final IC": test.get("final_rank_ic", 0),
                "Best Feature": test.get("best_feature", "?"),
                "Best Delta": test.get("best_marginal_sharpe", 0),
                "Duration (min)": round(test.get("duration_seconds", 0) / 60, 1),
            })

        df = pd.DataFrame(summary_data)
        st.dataframe(df.style.format({
            "Baseline Sharpe": "{:.2f}",
            "Peak Sharpe": "{:.2f}",
            "Final Sharpe": "{:.2f}",
            "Final IC": "{:.4f}",
            "Best Delta": "{:+.3f}",
        }), use_container_width=True)

        # Sharpe comparison chart
        fig = go.Figure()
        for _, row in df.iterrows():
            fig.add_trace(go.Bar(
                name=row["Watchlist"],
                x=["Baseline", "Peak", "Final"],
                y=[row["Baseline Sharpe"], row["Peak Sharpe"], row["Final Sharpe"]],
            ))
        fig.update_layout(
            title="Sharpe Ratio by Watchlist",
            barmode="group",
            yaxis_title="Sharpe Ratio",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Feature impact heatmap
        st.subheader("Feature Impact Across Watchlists")
        feature_data = {}
        for wl, data in reg_results.items():
            for step in data.get("steps", []):
                feature = step.get("feature_added", "")
                if feature and feature != "BASELINE":
                    delta = step.get("marginal_sharpe", 0) or 0
                    if feature not in feature_data:
                        feature_data[feature] = {}
                    feature_data[feature][wl] = delta

        if feature_data:
            heatmap_df = pd.DataFrame(feature_data).T
            fig = px.imshow(
                heatmap_df.values,
                x=heatmap_df.columns.tolist(),
                y=heatmap_df.index.tolist(),
                color_continuous_scale="RdYlGn",
                color_continuous_midpoint=0,
                labels={"color": "Marginal Sharpe"},
                title="Feature Impact Heatmap (Marginal Sharpe)",
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No regression results found. Run: `python scripts/run_regression_test.py run --watchlist <name>`")

    # --- Ensemble Comparison ---
    st.header("Ensemble vs ML-Only")

    ensemble = _load_ensemble_comparison()
    if ensemble:
        col1, col2, col3 = st.columns(3)
        ml = ensemble["ml_metrics"]
        ens = ensemble["ensemble_metrics"]

        col1.metric("ML-Only Sharpe", f"{ml['sharpe']:.3f}")
        col2.metric("Ensemble Sharpe", f"{ens['sharpe']:.3f}",
                     delta=f"+{((ens['sharpe']/ml['sharpe'])-1)*100:.1f}%")
        col3.metric("Verdict", ensemble["verdict"].split("—")[0].strip())

        # Comparison table
        comp_data = {
            "Metric": ["Sharpe", "Total Return", "Max Drawdown", "Win Rate", "Turnover"],
            "ML-Only": [f"{ml['sharpe']:.3f}", f"{ml['total_return']:.1%}",
                        f"{ml['max_drawdown']:.1%}", f"{ml['win_rate']:.1%}",
                        f"{ml['avg_turnover_per_rebalance']:.1f}"],
            "Ensemble": [f"{ens['sharpe']:.3f}", f"{ens['total_return']:.1%}",
                         f"{ens['max_drawdown']:.1%}", f"{ens['win_rate']:.1%}",
                         f"{ens['avg_turnover_per_rebalance']:.1f}"],
        }
        st.table(pd.DataFrame(comp_data))
    else:
        st.info("No ensemble comparison. Run: `python scripts/compare_ensemble.py --watchlist tech_giants`")

    # --- Stress Test ---
    st.header("Risk Manager Stress Test")

    stress = _load_stress_test()
    if stress:
        stress_data = []
        for s in stress:
            stress_data.append({
                "Scenario": s["scenario"],
                "Days": s["days"],
                "Return": f"{s['total_return']:+.1%}",
                "Max DD": f"{s['max_drawdown']:+.1%}",
                "Halted": "YES" if s["halted"] else "no",
                "Liquidated": "YES" if s["liquidated"] else "no",
                "Day Triggered": s.get("halted_day") or s.get("liquidated_day") or "-",
                "Without Rules": f"${s['value_without_rules']:,.0f}",
                "With Rules": f"${s['value_at_exit']:,.0f}",
            })
        st.dataframe(pd.DataFrame(stress_data), use_container_width=True)

        # Chart: with vs without rules
        fig = go.Figure()
        names = [s["scenario"] for s in stress]
        with_rules = [s["value_at_exit"] for s in stress]
        without_rules = [s["value_without_rules"] for s in stress]
        fig.add_trace(go.Bar(name="With Risk Rules", x=names, y=with_rules, marker_color="green"))
        fig.add_trace(go.Bar(name="Without Rules", x=names, y=without_rules, marker_color="red"))
        fig.add_hline(y=100000, line_dash="dash", annotation_text="Initial $100K")
        fig.update_layout(title="Portfolio Value: With vs Without Risk Rules",
                          barmode="group", yaxis_title="Portfolio Value ($)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No stress test results. Run: `python scripts/stress_test_risk.py`")

    # --- Trigger Config Coverage ---
    st.header("Per-Ticker Optimization Coverage")

    import yaml
    wl_path = PROJECT_ROOT / "config" / "watchlists.yaml"
    if wl_path.exists():
        with open(wl_path) as f:
            watchlists = yaml.safe_load(f)
        wls = watchlists.get("watchlists", watchlists)
        configs = _load_ticker_configs()

        coverage_data = []
        for name in ["moby_picks", "tech_giants", "semiconductors", "precious_metals"]:
            wl = wls.get(name, {})
            symbols = wl.get("symbols", [])
            with_config = sum(1 for s in symbols if s in configs)
            coverage_data.append({
                "Watchlist": name,
                "Total Tickers": len(symbols),
                "With Trigger Config": with_config,
                "Coverage": f"{with_config/len(symbols):.0%}" if symbols else "0%",
            })

        st.dataframe(pd.DataFrame(coverage_data), use_container_width=True)

    # --- Daily Cron Schedule ---
    st.header("Daily Automation")
    st.markdown("""
    | Time (ET) | Job | Status |
    |-----------|-----|--------|
    | 5:30 PM | `moby_picks` — Alpaca paper trading (ensemble + tier weights) | **Primary** |
    | 5:45 PM | `tech_giants` — local sim analysis | Tracking |
    | 5:50 PM | `semiconductors` — local sim analysis | Tracking |
    | 5:55 PM | `precious_metals` — local sim analysis | Tracking |
    | 6:00 PM | Sentiment download (Finnhub + EODHD) + scoring | Accumulating |
    """)
