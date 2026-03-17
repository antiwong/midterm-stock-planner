# Cross-Asset Capital Rotation Features

> [← Back to Documentation Index](README.md)

## Motivation
Inspired by capital rotation thesis: when gold/silver rallies exhaust, capital rotates into equities/crypto. These features capture this as systematic, testable signals.

## Features

All rotation features are **macro** (same value for all stocks on a given date):

| Feature | Formula | Rationale |
|---------|---------|-----------|
| `gold_momentum_20d` | GLD 20d return | Gold rally strength |
| `gold_momentum_decay` | delta(gold_momentum) over 5d | Detects when gold rally is exhausting |
| `gold_spy_relative_momentum` | GLD 20d return - SPY 20d return | When high & declining -> rotation signal |
| `safe_haven_flow` | avg(GLD ret, TIP ret) - SPY ret | Positive = safety flow; negative = risk-on |
| `cross_asset_momentum_dispersion` | std(GLD, TIP, UUP, SPY returns) | High = strong rotation in progress |
| `btc_momentum_20d` | BTC-USD 20d return | Crypto rotation target |
| `btc_gold_relative` | BTC ret - GLD ret | "Digital gold" rotation |

## Configuration
In `config/config.yaml` under `features.cross_asset`:
```yaml
rotation_lookback: 20     # Tunable 10-42d
include_btc: true         # Include BTC-USD features
```

## Regression Testing
```bash
python scripts/run_regression_test.py run --watchlist tech_giants --features rotation
```

## Reference Data Required
Download reference ETFs first:
```bash
python scripts/download_prices.py --tickers GLD TIP UUP BTC-USD --interval 1d --output data/prices_daily.csv
```

GLD and SPY are already in prices_daily.csv. TIP, UUP, and BTC-USD need to be downloaded.

## Implementation
- `src/features/cross_asset.py` — `add_rotation_features()` and sub-functions
- `src/regression/feature_registry.py` — Registered as `"rotation"` FeatureSpec
- Tunable parameter: `rotation_lookback` (10-42, default 20)

---

## See Also

- [Macro indicators](macro-indicators.md)
- [Technical indicators](technical-indicators.md)
- [Daily trading pipeline](daily-run.md)
- [Paper trading execution](alpaca-paper-trading.md)
