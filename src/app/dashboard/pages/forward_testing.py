"""
Forward Testing Dashboard Page
================================
Track forward prediction accuracy across all portfolios and horizons.

Reads from data/forward_journal.db (created by scripts/daily_routine.py).
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


DB_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "forward_journal.db"


def _get_db() -> Optional[sqlite3.Connection]:
    """Get forward journal database connection."""
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


def render_forward_testing():
    """Render forward testing dashboard page."""
    render_page_header(
        "Forward Testing",
        "Track prediction accuracy over time"
    )

    conn = _get_db()
    if conn is None:
        st.warning(
            "No forward testing data found. Run `python scripts/daily_routine.py daily` "
            "to start logging predictions."
        )
        return
    conn.close()

    # Summary stats
    stats = _query("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN evaluated_at IS NOT NULL THEN 1 END) as evaluated,
            COUNT(CASE WHEN evaluated_at IS NULL AND maturity_date > date('now') THEN 1 END) as active,
            COUNT(CASE WHEN evaluated_at IS NULL AND maturity_date <= date('now') THEN 1 END) as pending,
            MIN(prediction_date) as first_date,
            MAX(prediction_date) as last_date
        FROM predictions
    """)

    if not stats or stats[0]["total"] == 0:
        st.info("No predictions logged yet. Run the daily routine to start.")
        return

    s = stats[0]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Predictions", f"{s['total']:,}")
    col2.metric("Evaluated", f"{s['evaluated']:,}")
    col3.metric("Active (Pending)", f"{s['active']:,}")
    col4.metric("Awaiting Eval", f"{s['pending']:,}")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Hit Rates", "Accuracy Trend", "Active Predictions", "Full History"
    ])

    with tab1:
        _render_hit_rates()

    with tab2:
        _render_accuracy_trend()

    with tab3:
        _render_active_predictions()

    with tab4:
        _render_full_history()


def _render_hit_rates():
    """Hit rates by watchlist and horizon."""
    render_section_header("Hit Rates by Portfolio", "")

    rows = _query("""
        SELECT
            watchlist,
            horizon_days,
            COUNT(*) as total,
            SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits,
            AVG(actual_return) as avg_return
        FROM predictions
        WHERE evaluated_at IS NOT NULL AND predicted_action = 'BUY'
        GROUP BY watchlist, horizon_days
        ORDER BY watchlist, horizon_days
    """)

    if not rows:
        st.info("No evaluated predictions yet. Predictions need time to mature.")
        return

    df = pd.DataFrame(rows)
    df["hit_rate"] = df["hits"] / df["total"]
    df["hit_rate_pct"] = df["hit_rate"].map(lambda x: f"{x:.1%}")
    df["avg_return_pct"] = df["avg_return"].map(lambda x: f"{x:+.2%}")

    # Bar chart
    fig = px.bar(
        df, x="watchlist", y="hit_rate", color="horizon_days",
        barmode="group", text="hit_rate_pct",
        labels={"hit_rate": "Hit Rate", "watchlist": "Portfolio", "horizon_days": "Horizon"},
        color_discrete_sequence=["#6366f1", "#06b6d4"],
    )
    fig.update_layout(yaxis_tickformat=".0%", height=400)
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    # Table
    display_cols = ["watchlist", "horizon_days", "total", "hits", "hit_rate_pct", "avg_return_pct"]
    st.dataframe(
        df[display_cols].rename(columns={
            "watchlist": "Portfolio",
            "horizon_days": "Horizon (days)",
            "total": "Predictions",
            "hits": "Hits",
            "hit_rate_pct": "Hit Rate",
            "avg_return_pct": "Avg Return",
        }),
        use_container_width=True,
        hide_index=True,
    )


def _render_accuracy_trend():
    """Cumulative accuracy over time."""
    render_section_header("Accuracy Trend", "")

    horizon = st.radio("Horizon", [5, 63], horizontal=True, key="trend_horizon")

    rows = _query("""
        SELECT
            prediction_date,
            watchlist,
            SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits,
            COUNT(*) as total,
            AVG(actual_return) as avg_return
        FROM predictions
        WHERE evaluated_at IS NOT NULL
          AND predicted_action = 'BUY'
          AND horizon_days = ?
        GROUP BY prediction_date, watchlist
        ORDER BY prediction_date
    """, (horizon,))

    if not rows:
        st.info(f"No evaluated {horizon}-day predictions yet.")
        return

    df = pd.DataFrame(rows)
    df["prediction_date"] = pd.to_datetime(df["prediction_date"])
    df["hit_rate"] = df["hits"] / df["total"]

    # Compute rolling hit rate per watchlist
    fig = go.Figure()
    for wl in df["watchlist"].unique():
        wl_df = df[df["watchlist"] == wl].sort_values("prediction_date")
        wl_df["rolling_hits"] = wl_df["hits"].cumsum()
        wl_df["rolling_total"] = wl_df["total"].cumsum()
        wl_df["rolling_rate"] = wl_df["rolling_hits"] / wl_df["rolling_total"]

        fig.add_trace(go.Scatter(
            x=wl_df["prediction_date"],
            y=wl_df["rolling_rate"],
            mode="lines+markers",
            name=wl,
            hovertemplate="%{x|%Y-%m-%d}<br>Hit rate: %{y:.1%}<extra></extra>",
        ))

    fig.add_hline(y=0.5, line_dash="dash", line_color="gray",
                  annotation_text="50% (random)")
    fig.update_layout(
        title=f"Cumulative {horizon}-Day Hit Rate",
        yaxis_title="Hit Rate",
        yaxis_tickformat=".0%",
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_active_predictions():
    """Predictions not yet matured."""
    render_section_header("Active Predictions", "")

    rows = _query("""
        SELECT prediction_date, maturity_date, ticker, watchlist,
               horizon_days, predicted_score, predicted_rank, predicted_action, entry_price
        FROM predictions
        WHERE maturity_date > date('now') AND evaluated_at IS NULL
        ORDER BY maturity_date, watchlist, predicted_rank
    """)

    if not rows:
        st.info("No active predictions. Run the daily routine to log new ones.")
        return

    df = pd.DataFrame(rows)
    st.metric("Active Predictions", len(df))

    # Filter
    col1, col2 = st.columns(2)
    with col1:
        wl_filter = st.selectbox(
            "Portfolio", ["All"] + sorted(df["watchlist"].unique().tolist()),
            key="active_wl_filter"
        )
    with col2:
        horizon_filter = st.selectbox(
            "Horizon", ["All"] + sorted(df["horizon_days"].unique().tolist()),
            key="active_horizon_filter"
        )

    if wl_filter != "All":
        df = df[df["watchlist"] == wl_filter]
    if horizon_filter != "All":
        df = df[df["horizon_days"] == int(horizon_filter)]

    st.dataframe(
        df.rename(columns={
            "prediction_date": "Predicted",
            "maturity_date": "Matures",
            "ticker": "Ticker",
            "watchlist": "Portfolio",
            "horizon_days": "Horizon",
            "predicted_score": "Score",
            "predicted_rank": "Rank",
            "predicted_action": "Action",
            "entry_price": "Entry Price",
        }),
        use_container_width=True,
        hide_index=True,
    )


def _render_full_history():
    """Searchable table of all predictions."""
    render_section_header("Prediction History", "")

    col1, col2, col3 = st.columns(3)
    with col1:
        ticker_search = st.text_input("Ticker", key="hist_ticker")
    with col2:
        wl_options = _query("SELECT DISTINCT watchlist FROM predictions ORDER BY watchlist")
        wl_list = ["All"] + [r["watchlist"] for r in wl_options]
        wl_filter = st.selectbox("Portfolio", wl_list, key="hist_wl")
    with col3:
        eval_filter = st.selectbox("Status", ["All", "Evaluated", "Pending"], key="hist_eval")

    conditions = ["1=1"]
    params: list = []

    if ticker_search:
        conditions.append("ticker LIKE ?")
        params.append(f"%{ticker_search.upper()}%")
    if wl_filter != "All":
        conditions.append("watchlist = ?")
        params.append(wl_filter)
    if eval_filter == "Evaluated":
        conditions.append("evaluated_at IS NOT NULL")
    elif eval_filter == "Pending":
        conditions.append("evaluated_at IS NULL")

    where = " AND ".join(conditions)
    params.append(500)

    rows = _query(f"""
        SELECT prediction_date, maturity_date, ticker, watchlist, horizon_days,
               predicted_score, predicted_rank, predicted_action, entry_price,
               actual_price, actual_return, hit, evaluated_at
        FROM predictions
        WHERE {where}
        ORDER BY prediction_date DESC, watchlist, predicted_rank
        LIMIT ?
    """, params)

    if not rows:
        st.info("No predictions match the filter.")
        return

    df = pd.DataFrame(rows)
    # Format for display
    if "actual_return" in df.columns:
        df["actual_return"] = df["actual_return"].apply(
            lambda x: f"{x:+.2%}" if x is not None else ""
        )
    if "hit" in df.columns:
        df["hit"] = df["hit"].apply(
            lambda x: "HIT" if x == 1 else ("MISS" if x == 0 else "")
        )

    st.dataframe(df, use_container_width=True, hide_index=True)
