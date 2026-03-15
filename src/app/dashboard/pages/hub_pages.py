"""
Hub Pages — Process-flow landing pages
=======================================
Each hub is a rich landing page for a workflow phase, providing context,
recommended workflow order, tool descriptions, and quick status indicators.
"""

import streamlit as st
from pathlib import Path

from ..components.sidebar import render_page_header
from ..config import PROCESS_PHASES, COLORS
from ..data import load_runs, get_available_run_folders
from ..utils import get_project_root


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _navigate_to(page_label: str):
    """Navigate to a page via query-param routing."""
    st.session_state.selected_nav_item = page_label
    st.query_params["page"] = page_label
    st.rerun()


def _phase_css():
    """Inject hub-page-specific CSS (called once per render)."""
    st.markdown(f"""
<style>
    .hub-intro {{
        font-size: 1.05rem;
        line-height: 1.7;
        color: {COLORS['muted']};
        max-width: 720px;
        margin-bottom: 2rem;
    }}
    .hub-intro strong {{
        color: {COLORS['dark']};
    }}
    .hub-section-title {{
        font-family: 'Instrument Sans', sans-serif;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: {COLORS['muted']};
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid {COLORS['card_border']};
    }}
    .hub-tool-card {{
        background: {COLORS['card_bg']};
        border: 1px solid {COLORS['card_border']};
        border-radius: 12px;
        padding: 1.25rem 1.4rem;
        margin-bottom: 0.75rem;
        transition: border-color 0.25s ease, box-shadow 0.25s ease;
        position: relative;
    }}
    .hub-tool-card:hover {{
        border-color: {COLORS['primary']};
        box-shadow: 0 4px 16px rgba(232, 115, 90, 0.08);
    }}
    .hub-tool-card .tool-step {{
        position: absolute;
        top: 1.25rem;
        right: 1.4rem;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: {COLORS['light']};
        border: 1.5px solid {COLORS['card_border']};
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.7rem;
        font-weight: 700;
        color: {COLORS['muted']};
        font-family: 'JetBrains Mono', monospace;
    }}
    .hub-tool-card .tool-name {{
        font-family: 'Instrument Sans', sans-serif;
        font-size: 1.05rem;
        font-weight: 600;
        color: {COLORS['dark']};
        margin-bottom: 0.35rem;
    }}
    .hub-tool-card .tool-desc {{
        font-size: 0.88rem;
        color: {COLORS['muted']};
        line-height: 1.55;
        margin-bottom: 0.15rem;
    }}
    .hub-tool-card .tool-tag {{
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 0.15rem 0.55rem;
        border-radius: 4px;
        margin-top: 0.5rem;
        margin-right: 0.35rem;
    }}
    .tag-core {{
        background: rgba(232, 115, 90, 0.10);
        color: {COLORS['primary']};
    }}
    .tag-optional {{
        background: rgba(207, 230, 218, 0.35);
        color: #4a7c5f;
    }}
    .tag-advanced {{
        background: rgba(199, 215, 242, 0.35);
        color: #4a6a9e;
    }}
    .tag-ai {{
        background: rgba(233, 199, 184, 0.35);
        color: #8b5e3c;
    }}
    .hub-workflow-note {{
        background: {COLORS['light']};
        border-left: 3px solid {COLORS['primary']};
        border-radius: 0 8px 8px 0;
        padding: 0.9rem 1.2rem;
        margin: 1.5rem 0;
        font-size: 0.88rem;
        color: {COLORS['muted']};
        line-height: 1.6;
    }}
    .hub-workflow-note strong {{
        color: {COLORS['dark']};
    }}
    .hub-stat-row {{
        display: flex;
        gap: 1.5rem;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
    }}
    .hub-stat {{
        background: {COLORS['card_bg']};
        border: 1px solid {COLORS['card_border']};
        border-radius: 10px;
        padding: 0.9rem 1.2rem;
        min-width: 140px;
        flex: 1;
    }}
    .hub-stat .stat-label {{
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: {COLORS['muted']};
        margin-bottom: 0.25rem;
    }}
    .hub-stat .stat-value {{
        font-family: 'Instrument Sans', sans-serif;
        font-size: 1.35rem;
        font-weight: 700;
        color: {COLORS['dark']};
    }}
</style>
""", unsafe_allow_html=True)


def _render_tool_card(step: int, label: str, identifier: str, description: str,
                      tags: list[tuple[str, str]] | None = None,
                      detail: str = ""):
    """Render a single tool card with step number and open button."""
    tag_html = ""
    if tags:
        for tag_text, tag_class in tags:
            tag_html += f'<span class="hub-tool-card tool-tag {tag_class}">{tag_text}</span>'

    detail_html = ""
    if detail:
        detail_html = f'<div style="font-size: 0.8rem; color: {COLORS["muted"]}; margin-top: 0.4rem; font-style: italic;">{detail}</div>'

    st.markdown(f"""
    <div class="hub-tool-card">
        <div class="tool-step">{step}</div>
        <div class="tool-name">{label}</div>
        <div class="tool-desc">{description}</div>
        {detail_html}
        {tag_html}
    </div>
    """, unsafe_allow_html=True)
    if st.button(f"Open {label}", key=f"hub_{identifier}", use_container_width=True):
        _navigate_to(label)


def _render_stat(label: str, value: str):
    """Render a single stat block."""
    return f"""
    <div class="hub-stat">
        <div class="stat-label">{label}</div>
        <div class="stat-value">{value}</div>
    </div>"""


# ---------------------------------------------------------------------------
# Setup Hub
# ---------------------------------------------------------------------------

def render_setup_hub():
    """Render the Setup phase hub page."""
    _phase_css()
    render_page_header("Setup", "Configure watchlists, data sources, and settings")

    st.markdown("""
    <div class="hub-intro">
        Before running any analysis, ensure your <strong>stock universe</strong> is defined,
        <strong>data quality</strong> is validated, and <strong>fundamental data</strong> is up to date.
        A clean data foundation prevents misleading results downstream.
    </div>
    """, unsafe_allow_html=True)

    # Quick status
    runs = load_runs()
    run_folders = get_available_run_folders()
    watchlist_path = get_project_root() / "config" / "watchlists.yaml"
    has_watchlists = watchlist_path.exists()
    prices_path = get_project_root() / "data" / "prices_daily.csv"
    has_prices = prices_path.exists()
    fundamentals_path = get_project_root() / "data" / "fundamentals.csv"
    has_fundamentals = fundamentals_path.exists()

    st.markdown(f"""
    <div class="hub-stat-row">
        {_render_stat("Watchlists", "Configured" if has_watchlists else "Not found")}
        {_render_stat("Price Data", "Available" if has_prices else "Missing")}
        {_render_stat("Fundamentals", "Available" if has_fundamentals else "Missing")}
        {_render_stat("Analysis Runs", str(len(runs)) if runs else "0")}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="hub-section-title">Setup Tools</div>', unsafe_allow_html=True)

    _render_tool_card(
        1, "Watchlist Manager", "watchlist_manager",
        "Define which stocks to analyze. Create watchlists by theme (tech, energy, ETFs) or use built-in universes like NASDAQ-100.",
        tags=[("core", "tag-core")],
        detail="Start here — all analyses run against a watchlist.",
    )
    _render_tool_card(
        2, "Data Quality", "data_quality",
        "Validate that price data is complete, dates align, and there are no gaps. Flags issues that could silently corrupt backtest results.",
        tags=[("core", "tag-core")],
    )
    _render_tool_card(
        3, "Fundamentals Status", "fundamentals_status",
        "Check coverage of PE, PB, ROE, margins, and other fundamental data. Identifies tickers with missing or stale fundamentals.",
        tags=[("optional", "tag-optional")],
        detail="Only needed if using valuation features in the model.",
    )
    _render_tool_card(
        4, "Settings", "settings",
        "System preferences: dark mode, custom CSS, font scale, color scheme, and other UI configuration.",
        tags=[("optional", "tag-optional")],
    )

    st.markdown("""
    <div class="hub-workflow-note">
        <strong>Recommended order:</strong> Configure watchlists first, then validate data quality.
        Fundamentals and settings can be done any time.
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Analyze Hub
# ---------------------------------------------------------------------------

def render_analyze_hub():
    """Render the Analyze phase hub page."""
    _phase_css()
    render_page_header("Analyze", "Run analyses, backtest strategies, and test features")

    st.markdown("""
    <div class="hub-intro">
        This is the core of QuantaAlpha. Run <strong>walk-forward backtests</strong> to generate
        stock predictions, <strong>test individual features</strong> for statistical significance,
        and <strong>optimize strategy parameters</strong>. Each tool produces results that feed
        into the Build and Review phases.
    </div>
    """, unsafe_allow_html=True)

    # Quick status
    runs = load_runs()
    completed = sum(1 for r in runs if r.get('status') == 'completed') if runs else 0

    st.markdown(f"""
    <div class="hub-stat-row">
        {_render_stat("Completed Runs", str(completed))}
        {_render_stat("Total Runs", str(len(runs)) if runs else "0")}
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="hub-section-title">Analysis Tools</div>', unsafe_allow_html=True)

    _render_tool_card(
        1, "Run Analysis", "run_analysis",
        "Execute a walk-forward backtest on a watchlist. Trains LightGBM models in rolling windows, ranks stocks, and computes portfolio returns with transaction costs.",
        tags=[("core", "tag-core")],
        detail="This is the primary analysis — produces stock scores, portfolio returns, and IC metrics.",
    )
    _render_tool_card(
        2, "Regression Testing", "regression_testing",
        "Add features one-by-one to a baseline model and measure marginal contribution. Uses paired t-tests and bootstrap CIs to determine statistical significance.",
        tags=[("advanced", "tag-advanced")],
        detail="Run after initial backtests to identify which features actually improve predictions.",
    )
    _render_tool_card(
        3, "Strategy Optimizer", "strategy_optimizer",
        "Bayesian optimization of MACD, RSI, and other indicator parameters. Searches for optimal settings per ticker or globally.",
        tags=[("advanced", "tag-advanced")],
    )
    _render_tool_card(
        4, "Trigger Backtester", "trigger_backtester",
        "Single-ticker backtesting of buy/sell trigger signals (RSI/MACD/Bollinger/combined) with optional macro filters (VIX, DXY, gold/silver ratio).",
        tags=[("optional", "tag-optional")],
    )
    _render_tool_card(
        5, "Stock Explorer", "stock_explorer",
        "Browse individual stock scores, features, and model predictions. Search and filter across the full universe.",
        tags=[("optional", "tag-optional")],
    )
    _render_tool_card(
        6, "AI Insights", "ai_insights",
        "Generate AI-powered commentary on analysis results using Gemini. Produces executive summaries, sector analysis, and investment recommendations.",
        tags=[("ai", "tag-ai")],
        detail="Requires a completed analysis run. Best used after reviewing results manually first.",
    )

    st.markdown("""
    <div class="hub-workflow-note">
        <strong>Typical workflow:</strong> Start with <em>Run Analysis</em> on your target watchlist.
        If results look promising, use <em>Regression Testing</em> to validate which features contribute.
        <em>Strategy Optimizer</em> and <em>Trigger Backtester</em> are for deep-dives on specific tickers.
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Build Hub
# ---------------------------------------------------------------------------

def render_build_hub():
    """Render the Build phase hub page."""
    _phase_css()
    render_page_header("Build", "Construct and optimize portfolios")

    st.markdown("""
    <div class="hub-intro">
        Turn backtest results into <strong>actionable portfolios</strong>. Select stocks based on
        model scores and fundamental filters, apply risk constraints (position limits, sector caps,
        volatility targets), and generate buy/sell signals.
    </div>
    """, unsafe_allow_html=True)

    runs = load_runs()
    completed = sum(1 for r in runs if r.get('status') == 'completed') if runs else 0

    if completed == 0:
        st.markdown("""
        <div class="hub-workflow-note">
            <strong>No completed runs yet.</strong> Run an analysis first in the
            <em>Analyze</em> phase to generate stock scores, then return here to build a portfolio.
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="hub-section-title">Portfolio Tools</div>', unsafe_allow_html=True)

    _render_tool_card(
        1, "Portfolio Builder", "portfolio_builder",
        "Build risk-optimized portfolios from scored stocks. Choose a risk profile (conservative/moderate/aggressive), set position and sector constraints, and generate allocations.",
        tags=[("core", "tag-core")],
        detail="Combines vertical (within-sector) ranking with horizontal (cross-sector) optimization.",
    )
    _render_tool_card(
        2, "Purchase Triggers", "purchase_triggers",
        "Generate specific buy/sell signals with entry prices, stop losses, and position sizes. Uses RSI, MACD, and Bollinger band confluence.",
        tags=[("core", "tag-core")],
    )
    _render_tool_card(
        3, "Tax Optimization", "tax_optimization",
        "Tax-loss harvesting analysis: identify losing positions to sell, wash sale detection, and tax-efficient rebalancing suggestions.",
        tags=[("optional", "tag-optional")],
        detail="Most useful near year-end or when rebalancing an existing portfolio.",
    )

    st.markdown("""
    <div class="hub-workflow-note">
        <strong>Recommended order:</strong> Use <em>Portfolio Builder</em> to construct your target allocation,
        then <em>Purchase Triggers</em> for execution timing. <em>Tax Optimization</em> applies to existing holdings.
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Monitor Hub
# ---------------------------------------------------------------------------

def render_monitor_hub():
    """Render the Monitor phase hub page."""
    _phase_css()
    render_page_header("Monitor", "Track portfolio performance and market signals")

    st.markdown("""
    <div class="hub-intro">
        Once your portfolio is live, these tools help you <strong>track performance</strong>,
        monitor <strong>earnings dates</strong>, and manage <strong>alerts</strong> for price moves,
        drawdowns, and other events.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="hub-section-title">Monitoring Tools</div>', unsafe_allow_html=True)

    _render_tool_card(
        1, "Real-Time Monitoring", "realtime_monitoring",
        "Live portfolio and market tracking. Daily P&L summary, position-level performance, benchmark comparison, and drawdown alerts.",
        tags=[("core", "tag-core")],
    )
    _render_tool_card(
        2, "Recommendation Tracking", "recommendation_tracking",
        "Track how AI-generated recommendations perform over time. Hit rate, average return, and accuracy metrics per recommendation.",
        tags=[("optional", "tag-optional")],
    )
    _render_tool_card(
        3, "Alert Management", "alert_management",
        "Configure price alerts, drawdown warnings, volume spikes, and custom event triggers. Supports email and SMS notifications.",
        tags=[("optional", "tag-optional")],
    )
    _render_tool_card(
        4, "Earnings Calendar", "earnings_calendar",
        "Upcoming earnings dates for portfolio holdings. Track earnings exposure, estimate consensus, and historical surprise patterns.",
        tags=[("optional", "tag-optional")],
    )
    _render_tool_card(
        5, "Notifications", "notifications",
        "View history of all triggered alerts and system notifications.",
        tags=[("optional", "tag-optional")],
    )

    st.markdown("""
    <div class="hub-workflow-note">
        <strong>Tip:</strong> Set up <em>Alert Management</em> rules once, then use
        <em>Real-Time Monitoring</em> as your daily dashboard. Check <em>Earnings Calendar</em>
        weekly to avoid surprise volatility around reporting dates.
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Review Hub
# ---------------------------------------------------------------------------

def render_review_hub():
    """Render the Review phase hub page."""
    _phase_css()
    render_page_header("Review", "Compare results, generate reports, and deep-dive analytics")

    st.markdown("""
    <div class="hub-intro">
        Deep-dive into completed analyses. Compare runs side-by-side, decompose returns into
        factor contributions, stress-test portfolios, and generate professional reports.
        This phase is about <strong>understanding</strong> results, not just seeing numbers.
    </div>
    """, unsafe_allow_html=True)

    runs = load_runs()
    completed = sum(1 for r in runs if r.get('status') == 'completed') if runs else 0

    st.markdown(f"""
    <div class="hub-stat-row">
        {_render_stat("Completed Runs", str(completed))}
        {_render_stat("Available for Review", str(completed))}
    </div>
    """, unsafe_allow_html=True)

    # Group into sub-sections
    st.markdown('<div class="hub-section-title">Portfolio Review</div>', unsafe_allow_html=True)

    _render_tool_card(
        1, "Portfolio Analysis", "portfolio_analysis",
        "Analyze portfolio composition, sector allocation, risk metrics, and concentration. Includes position-level diagnostics and risk warnings.",
        tags=[("core", "tag-core")],
    )
    _render_tool_card(
        2, "Comprehensive Analysis", "comprehensive_analysis",
        "Full-spectrum suite: performance attribution, benchmark comparison, factor exposure, style analysis, and rebalancing analysis — all in one view.",
        tags=[("core", "tag-core")],
        detail="The most thorough single-page analysis. Runs all analytics modules on a selected run.",
    )

    st.markdown('<div class="hub-section-title">Run Comparison</div>', unsafe_allow_html=True)

    _render_tool_card(
        3, "Compare Runs", "compare_runs",
        "Side-by-side comparison of two analysis runs. Metric deltas, holding overlap, and performance divergence.",
        tags=[("optional", "tag-optional")],
    )
    _render_tool_card(
        4, "Advanced Comparison", "advanced_comparison",
        "Statistical comparison with confidence intervals, paired tests, and regime-conditional analysis across multiple runs.",
        tags=[("advanced", "tag-advanced")],
    )

    st.markdown('<div class="hub-section-title">Reports & History</div>', unsafe_allow_html=True)

    _render_tool_card(
        5, "Reports", "reports",
        "Generate PDF and markdown reports from analysis results. Export-ready format for sharing or archival.",
        tags=[("core", "tag-core")],
    )
    _render_tool_card(
        6, "Report Templates", "report_templates",
        "Create and manage reusable report templates. Schedule recurring report generation.",
        tags=[("optional", "tag-optional")],
    )
    _render_tool_card(
        7, "Analysis Runs", "analysis_runs",
        "Browse the full history of analysis runs. Filter by date, watchlist, status. View details and navigate to results.",
        tags=[("core", "tag-core")],
    )

    st.markdown('<div class="hub-section-title">Advanced Analytics</div>', unsafe_allow_html=True)

    _render_tool_card(
        8, "Event Analysis", "event_analysis",
        "Analyze portfolio performance around specific market events — Fed meetings, earnings announcements, macro data releases.",
        tags=[("advanced", "tag-advanced")],
    )
    _render_tool_card(
        9, "Monte Carlo", "monte_carlo",
        "Monte Carlo simulation of portfolio outcomes. VaR, CVaR, confidence intervals, and probability of meeting return targets.",
        tags=[("advanced", "tag-advanced")],
    )
    _render_tool_card(
        10, "Turnover Analysis", "turnover_analysis",
        "Portfolio turnover rate, churn analysis, holding period distribution, and rebalancing cost estimation.",
        tags=[("optional", "tag-optional")],
    )
    _render_tool_card(
        11, "Performance Monitoring", "performance_monitoring",
        "System performance metrics: query times, cache hit rates, database size, and memory usage.",
        tags=[("optional", "tag-optional")],
    )

    st.markdown("""
    <div class="hub-workflow-note">
        <strong>Start with:</strong> <em>Portfolio Analysis</em> for a quick overview, then
        <em>Comprehensive Analysis</em> for the deep dive. Use <em>Compare Runs</em> when
        evaluating changes (e.g., with vs without a feature).
    </div>
    """, unsafe_allow_html=True)
