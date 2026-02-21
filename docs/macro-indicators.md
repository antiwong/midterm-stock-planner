# Macro Indicators for Trigger Backtesting

> **Part of**: [Backtesting & Performance Evaluation](backtesting.md)
>
> This document describes the volume and macro indicators used in the Trigger Backtester: Chaikin Money Flow (CMF), Gold-Silver Ratio (GSR), Dollar Index (DXY), and VIX. These can filter or augment RSI/MACD/Bollinger signals.

## Overview

| Indicator | Type | Purpose |
|-----------|------|---------|
| **CMF** | Volume | Buying vs selling pressure; standalone signal or combined voting |
| **GSR** | Macro | Gold/silver relative value; for commodities (e.g. SLV) |
| **DXY** | Macro | US dollar strength; weak dollar can support risk assets |
| **VIX** | Macro | Market fear/volatility; high VIX blocks new BUY signals |

The Trigger Backtester displays **DXY** and **VIX** as separate visual charts below the main results, regardless of whether filters are enabled. All indicators can be configured per ticker in `config/tickers/{TICKER}.yaml`.

---

## How Macro Indicators Work with Combined (RSI + MACD) Signals

Macro indicators (GSR, DXY, VIX) act as **post-filters** on the technical signal—they do not generate BUY/SELL themselves. The flow is:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: Technical indicators vote (RSI, MACD, optionally BB, CMF)         │
│  → Raw signal: 1 (BUY), -1 (SELL), or 0 (HOLD) per bar                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Macro filters gate the signal (when enabled)                        │
│  → BUY (1): blocked if GSR too low, DXY too high, or VIX too high            │
│  → SELL (-1): blocked if GSR too high, DXY too low, or VIX too low           │
│  → Blocked signals become 0 (HOLD)                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Example (Combined RSI+MACD with VIX filter):**

1. RSI crosses above oversold → BUY vote. MACD crosses above signal → BUY vote. Majority agrees → raw signal = BUY.
2. VIX filter: BUY allowed only when VIX ≤ 25. If VIX = 30 that day → BUY is **blocked** → final signal = HOLD.
3. On another day, RSI+MACD agree on BUY and VIX = 20 → BUY **passes** → final signal = BUY.

Macro filters never create signals; they only allow or block signals from the technical indicators. All macro filters are applied in sequence (GSR first, then DXY, then VIX).

---

## 1. Chaikin Money Flow (CMF)

CMF measures buying vs selling pressure over a rolling window using volume and price range. It oscillates between -1 and +1.

### Formula

```
MFM = (2×close - high - low) / (high - low)
CMF = sum(MFM × volume) / sum(volume)  over window
```

### Usage

- **Standalone signal** (`signal_type: cmf`): BUY when CMF crosses above `cmf_buy_threshold`, SELL when it crosses below `cmf_sell_threshold`.
- **Combined mode**: Set `combined_use_cmf: true` in per-ticker YAML to include CMF as a fourth indicator in the voting logic.

### Per-Ticker YAML

```yaml
trigger:
  volume_trigger:
    cmf_window: 20
    cmf_buy_threshold: 0.0
    cmf_sell_threshold: 0.0
  combined_use_cmf: false
```

---

## 2. Gold-Silver Ratio (GSR)

For commodities like SLV (silver), the Gold-Silver Ratio can act as a macro filter: BUY only when silver is cheap relative to gold (GSR high), SELL when silver is expensive (GSR low).

### Formula

`GSR = gold_close / silver_close` (e.g. GLD/SLV)

### Logic

- **BUY** allowed when `GSR >= gsr_buy_threshold` (e.g. 90) — silver cheap
- **SELL** allowed when `GSR <= gsr_sell_threshold` (e.g. 70) — silver expensive
- When GSR is between thresholds, existing signals pass through; the filter only blocks BUY when GSR is low and SELL when GSR is high.

### Per-Ticker YAML (e.g. SLV)

```yaml
trigger:
  macro_factors:
    gsr_enabled: true
    gold_ticker: GLD
    gsr_buy_threshold: 90
    gsr_sell_threshold: 70
```

### Data Source

When `macro_gsr_enabled` is true, the pipeline fetches the gold ticker (e.g. GLD) via yfinance (live mode) or from `data/prices.csv` (CSV mode) and merges it by date to compute GSR.

**Note:** GSR combined with strict DXY/VIX thresholds can block all trades. If validation shows 0 trades with macro ON, consider disabling GSR or using more permissive thresholds.

---

## 3. Dollar Index (DXY)

DXY measures the US dollar strength vs a basket of currencies. A weak dollar can support risk assets; a strong dollar can pressure them.

### Logic

- **BUY** allowed when `DXY <= dxy_buy_max` (e.g. 102) — weak dollar
- **SELL** allowed when `DXY >= dxy_sell_min` (e.g. 106) — strong dollar

### Per-Ticker YAML

```yaml
trigger:
  macro_factors:
    dxy_enabled: true
    dxy_buy_max: 102
    dxy_sell_min: 106
```

### Data Source

DXY is fetched from yfinance (`DX-Y.NYB`). The Trigger Backtester displays DXY as a separate chart in the **Macro Indicators** section.

---

## 4. VIX (Volatility Index)

VIX measures implied volatility (fear). High VIX can block new BUY signals; low VIX allows entries.

### Logic

- **BUY** allowed when `VIX <= vix_buy_max` (e.g. 25) — low fear
- **SELL** allowed when `VIX >= vix_sell_min` (e.g. 30) — high fear

### Per-Ticker YAML

```yaml
trigger:
  macro_factors:
    vix_enabled: true
    vix_buy_max: 25
    vix_sell_min: 30
```

### Data Source

VIX is fetched from yfinance (`^VIX`). The Trigger Backtester displays VIX as a separate chart in the **Macro Indicators** section.

### VIX in Bayesian Optimization

VIX thresholds can be optimized alongside RSI/MACD parameters using `--optimize-vix`:

```bash
python scripts/optimize_macd_rsi_bayesian.py --optimize-vix --tickers AMD --n-calls 60 --save output/best_params_AMD.json
```

**Search space when `--optimize-vix` is set:**
- `vix_buy_max`: 18–45 (BUY when VIX below this)
- `vix_sell_min`: 22–50 (SELL when VIX above this)
- Constraint: `vix_sell_min` must be ≥ `vix_buy_max + 2` (enforces a buffer zone)
- The optimizer rejects runs with fewer than 3 trades; if all macro combinations block trades, optimize without macro first, then add permissive filters.

The optimizer fetches VIX from yfinance for the price data date range. Best params are saved with `macro_vix_enabled: true` and `vix_buy_max`, `vix_sell_min`.

### DXY (USD) in Bayesian Optimization

DXY thresholds can be optimized using `--optimize-dxy`:

```bash
python scripts/optimize_macd_rsi_bayesian.py --optimize-dxy --tickers SLV --n-calls 60 --save output/best_params_SLV.json
```

**Search space when `--optimize-dxy` is set:**
- `dxy_buy_max`: 98–112 (BUY when DXY below this — weak dollar)
- `dxy_sell_min`: 100–116 (SELL when DXY above this — strong dollar)
- Constraint: `dxy_sell_min` must be ≥ `dxy_buy_max + 2` (enforces a buffer zone)

VIX and DXY can be optimized together: `--optimize-vix --optimize-dxy`.

---

## 5. Regime-Based Performance Split

When VIX data is available (e.g. live mode), the Trigger Backtester computes **metrics by VIX regime**:

| Regime   | VIX range | Metrics shown |
|----------|-----------|---------------|
| low_vol  | VIX < 15  | Return, Sharpe, Max DD, Trades, % days |
| normal   | 15 ≤ VIX < 20 | Same |
| high_vol | VIX ≥ 20  | Same |

This helps assess whether the strategy holds up in high-volatility periods. The regime table appears below the main metrics when VIX data is available.

---

## 6. Visual Charts in the Trigger Backtester

The Trigger Backtester UI shows **DXY** and **VIX** as separate charts below the main backtest results:

- **DXY (Dollar Index)** — weak dollar can support risk assets
- **VIX (Volatility Index)** — high VIX indicates market fear

These charts are displayed regardless of whether the DXY or VIX filters are enabled. When macro filters are configured, **BUY/SELL bands** (horizontal dashed lines) show the threshold zones:
- Green dashed line: BUY zone (≤ buy_max)
- Red dashed line: SELL zone (≥ sell_min)

The **Price + Signals** chart shows executed trades (filled triangles) and **blocked-by-macro signals** (hollow triangles, same colors) when macro filters are enabled. A checkbox lets you toggle the display of blocked signals.

---

## 7. Single-Ticker UI Controls

For single-ticker mode, the **Macro Filters (DXY, VIX)** expander in the Signal Parameters section provides:

- **Use macro filters** — master toggle; when unchecked, all macro filters (GSR, DXY, VIX) are disabled
- **Use DXY filter** — enable/disable DXY filter with configurable thresholds
- **Use VIX filter** — enable/disable VIX filter with configurable thresholds

Checkbox defaults and threshold values are loaded from `config/tickers/{TICKER}.yaml` when available. Multi-ticker mode uses per-ticker YAML for macro filters.

---

## 8. Full Macro Factors Schema

```yaml
trigger:
  macro_factors:
    # Gold-Silver Ratio (commodities)
    gsr_enabled: false
    gold_ticker: GLD
    gsr_buy_threshold: 90
    gsr_sell_threshold: 70
    # Dollar Index
    dxy_enabled: false
    dxy_buy_max: 102
    dxy_sell_min: 106
    # VIX
    vix_enabled: false
    vix_buy_max: 25
    vix_sell_min: 30
```

---

## 9. VIX Stress Scenarios

The stress testing script (`scripts/stress_testing.py`) includes VIX-based scenarios:

- **VIX Spike to 40** — Volatility spike; growth stocks down 20–30%
- **VIX Elevated (30)** — Sustained elevated volatility; moderate drawdowns

Run stress tests on a portfolio run directory:

```bash
python scripts/stress_testing.py --run-dir output/run_xyz_123456_
```

---

## 10. Validate Macro Influence

To verify that macro filters actually affect trades (block signals when conditions are unfavorable):

```bash
python scripts/validate_macro_influence.py --ticker SLV
```

The script compares backtest results with macro filters **ON** vs **OFF** and reports:
- Trade count difference
- Number of BUY/SELL signals blocked by macro
- Whether macro filters are influencing trades

If all trades are blocked (0 trades with macro ON), thresholds may be too strict—relax DXY/VIX params or disable GSR. Optimize RSI/MACD first without macro, then add permissive macro filters and tune.

---

## 11. Trade Log with DXY and VIX

When macro filters (DXY, VIX) are enabled, the **Trade Log** tab includes DXY and VIX values at the time of each trade. This helps correlate trade outcomes with macro conditions. DXY and VIX columns appear only when the corresponding macro filter was used in the backtest.

---

## Related Documents

- [backtesting.md](backtesting.md) — Walk-forward backtesting, Trigger Backtester, Bayesian optimization (§12)
- [config/tickers/README.md](../config/tickers/README.md) — Per-ticker YAML schema, macro params
- [configuration-cli.md](configuration-cli.md) — CLI and config reference
- [risk-analysis-guide.md](risk-analysis-guide.md) — Stress testing and risk analysis
- [quantaalpha-feature-proposal.md](quantaalpha-feature-proposal.md) — Evolutionary optimizer, diversified templates
- [docs/README.md](README.md) — Full documentation index
