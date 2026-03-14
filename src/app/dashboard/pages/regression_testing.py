"""
Regression Testing Page
========================
Browse, inspect, and launch feature regression tests.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ..components.sidebar import render_page_header, render_section_header
from ..components.loading import operation_with_feedback
from ..data import get_all_available_watchlists
from ..utils import get_project_root
from ..config import COLORS, CHART_COLORS


def _safe_json_loads(value) -> Optional[dict | list]:
    """Safely parse a JSON string, returning None on failure."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def _get_db():
    """Get a RegressionDatabase instance."""
    from src.regression.database import RegressionDatabase
    db_path = str(get_project_root() / "data" / "runs.db")
    return RegressionDatabase(db_path=db_path)


def _status_badge(status: str) -> str:
    """Return an HTML badge for a regression test status."""
    color_map = {
        "completed": COLORS["success"],
        "running": COLORS["info"],
        "failed": COLORS["danger"],
    }
    color = color_map.get(status, COLORS["muted"])
    return f'<span style="background:{color}; padding:2px 8px; border-radius:8px; font-size:0.8rem;">{status}</span>'


def _guard_light(value: Optional[float], threshold_warn: float, threshold_fail: float, higher_is_better: bool = True) -> str:
    """Return a traffic-light emoji based on guard metric thresholds."""
    if value is None:
        return "---"
    if higher_is_better:
        if value >= threshold_warn:
            return "🟢"
        elif value >= threshold_fail:
            return "🟡"
        else:
            return "🔴"
    else:
        if value <= threshold_warn:
            return "🟢"
        elif value <= threshold_fail:
            return "🟡"
        else:
            return "🔴"


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_regression_testing():
    """Render the regression testing page."""
    render_page_header(
        "Regression Testing",
        "Browse feature regression tests, inspect step-by-step results, and launch new tests"
    )

    st.markdown("""
    <div style="background: {bg}; padding: 1.25rem; border-radius: 12px; border-left: 4px solid {primary}; margin-bottom: 1.5rem;">
        <p style="margin: 0; color: {muted}; font-size: 0.9rem;">
            Feature regression testing adds features one-by-one, measures marginal contribution
            to Sharpe and Rank IC, and identifies which features genuinely improve model performance.
        </p>
    </div>
    """.format(
        bg=COLORS['light'],
        primary=COLORS['primary'],
        muted=COLORS['muted']
    ), unsafe_allow_html=True)

    try:
        db = _get_db()
    except Exception as e:
        st.error(f"Failed to connect to regression database: {e}")
        return

    # Auto-refresh if any test is running
    try:
        all_tests = db.list_regression_tests()
        running = [t for t in all_tests if t.get("status") == "running"]
        if running:
            st.info(f"**Live monitoring**: {len(running)} test(s) running. Click **Refresh** below to check progress.")
            if st.button("🔄 Refresh", key="reg_refresh"):
                st.rerun()
    except Exception:
        pass

    # --- Test Browser ---
    _render_test_browser(db)

    # --- New Test Launcher ---
    with st.expander("Launch New Regression Test", expanded=False):
        _render_test_launcher()


def _render_test_browser(db):
    """List all regression tests and show detail for the selected one."""
    render_section_header("Test Browser")

    try:
        tests = db.list_regression_tests()
    except Exception as e:
        st.error(f"Failed to load regression tests: {e}")
        return

    if not tests:
        st.info("No regression tests found. Launch one below.")
        return

    # Build summary table
    rows = []
    for t in tests:
        status = t.get("status", "")
        # For running tests, count completed steps from DB
        step_count = t.get("total_steps", 0)
        if status == "running":
            try:
                steps = db.get_regression_steps(t.get("regression_id", ""))
                step_count = len(steps)
            except Exception:
                pass
        rows.append({
            "Name": t.get("name", ""),
            "Status": status,
            "Date": (t.get("created_at") or "")[:19],
            "Steps": step_count,
            "Final Sharpe": t.get("final_sharpe"),
            "Final Rank IC": t.get("final_rank_ic"),
            "Best Feature": t.get("best_feature", ""),
            "Duration (s)": round(t.get("duration_seconds") or 0, 1),
            "regression_id": t.get("regression_id", ""),
        })

    df_tests = pd.DataFrame(rows)

    # Display table (without regression_id column)
    display_cols = [c for c in df_tests.columns if c != "regression_id"]
    st.dataframe(
        df_tests[display_cols],
        use_container_width=True,
        hide_index=True,
    )

    # Select a test
    test_options = {f"{r['Name']}  ({r['Date']})": r["regression_id"] for r in rows}
    if not test_options:
        return

    selected_label = st.selectbox(
        "Select test for details",
        options=list(test_options.keys()),
        key="reg_test_select",
    )
    selected_id = test_options[selected_label]

    # --- Detail View ---
    _render_test_detail(db, selected_id)


def _render_test_detail(db, regression_id: str):
    """Render detailed view for a single regression test."""
    test = db.get_regression_test(regression_id)
    if not test:
        st.warning("Test not found.")
        return

    steps = db.get_regression_steps(regression_id)
    leaderboard = db.get_feature_leaderboard(regression_id)

    # --- Summary metrics ---
    render_section_header("Summary")

    baseline_sharpe = None
    if steps:
        baseline_sharpe = steps[0].get("sharpe_ratio")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Baseline Sharpe",
            f"{baseline_sharpe:.4f}" if baseline_sharpe is not None else "N/A",
        )
    with col2:
        final_sharpe = test.get("final_sharpe")
        delta = None
        if final_sharpe is not None and baseline_sharpe is not None:
            delta = f"{final_sharpe - baseline_sharpe:+.4f}"
        st.metric(
            "Final Sharpe",
            f"{final_sharpe:.4f}" if final_sharpe is not None else "N/A",
            delta=delta,
        )
    with col3:
        st.metric("Best Feature", test.get("best_feature") or "N/A")
    with col4:
        duration = test.get("duration_seconds")
        if duration is not None:
            mins, secs = divmod(int(duration), 60)
            st.metric("Total Duration", f"{mins}m {secs}s")
        else:
            st.metric("Total Duration", "N/A")

    if not steps:
        st.info("No steps recorded for this test.")
        return

    # --- Step-by-step table ---
    render_section_header("Step-by-Step Results")

    step_rows = []
    for s in steps:
        sig = _safe_json_loads(s.get("significance_json"))
        p_value = None
        is_significant = None
        if sig:
            p_value = sig.get("sharpe_p_value") or sig.get("p_value")
            is_significant = sig.get("is_significant")

        step_rows.append({
            "Step": s.get("step_number", 0),
            "Feature": s.get("feature_added", ""),
            "Sharpe": s.get("sharpe_ratio"),
            "Rank IC": s.get("mean_rank_ic"),
            "Marginal Sharpe": s.get("marginal_sharpe"),
            "Marginal IC": s.get("marginal_rank_ic"),
            "p-value": round(p_value, 4) if p_value is not None else None,
            "Significant?": "Yes" if is_significant else ("No" if is_significant is not None else ""),
        })

    df_steps = pd.DataFrame(step_rows)
    st.dataframe(df_steps, use_container_width=True, hide_index=True)

    # --- Cumulative performance chart ---
    render_section_header("Cumulative Performance")

    fig_perf = go.Figure()
    fig_perf.add_trace(go.Scatter(
        x=df_steps["Step"],
        y=df_steps["Sharpe"],
        mode="lines+markers",
        name="Sharpe Ratio",
        line=dict(color=CHART_COLORS["categorical"][0], width=2),
        marker=dict(size=8),
    ))
    fig_perf.add_trace(go.Scatter(
        x=df_steps["Step"],
        y=df_steps["Rank IC"],
        mode="lines+markers",
        name="Rank IC",
        yaxis="y2",
        line=dict(color=CHART_COLORS["categorical"][1], width=2),
        marker=dict(size=8),
    ))
    fig_perf.update_layout(
        xaxis_title="Step",
        yaxis_title="Sharpe Ratio",
        yaxis2=dict(title="Rank IC", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
        margin=dict(t=30, b=40),
        hovermode="x unified",
    )
    # Add feature labels on x-axis
    fig_perf.update_xaxes(
        tickvals=df_steps["Step"].tolist(),
        ticktext=df_steps["Feature"].tolist(),
        tickangle=45,
    )
    st.plotly_chart(fig_perf, use_container_width=True)

    # --- Feature leaderboard bar chart ---
    render_section_header("Feature Leaderboard")

    if leaderboard:
        df_lb = pd.DataFrame(leaderboard)
        if "marginal_sharpe" in df_lb.columns and "feature_name" in df_lb.columns:
            df_lb = df_lb.sort_values("marginal_sharpe", ascending=True)
            fig_lb = px.bar(
                df_lb,
                x="marginal_sharpe",
                y="feature_name",
                orientation="h",
                title="Marginal Sharpe Contribution by Feature",
                color="marginal_sharpe",
                color_continuous_scale=["#ef4444", "#fbbf24", "#10b981"],
            )
            fig_lb.update_layout(
                yaxis_title="",
                xaxis_title="Marginal Sharpe",
                height=max(300, len(df_lb) * 35),
                margin=dict(t=40, b=30),
            )
            st.plotly_chart(fig_lb, use_container_width=True)
        else:
            st.caption("Leaderboard data missing expected columns.")
    else:
        st.caption("No feature leaderboard data for this test.")

    # --- Feature importance heatmap ---
    render_section_header("Feature Importance Heatmap")

    importance_data = []
    for s in steps:
        fi = _safe_json_loads(s.get("feature_importance_json"))
        if fi:
            for feat, imp in fi.items():
                importance_data.append({
                    "Step": s.get("step_number", 0),
                    "Feature Added": s.get("feature_added", ""),
                    "Column": feat,
                    "Importance": imp,
                })

    if importance_data:
        df_imp = pd.DataFrame(importance_data)
        pivot = df_imp.pivot_table(
            index="Column",
            columns="Feature Added",
            values="Importance",
            aggfunc="first",
        )
        # Order columns by step order
        step_order = [s.get("feature_added", "") for s in steps if s.get("feature_added")]
        ordered_cols = [c for c in step_order if c in pivot.columns]
        remaining = [c for c in pivot.columns if c not in ordered_cols]
        pivot = pivot[ordered_cols + remaining]

        fig_hm = px.imshow(
            pivot.values,
            x=list(pivot.columns),
            y=list(pivot.index),
            color_continuous_scale=CHART_COLORS["heatmap"],
            aspect="auto",
            labels=dict(color="Importance"),
        )
        fig_hm.update_layout(
            height=max(350, len(pivot.index) * 22),
            margin=dict(t=20, b=30),
            xaxis_title="Step (Feature Added)",
            yaxis_title="Feature Column",
        )
        st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.caption("No feature importance data available.")

    # --- Guard metric status ---
    render_section_header("Guard Metric Status")

    if steps:
        last_step = steps[-1]
        metrics = _safe_json_loads(last_step.get("metrics_json")) or {}

        guard_items = [
            ("Sharpe Ratio", metrics.get("sharpe_ratio"), 0.5, 0.0, True),
            ("Rank IC", metrics.get("mean_rank_ic"), 0.03, 0.0, True),
            ("Max Drawdown", metrics.get("max_drawdown"), -0.15, -0.25, False),
            ("Hit Rate", metrics.get("hit_rate"), 0.52, 0.48, True),
            ("Turnover", metrics.get("turnover"), 0.3, 0.5, False),
        ]

        cols = st.columns(len(guard_items))
        for col, (label, value, thresh_w, thresh_f, higher_better) in zip(cols, guard_items):
            with col:
                light = _guard_light(value, thresh_w, thresh_f, higher_better)
                formatted = f"{value:.4f}" if value is not None else "N/A"
                st.markdown(
                    f"**{label}**  {light}<br/>`{formatted}`",
                    unsafe_allow_html=True,
                )

    # --- Tuned parameters table ---
    render_section_header("Tuned Parameters")

    tuned_rows = []
    for s in steps:
        tp = _safe_json_loads(s.get("tuned_params_json"))
        if tp:
            for param, val in tp.items():
                tuned_rows.append({
                    "Step": s.get("step_number", 0),
                    "Feature": s.get("feature_added", ""),
                    "Parameter": param,
                    "Value": val,
                })

    if tuned_rows:
        df_tuned = pd.DataFrame(tuned_rows)
        st.dataframe(df_tuned, use_container_width=True, hide_index=True)
    else:
        st.caption("No tuned parameters recorded.")


# ---------------------------------------------------------------------------
# New Test Launcher
# ---------------------------------------------------------------------------

def _render_test_launcher():
    """Render the new test launcher form."""
    render_section_header("Configure New Regression Test")

    watchlists = get_all_available_watchlists()
    watchlist_options = list(watchlists.keys()) if watchlists else []

    col1, col2 = st.columns(2)
    with col1:
        watchlist = st.selectbox(
            "Watchlist",
            options=watchlist_options,
            index=0 if watchlist_options else 0,
            key="reg_launch_watchlist",
            help="Stock universe for the regression test",
        )
    with col2:
        tune = st.toggle(
            "Enable parameter tuning",
            value=True,
            key="reg_launch_tune",
            help="Tune feature parameters at each step (slower but more accurate)",
        )

    # Feature checkboxes
    st.markdown("**Features to test:**")
    from src.regression.feature_registry import DEFAULT_FEATURE_ORDER

    feature_cols = st.columns(4)
    selected_features = []
    for i, feat in enumerate(DEFAULT_FEATURE_ORDER):
        with feature_cols[i % 4]:
            if st.checkbox(feat, value=True, key=f"reg_feat_{feat}"):
                selected_features.append(feat)

    col_trials, _ = st.columns(2)
    with col_trials:
        tuning_trials = st.number_input(
            "Tuning trials",
            min_value=10,
            max_value=200,
            value=30,
            key="reg_launch_trials",
            help="Number of Bayesian optimization trials per step",
            disabled=not tune,
        )

    if st.button("Run Regression Test", type="primary", key="reg_launch_run"):
        if not watchlist:
            st.error("Please select a watchlist.")
            return
        if not selected_features:
            st.error("Please select at least one feature.")
            return

        output_area = st.empty()
        cmd = [
            "python", "scripts/run_regression_test.py",
            "--watchlist", watchlist,
            "--features", *selected_features,
        ]
        if tune:
            cmd.extend(["--tune", "--tuning-trials", str(tuning_trials)])

        with operation_with_feedback("Running Regression Test", show_progress=True):
            returncode, output = _run_script_sync(cmd, output_area)

        if returncode == 0:
            st.success("Regression test completed! Refresh the page to see results.")
            st.cache_data.clear()
        else:
            st.error(f"Regression test failed with code {returncode}")


def _run_script_sync(cmd: list, placeholder) -> tuple:
    """Run a script synchronously with live output."""
    import os
    try:
        cwd = str(get_project_root())
        env = os.environ.copy()
        env['PYTHONPATH'] = cwd + os.pathsep + env.get('PYTHONPATH', '')
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd,
            env=env,
        )
        output_lines = []
        for line in iter(process.stdout.readline, ''):
            output_lines.append(line)
            placeholder.code(''.join(output_lines[-30:]), language='text')
        process.wait()
        return process.returncode, ''.join(output_lines)
    except Exception as e:
        return -1, f"Error: {str(e)}"
