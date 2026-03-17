# Regression Test Report: sharpe-fix-v2

**ID**: reg_20260315_075520_052fa388
**Date**: 2026-03-15T07:55:20.121272
**Status**: completed
**Duration**: 2384.5s

## Summary

| Metric | Baseline | Final | Change |
|--------|----------|-------|--------|
| sharpe_ratio | 0.7780 | 0.8891 | +0.1111 |
| mean_rank_ic | 0.4149 | 0.5220 | +0.1071 |
| excess_return | 0.1251 | 0.1725 | +0.0475 |
| hit_rate | 0.5197 | 0.5311 | +0.0115 |
| max_drawdown | -0.7208 | -0.6375 | +0.0833 |

**Best Feature**: bollinger (+0.6413 Sharpe)

## Step-by-Step Results

| Step | Feature | Sharpe | Rank IC | Marginal Sharpe | p-value | Sig? |
|------|---------|--------|---------|-----------------|---------|------|
| 0 | BASELINE | 0.7780 | 0.4149 | - | - | - |
| 1 | valuation | 0.7780 | 0.4149 | +0.0000 | nan | no |
| 2 | rsi | 0.4985 | 0.4122 | -0.2795 | 0.0051 | YES |
| 3 | macd | 0.6515 | 0.4208 | +0.1530 | 0.0000 | YES |
| 4 | bollinger | 1.2927 | 0.4784 | +0.6413 | 0.0000 | YES |
| 5 | atr | 1.2614 | 0.4785 | -0.0313 | 0.8977 | no |
| 6 | adx | 1.3393 | 0.4780 | +0.0779 | 0.5319 | no |
| 7 | obv | 1.1596 | 0.5288 | -0.1797 | 0.0000 | YES |
| 8 | gap | 1.1811 | 0.5283 | +0.0215 | 0.4648 | no |
| 9 | momentum | 0.9414 | 0.5226 | -0.2397 | 0.0003 | YES |
| 10 | mean_reversion | 0.8891 | 0.5220 | -0.0523 | 0.3776 | no |
| 11 | sentiment | 0.8891 | 0.5220 | +0.0000 | nan | no |

## Feature Contribution Leaderboard

| Rank | Feature | Marginal Sharpe | Marginal IC | Importance % | Significant? |
|------|---------|-----------------|-------------|-------------|-------------|
| 1 | bollinger | +0.6413 | +0.0576 | 0.0% | YES |
| 2 | macd | +0.1530 | +0.0086 | 2.8% | YES |
| 3 | adx | +0.0779 | -0.0005 | 0.9% | no |
| 4 | gap | +0.0215 | -0.0006 | 0.0% | no |
| 5 | valuation | +0.0000 | +0.0000 | 0.0% | no |
| 6 | sentiment | +0.0000 | +0.0000 | 0.0% | no |
| 7 | atr | -0.0313 | +0.0001 | 5.5% | no |
| 8 | mean_reversion | -0.0523 | -0.0006 | 0.0% | no |
| 9 | obv | -0.1797 | +0.0508 | 11.4% | YES |
| 10 | momentum | -0.2397 | -0.0057 | 0.0% | YES |
| 11 | rsi | -0.2795 | -0.0027 | 1.7% | YES |

## Guard Metric Violations

| Step | Feature | Metric | Value | Threshold |
|------|---------|--------|-------|-----------|
| 0 | BASELINE | max_drawdown | -0.7208 | -0.3 |
| 0 | BASELINE | train_test_sharpe_ratio | 45.7941 | 2.5 |
| 1 | valuation | max_drawdown | -0.7208 | -0.3 |
| 1 | valuation | train_test_sharpe_ratio | 45.7941 | 2.5 |
| 2 | rsi | max_drawdown | -0.7448 | -0.3 |
| 2 | rsi | train_test_sharpe_ratio | 79.0998 | 2.5 |
| 3 | macd | max_drawdown | -0.7322 | -0.3 |
| 3 | macd | train_test_sharpe_ratio | 240.7215 | 2.5 |
| 4 | bollinger | max_drawdown | -0.5522 | -0.3 |
| 4 | bollinger | train_test_sharpe_ratio | 80.1443 | 2.5 |
| 5 | atr | max_drawdown | -0.5660 | -0.3 |
| 5 | atr | train_test_sharpe_ratio | 123.8436 | 2.5 |
| 6 | adx | max_drawdown | -0.5490 | -0.3 |
| 6 | adx | train_test_sharpe_ratio | 280.1260 | 2.5 |
| 7 | obv | max_drawdown | -0.5793 | -0.3 |
| 7 | obv | train_test_sharpe_ratio | 145.8281 | 2.5 |
| 8 | gap | max_drawdown | -0.5789 | -0.3 |
| 8 | gap | train_test_sharpe_ratio | 727.0864 | 2.5 |
| 9 | momentum | max_drawdown | -0.6200 | -0.3 |
| 9 | momentum | train_test_sharpe_ratio | 18.3599 | 2.5 |
| 10 | mean_reversion | max_drawdown | -0.6375 | -0.3 |
| 10 | mean_reversion | train_test_sharpe_ratio | 76.8835 | 2.5 |
| 11 | sentiment | max_drawdown | -0.6375 | -0.3 |
| 11 | sentiment | train_test_sharpe_ratio | 76.8835 | 2.5 |