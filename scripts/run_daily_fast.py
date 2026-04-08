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

import requests

DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

# Concentration limits — diversified portfolios
MAX_SECTOR_PCT = 0.40       # Max 40% of portfolio value in any single sector
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
    "precious_metals": {
        "Miners": (2, {
            "NEM", "GOLD", "KGC", "BTG", "CDE", "AEM", "AU", "EGO", "AGI", "HL",
            "HMY", "PAAS", "MAG",
        }),
        "Streaming/Royalty": (1, {"FNV", "WPM", "RGLD", "OR", "SAND"}),
        "Silver": (1, {"SLV", "SIVR", "PSLV", "AG", "PAAS", "MAG"}),
        "Gold ETFs": (2, {"GLD", "IAU", "GLDM", "SGOL"}),
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

# Slack webhooks — stock-planner channel + sentimental-blogs channel
SLACK_STOCK_PLANNER = os.environ.get("SLACK_WEBHOOK_URL") or os.environ.get("slack_webhook")
SLACK_SENTIMENT = os.environ.get("SLACK_WEBHOOK_SENTIMENT")
SP_TAG = os.environ.get("SP_INSTANCE", "SP")


def notify_slack(message: str, channel: str = "stock-planner"):
    """Send message to Slack. channel: 'stock-planner' or 'sentiment'."""
    url = SLACK_SENTIMENT if channel == "sentiment" else SLACK_STOCK_PLANNER
    if not url:
        return
    tagged = "[{}] {}".format(SP_TAG, message)
    try:
        requests.post(url, json={"text": tagged}, timeout=15)
    except Exception:
        pass


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
      - MAX_SECTOR_PCT (40%) of portfolio value per sector
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

            # Sector cap (40%)
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


def get_ticker_20d_return(ticker: str, price_df: pd.DataFrame = None) -> float:
    """Get any ticker's 20-trading-day return (for STI/ES3.SI regime check)."""
    try:
        if price_df is not None:
            tk = price_df[price_df["ticker"] == ticker].sort_values("date").tail(30)
            if len(tk) >= 20:
                return (tk.iloc[-1]["close"] / tk.iloc[-20]["close"]) - 1
        # Fallback to yfinance for tickers not in price_df
        import yfinance as yf
        data = yf.download(ticker, period="2mo", interval="1d", progress=False)
        if len(data) >= 20:
            return (data["Close"].iloc[-1] / data["Close"].iloc[-20]) - 1
    except Exception:
        pass
    return 0.0


def get_vix_level() -> float:
    """Get current VIX level."""
    try:
        import yfinance as yf
        vix = yf.download("^VIX", period="5d", interval="1d", progress=False)
        if not vix.empty:
            return float(vix["Close"].iloc[-1].item() if hasattr(vix["Close"].iloc[-1], 'item') else vix["Close"].iloc[-1])
    except Exception:
        pass
    return 20.0  # Default to neutral if unavailable


def compute_vix_scale(vix: float) -> float:
    """VIX-based position scaling.

    VIX < 20: 100%  |  20-25: 50%  |  25-30: 50%  |  > 30: 25%
    """
    if vix < 20:
        return 1.0
    elif vix < 25:
        return 0.50
    elif vix < 30:
        return 0.50
    else:
        return 0.25


def compute_dxy_scale(uup_20d_return: float,
                      threshold_headwind: float = 0.02,
                      headwind_scale: float = 0.25,
                      mild_headwind_scale: float = 0.60) -> float:
    """UUP/DXY-based position scaling for precious_metals.

    Dollar strength is a headwind for gold/silver.
    UUP > threshold_headwind:  headwind_scale (strong headwind)
    UUP 0 to threshold:        mild_headwind_scale (mild headwind)
    UUP < 0%:                  1.00 (tailwind/flat — full sizing)
    """
    import math
    if math.isnan(uup_20d_return):
        return 1.0
    if uup_20d_return > threshold_headwind:
        return headwind_scale
    elif uup_20d_return >= 0.0:
        return mild_headwind_scale
    return 1.0


def compute_dual_regime(spy_return: float, sgx_return: float,
                        threshold_reduce: float = -0.05,
                        threshold_exit: float = -0.08,
                        reduce_scale: float = 0.30) -> tuple:
    """Dual US+SGX regime filter — use the MORE conservative of the two.

    Returns (regime, regime_scale, trigger_source).
    """
    # Determine each market's regime independently
    def _classify(ret):
        if ret <= threshold_exit:
            return "exit", 0.0
        elif ret <= threshold_reduce:
            return "reduce", reduce_scale
        return "normal", 1.0

    spy_regime, spy_scale = _classify(spy_return)
    sgx_regime, sgx_scale = _classify(sgx_return)

    # Use the more conservative (lower scale)
    if spy_scale <= sgx_scale:
        return spy_regime, spy_scale, "SPY"
    return sgx_regime, sgx_scale, "ES3.SI"


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
            # Close position — write all four fields to avoid zombie rows
            try:
                conn.execute(
                    "UPDATE positions SET is_active = 0, exit_date = ?, exit_price = ?, realized_pnl = ? WHERE id = ?",
                    (today, current, pnl, p["id"])
                )
            except sqlite3.IntegrityError:
                # UNIQUE constraint on (ticker, entry_date, is_active) — delete the old inactive row first
                conn.execute("DELETE FROM positions WHERE ticker = ? AND entry_date = ? AND is_active = 0",
                             (tk, p["entry_date"]))
                conn.execute(
                    "UPDATE positions SET is_active = 0, exit_date = ?, exit_price = ?, realized_pnl = ? WHERE id = ?",
                    (today, current, pnl, p["id"])
                )
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


def _build_cross_asset_prices(price_df: pd.DataFrame, ref_tickers: list) -> dict:
    """Extract reference ticker DataFrames from price_df for cross-asset features."""
    result = {}
    for ticker in ref_tickers:
        tk_df = price_df[price_df["ticker"] == ticker].copy()
        if not tk_df.empty:
            result[ticker] = tk_df
    return result


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

    # Check for per-watchlist cross-asset feature override
    wl_overrides = fc.watchlist_overrides or {}
    wl_override = wl_overrides.get(wl, {})
    use_cross_asset = wl_override.get("use_cross_asset", fc.use_cross_asset)

    cross_asset_prices = None
    if use_cross_asset:
        ref_tickers = get_reference_etf_tickers()
        cross_asset_prices = _build_cross_asset_prices(price_df, ref_tickers)

    # Step 1: compute features for all dates (including today)
    feature_df = compute_all_features_extended(
        price_df=wl_prices, fundamental_df=None, benchmark_df=benchmark_df,
        include_technical=getattr(fc, "include_technical", True),
        include_rsi=getattr(fc, "include_rsi", False),
        include_obv=False,
        include_momentum=getattr(fc, "include_momentum", False),
        include_mean_reversion=getattr(fc, "include_mean_reversion", False),
        include_cross_asset=use_cross_asset,
        cross_asset_prices=cross_asset_prices,
        cross_asset_params=fc.cross_asset if isinstance(fc.cross_asset, dict) else None,
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

    # 1b. Paused watchlist — stop-losses still run, but no new BUY entries
    paused = getattr(config.backtest, "paused_watchlists", None) or []
    if wl in paused:
        print("  {} — PAUSED (no new buys), existing positions run normally".format(wl))
        return

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
            pnl = (current - entry) * shares
            try:
                conn.execute(
                    "UPDATE positions SET is_active = 0, exit_date = ?, exit_price = ?, realized_pnl = ? WHERE id = ?",
                    (today, current, pnl, p["id"])
                )
            except sqlite3.IntegrityError:
                conn.execute("DELETE FROM positions WHERE ticker = ? AND entry_date = ? AND is_active = 0",
                             (tk, p["entry_date"]))
                conn.execute(
                    "UPDATE positions SET is_active = 0, exit_date = ?, exit_price = ?, realized_pnl = ? WHERE id = ?",
                    (today, current, pnl, p["id"])
                )
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
            if not price or price <= 0 or pos["shares"] <= 0:
                print("    SKIP SELL {} — no valid price/shares".format(tk))
                continue
            value = pos["shares"] * price
            cost = value * 0.001
            pnl = (price - pos["entry_price"]) * pos["shares"]
            conn.execute(
                "INSERT INTO trades (date, ticker, action, shares, price, value, cost, weight_before, weight_after) "
                "VALUES (?, ?, 'SELL', ?, ?, ?, ?, ?, 0.0)",
                (today, tk, pos["shares"], price, value, cost, pos["weight"])
            )
            try:
                conn.execute(
                    "UPDATE positions SET is_active = 0, exit_date = ?, exit_price = ?, realized_pnl = ? WHERE id = ?",
                    (today, price, pnl, pos["id"])
                )
            except sqlite3.IntegrityError:
                # UNIQUE constraint on (ticker, entry_date, is_active) — delete the old inactive row first
                conn.execute("DELETE FROM positions WHERE ticker = ? AND entry_date = ? AND is_active = 0",
                             (tk, pos["entry_date"] if "entry_date" in pos.keys() else today))
                conn.execute(
                    "UPDATE positions SET is_active = 0, exit_date = ?, exit_price = ?, realized_pnl = ? WHERE id = ?",
                    (today, price, pnl, pos["id"])
                )
            cash += value - cost
            print("    SELL {} {:.1f}@${:.2f} PnL=${:+,.0f}".format(tk, pos["shares"], price, pnl))
            del current_positions[tk]

    # Buy/rebalance target positions
    for tk, weight in target_weights.items():
        price = latest_prices.get(tk)
        if not price or price <= 0:
            continue

        # Skip if already holding this ticker at target weight (prevent stacking)
        if tk in current_positions and abs(current_positions[tk]["weight"] - weight) < 0.005:
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
                try:
                    conn.execute(
                        "INSERT INTO positions (ticker, shares, entry_price, entry_date, weight) VALUES (?, ?, ?, ?, ?)",
                        (tk, new_shares, entry_price, today, weight)
                    )
                except sqlite3.IntegrityError:
                    # UNIQUE constraint on (ticker, entry_date, is_active) — update existing inactive row
                    conn.execute(
                        "UPDATE positions SET shares = ?, entry_price = ?, weight = ?, is_active = 1, "
                        "exit_date = NULL, exit_price = NULL, realized_pnl = NULL "
                        "WHERE ticker = ? AND entry_date = ? AND is_active = 0",
                        (new_shares, entry_price, weight, tk, today)
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


def write_daily_summary(config, latest_prices, spy_return, regime, regime_scale, all_stopped,
                        sgx_return=0.0, vix_level=20.0):
    """Write plain-language daily summary."""
    lines = []
    lines.append("=" * 60)
    lines.append("DAILY SUMMARY — {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")))
    lines.append("=" * 60)

    lines.append("\nMARKET REGIME: {} (scale: {:.0%})".format(regime.upper(), regime_scale))
    lines.append("  SPY 20d: {:+.2%} | ES3.SI 20d: {:+.2%} | VIX: {:.1f}".format(
        spy_return, sgx_return, vix_level))
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


PREDICTION_HORIZONS = [5, 63]  # days
OVERALL_TIMEOUT_S = 1200  # 20 minutes


def get_all_tickers(watchlists: list) -> list:
    """Get union of all tickers across given watchlists (deduplicated)."""
    config_path = PROJECT_ROOT / "config" / "watchlists.yaml"
    with open(config_path) as f:
        wl_config = yaml.safe_load(f)
    all_tickers = set()
    for wl_name in watchlists:
        wl = wl_config.get("watchlists", {}).get(wl_name, {})
        all_tickers.update(str(s) for s in wl.get("symbols", []))
    return sorted(all_tickers)


def get_reference_etf_tickers() -> list:
    """Get all unique reference ETF tickers from watchlists.yaml (not tradeable symbols)."""
    config_path = PROJECT_ROOT / "config" / "watchlists.yaml"
    with open(config_path) as f:
        wl_config = yaml.safe_load(f)
    ref_etfs = wl_config.get("reference_etfs", {})
    all_ref = set()
    for group_tickers in ref_etfs.values():
        if isinstance(group_tickers, list):
            all_ref.update(str(t) for t in group_tickers)
    return sorted(all_ref)


# ── Step runner ──────────────────────────────────────────────────────────────

def run_step(step_num: int, name: str, fn, step_results: list, **kwargs):
    """Run a step with timing, error isolation, and Slack notification on failure.

    Each step:
    - Logs start and completion time
    - Sends Slack notification if it fails
    - Continues to next step on failure (never aborts the run)
    """
    print("\n[{}/8] {} — starting...".format(step_num, name))
    t0 = time.time()
    try:
        result = fn(**kwargs) if kwargs else fn()
        elapsed = time.time() - t0
        status = "OK"
        print("[{}/8] {} — done ({:.1f}s)".format(step_num, name, elapsed))
        step_results.append({"step": step_num, "name": name, "time_s": elapsed, "status": status})
        return result
    except Exception as e:
        elapsed = time.time() - t0
        status = "FAILED"
        print("[{}/8] {} — FAILED: {} ({:.1f}s)".format(step_num, name, e, elapsed))
        notify_slack(":x: [{}/8] {} FAILED: {}".format(step_num, name, str(e)[:200]))
        step_results.append({"step": step_num, "name": name, "time_s": elapsed, "status": status, "error": str(e)[:200]})
        return None


# ── Step 1: Price Refresh ────────────────────────────────────────────────────

def step_price_refresh() -> dict:
    """Download fresh prices via yf.download() batch mode. ~30-40s."""
    import yfinance as yf
    import signal

    watchlist_names = [p["watchlist"] for p in PORTFOLIOS]
    all_tickers = get_all_tickers(watchlist_names)
    # Also fetch reference ETFs (UUP, TIP, etc.) for cross-asset features
    ref_tickers = get_reference_etf_tickers()
    added_ref = [t for t in ref_tickers if t not in all_tickers]
    if added_ref:
        all_tickers = sorted(set(all_tickers) | set(ref_tickers))
        print("  + {} reference ETFs: {}".format(len(added_ref), ", ".join(added_ref)))
    sgx_tickers = [t for t in all_tickers if t.endswith(".SI")]
    us_tickers = [t for t in all_tickers if not t.endswith(".SI")]

    print("  Refreshing: {} US + {} SGX tickers".format(len(us_tickers), len(sgx_tickers)))

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    all_dfs = []
    us_rows, sgx_rows = 0, 0

    # US batch download
    if us_tickers:
        try:
            yf_data = yf.download(
                us_tickers, start=start_date, end=end_date,
                group_by="ticker", auto_adjust=True, threads=True, progress=False,
                timeout=60,
            )
            rows = _parse_yf_batch(yf_data, us_tickers)
            if rows:
                all_dfs.append(pd.DataFrame(rows))
                us_rows = len(rows)
                print("  US: {} rows".format(us_rows))
        except Exception as e:
            print("  US download failed: {}".format(e))

    # SGX batch download
    if sgx_tickers:
        try:
            yf_data = yf.download(
                sgx_tickers, start=start_date, end=end_date,
                group_by="ticker", auto_adjust=True, threads=True, progress=False,
                timeout=60,
            )
            rows = _parse_yf_batch(yf_data, sgx_tickers)
            if rows:
                all_dfs.append(pd.DataFrame(rows))
                sgx_rows = len(rows)
                print("  SGX: {} rows".format(sgx_rows))
        except Exception as e:
            print("  SGX download failed: {}".format(e))

    # Merge and save
    output_path = DATA_DIR / "prices_daily.csv"
    if all_dfs:
        new_data = pd.concat(all_dfs, ignore_index=True)
        if output_path.exists():
            existing = pd.read_csv(output_path)
            combined = pd.concat([existing, new_data], ignore_index=True).drop_duplicates(
                subset=["date", "ticker"])
            combined.to_csv(output_path, index=False)
        else:
            new_data.to_csv(output_path, index=False)
        print("  Saved {} new rows (US: {}, SGX: {})".format(len(new_data), us_rows, sgx_rows))
        # Keep prices.csv in sync for dashboard and ad-hoc scripts
        import shutil
        shutil.copy2(output_path, DATA_DIR / "prices.csv")
        print("  Synced prices.csv <- prices_daily.csv")
    else:
        print("  WARNING: No data downloaded — using stale prices")
        notify_slack(":warning: Price refresh returned 0 rows — stale prices")

    # Also refresh benchmark
    try:
        bench_data = yf.download("SPY", start=start_date, end=end_date,
                                  auto_adjust=True, progress=False, timeout=30)
        if bench_data is not None and len(bench_data) > 0:
            bench_rows = []
            for idx, row in bench_data.iterrows():
                bench_rows.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": round(float(row.get("Open", 0)), 4),
                    "high": round(float(row.get("High", 0)), 4),
                    "low": round(float(row.get("Low", 0)), 4),
                    "close": round(float(row.get("Close", 0)), 4),
                    "volume": int(row.get("Volume", 0)),
                })
            bench_path = DATA_DIR / "benchmark_daily.csv"
            if bench_path.exists():
                existing = pd.read_csv(bench_path)
                combined = pd.concat([existing, pd.DataFrame(bench_rows)], ignore_index=True)
                combined = combined.drop_duplicates(subset=["date"])
                combined.to_csv(bench_path, index=False)
    except Exception as e:
        print("  Benchmark refresh failed: {}".format(e))

    return {"us_rows": us_rows, "sgx_rows": sgx_rows, "total": us_rows + sgx_rows}


def _parse_yf_batch(yf_data, tickers: list) -> list:
    """Parse yf.download() batch result into list of row dicts."""
    rows = []
    for ticker in tickers:
        try:
            if len(tickers) == 1:
                t_df = yf_data
            else:
                t_df = yf_data[ticker] if ticker in yf_data.columns.get_level_values(0) else None
            if t_df is None or t_df.empty:
                continue
            t_df = t_df.dropna(subset=["Close"])
            for idx, row in t_df.iterrows():
                rows.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "ticker": ticker,
                    "open": round(float(row.get("Open", 0)), 4),
                    "high": round(float(row.get("High", 0)), 4),
                    "low": round(float(row.get("Low", 0)), 4),
                    "close": round(float(row.get("Close", 0)), 4),
                    "volume": int(row.get("Volume", 0)),
                })
        except Exception:
            pass
    return rows


# ── Step 2: Sentiment Check ─────────────────────────────────────────────────

def step_sentiment_check() -> dict:
    """Check DuckDB freshness. SentimentPulse crawl runs separately. ~2s."""
    try:
        import duckdb
        db_path = DATA_DIR / "sentimentpulse.db"
        if not db_path.exists():
            print("  sentimentpulse.db not found — sentiment unavailable")
            return {"status": "skipped", "reason": "no_duckdb"}

        conn = duckdb.connect(str(db_path), read_only=True)
        row = conn.execute(
            "SELECT MAX(date) as latest, COUNT(DISTINCT ticker) as tickers FROM sentiment_features"
        ).fetchone()
        conn.close()

        latest_date = str(row[0]) if row[0] else "none"
        ticker_count = row[1] if row[1] else 0
        print("  DuckDB sentiment: latest={}, tickers={}".format(latest_date, ticker_count))

        if row[0]:
            try:
                days_old = (datetime.now().date() - pd.Timestamp(row[0]).date()).days
                if days_old > 1:
                    print("  WARNING: DuckDB sentiment is {} days old".format(days_old))
            except Exception:
                pass

        return {"latest_date": latest_date, "tickers": ticker_count}
    except ImportError:
        print("  duckdb not installed — skipping")
        return {"status": "skipped", "reason": "no_duckdb_module"}


# ── Step 3: Moby Parsing ────────────────────────────────────────────────────

def step_moby_parsing() -> dict:
    """Parse Moby emails for ticker picks. Skips gracefully if no credentials. ~5s."""
    moby_password = os.environ.get("MOBY_APP_PASSWORD", "")
    if not moby_password:
        print("  MOBY_APP_PASSWORD not set — skipping")
        return {"status": "skipped"}

    result = {}

    # Email picks
    try:
        from scripts.parse_moby_emails import MobyEmailParser
        parser = MobyEmailParser()
        picks = parser.download(days=7)
        count = len(picks) if picks is not None else 0
        print("  Parsed {} Moby email picks".format(count))
        result["email_picks"] = count
    except Exception as e:
        print("  Moby email parsing failed: {}".format(e))
        result["email_picks_error"] = str(e)[:100]

    # Structured analysis from moby_news/
    try:
        from scripts.parse_moby_analysis import parse_all_files
        moby_dir = PROJECT_ROOT / "moby_news"
        if moby_dir.exists():
            df = parse_all_files(moby_dir)
            if len(df) > 0:
                output_path = DATA_DIR / "sentiment" / "moby_analysis.csv"
                if output_path.exists():
                    existing = pd.read_csv(output_path)
                    df = pd.concat([existing, df], ignore_index=True)
                    df = df.drop_duplicates(subset=["date", "ticker"], keep="last")
                df.to_csv(output_path, index=False)
                print("  Parsed {} Moby stock analyses".format(len(df)))
                result["analyses"] = len(df)
    except Exception as e:
        print("  Moby analysis parsing failed: {}".format(e))
        result["analysis_error"] = str(e)[:100]

    return result


# ── Step 4: Portfolio Runs (existing, wrapped) ───────────────────────────────

def step_portfolio_runs() -> dict:
    """Run all portfolios — stop-loss, regime, signals, rebalance. ~4-5 min."""
    config = load_config("config/config.yaml")

    price_df = pd.read_csv(DATA_DIR / "prices_daily.csv", parse_dates=["date"])
    latest_prices = price_df.sort_values("date").groupby("ticker").last()["close"].to_dict()
    benchmark_df = pd.read_csv(DATA_DIR / "benchmark_daily.csv", parse_dates=["date"])

    # Market regime
    spy_return = get_spy_20d_return(price_df)
    sgx_return = get_ticker_20d_return("ES3.SI", price_df)
    vix_level = get_vix_level()
    vix_scale = compute_vix_scale(vix_level)

    mrf = config.backtest.market_regime_filter
    if mrf and (mrf.get("enabled") if isinstance(mrf, dict) else getattr(mrf, "enabled", False)):
        _get = mrf.get if isinstance(mrf, dict) else lambda k, d: getattr(mrf, k, d)
        threshold_exit = _get("threshold_exit", -0.08)
        threshold_reduce = _get("threshold_reduce", -0.05)
        reduce_scale = _get("reduce_scale", 0.30)
    else:
        threshold_exit, threshold_reduce, reduce_scale = -0.08, -0.05, 0.30

    regime, regime_scale, regime_trigger = compute_dual_regime(
        spy_return, sgx_return, threshold_reduce, threshold_exit, reduce_scale)
    regime_scale *= vix_scale

    print("  SPY 20d: {:+.2%} | ES3.SI 20d: {:+.2%} | VIX: {:.1f} ({:.0%})".format(
        spy_return, sgx_return, vix_level, vix_scale))
    print("  REGIME: {} (scale: {:.0%})".format(regime.upper(), regime_scale))

    sector_map = load_sector_map()
    industry_map = load_industry_map()
    wl_config = load_watchlist_config()

    # Per-watchlist macro filters
    wl_overrides = config.features.watchlist_overrides or {}

    results = {}
    for p in PORTFOLIOS:
        wl = p["watchlist"]
        focused = is_sector_focused(wl, wl_config)
        print("\n  --- {} {} ---".format(wl, "[sector-focused]" if focused else "[diversified]"))

        # Per-watchlist regime adjustments (multiplicative with global regime)
        wl_regime_scale = regime_scale
        wl_override = wl_overrides.get(wl, {})
        dxy_cfg = wl_override.get("dxy_regime_filter", {})
        if dxy_cfg.get("enabled"):
            dxy_ticker = dxy_cfg.get("ticker", "UUP")
            uup_return = get_ticker_20d_return(dxy_ticker, price_df)
            _dget = dxy_cfg.get if isinstance(dxy_cfg, dict) else lambda k, d: getattr(dxy_cfg, k, d)
            dxy_scale = compute_dxy_scale(
                uup_return,
                threshold_headwind=_dget("threshold_headwind", 0.02),
                headwind_scale=_dget("headwind_scale", 0.25),
                mild_headwind_scale=_dget("mild_headwind_scale", 0.60),
            )
            wl_regime_scale *= dxy_scale
            print("    {} 20d: {:+.2%} -> DXY scale: {:.0%} (combined: {:.0%})".format(
                dxy_ticker, uup_return, dxy_scale, wl_regime_scale))

        try:
            execute_portfolio(wl, config, latest_prices, spy_return, regime, wl_regime_scale,
                              sector_map, industry_map, wl_config, price_df, benchmark_df)
            results[wl] = "OK"
        except Exception as e:
            print("  {} FAILED: {}".format(wl, e))
            notify_slack(":x: Portfolio {} failed: {}".format(wl, str(e)[:150]))
            results[wl] = "FAILED: {}".format(str(e)[:100])

    # Write summary
    write_daily_summary(config, latest_prices, spy_return, regime, regime_scale, [],
                        sgx_return=sgx_return, vix_level=vix_level)

    # Slack summary
    _send_slack_summary(latest_prices, spy_return, regime, regime_scale, 0)

    ok = sum(1 for v in results.values() if v == "OK")
    failed = len(results) - ok
    return {"ok": ok, "failed": failed, "regime": regime, "scale": regime_scale,
            "spy_return": spy_return, "sgx_return": sgx_return, "vix": vix_level}


# ── Step 5: Personal Alerts ──────────────────────────────────────────────────

def step_personal_alerts() -> dict:
    """Check anthony_watchlist for P&L thresholds and signal contradictions. ~2s."""
    alerts = []
    personal_dir = PROJECT_ROOT / "config" / "personal"
    if not personal_dir.exists():
        print("  No personal config dir — skipping")
        return {"alerts": []}

    # Load personal config
    personal_cfg = None
    try:
        for yaml_file in personal_dir.glob("*.yaml"):
            with open(yaml_file) as f:
                cfg = yaml.safe_load(f)
            if cfg and "portfolio" in cfg:
                personal_cfg = cfg
                break
    except Exception as e:
        print("  Could not load personal config: {}".format(e))
        return {"alerts": []}

    if not personal_cfg:
        print("  No personal portfolio config found")
        return {"alerts": []}

    alert_cfg = personal_cfg.get("alerts", {})
    all_positions = (
        personal_cfg["portfolio"].get("us_positions", [])
        + personal_cfg["portfolio"].get("sgx_positions", [])
    )
    holdings = {pos["ticker"]: pos for pos in all_positions}

    # Load latest prices
    try:
        price_df = pd.read_csv(DATA_DIR / "prices_daily.csv", parse_dates=["date"])
        latest_prices = price_df.sort_values("date").groupby("ticker").last()["close"].to_dict()
    except Exception:
        latest_prices = {}

    # Check P&L thresholds
    pnl_cfg = alert_cfg.get("pnl_thresholds", {})
    loss_pct = pnl_cfg.get("loss_pct", -10.0)
    gain_pct = pnl_cfg.get("gain_pct", 20.0)

    for ticker, pos in holdings.items():
        current = latest_prices.get(ticker)
        if current is None or pos.get("cost_basis", 0) <= 0:
            continue
        pnl_pct = ((current - pos["cost_basis"]) / pos["cost_basis"]) * 100
        if pnl_pct <= loss_pct:
            alerts.append("P&L: {} down {:.1f}% (${:.2f} -> ${:.2f})".format(
                ticker, pnl_pct, pos["cost_basis"], current))
        elif pnl_pct >= gain_pct:
            alerts.append("P&L: {} up {:.1f}% (${:.2f} -> ${:.2f})".format(
                ticker, pnl_pct, pos["cost_basis"], current))

    # Check signal contradictions from anthony_watchlist DB
    db_path = DATA_DIR / "paper_trading_anthony_watchlist.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            today = datetime.now().strftime("%Y-%m-%d")
            signals = conn.execute(
                "SELECT ticker, action, prediction, rank FROM signals WHERE date = ?", (today,)
            ).fetchall()
            conn.close()

            for sig in signals:
                ticker = sig["ticker"]
                if ticker in holdings and sig["action"] == "SELL":
                    alerts.append("CONFLICT: Model says SELL {} (rank={}, score={:.3f}) — you hold it".format(
                        ticker, sig["rank"], sig["prediction"]))
        except Exception:
            pass

    if alerts:
        alert_msg = "PERSONAL ALERTS:\n" + "\n".join("  " + a for a in alerts)
        print("  " + alert_msg.replace("\n", "\n  "))
        notify_slack(":bell: " + alert_msg)

    return {"alerts": alerts}


# ── Step 6: Forward Predictions ──────────────────────────────────────────────

def step_forward_predictions() -> dict:
    """Log today's signals to forward_journal.db. ~5s."""
    from scripts.forward_journal import ForwardJournalDB

    journal = ForwardJournalDB()
    today = datetime.now().strftime("%Y-%m-%d")
    total_logged = 0

    price_df = pd.read_csv(DATA_DIR / "prices_daily.csv")
    if "date" in price_df.columns:
        price_df["date"] = pd.to_datetime(price_df["date"], format="mixed")

    for p in PORTFOLIOS:
        wl = p["watchlist"]
        db_path = DATA_DIR / "paper_trading_{}.db".format(wl)
        if not db_path.exists():
            continue

        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            signals = conn.execute(
                "SELECT ticker, prediction, rank, percentile, action FROM signals WHERE date = ? ORDER BY rank",
                (today,)
            ).fetchall()

            if not signals:
                # Try most recent date
                signals = conn.execute(
                    "SELECT ticker, prediction, rank, percentile, action, date "
                    "FROM signals ORDER BY date DESC LIMIT 50"
                ).fetchall()
                if signals:
                    latest_date = signals[0]["date"]
                    signals = [s for s in signals if s["date"] == latest_date]
            conn.close()

            predictions_batch = []
            for sig in signals:
                ticker = sig["ticker"]
                ticker_prices = price_df[price_df["ticker"] == ticker] if "ticker" in price_df.columns else pd.DataFrame()
                entry_price = float(ticker_prices.iloc[-1]["close"]) if len(ticker_prices) > 0 and "close" in ticker_prices.columns else 0.0

                for horizon in PREDICTION_HORIZONS:
                    predictions_batch.append({
                        "prediction_date": today,
                        "ticker": ticker,
                        "watchlist": wl,
                        "horizon_days": horizon,
                        "predicted_score": float(sig["prediction"]),
                        "predicted_rank": int(sig["rank"]),
                        "predicted_action": sig["action"],
                        "entry_price": entry_price,
                    })

            logged = journal.log_predictions_batch(predictions_batch)
            total_logged += logged
            if logged > 0:
                print("  {}: {} predictions ({} signals x {} horizons)".format(
                    wl, logged, len(signals), len(PREDICTION_HORIZONS)))

        except Exception as e:
            print("  {} journal failed: {}".format(wl, e))

    journal.close()
    print("  Total logged: {}".format(total_logged))
    return {"logged": total_logged}


# ── Step 7: Evaluate Matured Predictions ─────────────────────────────────────

def step_evaluate_predictions() -> dict:
    """Evaluate matured 5-day and 63-day predictions. ~3s."""
    from scripts.forward_journal import ForwardJournalDB

    journal = ForwardJournalDB()
    today = datetime.now().strftime("%Y-%m-%d")
    total_evaluated = 0

    try:
        price_df = pd.read_csv(DATA_DIR / "prices_daily.csv")
        if "date" in price_df.columns:
            price_df["date"] = pd.to_datetime(price_df["date"], format="mixed")
    except Exception as e:
        print("  Cannot load prices: {}".format(e))
        journal.close()
        return {"evaluated": 0, "error": str(e)}

    for horizon in PREDICTION_HORIZONS:
        matured = journal.get_matured_predictions(horizon_days=horizon, as_of_date=today)
        if not matured:
            continue

        print("  Evaluating {} matured {}-day predictions".format(len(matured), horizon))

        for pred in matured:
            ticker = pred["ticker"]
            entry_price = pred["entry_price"]
            if entry_price <= 0:
                continue

            ticker_prices = price_df[price_df["ticker"] == ticker] if "ticker" in price_df.columns else pd.DataFrame()
            if len(ticker_prices) == 0 or "close" not in ticker_prices.columns:
                continue

            actual_price = float(ticker_prices.iloc[-1]["close"])
            actual_return = (actual_price - entry_price) / entry_price

            if pred["predicted_action"] == "BUY":
                hit = 1 if actual_return > 0 else 0
            elif pred["predicted_action"] == "SELL":
                hit = 1 if actual_return < 0 else 0
            else:
                hit = 0

            journal.record_evaluation(pred["id"], actual_price, actual_return, hit)
            total_evaluated += 1

    # Log hit rates
    for horizon in PREDICTION_HORIZONS:
        rates = journal.get_hit_rates(horizon_days=horizon, last_n_days=30)
        if rates["total"] > 0:
            print("  {}d hit rate (30d): {:.1%} ({}/{})".format(
                horizon, rates["hit_rate"], rates["hits"], rates["total"]))

    journal.close()
    return {"evaluated": total_evaluated}


# ── Step 8: Generate Recommendations ─────────────────────────────────────────

def step_recommendations() -> dict:
    """Generate recommendations from top signals across all portfolios. ~2s."""
    today = datetime.now().strftime("%Y-%m-%d")
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Load prices and sectors
    price_map = {}
    try:
        pdf = pd.read_csv(DATA_DIR / "prices_daily.csv")
        if "date" in pdf.columns:
            pdf["date"] = pd.to_datetime(pdf["date"], format="mixed")
        for ticker in pdf["ticker"].unique():
            tdf = pdf[pdf["ticker"] == ticker].sort_values("date")
            if len(tdf) > 0 and "close" in tdf.columns:
                price_map[ticker] = float(tdf.iloc[-1]["close"])
    except Exception:
        pass

    sector_map = load_sector_map()

    # Collect top signals from all watchlists
    all_signals = []
    for p in PORTFOLIOS:
        wl = p["watchlist"]
        db_path = DATA_DIR / "paper_trading_{}.db".format(wl)
        if not db_path.exists():
            continue
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT ticker, prediction, rank, percentile, action, date "
                "FROM signals ORDER BY date DESC LIMIT 50"
            ).fetchall()
            conn.close()
            if not rows:
                continue
            latest_date = rows[0]["date"]
            for r in rows:
                if r["date"] != latest_date:
                    break
                all_signals.append({
                    "ticker": r["ticker"], "prediction": r["prediction"],
                    "rank": r["rank"], "action": r["action"], "watchlist": wl,
                })
        except Exception:
            pass

    if not all_signals:
        print("  No signals — skipping")
        return {"count": 0}

    # Deduplicate: keep highest prediction per ticker
    best = {}
    for sig in all_signals:
        t = sig["ticker"]
        if t not in best or sig["prediction"] > best[t]["prediction"]:
            best[t] = sig

    sorted_sigs = sorted(best.values(), key=lambda s: s["prediction"], reverse=True)
    top_buys = [s for s in sorted_sigs if s["action"] == "BUY"][:10]
    top_sells = [s for s in sorted_sigs if s["action"] == "SELL"][:5]
    recs = top_buys + top_sells

    if not recs:
        print("  No actionable signals")
        return {"count": 0}

    # Write to analysis.db
    analysis_db = DATA_DIR / "analysis.db"
    conn = sqlite3.connect(str(analysis_db))
    inserted = 0

    for sig in recs:
        ticker = sig["ticker"]
        price = price_map.get(ticker, 0.0)
        sector = sector_map.get(ticker, "Unknown")
        action = sig["action"]
        score = sig["prediction"]
        confidence = 0.8 if (score > 0.8 or score < 0.2) else 0.7 if (score > 0.7 or score < 0.3) else 0.5

        if action == "BUY" and price > 0:
            target_price, stop_loss = round(price * 1.10, 2), round(price * 0.95, 2)
        elif action == "SELL" and price > 0:
            target_price, stop_loss = round(price * 0.90, 2), round(price * 1.05, 2)
        else:
            target_price, stop_loss = None, None

        reason = "Score: {:.3f}, Rank #{} in {}".format(score, sig["rank"], sig["watchlist"].replace("_", " "))

        existing = conn.execute(
            "SELECT 1 FROM recommendations WHERE ticker = ? AND recommendation_date = ?",
            (ticker, today)
        ).fetchone()
        if existing:
            continue
        try:
            conn.execute(
                """INSERT INTO recommendations
                   (run_id, ticker, action, recommendation_date, reason,
                    confidence, target_price, stop_loss, time_horizon,
                    current_price, score, sector, source, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, ticker, action, today, reason, confidence, target_price,
                 stop_loss, "medium", price, score, sector, "daily_fast", datetime.now().isoformat()),
            )
            inserted += 1
        except Exception:
            pass

    conn.commit()

    # Update tracking for past recommendations
    updated = 0
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, ticker, action, current_price, target_price, stop_loss FROM recommendations WHERE current_price > 0"
        ).fetchall()
        now = datetime.now().isoformat()
        for row in rows:
            current_price = price_map.get(row["ticker"])
            if current_price is None or row["current_price"] <= 0:
                continue
            actual_return = (current_price / row["current_price"]) - 1.0
            if row["action"] == "SELL":
                actual_return = -actual_return
            hit_target = 1 if (row["target_price"] and row["action"] == "BUY" and current_price >= row["target_price"]) else 0
            hit_stop = 1 if (row["stop_loss"] and row["action"] == "BUY" and current_price <= row["stop_loss"]) else 0
            if row["action"] == "SELL":
                hit_target = 1 if (row["target_price"] and current_price <= row["target_price"]) else 0
                hit_stop = 1 if (row["stop_loss"] and current_price >= row["stop_loss"]) else 0
            conn.execute(
                "UPDATE recommendations SET actual_return=?, hit_target=?, hit_stop_loss=?, tracking_updated_at=? WHERE id=?",
                (round(actual_return, 6), hit_target, hit_stop, now, row["id"]))
            updated += 1
        conn.commit()
    except Exception:
        pass
    conn.close()

    print("  Generated {} recommendations ({} BUY, {} SELL), updated {} tracking".format(
        inserted, len(top_buys), len(top_sells), updated))
    return {"count": inserted, "buys": len(top_buys), "sells": len(top_sells), "tracking_updated": updated}


# ── Step Timer Table ─────────────────────────────────────────────────────────

def print_step_table(step_results: list, total_elapsed: float):
    """Print and return formatted step timer table."""
    lines = []
    lines.append("+" + "-" * 30 + "+" + "-" * 10 + "+" + "-" * 10 + "+")
    lines.append("| {:28s} | {:8s} | {:8s} |".format("Step", "Time", "Status"))
    lines.append("+" + "-" * 30 + "+" + "-" * 10 + "+" + "-" * 10 + "+")
    for r in step_results:
        t = "{:.1f}s".format(r["time_s"])
        lines.append("| {:28s} | {:>8s} | {:8s} |".format(
            "{}. {}".format(r["step"], r["name"])[:28], t, r["status"]))
    lines.append("+" + "-" * 30 + "+" + "-" * 10 + "+" + "-" * 10 + "+")
    lines.append("| {:28s} | {:>8s} |          |".format("Total", "{:.0f}s".format(total_elapsed)))
    lines.append("+" + "-" * 30 + "+" + "-" * 10 + "+" + "-" * 10 + "+")
    table = "\n".join(lines)
    print("\n" + table)

    # Write to daily_summary.txt
    summary_path = LOG_DIR / "daily_summary.txt"
    try:
        with open(summary_path, "a") as f:
            f.write("\n\n--- Step Timer ({}) ---\n".format(datetime.now().strftime("%Y-%m-%d %H:%M")))
            f.write(table + "\n")
    except Exception:
        pass

    return table


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    start = time.time()
    print("=" * 60)
    print("DAILY RUN — {} (8-step pipeline)".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print("=" * 60)

    # Slack monitoring
    try:
        from utils.slack_notifier import SlackNotifier
        notifier = SlackNotifier(job_name="daily-fast")
        thread_ts = notifier.started("Daily run starting (8-step pipeline)")
    except Exception:
        notifier, thread_ts = None, None

    step_results = []

    # ── 8-step pipeline (each step isolated) ─────────────────────────────
    run_step(1, "Price Refresh", step_price_refresh, step_results)
    run_step(2, "Sentiment Check", step_sentiment_check, step_results)
    run_step(3, "Moby Parsing", step_moby_parsing, step_results)
    run_step(4, "Portfolio Runs", step_portfolio_runs, step_results)
    run_step(5, "Personal Alerts", step_personal_alerts, step_results)
    run_step(6, "Forward Predictions", step_forward_predictions, step_results)
    run_step(7, "Evaluate Predictions", step_evaluate_predictions, step_results)
    run_step(8, "Recommendations", step_recommendations, step_results)

    # ── Summary ──────────────────────────────────────────────────────────
    total_elapsed = time.time() - start
    table = print_step_table(step_results, total_elapsed)
    print("COMPLETE in {:.0f}s".format(total_elapsed))

    # Check for timeout
    if total_elapsed > OVERALL_TIMEOUT_S:
        notify_slack(":rotating_light: Daily run exceeded {:.0f}s timeout ({:.0f}s)".format(
            OVERALL_TIMEOUT_S, total_elapsed))

    # Send step table to Slack
    failed_steps = [r for r in step_results if r["status"] == "FAILED"]
    if failed_steps:
        notify_slack(":warning: Daily run completed with {} failed step(s):\n```\n{}\n```".format(
            len(failed_steps), table))
    else:
        notify_slack(":white_check_mark: Daily run complete ({:.0f}s)\n```\n{}\n```".format(
            total_elapsed, table))

    # Slack notifier wrap-up
    if notifier:
        metrics = {
            "steps": "{}/8 OK".format(sum(1 for r in step_results if r["status"] == "OK")),
            "duration_s": "{:.0f}".format(total_elapsed),
        }
        if failed_steps:
            notifier.completed(thread_ts=thread_ts, metrics=metrics,
                               warnings=[r["error"] for r in failed_steps if "error" in r])
        else:
            notifier.completed(thread_ts=thread_ts, metrics=metrics)


def _send_slack_summary(latest_prices: dict, spy_return: float, regime: str, regime_scale: float, elapsed: float):
    """Send summaries to both Slack channels."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Build portfolio summary lines
    portfolio_lines = []
    total_value = 0
    sg_blue_chips_detail = ""
    for p in PORTFOLIOS:
        wl = p["watchlist"]
        db_path = DATA_DIR / "paper_trading_{}.db".format(wl)
        if not db_path.exists():
            continue
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            snap = conn.execute(
                "SELECT portfolio_value, daily_return, cumulative_return FROM daily_snapshots ORDER BY date DESC LIMIT 1"
            ).fetchone()
            pos_count = conn.execute("SELECT COUNT(*) FROM positions WHERE is_active = 1").fetchone()[0]
            if snap:
                pv, dr, cr = snap["portfolio_value"], snap["daily_return"], snap["cumulative_return"]
                total_value += pv
                primary = " *" if p.get("primary") else ""
                portfolio_lines.append("  {:20s} ${:>9,.0f} {:+.2%} (total {:+.2%}) {}pos{}".format(
                    wl, pv, dr, cr, pos_count, primary))

                # Detailed sg_blue_chips for sentiment channel
                if wl == "sg_blue_chips":
                    positions = conn.execute(
                        "SELECT ticker, shares, entry_price FROM positions WHERE is_active = 1"
                    ).fetchall()
                    pos_lines = []
                    for pos in positions:
                        tk = pos["ticker"]
                        price = latest_prices.get(tk, pos["entry_price"])
                        ret = (price / pos["entry_price"]) - 1 if pos["entry_price"] > 0 else 0
                        pos_lines.append("    {} {:.0f}sh @${:.2f} now ${:.2f} ({:+.1%})".format(
                            tk, pos["shares"], pos["entry_price"], price, ret))
                    sg_blue_chips_detail = "\n".join(pos_lines)
            conn.close()
        except Exception:
            pass

    # --- Stock Planner channel ---
    stock_msg = (
        ":chart_with_upwards_trend: *Daily Run* — {}\n"
        "Regime: {} (SPY 20d: {:+.2%}, scale {:.0%})\n"
        "```\n{}\n```\n"
        "Total: ${:,.0f} | {:.0f}s"
    ).format(
        today, regime.upper(), spy_return, regime_scale,
        "\n".join(portfolio_lines), total_value, elapsed,
    )
    notify_slack(stock_msg, "stock-planner")

    # --- SentimentPulse channel ---
    sentiment_msg = (
        ":robot_face: *Stock Planner Signal* — {}\n"
        "sg_blue_chips (PRIMARY forward test):\n"
        "```\n{}\n```\n"
        "Portfolio: ${:,.0f} | Regime: {} ({:.0%} invested)\n"
        "Target Sharpe: 0.619 | Review: 2026-04-25"
    ).format(
        today,
        sg_blue_chips_detail or "  no positions",
        total_value, regime.upper(), regime_scale,
    )
    notify_slack(sentiment_msg, "sentiment")


if __name__ == "__main__":
    main()
