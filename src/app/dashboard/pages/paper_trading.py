"""
Paper Trading Dashboard Page
=============================
Track paper trading portfolio performance, positions, signals, and trade history.

Reads from data/paper_trading.db (created by scripts/paper_trading.py).
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from ..components.sidebar import render_page_header, render_section_header


DB_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "paper_trading.db"


def _get_db() -> Optional[sqlite3.Connection]:
    """Get paper trading database connection."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _query(sql: str, params=()) -> List[Dict[str, Any]]:
    """Run a query and return list of dicts."""
    conn = _get_db()
    if conn is None:
        return []
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def render_paper_trading():
    """Render paper trading dashboard page."""
    render_page_header(
        "Paper Trading",
        "Simulated portfolio tracking and signal history"
    )

    conn = _get_db()
    if conn is None:
        st.warning(
            "No paper trading data found. Run `python scripts/paper_trading.py run` to start."
        )
        st.code("python scripts/paper_trading.py run --watchlist tech_giants", language="bash")
        return
    conn.close()

    # KPI cards
    _render_kpi_cards()

    # Tabs
    tabs = st.tabs([
        "📈 Performance",
        "💼 Positions",
        "📊 Signals",
        "📋 Trades",
        "⚙️ Controls",
    ])

    with tabs[0]:
        _render_performance_tab()
    with tabs[1]:
        _render_positions_tab()
    with tabs[2]:
        _render_signals_tab()
    with tabs[3]:
        _render_trades_tab()
    with tabs[4]:
        _render_controls_tab()


# ---------------------------------------------------------------------------
# KPI Cards
# ---------------------------------------------------------------------------

def _render_kpi_cards():
    """Top-level portfolio KPI cards."""
    state = _query("SELECT * FROM portfolio_state WHERE id = 1")
    if not state:
        return
    state = state[0]

    positions = _query("SELECT * FROM positions WHERE is_active = 1")
    snapshots = _query("SELECT * FROM daily_snapshots ORDER BY date DESC LIMIT 2")

    cash = state.get("cash", 0)
    initial = state.get("initial_value", 100000)

    # Calculate invested value from latest snapshot or positions
    if snapshots:
        latest = snapshots[0]
        portfolio_value = latest["portfolio_value"]
        invested = latest["invested"]
        cum_return = latest.get("cumulative_return", 0) or 0
        daily_return = latest.get("daily_return", 0) or 0
    else:
        invested = 0
        portfolio_value = cash
        cum_return = 0
        daily_return = 0

    total_return_pct = cum_return * 100

    # Compute Sharpe from snapshots
    all_snaps = _query("SELECT daily_return FROM daily_snapshots ORDER BY date")
    if len(all_snaps) > 5:
        daily_rets = [s["daily_return"] for s in all_snaps if s["daily_return"] is not None]
        if daily_rets and np.std(daily_rets) > 0:
            sharpe = np.mean(daily_rets) / np.std(daily_rets) * np.sqrt(252)
        else:
            sharpe = 0
    else:
        sharpe = 0

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Portfolio Value",
            f"${portfolio_value:,.0f}",
            delta=f"{daily_return:+.2%}" if snapshots else None,
        )
    with col2:
        st.metric(
            "Total Return",
            f"{total_return_pct:+.2f}%",
            delta=f"${portfolio_value - initial:+,.0f}",
        )
    with col3:
        st.metric("Sharpe Ratio", f"{sharpe:.2f}")
    with col4:
        st.metric("Positions", f"{len(positions)}")
    with col5:
        st.metric(
            "Cash",
            f"${cash:,.0f}",
            delta=f"{cash / portfolio_value * 100:.0f}% of portfolio" if portfolio_value > 0 else None,
            delta_color="off",
        )


# ---------------------------------------------------------------------------
# Performance Tab
# ---------------------------------------------------------------------------

def _render_performance_tab():
    """Portfolio value and returns over time."""
    render_section_header("Portfolio Performance", "📈")

    snapshots = _query("SELECT * FROM daily_snapshots ORDER BY date")
    if not snapshots:
        st.info("No performance data yet. Run paper trading for at least one day.")
        return

    df = pd.DataFrame(snapshots)
    df["date"] = pd.to_datetime(df["date"])

    # Portfolio value chart
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.65, 0.35],
        subplot_titles=("Portfolio Value", "Daily Returns"),
    )

    # Portfolio value line
    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["portfolio_value"],
            mode="lines",
            name="Portfolio",
            line=dict(color="#2962FF", width=2),
            fill="tozeroy",
            fillcolor="rgba(41, 98, 255, 0.1)",
        ),
        row=1, col=1,
    )

    # Benchmark cumulative (scaled to initial value)
    if "benchmark_cumulative" in df.columns:
        state = _query("SELECT initial_value FROM portfolio_state WHERE id = 1")
        initial = state[0]["initial_value"] if state else 100000
        bench_value = initial * (1 + df["benchmark_cumulative"].fillna(0))
        fig.add_trace(
            go.Scatter(
                x=df["date"], y=bench_value,
                mode="lines",
                name="SPY Benchmark",
                line=dict(color="#FF6D00", width=1.5, dash="dash"),
            ),
            row=1, col=1,
        )

    # Daily returns bar chart
    colors = ["#4CAF50" if r >= 0 else "#F44336" for r in df["daily_return"].fillna(0)]
    fig.add_trace(
        go.Bar(
            x=df["date"], y=df["daily_return"].fillna(0) * 100,
            name="Daily Return %",
            marker_color=colors,
        ),
        row=2, col=1,
    )

    fig.update_layout(
        height=550,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=60, r=20, t=40, b=20),
    )
    fig.update_yaxes(title_text="Value ($)", row=1, col=1)
    fig.update_yaxes(title_text="Return (%)", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # Cumulative return comparison
    if len(df) > 1:
        render_section_header("Cumulative Returns", "📊")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df["date"], y=df["cumulative_return"].fillna(0) * 100,
            mode="lines", name="Portfolio",
            line=dict(color="#2962FF", width=2),
        ))
        if "benchmark_cumulative" in df.columns:
            fig2.add_trace(go.Scatter(
                x=df["date"], y=df["benchmark_cumulative"].fillna(0) * 100,
                mode="lines", name="SPY",
                line=dict(color="#FF6D00", width=1.5, dash="dash"),
            ))
        fig2.update_layout(
            height=300,
            yaxis_title="Cumulative Return (%)",
            showlegend=True,
            margin=dict(l=60, r=20, t=20, b=20),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Stats table
    if len(df) > 1:
        render_section_header("Performance Statistics", "📋")
        daily_rets = df["daily_return"].dropna()
        stats = {
            "Total Return": f"{df['cumulative_return'].iloc[-1] * 100:.2f}%",
            "Best Day": f"{daily_rets.max() * 100:+.2f}%",
            "Worst Day": f"{daily_rets.min() * 100:+.2f}%",
            "Avg Daily Return": f"{daily_rets.mean() * 100:+.3f}%",
            "Daily Volatility": f"{daily_rets.std() * 100:.3f}%",
            "Trading Days": str(len(df)),
            "Win Rate": f"{(daily_rets > 0).sum() / len(daily_rets) * 100:.1f}%",
        }

        # Max drawdown
        cum_vals = (1 + daily_rets).cumprod()
        running_max = cum_vals.cummax()
        drawdowns = (cum_vals - running_max) / running_max
        stats["Max Drawdown"] = f"{drawdowns.min() * 100:.2f}%"

        col1, col2 = st.columns(2)
        items = list(stats.items())
        mid = len(items) // 2
        with col1:
            for k, v in items[:mid]:
                st.markdown(f"**{k}:** {v}")
        with col2:
            for k, v in items[mid:]:
                st.markdown(f"**{k}:** {v}")


# ---------------------------------------------------------------------------
# Positions Tab
# ---------------------------------------------------------------------------

def _render_positions_tab():
    """Current and historical positions."""
    render_section_header("Active Positions", "💼")

    positions = _query("SELECT * FROM positions WHERE is_active = 1 ORDER BY weight DESC")
    if not positions:
        st.info("No active positions. Run paper trading to open positions.")
        return

    # Get latest prices from snapshots
    latest_snap = _query("SELECT positions_json FROM daily_snapshots ORDER BY date DESC LIMIT 1")
    price_map = {}
    if latest_snap and latest_snap[0].get("positions_json"):
        try:
            snap_positions = json.loads(latest_snap[0]["positions_json"])
            price_map = {p["ticker"]: p.get("current_price", 0) for p in snap_positions}
        except (json.JSONDecodeError, TypeError):
            pass

    # Build positions table
    rows = []
    for p in positions:
        current_price = price_map.get(p["ticker"], p["entry_price"])
        pnl = (current_price - p["entry_price"]) * p["shares"]
        pnl_pct = (current_price / p["entry_price"] - 1) * 100 if p["entry_price"] > 0 else 0
        rows.append({
            "Ticker": p["ticker"],
            "Shares": f"{p['shares']:.1f}",
            "Entry Price": f"${p['entry_price']:.2f}",
            "Current Price": f"${current_price:.2f}",
            "P&L": f"${pnl:+,.2f}",
            "P&L %": f"{pnl_pct:+.2f}%",
            "Weight": f"{p['weight']:.1%}",
            "Entry Date": p["entry_date"],
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Weight allocation pie chart
    if len(positions) > 0:
        render_section_header("Portfolio Allocation", "🥧")
        tickers = [p["ticker"] for p in positions]
        weights = [p["weight"] for p in positions]
        cash_weight = 1 - sum(weights)
        if cash_weight > 0.01:
            tickers.append("Cash")
            weights.append(cash_weight)

        fig = go.Figure(data=[go.Pie(
            labels=tickers,
            values=weights,
            hole=0.4,
            textinfo="label+percent",
            marker=dict(colors=px.colors.qualitative.Set2),
        )])
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Closed positions
    render_section_header("Closed Positions", "📦")
    closed = _query(
        "SELECT * FROM positions WHERE is_active = 0 ORDER BY exit_date DESC LIMIT 50"
    )
    if closed:
        closed_rows = []
        for p in closed:
            closed_rows.append({
                "Ticker": p["ticker"],
                "Entry": f"${p['entry_price']:.2f}",
                "Exit": f"${p.get('exit_price', 0):.2f}",
                "Shares": f"{p['shares']:.1f}",
                "Realized P&L": f"${p.get('realized_pnl', 0):+,.2f}",
                "Held": f"{p['entry_date']} → {p.get('exit_date', '?')}",
            })
        st.dataframe(pd.DataFrame(closed_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No closed positions yet.")


# ---------------------------------------------------------------------------
# Signals Tab
# ---------------------------------------------------------------------------

def _render_signals_tab():
    """Signal history — model predictions over time."""
    render_section_header("Signal History", "📊")

    # Date filter
    dates = _query("SELECT DISTINCT date FROM signals ORDER BY date DESC LIMIT 30")
    if not dates:
        st.info("No signals generated yet. Run paper trading to generate signals.")
        return

    date_options = [d["date"] for d in dates]
    selected_date = st.selectbox("Select Date", date_options, index=0)

    signals = _query(
        "SELECT * FROM signals WHERE date = ? ORDER BY rank",
        (selected_date,)
    )

    if signals:
        df = pd.DataFrame(signals)

        # Color-coded signal table
        rows = []
        for s in signals:
            action = s.get("action", "HOLD")
            rows.append({
                "Rank": s["rank"],
                "Ticker": s["ticker"],
                "Score": f"{s['prediction']:.4f}",
                "Percentile": f"{s.get('percentile', 0):.0f}%",
                "Action": action,
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Signal score bar chart
        fig = go.Figure()
        colors = ["#4CAF50" if s.get("action") == "BUY" else "#9E9E9E"
                  for s in signals]
        fig.add_trace(go.Bar(
            x=[s["ticker"] for s in signals],
            y=[s["prediction"] for s in signals],
            marker_color=colors,
            text=[s.get("action", "") for s in signals],
            textposition="outside",
        ))
        fig.update_layout(
            height=350,
            xaxis_title="Ticker",
            yaxis_title="Prediction Score",
            title=f"Signals for {selected_date}",
            margin=dict(l=60, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Signal consistency over time
    render_section_header("Signal Consistency", "🔄")
    recent_signals = _query(
        "SELECT date, ticker, rank FROM signals WHERE rank <= 5 ORDER BY date DESC LIMIT 150"
    )
    if recent_signals:
        sig_df = pd.DataFrame(recent_signals)
        # Count how often each ticker appears in top 5
        freq = sig_df["ticker"].value_counts().head(10)
        fig2 = go.Figure(go.Bar(
            x=freq.index,
            y=freq.values,
            marker_color="#2962FF",
        ))
        fig2.update_layout(
            height=300,
            title="Top 5 Signal Frequency (last 30 days)",
            xaxis_title="Ticker",
            yaxis_title="Times in Top 5",
            margin=dict(l=60, r=20, t=40, b=20),
        )
        st.plotly_chart(fig2, use_container_width=True)


# ---------------------------------------------------------------------------
# Trades Tab
# ---------------------------------------------------------------------------

def _render_trades_tab():
    """Trade history and execution analysis."""
    render_section_header("Trade History", "📋")

    trades = _query("SELECT * FROM trades ORDER BY date DESC, id DESC LIMIT 100")
    if not trades:
        st.info("No trades executed yet.")
        return

    rows = []
    for t in trades:
        rows.append({
            "Date": t["date"],
            "Action": t["action"],
            "Ticker": t["ticker"],
            "Shares": f"{t['shares']:.1f}",
            "Price": f"${t['price']:.2f}",
            "Value": f"${t['value']:,.2f}",
            "Cost": f"${t['cost']:.2f}",
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Trade summary stats
    render_section_header("Trade Summary", "📊")
    trade_df = pd.DataFrame(trades)

    col1, col2, col3 = st.columns(3)
    with col1:
        total_trades = len(trade_df)
        buys = len(trade_df[trade_df["action"] == "BUY"])
        sells = len(trade_df[trade_df["action"] == "SELL"])
        st.metric("Total Trades", total_trades)
        st.markdown(f"Buys: {buys} | Sells: {sells}")
    with col2:
        total_cost = trade_df["cost"].sum()
        st.metric("Total Transaction Costs", f"${total_cost:,.2f}")
    with col3:
        total_volume = trade_df["value"].sum()
        st.metric("Total Volume Traded", f"${total_volume:,.0f}")

    # Trades over time
    if len(trade_df) > 1:
        trade_df["date"] = pd.to_datetime(trade_df["date"])
        daily_trades = trade_df.groupby("date").agg(
            count=("id", "count"),
            volume=("value", "sum"),
            cost=("cost", "sum"),
        ).reset_index()

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(x=daily_trades["date"], y=daily_trades["count"],
                   name="Trade Count", marker_color="#2962FF"),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(x=daily_trades["date"], y=daily_trades["cost"].cumsum(),
                       name="Cumulative Costs", line=dict(color="#F44336", width=2)),
            secondary_y=True,
        )
        fig.update_layout(
            height=300,
            title="Trading Activity Over Time",
            margin=dict(l=60, r=60, t=40, b=20),
        )
        fig.update_yaxes(title_text="Trades", secondary_y=False)
        fig.update_yaxes(title_text="Cumulative Cost ($)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Controls Tab
# ---------------------------------------------------------------------------

def _render_controls_tab():
    """Configuration and manual controls."""
    render_section_header("Paper Trading Controls", "⚙️")

    state = _query("SELECT * FROM portfolio_state WHERE id = 1")
    if state:
        state = state[0]
        st.markdown(f"**Initial Capital:** ${state.get('initial_value', 100000):,.2f}")
        st.markdown(f"**Current Cash:** ${state.get('cash', 0):,.2f}")
        st.markdown(f"**Last Updated:** {state.get('last_updated', 'Never')}")

    st.divider()

    render_section_header("Quick Commands", "🚀")
    st.markdown("""
Copy and run these in your terminal:

**Run daily signal generation:**
```bash
python scripts/paper_trading.py run --watchlist tech_giants
```

**Check status:**
```bash
python scripts/paper_trading.py status
```

**View trade history:**
```bash
python scripts/paper_trading.py history --last 30
```

**Setup cron (automate daily):**
```bash
python scripts/paper_trading.py setup-cron
```
""")

    st.divider()

    render_section_header("Configuration", "🔧")

    st.markdown("""
Current model configuration (from `config/config.yaml`):

| Setting | Value | Rationale |
|---------|-------|-----------|
| **Features** | MACD + Bollinger + ADX | Validated by regression test (Sharpe=1.34) |
| **RSI** | Disabled | Hurts cross-sectional model (-0.28 Sharpe) |
| **Momentum** | Disabled | Hurts cross-sectional model (-0.24 Sharpe) |
| **Top N** | 5 stocks | Better differentiation than top 10 |
| **Max Position** | 20% | Prevents single-stock concentration |
| **Stop Loss** | -15% | Limits per-position drawdown |
| **VIX Scaling** | Enabled | Reduces exposure at VIX>30 |
| **Transaction Cost** | 0.1% | Includes bid-ask spread |
""")

    st.divider()

    # Reset option
    render_section_header("Reset Portfolio", "🔄")
    st.warning("This will delete all paper trading data and start fresh.")
    if st.button("Reset Paper Trading Portfolio", type="secondary"):
        if st.session_state.get("confirm_reset"):
            import os
            if DB_PATH.exists():
                os.remove(str(DB_PATH))
                st.success("Paper trading data cleared. Run `paper_trading.py run` to start fresh.")
                st.session_state["confirm_reset"] = False
                st.rerun()
        else:
            st.session_state["confirm_reset"] = True
            st.warning("Click again to confirm reset.")
