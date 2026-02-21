"""
Strategy Optimizer Page
=======================
Run evolutionary backtest, diversified backtest, lineage report, and strengthen recommendations.
"""

import json
import subprocess
from pathlib import Path

import streamlit as st

from ..components.sidebar import render_page_header, render_section_header
from ..components.loading import operation_with_feedback
from ..data import (
    get_all_available_watchlists,
    get_runs_with_folders,
)
from ..utils import get_project_root
from ..config import COLORS


def render_strategy_optimizer():
    """Render the strategy optimizer page with evolutionary, diversified, lineage, and strengthen tools."""
    render_page_header(
        "Strategy Optimizer",
        "Evolutionary backtest, diversified strategies, lineage report, and risk strengthening"
    )

    st.markdown("""
    <div style="background: {bg}; padding: 1.25rem; border-radius: 12px; border-left: 4px solid {primary}; margin-bottom: 1.5rem;">
        <p style="margin: 0; color: {muted}; font-size: 0.9rem;">
            Run advanced backtest workflows: evolve config params, compare strategy templates,
            inspect run lineage, and strengthen portfolio recommendations with risk analysis.
        </p>
    </div>
    """.format(
        bg=COLORS['light'],
        primary=COLORS['primary'],
        muted=COLORS['muted']
    ), unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "🧬 Evolutionary Backtest",
        "📊 Diversified Backtest",
        "🔗 Lineage Report",
        "🛡️ Strengthen Recommendations",
    ])

    with tab1:
        _render_evolutionary_tab()
    with tab2:
        _render_diversified_tab()
    with tab3:
        _render_lineage_tab()
    with tab4:
        _render_strengthen_tab()


def _render_evolutionary_tab():
    """Evolutionary strategy optimizer: mutate backtest params, evolve by fitness."""
    render_section_header("Evolutionary Strategy Optimizer")
    st.markdown("""
    Evolves backtest config params (train_years, rebalance_freq, top_n, etc.) via mutation and crossover.
    Fitness = Sharpe (or total_return, hit_rate). Exports best config to YAML.
    """)

    watchlists = get_all_available_watchlists()
    watchlist_options = list(watchlists.keys()) if watchlists else []
    default_wl = watchlist_options[0] if watchlist_options else None

    col1, col2, col3 = st.columns(3)
    with col1:
        watchlist = st.selectbox(
            "Watchlist",
            options=watchlist_options,
            index=0 if default_wl else 0,
            key="evo_watchlist",
            help="Stock universe for backtest",
        )
    with col2:
        generations = st.number_input(
            "Generations",
            min_value=2,
            max_value=20,
            value=5,
            key="evo_generations",
            help="Number of evolutionary generations",
        )
    with col3:
        population = st.number_input(
            "Population",
            min_value=4,
            max_value=20,
            value=8,
            key="evo_population",
            help="Population size per generation",
        )

    col4, col5 = st.columns(2)
    with col4:
        metric = st.selectbox(
            "Fitness Metric",
            options=["sharpe_ratio", "total_return", "hit_rate"],
            index=0,
            key="evo_metric",
            help="Metric to maximize",
        )
    with col5:
        save_path = st.text_input(
            "Save best config to (optional)",
            value="output/evolutionary_best.yaml",
            key="evo_save",
            help="YAML path for best config export",
        )

    if st.button("▶️ Run Evolutionary Backtest", type="primary", key="run_evo"):
        if not watchlist:
            st.error("Please select a watchlist.")
            return
        output_area = st.empty()
        cmd = [
            "python", "scripts/evolutionary_backtest.py",
            "--watchlist", watchlist,
            "--generations", str(generations),
            "--population", str(population),
            "--metric", metric,
            "--save", save_path or "output/evolutionary_best.yaml",
        ]
        with operation_with_feedback("Running Evolutionary Backtest", show_progress=True):
            returncode, output = _run_script_sync(cmd, output_area)
        if returncode == 0:
            st.success("✅ Evolutionary backtest completed! Best config exported.")
            st.cache_data.clear()
        else:
            st.error(f"❌ Failed with code {returncode}")

    # View results
    st.markdown("---")
    render_section_header("View Evolutionary Results")
    evo_dir = get_project_root() / "output" / "evolutionary"
    if evo_dir.exists():
        evo_files = sorted(evo_dir.glob("evolutionary_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if evo_files:
            selected = st.selectbox(
                "Select run",
                options=[f.name for f in evo_files],
                key="evo_view_select",
            )
            if selected:
                path = evo_dir / selected
                try:
                    with open(path) as f:
                        trajectories = json.load(f)
                    if trajectories:
                        # Best by fitness (skip failed runs with fitness -1e9)
                        valid = [t for t in trajectories if t.get("fitness", -1e9) > -1e8]
                        best = max(valid, key=lambda t: t.get("fitness", -1e9)) if valid else trajectories[-1]
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Best config**")
                            pv = best.get("param_vector", {})
                            for k, v in pv.items():
                                st.write(f"- **{k}:** {v}")
                        with col2:
                            st.markdown("**Best metrics**")
                            m = best.get("metrics", {})
                            if m:
                                for k, v in m.items():
                                    if isinstance(v, float):
                                        st.write(f"- **{k}:** {v:.4f}" if abs(v) < 1e6 else f"- **{k}:** {v:.2e}")
                                    else:
                                        st.write(f"- **{k}:** {v}")
                            else:
                                st.caption("No metrics (run may have failed)")
                        with st.expander("All trajectories"):
                            import pandas as pd
                            rows = []
                            for t in trajectories:
                                m = t.get("metrics", {}) or {}
                                rows.append({
                                    "run_id": t.get("run_id", "")[:16],
                                    "gen": t.get("generation", 0),
                                    "fitness": t.get("fitness"),
                                    "sharpe": m.get("sharpe_ratio"),
                                    "return": m.get("total_return"),
                                    "mutation": t.get("mutation_type", ""),
                                })
                            if rows:
                                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"Failed to load: {e}")
        else:
            st.caption("No evolutionary runs yet. Run one above.")
    else:
        st.caption("No output/evolutionary folder yet.")


def _render_diversified_tab():
    """Diversified strategy backtest: run templates, correlation matrix, select diverse subset."""
    render_section_header("Diversified Strategy Backtest")
    st.markdown("""
    Runs multiple strategy templates (value_tilt, momentum_tilt, quality_tilt, etc.),
    computes correlation of portfolio returns, and selects a diversified subset.
    """)

    templates_dir = get_project_root() / "config" / "strategy_templates"
    template_files = sorted(templates_dir.glob("*.yaml")) if templates_dir.exists() else []
    template_names = [p.stem for p in template_files]
    default_templates = template_names[:5] if len(template_names) >= 5 else template_names

    watchlists = get_all_available_watchlists()
    watchlist_options = [""] + list(watchlists.keys()) if watchlists else [""]

    col1, col2 = st.columns(2)
    with col1:
        templates = st.multiselect(
            "Templates",
            options=template_names,
            default=default_templates,
            key="div_templates",
            help="Strategy templates to run (default: all)",
        )
    with col2:
        watchlist = st.selectbox(
            "Watchlist (optional)",
            options=watchlist_options,
            index=0,
            key="div_watchlist",
            help="Restrict universe; leave empty for config default",
        )

    max_corr = st.slider(
        "Max pairwise correlation",
        min_value=0.5,
        max_value=1.0,
        value=0.85,
        step=0.05,
        key="div_max_corr",
        help="Max correlation for diversified subset selection",
    )

    if st.button("▶️ Run Diversified Backtest", type="primary", key="run_div"):
        if not templates:
            st.error("Please select at least one template.")
            return
        output_area = st.empty()
        cmd = [
            "python", "scripts/diversified_backtest.py",
            "--templates", *templates,
            "--max-correlation", str(max_corr),
        ]
        if watchlist:
            cmd.extend(["--watchlist", watchlist])
        with operation_with_feedback("Running Diversified Backtest", show_progress=True):
            returncode, output = _run_script_sync(cmd, output_area)
        if returncode == 0:
            st.success("✅ Diversified backtest completed!")
        else:
            st.error(f"❌ Failed with code {returncode}")


def _render_lineage_tab():
    """Lineage report: DAG of runs, best branches by metric."""
    render_section_header("Lineage Report")
    st.markdown("""
    Scans `output/run_*` and `output/evolutionary/`, builds DAG from parent_run_ids,
    highlights best runs by Sharpe, total return, or hit rate.
    """)

    col1, col2 = st.columns(2)
    with col1:
        metric = st.selectbox(
            "Best-branch metric",
            options=["sharpe_ratio", "total_return", "hit_rate"],
            index=0,
            key="lineage_metric",
        )
    with col2:
        top_n = st.number_input(
            "Top N runs",
            min_value=3,
            max_value=20,
            value=5,
            key="lineage_top",
        )

    if st.button("▶️ Generate Lineage Report", type="primary", key="run_lineage"):
        output_area = st.empty()
        output_dir = get_project_root() / "output"
        cmd = [
            "python", "scripts/lineage_report.py",
            "--output-dir", str(output_dir),
            "--format", "text",
            "--metric", metric,
            "--top", str(top_n),
        ]
        with operation_with_feedback("Generating Lineage Report", show_progress=True):
            returncode, output = _run_script_sync(cmd, output_area)
        if returncode == 0:
            st.success("✅ Lineage report generated.")
        else:
            st.error(f"❌ Failed with code {returncode}")


def _render_strengthen_tab():
    """Strengthen recommendations: run risk analysis on a selected run."""
    render_section_header("Strengthen Recommendations")
    st.markdown("""
    Runs comprehensive risk analysis on a backtest run: regime analysis, tail risk (VaR/CVaR),
    drawdown duration, stress scenarios, position diagnostics, conscience filters.
    """)

    runs_with_folders = get_runs_with_folders()
    if not runs_with_folders:
        st.info("No runs with output folders found. Run a backtest first.")
        return

    runs_with_folders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    run_options = [r['run_id'] for r in runs_with_folders]

    def format_run(run_id):
        r = next((x for x in runs_with_folders if x['run_id'] == run_id), None)
        if not r:
            return run_id[:16]
        name = r.get('name') or 'Unnamed'
        wl = r.get('watchlist_display_name') or r.get('watchlist', '')
        return f"{name} [{wl}]" if wl else name

    col1, col2 = st.columns(2)
    with col1:
        run_id = st.selectbox(
            "Run to analyze",
            options=run_options,
            format_func=format_run,
            index=0,
            key="strengthen_run",
        )
    with col2:
        full_analysis = st.checkbox(
            "Full analysis (tail risk, stress tests, conscience)",
            value=False,
            key="strengthen_full",
        )

    exclude_sectors = st.text_input(
        "Exclude sectors (comma-separated)",
        placeholder="Energy, Defense",
        key="strengthen_exclude_sectors",
    )
    exclude_tickers = st.text_input(
        "Exclude tickers (comma-separated)",
        placeholder="XOM, CVX",
        key="strengthen_exclude_tickers",
    )

    if st.button("▶️ Run Strengthen Analysis", type="primary", key="run_strengthen"):
        output_area = st.empty()
        cmd = [
            "python", "scripts/strengthen_recommendations.py",
            "--run-id", run_id,
        ]
        if full_analysis:
            cmd.append("--full")
        if exclude_sectors:
            cmd.extend(["--exclude-sectors", exclude_sectors.strip()])
        if exclude_tickers:
            cmd.extend(["--exclude-tickers", exclude_tickers.strip()])
        with operation_with_feedback("Running Strengthen Analysis", show_progress=True):
            returncode, output = _run_script_sync(cmd, output_area)
        if returncode == 0:
            st.success("✅ Strengthen analysis completed! Report saved to run folder.")
            output_dir = get_project_root() / "output"
            matches = [p for p in output_dir.iterdir() if p.is_dir() and run_id in p.name]
            if matches:
                report_file = matches[0] / "strengthening_analysis.json"
                if report_file.exists():
                    with st.expander("View report JSON"):
                        try:
                            with open(report_file) as f:
                                data = json.load(f)
                            st.json(data)
                        except Exception:
                            st.code(report_file.read_text())
        else:
            st.error(f"❌ Failed with code {returncode}")


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
