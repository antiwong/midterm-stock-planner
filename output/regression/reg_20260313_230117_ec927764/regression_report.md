# Regression Test Report: Tech Giants Feature Regression

**ID**: reg_20260313_230117_ec927764
**Date**: 2026-03-13T23:01:17.112837
**Status**: completed
**Duration**: 24711.6s

## Summary

| Metric | Baseline | Final | Change |
|--------|----------|-------|--------|
| sharpe_ratio | -0.3531 | -0.3531 | +0.0000 |
| mean_rank_ic | 0.3405 | 0.1298 | -0.2107 |
| excess_return | -0.9173 | -0.9173 | +0.0000 |
| hit_rate | 0.5593 | 0.5593 | +0.0000 |
| max_drawdown | -0.9999 | -0.9999 | +0.0000 |

**Best Feature**: momentum (+0.0000 Sharpe)

## Step-by-Step Results

| Step | Feature | Sharpe | Rank IC | Marginal Sharpe | p-value | Sig? |
|------|---------|--------|---------|-----------------|---------|------|
| 0 | BASELINE | -0.3531 | 0.3405 | - | - | - |
| 1 | valuation | -0.3531 | 0.3405 | +0.0000 | nan | no |
| 2 | rsi | -0.3531 | 0.3389 | +0.0000 | 0.4647 | no |
| 3 | macd | -0.3531 | 0.3526 | +0.0000 | 0.0000 | YES |
| 4 | bollinger | -0.3531 | 0.1845 | +0.0000 | 0.0000 | YES |
| 5 | atr | -0.3531 | 0.2127 | +0.0000 | 0.0000 | YES |
| 6 | adx | -0.3531 | 0.2117 | +0.0000 | 0.6289 | no |
| 7 | obv | -0.3531 | 0.1586 | +0.0000 | 0.0000 | YES |
| 8 | gap | -0.3531 | 0.1607 | +0.0000 | 0.2276 | no |
| 9 | momentum | -0.3531 | 0.1304 | +0.0000 | 0.0000 | YES |
| 10 | mean_reversion | -0.3531 | 0.1298 | -0.0000 | 0.7757 | no |
| 11 | sentiment | -0.3531 | 0.1298 | +0.0000 | nan | no |

## Feature Contribution Leaderboard

| Rank | Feature | Marginal Sharpe | Marginal IC | Importance % | Significant? |
|------|---------|-----------------|-------------|-------------|-------------|
| 1 | momentum | +0.0000 | -0.0304 | 0.0% | YES |
| 2 | valuation | +0.0000 | +0.0000 | 0.0% | no |
| 3 | rsi | +0.0000 | -0.0016 | 4.5% | no |
| 4 | macd | +0.0000 | +0.0136 | 3.3% | YES |
| 5 | bollinger | +0.0000 | -0.1681 | 0.0% | YES |
| 6 | atr | +0.0000 | +0.0282 | 4.6% | YES |
| 7 | adx | +0.0000 | -0.0010 | 1.9% | no |
| 8 | obv | +0.0000 | -0.0530 | 7.2% | YES |
| 9 | gap | +0.0000 | +0.0021 | 0.0% | no |
| 10 | sentiment | +0.0000 | +0.0000 | 0.0% | no |
| 11 | mean_reversion | -0.0000 | -0.0005 | 0.0% | no |

## Guard Metric Violations

| Step | Feature | Metric | Value | Threshold |
|------|---------|--------|-------|-----------|
| 0 | BASELINE | max_drawdown | -0.9999 | -0.3 |
| 0 | BASELINE | train_test_sharpe_ratio | 67.6776 | 2.5 |
| 1 | valuation | max_drawdown | -0.9999 | -0.3 |
| 1 | valuation | train_test_sharpe_ratio | 67.6776 | 2.5 |
| 2 | rsi | max_drawdown | -0.9999 | -0.3 |
| 2 | rsi | train_test_sharpe_ratio | 67.6776 | 2.5 |
| 3 | macd | max_drawdown | -0.9999 | -0.3 |
| 3 | macd | train_test_sharpe_ratio | 67.6776 | 2.5 |
| 4 | bollinger | max_drawdown | -0.9999 | -0.3 |
| 4 | bollinger | train_test_sharpe_ratio | 67.6776 | 2.5 |
| 5 | atr | max_drawdown | -0.9999 | -0.3 |
| 5 | atr | train_test_sharpe_ratio | 67.6776 | 2.5 |
| 6 | adx | max_drawdown | -0.9999 | -0.3 |
| 6 | adx | train_test_sharpe_ratio | 67.6776 | 2.5 |
| 7 | obv | max_drawdown | -0.9999 | -0.3 |
| 7 | obv | train_test_sharpe_ratio | 67.6776 | 2.5 |
| 8 | gap | max_drawdown | -0.9999 | -0.3 |
| 8 | gap | train_test_sharpe_ratio | 67.6776 | 2.5 |
| 9 | momentum | max_drawdown | -0.9999 | -0.3 |
| 9 | momentum | train_test_sharpe_ratio | 67.6776 | 2.5 |
| 10 | mean_reversion | max_drawdown | -0.9999 | -0.3 |
| 10 | mean_reversion | train_test_sharpe_ratio | 67.6776 | 2.5 |
| 11 | sentiment | max_drawdown | -0.9999 | -0.3 |
| 11 | sentiment | train_test_sharpe_ratio | 67.6776 | 2.5 |