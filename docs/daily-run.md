# Daily Run Guide

**Date**: 2026-03-15
**Script**: `scripts/paper_trading.py`
**Database**: `data/paper_trading.db`

---

## Overview

The daily run pipeline generates trading signals and tracks simulated portfolio performance without risking real money. It runs after market close each day:

1. **Refresh data** — Download latest daily prices
2. **Retrain model** — Walk-forward backtest on updated data
3. **Generate signals** — Rank all stocks, identify top 5 to buy
4. **Execute trades** — Simulate buying/selling with transaction costs
5. **Track P&L** — Log portfolio value, positions, and returns to SQLite

---

## Quick Start

```bash
# First run — generates signals and creates initial portfolio ($100K paper money)
python scripts/paper_trading.py run --watchlist tech_giants

# Check your portfolio
python scripts/paper_trading.py status

# View trade history
python scripts/paper_trading.py history --last 30

# Automate (runs 5:30 PM ET every weekday)
python scripts/paper_trading.py setup-cron
```

---

## Commands

### `run` — Daily Signal Generation

```bash
python scripts/paper_trading.py run --watchlist tech_giants
```

This is the main command. Run it once per trading day after market close.

**What it does:**
1. Downloads latest price data for the watchlist (appends to `data/prices_daily.csv`)
2. Computes features using the optimal set (MACD, Bollinger Bands, ATR, ADX — RSI/momentum/OBV disabled)
3. Runs walk-forward backtest to train the LightGBM ranking model
4. Extracts the latest predictions and ranks all stocks
5. Identifies top 5 stocks (BUY signals) and bottom stocks (SELL signals)
6. Simulates execution: sells positions not in top 5, buys new top-5 stocks
7. Applies position sizing: 20% max per stock, 15% stop-loss, VIX-based exposure scaling
8. Logs everything to `data/paper_trading.db`

**Options:**
- `--watchlist tech_giants` — Which stocks to trade (default: tech_giants = 13 US tech stocks)
- `--skip-refresh` — Skip data download (use existing data)
- `--capital 100000` — Starting capital (default: $100,000)

**Output example:**
```
============================================================
Paper Trading - 2026-03-15 17:30
============================================================
Refreshing price data...
Data refreshed: 13 rows appended.

Generating signals...
Computing features for 13 tickers...
Running walk-forward backtest (24 features)...
Backtest complete in 142s. Sharpe=1.34

Top signals:
  BUY  NVDA    score=0.8421  rank=1
  BUY  AMD     score=0.7834  rank=2
  BUY  META    score=0.6912  rank=3
  BUY  MSFT    score=0.6501  rank=4
  BUY  AAPL    score=0.5890  rank=5
  SELL INTC    score=0.1234  rank=6
  SELL ORCL    score=0.0987  rank=7
  ...

Executing trades...
  BUY  NVDA : 15.2 shares @ $892.40 (weight: 20.0%)
  BUY  AMD  : 82.1 shares @ $178.30 (weight: 18.5%)
  BUY  META : 28.4 shares @ $523.10 (weight: 19.2%)
  BUY  MSFT : 31.7 shares @ $412.80 (weight: 17.8%)
  BUY  AAPL : 57.3 shares @ $198.50 (weight: 15.5%)

Portfolio: $100,000.00 (return: +0.00%)
Cash: $9,012.45 | Invested: $90,987.55
Positions: 5 | Trades today: 5

Done.
```

### `status` — Portfolio Status

```bash
python scripts/paper_trading.py status
```

Shows current holdings, P&L, and recent performance.

**Output example:**
```
============================================================
Paper Trading Portfolio Status
============================================================
Portfolio Value: $103,421.50
Cash:           $9,012.45
Invested:       $94,409.05
Total Return:   +3.42%
Initial Value:  $100,000.00
Last Updated:   2026-03-15T17:30:00

Positions (5):
Ticker    Shares    Entry  Current        PnL   Weight
------------------------------------------------------------
NVDA        15.2  $892.40  $921.30   +$439.69    20.0%
AMD         82.1  $178.30  $185.20   +$566.49    18.5%
META        28.4  $523.10  $531.80   +$247.08    19.2%
MSFT        31.7  $412.80  $418.50   +$180.69    17.8%
AAPL        57.3  $198.50  $195.20   -$189.09    15.5%

Recent Performance:
Date          Value     Daily  Cumulative
--------------------------------------------------
2026-03-15  $103,421   +0.82%      +3.42%
2026-03-14  $102,578   +1.23%      +2.58%
2026-03-13  $101,325   -0.41%      +1.33%
```

### `history` — Trade History

```bash
python scripts/paper_trading.py history --last 30
```

Shows recent trades with prices and costs.

### `refresh` — Data Only

```bash
python scripts/paper_trading.py refresh --watchlist tech_giants
```

Downloads latest prices without generating signals or trading. Useful for debugging data issues.

### `setup-cron` — Automate Daily Runs

```bash
python scripts/paper_trading.py setup-cron
```

Prints the crontab line to add. Runs at 5:30 PM ET every weekday (after market close).

---

## Configuration

The paper trading pipeline reads from `config/config.yaml`. Key settings:

### Feature Set (what the model uses)

```yaml
features:
  include_technical: true      # MACD, Bollinger, ATR, ADX (always on)
  include_rsi: false           # Disabled — hurts cross-sectional model
  include_obv: false           # Disabled — hurts cross-sectional model
  include_momentum: false      # Disabled — hurts cross-sectional model
  include_mean_reversion: false # Disabled — adds noise
```

These were validated by regression test `reg_20260315_152332` on tech_giants:
- Bollinger: +0.64 Sharpe (best feature)
- MACD: +0.15 Sharpe
- ADX: +0.08 Sharpe
- RSI: -0.28, Momentum: -0.24, OBV: -0.18 (all disabled)

### Portfolio Construction

```yaml
backtest:
  top_n: 5                     # Hold top 5 stocks
  max_position_weight: 0.20    # Max 20% in any single stock
  stop_loss_pct: -0.15         # Exit if stock drops 15% from entry
  transaction_cost: 0.001      # 0.1% per trade (bid-ask + commission)
  vix_scale_enabled: true      # Reduce exposure during high volatility
  vix_high_threshold: 30.0     # VIX > 30 → reduce to 60% exposure
  vix_extreme_threshold: 40.0  # VIX > 40 → reduce to 30% exposure
```

### Model (LightGBM)

```yaml
model:
  params:
    n_estimators: 200
    learning_rate: 0.03
    max_depth: 6
    num_leaves: 15
    min_child_samples: 50
    reg_alpha: 0.3
    reg_lambda: 0.5
    subsample: 0.7
    colsample_bytree: 0.7
    early_stopping_rounds: 30
```

---

## How Signals Are Generated

The pipeline uses a **cross-sectional ranking model**:

1. **Walk-forward backtest**: Train on 3 years of daily data, test on 6 months, step forward 7 days. This creates ~265 overlapping windows.

2. **Per window**: LightGBM learns to predict which stocks will have the highest excess returns (vs SPY benchmark) over the next 63 trading days.

3. **Final scores**: The latest window's predictions are extracted. Each stock gets a score — higher = more likely to outperform.

4. **Portfolio**: Top 5 stocks by score are selected. Weights are proportional to scores, capped at 20%.

5. **Risk controls**:
   - **Max position weight**: No stock exceeds 20% of portfolio
   - **Stop-loss**: If a stock drops 15% from entry, it's sold
   - **VIX scaling**: When market volatility is high (benchmark 21-day vol > 30 annualized), exposure is reduced to 60%. Above 40, reduced to 30%.

---

## Database Schema

All paper trading state lives in `data/paper_trading.db`:

| Table | Purpose |
|-------|---------|
| `portfolio_state` | Cash balance, initial value, last update time |
| `positions` | Active and closed positions (ticker, shares, entry/exit price, PnL) |
| `trades` | Every simulated trade (date, action, shares, price, cost) |
| `daily_snapshots` | End-of-day portfolio value, returns, positions, signals |
| `signals` | Every signal generated (ticker, prediction score, rank, action) |

---

## Watchlists

Available watchlists (defined in `config/watchlists.yaml`):

| Watchlist | Stocks | Description |
|-----------|--------|-------------|
| `tech_giants` | 13 | AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, AMD, INTC, ORCL, CRM, ADBE, NFLX |
| `sp500` | ~500 | S&P 500 constituents |
| `nasdaq_100` | ~100 | NASDAQ-100 constituents |

Default: `tech_giants` (validated by regression testing).

---

## Interpreting Results

### What a Good Day Looks Like

- **Daily return > 0**: Portfolio gained value
- **Excess return > 0**: Portfolio beat SPY
- **Low turnover**: Few trades means the model's conviction is stable

### Warning Signs

- **Consecutive negative days**: Model may be in a regime shift — check IC regime detection
- **High turnover**: Many trades per day = model is uncertain, transaction costs are eating returns
- **All positions hitting stop-loss**: Market crash or model breakdown — consider pausing

### Expected Performance

Based on the regression test (tech_giants, 2016-2026):
- **Sharpe ratio**: ~1.34 (optimal feature set)
- **Total return**: ~959% over 10 years
- **Max drawdown**: -55% to -72% (this is the main risk — position sizing helps but doesn't eliminate it)
- **Turnover**: Moderate (monthly rebalancing)

**Important**: Paper trading results will differ from backtest because:
1. Backtest has look-ahead bias in target construction
2. Real-time data may have gaps or delays
3. Walk-forward retraining uses all available history, not fixed windows

---

## Troubleshooting

### "No signals generated"

- Check that `data/prices_daily.csv` has recent data
- Run `python scripts/paper_trading.py refresh` to update data
- Verify the watchlist has tickers present in the price data

### "Data refresh failed"

- Check internet connection
- Alpaca API key may have expired (see `scripts/download_prices.py`)
- yfinance fallback may be rate-limited — try again in a few minutes

### "No new data downloaded"

- Markets are closed (weekends, holidays)
- Run on the next trading day

### Resetting the Paper Portfolio

Delete the database to start fresh:
```bash
rm data/paper_trading.db
python scripts/paper_trading.py run --watchlist tech_giants --capital 100000
```

---

## Automation

### macOS/Linux (cron)

```bash
# Generate the cron line
python scripts/paper_trading.py setup-cron

# Add to crontab
crontab -e
# Paste the line, save, and exit
```

Runs at 5:30 PM ET (22:30 UTC) every weekday. Logs go to `logs/paper_trading.log`.

### Manual Daily Routine

If you prefer running manually:

```bash
# After market close (~4:30 PM ET)
cd /path/to/midterm-stock-planner

# 1. Update data
python scripts/paper_trading.py refresh

# 2. Generate signals and execute
python scripts/paper_trading.py run --watchlist tech_giants --skip-refresh

# 3. Review
python scripts/paper_trading.py status
```
