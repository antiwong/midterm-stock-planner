# Regression Test Report: Tech Giants Fixed Sharpe v2

**ID**: reg_20260315_071349_7b37a065
**Date**: 2026-03-15T07:13:49.130574
**Status**: completed
**Duration**: 2055.5s

## Summary

| Metric | Baseline | Final | Change |
|--------|----------|-------|--------|
| sharpe_ratio | -0.1021 | -0.0997 | +0.0024 |
| mean_rank_ic | 0.4149 | 0.5220 | +0.1071 |
| excess_return | -1.0000 | -1.0000 | +0.0000 |
| hit_rate | 0.5347 | 0.5433 | +0.0086 |
| max_drawdown | -1.0015 | -1.0087 | -0.0072 |

**Best Feature**: bollinger (+0.0051 Sharpe)

## Step-by-Step Results

| Step | Feature | Sharpe | Rank IC | Marginal Sharpe | p-value | Sig? |
|------|---------|--------|---------|-----------------|---------|------|
| 0 | BASELINE | -0.1021 | 0.4149 | - | - | - |
| 1 | valuation | -0.1021 | 0.4149 | +0.0000 | nan | no |
| 2 | rsi | -0.1021 | 0.4122 | +0.0000 | 0.0051 | YES |
| 3 | macd | -0.1044 | 0.4208 | -0.0023 | 0.0000 | YES |
| 4 | bollinger | -0.0993 | 0.4784 | +0.0051 | 0.0000 | YES |
| 5 | atr | -0.1000 | 0.4785 | -0.0007 | 0.8977 | no |
| 6 | adx | -0.1002 | 0.4780 | -0.0002 | 0.5319 | no |
| 7 | obv | -0.1004 | 0.5288 | -0.0002 | 0.0000 | YES |
| 8 | gap | -0.1002 | 0.5283 | +0.0001 | 0.4648 | no |
| 9 | momentum | -0.0997 | 0.5226 | +0.0005 | 0.0003 | YES |
| 10 | mean_reversion | -0.0997 | 0.5220 | -0.0000 | 0.3776 | no |

## Feature Contribution Leaderboard

| Rank | Feature | Marginal Sharpe | Marginal IC | Importance % | Significant? |
|------|---------|-----------------|-------------|-------------|-------------|
| 1 | bollinger | +0.0051 | +0.0576 | 0.0% | YES |
| 2 | momentum | +0.0005 | -0.0057 | 0.0% | YES |
| 3 | gap | +0.0001 | -0.0006 | 0.0% | no |
| 4 | rsi | +0.0000 | -0.0027 | 1.7% | YES |
| 5 | valuation | +0.0000 | +0.0000 | 0.0% | no |
| 6 | mean_reversion | -0.0000 | -0.0006 | 0.0% | no |
| 7 | adx | -0.0002 | -0.0005 | 0.9% | no |
| 8 | obv | -0.0002 | +0.0508 | 11.4% | YES |
| 9 | atr | -0.0007 | +0.0001 | 5.5% | no |
| 10 | macd | -0.0023 | +0.0086 | 2.8% | YES |

## Guard Metric Violations

| Step | Feature | Metric | Value | Threshold |
|------|---------|--------|-------|-----------|
| 0 | BASELINE | max_drawdown | -1.0015 | -0.3 |
| 0 | BASELINE | train_test_sharpe_ratio | 45.7941 | 2.5 |
| 1 | valuation | max_drawdown | -1.0015 | -0.3 |
| 1 | valuation | train_test_sharpe_ratio | 45.7941 | 2.5 |
| 2 | rsi | max_drawdown | -1.0007 | -0.3 |
| 2 | rsi | train_test_sharpe_ratio | 79.0998 | 2.5 |
| 3 | macd | max_drawdown | -1.0097 | -0.3 |
| 3 | macd | train_test_sharpe_ratio | 240.7215 | 2.5 |
| 4 | bollinger | max_drawdown | -1.0080 | -0.3 |
| 4 | bollinger | train_test_sharpe_ratio | 80.1443 | 2.5 |
| 5 | atr | max_drawdown | -1.0086 | -0.3 |
| 5 | atr | train_test_sharpe_ratio | 86.7472 | 2.5 |
| 6 | adx | max_drawdown | -1.0087 | -0.3 |
| 6 | adx | train_test_sharpe_ratio | 67.3407 | 2.5 |
| 7 | obv | max_drawdown | -1.0078 | -0.3 |
| 7 | obv | train_test_sharpe_ratio | 145.2881 | 2.5 |
| 8 | gap | max_drawdown | -1.0087 | -0.3 |
| 8 | gap | train_test_sharpe_ratio | 727.0864 | 2.5 |
| 9 | momentum | max_drawdown | -1.0081 | -0.3 |
| 9 | momentum | train_test_sharpe_ratio | 18.3512 | 2.5 |
| 10 | mean_reversion | max_drawdown | -1.0087 | -0.3 |
| 10 | mean_reversion | train_test_sharpe_ratio | 76.5199 | 2.5 |