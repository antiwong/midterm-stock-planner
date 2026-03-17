> [← Back to Documentation Index](README.md)

# Troubleshooting Guide

Consolidated troubleshooting reference for common issues encountered when using the Midterm Stock Planner.

---

### Data Issues

**"No price data found"**
- Verify that `data/prices_daily.csv` exists and contains data for your watchlist symbols.
- Run `python scripts/download_prices.py --watchlist <watchlist>` to fetch missing data.

**"Data refresh failed"**
- Check your internet connection.
- Verify Alpaca API keys are set (`ALPACA_API_KEY`, `ALPACA_SECRET_KEY`).
- yfinance may be rate-limiting requests — wait a few minutes and retry.

**"No new data downloaded"**
- Markets are closed on weekends and US holidays. No new data will be available outside trading days.

**"Symbol not found"**
- Check ticker format: use `BRK-B` (not `BRK.B`).
- Confirm the symbol is not delisted.
- Known delisted symbols:
  - **ATVI** — Acquired by Microsoft (2023)
  - **SPLK** — Acquired by Cisco (2024)
  - **PXD** — Acquired by Exxon (2023)

---

### Model & Signal Issues

**"No signals generated"**
- Confirm `data/prices_daily.csv` has recent price data. Run a data refresh if stale.
- Check that your watchlist contains valid, active symbols.

**"Insufficient data for walk-forward"**
- Walk-forward backtesting requires 5+ years of history. Verify the date range in your config covers enough history.

**High turnover / unstable signals**
- The model may be in an uncertain regime. Check the IC (Information Coefficient) regime in the regression report.
- Consider running a regression test to validate feature stability.

---

### Dashboard Issues

**"Dashboard won't start"**
- Confirm Python 3.11+ is installed: `python --version`
- Ensure dependencies are installed: `pip install -r requirements.txt`
- Check if port 8501 is already in use: `lsof -i :8501`. Kill the conflicting process or specify a different port.

**"Module not found"**
- Make sure you are running inside the virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

**Charts not loading**
- Clear your browser cache and reload.
- Enable lazy load mode in dashboard settings to reduce initial load.

**Slow performance**
- Reduce watchlist size to fewer symbols.
- Enable lazy loading for charts and data tables.

---

### Trading Issues

**"Alpaca connection failed"**
- Verify environment variables are set: `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`.
- Ensure `paper=True` is set for paper trading (not live).
- Check Alpaca API status at https://status.alpaca.markets.

**Orders not executing**
- US market hours are 9:30 AM – 4:00 PM ET. Orders submitted outside these hours will queue until market open.

---

### Database Issues

**"Database errors"**
- Check file permissions on `data/` directory and `.db` files.
- Run the migration script if the schema has changed.

**Reset paper portfolio**
```bash
rm data/paper_trading.db
python scripts/paper_trading.py run --watchlist <watchlist>
```
This removes all paper trading history and starts fresh.

---

### Configuration Issues

**"Config file not found"**
```bash
cp config/config.yaml.example config/config.yaml
```
Then edit `config/config.yaml` with your settings.

**YAML syntax errors**
- Validate your YAML with an online validator or `python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"`.
- Common mistakes: incorrect indentation, missing colons, unquoted special characters.

---

### See Also

- [Quick Start Guide](quick-start-guide.md)
- [Configuration Reference](configuration-reference.md)
- [FAQ](faq.md)
- [Developer Guide](developer-guide.md)
- [Alpaca Paper Trading](alpaca-paper-trading.md)
- [Data Providers Guide](data-providers-guide.md)
