# Regression Report Chart Guide

**Regression ID**: reg_20260315_152332_a41646df
**Watchlist**: tech_giants (AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, AMD, INTC, ORCL, CRM, ADBE, NFLX)
**Data**: `data/prices_daily.csv` — 10-year daily OHLCV (2016–2026, 114 tickers, zero NaN)
**Duration**: 38 min, 265 walk-forward windows, 7-day step

---

## What This Report Shows

This regression test evaluates features **one at a time**, adding each to a baseline model and measuring its marginal contribution. The model is a cross-sectional LightGBM ranker that predicts which of the 13 tech_giants stocks will outperform over each walk-forward window.

---

## Chart 1: Cumulative Performance (Line Chart)

**What it shows**: Sharpe ratio and Rank IC plotted on the y-axis, with each step (feature addition) on the x-axis. Step 0 is the baseline (returns + volatility + volume), then each subsequent step adds one feature.

**How to read it**: Look for the peak — that's your optimal feature set. Everything after the peak is adding noise. In this run, performance peaked at **Step 6 (+adx)** with Sharpe=1.34, then declined as less-useful features were added.

**Key insight**: More features does not mean a better model. The best model uses only baseline + macd + bollinger + adx.

---

## Chart 2: Marginal Sharpe Contribution (Bar Chart)

**What it shows**: Each bar represents how much adding that specific feature changed the Sharpe ratio compared to the previous step. Green bars = improvement, red bars = degradation.

**How to read it**: Tall green bars are high-value features. Red bars are features that hurt performance and should be excluded.

**Results**:
| Feature | Marginal Sharpe | Verdict |
|---------|----------------|---------|
| bollinger | +0.64 | Best feature |
| macd | +0.15 | Strong contributor |
| adx | +0.08 | Moderate contributor |
| valuation | +0.02 | Neutral |
| gap | -0.02 | Slight drag |
| obv | -0.18 | Hurts performance |
| momentum | -0.24 | Hurts performance |
| rsi | -0.28 | Worst feature |

---

## Chart 3: Feature Importance (Bar Chart)

**What it shows**: LightGBM's internal feature importance (% of total split gain) at each step. Shows how much the model relies on each feature for making predictions.

**How to read it**: A feature with high importance but negative marginal Sharpe is a red flag — the model is using it heavily, but it's not helping out-of-sample performance. That's a sign of overfitting to noise.

**Key insight**: Compare importance % to marginal Sharpe. Features where both are positive (bollinger at 21.9%, macd at 10.4%) are genuine signals. Features with high importance but negative Sharpe (momentum at 25.1%) are noise the model is memorizing.

---

## Chart 4: Guard Metrics (Heatmap / Traffic Light)

**What it shows**: Status of guard metrics at each step — max drawdown, turnover, train/test Sharpe ratio, and IC % positive. Color-coded: green = within threshold, red = violated.

**How to read it**: Any red cell means that step's model configuration has a risk issue.

**Guard thresholds**:
| Metric | Threshold | This Run |
|--------|-----------|----------|
| max_drawdown | > -30% | VIOLATED (-55% to -72%) |
| turnover | < 0.80 | OK |
| train_test_sharpe_ratio | < 2.5x | VIOLATED (18x–727x) |
| ic_pct_positive | > 50% | OK |

**Key insight**: Despite strong Sharpe numbers, the model has severe overfitting (train vastly outperforms test) and unacceptable drawdowns. The regularization improvements help but don't fully solve this — guard violations indicate further work is needed (position sizing, risk limits, or more aggressive regularization).

---

## Chart 5: Sharpe vs Rank IC Scatter

**What it shows**: Each dot is a regression step. X-axis = Rank IC (signal quality), Y-axis = Sharpe ratio (risk-adjusted return). Dot size = feature importance. Color = whether the feature is statistically significant.

**How to read it**: The ideal features are in the **top-right** (high IC AND high Sharpe). Features in the bottom-left are weak. Features with high IC but low Sharpe (or vice versa) have a disconnect between signal quality and portfolio performance.

**Key insight**: This reveals the OBV paradox — OBV has decent IC (+0.05 gain) but negative Sharpe impact (-0.18). OBV provides some predictive signal that the model can detect, but it doesn't translate into profitable trades (possibly due to correlation with existing features or poor signal-to-noise at the portfolio level).

---

## Summary: Optimal Configuration

Based on this regression test:

- **Use**: baseline (returns, volatility, volume) + macd + bollinger + adx
- **Skip**: rsi, momentum, obv, mean_reversion
- **Watch out for**: Severe overfitting (train/test ratio 18-727x) and drawdowns (-55% to -72%)
- **Next steps**: Further regularization, position sizing constraints, or ensemble approaches to reduce overfitting
