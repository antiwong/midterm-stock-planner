# Regression Test Report: reg_semiconductors_20260316

**ID**: reg_20260316_231040_589d9271
**Date**: 2026-03-16T23:10:40.450106
**Status**: completed
**Duration**: 4882.3s

## Summary

| Metric | Baseline | Final | Change |
|--------|----------|-------|--------|
| sharpe_ratio | 7.1103 | 8.1648 | +1.0545 |
| mean_rank_ic | 0.4076 | 0.5699 | +0.1624 |
| excess_return | 2.5016 | 2.8343 | +0.3327 |
| hit_rate | 0.5805 | 0.6042 | +0.0236 |
| max_drawdown | -0.2830 | -0.2940 | -0.0110 |

**Best Feature**: bollinger (+0.8047 Sharpe)

## Step-by-Step Results

| Step | Feature | Sharpe | Rank IC | Marginal Sharpe | p-value | Sig? |
|------|---------|--------|---------|-----------------|---------|------|
| 0 | BASELINE | 7.1103 | 0.4076 | - | - | - |
| 1 | macd | 7.2136 | 0.4172 | +0.1033 | 0.0018 | YES |
| 2 | bollinger | 8.0184 | 0.5283 | +0.8047 | 0.0000 | YES |
| 3 | adx | 7.6869 | 0.5346 | -0.3315 | 0.0001 | YES |
| 4 | valuation | 7.6869 | 0.5346 | +0.0000 | nan | no |
| 5 | gap | 7.9919 | 0.5364 | +0.3051 | 0.3097 | no |
| 6 | atr | 7.9149 | 0.5358 | -0.0770 | 0.7475 | no |
| 7 | obv | 8.0372 | 0.5782 | +0.1223 | 0.0000 | YES |
| 8 | rsi | 8.0869 | 0.5796 | +0.0497 | 0.3351 | no |
| 9 | momentum | 8.1140 | 0.5681 | +0.0270 | 0.0000 | YES |
| 10 | mean_reversion | 7.9225 | 0.5747 | -0.1915 | 0.0006 | YES |
| 11 | sentiment | 7.9225 | 0.5747 | +0.0000 | nan | no |
| 12 | rotation | 8.1648 | 0.5699 | +0.2423 | 0.0044 | YES |

## Feature Contribution Leaderboard

| Rank | Feature | Marginal Sharpe | Marginal IC | Importance % | Significant? |
|------|---------|-----------------|-------------|-------------|-------------|
| 1 | bollinger | +0.8047 | +0.1111 | 25.6% | YES |
| 2 | gap | +0.3051 | +0.0018 | 1.6% | no |
| 3 | rotation | +0.2423 | -0.0048 | 1.4% | YES |
| 4 | obv | +0.1223 | +0.0424 | 13.0% | YES |
| 5 | macd | +0.1033 | +0.0097 | 10.0% | YES |
| 6 | rsi | +0.0497 | +0.0014 | 0.2% | no |
| 7 | momentum | +0.0270 | -0.0115 | 26.4% | YES |
| 8 | valuation | +0.0000 | +0.0000 | 0.0% | no |
| 9 | sentiment | +0.0000 | +0.0000 | 0.0% | no |
| 10 | atr | -0.0770 | -0.0006 | 3.3% | no |
| 11 | mean_reversion | -0.1915 | +0.0066 | 1.0% | YES |
| 12 | adx | -0.3315 | +0.0063 | 1.7% | YES |

## Guard Metric Violations

| Step | Feature | Metric | Value | Threshold |
|------|---------|--------|-------|-----------|
| 7 | obv | max_drawdown | -0.3013 | -0.3 |

## IC Regime Analysis

| Step | Feature | Recent IC | Historical IC | Z-Score | Status |
|------|---------|-----------|---------------|---------|--------|
| 0 | BASELINE | 0.4928 | 0.4076 | 3.17 | stable |
| 1 | macd | 0.4901 | 0.4172 | 2.99 | stable |
| 2 | bollinger | 0.5568 | 0.5283 | 1.26 | stable |
| 3 | adx | 0.5653 | 0.5346 | 1.34 | stable |
| 4 | valuation | 0.5653 | 0.5346 | 1.34 | stable |
| 5 | gap | 0.5459 | 0.5364 | 0.41 | stable |
| 6 | atr | 0.5784 | 0.5358 | 1.88 | stable |
| 7 | obv | 0.5924 | 0.5782 | 0.73 | stable |
| 8 | rsi | 0.5774 | 0.5796 | -0.11 | stable |
| 9 | momentum | 0.5615 | 0.5681 | -0.35 | stable |
| 10 | mean_reversion | 0.5925 | 0.5747 | 0.89 | stable |
| 11 | sentiment | 0.5925 | 0.5747 | 0.89 | stable |
| 12 | rotation | 0.5810 | 0.5699 | 0.58 | stable |