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

import json

import pandas as pd
import numpy as np
import yaml

from dotenv import load_dotenv
load_dotenv()

from src.config.config import load_config, bars_per_day_from_interval
from src.features.engineering import (
    compute_all_features_extended,
    make_training_dataset,
    get_feature_columns,
)
from src.models.trainer import train_lgbm_regressor, ModelConfig

DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

# Concentration limits — diversified portfolios
MAX_SECTOR_PCT = 0.25       # Max 25% of portfolio value in any single sector
MAX_SAME_WATCHLIST = 2      # Max 2 positions from the portfolio's own watchlist

# Concentration limits — sector-focused portfolios
MAX_TICKER_PCT = 0.20       # Max 20% of portfolio value in any single ticker
MAX_SAME_SUBSECTOR = 3      # Max 3 positions from the same industry/sub-sector

# Per-watchlist sub-sector group limits
# Key = watchlist name, value = dict of {group_name: (max_positions, set_of_tickers)}
WATCHLIST_GROUP_LIMITS = {
    "sg_blue_chips": {
        "SG Banks": (1, {"D05.SI", "O39.SI", "U11.SI"}),
        "SG REITs": (2, {
            "C38U.SI", "ME8U.SI", "N2IU.SI", "A17U.SI", "BUOU.SI",
            # Full sg_reits list loaded at runtime from watchlists.yaml
        }),
    },
}

# All portfolios
PORTFOLIOS = [
    {"watchlist": "moby_picks", "local": False, "capital": 100000},
    {"watchlist": "tech_giants", "local": True, "capital": 100000},
    {"watchlist": "semiconductors", "local": True, "capital": 100000},
    {"watchlist": "precious_metals", "local": True, "capital": 100000},
    {"watchlist": "sg_reits", "local": True, "capital": 100000},
    {"watchlist": "sg_blue_chips", "local": True, "capital": 100000, "primary": True, "tx_cost": 0.001},  # Sharpe 0.619 @ 0.1% tx, PF 1.22
    {"watchlist": "anthony_watchlist", "local": True, "capital": 13100},
    {"watchlist": "sp500", "local": True, "capital": 100000},
    {"watchlist": "clean_energy", "local": True, "capital": 100000},
    {"watchlist": "etfs", "local": True, "capital": 100000},
]


def load_sector_map() -> dict:
    """Load ticker → sector mapping from sectors.json."""
    for path in [DATA_DIR / "sectors.json", PROJECT_ROOT / "src" / "data" / "sectors.json"]:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    return {}


def load_industry_map() -> dict:
    """Load ticker → industry (sub-sector) mapping from sectors.csv."""
    csv_path = DATA_DIR / "sectors.csv"
    if not csv_path.exists():
        return {}
    df = pd.read_csv(csv_path)
    return dict(zip(df["ticker"].astype(str), df["industry"].fillna("Unknown")))


def load_watchlist_config() -> dict:
    """Load watchlist definitions from watchlists.yaml.

    Returns dict of {wl_name: {"category": str, "symbols": set}}.
    """
    wl_path = PROJECT_ROOT / "config" / "watchlists.yaml"
    if not wl_path.exists():
        return {}
    with open(wl_path) as f:
        data = yaml.safe_load(f)
    result = {}
    for wl_name, wl_def in data.get("watchlists", {}).items():
        result[wl_name] = {
            "category": wl_def.get("category", ""),
            "symbols": {str(s) for s in wl_def.get("symbols", [])},
        }
    return result


def is_sector_focused(portfolio_wl: str, wl_config: dict) -> bool:
    """Check if a portfolio's watchlist is sector/theme-focused."""
    cfg = wl_config.get(portfolio_wl, {})
    return cfg.get("category") in ("sector", "theme")


def apply_concentration_limits(
    buy_signals: pd.DataFrame,
    current_positions: dict,
    latest_prices: dict,
    portfolio_value: float,
    sector_map: dict,
    industry_map: dict,
    portfolio_wl: str,
    wl_config: dict,
    top_n: int,
) -> pd.DataFrame:
    """Filter buy signals to enforce concentration limits.

    Sector-focused portfolios (category="sector"):
      - No sector cap (redundant — whole portfolio is that sector)
      - MAX_TICKER_PCT (20%) per individual ticker
      - MAX_SAME_SUBSECTOR (3) positions from same industry

    Diversified portfolios:
      - MAX_SECTOR_PCT (25%) of portfolio value per sector
      - MAX_SAME_WATCHLIST (2) from the portfolio's own watchlist only

    Returns a filtered DataFrame with at most top_n rows.
    """
    focused = is_sector_focused(portfolio_wl, wl_config)
    own_symbols = wl_config.get(portfolio_wl, {}).get("symbols", set())

    # Resolve per-watchlist group limits (e.g. SG Banks max 1, SG REITs max 2)
    group_limits = WATCHLIST_GROUP_LIMITS.get(portfolio_wl, {})
    # Expand SG REITs group with full sg_reits watchlist if available
    if "SG REITs" in group_limits and "sg_reits" in wl_config:
        _, base_set = group_limits["SG REITs"]
        reit_tickers = wl_config["sg_reits"].get("symbols", set())
        group_limits["SG REITs"] = (group_limits["SG REITs"][0], base_set | reit_tickers)

    # Build current exposure from existing positions
    sector_value: Dict[str, float] = {}
    subsector_count: Dict[str, int] = {}
    ticker_value: Dict[str, float] = {}
    own_wl_count = 0
    group_count: Dict[str, int] = {g: 0 for g in group_limits}

    for tk, pos in current_positions.items():
        price = latest_prices.get(tk, pos["entry_price"])
        value = pos["shares"] * price
        ticker_value[tk] = value

        sector = sector_map.get(tk, "Unknown")
        sector_value[sector] = sector_value.get(sector, 0) + value

        industry = industry_map.get(tk, "Unknown")
        subsector_count[industry] = subsector_count.get(industry, 0) + 1

        if tk in own_symbols:
            own_wl_count += 1

        for grp, (_, tickers) in group_limits.items():
            if tk in tickers:
                group_count[grp] += 1

    accepted = []
    skipped = []

    for _, row in buy_signals.iterrows():
        if len(accepted) >= top_n:
            break
        tk = row["ticker"]
        price = latest_prices.get(tk, 0)
        if price <= 0:
            continue

        est_weight = 1.0 / top_n
        est_value = portfolio_value * est_weight
        sector = sector_map.get(tk, "Unknown")
        industry = industry_map.get(tk, "Unknown")

        # --- Per-watchlist group limits (applies to all portfolio types) ---
        group_breached = False
        for grp, (max_n, tickers) in group_limits.items():
            if tk in tickers and group_count[grp] >= max_n:
                skipped.append((tk, "{} already has {}/{}".format(grp, group_count[grp], max_n)))
                group_breached = True
                break
        if group_breached:
            continue

        if focused:
            # --- Sector-focused rules ---

            # Per-ticker position limit (20%)
            existing_val = ticker_value.get(tk, 0)
            if (existing_val + est_value) / portfolio_value > MAX_TICKER_PCT:
                skipped.append((tk, "ticker at {:.0%}".format(
                    (existing_val + est_value) / portfolio_value)))
                continue

            # Sub-sector (industry) limit
            if subsector_count.get(industry, 0) >= MAX_SAME_SUBSECTOR and industry != "Unknown":
                skipped.append((tk, "sub-sector:{} already has {}".format(
                    industry, subsector_count[industry])))
                continue

        else:
            # --- Diversified rules ---

            # Sector cap (25%)
            new_sector_total = sector_value.get(sector, 0) + est_value
            if new_sector_total / portfolio_value > MAX_SECTOR_PCT and sector != "Unknown":
                skipped.append((tk, "sector:{} at {:.0%}".format(
                    sector, new_sector_total / portfolio_value)))
                continue

            # Watchlist limit — only for multi-watchlist portfolios (moby_picks, sp500)
            # Skip this check when the portfolio IS the watchlist (all tickers are "own")
            is_single_watchlist = own_symbols and all(
                row2["ticker"] in own_symbols for _, row2 in buy_signals.head(top_n).iterrows()
            )
            if not is_single_watchlist and tk in own_symbols and own_wl_count >= MAX_SAME_WATCHLIST:
                skipped.append((tk, "own watchlist {} already has {}".format(
                    portfolio_wl, own_wl_count)))
                continue

        # Accept — update tracking
        accepted.append(row)
        sector_value[sector] = sector_value.get(sector, 0) + est_value
        subsector_count[industry] = subsector_count.get(industry, 0) + 1
        ticker_value[tk] = ticker_value.get(tk, 0) + est_value
        if tk in own_symbols:
            own_wl_count += 1
        for grp, (_, tickers) in group_limits.items():
            if tk in tickers:
                group_count[grp] += 1

    if skipped:
        for tk, reason in skipped:
            print("    SKIP {} ({})".format(tk, reason))

    if not accepted:
        return pd.DataFrame()
    return pd.DataFrame(accepted)


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


def generate_live_signals(wl: str, config, price_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> pd.DataFrame:
    """Generate today's signals by training on historical data and scoring today's features.

    1. Compute features for ALL dates including today (no forward returns needed)
    2. Build training targets only for dates with 63-day forward returns
    3. Train model on most recent 3 years of training data
    4. Score today's features → ranked signal list

    Returns DataFrame with columns: ticker, prediction, rank, action
    """
    with open(PROJECT_ROOT / "config" / "watchlists.yaml") as f:
        wl_data = yaml.safe_load(f)
    symbols = [str(s) for s in wl_data["watchlists"][wl]["symbols"]]
    wl_prices = price_df[price_df["ticker"].isin(symbols)]
    n_tickers = wl_prices["ticker"].nunique()
    if n_tickers < 2:
        return pd.DataFrame()

    fc = config.features
    bpd = bars_per_day_from_interval("1d")

    # Step 1: compute features for all dates (including today)
    feature_df = compute_all_features_extended(
        price_df=wl_prices, fundamental_df=None, benchmark_df=benchmark_df,
        include_technical=getattr(fc, "include_technical", True),
        include_rsi=getattr(fc, "include_rsi", False),
        include_obv=False,
        include_momentum=getattr(fc, "include_momentum", False),
        include_mean_reversion=getattr(fc, "include_mean_reversion", False),
        bars_per_day=bpd,
        rsi_period=fc.rsi_period, macd_fast=fc.macd_fast,
        macd_slow=fc.macd_slow, macd_signal=fc.macd_signal,
    )
    feature_cols = get_feature_columns(feature_df)
    if not feature_cols:
        return pd.DataFrame()

    # Step 2: build training data (only rows with valid 63-day forward returns)
    training_data = make_training_dataset(
        feature_df, benchmark_df, fc.horizon_days, config.model.target_col, bpd,
    )
    if training_data.empty:
        return pd.DataFrame()

    # Use most recent 3 years of training data
    train_years = config.backtest.train_years
    max_train_date = training_data["date"].max()
    min_train_date = max_train_date - pd.Timedelta(days=int(train_years * 365.25))
    train_subset = training_data[training_data["date"] >= min_train_date]

    # Step 3: train model
    model, _, _, metrics = train_lgbm_regressor(train_subset, feature_cols, config.model)

    # Step 4: score TODAY's features (latest date in feature_df, regardless of target)
    latest_date = feature_df["date"].max()
    today_features = feature_df[feature_df["date"] == latest_date].copy()
    if today_features.empty:
        return pd.DataFrame()

    X_today = today_features[feature_cols].fillna(0)
    today_features["prediction"] = model.predict(X_today)
    today_features = today_features.sort_values("prediction", ascending=False)
    today_features["rank"] = range(1, len(today_features) + 1)

    top_n = config.backtest.top_n or 5
    today_features["action"] = "HOLD"
    today_features.iloc[:top_n, today_features.columns.get_loc("action")] = "BUY"

    print("    Live signals: trained on {:,} rows ({} to {}), scoring {} on {}".format(
        len(train_subset), min_train_date.date(), max_train_date.date(),
        n_tickers, latest_date.date()))

    return today_features[["ticker", "prediction", "rank", "action"]].reset_index(drop=True)


def execute_portfolio(wl: str, config, latest_prices: dict, spy_return: float, regime: str, regime_scale: float,
                      sector_map: dict = None, industry_map: dict = None, wl_config: dict = None,
                      price_df: pd.DataFrame = None, benchmark_df: pd.DataFrame = None):
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

    # 3. Generate live signals (train on historical data, score today's features)
    if price_df is not None and benchmark_df is not None:
        signals = generate_live_signals(wl, config, price_df, benchmark_df)
    else:
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

    # 4b. Get current positions and portfolio value for concentration check
    top_n = config.backtest.top_n or 5

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    pre_positions = {
        p["ticker"]: p for p in
        conn.execute("SELECT id, ticker, shares, entry_price, weight FROM positions WHERE is_active = 1").fetchall()
    }
    pre_state = conn.execute("SELECT cash, initial_value FROM portfolio_state WHERE id = 1").fetchone()
    pre_cash = pre_state["cash"]
    pre_invested = sum(
        p["shares"] * latest_prices.get(p["ticker"], p["entry_price"])
        for p in pre_positions.values()
    )
    pre_pv = pre_cash + pre_invested
    conn.close()

    # 5. Apply concentration limits, then compute target weights
    if sector_map and wl_config:
        top = apply_concentration_limits(
            buy_signals, pre_positions, latest_prices, pre_pv,
            sector_map, industry_map or {}, wl, wl_config, top_n,
        )
        if top.empty:
            print("  {} — no buy signals after concentration limits".format(wl))
            return
    else:
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
            try:
                conn.execute("UPDATE positions SET is_active = 0 WHERE id = ?", (pos["id"],))
            except sqlite3.IntegrityError:
                # UNIQUE constraint on (ticker, entry_date, is_active) — delete the old inactive row first
                conn.execute("DELETE FROM positions WHERE ticker = ? AND entry_date = ? AND is_active = 0",
                             (tk, pos["entry_date"] if "entry_date" in pos.keys() else today))
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

    # 1. Load prices + benchmark
    print("\nLoading prices...")
    price_df = pd.read_csv(DATA_DIR / "prices_daily.csv", parse_dates=["date"])
    latest_prices = price_df.sort_values("date").groupby("ticker").last()["close"].to_dict()
    benchmark_df = pd.read_csv(DATA_DIR / "benchmark_daily.csv", parse_dates=["date"])

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

    # 2b. Load sector, industry, and watchlist mappings for concentration limits
    sector_map = load_sector_map()
    industry_map = load_industry_map()
    wl_config = load_watchlist_config()
    print("Sector map: {} tickers, Industry map: {} tickers, Watchlists: {}".format(
        len(sector_map), len(industry_map), len(wl_config)))

    # 3. Execute each portfolio
    all_stopped = []
    for p in PORTFOLIOS:
        wl = p["watchlist"]
        focused = is_sector_focused(wl, wl_config)
        print("\n--- {} {} ---".format(wl, "[sector-focused]" if focused else "[diversified]"))
        execute_portfolio(wl, config, latest_prices, spy_return, regime, regime_scale,
                          sector_map, industry_map, wl_config, price_df, benchmark_df)

    # 4. Summary
    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print("COMPLETE in {:.0f}s".format(elapsed))
    write_daily_summary(config, latest_prices, spy_return, regime, regime_scale, all_stopped)


if __name__ == "__main__":
    main()
