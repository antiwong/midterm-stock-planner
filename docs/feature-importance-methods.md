# Feature Importance Methods for Walk-Forward Backtesting

> [← Back to Documentation Index](README.md)

## Context

Our walk-forward backtest runs ~265 overlapping windows (7-day step, 3yr train, 6mo test) on 114 tickers. Each window trains a LightGBM regressor independently. We need feature importance that reflects this walk-forward structure, not a single model trained on all data.

**Problem with single-model approach:** Training one model on all data (a) sees future data that individual walk-forward windows wouldn't, (b) doesn't reflect how importance varies across market regimes, and (c) gives a single-point estimate instead of a distribution.

## Decision

**Use multiple complementary methods and look for convergence** (Lopez de Prado, *Advances in Financial ML*, 2018). A feature that shows up as important across methods is almost certainly real. A feature that only appears in one method is suspect.

## Method Comparison

| Method | Cost | Correlated Features | Regime Tracking | Model-Free? |
|--------|------|-------------------|----------------|------------|
| Avg LightGBM gain | Free | Poor (splits arbitrarily) | Yes | No |
| TreeSHAP on test sets | ~15 min | Fair (distributes among correlated) | Excellent | No |
| Permutation importance | ~5 min | Poor (creates impossible data) | Yes | Yes |
| Drop-column ablation | 50x backtest | Good (marginal contribution) | Only if per-window | Yes |
| Marginal IC per feature | Free | Good (both correlated show high) | Yes | Yes |
| Clustered importance (de Prado) | Same as underlying | Best | Yes | Depends |
| Stability selection | 50x per window | Good with subsampling | Yes | No |
| Mutual information | Cheap | Good (marginal) | Yes | Yes |

## Tiered Implementation

### Tier 1 — Implemented (cheap, high value)

Three complementary views that together give high confidence:

#### 1. Average LightGBM Gain Across Walk-Forward Windows

- **What:** Save `model.feature_importances_` (gain-based) from each of the 265 window models, average them.
- **Why:** Model-internal view — what the model actually uses to make splits.
- **Cost:** Essentially free (importances already computed during training).
- **Weakness:** Biased toward high-cardinality features. Splits importance arbitrarily among correlated features.
- **Storage:** Per-window importance array + mean/std summary.

#### 2. Marginal IC Per Feature Per Window

- **What:** For each feature, compute Spearman rank correlation with the target, per window.
- **Why:** Model-free signal quality measure — the standard "alpha factor" evaluation in quant finance.
- **Cost:** Near zero (just correlations on existing data).
- **Weakness:** Only captures monotonic relationships. Misses nonlinear effects that LightGBM exploits. Doesn't account for feature interactions.
- **Storage:** Per-feature, per-window IC array + mean/std summary.

#### 3. TreeSHAP on Walk-Forward Test Sets

- **What:** For each window, compute SHAP values on the test set using TreeSHAP. Average absolute SHAP values.
- **Why:** Theoretically grounded (Shapley values from cooperative game theory). Measures actual contribution to predictions on unseen data. Provides both local (per-sample) and global importance.
- **Cost:** ~15 min total for 265 windows (~3 seconds per window).
- **Weakness:** Can distribute importance among correlated features unstably. Assumes feature independence when computing marginal contributions.
- **Storage:** Per-feature mean absolute SHAP per window + summary.

### Tier 2 — Future (when needed)

#### 4. Clustered Feature Importance (de Prado)

- **What:** Cluster correlated features using hierarchical clustering on the correlation matrix. Evaluate importance at the cluster level by permuting/dropping entire clusters.
- **Why:** Solves the correlated-feature problem that plagues all Tier 1 methods.
- **When:** After we have more features or see inconsistent results across Tier 1 methods.

#### 5. Time-Varying Importance Dashboard

- **What:** Track per-window importance as time series. Detect regime shifts via CUSUM or change-point detection.
- **When:** After Tier 1 per-window data is stored and we want to analyze regime changes.

### Tier 3 — Skip

- **Drop-column ablation:** 50x backtest cost (~33 hours). Only for final validation of top features.
- **Stability selection:** Redundant — 265 walk-forward windows already provide stability information.
- **Mutual information:** Unreliable at our sample sizes (~750 samples, low SNR in financial data).

## Convergence Scoring

A feature's "convergence score" indicates confidence in its importance:

```
convergence = (
    normalize(avg_lgbm_gain) +
    normalize(avg_marginal_ic) +
    normalize(avg_abs_shap)
) / 3
```

Features with high convergence across all three methods are reliably important. Features with divergent scores warrant investigation (e.g., high SHAP but low marginal IC suggests the model uses it in a nonlinear way that simple correlation misses).

## The Correlated Features Problem

Our feature set has known correlations:
- RSI <-> Bollinger bands (both derived from price oscillation)
- Momentum <-> Returns (overlapping lookback periods)
- ADX <-> ATR (both measure trend/volatility)

All Tier 1 methods handle correlated features imperfectly. The practical mitigation:
1. **Be aware** — when two correlated features show split/low importance, check if their combined importance is high.
2. **Use marginal IC** as the "would this feature work alone?" test.
3. **Implement clustered importance (Tier 2)** if correlation-driven confusion becomes a problem.

## References

- Lopez de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. Ch. 8: Feature Importance.
- Lundberg & Lee (2017). *A Unified Approach to Interpreting Model Predictions* (SHAP).
- Strobl et al. (2007). *Bias in random forest variable importance measures*.
- Hooker & Mentch (2019). *Please Stop Permuting Features*.
- Coqueret & Guida (2020). *Machine Learning for Factor Investing*.

---

## See Also

- [Model training pipeline](model-training.md)
- [Walk-forward backtesting](backtesting.md)
- [SHAP explanations](explainability.md)
- [Feature definitions](technical-indicators.md)
- [Regression testing](regression-testing-guide.md)
