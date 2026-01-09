"""
Portfolio Builder Page
======================
Personalized portfolio optimization with investor profiles.
"""

import streamlit as st
import pandas as pd
import subprocess
import os
import json
from pathlib import Path

from ..components.sidebar import render_page_header, render_section_header
from ..components.metrics import render_metric_card
from ..components.charts import create_sector_pie, create_weight_bar
from ..components.cards import render_info_card, render_alert
from ..data import load_runs, get_run_summary
from ..utils import get_project_root, format_percent, format_number
from ..config import COLORS


# Profile presets
PROFILE_PRESETS = {
    "Conservative": {
        "risk_tolerance": "conservative",
        "target_return": 0.08,
        "max_drawdown": 0.10,
        "max_volatility": 0.15,
        "time_horizon": "long",
        "investment_style": "value",
        "dividend_preference": "income",
    },
    "Moderate": {
        "risk_tolerance": "moderate",
        "target_return": 0.12,
        "max_drawdown": 0.15,
        "max_volatility": 0.20,
        "time_horizon": "medium",
        "investment_style": "blend",
        "dividend_preference": "neutral",
    },
    "Aggressive": {
        "risk_tolerance": "aggressive",
        "target_return": 0.18,
        "max_drawdown": 0.25,
        "max_volatility": 0.30,
        "time_horizon": "short",
        "investment_style": "growth",
        "dividend_preference": "growth",
    },
}


def render_portfolio_builder():
    """Render the portfolio builder page."""
    render_page_header(
        "Portfolio Builder",
        "Build a personalized portfolio based on your risk profile"
    )
    
    runs = load_runs()
    completed_runs = [r for r in runs if r['status'] == 'completed']
    
    if not completed_runs:
        st.warning("No completed analysis runs found. Run a backtest first!")
        return
    
    # Two column layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        _render_parameter_form(completed_runs)
    
    with col2:
        _render_profile_summary()


def _render_parameter_form(completed_runs: list):
    """Render the parameter configuration form."""
    render_section_header("Configuration", "⚙️")
    
    # Profile presets
    preset = st.selectbox(
        "Profile Preset",
        ["Custom"] + list(PROFILE_PRESETS.keys()),
        index=2  # Default to Moderate
    )
    
    # Load preset values
    if preset != "Custom":
        preset_values = PROFILE_PRESETS[preset]
    else:
        preset_values = PROFILE_PRESETS["Moderate"]  # Default
    
    # Store in session state
    if 'profile' not in st.session_state or st.session_state.get('last_preset') != preset:
        st.session_state['profile'] = preset_values.copy()
        st.session_state['last_preset'] = preset
    
    st.markdown("---")
    
    # Risk & Return section
    st.markdown("#### Risk & Return")
    
    col1, col2 = st.columns(2)
    
    with col1:
        risk_tolerance = st.select_slider(
            "Risk Tolerance",
            options=["conservative", "moderate", "aggressive"],
            value=st.session_state['profile'].get('risk_tolerance', 'moderate')
        )
        st.session_state['profile']['risk_tolerance'] = risk_tolerance
        
        target_return = st.slider(
            "Target Annual Return",
            min_value=0.05,
            max_value=0.30,
            value=st.session_state['profile'].get('target_return', 0.12),
            step=0.01,
            format="%.0f%%",
            help="Expected annual return target"
        )
        st.session_state['profile']['target_return'] = target_return
    
    with col2:
        max_drawdown = st.slider(
            "Max Drawdown",
            min_value=0.05,
            max_value=0.40,
            value=st.session_state['profile'].get('max_drawdown', 0.15),
            step=0.01,
            format="%.0f%%",
            help="Maximum acceptable portfolio decline"
        )
        st.session_state['profile']['max_drawdown'] = max_drawdown
        
        max_volatility = st.slider(
            "Max Volatility",
            min_value=0.10,
            max_value=0.40,
            value=st.session_state['profile'].get('max_volatility', 0.20),
            step=0.01,
            format="%.0f%%",
            help="Maximum portfolio volatility"
        )
        st.session_state['profile']['max_volatility'] = max_volatility
    
    st.markdown("---")
    
    # Portfolio Construction section
    st.markdown("#### Portfolio Construction")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        portfolio_size = st.number_input(
            "Portfolio Size",
            min_value=5,
            max_value=30,
            value=10,
            help="Number of stocks in portfolio"
        )
    
    with col2:
        max_position = st.slider(
            "Max Position Weight",
            min_value=0.05,
            max_value=0.25,
            value=0.15,
            step=0.01,
            format="%.0f%%"
        )
    
    with col3:
        max_sector = st.slider(
            "Max Sector Weight",
            min_value=0.20,
            max_value=0.50,
            value=0.35,
            step=0.01,
            format="%.0f%%"
        )
    
    st.markdown("---")
    
    # Style Preferences section
    st.markdown("#### Style Preferences")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        investment_style = st.selectbox(
            "Investment Style",
            ["value", "blend", "growth"],
            index=["value", "blend", "growth"].index(st.session_state['profile'].get('investment_style', 'blend'))
        )
        st.session_state['profile']['investment_style'] = investment_style
    
    with col2:
        dividend_preference = st.selectbox(
            "Dividend Preference",
            ["income", "neutral", "growth"],
            index=["income", "neutral", "growth"].index(st.session_state['profile'].get('dividend_preference', 'neutral'))
        )
        st.session_state['profile']['dividend_preference'] = dividend_preference
    
    with col3:
        time_horizon = st.selectbox(
            "Time Horizon",
            ["short", "medium", "long"],
            index=["short", "medium", "long"].index(st.session_state['profile'].get('time_horizon', 'medium'))
        )
        st.session_state['profile']['time_horizon'] = time_horizon
    
    st.markdown("---")
    
    # Run selection and execution
    st.markdown("#### Run & Execute")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_run_id = st.selectbox(
            "Base Run",
            options=[r['run_id'] for r in completed_runs],
            format_func=lambda x: f"{x[:12]}... - {next((r.get('name') or 'Unnamed' for r in completed_runs if r['run_id'] == x), 'Unknown')}"
        )
    
    with col2:
        with_ai = st.checkbox("Include AI Recommendations", value=True)
    
    # Build button
    if st.button("🚀 Build Portfolio", type="primary", use_container_width=True):
        _run_optimization(
            run_id=selected_run_id,
            risk_tolerance=risk_tolerance,
            target_return=target_return,
            max_drawdown=max_drawdown,
            max_volatility=max_volatility,
            portfolio_size=portfolio_size,
            max_position=max_position,
            max_sector=max_sector,
            investment_style=investment_style,
            dividend_preference=dividend_preference,
            time_horizon=time_horizon,
            with_ai=with_ai
        )


def _render_profile_summary():
    """Render profile summary panel."""
    render_section_header("Profile Summary", "📋")
    
    profile = st.session_state.get('profile', {})
    
    # Risk level indicator
    risk_level = profile.get('risk_tolerance', 'moderate')
    risk_colors = {
        'conservative': COLORS['success'],
        'moderate': COLORS['warning'],
        'aggressive': COLORS['danger'],
    }
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {risk_colors.get(risk_level, COLORS['primary'])} 0%, 
                {risk_colors.get(risk_level, COLORS['primary'])}88 100%);
                padding: 1.5rem; border-radius: 12px; color: white; text-align: center; margin-bottom: 1rem;">
        <div style="font-size: 0.75rem; text-transform: uppercase; opacity: 0.9;">Risk Profile</div>
        <div style="font-size: 1.5rem; font-weight: 700;">{risk_level.title()}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Key parameters
    st.markdown("**Targets**")
    st.write(f"- Return: {profile.get('target_return', 0.12)*100:.0f}%")
    st.write(f"- Max DD: {profile.get('max_drawdown', 0.15)*100:.0f}%")
    st.write(f"- Volatility: {profile.get('max_volatility', 0.20)*100:.0f}%")
    
    st.markdown("**Style**")
    st.write(f"- Style: {profile.get('investment_style', 'blend').title()}")
    st.write(f"- Dividend: {profile.get('dividend_preference', 'neutral').title()}")
    st.write(f"- Horizon: {profile.get('time_horizon', 'medium').title()}")
    
    # Expected characteristics
    st.markdown("---")
    st.markdown("**Expected Portfolio**")
    
    if risk_level == 'conservative':
        st.info("📊 Lower volatility, focus on quality and dividends")
    elif risk_level == 'aggressive':
        st.info("📈 Higher growth potential, more concentrated positions")
    else:
        st.info("⚖️ Balanced approach with diversified holdings")


def _run_optimization(**kwargs):
    """Run portfolio optimization."""
    st.markdown("### Optimizing Portfolio...")
    
    output_placeholder = st.empty()
    
    # Build command
    cmd = [
        "python", "-m", "scripts.run_portfolio_optimizer",
        "--run-id", kwargs['run_id'],
        "--risk-tolerance", kwargs['risk_tolerance'],
        "--target-annual-return", str(kwargs['target_return']),
        "--max-drawdown", str(kwargs['max_drawdown']),
        "--portfolio-size", str(kwargs['portfolio_size']),
        "--max-position-weight", str(kwargs['max_position']),
        "--max-sector-weight", str(kwargs['max_sector']),
        "--investment-style", kwargs['investment_style'],
        "--dividend-preference", kwargs['dividend_preference'],
        "--time-horizon", kwargs['time_horizon'],
    ]
    
    if kwargs.get('with_ai'):
        cmd.append("--with-ai-recommendations")
    
    returncode, output = _run_script_sync(cmd, output_placeholder)
    
    if returncode == 0:
        st.success("✅ Portfolio optimization completed!")
        
        # Display results
        _display_optimization_results(kwargs['run_id'])
        
        st.cache_data.clear()
        st.cache_resource.clear()
    else:
        st.error(f"❌ Optimization failed with code {returncode}")


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
            placeholder.code(''.join(output_lines[-30:]), language='text')
        
        process.wait()
        return process.returncode, ''.join(output_lines)
        
    except Exception as e:
        return -1, f"Error: {str(e)}"


def _display_optimization_results(run_id: str):
    """Display optimization results."""
    output_dir = get_project_root() / "output"
    
    # Find the run folder - could be run_RUNID or run_WATCHLIST_RUNID
    run_folder = None
    for folder in output_dir.iterdir():
        if folder.is_dir() and run_id[:16] in folder.name:
            run_folder = folder
            break
    
    if not run_folder:
        run_folder = output_dir / f"run_{run_id[:16]}"
    
    # Find portfolio files in run folder, or fall back to output dir
    portfolio_files = list(run_folder.glob("optimized_portfolio_*.csv")) if run_folder.exists() else []
    
    if not portfolio_files:
        # Fall back to output directory root
        portfolio_files = list(output_dir.glob("**/optimized_portfolio_*.csv"))
    
    if not portfolio_files:
        st.info("No portfolio files found")
        return
    
    latest_file = max(portfolio_files, key=lambda f: f.stat().st_mtime)
    
    # Load and display
    df = pd.read_csv(latest_file)
    
    render_section_header("Optimized Portfolio", "🎯")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Portfolio table
        display_cols = ['ticker', 'sector', 'optimized_weight', 'score', 'volatility_annual']
        display_cols = [c for c in display_cols if c in df.columns]
        
        display_df = df[display_cols].copy()
        if 'optimized_weight' in display_df.columns:
            display_df['optimized_weight'] = display_df['optimized_weight'].apply(lambda x: f"{x*100:.1f}%")
        if 'volatility_annual' in display_df.columns:
            display_df['volatility_annual'] = display_df['volatility_annual'].apply(lambda x: f"{x*100:.1f}%")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    with col2:
        # Sector allocation chart
        if 'sector' in df.columns and 'optimized_weight' in df.columns:
            sector_weights = df.groupby('sector')['optimized_weight'].sum().to_dict()
            
            fig = create_sector_pie(
                sectors=sector_weights,
                title="Sector Allocation"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Download button
    st.download_button(
        "📥 Download Portfolio",
        df.to_csv(index=False),
        file_name=latest_file.name,
        mime="text/csv"
    )
