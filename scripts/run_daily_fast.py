#!/usr/bin/env python3
"""Fast daily trading — load saved model, generate signals, execute trades.

This is the DAILY runner. Completes in under 5 minutes.
Does NOT retrain the model. Uses the latest saved model from each portfolio's DB.

For model retraining, use run_retrain.py (weekly/manual).

Steps:
    1. Load today's prices
    2. For each portfolio:
       a. Check stop-losses FIRST (before anything else)
       b. Check market regime (SPY 20d return)
       c. Load latest signals from DB (from last backtest)
       d. Apply cooldown filter
       e. Execute trades with regime scaling
    3. Write daily_summary.txt
"""

import sys
import os
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

import pandas as pd
import numpy as np

from dotenv import load_dotenv
load_dotenv()

from src.config.config import load_config

DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

# All portfolios
PORTFOLIOS = [
    {"watchlist": "moby_picks", "local": False, "capital": 100000},
    {"watchlist": "tech_giants", "local": True, "capital": 100000},
    {"watchlist": "semiconductors", "local": True, "capital": 100000},
    {"watchlist": "precious_metals", "local": True, "capital": 100000},
    {"watchlist": "sg_reits", "local": True, "capital": 100000},
    {"watchlist": "sg_blue_chips", "local": True, "capital": 100000},
    {"watchlist": "anthony_watchlist", "local": True, "capital": 13100},
    {"watchlist": "sp500", "local": True, "capital": 100000},
    {"watchlist": "clean_energy", "local": True, "capital": 100000},
    {"watchlist": "etfs", "local": True, "capital": 100000},
]


def get_latest_prices() -> dict:
    """Load latest close price per ticker from prices_daily.csv."""
    df = pd.read_csv(DATA_DIR / "prices_daily.csv")
    return df.sort_values("date").groupby("ticker").last()["close"].to_dict()


def get_spy_20d_return(latest_prices_df: pd.DataFrame = None) -> float:
    """Get SPY 20-trading-day return."""
    if latest_prices_df is None:
        latest_prices_df = pd.read_csv(DATA_DIR / "prices_daily.csv", parse_dates=["date"])
    spy = latest_prices_df[latest_prices_df["ticker"] == "SPY"].sort_values("date").tail(30)
    if len(spy) < 20:
        return 0.0
    return (spy.iloc[-1]["close"] / spy.iloc[-20]["close"]) - 1


def check_stop_losses(db_path: str, latest_prices: dict, stop_pct: float, cooldown_days: int) -> list:
    """Check and execute stop-losses. Returns list of stopped tickers."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    positions = conn.execute(
        "SELECT id, ticker, shares, entry_price, entry_date, weight FROM positions WHERE is_active = 1"
    ).fetchall()

    today = datetime.now().strftime("%Y-%m-%d")
    stopped = []

    for p in positions:
        tk = p["ticker"]
        entry = p["entry_price"]
        current = latest_prices.get(tk, entry)
        if entry <= 0:
            continue
        ret = (current / entry) - 1
        if ret <= stop_pct:
            shares = p["shares"]
            value = shares * current
            cost = value * 0.001
            pnl = (current - entry) * shares

            # Record trade
            conn.execute(
                "INSERT INTO trades (date, ticker, action, shares, price, value, cost, weight_before, weight_after) "
                "VALUES (?, ?, 'SELL', ?, ?, ?, ?, ?, 0.0)",
                (today, tk, shares, current, value, cost, p["weight"])
            )
            # Close position
            conn.execute("UPDATE positions SET is_active = 0 WHERE id = ?", (p["id"],))
            # Update cash
            conn.execute("UPDATE portfolio_state SET cash = cash + ? WHERE id = 1", (value - cost,))
            # Cooldown
            conn.execute(
                "CREATE TABLE IF NOT EXISTS stop_loss_cooldown "
                "(ticker TEXT, stopped_date TEXT, cooldown_until TEXT, PRIMARY KEY (ticker, stopped_date))"
            )
            cooldown_until = (datetime.now() + timedelta(days=cooldown_days)).strftime("%Y-%m-%d")
            conn.execute(
                "INSERT OR REPLACE INTO stop_loss_cooldown VALUES (?, ?, ?)",
                (tk, today, cooldown_until)
            )
            stopped.append({"ticker": tk, "pnl": pnl, "return": ret})
            print("  STOP-LOSS {} {:.1f} shares @ ${:.2f} (PnL: ${:+,.2f}, {:+.1%})".format(
                tk, shares, current, pnl, ret))

    conn.commit()
    conn.close()
    return stopped


def get_cooled_tickers(db_path: str) -> set:
    """Get tickers in stop-loss cooldown."""
    conn = sqlite3.connect(db_path)
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        rows = conn.execute(
            "SELECT ticker FROM stop_loss_cooldown WHERE cooldown_until > ?", (today,)
        ).fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()
    finally:
        conn.close()


def get_latest_signals(db_path: str) -> pd.DataFrame:
    """Load most recent signals from the portfolio's DB."""
    conn = sqlite3.connect(db_path)
    try:
        # Get the latest signal date
        row = conn.execute("SELECT MAX(date) FROM signals").fetchone()
        if not row or not row[0]:
            return pd.DataFrame()
        latest_date = row[0]
        signals = pd.read_sql(
            "SELECT * FROM signals WHERE date = ? ORDER BY rank",
            conn, params=(latest_date,)
        )
        return signals
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def execute_portfolio(wl: str, config, latest_prices: dict, spy_return: float, regime: str, regime_scale: float):
    """Execute one portfolio: stop-loss → regime → signals → trades."""
    db_path = str(DATA_DIR / "paper_trading_{}.db".format(wl))
    if not os.path.exists(db_path):
        print("  {} — no DB, skipping".format(wl))
        return

    stop_pct = config.backtest.stop_loss_pct
    cooldown_days = config.backtest.stop_loss_cooldown_days

    # 1. Stop-losses FIRST
    stopped = check_stop_losses(db_path, latest_prices, stop_pct, cooldown_days)
    if stopped:
        for s in stopped:
            print("    Stopped: {} ${:+,.2f} ({:+.1%})".format(s["ticker"], s["pnl"], s["return"]))

    # 2. Regime check — if EXIT, liquidate remaining
    if regime == "exit":
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        positions = conn.execute(
            "SELECT id, ticker, shares, entry_price, weight FROM positions WHERE is_active = 1"
        ).fetchall()
        today = datetime.now().strftime("%Y-%m-%d")
        for p in positions:
            tk, shares, entry = p["ticker"], p["shares"], p["entry_price"]
            current = latest_prices.get(tk, entry)
            value = shares * current
            cost = value * 0.001
            conn.execute(
                "INSERT INTO trades (date, ticker, action, shares, price, value, cost, weight_before, weight_after) "
                "VALUES (?, ?, 'SELL', ?, ?, ?, ?, ?, 0.0)",
                (today, tk, shares, current, value, cost, p["weight"])
            )
            conn.execute("UPDATE positions SET is_active = 0 WHERE id = ?", (p["id"],))
            conn.execute("UPDATE portfolio_state SET cash = cash + ? WHERE id = 1", (value - cost,))
            print("    REGIME SELL {} {:.1f} shares @ ${:.2f}".format(tk, shares, current))
        conn.commit()
        conn.close()
        return

    # 3. Load latest signals (from last backtest run)
    signals = get_latest_signals(db_path)
    if signals.empty:
        print("  {} — no signals, skipping".format(wl))
        return

    # 4. Filter cooled tickers
    cooled = get_cooled_tickers(db_path)
    buy_signals = signals[signals["action"] == "BUY"].copy()
    if cooled:
        buy_signals = buy_signals[~buy_signals["ticker"].isin(cooled)]
        if cooled:
            print("    Cooldown: {}".format(", ".join(sorted(cooled))))

    if buy_signals.empty:
        print("  {} — no buy signals after cooldown".format(wl))
        return

    # 5. Compute target weights (equal weight, capped at 20%)
    top_n = config.backtest.top_n or 5
    top = buy_signals.head(top_n)
    n = len(top)
    base_weight = 1.0 / n if n > 0 else 0
    target_weights = {row["ticker"]: min(base_weight, 0.20) for _, row in top.iterrows()}

    # Apply regime scale
    if regime_scale < 1.0:
        target_weights = {t: w * regime_scale for t, w in target_weights.items()}

    # 6. Execute (simplified — just show what would happen)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    state = conn.execute("SELECT cash, initial_value FROM portfolio_state WHERE id = 1").fetchone()
    cash = state["cash"]
    initial = state["initial_value"]

    current_positions = {
        p["ticker"]: p for p in
        conn.execute("SELECT id, ticker, shares, entry_price, weight FROM positions WHERE is_active = 1").fetchall()
    }

    # Calculate portfolio value
    invested = sum(
        p["shares"] * latest_prices.get(p["ticker"], p["entry_price"])
        for p in current_positions.values()
    )
    portfolio_value = cash + invested
    today = datetime.now().strftime("%Y-%m-%d")

    # Sell positions not in target
    for tk, pos in list(current_positions.items()):
        if tk not in target_weights:
            price = latest_prices.get(tk, pos["entry_price"])
            value = pos["shares"] * price
            cost = value * 0.001
            pnl = (price - pos["entry_price"]) * pos["shares"]
            conn.execute(
                "INSERT INTO trades (date, ticker, action, shares, price, value, cost, weight_before, weight_after) "
                "VALUES (?, ?, 'SELL', ?, ?, ?, ?, ?, 0.0)",
                (today, tk, pos["shares"], price, value, cost, pos["weight"])
            )
            conn.execute("UPDATE positions SET is_active = 0 WHERE id = ?", (pos["id"],))
            cash += value - cost
            print("    SELL {} {:.1f}@${:.2f} PnL=${:+,.0f}".format(tk, pos["shares"], price, pnl))
            del current_positions[tk]

    # Buy/rebalance target positions
    for tk, weight in target_weights.items():
        price = latest_prices.get(tk)
        if not price or price <= 0:
            continue
        target_value = portfolio_value * weight
        current_value = 0
        current_shares = 0
        if tk in current_positions:
            current_shares = current_positions[tk]["shares"]
            current_value = current_shares * price

        delta_value = target_value - current_value
        if abs(delta_value) < 50:
            continue

        delta_shares = delta_value / price
        cost = abs(delta_value) * 0.001
        new_shares = current_shares + delta_shares
        action = "BUY" if delta_shares > 0 else "REBALANCE"

        conn.execute(
            "INSERT INTO trades (date, ticker, action, shares, price, value, cost, weight_before, weight_after) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (today, tk, action, abs(delta_shares), price, abs(delta_value), cost,
             dict(current_positions[tk]).get("weight", 0) if tk in current_positions else 0, weight)
        )

        if new_shares > 0:
            entry_price = price if tk not in current_positions else current_positions[tk]["entry_price"]
            # Upsert position
            existing = conn.execute("SELECT id FROM positions WHERE ticker = ? AND is_active = 1", (tk,)).fetchone()
            if existing:
                conn.execute("UPDATE positions SET shares = ?, weight = ? WHERE id = ?",
                             (new_shares, weight, existing["id"]))
            else:
                conn.execute(
                    "INSERT INTO positions (ticker, shares, entry_price, entry_date, weight) VALUES (?, ?, ?, ?, ?)",
                    (tk, new_shares, entry_price, today, weight)
                )

        cash -= delta_value + cost
        print("    {} {} {:.1f}@${:.2f} (w={:.0%})".format(action, tk, abs(delta_shares), price, weight))

    conn.execute("UPDATE portfolio_state SET cash = ?, last_updated = ? WHERE id = 1", (cash, today))
    conn.commit()

    # Record snapshot
    positions = conn.execute(
        "SELECT ticker, shares, entry_price, weight FROM positions WHERE is_active = 1"
    ).fetchall()
    invested = sum(p["shares"] * latest_prices.get(p["ticker"], p["entry_price"]) for p in positions)
    pv = cash + invested
    daily_ret = (pv / initial) - 1

    conn.execute(
        "INSERT OR REPLACE INTO daily_snapshots (date, portfolio_value, cash, invested, daily_return, cumulative_return) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (today, pv, cash, invested, daily_ret, daily_ret)
    )
    conn.commit()
    conn.close()

    print("  {} done: ${:,.0f} ({:+.2%}) | {} positions".format(wl, pv, daily_ret, len(positions)))


def write_daily_summary(config, latest_prices, spy_return, regime, regime_scale, all_stopped):
    """Write plain-language daily summary."""
    lines = []
    lines.append("=" * 60)
    lines.append("DAILY SUMMARY — {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")))
    lines.append("=" * 60)

    lines.append("\nMARKET REGIME: {} (SPY 20d: {:+.2%})".format(regime.upper(), spy_return))
    if regime == "reduce":
        lines.append("  Position sizes scaled to {:.0%}".format(regime_scale))
    elif regime == "exit":
        lines.append("  ALL POSITIONS LIQUIDATED")

    lines.append("\nPORTFOLIOS:")
    total_value = 0
    for p in PORTFOLIOS:
        wl = p["watchlist"]
        db_path = DATA_DIR / "paper_trading_{}.db".format(wl)
        if not db_path.exists():
            continue
        try:
            conn = sqlite3.connect(str(db_path))
            snap = conn.execute(
                "SELECT portfolio_value, daily_return, cumulative_return FROM daily_snapshots ORDER BY date DESC LIMIT 1"
            ).fetchone()
            pos_count = conn.execute("SELECT COUNT(*) FROM positions WHERE is_active = 1").fetchone()[0]
            conn.close()
            if snap:
                pv, dr, cr = snap
                total_value += pv
                lines.append("  {:22s} ${:>10,.0f}  daily:{:+.2%}  total:{:+.2%}  pos:{}".format(
                    wl, pv, dr, cr, pos_count))
        except Exception:
            pass

    lines.append("\n  TOTAL: ${:,.0f}".format(total_value))

    if all_stopped:
        lines.append("\nSTOP-LOSSES TRIGGERED:")
        for s in all_stopped:
            lines.append("  {} ${:+,.2f} ({:+.1%})".format(s["ticker"], s["pnl"], s["return"]))
    else:
        lines.append("\nSTOP-LOSSES: none")

    lines.append("\n" + "=" * 60)
    summary = "\n".join(lines)

    with open(LOG_DIR / "daily_summary.txt", "w") as f:
        f.write(summary)
    print(summary)


def main():
    start = time.time()
    print("=" * 60)
    print("FAST DAILY RUN — {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print("=" * 60)

    config = load_config("config/config.yaml")

    # 1. Load prices
    print("\nLoading prices...")
    price_df = pd.read_csv(DATA_DIR / "prices_daily.csv", parse_dates=["date"])
    latest_prices = price_df.sort_values("date").groupby("ticker").last()["close"].to_dict()

    # 2. Market regime
    spy_return = get_spy_20d_return(price_df)
    mrf = config.backtest.market_regime_filter
    if mrf and (mrf.get("enabled") if isinstance(mrf, dict) else getattr(mrf, "enabled", False)):
        _get = mrf.get if isinstance(mrf, dict) else lambda k, d: getattr(mrf, k, d)
        threshold_exit = _get("threshold_exit", -0.08)
        threshold_reduce = _get("threshold_reduce", -0.05)
        reduce_scale = _get("reduce_scale", 0.30)
    else:
        threshold_exit, threshold_reduce, reduce_scale = -0.08, -0.05, 0.30

    if spy_return <= threshold_exit:
        regime, regime_scale = "exit", 0.0
    elif spy_return <= threshold_reduce:
        regime, regime_scale = "reduce", reduce_scale
    else:
        regime, regime_scale = "normal", 1.0

    print("SPY 20d: {:+.2%} → REGIME: {} (scale: {:.0%})".format(spy_return, regime.upper(), regime_scale))

    # 3. Execute each portfolio
    all_stopped = []
    for p in PORTFOLIOS:
        wl = p["watchlist"]
        print("\n--- {} ---".format(wl))
        execute_portfolio(wl, config, latest_prices, spy_return, regime, regime_scale)

    # 4. Summary
    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print("COMPLETE in {:.0f}s".format(elapsed))
    write_daily_summary(config, latest_prices, spy_return, regime, regime_scale, all_stopped)


if __name__ == "__main__":
    main()
