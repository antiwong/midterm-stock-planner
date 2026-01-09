"""SHAP explainability module for mid-term stock planner.

This module provides functions to compute SHAP values and generate
human-readable explanations for model predictions.

Features:
- Global and local SHAP explanations
- Feature grouping by category (Return, Volatility, Sentiment, etc.)
- Portfolio-level SHAP aggregation
- Sentiment factor contribution analysis
"""

import numpy as np
import pandas as pd
import shap
from typing import Dict, List, Optional, Tuple, Union
from lightgbm import LGBMRegressor


# Feature group definitions for categorizing features
FEATURE_GROUPS = {
    "Return": ["return_1m", "return_3m", "return_6m", "return_12m"],
    "Volatility": ["vol_20d", "vol_60d", "atr", "bb_width"],
    "Volume": ["dollar_volume", "volume_ratio", "turnover", "obv"],
    "Valuation": ["pe_ratio", "pb_ratio", "earnings_yield", "ps_ratio"],
    "Momentum": ["momentum_score", "rel_strength", "high_52w_dist", "rsi"],
    "Mean_Reversion": ["zscore", "ma_distance", "bb_pct_b"],
    "Technical": ["macd", "macd_signal", "adx", "ema"],
    "Sentiment": ["sentiment_mean", "sentiment_std", "sentiment_count", "sentiment_trend"],
}


def get_feature_group(feature_name: str) -> str:
    """
    Get the category/group for a feature name.
    
    Args:
        feature_name: Name of the feature.
    
    Returns:
        Group name (e.g., "Sentiment", "Return", "Volatility").
    """
    feature_lower = feature_name.lower()
    
    # Check for sentiment features
    if feature_lower.startswith("sentiment_"):
        return "Sentiment"
    
    # Check for return features
    if "return" in feature_lower:
        return "Return"
    
    # Check for volatility features
    if any(v in feature_lower for v in ["vol", "atr", "bb_width", "volatility"]):
        return "Volatility"
    
    # Check for volume features
    if any(v in feature_lower for v in ["volume", "turnover", "obv", "dollar_vol"]):
        return "Volume"
    
    # Check for valuation features
    if any(v in feature_lower for v in ["pe_", "pb_", "earnings", "ps_", "valuation"]):
        return "Valuation"
    
    # Check for momentum features
    if any(v in feature_lower for v in ["momentum", "rel_strength", "rsi", "52w"]):
        return "Momentum"
    
    # Check for mean reversion features
    if any(v in feature_lower for v in ["zscore", "ma_dist", "bb_pct", "reversion"]):
        return "Mean_Reversion"
    
    # Check for technical features
    if any(v in feature_lower for v in ["macd", "adx", "ema", "sma", "technical"]):
        return "Technical"
    
    return "Other"


def group_features(feature_names: List[str]) -> Dict[str, List[str]]:
    """
    Group features by category.
    
    Args:
        feature_names: List of feature names.
    
    Returns:
        Dictionary mapping group names to lists of feature names.
    """
    groups = {}
    for feat in feature_names:
        group = get_feature_group(feat)
        if group not in groups:
            groups[group] = []
        groups[group].append(feat)
    return groups


def compute_shap_values(
    model: LGBMRegressor,
    X: pd.DataFrame
) -> Tuple[np.ndarray, shap.TreeExplainer]:
    """
    Compute SHAP values for predictions.
    
    Args:
        model: Trained LightGBM model.
        X: Feature DataFrame for which to compute SHAP values.
    
    Returns:
        Tuple of (shap_values array, explainer object)
    """
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    return shap_values, explainer


def summarize_feature_importance(
    shap_values: np.ndarray,
    X: pd.DataFrame
) -> pd.Series:
    """
    Summarize global feature importance from SHAP values.
    
    Args:
        shap_values: SHAP values array from compute_shap_values.
        X: Feature DataFrame (used for column names).
    
    Returns:
        Series of feature importances sorted by importance (descending).
    """
    abs_vals = np.abs(shap_values)
    mean_abs = abs_vals.mean(axis=0)
    importance = pd.Series(mean_abs, index=X.columns).sort_values(ascending=False)
    return importance


def explain_single_prediction(
    shap_values: np.ndarray,
    X: pd.DataFrame,
    idx: int,
    top_n: int = 5
) -> Dict[str, float]:
    """
    Explain a single prediction.
    
    Args:
        shap_values: SHAP values array.
        X: Feature DataFrame.
        idx: Index of the prediction to explain.
        top_n: Number of top features to return.
    
    Returns:
        Dictionary of {feature_name: shap_contribution}
    """
    row_shap = shap_values[idx]
    feature_contrib = pd.Series(row_shap, index=X.columns)
    
    # Get top positive and negative contributors
    top_positive = feature_contrib.nlargest(top_n)
    top_negative = feature_contrib.nsmallest(top_n)
    
    return {
        'top_positive': top_positive.to_dict(),
        'top_negative': top_negative.to_dict(),
        'all': feature_contrib.to_dict(),
    }


def explain_stock(
    model: LGBMRegressor,
    feature_df: pd.DataFrame,
    feature_names: List[str],
    ticker: str,
    date: Optional[str] = None,
    top_n: int = 5
) -> Dict:
    """
    Generate explanation for a specific stock.
    
    Args:
        model: Trained model.
        feature_df: DataFrame with features.
        feature_names: List of feature column names.
        ticker: Stock ticker to explain.
        date: Optional date to filter to. If None, uses latest.
        top_n: Number of top features to include.
    
    Returns:
        Dictionary with explanation data.
    """
    df = feature_df.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    # Filter to ticker
    df = df[df['ticker'] == ticker]
    
    if len(df) == 0:
        raise ValueError(f"No data found for ticker: {ticker}")
    
    # Filter to date
    if date is not None:
        date = pd.to_datetime(date)
        df = df[df['date'] == date]
    else:
        df = df[df['date'] == df['date'].max()]
    
    if len(df) == 0:
        raise ValueError(f"No data found for ticker {ticker} on specified date")
    
    # Get features
    X = df[feature_names].fillna(0)
    
    # Compute SHAP values
    shap_values, _ = compute_shap_values(model, X)
    
    # Get prediction
    prediction = model.predict(X)[0]
    
    # Get explanation
    explanation = explain_single_prediction(shap_values, X, 0, top_n)
    
    return {
        'ticker': ticker,
        'date': df['date'].iloc[0],
        'prediction': float(prediction),
        'top_positive_factors': explanation['top_positive'],
        'top_negative_factors': explanation['top_negative'],
    }


def generate_explanation_text(
    explanation: Dict,
    format: str = "text"
) -> str:
    """
    Generate human-readable explanation text.
    
    Args:
        explanation: Explanation dictionary from explain_stock.
        format: Output format ("text" or "markdown").
    
    Returns:
        Formatted explanation string.
    """
    ticker = explanation['ticker']
    date = explanation['date']
    prediction = explanation['prediction']
    positive = explanation['top_positive_factors']
    negative = explanation['top_negative_factors']
    
    if format == "markdown":
        lines = [
            f"## {ticker} Explanation ({date.date()})",
            f"",
            f"**Predicted Score:** {prediction:.4f}",
            f"",
            f"### Factors Increasing Score:",
        ]
        for feat, val in positive.items():
            group = get_feature_group(feat)
            lines.append(f"- {feat} [{group}]: +{val:.4f}")
        
        lines.append(f"")
        lines.append(f"### Factors Decreasing Score:")
        for feat, val in negative.items():
            group = get_feature_group(feat)
            lines.append(f"- {feat} [{group}]: {val:.4f}")
        
        return "\n".join(lines)
    
    else:  # text format
        lines = [
            f"{ticker} Explanation ({date.date()})",
            f"=" * 40,
            f"Predicted Score: {prediction:.4f}",
            f"",
            f"Factors Increasing Score:",
        ]
        for feat, val in positive.items():
            group = get_feature_group(feat)
            lines.append(f"  {feat} [{group}]: +{val:.4f}")
        
        lines.append(f"")
        lines.append(f"Factors Decreasing Score:")
        for feat, val in negative.items():
            group = get_feature_group(feat)
            lines.append(f"  {feat} [{group}]: {val:.4f}")
        
        return "\n".join(lines)


def summarize_importance_by_group(
    shap_values: np.ndarray,
    X: pd.DataFrame,
) -> pd.DataFrame:
    """
    Summarize feature importance by group.
    
    Args:
        shap_values: SHAP values array.
        X: Feature DataFrame.
    
    Returns:
        DataFrame with group-level importance.
    """
    # Get per-feature importance
    feature_importance = summarize_feature_importance(shap_values, X)
    
    # Group features
    feature_groups = group_features(X.columns.tolist())
    
    # Aggregate by group
    group_importance = {}
    for group, features in feature_groups.items():
        group_features_in_df = [f for f in features if f in feature_importance.index]
        if group_features_in_df:
            group_importance[group] = feature_importance[group_features_in_df].sum()
        else:
            group_importance[group] = 0.0
    
    return pd.Series(group_importance).sort_values(ascending=False)


def compute_portfolio_shap(
    model: LGBMRegressor,
    portfolio_features: pd.DataFrame,
    weights: pd.Series,
    feature_names: List[str],
) -> Dict:
    """
    Compute portfolio-level SHAP aggregation.
    
    Aggregates SHAP values across all holdings weighted by portfolio weights
    to understand what factors drive the overall portfolio.
    
    Args:
        model: Trained LightGBM model.
        portfolio_features: DataFrame with features for portfolio stocks.
                           Index should be tickers.
        weights: Series of portfolio weights. Index should be tickers.
        feature_names: List of feature column names.
    
    Returns:
        Dictionary with:
        - stock_shap: Per-stock SHAP values
        - weighted_shap: Weight-adjusted SHAP per feature
        - group_shap: SHAP aggregated by feature group
        - sentiment_contribution: Total sentiment factor contribution
        - dominant_factor: Most influential factor group
    """
    X = portfolio_features[feature_names].fillna(0)
    
    # Compute SHAP for all portfolio stocks
    shap_values, explainer = compute_shap_values(model, X)
    
    # Create DataFrame of SHAP values
    shap_df = pd.DataFrame(
        shap_values,
        index=portfolio_features.index,
        columns=feature_names
    )
    
    # Compute weighted SHAP (multiply each row by weight)
    aligned_weights = weights.reindex(shap_df.index).fillna(0)
    weighted_shap = shap_df.multiply(aligned_weights, axis=0)
    
    # Sum weighted SHAP per feature
    total_weighted_shap = weighted_shap.sum()
    
    # Group by feature category
    group_shap = {}
    feature_groups = group_features(feature_names)
    for group, features in feature_groups.items():
        group_features_in_df = [f for f in features if f in total_weighted_shap.index]
        if group_features_in_df:
            group_shap[group] = total_weighted_shap[group_features_in_df].sum()
    
    # Find dominant factor
    dominant_factor = max(group_shap.items(), key=lambda x: abs(x[1]))[0] if group_shap else None
    
    # Sentiment contribution
    sentiment_contribution = group_shap.get("Sentiment", 0.0)
    
    return {
        "stock_shap": shap_df.to_dict(),
        "weighted_shap": total_weighted_shap.to_dict(),
        "group_shap": group_shap,
        "sentiment_contribution": sentiment_contribution,
        "dominant_factor": dominant_factor,
        "base_value": float(explainer.expected_value),
    }


def analyze_sentiment_impact(
    model: LGBMRegressor,
    X: pd.DataFrame,
    feature_names: List[str],
) -> Dict:
    """
    Analyze the impact of sentiment features on predictions.
    
    Args:
        model: Trained model.
        X: Feature DataFrame.
        feature_names: List of feature column names.
    
    Returns:
        Dictionary with sentiment impact analysis.
    """
    # Compute SHAP values
    shap_values, _ = compute_shap_values(model, X[feature_names].fillna(0))
    
    # Create SHAP DataFrame
    shap_df = pd.DataFrame(shap_values, columns=feature_names)
    
    # Identify sentiment features
    sentiment_features = [f for f in feature_names if get_feature_group(f) == "Sentiment"]
    non_sentiment_features = [f for f in feature_names if get_feature_group(f) != "Sentiment"]
    
    if not sentiment_features:
        return {
            "sentiment_features": [],
            "sentiment_importance": 0.0,
            "sentiment_pct_of_total": 0.0,
            "top_sentiment_feature": None,
        }
    
    # Compute importance
    sentiment_importance = np.abs(shap_df[sentiment_features]).mean().sum()
    total_importance = np.abs(shap_df).mean().sum()
    
    # Top sentiment feature
    sentiment_feature_importance = np.abs(shap_df[sentiment_features]).mean()
    top_sentiment_feature = sentiment_feature_importance.idxmax()
    
    return {
        "sentiment_features": sentiment_features,
        "sentiment_importance": float(sentiment_importance),
        "sentiment_pct_of_total": float(sentiment_importance / total_importance * 100) if total_importance > 0 else 0.0,
        "non_sentiment_importance": float(total_importance - sentiment_importance),
        "top_sentiment_feature": top_sentiment_feature,
        "top_sentiment_importance": float(sentiment_feature_importance[top_sentiment_feature]),
        "per_feature_importance": sentiment_feature_importance.to_dict(),
    }
