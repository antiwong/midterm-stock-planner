# Bayesian Optimization Report: Precious Metals

**Date**: 2026-03-16
**Watchlist**: precious_metals (31 tickers)
**Method**: Bayesian optimization (scikit-optimize, gp_minimize)
**Settings**: n_calls=40, n_initial=8, acq_func=EI, metric=sharpe, seed=42
**Data**: Hourly prices, 2023-03-15 to 2026-03-13
**Total Duration**: 2,665s (~44 min)

---

## Summary

- **31/31 tickers optimized** — all successful
- **Average Sharpe**: 0.871
- **Average Return**: 241.9%
- **Top performer**: HMY (Sharpe=2.82, 1173% return, -19% drawdown)
- **Worst performer**: BTG (Sharpe=0.08, 15% return, -42% drawdown)

---

## Results (sorted by Sharpe ratio)

| Rank | Ticker | Name | Sharpe | Return | MaxDD | Trades | MACD (F/S/Sig) | RSI (Len/Hi/Lo) |
|------|--------|------|--------|--------|-------|--------|----------------|------------------|
| 1 | **HMY** | Harmony Gold | 2.816 | 1172.5% | -19.0% | 27 | 12/36/6 | 16/69/34 |
| 2 | **AU** | AngloGold Ashanti | 2.452 | 761.5% | -30.5% | 32 | 12/35/6 | 7/78/20 |
| 3 | **SIL** | Silver Miners ETF | 2.342 | 302.4% | -14.8% | 31 | 10/28/10 | 16/71/27 |
| 4 | **KGC** | Kinross Gold | 2.284 | 653.3% | -21.1% | 27 | 17/59/13 | 15/80/40 |
| 5 | **PSLV** | Sprott Silver | 2.171 | 313.9% | -11.0% | 45 | 5/56/5 | 11/80/32 |
| 6 | **AGI** | Alamos Gold | 1.988 | 292.7% | -16.4% | 22 | 19/27/12 | 21/61/40 |
| 7 | **GLDM** | Gold Mini ETF | 1.929 | 78.4% | -9.1% | 23 | 20/60/20 | 10/80/32 |
| 8 | **FNV** | Franco-Nevada | 1.728 | 137.0% | -14.5% | 27 | 12/33/7 | 16/61/34 |
| 9 | **RGLD** | Royal Gold | 1.546 | 114.6% | -19.4% | 20 | 13/42/20 | 12/79/20 |
| 10 | **GLD** | SPDR Gold ETF | 1.037 | 159.5% | -10.2% | 69 | 16/60/19 | 16/71/21 |
| 11 | SGOL | Aberdeen Gold | 0.579 | 156.9% | -11.1% | 48 | 20/20/20 | 21/80/40 |
| 12 | CDE | Coeur Mining | 0.439 | 582.7% | -27.0% | 480 | 8/60/18 | 7/60/20 |
| 13 | OR | Osisko Royalties | 0.435 | 247.5% | -23.3% | 298 | 17/60/20 | 7/80/30 |
| 14 | IAU | iShares Gold | 0.413 | 96.1% | -11.0% | 60 | 20/20/20 | 21/80/40 |
| 15 | SILJ | Junior Silver Miners | 0.408 | 312.2% | -26.3% | 324 | 14/60/20 | 9/77/27 |
| 16 | GDXJ | Junior Gold Miners | 0.402 | 206.1% | -17.9% | 42 | 20/20/5 | 21/80/25 |
| 17 | WPM | Wheaton Precious | 0.376 | 188.3% | -30.9% | 185 | 20/56/20 | 21/80/32 |
| 18 | RING | iShares Gold Miners | 0.372 | 167.8% | -26.7% | 143 | 20/60/14 | 20/80/40 |
| 19 | MAG | MAG Silver | 0.358 | 188.2% | -29.1% | 16 | 20/20/20 | 21/80/27 |
| 20 | PAAS | Pan American Silver | 0.323 | 209.3% | -28.8% | 263 | 12/57/20 | 20/60/40 |
| 21 | SAND | Sandstorm Gold | 0.322 | 160.6% | -23.9% | 227 | 15/26/20 | 12/80/40 |
| 22 | AEM | Agnico Eagle | 0.289 | 109.6% | -21.9% | 416 | 11/21/12 | 9/68/40 |
| 23 | EGO | Eldorado Gold | 0.287 | 107.7% | -24.2% | 246 | 15/21/13 | 16/68/21 |
| 24 | GDX | Gold Miners ETF | 0.255 | 124.2% | -26.4% | 64 | 20/20/9 | 21/80/40 |
| 25 | HL | Hecla Mining | 0.253 | 217.2% | -45.4% | 76 | 20/20/20 | 15/80/40 |
| 26 | SLV | iShares Silver | 0.253 | 54.5% | -16.2% | 239 | 19/28/17 | 19/63/20 |
| 27 | SIVR | Aberdeen Silver | 0.241 | 81.4% | -26.4% | 465 | 12/23/17 | 8/69/38 |
| 28 | AG | First Majestic Silver | 0.228 | 160.8% | -48.7% | 397 | 16/60/5 | 21/77/36 |
| 29 | GOLD | Barrick Gold | 0.207 | 61.2% | -55.3% | 204 | 8/60/20 | 12/76/20 |
| 30 | NEM | Newmont | 0.181 | 64.6% | -40.8% | 217 | 20/60/20 | 19/74/40 |
| 31 | BTG | B2Gold | 0.082 | 15.2% | -41.9% | 267 | 20/20/18 | 7/70/20 |

---

## Analysis

### Tier Classification

**Tier 1 — Excellent (Sharpe > 1.5):**
- HMY (2.82): Best in class — South African gold miner with explosive returns and moderate drawdown
- AU (2.45): AngloGold — similar MACD(12/35/6) to HMY, both benefit from gold bull cycle
- SIL (2.34): Silver miners ETF — diversified exposure, good risk profile (-14.8% MaxDD)
- KGC (2.28): Kinross — slow MACD(17/59) captures long gold trends
- PSLV (2.17): Sprott Silver — very slow MACD(5/56), consistent with earlier SLV optimization
- AGI (1.99): Alamos Gold — lowest trade count (22), highest conviction signals
- GLDM (1.93): Gold mini ETF — best risk profile of all (MaxDD -9.1%)
- FNV (1.73): Franco-Nevada — royalty/streaming, lower vol than miners
- RGLD (1.55): Royal Gold — another royalty company, lowest trades (20)

**Tier 2 — Good (Sharpe 0.5–1.5):**
- GLD (1.04): Core gold ETF, very stable (-10.2% MaxDD)
- SGOL (0.58): Another gold ETF, similar to GLD

**Tier 3 — Marginal (Sharpe < 0.5):**
- CDE through BTG: Miners with higher volatility and lower Sharpe

### Gold vs Silver

| Asset | Avg Sharpe | Avg MaxDD | Best Ticker |
|-------|-----------|-----------|-------------|
| Gold ETFs (GLD, IAU, GLDM, SGOL) | 0.990 | -10.4% | GLDM (1.93) |
| Gold Miners (HMY, AU, KGC, AGI, etc.) | 1.083 | -27.1% | HMY (2.82) |
| Gold Royalties (FNV, RGLD, SAND, OR) | 1.008 | -20.3% | FNV (1.73) |
| Silver ETFs (SLV, SIVR, PSLV) | 0.888 | -17.9% | PSLV (2.17) |
| Silver Miners (SIL, SILJ, AG, CDE, etc.) | 0.674 | -30.8% | SIL (2.34) |

**Key insight**: Gold royalty companies (FNV, RGLD) offer the best risk-adjusted returns among individual stocks. Gold ETFs have the lowest drawdowns. Gold miners have highest Sharpe but also highest drawdowns.

### MACD Parameter Patterns

- **Slow trend-followers** (MACD slow 50-60): PSLV, KGC, GLD, PAAS — precious metals are strong trend-following assets
- **Medium cycle** (MACD slow 28-42): HMY, AU, SIL, FNV, RGLD — miners have medium-term cycles
- **Fast/degenerate** (MACD slow 20): IAU, SGOL, GDX, MAG, HL — converges to momentum

### Risk Observations

- **Safest**: GLDM (-9.1%), GLD (-10.2%), IAU (-11.0%), PSLV (-11.0%), SGOL (-11.1%)
- **Most volatile**: GOLD (-55.3%), AG (-48.7%), HL (-45.4%), BTG (-41.9%), NEM (-40.8%)
- **Best risk-adjusted**: GLDM (Sharpe 1.93 with only -9.1% MaxDD)

---

## Comparison Across Watchlists

| Metric | Precious Metals (31) | Semiconductors (22) | Tech Giants (13) |
|--------|---------------------|-------------------|-----------------|
| Avg Sharpe | **0.871** | 0.517 | 1.235 |
| Best Sharpe | **2.816 (HMY)** | 2.012 (TSM) | 2.059 (META) |
| Tickers > 1.5 Sharpe | **9 (29%)** | 1 (5%) | 1 (8%) |
| Avg Return | 241.9% | 478.8% | 1297.5% |
| Avg MaxDD | **-23.4%** | -38.6% | -31.4% |

Precious metals have the most tickers with strong trigger signals (9 above Sharpe 1.5) and the lowest average drawdown. The trigger backtest works particularly well on precious metals because they are strong trend-following assets.

---

## Files Generated

- Per-ticker configs: `config/tickers/{TICKER}.yaml` (31 files)
- Per-ticker params: `output/best_params_{TICKER}.json` (31 files)
- Batch summary: `output/batch_optimization_summary.json`
- This report: `output/reports/bayesian_optimization_precious_metals_20260316.md`
