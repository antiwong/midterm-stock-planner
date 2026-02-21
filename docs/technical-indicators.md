# Technical Indicators & Strategy Features

> **Part of**: [Mid-term Stock Planner Design](design.md)
> 
> This document covers technical indicator calculations and strategy-oriented features.

## Related Documents

- [design.md](design.md) - Main overview and architecture
- [data-engineering.md](data-engineering.md) - Core feature engineering
- [visualization-analytics.md](visualization-analytics.md) - Chart visualization
- [backtesting.md](backtesting.md) - Trigger Backtester, Bayesian optimization
- [macro-indicators.md](macro-indicators.md) - DXY, VIX, GSR
- [quantaalpha-feature-proposal.md](quantaalpha-feature-proposal.md) - Gap features (§4)

---

## 1. Technical Indicators Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TECHNICAL INDICATORS                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┬─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│    MOMENTUM     │    VOLATILITY   │      TREND      │     VOLUME      │   GAP/OVERNIGHT  │
├─────────────────┼─────────────────┼─────────────────┼─────────────────┼─────────────────┤
│ • RSI           │ • ATR           │ • ADX           │ • OBV           │ • overnight_gap  │
│ • MACD          │ • Bollinger     │ • +DI / -DI     │ • Volume Ratio  │ • gap_vs_tr     │
│ • Stochastic    │   Bands         │ • EMA/SMA       │ • Accumulation  │ • gap_acceptance │
│ • ROC           │ • Keltner       │ • Trend Lines   │   Distribution  │ • (QuantaAlpha)  │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

---

## 2. Momentum Indicators

### 2.1 RSI (Relative Strength Index)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RSI VISUALIZATION                               │
└─────────────────────────────────────────────────────────────────────────────┘

  100 ┬─────────────────────────────────────────────────────────────
      │                              OVERBOUGHT (>70)
   70 ├─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ 
      │             ╱╲          ╱╲
   50 ├────────────╱──╲────────╱──╲────────────────────────────────
      │           ╱    ╲      ╱    ╲╱╲
   30 ├─ ─ ─ ─ ─╱─ ─ ─ ╲─ ─ ╱─ ─ ─ ─ ╲─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
      │        ╱        ╲  ╱          ╲
    0 ┴────────┴─────────╲╱────────────╲───────────────────────────
                             OVERSOLD (<30)
```

```python
def calculate_rsi(
    df: pd.DataFrame,
    period: int = 14,
    price_col: str = "close"
) -> pd.DataFrame:
    """
    Calculate Relative Strength Index.
    
    RSI = 100 - (100 / (1 + RS))
    RS = Avg Gain / Avg Loss over period
    """
    delta = df.groupby("ticker")[price_col].diff()
    
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    
    avg_gain = gain.groupby(df["ticker"]).transform(
        lambda x: x.ewm(span=period).mean()
    )
    avg_loss = loss.groupby(df["ticker"]).transform(
        lambda x: x.ewm(span=period).mean()
    )
    
    rs = avg_gain / avg_loss
    df[f"rsi_{period}"] = 100 - (100 / (1 + rs))
    return df
```

### 2.2 MACD

```python
def calculate_macd(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    price_col: str = "close"
) -> pd.DataFrame:
    """
    Calculate MACD, Signal Line, and Histogram.
    
    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(MACD)
    Histogram = MACD - Signal
    """
    for ticker in df["ticker"].unique():
        mask = df["ticker"] == ticker
        prices = df.loc[mask, price_col]
        
        ema_fast = prices.ewm(span=fast_period).mean()
        ema_slow = prices.ewm(span=slow_period).mean()
        
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=signal_period).mean()
        histogram = macd - signal
        
        df.loc[mask, "macd"] = macd
        df.loc[mask, "macd_signal"] = signal
        df.loc[mask, "macd_histogram"] = histogram
    
    return df
```

---

## 3. Volatility Indicators

### 3.1 ATR (Average True Range)

```python
def calculate_atr(
    df: pd.DataFrame,
    period: int = 14
) -> pd.DataFrame:
    """
    Calculate Average True Range.
    
    TR = max(H-L, |H-Cp|, |L-Cp|)
    ATR = EMA(TR, period)
    """
    df["tr"] = df.groupby("ticker").apply(
        lambda g: np.maximum(
            g["high"] - g["low"],
            np.maximum(
                abs(g["high"] - g["close"].shift(1)),
                abs(g["low"] - g["close"].shift(1))
            )
        )
    ).reset_index(level=0, drop=True)
    
    df[f"atr_{period}"] = df.groupby("ticker")["tr"].transform(
        lambda x: x.ewm(span=period).mean()
    )
    return df
```

### 3.2 Bollinger Bands

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BOLLINGER BANDS                                      │
└─────────────────────────────────────────────────────────────────────────────┘

        Upper Band (SMA + 2σ)
           ╱╲    ╱╲
          ╱  ╲  ╱  ╲           
  ───────╱────╲╱────╲─────────  Middle Band (SMA 20)
        ╱              ╲
       ╱                ╲       Lower Band (SMA - 2σ)
      ╱                  ╲

  Width = (Upper - Lower) / Middle
  %B = (Price - Lower) / (Upper - Lower)
```

```python
def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    num_std: float = 2.0,
    price_col: str = "close"
) -> pd.DataFrame:
    """Calculate Bollinger Bands."""
    df["bb_middle"] = df.groupby("ticker")[price_col].transform(
        lambda x: x.rolling(period).mean()
    )
    rolling_std = df.groupby("ticker")[price_col].transform(
        lambda x: x.rolling(period).std()
    )
    
    df["bb_upper"] = df["bb_middle"] + (num_std * rolling_std)
    df["bb_lower"] = df["bb_middle"] - (num_std * rolling_std)
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]
    df["bb_pct_b"] = (df[price_col] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])
    
    return df
```

---

## 4. Trend Indicators

### 4.1 ADX (Average Directional Index)

```python
def calculate_adx(
    df: pd.DataFrame,
    period: int = 14
) -> pd.DataFrame:
    """
    Calculate ADX and Directional Movement Indicators.
    
    ADX measures trend strength (not direction).
    +DI/-DI indicate trend direction.
    """
    # Implementation details...
    df[f"adx_{period}"] = adx
    df["plus_di"] = plus_di
    df["minus_di"] = minus_di
    return df
```

### 4.2 Moving Averages

```python
def calculate_ema(
    df: pd.DataFrame,
    periods: List[int] = [9, 21, 50, 200],
    price_col: str = "close"
) -> pd.DataFrame:
    """Calculate Exponential Moving Averages."""
    for period in periods:
        df[f"ema_{period}"] = df.groupby("ticker")[price_col].transform(
            lambda x: x.ewm(span=period).mean()
        )
    return df
```

---

## 5. Volume Indicators

### 5.1 OBV (On-Balance Volume)

```python
def calculate_obv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate On-Balance Volume.
    
    OBV = cumsum(volume * sign(price_change))
    """
    def calc_obv(group):
        price_change = group["close"].diff()
        obv = (group["volume"] * np.sign(price_change)).cumsum()
        return obv
    
    df["obv"] = df.groupby("ticker").apply(calc_obv).reset_index(level=0, drop=True)
    return df
```

When technical indicators are included in the extended feature pipeline, **obv_slope_20d** is also computed: the 20-period slope of OBV, `(obv - obv.shift(20)) / 20`, per ticker. This is used as an institutional accumulation signal (e.g. with the Trigger Backtester’s `obv_slope_positive` filter). See [macro-indicators.md](macro-indicators.md) §5.

---

## 6. Strategy Features

### 6.1 Momentum Strategy Features

```python
# src/strategies/momentum.py

def calculate_momentum_score(
    df: pd.DataFrame,
    weights: Dict[str, float] = None
) -> pd.DataFrame:
    """
    Composite momentum score from multiple timeframes.
    
    Default weights: {1m: 0.1, 3m: 0.3, 6m: 0.3, 12m: 0.3}
    """
    weights = weights or {"1m": 0.1, "3m": 0.3, "6m": 0.3, "12m": 0.3}
    
    df["momentum_score"] = (
        df["return_1m"] * weights["1m"] +
        df["return_3m"] * weights["3m"] +
        df["return_6m"] * weights["6m"] +
        df["return_12m"] * weights["12m"]
    )
    return df

def calculate_relative_strength(
    df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    lookback_days: int = 63,
    output_col: str = "relative_strength",
) -> pd.DataFrame:
    """Calculate relative strength vs benchmark (stock return - benchmark return over lookback)."""
    # Adds output_col; call with lookback_days=21, output_col="rel_strength_21d" for 21d RS.
    df[output_col] = stock_ret - bench_ret  # per (date, ticker)
    return df
```

The extended feature pipeline adds **relative_strength** (63d) and **rel_strength_21d** (21d) when `benchmark_df` is provided. The 21d variant is used for regime signals (e.g. AMD vs SPY over 21 days). See [QuantaAlpha Implementation Guide](quantaalpha-implementation-guide.md) §6.

```python
def calculate_52_week_high_low_distance(df: pd.DataFrame) -> pd.DataFrame:
    """Distance from 52-week high and low."""
    df["high_52w"] = df.groupby("ticker")["high"].transform(
        lambda x: x.rolling(252).max()
    )
    df["low_52w"] = df.groupby("ticker")["low"].transform(
        lambda x: x.rolling(252).min()
    )
    df["dist_from_high"] = df["close"] / df["high_52w"] - 1
    df["dist_from_low"] = df["close"] / df["low_52w"] - 1
    return df
```

### 6.2 Mean Reversion Features

```python
# src/strategies/mean_reversion.py

def calculate_z_score(
    df: pd.DataFrame,
    lookback: int = 20,
    price_col: str = "close"
) -> pd.DataFrame:
    """
    Z-score for mean reversion signals.
    
    Z = (price - mean) / std
    """
    df[f"zscore_{lookback}d"] = df.groupby("ticker")[price_col].transform(
        lambda x: (x - x.rolling(lookback).mean()) / x.rolling(lookback).std()
    )
    return df

def calculate_distance_from_ma(
    df: pd.DataFrame,
    ma_periods: List[int] = [20, 50, 200]
) -> pd.DataFrame:
    """Distance from moving averages as % deviation."""
    for period in ma_periods:
        ma = df.groupby("ticker")["close"].transform(
            lambda x: x.rolling(period).mean()
        )
        df[f"dist_ma_{period}"] = (df["close"] - ma) / ma
    return df

def calculate_oversold_overbought_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Binary indicators for extreme conditions."""
    df["oversold"] = (df["rsi_14"] < 30).astype(int)
    df["overbought"] = (df["rsi_14"] > 70).astype(int)
    df["below_lower_bb"] = (df["close"] < df["bb_lower"]).astype(int)
    df["above_upper_bb"] = (df["close"] > df["bb_upper"]).astype(int)
    return df
```

---

## 7. Orchestrator Function

```python
def calculate_all_technical_indicators(
    df: pd.DataFrame,
    benchmark_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Calculate all technical indicators.
    
    Adds:
    - RSI (14)
    - MACD (12, 26, 9)
    - ATR (14)
    - Bollinger Bands (20, 2)
    - ADX (14)
    - EMA (9, 21, 50, 200)
    - OBV
    - Momentum features
    - Mean reversion features
    """
    df = calculate_rsi(df)
    df = calculate_macd(df)
    df = calculate_atr(df)
    df = calculate_bollinger_bands(df)
    df = calculate_adx(df)
    df = calculate_ema(df)
    df = calculate_obv(df)
    
    # Strategy features
    df = calculate_momentum_score(df)
    if benchmark_df is not None:
        df = calculate_relative_strength(df, benchmark_df)
    df = calculate_52_week_high_low_distance(df)
    df = calculate_z_score(df)
    df = calculate_distance_from_ma(df)
    df = calculate_oversold_overbought_indicators(df)
    
    return df
```

---

## 8. Gap/Overnight Features (QuantaAlpha-Inspired)

Gap and overnight features capture information released during non-trading hours and auction-driven price discovery. Empirical evidence (QuantaAlpha, arXiv:2602.07085) shows they remain predictive under regime shifts.

| Feature | Description | Module |
|---------|-------------|--------|
| `overnight_gap_pct` | (open - prev_close) / prev_close | `src/features/gap_features.py` |
| `gap_vs_true_range` | Overnight gap / rolling mean(TR), 10d lookback | `gap_features.py` |
| `gap_acceptance_raw` | +1 if intraday continues gap direction, -1 if reverses | `gap_features.py` |
| `gap_acceptance_score_20d` | Rolling mean of acceptance | `gap_features.py` |
| `gap_acceptance_vol_weighted_20d` | Volume-weighted acceptance (emphasizes high-participation openings) | `gap_features.py` |

```python
from src.features.gap_features import add_gap_features

df = add_gap_features(df)  # Adds all gap features
```

Wired into `compute_all_features_extended()` when OHLC data is available.

---

## 9. Feature Summary

| Indicator | Function | Output Columns |
|-----------|----------|----------------|
| RSI | `calculate_rsi()` | `rsi_14` |
| MACD | `calculate_macd()` | `macd`, `macd_signal`, `macd_histogram` |
| ATR | `calculate_atr()` | `atr_14` |
| Bollinger | `calculate_bollinger_bands()` | `bb_upper`, `bb_lower`, `bb_width`, `bb_pct_b` |
| ADX | `calculate_adx()` | `adx_14`, `plus_di`, `minus_di` |
| EMA | `calculate_ema()` | `ema_9`, `ema_21`, `ema_50`, `ema_200` |
| OBV | `calculate_obv()` (+ pipeline) | `obv`, `obv_slope_20d` |
| Gap/Overnight | `add_gap_features()` | `overnight_gap_pct`, `gap_vs_true_range`, `gap_acceptance_*` |
| Momentum | `calculate_momentum_score()` | `momentum_score` |
| Rel Strength | `calculate_relative_strength()` | `relative_strength` (63d), `rel_strength_21d` |
| Z-Score | `calculate_z_score()` | `zscore_20d` |

---

## Related Documents

- **Back to**: [design.md](design.md) - Main overview
- **Core Features**: [data-engineering.md](data-engineering.md) - Basic features
- **Visualization**: [visualization-analytics.md](visualization-analytics.md) - Charts
