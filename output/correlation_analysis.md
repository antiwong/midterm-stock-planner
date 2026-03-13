# Cross-Asset Correlation Analysis

**Generated**: 2026-03-14T00:18:24.695019

---
## AMD — Tech/AI/Semiconductor Correlations

### Static Correlations (Full Period)

| Peer | Pearson | Spearman | Interpretation |
|------|---------|----------|----------------|
| AAPL | 0.3761 | 0.3141 | Weak positive |
| AMZN | 0.4011 | 0.3781 | Moderate positive |
| GOOGL | 0.4150 | 0.4221 | Moderate positive |
| META | 0.4023 | 0.3615 | Moderate positive |
| MSFT | 0.3970 | 0.4076 | Weak positive |
| NVDA | 0.5520 | 0.5530 | Moderate positive |
| TSLA | 0.4140 | 0.3961 | Moderate positive |

### Rolling Correlation Stability (20-day window)

| Peer | Mean | Std | Min | Max | Stability |
|------|------|-----|-----|-----|-----------|
| AAPL | 0.2937 | 0.2544 | -0.3162 | 0.9576 | Unstable |
| AMZN | 0.3338 | 0.2845 | -0.5462 | 0.9039 | Unstable |
| GOOGL | 0.3880 | 0.2484 | -0.1653 | 0.9359 | Moderate |
| META | 0.3555 | 0.2804 | -0.3898 | 0.9149 | Unstable |
| MSFT | 0.3553 | 0.2763 | -0.6483 | 0.9446 | Unstable |
| NVDA | 0.5507 | 0.2610 | -0.2890 | 0.9485 | Unstable |
| TSLA | 0.3748 | 0.2506 | -0.3191 | 0.9303 | Unstable |

### Lead-Lag Analysis (Cross-Correlation)

Positive lag = peer leads AMD. Peak at lag 0 = synchronous.

- **AAPL**: Synchronous (lag=0, r=0.3761)
- **AMZN**: Synchronous (lag=0, r=0.4011)
- **GOOGL**: Synchronous (lag=0, r=0.4150)
- **META**: Synchronous (lag=0, r=0.4023)
- **MSFT**: Synchronous (lag=0, r=0.3970)
- **NVDA**: Synchronous (lag=0, r=0.5520)
- **TSLA**: Synchronous (lag=0, r=0.4140)

### AMD Key Insights

1. **Sector correlation**: AMD typically moves with NVDA (semiconductor peer) and broader tech (GOOGL, MSFT, META) — shared AI/data center demand driver.
2. **Index tracking**: QQQ (NASDAQ-100) and SMH (Semiconductor ETF) are natural benchmarks. High correlation with SMH suggests semiconductor cycle exposure.
3. **News/sentiment gap**: Tech/AI news sentiment (earnings, chip demand, AI capex announcements) would add alpha. Consider: Finnhub news sentiment, Reddit/Twitter sentiment on $AMD, AI investment news flow.
4. **Recommended new features for regression testing**:
   - `peer_momentum_nvda`: NVDA relative strength (leads AMD in some cycles)
   - `sector_breadth_semis`: % of semiconductor stocks above 50d SMA
   - `ai_news_sentiment`: NLP sentiment on AI/chip news
   - `qqq_relative_strength`: AMD performance relative to QQQ

---
## SLV — Precious Metals / Macro Correlations

### Static Correlations (Full Period)

| Peer | Pearson | Spearman | Interpretation |
|------|---------|----------|----------------|

### Rolling Correlation Stability (20-day window)

| Peer | Mean | Std | Min | Max | Stability |
|------|------|-----|-----|-----|-----------|

### Lead-Lag Analysis


### SLV Key Insights

1. **Precious metals correlation**: SLV (silver) typically correlates strongly with GLD (gold) but with higher beta. Gold leads silver in risk-off moves.
2. **Dollar inverse**: DXY (US Dollar Index) has a historically negative correlation with precious metals. Dollar strength = metals weakness. Already captured via DXY optimization.
3. **Fear gauge**: VIX (volatility) correlation with SLV is typically positive in crisis periods (safe haven demand) but can decouple. Already captured via VIX optimization.
4. **Geopolitical/war gap**: War, sanctions, and geopolitical tension drive precious metals demand. No automated geopolitical risk indicator in the system currently.
5. **Recommended new features for regression testing**:
   - `gold_silver_ratio`: GLD/SLV ratio (mean-reverts, signals relative value)
   - `dxy_momentum`: Dollar momentum (inverse signal for metals)
   - `vix_regime`: VIX regime classification (low/medium/high volatility)
   - `geopolitical_risk_index`: GPR index from Caldara & Iacoviello (publicly available)
   - `real_yield_10y`: 10Y Treasury yield - inflation expectations (key metals driver)
   - `mining_etf_breadth`: % of mining stocks above 50d SMA

---
## Summary: Recommended Feature Additions

### For AMD (Tech/Semiconductor)
| Feature | Source | Expected Impact |
|---------|--------|----------------|
| NVDA relative strength | Calculated from prices | High — strongest peer correlation |
| Semiconductor sector breadth | SMH holdings | Medium — sector health |
| Tech/AI news sentiment | Finnhub / NewsAPI + NLP | High — earnings and AI capex catalysts |
| QQQ relative performance | Calculated from prices | Medium — broad tech benchmark |

### For SLV (Precious Metals)
| Feature | Source | Expected Impact |
|---------|--------|----------------|
| Gold/Silver ratio | GLD/SLV prices | High — mean-reverting signal |
| DXY momentum & regime | DXY prices | High — inverse correlation driver |
| VIX regime classification | VIX prices | Medium — fear-driven demand |
| Geopolitical risk index | Caldara-Iacoviello GPR | High — war/sanctions premium |
| Real yield 10Y | FRED / Treasury data | High — opportunity cost of holding metals |
| Mining ETF breadth | GDX/GDXJ holdings | Medium — sector participation |