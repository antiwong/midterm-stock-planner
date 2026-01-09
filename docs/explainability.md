# Explainability & Interpretability

> **Part of**: [Mid-term Stock Planner Design](design.md)
> 
> This document covers SHAP explanations, feature importance, and model interpretability.

## Related Documents

- [design.md](design.md) - Main overview and architecture
- [model-training.md](model-training.md) - Model training
- [risk-management.md](risk-management.md) - Portfolio analysis
- [visualization-analytics.md](visualization-analytics.md) - Visualization of explanations

---

## 1. SHAP Explainability Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SHAP EXPLAINABILITY                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                         GLOBAL EXPLANATION                                    │
│                                                                               │
│  Feature Importance (Mean |SHAP|)                                             │
│                                                                               │
│  return_3m      ████████████████████████████  0.45                           │
│  vol_20d        ████████████████████         0.32                            │
│  pe_ratio       ██████████████               0.25                            │
│  return_12m     ████████████                 0.20                            │
│  dollar_volume  ██████████                   0.18                            │
│  return_1m      ████████                     0.15                            │
│  pb_ratio       ██████                       0.12                            │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                         LOCAL EXPLANATION (Per Stock)                         │
│                                                                               │
│  AAPL Score: +0.08 (Predicted 8% excess return)                              │
│                                                                               │
│  Feature Contributions:                                                       │
│                                                                               │
│  return_3m (+15%)     ████████████████  +0.05  ← Strong momentum             │
│  vol_20d (12%)        ████████         +0.02  ← Low volatility               │
│  pe_ratio (28)        ██████           +0.01  ← Reasonable valuation         │
│  dollar_volume        ████             +0.01  ← High liquidity               │
│  return_12m (-5%)     ██               -0.01  ← Weak annual return           │
│                       ─────────────────────                                   │
│  Base value           ───────          +0.00  (Average prediction)           │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. SHAP Overview

### 2.1 What is SHAP?

**SHAP (SHapley Additive exPlanations)** provides a unified approach to explaining model predictions:

- **Additive**: Feature contributions sum to the prediction
- **Consistent**: Higher feature impact → higher SHAP value
- **Local accuracy**: Explanations match model output exactly

### 2.2 SHAP for Tree Models

```python
# TreeExplainer is optimal for LightGBM/XGBoost
import shap

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)

# For each prediction:
# prediction = base_value + sum(shap_values)
```

---

## 3. Core Functions

### 3.1 API

```python
# src/explain/shap_explain.py

def compute_shap_values(
    model: LGBMRegressor,
    X: pd.DataFrame
) -> Tuple[np.ndarray, shap.TreeExplainer]:
    """
    Compute SHAP values for all samples.
    
    Args:
        model: Trained LightGBM model
        X: Feature matrix
    
    Returns:
        Tuple of (shap_values array, explainer object)
    """

def summarize_feature_importance(
    shap_values: np.ndarray,
    feature_names: List[str]
) -> pd.Series:
    """
    Compute global feature importance from SHAP values.
    
    Args:
        shap_values: SHAP values array
        feature_names: Feature column names
    
    Returns:
        Series of mean |SHAP| per feature, sorted descending
    """

def explain_stock(
    model: LGBMRegressor,
    X_row: pd.DataFrame,
    feature_names: List[str]
) -> Dict[str, Any]:
    """
    Explain prediction for a single stock.
    
    Args:
        model: Trained model
        X_row: Single row feature DataFrame
        feature_names: Feature names
    
    Returns:
        Dict with:
        - prediction: Model output
        - base_value: Average prediction
        - contributions: Dict of feature -> SHAP value
        - top_positive: Top features increasing score
        - top_negative: Top features decreasing score
    """
```

### 3.2 Implementation

```python
def compute_shap_values(model, X):
    """Compute SHAP values using TreeExplainer."""
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    return shap_values, explainer

def summarize_feature_importance(shap_values, feature_names):
    """Global importance = mean |SHAP| per feature."""
    importance = np.abs(shap_values).mean(axis=0)
    return pd.Series(
        importance, 
        index=feature_names
    ).sort_values(ascending=False)

def explain_stock(model, X_row, feature_names):
    """Local explanation for one stock."""
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_row)
    
    contributions = dict(zip(feature_names, shap_values[0]))
    sorted_contrib = sorted(
        contributions.items(), 
        key=lambda x: abs(x[1]), 
        reverse=True
    )
    
    return {
        "prediction": model.predict(X_row)[0],
        "base_value": explainer.expected_value,
        "contributions": contributions,
        "top_positive": [(k, v) for k, v in sorted_contrib if v > 0][:5],
        "top_negative": [(k, v) for k, v in sorted_contrib if v < 0][:5],
    }
```

---

## 4. Global Explanations

### 4.1 Feature Importance

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GLOBAL FEATURE IMPORTANCE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

  Method: Mean |SHAP value| across all predictions
  
  Feature          Mean |SHAP|    Interpretation
  ───────────────────────────────────────────────────────────────────
  return_3m         0.045         3-month momentum is primary driver
  vol_20d           0.032         Volatility matters for stock selection
  pe_ratio          0.025         Valuation is important
  return_12m        0.020         Annual momentum adds signal
  dollar_volume     0.018         Liquidity affects predictions
  return_1m         0.015         Short-term momentum contributes
  pb_ratio          0.012         Book value valuation adds info
```

### 4.2 SHAP Summary Plot

```python
import shap

# Beeswarm plot - shows distribution of SHAP values
shap.summary_plot(shap_values, X, feature_names=feature_names)

# Bar plot - shows mean |SHAP|
shap.summary_plot(shap_values, X, plot_type="bar")
```

### 4.3 Feature Interaction

```python
# Check if two features interact
shap.dependence_plot(
    "return_3m", 
    shap_values, 
    X,
    interaction_index="vol_20d"  # Color by interaction feature
)
```

---

## 5. Local Explanations

### 5.1 Per-Stock Explanation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PER-STOCK EXPLANATION: NVDA                               │
└─────────────────────────────────────────────────────────────────────────────┘

  Predicted Score: +0.12 (12% expected excess return)
  Base Value: 0.00 (average prediction across all stocks)
  
  Feature Breakdown:
  
    Feature        Value       SHAP        Impact
    ──────────────────────────────────────────────────
    return_3m      +25%       +0.06       Strong momentum ↑
    vol_20d        15%        +0.02       Moderate vol (good) ↑
    pe_ratio       35         +0.01       Growth premium ↑
    return_12m     +80%       +0.02       Strong annual perf ↑
    dollar_volume  High       +0.01       Very liquid ↑
    ──────────────────────────────────────────────────
    Sum of SHAP:              +0.12       = Final prediction
  
  Narrative: NVDA scores high primarily due to strong 3-month 
  momentum (+25%) and solid annual returns. Moderate volatility 
  and high liquidity contribute positively.
```

### 5.2 Waterfall Plot

```python
# Show how features contribute to single prediction
shap.waterfall_plot(
    shap.Explanation(
        values=shap_values[idx],
        base_values=explainer.expected_value,
        data=X.iloc[idx],
        feature_names=feature_names
    )
)
```

### 5.3 Force Plot

```python
# Compact visualization of contributions
shap.force_plot(
    explainer.expected_value,
    shap_values[idx],
    X.iloc[idx],
    feature_names=feature_names
)
```

---

## 6. Portfolio-Level SHAP

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PORTFOLIO-LEVEL SHAP AGGREGATION                          │
└─────────────────────────────────────────────────────────────────────────────┘

Portfolio Holdings (Top 10):
┌────────┬────────┬─────────────────────────────────────────────────────────┐
│ Ticker │ Weight │           Factor Contributions (SHAP × Weight)          │
├────────┼────────┼─────────────────────────────────────────────────────────┤
│ AAPL   │  10%   │  momentum: +0.02   value: +0.01   vol: +0.005          │
│ NVDA   │  10%   │  momentum: +0.03   value: -0.01   vol: +0.01           │
│ MSFT   │  10%   │  momentum: +0.015  value: +0.02   vol: +0.003          │
│ AMD    │  10%   │  momentum: +0.025  value: +0.005  vol: +0.008          │
│ ...    │  ...   │  ...                                                    │
└────────┴────────┴─────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              AGGREGATED PORTFOLIO FACTOR EXPOSURE                            │
│                                                                              │
│  Momentum    ████████████████████████████████████  +0.15  ← DOMINANT        │
│  Value       ██████████████                        +0.06                     │
│  Low Vol     ████████████                          +0.05                     │
│  Liquidity   ██████████                            +0.04                     │
│  Growth      ████████                              +0.03                     │
│                                                                              │
│  ⚠️  WARNING: Portfolio has high concentration in momentum factor!           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.1 Portfolio SHAP Function

```python
def compute_portfolio_shap(
    model: LGBMRegressor,
    X_portfolio: pd.DataFrame,
    weights: pd.Series,
    feature_names: List[str],
    factor_mapping: Optional[Dict[str, List[str]]] = None
) -> Dict[str, Any]:
    """
    Compute portfolio-level SHAP aggregation.
    
    Args:
        model: Trained model
        X_portfolio: Features for portfolio stocks
        weights: Portfolio weights per stock
        feature_names: Feature column names
        factor_mapping: Optional mapping of features to factors
    
    Returns:
        Dict with:
        - stock_shap: Per-stock SHAP values
        - weighted_shap: Weight-adjusted SHAP per feature
        - factor_exposure: Factor-level aggregation (if mapping provided)
        - concentration_warning: True if single factor dominates
    """
```

### 6.2 Factor Mapping

```python
# Map features to economic factors
FACTOR_MAPPING = {
    "momentum": ["return_1m", "return_3m", "return_6m", "return_12m"],
    "value": ["pe_ratio", "pb_ratio", "earnings_yield"],
    "volatility": ["vol_20d", "vol_60d", "atr"],
    "liquidity": ["dollar_volume", "volume_ratio", "turnover"],
    "quality": ["roe", "roa", "debt_to_equity"],
}

# Aggregate SHAP to factor level
factor_exposure = {}
for factor, features in FACTOR_MAPPING.items():
    factor_exposure[factor] = weighted_shap[features].sum()
```

### 6.3 Concentration Detection

```python
def detect_factor_concentration(
    factor_exposure: Dict[str, float],
    threshold: float = 0.5
) -> List[str]:
    """
    Detect if portfolio is concentrated in few factors.
    
    Args:
        factor_exposure: Factor-level SHAP sums
        threshold: Concentration threshold
    
    Returns:
        List of warnings
    """
    total = sum(abs(v) for v in factor_exposure.values())
    warnings = []
    
    for factor, exposure in factor_exposure.items():
        if abs(exposure) / total > threshold:
            warnings.append(
                f"High concentration in {factor}: "
                f"{exposure/total:.1%} of total"
            )
    
    return warnings
```

---

## 7. Robustness Checks

### 7.1 Feature Perturbation

```python
def sensitivity_analysis(
    model: LGBMRegressor,
    X: pd.DataFrame,
    feature: str,
    perturbation_pct: float = 0.1
) -> pd.DataFrame:
    """
    Analyze sensitivity to feature perturbations.
    
    Perturbs feature by ±perturbation_pct and measures
    change in predictions.
    """
    X_perturbed = X.copy()
    X_perturbed[feature] *= (1 + perturbation_pct)
    
    original_pred = model.predict(X)
    perturbed_pred = model.predict(X_perturbed)
    
    return pd.DataFrame({
        "original": original_pred,
        "perturbed": perturbed_pred,
        "change": perturbed_pred - original_pred,
        "pct_change": (perturbed_pred - original_pred) / original_pred
    })
```

### 7.2 Sanity Checks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SANITY CHECKS                                        │
└─────────────────────────────────────────────────────────────────────────────┘

  Check                          Status    Notes
  ─────────────────────────────────────────────────────────────
  Feature signs match intuition    ✅      Momentum positive
  No single feature dominates      ⚠️      return_3m = 40%
  Predictions reasonable range     ✅      -15% to +20%
  SHAP values sum to predictions   ✅      Verified
  Top stocks have clear drivers    ✅      Explainable
```

```python
def run_sanity_checks(
    model: LGBMRegressor,
    shap_values: np.ndarray,
    X: pd.DataFrame,
    feature_names: List[str]
) -> Dict[str, Any]:
    """Run sanity checks on model explanations."""
    
    checks = {}
    
    # Check SHAP values sum to predictions
    predictions = model.predict(X)
    explainer = shap.TreeExplainer(model)
    shap_sum = shap_values.sum(axis=1) + explainer.expected_value
    checks["shap_sums_match"] = np.allclose(predictions, shap_sum)
    
    # Check for feature dominance
    importance = np.abs(shap_values).mean(axis=0)
    importance_pct = importance / importance.sum()
    checks["max_feature_pct"] = importance_pct.max()
    checks["dominant_feature"] = feature_names[importance_pct.argmax()]
    
    # Check prediction range
    checks["pred_range"] = (predictions.min(), predictions.max())
    checks["reasonable_range"] = predictions.min() > -0.5 and predictions.max() < 0.5
    
    return checks
```

---

## 8. Output Formats

### 8.1 Score-Latest Output with Explanations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STOCK SCORES WITH EXPLANATIONS                            │
└─────────────────────────────────────────────────────────────────────────────┘

Date: 2024-01-15

Rank  Ticker  Score   Top Positive Factors           Top Negative Factors
────────────────────────────────────────────────────────────────────────────
  1   NVDA    0.12    momentum (+0.06), vol (+0.02)  valuation (-0.01)
  2   AMD     0.09    momentum (+0.04), growth (+0.02)  pe (-0.005)
  3   AAPL    0.07    value (+0.04), quality (+0.02)   momentum (-0.01)
  4   MSFT    0.06    stability (+0.03), value (+0.02) momentum (-0.005)
  5   GOOGL   0.05    growth (+0.03), quality (+0.02)  vol (-0.01)
```

### 8.2 JSON Output

```json
{
  "date": "2024-01-15",
  "stocks": [
    {
      "ticker": "NVDA",
      "score": 0.12,
      "rank": 1,
      "contributions": {
        "return_3m": 0.06,
        "vol_20d": 0.02,
        "pe_ratio": -0.01,
        "return_12m": 0.02,
        "dollar_volume": 0.01
      },
      "top_drivers": ["3-month momentum", "moderate volatility"],
      "concerns": ["high valuation"]
    }
  ]
}
```

---

## 9. Usage Examples

### 9.1 Global Importance

```python
from src.explain.shap_explain import compute_shap_values, summarize_feature_importance

# Compute SHAP
shap_values, explainer = compute_shap_values(model, X_train)

# Get feature importance
importance = summarize_feature_importance(shap_values, feature_names)
print("Top Features:")
print(importance.head(10))
```

### 9.2 Explain Single Stock

```python
from src.explain.shap_explain import explain_stock

# Get explanation for NVDA
nvda_row = X_inference[X_inference.index == "NVDA"]
explanation = explain_stock(model, nvda_row, feature_names)

print(f"Prediction: {explanation['prediction']:.4f}")
print("\nTop positive contributors:")
for feat, val in explanation["top_positive"]:
    print(f"  {feat}: +{val:.4f}")
```

### 9.3 Portfolio Analysis

```python
from src.explain.shap_explain import compute_portfolio_shap

# Analyze portfolio
portfolio_analysis = compute_portfolio_shap(
    model,
    X_portfolio,
    weights,
    feature_names,
    factor_mapping=FACTOR_MAPPING
)

print("Portfolio Factor Exposure:")
for factor, exposure in portfolio_analysis["factor_exposure"].items():
    print(f"  {factor}: {exposure:.4f}")

if portfolio_analysis["concentration_warning"]:
    print("\n⚠️ Warnings:")
    for warning in portfolio_analysis["concentration_warning"]:
        print(f"  {warning}")
```

---

## Related Documents

- **Previous**: [model-training.md](model-training.md) - Model that we explain
- **Visualization**: [visualization-analytics.md](visualization-analytics.md) - SHAP plots
- **Risk Analysis**: [risk-management.md](risk-management.md) - Portfolio risk
- **Back to**: [design.md](design.md) - Main overview
