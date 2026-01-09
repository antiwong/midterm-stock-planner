"""Model training module for mid-term stock planner.

This module provides functions to train gradient-boosted tree models
(LightGBM) and manage model persistence with metadata.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import uuid

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
from lightgbm import LGBMRegressor


@dataclass
class ModelConfig:
    """Configuration for model training."""
    target_col: str = "target"
    test_size: float = 0.2
    random_state: int = 42
    params: Dict[str, Any] = field(default_factory=lambda: {
        "n_estimators": 300,
        "learning_rate": 0.05,
        "max_depth": -1,
        "num_leaves": 31,
    })


@dataclass
class ModelMetadata:
    """Metadata for a trained model."""
    model_id: str
    feature_names: List[str]
    target_col: str
    training_date: str
    training_config: Dict[str, Any]
    performance_metrics: Dict[str, float]
    data_info: Dict[str, Any]


def train_lgbm_regressor(
    data: pd.DataFrame,
    feature_cols: List[str],
    config: Optional[ModelConfig] = None,
) -> Tuple[LGBMRegressor, pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    """
    Train a LightGBM regressor model.
    
    Args:
        data: Training data with features and target column.
        feature_cols: List of feature column names.
        config: Model configuration. Uses defaults if None.
    
    Returns:
        Tuple of (trained_model, X_train, X_valid, metrics)
    """
    if config is None:
        config = ModelConfig()
    
    X = data[feature_cols]
    y = data[config.target_col]

    X_train, X_valid, y_train, y_valid = train_test_split(
        X, y, test_size=config.test_size, random_state=config.random_state
    )

    model = LGBMRegressor(**config.params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_valid, y_valid)],
        callbacks=[lambda env: None]  # Suppress verbose output
    )
    
    # Compute validation metrics
    y_pred_valid = model.predict(X_valid)
    metrics = {
        'mse': float(mean_squared_error(y_valid, y_pred_valid)),
        'rmse': float(np.sqrt(mean_squared_error(y_valid, y_pred_valid))),
        'mae': float(mean_absolute_error(y_valid, y_pred_valid)),
        'n_train': len(X_train),
        'n_valid': len(X_valid),
    }

    return model, X_train, X_valid, metrics


def save_model(
    model: LGBMRegressor,
    feature_names: List[str],
    config: ModelConfig,
    metrics: Dict[str, float],
    base_dir: str = "models",
    model_id: Optional[str] = None,
    data_info: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Save a trained model with metadata.
    
    Creates a directory structure:
    models/{model_id}/
        model.txt          # Native LightGBM format
        metadata.json      # Feature names, config, training date, performance
    
    Args:
        model: Trained LightGBM model.
        feature_names: List of feature column names used in training.
        config: Model configuration used for training.
        metrics: Performance metrics from validation.
        base_dir: Base directory for model storage.
        model_id: Optional model ID. If None, generates a UUID.
        data_info: Optional additional data information (date ranges, etc.)
    
    Returns:
        Path to the saved model directory.
    """
    if model_id is None:
        model_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
    
    # Create model directory
    model_dir = Path(base_dir) / model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Save model in native format
    model_path = model_dir / "model.txt"
    model.booster_.save_model(str(model_path))
    
    # Create metadata
    metadata = ModelMetadata(
        model_id=model_id,
        feature_names=feature_names,
        target_col=config.target_col,
        training_date=datetime.now().isoformat(),
        training_config={
            'target_col': config.target_col,
            'test_size': config.test_size,
            'random_state': config.random_state,
            'params': config.params,
        },
        performance_metrics=metrics,
        data_info=data_info or {},
    )
    
    # Save metadata
    metadata_path = model_dir / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(asdict(metadata), f, indent=2)
    
    return str(model_dir)


def load_model(
    model_dir: str,
) -> Tuple[LGBMRegressor, ModelMetadata]:
    """
    Load a trained model with its metadata.
    
    Args:
        model_dir: Path to the model directory.
    
    Returns:
        Tuple of (model, metadata)
    
    Raises:
        FileNotFoundError: If model or metadata files not found.
        ValueError: If metadata is invalid.
    """
    model_path = Path(model_dir)
    
    # Load model
    model_file = model_path / "model.txt"
    if not model_file.exists():
        raise FileNotFoundError(f"Model file not found: {model_file}")
    
    model = LGBMRegressor()
    model._Booster = None
    import lightgbm as lgb
    booster = lgb.Booster(model_file=str(model_file))
    model._Booster = booster
    model._n_features = booster.num_feature()
    model._n_features_in = booster.num_feature()
    model.fitted_ = True
    
    # Load metadata
    metadata_file = model_path / "metadata.json"
    if not metadata_file.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_file}")
    
    with open(metadata_file, 'r') as f:
        metadata_dict = json.load(f)
    
    metadata = ModelMetadata(**metadata_dict)
    
    return model, metadata


def list_models(base_dir: str = "models") -> List[Dict[str, Any]]:
    """
    List all saved models in the base directory.
    
    Args:
        base_dir: Base directory for model storage.
    
    Returns:
        List of model info dictionaries with id, date, and metrics summary.
    """
    base_path = Path(base_dir)
    if not base_path.exists():
        return []
    
    models = []
    for model_dir in base_path.iterdir():
        if model_dir.is_dir():
            metadata_file = model_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                models.append({
                    'model_id': metadata.get('model_id'),
                    'training_date': metadata.get('training_date'),
                    'rmse': metadata.get('performance_metrics', {}).get('rmse'),
                    'path': str(model_dir),
                })
    
    # Sort by training date descending
    models.sort(key=lambda x: x.get('training_date', ''), reverse=True)
    return models
