# Feature Engineering

> [← Daily Run Index](README.md) | [← Documentation Index](../README.md)

All features are computed by `compute_all_features_extended()` in `src/features/engineering.py`. The pipeline produces ~24 features from daily OHLCV data and an optional fundamental data source.

---

## Feature Summary

| Group | Features | Count | Status |
|-------|----------|-------|--------|
| Returns | 1m, 3m, 6m, 12m lagged returns | 4 | Always on |
| Volatility | 20-day, 60-day rolling std | 2 | Always on |
| Volume | Dollar volume, volume ratio, turnover | 3 | Always on |
| MACD | MACD line, signal, histogram | 3 | On (`include_technical`) |
| Bollinger | %B, bandwidth, upper/middle/lower | 5 | On (`include_technical`) |
| ATR | 14-period average true range | 1 | On (when OHLC available) |
| ADX | 14-period average directional index | 1 | On (when OHLC available) |
| RSI | 14-period relative strength index | 1 | **Off** (hurts model) |
| OBV | On-balance volume, 20-day slope | 2 | Conditional |
| Momentum | Relative strength, 52-week distance | 3 | **Off** (hurts model) |
| Valuation | PE, PB, earnings yield | 3 | When fundamentals available |

---

## Target Variable

The model predicts **63-day forward excess return** — how much a stock will outperform SPY over the next ~3 months.

```
forward_return[stock] = (close[t+63] / close[t]) - 1
forward_return[SPY]   = (close_spy[t+63] / close_spy[t]) - 1

target = forward_return[stock] - forward_return[SPY]
```

**Source:** `make_training_dataset()` in `src/features/engineering.py`

---

## Baseline Features (Always Computed)

### Return Features

Lagged percentage returns over standard lookback windows.

```
return_1m  = (close[t] / close[t-21])  - 1      # 1-month (21 trading days)
return_3m  = (close[t] / close[t-63])  - 1      # 3-month
return_6m  = (close[t] / close[t-126]) - 1      # 6-month
return_12m = (close[t] / close[t-252]) - 1      # 12-month
```

**Why these periods:** Standard momentum lookbacks used in factor investing. The 12-month return captures long-term trend; 1-month captures recent price action.

### Volatility Features

Rolling standard deviation of daily returns, annualized implicitly by the model.

```
daily_return = close.pct_change()
vol_20d  = rolling_std(daily_return, window=20)    # ~1 month realized vol
vol_60d  = rolling_std(daily_return, window=60)    # ~3 month realized vol
```

**Why:** Volatility is a key risk factor. Low-vol stocks tend to outperform on a risk-adjusted basis (low-volatility anomaly). The model learns to incorporate volatility into its ranking.

### Volume Features

```
dollar_volume    = close * volume
dollar_volume_20d = rolling_mean(dollar_volume, window=20)   # Liquidity proxy
volume_ratio     = volume[t] / rolling_mean(volume, 20)      # Relative activity
turnover_20d     = rolling_std(volume, 20) / rolling_mean(volume, 20)  # Volume stability
```

**Why:** Dollar volume filters out illiquid stocks. Volume ratio detects unusual activity (institutional interest, news events). Turnover stability measures whether volume is consistent.

---

## Technical Indicators

### MACD (Moving Average Convergence Divergence)

Measures trend momentum through the relationship between two exponential moving averages.

```
MACD_line    = EMA(close, fast=12) - EMA(close, slow=26)
Signal_line  = EMA(MACD_line, period=9)
Histogram    = MACD_line - Signal_line
```

**Features produced:** `macd`, `macd_signal`, `macd_histogram`

**Interpretation:**
- Histogram > 0: Upward momentum (fast EMA above slow EMA and diverging)
- Histogram < 0: Downward momentum
- Histogram crossing zero: Trend change signal

**Regression test impact:** +0.15 Sharpe (validated on tech_giants, reg_20260315_152332)

**Source:** `calculate_macd()` in `src/indicators/technical.py`

**Default parameters:** fast=12, slow=26, signal=9 (global). Per-ticker configs in `config/tickers/*.yaml` override these for the trigger backtest (e.g., SLV uses fast=5, slow=51, signal=5 — very slow MACD for trend-following commodities).

---

### Bollinger Bands

Volatility-based envelope around a moving average. Identifies overbought/oversold conditions and volatility expansion/contraction.

```
Middle = SMA(close, period=20)
Std    = rolling_std(close, period=20)
Upper  = Middle + 2 * Std
Lower  = Middle - 2 * Std

%B        = (close - Lower) / (Upper - Lower)    # Position within bands [0, 1]
Bandwidth = (Upper - Lower) / Middle              # Normalized band width
```

**Features produced:** `bb_upper`, `bb_middle`, `bb_lower`, `bb_pct` (%B), `bb_width`

**Interpretation:**
- %B > 1.0: Price above upper band (overbought, strong uptrend)
- %B < 0.0: Price below lower band (oversold, strong downtrend)
- %B ~ 0.5: Price at middle band (neutral)
- Bandwidth expanding: Volatility increasing (breakout potential)
- Bandwidth contracting: Volatility decreasing (squeeze, breakout imminent)

**Regression test impact:** +0.64 Sharpe — **strongest single feature** (21.9% model importance)

**Source:** `calculate_bollinger_bands()` in `src/indicators/technical.py`

---

### ATR (Average True Range)

Measures volatility using the full trading range (including gaps).

```
True Range = max(
    high[t] - low[t],              # Intraday range
    abs(high[t] - close[t-1]),     # Gap up from previous close
    abs(low[t] - close[t-1])       # Gap down from previous close
)

ATR = SMA(True Range, period=14)    # 14-period smoothed average
```

**Features produced:** `atr`

**Interpretation:** Higher ATR = more volatile stock. Used by position sizing methods (ATR-based sizing invests less in volatile stocks).

**Regression test impact:** +0.08 Sharpe

**Source:** `calculate_atr()` in `src/indicators/technical.py`

---

### ADX (Average Directional Index)

Measures trend strength regardless of direction (0 to 100 scale).

```
+DM = high[t] - high[t-1]   if positive and > |low[t-1] - low[t]|, else 0
-DM = low[t-1] - low[t]     if positive and > high[t] - high[t-1], else 0

+DI = 100 * SMA(+DM, 14) / ATR(14)    # Positive directional indicator
-DI = 100 * SMA(-DM, 14) / ATR(14)    # Negative directional indicator

DX  = 100 * |+DI - -DI| / (+DI + -DI) # Directional movement index
ADX = SMA(DX, period=14)               # Smoothed trend strength
```

**Features produced:** `adx`

**Interpretation:**
- ADX > 25: Strong trend (either direction)
- ADX < 20: Weak/no trend (range-bound market)
- ADX > 40: Very strong trend

**Source:** `calculate_adx()` in `src/indicators/technical.py`

---

### RSI (Relative Strength Index)

Momentum oscillator measuring speed and magnitude of price changes.

```
gains = max(close[t] - close[t-1], 0)
losses = max(close[t-1] - close[t], 0)

avg_gain = SMA(gains, period=14)
avg_loss = SMA(losses, period=14)

RS  = avg_gain / avg_loss
RSI = 100 - 100 / (1 + RS)
```

**Features produced:** `rsi`

**Status:** **Disabled by default** (`include_rsi: false`)

**Why disabled:** Regression testing showed RSI hurts the cross-sectional ranking model by -0.28 Sharpe. RSI works well for single-stock timing (trigger backtest) but adds noise when ranking stocks relative to each other.

**Source:** `calculate_rsi()` in `src/indicators/technical.py`

---

### OBV (On-Balance Volume)

Cumulative volume indicator that confirms price trends through volume.

```
if close[t] > close[t-1]:
    OBV[t] = OBV[t-1] + volume[t]     # Up day → add volume
elif close[t] < close[t-1]:
    OBV[t] = OBV[t-1] - volume[t]     # Down day → subtract volume
else:
    OBV[t] = OBV[t-1]                 # Flat → no change

obv_slope_20d = (OBV[t] - OBV[t-20]) / 20   # Trend of OBV
```

**Features produced:** `obv`, `obv_slope_20d`

**Status:** Conditional — helps with top_n=5 portfolios (+0.46 Sharpe) but hurts with top_n=10 (-0.18 Sharpe).

**Interpretation:** Rising OBV with rising price = strong trend. Rising OBV with falling price = institutional accumulation (bullish divergence).

**Source:** `calculate_obv()` in `src/indicators/technical.py`

---

## Disabled Features

These features were tested via regression testing and found to hurt cross-sectional model performance:

| Feature Group | Impact | Reason |
|--------------|--------|--------|
| RSI | -0.28 Sharpe | Works for single-stock timing but adds noise to cross-sectional ranking |
| Momentum (relative strength, 52w distance) | -0.24 Sharpe | Redundant with return features; model capacity wasted |
| OBV (with top_n=10) | -0.18 Sharpe | Volume signals less useful in broader portfolios |
| Mean Reversion (z-scores) | Noise | Conflicts with momentum signal in 63-day horizon |

**Reference:** Regression test `reg_20260315_152332` on tech_giants (265 windows, 7-day step, 38 minutes).

---

## Feature Toggle Configuration

In `config/config.yaml`:

```yaml
features:
  include_technical: true       # MACD + Bollinger + ATR + ADX
  include_rsi: false            # RSI (disabled — hurts model)
  include_obv: false            # OBV (conditional)
  include_momentum: false       # Momentum composites (disabled)
  include_mean_reversion: false # Z-scores (disabled)
  horizon_days: 63              # Target prediction horizon
  return_periods: [21, 63, 126, 252]
  volatility_windows: [20, 60]
  macd_fast: 12
  macd_slow: 26
  macd_signal: 9
  rsi_period: 14
```

---

## See Also

- [LightGBM Model](lightgbm-model.md) — how these features are used for training
- [Walk-Forward Backtest](walk-forward-backtest.md) — how features are validated
- [Signal Generation](signal-generation.md) — how predictions become trading signals
- [Technical Indicators](../technical-indicators.md) — extended indicator reference
- [Macro Indicators](../macro-indicators.md) — DXY, VIX, GSR macro features
