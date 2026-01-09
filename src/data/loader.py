"""Data loading module for mid-term stock planner.

This module provides functions to load price and fundamental data
from CSV/Parquet files with validation.
"""

import pandas as pd
from pathlib import Path
from typing import List, Optional, Union


class DataValidationError(Exception):
    """Raised when data validation fails."""
    pass


def _validate_required_columns(
    df: pd.DataFrame,
    required_columns: List[str],
    data_name: str
) -> None:
    """
    Validate that required columns exist in the DataFrame.
    
    Args:
        df: DataFrame to validate.
        required_columns: List of required column names.
        data_name: Name of the data for error messages.
    
    Raises:
        DataValidationError: If required columns are missing.
    """
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise DataValidationError(
            f"{data_name} is missing required columns: {missing}. "
            f"Found columns: {list(df.columns)}"
        )


def _validate_date_column(df: pd.DataFrame, date_col: str = 'date') -> pd.DataFrame:
    """
    Validate and convert date column to datetime.
    
    Args:
        df: DataFrame to validate.
        date_col: Name of the date column.
    
    Returns:
        DataFrame with date column converted to datetime.
    
    Raises:
        DataValidationError: If date column cannot be parsed.
    """
    df = df.copy()
    
    if date_col not in df.columns:
        raise DataValidationError(f"Date column '{date_col}' not found in DataFrame")
    
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        try:
            df[date_col] = pd.to_datetime(df[date_col])
        except Exception as e:
            raise DataValidationError(
                f"Could not parse date column '{date_col}': {e}"
            )
    
    # Check for invalid dates
    if df[date_col].isna().any():
        n_invalid = df[date_col].isna().sum()
        raise DataValidationError(
            f"Date column contains {n_invalid} invalid/null dates"
        )
    
    return df


def load_price_data(
    path: Union[str, Path],
    validate: bool = True
) -> pd.DataFrame:
    """
    Load historical price data.
    
    Expected format:
    - Columns: date, ticker, open, high, low, close, volume
    - date as datetime or parseable string
    
    Args:
        path: Path to CSV or Parquet file.
        validate: Whether to validate the data (default: True).
    
    Returns:
        DataFrame with price data.
    
    Raises:
        DataValidationError: If validation fails.
        FileNotFoundError: If file not found.
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Price data file not found: {path}")
    
    # Load data based on file extension
    if path.suffix.lower() == '.parquet':
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    
    if validate:
        # Validate required columns
        required_columns = ['date', 'ticker', 'close']
        _validate_required_columns(df, required_columns, "Price data")
        
        # Validate and convert date column
        df = _validate_date_column(df)
        
        # Validate numeric columns
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    try:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    except Exception:
                        pass  # Let downstream code handle non-numeric values
    
    # Sort by ticker and date
    df = df.sort_values(['ticker', 'date'])
    df = df.reset_index(drop=True)
    
    return df


def load_fundamental_data(
    path: Union[str, Path],
    validate: bool = True
) -> pd.DataFrame:
    """
    Load fundamental data like PE, PB, etc.
    
    Expected columns: date, ticker, <fundamental fields...>
    
    Args:
        path: Path to CSV or Parquet file.
        validate: Whether to validate the data (default: True).
    
    Returns:
        DataFrame with fundamental data.
    
    Raises:
        DataValidationError: If validation fails.
        FileNotFoundError: If file not found.
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Fundamental data file not found: {path}")
    
    # Load data based on file extension
    if path.suffix.lower() == '.parquet':
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    
    if validate:
        # Validate required columns
        required_columns = ['date', 'ticker']
        _validate_required_columns(df, required_columns, "Fundamental data")
        
        # Validate and convert date column
        df = _validate_date_column(df)
    
    # Sort by ticker and date
    df = df.sort_values(['ticker', 'date'])
    df = df.reset_index(drop=True)
    
    return df


def load_benchmark_data(
    path: Union[str, Path],
    validate: bool = True
) -> pd.DataFrame:
    """
    Load benchmark index data.
    
    Expected columns: date, close (or price, value)
    
    Args:
        path: Path to CSV or Parquet file.
        validate: Whether to validate the data (default: True).
    
    Returns:
        DataFrame with benchmark data.
    
    Raises:
        DataValidationError: If validation fails.
        FileNotFoundError: If file not found.
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Benchmark data file not found: {path}")
    
    # Load data based on file extension
    if path.suffix.lower() == '.parquet':
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    
    if validate:
        # Validate date column
        if 'date' not in df.columns:
            raise DataValidationError("Benchmark data must have 'date' column")
        
        # Validate and convert date column
        df = _validate_date_column(df)
        
        # Check for price column
        price_cols = ['close', 'price', 'value']
        has_price = any(col in df.columns for col in price_cols)
        if not has_price:
            raise DataValidationError(
                f"Benchmark data must have one of {price_cols} columns. "
                f"Found columns: {list(df.columns)}"
            )
    
    # Sort by date
    df = df.sort_values('date')
    df = df.reset_index(drop=True)
    
    return df


def load_universe(
    path: Union[str, Path],
) -> List[str]:
    """
    Load a stock universe from a file.
    
    Supports:
    - CSV with 'ticker' column
    - Text file with one ticker per line
    
    Args:
        path: Path to file.
    
    Returns:
        List of ticker symbols.
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Universe file not found: {path}")
    
    if path.suffix.lower() == '.csv':
        df = pd.read_csv(path)
        if 'ticker' in df.columns:
            return df['ticker'].tolist()
        elif 'symbol' in df.columns:
            return df['symbol'].tolist()
        else:
            # Assume first column is tickers
            return df.iloc[:, 0].tolist()
    else:
        # Text file with one ticker per line
        with open(path, 'r') as f:
            tickers = [line.strip() for line in f if line.strip()]
        return tickers
