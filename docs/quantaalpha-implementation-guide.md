# QuantaAlpha Implementation Guide

**Concrete examples, parameter values, and step-by-step workflows for the QuantaAlpha-inspired pipeline.**

**Related**: [QuantaAlpha Feature Proposal](quantaalpha-feature-proposal.md) (design rationale), [Backtesting](backtesting.md) (walk-forward details), [Technical Indicators](technical-indicators.md) (feature formulas), [Macro Indicators](macro-indicators.md) (DXY, VIX, GSR), [Risk Analysis Guide](risk-analysis-guide.md) (strengthen recommendations)

**Paper**: QuantaAlpha: An Evolutionary Framework for LLM-Driven Alpha Mining. arXiv:2602.07085v1, Feb 2026.

---

## 1. Factor Formulas (Concrete Examples)

### Gap features (`src/features/gap_features.py`)

| Feature | Formula |
|---------|---------|
| `overnight_gap_pct` | `(open - prev_close) / prev_close` |
| `gap_vs_true_range` | `overnight_gap / rolling_mean(true_range, 10d)` |
| `gap_acceptance_raw` | `+1` if intraday close continues gap direction, `-1` if it reverses |
| `gap_acceptance_score_20d` | `rolling_mean(gap_acceptance_raw, 20d)` |
| `gap_acceptance_vol_weighted_20d` | `sum(gap_acceptance_raw * volume) / sum(volume)` over 20d |

### Volatility clustering

```
vol_ratio = vol_20d / vol_60d
```
A value > 1 means expanding volatility (short-term spike regime).

### Momentum score

```
momentum_score = 0.1 * r_1m + 0.3 * r_3m + 0.3 * r_6m + 0.3 * r_12m
```

---

## 2. Step-by-Step Factor Research Process

Maps the QuantaAlpha hypothesis -> code -> backtest -> refinement loop to this codebase:

1. **Hypothesis** — State a testable premise, e.g., "SLV gap acceptance score predicts 3-month excess return when GSR > 90"
2. **Code** — Add to `compute_all_features_extended()` via `add_gap_features(df)`; confirm feature appears in the feature DataFrame
3. **Validate (IC check)** — Run `scripts/diagnose_backtest_data.py` to verify data coverage; require `|IC| > 0.02` before proceeding; reject the factor if IC ~ 0
4. **Walk-forward backtest** — Run `run_walk_forward_backtest()` with `train_years=5.0, test_years=1.0`; check Sharpe > 0.5 and MDD < 20%
5. **Refinement / mutation** — Use `scripts/evolutionary_backtest.py` to mutate RSI/MACD thresholds; fitness = Sharpe; trajectories stored in `output/evolutionary/*.json`
6. **Transfer test** — Run `scripts/transfer_report.py --transfer-watchlist sp500` to confirm zero-shot robustness
7. **Promote or reject** — If walk-forward Sharpe degrades > 40% in transfer, reject; otherwise export best config to YAML

**Decision point:** If `gap_acceptance_score_20d` has |IC| < 0.01 across 3 walk-forward windows, drop the feature and flag it as redundant via `compute_factor_redundancy()` in `src/risk/complexity.py`.

---

## 3. Parameter Values and Thresholds

From `BacktestConfig`, Bayesian optimization search spaces, and QuantaAlpha paper benchmarks:

| Parameter | Default | Recommended Range | Red Flag |
|-----------|---------|-------------------|----------|
| `train_years` | 5.0 | 3–5 | < 2 (too little history) |
| `test_years` | 1.0 | 0.25–1.0 | > 2 (data bleed) |
| `top_n` | 10 | 5–20 | > 30 (dilution) |
| `transaction_cost` | 0.001 | 0.001–0.003 | 0 (unrealistic) |
| RSI period | 14 | 7–21 | — |
| MACD fast/slow/signal | 12/26/9 | 5–20 / 20–60 / 5–20 | — |
| IC threshold (keep factor) | — | > 0.02 | < 0.01 |
| Target Sharpe | — | > 0.6 | < 0.3 |
| MDD target | — | < 20% | > 35% |
| Factor inter-correlation | — | < 0.7 | > 0.85 (redundancy) |
| Complexity reject | — | `--reject-complexity-above` | exceeds threshold in `src/risk/complexity.py` |

**QuantaAlpha benchmarks** (CSI 300, Section 4 Table 2): IC = 0.1501, ARR = 27.75%, MDD = 7.98%.

---

## 4. Trading Implementation

Defined in `src/backtest/rolling.py` via `BacktestConfig`:

- **Entry rule**: Score universe on each rebalance date; hold top `top_n` (default 10) or top `top_pct` (default 10%) stocks by model score
- **Exit rule**: Stock is exited when it falls out of the top-N at next rebalance; partial exit when weight reduces
- **Position sizing**: Equal weight within top-N; risk-parity weighting available via `src/risk/risk_parity.py`
- **Rebalancing**: Monthly-start (`rebalance_freq=MS`); AMD uses `4h` intraday rebalance
- **Transaction cost**: commission 5 bps + slippage 3 bps = 8 bps total per trade
- **Turnover**: `sum(|new_weight - old_weight|) / 2` per rebalance; tracked in metrics output

---

## 5. Silver vs Gold

The pipeline supports silver-specific configuration via `config/tickers/SLV.yaml`:

| Dimension | Gold (GLD) | Silver (SLV) |
|-----------|-----------|--------------|
| Primary driver | Safe haven / USD inverse | Industrial demand + safe haven |
| Volatility | ~15% annual | ~25–35% annual |
| Macro signal | DXY (dollar strength) | GSR + DXY both matter |
| GSR filter | n/a (gold is the numerator) | BUY when GSR > 90 (silver cheap); SELL when GSR < 70 |
| `rebalance_freq` | Monthly (`MS`) | Monthly; can shorten to weekly due to higher vol |
| Overshoot tendency | Lower | Higher — `gap_acceptance_score_20d` more predictive |

**Silver strategy**: Use 20d volatility clustering (`vol_ratio > 1.2` = expanding vol = mean-reversion regime favored) + overnight gap filter (`gap_acceptance_score_20d > 0.3` = gaps accepted = continuation signal).

SLV YAML macro example:
```yaml
trigger:
  macro_factors:
    gsr_enabled: true
    gold_ticker: GLD
    gsr_buy_threshold: 90
    gsr_sell_threshold: 70
    vix_enabled: true
    vix_buy_max: 25
    dxy_enabled: true
    dxy_buy_max: 102
```

---

## 6. AMD / AI Stocks

AMD per-ticker config in `config/tickers/AMD.yaml`:
```yaml
trigger:
  rsi_period: 15
  rsi_oversold: 20
  rsi_overbought: 69
  macd_fast: 6
  macd_slow: 57
  macd_signal: 13
backtest:
  train_years: 1.0
  test_years: 0.25
  rebalance_freq: 4h
```

### Regime-awareness signals for AI names

- **Volume surge filter**: `volume_ratio > 2.0` (institutional accumulation signal via volume features)
- **Relative strength**: `rel_strength_21d > 0` (AMD outperforming SPY over 21d = institutional-driven)
- **CMF confirmation**: Set `combined_use_cmf: true` — BUY only when CMF > 0 (buying pressure), avoiding retail-driven gap-and-trap
- **Regime gate**: Enable VIX filter `vix_buy_max: 25`; during high-vol regimes AMD experiences -25%+ worst months

### Separating institutional vs retail

- **Institutional continuation**: high `dollar_volume_20d` + positive OBV slope + `gap_acceptance_vol_weighted_20d > 0.4`
- **Retail gap-and-fade**: low volume + high `overnight_gap_pct` without acceptance

---

## 7. Codebase Mapping

| QuantaAlpha Concept | Implementation |
|---------------------|----------------|
| Trajectory (hypothesis -> code -> backtest) | `run_walk_forward_backtest()` -> `output/run_*/run_info.json` |
| Mutation | `scripts/evolutionary_backtest.py` — perturbs RSI thresholds, domain weights, top-K |
| Crossover | Same script — swaps param blocks between two high-Sharpe parent configs |
| Terminal reward (IC + ARR) | Fitness = sharpe_ratio / total_return / hit_rate (configurable) |
| Complexity penalty | `src/risk/complexity.py`: `compute_config_complexity()`, `compute_factor_redundancy()` |
| Diversified planning | `scripts/diversified_backtest.py` — runs value_tilt, momentum_tilt, quality_tilt, balanced, low_vol templates |
| Lineage / trajectory archive | `scripts/lineage_report.py` — DAG of runs from `run_info.json` with parent_run_ids |
| Factor construction | `src/features/gap_features.py`, `compute_all_features_extended()` |
| Transfer testing | `scripts/transfer_report.py --transfer-watchlist <name>` |

**Where we diverge from the paper**: QuantaAlpha uses an LLM to mutate factor *expressions/code*; this project mutates YAML *config parameters* (RSI thresholds, weights, top-K) deterministically — by design.

---

## 8. Walk-Forward Backtest Methodology

Implemented in `src/backtest/rolling.py`:

- **Train**: rolling window (default 5 years); re-trains LightGBM at each step
- **Test**: out-of-sample window (default 1 year); never seen during training
- **Step**: 1 year forward per iteration (4 test windows for 2015–2023 data)
- **True OOS**: Reserve the most recent 1-year period completely; never optimize against it
- **Overfitting checks**: Watch for train Sharpe >> test Sharpe; performance degrading in recent windows; high sensitivity to RSI threshold +/-1
- **Regularization**: L1/L2 via `reg_alpha` and `reg_lambda` in LightGBM config
- **Per-ticker short windows** (e.g., AMD): `train_years=1.0, test_years=0.25, step_unit=days, rebalance_freq=4h` — shorter windows capture regime shifts in high-beta tech names faster

---

## 9. Paper References by Section

| Paper Section | Topic | Codebase Mapping |
|---------------|-------|------------------|
| Section 3.1 | Trajectory-level mutation and crossover | `evolutionary_backtest.py` |
| Section 3.2 | Diversified planning initialization | `diversified_backtest.py` templates |
| Section 3.3 | Factor complexity and redundancy control | `src/risk/complexity.py` |
| Section 4 (Table 2) | IC=0.1501, ARR=27.75%, MDD=7.98% on CSI 300 | Target benchmarks |
| Section 4.2 | Overnight gap factors, volatility structure | `src/features/gap_features.py` |
| Section 4.4 | Transfer to S&P 500: 137% cumulative excess return | `transfer_report.py` |

---

## 10. Transfer Learning

The 137% S&P 500 result: factors mined and optimized on CSI 300 were applied **zero-shot** (no re-optimization) to S&P 500 data, delivering 137% cumulative excess return over 4 years. The transferred factors were overnight-gap, volatility structure, and trend-quality signals — the same types this pipeline implements.

### How to apply transfer to your universes

1. **Train** on a large primary universe (e.g., `nasdaq_100` watchlist) with `run_walk_forward_backtest()`
2. **Export** the best config from evolutionary optimizer to YAML
3. **Transfer zero-shot**: `python scripts/transfer_report.py --watchlist nasdaq_100 --transfer-watchlist precious_metals` — same config, no parameter changes
4. **Evaluate**: compare Total Return / Sharpe / Max DD side-by-side; if transfer Sharpe > 0.4x primary Sharpe, the factors are robust
5. **What is reused**: the entire config (RSI thresholds, feature weights, top-N, rebal freq); nothing is retrained
6. **What to watch**: SLV/GLD behave very differently from tech stocks — gap acceptance and volatility regime features transfer well; momentum score weights may need re-tuning if transfer Sharpe collapses below 0.3

---

## Planned Tasks

These items are identified as gaps that need implementation:

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 2.1 | Add IC threshold checking to the pipeline | Done | IC and Rank IC per window in `window_results`; `mean_ic`, `mean_rank_ic`, `windows_below_ic_threshold` in metrics; `ic_min_threshold` and `ic_action` in BacktestConfig. See [backtesting.md](backtesting.md) §2.3. |
| 2.2 | Volume surge + OBV institutional filter for AMD/NVDA | Done | OBV + `obv_slope_20d` in extended features; `TriggerConfig.volume_surge_min`, `obv_slope_positive`; gate in `generate_signals()`; AMD/NVDA YAML use `macro_factors.volume_surge_min: 2.0`, `obv_slope_positive: true`. |
| 2.3 | Relative strength feature (`rel_strength_21d`) | Done | `calculate_relative_strength(..., lookback_days=21, output_col="rel_strength_21d")` in `compute_all_features_extended` when `benchmark_df` is provided. |
| 2.4 | Regime-aware VIX gating for AI names | Done | `vix_enabled: true`, `vix_buy_max: 25` in `config/tickers/AMD.yaml` and `config/tickers/NVDA.yaml` under `trigger.macro_factors`. |
| 2.5 | Overfitting detection in walk-forward | Done | Per-window `train_sharpe` and `test_sharpe` in `window_results`; `metrics["max_train_test_sharpe_ratio"]`; verbose warning when ratio ≥ `overfit_sharpe_ratio_threshold` (default 2.0). |
