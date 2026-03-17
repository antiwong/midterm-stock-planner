# Daily Routine Orchestrator

> [<- Daily Run Index](README.md) | [<- Documentation Index](../README.md)

Single script replacing 5 separate cron jobs. Runs all 4 portfolios, data downloads, forward prediction journal, and notifications in one invocation.

**Script:** `scripts/daily_routine.py`
**Database:** `data/forward_journal.db` (predictions), `data/paper_trading_{watchlist}.db` (per-portfolio)

---

## Quick Start

```bash
# Daily routine (after US market close)
python scripts/daily_routine.py daily

# Weekly review (Sunday)
python scripts/daily_routine.py weekly

# Monthly maintenance (1st of month)
python scripts/daily_routine.py monthly

# Dry run (log without executing)
python scripts/daily_routine.py daily --dry-run
```

---

## Modes

### Daily

Runs after US market close (weekdays only, skips holidays).

| Step | What It Does | Failure Handling |
|------|-------------|------------------|
| 1. Data refresh | Download prices for all tickers across 4 watchlists (deduplicated) | Logs error, continues |
| 2. Sentiment | Download Finnhub data + score articles | Skips if no FINNHUB_API_KEY |
| 3. Moby parse | Parse Gmail for Moby newsletter picks | Skips if no MOBY_APP_PASSWORD |
| 4. Portfolio runs | Run 4 portfolios sequentially (moby=Alpaca, rest=local) | Each isolated — one failure doesn't stop others |
| 5. Forward journal | Log predictions at 5-day and 63-day horizons | INSERT OR IGNORE for idempotency |
| 6. Evaluate matured | Check predictions whose maturity date has passed | Updates actual_return and hit fields |
| 7. Notify | Send summary to Slack + Google Chat | Continues if webhook fails |

### Weekly

Performance review and forward test summary.

| Step | What It Does |
|------|-------------|
| 1. Weekly report | 4 portfolios side-by-side: value, weekly return, total return |
| 2. Drift check | Flag positions exceeding 30% weight |
| 3. Forward review | Hit rates by watchlist and horizon for the past 7 days |

### Monthly

Maintenance and long-horizon evaluation.

| Step | What It Does |
|------|-------------|
| 1. Fundamentals | Download PE/PB/ROE for all tickers |
| 2. 63-day evaluation | Evaluate predictions whose 63-day maturity has passed |

---

## Portfolios

| Watchlist | Tickers | Execution | DB File |
|-----------|---------|-----------|---------|
| `moby_picks` | 56 | Alpaca paper trading | `data/paper_trading_moby_picks.db` |
| `tech_giants` | 13 | Local simulation | `data/paper_trading_tech_giants.db` |
| `semiconductors` | 25 | Local simulation | `data/paper_trading_semiconductors.db` |
| `precious_metals` | 31 | Local simulation | `data/paper_trading_precious_metals.db` |

Each portfolio gets its own SQLite database. The orchestrator refreshes price data once for the union of all tickers (~100+ unique), then each portfolio runs with `--skip-refresh`.

---

## Cron Configuration (SGT)

This PC is in Singapore (UTC+8). US market closes at 4:00 PM ET.

**Day mapping**: SGT Tuesday 6:30 AM = ET Monday 5:30 PM (Monday market close).

```crontab
# Daily: Tue-Sat 6:30 AM SGT (= Mon-Fri 5:30 PM ET)
30 6 * * 2-6 cd /home/antiwong/code/midterm-stock-planner && python scripts/daily_routine.py daily >> logs/daily_routine.log 2>&1

# Weekly: Sunday 10:00 AM SGT
0 10 * * 0 cd /home/antiwong/code/midterm-stock-planner && python scripts/daily_routine.py weekly >> logs/weekly_routine.log 2>&1

# Monthly: 1st of month 10:00 AM SGT
0 10 1 * * cd /home/antiwong/code/midterm-stock-planner && python scripts/daily_routine.py monthly >> logs/monthly_routine.log 2>&1
```

The script also checks `is_us_trading_day()` at the start of daily runs and exits early for US holidays.

---

## Environment Variables

Required in `.env`:

```bash
# Alpaca Paper Trading (moby_picks portfolio)
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret

# Finnhub Sentiment Data
FINNHUB_API_KEY=your_key

# Moby Email Parsing (optional)
MOBY_EMAIL=antiwongmoby@gmail.com
MOBY_APP_PASSWORD=your_gmail_app_password

# Notifications (optional — both used if set)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/...
```

Missing keys cause the corresponding step to skip gracefully (not fail).

---

## Notifications

The orchestrator posts a summary to both Slack and Google Chat after each run. Both accept the same `{"text": "..."}` webhook format.

Example daily notification:

```
Daily Routine Complete -- 2026-03-17

PORTFOLIOS
  moby_picks           $102,340 (+2.34%) -- Alpaca
  tech_giants          $101,890 (+1.89%) -- Local
  semiconductors        $98,450 (-1.55%) -- Local
  precious_metals      $103,120 (+3.12%) -- Local

PREDICTIONS LOGGED: 248
PREDICTIONS EVALUATED: 12
SENTIMENT: success
MOBY PARSE: success (3 picks)
```

---

## Logging

Logs are written to `logs/` with daily rotation:

| File | Content |
|------|---------|
| `logs/daily_routine_YYYYMMDD.log` | Daily run output |
| `logs/weekly_routine_YYYYMMDD.log` | Weekly run output |
| `logs/monthly_routine_YYYYMMDD.log` | Monthly run output |

All output also goes to stdout for cron capture.

---

## Error Isolation

Each portfolio run is wrapped in try/except. If `semiconductors` fails, `precious_metals` still runs. The failure is:
1. Logged to file
2. Reported in the notification summary
3. Reported as `"status": "error"` in the results dict

---

## See Also

- [Forward Testing](forward-testing.md) — prediction journal schema and evaluation
- [Pipeline Overview](pipeline-overview.md) — how each portfolio run works internally
- [Signal Generation](signal-generation.md) — ML + trigger ensemble
- [Risk Controls](risk-controls.md) — drawdown, stop-loss, VIX scaling
