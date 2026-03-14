"""Cross-asset and macro features for enhanced signal generation.

Provides features that capture inter-market relationships:

Commodities (SLV focus):
- gold_silver_ratio: GLD close / SLV close (mean-reverts historically)
- gold_silver_ratio_zscore: Z-score of gold/silver ratio over lookback window
- dxy_momentum: Dollar index proxy (UUP) 21-day return
- real_yield_proxy: TIP (TIPS ETF) 63-day return as proxy for real yields

Semiconductors (AMD focus):
- peer_momentum_nvda: NVDA 21-day return (strongest AMD peer, r~0.55)
- sector_breadth_semis: % of semi peers with positive 21-day return
- qqq_relative_strength: AMD return minus QQQ return over 63 days
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Commodity / macro features (SLV)
# ---------------------------------------------------------------------------

def _merge_reference_close(
    df: pd.DataFrame,
    ref_prices: pd.DataFrame,
    ref_ticker: str,
    col_alias: str,
) -> pd.DataFrame:
    """Merge a reference ticker's close price onto *df* by date.

    Args:
        df: Target DataFrame (must have 'date' column).
        ref_prices: DataFrame with columns [date, ticker, close] (or at least
            date + close for the reference ticker).
        ref_ticker: Ticker to filter from *ref_prices* if it contains
            multiple tickers.
        col_alias: Column name for the merged close price.

    Returns:
        DataFrame with *col_alias* column added.
    """
    ref = ref_prices.copy()

    # Filter to ref_ticker if 'ticker' column exists
    if "ticker" in ref.columns:
        ref = ref[ref["ticker"] == ref_ticker].copy()

    if ref.empty:
        df[col_alias] = np.nan
        return df

    # Ensure datetime
    if not pd.api.types.is_datetime64_any_dtype(ref["date"]):
        ref["date"] = pd.to_datetime(ref["date"], format="mixed")

    ref = ref[["date", "close"]].drop_duplicates(subset=["date"]).rename(
        columns={"close": col_alias}
    )

    df = df.merge(ref, on="date", how="left")
    return df


def add_gold_silver_ratio(
    df: pd.DataFrame,
    gld_prices: pd.DataFrame,
    slv_prices: pd.DataFrame,
    zscore_window: int = 60,
) -> pd.DataFrame:
    """Add gold/silver ratio and its z-score.

    Features added:
    - gold_silver_ratio: GLD close / SLV close
    - gold_silver_ratio_zscore: rolling z-score over *zscore_window* days

    Args:
        df: Target DataFrame with 'date' column (one or many tickers).
        gld_prices: GLD price DataFrame [date, (ticker), close].
        slv_prices: SLV price DataFrame [date, (ticker), close].
        zscore_window: Rolling window for z-score (default 60).

    Returns:
        DataFrame with ratio features added.
    """
    df = _merge_reference_close(df, gld_prices, "GLD", "_gld_close")
    df = _merge_reference_close(df, slv_prices, "SLV", "_slv_close")

    df["gold_silver_ratio"] = df["_gld_close"] / df["_slv_close"].replace(0, np.nan)

    # Z-score per ticker (or global if single-ticker)
    if "ticker" in df.columns:
        rolling_mean = df.groupby("ticker")["gold_silver_ratio"].transform(
            lambda x: x.rolling(window=zscore_window, min_periods=zscore_window // 2).mean()
        )
        rolling_std = df.groupby("ticker")["gold_silver_ratio"].transform(
            lambda x: x.rolling(window=zscore_window, min_periods=zscore_window // 2).std()
        )
    else:
        rolling_mean = df["gold_silver_ratio"].rolling(
            window=zscore_window, min_periods=zscore_window // 2
        ).mean()
        rolling_std = df["gold_silver_ratio"].rolling(
            window=zscore_window, min_periods=zscore_window // 2
        ).std()

    df["gold_silver_ratio_zscore"] = (
        (df["gold_silver_ratio"] - rolling_mean) / rolling_std.replace(0, np.nan)
    )

    # Drop intermediate columns
    df = df.drop(columns=["_gld_close", "_slv_close"], errors="ignore")
    return df


def add_dxy_momentum(
    df: pd.DataFrame,
    uup_prices: pd.DataFrame,
    lookback: int = 21,
) -> pd.DataFrame:
    """Add dollar index momentum using UUP ETF as proxy.

    Feature added:
    - dxy_momentum: UUP *lookback*-day return (decimal).

    Args:
        df: Target DataFrame with 'date' column.
        uup_prices: UUP price DataFrame.
        lookback: Return lookback in trading days (default 21).

    Returns:
        DataFrame with dxy_momentum added.
    """
    df = _merge_reference_close(df, uup_prices, "UUP", "_uup_close")

    if df["_uup_close"].isna().all():
        df["dxy_momentum"] = np.nan
        df = df.drop(columns=["_uup_close"], errors="ignore")
        return df

    # Compute UUP return globally (same value for every ticker on a given date),
    # then broadcast.  Sort by date first.
    uup_series = (
        df[["date", "_uup_close"]]
        .drop_duplicates(subset=["date"])
        .sort_values("date")
        .set_index("date")["_uup_close"]
    )
    uup_ret = uup_series.pct_change(lookback, fill_method=None).rename("dxy_momentum")

    # Merge back
    df = df.merge(uup_ret, left_on="date", right_index=True, how="left")
    df = df.drop(columns=["_uup_close"], errors="ignore")
    return df


def add_real_yield_proxy(
    df: pd.DataFrame,
    tip_prices: pd.DataFrame,
    lookback: int = 63,
) -> pd.DataFrame:
    """Add real yield proxy using TIP ETF return.

    Feature added:
    - real_yield_proxy: TIP *lookback*-day return (decimal).

    Args:
        df: Target DataFrame with 'date' column.
        tip_prices: TIP price DataFrame.
        lookback: Return lookback in trading days (default 63).

    Returns:
        DataFrame with real_yield_proxy added.
    """
    df = _merge_reference_close(df, tip_prices, "TIP", "_tip_close")

    if df["_tip_close"].isna().all():
        df["real_yield_proxy"] = np.nan
        df = df.drop(columns=["_tip_close"], errors="ignore")
        return df

    tip_series = (
        df[["date", "_tip_close"]]
        .drop_duplicates(subset=["date"])
        .sort_values("date")
        .set_index("date")["_tip_close"]
    )
    tip_ret = tip_series.pct_change(lookback, fill_method=None).rename("real_yield_proxy")

    df = df.merge(tip_ret, left_on="date", right_index=True, how="left")
    df = df.drop(columns=["_tip_close"], errors="ignore")
    return df


def add_commodity_cross_asset_features(
    df: pd.DataFrame,
    reference_prices: Dict[str, pd.DataFrame],
    zscore_window: int = 60,
    dxy_lookback: int = 21,
    real_yield_lookback: int = 63,
) -> pd.DataFrame:
    """Add all commodity/macro cross-asset features (SLV focus).

    Convenience wrapper that adds:
    - gold_silver_ratio, gold_silver_ratio_zscore
    - dxy_momentum
    - real_yield_proxy

    Gracefully handles missing reference data by filling with NaN.

    Args:
        df: Target DataFrame with 'date' (and optionally 'ticker').
        reference_prices: Dict mapping ticker -> DataFrame.
            Expected keys: "GLD", "UUP", "TIP".  SLV prices should be in df
            itself or passed as "SLV".
        zscore_window: Window for gold/silver ratio z-score.
        dxy_lookback: Lookback for DXY momentum.
        real_yield_lookback: Lookback for real yield proxy.

    Returns:
        DataFrame with commodity cross-asset features.
    """
    gld = reference_prices.get("GLD", pd.DataFrame())
    slv = reference_prices.get("SLV", pd.DataFrame())
    uup = reference_prices.get("UUP", pd.DataFrame())
    tip = reference_prices.get("TIP", pd.DataFrame())

    # Gold/silver ratio
    if not gld.empty and not slv.empty:
        df = add_gold_silver_ratio(df, gld, slv, zscore_window=zscore_window)
    else:
        df["gold_silver_ratio"] = np.nan
        df["gold_silver_ratio_zscore"] = np.nan

    # DXY momentum
    if not uup.empty:
        df = add_dxy_momentum(df, uup, lookback=dxy_lookback)
    else:
        df["dxy_momentum"] = np.nan

    # Real yield proxy
    if not tip.empty:
        df = add_real_yield_proxy(df, tip, lookback=real_yield_lookback)
    else:
        df["real_yield_proxy"] = np.nan

    return df


# ---------------------------------------------------------------------------
# Semiconductor cross-asset features (AMD)
# ---------------------------------------------------------------------------

SEMI_PEERS_DEFAULT: List[str] = ["NVDA", "INTC", "QCOM", "TXN", "MU", "MRVL", "AVGO"]


def add_peer_momentum_nvda(
    df: pd.DataFrame,
    nvda_prices: pd.DataFrame,
    lookback: int = 21,
) -> pd.DataFrame:
    """Add NVDA peer momentum (21-day return).

    Feature added:
    - peer_momentum_nvda: NVDA *lookback*-day return.

    Args:
        df: Target DataFrame with 'date'.
        nvda_prices: NVDA price DataFrame.
        lookback: Return lookback (default 21).

    Returns:
        DataFrame with peer_momentum_nvda added.
    """
    df = _merge_reference_close(df, nvda_prices, "NVDA", "_nvda_close")

    if df["_nvda_close"].isna().all():
        df["peer_momentum_nvda"] = np.nan
        df = df.drop(columns=["_nvda_close"], errors="ignore")
        return df

    nvda_series = (
        df[["date", "_nvda_close"]]
        .drop_duplicates(subset=["date"])
        .sort_values("date")
        .set_index("date")["_nvda_close"]
    )
    nvda_ret = nvda_series.pct_change(lookback, fill_method=None).rename("peer_momentum_nvda")

    df = df.merge(nvda_ret, left_on="date", right_index=True, how="left")
    df = df.drop(columns=["_nvda_close"], errors="ignore")
    return df


def add_sector_breadth_semis(
    df: pd.DataFrame,
    reference_prices: Dict[str, pd.DataFrame],
    peers: Optional[List[str]] = None,
    lookback: int = 21,
) -> pd.DataFrame:
    """Add semiconductor sector breadth.

    Feature added:
    - sector_breadth_semis: fraction of *peers* with positive *lookback*-day
      return (0.0 to 1.0).

    Args:
        df: Target DataFrame with 'date'.
        reference_prices: Dict mapping ticker -> DataFrame for each peer.
        peers: List of peer tickers (default: SEMI_PEERS_DEFAULT).
        lookback: Return lookback (default 21).

    Returns:
        DataFrame with sector_breadth_semis added.
    """
    if peers is None:
        peers = SEMI_PEERS_DEFAULT

    # Build a date-indexed DataFrame of peer returns
    unique_dates = df[["date"]].drop_duplicates().sort_values("date")
    if not pd.api.types.is_datetime64_any_dtype(unique_dates["date"]):
        unique_dates["date"] = pd.to_datetime(unique_dates["date"], format="mixed")

    positive_counts = pd.Series(np.nan, index=unique_dates["date"])
    valid_peer_count = 0

    for ticker in peers:
        ref = reference_prices.get(ticker, pd.DataFrame())
        if ref.empty:
            continue

        ref = ref.copy()
        if "ticker" in ref.columns:
            ref = ref[ref["ticker"] == ticker]
        if ref.empty:
            continue

        if not pd.api.types.is_datetime64_any_dtype(ref["date"]):
            ref["date"] = pd.to_datetime(ref["date"], format="mixed")

        ref = ref[["date", "close"]].drop_duplicates(subset=["date"]).sort_values("date")
        ref = ref.set_index("date")["close"]
        peer_ret = ref.pct_change(lookback, fill_method=None)

        # Positive indicator (1 if positive, 0 otherwise, NaN if missing)
        positive = (peer_ret > 0).astype(float)
        positive[peer_ret.isna()] = np.nan

        # Align to unique dates
        aligned = positive.reindex(unique_dates["date"])

        if valid_peer_count == 0:
            positive_counts = aligned.fillna(0)
            valid_counts = (~aligned.isna()).astype(float)
        else:
            positive_counts = positive_counts + aligned.fillna(0)
            valid_counts = valid_counts + (~aligned.isna()).astype(float)

        valid_peer_count += 1

    if valid_peer_count == 0:
        df["sector_breadth_semis"] = np.nan
        return df

    breadth = positive_counts / valid_counts.replace(0, np.nan)
    breadth_df = breadth.rename("sector_breadth_semis").reset_index()
    breadth_df.columns = ["date", "sector_breadth_semis"]

    df = df.merge(breadth_df, on="date", how="left")
    return df


def add_qqq_relative_strength(
    df: pd.DataFrame,
    qqq_prices: pd.DataFrame,
    lookback: int = 63,
) -> pd.DataFrame:
    """Add AMD return minus QQQ return over *lookback* days.

    Feature added:
    - qqq_relative_strength: ticker return - QQQ return over *lookback* days.

    Args:
        df: Target DataFrame with 'date', 'ticker', 'close'.
        qqq_prices: QQQ price DataFrame.
        lookback: Return lookback (default 63).

    Returns:
        DataFrame with qqq_relative_strength added.
    """
    df = _merge_reference_close(df, qqq_prices, "QQQ", "_qqq_close")

    if df["_qqq_close"].isna().all():
        df["qqq_relative_strength"] = np.nan
        df = df.drop(columns=["_qqq_close"], errors="ignore")
        return df

    # QQQ return (global, same for all tickers on a date)
    qqq_series = (
        df[["date", "_qqq_close"]]
        .drop_duplicates(subset=["date"])
        .sort_values("date")
        .set_index("date")["_qqq_close"]
    )
    qqq_ret = qqq_series.pct_change(lookback, fill_method=None).rename("_qqq_ret")
    df = df.merge(qqq_ret, left_on="date", right_index=True, how="left")

    # Ticker return
    if "ticker" in df.columns:
        df["_ticker_ret"] = df.groupby("ticker")["close"].pct_change(
            lookback, fill_method=None
        )
    else:
        df["_ticker_ret"] = df["close"].pct_change(lookback, fill_method=None)

    df["qqq_relative_strength"] = df["_ticker_ret"] - df["_qqq_ret"]

    df = df.drop(columns=["_qqq_close", "_qqq_ret", "_ticker_ret"], errors="ignore")
    return df


def add_semiconductor_cross_asset_features(
    df: pd.DataFrame,
    reference_prices: Dict[str, pd.DataFrame],
    peers: Optional[List[str]] = None,
    nvda_lookback: int = 21,
    breadth_lookback: int = 21,
    qqq_lookback: int = 63,
) -> pd.DataFrame:
    """Add all semiconductor cross-asset features (AMD focus).

    Convenience wrapper that adds:
    - peer_momentum_nvda
    - sector_breadth_semis
    - qqq_relative_strength

    Args:
        df: Target DataFrame with 'date', 'ticker', 'close'.
        reference_prices: Dict mapping ticker -> DataFrame.
            Expected keys: "NVDA", "INTC", "QCOM", "TXN", "MU", "MRVL",
            "AVGO", "QQQ".
        peers: Semi peers for breadth (default SEMI_PEERS_DEFAULT).
        nvda_lookback: Lookback for NVDA momentum.
        breadth_lookback: Lookback for sector breadth.
        qqq_lookback: Lookback for QQQ relative strength.

    Returns:
        DataFrame with semiconductor cross-asset features.
    """
    nvda = reference_prices.get("NVDA", pd.DataFrame())
    qqq = reference_prices.get("QQQ", pd.DataFrame())

    # Peer momentum (NVDA)
    if not nvda.empty:
        df = add_peer_momentum_nvda(df, nvda, lookback=nvda_lookback)
    else:
        df["peer_momentum_nvda"] = np.nan

    # Sector breadth
    df = add_sector_breadth_semis(
        df, reference_prices, peers=peers, lookback=breadth_lookback
    )

    # QQQ relative strength
    if not qqq.empty:
        df = add_qqq_relative_strength(df, qqq, lookback=qqq_lookback)
    else:
        df["qqq_relative_strength"] = np.nan

    return df


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------

def add_cross_asset_features(
    price_df: pd.DataFrame,
    reference_prices: Dict[str, pd.DataFrame],
    target_ticker: Optional[str] = None,
    zscore_window: int = 60,
    dxy_lookback: int = 21,
    real_yield_lookback: int = 63,
    nvda_lookback: int = 21,
    breadth_lookback: int = 21,
    qqq_lookback: int = 63,
    semi_peers: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Add cross-asset features based on target ticker or auto-detect.

    Dispatches to commodity or semiconductor feature sets based on
    *target_ticker*.  If *target_ticker* is None the function inspects the
    tickers in *price_df* and applies all applicable feature sets:
    - SLV -> commodity features
    - AMD -> semiconductor features

    Args:
        price_df: DataFrame with ['date', 'ticker', 'close'] at minimum.
        reference_prices: Dict mapping ticker symbol -> price DataFrame.
        target_ticker: If set, only apply features for this ticker.
        zscore_window: Window for gold/silver z-score.
        dxy_lookback: DXY momentum lookback.
        real_yield_lookback: Real yield proxy lookback.
        nvda_lookback: NVDA momentum lookback.
        breadth_lookback: Sector breadth lookback.
        qqq_lookback: QQQ relative strength lookback.
        semi_peers: Custom list of semiconductor peers for breadth.

    Returns:
        DataFrame with cross-asset features added.
    """
    df = price_df.copy()

    # Ensure datetime
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"], format="mixed")

    # Determine which tickers are present
    tickers_in_df = set()
    if "ticker" in df.columns:
        tickers_in_df = set(df["ticker"].unique())

    apply_commodities = False
    apply_semis = False

    if target_ticker is not None:
        if target_ticker == "SLV":
            apply_commodities = True
        elif target_ticker == "AMD":
            apply_semis = True
        else:
            # Apply both if unknown
            apply_commodities = True
            apply_semis = True
    else:
        # Auto-detect based on tickers in df
        if "SLV" in tickers_in_df:
            apply_commodities = True
        if "AMD" in tickers_in_df:
            apply_semis = True
        # If no specific target detected, apply both for general use
        if not apply_commodities and not apply_semis:
            apply_commodities = True
            apply_semis = True

    if apply_commodities:
        df = add_commodity_cross_asset_features(
            df,
            reference_prices,
            zscore_window=zscore_window,
            dxy_lookback=dxy_lookback,
            real_yield_lookback=real_yield_lookback,
        )

    if apply_semis:
        df = add_semiconductor_cross_asset_features(
            df,
            reference_prices,
            peers=semi_peers,
            nvda_lookback=nvda_lookback,
            breadth_lookback=breadth_lookback,
            qqq_lookback=qqq_lookback,
        )

    return df
