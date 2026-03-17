# Regression Test Report: reg_moby_picks_20260316

**ID**: reg_20260316_231056_8f18975f
**Date**: 2026-03-16T23:10:56.745759
**Status**: completed
**Duration**: 5187.5s

## Summary

| Metric | Baseline | Final | Change |
|--------|----------|-------|--------|
| sharpe_ratio | 19.4467 | 19.1056 | -0.3412 |
| mean_rank_ic | 0.3409 | 0.4294 | +0.0885 |
| excess_return | 6.4064 | 6.4767 | +0.0703 |
| hit_rate | 0.6650 | 0.6865 | +0.0215 |
| max_drawdown | -0.2509 | -0.3332 | -0.0823 |

**Best Feature**: bollinger (+2.7501 Sharpe)

## Step-by-Step Results

| Step | Feature | Sharpe | Rank IC | Marginal Sharpe | p-value | Sig? |
|------|---------|--------|---------|-----------------|---------|------|
| 0 | BASELINE | 19.4467 | 0.3409 | - | - | - |
| 1 | macd | 19.7118 | 0.3486 | +0.2651 | 0.0000 | YES |
| 2 | bollinger | 22.4619 | 0.3997 | +2.7501 | 0.0000 | YES |
| 3 | adx | 22.2538 | 0.3997 | -0.2081 | 0.9542 | no |
| 4 | valuation | 22.2538 | 0.3997 | +0.0000 | nan | no |
| 5 | gap | 22.2781 | 0.3998 | +0.0243 | 0.9483 | no |
| 6 | atr | 21.3156 | 0.4009 | -0.9625 | 0.4233 | no |
| 7 | obv | 20.6899 | 0.4394 | -0.6257 | 0.0000 | YES |
| 8 | rsi | 20.9652 | 0.4351 | +0.2753 | 0.0005 | YES |
| 9 | momentum | 20.7601 | 0.4306 | -0.2051 | 0.0067 | YES |
| 10 | mean_reversion | 18.8399 | 0.4323 | -1.9202 | 0.1704 | no |
| 11 | sentiment | 18.8399 | 0.4323 | +0.0000 | nan | no |
| 12 | rotation | 19.1056 | 0.4294 | +0.2656 | 0.0384 | YES |

## Feature Contribution Leaderboard

| Rank | Feature | Marginal Sharpe | Marginal IC | Importance % | Significant? |
|------|---------|-----------------|-------------|-------------|-------------|
| 1 | bollinger | +2.7501 | +0.0510 | 26.0% | YES |
| 2 | rsi | +0.2753 | -0.0044 | 0.1% | YES |
| 3 | rotation | +0.2656 | -0.0029 | 0.7% | YES |
| 4 | macd | +0.2651 | +0.0078 | 9.9% | YES |
| 5 | gap | +0.0243 | +0.0001 | 1.6% | no |
| 6 | valuation | +0.0000 | +0.0000 | 0.0% | no |
| 7 | sentiment | +0.0000 | +0.0000 | 0.0% | no |
| 8 | momentum | -0.2051 | -0.0045 | 23.6% | YES |
| 9 | adx | -0.2081 | +0.0001 | 0.9% | no |
| 10 | obv | -0.6257 | +0.0385 | 14.7% | YES |
| 11 | atr | -0.9625 | +0.0011 | 4.0% | no |
| 12 | mean_reversion | -1.9202 | +0.0017 | 1.2% | no |

## Guard Metric Violations

| Step | Feature | Metric | Value | Threshold |
|------|---------|--------|-------|-----------|
| 2 | bollinger | max_drawdown | -0.3304 | -0.3 |
| 3 | adx | max_drawdown | -0.3221 | -0.3 |
| 4 | valuation | max_drawdown | -0.3221 | -0.3 |
| 5 | gap | max_drawdown | -0.3204 | -0.3 |
| 6 | atr | max_drawdown | -0.3211 | -0.3 |
| 7 | obv | max_drawdown | -0.3275 | -0.3 |
| 8 | rsi | max_drawdown | -0.3241 | -0.3 |
| 9 | momentum | max_drawdown | -0.3271 | -0.3 |
| 10 | mean_reversion | max_drawdown | -0.3378 | -0.3 |
| 11 | sentiment | max_drawdown | -0.3378 | -0.3 |
| 12 | rotation | max_drawdown | -0.3332 | -0.3 |

## IC Regime Analysis

| Step | Feature | Recent IC | Historical IC | Z-Score | Status |
|------|---------|-----------|---------------|---------|--------|
| 0 | BASELINE | 0.5013 | 0.3409 | 5.22 | stable |
| 1 | macd | 0.4958 | 0.3486 | 5.17 | stable |
| 2 | bollinger | 0.5334 | 0.3997 | 5.25 | stable |
| 3 | adx | 0.5364 | 0.3997 | 5.29 | stable |
| 4 | valuation | 0.5364 | 0.3997 | 5.29 | stable |
| 5 | gap | 0.5314 | 0.3998 | 5.11 | stable |
| 6 | atr | 0.5343 | 0.4009 | 5.29 | stable |
| 7 | obv | 0.5275 | 0.4394 | 3.74 | stable |
| 8 | rsi | 0.5375 | 0.4351 | 4.30 | stable |
| 9 | momentum | 0.5418 | 0.4306 | 4.65 | stable |
| 10 | mean_reversion | 0.5425 | 0.4323 | 4.60 | stable |
| 11 | sentiment | 0.5425 | 0.4323 | 4.60 | stable |
| 12 | rotation | 0.5403 | 0.4294 | 4.55 | stable |