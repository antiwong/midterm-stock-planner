#!/usr/bin/env python3
"""
Consolidated Daily/Weekly/Monthly Orchestrator
================================================
Single entry point replacing separate cron jobs for 4 portfolios.

Modes:
    python scripts/daily_routine.py daily    # Weekdays after US market close
    python scripts/daily_routine.py weekly   # Sunday performance review
    python scripts/daily_routine.py monthly  # 1st of month maintenance

Daily routine:
    1. Shared data refresh (prices for all 4 watchlists, deduplicated)
    2. Sentiment download + scoring
    3. Moby email parsing
    4. Run 4 portfolios (moby=Alpaca, rest=local sim)
    5. Log forward predictions (5-day + 63-day horizons)
    6. Evaluate matured predictions
    7. Generate summary + notify Slack/Google Chat

Weekly routine:
    1. Weekly performance report (4 portfolios side-by-side)
    2. Portfolio drift check
    3. Forward test weekly review

Monthly routine:
    1. Download fundamentals
    2. Regression health check (IC stability)
    3. Evaluate 63-day predictions that matured

Cron (SGT timezone — Tue-Sat 6:30 AM = Mon-Fri 5:30 PM ET):
    30 6 * * 2-6 cd /path/to/project && python scripts/daily_routine.py daily >> logs/daily_routine.log 2>&1
    0 10 * * 0   cd /path/to/project && python scripts/daily_routine.py weekly >> logs/weekly_routine.log 2>&1
    0 10 1 * *   cd /path/to/project && python scripts/daily_routine.py monthly >> logs/monthly_routine.log 2>&1
"""

import argparse
import fcntl
import json
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

LOCK_DIR = PROJECT_ROOT / "logs"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PORTFOLIOS = [
    {"watchlist": "moby_picks", "local": False, "capital": 100000},
    {"watchlist": "tech_giants", "local": True, "capital": 100000},
    {"watchlist": "semiconductors", "local": True, "capital": 100000},
    {"watchlist": "precious_metals", "local": True, "capital": 100000},
    {"watchlist": "sg_reits", "local": True, "capital": 100000},
    {"watchlist": "sg_blue_chips", "local": True, "capital": 100000},
    {"watchlist": "anthony_watchlist", "local": True, "capital": 13100},  # Real portfolio ~$13.1k
    {"watchlist": "sp500", "local": True, "capital": 100000},
    {"watchlist": "clean_energy", "local": True, "capital": 100000},
    {"watchlist": "etfs", "local": True, "capital": 100000},
]

PREDICTION_HORIZONS = [5, 63]  # days

LOG_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(mode: str) -> logging.Logger:
    """Configure logging to file + stdout."""
    LOG_DIR.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    log_file = LOG_DIR / f"{mode}_routine_{date_str}.log"

    logger = logging.getLogger("daily_routine")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    fh = logging.FileHandler(str(log_file))
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_us_trading_day(date: Optional[datetime] = None) -> bool:
    """Check if the given date (or today) is a US trading day (weekday, not holiday)."""
    from pandas.tseries.holiday import USFederalHolidayCalendar
    d = date or datetime.now()
    # Convert SGT to ET (roughly -13 hours, so previous day if before ~1 PM SGT)
    # For cron at 6:30 AM SGT, the US date is the previous calendar day
    us_date = d - timedelta(hours=13)
    us_date = us_date.date() if hasattr(us_date, "date") else us_date

    us_date_ts = pd.Timestamp(us_date)
    if us_date_ts.weekday() >= 5:  # Sat=5, Sun=6
        return False

    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(start=us_date_ts - pd.Timedelta(days=1),
                            end=us_date_ts + pd.Timedelta(days=1))
    return us_date_ts not in holidays


def get_all_tickers(watchlists: List[str]) -> List[str]:
    """Get union of all tickers across given watchlists (deduplicated)."""
    import yaml
    config_path = PROJECT_ROOT / "config" / "watchlists.yaml"
    with open(config_path) as f:
        wl_config = yaml.safe_load(f)

    all_tickers = set()
    for wl_name in watchlists:
        wl = wl_config.get("watchlists", {}).get(wl_name, {})
        symbols = wl.get("symbols", [])
        all_tickers.update(str(s) for s in symbols)
    return sorted(all_tickers)


def _run_single_portfolio(p: Dict) -> Dict:
    """Run a single portfolio engine. Module-level for ProcessPoolExecutor."""
    import sqlite3
    from datetime import datetime as _dt
    wl = p["watchlist"]
    today = _dt.now().strftime("%Y-%m-%d")
    try:
        from scripts.paper_trading import PaperTradingEngine
        engine = PaperTradingEngine(
            watchlist=wl,
            initial_capital=p["capital"],
            force_local=p["local"],
        )
        engine.run_daily(skip_refresh=True)

        # Read status from DB
        db_path = DATA_DIR / f"paper_trading_{wl}.db"
        if not db_path.exists():
            return {"status": "success"}
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        snap = conn.execute(
            "SELECT portfolio_value, daily_return, cumulative_return "
            "FROM daily_snapshots ORDER BY date DESC LIMIT 1"
        ).fetchone()

        # Get today's trades (rebalancing)
        trades = conn.execute(
            "SELECT ticker, action, shares, price, value "
            "FROM trades WHERE date LIKE ? ORDER BY action, ticker",
            (f"{today}%",),
        ).fetchall()
        trades_list = [dict(t) for t in trades]

        conn.close()
        result = {"status": "success", "trades": trades_list}
        if snap:
            result["portfolio_value"] = snap["portfolio_value"]
            result["daily_return"] = snap["daily_return"]
            result["cumulative_return"] = snap["cumulative_return"]
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


def post_webhook(url: Optional[str], message: str, logger: logging.Logger):
    """Post message to a webhook URL (Slack or Google Chat)."""
    if not url:
        return
    try:
        resp = requests.post(url, json={"text": message}, timeout=15)
        if resp.status_code == 200:
            logger.info(f"Webhook notification sent ({url[:40]}...)")
        else:
            logger.warning(f"Webhook returned {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        logger.warning(f"Webhook failed: {e}")


def acquire_daily_lock(mode: str, logger: logging.Logger) -> Optional[int]:
    """Acquire a lock file to ensure the routine runs only once per day.

    Returns the file descriptor if the lock was acquired, None if already ran today.
    The lock file contains the date; if the date matches today, we skip.
    The file lock (flock) prevents concurrent runs.
    """
    LOCK_DIR.mkdir(exist_ok=True)
    lock_path = LOCK_DIR / f".{mode}_routine.lock"
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Check if already ran today
    if lock_path.exists():
        try:
            content = lock_path.read_text().strip()
            if content == today_str:
                logger.info(f"{mode} routine already ran today ({today_str}) — skipping.")
                return None
        except Exception:
            pass

    # Acquire exclusive file lock to prevent concurrent runs
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        logger.info(f"{mode} routine is already running — skipping.")
        return None

    # Double-check date after acquiring lock (race condition guard)
    try:
        content = os.read(fd, 64).decode().strip()
        if content == today_str:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            logger.info(f"{mode} routine already ran today ({today_str}) — skipping.")
            return None
    except Exception:
        pass

    return fd


def stamp_daily_lock(mode: str, fd: int):
    """Write today's date to the lock file and release it."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    lock_path = LOCK_DIR / f".{mode}_routine.lock"
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(fd, today_str.encode())
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# DailyRoutine
# ---------------------------------------------------------------------------

class DailyRoutine:
    """Orchestrates all daily, weekly, and monthly tasks."""

    def __init__(self, dry_run: bool = False, skip_sentiment: bool = False):
        self.dry_run = dry_run
        self.skip_sentiment = skip_sentiment
        self.logger = setup_logging("daily")
        self.slack_url = (os.environ.get("SLACK_WEBHOOK_URL")
                          or os.environ.get("slack_webhook"))
        self.gchat_url = (os.environ.get("GOOGLE_CHAT_WEBHOOK_URL")
                          or os.environ.get("google_chat_webhook_url"))

    # ------------------------------------------------------------------
    # DAILY
    # ------------------------------------------------------------------

    def run_daily(self) -> Dict[str, Any]:
        """Full daily routine. Returns summary dict."""
        self.logger.info("=" * 60)
        self.logger.info("DAILY ROUTINE START")
        self.logger.info("=" * 60)

        if not is_us_trading_day():
            self.logger.info("Not a US trading day — skipping.")
            self._notify(":moon: Daily routine skipped — US market closed today.")
            return {"skipped": True, "reason": "not_trading_day"}

        self._notify(":rocket: Daily routine STARTED (8 steps)")
        start_time = datetime.now()

        results: Dict[str, Any] = {}
        step_statuses: list[str] = []

        def _run_step(step_num: int, name: str, fn, **kwargs):
            """Run a step with start/complete Slack notifications."""
            self._notify(f":hourglass_flowing_sand: [{step_num}/8] {name} — starting...")
            step_start = datetime.now()
            try:
                result = fn(**kwargs) if kwargs else fn()
                elapsed_s = (datetime.now() - step_start).total_seconds()
                status_line = self._step_status(name, result)
                step_statuses.append(f"[{step_num}/8] {status_line} ({elapsed_s:.0f}s)")
                self._notify(f"{status_line} ({elapsed_s:.0f}s)")
                return result
            except Exception as e:
                elapsed_s = (datetime.now() - step_start).total_seconds()
                err_line = f":x: [{step_num}/8] {name}: FAILED — {str(e)[:150]} ({elapsed_s:.0f}s)"
                step_statuses.append(err_line)
                self._notify(err_line)
                raise

        try:
            # 1. Shared data refresh
            results["data_refresh"] = _run_step(1, "Data Refresh", self._refresh_all_data)

            # 2. Sentiment pipeline
            if self.skip_sentiment:
                self.logger.info("--- Sentiment Pipeline (SKIPPED) ---")
                results["sentiment"] = {"status": "skipped", "reason": "skip_sentiment flag"}
                step_statuses.append("[2/8] :fast_forward: Sentiment: skipped")
                self._notify(":fast_forward: [2/8] Sentiment — skipped (flag)")
            else:
                results["sentiment"] = _run_step(2, "Sentiment", self._run_sentiment_pipeline)

            # 3. Moby email parsing
            results["moby_parse"] = _run_step(3, "Moby Parsing", self._run_moby_parser)

            # 4. Portfolio runs (error-isolated)
            results["portfolios"] = _run_step(4, "Portfolio Runs", self._run_all_portfolios)

            # 5. Personal portfolio alerts
            results["personal_alerts"] = _run_step(5, "Personal Alerts", self._check_personal_portfolio_alerts, results=results)

            # 6. Forward prediction journal
            results["predictions"] = _run_step(6, "Forward Predictions", self._log_forward_predictions)

            # 7. Evaluate matured predictions
            results["evaluations"] = _run_step(7, "Evaluate Predictions", self._evaluate_matured_predictions)

            # 8. Generate recommendations
            results["recommendations"] = _run_step(8, "Recommendations", self._generate_recommendations)

            # Write daily monitoring summary
            self._write_daily_summary(results)

            # Final summary
            elapsed = datetime.now() - start_time
            summary = self._format_daily_summary(results)
            self.logger.info("\n" + summary)

            recap = "\n".join(step_statuses)
            self._notify(
                f":white_check_mark: Daily routine COMPLETED in {elapsed.seconds // 60}m {elapsed.seconds % 60}s\n\n"
                f"Step recap:\n{recap}\n\n{summary}"
            )

            self.logger.info("DAILY ROUTINE COMPLETE")
            return results

        except Exception as e:
            elapsed = datetime.now() - start_time
            recap = "\n".join(step_statuses) if step_statuses else "(failed before any step completed)"
            error_msg = (
                f":x: Daily routine FAILED after {elapsed.seconds // 60}m {elapsed.seconds % 60}s\n\n"
                f"Step recap:\n{recap}\n\nError: {e}\n\n{traceback.format_exc()[-500:]}"
            )
            self.logger.error(f"DAILY ROUTINE FAILED: {e}\n{traceback.format_exc()}")
            self._notify(error_msg)
            raise

    # ------------------------------------------------------------------
    # WEEKLY
    # ------------------------------------------------------------------

    def run_weekly(self) -> Dict[str, Any]:
        """Weekly performance review."""
        self.logger = setup_logging("weekly")
        self.logger.info("=" * 60)
        self.logger.info("WEEKLY ROUTINE START")
        self.logger.info("=" * 60)

        self._notify(":chart_with_upwards_trend: Weekly routine STARTED")
        start_time = datetime.now()

        try:
            results: Dict[str, Any] = {}
            results["weekly_report"] = self._generate_weekly_report()
            results["drift_check"] = self._check_portfolio_drift()
            results["forward_review"] = self._forward_test_weekly_review()

            elapsed = datetime.now() - start_time
            summary = self._format_weekly_summary(results)
            self.logger.info("\n" + summary)
            self._notify(f":white_check_mark: Weekly routine COMPLETED in {elapsed.seconds // 60}m {elapsed.seconds % 60}s\n\n{summary}")

            self.logger.info("WEEKLY ROUTINE COMPLETE")
            return results

        except Exception as e:
            elapsed = datetime.now() - start_time
            error_msg = f":x: Weekly routine FAILED after {elapsed.seconds // 60}m {elapsed.seconds % 60}s\n\nError: {e}\n\n{traceback.format_exc()[-500:]}"
            self.logger.error(f"WEEKLY ROUTINE FAILED: {e}\n{traceback.format_exc()}")
            self._notify(error_msg)
            raise

    # ------------------------------------------------------------------
    # MONTHLY
    # ------------------------------------------------------------------

    def run_monthly(self) -> Dict[str, Any]:
        """Monthly maintenance tasks."""
        self.logger = setup_logging("monthly")
        self.logger.info("=" * 60)
        self.logger.info("MONTHLY ROUTINE START")
        self.logger.info("=" * 60)

        self._notify(":wrench: Monthly routine STARTED")
        start_time = datetime.now()

        try:
            results: Dict[str, Any] = {}
            results["fundamentals"] = self._download_fundamentals()
            results["forward_63d"] = self._evaluate_63day_predictions()

            elapsed = datetime.now() - start_time
            summary = self._format_monthly_summary(results)
            self.logger.info("\n" + summary)
            self._notify(f":white_check_mark: Monthly routine COMPLETED in {elapsed.seconds // 60}m {elapsed.seconds % 60}s\n\n{summary}")

            self.logger.info("MONTHLY ROUTINE COMPLETE")
            return results

        except Exception as e:
            elapsed = datetime.now() - start_time
            error_msg = f":x: Monthly routine FAILED after {elapsed.seconds // 60}m {elapsed.seconds % 60}s\n\nError: {e}\n\n{traceback.format_exc()[-500:]}"
            self.logger.error(f"MONTHLY ROUTINE FAILED: {e}\n{traceback.format_exc()}")
            self._notify(error_msg)
            raise

    # ------------------------------------------------------------------
    # Data Refresh
    # ------------------------------------------------------------------

    def _download_us_yfinance(self, tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
        """Fallback: download US tickers via yfinance."""
        import yfinance as yf
        self.logger.info(f"  yfinance fallback: downloading {len(tickers)} US tickers...")
        yf_data = yf.download(
            tickers, start=start_date, end=end_date,
            group_by="ticker", auto_adjust=True, threads=True,
        )
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
        if rows:
            return pd.DataFrame(rows)
        return pd.DataFrame()

    def _refresh_all_data(self) -> Dict:
        """Download prices for union of all watchlists (deduplicated).
        Uses Alpaca (SIP → IEX fallback) for US tickers, yfinance for SGX.
        Falls back to yfinance for US if Alpaca completely fails."""
        self.logger.info("--- Data Refresh ---")
        watchlist_names = [p["watchlist"] for p in PORTFOLIOS]
        all_tickers = get_all_tickers(watchlist_names)

        # Split into US (Alpaca) and SGX (yfinance)
        sgx_tickers = [t for t in all_tickers if t.endswith(".SI")]
        us_tickers = [t for t in all_tickers if not t.endswith(".SI")]
        self.logger.info(f"Refreshing prices: {len(us_tickers)} US (Alpaca) + {len(sgx_tickers)} SGX (yfinance)")

        if self.dry_run:
            return {"status": "dry_run", "tickers": len(all_tickers)}

        output_path = DATA_DIR / "prices_daily.csv"
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        all_dfs = []
        us_rows = 0
        us_source = "none"

        # US tickers: yfinance (free, primary) → Alpaca IEX (free fallback)
        if us_tickers:
            # Try 1: yfinance (free, reliable for daily data)
            try:
                yf_df = self._download_us_yfinance(us_tickers, start_date, end_date)
                if not yf_df.empty:
                    all_dfs.append(yf_df)
                    us_rows = len(yf_df)
                    us_source = "yfinance"
                    self.logger.info(f"  yfinance: {us_rows} rows for {len(us_tickers)} US tickers")
            except Exception as e:
                self.logger.warning(f"  yfinance US download failed: {e}")

            # Try 2: Alpaca IEX feed (free tier fallback)
            if us_rows == 0:
                try:
                    from src.data.alpaca_client import AlpacaClient
                    client = AlpacaClient()
                    df = client.download(
                        tickers=us_tickers,
                        start_date=start_date,
                        end_date=end_date,
                        interval="1d",
                    )
                    if df is not None and len(df) > 0:
                        all_dfs.append(df)
                        us_rows = len(df)
                        us_source = "alpaca"
                        self.logger.info(f"  Alpaca fallback: {us_rows} rows for {len(us_tickers)} US tickers")
                except Exception as e:
                    self.logger.warning(f"  Alpaca fallback also failed: {e}")

            # Data freshness guard
            if us_rows == 0 and us_tickers:
                self.logger.error(f"CRITICAL: 0 US price rows downloaded from all sources (SIP/IEX/yfinance). "
                                  f"{len(us_tickers)} tickers will use stale data!")
                self._notify(f":rotating_light: *Data Refresh CRITICAL*: 0 US rows from ALL sources "
                             f"(Alpaca SIP, IEX, yfinance). {len(us_tickers)} tickers running on stale data.")

        # SGX tickers via yfinance
        sgx_rows = 0
        if sgx_tickers:
            try:
                sgx_df = self._download_us_yfinance(sgx_tickers, start_date, end_date)
                if not sgx_df.empty:
                    all_dfs.append(sgx_df)
                    sgx_rows = len(sgx_df)
                    self.logger.info(f"  yfinance: {sgx_rows} rows for {len(sgx_tickers)} SGX tickers")
            except Exception as e:
                self.logger.error(f"  yfinance SGX download failed: {e}")

        # Merge and save
        if all_dfs:
            new_data = pd.concat(all_dfs, ignore_index=True)
            if output_path.exists():
                existing = pd.read_csv(output_path)
                combined = pd.concat([existing, new_data], ignore_index=True).drop_duplicates(
                    subset=["date", "ticker"]
                )
                combined.to_csv(output_path, index=False)
                self.logger.info(f"Data refresh complete: {len(new_data)} new rows appended (US: {us_rows} via {us_source}, SGX: {sgx_rows})")
            else:
                new_data.to_csv(output_path, index=False)
                self.logger.info(f"Data refresh complete: {len(new_data)} rows (fresh)")
        else:
            self.logger.warning("Data refresh returned no data from any source")
            self._notify(":x: *Data Refresh FAILED*: No data from any source. All portfolios will use stale data.")

        return {
            "status": "success" if us_rows > 0 or sgx_rows > 0 else "error",
            "tickers": len(all_tickers),
            "us": len(us_tickers), "us_rows": us_rows, "us_source": us_source,
            "sgx": len(sgx_tickers), "sgx_rows": sgx_rows,
        }

    # ------------------------------------------------------------------
    # Sentiment
    # ------------------------------------------------------------------

    def _run_sentiment_pipeline(self) -> Dict:
        """Check DuckDB freshness (SentimentPulse handles crawl + scoring externally)."""
        self.logger.info("--- Sentiment Pipeline (DuckDB check) ---")
        if self.dry_run:
            return {"status": "dry_run"}

        # SentimentPulse runs on the Mac (5x/day) and syncs to Hetzner via rsync.
        # We just verify the DuckDB has fresh data — no CSV download needed.
        result = {}
        try:
            import duckdb
            db_path = DATA_DIR / "sentimentpulse.db"
            if not db_path.exists():
                self.logger.warning("sentimentpulse.db not found — sentiment unavailable")
                return {"status": "skipped", "reason": "no_duckdb"}

            conn = duckdb.connect(str(db_path), read_only=True)
            row = conn.execute(
                "SELECT MAX(date) as latest, COUNT(DISTINCT ticker) as tickers "
                "FROM sentiment_features"
            ).fetchone()
            conn.close()

            latest_date = str(row[0]) if row[0] else "none"
            ticker_count = row[1] if row[1] else 0
            self.logger.info(f"DuckDB sentiment: latest={latest_date}, tickers={ticker_count}")

            # Warn if data is stale (>1 day old)
            if row[0]:
                from datetime import date as _date
                days_old = (datetime.now().date() - row[0]).days if hasattr(row[0], 'days') else 0
                try:
                    days_old = (datetime.now().date() - pd.Timestamp(row[0]).date()).days
                except Exception:
                    days_old = 0
                if days_old > 1:
                    self.logger.warning(f"DuckDB sentiment is {days_old} days old — check rsync")

            result = {"status": "success", "latest_date": latest_date, "tickers": ticker_count}
        except Exception as e:
            self.logger.error(f"DuckDB sentiment check failed: {e}")
            result = {"status": "error", "error": str(e)}

        return result

    # ------------------------------------------------------------------
    # Moby Email Parsing
    # ------------------------------------------------------------------

    def _run_moby_parser(self) -> Dict:
        """Parse Moby emails from Gmail."""
        self.logger.info("--- Moby Email Parsing ---")
        if self.dry_run:
            return {"status": "dry_run"}

        moby_password = os.environ.get("MOBY_APP_PASSWORD", "")
        if not moby_password:
            self.logger.info("MOBY_APP_PASSWORD not set — skipping Moby parsing")
            return {"status": "skipped", "reason": "no_credentials"}

        result = {}

        # Parse emails for ticker picks
        try:
            from scripts.parse_moby_emails import MobyEmailParser
            parser = MobyEmailParser()
            picks = parser.download(days=7)
            count = len(picks) if picks is not None else 0
            self.logger.info(f"Parsed {count} Moby email picks")
            result["email_picks"] = {"status": "success", "picks": count}
        except Exception as e:
            self.logger.error(f"Moby email parsing failed: {e}")
            result["email_picks"] = {"status": "error", "error": str(e)}

        # Parse structured analysis from moby_news/ markdown
        try:
            from scripts.parse_moby_analysis import parse_all_files
            moby_dir = PROJECT_ROOT / "moby_news"
            if moby_dir.exists():
                df = parse_all_files(moby_dir)
                if len(df) > 0:
                    output_path = DATA_DIR / "sentiment" / "moby_analysis.csv"
                    # Merge with existing
                    if output_path.exists():
                        existing = pd.read_csv(output_path)
                        df = pd.concat([existing, df], ignore_index=True)
                        df = df.drop_duplicates(subset=["date", "ticker"], keep="last")
                    df.to_csv(output_path, index=False)
                    self.logger.info(f"Parsed {len(df)} Moby stock analyses")
                    result["analysis"] = {"status": "success", "stocks": len(df)}
                else:
                    result["analysis"] = {"status": "no_files"}
            else:
                result["analysis"] = {"status": "skipped", "reason": "no moby_news/ dir"}
        except Exception as e:
            self.logger.error(f"Moby analysis parsing failed: {e}")
            result["analysis"] = {"status": "error", "error": str(e)}

        return result

    # ------------------------------------------------------------------
    # Portfolio Runs
    # ------------------------------------------------------------------

    def _run_all_portfolios(self) -> Dict:
        """Run portfolio engines in parallel with error isolation."""
        from concurrent.futures import ProcessPoolExecutor, as_completed

        self.logger.info("--- Portfolio Runs (parallel) ---")

        if self.dry_run:
            return {p["watchlist"]: {"status": "dry_run"} for p in PORTFOLIOS}

        # Alpaca (non-local) must run alone to avoid API rate limits
        alpaca_portfolios = [p for p in PORTFOLIOS if not p["local"]]
        local_portfolios = [p for p in PORTFOLIOS if p["local"]]

        results = {}

        # Run Alpaca portfolios sequentially (API rate limits)
        for p in alpaca_portfolios:
            wl = p["watchlist"]
            self.logger.info(f"Running {wl} (Alpaca)...")
            try:
                result = _run_single_portfolio(p)
                results[wl] = result
                self.logger.info(f"  {wl}: {result['status']}")
            except Exception as e:
                self.logger.error(f"  {wl} FAILED: {e}")
                results[wl] = {"status": "error", "error": str(e)}

        # Run local portfolios in parallel
        if local_portfolios:
            max_workers = min(len(local_portfolios), 4)
            self.logger.info(f"Running {len(local_portfolios)} local portfolios in parallel (workers={max_workers})...")

            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                future_to_wl = {
                    executor.submit(_run_single_portfolio, p): p["watchlist"]
                    for p in local_portfolios
                }
                for future in as_completed(future_to_wl):
                    wl = future_to_wl[future]
                    try:
                        result = future.result(timeout=600)
                        results[wl] = result
                        self.logger.info(f"  {wl}: {result['status']}")
                    except Exception as e:
                        self.logger.error(f"  {wl} FAILED: {e}")
                        results[wl] = {"status": "error", "error": str(e)}

        return results

    def _get_portfolio_status(self, watchlist: str) -> Dict:
        """Read latest portfolio status from per-watchlist DB."""
        import sqlite3
        db_path = DATA_DIR / f"paper_trading_{watchlist}.db"
        if not db_path.exists():
            return {}
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            state = conn.execute("SELECT * FROM portfolio_state WHERE id = 1").fetchone()
            if state is None:
                conn.close()
                return {}
            cash = state["cash"]
            initial = state["initial_value"]

            # Get total invested value from active positions
            positions = conn.execute(
                "SELECT ticker, shares, entry_price FROM positions WHERE is_active = 1"
            ).fetchall()

            # Get latest snapshot for portfolio value
            snap = conn.execute(
                "SELECT portfolio_value, daily_return, cumulative_return "
                "FROM daily_snapshots ORDER BY date DESC LIMIT 1"
            ).fetchone()

            conn.close()

            portfolio_value = snap["portfolio_value"] if snap else initial
            daily_return = snap["daily_return"] if snap else 0.0
            cum_return = snap["cumulative_return"] if snap else 0.0

            return {
                "portfolio_value": portfolio_value,
                "cash": cash,
                "daily_return": daily_return,
                "cumulative_return": cum_return,
                "positions": len(positions),
            }
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Personal Portfolio Alerts
    # ------------------------------------------------------------------

    def _check_personal_portfolio_alerts(self, results: Dict) -> Dict:
        """Check for signal contradictions and P&L thresholds on personal portfolios."""
        import sqlite3
        alerts = []

        for p in PORTFOLIOS:
            wl = p["watchlist"]
            # Load personal config for this watchlist
            personal_dir = PROJECT_ROOT / "config" / "personal"
            if not personal_dir.exists():
                continue

            personal_cfg = None
            try:
                import yaml
                for yaml_file in personal_dir.glob("*.yaml"):
                    with open(yaml_file) as f:
                        cfg = yaml.safe_load(f)
                    if not cfg or "portfolio" not in cfg:
                        continue
                    # Collect tickers from personal config
                    p_tickers = set()
                    for pos in cfg["portfolio"].get("us_positions", []):
                        p_tickers.add(pos["ticker"])
                    for pos in cfg["portfolio"].get("sgx_positions", []):
                        p_tickers.add(pos["ticker"])
                    # Match against watchlist
                    wl_cfg_path = PROJECT_ROOT / "config" / "watchlists.yaml"
                    with open(wl_cfg_path) as f:
                        wl_cfg = yaml.safe_load(f)
                    wl_symbols = set(
                        wl_cfg.get("watchlists", {}).get(wl, {}).get("symbols", [])
                    )
                    if wl_symbols and p_tickers == wl_symbols:
                        personal_cfg = cfg
                        break
            except Exception:
                continue

            if not personal_cfg:
                continue

            alert_cfg = personal_cfg.get("alerts", {})
            all_positions = (
                personal_cfg["portfolio"].get("us_positions", [])
                + personal_cfg["portfolio"].get("sgx_positions", [])
            )
            holdings = {pos["ticker"]: pos for pos in all_positions}

            # Read today's signals from the paper trading DB
            db_path = DATA_DIR / f"paper_trading_{wl}.db"
            if not db_path.exists():
                continue

            try:
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                today = datetime.now().strftime("%Y-%m-%d")
                signals = conn.execute(
                    "SELECT ticker, action, prediction, rank FROM signals WHERE date = ?",
                    (today,)
                ).fetchall()
                conn.close()
            except Exception:
                continue

            if not signals:
                continue

            # Check signal contradictions (SELL on a stock you hold)
            if alert_cfg.get("signal_contradiction", True):
                for sig in signals:
                    ticker = sig["ticker"]
                    action = sig["action"]
                    if ticker in holdings and action == "SELL":
                        pos = holdings[ticker]
                        alerts.append(
                            f"SIGNAL CONFLICT: Model says SELL {ticker} "
                            f"(rank={sig['rank']}, score={sig['prediction']:.3f}) "
                            f"— you hold {pos['shares']:.2f} shares @ ${pos['cost_basis']:.2f}"
                        )
                    elif ticker in holdings and action == "BUY":
                        pos = holdings[ticker]
                        alerts.append(
                            f"SIGNAL CONFIRM: Model says BUY {ticker} "
                            f"(rank={sig['rank']}, score={sig['prediction']:.3f}) "
                            f"— you hold {pos['shares']:.2f} shares @ ${pos['cost_basis']:.2f}"
                        )

            # Check P&L thresholds against current prices
            pnl_cfg = alert_cfg.get("pnl_thresholds", {})
            loss_pct = pnl_cfg.get("loss_pct", -10.0)
            gain_pct = pnl_cfg.get("gain_pct", 20.0)

            try:
                price_path = DATA_DIR / "prices_daily.csv"
                price_df = pd.read_csv(price_path, parse_dates=["date"])
                latest_prices = (
                    price_df.sort_values("date")
                    .groupby("ticker")
                    .last()["close"]
                    .to_dict()
                )

                for ticker, pos in holdings.items():
                    current = latest_prices.get(ticker)
                    if current is None:
                        continue
                    pnl_pct = ((current - pos["cost_basis"]) / pos["cost_basis"]) * 100
                    if pnl_pct <= loss_pct:
                        alerts.append(
                            f"P&L ALERT: {ticker} down {pnl_pct:.1f}% "
                            f"(${pos['cost_basis']:.2f} -> ${current:.2f}, "
                            f"threshold: {loss_pct}%)"
                        )
                    elif pnl_pct >= gain_pct:
                        alerts.append(
                            f"P&L ALERT: {ticker} up {pnl_pct:.1f}% "
                            f"(${pos['cost_basis']:.2f} -> ${current:.2f}, "
                            f"threshold: +{gain_pct}%)"
                        )
            except Exception as e:
                self.logger.warning(f"P&L threshold check failed: {e}")

        if alerts:
            self.logger.info("--- Personal Portfolio Alerts ---")
            alert_msg = "PERSONAL PORTFOLIO ALERTS\n" + "\n".join(f"  {a}" for a in alerts)
            self.logger.info(alert_msg)
            self._notify(alert_msg)

        return {"alerts": alerts}

    # ------------------------------------------------------------------
    # Forward Prediction Journal
    # ------------------------------------------------------------------

    def _log_forward_predictions(self) -> Dict:
        """Log today's predictions from all portfolios to forward journal."""
        self.logger.info("--- Forward Prediction Journal ---")
        if self.dry_run:
            return {"status": "dry_run"}

        from scripts.forward_journal import ForwardJournalDB
        import sqlite3

        journal = ForwardJournalDB()
        today = datetime.now().strftime("%Y-%m-%d")
        total_logged = 0

        for p in PORTFOLIOS:
            wl = p["watchlist"]
            db_path = DATA_DIR / f"paper_trading_{wl}.db"
            if not db_path.exists():
                continue

            try:
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                # Get today's signals
                signals = conn.execute(
                    "SELECT ticker, prediction, rank, percentile, action "
                    "FROM signals WHERE date = ? ORDER BY rank",
                    (today,)
                ).fetchall()
                conn.close()

                if not signals:
                    # Try most recent date
                    conn = sqlite3.connect(str(db_path))
                    conn.row_factory = sqlite3.Row
                    signals = conn.execute(
                        "SELECT ticker, prediction, rank, percentile, action, date "
                        "FROM signals ORDER BY date DESC LIMIT 50"
                    ).fetchall()
                    if signals:
                        latest_date = signals[0]["date"]
                        signals = [s for s in signals if s["date"] == latest_date]
                        today_for_wl = latest_date
                    else:
                        today_for_wl = today
                    conn.close()
                else:
                    today_for_wl = today

                # Get current prices for entry_price
                price_df = pd.read_csv(DATA_DIR / "prices_daily.csv")
                if "date" in price_df.columns:
                    price_df["date"] = pd.to_datetime(price_df["date"], format="mixed")

                predictions_batch = []
                for sig in signals:
                    ticker = sig["ticker"]
                    # Get latest close price for this ticker
                    if "ticker" in price_df.columns:
                        ticker_prices = price_df[price_df["ticker"] == ticker]
                    elif "symbol" in price_df.columns:
                        ticker_prices = price_df[price_df["symbol"] == ticker]
                    else:
                        ticker_prices = pd.DataFrame()

                    entry_price = 0.0
                    if len(ticker_prices) > 0 and "close" in ticker_prices.columns:
                        entry_price = float(ticker_prices.iloc[-1]["close"])

                    for horizon in PREDICTION_HORIZONS:
                        predictions_batch.append({
                            "prediction_date": today_for_wl,
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
                self.logger.info(f"  {wl}: logged {logged} predictions "
                                 f"({len(signals)} signals x {len(PREDICTION_HORIZONS)} horizons)")

            except Exception as e:
                self.logger.error(f"  {wl} journal logging failed: {e}")

        journal.close()
        self.logger.info(f"Total predictions logged: {total_logged}")
        return {"status": "success", "logged": total_logged}

    def _evaluate_matured_predictions(self) -> Dict:
        """Evaluate predictions that have matured (5-day)."""
        self.logger.info("--- Evaluate Matured Predictions ---")
        if self.dry_run:
            return {"status": "dry_run"}

        from scripts.forward_journal import ForwardJournalDB

        journal = ForwardJournalDB()
        today = datetime.now().strftime("%Y-%m-%d")
        total_evaluated = 0

        # Load current prices
        try:
            price_df = pd.read_csv(DATA_DIR / "prices_daily.csv")
            if "date" in price_df.columns:
                price_df["date"] = pd.to_datetime(price_df["date"], format="mixed")
        except Exception as e:
            self.logger.error(f"Cannot load prices for evaluation: {e}")
            journal.close()
            return {"status": "error", "error": str(e)}

        for horizon in PREDICTION_HORIZONS:
            matured = journal.get_matured_predictions(horizon_days=horizon, as_of_date=today)
            if not matured:
                continue

            self.logger.info(f"  Evaluating {len(matured)} matured {horizon}-day predictions")

            for pred in matured:
                ticker = pred["ticker"]
                entry_price = pred["entry_price"]

                if entry_price <= 0:
                    continue

                # Get current price
                if "ticker" in price_df.columns:
                    ticker_prices = price_df[price_df["ticker"] == ticker]
                elif "symbol" in price_df.columns:
                    ticker_prices = price_df[price_df["symbol"] == ticker]
                else:
                    continue

                if len(ticker_prices) == 0 or "close" not in ticker_prices.columns:
                    continue

                actual_price = float(ticker_prices.iloc[-1]["close"])
                actual_return = (actual_price - entry_price) / entry_price

                # Hit: BUY + positive return, or SELL + negative return
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
                self.logger.info(
                    f"  {horizon}d hit rate (30d): "
                    f"{rates['hit_rate']:.1%} ({rates['hits']}/{rates['total']})"
                )

        journal.close()
        self.logger.info(f"Total evaluated: {total_evaluated}")
        return {"status": "success", "evaluated": total_evaluated}

    # ------------------------------------------------------------------
    # Weekly Helpers
    # ------------------------------------------------------------------

    def _generate_weekly_report(self) -> Dict:
        """Generate side-by-side performance for 4 portfolios over the past week."""
        self.logger.info("--- Weekly Performance Report ---")
        import sqlite3
        report = {}

        for p in PORTFOLIOS:
            wl = p["watchlist"]
            db_path = DATA_DIR / f"paper_trading_{wl}.db"
            if not db_path.exists():
                report[wl] = {"status": "no_data"}
                continue

            try:
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                snaps = conn.execute(
                    "SELECT date, portfolio_value, daily_return, cumulative_return "
                    "FROM daily_snapshots WHERE date >= ? ORDER BY date",
                    (week_ago,)
                ).fetchall()
                conn.close()

                if not snaps:
                    report[wl] = {"status": "no_data"}
                    continue

                returns = [s["daily_return"] for s in snaps if s["daily_return"] is not None]
                weekly_return = sum(returns) if returns else 0.0
                latest_value = snaps[-1]["portfolio_value"]
                cum_return = snaps[-1]["cumulative_return"]

                report[wl] = {
                    "status": "ok",
                    "portfolio_value": latest_value,
                    "weekly_return": weekly_return,
                    "cumulative_return": cum_return,
                    "trading_days": len(snaps),
                }
                self.logger.info(
                    f"  {wl}: ${latest_value:,.0f} "
                    f"(week: {weekly_return:+.2%}, total: {cum_return:+.2%})"
                )
            except Exception as e:
                report[wl] = {"status": "error", "error": str(e)}
                self.logger.error(f"  {wl}: {e}")

        return report

    def _check_portfolio_drift(self) -> Dict:
        """Check if actual weights deviate from targets by >5%."""
        self.logger.info("--- Portfolio Drift Check ---")
        # For now, log position counts as a basic drift indicator
        import sqlite3
        drift_report = {}

        for p in PORTFOLIOS:
            wl = p["watchlist"]
            db_path = DATA_DIR / f"paper_trading_{wl}.db"
            if not db_path.exists():
                continue

            try:
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                positions = conn.execute(
                    "SELECT ticker, weight FROM positions WHERE is_active = 1"
                ).fetchall()
                conn.close()

                max_weight = max((pos["weight"] for pos in positions), default=0)
                drift_report[wl] = {
                    "positions": len(positions),
                    "max_weight": max_weight,
                    "drift_alert": max_weight > 0.30,  # Flag if any position > 30%
                }
                if max_weight > 0.30:
                    self.logger.warning(f"  {wl}: DRIFT — max weight {max_weight:.1%}")
            except Exception as e:
                drift_report[wl] = {"error": str(e)}

        return drift_report

    def _forward_test_weekly_review(self) -> Dict:
        """Summarize forward test hit rates for the past week."""
        self.logger.info("--- Forward Test Weekly Review ---")
        from scripts.forward_journal import ForwardJournalDB

        journal = ForwardJournalDB()
        by_watchlist = journal.get_hit_rates_by_watchlist(last_n_days=7)

        for row in by_watchlist:
            total = row["total"]
            hits = row["hits"]
            rate = hits / total if total > 0 else 0
            self.logger.info(
                f"  {row['watchlist']} ({row['horizon_days']}d): "
                f"{rate:.1%} ({hits}/{total})"
            )

        journal.close()
        return {"by_watchlist": by_watchlist}

    # ------------------------------------------------------------------
    # Monthly Helpers
    # ------------------------------------------------------------------

    def _download_fundamentals(self) -> Dict:
        """Download fundamentals for union of all watchlists."""
        self.logger.info("--- Download Fundamentals ---")
        if self.dry_run:
            return {"status": "dry_run"}

        try:
            watchlist_names = [p["watchlist"] for p in PORTFOLIOS]
            tickers = get_all_tickers(watchlist_names)
            self.logger.info(f"Downloading fundamentals for {len(tickers)} tickers")

            from scripts.download_fundamentals import download_fundamentals
            download_fundamentals(tickers=tickers, output_path=DATA_DIR / "fundamentals.csv")
            self.logger.info("Fundamentals download complete")
            return {"status": "success", "tickers": len(tickers)}
        except Exception as e:
            self.logger.error(f"Fundamentals download failed: {e}")
            return {"status": "error", "error": str(e)}

    def _evaluate_63day_predictions(self) -> Dict:
        """Evaluate 63-day predictions that have matured."""
        self.logger.info("--- 63-Day Prediction Evaluation ---")
        return self._evaluate_matured_predictions()

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def _write_daily_summary(self, results: Dict):
        """Write a plain-language daily summary to logs/daily_summary.txt."""
        from datetime import datetime as dt
        import sqlite3
        lines = []
        lines.append(f"{'='*60}")
        lines.append(f"DAILY SUMMARY — {dt.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"{'='*60}")

        # 1. Market regime
        try:
            price_df = pd.read_csv(DATA_DIR / "prices_daily.csv", parse_dates=["date"])
            spy = price_df[price_df["ticker"] == "SPY"].sort_values("date")
            if len(spy) >= 20:
                spy_current = spy.iloc[-1]["close"]
                spy_20d = spy.iloc[-20]["close"]
                spy_ret = (spy_current / spy_20d) - 1
                if spy_ret <= -0.08:
                    regime = "CASH (SPY <-8%)"
                elif spy_ret <= -0.05:
                    regime = "REDUCED (SPY <-5%)"
                else:
                    regime = "NORMAL"
                lines.append(f"\nMARKET REGIME: {regime}")
                lines.append(f"  SPY 20d return: {spy_ret:+.2%}  (reduce at -5%, exit at -8%)")
                lines.append(f"  SPY close: ${spy_current:.2f}")
        except Exception as e:
            lines.append(f"\nMARKET REGIME: unknown ({e})")

        # 2. Portfolio summary
        lines.append(f"\nPORTFOLIOS:")
        total_value = 0
        positions_count = 0
        stopped_today = []
        cooled_tickers = set()
        all_position_returns = []

        for p in PORTFOLIOS:
            wl = p["watchlist"]
            db_path = DATA_DIR / f"paper_trading_{wl}.db"
            if not db_path.exists():
                continue
            try:
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row

                snap = conn.execute(
                    "SELECT portfolio_value, daily_return, cumulative_return "
                    "FROM daily_snapshots ORDER BY date DESC LIMIT 1"
                ).fetchone()

                pos = conn.execute(
                    "SELECT ticker, shares, entry_price, weight "
                    "FROM positions WHERE is_active = 1"
                ).fetchall()

                # Check for stop-loss cooldowns
                try:
                    cooled = conn.execute(
                        "SELECT ticker, cooldown_until FROM stop_loss_cooldown WHERE cooldown_until > date('now')"
                    ).fetchall()
                    for c in cooled:
                        cooled_tickers.add(f"{c[0]} ({wl}, until {c[1]})")
                except Exception:
                    pass

                # Check today's trades for stop-losses
                today_str = dt.now().strftime("%Y-%m-%d")
                try:
                    today_trades = conn.execute(
                        "SELECT ticker, action, shares, price FROM trades WHERE date LIKE ? AND action = 'SELL'",
                        (f"{today_str}%",)
                    ).fetchall()
                except Exception:
                    today_trades = []

                conn.close()

                if snap:
                    pv = snap["portfolio_value"]
                    dr = snap["daily_return"]
                    cr = snap["cumulative_return"]
                    total_value += pv
                    positions_count += len(pos)
                    lines.append(f"  {wl:22s} ${pv:>10,.0f}  daily:{dr:+.2%}  total:{cr:+.2%}  pos:{len(pos)}")

                    # Track per-position returns for top/bottom
                    price_df_wl = pd.read_csv(DATA_DIR / "prices_daily.csv")
                    latest = price_df_wl.sort_values("date").groupby("ticker").last()["close"].to_dict()
                    for position in pos:
                        tk = position["ticker"]
                        entry = position["entry_price"]
                        current = latest.get(tk, entry)
                        if entry > 0:
                            ret = (current / entry) - 1
                            all_position_returns.append((tk, wl, ret, current, entry))

            except Exception as e:
                lines.append(f"  {wl:22s} ERROR: {e}")

        lines.append(f"\n  TOTAL VALUE: ${total_value:,.0f}  |  POSITIONS: {positions_count}")

        # 3. Stop-losses triggered today
        if stopped_today:
            lines.append(f"\nSTOP-LOSSES TODAY: {', '.join(stopped_today)}")
        else:
            lines.append(f"\nSTOP-LOSSES TODAY: none")

        # 4. Cooldown tickers
        if cooled_tickers:
            lines.append(f"COOLDOWN ACTIVE ({len(cooled_tickers)}):")
            for c in sorted(cooled_tickers):
                lines.append(f"  {c}")
        else:
            lines.append(f"COOLDOWN ACTIVE: none")

        # 5. Top 3 / Bottom 3 positions
        if all_position_returns:
            sorted_pos = sorted(all_position_returns, key=lambda x: x[2])
            lines.append(f"\nBOTTOM 3 POSITIONS:")
            for tk, wl, ret, cur, entry in sorted_pos[:3]:
                lines.append(f"  {tk:6s} ({wl:15s}) {ret:+.1%}  entry=${entry:.2f} now=${cur:.2f}")
            lines.append(f"\nTOP 3 POSITIONS:")
            for tk, wl, ret, cur, entry in sorted_pos[-3:]:
                lines.append(f"  {tk:6s} ({wl:15s}) {ret:+.1%}  entry=${entry:.2f} now=${cur:.2f}")

            avg_ret = sum(r[2] for r in all_position_returns) / len(all_position_returns)
            lines.append(f"\n  AVG POSITION RETURN: {avg_ret:+.2%} across {len(all_position_returns)} positions")

        lines.append(f"\n{'='*60}")

        summary = "\n".join(lines)
        summary_path = LOG_DIR / "daily_summary.txt"
        with open(summary_path, "w") as f:
            f.write(summary)
        self.logger.info(f"Daily summary written to {summary_path}")
        return summary

    def _step_status(self, name: str, result: dict) -> str:
        """Format a one-line status string for a step result."""
        status = result.get("status", "unknown")
        if status == "error":
            return f":x: {name}: FAILED — {result.get('error', 'unknown error')[:100]}"
        if status == "skipped":
            reason = result.get("reason", "")
            return f":fast_forward: {name}: skipped ({reason})"
        if status == "dry_run":
            return f":test_tube: {name}: dry run"

        # Build detail string from known keys
        parts = []
        for key in ("tickers", "logged", "evaluated", "hits", "total", "count",
                     "picks", "stocks", "recommendations"):
            if key in result:
                parts.append(f"{key}={result[key]}")
        # Portfolio results (nested dict of watchlist -> result)
        if isinstance(result, dict) and all(isinstance(v, dict) for v in result.values()):
            ok = sum(1 for v in result.values() if v.get("status") == "success")
            fail = sum(1 for v in result.values() if v.get("status") == "error")
            parts = [f"{ok} ok, {fail} failed"]

        detail = ", ".join(parts) if parts else "ok"
        return f":white_check_mark: {name}: {detail}"

    def _notify(self, message: str):
        """Send notification to Slack + Google Chat."""
        tag = os.environ.get("SP_INSTANCE", "SP")
        tagged = f"[{tag}] {message}"
        post_webhook(self.slack_url, tagged, self.logger)
        post_webhook(self.gchat_url, tagged, self.logger)

    # ------------------------------------------------------------------
    # Summary Formatters
    # ------------------------------------------------------------------


    def _generate_recommendations(self) -> Dict:
        """Generate fresh recommendations from today's top signals across all portfolios."""
        self.logger.info("--- Generate Recommendations ---")
        if self.dry_run:
            return {"status": "dry_run"}

        import sqlite3
        import json

        today = datetime.now().strftime("%Y-%m-%d")
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Load sector mapping
        sector_map = {}
        sectors_path = DATA_DIR / "sectors.json"
        if sectors_path.exists():
            try:
                with open(sectors_path) as f:
                    raw = json.load(f)
                    sector_map = {k: v for k, v in raw.items() if isinstance(v, str)}
            except Exception:
                pass

        # Load latest prices
        price_map = {}
        prices_path = DATA_DIR / "prices_daily.csv"
        if prices_path.exists():
            try:
                pdf = pd.read_csv(prices_path)
                if "date" in pdf.columns:
                    pdf["date"] = pd.to_datetime(pdf["date"], format="mixed")
                ticker_col = "ticker" if "ticker" in pdf.columns else "symbol"
                for ticker in pdf[ticker_col].unique():
                    tdf = pdf[pdf[ticker_col] == ticker].sort_values("date")
                    if len(tdf) > 0 and "close" in tdf.columns:
                        price_map[ticker] = float(tdf.iloc[-1]["close"])
            except Exception as e:
                self.logger.warning(f"Could not load prices: {e}")

        # Collect top signals from all watchlists
        all_signals = []
        for p in PORTFOLIOS:
            wl = p["watchlist"]
            db_path = DATA_DIR / f"paper_trading_{wl}.db"
            if not db_path.exists():
                continue
            try:
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                # Get most recent signals
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
                        "ticker": r["ticker"],
                        "prediction": r["prediction"],
                        "rank": r["rank"],
                        "action": r["action"],
                        "watchlist": wl,
                        "date": latest_date,
                    })
            except Exception as e:
                self.logger.warning(f"  {wl}: could not read signals: {e}")

        if not all_signals:
            self.logger.info("  No signals found — skipping recommendations")
            return {"status": "no_signals", "count": 0}

        # Deduplicate: keep the signal with highest prediction score per ticker
        best_by_ticker = {}
        for sig in all_signals:
            t = sig["ticker"]
            if t not in best_by_ticker or sig["prediction"] > best_by_ticker[t]["prediction"]:
                best_by_ticker[t] = sig

        # Take top BUYs (rank 1-5 by score) and top SELLs (lowest scores)
        sorted_sigs = sorted(best_by_ticker.values(), key=lambda s: s["prediction"], reverse=True)
        top_buys = [s for s in sorted_sigs if s["action"] == "BUY"][:10]
        top_sells = [s for s in sorted_sigs if s["action"] == "SELL"][:5]
        recs = top_buys + top_sells

        if not recs:
            self.logger.info("  No actionable signals — skipping")
            return {"status": "no_actionable", "count": 0}

        # Write to analysis.db recommendations table
        analysis_db = DATA_DIR / "analysis.db"
        conn = sqlite3.connect(str(analysis_db))

        inserted = 0
        for sig in recs:
            ticker = sig["ticker"]
            price = price_map.get(ticker, 0.0)
            sector = sector_map.get(ticker, "Unknown")
            action = sig["action"]
            score = sig["prediction"]

            # Confidence based on how extreme the score is
            if score > 0.8 or score < 0.2:
                confidence = 0.8
            elif score > 0.7 or score < 0.3:
                confidence = 0.7
            else:
                confidence = 0.5

            # Set target/stop based on action
            if action == "BUY" and price > 0:
                target_price = round(price * 1.10, 2)   # +10% target
                stop_loss = round(price * 0.95, 2)       # -5% stop
            elif action == "SELL" and price > 0:
                target_price = round(price * 0.90, 2)    # -10% target
                stop_loss = round(price * 1.05, 2)       # +5% stop
            else:
                target_price = None
                stop_loss = None

            reason = f"Score: {score:.3f}, Rank #{sig['rank']} in {sig['watchlist'].replace('_', ' ')}"

            # Skip if already recommended today
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
                    (run_id, ticker, action, today, reason,
                     confidence, target_price, stop_loss, "medium",
                     price, score, sector, "daily_routine", datetime.now().isoformat()),
                )
                inserted += 1
            except Exception as e:
                self.logger.warning(f"  Failed to insert {ticker}: {e}")

        conn.commit()
        conn.close()

        self.logger.info(f"  Generated {inserted} recommendations ({len(top_buys)} BUY, {len(top_sells)} SELL)")

        # Update tracking for past recommendations
        updated = self._update_recommendation_tracking(price_map)

        return {"status": "success", "count": inserted, "buys": len(top_buys), "sells": len(top_sells), "tracking_updated": updated}

    def _update_recommendation_tracking(self, price_map: Dict) -> int:
        """Update actual_return, hit_target, hit_stop_loss for past recommendations."""
        import sqlite3

        analysis_db = DATA_DIR / "analysis.db"
        conn = sqlite3.connect(str(analysis_db))
        conn.row_factory = sqlite3.Row

        # Get recommendations that need tracking updates
        rows = conn.execute(
            """SELECT id, ticker, action, current_price, target_price, stop_loss
               FROM recommendations
               WHERE current_price > 0"""
        ).fetchall()

        updated = 0
        now = datetime.now().isoformat()
        for row in rows:
            ticker = row["ticker"]
            entry_price = row["current_price"]
            current_price = price_map.get(ticker)
            if current_price is None or entry_price <= 0:
                continue

            actual_return = (current_price / entry_price) - 1.0

            # For SELL recommendations, return is inverted (we profit when price drops)
            if row["action"] == "SELL":
                actual_return = -actual_return

            hit_target = 0
            hit_stop = 0
            if row["target_price"] and row["action"] == "BUY":
                hit_target = 1 if current_price >= row["target_price"] else 0
                hit_stop = 1 if row["stop_loss"] and current_price <= row["stop_loss"] else 0
            elif row["target_price"] and row["action"] == "SELL":
                hit_target = 1 if current_price <= row["target_price"] else 0
                hit_stop = 1 if row["stop_loss"] and current_price >= row["stop_loss"] else 0

            conn.execute(
                """UPDATE recommendations
                   SET actual_return = ?, hit_target = ?, hit_stop_loss = ?, tracking_updated_at = ?
                   WHERE id = ?""",
                (round(actual_return, 6), hit_target, hit_stop, now, row["id"]),
            )
            updated += 1

        conn.commit()
        conn.close()
        self.logger.info(f"  Updated tracking for {updated} recommendations")
        return updated

    def _format_daily_summary(self, results: Dict) -> str:
        """Format daily results into notification message."""
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [f"Daily Routine Complete -- {today}", ""]

        # Portfolios
        lines.append("PORTFOLIOS")
        portfolios = results.get("portfolios", {})
        for p in PORTFOLIOS:
            wl = p["watchlist"]
            info = portfolios.get(wl, {})
            status = info.get("status", "unknown")
            mode = "Alpaca" if not p["local"] else "Local"

            if status == "success":
                val = info.get("portfolio_value", 0)
                ret = info.get("cumulative_return", 0)
                lines.append(f"  {wl:20s} ${val:>10,.0f} ({ret:+.2%}) -- {mode}")
            elif status == "error":
                lines.append(f"  {wl:20s} FAILED: {info.get('error', '')[:50]} -- {mode}")
            else:
                lines.append(f"  {wl:20s} {status} -- {mode}")

        # Rebalancing trades
        has_trades = False
        for p in PORTFOLIOS:
            wl = p["watchlist"]
            info = portfolios.get(wl, {})
            trades = info.get("trades", [])
            if trades:
                if not has_trades:
                    lines.append("")
                    lines.append("REBALANCING")
                    has_trades = True
                buys = [t for t in trades if t["action"] == "BUY"]
                sells = [t for t in trades if t["action"] == "SELL"]
                lines.append(f"  {wl}:")
                if buys:
                    buy_tickers = ", ".join(f"{t['ticker']}(${t['value']:,.0f})" for t in buys)
                    lines.append(f"    BUY:  {buy_tickers}")
                if sells:
                    sell_tickers = ", ".join(f"{t['ticker']}(${t['value']:,.0f})" for t in sells)
                    lines.append(f"    SELL: {sell_tickers}")

        # Forward predictions
        pred_info = results.get("predictions", {})
        eval_info = results.get("evaluations", {})
        lines.append("")
        lines.append(f"PREDICTIONS LOGGED: {pred_info.get('logged', 0)}")
        lines.append(f"PREDICTIONS EVALUATED: {eval_info.get('evaluated', 0)}")

        # Sentiment
        sent_info = results.get("sentiment", {})
        dl_status = sent_info.get("download", {}).get("status", "")
        lines.append(f"SENTIMENT: {dl_status}")

        # Moby
        moby_info = results.get("moby_parse", {})
        lines.append(f"MOBY PARSE: {moby_info.get('status', 'unknown')} "
                      f"({moby_info.get('picks', 0)} picks)")

        return "\n".join(lines)

    def _format_weekly_summary(self, results: Dict) -> str:
        """Format weekly results into notification message."""
        lines = [f"Weekly Report -- {datetime.now().strftime('%Y-%m-%d')}", ""]

        lines.append("PORTFOLIO PERFORMANCE (7 days)")
        report = results.get("weekly_report", {})
        for p in PORTFOLIOS:
            wl = p["watchlist"]
            info = report.get(wl, {})
            if info.get("status") == "ok":
                val = info.get("portfolio_value", 0)
                wr = info.get("weekly_return", 0)
                cr = info.get("cumulative_return", 0)
                lines.append(f"  {wl:20s} ${val:>10,.0f}  week: {wr:+.2%}  total: {cr:+.2%}")
            else:
                lines.append(f"  {wl:20s} {info.get('status', 'no data')}")

        # Forward test
        fwd = results.get("forward_review", {})
        by_wl = fwd.get("by_watchlist", [])
        if by_wl:
            lines.append("")
            lines.append("FORWARD TEST HIT RATES (7 days)")
            for row in by_wl:
                total = row["total"]
                hits = row["hits"]
                rate = hits / total if total > 0 else 0
                lines.append(
                    f"  {row['watchlist']:20s} {row['horizon_days']:3d}d: "
                    f"{rate:.1%} ({hits}/{total})"
                )

        # Drift
        drift = results.get("drift_check", {})
        alerts = [wl for wl, d in drift.items() if d.get("drift_alert")]
        if alerts:
            lines.append("")
            lines.append(f"DRIFT ALERTS: {', '.join(alerts)}")

        return "\n".join(lines)

    def _format_monthly_summary(self, results: Dict) -> str:
        """Format monthly results into notification message."""
        lines = [f"Monthly Report -- {datetime.now().strftime('%Y-%m-%d')}", ""]

        fund = results.get("fundamentals", {})
        lines.append(f"FUNDAMENTALS: {fund.get('status', 'unknown')}")

        fwd = results.get("forward_63d", {})
        lines.append(f"63-DAY EVALUATIONS: {fwd.get('evaluated', 0)}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Consolidated daily/weekly/monthly orchestrator"
    )
    parser.add_argument(
        "mode",
        choices=["daily", "weekly", "monthly"],
        help="Which routine to run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would happen without executing trades or downloading data",
    )
    parser.add_argument(
        "--skip-sentiment",
        action="store_true",
        help="Skip Finnhub sentiment download (saves ~18 min on re-runs)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if already ran today (bypass once-per-day lock)",
    )
    args = parser.parse_args()

    logger = setup_logging(args.mode)

    # Once-per-day lock (unless --force or --dry-run)
    fd = None
    if not args.force and not args.dry_run:
        fd = acquire_daily_lock(args.mode, logger)
        if fd is None:
            return  # Already ran today or another instance is running

    routine = DailyRoutine(dry_run=args.dry_run, skip_sentiment=args.skip_sentiment)

    try:
        if args.mode == "daily":
            routine.run_daily()
        elif args.mode == "weekly":
            routine.run_weekly()
        elif args.mode == "monthly":
            routine.run_monthly()

        # Mark as completed for today
        if fd is not None:
            stamp_daily_lock(args.mode, fd)
            fd = None
    except Exception:
        # Notification already sent in run_* methods; just ensure lock is released
        if fd is not None:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
