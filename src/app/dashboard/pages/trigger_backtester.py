"""Trigger Backtester Page.

Interactive backtesting interface for buy/sell trigger strategies on individual stocks.
Supports RSI, MACD, and Bollinger Band signals with configurable parameters.
Real-time monitoring with live indicators and buy/sell signal notifications.
"""

import json
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..components.sidebar import render_page_header, render_section_header
from ..components.metrics import render_metric_card
from ..components.notifications import NotificationManager
from ..config import COLORS, CHART_COLORS
from ..data import load_app_settings, save_app_settings

from src.backtest.trigger_backtest import (
    TriggerConfig,
    run_trigger_backtest,
    optimize_parameters,
    PARAM_GRIDS,
)


def _run_trigger_backtest_safe(price_df, config, **kwargs):
    """Call run_trigger_backtest; fall back to fewer kwargs if module is cached/old."""
    try:
        return run_trigger_backtest(price_df, config, **kwargs)
    except TypeError as e:
        if "unexpected keyword argument" not in str(e):
            raise
        # Retry with all macro params (preserve DXY/VIX so filters actually apply)
        macro_keys = ("macro_price_df", "macro_dxy_df", "macro_vix_df", "vix_df_for_regime")
        safe = {k: v for k, v in kwargs.items() if k in macro_keys and v is not None}
        try:
            return run_trigger_backtest(price_df, config, **safe) if safe else run_trigger_backtest(price_df, config)
        except TypeError:
            return run_trigger_backtest(price_df, config)


def _log_trigger(level: str, message: str) -> None:
    """Append a notification, warning, or error to the trigger log."""
    st.session_state.setdefault("trigger_log", [])
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state["trigger_log"].append(f"[{ts}] {level.upper()}: {message}")


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


def _fetch_macro_price_df(
    gold_ticker: str, start: str, end: str, from_csv: bool = False
) -> pd.DataFrame:
    """Fetch gold (or other macro) price data for GSR. Returns [date, close]."""
    if from_csv:
        df = _load_price_data_for_ticker(gold_ticker)
        if df.empty:
            return pd.DataFrame()
        df = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]
    else:
        df = _fetch_yfinance_data(gold_ticker, start, end)
    if df.empty or "close" not in df.columns:
        return pd.DataFrame()
    return df[["date", "close"]].copy()


def _fetch_macro_series(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Fetch macro index (DXY, VIX, etc.) from yfinance. Returns [date, close]."""
    df = _fetch_yfinance_data(ticker, start, end)
    if df.empty or "close" not in df.columns:
        return pd.DataFrame()
    return df[["date", "close"]].copy()


def _parse_tickers(ticker_str: str, max_tickers: int = 5) -> list[str]:
    """Parse ticker input: 'AMD SLV' or 'AMD, SLV' -> ['AMD', 'SLV']."""
    if not ticker_str or not ticker_str.strip():
        return []
    parts = [p.strip().upper() for p in ticker_str.replace(",", " ").split() if p.strip()]
    seen = set()
    out = []
    for p in parts:
        if p not in seen and len(out) < max_tickers:
            seen.add(p)
            out.append(p)
    return out


def _build_trigger_config_from_yaml(
    ticker: str,
    signal_key: str,
    load_ticker_config_fn,
    fallback_params: dict | None,
    initial_capital: float = 10000.0,
    transaction_cost: float = 0.001,
) -> TriggerConfig:
    """Build TriggerConfig from per-ticker YAML; fallback to best_params or defaults."""
    cfg = TriggerConfig(
        signal_type=signal_key,
        initial_capital=initial_capital,
        transaction_cost=transaction_cost,
    )
    if signal_key == "combined":
        cfg.combined_use_rsi = True
        cfg.combined_use_macd = True
        cfg.combined_use_bollinger = False

    ticker_cfg = load_ticker_config_fn(ticker) if load_ticker_config_fn else None
    if ticker_cfg and "trigger" in ticker_cfg:
        t = ticker_cfg["trigger"]
        for key in ("rsi_period", "rsi_oversold", "rsi_overbought", "macd_fast", "macd_slow", "macd_signal", "bb_period", "bb_std"):
            if key in t:
                setattr(cfg, key, t[key])
        # Volume trigger (CMF)
        if "volume_trigger" in t:
            vt = t["volume_trigger"]
            for k in ("cmf_window", "cmf_buy_threshold", "cmf_sell_threshold"):
                if k in vt:
                    setattr(cfg, k, vt[k])
        if "combined_use_cmf" in t:
            cfg.combined_use_cmf = bool(t["combined_use_cmf"])
        # Macro factors (GSR)
        if "macro_factors" in t:
            mf = t["macro_factors"]
            if mf.get("gsr_enabled"):
                cfg.macro_gsr_enabled = True
                cfg.macro_gsr_gold_ticker = str(mf.get("gold_ticker", cfg.macro_gsr_gold_ticker))
                cfg.macro_gsr_buy_threshold = float(mf.get("gsr_buy_threshold", cfg.macro_gsr_buy_threshold))
                cfg.macro_gsr_sell_threshold = float(mf.get("gsr_sell_threshold", cfg.macro_gsr_sell_threshold))
            if mf.get("dxy_enabled"):
                cfg.macro_dxy_enabled = True
                cfg.macro_dxy_buy_max = float(mf.get("dxy_buy_max", cfg.macro_dxy_buy_max))
                cfg.macro_dxy_sell_min = float(mf.get("dxy_sell_min", cfg.macro_dxy_sell_min))
            if mf.get("vix_enabled"):
                cfg.macro_vix_enabled = True
                cfg.macro_vix_buy_max = float(mf.get("vix_buy_max", cfg.macro_vix_buy_max))
                cfg.macro_vix_sell_min = float(mf.get("vix_sell_min", cfg.macro_vix_sell_min))
            if mf.get("volume_surge_min") is not None:
                cfg.volume_surge_min = float(mf["volume_surge_min"])
            if mf.get("obv_slope_positive"):
                cfg.obv_slope_positive = True
        return cfg

    if fallback_params:
        cfg.macd_fast = int(fallback_params.get("macd_fast", cfg.macd_fast))
        cfg.macd_slow = int(fallback_params.get("macd_slow", cfg.macd_slow))
        cfg.macd_signal = int(fallback_params.get("macd_signal", cfg.macd_signal))
        cfg.rsi_period = int(fallback_params.get("rsi_period", fallback_params.get("rsi_len", cfg.rsi_period)))
        cfg.rsi_overbought = float(fallback_params.get("rsi_overbought", fallback_params.get("rsi_hi", cfg.rsi_overbought)))
        cfg.rsi_oversold = float(fallback_params.get("rsi_oversold", fallback_params.get("rsi_lo", cfg.rsi_oversold)))
        if "bb_period" in fallback_params:
            cfg.bb_period = int(fallback_params["bb_period"])
        if "bb_std" in fallback_params:
            cfg.bb_std = float(fallback_params["bb_std"])
    return cfg


def _load_fallback_params() -> dict | None:
    """Load best_params from output/best_params.json if exists."""
    try:
        root = Path(__file__).resolve().parents[4]
        p = root / "output" / "best_params.json"
        if not p.exists():
            return None
        with open(p) as f:
            data = json.load(f)
        return data.get("best_params", {})
    except Exception:
        return None


def _format_params_readonly(ticker_cfg: dict | None, fallback: dict | None, ticker: str) -> str:
    """Format params for read-only display. Edit in config/tickers/{TICKER}.yaml."""
    if ticker_cfg and "trigger" in ticker_cfg:
        t = ticker_cfg["trigger"]
        lines = [f"{k}: {v}" for k, v in sorted(t.items())]
        if "horizon_days" in ticker_cfg:
            lines.append(f"horizon_days: {ticker_cfg['horizon_days']}")
        if "return_periods" in ticker_cfg:
            lines.append(f"return_periods: {ticker_cfg['return_periods']}")
        if "backtest" in ticker_cfg:
            b = ticker_cfg["backtest"]
            lines.append("--- backtest ---")
            for k in ("train_years", "test_years", "step_value", "step_unit", "rebalance_freq"):
                if k in b:
                    lines.append(f"  {k}: {b[k]}")
        return "\n".join(lines) + f"\n\nEdit: config/tickers/{ticker}.yaml"
    if fallback:
        lines = [f"{k}: {v}" for k, v in sorted(fallback.items())]
        return "\n".join(lines) + "\n\n(Fallback from best_params.json)"
    return f"Using defaults.\nAdd config/tickers/{ticker}.yaml for custom params."


def _create_price_chart_with_signals(
    results, height: int = 450, show_blocked: bool = True
) -> go.Figure:
    """Create price chart with buy/sell markers and optionally blocked-by-macro signals."""
    signals = results.signals
    trades = results.trades
    config = results.config

    fig = go.Figure()

    # Price line
    fig.add_trace(go.Scatter(
        x=signals["date"],
        y=signals["close"],
        mode="lines",
        name="Price",
        line=dict(color=CHART_COLORS["categorical"][0], width=1.5),
    ))

    # Blocked-by-macro signals (same colors as BUY/SELL, hollow markers)
    has_macro = (
        getattr(config, "macro_gsr_enabled", False)
        or getattr(config, "macro_dxy_enabled", False)
        or getattr(config, "macro_vix_enabled", False)
    )
    if (
        show_blocked
        and has_macro
        and "signal_raw" in signals.columns
    ):
        blocked_buy = (signals["signal_raw"] == 1) & (signals["signal"] == 0)
        blocked_sell = (signals["signal_raw"] == -1) & (signals["signal"] == 0)
        if blocked_buy.any():
            bb = signals.loc[blocked_buy]
            fig.add_trace(go.Scatter(
                x=bb["date"],
                y=bb["close"],
                mode="markers",
                name="BUY (blocked)",
                marker=dict(
                    symbol="triangle-up-open",
                    size=10,
                    color="#10b981",
                    line=dict(width=1.5, color="#10b981"),
                ),
            ))
        if blocked_sell.any():
            bs = signals.loc[blocked_sell]
            fig.add_trace(go.Scatter(
                x=bs["date"],
                y=bs["close"],
                mode="markers",
                name="SELL (blocked)",
                marker=dict(
                    symbol="triangle-down-open",
                    size=10,
                    color="#ef4444",
                    line=dict(width=1.5, color="#ef4444"),
                ),
            ))

    # Executed buy/sell markers
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
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=60, b=40),
    )
    return fig


def _create_macro_chart(
    df: pd.DataFrame,
    title: str,
    ylabel: str,
    color: str,
    height: int = 280,
    buy_max: float | None = None,
    sell_min: float | None = None,
) -> go.Figure:
    """Create a line chart for a macro series (DXY, VIX) with optional BUY/SELL bands."""
    if df.empty or "close" not in df.columns:
        return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["close"],
        mode="lines",
        name=title,
        line=dict(color=color, width=1.5),
    ))
    if buy_max is not None:
        fig.add_hline(
            y=buy_max,
            line_dash="dash",
            line_color="#10b981",
            annotation_text=f"BUY zone (≤{buy_max:.0f})",
            annotation_position="right",
        )
    if sell_min is not None:
        fig.add_hline(
            y=sell_min,
            line_dash="dash",
            line_color="#ef4444",
            annotation_text=f"SELL zone (≥{sell_min:.0f})",
            annotation_position="right",
        )
    fig.update_layout(
        title=title,
        yaxis_title=ylabel,
        template="plotly_white",
        height=height,
        margin=dict(l=60, r=20, t=50, b=40),
        showlegend=False,
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

    elif config.signal_type == "combined":
        # Show first available indicator subplot (priority: RSI > MACD > BB)
        if config.combined_use_rsi and "rsi" in signals.columns:
            fig.add_trace(
                go.Scatter(
                    x=signals["date"], y=signals["rsi"],
                    mode="lines", name="RSI",
                    line=dict(color=CHART_COLORS["categorical"][5], width=1.5),
                ),
                row=2, col=1,
            )
            fig.add_hline(
                y=config.rsi_oversold, line_dash="dash", line_color="#10b981",
                row=2, col=1,
            )
            fig.add_hline(
                y=config.rsi_overbought, line_dash="dash", line_color="#ef4444",
                row=2, col=1,
            )
            fig.update_yaxes(range=[0, 100], row=2, col=1)
        elif config.combined_use_macd and "macd" in signals.columns:
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
            colors = ["#10b981" if v >= 0 else "#ef4444" for v in signals["macd_histogram"].fillna(0)]
            fig.add_trace(
                go.Bar(
                    x=signals["date"], y=signals["macd_histogram"],
                    name="Histogram", marker_color=colors, opacity=0.4,
                ),
                row=2, col=1,
            )
        elif config.combined_use_bollinger and "bb_pct" in signals.columns:
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
        else:
            fig.add_trace(
                go.Scatter(
                    x=signals["date"], y=signals["signal"],
                    mode="lines", name="Signal",
                    line=dict(color=CHART_COLORS["categorical"][5], width=1.5),
                ),
                row=2, col=1,
            )
            fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)

    fig.update_layout(
        template="plotly_white",
        height=550,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=60, b=40),
    )
    return fig


def _indicator_label(signal_type: str) -> str:
    labels = {
        "rsi": "RSI (14)",
        "macd": "MACD",
        "bollinger": "Bollinger %B",
        "combined": "Combined",
    }
    return labels.get(signal_type, signal_type.upper())


def _render_realtime_indicator(ticker: str, refresh_seconds: int, refresh_label: str):
    """Render a prominent real-time monitoring status indicator."""
    st.markdown(
        """
        <style>
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        .realtime-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
            color: white;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 12px;
        }
        .realtime-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: white;
            animation: pulse-dot 1.5s ease-in-out infinite;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container():
        st.markdown(
            f'<div class="realtime-badge">'
            f'<span class="realtime-dot"></span>'
            f'LIVE – Monitoring <strong>{ticker}</strong> • Refreshing every {refresh_label}'
            f'</div>',
            unsafe_allow_html=True,
        )


def _check_and_notify_signals(
    results,
    ticker: str,
    signal_type: str,
    is_realtime: bool,
) -> None:
    """Check for new BUY/SELL signals and show notifications (toast + notification center)."""
    if not is_realtime or results is None or len(results.signals) == 0:
        return

    signals = results.signals
    last_row = signals.iloc[-1]
    new_signal = int(last_row.get("signal", 0))
    last_date_val = last_row.get("date", "")
    if last_date_val is not None and hasattr(last_date_val, "strftime"):
        last_date = last_date_val.strftime("%Y-%m-%d %H:%M")
    else:
        last_date = str(last_date_val) if last_date_val else ""

    # Session state key for tracking last signal per ticker
    key = f"trigger_last_signal_{ticker}_{signal_type}"
    prev_signal = st.session_state.get(key, None)

    if new_signal == 1:  # BUY
        if prev_signal != 1:
            msg = f"🟢 BUY signal for {ticker} | {signal_type} | {last_date}"
            _log_trigger("notification", msg)
            try:
                st.toast(msg, icon="🟢")
            except Exception:
                pass
            NotificationManager().add_notification(
                message=msg,
                type="success",
                category="trigger_signals",
                action="trigger_backtester",
                action_label="View",
            )
    elif new_signal == -1:  # SELL
        if prev_signal != -1:
            msg = f"🔴 SELL signal for {ticker} | {signal_type} | {last_date}"
            _log_trigger("notification", msg)
            try:
                st.toast(msg, icon="🔴")
            except Exception:
                pass
            NotificationManager().add_notification(
                message=msg,
                type="warning",
                category="trigger_signals",
                action="trigger_backtester",
                action_label="View",
            )

    st.session_state[key] = new_signal


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
    elif signal_key == "combined":
        st.caption("Optimization not available for Combined.")

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


def _render_trigger_log():
    """Render the trigger notification/error/warning log textbox."""
    st.session_state.setdefault("trigger_log", [])
    log_lines = st.session_state["trigger_log"]
    log_text = "\n".join(log_lines) if log_lines else "(No notifications yet)"
    with st.expander("📋 Trigger Log (notifications, warnings, errors)", expanded=bool(log_lines)):
        st.text_area(
            "Log",
            value=log_text,
            height=120,
            disabled=True,
            key="trigger_log_display",
            label_visibility="collapsed",
        )
        if st.button("Clear log", key="trigger_log_clear"):
            st.session_state["trigger_log"] = []
            st.rerun()


def render_trigger_backtester():
    """Render the Trigger Backtester page."""
    render_page_header("Trigger Backtester", "Backtest buy/sell trigger strategies on individual stocks")
    _render_trigger_log()

    # Load config (includes Bayesian-optimized params from output/best_params.json when set)
    try:
        from pathlib import Path
        from src.config.config import load_config, load_ticker_config
        _cfg_path = Path(__file__).resolve().parents[4] / "config" / "config.yaml"
        _config = load_config(_cfg_path if _cfg_path.exists() else None)
        _trigger = _config.trigger
        _defaults = {
            "rsi_period": _trigger.rsi_period,
            "rsi_oversold": _trigger.rsi_oversold,
            "rsi_overbought": _trigger.rsi_overbought,
            "macd_fast": _trigger.macd_fast,
            "macd_slow": _trigger.macd_slow,
            "macd_signal": _trigger.macd_signal,
            "bb_period": 20,
            "bb_std": 2.0,
        }
    except Exception:
        _defaults = {"rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70, "macd_fast": 12, "macd_slow": 26, "macd_signal": 9, "bb_period": 20, "bb_std": 2.0}

    # Load persisted params (recalled on start/refresh)
    saved = load_app_settings("trigger_backtester", default={})
    for k, v in saved.items():
        if k not in ("ticker", "start_date", "end_date", "signal_type"):
            st.session_state.setdefault(f"trigger_last_{k}", v)

    # --- Controls ---
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 1])

    available_tickers = _get_available_tickers()
    default_ticker = saved.get("ticker") or ("AMD" if "AMD" in available_tickers else (available_tickers[0] if available_tickers else ""))
    if default_ticker not in (t.upper() for t in available_tickers):
        default_ticker = "AMD" if "AMD" in available_tickers else (available_tickers[0] if available_tickers else "")

    with col1:
        ticker_input = st.text_input(
            "Tickers",
            value=default_ticker,
            key="trigger_ticker",
            help="One or more tickers, space or comma separated (e.g. AMD SLV). Max 5.",
        ).strip()
    tickers = _parse_tickers(ticker_input)
    multi_ticker = len(tickers) > 1
    ticker = tickers[0] if tickers else ""

    # Override defaults with per-ticker YAML (config/tickers/{TICKER}.yaml) if present
    if ticker:
        try:
            _ticker_cfg = load_ticker_config(ticker)
            if _ticker_cfg and "trigger" in _ticker_cfg:
                for k, v in _ticker_cfg["trigger"].items():
                    if k in _defaults:
                        _defaults[k] = v
        except Exception:
            pass

    with col2:
        end_default = datetime.now().date()
        start_default = end_default - timedelta(days=365 * 3)
        if saved.get("start_date"):
            try:
                start_default = datetime.strptime(saved["start_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass
        if saved.get("end_date"):
            try:
                end_default = datetime.strptime(saved["end_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass
        start_date = st.date_input("Start Date", value=start_default, key="trigger_start")

    with col3:
        end_date = st.date_input("End Date", value=end_default, key="trigger_end")

    with col4:
        signal_options = ["RSI", "MACD", "Bollinger Bands", "Combined"]
        default_signal = saved.get("signal_type", "RSI")
        default_signal_idx = signal_options.index(default_signal) if default_signal in signal_options else 0
        signal_type = st.selectbox(
            "Signal Type",
            options=signal_options,
            index=default_signal_idx,
            key="trigger_signal_type",
        )

    signal_map = {
        "RSI": "rsi",
        "MACD": "macd",
        "Bollinger Bands": "bollinger",
        "Combined": "combined",
    }
    signal_key = signal_map[signal_type]

    # --- Signal Parameters (single-ticker only; multi-ticker uses YAML per ticker) ---
    if not multi_ticker:
        render_section_header("Signal Parameters")
        pcol1, pcol2, pcol3, pcol4 = st.columns(4)
    else:
        st.caption("Multi-ticker mode: params from config/tickers/{TICKER}.yaml per stock. Edit YAML files to change.")
        # Placeholders for variables used in config build (single-ticker path)
        rsi_period = _defaults.get("rsi_period", 14)
        rsi_oversold = _defaults.get("rsi_oversold", 30)
        rsi_overbought = _defaults.get("rsi_overbought", 70)
        macd_fast = _defaults.get("macd_fast", 12)
        macd_slow = _defaults.get("macd_slow", 26)
        macd_signal_p = _defaults.get("macd_signal", 9)
        bb_period = _defaults.get("bb_period", 20)
        bb_std = _defaults.get("bb_std", 2.0)
        tx_cost = 0.1
        use_rsi = True
        use_macd = True
        use_bollinger = False
        agreement_mode = "majority"

    if not multi_ticker:
        # Apply pending optimized parameters (from "Apply Best" button).
        _pending = st.session_state.pop("trigger_pending_params", None)
        if _pending:
            for _wk in [
                "trigger_rsi_period", "trigger_rsi_os", "trigger_rsi_ob",
                "trigger_macd_fast", "trigger_macd_slow", "trigger_macd_sig",
                "trigger_bb_period", "trigger_bb_std",
            ]:
                st.session_state.pop(_wk, None)

        def _default(key: str, static_default):
            if _pending and key in _pending:
                return _pending[key]
            ss_key = f"trigger_last_{key}"
            if ss_key in st.session_state:
                return st.session_state[ss_key]
            return _defaults.get(key, static_default)

        def _int_default(key: str, static: int):
            v = _default(key, static)
            if v is None:
                return static
            try:
                return int(float(v))
            except (ValueError, TypeError):
                return static

        def _float_default(key: str, static: float):
            v = _default(key, static)
            if v is None:
                return static
            try:
                return float(v)
            except (ValueError, TypeError):
                return static

        if signal_key == "rsi":
            with pcol1:
                rsi_period = st.slider("RSI Period", 5, 30, _int_default("rsi_period", 14), step=1, key="trigger_rsi_period")
            with pcol2:
                rsi_oversold = st.slider("Oversold Threshold", 10, 50, _int_default("rsi_oversold", 30), step=1, key="trigger_rsi_os")
            with pcol3:
                rsi_overbought = st.slider("Overbought Threshold", 50, 90, _int_default("rsi_overbought", 70), step=1, key="trigger_rsi_ob")
            with pcol4:
                tx_cost = st.number_input("Transaction Cost (%)", 0.0, 2.0, _float_default("tx_cost", 0.1), step=0.05, key="trigger_txcost")
        elif signal_key == "macd":
            with pcol1:
                macd_fast = st.slider("Fast Period", 5, 20, _int_default("macd_fast", 12), step=1, key="trigger_macd_fast")
            with pcol2:
                macd_slow = st.slider("Slow Period", 15, 60, _int_default("macd_slow", 26), step=1, key="trigger_macd_slow")
            with pcol3:
                macd_signal_p = st.slider("Signal Period", 5, 20, _int_default("macd_signal", 9), step=1, key="trigger_macd_sig")
            with pcol4:
                tx_cost = st.number_input("Transaction Cost (%)", 0.0, 2.0, _float_default("tx_cost", 0.1), step=0.05, key="trigger_txcost")
        elif signal_key == "bollinger":
            with pcol1:
                bb_period = st.slider("BB Period", 10, 50, _int_default("bb_period", 20), step=1, key="trigger_bb_period")
            with pcol2:
                bb_std = st.slider("Std Deviation", 1.0, 3.0, _float_default("bb_std", 2.0), step=0.25, key="trigger_bb_std")
            with pcol3:
                st.empty()
            with pcol4:
                tx_cost = st.number_input("Transaction Cost (%)", 0.0, 2.0, _float_default("tx_cost", 0.1), step=0.05, key="trigger_txcost")
        elif signal_key == "combined":
            st.caption(
                "Combined uses voting: BUY when enough indicators agree, SELL when enough agree. "
                "**All** = strict (all must agree). **Majority** = 2 of 3 (default). **Any** = 1 agrees."
            )
            agreement_mode = st.radio(
                "Agreement",
                options=["majority", "all", "any"],
                index=0,
                format_func=lambda x: {"majority": "Majority (2 of 3)", "all": "All must agree", "any": "Any (1 agrees)"}[x],
                key="trigger_comb_agreement",
                horizontal=True,
            )
            comb_col1, comb_col2, comb_col3, comb_col4 = st.columns(4)
            with comb_col1:
                use_rsi = st.checkbox("Use RSI", value=True, key="trigger_comb_rsi")
            with comb_col2:
                use_macd = st.checkbox("Use MACD", value=True, key="trigger_comb_macd")
            with comb_col3:
                use_bollinger = st.checkbox("Use Bollinger", value=True, key="trigger_comb_bb")
            with comb_col4:
                tx_cost = st.number_input("Transaction Cost (%)", 0.0, 2.0, _float_default("tx_cost", 0.1), step=0.05, key="trigger_txcost")
            if not (use_rsi or use_macd or use_bollinger):
                _log_trigger("warning", "Select at least one indicator for combined signals.")
            st.warning("Select at least one indicator for combined signals.")
            st.markdown("**Indicator parameters** (used for selected indicators)")
            p2col1, p2col2, p2col3, p2col4 = st.columns(4)
            with p2col1:
                rsi_period = st.slider("RSI Period", 5, 30, _int_default("rsi_period", 14), step=1, key="trigger_rsi_period", disabled=not use_rsi)
                rsi_oversold = st.slider("RSI Oversold", 10, 50, _int_default("rsi_oversold", 30), step=1, key="trigger_rsi_os", disabled=not use_rsi)
                rsi_overbought = st.slider("RSI Overbought", 50, 90, _int_default("rsi_overbought", 70), step=1, key="trigger_rsi_ob", disabled=not use_rsi)
            with p2col2:
                macd_fast = st.slider("MACD Fast", 5, 20, _int_default("macd_fast", 12), step=1, key="trigger_macd_fast", disabled=not use_macd)
                macd_slow = st.slider("MACD Slow", 15, 60, _int_default("macd_slow", 26), step=1, key="trigger_macd_slow", disabled=not use_macd)
                macd_signal_p = st.slider("MACD Signal", 5, 20, _int_default("macd_signal", 9), step=1, key="trigger_macd_sig", disabled=not use_macd)
            with p2col3:
                bb_period = st.slider("BB Period", 10, 50, _int_default("bb_period", 20), step=1, key="trigger_bb_period", disabled=not use_bollinger)
                bb_std = st.slider("BB Std Dev", 1.0, 3.0, _float_default("bb_std", 2.0), step=0.25, key="trigger_bb_std", disabled=not use_bollinger)

        # Macro filters (DXY, VIX) - single-ticker only; defaults from per-ticker YAML
        _mf = {}
        if ticker:
            try:
                from src.config.config import load_ticker_config
                _tc = load_ticker_config(ticker)
                _mf = (_tc.get("trigger") or {}).get("macro_factors") or {}
            except Exception:
                pass
        with st.expander("Macro Filters (DXY, VIX)", expanded=bool(_mf.get("dxy_enabled") or _mf.get("vix_enabled"))):
            use_macro_filters = st.checkbox(
                "Use macro filters",
                value=True,
                key="trigger_use_macro",
                help="When unchecked, all macro filters (GSR, DXY, VIX) are disabled and signals are not filtered.",
            )
            st.caption("Filter signals by Dollar Index and VIX. DXY: BUY when weak (≤max), SELL when strong (≥min). VIX: BUY when low (≤max), SELL when high (≥min).")
            mf1, mf2 = st.columns(2)
            with mf1:
                use_dxy = st.checkbox("Use DXY filter", value=bool(_mf.get("dxy_enabled")), key="trigger_macro_dxy", disabled=not use_macro_filters)
                dxy_buy_max = st.number_input("DXY BUY max (weak $)", 95.0, 110.0, float(_mf.get("dxy_buy_max", 102)), 0.5, key="trigger_dxy_buy_max", disabled=not (use_macro_filters and use_dxy))
                dxy_sell_min = st.number_input("DXY SELL min (strong $)", 95.0, 115.0, float(_mf.get("dxy_sell_min", 106)), 0.5, key="trigger_dxy_sell_min", disabled=not (use_macro_filters and use_dxy))
            with mf2:
                use_vix = st.checkbox("Use VIX filter", value=bool(_mf.get("vix_enabled")), key="trigger_macro_vix", disabled=not use_macro_filters)
                vix_buy_max = st.number_input("VIX BUY max (low fear)", 10.0, 40.0, float(_mf.get("vix_buy_max", 25)), 1.0, key="trigger_vix_buy_max", disabled=not (use_macro_filters and use_vix))
                vix_sell_min = st.number_input("VIX SELL min (high fear)", 15.0, 50.0, float(_mf.get("vix_sell_min", 30)), 1.0, key="trigger_vix_sell_min", disabled=not (use_macro_filters and use_vix))

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
                "Real-time monitoring",
                value=False,
                key="trigger_auto_refresh",
                help="Continuously monitor and refresh data; shows live indicator and buy/sell notifications",
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
            ticker_label = ", ".join(tickers) if tickers else "ticker"
            st.info(
                f"Configure parameters above and click **Run Backtest** to test "
                f"{signal_type} signals on **{ticker_label}**, or **Optimize Parameters** "
                f"(single-ticker only) to find the best parameter combination."
            )
        return

    if not tickers:
        _log_trigger("error", "Please enter at least one ticker symbol.")
        st.error("Please enter at least one ticker symbol.")
        return

    if multi_ticker and optimize_clicked:
        _log_trigger("info", "Parameter optimization is single-ticker only. Enter one ticker to optimize.")
        st.info("Parameter optimization is single-ticker only. Enter one ticker to optimize.")
        return

    # --- Multi-ticker flow: read-only params, small charts ---
    if multi_ticker and run_clicked:
        fallback_params = _load_fallback_params()
        from src.config.config import load_ticker_config
        first_cfg = None  # first ticker's config for macro chart bands
        for t in tickers:
            with st.spinner(f"Loading {t}..."):
                if live_mode:
                    price_df = _fetch_yfinance_data(t, str(start_date), str(end_date + timedelta(days=1)))
                else:
                    price_df = _load_price_data_for_ticker(t)
            if len(price_df) == 0:
                _log_trigger("warning", f"No data for {t}. Skipped.")
                st.warning(f"No data for **{t}**. Skipped.")
                continue
            price_df = price_df[
                (price_df["date"] >= pd.Timestamp(start_date))
                & (price_df["date"] <= pd.Timestamp(end_date))
            ].reset_index(drop=True)
            if len(price_df) < 50:
                _log_trigger("warning", f"Insufficient data for {t} ({len(price_df)} rows). Skipped.")
                st.warning(f"Insufficient data for **{t}** ({len(price_df)} rows). Skipped.")
                continue
            cfg = _build_trigger_config_from_yaml(
                t, signal_key, load_ticker_config, fallback_params, initial_capital, 0.001
            )
            if first_cfg is None:
                first_cfg = cfg
            date_end_str = str(end_date + timedelta(days=1))
            date_start_str = str(start_date)
            macro_price_df = _fetch_macro_price_df(
                cfg.macro_gsr_gold_ticker, date_start_str, date_end_str,
                from_csv=not live_mode,
            ) if cfg.macro_gsr_enabled else None
            macro_dxy_df = _fetch_macro_series("DX-Y.NYB", date_start_str, date_end_str) if cfg.macro_dxy_enabled else None
            macro_vix_df = _fetch_macro_series("^VIX", date_start_str, date_end_str) if cfg.macro_vix_enabled else None
            vix_for_regime = _fetch_macro_series("^VIX", date_start_str, date_end_str) if live_mode else None
            kwargs = {}
            if macro_price_df is not None and len(macro_price_df) > 0:
                kwargs["macro_price_df"] = macro_price_df
            if macro_dxy_df is not None and len(macro_dxy_df) > 0:
                kwargs["macro_dxy_df"] = macro_dxy_df
            if macro_vix_df is not None and len(macro_vix_df) > 0:
                kwargs["macro_vix_df"] = macro_vix_df
            if vix_for_regime is not None and len(vix_for_regime) > 0:
                kwargs["vix_df_for_regime"] = vix_for_regime
            try:
                results = _run_trigger_backtest_safe(price_df, cfg, **kwargs) if kwargs else run_trigger_backtest(price_df, cfg)
            except Exception as e:
                _log_trigger("error", f"Backtest failed for {t}: {e}")
                st.error(f"Backtest failed for {t}: {e}")
                continue
            ticker_cfg = load_ticker_config(t)
            params_text = _format_params_readonly(ticker_cfg, fallback_params, t)
            m = results.metrics
            st.markdown(f"### {t}")
            chart_col, params_col = st.columns([2, 1])
            with chart_col:
                fig = _create_price_chart_with_signals(results, height=220)
                st.plotly_chart(fig, use_container_width=True)
            with params_col:
                st.text_area("Parameters", value=params_text, height=200, disabled=True, key=f"params_{t}")
            st.caption(
                f"Sharpe: {m.get('sharpe_ratio', 0):.2f} | "
                f"Return: {m.get('total_return', 0)*100:.1f}% | "
                f"Max DD: {m.get('max_drawdown', 0)*100:.1f}% | "
                f"Trades: {len(results.trades)}"
            )
            _log_trigger("info", f"Backtest completed for {t}: {len(results.trades)} trades")
            st.markdown("---")
        # Macro indicators for multi-ticker
        render_section_header("Macro Indicators")
        date_end_str = str(end_date + timedelta(days=1))
        dxy_df = _fetch_macro_series("DX-Y.NYB", str(start_date), date_end_str)
        vix_df = _fetch_macro_series("^VIX", str(start_date), date_end_str)
        mac1, mac2 = st.columns(2)
        cfg_m = first_cfg if first_cfg else None
        with mac1:
            st.caption("DXY (Dollar Index)")
            if not dxy_df.empty:
                fig_dxy = _create_macro_chart(
                    dxy_df, "DXY", "Level", CHART_COLORS["categorical"][2],
                    buy_max=getattr(cfg_m, "macro_dxy_buy_max", None) if cfg_m else None,
                    sell_min=getattr(cfg_m, "macro_dxy_sell_min", None) if cfg_m else None,
                )
                st.plotly_chart(fig_dxy, use_container_width=True)
            else:
                st.info("DXY data unavailable. Use live mode.")
        with mac2:
            st.caption("VIX (Volatility Index)")
            if not vix_df.empty:
                fig_vix = _create_macro_chart(
                    vix_df, "VIX", "Level", CHART_COLORS["categorical"][4],
                    buy_max=getattr(cfg_m, "macro_vix_buy_max", None) if cfg_m else None,
                    sell_min=getattr(cfg_m, "macro_vix_sell_min", None) if cfg_m else None,
                )
                st.plotly_chart(fig_vix, use_container_width=True)
            else:
                st.info("VIX data unavailable. Use live mode.")
        return

    # --- Single-ticker flow ---
    if live_mode:
        with st.spinner(f"Fetching live data for {ticker} from yfinance..."):
            price_df = _fetch_yfinance_data(
                ticker,
                str(start_date),
                str(end_date + timedelta(days=1)),
            )
        if len(price_df) == 0:
            _log_trigger("error", f"Could not fetch data for {ticker} from yfinance. Check the ticker symbol.")
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
            _log_trigger("error", f"No price data found for {ticker}. Make sure it exists in data/prices.csv.")
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
        _log_trigger("warning", f"Only {len(price_df)} data points for {ticker} in the selected date range. Need at least 50 for reliable signals.")
        st.warning(
            f"Only {len(price_df)} data points for {ticker} in the selected "
            f"date range. Need at least 50 for reliable signals."
        )
        if len(price_df) == 0:
            return

    # --- Optimization Flow ---
    if optimize_clicked:
        if signal_key == "combined":
            _log_trigger("info", "Parameter optimization is not available for Combined signals. Use single indicators to optimize.")
            st.info(
                "Parameter optimization is not available for Combined signals. "
                "Use single indicators (RSI, MACD, or Bollinger) to optimize, "
                "then apply the best parameters manually in Combined mode."
            )
            return
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
            _log_trigger("error", f"Optimization failed: {e}")
            st.error(f"Optimization failed: {e}")
            return
        finally:
            progress_bar.empty()

        st.session_state["trigger_opt_results"] = opt_results
        _display_optimization_results(opt_results, signal_key)
        return

    # --- Build Config ---
    if signal_key == "combined" and not (use_rsi or use_macd or use_bollinger):
        _log_trigger("error", "Select at least one indicator (RSI, MACD, or Bollinger) for combined signals.")
        st.error("Select at least one indicator (RSI, MACD, or Bollinger) for combined signals.")
        return

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
    elif signal_key == "combined":
        config.combined_use_rsi = use_rsi
        config.combined_use_macd = use_macd
        config.combined_use_bollinger = use_bollinger
        config.combined_agreement = agreement_mode
        config.rsi_period = rsi_period
        config.rsi_oversold = rsi_oversold
        config.rsi_overbought = rsi_overbought
        config.macd_fast = macd_fast
        config.macd_slow = macd_slow
        config.macd_signal = macd_signal_p
        config.bb_period = bb_period
        config.bb_std = bb_std

    # Macro filters (single-ticker from UI + per-ticker YAML; multi-ticker from YAML)
    if not multi_ticker:
        config.macro_gsr_enabled = use_macro_filters and bool(_mf.get("gsr_enabled"))
        config.macro_gsr_gold_ticker = str(_mf.get("gold_ticker", "GLD"))
        config.macro_gsr_buy_threshold = float(_mf.get("gsr_buy_threshold", 90))
        config.macro_gsr_sell_threshold = float(_mf.get("gsr_sell_threshold", 70))
        config.macro_dxy_enabled = use_macro_filters and use_dxy
        config.macro_vix_enabled = use_macro_filters and use_vix
        if config.macro_dxy_enabled:
            config.macro_dxy_buy_max = dxy_buy_max
            config.macro_dxy_sell_min = dxy_sell_min
        if config.macro_vix_enabled:
            config.macro_vix_buy_max = vix_buy_max
            config.macro_vix_sell_min = vix_sell_min

    # --- Macro data (GSR, DXY, VIX) ---
    date_end = str(end_date + timedelta(days=1))
    date_start = str(start_date)
    macro_price_df = None
    macro_dxy_df = None
    macro_vix_df = None
    vix_df_for_regime = None
    if getattr(config, "macro_gsr_enabled", False):
        macro_price_df = _fetch_macro_price_df(
            getattr(config, "macro_gsr_gold_ticker", "GLD"),
            date_start, date_end,
            from_csv=not live_mode,
        )
    if getattr(config, "macro_dxy_enabled", False):
        macro_dxy_df = _fetch_macro_series("DX-Y.NYB", date_start, date_end)
    if getattr(config, "macro_vix_enabled", False):
        macro_vix_df = _fetch_macro_series("^VIX", date_start, date_end)
    # Always fetch VIX for regime metrics when in live mode
    if live_mode:
        vix_df_for_regime = _fetch_macro_series("^VIX", date_start, date_end)

    # --- Run Backtest ---
    with st.spinner(f"Running {signal_type} backtest on {ticker}..."):
        try:
            kwargs = {}
            if macro_price_df is not None:
                kwargs["macro_price_df"] = macro_price_df
            if macro_dxy_df is not None:
                kwargs["macro_dxy_df"] = macro_dxy_df
            if macro_vix_df is not None:
                kwargs["macro_vix_df"] = macro_vix_df
            if vix_df_for_regime is not None and len(vix_df_for_regime) > 0:
                kwargs["vix_df_for_regime"] = vix_df_for_regime
            results = _run_trigger_backtest_safe(price_df, config, **kwargs) if kwargs else run_trigger_backtest(price_df, config)
        except Exception as e:
            _log_trigger("error", f"Backtest failed: {e}")
            st.error(f"Backtest failed: {e}")
            return

    # --- Persist params to DB and session (recalled on start/refresh) ---
    c = config
    trigger_params = {
        "rsi_period": int(c.rsi_period),
        "rsi_oversold": float(c.rsi_oversold),
        "rsi_overbought": float(c.rsi_overbought),
        "macd_fast": int(c.macd_fast),
        "macd_slow": int(c.macd_slow),
        "macd_signal": int(c.macd_signal),
        "bb_period": int(c.bb_period),
        "bb_std": float(c.bb_std),
        "tx_cost": float(tx_cost),
        "ticker": ticker,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "signal_type": signal_type,
    }
    if signal_key == "combined":
        trigger_params["combined_agreement"] = getattr(c, "combined_agreement", "majority")
        trigger_params["combined_use_rsi"] = getattr(c, "combined_use_rsi", True)
        trigger_params["combined_use_macd"] = getattr(c, "combined_use_macd", True)
        trigger_params["combined_use_bollinger"] = getattr(c, "combined_use_bollinger", True)
    save_app_settings("trigger_backtester", trigger_params)
    for k, v in trigger_params.items():
        st.session_state[f"trigger_last_{k}"] = v
    _log_trigger("info", f"Backtest completed for {ticker}: {len(results.trades)} trades")

    # --- Real-time indicator (when live + auto-refresh) ---
    is_realtime = live_mode and auto_refresh
    if is_realtime:
        _render_realtime_indicator(ticker, refresh_seconds, refresh_label)
        rcol1, rcol2 = st.columns([4, 1])
        with rcol2:
            if st.button(
                "⏹ Stop real-time",
                key="trigger_stop_realtime",
                use_container_width=True,
            ):
                st.session_state["trigger_auto_refresh"] = False
                st.rerun()

    # --- Buy/Sell signal notifications (real-time mode) ---
    _check_and_notify_signals(results, ticker, signal_type, is_realtime)

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

    # --- Regime metrics (when available) ---
    if getattr(results, "metrics_by_regime", None) and results.metrics_by_regime:
        st.markdown("#### Performance by VIX Regime")
        regime = results.metrics_by_regime
        reg_df = pd.DataFrame(regime).T
        reg_df["total_return"] = reg_df["total_return"].apply(lambda x: f"{x:.1%}")
        reg_df["sharpe_ratio"] = reg_df["sharpe_ratio"].apply(lambda x: f"{x:.2f}")
        reg_df["max_drawdown"] = reg_df["max_drawdown"].apply(lambda x: f"{x:.1%}")
        reg_df["pct_days"] = reg_df["pct_days"].apply(lambda x: f"{x:.0%}")
        reg_df = reg_df.rename(columns={"pct_days": "% days"})
        st.dataframe(reg_df[["total_return", "sharpe_ratio", "max_drawdown", "num_trades", "% days"]], use_container_width=True, hide_index=True)
        st.caption("low_vol: VIX<15 | normal: 15–20 | high_vol: VIX≥20")

    st.markdown("---")

    # --- Charts ---
    tabs = st.tabs(["Price + Signals", "Equity Curve", "Signal Indicator", "Trade Log"])

    with tabs[0]:
        has_macro = (
            getattr(results.config, "macro_gsr_enabled", False)
            or getattr(results.config, "macro_dxy_enabled", False)
            or getattr(results.config, "macro_vix_enabled", False)
        )
        show_blocked = (
            st.checkbox(
                "Show blocked-by-macro signals",
                value=True,
                key="trigger_show_blocked",
                disabled=not has_macro,
                help="When macro filters are used, show signals that were blocked (hollow markers). Same colors as BUY/SELL.",
            )
            if has_macro
            else True
        )
        fig = _create_price_chart_with_signals(results, show_blocked=show_blocked)
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
            if "dxy" in display_df.columns:
                display_df["dxy"] = display_df["dxy"].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) else "-"
                )
            if "vix" in display_df.columns:
                display_df["vix"] = display_df["vix"].apply(
                    lambda x: f"{x:.1f}" if pd.notna(x) else "-"
                )
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            hint = (
                "For **Combined** mode: try **Any (1 agrees)** and ensure at least one indicator is checked. "
                if signal_key == "combined"
                else ""
            )
            _log_trigger("info", f"No trades were generated. {hint}Try adjusting the signal parameters or date range.")
            st.info(f"No trades were generated. {hint}Try adjusting the signal parameters or date range.")

    # --- Macro indicators: DXY and VIX charts (visual) ---
    st.markdown("---")
    render_section_header("Macro Indicators")
    date_end_str = str(end_date + timedelta(days=1))
    dxy_df = _fetch_macro_series("DX-Y.NYB", str(start_date), date_end_str)
    vix_df = _fetch_macro_series("^VIX", str(start_date), date_end_str)
    mac1, mac2 = st.columns(2)
    with mac1:
        st.caption("DXY (Dollar Index) — weak dollar can support risk assets")
        if not dxy_df.empty:
            cfg = results.config
            fig_dxy = _create_macro_chart(
                dxy_df, "DXY (Dollar Index)", "Level",
                CHART_COLORS["categorical"][2],
                buy_max=getattr(cfg, "macro_dxy_buy_max", None),
                sell_min=getattr(cfg, "macro_dxy_sell_min", None),
            )
            st.plotly_chart(fig_dxy, use_container_width=True)
        else:
            st.info("DXY data unavailable for this range. Use live mode.")
    with mac2:
        st.caption("VIX (Volatility Index) — high VIX indicates market fear")
        if not vix_df.empty:
            cfg = results.config
            fig_vix = _create_macro_chart(
                vix_df, "VIX (Volatility Index)", "Level",
                CHART_COLORS["categorical"][4],
                buy_max=getattr(cfg, "macro_vix_buy_max", None),
                sell_min=getattr(cfg, "macro_vix_sell_min", None),
            )
            st.plotly_chart(fig_vix, use_container_width=True)
        else:
            st.info("VIX data unavailable for this range. Use live mode.")

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
