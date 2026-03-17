> [← Back to Documentation Index](README.md)

# Common Workflows

Step-by-step recipes for frequent tasks.

---

### 1. Run Daily Paper Trading

```bash
python scripts/paper_trading.py run --watchlist tech_giants
python scripts/paper_trading.py status
```

---

### 2. Add a New Stock Symbol

1. Edit `config/watchlists.yaml` or use the GUI Watchlist Manager in the dashboard.
2. Validate: `python scripts/validate_watchlist.py <watchlist>`
3. Download data: `python scripts/download_prices.py --watchlist <watchlist>`
4. Download fundamentals: `python scripts/download_fundamentals.py --watchlist <watchlist>`

---

### 3. Optimize a Ticker's Parameters

```bash
python scripts/optimize_all_tickers.py --tickers AAPL --n-calls 40 --metric sharpe
```

Results saved to `config/tickers/AAPL.yaml` and `output/best_params_AAPL.json`.

---

### 4. Run a Regression Test

```bash
python scripts/run_regression_test.py run --watchlist tech_giants
python scripts/run_regression_test.py leaderboard
```

Takes 40-120 minutes. Tests each feature's marginal Sharpe contribution.

---

### 5. Debug a Bad Signal

1. **Check IC regime:** `python scripts/run_regression_test.py report <id>` — look for z-score < -2.0.
2. **Check accuracy log:** `python scripts/paper_trading.py status` — look at hit rate.
3. **Check VIX level:** High VIX reduces exposure automatically.
4. **If persistent:** re-run a regression test to validate features.

---

### 6. Download Fresh Data

```bash
python scripts/download_prices.py --watchlist tech_giants
python scripts/download_fundamentals.py --watchlist tech_giants
python scripts/download_macro.py
```

---

### 7. Launch the Dashboard

```bash
streamlit run src/app/dashboard.py
# or: python scripts/run_dashboard.py
```

---

### 8. Adjust Risk Parameters

Edit `config/config.yaml`:

| Parameter | Purpose |
|-----------|---------|
| `backtest.max_position_weight` | Concentration cap per position |
| `backtest.stop_loss_pct` | Stop-loss threshold |
| `backtest.vix_high_threshold` | VIX level to begin scaling down exposure |
| `backtest.vix_extreme_threshold` | VIX level for maximum exposure reduction |

---

### See Also

- [Quick Start Guide](quick-start-guide.md)
- [Configuration Reference](configuration-reference.md)
- [Troubleshooting](troubleshooting.md)
- [Developer Guide](developer-guide.md)
- [Risk Management](risk-management.md)
- [Regression Testing Guide](regression-testing-guide.md)
