"""News data loading and filtering for sentiment analysis.

This module provides functions to:
- Load raw news data from CSV/Parquet files
- Filter news to a specific point in time (crucial for avoiding look-ahead bias)
- Validate news data schema and types
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Union, List
import warnings


# Required columns for news data
REQUIRED_COLUMNS = ["timestamp", "ticker", "headline"]
OPTIONAL_COLUMNS = ["news_id", "body", "source", "url"]


def validate_news_data(df: pd.DataFrame) -> List[str]:
    """
    Validate news DataFrame has required schema.
    
    Args:
        df: News DataFrame to validate.
    
    Returns:
        List of validation warnings (empty if all valid).
    
    Raises:
        ValueError: If required columns are missing.
    """
    warnings_list = []
    
    # Check required columns
    missing_required = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_required:
        raise ValueError(
            f"News data missing required columns: {missing_required}. "
            f"Required: {REQUIRED_COLUMNS}"
        )
    
    # Check for missing optional columns (just warn)
    missing_optional = [col for col in OPTIONAL_COLUMNS if col not in df.columns]
    if missing_optional:
        warnings_list.append(
            f"News data missing optional columns: {missing_optional}"
        )
    
    # Validate timestamp is parseable
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        try:
            pd.to_datetime(df["timestamp"])
        except Exception as e:
            raise ValueError(f"Cannot parse timestamp column: {e}")
    
    # Check for empty headlines
    empty_headlines = df["headline"].isna().sum() + (df["headline"] == "").sum()
    if empty_headlines > 0:
        warnings_list.append(
            f"Found {empty_headlines} empty/null headlines ({empty_headlines/len(df)*100:.1f}%)"
        )
    
    # Check for duplicate news_id if present
    if "news_id" in df.columns:
        n_duplicates = df["news_id"].duplicated().sum()
        if n_duplicates > 0:
            warnings_list.append(f"Found {n_duplicates} duplicate news_id values")
    
    return warnings_list


def load_news_data(
    path: Union[str, Path],
    validate: bool = True,
    parse_dates: bool = True,
    timezone: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load news data from CSV or Parquet file.
    
    Expected columns:
    - timestamp: Publication datetime (timezone-aware if possible)
    - ticker: Stock ticker(s) mentioned
    - headline: Article headline
    - body: Article body (optional)
    - source: News source (optional)
    - news_id: Unique identifier (optional)
    
    Args:
        path: Path to news data file (CSV or Parquet).
        validate: Whether to validate the data schema.
        parse_dates: Whether to parse timestamp column to datetime.
        timezone: Timezone to convert timestamps to (e.g., "US/Eastern").
    
    Returns:
        DataFrame with news data, sorted by timestamp.
    
    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If required columns are missing.
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"News data file not found: {path}")
    
    # Load based on file type
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        df = pd.read_parquet(path)
    elif suffix in [".csv", ".txt"]:
        df = pd.read_csv(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use .csv or .parquet")
    
    # Parse dates if requested
    if parse_dates and "timestamp" in df.columns:
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    
    # Convert timezone if specified
    if timezone is not None and "timestamp" in df.columns:
        if df["timestamp"].dt.tz is None:
            # Assume UTC if no timezone
            df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
        df["timestamp"] = df["timestamp"].dt.tz_convert(timezone)
    
    # Validate if requested
    if validate:
        validation_warnings = validate_news_data(df)
        for warning in validation_warnings:
            warnings.warn(warning)
    
    # Sort by timestamp
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    return df


def filter_news_to_asof(
    news_df: pd.DataFrame,
    as_of: Union[str, pd.Timestamp],
    inclusive: bool = True,
) -> pd.DataFrame:
    """
    Filter news data to only include items published before or at the as_of time.
    
    This is CRITICAL for avoiding look-ahead bias. Only news published
    before the as_of time should be used for features on that date.
    
    Args:
        news_df: News DataFrame with 'timestamp' column.
        as_of: Point-in-time to filter to.
        inclusive: If True, include items at exactly as_of time.
    
    Returns:
        Filtered DataFrame with only past news items.
    """
    df = news_df.copy()
    
    # Ensure timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    # Parse as_of
    as_of = pd.to_datetime(as_of)
    
    # Handle timezone
    if df["timestamp"].dt.tz is not None and as_of.tz is None:
        as_of = as_of.tz_localize(df["timestamp"].dt.tz)
    elif df["timestamp"].dt.tz is None and as_of.tz is not None:
        as_of = as_of.tz_localize(None)
    
    # Filter
    if inclusive:
        mask = df["timestamp"] <= as_of
    else:
        mask = df["timestamp"] < as_of
    
    return df[mask].copy()


def filter_news_by_ticker(
    news_df: pd.DataFrame,
    tickers: Union[str, List[str]],
) -> pd.DataFrame:
    """
    Filter news data to only include items for specified tickers.
    
    Args:
        news_df: News DataFrame with 'ticker' column.
        tickers: Single ticker or list of tickers.
    
    Returns:
        Filtered DataFrame.
    """
    if isinstance(tickers, str):
        tickers = [tickers]
    
    return news_df[news_df["ticker"].isin(tickers)].copy()


def filter_news_by_date_range(
    news_df: pd.DataFrame,
    start_date: Optional[Union[str, pd.Timestamp]] = None,
    end_date: Optional[Union[str, pd.Timestamp]] = None,
) -> pd.DataFrame:
    """
    Filter news data to a date range.
    
    Args:
        news_df: News DataFrame with 'timestamp' column.
        start_date: Start of date range (inclusive).
        end_date: End of date range (inclusive).
    
    Returns:
        Filtered DataFrame.
    """
    df = news_df.copy()
    
    if start_date is not None:
        start_date = pd.to_datetime(start_date)
        df = df[df["timestamp"] >= start_date]
    
    if end_date is not None:
        end_date = pd.to_datetime(end_date)
        df = df[df["timestamp"] <= end_date]
    
    return df


def get_news_date(timestamp: pd.Timestamp, market_close_hour: int = 16) -> pd.Timestamp:
    """
    Map a news timestamp to a trading date.
    
    News published before market close is assigned to that trading day.
    News published after market close is assigned to the next trading day.
    
    Args:
        timestamp: News publication timestamp.
        market_close_hour: Hour at which market closes (default: 4pm).
    
    Returns:
        Trading date for the news item.
    """
    # Extract date component
    date = timestamp.normalize()
    
    # If published after market close, assign to next day
    if timestamp.hour >= market_close_hour:
        date = date + pd.Timedelta(days=1)
    
    return date


def expand_multi_ticker_news(news_df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand news items that mention multiple tickers into separate rows.
    
    If the ticker column contains comma-separated tickers or lists,
    expand into one row per ticker.
    
    Args:
        news_df: News DataFrame where 'ticker' may contain multiple tickers.
    
    Returns:
        Expanded DataFrame with one row per ticker mention.
    """
    df = news_df.copy()
    
    # Check if ticker column contains lists or comma-separated values
    if df["ticker"].dtype == object:
        # Try to split comma-separated values
        def expand_ticker(ticker):
            if isinstance(ticker, str) and "," in ticker:
                return [t.strip() for t in ticker.split(",")]
            elif isinstance(ticker, list):
                return ticker
            else:
                return [ticker]
        
        df["ticker"] = df["ticker"].apply(expand_ticker)
        
        # Explode the ticker column
        df = df.explode("ticker").reset_index(drop=True)
    
    return df


def create_sample_news_data(
    tickers: List[str],
    start_date: str = "2023-01-01",
    end_date: str = "2024-01-01",
    items_per_ticker_per_day: float = 2.0,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Create sample news data for testing.
    
    Args:
        tickers: List of stock tickers.
        start_date: Start date for sample data.
        end_date: End date for sample data.
        items_per_ticker_per_day: Average news items per ticker per day.
        seed: Random seed for reproducibility.
    
    Returns:
        Sample news DataFrame.
    """
    np.random.seed(seed)
    
    date_range = pd.date_range(start_date, end_date, freq="D")
    
    records = []
    news_id = 0
    
    # Sample headlines (positive, negative, neutral)
    positive_headlines = [
        "{ticker} beats earnings expectations",
        "{ticker} raises guidance for Q4",
        "{ticker} announces new product launch",
        "Analysts upgrade {ticker} to buy",
        "{ticker} reports strong revenue growth",
    ]
    negative_headlines = [
        "{ticker} misses earnings estimates",
        "{ticker} cuts full-year outlook",
        "{ticker} faces regulatory scrutiny",
        "Analysts downgrade {ticker}",
        "{ticker} reports declining margins",
    ]
    neutral_headlines = [
        "{ticker} to present at investor conference",
        "{ticker} announces board changes",
        "{ticker} schedules earnings call",
        "{ticker} files quarterly report",
    ]
    all_headlines = positive_headlines + negative_headlines + neutral_headlines
    
    for date in date_range:
        for ticker in tickers:
            # Random number of news items for this ticker/day
            n_items = np.random.poisson(items_per_ticker_per_day)
            
            for _ in range(n_items):
                # Random time during market hours
                hour = np.random.randint(6, 20)
                minute = np.random.randint(0, 60)
                timestamp = date + pd.Timedelta(hours=hour, minutes=minute)
                
                # Random headline
                headline = np.random.choice(all_headlines).format(ticker=ticker)
                
                records.append({
                    "news_id": f"news_{news_id}",
                    "timestamp": timestamp,
                    "ticker": ticker,
                    "headline": headline,
                    "source": np.random.choice(["Reuters", "Bloomberg", "WSJ", "CNBC"]),
                })
                news_id += 1
    
    df = pd.DataFrame(records)
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    return df
