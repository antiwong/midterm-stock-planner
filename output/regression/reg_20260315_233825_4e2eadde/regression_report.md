# Regression Test Report: Top5 Position Sizing Tuned

**ID**: reg_20260315_233825_4e2eadde
**Date**: 2026-03-15T23:38:25.217822
**Status**: completed
**Duration**: 2806.8s

## Summary

| Metric | Baseline | Final | Change |
|--------|----------|-------|--------|
| sharpe_ratio | 8.2951 | 8.4486 | +0.1535 |
| mean_rank_ic | 0.4998 | 0.5984 | +0.0986 |
| excess_return | 2.5673 | 2.6452 | +0.0779 |
| hit_rate | 0.6106 | 0.6142 | +0.0036 |
| max_drawdown | -0.2590 | -0.2794 | -0.0205 |

**Best Feature**: obv (+0.4584 Sharpe)

## Step-by-Step Results

| Step | Feature | Sharpe | Rank IC | Marginal Sharpe | p-value | Sig? |
|------|---------|--------|---------|-----------------|---------|------|
| 0 | BASELINE | 8.2951 | 0.4998 | - | - | - |
| 1 | macd | 8.2713 | 0.4943 | -0.0238 | 0.0129 | YES |
| 2 | bollinger | 8.3426 | 0.5886 | +0.0713 | 0.0000 | YES |
| 3 | adx | 8.6328 | 0.5895 | +0.2902 | 0.6523 | no |
| 4 | valuation | 8.6328 | 0.5895 | +0.0000 | nan | no |
| 5 | gap | 8.5319 | 0.5949 | -0.1009 | 0.0016 | YES |
| 6 | atr | 8.3531 | 0.5860 | -0.1788 | 0.0000 | YES |
| 7 | obv | 8.8116 | 0.6002 | +0.4584 | 0.0001 | YES |
| 8 | rsi | 8.6712 | 0.6048 | -0.1403 | 0.0027 | YES |
| 9 | momentum | 8.4239 | 0.5934 | -0.2473 | 0.0000 | YES |
| 10 | mean_reversion | 8.4486 | 0.5984 | +0.0247 | 0.0067 | YES |
| 11 | sentiment | 8.4486 | 0.5984 | +0.0000 | nan | no |

## Feature Contribution Leaderboard

| Rank | Feature | Marginal Sharpe | Marginal IC | Importance % | Significant? |
|------|---------|-----------------|-------------|-------------|-------------|
| 1 | obv | +0.4584 | +0.0142 | 16.3% | YES |
| 2 | adx | +0.2902 | +0.0008 | 2.2% | no |
| 3 | bollinger | +0.0713 | +0.0944 | 25.6% | YES |
| 4 | mean_reversion | +0.0247 | +0.0050 | 0.6% | YES |
| 5 | valuation | +0.0000 | +0.0000 | 0.0% | no |
| 6 | sentiment | +0.0000 | +0.0000 | 0.0% | no |
| 7 | macd | -0.0238 | -0.0055 | 8.0% | YES |
| 8 | gap | -0.1009 | +0.0055 | 1.9% | YES |
| 9 | rsi | -0.1403 | +0.0045 | 0.4% | YES |
| 10 | atr | -0.1788 | -0.0089 | 2.9% | YES |
| 11 | momentum | -0.2473 | -0.0113 | 30.9% | YES |

## IC Regime Analysis

| Step | Feature | Recent IC | Historical IC | Z-Score | Status |
|------|---------|-----------|---------------|---------|--------|
| 0 | BASELINE | 0.6254 | 0.4998 | 2.82 | stable |
| 1 | macd | 0.6279 | 0.4943 | 3.08 | stable |
| 2 | bollinger | 0.7364 | 0.5886 | 3.89 | stable |
| 3 | adx | 0.7331 | 0.5895 | 3.84 | stable |
| 4 | valuation | 0.7331 | 0.5895 | 3.84 | stable |
| 5 | gap | 0.7449 | 0.5949 | 3.99 | stable |
| 6 | atr | 0.7368 | 0.5860 | 3.82 | stable |
| 7 | obv | 0.7591 | 0.6002 | 4.40 | stable |
| 8 | rsi | 0.7586 | 0.6048 | 4.29 | stable |
| 9 | momentum | 0.7325 | 0.5934 | 3.84 | stable |
| 10 | mean_reversion | 0.7441 | 0.5984 | 4.17 | stable |
| 11 | sentiment | 0.7441 | 0.5984 | 4.17 | stable |