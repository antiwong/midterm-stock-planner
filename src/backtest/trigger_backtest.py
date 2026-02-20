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
    signal_type: str = "rsi"          # "rsi", "macd", "bollinger"
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


@dataclass
class TriggerBacktestResults:
    """Results from a trigger-based backtest."""
    trades: pd.DataFrame           # date, type, price, shares, portfolio_value, pnl
    equity_curve: pd.Series        # daily portfolio value (index=date)
    buy_hold_curve: pd.Series      # daily buy-and-hold value (index=date)
    signals: pd.DataFrame          # date, close, indicator cols, signal
    metrics: Dict[str, float]
    config: TriggerConfig


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


def generate_signals(price_df: pd.DataFrame, config: TriggerConfig) -> pd.DataFrame:
    """Generate buy/sell signals from price data using technical indicators.

    Computes indicators directly on the single-ticker price series (avoids
    the panel-data groupby logic in src/indicators/technical.py).

    Args:
        price_df: DataFrame with columns [date, ticker, open, high, low, close, volume].
                  Must contain exactly one ticker.
        config: Trigger configuration with signal type and parameters.

    Returns:
        DataFrame with original columns plus indicator values and a 'signal' column
        where 1 = BUY, -1 = SELL, 0 = HOLD.
    """
    df = price_df.copy()
    df = df.sort_values("date").reset_index(drop=True)
    close = df["close"]

    if config.signal_type == "rsi":
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

    elif config.signal_type == "macd":
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

    elif config.signal_type == "bollinger":
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

    else:
        raise ValueError(f"Unknown signal type: {config.signal_type}")

    return df


def run_trigger_backtest(
    price_df: pd.DataFrame, config: TriggerConfig
) -> TriggerBacktestResults:
    """Run a trigger-based backtest on a single stock.

    Simulates long-only trading: fully invested or fully in cash.
    Buys at next day's open after a BUY signal, sells at next day's open after SELL.

    Args:
        price_df: DataFrame with OHLCV data for a single ticker.
        config: Trigger configuration.

    Returns:
        TriggerBacktestResults with trades, equity curve, metrics, etc.
    """
    signals_df = generate_signals(price_df, config)
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
            trades.append({
                "date": date,
                "type": "BUY",
                "price": exec_price,
                "shares": shares,
                "value": invest_amount,
                "pnl": None,
                "hold_days": None,
            })

        # Execute SELL
        elif signal == -1 and position_open:
            sell_value = shares * exec_price
            cost = sell_value * config.transaction_cost
            capital = sell_value - cost
            pnl = capital - (entry_price * shares)
            hold_days = (date - entry_date).days if entry_date else 0
            trades.append({
                "date": date,
                "type": "SELL",
                "price": exec_price,
                "shares": shares,
                "value": capital,
                "pnl": pnl,
                "hold_days": hold_days,
            })
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

    return TriggerBacktestResults(
        trades=trades_df,
        equity_curve=equity_curve,
        buy_hold_curve=buy_hold_curve,
        signals=signals_df,
        metrics=metrics,
        config=config,
    )


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
