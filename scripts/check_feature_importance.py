#!/usr/bin/env python3
"""Quick script to train one window and print feature importance (used vs unused)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import prepare_data_from_config
from src.config.config import load_config
from src.models.trainer import train_lgbm_regressor, ModelConfig

def main():
    config = load_config(Path(__file__).parent.parent / "config" / "config.yaml")
    training_df, feature_cols, _, _ = prepare_data_from_config(
        config, for_training=True, override_universe=["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]
    )
    print(f"Features passed to model: {len(feature_cols)}")
    model, X_train, _, metrics = train_lgbm_regressor(
        training_df, feature_cols, ModelConfig()
    )
    imp = model.feature_importances_
    used = [(f, i) for f, i in zip(feature_cols, imp) if i > 0]
    unused = [(f, i) for f, i in zip(feature_cols, imp) if i == 0]
    print(f"\nUsed ({len(used)}):")
    for f, i in sorted(used, key=lambda x: -x[1])[:15]:
        print(f"  {f}: {i}")
    print(f"\nUnused ({len(unused)}): {[f for f, _ in unused]}")

if __name__ == "__main__":
    main()
