"""
Overview Page
=============
Dashboard home page with summary metrics and recent activity.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import subprocess
import sys
from pathlib import Path

from ..components.sidebar import render_page_header, render_section_header
from ..components.metrics import render_metric_card, render_kpi_summary
from ..components.charts import create_performance_bar, create_returns_chart
from ..components.tables import render_runs_table
from ..components.cards import render_run_card, render_info_card
from ..components.loading import loading_spinner, render_stage_progress
from ..components.errors import ErrorHandler
from ..data import load_runs, get_available_run_folders, get_all_available_watchlists
from ..utils import format_percent, format_number, get_project_root
from ..config import COLORS
from src.analytics.fundamentals_status import FundamentalsStatusChecker


def render_overview():
    """Render the overview page."""
    render_page_header(
        "The Long Game",
        "Mid-term portfolio intelligence and analysis"
    )
    
    runs = load_runs()
    
    if not runs:
        _render_empty_state()
        return
    
    _render_summary_metrics(runs)
    _render_data_quality_summary()
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        _render_recent_runs(runs)
    
    with col2:
        _render_quick_insights(runs)
    
    if len(runs) >= 2:
        st.markdown("---")
        _render_performance_chart(runs)


def _render_empty_state():
    """Render empty state when no runs exist."""
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">📊</div>
        <h2 style="color: {dark}; margin-bottom: 0.5rem;">No Analysis Runs Yet</h2>
        <p style="color: {muted}; max-width: 400px; margin: 0 auto 2rem auto;">
            Run your first backtest to see performance metrics, stock scores, and AI-powered insights.
        </p>
    </div>
    """.format(dark=COLORS['dark'], muted=COLORS['muted']), unsafe_allow_html=True)
    
    st.code("python -m src.app.cli run-backtest --config config/config.yaml", language="bash")
    
    with st.expander("📖 Quick Start Guide"):
        st.markdown("""
        1. **Configure your watchlist** in `config/watchlists.yaml`
        2. **Set API keys** in your `.env` file
        3. **Run a backtest** using the command above
        4. **View results** in this dashboard
        5. **Build a portfolio** using the Portfolio Builder
        """)


def _render_summary_metrics(runs: list):
    """Render summary metric cards."""
    col1, col2, col3, col4 = st.columns(4)
    
    completed = [r for r in runs if r['status'] == 'completed']
    returns = [r['total_return'] for r in completed if r.get('total_return') is not None]
    sharpes = [r['sharpe_ratio'] for r in completed if r.get('sharpe_ratio') is not None]
    
    with col1:
        render_metric_card(
            "Total Runs",
            str(len(runs)),
            f"{len(completed)} completed",
            icon="📊"
        )
    
    with col2:
        avg_ret = np.mean(returns) if returns else None
        render_metric_card(
            "Avg Return",
            format_percent(avg_ret) if avg_ret is not None else "N/A",
            delta_color="positive" if avg_ret and avg_ret > 0 else "negative" if avg_ret else "normal",
            icon="📈"
        )
    
    with col3:
        avg_sharpe = np.mean(sharpes) if sharpes else None
        render_metric_card(
            "Avg Sharpe",
            format_number(avg_sharpe) if avg_sharpe is not None else "N/A",
            delta_color="positive" if avg_sharpe and avg_sharpe > 1 else "normal",
            icon="⚡"
        )
    
    with col4:
        run_folders = get_available_run_folders()
        render_metric_card(
            "Output Folders",
            str(len(run_folders)),
            "with results",
            icon="📁"
        )


@st.cache_data(ttl=600, show_spinner=False)
def _get_data_file_status():
    """Get data freshness status for key data files."""
    project_root = get_project_root()
    data_files = {
        "prices": project_root / "data" / "prices.csv",
        "fundamentals": project_root / "data" / "fundamentals.csv",
        "benchmark": project_root / "data" / "benchmark.csv",
    }

    status = {}
    now = datetime.utcnow()
    for key, path in data_files.items():
        if not path.exists():
            status[key] = {
                "exists": False,
                "last_modified": None,
                "age_days": None,
            }
            continue
        last_modified = datetime.utcfromtimestamp(path.stat().st_mtime)
        age_days = (now - last_modified).total_seconds() / 86400
        status[key] = {
            "exists": True,
            "last_modified": last_modified,
            "age_days": age_days,
        }
    return status


@st.cache_data(ttl=600, show_spinner=False)
def _get_fundamentals_completeness(symbols: tuple):
    """Get fundamentals completeness for a set of symbols."""
    checker = FundamentalsStatusChecker("data/fundamentals.csv")
    return checker.check_watchlist_fundamentals(watchlist_symbols=list(symbols))


def _render_data_quality_summary():
    """Render data freshness and completeness summary."""
    render_section_header("Data Quality & Freshness", "🧪")

    status = _get_data_file_status()
    watchlists = get_all_available_watchlists()
    all_symbols = []
    for wl in watchlists.values():
        all_symbols.extend(wl.get("symbols", []))
    unique_symbols = tuple(sorted(set(all_symbols)))

    fundamentals_summary = None
    if unique_symbols:
        fundamentals_summary = _get_fundamentals_completeness(unique_symbols)

    col1, col2, col3 = st.columns(3)

    with col1:
        prices = status.get("prices", {})
        if prices.get("exists"):
            age_days = prices.get("age_days", 0) or 0
            render_metric_card(
                "Price Data Age",
                f"{age_days:.0f} days",
                "Last update",
                icon="🕒"
            )
        else:
            render_metric_card("Price Data Age", "Missing", "prices.csv not found", icon="⚠️")
        
        # Update button
        if st.button("🔄 Update Prices", key="update_prices_btn", use_container_width=True,
                    help="Download latest price data for all watchlists"):
            _update_prices()

    with col2:
        if fundamentals_summary and fundamentals_summary.get("total_stocks", 0) > 0:
            completeness = fundamentals_summary.get("required_completeness_rate", 0.0) or 0.0
            render_metric_card(
                "Fundamentals Coverage",
                f"{completeness*100:.1f}%",
                f"{fundamentals_summary.get('stocks_complete', 0)}/{fundamentals_summary.get('total_stocks', 0)} complete",
                icon="📊"
            )
        else:
            render_metric_card("Fundamentals Coverage", "N/A", "No symbols found", icon="⚠️")

    with col3:
        benchmark = status.get("benchmark", {})
        if benchmark.get("exists"):
            age_days = benchmark.get("age_days", 0) or 0
            render_metric_card(
                "Benchmark Data Age",
                f"{age_days:.0f} days",
                "Last update",
                icon="📈"
            )
        else:
            render_metric_card("Benchmark Data Age", "Missing", "benchmark.csv not found", icon="⚠️")
        
        # Update benchmark button
        if st.button("🔄 Update Benchmark", key="update_benchmark_btn", use_container_width=True,
                    help="Download latest benchmark data (SPY/QQQ)"):
            _update_benchmark()

    warnings = []
    if not status.get("prices", {}).get("exists"):
        warnings.append("Price data missing: `data/prices.csv` not found.")
    elif status.get("prices", {}).get("age_days", 0) and status["prices"]["age_days"] > 30:
        warnings.append("Price data is older than 30 days. Consider updating.")

    if not status.get("benchmark", {}).get("exists"):
        warnings.append("Benchmark data missing: `data/benchmark.csv` not found.")
    elif status.get("benchmark", {}).get("age_days", 0) and status["benchmark"]["age_days"] > 30:
        warnings.append("Benchmark data is older than 30 days. Consider updating.")

    if fundamentals_summary and fundamentals_summary.get("required_completeness_rate", 1.0) < 0.8:
        warnings.append("Fundamentals coverage below 80%. Download fundamentals to improve scores.")

    if warnings:
        for msg in warnings:
            st.warning(msg)


def _render_recent_runs(runs: list):
    """Render recent runs section."""
    render_section_header("Recent Analysis Runs", "📋")
    
    # Show last 5 runs as cards
    for run in runs[:5]:
        render_run_card(run, show_metrics=True)
        st.markdown("")  # Spacing


def _render_quick_insights(runs: list):
    """Render quick insights panel."""
    render_section_header("Quick Insights", "💡")
    
    completed = [r for r in runs if r['status'] == 'completed']
    
    if not completed:
        render_info_card(
            "No Completed Runs",
            "Complete a backtest to see insights",
            icon="ℹ️",
            color="info"
        )
        return
    
    # Best performing run
    best_run = max(completed, key=lambda x: x.get('total_return', -float('inf')))
    if best_run.get('total_return') is not None:
        render_info_card(
            "Best Performer",
            f"**{best_run.get('name') or best_run['run_id'][:8]}**\n\n"
            f"Return: {format_percent(best_run['total_return'])}",
            icon="🏆",
            color="success"
        )
        st.markdown("")
    
    # Average stats
    returns = [r['total_return'] for r in completed if r.get('total_return') is not None]
    if returns:
        positive_rate = sum(1 for r in returns if r > 0) / len(returns)
        render_info_card(
            "Win Rate",
            f"**{positive_rate*100:.0f}%** of runs profitable",
            icon="🎯",
            color="primary"
        )
        st.markdown("")
    
    # Latest run status
    latest = runs[0]
    status_icon = {
        'completed': '✅',
        'running': '🔄',
        'failed': '❌',
        'pending': '⏳'
    }.get(latest['status'].lower(), '❓')
    
    render_info_card(
        "Latest Run",
        f"{status_icon} {latest['status'].title()}",
        icon="🕐",
        color="info",
        footer=f"ID: {latest['run_id'][:12]}..."
    )


def _render_performance_chart(runs: list):
    """Render performance over time chart."""
    render_section_header("Performance History", "📈")
    
    # Filter runs with valid data
    perf_data = []
    for r in runs:
        if r.get('created_at') and r.get('total_return') is not None:
            perf_data.append({
                'date': pd.to_datetime(r['created_at']),
                'return': r['total_return'],
                'sharpe': r.get('sharpe_ratio', 0),
                'name': r.get('name') or r['run_id'][:8]
            })
    
    if not perf_data:
        st.info("Not enough data to display performance chart")
        return
    
    perf_df = pd.DataFrame(perf_data).sort_values('date')
    
    # Create chart
    fig = create_performance_bar(
        runs=runs,
        metric='total_return',
        title="Return by Run",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def _update_prices():
    """Update price data for all watchlists."""
    try:
        import yfinance as yf
    except ImportError:
        st.error("❌ yfinance not installed. Install with: `pip install yfinance`")
        return
    
    # Import PriceDownloader from the script
    project_root = get_project_root()
    script_path = project_root / "scripts" / "download_prices.py"
    
    # Add scripts to path to import PriceDownloader
    sys.path.insert(0, str(project_root / "scripts"))
    sys.path.insert(0, str(project_root))
    
    try:
        from scripts.download_prices import PriceDownloader
    except ImportError:
        # Fallback: try importing directly
        import importlib.util
        spec = importlib.util.spec_from_file_location("download_prices", script_path)
        download_prices_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(download_prices_module)
        PriceDownloader = download_prices_module.PriceDownloader
    
    # Get all watchlists
    watchlists = get_all_available_watchlists()
    if not watchlists:
        st.warning("No watchlists found. Please configure watchlists first.")
        return
    
    # Collect all unique symbols
    all_symbols = []
    for wl in watchlists.values():
        all_symbols.extend(wl.get("symbols", []))
    unique_symbols = sorted(set(all_symbols))
    
    if not unique_symbols:
        st.warning("No symbols found in watchlists.")
        return
    
    # Show confirmation
    st.info(f"📥 Updating prices for {len(unique_symbols)} unique symbols across {len(watchlists)} watchlists...")
    
    # Calculate date range (3 years back to today)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=3*365)).strftime('%Y-%m-%d')
    
    output_path = project_root / "data" / "prices.csv"
    
    # Download with progress
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    
    try:
        downloader = PriceDownloader(str(output_path))
        
        # Show progress
        status_placeholder.info(f"🔄 Downloading {len(unique_symbols)} symbols... This may take a few minutes.")
        
        # Download data
        df = downloader.download(
            tickers=unique_symbols,
            start_date=start_date,
            end_date=end_date,
            merge_existing=True
        )
        
        if df.empty:
            st.error("❌ No data downloaded. Check your internet connection and try again.")
            return
        
        # Save data
        downloader.save(df)
        report = downloader.get_report()
        
        # Clear cache to refresh data age
        st.cache_data.clear()
        
        # Show success
        status_placeholder.success(f"✅ Price data updated successfully!")
        
        # Show summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("✅ Successful", report.get('successful', 0))
        with col2:
            st.metric("❌ Failed", report.get('failed', 0))
        with col3:
            st.metric("📊 Total Rows", len(df))
        
        if report.get('failed', 0) > 0:
            st.warning(f"⚠️ {report['failed']} symbols failed to download. Check the details below.")
            if downloader.failed_tickers:
                with st.expander("❌ Failed Symbols", expanded=True):
                    # Group by error type if failed_reasons is available
                    failed_reasons = report.get('failed_reasons', {})
                    if failed_reasons:
                        delisted = []
                        timeout = []
                        format_issues = []
                        other = []
                        
                        for ticker in downloader.failed_tickers:
                            reason = failed_reasons.get(ticker, "Unknown error")
                            if 'delisted' in reason.lower() or 'invalid' in reason.lower():
                                delisted.append((ticker, reason))
                            elif 'timeout' in reason.lower():
                                timeout.append((ticker, reason))
                            elif 'format' in reason.lower() or ticker == 'BRK.B':
                                format_issues.append((ticker, reason))
                            else:
                                other.append((ticker, reason))
                        
                        # Display grouped errors
                        if delisted:
                            st.markdown("**🗑️ Delisted/Invalid Symbols:**")
                            for ticker, reason in delisted[:20]:
                                st.markdown(f"- **{ticker}**: {reason}")
                            if len(delisted) > 20:
                                st.markdown(f"... and {len(delisted) - 20} more")
                            st.markdown("")
                        
                        if timeout:
                            st.markdown("**⏱️ Timeout Errors (try again):**")
                            for ticker, reason in timeout[:10]:
                                st.markdown(f"- **{ticker}**: {reason}")
                            if len(timeout) > 10:
                                st.markdown(f"... and {len(timeout) - 10} more")
                            st.markdown("")
                        
                        if format_issues:
                            st.markdown("**🔧 Format Issues:**")
                            for ticker, reason in format_issues:
                                st.markdown(f"- **{ticker}**: {reason}")
                            st.markdown("")
                        
                        if other:
                            st.markdown("**❓ Other Errors:**")
                            for ticker, reason in other[:10]:
                                st.markdown(f"- **{ticker}**: {reason}")
                            if len(other) > 10:
                                st.markdown(f"... and {len(other) - 10} more")
                    else:
                        # Fallback: simple list
                        failed_list = ", ".join(downloader.failed_tickers[:50])
                        st.write(failed_list)
                        if len(downloader.failed_tickers) > 50:
                            st.write(f"... and {len(downloader.failed_tickers) - 50} more")
                    
                    st.markdown("---")
                    st.markdown("**Common Issues & Fixes:**")
                    st.markdown("""
                    - **BRK.B** → Automatically converted to **BRK-B** (format issue - fixed automatically)
                    - **ATVI, SPLK, PXD** → Remove (acquired/delisted)
                    - **Timeout errors** → Try downloading again later
                    - **Others** → May be invalid or temporarily unavailable
                    
                    **Action**: Use **Watchlist Manager → Validate & Fix** to automatically fix these issues.
                    """)
                    
                    st.info("📖 See `docs/failed-symbols-guide.md` for detailed recommendations")
                    
                    # Quick fix buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔧 Go to Watchlist Manager", use_container_width=True,
                                    help="Open Watchlist Manager to fix invalid symbols"):
                            st.session_state['page'] = 'Watchlist Manager'
                            st.rerun()
                    with col2:
                        if st.button("🔄 Retry Failed Symbols", use_container_width=True,
                                    help="Try downloading failed symbols again (may work for timeouts)"):
                            st.info("💡 Use Watchlist Manager → Validate & Fix to remove invalid symbols first, then retry.")
        
        st.info("💡 The data age will refresh after you reload the page.")
        
    except Exception as e:
        ErrorHandler.render_error(
            e,
            error_type='data_loading_error',
            custom_actions=[
                "Check your internet connection",
                "Verify yfinance is installed: `pip install yfinance`",
                "Check the technical details below",
                "Try running the script manually: `python scripts/download_prices.py --watchlist <watchlist_name>`"
            ],
            show_traceback=True
        )


def _update_benchmark():
    """Update benchmark data (SPY/QQQ)."""
    project_root = get_project_root()
    benchmark_path = project_root / "data" / "benchmark.csv"
    
    try:
        import yfinance as yf
    except ImportError:
        st.error("❌ yfinance not installed. Install with: `pip install yfinance`")
        return
    
    st.info("📥 Downloading benchmark data (SPY, QQQ)...")
    
    with loading_spinner("Downloading benchmark data...", show_progress=False):
        try:
            # Calculate date range (3 years back to today)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=3*365)
            
            # Download SPY and QQQ
            benchmarks = {}
            for symbol in ['SPY', 'QQQ']:
                try:
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(start=start_date, end=end_date, auto_adjust=True)
                    
                    if not data.empty:
                        data = data.reset_index()
                        data['ticker'] = symbol
                        data['date'] = data['Date'].dt.strftime('%Y-%m-%d')
                        data = data[['date', 'ticker', 'Close']].rename(columns={'Close': 'close'})
                        benchmarks[symbol] = data
                except Exception as e:
                    st.warning(f"⚠️ Failed to download {symbol}: {e}")
            
            if benchmarks:
                # Combine and save
                all_data = pd.concat(benchmarks.values(), ignore_index=True)
                all_data.to_csv(benchmark_path, index=False)
                
                # Clear cache
                st.cache_data.clear()
                
                st.success(f"✅ Benchmark data updated successfully!")
                st.info(f"📊 Downloaded {len(all_data)} rows for {len(benchmarks)} benchmarks")
                st.info("💡 The data age will refresh after you reload the page.")
            else:
                st.error("❌ Failed to download any benchmark data")
                
        except Exception as e:
            ErrorHandler.render_error(
                e,
                error_type='data_loading_error',
                custom_actions=[
                    "Check your internet connection",
                    "Verify yfinance is installed",
                    "Check the technical details below"
                ],
                show_traceback=True
            )
