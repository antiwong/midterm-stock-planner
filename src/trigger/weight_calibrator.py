"""Monthly recalibration of composite score source weights using feedback data.

Replaces static weights (0.28, 0.18, 0.10 ...) with empirically-derived values
that maximize directional accuracy on the labeled feedback dataset.

Run monthly via run_feedback.py --force-recal, or manually:
  python -m src.trigger.weight_calibrator

Reads from: data/sentiment/feedback/feedback_*.csv (labeled dataset)
Writes to:  data/sentiment/source_weights_5d.json (consumed by composite.py)
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
from scipy.optimize import minimize

logger = logging.getLogger(__name__)

SOURCE_WEIGHT_COLS = [
    'llm_score', 'finnhub_score', 'finnhub_social_score',
    'av_score', 'massive_score', 'eodhd_score',
    'marketaux_score', 'stocktwits_bullish_pct',
    'fmp_social_score',
]

DEFAULT_WEIGHTS = np.array([0.28, 0.18, 0.05, 0.10, 0.10, 0.09, 0.10, 0.05, 0.05])

SENTIMENT_DIR = Path(__file__).parent.parent.parent / "data" / "sentiment"
FEEDBACK_DIR = SENTIMENT_DIR / "feedback"


def load_feedback_data() -> pd.DataFrame:
    """Load all feedback CSVs and merge with feature CSVs."""
    feedback_files = sorted(FEEDBACK_DIR.glob("feedback_*.csv"))
    feature_files = sorted(SENTIMENT_DIR.glob("sentimentpulse_*.csv"))

    if not feedback_files or not feature_files:
        return pd.DataFrame()

    feedback_df = pd.concat(
        [pd.read_csv(f) for f in feedback_files], ignore_index=True
    )
    features_df = pd.concat(
        [pd.read_csv(f, low_memory=False) for f in feature_files], ignore_index=True
    )

    # Join on run_id + ticker + date (safe join — no look-ahead)
    labeled = features_df.merge(
        feedback_df[['run_id', 'ticker', 'date',
                      'actual_return_5d', 'actual_return_10d', 'actual_return_20d',
                      'signal_correct_5d', 'signal_correct_10d', 'signal_correct_20d']],
        on=['run_id', 'ticker', 'date'],
        how='inner',
    )
    return labeled


def recalibrate_weights(feedback_df: pd.DataFrame,
                         horizon: int = 5) -> Dict[str, float]:
    """Fit source weights to maximize trigger performance.

    SP-1.1: When trigger_alpha_{horizon}d is available as the target column
    (actual_return overridden with trigger_alpha by run_feedback.py), this
    optimizes for ENTRY TIMING improvement over the ranker baseline.
    When trigger_alpha is not yet available, falls back to directional accuracy.

    Args:
        feedback_df: Labeled dataset with SOURCE_WEIGHT_COLS + actual_return_{horizon}d.
                     If actual_return has been overridden with trigger_alpha, the
                     optimization target is timing improvement, not raw direction.
        horizon: 5, 10, or 20 trading days

    Returns:
        Dict of source name -> optimized weight
    """
    target_col = f'actual_return_{horizon}d'
    df = feedback_df.dropna(subset=[c for c in SOURCE_WEIGHT_COLS if c in feedback_df.columns] + [target_col]).copy()

    if len(df) < 30:
        logger.warning("Insufficient labeled data for recalibration: %d rows (need 30)", len(df))
        return dict(zip(SOURCE_WEIGHT_COLS, (DEFAULT_WEIGHTS / DEFAULT_WEIGHTS.sum()).tolist()))

    # Build feature matrix — fill missing sources with 0
    available_cols = [c for c in SOURCE_WEIGHT_COLS if c in df.columns]
    X = df[available_cols].fillna(0.0).values

    # Normalize stocktwits from [0,1] to [-1,+1]
    st_idx = available_cols.index('stocktwits_bullish_pct') if 'stocktwits_bullish_pct' in available_cols else None
    if st_idx is not None:
        X[:, st_idx] = (X[:, st_idx] - 0.5) * 2.0

    y = np.sign(df[target_col].values)

    n_cols = len(available_cols)

    def neg_directional_accuracy(weights):
        weights = np.abs(weights)
        weights = weights / (weights.sum() + 1e-8)
        pred_score = X @ weights
        pred_direction = np.sign(pred_score)
        accuracy = np.mean(pred_direction == y)
        return -accuracy

    # Initial weights (current values, matching available columns)
    w0 = np.array([
        DEFAULT_WEIGHTS[SOURCE_WEIGHT_COLS.index(c)] if c in SOURCE_WEIGHT_COLS else 1.0 / n_cols
        for c in available_cols
    ])
    w0 = w0 / w0.sum()

    result = minimize(
        neg_directional_accuracy, w0,
        method='SLSQP',
        bounds=[(0.02, 0.50)] * n_cols,
        constraints={'type': 'eq', 'fun': lambda w: np.abs(w).sum() - 1.0},
    )

    optimized = np.abs(result.x)
    optimized = optimized / optimized.sum()

    accuracy_before = -neg_directional_accuracy(w0)
    accuracy_after = -neg_directional_accuracy(optimized)

    logger.info("Recalibration @%dd: accuracy %.1f%% -> %.1f%% (%d samples)",
                horizon, accuracy_before * 100, accuracy_after * 100, len(df))

    # Build full weight dict (zeros for missing sources)
    weights = {}
    for i, col in enumerate(available_cols):
        weights[col] = round(float(optimized[i]), 4)
    for col in SOURCE_WEIGHT_COLS:
        if col not in weights:
            weights[col] = 0.0

    return weights


def save_weights(weights: Dict[str, float], horizon: int = 5):
    """Save recalibrated weights to JSON."""
    output_path = SENTIMENT_DIR / f"source_weights_{horizon}d.json"
    data = {
        'recalibrated_at': date.today().isoformat(),
        'horizon': horizon,
        'weights': weights,
    }
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info("Saved weights to %s", output_path)

    # Also save to weight history log
    history_path = SENTIMENT_DIR / "weight_history.csv"
    record = {'date': date.today().isoformat(), 'horizon': horizon}
    record.update(weights)
    history_df = pd.DataFrame([record])
    if history_path.exists():
        existing = pd.read_csv(history_path)
        history_df = pd.concat([existing, history_df], ignore_index=True)
    history_df.to_csv(history_path, index=False)


def run_recalibration():
    """Full recalibration pipeline."""
    logger.info("Starting weight recalibration")
    df = load_feedback_data()

    if df.empty:
        logger.warning("No labeled data available for recalibration")
        return

    for horizon in [5, 10, 20]:
        target = f'actual_return_{horizon}d'
        if target not in df.columns or df[target].notna().sum() < 30:
            logger.info("Skipping %dd horizon — insufficient data", horizon)
            continue

        weights = recalibrate_weights(df, horizon=horizon)
        save_weights(weights, horizon=horizon)
        logger.info("Weights @%dd: %s", horizon, weights)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s — %(message)s')
    run_recalibration()
