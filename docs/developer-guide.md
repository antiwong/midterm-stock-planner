> [← Back to Documentation Index](README.md)

# Developer Guide

Onboarding guide for developers contributing to the Midterm Stock Planner.

---

### Prerequisites

- **Python 3.11+**
- **pip** (package manager)
- **Git**
- **4GB+ RAM** (model training and backtesting are memory-intensive)

---

### Setup

```bash
git clone <repo>
cd midterm-stock-planner
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config/config.yaml.example config/config.yaml  # if needed
```

---

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `ALPACA_API_KEY` | Alpaca paper trading API key |
| `ALPACA_SECRET_KEY` | Alpaca paper trading secret key |
| `FRED_API_KEY` | Federal Reserve macro data (FRED) |
| `GOOGLE_GENERATIVEAI_API_KEY` | Google Gemini AI insights |
| `NEWS_API_KEY` | News sentiment data |

Set these in your shell profile or a `.env` file (not committed to version control).

---

### Project Structure

```
src/
├── data/            — Data loading and management
├── features/        — Feature engineering pipelines
├── indicators/      — Technical indicators (RSI, MACD, etc.)
├── models/          — LightGBM training & prediction
├── backtest/        — Walk-forward backtesting engine
├── risk/            — Risk metrics, position sizing, risk parity
├── regression/      — Feature regression testing
├── trading/         — Alpaca broker integration
├── analysis/        — Comprehensive analysis workflows
├── app/             — Streamlit dashboard
└── visualization/   — Charts and plotting utilities
```

---

### Running Tests

```bash
pytest tests/ -v
pytest tests/ --cov=src
```

208+ tests, 100% pass rate.

---

### Key Scripts

| Script | Purpose |
|--------|---------|
| `scripts/paper_trading.py` | Daily paper trading pipeline |
| `scripts/run_regression_test.py` | Feature regression testing |
| `scripts/download_prices.py` | Price data fetching |
| `scripts/optimize_all_tickers.py` | Bayesian parameter optimization |

---

### Configuration

See [Configuration Reference](configuration-reference.md) for full details on `config/config.yaml`, watchlists, and per-ticker overrides.

---

### See Also

- [Quick Start Guide](quick-start-guide.md)
- [Configuration Reference](configuration-reference.md)
- [Common Workflows](common-workflows.md)
- [Troubleshooting](troubleshooting.md)
- [Test Suite Documentation](test-suite-documentation.md)
- [Regression Testing Guide](regression-testing-guide.md)
