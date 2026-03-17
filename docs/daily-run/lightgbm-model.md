# LightGBM Model

> [← Daily Run Index](README.md) | [← Documentation Index](../README.md)

The pipeline uses **LightGBM** (Light Gradient Boosting Machine) to predict which stocks will outperform the S&P 500 over the next 63 trading days. A fresh model is trained for each walk-forward window.

**Source:** `src/models/trainer.py` (training), `src/models/predictor.py` (prediction)

---

## What Is LightGBM?

LightGBM is a gradient boosting framework that builds an ensemble of decision trees sequentially. Each tree corrects the errors of the previous ones.

```
Prediction = Tree_1(features) + Tree_2(features) + ... + Tree_200(features)
                  ↑                    ↑                        ↑
             learns the          learns the              learns remaining
             main pattern        residual errors          subtle patterns
```

**Why LightGBM for stock ranking:**
- Handles non-linear relationships (e.g., Bollinger %B has different meaning at extremes)
- Built-in feature selection (ignores uninformative features)
- Fast training (~1 second per window on daily data)
- L1/L2 regularization prevents overfitting
- Robust to missing values and outliers

**Reference:** Ke et al., "LightGBM: A Highly Efficient Gradient Boosting Decision Tree" (NeurIPS 2017)

---

## Hyperparameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `n_estimators` | 200 | Number of boosting rounds (trees) |
| `learning_rate` | 0.03 | Shrinkage per tree (slow learning = more robust) |
| `max_depth` | 6 | Maximum tree depth |
| `num_leaves` | 15 | Maximum leaf nodes per tree (< 2^depth to prevent overfitting) |
| `min_child_samples` | 50 | Minimum samples to create a leaf (prevents fitting to noise) |
| `reg_alpha` | 0.3 | L1 regularization (feature selection pressure) |
| `reg_lambda` | 0.5 | L2 regularization (weight shrinkage) |
| `subsample` | 0.7 | Row sampling per tree (70% of data) |
| `colsample_bytree` | 0.7 | Feature sampling per tree (70% of features) |
| `early_stopping_rounds` | 30 | Stop if validation loss doesn't improve for 30 rounds |
| `random_state` | 42 | Reproducibility seed |

### Why These Values?

These hyperparameters were tuned to prevent severe overfitting discovered during regression testing (train/test Sharpe ratios of 18-727x before tuning):

- **Low learning rate (0.03):** Each tree makes small corrections, reducing variance
- **Shallow trees (depth=6, leaves=15):** Prevents memorizing complex patterns
- **High min_child_samples (50):** Requires substantial evidence before splitting
- **L1 + L2 regularization:** Pushes small weights to zero, shrinks large weights
- **70% subsampling:** Each tree sees different data and features, reducing correlation between trees
- **Early stopping (30 rounds):** Stops training when validation performance plateaus

**Reference:** Overfitting fix documented in beads memory `overfitting-fix-regularization-2026-03-15`

---

## Training Process

```python
def train_lgbm_regressor(X_train, y_train, config):
    # 1. Split into train/validation (80/20)
    X_tr, X_val, y_tr, y_val = train_test_split(X_train, y_train, test_size=0.2)

    # 2. Create LightGBM model
    model = lgb.LGBMRegressor(**params)

    # 3. Train with early stopping
    model.fit(
        X_tr, y_tr,
        eval_set=[(X_val, y_val)],
        callbacks=[early_stopping(30)]
    )

    # 4. Return model + metrics
    return model, {
        'rmse': rmse(model.predict(X_val), y_val),
        'mae': mae(model.predict(X_val), y_val),
        'n_train': len(X_tr),
        'n_valid': len(X_val),
        'best_iteration': model.best_iteration_
    }
```

---

## Prediction & Ranking

After training, the model produces a continuous score for each stock. Higher score = predicted to outperform SPY more.

```python
def predict(model, X):
    scores = model.predict(X[feature_names])    # Continuous score

    # Cross-sectional ranking (within each date)
    for date in unique_dates:
        mask = (X['date'] == date)
        ranks = scores[mask].rank(ascending=False)  # Rank 1 = best
        percentile = (1 - ranks / n_stocks) * 100   # 100th = best

    return scores, ranks, percentiles
```

**Important:** The model predicts *relative* outperformance (excess return vs SPY), not absolute returns. This is a cross-sectional ranking model — it only needs to get the *order* right, not the magnitude.

---

## Feature Importance

Three methods are used to assess which features contribute most to predictions:

### 1. LightGBM Gain (Free, Model-Internal)

```
importance[feature] = sum of split gain when feature is used for splitting
```

Built into LightGBM. Averaged across all walk-forward windows for stability.

**Limitation:** Biased toward high-cardinality features and can be misleading when features are correlated.

### 2. Marginal IC (Free, Model-Free)

```
marginal_IC[feature] = spearman_corr(feature[t], excess_return[t+63])
```

Computed per window, averaged across windows. Measures raw predictive power of each feature independently.

**Limitation:** Doesn't capture feature interactions or conditional effects.

### 3. TreeSHAP (Expensive, Model-External)

```
SHAP_value[feature, sample] = contribution of this feature to this prediction
importance[feature] = mean(abs(SHAP_values[feature, :]))
```

Uses Shapley values from cooperative game theory to decompose each prediction into per-feature contributions.

**Limitation:** Adds ~15 minutes per backtest. Only enabled with `compute_shap=True`.

### Convergence Principle

A feature is genuinely important if **all three methods agree**. If gain says a feature is important but IC and SHAP don't, the model may be overfitting to noise in that feature.

**Reference:** Lopez de Prado, "Advances in Financial Machine Learning" (2018)

---

## SHAP Explanations

When enabled, TreeSHAP provides per-stock interpretability:

```
For stock NVDA on 2026-03-15:
  Prediction: 0.0234 (excess return)
  Breakdown:
    bollinger_pct:    +0.0089   (price near lower band → bullish)
    return_3m:        +0.0067   (strong recent momentum)
    vol_20d:          -0.0043   (high volatility → penalty)
    macd_histogram:   +0.0031   (positive MACD crossover)
    dollar_volume_20d: +0.0018  (high liquidity → premium)
    ...
```

This explains *why* the model ranked NVDA highly — useful for building confidence in signals before execution.

**Source:** `src/backtest/rolling.py` (SHAP computation per window), `src/features/engineering.py` (feature interpretation)

---

## Model Persistence

Models are saved with full metadata for reproducibility:

```
output/models/
├── model_20260316.txt           # LightGBM native format
└── model_20260316_metadata.json # Training params, features, metrics
```

Metadata includes: feature names, training date, hyperparameters, RMSE, MAE, number of training/validation samples, best iteration count.

---

## See Also

- [Feature Engineering](feature-engineering.md) — input features
- [Walk-Forward Backtest](walk-forward-backtest.md) — how models are trained and evaluated
- [Signal Generation](signal-generation.md) — how predictions become signals
- [Model Training](../model-training.md) — extended model reference
- [Explainability](../explainability.md) — SHAP and interpretability
- [Feature Importance Methods](../feature-importance-methods.md) — multi-method importance analysis
