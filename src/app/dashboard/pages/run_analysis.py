"""
Run Analysis Page
=================
Execute analysis pipeline with staged workflow.
"""

import streamlit as st
import subprocess
import os
from pathlib import Path
from datetime import datetime, date, timedelta

from ..components.sidebar import render_page_header, render_section_header
from ..components.cards import render_info_card, render_progress_steps, render_alert
from ..components.loading import render_stage_progress, operation_with_feedback
from ..components.errors import ErrorHandler
from ..data import (
    load_runs, get_runs_with_folders, get_run_summary, get_available_run_folders,
    get_all_available_watchlists, load_custom_watchlists,
    load_app_settings, save_app_settings,
)
from ..utils import get_project_root, check_run_folder_exists
from ..config import COLORS


def render_run_analysis():
    """Render the run analysis page."""
    render_page_header(
        "Run Analysis",
        "Execute analysis pipeline"
    )
    
    # Two main tabs: New Analysis vs Continue Existing
    tab1, tab2 = st.tabs(["🆕 Start New Analysis", "📂 Continue Existing Run"])
    
    with tab1:
        _render_new_analysis_tab()
    
    with tab2:
        _render_continue_existing_tab()


def _render_new_analysis_tab():
    """Render the new analysis workflow."""
    st.markdown("""
    <div style="background: {bg}; 
                padding: 1.5rem; border-radius: 12px; color: #0b0b0f; margin-bottom: 1.5rem;">
        <h3 style="margin: 0 0 0.5rem 0;">🚀 Start Fresh Analysis</h3>
        <p style="margin: 0; opacity: 0.9; font-size: 0.9rem;">
            Select a watchlist and run the complete analysis pipeline from scratch.
        </p>
    </div>
    """.format(bg=COLORS['light']), unsafe_allow_html=True)
    
    # Load persisted params (recalled on start/refresh)
    saved = load_app_settings("run_analysis", default={})
    
    # Step 1: Select Watchlist
    st.markdown("### Step 1: Select Stock Universe")
    
    watchlists = get_all_available_watchlists()
    
    if not watchlists:
        st.warning("No watchlists found. Please configure watchlists first.")
        return
    
    # Category filter and watchlist selector in columns
    col1, col2 = st.columns([1, 2])
    
    # Build categories
    categories = {}
    for wl_id, wl in watchlists.items():
        cat = wl.get('category', 'custom')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(wl_id)
    
    category_options = ['All Categories'] + sorted(categories.keys())
    default_category = saved.get("category", "All Categories")
    if default_category not in category_options:
        default_category = "All Categories"
    
    with col1:
        selected_category = st.selectbox(
            "Filter by Category",
            options=category_options,
            index=category_options.index(default_category) if default_category in category_options else 0,
            key="new_analysis_category",
            help="Filter watchlists by category (custom, sector, region, etc.)"
        )
    
    with col2:
        # Filter by category
        if selected_category == 'All Categories':
            filtered_watchlists = watchlists
        else:
            filtered_ids = categories.get(selected_category, [])
            filtered_watchlists = {k: v for k, v in watchlists.items() if k in filtered_ids}
        
        watchlist_options = list(filtered_watchlists.keys())
        default_watchlist = saved.get("watchlist")
        if not default_watchlist or default_watchlist not in watchlist_options:
            default_watchlist = watchlist_options[0] if watchlist_options else None
        watchlist_index = watchlist_options.index(default_watchlist) if default_watchlist in watchlist_options else 0
        
        def format_watchlist(wl_id):
            wl = watchlists.get(wl_id, {})
            name = wl.get('name', wl_id)
            count = wl.get('count', 0)
            is_custom = wl.get('is_custom', False)
            return f"{name} ({count} stocks)" + (" ⭐" if is_custom else "")
        
        selected_watchlist = st.selectbox(
            "Select Watchlist",
            options=watchlist_options,
            index=watchlist_index,
            format_func=format_watchlist,
            key="new_analysis_watchlist",
            help="Pick the stock universe to analyze"
        )
    
    # Show watchlist preview
    if selected_watchlist:
        wl = watchlists.get(selected_watchlist, {})
        symbols = wl.get('symbols', [])
        
        with st.expander(f"📋 Preview: {wl.get('name', selected_watchlist)} ({len(symbols)} stocks)", expanded=False):
            st.markdown(f"**Description:** {wl.get('description', 'No description')}")
            if symbols:
                # Show symbols in a compact grid
                symbol_text = " • ".join(symbols[:30])
                if len(symbols) > 30:
                    symbol_text += f" ... and {len(symbols) - 30} more"
                st.markdown(f"`{symbol_text}`")
    
    st.markdown("---")
    
    # Step 2: Configure Analysis Period
    st.markdown("### Step 2: Configure Analysis Period")
    
    # Date period selector
    st.markdown("""
    <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid #6366f1;">
        <strong>📅 Backtest Period</strong><br>
        <span style="font-size: 0.85rem; color: #64748b;">
            Select the date range for training and testing. Walk-forward validation will use data within this period.
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    # Default dates (from saved or defaults)
    default_end = date.today()
    default_start = date(2015, 1, 1)
    if saved.get("start_date"):
        try:
            default_start = datetime.strptime(saved["start_date"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass
    if saved.get("end_date"):
        try:
            default_end = datetime.strptime(saved["end_date"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=default_start,
            min_value=date(2010, 1, 1),
            max_value=default_end - timedelta(days=365),
            key="analysis_start_date",
            help="Earliest date for training data"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=default_end,
            min_value=start_date + timedelta(days=365),
            max_value=date.today(),
            key="analysis_end_date",
            help="Latest date for testing data"
        )
    
    with col3:
        # Show period summary
        period_years = (end_date - start_date).days / 365.25
        st.markdown(f"""
        <div style="background: #e0e7ff; padding: 0.75rem; border-radius: 8px; text-align: center; margin-top: 0.5rem;">
            <div style="font-size: 1.5rem; font-weight: 700; color: #4338ca;">{period_years:.1f}</div>
            <div style="font-size: 0.75rem; color: #6366f1;">Years of Data</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Backtest config (from config.yaml - for visibility)
    try:
        from src.config.config import load_config
        _cfg = load_config()
        step_str = f"{_cfg.backtest.step_value} {_cfg.backtest.step_unit}"
        st.markdown("**Backtest settings** (from `config/config.yaml`):")
        st.caption(f"Train: {_cfg.backtest.train_years}y · Test: {_cfg.backtest.test_years}y · **Step: {step_str}** · Rebalance: {_cfg.backtest.rebalance_freq}")
        st.caption("Step = how far the window advances between walk-forward iterations. Smaller step (e.g. 1 month) = more windows = slower run.")
    except Exception:
        pass
    
    st.markdown("---")
    
    # Step 3: Additional Options
    st.markdown("### Step 3: Configure & Run")
    
    col1, col2 = st.columns(2)
    
    with col1:
        include_ai = st.checkbox(
            "Include AI Commentary & Recommendations",
            value=saved.get("include_ai", True),
            help="Generates Gemini-powered commentary and recommendations"
        )
    
    with col2:
        custom_name = st.text_input(
            "Run Name (optional)",
            value=saved.get("custom_name", ""),
            placeholder="e.g., Q1 2025 Analysis",
            help="Helps you identify this run later"
        )
    
    # Pipeline overview
    st.markdown("**Pipeline Steps:**")
    steps_col1, steps_col2, steps_col3, steps_col4 = st.columns(4)
    with steps_col1:
        st.markdown("1️⃣ **Backtest**\n\nWalk-forward validation")
    with steps_col2:
        st.markdown("2️⃣ **Enrichment**\n\nRisk metrics & sectors")
    with steps_col3:
        st.markdown("3️⃣ **Domain Analysis**\n\nVertical & horizontal")
    with steps_col4:
        st.markdown("4️⃣ **AI Analysis**\n\nCommentary & recs")
    
    st.markdown("")
    
    # Run button
    if st.button("▶️ Run Full Analysis", type="primary", use_container_width=True, key="run_new_analysis"):
        if not selected_watchlist:
            st.error("Please select a watchlist first.")
            return
        # Persist params to DB (recalled on next start/refresh)
        save_app_settings("run_analysis", {
            "watchlist": selected_watchlist,
            "category": selected_category,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "include_ai": include_ai,
            "custom_name": custom_name or "",
        })
        _run_new_analysis(
            selected_watchlist, 
            include_ai, 
            custom_name,
            start_date=str(start_date),
            end_date=str(end_date)
        )


def _render_continue_existing_tab():
    """Render the continue existing run workflow."""
    st.markdown("""
    <div style="background: {bg}; padding: 1.5rem; border-radius: 12px; 
                border: 1px solid {border}; margin-bottom: 1.5rem;">
        <h3 style="margin: 0 0 0.5rem 0; color: {dark};">📂 Continue Existing Run</h3>
        <p style="margin: 0; color: {muted}; font-size: 0.9rem;">
            Select a previous run to view status or continue incomplete stages.
        </p>
    </div>
    """.format(
        bg=COLORS['light'], 
        border=COLORS['card_border'],
        dark=COLORS['dark'],
        muted=COLORS['muted']
    ), unsafe_allow_html=True)
    
    # Get runs with folder info
    runs_with_folders = get_runs_with_folders()
    
    if not runs_with_folders:
        st.info("No existing runs found. Start a new analysis from the first tab.")
        return
    
    # Sort: runs with folders first, then by date
    runs_with_folders.sort(key=lambda x: (not x.get('has_folder', False), x.get('created_at', '')), reverse=True)
    
    # Run selector
    def format_run(run_id):
        run = next((r for r in runs_with_folders if r['run_id'] == run_id), None)
        if not run:
            return run_id[:12]
        
        name = run.get('name') or 'Unnamed'
        has_folder = run.get('has_folder', False)
        file_count = run.get('file_count', 0)
        watchlist = run.get('watchlist_display_name') or run.get('watchlist')
        
        # Build display string
        parts = []
        if has_folder:
            parts.append("📁")
        else:
            parts.append("⚪")
        
        if watchlist:
            parts.append(f"[{watchlist}]")
        
        parts.append(name)
        
        if has_folder:
            parts.append(f"({file_count} files)")
        else:
            parts.append("(no folder)")
        
        return " ".join(parts)
    
    selected_run_id = st.selectbox(
        "Select Run",
        options=[r['run_id'] for r in runs_with_folders],
        format_func=format_run,
        key="continue_run_selector"
    )
    
    if not selected_run_id:
        return
    
    # Get run summary
    summary = get_run_summary(selected_run_id)
    run = summary.get('run', {})
    stages = summary.get('stages', {})
    
    # Display run info
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Run Details**")
        st.markdown(f"- **Name:** {run.get('name') or 'Unnamed'}")
        st.markdown(f"- **Watchlist:** {run.get('watchlist_display_name') or run.get('watchlist') or 'Default Universe'}")
        st.markdown(f"- **Created:** {run.get('created_at', 'N/A')[:19] if run.get('created_at') else 'N/A'}")
    
    with col2:
        st.markdown("**Performance**")
        total_return = run.get('total_return')
        sharpe = run.get('sharpe_ratio')
        st.markdown(f"- **Return:** {total_return*100:+.1f}%" if total_return else "- **Return:** N/A")
        st.markdown(f"- **Sharpe:** {sharpe:.2f}" if sharpe else "- **Sharpe:** N/A")
        st.markdown(f"- **Status:** {run.get('status', 'unknown').title()}")
    
    st.markdown("---")
    
    # Pipeline status
    st.markdown("### Pipeline Status")
    
    status_cols = st.columns(4)
    stage_info = [
        ('Backtest', stages.get('backtest', False), 'Walk-forward validation'),
        ('Enrichment', stages.get('enrichment', False), 'Risk metrics & sectors'),
        ('Domain Analysis', stages.get('domain_analysis', False), 'Vertical & horizontal'),
        ('AI Analysis', stages.get('ai_analysis', False), 'Commentary & recs'),
    ]
    
    for i, (name, complete, desc) in enumerate(stage_info):
        with status_cols[i]:
            icon = "✅" if complete else "🔴"
            color = COLORS['success'] if complete else COLORS['danger']
            st.markdown(f"""
            <div style="text-align: center; padding: 1rem; background: {COLORS['light']}; 
                        border-radius: 8px; border-left: 4px solid {color};">
                <div style="font-size: 1.5rem;">{icon}</div>
                <div style="font-weight: 600; margin-top: 0.5rem;">{name}</div>
                <div style="font-size: 0.75rem; color: {COLORS['muted']};">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Action buttons based on what's missing
    st.markdown("### Available Actions")
    
    if not stages.get('backtest'):
        render_alert("⚠️ This run has no backtest data. You may need to start a new analysis.", "warning")
    else:
        # Show available actions
        action_cols = st.columns(4)
        
        with action_cols[0]:
            if not stages.get('enrichment'):
                if st.button("▶️ Run Enrichment", use_container_width=True, key="run_enrichment"):
                    _run_stage("enrichment", selected_run_id)
            else:
                st.success("✓ Enrichment complete")
        
        with action_cols[1]:
            if not stages.get('domain_analysis'):
                if st.button("▶️ Run Domain Analysis", use_container_width=True, key="run_domain"):
                    _run_stage("domain", selected_run_id)
            else:
                st.success("✓ Domain Analysis complete")
        
        with action_cols[2]:
            if not stages.get('ai_analysis'):
                if st.button("▶️ Run AI Analysis", use_container_width=True, key="run_ai"):
                    _run_stage("ai", selected_run_id)
            else:
                st.success("✓ AI Analysis complete")
        
        with action_cols[3]:
            if st.button("🛡️ Strengthen Recommendations", use_container_width=True, key="run_strengthen"):
                _run_stage("strengthen", selected_run_id)
        
        # Re-run all button
        st.markdown("")
        if st.button("🔄 Re-run All Stages", use_container_width=True, key="rerun_all"):
            _run_all_stages(selected_run_id)


def _run_new_analysis(watchlist: str, include_ai: bool, custom_name: str = None, 
                      start_date: str = None, end_date: str = None):
    """Run a complete new analysis with the selected watchlist."""
    # Get watchlist display name
    watchlists = get_all_available_watchlists()
    wl = watchlists.get(watchlist, {})
    wl_name = wl.get('name', watchlist)
    
    st.markdown(f"### 🚀 Running Analysis with **{wl_name}** watchlist")
    
    # Show period info
    period_info = f"*Watchlist ID: `{watchlist}`*"
    if start_date and end_date:
        period_info += f" • *Period: `{start_date}` to `{end_date}`*"
    st.markdown(period_info)
    
    # Use enhanced loading components
    render_stage_progress("Initializing", 0, 4)
    output_area = st.empty()
    
    # Step 1: Run backtest
    render_stage_progress("Running Backtest", 1, 4)
    st.markdown("#### Step 1: Backtest")
    
    cmd_backtest = [
        "python", "-m", "src.app.cli", "run-backtest",
        "--config", "config/config.yaml",
        "--watchlist", watchlist
    ]
    
    if custom_name:
        cmd_backtest.extend(["--name", custom_name])
    
    if start_date:
        cmd_backtest.extend(["--start-date", start_date])
    
    if end_date:
        cmd_backtest.extend(["--end-date", end_date])
    
    with operation_with_feedback("Running Backtest", show_progress=True):
        returncode, output = _run_script_sync(cmd_backtest, output_area)
    
    if returncode != 0:
        ErrorHandler.render_error(
            Exception(f"Backtest failed with code {returncode}"),
            error_type='analysis_error',
            show_traceback=False,
            custom_message=f"Backtest failed with exit code {returncode}",
            custom_actions=[
                "Check the output above for error details",
                "Verify watchlist configuration",
                "Ensure data files are available",
                "Try running the backtest again"
            ]
        )
        return
    
    st.success("✅ Backtest completed!")
    
    # Step 2: Run full analysis workflow
    render_stage_progress("Running Analysis Workflow", 2, 4)
    st.markdown("#### Steps 2-4: Analysis Workflow")
    
    output_area2 = st.empty()
    
    cmd_analysis = [
        "python", "scripts/full_analysis_workflow.py",
        "--config", "config/config.yaml",
        "--watchlist", watchlist
    ]
    
    if start_date:
        cmd_analysis.extend(["--start-date", start_date])
    
    if end_date:
        cmd_analysis.extend(["--end-date", end_date])
    
    if include_ai:
        cmd_analysis.extend(["--with-commentary", "--with-recommendations"])
    
    with operation_with_feedback("Running Analysis Workflow", show_progress=True):
        returncode, output = _run_script_sync(cmd_analysis, output_area2)
    
    if returncode == 0:
        render_stage_progress("Complete", 4, 4)
        st.success("✅ Full analysis completed!")
        st.balloons()
        
        # Clear cache and refresh
        st.cache_data.clear()
        st.cache_resource.clear()
        
        st.markdown("---")
        st.info("🎉 Analysis complete! Check the **Reports** page to view results.")
        
        if st.button("🔄 Refresh Page"):
            st.rerun()
    else:
        ErrorHandler.render_error(
            Exception(f"Analysis workflow failed with code {returncode}"),
            error_type='analysis_error',
            show_traceback=False,
            custom_message=f"Analysis workflow failed with exit code {returncode}",
            custom_actions=[
                "Review the output above for specific errors",
                "Check if all required data is available",
                "Verify configuration settings",
                "Try running individual stages instead"
            ]
        )


def _run_stage(stage: str, run_id: str):
    """Run a specific analysis stage."""
    st.markdown(f"### Running {stage.title()}...")
    
    output_area = st.empty()
    
    if stage == "enrichment":
        cmd = ["python", "scripts/analyze_portfolio.py", "--run-id", run_id]
    elif stage == "domain":
        cmd = ["python", "scripts/run_domain_analysis.py", "--run-id", run_id]
    elif stage == "ai":
        cmd = ["python", "scripts/full_analysis_workflow.py", "--run-id", run_id,
               "--with-commentary", "--with-recommendations"]
    elif stage == "strengthen":
        cmd = ["python", "scripts/strengthen_recommendations.py", "--run-id", run_id]
    else:
        st.error(f"Unknown stage: {stage}")
        return
    
    returncode, output = _run_script_sync(cmd, output_area)
    
    if returncode == 0:
        st.success(f"✅ {stage.title()} completed!")
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()
    else:
        st.error(f"❌ {stage.title()} failed with code {returncode}")


def _run_all_stages(run_id: str):
    """Re-run all analysis stages for an existing run."""
    st.markdown("### Re-running all stages...")
    
    output_area = st.empty()
    
    cmd = [
        "python", "scripts/full_analysis_workflow.py",
        "--run-id", run_id,
        "--with-commentary", "--with-recommendations"
    ]
    
    returncode, output = _run_script_sync(cmd, output_area)
    
    if returncode == 0:
        st.success("✅ All stages completed!")
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()
    else:
        st.error(f"❌ Failed with code {returncode}")


def _run_script_sync(cmd: list, placeholder) -> tuple:
    """Run a script synchronously with live output."""
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
            env=env
        )
        
        output_lines = []
        for line in iter(process.stdout.readline, ''):
            output_lines.append(line)
            # Show last 25 lines
            placeholder.code(''.join(output_lines[-25:]), language='text')
        
        process.wait()
        return process.returncode, ''.join(output_lines)
        
    except Exception as e:
        return -1, f"Error: {str(e)}"
