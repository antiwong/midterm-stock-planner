"""Technical indicators calculations for panel data (date, ticker).

All functions accept DataFrames with columns including ['date', 'ticker', 'close']
and optionally ['high', 'low', 'volume'] for certain indicators.
"""

import pandas as pd
import numpy as np
from typing import Optional


def calculate_rsi(
    df: pd.DataFrame,
    period: int = 14,
    price_col: str = "close"
) -> pd.DataFrame:
    """
    Calculate Relative Strength Index (RSI) per ticker.
    
    RSI = 100 - 100 / (1 + RS)
    where RS = average gain / average loss over period
    
    Args:
        df: DataFrame with columns ['date', 'ticker', price_col]
        period: RSI period (default 14)
        price_col: Column name for price data
    
    Returns:
        DataFrame with added 'rsi' column
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    def _rsi_for_ticker(group: pd.DataFrame) -> pd.Series:
        delta = group[price_col].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    df["rsi"] = df.groupby("ticker", group_keys=False).apply(
        lambda g: _rsi_for_ticker(g)
    ).reset_index(level=0, drop=True)
    
    return df


def calculate_macd(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    price_col: str = "close"
) -> pd.DataFrame:
    """
    Calculate MACD (Moving Average Convergence Divergence) per ticker.
    
    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(MACD, signal_period)
    Histogram = MACD - Signal
    
    Args:
        df: DataFrame with columns ['date', 'ticker', price_col]
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line period (default 9)
        price_col: Column name for price data
    
    Returns:
        DataFrame with added 'macd', 'macd_signal', 'macd_histogram' columns
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    def _macd_for_ticker(group: pd.DataFrame) -> pd.DataFrame:
        price = group[price_col]
        ema_fast = price.ewm(span=fast_period, adjust=False).mean()
        ema_slow = price.ewm(span=slow_period, adjust=False).mean()
        
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal_period, adjust=False).mean()
        macd_histogram = macd - macd_signal
        
        return pd.DataFrame({
            "macd": macd,
            "macd_signal": macd_signal,
            "macd_histogram": macd_histogram
        }, index=group.index)
    
    macd_df = df.groupby("ticker", group_keys=False).apply(_macd_for_ticker)
    df["macd"] = macd_df["macd"]
    df["macd_signal"] = macd_df["macd_signal"]
    df["macd_histogram"] = macd_df["macd_histogram"]
    
    return df


def calculate_ema(
    df: pd.DataFrame,
    period: int = 20,
    price_col: str = "close"
) -> pd.DataFrame:
    """
    Calculate Exponential Moving Average (EMA) per ticker.
    
    Args:
        df: DataFrame with columns ['date', 'ticker', price_col]
        period: EMA period (default 20)
        price_col: Column name for price data
    
    Returns:
        DataFrame with added 'ema_{period}' column
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    col_name = f"ema_{period}"
    df[col_name] = df.groupby("ticker")[price_col].transform(
        lambda x: x.ewm(span=period, adjust=False).mean()
    )
    
    return df


def calculate_sma(
    df: pd.DataFrame,
    period: int = 20,
    price_col: str = "close"
) -> pd.DataFrame:
    """
    Calculate Simple Moving Average (SMA) per ticker.
    
    Args:
        df: DataFrame with columns ['date', 'ticker', price_col]
        period: SMA period (default 20)
        price_col: Column name for price data
    
    Returns:
        DataFrame with added 'sma_{period}' column
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    col_name = f"sma_{period}"
    df[col_name] = df.groupby("ticker")[price_col].transform(
        lambda x: x.rolling(window=period, min_periods=period).mean()
    )
    
    return df


def calculate_atr(
    df: pd.DataFrame,
    period: int = 14
) -> pd.DataFrame:
    """
    Calculate Average True Range (ATR) per ticker.
    
    True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
    ATR = smoothed average of True Range
    
    Args:
        df: DataFrame with columns ['date', 'ticker', 'high', 'low', 'close']
        period: ATR period (default 14)
    
    Returns:
        DataFrame with added 'atr' column
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    required_cols = ["high", "low", "close"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' required for ATR calculation")
    
    def _atr_for_ticker(group: pd.DataFrame) -> pd.Series:
        high = group["high"]
        low = group["low"]
        close = group["close"]
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period, min_periods=period).mean()
        return atr
    
    df["atr"] = df.groupby("ticker", group_keys=False).apply(
        lambda g: _atr_for_ticker(g)
    ).reset_index(level=0, drop=True)
    
    return df


def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    price_col: str = "close"
) -> pd.DataFrame:
    """
    Calculate Bollinger Bands per ticker.
    
    Middle Band = SMA(period)
    Upper Band = Middle + std_dev * stddev(period)
    Lower Band = Middle - std_dev * stddev(period)
    
    Args:
        df: DataFrame with columns ['date', 'ticker', price_col]
        period: Moving average period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)
        price_col: Column name for price data
    
    Returns:
        DataFrame with added 'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_pct' columns
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    def _bb_for_ticker(group: pd.DataFrame) -> pd.DataFrame:
        price = group[price_col]
        middle = price.rolling(window=period, min_periods=period).mean()
        std = price.rolling(window=period, min_periods=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        width = (upper - lower) / middle  # Normalized width
        pct = (price - lower) / (upper - lower)  # %B indicator
        
        return pd.DataFrame({
            "bb_upper": upper,
            "bb_middle": middle,
            "bb_lower": lower,
            "bb_width": width,
            "bb_pct": pct
        }, index=group.index)
    
    bb_df = df.groupby("ticker", group_keys=False).apply(_bb_for_ticker)
    for col in ["bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_pct"]:
        df[col] = bb_df[col]
    
    return df


def calculate_adx(
    df: pd.DataFrame,
    period: int = 14
) -> pd.DataFrame:
    """
    Calculate Average Directional Index (ADX) per ticker.
    
    ADX measures trend strength (not direction).
    Values > 25 indicate strong trend, < 20 indicate weak/no trend.
    
    Args:
        df: DataFrame with columns ['date', 'ticker', 'high', 'low', 'close']
        period: ADX period (default 14)
    
    Returns:
        DataFrame with added 'adx', 'plus_di', 'minus_di' columns
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    required_cols = ["high", "low", "close"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' required for ADX calculation")
    
    def _adx_for_ticker(group: pd.DataFrame) -> pd.DataFrame:
        high = group["high"]
        low = group["low"]
        close = group["close"]
        
        # True Range
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movement
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
        
        # Smoothed values
        atr = tr.rolling(window=period, min_periods=period).mean()
        plus_dm_smooth = plus_dm.rolling(window=period, min_periods=period).mean()
        minus_dm_smooth = minus_dm.rolling(window=period, min_periods=period).mean()
        
        # Directional Indicators
        plus_di = 100 * (plus_dm_smooth / atr)
        minus_di = 100 * (minus_dm_smooth / atr)
        
        # ADX
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        adx = dx.rolling(window=period, min_periods=period).mean()
        
        return pd.DataFrame({
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di
        }, index=group.index)
    
    adx_df = df.groupby("ticker", group_keys=False).apply(_adx_for_ticker)
    df["adx"] = adx_df["adx"]
    df["plus_di"] = adx_df["plus_di"]
    df["minus_di"] = adx_df["minus_di"]
    
    return df


def calculate_obv(
    df: pd.DataFrame,
    price_col: str = "close"
) -> pd.DataFrame:
    """
    Calculate On-Balance Volume (OBV) per ticker.
    
    OBV is a cumulative volume indicator based on price direction.
    
    Args:
        df: DataFrame with columns ['date', 'ticker', price_col, 'volume']
        price_col: Column name for price data
    
    Returns:
        DataFrame with added 'obv' column
    """
    df = df.copy()
    df = df.sort_values(["ticker", "date"])
    
    if "volume" not in df.columns:
        raise ValueError("Column 'volume' required for OBV calculation")
    
    def _obv_for_ticker(group: pd.DataFrame) -> pd.Series:
        price = group[price_col]
        volume = group["volume"]
        
        direction = np.sign(price.diff())
        obv = (volume * direction).fillna(0).cumsum()
        return obv
    
    df["obv"] = df.groupby("ticker", group_keys=False).apply(
        lambda g: _obv_for_ticker(g)
    ).reset_index(level=0, drop=True)
    
    return df


def calculate_all_indicators(
    df: pd.DataFrame,
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    ema_periods: list = None,
    sma_periods: list = None,
    atr_period: int = 14,
    bb_period: int = 20,
    bb_std: float = 2.0,
    adx_period: int = 14,
    include_obv: bool = True
) -> pd.DataFrame:
    """
    Calculate all available technical indicators.
    
    Args:
        df: DataFrame with OHLCV data and columns ['date', 'ticker', 'open', 'high', 'low', 'close', 'volume']
        rsi_period: RSI period
        macd_fast: MACD fast period
        macd_slow: MACD slow period
        macd_signal: MACD signal period
        ema_periods: List of EMA periods (default [12, 26, 50])
        sma_periods: List of SMA periods (default [20, 50, 200])
        atr_period: ATR period
        bb_period: Bollinger Bands period
        bb_std: Bollinger Bands standard deviation
        adx_period: ADX period
        include_obv: Whether to calculate OBV
    
    Returns:
        DataFrame with all indicators added
    """
    if ema_periods is None:
        ema_periods = [12, 26, 50]
    if sma_periods is None:
        sma_periods = [20, 50, 200]
    
    df = df.copy()
    
    # Momentum indicators
    df = calculate_rsi(df, period=rsi_period)
    df = calculate_macd(df, fast_period=macd_fast, slow_period=macd_slow, signal_period=macd_signal)
    
    # Moving averages
    for period in ema_periods:
        df = calculate_ema(df, period=period)
    for period in sma_periods:
        df = calculate_sma(df, period=period)
    
    # Volatility indicators
    has_hlc = all(col in df.columns for col in ["high", "low", "close"])
    if has_hlc:
        df = calculate_atr(df, period=atr_period)
        df = calculate_adx(df, period=adx_period)
    
    df = calculate_bollinger_bands(df, period=bb_period, std_dev=bb_std)
    
    # Volume indicators
    if include_obv and "volume" in df.columns:
        df = calculate_obv(df)
    
    return df
