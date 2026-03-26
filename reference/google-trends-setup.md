# Google Trends Local Fetcher — Setup & Operations

## Architecture

Google Trends blocks datacenter IPs (Hetzner gets HTTP 400). Solution:

```
Mac (residential IP)                    Hetzner Server
─────────────────                       ──────────────
fetch_google_trends_local.py            POST /api/sentiment/trends-update
  ↓ pytrends API                          ↓
  ↓ batch of 5, 15s delay                DuckDB sentiment_features
  ↓                                        (trends_interest_7d,
  → HTTP POST with Bearer token ────────→   trends_interest_30d,
                                            trends_7d_change,
                                            trends_spike_flag)
```

## Files

| Location | File | Purpose |
|----------|------|---------|
| Local | `scripts/fetch_google_trends_local.py` | Fetches trends, pushes to server |
| Server | `src/api/routers/sentiment.py` | `POST /api/sentiment/trends-update` endpoint |
| Server | `src/api/main.py` | Path whitelisted in `PUBLIC_PATHS` |

## Environment Variables

### Mac (`~/.sentimentpulse.env`)
```bash
SENTIMENT_SERVER_URL=http://178.156.173.199:9000
SENTIMENT_API_TOKEN=4peYJ6snKbt2eVXdF8eF-zoQKGhr7i1Sg7PV9_YNv4s
WATCHLISTS_PATH=~/Documents/code/my_code/stock_all/midterm-stock-planner/config/watchlists.yaml
```

### Hetzner Server
```bash
# In /home/deploy/stock-planner/.env AND /home/deploy/sentimental_blogs/.env
TRENDS_API_TOKEN=4peYJ6snKbt2eVXdF8eF-zoQKGhr7i1Sg7PV9_YNv4s
HETZNER_SERVER=1
```

## Usage

```bash
# Dry run (fetch + print, no push)
python3 scripts/fetch_google_trends_local.py --dry-run

# Single watchlist
python3 scripts/fetch_google_trends_local.py --watchlist tech_giants

# All tickers (20-25 min)
python3 scripts/fetch_google_trends_local.py

# Custom delay between batches
python3 scripts/fetch_google_trends_local.py --delay 20
```

## Mac Crontab

```bash
# Daily at 7:00 AM SGT
0 7 * * * source ~/.sentimentpulse.env && \
  cd ~/Documents/code/my_code/stock_all/midterm-stock-planner && \
  .venv/bin/python scripts/fetch_google_trends_local.py \
  >> ~/Library/Logs/trends.log 2>&1
```

## Verification

```bash
# On server — check DuckDB for non-zero trends
ssh stock-planner "/home/deploy/sentimental_blogs/.venv/bin/python3 -c \"
import duckdb
conn = duckdb.connect('/home/deploy/stock-planner/data/sentimentpulse.db', read_only=True)
rows = conn.execute('''
    SELECT ticker, date, trends_interest_7d, trends_spike_flag
    FROM sentiment_features
    WHERE trends_interest_7d > 0
    ORDER BY date DESC LIMIT 10
''').fetchall()
print(f'Rows with trends data: {len(rows)}')
for r in rows:
    print(f'  {r[0]:10s} {r[1]}  7d={r[2]:.1f}  spike={r[3]}')
conn.close()
\""
```

## Server Changes (2026-03-26)

- `FMP_API_KEY` commented out in `.env` (deprecated Aug 2025)
- Tavily: already routing through MySearch-Proxy, no change needed
- `HETZNER_SERVER=1` added to skip pytrends on server
- `TRENDS_API_TOKEN` added to both server `.env` files
