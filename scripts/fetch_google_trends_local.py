#!/usr/bin/env python3
"""
Google Trends local fetcher.

Runs on Mac (residential IP) — NOT on Hetzner (blocked by Google).

Usage:
    python scripts/fetch_google_trends_local.py
    python scripts/fetch_google_trends_local.py --watchlist sg_blue_chips
    python scripts/fetch_google_trends_local.py --dry-run   # print results, don't push
    python scripts/fetch_google_trends_local.py --output /tmp/trends.json  # save locally

Schedule on Mac via crontab:
    0 7 * * * source ~/.sentimentpulse.env && \
      cd ~/Documents/code/my_code/stock_all/midterm-stock-planner && \
      .venv/bin/python scripts/fetch_google_trends_local.py \
      >> ~/Library/Logs/trends.log 2>&1
"""

import argparse
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests
import yaml
from pytrends.request import TrendReq

log = logging.getLogger("google_trends")

# ---------------------------------------------------------------------------
# Ticker -> search term mapping
# ---------------------------------------------------------------------------

TICKER_TO_SEARCH_TERM = {
    # US Tech
    "AAPL": "Apple stock",
    "MSFT": "Microsoft stock",
    "NVDA": "NVIDIA stock",
    "AMD": "AMD stock",
    "GOOGL": "Google stock",
    "META": "Meta stock",
    "AMZN": "Amazon stock",
    "TSLA": "Tesla stock",
    "NFLX": "Netflix stock",
    "ORCL": "Oracle stock",
    "CRM": "Salesforce stock",
    "ADBE": "Adobe stock",
    "INTC": "Intel stock",
    # Semiconductors
    "TSM": "TSMC stock",
    "ASML": "ASML stock",
    "AVGO": "Broadcom stock",
    "QCOM": "Qualcomm stock",
    "MU": "Micron stock",
    "ON": "ON Semiconductor stock",
    # SGX — use company name, not ticker code
    "D05.SI": "DBS bank Singapore",
    "O39.SI": "OCBC bank Singapore",
    "U11.SI": "UOB bank Singapore",
    "Z74.SI": "Singtel stock",
    "C6L.SI": "Singapore Airlines stock",
    "BN4.SI": "Keppel Corporation Singapore",
    "S63.SI": "ST Engineering Singapore",
    "S68.SI": "SGX Singapore Exchange",
    "C09.SI": "City Developments Singapore",
    "ES3.SI": "STI ETF Singapore",
    "C38U.SI": "CapitaLand REIT Singapore",
    "ME8U.SI": "Mapletree Industrial Trust",
    # Precious metals
    "GLD": "gold ETF price",
    "SLV": "silver ETF price",
    "GDX": "gold miners ETF",
    "NEM": "Newmont gold mining",
    "WPM": "Wheaton Precious Metals",
    # Energy
    "XOM": "ExxonMobil stock",
    "CVX": "Chevron stock",
    # Nuclear
    "NLR": "uranium nuclear energy ETF",
    "CCJ": "Cameco uranium",
    # ETFs
    "SPY": "S&P 500 ETF",
    "QQQ": "Nasdaq ETF",
    "ARKK": "ARK Innovation ETF",
    "SMH": "semiconductor ETF",
}


def get_search_term(ticker: str) -> str:
    """Get Google-friendly search term for a ticker."""
    clean = str(ticker).replace("\n", "").strip()
    if clean in TICKER_TO_SEARCH_TERM:
        return TICKER_TO_SEARCH_TERM[clean]
    base = clean.replace(".SI", "").replace("-", " ")
    return f"{base} stock"


# ---------------------------------------------------------------------------
# Ticker loading from watchlists.yaml
# ---------------------------------------------------------------------------


def load_all_tickers(watchlists_path: str) -> list:
    """Load all unique tickers from watchlists.yaml."""
    with open(watchlists_path) as f:
        config = yaml.safe_load(f)

    tickers = set()
    for wl_name, wl_data in config.get("watchlists", {}).items():
        for t in wl_data.get("symbols", []):
            # YAML parses ON (ON Semiconductor) as boolean True — coerce to string
            if isinstance(t, bool):
                t = "ON"
            tickers.add(str(t))

    return sorted(tickers)


def load_watchlist_tickers(watchlists_path: str, watchlist: str) -> list:
    """Load tickers from a specific watchlist."""
    with open(watchlists_path) as f:
        wl_config = yaml.safe_load(f)
    wl_data = wl_config.get("watchlists", {}).get(watchlist, {})
    return [
        str(t) if not isinstance(t, bool) else "ON"
        for t in wl_data.get("symbols", [])
    ]


# ---------------------------------------------------------------------------
# Google Trends fetching
# ---------------------------------------------------------------------------


def _empty() -> dict:
    return {
        "trends_interest_7d": 0.0,
        "trends_interest_30d": 0.0,
        "trends_7d_change": 0.0,
        "trends_spike_flag": False,
        "fetched_at": datetime.now().isoformat(),
    }


def fetch_trends_for_tickers(
    tickers: List[str],
    lookback_days: int = 30,
    batch_delay_s: float = 15.0,
    retry_delay_s: float = 60.0,
    max_retries: int = 2,
) -> Dict[str, dict]:
    """
    Fetch Google Trends for all tickers in batches of 5.

    Returns dict of ticker -> {trends_interest_7d, trends_interest_30d,
                                trends_7d_change, trends_spike_flag, fetched_at}
    """
    pytrends = TrendReq(
        hl="en-US", tz=480, timeout=(15, 45), retries=1, backoff_factor=0.5
    )
    results = {}
    batches = [tickers[i : i + 5] for i in range(0, len(tickers), 5)]

    log.info(
        f"Fetching trends for {len(tickers)} tickers "
        f"in {len(batches)} batches of 5"
    )

    for batch_num, batch in enumerate(batches, 1):
        terms = [get_search_term(t) for t in batch]
        log.info(f"Batch {batch_num}/{len(batches)}: {batch}")

        success = False
        for attempt in range(max_retries + 1):
            try:
                pytrends.build_payload(
                    terms,
                    cat=0,
                    timeframe=f"today {lookback_days}-d",
                    geo="",
                    gprop="",
                )
                df = pytrends.interest_over_time()
                success = True

                if df.empty:
                    log.warning(f"  Empty DataFrame for batch {batch_num}")
                    for t in batch:
                        results[t] = _empty()
                    break

                for ticker, term in zip(batch, terms):
                    if term not in df.columns:
                        results[ticker] = _empty()
                        continue

                    series = df[term].fillna(0).astype(float)
                    interest_7d = float(series.iloc[-7:].mean())
                    interest_30d = float(series.mean())
                    baseline = (
                        float(series.iloc[:-7].mean())
                        if len(series) > 7
                        else interest_30d
                    )
                    pct_change = (
                        (interest_7d - baseline) / baseline * 100
                        if baseline > 0
                        else 0.0
                    )
                    spike_flag = interest_7d > 2.0 * interest_30d and interest_7d > 20

                    results[ticker] = {
                        "trends_interest_7d": round(interest_7d, 2),
                        "trends_interest_30d": round(interest_30d, 2),
                        "trends_7d_change": round(pct_change, 2),
                        "trends_spike_flag": bool(spike_flag),
                        "fetched_at": datetime.now().isoformat(),
                    }
                    if interest_7d > 0:
                        log.info(
                            f"  {ticker}: 7d={interest_7d:.1f}, "
                            f"30d={interest_30d:.1f}, "
                            f"change={pct_change:+.1f}%"
                            f"{' SPIKE' if spike_flag else ''}"
                        )
                break  # Success — exit retry loop

            except Exception as e:
                log.warning(f"  Attempt {attempt + 1} failed: {e}")

                if attempt < max_retries:
                    wait = retry_delay_s * (2**attempt)
                    log.info(f"  Waiting {wait}s before retry...")
                    time.sleep(wait)
                else:
                    log.error(f"  All attempts failed for batch {batch_num}")
                    for t in batch:
                        results[t] = _empty()

        # Delay between successful batches
        if success and batch_num < len(batches):
            log.debug(f"  Sleeping {batch_delay_s}s before next batch")
            time.sleep(batch_delay_s)

    return results


# ---------------------------------------------------------------------------
# Push to server
# ---------------------------------------------------------------------------


def push_to_server(
    results: dict,
    server_url: str,
    api_token: str,
    output_file: Path = None,
) -> bool:
    """
    Push trends results to the server via POST /api/sentiment/trends-update.
    Returns True on success.

    If server unreachable, saves to output_file for manual upload.
    """
    payload = {
        "data": results,
        "fetched_at": datetime.now().isoformat(),
        "ticker_count": len(results),
        "spike_count": sum(1 for v in results.values() if v.get("trends_spike_flag")),
    }

    try:
        response = requests.post(
            f"{server_url}/api/sentiment/trends-update",
            json=payload,
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=30,
        )
        if response.status_code == 200:
            resp_data = response.json()
            log.info(
                f"Pushed {len(results)} trends to server. "
                f"Updated: {resp_data.get('updated_rows', '?')} rows in DuckDB"
            )
            return True
        else:
            log.error(
                f"Server returned {response.status_code}: {response.text[:200]}"
            )
    except requests.ConnectionError:
        log.error("Cannot reach server — saving locally for manual upload")
    except Exception as e:
        log.error(f"Push failed: {e}")

    # Fallback: save locally
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(payload, indent=2))
        log.info(f"Saved to {output_file} — upload manually with:")
        log.info(f"  curl -X POST {server_url}/api/sentiment/trends-update \\")
        log.info(f"    -H 'Authorization: Bearer {api_token}' \\")
        log.info(f"    -H 'Content-Type: application/json' \\")
        log.info(f"    -d @{output_file}")
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Google Trends locally and push to Hetzner server"
    )
    parser.add_argument(
        "--watchlist",
        default=None,
        help="Only fetch tickers from this watchlist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and print results but do not push to server",
    )
    parser.add_argument(
        "--output",
        default="/tmp/trends_output.json",
        help="Local JSON file path if server is unreachable",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=30,
        help="Days of historical data to fetch (default: 30)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=15.0,
        help="Seconds between batches (default: 15)",
    )
    args = parser.parse_args()

    # Ensure log directory exists
    log_dir = Path.home() / "logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s — %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                log_dir / f"trends_{datetime.now().strftime('%Y%m%d')}.log"
            ),
        ],
    )

    # Load config from environment
    server_url = os.environ.get("SENTIMENT_SERVER_URL", "http://your-hetzner-ip:9000")
    api_token = os.environ.get("SENTIMENT_API_TOKEN", "")
    watchlists_path = os.environ.get(
        "WATCHLISTS_PATH",
        str(Path(__file__).resolve().parent.parent / "config" / "watchlists.yaml"),
    )

    if not Path(watchlists_path).exists():
        log.error(f"Watchlists file not found: {watchlists_path}")
        log.error("Set WATCHLISTS_PATH env var or run from repo root")
        return

    # Load tickers
    if args.watchlist:
        tickers = load_watchlist_tickers(watchlists_path, args.watchlist)
        log.info(f"Filtering to watchlist '{args.watchlist}': {len(tickers)} tickers")
    else:
        tickers = load_all_tickers(watchlists_path)
        log.info(f"Fetching all {len(tickers)} unique tickers")

    if not tickers:
        log.error("No tickers found")
        return

    # Fetch
    start = datetime.now()
    results = fetch_trends_for_tickers(
        tickers,
        lookback_days=args.lookback,
        batch_delay_s=args.delay,
    )
    elapsed = (datetime.now() - start).total_seconds()

    # Summary
    with_data = sum(1 for v in results.values() if v["trends_interest_7d"] > 0)
    spikes = sum(1 for v in results.values() if v["trends_spike_flag"])
    log.info(f"\n{'=' * 50}")
    log.info(f"Complete: {len(results)} tickers in {elapsed:.0f}s")
    log.info(f"With data: {with_data}/{len(results)}")
    log.info(f"Spikes detected: {spikes}")
    if spikes:
        spike_tickers = [t for t, v in results.items() if v["trends_spike_flag"]]
        log.info(f"Spike tickers: {spike_tickers}")
    log.info(f"{'=' * 50}")

    if args.dry_run:
        print(json.dumps(results, indent=2))
        log.info("Dry run — not pushing to server")
        return

    # Push to server
    push_to_server(
        results,
        server_url=server_url,
        api_token=api_token,
        output_file=Path(args.output),
    )


if __name__ == "__main__":
    main()
