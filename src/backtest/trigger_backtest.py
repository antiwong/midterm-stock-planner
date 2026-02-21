"""Buy/Sell Trigger Backtesting Engine.

Simulates single-stock trading strategies based on technical indicator triggers
(RSI, MACD, Bollinger Bands). Supports configurable parameters, transaction costs,
and produces equity curves with performance metrics.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from itertools import product
from typing import Dict, List, Optional, Tuple


@dataclass
class TriggerConfig:
    """Configuration for a trigger-based backtest."""
    signal_type: str = "rsi"          # "rsi", "macd", "bollinger", "cmf", "combined"
    initial_capital: float = 10000.0
    transaction_cost: float = 0.001   # 0.1% per trade

    # RSI parameters
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0

    # MACD parameters
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    # Bollinger Band parameters
    bb_period: int = 20
    bb_std: float = 2.0

    # Chaikin Money Flow (volume) parameters
    cmf_window: int = 20
    cmf_buy_threshold: float = 0.0   # BUY when CMF crosses above
    cmf_sell_threshold: float = 0.0  # SELL when CMF crosses below

    # Combined signal: which indicators to use
    combined_use_rsi: bool = True
    combined_use_macd: bool = True
    combined_use_bollinger: bool = True
    combined_use_cmf: bool = False
    # Agreement: "all" = all must agree (strict), "majority" = 2 of 3, "any" = 1 agrees (relaxed)
    combined_agreement: str = "majority"

    # Macro filter: Gold-Silver Ratio (for commodities like SLV)
    # When set, BUY only when GSR >= macro_gsr_buy_threshold, SELL when GSR <= macro_gsr_sell_threshold
    macro_gsr_enabled: bool = False
    macro_gsr_gold_ticker: str = "GLD"
    macro_gsr_buy_threshold: float = 90.0   # GSR > 90: silver cheap, allow BUY
    macro_gsr_sell_threshold: float = 70.0  # GSR < 70: silver expensive, allow SELL

    # Macro filter: Dollar Index (DXY) - weak dollar can support risk assets
    # BUY when DXY <= macro_dxy_buy_max, SELL when DXY >= macro_dxy_sell_min
    macro_dxy_enabled: bool = False
    macro_dxy_buy_max: float = 102.0   # BUY when DXY below this (weak dollar)
    macro_dxy_sell_min: float = 106.0  # SELL when DXY above this (strong dollar)

    # Macro filter: VIX - high vol blocks BUY, low vol allows BUY
    # BUY when VIX <= macro_vix_buy_max, SELL when VIX >= macro_vix_sell_min
    macro_vix_enabled: bool = False
    macro_vix_buy_max: float = 25.0   # BUY when VIX below this (low fear)
    macro_vix_sell_min: float = 30.0  # SELL when VIX above this (high fear)


@dataclass
class TriggerBacktestResults:
    """Results from a trigger-based backtest."""
    trades: pd.DataFrame           # date, type, price, shares, portfolio_value, pnl
    equity_curve: pd.Series        # daily portfolio value (index=date)
    buy_hold_curve: pd.Series      # daily buy-and-hold value (index=date)
    signals: pd.DataFrame          # date, close, indicator cols, signal
    metrics: Dict[str, float]
    config: TriggerConfig
    metrics_by_regime: Optional[Dict[str, Dict[str, float]]] = None  # VIX regime splits


def _compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI for a single price series."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _compute_macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    """Compute MACD for a single price series."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_histogram = macd - macd_signal
    return pd.DataFrame(
        {"macd": macd, "macd_signal": macd_signal, "macd_histogram": macd_histogram},
        index=close.index,
    )


def _compute_bollinger(
    close: pd.Series, period: int = 20, std_dev: float = 2.0
) -> pd.DataFrame:
    """Compute Bollinger Bands for a single price series."""
    middle = close.rolling(window=period, min_periods=period).mean()
    std = close.rolling(window=period, min_periods=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    pct = (close - lower) / (upper - lower)
    return pd.DataFrame(
        {"bb_upper": upper, "bb_middle": middle, "bb_lower": lower, "bb_pct": pct},
        index=close.index,
    )


def _compute_cmf(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, window: int = 20
) -> pd.Series:
    """Compute Chaikin Money Flow (CMF).

    CMF measures buying vs selling pressure over a window. Oscillates between -1 and +1.
    BUY when CMF crosses above threshold, SELL when crosses below.
    """
    mf_mult = (2 * close - high - low) / (high - low).replace(0, np.nan)
    mf_mult = mf_mult.fillna(0)
    mf_vol = mf_mult * volume
    cmf = mf_vol.rolling(window=window, min_periods=window).sum() / volume.rolling(
        window=window, min_periods=window
    ).sum()
    return cmf


def generate_signals(
    price_df: pd.DataFrame,
    config: TriggerConfig,
    macro_price_df: Optional[pd.DataFrame] = None,
    macro_dxy_df: Optional[pd.DataFrame] = None,
    macro_vix_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Generate buy/sell signals from price data using technical indicators.

    Computes indicators directly on the single-ticker price series (avoids
    the panel-data groupby logic in src/indicators/technical.py).

    Args:
        price_df: DataFrame with columns [date, ticker, open, high, low, close, volume].
                  Must contain exactly one ticker.
        config: Trigger configuration with signal type and parameters.
        macro_price_df: Optional [date, close] for GSR (e.g. GLD).
        macro_dxy_df: Optional [date, close] for Dollar Index when macro_dxy_enabled.
        macro_vix_df: Optional [date, close] for VIX when macro_vix_enabled.

    Returns:
        DataFrame with original columns plus indicator values and a 'signal' column
        where 1 = BUY, -1 = SELL, 0 = HOLD.
    """
    df = price_df.copy()
    df = df.sort_values("date").reset_index(drop=True)
    close = df["close"]

    signal_type = (config.signal_type or "rsi").lower().strip()

    if signal_type == "rsi":
        df["rsi"] = _compute_rsi(close, period=config.rsi_period)
        df["signal"] = 0
        rsi_prev = df["rsi"].shift(1)
        df.loc[
            (rsi_prev >= config.rsi_oversold) & (df["rsi"] < config.rsi_oversold),
            "signal",
        ] = 1
        df.loc[
            (rsi_prev <= config.rsi_overbought) & (df["rsi"] > config.rsi_overbought),
            "signal",
        ] = -1

    elif signal_type == "macd":
        macd_df = _compute_macd(
            close,
            fast=config.macd_fast,
            slow=config.macd_slow,
            signal=config.macd_signal,
        )
        df["macd"] = macd_df["macd"].values
        df["macd_signal"] = macd_df["macd_signal"].values
        df["macd_histogram"] = macd_df["macd_histogram"].values
        df["signal"] = 0
        macd_prev = df["macd"].shift(1)
        signal_prev = df["macd_signal"].shift(1)
        df.loc[
            (macd_prev <= signal_prev) & (df["macd"] > df["macd_signal"]),
            "signal",
        ] = 1
        df.loc[
            (macd_prev >= signal_prev) & (df["macd"] < df["macd_signal"]),
            "signal",
        ] = -1

    elif signal_type == "bollinger":
        bb_df = _compute_bollinger(close, period=config.bb_period, std_dev=config.bb_std)
        df["bb_upper"] = bb_df["bb_upper"].values
        df["bb_middle"] = bb_df["bb_middle"].values
        df["bb_lower"] = bb_df["bb_lower"].values
        df["bb_pct"] = bb_df["bb_pct"].values
        df["signal"] = 0
        close_prev = df["close"].shift(1)
        lower_prev = df["bb_lower"].shift(1)
        upper_prev = df["bb_upper"].shift(1)
        df.loc[
            (close_prev >= lower_prev) & (df["close"] < df["bb_lower"]),
            "signal",
        ] = 1
        df.loc[
            (close_prev <= upper_prev) & (df["close"] > df["bb_upper"]),
            "signal",
        ] = -1

    elif signal_type == "cmf":
        if "volume" not in df.columns:
            df["signal"] = 0
        else:
            df["cmf"] = _compute_cmf(
                df["high"], df["low"], df["close"], df["volume"],
                window=config.cmf_window,
            )
            df["signal"] = 0
            cmf_prev = df["cmf"].shift(1)
            df.loc[
                (cmf_prev <= config.cmf_buy_threshold) & (df["cmf"] > config.cmf_buy_threshold),
                "signal",
            ] = 1
            df.loc[
                (cmf_prev >= config.cmf_sell_threshold) & (df["cmf"] < config.cmf_sell_threshold),
                "signal",
            ] = -1

    elif signal_type == "combined":
        # Confluence (AND) logic: BUY/SELL only when all selected indicators agree
        sig_rsi = np.zeros(len(df), dtype=int)
        sig_macd = np.zeros(len(df), dtype=int)
        sig_bb = np.zeros(len(df), dtype=int)
        sig_cmf = np.zeros(len(df), dtype=int)

        if config.combined_use_rsi:
            df["rsi"] = _compute_rsi(close, period=config.rsi_period)
            rsi_prev = df["rsi"].shift(1)
            sig_rsi[
                (rsi_prev >= config.rsi_oversold) & (df["rsi"] < config.rsi_oversold)
            ] = 1
            sig_rsi[
                (rsi_prev <= config.rsi_overbought) & (df["rsi"] > config.rsi_overbought)
            ] = -1

        if config.combined_use_macd:
            macd_df = _compute_macd(
                close,
                fast=config.macd_fast,
                slow=config.macd_slow,
                signal=config.macd_signal,
            )
            df["macd"] = macd_df["macd"].values
            df["macd_signal"] = macd_df["macd_signal"].values
            df["macd_histogram"] = macd_df["macd_histogram"].values
            macd_prev = df["macd"].shift(1)
            signal_prev = df["macd_signal"].shift(1)
            sig_macd[
                (macd_prev <= signal_prev) & (df["macd"] > df["macd_signal"])
            ] = 1
            sig_macd[
                (macd_prev >= signal_prev) & (df["macd"] < df["macd_signal"])
            ] = -1

        if config.combined_use_bollinger:
            bb_df = _compute_bollinger(close, period=config.bb_period, std_dev=config.bb_std)
            df["bb_upper"] = bb_df["bb_upper"].values
            df["bb_middle"] = bb_df["bb_middle"].values
            df["bb_lower"] = bb_df["bb_lower"].values
            df["bb_pct"] = bb_df["bb_pct"].values
            close_prev = df["close"].shift(1)
            lower_prev = df["bb_lower"].shift(1)
            upper_prev = df["bb_upper"].shift(1)
            sig_bb[
                (close_prev >= lower_prev) & (df["close"] < df["bb_lower"])
            ] = 1
            sig_bb[
                (close_prev <= upper_prev) & (df["close"] > df["bb_upper"])
            ] = -1

        if config.combined_use_cmf and "volume" in df.columns:
            df["cmf"] = _compute_cmf(
                df["high"], df["low"], df["close"], df["volume"],
                window=config.cmf_window,
            )
            cmf_prev = df["cmf"].shift(1)
            sig_cmf[
                (cmf_prev <= config.cmf_buy_threshold) & (df["cmf"] > config.cmf_buy_threshold)
            ] = 1
            sig_cmf[
                (cmf_prev >= config.cmf_sell_threshold) & (df["cmf"] < config.cmf_sell_threshold)
            ] = -1

        # Build masks: voting logic - how many indicators must agree
        use_rsi = config.combined_use_rsi
        use_macd = config.combined_use_macd
        use_bb = config.combined_use_bollinger
        use_cmf = config.combined_use_cmf
        n_active = sum([use_rsi, use_macd, use_bb, use_cmf])
        if n_active == 0:
            raise ValueError("Combined signal requires at least one indicator selected")

        agreement = (config.combined_agreement or "majority").lower()
        if agreement == "all":
            min_agree = n_active
        elif agreement == "majority":
            min_agree = (n_active + 1) // 2  # 2 of 3, 1 of 1, 2 of 2
        elif agreement == "any":
            min_agree = 1
        else:
            min_agree = max(1, (n_active + 1) // 2)

        # BUY: at least min_agree indicators must show 1
        buy_count = np.zeros(len(df), dtype=int)
        if use_rsi:
            buy_count += (sig_rsi == 1).astype(int)
        if use_macd:
            buy_count += (sig_macd == 1).astype(int)
        if use_bb:
            buy_count += (sig_bb == 1).astype(int)
        if use_cmf:
            buy_count += (sig_cmf == 1).astype(int)
        buy_mask = buy_count >= min_agree

        # SELL: at least min_agree indicators must show -1
        sell_count = np.zeros(len(df), dtype=int)
        if use_rsi:
            sell_count += (sig_rsi == -1).astype(int)
        if use_macd:
            sell_count += (sig_macd == -1).astype(int)
        if use_bb:
            sell_count += (sig_bb == -1).astype(int)
        if use_cmf:
            sell_count += (sig_cmf == -1).astype(int)
        sell_mask = sell_count >= min_agree

        # Conflict resolution: when both buy and sell fire on same bar (indicators disagree)
        conflict = buy_mask & sell_mask
        signal = np.zeros(len(df), dtype=np.int32)
        if agreement == "any":
            # "Any" = at least one agrees. On conflict (e.g. 1 buy + 1 sell), use tie-breaker:
            # prefer the higher count; if tie, prefer BUY so we get entries.
            signal[buy_mask & (buy_count >= sell_count)] = 1
            signal[sell_mask & (sell_count > buy_count)] = -1
        else:
            # "majority" / "all": strict - no signal when indicators disagree
            signal[buy_mask & ~conflict] = 1
            signal[sell_mask & ~conflict] = -1
        df["signal"] = signal

    else:
        raise ValueError(f"Unknown signal type: {config.signal_type!r}")

    # Store raw signal before macro filters (for blocked-signal visualization)
    df["signal_raw"] = df["signal"].values.copy()

    # Macro filter: Gold-Silver Ratio (GSR) - for commodities like SLV
    if config.macro_gsr_enabled and macro_price_df is not None and len(macro_price_df) > 0:
        df_date = pd.to_datetime(df["date"]).dt.normalize().dt.tz_localize(None)
        gold = macro_price_df.rename(columns={"close": "gold_close"})[["date", "gold_close"]].copy()
        gold["date"] = pd.to_datetime(gold["date"]).dt.normalize().dt.tz_localize(None)
        merged = df_date.to_frame("date").merge(gold, on="date", how="left")
        merged["close"] = df["close"].values
        merged["gsr"] = merged["gold_close"] / merged["close"].replace(0, np.nan)
        gsr = merged["gsr"].values
        if len(gsr) == len(df):
            signal = df["signal"].values.copy()
            buy_ok = (gsr >= config.macro_gsr_buy_threshold) | (gsr != gsr)  # nan passes
            sell_ok = (gsr <= config.macro_gsr_sell_threshold) | (gsr != gsr)
            signal[(df["signal"].values == 1) & ~buy_ok] = 0
            signal[(df["signal"].values == -1) & ~sell_ok] = 0
            df["signal"] = signal
            df["gsr"] = gsr

    # Macro filter: Dollar Index (DXY)
    if config.macro_dxy_enabled and macro_dxy_df is not None and len(macro_dxy_df) > 0:
        df_date = pd.to_datetime(df["date"]).dt.normalize().dt.tz_localize(None)
        dxy = macro_dxy_df.rename(columns={"close": "dxy"})[["date", "dxy"]].copy()
        dxy["date"] = pd.to_datetime(dxy["date"]).dt.normalize().dt.tz_localize(None)
        merged = df_date.to_frame("date").merge(dxy, on="date", how="left")
        dxy_vals = merged["dxy"].values
        if len(dxy_vals) == len(df):
            signal = df["signal"].values.copy()
            buy_ok = (dxy_vals <= config.macro_dxy_buy_max) | (dxy_vals != dxy_vals)
            sell_ok = (dxy_vals >= config.macro_dxy_sell_min) | (dxy_vals != dxy_vals)
            signal[(df["signal"].values == 1) & ~buy_ok] = 0
            signal[(df["signal"].values == -1) & ~sell_ok] = 0
            df["signal"] = signal
            df["dxy"] = dxy_vals

    # Macro filter: VIX
    if config.macro_vix_enabled and macro_vix_df is not None and len(macro_vix_df) > 0:
        df_date = pd.to_datetime(df["date"]).dt.normalize().dt.tz_localize(None)
        vix = macro_vix_df.rename(columns={"close": "vix"})[["date", "vix"]].copy()
        vix["date"] = pd.to_datetime(vix["date"]).dt.normalize().dt.tz_localize(None)
        merged = df_date.to_frame("date").merge(vix, on="date", how="left")
        vix_vals = merged["vix"].values
        if len(vix_vals) == len(df):
            signal = df["signal"].values.copy()
            buy_ok = (vix_vals <= config.macro_vix_buy_max) | (vix_vals != vix_vals)
            sell_ok = (vix_vals >= config.macro_vix_sell_min) | (vix_vals != vix_vals)
            signal[(df["signal"].values == 1) & ~buy_ok] = 0
            signal[(df["signal"].values == -1) & ~sell_ok] = 0
            df["signal"] = signal
            df["vix"] = vix_vals

    return df


def run_trigger_backtest(
    price_df: pd.DataFrame,
    config: TriggerConfig,
    macro_price_df: Optional[pd.DataFrame] = None,
    macro_dxy_df: Optional[pd.DataFrame] = None,
    macro_vix_df: Optional[pd.DataFrame] = None,
    vix_df_for_regime: Optional[pd.DataFrame] = None,
) -> TriggerBacktestResults:
    """Run a trigger-based backtest on a single stock.

    Simulates long-only trading: fully invested or fully in cash.
    Buys at next day's open after a BUY signal, sells at next day's open after SELL.

    Args:
        price_df: DataFrame with OHLCV data for a single ticker.
        config: Trigger configuration.
        macro_price_df: Optional [date, close] for GSR (e.g. GLD).
        macro_dxy_df: Optional [date, close] for DXY when macro_dxy_enabled.
        macro_vix_df: Optional [date, close] for VIX when macro_vix_enabled.
        vix_df_for_regime: Optional [date, close] for regime metrics (can be same as macro_vix_df).

    Returns:
        TriggerBacktestResults with trades, equity curve, metrics, etc.
    """
    signals_df = generate_signals(
        price_df, config,
        macro_price_df=macro_price_df,
        macro_dxy_df=macro_dxy_df,
        macro_vix_df=macro_vix_df,
    )
    signals_df = signals_df.dropna(subset=["close"]).reset_index(drop=True)

    capital = config.initial_capital
    shares = 0.0
    position_open = False
    entry_price = 0.0
    entry_date = None

    trades: List[Dict] = []
    equity_values: List[float] = []
    equity_dates: List = []

    for i in range(len(signals_df)):
        row = signals_df.iloc[i]
        date = row["date"]
        close = row["close"]

        # Use next day's open if available, otherwise current close
        if i + 1 < len(signals_df) and "open" in signals_df.columns:
            exec_price = signals_df.iloc[i + 1]["open"]
        else:
            exec_price = close

        # Track equity
        if position_open:
            equity = shares * close
        else:
            equity = capital
        equity_values.append(equity)
        equity_dates.append(date)

        signal = row["signal"]

        # Execute BUY
        if signal == 1 and not position_open:
            cost = capital * config.transaction_cost
            invest_amount = capital - cost
            shares = invest_amount / exec_price
            entry_price = exec_price
            entry_date = date
            capital = 0.0
            position_open = True
            trade = {
                "date": date,
                "type": "BUY",
                "price": exec_price,
                "shares": shares,
                "value": invest_amount,
                "pnl": None,
                "hold_days": None,
            }
            if "dxy" in row and pd.notna(row.get("dxy")):
                trade["dxy"] = float(row["dxy"])
            if "vix" in row and pd.notna(row.get("vix")):
                trade["vix"] = float(row["vix"])
            trades.append(trade)

        # Execute SELL
        elif signal == -1 and position_open:
            sell_value = shares * exec_price
            cost = sell_value * config.transaction_cost
            capital = sell_value - cost
            pnl = capital - (entry_price * shares)
            hold_days = (date - entry_date).days if entry_date else 0
            trade = {
                "date": date,
                "type": "SELL",
                "price": exec_price,
                "shares": shares,
                "value": capital,
                "pnl": pnl,
                "hold_days": hold_days,
            }
            if "dxy" in row and pd.notna(row.get("dxy")):
                trade["dxy"] = float(row["dxy"])
            if "vix" in row and pd.notna(row.get("vix")):
                trade["vix"] = float(row["vix"])
            trades.append(trade)
            shares = 0.0
            position_open = False

    # Build equity curve
    equity_curve = pd.Series(equity_values, index=pd.DatetimeIndex(equity_dates), name="equity")

    # Build buy-and-hold curve
    first_close = signals_df.iloc[0]["close"]
    buy_hold_shares = config.initial_capital / first_close
    buy_hold_curve = pd.Series(
        (signals_df["close"].values * buy_hold_shares),
        index=pd.DatetimeIndex(signals_df["date"].values),
        name="buy_hold",
    )

    # Calculate metrics
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame(
        columns=["date", "type", "price", "shares", "value", "pnl", "hold_days"]
    )
    metrics = _calculate_metrics(equity_curve, buy_hold_curve, trades_df, config)

    # Regime-based metrics when VIX data available
    metrics_by_regime: Optional[Dict[str, Dict[str, float]]] = None
    vix_for_regime = vix_df_for_regime if vix_df_for_regime is not None and len(vix_df_for_regime) > 0 else macro_vix_df
    if vix_for_regime is not None and len(vix_for_regime) > 0:
        metrics_by_regime = _compute_metrics_by_vix_regime(
            equity_curve, buy_hold_curve, trades_df, vix_for_regime,
        )

    return TriggerBacktestResults(
        trades=trades_df,
        equity_curve=equity_curve,
        buy_hold_curve=buy_hold_curve,
        signals=signals_df,
        metrics=metrics,
        config=config,
        metrics_by_regime=metrics_by_regime,
    )


def _compute_metrics_by_vix_regime(
    equity: pd.Series,
    buy_hold: pd.Series,
    trades_df: pd.DataFrame,
    vix_df: pd.DataFrame,
    low_threshold: float = 15.0,
    high_threshold: float = 20.0,
) -> Dict[str, Dict[str, float]]:
    """Compute metrics split by VIX regime: low_vol (VIX<15), normal (15-20), high_vol (VIX>=20)."""
    if vix_df.empty or "close" not in vix_df.columns:
        return {}
    vix = vix_df.rename(columns={"close": "vix"})[["date", "vix"]].copy()
    vix["date"] = pd.to_datetime(vix["date"]).dt.normalize()
    equity_df = equity.reset_index()
    equity_df.columns = ["date", "equity"]
    equity_df["date"] = pd.to_datetime(equity_df["date"]).dt.normalize()
    merged = equity_df.merge(vix, on="date", how="inner")
    if len(merged) < 5:
        return {}
    merged["regime"] = "normal"
    merged.loc[merged["vix"] < low_threshold, "regime"] = "low_vol"
    merged.loc[merged["vix"] >= high_threshold, "regime"] = "high_vol"
    merged = merged.sort_values("date")
    out: Dict[str, Dict[str, float]] = {}
    for regime in ("low_vol", "normal", "high_vol"):
        sub = merged[merged["regime"] == regime].sort_values("date")
        if len(sub) < 5:
            continue
        eq = sub["equity"].values
        total_ret = (eq[-1] - eq[0]) / eq[0] if eq[0] != 0 else 0.0
        rets = np.diff(eq) / np.where(eq[:-1] != 0, eq[:-1], np.nan)
        rets = rets[np.isfinite(rets)]
        vol = float(np.std(rets) * np.sqrt(252)) if len(rets) > 1 and np.std(rets) > 0 else 0.0
        sharpe = (float(np.mean(rets)) * 252) / vol if vol > 0 else 0.0
        cummax = np.maximum.accumulate(eq)
        dd = (eq - cummax) / np.where(cummax > 0, cummax, 1)
        max_dd = float(np.min(dd)) if len(dd) > 0 else 0.0
        regime_dates = set(sub["date"].dt.date)
        trade_dates = pd.to_datetime(trades_df["date"]).dt.date.tolist() if len(trades_df) > 0 else []
        n_trades = sum(1 for d in trade_dates if d in regime_dates)
        out[regime] = {
            "total_return": total_ret,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "num_trades": float(n_trades),
            "pct_days": len(sub) / len(merged),
        }
    return out


def _calculate_metrics(
    equity: pd.Series,
    buy_hold: pd.Series,
    trades_df: pd.DataFrame,
    config: TriggerConfig,
) -> Dict[str, float]:
    """Calculate backtest performance metrics."""
    if len(equity) < 2:
        return {
            "total_return": 0.0,
            "buy_hold_return": 0.0,
            "excess_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "num_trades": 0,
            "avg_hold_days": 0.0,
            "profit_factor": 0.0,
        }

    initial = config.initial_capital
    final_equity = equity.iloc[-1]
    final_bh = buy_hold.iloc[-1]

    total_return = (final_equity - initial) / initial
    buy_hold_return = (final_bh - initial) / initial
    excess_return = total_return - buy_hold_return

    # Daily returns for Sharpe
    daily_returns = equity.pct_change().dropna()
    if len(daily_returns) > 0 and daily_returns.std() > 0:
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
    else:
        sharpe_ratio = 0.0

    # Max drawdown
    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax
    max_drawdown = drawdown.min()

    # Trade statistics
    sell_trades = trades_df[trades_df["type"] == "SELL"] if len(trades_df) > 0 else pd.DataFrame()
    num_trades = len(sell_trades)

    if num_trades > 0:
        wins = sell_trades[sell_trades["pnl"] > 0]
        losses = sell_trades[sell_trades["pnl"] <= 0]
        win_rate = len(wins) / num_trades
        avg_hold_days = sell_trades["hold_days"].mean()
        total_wins = wins["pnl"].sum() if len(wins) > 0 else 0.0
        total_losses = abs(losses["pnl"].sum()) if len(losses) > 0 else 0.0
        profit_factor = total_wins / total_losses if total_losses > 0 else float("inf")
    else:
        win_rate = 0.0
        avg_hold_days = 0.0
        profit_factor = 0.0

    return {
        "total_return": total_return,
        "buy_hold_return": buy_hold_return,
        "excess_return": excess_return,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "num_trades": num_trades,
        "avg_hold_days": avg_hold_days,
        "profit_factor": profit_factor,
    }


# ---------------------------------------------------------------------------
# Parameter Optimization
# ---------------------------------------------------------------------------

# Default search grids per signal type
PARAM_GRIDS: Dict[str, Dict[str, List]] = {
    "rsi": {
        "rsi_period": [7, 10, 14, 21],
        "rsi_oversold": [20, 25, 30, 35],
        "rsi_overbought": [65, 70, 75, 80],
    },
    "macd": {
        "macd_fast": [8, 10, 12, 15],
        "macd_slow": [20, 26, 30, 35],
        "macd_signal": [5, 7, 9, 12],
    },
    "bollinger": {
        "bb_period": [10, 15, 20, 25, 30],
        "bb_std": [1.5, 1.75, 2.0, 2.25, 2.5],
    },
}


@dataclass
class OptimizationResults:
    """Results from parameter optimization."""
    best_config: TriggerConfig
    best_metrics: Dict[str, float]
    best_result: TriggerBacktestResults
    all_runs: pd.DataFrame   # param cols + metric cols for every combination
    objective: str
    total_combinations: int


def optimize_parameters(
    price_df: pd.DataFrame,
    signal_type: str,
    objective: str = "sharpe_ratio",
    transaction_cost: float = 0.001,
    initial_capital: float = 10000.0,
    param_grid: Optional[Dict[str, List]] = None,
    min_trades: int = 3,
    progress_callback=None,
) -> OptimizationResults:
    """Grid-search over parameter combinations to find the best trigger config.

    Args:
        price_df: Single-ticker OHLCV DataFrame.
        signal_type: One of "rsi", "macd", "bollinger".
        objective: Metric to maximize. One of "sharpe_ratio", "total_return",
                   "profit_factor", "win_rate".
        transaction_cost: Transaction cost fraction (e.g. 0.001 = 0.1%).
        initial_capital: Starting capital.
        param_grid: Custom parameter grid. If None, uses PARAM_GRIDS defaults.
        min_trades: Minimum completed trades to consider a run valid.
        progress_callback: Optional callable(current, total) for progress updates.

    Returns:
        OptimizationResults with the best configuration and a summary table.
    """
    grid = param_grid or PARAM_GRIDS.get(signal_type)
    if grid is None:
        raise ValueError(f"No parameter grid for signal type: {signal_type}")

    param_names = list(grid.keys())
    param_values = list(grid.values())
    combos = list(product(*param_values))
    total = len(combos)

    rows: List[Dict] = []
    best_score = -np.inf
    best_config: Optional[TriggerConfig] = None
    best_metrics: Optional[Dict] = None
    best_result: Optional[TriggerBacktestResults] = None

    for idx, combo in enumerate(combos):
        params = dict(zip(param_names, combo))

        # Skip invalid MACD combos where fast >= slow
        if signal_type == "macd" and params.get("macd_fast", 0) >= params.get("macd_slow", 99):
            continue

        config = TriggerConfig(
            signal_type=signal_type,
            initial_capital=initial_capital,
            transaction_cost=transaction_cost,
            **params,
        )

        try:
            result = run_trigger_backtest(price_df, config)
            m = result.metrics
        except Exception:
            continue

        if progress_callback:
            progress_callback(idx + 1, total)

        row = {**params, **m}
        rows.append(row)

        # Only consider runs with enough trades
        if m["num_trades"] < min_trades:
            continue

        score = m.get(objective, -np.inf)
        if np.isfinite(score) and score > best_score:
            best_score = score
            best_config = config
            best_metrics = m
            best_result = result

    all_runs = pd.DataFrame(rows) if rows else pd.DataFrame()

    # Fallback: if no run met min_trades, pick best by objective anyway
    if best_config is None and len(all_runs) > 0:
        valid = all_runs[all_runs[objective].notna() & np.isfinite(all_runs[objective])]
        if len(valid) > 0:
            best_row = valid.loc[valid[objective].idxmax()]
            params = {k: best_row[k] for k in param_names}
            best_config = TriggerConfig(
                signal_type=signal_type,
                initial_capital=initial_capital,
                transaction_cost=transaction_cost,
                **{k: (int(v) if isinstance(v, (np.integer, int)) else float(v))
                   for k, v in params.items()},
            )
            best_result = run_trigger_backtest(price_df, best_config)
            best_metrics = best_result.metrics

    # Ultimate fallback
    if best_config is None:
        best_config = TriggerConfig(signal_type=signal_type)
        best_result = run_trigger_backtest(price_df, best_config)
        best_metrics = best_result.metrics

    return OptimizationResults(
        best_config=best_config,
        best_metrics=best_metrics,
        best_result=best_result,
        all_runs=all_runs,
        objective=objective,
        total_combinations=total,
    )
