# React Trading Dashboard

> [<- Daily Run Index](README.md) | [<- Documentation Index](../README.md)

Separate React SPA for daily trading use. Runs alongside the Streamlit analysis dashboard.

**Frontend:** `http://localhost:5000` (Vite + React + TypeScript + Tailwind + Recharts)
**Backend:** `http://localhost:9000` (FastAPI, read-only access to SQLite DBs)
**Source:** `trading-dashboard/` (React), `src/api/` (FastAPI)

---

## Quick Start

```bash
# Start backend (from project root)
uvicorn src.api.main:app --port 9000 &

# Start frontend
cd trading-dashboard && npm run dev

# Open http://localhost:5000
```

---

## Pages

| Page | URL | What It Shows |
|------|-----|---------------|
| **Dashboard** | `/` | 4 portfolio cards (value, return, positions), summary table |
| **Paper Trading** | `/paper-trading` | Positions, equity curve vs SPY, daily P&L, signals, trade history |
| **Forward Testing** | `/forward-testing` | Prediction stats, hit rates, BUY/SELL breakdown by watchlist |
| **Multi-Portfolio** | `/multi-portfolio` | Overlay equity curves, comparison table, position overlap |
| **Moby Analysis** | `/moby` | Price target cards, upside chart, performance vs target |

---

## API Endpoints

All endpoints are read-only GET requests on port 9000.

| Route | Returns |
|-------|---------|
| `/api/health` | `{"status": "ok"}` |
| `/api/portfolios/summary` | All 4 portfolios: value, return, positions count |
| `/api/portfolios/{wl}/positions` | Active positions for one watchlist |
| `/api/portfolios/{wl}/trades?limit=50` | Trade history |
| `/api/portfolios/{wl}/snapshots?days=90` | Daily snapshots for equity curve |
| `/api/portfolios/{wl}/signals` | Latest BUY/SELL signals |
| `/api/forward/predictions?watchlist=all&horizon=5&status=active` | Forward journal |
| `/api/forward/accuracy` | Hit rates by watchlist/horizon |
| `/api/forward/trend?horizon=5` | Rolling hit rate over time |
| `/api/prices/{ticker}?days=90` | OHLCV data for charting |
| `/api/prices/multi/batch?tickers=KMX,BKNG&days=90` | Multiple tickers |
| `/api/moby/analysis` | Moby analyst picks with targets |
| `/api/moby/performance` | Picks vs actual prices |

Data sources: `data/paper_trading_{watchlist}.db`, `data/forward_journal.db`, `data/prices_daily.csv`, `data/sentiment/moby_analysis.csv`

---

## Architecture

```
React SPA (port 5000) --> Vite proxy --> FastAPI (port 9000) --> SQLite DBs + CSV
```

- Vite proxies `/api/*` to `http://localhost:9000` during development
- FastAPI has CORS enabled for `http://localhost:5000`
- Price data (280K rows) cached in memory on first request (~50MB)
- Auto-refresh: frontend polls every 60 seconds

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vite 8 + React 18 + TypeScript |
| Styling | Tailwind CSS 3 (dark theme) |
| Charts | Recharts (LineChart, BarChart, ComposedChart) |
| Routing | React Router 6 |
| Backend | FastAPI + uvicorn |
| Data | sqlite3 (stdlib) + pandas (price cache) |

---

## Development

```bash
# Frontend dev (hot reload)
cd trading-dashboard && npm run dev

# Backend dev (auto reload)
uvicorn src.api.main:app --port 9000 --reload

# Test API
curl http://localhost:9000/api/portfolios/summary | python3 -m json.tool
```

---

## See Also

- [Orchestrator](orchestrator.md) — daily routine that populates the databases
- [Forward Testing](forward-testing.md) — prediction journal schema
- [Dashboard (Streamlit)](../dashboard.md) — analysis dashboard at port 8502
