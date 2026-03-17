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


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PORTFOLIOS = [
    {"watchlist": "moby_picks", "local": False, "capital": 100000},
    {"watchlist": "tech_giants", "local": True, "capital": 100000},
    {"watchlist": "semiconductors", "local": True, "capital": 100000},
    {"watchlist": "precious_metals", "local": True, "capital": 100000},
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
            self._notify("Daily routine skipped — US market closed today.")
            return {"skipped": True, "reason": "not_trading_day"}

        results: Dict[str, Any] = {}

        # 1. Shared data refresh
        results["data_refresh"] = self._refresh_all_data()

        # 2. Sentiment pipeline
        if self.skip_sentiment:
            self.logger.info("--- Sentiment Pipeline (SKIPPED) ---")
            results["sentiment"] = {"status": "skipped", "reason": "skip_sentiment flag"}
        else:
            results["sentiment"] = self._run_sentiment_pipeline()

        # 3. Moby email parsing
        results["moby_parse"] = self._run_moby_parser()

        # 4. Portfolio runs (error-isolated)
        results["portfolios"] = self._run_all_portfolios()

        # 5. Forward prediction journal
        results["predictions"] = self._log_forward_predictions()

        # 6. Evaluate matured predictions
        results["evaluations"] = self._evaluate_matured_predictions()

        # 7. Summary + notify
        summary = self._format_daily_summary(results)
        self.logger.info("\n" + summary)
        self._notify(summary)

        self.logger.info("DAILY ROUTINE COMPLETE")
        return results

    # ------------------------------------------------------------------
    # WEEKLY
    # ------------------------------------------------------------------

    def run_weekly(self) -> Dict[str, Any]:
        """Weekly performance review."""
        self.logger = setup_logging("weekly")
        self.logger.info("=" * 60)
        self.logger.info("WEEKLY ROUTINE START")
        self.logger.info("=" * 60)

        results: Dict[str, Any] = {}
        results["weekly_report"] = self._generate_weekly_report()
        results["drift_check"] = self._check_portfolio_drift()
        results["forward_review"] = self._forward_test_weekly_review()

        summary = self._format_weekly_summary(results)
        self.logger.info("\n" + summary)
        self._notify(summary)

        self.logger.info("WEEKLY ROUTINE COMPLETE")
        return results

    # ------------------------------------------------------------------
    # MONTHLY
    # ------------------------------------------------------------------

    def run_monthly(self) -> Dict[str, Any]:
        """Monthly maintenance tasks."""
        self.logger = setup_logging("monthly")
        self.logger.info("=" * 60)
        self.logger.info("MONTHLY ROUTINE START")
        self.logger.info("=" * 60)

        results: Dict[str, Any] = {}
        results["fundamentals"] = self._download_fundamentals()
        results["forward_63d"] = self._evaluate_63day_predictions()

        summary = self._format_monthly_summary(results)
        self.logger.info("\n" + summary)
        self._notify(summary)

        self.logger.info("MONTHLY ROUTINE COMPLETE")
        return results

    # ------------------------------------------------------------------
    # Data Refresh
    # ------------------------------------------------------------------

    def _refresh_all_data(self) -> Dict:
        """Download prices for union of all 4 watchlists (deduplicated)."""
        self.logger.info("--- Data Refresh ---")
        watchlist_names = [p["watchlist"] for p in PORTFOLIOS]
        all_tickers = get_all_tickers(watchlist_names)
        self.logger.info(f"Refreshing prices for {len(all_tickers)} unique tickers "
                         f"across {len(watchlist_names)} watchlists")

        if self.dry_run:
            return {"status": "dry_run", "tickers": len(all_tickers)}

        try:
            from src.data.alpaca_client import AlpacaClient
            client = AlpacaClient()
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            df = client.download(
                tickers=all_tickers,
                start_date=start_date,
                end_date=end_date,
                interval="1d",
            )
            # Append to existing prices_daily.csv
            output_path = DATA_DIR / "prices_daily.csv"
            if output_path.exists() and df is not None and len(df) > 0:
                existing = pd.read_csv(output_path)
                combined = pd.concat([existing, df], ignore_index=True).drop_duplicates(
                    subset=["date", "ticker"]
                )
                combined.to_csv(output_path, index=False)
                self.logger.info(f"Data refresh complete: {len(all_tickers)} tickers, "
                                 f"{len(df)} new rows appended")
            elif df is not None and len(df) > 0:
                df.to_csv(output_path, index=False)
                self.logger.info(f"Data refresh complete: {len(all_tickers)} tickers, "
                                 f"{len(df)} rows (fresh)")
            else:
                self.logger.warning("Data refresh returned no data")
            return {"status": "success", "tickers": len(all_tickers)}
        except Exception as e:
            self.logger.error(f"Data refresh failed: {e}")
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------
    # Sentiment
    # ------------------------------------------------------------------

    def _run_sentiment_pipeline(self) -> Dict:
        """Download sentiment data + score articles."""
        self.logger.info("--- Sentiment Pipeline ---")
        if self.dry_run:
            return {"status": "dry_run"}

        result = {}

        # Download from Finnhub
        try:
            from scripts.download_sentiment import FinnhubSentiment
            api_key = os.environ.get("FINNHUB_API_KEY", "")
            if not api_key:
                self.logger.warning("FINNHUB_API_KEY not set — skipping sentiment download")
                result["download"] = {"status": "skipped", "reason": "no_api_key"}
            else:
                watchlist_names = [p["watchlist"] for p in PORTFOLIOS]
                tickers = get_all_tickers(watchlist_names)
                downloader = FinnhubSentiment(api_key=api_key)
                downloader.download_all(tickers, days=30)
                self.logger.info(f"Sentiment downloaded for {len(tickers)} tickers")
                result["download"] = {"status": "success", "tickers": len(tickers)}
        except Exception as e:
            self.logger.error(f"Sentiment download failed: {e}")
            result["download"] = {"status": "error", "error": str(e)}

        # Score articles
        try:
            from scripts.score_sentiment import main as score_main
            score_main()
            self.logger.info("Sentiment scoring complete")
            result["scoring"] = {"status": "success"}
        except Exception as e:
            self.logger.error(f"Sentiment scoring failed: {e}")
            result["scoring"] = {"status": "error", "error": str(e)}

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
        """Run 4 portfolio engines with error isolation."""
        self.logger.info("--- Portfolio Runs ---")
        results = {}

        for p in PORTFOLIOS:
            wl = p["watchlist"]
            self.logger.info(f"Running {wl} ({'local' if p['local'] else 'Alpaca'})...")

            if self.dry_run:
                results[wl] = {"status": "dry_run"}
                continue

            try:
                from scripts.paper_trading import PaperTradingEngine
                engine = PaperTradingEngine(
                    watchlist=wl,
                    initial_capital=p["capital"],
                    force_local=p["local"],
                )
                engine.run_daily(skip_refresh=True)  # Data already refreshed
                results[wl] = self._get_portfolio_status(wl)
                results[wl]["status"] = "success"
                self.logger.info(f"  {wl}: OK")
            except Exception as e:
                self.logger.error(f"  {wl} FAILED: {e}\n{traceback.format_exc()}")
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

    def _notify(self, message: str):
        """Send notification to Slack + Google Chat."""
        post_webhook(self.slack_url, message, self.logger)
        post_webhook(self.gchat_url, message, self.logger)

    # ------------------------------------------------------------------
    # Summary Formatters
    # ------------------------------------------------------------------

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
    args = parser.parse_args()

    routine = DailyRoutine(dry_run=args.dry_run, skip_sentiment=args.skip_sentiment)

    if args.mode == "daily":
        routine.run_daily()
    elif args.mode == "weekly":
        routine.run_weekly()
    elif args.mode == "monthly":
        routine.run_monthly()


if __name__ == "__main__":
    main()
