# Deployment Guide

Production deployment on Hetzner Cloud running FastAPI + React (myFuture dashboard).

## Server Details

| Field | Value |
|-------|-------|
| URL | https://stockplanner.blueideas.net |
| IP | 178.156.173.199 |
| SSH | `ssh deploy@178.156.173.199` |
| Provider | Hetzner Cloud (Ashburn) |
| Plan | CCX13 — 8GB RAM, 2 vCPU dedicated |
| OS | Ubuntu 24.04 LTS |
| Timezone | Asia/Singapore (SGT, UTC+8) |

## Architecture

```
Internet → Nginx (443/SSL) → FastAPI (127.0.0.1:9000, 2 workers)
                            → React static files (myfuture/dist/)
```

- **Backend**: FastAPI via uvicorn, served by `stock-api.service`
- **Frontend**: React (Vite + Tailwind), built to `myfuture/dist/`, served by Nginx
- **Auth**: Cookie-based sessions (`sp_session`), stored in `data/auth.db`
- **Data**: SQLite (paper trading, auth) + DuckDB (sentimentpulse) + CSV (prices, fundamentals)

## Services

### stock-api.service

```ini
[Unit]
Description=Stock Planner FastAPI
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/stock-planner
EnvironmentFile=/home/deploy/stock-planner/.env
ExecStart=/home/deploy/stock-planner/venv/bin/uvicorn src.api.main:app --host 127.0.0.1 --port 9000 --workers 2
Restart=always
RestartSec=5
```

```bash
sudo systemctl restart stock-api    # Restart after code changes
sudo systemctl status stock-api     # Check status
journalctl -u stock-api --since today  # View logs
```

### Nginx

Reverse proxy on port 443 (SSL via Let's Encrypt). Config at `/etc/nginx/sites-enabled/stock-planner`.

- `/api/*` → proxied to FastAPI on port 9000
- `/*` → static files from `myfuture/dist/`
- Rate limiting: 10 req/s per IP with burst of 20

## Cron Schedule (all times SGT)

| # | Job | Schedule | Command |
|---|-----|----------|---------|
| 1 | Daily pipeline | Tue-Sat 6:30 AM | `run_daily_fast.py` |
| 2 | Weekly retrain | Sunday 11:00 PM | `run_retrain.py --watchlist sg_blue_chips` |
| 3 | Feedback eval | Daily 7:00 PM | `run_feedback.py` |
| 4 | Fundamentals refresh | Saturday 2:00 AM | `download_fundamentals.py --all-us-watchlists` |
| 5 | Health monitor | Every 2 hours | `health_monitor.py` |
| 6 | Google Trends | Daily 5:00 AM | `fetch_google_trends_local.py` |
| 7 | Data backup | Daily 3:00 AM | `backup_data.sh` (7-day rotation) |

### Systemd timers

| # | Timer | Schedule | Service | OnFailure |
|---|-------|----------|---------|-----------|
| 1 | daily-routine | Tue-Sat 6:30 AM | `run_daily_fast.py` | Slack alert |
| 2 | sentimentpulse-crawl | 4x daily (00/06/12/18) | SentimentPulse batched crawl | Slack alert |
| 3 | sentimentpulse-feedback | Daily 19:30 | SentimentPulse feedback | - |
| 4 | sentimentpulse-postclose | Tue-Sat 04:30 | SentimentPulse post-close | - |
| 5 | heartbeat | Daily 8:00 AM | `heartbeat.py` | Slack alert |

The heartbeat timer is the **safety net** — it runs via systemd (not cron), so it catches cron failures. It checks: health monitor freshness, daily pipeline ran, no portfolio failures, API up, Google Trends ran. It always sends a Slack message (silence = broken).

Edit with: `crontab -e` (as deploy user). All jobs use `. .env` (not `source`) for POSIX compatibility.

**Important**: Use ASCII-only characters in crontab files (including comments). Ubuntu 24.04 cron silently rejects crontabs containing UTF-8 characters like em-dashes (`—`). Use regular dashes (`-`) instead.

## Deploying Code Changes

### Backend (Python)

```bash
# From local machine
scp scripts/run_daily_fast.py deploy@178.156.173.199:~/stock-planner/scripts/
scp src/api/routers/portfolios.py deploy@178.156.173.199:~/stock-planner/src/api/routers/

# Restart API to pick up changes
ssh deploy@178.156.173.199 "sudo systemctl restart stock-api"
```

### Frontend (React)

```bash
# From local machine — copy source files
scp myfuture/src/pages/NewPage.tsx deploy@178.156.173.199:~/stock-planner/myfuture/src/pages/
scp myfuture/src/App.tsx deploy@178.156.173.199:~/stock-planner/myfuture/src/

# On server — rebuild
ssh deploy@178.156.173.199 "cd ~/stock-planner/myfuture && npm run build"
```

No restart needed — Nginx serves the new static files immediately.

## Data Layout

```
data/
├── prices_daily.csv          # Primary price data (US + SGX), updated daily
├── prices.csv                # Synced copy of prices_daily.csv
├── fundamentals.csv          # Quarterly fundamentals, refreshed weekly
├── analysis.db               # Analysis results
├── forward_journal.db        # Forward prediction tracking
├── runs.db                   # Backtest run history
├── auth.db                   # User sessions
├── sentimentpulse.db         # DuckDB — sentiment data (424+ tickers)
├── paper_trading_*.db        # One SQLite DB per watchlist portfolio
│   ├── portfolio_state       # Cash, initial value
│   ├── positions             # Active + closed positions
│   ├── trades                # All executed trades
│   ├── signals               # Model BUY/SELL signals
│   ├── daily_snapshots       # Daily equity snapshots
│   └── stop_loss_cooldown    # Stop-loss cooldown tracking
└── sentiment/
    ├── sentimentpulse_YYYY-MM-DD.csv  # Daily crawl exports
    ├── sentimentpulse.parquet         # Consolidated parquet
    ├── moby_picks.csv                 # Moby newsletter picks
    └── news.csv                       # News sentiment
```

## Active Portfolios

| Watchlist | Capital | Mode | Notes |
|-----------|---------|------|-------|
| moby_picks | $100K | Paper | Moby newsletter picks |
| tech_giants | $100K | Paper | FAANG+ |
| semiconductors | $100K | Paper | SOX constituents |
| precious_metals | $100K | Paper | Miners, ETFs, streaming cos |
| sg_reits | $100K | Paper | Singapore REITs |
| sg_blue_chips | $100K | Paper | Primary forward test |
| anthony_watchlist | $13.1K | Paper | Personal picks |
| sp500 | $100K | Paper | S&P 500 |
| clean_energy | $100K | Paper | Solar, wind, clean energy |
| etfs | $100K | Paper | Broad market ETFs |

## Risk Controls

- **Stop-loss**: -8% from entry price, 5-day cooldown before re-entry
- **Concentration limits**:
  - Diversified portfolios: max 40% in any single sector
  - Precious metals: max 2 miners, 1 streaming/royalty, 1 silver, 2 gold ETFs
  - sg_blue_chips: max 1 SG bank, max 2 SG REITs
- **Position dedup**: Skip BUY if ticker already held at same weight
- **Regime scaling**: 
  - VIX 20-30: 50% | VIX > 30: 25%
  - SPY 20d < -5%: 30% (reduce) | < -8%: 0% (exit to cash)
  - All scales are multiplicative (e.g. VIX 25 + SPY reduce = 50% x 30% = 15%)
- **DXY filter (precious_metals only)**: UUP 20d > +2%: 25% | 0-2%: 60% | < 0%: 100%. Multiplicative with VIX/SPY scales. Configured via `watchlist_overrides` in config.yaml.

## Environment Variables

Key variables in `/home/deploy/stock-planner/.env`:

- `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` — Alpaca paper trading (IEX feed)
- `GOOGLE_API_KEY` — Gemini for LLM commentary
- `SLACK_WEBHOOK_URL` — Daily run notifications
- `TRENDS_API_TOKEN` — Google Trends push endpoint auth
- `EODHD_API_KEY` — EOD Historical Data sentiment

## Monitoring

- **Health monitor** (cron, every 2h) checks job freshness: sentimentpulse crawl, daily pipeline, feedback eval, fundamentals, Google Trends. Alerts Slack on failure/staleness.
- **Heartbeat** (systemd timer, daily 8 AM) is the safety net — independent of cron. Checks: health monitor alive, daily pipeline ran, no portfolio failures, API up, trends ran. Always sends Slack (silence = broken).
- **OnFailure handlers**: `daily-routine.service` and `sentimentpulse-crawl.service` trigger Slack alerts via `slack-notify-failure@.service` if the process crashes.
- **Slack notifications**: Daily run summary, portfolio failures, heartbeat status all sent to Slack.

## Dashboard Pages

| Path | Page | Description |
|------|------|-------------|
| `/` | Dashboard | Overview with equity curves |
| `/portfolio-overview` | Portfolio P&L | All positions with live prices, P&L, cash, grand totals |
| `/daily-actions` | Daily Actions | Actionable BUY/SELL sheet per watchlist |
| `/paper-trading` | Paper Trading | Per-watchlist deep dive |
| `/forward-testing` | Forward Testing | Prediction accuracy tracking |
| `/multi-portfolio` | Multi-Portfolio | Normalized equity curve comparison |
| `/signals` | Signal Tracker | Latest BUY/SELL triggers with forward confirmation |
| `/moby` | Moby Analysis | Moby newsletter pick tracking |
| `/sentiment` | Sentiment | SentimentPulse composite scores |
| `/realtime-monitoring` | Monitoring | Real-time alerts and risk metrics |
| `/watchlists` | Watchlists | Browse and manage watchlists |
| `/recommendations` | Recommendations | AI-generated trade recommendations |
| `/settings` | Settings | System configuration |

## Troubleshooting

```bash
# Check API health
curl https://stockplanner.blueideas.net/api/health

# View API logs
ssh deploy@178.156.173.199 "journalctl -u stock-api --since '1 hour ago'"

# View daily pipeline log
ssh deploy@178.156.173.199 "tail -50 ~/stock-planner/logs/daily_cron.log"

# View health monitor log
ssh deploy@178.156.173.199 "tail -20 ~/stock-planner/logs/health_monitor.log"

# Check cron is running
ssh deploy@178.156.173.199 "sudo journalctl --unit=cron --since today | grep deploy"

# Rebuild frontend after changes
ssh deploy@178.156.173.199 "cd ~/stock-planner/myfuture && npm run build"

# Restart API after Python changes
ssh deploy@178.156.173.199 "sudo systemctl restart stock-api"
```
