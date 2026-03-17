# Alpaca Trade Execution

> [← Daily Run Index](README.md) | [← Documentation Index](../README.md)

When Alpaca API keys are configured, the daily pipeline places real orders on Alpaca's paper trading platform. Otherwise, it falls back to local simulation.

**Source:** `src/trading/alpaca_broker.py`, `scripts/paper_trading.py`

---

## Execution Modes

| Mode | Trigger | Fills | Costs | Timing |
|------|---------|-------|-------|--------|
| **Alpaca Paper** | `ALPACA_API_KEY` env var set | Realistic market simulation | Free | Market hours only |
| **Local Simulation** | No API keys or `--local` flag | Instant at close price | 0.1% per trade | Any time |

---

## Alpaca Rebalancing Algorithm

The `AlpacaBroker.rebalance_portfolio()` method implements target-weight rebalancing:

```python
def rebalance_portfolio(target_weights):
    # 1. Get current account state
    account = get_account()           # Cash, equity, buying power
    positions = get_positions()       # {ticker: {qty, avg_cost, market_value}}

    # 2. Calculate current weights
    total_equity = account.equity
    current_weights = {ticker: pos.market_value / total_equity for ticker, pos in positions}

    # 3. Determine trades needed
    for ticker in union(current_weights, target_weights):
        target = target_weights.get(ticker, 0)     # 0 if not in target = close position
        current = current_weights.get(ticker, 0)

        delta_value = (target - current) * total_equity
        delta_shares = delta_value / current_price[ticker]

        if abs(delta_value) < 50:    # Skip tiny rebalances
            continue

        if delta_shares > 0:
            submit_order(ticker, qty=delta_shares, side='buy')
        elif delta_shares < 0:
            submit_order(ticker, qty=abs(delta_shares), side='sell')

    # 4. Sync state back to local DB
    sync_positions_to_db()
```

### Order Execution

| Parameter | Value |
|-----------|-------|
| Order type | Market |
| Time in force | DAY (cancels if unfilled by close) |
| Fractional shares | Supported |
| Minimum rebalance | $50 (skip smaller adjustments) |

### Execution Sequence

```
1. SELL positions NOT in target weights (full liquidation)
2. SELL excess shares in over-weight positions
3. BUY shares in under-weight positions
4. BUY shares in new positions
```

Sells execute before buys to free up capital.

---

## Local Simulation

When Alpaca keys are not configured:

```python
def simulate_trade(ticker, shares, price, side):
    if side == 'buy':
        cost = shares * price * (1 + transaction_cost)    # 0.1% cost
        cash -= cost
        positions[ticker] += shares
    elif side == 'sell':
        proceeds = shares * price * (1 - transaction_cost)
        cash += proceeds
        positions[ticker] -= shares
```

**Transaction cost:** 0.1% per trade (approximates bid-ask spread + any commission). This is conservative — Alpaca paper trading has zero commissions.

---

## State Synchronization

After each trade execution (Alpaca or local), the system syncs state to `paper_trading.db`:

| Table | What's Updated |
|-------|---------------|
| `portfolio_state` | Cash balance, total equity, last update time |
| `positions` | Active positions (qty, avg cost, current price, unrealized PnL) |
| `trades` | New trade records (date, ticker, action, shares, price, value) |

For Alpaca mode, the system queries Alpaca's actual filled orders and account state — it doesn't trust its own calculations, it uses Alpaca as the source of truth.

---

## Setup

### Environment Variables

```bash
export ALPACA_API_KEY="your-key-here"
export ALPACA_SECRET_KEY="your-secret-here"
```

Or add to `.env` file in the project root.

### Verify Connection

```bash
python scripts/paper_trading.py account
```

### Force Local Mode

```bash
python scripts/paper_trading.py run --watchlist tech_giants --local
```

---

## See Also

- [Pipeline Overview](pipeline-overview.md) — full execution flow
- [Position Sizing](position-sizing.md) — how target weights are determined
- [Risk Controls](risk-controls.md) — rules enforced before execution
- [Alpaca Paper Trading](../alpaca-paper-trading.md) — full Alpaca setup guide
