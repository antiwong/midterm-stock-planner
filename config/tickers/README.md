# Per-Ticker Configuration

Each ticker can have its own YAML file at `config/tickers/{TICKER}.yaml` with RSI, MACD, Bollinger parameters, time forward windows, and walk-forward backtest settings. When present, these override the global config for that ticker.

**Documentation**: [docs/backtesting.md](../docs/backtesting.md) (§11 Per-Ticker Config), [docs/macro-indicators.md](../docs/macro-indicators.md) (DXY, VIX, GSR), [docs/configuration-cli.md](../docs/configuration-cli.md), [docs/README.md](../docs/README.md)

## Schema

```yaml
ticker: AMD

# RSI, MACD, Bollinger parameters (used in trigger backtest)
# Or set optimized_params_path in config/config.yaml to load from JSON
trigger:
  rsi_period: 15
  rsi_oversold: 20
  rsi_overbought: 69
  macd_fast: 6
  macd_slow: 57
  macd_signal: 13
  bb_period: 20
  bb_std: 2.0
  # Optional: volume trigger (Chaikin Money Flow)
  volume_trigger:
    cmf_window: 20
    cmf_buy_threshold: 0.0
    cmf_sell_threshold: 0.0
  combined_use_cmf: false   # Include CMF in combined voting
  # Optional: macro factors (GSR, DXY, VIX)
  macro_factors:
    gsr_enabled: false
    gold_ticker: GLD
    gsr_buy_threshold: 90
    gsr_sell_threshold: 70
    dxy_enabled: false
    dxy_buy_max: 102    # BUY when DXY ≤ this (weak dollar)
    dxy_sell_min: 106   # SELL when DXY ≥ this (strong dollar)
    vix_enabled: false
    vix_buy_max: 25     # BUY when VIX ≤ this (low fear)
    vix_sell_min: 30    # SELL when VIX ≥ this (high fear)

# Time forward windows (used in feature engineering and walk-forward backtest)
horizon_days: 63
return_periods: [21, 63, 126, 252]
volatility_windows: [20, 60]
volume_window: 20

# Walk-forward backtest (overrides global config.backtest when running for this ticker)
backtest:
  train_years: 1.0
  test_years: 0.25
  step_value: 1.0
  step_unit: days
  rebalance_freq: 4h   # 4h, 2W, MS, ME (use ME not M for month-end)
```

## Generating Optimized Params

Run Bayesian optimization per ticker:

```bash
python scripts/optimize_macd_rsi_bayesian.py --tickers AMD --save output/best_params_AMD.json
```

Include VIX and DXY macro thresholds when optimizing:

```bash
python scripts/optimize_macd_rsi_bayesian.py --optimize-vix --optimize-dxy --tickers SLV --n-calls 80 --save output/best_params_SLV.json
```

If macro optimization yields 0 trades (all signals blocked), optimize RSI/MACD first without macro, then add permissive macro filters manually.

**Validate macro influence** after changing macro params:

```bash
python scripts/validate_macro_influence.py --ticker SLV
```

Then copy the values into `config/tickers/{TICKER}.yaml`.

## Related

- **Strategy templates**: `config/strategy_templates/` — value_tilt, momentum_tilt, quality_tilt, balanced, low_vol. Use with `scripts/diversified_backtest.py`.
- **Evolutionary optimizer**: `scripts/evolutionary_backtest.py` — mutates walk-forward backtest params (train_years, rebalance_freq, etc.), exports best config to YAML.
- **Lineage report**: `scripts/lineage_report.py` — DAG of runs from run_info.json, includes evolutionary trajectories.

## Usage

- **Trigger Backtester (GUI)**: Sliders default to per-ticker values when a ticker YAML exists.
- **Live backtest script**: `python scripts/run_trigger_backtest_live.py --tickers AMD SLV` uses per-ticker config for each ticker.
- **Walk-forward backtest**: Use `get_backtest_config_for_ticker(ticker, base_config)` from `src.config.config` to get per-ticker backtest config (train_years, test_years, step_value, step_unit, rebalance_freq) when running analysis for a specific ticker.
