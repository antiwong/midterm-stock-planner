# Regression Test Report: reg_precious_metals_20260316

**ID**: reg_20260316_231050_b8ac8544
**Date**: 2026-03-16T23:10:50.282288
**Status**: completed
**Duration**: 5012.0s

## Summary

| Metric | Baseline | Final | Change |
|--------|----------|-------|--------|
| sharpe_ratio | 5.0303 | 4.9869 | -0.0434 |
| mean_rank_ic | 0.3807 | 0.4541 | +0.0734 |
| excess_return | 1.5181 | 1.3580 | -0.1601 |
| hit_rate | 0.5390 | 0.5369 | -0.0021 |
| max_drawdown | -0.2486 | -0.2494 | -0.0009 |

**Best Feature**: bollinger (+0.5594 Sharpe)

## Step-by-Step Results

| Step | Feature | Sharpe | Rank IC | Marginal Sharpe | p-value | Sig? |
|------|---------|--------|---------|-----------------|---------|------|
| 0 | BASELINE | 5.0303 | 0.3807 | - | - | - |
| 1 | macd | 5.0223 | 0.3865 | -0.0080 | 0.0191 | YES |
| 2 | bollinger | 5.5818 | 0.4409 | +0.5594 | 0.0000 | YES |
| 3 | adx | 5.4224 | 0.4412 | -0.1593 | 0.8314 | no |
| 4 | valuation | 5.4224 | 0.4412 | +0.0000 | nan | no |
| 5 | gap | 5.4441 | 0.4411 | +0.0217 | 0.9375 | no |
| 6 | atr | 5.5924 | 0.4480 | +0.1483 | 0.0002 | YES |
| 7 | obv | 5.0895 | 0.4727 | -0.5028 | 0.0000 | YES |
| 8 | rsi | 5.1971 | 0.4690 | +0.1076 | 0.0076 | YES |
| 9 | momentum | 4.9801 | 0.4582 | -0.2171 | 0.0000 | YES |
| 10 | mean_reversion | 4.9198 | 0.4577 | -0.0603 | 0.6953 | no |
| 11 | sentiment | 4.9198 | 0.4577 | +0.0000 | nan | no |
| 12 | rotation | 4.9869 | 0.4541 | +0.0671 | 0.0293 | YES |

## Feature Contribution Leaderboard

| Rank | Feature | Marginal Sharpe | Marginal IC | Importance % | Significant? |
|------|---------|-----------------|-------------|-------------|-------------|
| 1 | bollinger | +0.5594 | +0.0544 | 26.9% | YES |
| 2 | atr | +0.1483 | +0.0069 | 6.9% | YES |
| 3 | rsi | +0.1076 | -0.0037 | 0.4% | YES |
| 4 | rotation | +0.0671 | -0.0036 | 3.4% | YES |
| 5 | gap | +0.0217 | -0.0001 | 0.6% | no |
| 6 | valuation | +0.0000 | +0.0000 | 0.0% | no |
| 7 | sentiment | +0.0000 | +0.0000 | 0.0% | no |
| 8 | macd | -0.0080 | +0.0058 | 8.2% | YES |
| 9 | mean_reversion | -0.0603 | -0.0005 | 0.6% | no |
| 10 | adx | -0.1593 | +0.0003 | 2.2% | no |
| 11 | momentum | -0.2171 | -0.0107 | 26.0% | YES |
| 12 | obv | -0.5028 | +0.0247 | 12.6% | YES |

## IC Regime Analysis

| Step | Feature | Recent IC | Historical IC | Z-Score | Status |
|------|---------|-----------|---------------|---------|--------|
| 0 | BASELINE | 0.2041 | 0.3807 | -4.75 | DEGRADED |
| 1 | macd | 0.2294 | 0.3865 | -4.60 | DEGRADED |
| 2 | bollinger | 0.3017 | 0.4409 | -4.80 | DEGRADED |
| 3 | adx | 0.3098 | 0.4412 | -4.79 | DEGRADED |
| 4 | valuation | 0.3098 | 0.4412 | -4.79 | DEGRADED |
| 5 | gap | 0.3130 | 0.4411 | -4.63 | DEGRADED |
| 6 | atr | 0.3185 | 0.4480 | -4.95 | DEGRADED |
| 7 | obv | 0.3178 | 0.4727 | -5.54 | DEGRADED |
| 8 | rsi | 0.3335 | 0.4690 | -5.04 | DEGRADED |
| 9 | momentum | 0.3472 | 0.4582 | -3.78 | DEGRADED |
| 10 | mean_reversion | 0.3563 | 0.4577 | -3.49 | DEGRADED |
| 11 | sentiment | 0.3563 | 0.4577 | -3.49 | DEGRADED |
| 12 | rotation | 0.3288 | 0.4541 | -4.27 | DEGRADED |