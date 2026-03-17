# Regression Test Report: Full 114-stock universe

**ID**: reg_20260315_220220_7fecc1bc
**Date**: 2026-03-15T22:02:20.415833
**Status**: completed
**Duration**: 4830.9s

## Summary

| Metric | Baseline | Final | Change |
|--------|----------|-------|--------|
| sharpe_ratio | 25.4603 | 22.5827 | -2.8776 |
| mean_rank_ic | 0.3325 | 0.4216 | +0.0891 |
| excess_return | 7.7774 | 7.2433 | -0.5341 |
| hit_rate | 0.6679 | 0.6893 | +0.0215 |
| max_drawdown | -0.1758 | -0.2252 | -0.0494 |

**Best Feature**: bollinger (+8.0561 Sharpe)

## Step-by-Step Results

| Step | Feature | Sharpe | Rank IC | Marginal Sharpe | p-value | Sig? |
|------|---------|--------|---------|-----------------|---------|------|
| 0 | BASELINE | 25.4603 | 0.3325 | - | - | - |
| 1 | macd | 23.6746 | 0.3420 | -1.7857 | 0.0000 | YES |
| 2 | bollinger | 31.7307 | 0.3950 | +8.0561 | 0.0000 | YES |
| 3 | adx | 32.3161 | 0.3957 | +0.5854 | 0.4436 | no |
| 4 | valuation | 32.3161 | 0.3957 | +0.0000 | nan | no |
| 5 | gap | 32.3460 | 0.3924 | +0.0299 | 0.0014 | YES |
| 6 | atr | 29.5221 | 0.3960 | -2.8239 | 0.0013 | YES |
| 7 | obv | 26.4401 | 0.4271 | -3.0820 | 0.0000 | YES |
| 8 | rsi | 24.7407 | 0.4281 | -1.6994 | 0.2399 | no |
| 9 | momentum | 24.3964 | 0.4236 | -0.3442 | 0.0021 | YES |
| 10 | mean_reversion | 22.5827 | 0.4216 | -1.8137 | 0.0206 | YES |
| 11 | sentiment | 22.5827 | 0.4216 | +0.0000 | nan | no |

## Feature Contribution Leaderboard

| Rank | Feature | Marginal Sharpe | Marginal IC | Importance % | Significant? |
|------|---------|-----------------|-------------|-------------|-------------|
| 1 | bollinger | +8.0561 | +0.0530 | 21.9% | YES |
| 2 | adx | +0.5854 | +0.0007 | 1.0% | no |
| 3 | gap | +0.0299 | -0.0033 | 1.0% | YES |
| 4 | valuation | +0.0000 | +0.0000 | 0.0% | no |
| 5 | sentiment | +0.0000 | +0.0000 | 0.0% | no |
| 6 | momentum | -0.3442 | -0.0045 | 29.3% | YES |
| 7 | rsi | -1.6994 | +0.0010 | 0.2% | no |
| 8 | macd | -1.7857 | +0.0095 | 10.1% | YES |
| 9 | mean_reversion | -1.8137 | -0.0020 | 0.3% | YES |
| 10 | atr | -2.8239 | +0.0036 | 4.2% | YES |
| 11 | obv | -3.0820 | +0.0310 | 15.3% | YES |

## IC Regime Analysis

| Step | Feature | Recent IC | Historical IC | Z-Score | Status |
|------|---------|-----------|---------------|---------|--------|
| 0 | BASELINE | 0.2842 | 0.3325 | -1.26 | stable |
| 1 | macd | 0.2843 | 0.3420 | -1.58 | warning |
| 2 | bollinger | 0.3102 | 0.3950 | -2.45 | DEGRADED |
| 3 | adx | 0.3101 | 0.3957 | -2.52 | DEGRADED |
| 4 | valuation | 0.3101 | 0.3957 | -2.52 | DEGRADED |
| 5 | gap | 0.3056 | 0.3924 | -2.55 | DEGRADED |
| 6 | atr | 0.3039 | 0.3960 | -2.69 | DEGRADED |
| 7 | obv | 0.3520 | 0.4271 | -2.40 | DEGRADED |
| 8 | rsi | 0.3468 | 0.4281 | -2.68 | DEGRADED |
| 9 | momentum | 0.3605 | 0.4236 | -2.03 | DEGRADED |
| 10 | mean_reversion | 0.3569 | 0.4216 | -2.08 | DEGRADED |
| 11 | sentiment | 0.3569 | 0.4216 | -2.08 | DEGRADED |