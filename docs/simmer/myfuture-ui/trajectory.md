# myFuture UI Simmer Trajectory

| Iter | Data Density | Mobile Polish | Visual Quality | Charting | Composite | Key Change |
|------|-------------|---------------|----------------|----------|-----------|------------|
| 0    | 6           | 5             | 5              | 1        | 4.3       | seed       |
| 1    | 7           | 6             | 7              | 5        | 6.3       | Lucide icons, skeletons, sparklines, overflow-x tables |
| 2    | 7           | 7             | 7              | 6        | 6.8       | Equity curve, P&L columns, mobile touch fixes, card elevation |
| 3    | 8           | 8             | 7              | 7        | 7.5       | Per-portfolio curves, sortable table, bottom tab bar, empty states |

| 4    | 8           | 7             | 7              | 6        | 7.0       | Real API data, leaderboard, error cards |
| 5    | 8           | 8             | 8              | 7        | 7.8       | Benchmark overlay, risk chips, polling spinner |
| 6    | 8           | 8             | 8              | 7        | 7.8       | XAxis date labels, focus-visible rings, nav a11y |

## Post-simmer polish (items 1-4)
- Per-portfolio unique curve seeds (watchlist name as seed)
- Real OHLC price data wired into sparklines via `/prices/{ticker}` API
- Real equity history wired into curves via `/portfolios/{watchlist}/snapshots` API
- Grand total equity aggregated from all watchlist snapshots
- Return leaderboard with rank badges (gold/silver/bronze) and horizontal comparison bars
- Styled ErrorCard component with AlertTriangle icon + retry button (replaces bare text errors)
