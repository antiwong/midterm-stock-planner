"""
Multi-Portfolio Comparison Dashboard Page
==========================================
Side-by-side comparison of all 4 portfolios (moby, tech_giants, semiconductors, precious_metals).

Reads from per-watchlist DB files: data/paper_trading_{watchlist}.db
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ..components.sidebar import render_page_header, render_section_header


DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"

PORTFOLIOS = ["moby_picks", "tech_giants", "semiconductors", "precious_metals"]
PORTFOLIO_COLORS = {
    "moby_picks": "#6366f1",
    "tech_giants": "#06b6d4",
    "semiconductors": "#10b981",
    "precious_metals": "#f59e0b",
}


def _get_db(watchlist: str) -> Optional[sqlite3.Connection]:
    """Get paper trading DB connection for a specific watchlist."""
    db_path = DATA_DIR / f"paper_trading_{watchlist}.db"
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _query_portfolio(watchlist: str, sql: str, params=()) -> List[Dict[str, Any]]:
    """Run a query against a specific portfolio's DB."""
    conn = _get_db(watchlist)
    if conn is None:
        return []
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def render_multi_portfolio():
    """Render multi-portfolio comparison dashboard page."""
    render_page_header(
        "Multi-Portfolio",
        "Compare 4 portfolios side-by-side"
    )

    # Check which portfolios have data
    available = []
    for wl in PORTFOLIOS:
        db_path = DATA_DIR / f"paper_trading_{wl}.db"
        if db_path.exists():
            available.append(wl)

    if not available:
        st.warning(
            "No portfolio data found. Run `python scripts/daily_routine.py daily` "
            "to start generating portfolio data."
        )
        return

    st.info(f"Portfolios with data: {', '.join(available)}")

    # Summary cards
    _render_summary_cards(available)

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Performance", "Weekly Summary", "Position Overlap", "Signal Agreement"
    ])

    with tab1:
        _render_performance(available)

    with tab2:
        _render_weekly_summary(available)

    with tab3:
        _render_position_overlap(available)

    with tab4:
        _render_signal_agreement(available)


def _render_summary_cards(portfolios: List[str]):
    """Show summary metrics for each portfolio."""
    cols = st.columns(len(portfolios))

    for i, wl in enumerate(portfolios):
        with cols[i]:
            state = _query_portfolio(wl, "SELECT * FROM portfolio_state WHERE id = 1")
            snap = _query_portfolio(
                wl,
                "SELECT portfolio_value, daily_return, cumulative_return "
                "FROM daily_snapshots ORDER BY date DESC LIMIT 1"
            )
            positions = _query_portfolio(
                wl, "SELECT COUNT(*) as cnt FROM positions WHERE is_active = 1"
            )

            if state and snap:
                val = snap[0]["portfolio_value"]
                cum_ret = snap[0]["cumulative_return"]
                daily_ret = snap[0]["daily_return"]
                pos_count = positions[0]["cnt"] if positions else 0
                mode = "Alpaca" if wl == "moby_picks" else "Local"

                st.markdown(f"**{wl}** ({mode})")
                st.metric("Value", f"${val:,.0f}", f"{daily_ret:+.2%}")
                st.caption(f"Total: {cum_ret:+.2%} | {pos_count} positions")
            else:
                st.markdown(f"**{wl}**")
                st.caption("No data yet")


def _render_performance(portfolios: List[str]):
    """Overlay equity curves for all portfolios."""
    render_section_header("Performance Comparison", "")

    days = st.slider("Lookback (days)", 7, 365, 90, key="perf_days")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    fig = go.Figure()
    has_data = False

    for wl in portfolios:
        snaps = _query_portfolio(
            wl,
            "SELECT date, portfolio_value, cumulative_return "
            "FROM daily_snapshots WHERE date >= ? ORDER BY date",
            (start_date,)
        )
        if not snaps:
            continue

        has_data = True
        df = pd.DataFrame(snaps)
        df["date"] = pd.to_datetime(df["date"])

        # Normalize to 100 for comparison
        base = df["portfolio_value"].iloc[0]
        df["normalized"] = (df["portfolio_value"] / base) * 100

        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["normalized"],
            mode="lines",
            name=wl,
            line=dict(color=PORTFOLIO_COLORS.get(wl, "#888")),
            hovertemplate="%{x|%Y-%m-%d}<br>%{y:.1f} (base=100)<extra></extra>",
        ))

    if not has_data:
        st.info("No daily snapshots available yet.")
        return

    fig.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(
        title="Portfolio Performance (Normalized to 100)",
        yaxis_title="Value (base=100)",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_weekly_summary(portfolios: List[str]):
    """Weekly return table for all portfolios."""
    render_section_header("Weekly Summary", "")

    rows = []
    for wl in portfolios:
        snaps = _query_portfolio(
            wl,
            "SELECT date, portfolio_value, daily_return, cumulative_return "
            "FROM daily_snapshots ORDER BY date DESC LIMIT 5"
        )
        if not snaps:
            rows.append({"Portfolio": wl, "Status": "No data"})
            continue

        returns = [s["daily_return"] for s in snaps if s["daily_return"] is not None]
        weekly_return = sum(returns) if returns else 0.0
        vol = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0.0
        sharpe = (np.mean(returns) * 252) / vol if vol > 0 else 0.0

        rows.append({
            "Portfolio": wl,
            "Value": f"${snaps[0]['portfolio_value']:,.0f}",
            "Week Return": f"{weekly_return:+.2%}",
            "Total Return": f"{snaps[0]['cumulative_return']:+.2%}",
            "Ann. Vol": f"{vol:.1%}",
            "Sharpe (est)": f"{sharpe:.2f}",
            "Days": len(snaps),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_position_overlap(portfolios: List[str]):
    """Show ticker overlap across portfolios."""
    render_section_header("Position Overlap", "")

    positions_by_wl = {}
    for wl in portfolios:
        pos = _query_portfolio(
            wl, "SELECT ticker FROM positions WHERE is_active = 1"
        )
        positions_by_wl[wl] = set(p["ticker"] for p in pos)

    if not any(positions_by_wl.values()):
        st.info("No active positions in any portfolio.")
        return

    # Overlap matrix
    all_tickers = sorted(set().union(*positions_by_wl.values()))

    if not all_tickers:
        st.info("No active positions found.")
        return

    # Build presence matrix
    data = []
    for ticker in all_tickers:
        row = {"Ticker": ticker}
        count = 0
        for wl in portfolios:
            present = ticker in positions_by_wl.get(wl, set())
            row[wl] = "Y" if present else ""
            if present:
                count += 1
        row["Count"] = count
        data.append(row)

    df = pd.DataFrame(data).sort_values("Count", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Summary
    overlapping = [t for t in all_tickers if sum(
        1 for wl in portfolios if t in positions_by_wl.get(wl, set())
    ) > 1]
    if overlapping:
        st.caption(f"Shared across 2+ portfolios: {', '.join(overlapping[:20])}")


def _render_signal_agreement(portfolios: List[str]):
    """Show where multiple portfolios agree on BUY/SELL."""
    render_section_header("Signal Agreement", "")

    # Get latest signals from each portfolio
    all_signals = {}
    latest_dates = {}
    for wl in portfolios:
        signals = _query_portfolio(
            wl,
            "SELECT ticker, prediction, rank, action, date "
            "FROM signals ORDER BY date DESC LIMIT 100"
        )
        if not signals:
            continue

        latest_date = signals[0]["date"]
        latest_dates[wl] = latest_date
        # Only keep signals from the latest date
        all_signals[wl] = {
            s["ticker"]: {"action": s["action"], "rank": s["rank"], "score": s["prediction"]}
            for s in signals if s["date"] == latest_date
        }

    if not all_signals:
        st.info("No signal data available.")
        return

    # Find tickers that appear in multiple portfolios
    all_tickers = sorted(set().union(*(s.keys() for s in all_signals.values())))

    data = []
    for ticker in all_tickers:
        row = {"Ticker": ticker}
        buy_count = 0
        sell_count = 0
        for wl in portfolios:
            sig = all_signals.get(wl, {}).get(ticker)
            if sig:
                action = sig["action"]
                row[f"{wl}"] = f"{action} (#{sig['rank']})"
                if action == "BUY":
                    buy_count += 1
                elif action == "SELL":
                    sell_count += 1
            else:
                row[f"{wl}"] = ""
        row["BUY Votes"] = buy_count
        row["SELL Votes"] = sell_count
        # Only include tickers present in 2+ portfolios
        if buy_count + sell_count >= 2:
            data.append(row)

    if not data:
        st.info("No overlapping signals across portfolios.")
        return

    df = pd.DataFrame(data).sort_values("BUY Votes", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Highlight consensus
    consensus_buys = df[df["BUY Votes"] >= 3]["Ticker"].tolist()
    consensus_sells = df[df["SELL Votes"] >= 3]["Ticker"].tolist()
    if consensus_buys:
        st.success(f"Consensus BUY (3+ portfolios): {', '.join(consensus_buys)}")
    if consensus_sells:
        st.error(f"Consensus SELL (3+ portfolios): {', '.join(consensus_sells)}")
