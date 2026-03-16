#!/usr/bin/env python3
"""Paper trading pipeline for midterm-stock-planner.

Executes trades on Alpaca paper-trading account based on ML-generated signals.
Falls back to local simulation when Alpaca keys are not configured.

Runs daily after market close to:
1. Refresh price data (append latest day)
2. Retrain model on updated data
3. Generate buy/sell signals for the next period
4. Execute orders via Alpaca paper trading (or simulate locally)
5. Track cumulative P&L in local database + Alpaca account
6. Log everything to database + JSON

Usage:
    # Run daily signal generation and execute via Alpaca
    python scripts/paper_trading.py run

    # Run with specific watchlist
    python scripts/paper_trading.py run --watchlist tech_giants

    # Force local simulation (no Alpaca orders)
    python scripts/paper_trading.py run --local

    # View current positions (from Alpaca or local DB)
    python scripts/paper_trading.py status

    # View Alpaca account details
    python scripts/paper_trading.py account

    # View trade history
    python scripts/paper_trading.py history --last 30

    # Refresh data only (no signal generation)
    python scripts/paper_trading.py refresh

    # Close all Alpaca positions (liquidate)
    python scripts/paper_trading.py liquidate

    # Setup cron job (runs daily at 5:30 PM ET)
    python scripts/paper_trading.py setup-cron
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config.config import load_config, load_ticker_config, BacktestConfig, ModelConfig, bars_per_day_from_interval
from src.features.engineering import (
    compute_all_features_extended,
    make_training_dataset,
    get_feature_columns,
)
from src.data.loader import load_price_data, load_benchmark_data, load_fundamental_data
from src.backtest.rolling import run_walk_forward_backtest, _construct_portfolio

from src.backtest.trigger_backtest import TriggerConfig, run_trigger_backtest

# Alpaca broker (optional — falls back to local simulation)
try:
    from src.trading.alpaca_broker import AlpacaBroker, ALPACA_TRADING_AVAILABLE
except ImportError:
    ALPACA_TRADING_AVAILABLE = False
    AlpacaBroker = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PaperPosition:
    """A single stock position in the paper portfolio."""
    ticker: str
    weight: float       # Target weight (0-1)
    shares: float       # Simulated shares (fractional OK)
    entry_price: float  # Price at entry
    entry_date: str
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0


@dataclass
class PaperTrade:
    """A simulated trade execution."""
    date: str
    ticker: str
    action: str         # "BUY", "SELL", "REBALANCE"
    shares: float
    price: float
    value: float        # shares * price
    cost: float         # transaction cost
    weight_before: float
    weight_after: float


@dataclass
class DailySnapshot:
    """End-of-day portfolio snapshot."""
    date: str
    portfolio_value: float
    cash: float
    invested: float
    daily_return: float
    cumulative_return: float
    benchmark_return: float
    benchmark_cumulative: float
    positions: List[Dict[str, Any]]
    signals: List[Dict[str, Any]]  # Top-ranked stocks with scores
    trades: List[Dict[str, Any]]
    metrics: Dict[str, Any]


# ---------------------------------------------------------------------------
# Paper Trading Database
# ---------------------------------------------------------------------------

class PaperTradingDB:
    """SQLite persistence for paper trading state."""

    def __init__(self, db_path: str = "data/paper_trading.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS portfolio_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                cash REAL NOT NULL DEFAULT 100000.0,
                initial_value REAL NOT NULL DEFAULT 100000.0,
                last_updated TEXT,
                config_json TEXT
            );

            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                shares REAL NOT NULL,
                entry_price REAL NOT NULL,
                entry_date TEXT NOT NULL,
                weight REAL NOT NULL DEFAULT 0.0,
                is_active INTEGER NOT NULL DEFAULT 1,
                exit_date TEXT,
                exit_price REAL,
                realized_pnl REAL,
                UNIQUE(ticker, entry_date, is_active)
            );

            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                shares REAL NOT NULL,
                price REAL NOT NULL,
                value REAL NOT NULL,
                cost REAL NOT NULL DEFAULT 0.0,
                weight_before REAL DEFAULT 0.0,
                weight_after REAL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS daily_snapshots (
                date TEXT PRIMARY KEY,
                portfolio_value REAL NOT NULL,
                cash REAL NOT NULL,
                invested REAL NOT NULL,
                daily_return REAL,
                cumulative_return REAL,
                benchmark_return REAL,
                benchmark_cumulative REAL,
                positions_json TEXT,
                signals_json TEXT,
                trades_json TEXT,
                metrics_json TEXT
            );

            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                ticker TEXT NOT NULL,
                prediction REAL NOT NULL,
                rank INTEGER NOT NULL,
                percentile REAL,
                action TEXT,
                features_json TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(date);
            CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(date);
            CREATE INDEX IF NOT EXISTS idx_positions_active ON positions(is_active);

            -- Accuracy calibration: track signal accuracy over time
            CREATE TABLE IF NOT EXISTS accuracy_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_date TEXT NOT NULL,
                eval_date TEXT NOT NULL,
                ticker TEXT NOT NULL,
                predicted_rank INTEGER,
                predicted_score REAL,
                actual_return REAL,
                hit INTEGER,  -- 1 if BUY signal had positive return
                UNIQUE(signal_date, ticker)
            );

            -- Risk events: log when risk rules triggered
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                event_type TEXT NOT NULL,  -- 'drawdown_close', 'daily_loss_halt', 'concentration_cap'
                details TEXT,
                portfolio_value REAL,
                threshold REAL
            );

            CREATE INDEX IF NOT EXISTS idx_accuracy_signal_date ON accuracy_log(signal_date);
            CREATE INDEX IF NOT EXISTS idx_risk_events_date ON risk_events(date);
        """)

        # Initialize portfolio state if not exists
        cursor.execute("INSERT OR IGNORE INTO portfolio_state (id, cash, initial_value) VALUES (1, 100000.0, 100000.0)")
        self.conn.commit()

    def get_state(self) -> Dict[str, Any]:
        row = self.conn.execute("SELECT * FROM portfolio_state WHERE id = 1").fetchone()
        return dict(row) if row else {"cash": 100000.0, "initial_value": 100000.0}

    def update_cash(self, cash: float):
        self.conn.execute("UPDATE portfolio_state SET cash = ?, last_updated = ? WHERE id = 1",
                          (cash, datetime.now().isoformat()))
        self.conn.commit()

    def get_active_positions(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM positions WHERE is_active = 1").fetchall()
        return [dict(r) for r in rows]

    def upsert_position(self, ticker: str, shares: float, entry_price: float,
                        entry_date: str, weight: float):
        """Insert or update an active position."""
        existing = self.conn.execute(
            "SELECT id FROM positions WHERE ticker = ? AND is_active = 1", (ticker,)
        ).fetchone()

        if existing:
            self.conn.execute(
                "UPDATE positions SET shares = ?, weight = ? WHERE id = ?",
                (shares, weight, existing["id"])
            )
        else:
            self.conn.execute(
                "INSERT INTO positions (ticker, shares, entry_price, entry_date, weight) "
                "VALUES (?, ?, ?, ?, ?)",
                (ticker, shares, entry_price, entry_date, weight)
            )
        self.conn.commit()

    def close_position(self, ticker: str, exit_date: str, exit_price: float, realized_pnl: float):
        self.conn.execute(
            "UPDATE positions SET is_active = 0, exit_date = ?, exit_price = ?, realized_pnl = ? "
            "WHERE ticker = ? AND is_active = 1",
            (exit_date, exit_price, realized_pnl, ticker)
        )
        self.conn.commit()

    def record_trade(self, trade: PaperTrade):
        self.conn.execute(
            "INSERT INTO trades (date, ticker, action, shares, price, value, cost, weight_before, weight_after) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (trade.date, trade.ticker, trade.action, trade.shares, trade.price,
             trade.value, trade.cost, trade.weight_before, trade.weight_after)
        )
        self.conn.commit()

    def record_signals(self, date: str, signals_df: pd.DataFrame):
        for _, row in signals_df.iterrows():
            self.conn.execute(
                "INSERT INTO signals (date, ticker, prediction, rank, percentile, action) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (date, row["ticker"], row["prediction"], row.get("rank", 0),
                 row.get("percentile", 0), row.get("action", "HOLD"))
            )
        self.conn.commit()

    def record_snapshot(self, snap: DailySnapshot):
        self.conn.execute(
            "INSERT OR REPLACE INTO daily_snapshots "
            "(date, portfolio_value, cash, invested, daily_return, cumulative_return, "
            "benchmark_return, benchmark_cumulative, positions_json, signals_json, trades_json, metrics_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (snap.date, snap.portfolio_value, snap.cash, snap.invested,
             snap.daily_return, snap.cumulative_return,
             snap.benchmark_return, snap.benchmark_cumulative,
             json.dumps(snap.positions), json.dumps(snap.signals),
             json.dumps(snap.trades), json.dumps(snap.metrics))
        )
        self.conn.commit()

    def get_snapshots(self, last_n: int = 30) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM daily_snapshots ORDER BY date DESC LIMIT ?", (last_n,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_trades(self, last_n: int = 50) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM trades ORDER BY date DESC, id DESC LIMIT ?", (last_n,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_latest_snapshot_date(self) -> Optional[str]:
        row = self.conn.execute(
            "SELECT date FROM daily_snapshots ORDER BY date DESC LIMIT 1"
        ).fetchone()
        return row["date"] if row else None

    # --- Accuracy Calibration ---

    def record_accuracy(self, signal_date: str, eval_date: str, ticker: str,
                        predicted_rank: int, predicted_score: float,
                        actual_return: float):
        hit = 1 if actual_return > 0 else 0
        self.conn.execute(
            "INSERT OR REPLACE INTO accuracy_log "
            "(signal_date, eval_date, ticker, predicted_rank, predicted_score, actual_return, hit) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (signal_date, eval_date, ticker, predicted_rank, predicted_score, actual_return, hit)
        )
        self.conn.commit()

    def get_calibration_factor(self, min_samples: int = 30) -> float:
        """Return calibration factor: historical_hit_rate / baseline (0.5).

        Factor > 1.0 means model is accurate → increase sizing.
        Factor < 1.0 means model is inaccurate → decrease sizing.
        Returns 1.0 if insufficient samples.
        Clamped to [0.5, 1.5] to prevent extreme adjustments.
        """
        row = self.conn.execute(
            "SELECT COUNT(*) as n, AVG(hit) as hit_rate FROM accuracy_log"
        ).fetchone()
        if not row or row["n"] < min_samples:
            return 1.0
        hit_rate = row["hit_rate"] or 0.5
        factor = hit_rate / 0.5  # baseline: random = 50% hit rate
        return max(0.5, min(1.5, factor))

    def get_accuracy_stats(self) -> Dict[str, Any]:
        """Get accuracy statistics for display."""
        row = self.conn.execute(
            "SELECT COUNT(*) as n, AVG(hit) as hit_rate, AVG(actual_return) as avg_return "
            "FROM accuracy_log"
        ).fetchone()
        if not row or row["n"] == 0:
            return {"samples": 0, "hit_rate": None, "avg_return": None, "calibration_factor": 1.0}
        return {
            "samples": row["n"],
            "hit_rate": row["hit_rate"],
            "avg_return": row["avg_return"],
            "calibration_factor": self.get_calibration_factor(),
        }

    # --- Risk Events ---

    def record_risk_event(self, date: str, event_type: str, details: str,
                          portfolio_value: float, threshold: float):
        self.conn.execute(
            "INSERT INTO risk_events (date, event_type, details, portfolio_value, threshold) "
            "VALUES (?, ?, ?, ?, ?)",
            (date, event_type, details, portfolio_value, threshold)
        )
        self.conn.commit()

    def get_peak_equity(self) -> float:
        """Get highest portfolio value from snapshots."""
        row = self.conn.execute(
            "SELECT MAX(portfolio_value) as peak FROM daily_snapshots"
        ).fetchone()
        return row["peak"] if row and row["peak"] else 0.0


# ---------------------------------------------------------------------------
# Risk Manager
# ---------------------------------------------------------------------------

class RiskManager:
    """Enforces risk rules on the paper trading portfolio.

    Rules:
    1. Drawdown-from-peak close: if portfolio retraces >drawdown_pct from peak
       (when profit > min_profit_pct), liquidate all positions.
    2. Daily loss limit: if today's P&L < daily_loss_limit, halt trading.
    3. Max position concentration: cap any single position at max_weight.
    """

    def __init__(self,
                 drawdown_pct: float = 0.30,
                 min_profit_pct: float = 0.05,
                 daily_loss_limit: float = -0.05,
                 max_position_weight: float = 0.25):
        self.drawdown_pct = drawdown_pct
        self.min_profit_pct = min_profit_pct
        self.daily_loss_limit = daily_loss_limit
        self.max_position_weight = max_position_weight

    def check_drawdown(self, current_value: float, peak_value: float,
                       initial_value: float) -> Optional[str]:
        """Check if drawdown-from-peak exceeds threshold.

        Returns risk event description or None if OK.
        """
        if peak_value <= 0 or initial_value <= 0:
            return None
        profit_pct = (peak_value / initial_value) - 1
        if profit_pct < self.min_profit_pct:
            return None  # Only enforce after minimum profit reached
        drawdown = (peak_value - current_value) / peak_value
        if drawdown >= self.drawdown_pct:
            return (f"Drawdown {drawdown:.1%} from peak ${peak_value:,.0f} exceeds "
                    f"{self.drawdown_pct:.0%} threshold (profit was {profit_pct:.1%})")
        return None

    def check_daily_loss(self, daily_return: float) -> Optional[str]:
        """Check if daily loss exceeds limit.

        Returns risk event description or None if OK.
        """
        if daily_return <= self.daily_loss_limit:
            return (f"Daily loss {daily_return:.2%} exceeds "
                    f"{self.daily_loss_limit:.0%} limit — halting trades")
        return None

    def apply_concentration_cap(self, target_weights: Dict[str, float]) -> Dict[str, float]:
        """Cap any single position at max_weight, redistribute excess equally."""
        capped = {}
        excess = 0.0
        uncapped_count = 0
        for ticker, w in target_weights.items():
            if w > self.max_position_weight:
                excess += w - self.max_position_weight
                capped[ticker] = self.max_position_weight
            else:
                capped[ticker] = w
                uncapped_count += 1

        # Redistribute excess to uncapped positions
        if excess > 0 and uncapped_count > 0:
            bonus = excess / uncapped_count
            for ticker in capped:
                if capped[ticker] < self.max_position_weight:
                    capped[ticker] = min(capped[ticker] + bonus, self.max_position_weight)

        return capped


# ---------------------------------------------------------------------------
# Ensemble Signal Generator
# ---------------------------------------------------------------------------

class EnsembleSignalGenerator:
    """Combines ML walk-forward rankings with per-ticker trigger backtest signals.

    Stocks that rank high in BOTH signal sources get a conviction boost.
    Stocks where signals disagree get a conviction penalty.

    Weights:
        ml_weight (default 0.7): Weight for ML walk-forward ranking signal
        trigger_weight (default 0.3): Weight for trigger backtest signal
    """

    def __init__(self, ml_weight: float = 0.7, trigger_weight: float = 0.3):
        self.ml_weight = ml_weight
        self.trigger_weight = trigger_weight

    def generate_trigger_signals(self, price_df: pd.DataFrame,
                                  tickers: List[str]) -> Dict[str, float]:
        """Run trigger backtest for each ticker using per-ticker optimized params.

        Returns dict of ticker -> trigger_score (Sharpe ratio from recent backtest).
        Tickers without per-ticker configs get score 0.0 (neutral).
        """
        trigger_scores = {}

        for ticker in tickers:
            ticker_cfg = load_ticker_config(ticker)
            if not ticker_cfg or "trigger" not in ticker_cfg:
                trigger_scores[ticker] = 0.0
                continue

            t = ticker_cfg["trigger"]
            config = TriggerConfig(
                signal_type="combined",
                combined_use_rsi=True,
                combined_use_macd=True,
                combined_use_bollinger=False,
                macd_fast=int(t.get("macd_fast", 12)),
                macd_slow=int(t.get("macd_slow", 26)),
                macd_signal=int(t.get("macd_signal", 9)),
                rsi_period=int(t.get("rsi_period", 14)),
                rsi_overbought=float(t.get("rsi_overbought", 70)),
                rsi_oversold=float(t.get("rsi_oversold", 30)),
            )

            sub = price_df[price_df["ticker"] == ticker].copy()
            if len(sub) < 100:
                trigger_scores[ticker] = 0.0
                continue

            try:
                res = run_trigger_backtest(sub, config)
                sharpe = res.metrics.get("sharpe_ratio", 0.0) or 0.0
                trigger_scores[ticker] = sharpe
            except Exception:
                trigger_scores[ticker] = 0.0

        return trigger_scores

    def combine_signals(self, ml_signals: pd.DataFrame,
                        trigger_scores: Dict[str, float]) -> pd.DataFrame:
        """Combine ML and trigger signals into an ensemble score.

        ML signal: prediction score (cross-sectional ranking)
        Trigger signal: per-ticker Sharpe from optimized params

        Ensemble score = ml_weight * normalized_ml + trigger_weight * normalized_trigger
        """
        signals = ml_signals.copy()

        # Normalize ML scores to [0, 1]
        ml_scores = signals["prediction"].values
        ml_min, ml_max = ml_scores.min(), ml_scores.max()
        ml_range = ml_max - ml_min
        if ml_range > 0:
            signals["ml_norm"] = (ml_scores - ml_min) / ml_range
        else:
            signals["ml_norm"] = 0.5

        # Normalize trigger scores to [0, 1]
        trigger_vals = signals["ticker"].map(trigger_scores).fillna(0.0).values
        t_min, t_max = trigger_vals.min(), trigger_vals.max()
        t_range = t_max - t_min
        if t_range > 0:
            signals["trigger_norm"] = (trigger_vals - t_min) / t_range
        else:
            signals["trigger_norm"] = 0.5

        # Ensemble score
        signals["ensemble_score"] = (
            self.ml_weight * signals["ml_norm"] +
            self.trigger_weight * signals["trigger_norm"]
        )

        # Re-rank by ensemble score
        signals = signals.sort_values("ensemble_score", ascending=False).reset_index(drop=True)
        signals["rank"] = range(1, len(signals) + 1)

        # Re-tag actions based on new ranking
        top_n = ml_signals[ml_signals["action"] == "BUY"].shape[0] or 5
        signals["action"] = "SELL"
        signals.iloc[:top_n, signals.columns.get_loc("action")] = "BUY"

        # Use ensemble_score as the prediction for downstream sizing
        signals["prediction"] = signals["ensemble_score"]

        return signals


# ---------------------------------------------------------------------------
# Paper Trading Engine
# ---------------------------------------------------------------------------

class PaperTradingEngine:
    """Core engine for paper trading — executes via Alpaca or local simulation."""

    def __init__(self, config_path: str = "config/config.yaml",
                 watchlist: Optional[str] = None,
                 initial_capital: float = 100000.0,
                 force_local: bool = False):
        self.config = load_config(config_path)
        self.watchlist = watchlist
        self.initial_capital = initial_capital
        self.db = PaperTradingDB()
        self.transaction_cost = self.config.backtest.transaction_cost
        self.force_local = force_local
        self.risk_manager = RiskManager(
            drawdown_pct=0.30,
            min_profit_pct=0.05,
            daily_loss_limit=-0.05,
            max_position_weight=getattr(self.config.backtest, "max_position_weight", 0.25),
        )
        self.ensemble = EnsembleSignalGenerator(ml_weight=0.7, trigger_weight=0.3)

        # Try to connect to Alpaca paper trading
        self.broker: Optional[AlpacaBroker] = None  # type: ignore[assignment]
        if not force_local and ALPACA_TRADING_AVAILABLE:
            try:
                self.broker = AlpacaBroker(paper=True)
                acct = self.broker.get_account()
                print(f"Connected to Alpaca paper trading (equity: ${float(acct.get('equity', 0)):,.2f})")
            except Exception as e:
                print(f"Alpaca not available ({e}), using local simulation")
                self.broker = None

        if self.broker is None:
            print("Mode: local simulation (no real orders)")

        # Initialize state if first run
        state = self.db.get_state()
        if state.get("last_updated") is None:
            self.db.update_cash(initial_capital)
            self.db.conn.execute(
                "UPDATE portfolio_state SET initial_value = ? WHERE id = 1",
                (initial_capital,)
            )
            self.db.conn.commit()

    def refresh_data(self) -> bool:
        """Download latest price data."""
        print("Refreshing price data...")
        try:
            from scripts.download_prices import PriceDownloader
        except ImportError:
            # Try running as subprocess
            import subprocess
            cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "download_prices.py")]
            if self.watchlist:
                cmd += ["--watchlist", self.watchlist]
            cmd += ["--interval", "1d", "--start",
                    (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
            if result.returncode != 0:
                print(f"Warning: Data refresh failed: {result.stderr[:200]}")
                return False
            print("Data refreshed successfully.")
            return True

        downloader = PriceDownloader(
            output_path=str(PROJECT_ROOT / self.config.data.price_data_path_daily)
        )
        # Get tickers
        tickers = self._get_universe()
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        df = downloader.download(
            tickers=tickers, start_date=start_date, end_date=end_date,
            interval="1d", merge_existing=True
        )
        if df is not None and len(df) > 0:
            downloader.save(df)
            print(f"Data refreshed: {len(df)} rows appended.")
            return True
        print("Warning: No new data downloaded.")
        return False

    def _get_universe(self) -> List[str]:
        """Get ticker universe from watchlist or config."""
        if self.watchlist:
            import yaml
            wl_path = PROJECT_ROOT / "config" / "watchlists.yaml"
            with open(wl_path) as f:
                watchlists = yaml.safe_load(f)
            if self.watchlist in watchlists.get("watchlists", watchlists):
                wl = watchlists.get("watchlists", watchlists)[self.watchlist]
                return wl.get("symbols", wl.get("tickers", []))
        # Fall back to all tickers in price data
        price_path = PROJECT_ROOT / self.config.data.price_data_path_daily
        if price_path.exists():
            df = pd.read_csv(price_path, usecols=["ticker"])
            return sorted(df["ticker"].unique().tolist())
        return []

    def _load_data(self) -> Tuple[pd.DataFrame, List[str], pd.DataFrame, pd.DataFrame]:
        """Load and prepare data for model training."""
        daily_price_path = PROJECT_ROOT / self.config.data.price_data_path_daily
        daily_bench_path = PROJECT_ROOT / getattr(self.config.data, "benchmark_data_path_daily",
                                                   "data/benchmark_daily.csv")

        price_df = pd.read_csv(daily_price_path, parse_dates=["date"])
        benchmark_df = pd.read_csv(daily_bench_path, parse_dates=["date"])

        # Filter by watchlist
        universe = self._get_universe()
        if universe:
            price_df = price_df[price_df["ticker"].isin(universe)]

        # Load fundamentals if available
        fundamental_df = None
        if self.config.data.fundamental_data_path:
            fund_path = PROJECT_ROOT / self.config.data.fundamental_data_path
            if fund_path.exists():
                fundamental_df = pd.read_csv(fund_path, parse_dates=["date"])

        bpd = bars_per_day_from_interval("1d")
        feature_cfg = self.config.features

        print(f"Computing features for {price_df['ticker'].nunique()} tickers...")
        feature_df = compute_all_features_extended(
            price_df=price_df,
            fundamental_df=fundamental_df,
            benchmark_df=benchmark_df,
            include_technical=getattr(feature_cfg, 'include_technical', True),
            include_rsi=getattr(feature_cfg, 'include_rsi', False),
            include_obv=getattr(feature_cfg, 'include_obv', False),
            include_momentum=getattr(feature_cfg, 'include_momentum', False),
            include_mean_reversion=getattr(feature_cfg, 'include_mean_reversion', False),
            bars_per_day=bpd,
            rsi_period=feature_cfg.rsi_period,
            macd_fast=feature_cfg.macd_fast,
            macd_slow=feature_cfg.macd_slow,
            macd_signal=feature_cfg.macd_signal,
        )

        training_data = make_training_dataset(
            feature_df=feature_df,
            benchmark_df=benchmark_df,
            horizon_days=feature_cfg.horizon_days,
            target_col=self.config.model.target_col,
            bars_per_day=bpd,
        )

        feature_cols = get_feature_columns(training_data)
        return training_data, feature_cols, price_df, benchmark_df

    def generate_signals(self) -> pd.DataFrame:
        """Run walk-forward backtest, combine with trigger signals (ensemble)."""
        training_data, feature_cols, price_df, benchmark_df = self._load_data()

        print(f"Running walk-forward backtest ({len(feature_cols)} features)...")
        t0 = time.time()
        results = run_walk_forward_backtest(
            training_data=training_data,
            benchmark_data=benchmark_df,
            price_data=price_df,
            feature_cols=feature_cols,
            config=self.config.backtest,
            model_config=self.config.model,
            verbose=False,
        )
        elapsed = time.time() - t0
        print(f"Backtest complete in {elapsed:.0f}s. Sharpe={results.metrics.get('sharpe_ratio', 0):.3f}")

        # Extract ML signals
        if results.final_scores is not None and len(results.final_scores) > 0:
            ml_signals = results.final_scores[["ticker", "prediction", "rank", "percentile"]].copy()
            ml_signals = ml_signals.sort_values("prediction", ascending=False)

            # Tag actions
            top_n = self.config.backtest.top_n or 5
            ml_signals["action"] = "HOLD"
            ml_signals.iloc[:top_n, ml_signals.columns.get_loc("action")] = "BUY"
            ml_signals.iloc[top_n:, ml_signals.columns.get_loc("action")] = "SELL"

            # Ensemble: combine ML + trigger backtest signals
            tickers = ml_signals["ticker"].tolist()
            print("Running trigger backtest for ensemble signals...")
            trigger_scores = self.ensemble.generate_trigger_signals(price_df, tickers)
            n_with_config = sum(1 for v in trigger_scores.values() if v != 0.0)
            print(f"  Trigger signals: {n_with_config}/{len(tickers)} tickers have per-ticker configs")

            signals = self.ensemble.combine_signals(ml_signals, trigger_scores)
            return signals
        else:
            print("Warning: No signals generated (empty final_scores).")
            return pd.DataFrame(columns=["ticker", "prediction", "rank", "percentile", "action"])

    def _compute_target_weights(self, buy_signals: pd.DataFrame, top_n: int) -> Dict[str, float]:
        """Compute target weights using confidence-based sizing + calibration + risk caps.

        Instead of equal-weight, allocates proportionally to prediction scores.
        Applies calibration factor from historical accuracy tracking.
        Applies concentration cap from risk manager.
        """
        top = buy_signals.head(top_n).copy()
        if len(top) == 0:
            return {}

        scores = top["prediction"].values.astype(float)

        # Normalize scores to weights (proportional to prediction score)
        # Shift scores so minimum is > 0 (scores can be negative)
        score_min = scores.min()
        shifted = scores - score_min + 0.01  # ensure all positive
        raw_weights = shifted / shifted.sum()

        # Apply calibration factor (scales total exposure, not individual ratios)
        calibration = self.db.get_calibration_factor()
        scaled_weights = raw_weights * calibration

        # Re-normalize to sum to 1.0
        total = scaled_weights.sum()
        if total > 0:
            scaled_weights = scaled_weights / total

        target_weights = dict(zip(top["ticker"].tolist(), scaled_weights.tolist()))

        # Apply concentration cap
        target_weights = self.risk_manager.apply_concentration_cap(target_weights)

        return target_weights

    def execute_signals(self, signals: pd.DataFrame, price_df: Optional[pd.DataFrame] = None):
        """Execute signals — via Alpaca paper trading or local simulation."""
        if self.broker is not None:
            return self._execute_via_alpaca(signals, price_df)
        return self._execute_local(signals, price_df)

    def _execute_via_alpaca(self, signals: pd.DataFrame, price_df: Optional[pd.DataFrame] = None):
        """Execute signals by placing real orders on Alpaca paper account."""
        today = datetime.now().strftime("%Y-%m-%d")
        state = self.db.get_state()
        initial_value = state["initial_value"]

        # Target portfolio from signals
        buy_signals = signals[signals["action"] == "BUY"].copy()
        if len(buy_signals) == 0:
            print("No BUY signals. Holding current positions.")
            return

        top_n = self.config.backtest.top_n or 5
        target_weights = self._compute_target_weights(buy_signals, top_n)

        print(f"\nTarget weights: {target_weights}")

        # Execute via Alpaca rebalance
        alpaca_trades = self.broker.rebalance_portfolio(target_weights)

        # Log trades to local DB for dashboard tracking
        trades = []
        for at in alpaca_trades:
            action = at.get("action", "unknown")
            symbol = at.get("symbol", "?")
            order = at.get("order", {})
            notional = at.get("notional", 0)
            error = at.get("error")

            if error:
                print(f"  WARNING {action} {symbol}: {error}")
                continue

            filled_qty = float(order.get("filled_qty", 0) or 0)
            filled_price = float(order.get("filled_avg_price", 0) or 0)
            value = notional or (filled_qty * filled_price)

            trade_action = "SELL" if "sell" in action else "BUY"
            trade = PaperTrade(
                date=today, ticker=symbol, action=trade_action,
                shares=filled_qty, price=filled_price, value=abs(value),
                cost=0,  # Alpaca paper has no commissions
                weight_before=0, weight_after=target_weights.get(symbol, 0)
            )
            trades.append(trade)
            self.db.record_trade(trade)
            print(f"  {trade_action} {symbol}: ${abs(value):,.2f} "
                  f"(weight: {target_weights.get(symbol, 0):.1%})")

        # Sync Alpaca state to local DB
        self._sync_alpaca_state(signals, trades, today, initial_value)

    def _sync_alpaca_state(self, signals, trades, today, initial_value):
        """Sync Alpaca account/positions to local DB for dashboard display."""
        acct = self.broker.get_account()
        alpaca_positions = self.broker.get_positions()

        cash = float(acct.get("cash", 0))
        equity = float(acct.get("equity", 0))
        invested = equity - cash

        # Update local DB with Alpaca state
        self.db.update_cash(cash)

        # Close all local active positions and re-create from Alpaca
        self.db.conn.execute("DELETE FROM positions WHERE is_active = 1")
        for pos in alpaca_positions:
            symbol = pos.get("symbol", "")
            qty = float(pos.get("qty", 0))
            avg_entry = float(pos.get("avg_entry_price", 0))
            market_value = float(pos.get("market_value", 0))
            weight = market_value / equity if equity > 0 else 0
            self.db.upsert_position(symbol, qty, avg_entry, today, weight)
        self.db.conn.commit()

        # Record signals
        self.db.record_signals(today, signals)

        # Benchmark return (SPY)
        bench_path = PROJECT_ROOT / getattr(self.config.data, "benchmark_data_path_daily",
                                             "data/benchmark_daily.csv")
        bench_df = pd.read_csv(bench_path, parse_dates=["date"])
        bench_prices = bench_df.sort_values("date")
        if len(bench_prices) >= 2:
            bench_start = bench_prices.iloc[0]["close"]
            bench_end = bench_prices.iloc[-1]["close"]
            benchmark_cumulative = (bench_end / bench_start) - 1
        else:
            benchmark_cumulative = 0.0

        prev = self.db.get_snapshots(last_n=1)
        if prev:
            prev_value = prev[0]["portfolio_value"]
            daily_pct = (equity / prev_value) - 1 if prev_value > 0 else 0
            bench_daily = benchmark_cumulative - (prev[0].get("benchmark_cumulative", 0) or 0)
        else:
            daily_pct = 0
            bench_daily = 0

        positions_data = self.db.get_active_positions()
        snapshot = DailySnapshot(
            date=today,
            portfolio_value=equity,
            cash=cash,
            invested=invested,
            daily_return=daily_pct,
            cumulative_return=(equity / initial_value) - 1,
            benchmark_return=bench_daily,
            benchmark_cumulative=benchmark_cumulative,
            positions=[{
                "ticker": p.get("symbol", p.get("ticker", "")),
                "shares": float(p.get("qty", p.get("shares", 0))),
                "weight": float(p.get("market_value", 0)) / equity if equity > 0 else 0,
                "entry_price": float(p.get("avg_entry_price", p.get("entry_price", 0))),
                "current_price": float(p.get("current_price", 0)),
                "pnl": float(p.get("unrealized_pl", 0)),
            } for p in alpaca_positions],
            signals=signals.head(10).to_dict("records"),
            trades=[asdict(t) for t in trades],
            metrics={
                "sharpe_ratio": None,
                "total_trades": len(trades),
                "total_cost": 0,
                "broker": "alpaca",
                "account_equity": equity,
            }
        )
        self.db.record_snapshot(snapshot)

        print(f"\nAlpaca Portfolio: ${equity:,.2f} (return: {(equity / initial_value - 1):+.2%})")
        print(f"Cash: ${cash:,.2f} | Invested: ${invested:,.2f}")
        print(f"Positions: {len(alpaca_positions)} | Trades today: {len(trades)}")

    def _execute_local(self, signals: pd.DataFrame, price_df: Optional[pd.DataFrame] = None):
        """Local simulation execution (no Alpaca — original behavior)."""
        today = datetime.now().strftime("%Y-%m-%d")
        state = self.db.get_state()
        cash = state["cash"]
        initial_value = state["initial_value"]

        # Get current prices
        if price_df is None:
            price_path = PROJECT_ROOT / self.config.data.price_data_path_daily
            price_df = pd.read_csv(price_path, parse_dates=["date"])

        latest_prices = (
            price_df.sort_values("date")
            .groupby("ticker")
            .last()["close"]
            .to_dict()
        )

        # Current positions
        current_positions = self.db.get_active_positions()
        current_tickers = {p["ticker"]: p for p in current_positions}

        # Calculate current portfolio value
        invested = sum(
            p["shares"] * latest_prices.get(p["ticker"], p["entry_price"])
            for p in current_positions
        )
        portfolio_value = cash + invested

        # Target portfolio from signals
        buy_signals = signals[signals["action"] == "BUY"].copy()
        if len(buy_signals) == 0:
            print("No BUY signals. Holding current positions.")
            return

        top_n = self.config.backtest.top_n or 5
        target_weights = self._compute_target_weights(buy_signals, top_n)

        trades = []

        # SELL positions not in target
        for ticker, pos in current_tickers.items():
            if ticker not in target_weights:
                price = latest_prices.get(ticker, pos["entry_price"])
                value = pos["shares"] * price
                cost = value * self.transaction_cost
                realized_pnl = (price - pos["entry_price"]) * pos["shares"] - cost

                trade = PaperTrade(
                    date=today, ticker=ticker, action="SELL",
                    shares=pos["shares"], price=price, value=value, cost=cost,
                    weight_before=pos["weight"], weight_after=0.0
                )
                trades.append(trade)
                self.db.record_trade(trade)
                self.db.close_position(ticker, today, price, realized_pnl)
                cash += value - cost
                print(f"  SELL {ticker}: {pos['shares']:.1f} shares @ ${price:.2f} "
                      f"(PnL: ${realized_pnl:+.2f})")

        # BUY / REBALANCE target positions
        for ticker, weight in target_weights.items():
            price = latest_prices.get(ticker)
            if price is None or price <= 0:
                continue

            target_value = portfolio_value * weight
            current_value = 0
            current_shares = 0
            if ticker in current_tickers:
                pos = current_tickers[ticker]
                current_shares = pos["shares"]
                current_value = current_shares * price

            delta_value = target_value - current_value
            if abs(delta_value) < 50:  # Skip tiny rebalances
                continue

            delta_shares = delta_value / price
            cost = abs(delta_value) * self.transaction_cost

            if delta_shares > 0:
                action = "BUY"
            else:
                action = "REBALANCE"

            new_shares = current_shares + delta_shares
            trade = PaperTrade(
                date=today, ticker=ticker, action=action,
                shares=abs(delta_shares), price=price, value=abs(delta_value),
                cost=cost,
                weight_before=current_tickers.get(ticker, {}).get("weight", 0),
                weight_after=weight
            )
            trades.append(trade)
            self.db.record_trade(trade)

            if new_shares > 0:
                entry_price = price if ticker not in current_tickers else current_tickers[ticker]["entry_price"]
                self.db.upsert_position(ticker, new_shares, entry_price, today, weight)
            cash -= delta_value + cost
            print(f"  {action} {ticker}: {abs(delta_shares):.1f} shares @ ${price:.2f} "
                  f"(weight: {weight:.1%})")

        self.db.update_cash(cash)

        # Record signals
        self.db.record_signals(today, signals)

        # Record daily snapshot
        positions = self.db.get_active_positions()
        invested = sum(
            p["shares"] * latest_prices.get(p["ticker"], p["entry_price"])
            for p in positions
        )
        portfolio_value = cash + invested
        daily_return = (portfolio_value / initial_value) - 1

        # Benchmark return (SPY)
        bench_path = PROJECT_ROOT / getattr(self.config.data, "benchmark_data_path_daily",
                                             "data/benchmark_daily.csv")
        bench_df = pd.read_csv(bench_path, parse_dates=["date"])
        bench_prices = bench_df.sort_values("date")
        if len(bench_prices) >= 2:
            bench_start = bench_prices.iloc[0]["close"]
            bench_end = bench_prices.iloc[-1]["close"]
            benchmark_cumulative = (bench_end / bench_start) - 1
        else:
            benchmark_cumulative = 0.0

        prev = self.db.get_snapshots(last_n=1)
        if prev:
            prev_value = prev[0]["portfolio_value"]
            daily_pct = (portfolio_value / prev_value) - 1 if prev_value > 0 else 0
            prev_bench = prev[0].get("benchmark_cumulative", 0)
            bench_daily = benchmark_cumulative - prev_bench
        else:
            daily_pct = 0
            bench_daily = 0

        snapshot = DailySnapshot(
            date=today,
            portfolio_value=portfolio_value,
            cash=cash,
            invested=invested,
            daily_return=daily_pct,
            cumulative_return=(portfolio_value / initial_value) - 1,
            benchmark_return=bench_daily,
            benchmark_cumulative=benchmark_cumulative,
            positions=[{
                "ticker": p["ticker"],
                "shares": p["shares"],
                "weight": p["weight"],
                "entry_price": p["entry_price"],
                "current_price": latest_prices.get(p["ticker"], 0),
                "pnl": (latest_prices.get(p["ticker"], 0) - p["entry_price"]) * p["shares"]
            } for p in positions],
            signals=signals.head(10).to_dict("records"),
            trades=[asdict(t) for t in trades],
            metrics={
                "sharpe_ratio": None,
                "total_trades": len(trades),
                "total_cost": sum(t.cost for t in trades),
                "broker": "local",
            }
        )
        self.db.record_snapshot(snapshot)

        print(f"\nPortfolio: ${portfolio_value:,.2f} (return: {daily_return:+.2%})")
        print(f"Cash: ${cash:,.2f} | Invested: ${invested:,.2f}")
        print(f"Positions: {len(positions)} | Trades today: {len(trades)}")

    def _evaluate_past_signals(self):
        """Evaluate accuracy of signals from ~5 trading days ago against actual returns."""
        today = datetime.now().strftime("%Y-%m-%d")
        eval_window_days = 5  # Check signals from 5 days ago

        # Find signals from ~5 days ago that haven't been evaluated
        rows = self.db.conn.execute(
            "SELECT DISTINCT date FROM signals "
            "WHERE date NOT IN (SELECT DISTINCT signal_date FROM accuracy_log) "
            "AND date <= date(?, '-' || ? || ' days') "
            "ORDER BY date DESC LIMIT 5",
            (today, eval_window_days)
        ).fetchall()

        if not rows:
            return

        # Load daily prices for evaluation
        price_path = PROJECT_ROOT / self.config.data.price_data_path_daily
        price_df = pd.read_csv(price_path, parse_dates=["date"])

        for row in rows:
            signal_date = row["date"]
            signals = self.db.conn.execute(
                "SELECT ticker, prediction, rank, action FROM signals WHERE date = ?",
                (signal_date,)
            ).fetchall()

            for sig in signals:
                ticker = sig["ticker"]
                # Get price on signal date and current
                ticker_prices = price_df[price_df["ticker"] == ticker].sort_values("date")
                sig_dt = pd.to_datetime(signal_date)
                after_signal = ticker_prices[ticker_prices["date"] > sig_dt]

                if len(after_signal) < eval_window_days:
                    continue

                price_at_signal = ticker_prices[ticker_prices["date"] <= sig_dt]
                if len(price_at_signal) == 0:
                    continue

                entry_price = price_at_signal.iloc[-1]["close"]
                eval_price = after_signal.iloc[eval_window_days - 1]["close"]
                actual_return = (eval_price / entry_price) - 1

                self.db.record_accuracy(
                    signal_date=signal_date,
                    eval_date=today,
                    ticker=ticker,
                    predicted_rank=sig["rank"],
                    predicted_score=sig["prediction"],
                    actual_return=actual_return,
                )

        stats = self.db.get_accuracy_stats()
        if stats["samples"] > 0:
            print(f"  Accuracy: {stats['samples']} samples, "
                  f"hit_rate={stats['hit_rate']:.1%}, "
                  f"calibration={stats['calibration_factor']:.2f}")

    def _check_risk_rules(self) -> Optional[str]:
        """Run risk checks before trading. Returns halt reason or None."""
        today = datetime.now().strftime("%Y-%m-%d")
        state = self.db.get_state()
        initial_value = state["initial_value"]

        # Get current portfolio value
        if self.broker:
            acct = self.broker.get_account()
            current_value = float(acct.get("equity", 0))
        else:
            snapshots = self.db.get_snapshots(last_n=1)
            current_value = snapshots[0]["portfolio_value"] if snapshots else initial_value

        peak_value = self.db.get_peak_equity()
        if peak_value == 0:
            peak_value = initial_value

        # Check drawdown from peak
        dd_event = self.risk_manager.check_drawdown(current_value, peak_value, initial_value)
        if dd_event:
            self.db.record_risk_event(today, "drawdown_close", dd_event,
                                      current_value, self.risk_manager.drawdown_pct)
            print(f"  RISK: {dd_event}")
            if self.broker:
                print("  Liquidating all positions...")
                self.broker.liquidate_all()
            return dd_event

        # Check daily loss
        snapshots = self.db.get_snapshots(last_n=1)
        if snapshots:
            daily_return = snapshots[0].get("daily_return", 0) or 0
            dl_event = self.risk_manager.check_daily_loss(daily_return)
            if dl_event:
                self.db.record_risk_event(today, "daily_loss_halt", dl_event,
                                          current_value, self.risk_manager.daily_loss_limit)
                print(f"  RISK: {dl_event}")
                return dl_event

        return None

    def run_daily(self, skip_refresh: bool = False):
        """Full daily paper trading cycle."""
        print(f"{'='*60}")
        print(f"Paper Trading - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*60}")

        # 1. Refresh data
        if not skip_refresh:
            self.refresh_data()

        # 2. Evaluate past signal accuracy (calibration loop)
        print("\nCalibration check...")
        self._evaluate_past_signals()

        # 3. Risk checks
        print("Risk checks...")
        halt_reason = self._check_risk_rules()
        if halt_reason:
            print(f"\nTrading halted: {halt_reason}")
            print("Done (no trades).")
            return

        # 4. Generate signals
        print("\nGenerating signals...")
        signals = self.generate_signals()

        if len(signals) == 0:
            print("No signals generated. Skipping execution.")
            return

        print(f"\nTop signals:")
        for _, row in signals.head(10).iterrows():
            print(f"  {row['action']:4s} {row['ticker']:6s}  "
                  f"score={row['prediction']:.4f}  rank={row['rank']}")

        # 5. Execute
        print("\nExecuting trades...")
        self.execute_signals(signals)

        print(f"\nDone.")

    def show_status(self):
        """Display current portfolio status — from Alpaca or local DB."""
        state = self.db.get_state()
        initial = state["initial_value"]

        print(f"\n{'='*60}")

        if self.broker is not None:
            # Live Alpaca data
            acct = self.broker.get_account()
            alpaca_positions = self.broker.get_positions()

            equity = float(acct.get("equity", 0))
            cash = float(acct.get("cash", 0))
            invested = equity - cash
            buying_power = float(acct.get("buying_power", 0))

            print(f"Alpaca Paper Trading Portfolio")
            print(f"{'='*60}")
            print(f"Portfolio Value: ${equity:,.2f}")
            print(f"Cash:           ${cash:,.2f}")
            print(f"Invested:       ${invested:,.2f}")
            print(f"Buying Power:   ${buying_power:,.2f}")
            print(f"Total Return:   {(equity/initial - 1):+.2%}")
            print(f"Initial Value:  ${initial:,.2f}")
            print(f"Account Status: {acct.get('status', 'unknown')}")

            if alpaca_positions:
                print(f"\nPositions ({len(alpaca_positions)}):")
                print(f"{'Ticker':8s} {'Shares':>8s} {'Entry':>8s} {'Current':>8s} {'PnL':>10s} {'Weight':>8s}")
                print("-" * 60)
                for p in sorted(alpaca_positions, key=lambda x: -abs(float(x.get("market_value", 0)))):
                    sym = p.get("symbol", "?")
                    qty = float(p.get("qty", 0))
                    avg_entry = float(p.get("avg_entry_price", 0))
                    current = float(p.get("current_price", 0))
                    pnl = float(p.get("unrealized_pl", 0))
                    mv = float(p.get("market_value", 0))
                    weight = mv / equity if equity > 0 else 0
                    print(f"{sym:8s} {qty:8.1f} ${avg_entry:7.2f} "
                          f"${current:7.2f} ${pnl:+9.2f} {weight:7.1%}")
            else:
                print("\nNo active positions.")
        else:
            # Local DB
            positions = self.db.get_active_positions()
            price_path = PROJECT_ROOT / self.config.data.price_data_path_daily
            price_df = pd.read_csv(price_path, parse_dates=["date"])
            latest_prices = (
                price_df.sort_values("date")
                .groupby("ticker")
                .last()["close"]
                .to_dict()
            )
            cash = state["cash"]
            invested = sum(
                p["shares"] * latest_prices.get(p["ticker"], p["entry_price"])
                for p in positions
            )
            total = cash + invested

            print(f"Paper Trading Portfolio (Local Simulation)")
            print(f"{'='*60}")
            print(f"Portfolio Value: ${total:,.2f}")
            print(f"Cash:           ${cash:,.2f}")
            print(f"Invested:       ${invested:,.2f}")
            print(f"Total Return:   {(total/initial - 1):+.2%}")
            print(f"Initial Value:  ${initial:,.2f}")
            print(f"Last Updated:   {state.get('last_updated', 'Never')}")

            if positions:
                print(f"\nPositions ({len(positions)}):")
                print(f"{'Ticker':8s} {'Shares':>8s} {'Entry':>8s} {'Current':>8s} {'PnL':>10s} {'Weight':>8s}")
                print("-" * 60)
                for p in sorted(positions, key=lambda x: -x["weight"]):
                    current = latest_prices.get(p["ticker"], p["entry_price"])
                    pnl = (current - p["entry_price"]) * p["shares"]
                    print(f"{p['ticker']:8s} {p['shares']:8.1f} ${p['entry_price']:7.2f} "
                          f"${current:7.2f} ${pnl:+9.2f} {p['weight']:7.1%}")
            else:
                print("\nNo active positions.")

        # Recent performance from local DB
        snapshots = self.db.get_snapshots(last_n=10)
        if snapshots:
            print(f"\nRecent Performance:")
            print(f"{'Date':12s} {'Value':>12s} {'Daily':>8s} {'Cumulative':>12s}")
            print("-" * 50)
            for s in reversed(snapshots):
                print(f"{s['date']:12s} ${s['portfolio_value']:11,.2f} "
                      f"{s['daily_return']:+7.2%} {s['cumulative_return']:+11.2%}")

    def show_history(self, last_n: int = 30):
        """Display trade history."""
        trades = self.db.get_trades(last_n=last_n)
        if not trades:
            print("No trade history.")
            return

        print(f"\nTrade History (last {last_n}):")
        print(f"{'Date':12s} {'Action':10s} {'Ticker':8s} {'Shares':>8s} {'Price':>8s} {'Value':>10s} {'Cost':>7s}")
        print("-" * 70)
        for t in reversed(trades):
            print(f"{t['date']:12s} {t['action']:10s} {t['ticker']:8s} "
                  f"{t['shares']:8.1f} ${t['price']:7.2f} ${t['value']:9.2f} ${t['cost']:6.2f}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Paper trading pipeline (Alpaca + local simulation)")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # run
    run_parser = subparsers.add_parser("run", help="Run daily paper trading cycle")
    run_parser.add_argument("--watchlist", type=str, default="tech_giants",
                            help="Watchlist name (default: tech_giants)")
    run_parser.add_argument("--skip-refresh", action="store_true",
                            help="Skip data refresh")
    run_parser.add_argument("--capital", type=float, default=100000,
                            help="Initial capital (default: 100000)")
    run_parser.add_argument("--local", action="store_true",
                            help="Force local simulation (no Alpaca orders)")

    # status
    status_parser = subparsers.add_parser("status", help="Show portfolio status")
    status_parser.add_argument("--watchlist", type=str, default="tech_giants")
    status_parser.add_argument("--local", action="store_true")

    # account — Alpaca-only
    account_parser = subparsers.add_parser("account", help="Show Alpaca account details")

    # history
    hist_parser = subparsers.add_parser("history", help="Show trade history")
    hist_parser.add_argument("--last", type=int, default=30, help="Number of trades to show")
    hist_parser.add_argument("--watchlist", type=str, default="tech_giants")

    # refresh
    refresh_parser = subparsers.add_parser("refresh", help="Refresh price data only")
    refresh_parser.add_argument("--watchlist", type=str, default="tech_giants")

    # liquidate — Alpaca-only
    liquidate_parser = subparsers.add_parser("liquidate", help="Close all Alpaca positions")

    # setup-cron
    subparsers.add_parser("setup-cron", help="Setup daily cron job")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "run":
        engine = PaperTradingEngine(
            watchlist=args.watchlist,
            initial_capital=args.capital,
            force_local=args.local,
        )
        engine.run_daily(skip_refresh=args.skip_refresh)

    elif args.command == "status":
        engine = PaperTradingEngine(
            watchlist=args.watchlist,
            force_local=getattr(args, "local", False),
        )
        engine.show_status()

    elif args.command == "account":
        if not ALPACA_TRADING_AVAILABLE:
            print("Alpaca SDK not installed. Run: pip install alpaca-py")
            return
        try:
            broker = AlpacaBroker(paper=True)
            acct = broker.get_account()
            print(f"\n{'='*60}")
            print("Alpaca Paper Trading Account")
            print(f"{'='*60}")
            for key in ["equity", "cash", "buying_power", "portfolio_value",
                        "long_market_value", "short_market_value",
                        "status", "account_number", "currency"]:
                val = acct.get(key, "N/A")
                if isinstance(val, (int, float)):
                    print(f"  {key:25s}: ${val:,.2f}")
                else:
                    print(f"  {key:25s}: {val}")

            positions = broker.get_positions()
            print(f"\nOpen Positions: {len(positions)}")
            for p in positions:
                sym = p.get("symbol", "?")
                qty = float(p.get("qty", 0))
                pnl = float(p.get("unrealized_pl", 0))
                mv = float(p.get("market_value", 0))
                print(f"  {sym:8s} {qty:8.1f} shares  ${mv:>10,.2f}  PnL: ${pnl:+,.2f}")

            clock = broker.get_clock()
            market_status = "OPEN" if clock.get("is_open") else "CLOSED"
            print(f"\nMarket: {market_status}")
            if not clock.get("is_open"):
                print(f"  Next open: {clock.get('next_open', 'N/A')}")
        except Exception as e:
            print(f"Error connecting to Alpaca: {e}")

    elif args.command == "history":
        engine = PaperTradingEngine(watchlist=args.watchlist)
        engine.show_history(last_n=args.last)

    elif args.command == "refresh":
        engine = PaperTradingEngine(watchlist=args.watchlist)
        engine.refresh_data()

    elif args.command == "liquidate":
        if not ALPACA_TRADING_AVAILABLE:
            print("Alpaca SDK not installed. Run: pip install alpaca-py")
            return
        try:
            broker = AlpacaBroker(paper=True)
            positions = broker.get_positions()
            if not positions:
                print("No open positions to close.")
                return
            print(f"Closing {len(positions)} positions...")
            results = broker.close_all_positions()
            for r in results:
                sym = r.get("symbol", "?")
                status = r.get("status", "unknown")
                print(f"  Closed {sym}: {status}")
            print("All positions closed.")
        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "setup-cron":
        script_path = Path(__file__).resolve()
        python_path = Path(sys.executable).resolve()
        project_dir = PROJECT_ROOT.resolve()

        cron_line = (
            f"30 17 * * 1-5 cd {project_dir} && "
            f"{python_path} {script_path} run --watchlist tech_giants "
            f">> {project_dir}/logs/paper_trading.log 2>&1"
        )
        print("Add this line to your crontab (crontab -e):\n")
        print(cron_line)
        print("\nThis runs at 5:30 PM ET every weekday (M-F).")

        logs_dir = project_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        print(f"\nLogs directory: {logs_dir}")


if __name__ == "__main__":
    main()
