# Model Training & Prediction

> [← Back to Documentation Index](README.md)
> **Part of**: [Mid-term Stock Planner Design](design.md)
> 
> This document covers model training, prediction, and persistence.

## Related Documents

- [design.md](design.md) - Main overview and architecture
- [data-engineering.md](data-engineering.md) - Creates the training datasets
- [backtesting.md](backtesting.md) - Uses trained models for evaluation
- [explainability.md](explainability.md) - SHAP analysis of trained models

---

## 1. Training Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MODEL TRAINING PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐
│  Training Dataset   │  ← From data-engineering.md
│  (features + target)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           train_lgbm_regressor()                             │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Train/Validation Split                        │    │
│  │   ┌──────────────────────────────┬──────────────────────────────┐   │    │
│  │   │         TRAIN SET            │       VALIDATION SET         │   │    │
│  │   │          (80%)               │           (20%)              │   │    │
│  │   └──────────────────────────────┴──────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         LightGBM Training                            │    │
│  │   ┌─────────────────┐                                                │    │
│  │   │  Hyperparameters│   n_estimators, learning_rate, num_leaves,    │    │
│  │   │  (from config)  │   max_depth, reg_alpha, reg_lambda            │    │
│  │   └─────────────────┘                                                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Validation Metrics                              │    │
│  │   • MSE, RMSE, MAE                                                   │    │
│  │   • Rank correlation (Spearman)                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │   Return:           │
                           │   • model           │
                           │   • metrics         │
                           │   • metadata        │
                           └─────────────────────┘
```

---

## 2. Model Configuration

### 2.1 ModelConfig Dataclass

```python
@dataclass
class ModelConfig:
    """Configuration for model training."""
    
    # Target
    target_col: str = "target"
    
    # Train/test split
    test_size: float = 0.2
    random_state: int = 42
    
    # LightGBM hyperparameters
    params: Dict[str, Any] = field(default_factory=lambda: {
        "n_estimators": 200,
        "learning_rate": 0.03,
        "num_leaves": 15,
        "max_depth": 6,
        "min_child_samples": 50,
        "reg_alpha": 0.3,
        "reg_lambda": 0.5,
        "subsample": 0.7,
        "colsample_bytree": 0.7,
        "early_stopping_rounds": 30,
        "random_state": 42,
        "n_jobs": -1,
        "verbose": -1
    })
```

### 2.2 Hyperparameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `n_estimators` | 200 | Number of boosting rounds |
| `learning_rate` | 0.03 | Step size shrinkage |
| `num_leaves` | 15 | Max leaves per tree |
| `max_depth` | 6 | Max tree depth (-1 = no limit) |
| `min_child_samples` | 50 | Min samples in leaf |
| `reg_alpha` | 0.3 | L1 regularization |
| `reg_lambda` | 0.5 | L2 regularization |
| `subsample` | 0.7 | Row subsampling ratio |
| `colsample_bytree` | 0.7 | Feature subsampling ratio |
| `early_stopping_rounds` | 30 | Stop training if validation metric does not improve for this many rounds |

---

## 3. Training Function

### 3.1 API

```python
# src/models/trainer.py

def train_lgbm_regressor(
    data: pd.DataFrame,
    feature_cols: List[str],
    config: Optional[ModelConfig] = None
) -> Tuple[LGBMRegressor, pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    """
    Train a LightGBM regression model.
    
    Args:
        data: Training DataFrame with features and target
        feature_cols: List of feature column names
        config: Model configuration (uses defaults if None)
    
    Returns:
        Tuple of:
        - model: Trained LGBMRegressor
        - X_train: Training features
        - X_valid: Validation features  
        - metrics: Dictionary of validation metrics
    """
```

### 3.2 Training Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRAINING FLOW                                        │
└─────────────────────────────────────────────────────────────────────────────┘

1. PREPARE DATA
   ┌─────────────────┐
   │ Extract X, y    │
   │ from DataFrame  │
   └────────┬────────┘
            │
            ▼
2. SPLIT DATA
   ┌──────────────────────────────────────────────────────────┐
   │ Train (80%)                    │ Validation (20%)        │
   └──────────────────────────────────────────────────────────┘
            │
            ▼
3. TRAIN MODEL
   ┌─────────────────┐
   │ LGBMRegressor   │
   │ .fit(X_train,   │
   │      y_train)   │
   └────────┬────────┘
            │
            ▼
4. EVALUATE
   ┌─────────────────┐
   │ Compute metrics │
   │ on validation   │
   └────────┬────────┘
            │
            ▼
5. RETURN
   ┌─────────────────┐
   │ (model, X_train,│
   │  X_valid,       │
   │  metrics)       │
   └─────────────────┘
```

### 3.3 Validation Metrics

| Metric | Description |
|--------|-------------|
| `mse` | Mean Squared Error |
| `rmse` | Root Mean Squared Error |
| `mae` | Mean Absolute Error |
| `r2` | R-squared score |
| `spearman_corr` | Rank correlation (for ranking quality) |

---

## 4. Prediction Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PREDICTION FLOW                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐      ┌─────────────────┐
│  Model File     │      │  Inference Data │
│  (model.txt)    │      │  (features only)│
└────────┬────────┘      └────────┬────────┘
         │                        │
         ▼                        │
┌─────────────────┐               │
│  load_model()   │               │
│  + metadata     │               │
└────────┬────────┘               │
         │                        │
         └────────────┬───────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │     predict()       │
           │  ┌───────────────┐  │
           │  │ Validate      │  │
           │  │ feature cols  │  │
           │  └───────────────┘  │
           │          │          │
           │          ▼          │
           │  ┌───────────────┐  │
           │  │ model.predict │  │
           │  │ (X_features)  │  │
           │  └───────────────┘  │
           │          │          │
           │          ▼          │
           │  ┌───────────────┐  │
           │  │ Cross-section │  │
           │  │ ranking       │  │
           │  └───────────────┘  │
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │  Output DataFrame   │
           │  ┌───────────────┐  │
           │  │ date          │  │
           │  │ ticker        │  │
           │  │ score         │  │
           │  │ rank          │  │
           │  │ percentile    │  │
           │  └───────────────┘  │
           └─────────────────────┘
```

### 4.1 Predictor API

```python
# src/models/predictor.py

def load_model(path: Path) -> Tuple[LGBMRegressor, ModelMetadata]:
    """
    Load a trained model and its metadata.
    
    Args:
        path: Path to model directory
    
    Returns:
        Tuple of (model, metadata)
    """

def predict(
    model: LGBMRegressor,
    feature_df: pd.DataFrame,
    feature_names: List[str],
    metadata: Optional[ModelMetadata] = None,
    include_rankings: bool = True
) -> pd.DataFrame:
    """
    Generate predictions and rankings.
    
    Args:
        model: Trained model
        feature_df: DataFrame with features
        feature_names: List of feature column names
        metadata: Optional model metadata for validation
        include_rankings: Whether to compute cross-sectional ranks
    
    Returns:
        DataFrame with columns: date, ticker, score, rank, percentile
    """
```

### 4.2 Feature Validation

```python
# Warn if features don't match training
if metadata and set(feature_names) != set(metadata.feature_names):
    missing = set(metadata.feature_names) - set(feature_names)
    extra = set(feature_names) - set(metadata.feature_names)
    warnings.warn(f"Feature mismatch! Missing: {missing}, Extra: {extra}")
```

### 4.3 Output Schema

| Column | Type | Description |
|--------|------|-------------|
| `date` | datetime | Prediction date |
| `ticker` | str | Stock symbol |
| `score` | float | Predicted excess return |
| `rank` | int | Cross-sectional rank (1 = best) |
| `percentile` | float | Percentile rank (0-100) |

---

## 5. Model Persistence

### 5.1 Directory Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MODEL PERSISTENCE STRUCTURE                            │
└─────────────────────────────────────────────────────────────────────────────┘

models/
│
├── model_20240101_v1/
│   ├── model.txt            ◄── Native LightGBM model
│   └── metadata.json        ◄── Feature names, hyperparams, metrics
│
├── model_20240201_v1/
│   ├── model.txt
│   └── metadata.json
│
└── model_20240301_v2/        ◄── New version with updated features
    ├── model.txt
    └── metadata.json
```

### 5.2 Metadata Schema

```json
{
  "model_id": "model_20240101_v1",
  "created_at": "2024-01-01T10:30:00",
  "feature_names": ["return_1m", "return_3m", "vol_20d", "..."],
  "target_col": "target",
  "hyperparameters": {
    "n_estimators": 200,
    "learning_rate": 0.03,
    "num_leaves": 15,
    "max_depth": 6,
    "early_stopping_rounds": 30
  },
  "training_period": {
    "start": "2019-01-01",
    "end": "2023-12-31"
  },
  "validation_metrics": {
    "rmse": 0.0425,
    "mae": 0.0312,
    "r2": 0.15,
    "spearman_corr": 0.12
  },
  "n_samples": 50000,
  "n_features": 15
}
```

### 5.3 Save/Load Functions

```python
def save_model(
    model: LGBMRegressor,
    feature_cols: List[str],
    config: ModelConfig,
    metrics: Dict[str, float],
    path: Path
) -> None:
    """
    Save model and metadata to disk.
    
    Creates:
    - {path}/model.txt - LightGBM model file
    - {path}/metadata.json - Training metadata
    """

def load_model(path: Path) -> Tuple[LGBMRegressor, ModelMetadata]:
    """
    Load model and metadata from disk.
    
    Args:
        path: Directory containing model.txt and metadata.json
    
    Returns:
        Tuple of (model, metadata)
    """
```

---

## 6. Cross-Sectional Ranking

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CROSS-SECTIONAL RANKING                                   │
└─────────────────────────────────────────────────────────────────────────────┘

For each date T:

  Raw Predictions (score)          Ranked (rank)           Percentile
  ┌─────────┬────────┐           ┌─────────┬────┐        ┌─────────┬─────┐
  │ NVDA    │  0.12  │           │ NVDA    │  1 │        │ NVDA    │  99 │
  │ AMD     │  0.09  │    ──▶    │ AMD     │  2 │   ──▶  │ AMD     │  80 │
  │ AAPL    │  0.07  │           │ AAPL    │  3 │        │ AAPL    │  60 │
  │ MSFT    │  0.05  │           │ MSFT    │  4 │        │ MSFT    │  40 │
  │ INTC    │  0.02  │           │ INTC    │  5 │        │ INTC    │  20 │
  └─────────┴────────┘           └─────────┴────┘        └─────────┴─────┘
  
  Higher score = Better expected excess return
  Lower rank = Better (1 is best)
  Higher percentile = Better (99 is best)
```

### 6.1 Ranking Logic

```python
# Group by date and rank
result_df["rank"] = result_df.groupby("date")["score"].rank(
    ascending=False, 
    method="dense"
).astype(int)

# Compute percentile
result_df["percentile"] = result_df.groupby("date")["score"].rank(
    pct=True
) * 100
```

---

## 7. Model Selection

### 7.1 MVP Approach

- Static hyperparameters from config
- Single train/validation split
- Use validation metrics to monitor overfitting

### 7.2 Future: Walk-Forward Optimization

> See [backtesting.md](backtesting.md) for walk-forward framework

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HYPERPARAMETER TUNING (FUTURE)                            │
└─────────────────────────────────────────────────────────────────────────────┘

Per walk-forward window:

  Training Window
  ┌──────────────────────────────────────────────────────────┐
  │                                                          │
  │  ┌────────────────────────────┬────────────────────┐    │
  │  │      Cross-Val Train       │   Cross-Val Valid  │    │
  │  └────────────────────────────┴────────────────────┘    │
  │                                                          │
  │  Try multiple hyperparameter sets                        │
  │  Select best based on CV performance                     │
  │                                                          │
  └──────────────────────────────────────────────────────────┘
  
  Then retrain on full training window with best hyperparams
```

---

## 8. Usage Examples

### 8.1 Training a Model

```python
from src.models.trainer import train_lgbm_regressor, ModelConfig, save_model
from src.features.engineering import compute_all_features, make_training_dataset

# Prepare data
feature_df = compute_all_features(price_df, fundamental_df, config)
training_df = make_training_dataset(feature_df, benchmark_df)

# Define features
feature_cols = [
    "return_1m", "return_3m", "return_6m", "return_12m",
    "vol_20d", "vol_60d", "pe_ratio", "pb_ratio"
]

# Train
model, X_train, X_valid, metrics = train_lgbm_regressor(
    training_df, 
    feature_cols
)

# Save
save_model(model, feature_cols, config, metrics, Path("models/v1"))
```

### 8.2 Making Predictions

```python
from src.models.predictor import load_model, predict

# Load model
model, metadata = load_model(Path("models/v1"))

# Prepare inference data
inference_df = prepare_inference_data(data_config, feature_config, "2024-01-15")

# Predict
results = predict(
    model, 
    inference_df, 
    feature_names=metadata.feature_names
)

# Top 10 stocks
print(results.nsmallest(10, "rank"))
```

---

## Related Documents

- **Previous**: [data-engineering.md](data-engineering.md) - Data preparation
- **Next**: [backtesting.md](backtesting.md) - Model evaluation
- **Explainability**: [explainability.md](explainability.md) - SHAP analysis
- **Back to**: [design.md](design.md) - Main overview
