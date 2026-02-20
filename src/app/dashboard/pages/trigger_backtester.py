"""Trigger Backtester Page.

Interactive backtesting interface for buy/sell trigger strategies on individual stocks.
Supports RSI, MACD, and Bollinger Band signals with configurable parameters.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..components.sidebar import render_page_header, render_section_header
from ..components.metrics import render_metric_card
from ..config import COLORS, CHART_COLORS

from src.backtest.trigger_backtest import (
    TriggerConfig,
    run_trigger_backtest,
    optimize_parameters,
    PARAM_GRIDS,
)


def _load_price_data_for_ticker(ticker: str) -> pd.DataFrame:
    """Load price data for a single ticker from data/prices.csv."""
    try:
        df = pd.read_csv("data/prices.csv", parse_dates=["date"])
        df["ticker"] = df["ticker"].str.upper().str.strip()
        ticker_df = df[df["ticker"] == ticker.upper().strip()].copy()
        return ticker_df.sort_values("date").reset_index(drop=True)
    except FileNotFoundError:
        return pd.DataFrame()


def _get_available_tickers() -> list:
    """Get list of available tickers from prices.csv."""
    try:
        df = pd.read_csv("data/prices.csv", usecols=["ticker"])
        return sorted(df["ticker"].str.upper().str.strip().unique().tolist())
    except (FileNotFoundError, Exception):
        return []


def _fetch_yfinance_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Fetch OHLCV data from yfinance for a single ticker."""
    import yfinance as yf
    data = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data.reset_index()
    data.columns = [c.lower() for c in data.columns]
    data["ticker"] = ticker.upper()
    return data[["date", "ticker", "open", "high", "low", "close", "volume"]].copy()


def _create_price_chart_with_signals(results) -> go.Figure:
    """Create price chart with buy/sell markers."""
    signals = results.signals
    trades = results.trades

    fig = go.Figure()

    # Price line
    fig.add_trace(go.Scatter(
        x=signals["date"],
        y=signals["close"],
        mode="lines",
        name="Price",
        line=dict(color=CHART_COLORS["categorical"][0], width=1.5),
    ))

    # Buy markers
    if len(trades) > 0:
        buys = trades[trades["type"] == "BUY"]
        if len(buys) > 0:
            fig.add_trace(go.Scatter(
                x=buys["date"],
                y=buys["price"],
                mode="markers",
                name="BUY",
                marker=dict(
                    symbol="triangle-up",
                    size=12,
                    color="#10b981",
                    line=dict(width=1, color="white"),
                ),
            ))

        # Sell markers
        sells = trades[trades["type"] == "SELL"]
        if len(sells) > 0:
            fig.add_trace(go.Scatter(
                x=sells["date"],
                y=sells["price"],
                mode="markers",
                name="SELL",
                marker=dict(
                    symbol="triangle-down",
                    size=12,
                    color="#ef4444",
                    line=dict(width=1, color="white"),
                ),
            ))

    fig.update_layout(
        title="Price with Buy/Sell Signals",
        yaxis_title="Price ($)",
        template="plotly_white",
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=60, b=40),
    )
    return fig


def _create_equity_chart(results) -> go.Figure:
    """Create equity curve vs buy-and-hold chart."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=results.equity_curve.index,
        y=results.equity_curve.values,
        mode="lines",
        name="Strategy",
        line=dict(color=CHART_COLORS["categorical"][0], width=2),
    ))

    fig.add_trace(go.Scatter(
        x=results.buy_hold_curve.index,
        y=results.buy_hold_curve.values,
        mode="lines",
        name="Buy & Hold",
        line=dict(color=CHART_COLORS["categorical"][3], width=2, dash="dash"),
    ))

    fig.update_layout(
        title="Strategy vs Buy & Hold",
        yaxis_title="Portfolio Value ($)",
        template="plotly_white",
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=60, b=40),
    )
    return fig


def _create_signal_subplot(results) -> go.Figure:
    """Create price chart with signal indicator subplot below."""
    signals = results.signals
    config = results.config

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.6, 0.4],
        subplot_titles=["Price", _indicator_label(config.signal_type)],
    )

    # Top: Price
    fig.add_trace(
        go.Scatter(
            x=signals["date"], y=signals["close"],
            mode="lines", name="Price",
            line=dict(color=CHART_COLORS["categorical"][0], width=1.5),
        ),
        row=1, col=1,
    )

    # Bottom: Indicator
    if config.signal_type == "rsi":
        fig.add_trace(
            go.Scatter(
                x=signals["date"], y=signals["rsi"],
                mode="lines", name="RSI",
                line=dict(color=CHART_COLORS["categorical"][5], width=1.5),
            ),
            row=2, col=1,
        )
        # Threshold lines
        fig.add_hline(
            y=config.rsi_oversold, line_dash="dash", line_color="#10b981",
            annotation_text=f"Oversold ({config.rsi_oversold})",
            row=2, col=1,
        )
        fig.add_hline(
            y=config.rsi_overbought, line_dash="dash", line_color="#ef4444",
            annotation_text=f"Overbought ({config.rsi_overbought})",
            row=2, col=1,
        )
        fig.update_yaxes(range=[0, 100], row=2, col=1)

    elif config.signal_type == "macd":
        fig.add_trace(
            go.Scatter(
                x=signals["date"], y=signals["macd"],
                mode="lines", name="MACD",
                line=dict(color=CHART_COLORS["categorical"][0], width=1.5),
            ),
            row=2, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=signals["date"], y=signals["macd_signal"],
                mode="lines", name="Signal",
                line=dict(color=CHART_COLORS["categorical"][4], width=1.5),
            ),
            row=2, col=1,
        )
        # Histogram
        colors = ["#10b981" if v >= 0 else "#ef4444" for v in signals["macd_histogram"].fillna(0)]
        fig.add_trace(
            go.Bar(
                x=signals["date"], y=signals["macd_histogram"],
                name="Histogram",
                marker_color=colors,
                opacity=0.4,
            ),
            row=2, col=1,
        )

    elif config.signal_type == "bollinger":
        # Show BB bands on the price chart instead
        fig.add_trace(
            go.Scatter(
                x=signals["date"], y=signals["bb_upper"],
                mode="lines", name="Upper Band",
                line=dict(color="#ef4444", width=1, dash="dot"),
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=signals["date"], y=signals["bb_lower"],
                mode="lines", name="Lower Band",
                line=dict(color="#10b981", width=1, dash="dot"),
                fill="tonexty", fillcolor="rgba(99, 102, 241, 0.05)",
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=signals["date"], y=signals["bb_middle"],
                mode="lines", name="Middle Band",
                line=dict(color=CHART_COLORS["categorical"][3], width=1, dash="dash"),
            ),
            row=1, col=1,
        )
        # %B indicator on bottom
        fig.add_trace(
            go.Scatter(
                x=signals["date"], y=signals["bb_pct"],
                mode="lines", name="%B",
                line=dict(color=CHART_COLORS["categorical"][5], width=1.5),
            ),
            row=2, col=1,
        )
        fig.add_hline(y=0, line_dash="dash", line_color="#10b981", row=2, col=1)
        fig.add_hline(y=1, line_dash="dash", line_color="#ef4444", row=2, col=1)

    fig.update_layout(
        template="plotly_white",
        height=550,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=60, b=40),
    )
    return fig


def _indicator_label(signal_type: str) -> str:
    labels = {"rsi": "RSI (14)", "macd": "MACD", "bollinger": "Bollinger %B"}
    return labels.get(signal_type, signal_type.upper())


def _display_optimization_results(opt_results, signal_key: str):
    """Display optimization results with best parameters and ranked table."""
    render_section_header("Optimization Results")

    best_m = opt_results.best_metrics
    best_c = opt_results.best_config
    obj_label = opt_results.objective.replace("_", " ").title()

    st.success(
        f"Best {obj_label}: **{best_m[opt_results.objective]:.4f}** "
        f"({opt_results.total_combinations} combinations tested)"
    )

    # Best parameters
    st.markdown("##### Best Parameters")
    param_cols = st.columns(4)
    if signal_key == "rsi":
        with param_cols[0]:
            render_metric_card("RSI Period", str(best_c.rsi_period))
        with param_cols[1]:
            render_metric_card("Oversold", f"{best_c.rsi_oversold:.0f}")
        with param_cols[2]:
            render_metric_card("Overbought", f"{best_c.rsi_overbought:.0f}")
    elif signal_key == "macd":
        with param_cols[0]:
            render_metric_card("Fast Period", str(best_c.macd_fast))
        with param_cols[1]:
            render_metric_card("Slow Period", str(best_c.macd_slow))
        with param_cols[2]:
            render_metric_card("Signal Period", str(best_c.macd_signal))
    elif signal_key == "bollinger":
        with param_cols[0]:
            render_metric_card("BB Period", str(best_c.bb_period))
        with param_cols[1]:
            render_metric_card("Std Dev", f"{best_c.bb_std:.2f}")

    # Best metrics
    st.markdown("##### Best Performance")
    mcols = st.columns(4)
    with mcols[0]:
        render_metric_card("Return", f"{best_m['total_return']:.1%}")
    with mcols[1]:
        render_metric_card("Sharpe", f"{best_m['sharpe_ratio']:.2f}")
    with mcols[2]:
        render_metric_card("Max DD", f"{best_m['max_drawdown']:.1%}")
    with mcols[3]:
        render_metric_card(
            "Win Rate", f"{best_m['win_rate']:.0%}",
            delta=f"{int(best_m['num_trades'])} trades",
        )

    # All runs table
    if len(opt_results.all_runs) > 0:
        with st.expander(
            f"All Parameter Combinations ({len(opt_results.all_runs)} runs)",
            expanded=False,
        ):
            display_df = opt_results.all_runs.sort_values(
                opt_results.objective, ascending=False,
            ).reset_index(drop=True)
            display_df.index = display_df.index + 1
            display_df.index.name = "Rank"
            fmt_pct = (
                "total_return", "buy_hold_return", "excess_return",
                "max_drawdown", "win_rate",
            )
            fmt_dec = ("sharpe_ratio", "profit_factor")
            for col in display_df.columns:
                if col in fmt_pct:
                    display_df[col] = display_df[col].apply(
                        lambda x: f"{x:.2%}" if pd.notna(x) else "-"
                    )
                elif col in fmt_dec:
                    display_df[col] = display_df[col].apply(
                        lambda x: (
                            f"{x:.3f}" if pd.notna(x) and np.isfinite(x) else "-"
                        )
                    )
            st.dataframe(display_df, use_container_width=True)

    # Apply best button
    if st.button(
        "Apply Best & Run Backtest",
        type="primary",
        use_container_width=True,
        key="trigger_apply_best",
    ):
        pending = {}
        if signal_key == "rsi":
            pending = {
                "rsi_period": int(best_c.rsi_period),
                "rsi_oversold": int(best_c.rsi_oversold),
                "rsi_overbought": int(best_c.rsi_overbought),
            }
        elif signal_key == "macd":
            pending = {
                "macd_fast": int(best_c.macd_fast),
                "macd_slow": int(best_c.macd_slow),
                "macd_signal": int(best_c.macd_signal),
            }
        elif signal_key == "bollinger":
            pending = {
                "bb_period": int(best_c.bb_period),
                "bb_std": float(best_c.bb_std),
            }
        st.session_state["trigger_pending_params"] = pending
        st.session_state["trigger_auto_run"] = True
        st.rerun()


def render_trigger_backtester():
    """Render the Trigger Backtester page."""
    render_page_header("Trigger Backtester", "Backtest buy/sell trigger strategies on individual stocks")

    # --- Controls ---
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 1])

    available_tickers = _get_available_tickers()
    default_ticker = "AMD" if "AMD" in available_tickers else (available_tickers[0] if available_tickers else "")

    with col1:
        ticker = st.text_input(
            "Ticker Symbol",
            value=default_ticker,
            key="trigger_ticker",
            help="Enter a stock ticker (must exist in data/prices.csv)",
        ).upper().strip()

    with col2:
        end_default = datetime.now().date()
        start_default = end_default - timedelta(days=365 * 3)
        start_date = st.date_input("Start Date", value=start_default, key="trigger_start")

    with col3:
        end_date = st.date_input("End Date", value=end_default, key="trigger_end")

    with col4:
        signal_type = st.selectbox(
            "Signal Type",
            options=["RSI", "MACD", "Bollinger Bands"],
            key="trigger_signal_type",
        )

    signal_map = {"RSI": "rsi", "MACD": "macd", "Bollinger Bands": "bollinger"}
    signal_key = signal_map[signal_type]

    # --- Signal Parameters ---
    render_section_header("Signal Parameters")
    pcol1, pcol2, pcol3, pcol4 = st.columns(4)

    # Apply pending optimized parameters (from "Apply Best" button).
    # Must delete widget keys BEFORE slider creation so new defaults take effect.
    _pending = st.session_state.pop("trigger_pending_params", None)
    if _pending:
        for _wk in [
            "trigger_rsi_period", "trigger_rsi_os", "trigger_rsi_ob",
            "trigger_macd_fast", "trigger_macd_slow", "trigger_macd_sig",
            "trigger_bb_period", "trigger_bb_std",
        ]:
            st.session_state.pop(_wk, None)

    def _pd(key, fallback):
        """Get pending param value or fallback default."""
        return _pending.get(key, fallback) if _pending else fallback

    if signal_key == "rsi":
        with pcol1:
            rsi_period = st.slider("RSI Period", 5, 30, _pd("rsi_period", 14), key="trigger_rsi_period")
        with pcol2:
            rsi_oversold = st.slider("Oversold Threshold", 10, 50, _pd("rsi_oversold", 30), key="trigger_rsi_os")
        with pcol3:
            rsi_overbought = st.slider("Overbought Threshold", 50, 90, _pd("rsi_overbought", 70), key="trigger_rsi_ob")
        with pcol4:
            tx_cost = st.number_input("Transaction Cost (%)", 0.0, 2.0, 0.1, step=0.05, key="trigger_txcost")
    elif signal_key == "macd":
        with pcol1:
            macd_fast = st.slider("Fast Period", 5, 20, _pd("macd_fast", 12), key="trigger_macd_fast")
        with pcol2:
            macd_slow = st.slider("Slow Period", 15, 40, _pd("macd_slow", 26), key="trigger_macd_slow")
        with pcol3:
            macd_signal_p = st.slider("Signal Period", 5, 15, _pd("macd_signal", 9), key="trigger_macd_sig")
        with pcol4:
            tx_cost = st.number_input("Transaction Cost (%)", 0.0, 2.0, 0.1, step=0.05, key="trigger_txcost")
    elif signal_key == "bollinger":
        with pcol1:
            bb_period = st.slider("BB Period", 10, 50, _pd("bb_period", 20), key="trigger_bb_period")
        with pcol2:
            bb_std = st.slider("Std Deviation", 1.0, 3.0, _pd("bb_std", 2.0), step=0.25, key="trigger_bb_std")
        with pcol3:
            st.empty()
        with pcol4:
            tx_cost = st.number_input("Transaction Cost (%)", 0.0, 2.0, 0.1, step=0.05, key="trigger_txcost")

    initial_capital = 10000.0

    # --- Data Source ---
    dcol1, dcol2, dcol3 = st.columns([2, 2, 2])
    with dcol1:
        live_mode = st.checkbox(
            "Live Data (yfinance)",
            value=False,
            key="trigger_live_mode",
            help="Fetch real-time price data from yfinance instead of local CSV",
        )
    with dcol2:
        if live_mode:
            auto_refresh = st.checkbox(
                "Auto-refresh",
                value=False,
                key="trigger_auto_refresh",
            )
        else:
            auto_refresh = False
    with dcol3:
        if live_mode and auto_refresh:
            refresh_map = {
                "1 min": 60,
                "5 min (recommended)": 300,
                "15 min": 900,
                "30 min": 1800,
                "1 hour": 3600,
            }
            refresh_label = st.selectbox(
                "Refresh Interval",
                options=list(refresh_map.keys()),
                index=1,
                key="trigger_refresh_label",
            )
            refresh_seconds = refresh_map[refresh_label]
        else:
            refresh_seconds = 300

    # --- Action Buttons ---
    bcol1, bcol2, bcol3 = st.columns([2, 2, 2])
    with bcol1:
        run_clicked = st.button(
            "Run Backtest", type="primary",
            use_container_width=True, key="trigger_run",
        )
    with bcol2:
        optimize_clicked = st.button(
            "Optimize Parameters",
            use_container_width=True, key="trigger_optimize",
        )
    with bcol3:
        objective_map = {
            "Sharpe Ratio": "sharpe_ratio",
            "Total Return": "total_return",
            "Profit Factor": "profit_factor",
            "Win Rate": "win_rate",
        }
        objective_label = st.selectbox(
            "Optimize For",
            options=list(objective_map.keys()),
            key="trigger_objective",
        )

    # Auto-run after applying best parameters or in live auto-refresh mode
    if st.session_state.get("trigger_auto_run"):
        run_clicked = True
        st.session_state["trigger_auto_run"] = False
    if live_mode and auto_refresh:
        run_clicked = True

    st.markdown("---")

    if not run_clicked and not optimize_clicked:
        if "trigger_opt_results" in st.session_state:
            _display_optimization_results(
                st.session_state["trigger_opt_results"], signal_key,
            )
        else:
            st.info(
                f"Configure parameters above and click **Run Backtest** to test "
                f"{signal_type} signals on **{ticker}**, or **Optimize Parameters** "
                f"to find the best parameter combination."
            )
        return

    # --- Load Data (shared by both flows) ---
    if not ticker:
        st.error("Please enter a ticker symbol.")
        return

    if live_mode:
        with st.spinner(f"Fetching live data for {ticker} from yfinance..."):
            price_df = _fetch_yfinance_data(
                ticker,
                str(start_date),
                str(end_date + timedelta(days=1)),
            )
        if len(price_df) == 0:
            st.error(
                f"Could not fetch data for **{ticker}** from yfinance. "
                f"Check the ticker symbol."
            )
            return
        st.caption(
            f"Live data: {len(price_df)} days from yfinance | "
            f"Last fetched: {datetime.now().strftime('%H:%M:%S')}"
        )
    else:
        price_df = _load_price_data_for_ticker(ticker)
        if len(price_df) == 0:
            st.error(
                f"No price data found for **{ticker}**. "
                f"Make sure it exists in `data/prices.csv`. "
                f"Available tickers: {', '.join(available_tickers[:20])}..."
            )
            return

    # Filter by date range
    price_df = price_df[
        (price_df["date"] >= pd.Timestamp(start_date))
        & (price_df["date"] <= pd.Timestamp(end_date))
    ].reset_index(drop=True)

    if len(price_df) < 50:
        st.warning(
            f"Only {len(price_df)} data points for {ticker} in the selected "
            f"date range. Need at least 50 for reliable signals."
        )
        if len(price_df) == 0:
            return

    # --- Optimization Flow ---
    if optimize_clicked:
        objective_key = objective_map[objective_label]
        progress_bar = st.progress(0, text="Optimizing parameters...")

        def _update_progress(current, total):
            progress_bar.progress(
                current / total,
                text=f"Testing combination {current}/{total}...",
            )

        try:
            opt_results = optimize_parameters(
                price_df,
                signal_type=signal_key,
                objective=objective_key,
                transaction_cost=tx_cost / 100.0,
                initial_capital=initial_capital,
                min_trades=3,
                progress_callback=_update_progress,
            )
        except Exception as e:
            st.error(f"Optimization failed: {e}")
            return
        finally:
            progress_bar.empty()

        st.session_state["trigger_opt_results"] = opt_results
        _display_optimization_results(opt_results, signal_key)
        return

    # --- Build Config ---
    config = TriggerConfig(
        signal_type=signal_key,
        initial_capital=initial_capital,
        transaction_cost=tx_cost / 100.0,
    )
    if signal_key == "rsi":
        config.rsi_period = rsi_period
        config.rsi_oversold = rsi_oversold
        config.rsi_overbought = rsi_overbought
    elif signal_key == "macd":
        config.macd_fast = macd_fast
        config.macd_slow = macd_slow
        config.macd_signal = macd_signal_p
    elif signal_key == "bollinger":
        config.bb_period = bb_period
        config.bb_std = bb_std

    # --- Run Backtest ---
    with st.spinner(f"Running {signal_type} backtest on {ticker}..."):
        try:
            results = run_trigger_backtest(price_df, config)
        except Exception as e:
            st.error(f"Backtest failed: {e}")
            return

    # --- Metrics ---
    m = results.metrics
    render_section_header("Performance Summary")

    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    with mcol1:
        render_metric_card(
            "Strategy Return",
            f"{m['total_return']:.1%}",
            delta=f"vs B&H: {m['excess_return']:+.1%}",
        )
    with mcol2:
        render_metric_card("Sharpe Ratio", f"{m['sharpe_ratio']:.2f}")
    with mcol3:
        render_metric_card("Max Drawdown", f"{m['max_drawdown']:.1%}")
    with mcol4:
        render_metric_card("Win Rate", f"{m['win_rate']:.0%}", delta=f"{int(m['num_trades'])} trades")

    mcol5, mcol6, mcol7, mcol8 = st.columns(4)
    with mcol5:
        render_metric_card("Buy & Hold Return", f"{m['buy_hold_return']:.1%}")
    with mcol6:
        render_metric_card(
            "Profit Factor",
            f"{m['profit_factor']:.2f}" if m['profit_factor'] != float('inf') else "N/A",
        )
    with mcol7:
        render_metric_card("Avg Hold (days)", f"{m['avg_hold_days']:.0f}")
    with mcol8:
        render_metric_card("Data Points", f"{len(results.signals):,}")

    st.markdown("---")

    # --- Charts ---
    tabs = st.tabs(["Price + Signals", "Equity Curve", "Signal Indicator", "Trade Log"])

    with tabs[0]:
        fig = _create_price_chart_with_signals(results)
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        fig = _create_equity_chart(results)
        st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        fig = _create_signal_subplot(results)
        st.plotly_chart(fig, use_container_width=True)

    with tabs[3]:
        if len(results.trades) > 0:
            display_df = results.trades.copy()
            display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%Y-%m-%d")
            display_df["price"] = display_df["price"].map("${:,.2f}".format)
            display_df["shares"] = display_df["shares"].map("{:,.2f}".format)
            display_df["value"] = display_df["value"].map("${:,.2f}".format)
            display_df["pnl"] = display_df["pnl"].apply(
                lambda x: f"${x:+,.2f}" if pd.notna(x) else "-"
            )
            display_df["hold_days"] = display_df["hold_days"].apply(
                lambda x: f"{int(x)}" if pd.notna(x) else "-"
            )
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No trades were generated. Try adjusting the signal parameters or date range.")

    # --- Auto-refresh ---
    if live_mode and auto_refresh:
        import streamlit.components.v1 as components
        components.html(
            f"""<script>
            setTimeout(function() {{
                window.parent.location.reload();
            }}, {refresh_seconds * 1000});
            </script>""",
            height=0,
        )
