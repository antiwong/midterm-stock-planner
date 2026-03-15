"""Walk-forward backtesting module for mid-term stock planner.

This module implements rolling window backtests with configurable
training periods, test periods, and portfolio construction rules.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
import numpy as np

from ..config.config import BacktestConfig
from ..models.trainer import train_lgbm_regressor, ModelConfig

from multiprocessing import Pool, cpu_count as mp_cpu_count
import lightgbm as lgb

class _SilentLogger:
    """Suppress LightGBM C++ Info/Warning messages."""
    def info(self, msg): pass
    def warning(self, msg): pass

# Suppress LightGBM C++ Info/Warning messages globally
lgb.register_logger(_SilentLogger())

# Module-level shared state for multiprocessing workers (set before Pool.map)
_MP_SHARED = {}


def _mp_process_window(args):
    """Module-level worker for multiprocessing. Reads shared data from _MP_SHARED."""
    w_num, w_train_start, w_test_start, w_test_end = args
    s = _MP_SHARED
    training_data = s['training_data']
    feature_cols = s['feature_cols']
    mc = s['model_config']
    config = s['config']
    price_data = s['price_data']
    benchmark_data = s['benchmark_data']
    benchmark_price_col = s['benchmark_price_col']

    # Extract training window
    train_mask = (training_data['date'] >= w_train_start) & (training_data['date'] < w_test_start)
    train_window = training_data[train_mask]
    test_mask = (training_data['date'] >= w_test_start) & (training_data['date'] < w_test_end)
    test_window = training_data[test_mask]

    if len(train_window) == 0 or len(test_window) == 0:
        return None, None, None, {'window': w_num, 'reason': f"Insufficient data (train={len(train_window)}, test={len(test_window)})"}

    # Train model
    try:
        model, X_train, X_valid, metrics = train_lgbm_regressor(train_window, feature_cols, mc)
    except Exception as e:
        return None, None, None, {'window': w_num, 'reason': f"Error training model: {e}"}

    # Predictions on test window
    X_test = test_window[feature_cols].fillna(0)
    predictions = model.predict(X_test)
    test_predictions = test_window[['date', 'ticker']].copy()
    test_predictions['prediction'] = predictions

    # IC / Rank IC
    target_col = getattr(mc, "target_col", "target")
    ic, rank_ic = None, None
    if target_col in test_window.columns:
        ic, rank_ic = _compute_ic(test_predictions["prediction"].values, test_window[target_col].values)

    # Train-period Sharpe (overfitting detection)
    train_sharpe = None
    train_rebalance_dates = _get_rebalance_dates(w_train_start, w_test_start, config.rebalance_freq)
    train_predictions_df = train_window[['date', 'ticker']].copy()
    train_predictions_df['prediction'] = model.predict(train_window[feature_cols].fillna(0))
    train_positions_list = []
    for rebal_date in train_rebalance_dates:
        if rebal_date >= w_test_start:
            break
        portfolio = _construct_portfolio(train_predictions_df, rebal_date, config.top_n, config.top_pct, config.min_stocks)
        if len(portfolio) > 0:
            portfolio['date'] = rebal_date
            train_positions_list.append(portfolio[['date', 'ticker', 'weight']])
    if train_positions_list:
        train_positions_df = pd.concat(train_positions_list, ignore_index=True)
        train_port_ret, train_bench_ret = _calculate_portfolio_returns(train_positions_df, price_data, benchmark_data, benchmark_price_col)
        if len(train_port_ret) > 0:
            train_metrics = _calculate_metrics(train_port_ret, train_bench_ret, train_positions_df)
            train_sharpe = train_metrics['sharpe_ratio']

    # Test-period portfolio
    rebalance_dates = _get_rebalance_dates(w_test_start, w_test_end, config.rebalance_freq)
    window_positions_list = []
    for rebal_date in rebalance_dates:
        if rebal_date >= w_test_end:
            break
        portfolio = _construct_portfolio(test_predictions, rebal_date, config.top_n, config.top_pct, config.min_stocks)
        if len(portfolio) > 0:
            portfolio['date'] = rebal_date
            window_positions_list.append(portfolio[['date', 'ticker', 'weight']])

    test_sharpe = None
    if window_positions_list:
        window_positions_df = pd.concat(window_positions_list, ignore_index=True)
        window_port_ret, window_bench_ret = _calculate_portfolio_returns(window_positions_df, price_data, benchmark_data, benchmark_price_col)
        if len(window_port_ret) > 0:
            window_metrics = _calculate_metrics(window_port_ret, window_bench_ret, window_positions_df)
            test_sharpe = window_metrics['sharpe_ratio']

    wr = {
        'window': w_num,
        'train_start': w_train_start, 'train_end': w_test_start,
        'test_start': w_test_start, 'test_end': w_test_end,
        'n_train_samples': len(train_window), 'n_test_samples': len(test_window),
        'train_rmse': metrics.get('rmse'),
    }
    if ic is not None:
        wr['ic'] = ic
    if rank_ic is not None:
        wr['rank_ic'] = rank_ic
    if train_sharpe is not None:
        wr['train_sharpe'] = train_sharpe
    if test_sharpe is not None:
        wr['test_sharpe'] = test_sharpe

    return test_predictions, window_positions_list, wr, None


@dataclass
class BacktestResults:
    """Results from a backtest run."""
    portfolio_returns: pd.Series
    benchmark_returns: pd.Series
    positions: pd.DataFrame  # date, ticker, weight
    metrics: Dict[str, float]
    window_results: List[Dict[str, Any]]
    predictions: Optional[pd.DataFrame] = None  # date, ticker, prediction
    final_scores: Optional[pd.DataFrame] = None  # Latest scores for each ticker


def _compute_ic(pred: np.ndarray, actual: np.ndarray) -> Tuple[Optional[float], Optional[float]]:
    """Compute Pearson IC and Spearman rank IC between predictions and actuals.
    Returns (ic, rank_ic); either may be None if insufficient data or constant series.
    """
    if pred is None or actual is None or len(pred) != len(actual) or len(pred) < 2:
        return None, None
    pred = np.asarray(pred, dtype=float)
    actual = np.asarray(actual, dtype=float)
    mask = np.isfinite(pred) & np.isfinite(actual)
    if mask.sum() < 2:
        return None, None
    pred = pred[mask]
    actual = actual[mask]
    if pred.std() == 0 or actual.std() == 0:
        return None, None
    ic = np.corrcoef(pred, actual)[0, 1]
    rank_ic = pd.Series(pred).rank().values
    act_rank = pd.Series(actual).rank().values
    if np.std(rank_ic) == 0 or np.std(act_rank) == 0:
        rank_ic_val = None
    else:
        rank_ic_val = np.corrcoef(rank_ic, act_rank)[0, 1]
    return float(ic), float(rank_ic_val) if rank_ic_val is not None else None


def _get_step_delta(step_value: float, step_unit: str):
    """Convert step_value + step_unit to a pandas Timedelta or DateOffset."""
    unit = step_unit.lower()
    if unit in ("hours", "h"):
        return pd.Timedelta(hours=step_value)
    if unit in ("days", "d"):
        return pd.Timedelta(days=step_value)
    if unit in ("months", "month", "m"):
        return pd.DateOffset(months=int(step_value))
    if unit in ("years", "year", "y"):
        return pd.DateOffset(months=int(step_value * 12))
    raise ValueError(f"Unknown step_unit: {step_unit}. Use: hours, days, months, years")


def _get_rebalance_dates(
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    freq: str = "MS"
) -> List[pd.Timestamp]:
    """Get list of rebalance dates between start and end."""
    dates = pd.date_range(start=start_date, end=end_date, freq=freq)
    return dates.tolist()


def _construct_portfolio(
    predictions: pd.DataFrame,
    date: pd.Timestamp,
    top_n: Optional[int],
    top_pct: float,
    min_stocks: int,
    weighting: str = "score"
) -> pd.DataFrame:
    """
    Construct portfolio from predictions at a given date.

    Args:
        predictions: DataFrame with columns ['date', 'ticker', 'prediction']
        date: Date to construct portfolio for
        top_n: Number of top stocks to select (if None, use top_pct)
        top_pct: Top percentage of stocks to select
        min_stocks: Minimum stocks required
        weighting: Weight scheme - "equal" or "score" (prediction-proportional)

    Returns:
        DataFrame with columns ['ticker', 'weight']
    """
    # Find closest date in predictions
    available_dates = predictions['date'].unique()
    closest_date = min(available_dates, key=lambda d: abs((d - date).total_seconds()))

    date_predictions = predictions[predictions['date'] == closest_date].copy()

    if len(date_predictions) == 0:
        return pd.DataFrame(columns=['ticker', 'weight'])

    # Sort by prediction (descending - higher is better)
    date_predictions = date_predictions.sort_values('prediction', ascending=False)

    # Determine number of stocks to select
    if top_n is not None:
        n_stocks = min(top_n, len(date_predictions))
    else:
        n_stocks = max(min_stocks, int(len(date_predictions) * top_pct))

    n_stocks = max(n_stocks, 1)  # At least 1 stock

    # Select top stocks
    selected = date_predictions.head(n_stocks)

    if weighting == "score" and len(selected) > 1:
        # Score-weighted: use prediction values as weights (higher prediction → larger weight)
        scores = selected['prediction'].values.astype(float)
        # Shift scores to be positive (in case of negative predictions)
        scores_shifted = scores - scores.min() + 1e-8
        weights = scores_shifted / scores_shifted.sum()
    else:
        # Equal weight fallback
        weights = np.full(len(selected), 1.0 / len(selected))

    portfolio = pd.DataFrame({
        'ticker': selected['ticker'].values,
        'weight': weights
    })

    return portfolio


def _calculate_metrics(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    positions: pd.DataFrame,
    trading_days_per_year: int = 252
) -> Dict[str, float]:
    """
    Calculate performance metrics.
    
    Returns:
        Dictionary with metrics: annualized_return, sharpe_ratio, max_drawdown,
        turnover, hit_rate, excess_return, volatility
    """
    # Align returns
    returns_df = pd.DataFrame({
        'portfolio': portfolio_returns,
        'benchmark': benchmark_returns
    }).dropna()
    
    if len(returns_df) == 0:
        return {
            'annualized_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'turnover': 0.0,
            'hit_rate': 0.0,
            'excess_return': 0.0,
            'volatility': 0.0,
            'total_return': 0.0,
        }
    
    portfolio_ret = returns_df['portfolio']
    benchmark_ret = returns_df['benchmark']
    excess_ret = portfolio_ret - benchmark_ret
    
    # Total return
    total_return = (1 + portfolio_ret).prod() - 1
    
    # Annualized return
    n_periods = len(portfolio_ret)
    if n_periods > 0:
        annualized_return = (1 + total_return) ** (trading_days_per_year / n_periods) - 1
    else:
        annualized_return = 0.0
    
    # Volatility (annualized)
    volatility = portfolio_ret.std() * np.sqrt(trading_days_per_year)
    
    # Sharpe ratio (annualized, assuming 0 risk-free rate)
    if volatility > 0:
        sharpe_ratio = annualized_return / volatility
    else:
        sharpe_ratio = 0.0
    
    # Max drawdown
    cumulative = (1 + portfolio_ret).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Turnover (average absolute change in weights per rebalance)
    if len(positions) > 0:
        positions_pivot = positions.pivot_table(
            index='date',
            columns='ticker',
            values='weight',
            fill_value=0.0
        )
        if len(positions_pivot) > 1:
            weight_changes = positions_pivot.diff().abs().sum(axis=1)
            turnover = weight_changes.mean()
        else:
            turnover = 0.0
    else:
        turnover = 0.0
    
    # Hit rate (percentage of periods where portfolio beats benchmark)
    if len(excess_ret) > 0:
        hit_rate = (excess_ret > 0).mean()
    else:
        hit_rate = 0.0
    
    # Excess return (annualized)
    total_excess = (1 + excess_ret).prod() - 1
    if n_periods > 0:
        excess_annualized = (1 + total_excess) ** (trading_days_per_year / n_periods) - 1
    else:
        excess_annualized = 0.0
    
    return {
        'total_return': float(total_return),
        'annualized_return': float(annualized_return),
        'sharpe_ratio': float(sharpe_ratio),
        'max_drawdown': float(max_drawdown),
        'turnover': float(turnover),
        'hit_rate': float(hit_rate),
        'excess_return': float(excess_annualized),
        'volatility': float(volatility),
    }


def run_walk_forward_backtest(
    training_data: pd.DataFrame,
    benchmark_data: pd.DataFrame,
    price_data: pd.DataFrame,
    feature_cols: List[str],
    config: Optional[BacktestConfig] = None,
    model_config: Optional[ModelConfig] = None,
    verbose: bool = True,
) -> BacktestResults:
    """
    Run a walk-forward backtest with rolling windows.
    
    Args:
        training_data: Full training dataset with features and target
                      (from make_training_dataset)
        benchmark_data: Benchmark price data with 'date' and price column
        price_data: Stock price data with 'date', 'ticker', 'close'
        feature_cols: List of feature column names
        config: Backtest configuration (uses defaults if None)
        model_config: Model training configuration (uses defaults if None)
        verbose: Whether to print progress messages
    
    Returns:
        BacktestResults with portfolio returns, metrics, and positions
    """
    if config is None:
        config = BacktestConfig()
    if model_config is None:
        model_config = ModelConfig()
    
    # Ensure dates are datetime
    training_data = training_data.copy()
    if not pd.api.types.is_datetime64_any_dtype(training_data['date']):
        training_data['date'] = pd.to_datetime(training_data['date'], format='mixed')
    price_data = price_data.copy()
    if not pd.api.types.is_datetime64_any_dtype(price_data['date']):
        price_data['date'] = pd.to_datetime(price_data['date'], format='mixed')
    benchmark_data = benchmark_data.copy()
    if not pd.api.types.is_datetime64_any_dtype(benchmark_data['date']):
        benchmark_data['date'] = pd.to_datetime(benchmark_data['date'], format='mixed')
    
    # Sort data
    training_data = training_data.sort_values(['date', 'ticker'])
    price_data = price_data.sort_values(['date', 'ticker'])
    benchmark_data = benchmark_data.sort_values('date')

    # Auto-detect data frequency and adjust rebalance frequency if needed
    # If price data is daily but rebalance freq is intraday, override to daily
    _sample_dates = price_data['date'].drop_duplicates().sort_values()
    if len(_sample_dates) > 2:
        _median_gap = _sample_dates.diff().dropna().median()
        _is_daily_data = _median_gap >= pd.Timedelta(hours=12)
        _rebal = config.rebalance_freq
        _is_intraday_rebal = any(u in _rebal.lower() for u in ('h', 'min', 't'))
        if _is_daily_data and _is_intraday_rebal:
            if verbose:
                print(f"  WARNING: Daily price data with intraday rebalance ({_rebal}). Overriding to 'B' (business-day).")
            config = BacktestConfig(
                train_years=config.train_years, test_years=config.test_years,
                step_value=config.step_value, step_unit=config.step_unit,
                rebalance_freq='B', top_n=config.top_n, top_pct=config.top_pct,
                min_stocks=config.min_stocks,
            )

    # Get date range
    min_date = training_data['date'].min()
    max_date = training_data['date'].max()
    
    # Calculate window parameters (approximate days)
    train_days = int(config.train_years * 365.25)
    test_days = int(config.test_years * 365.25)
    step_delta = _get_step_delta(config.step_value, config.step_unit)
    
    if verbose:
        print(f"  Step: {config.step_value} {config.step_unit} (advance between windows)")
    
    # Initialize results storage
    all_predictions = []
    all_positions = []
    window_results = []
    skipped_windows = []
    
    # Identify benchmark price column
    price_cols = ['close', 'price', 'value']
    benchmark_price_col = None
    for col in price_cols:
        if col in benchmark_data.columns:
            benchmark_price_col = col
            break
    
    if benchmark_price_col is None:
        raise ValueError(f"benchmark_data must have one of {price_cols}")
    
    # Pre-compute all window boundaries
    windows = []
    train_start = min_date
    test_start_dt = train_start + pd.Timedelta(days=train_days)
    test_end_dt = test_start_dt + pd.Timedelta(days=test_days)
    window_num = 0
    while test_end_dt <= max_date:
        window_num += 1
        windows.append((window_num, train_start, test_start_dt, test_end_dt))
        train_start = train_start + step_delta
        test_start_dt = train_start + pd.Timedelta(days=train_days)
        test_end_dt = test_start_dt + pd.Timedelta(days=test_days)

    if verbose:
        print(f"  Total windows: {window_num}")

    # Run windows — parallel via multiprocessing.Pool (fork), else sequential
    n_cpus = mp_cpu_count() or 4
    n_workers = min(n_cpus, max(2, len(windows) // 4))
    use_parallel = len(windows) > 4 and not verbose

    if use_parallel:
        # Set shared state for worker processes (fork inherits parent memory)
        lgbm_threads = max(1, n_cpus // n_workers)
        _MP_SHARED['training_data'] = training_data
        _MP_SHARED['feature_cols'] = feature_cols
        _MP_SHARED['model_config'] = ModelConfig(
            target_col=model_config.target_col,
            test_size=model_config.test_size,
            random_state=model_config.random_state,
            params={**model_config.params, 'n_jobs': lgbm_threads},
        )
        _MP_SHARED['config'] = config
        _MP_SHARED['price_data'] = price_data
        _MP_SHARED['benchmark_data'] = benchmark_data
        _MP_SHARED['benchmark_price_col'] = benchmark_price_col

        print(f"  Running {len(windows)} windows in parallel ({n_workers} processes, {lgbm_threads} LightGBM threads each)...")
        import multiprocessing as _mp
        ctx = _mp.get_context('fork')
        with ctx.Pool(n_workers) as pool:
            results = pool.map(_mp_process_window, windows)
        _MP_SHARED.clear()
    else:
        # Sequential (or verbose mode for readable output)
        # Use the module-level worker with shared state for consistency
        _MP_SHARED['training_data'] = training_data
        _MP_SHARED['feature_cols'] = feature_cols
        _MP_SHARED['model_config'] = model_config
        _MP_SHARED['config'] = config
        _MP_SHARED['price_data'] = price_data
        _MP_SHARED['benchmark_data'] = benchmark_data
        _MP_SHARED['benchmark_price_col'] = benchmark_price_col
        results = []
        for i, window_args in enumerate(windows):
            if verbose and i % 50 == 0:
                wn, ts, te_s, te_e = window_args
                print(f"  Window {wn}/{len(windows)}: Train {ts.date()} to {te_s.date()}, Test {te_s.date()} to {te_e.date()}")
            results.append(_mp_process_window(window_args))
        _MP_SHARED.clear()

    # Collect results
    for preds, positions, wr, skip in results:
        if skip is not None:
            skipped_windows.append(skip)
        else:
            if preds is not None:
                all_predictions.append(preds)
            if positions:
                all_positions.extend(positions)
            if wr is not None:
                window_results.append(wr)
    
    # Check if we have any results
    if not all_predictions:
        data_span_days = (max_date - min_date).days
        required_days = train_days + test_days

        if window_num == 0:
            root_cause = "Data span too short: no walk-forward window fits."
            if data_span_days < required_days:
                suggested_fix = (
                    "Extend benchmark data (target = excess vs benchmark):\n"
                    "  python scripts/download_benchmark.py --start 2010-01-01 --no-merge\n"
                    "Or reduce config.backtest.train_years (e.g. 2.0) in config.yaml"
                )
            else:
                suggested_fix = (
                    "Check benchmark alignment. Run:\n"
                    "  python scripts/download_benchmark.py --start 2010-01-01 --no-merge"
                )
        else:
            root_cause = "All windows skipped (train/test empty or model errors)."
            suggested_fix = (
                "Check skipped window reasons below. If 'Insufficient data': extend benchmark.\n"
                "  python scripts/download_benchmark.py --start 2010-01-01 --no-merge"
            )

        error_msg = (
            f"No predictions generated. {root_cause}\n\n"
            f"Data range:   {min_date.date()} to {max_date.date()} ({data_span_days} days)\n"
            f"Required:     {required_days} days ({config.train_years}y train + {config.test_years}y test)\n"
            f"Windows:      {window_num} attempted, {len(skipped_windows)} skipped\n"
        )
        if skipped_windows:
            error_msg += "\nSkipped windows:\n"
            for skip in skipped_windows[:10]:
                error_msg += f"  {skip['window']}: {skip['reason']}\n"
            if len(skipped_windows) > 10:
                error_msg += f"  ... and {len(skipped_windows) - 10} more\n"
        error_msg += f"\nFix:\n{suggested_fix}\n"

        from src.exceptions import InsufficientBacktestDataError
        raise InsufficientBacktestDataError(
            error_msg,
            data_range_days=data_span_days,
            required_days=required_days,
            windows_attempted=window_num,
            windows_skipped=len(skipped_windows),
            skipped_reasons=[s["reason"] for s in skipped_windows],
            suggested_fix=suggested_fix,
        )
    
    if not all_positions:
        from src.exceptions import BacktestError
        raise BacktestError(
            "No positions generated. Check rebalance dates and portfolio construction.",
            diagnostics={"all_predictions": len(all_predictions)},
        )
    
    # Combine results
    all_predictions_df = pd.concat(all_predictions, ignore_index=True)
    all_positions_df = pd.concat(all_positions, ignore_index=True)
    
    # Calculate portfolio returns
    portfolio_returns, benchmark_returns_series = _calculate_portfolio_returns(
        all_positions_df,
        price_data,
        benchmark_data,
        benchmark_price_col
    )
    
    # Calculate metrics
    metrics = _calculate_metrics(
        portfolio_returns,
        benchmark_returns_series,
        all_positions_df
    )
    
    # Aggregate IC metrics from window_results
    ics = [w["ic"] for w in window_results if w.get("ic") is not None and not np.isnan(w["ic"])]
    rank_ics = [w["rank_ic"] for w in window_results if w.get("rank_ic") is not None and not np.isnan(w["rank_ic"])]
    if ics:
        metrics["mean_ic"] = float(np.mean(ics))
        if rank_ics:
            metrics["mean_rank_ic"] = float(np.mean(rank_ics))
        _ic_thresh = getattr(config, "ic_min_threshold", None)
        if _ic_thresh is not None:
            metrics["windows_below_ic_threshold"] = sum(
                1 for w in window_results if w.get("ic") is not None and abs(w["ic"]) < _ic_thresh
            )

    # Overfitting detection: train Sharpe >> test Sharpe (e.g. ratio > 2)
    train_test_ratios = []
    for w in window_results:
        ts = w.get("test_sharpe")
        tr = w.get("train_sharpe")
        if ts is not None and tr is not None and ts > 0:
            train_test_ratios.append(tr / ts)
    if train_test_ratios:
        max_ratio = float(np.max(train_test_ratios))
        metrics["max_train_test_sharpe_ratio"] = max_ratio
        overfit_threshold = getattr(config, "overfit_sharpe_ratio_threshold", 2.0)
        if max_ratio >= overfit_threshold and verbose:
            print(
                f"  ⚠ Overfitting: max(train_sharpe/test_sharpe) = {max_ratio:.2f} "
                f"(threshold {overfit_threshold}). Consider regularization or shorter train window."
            )

    if verbose:
        print(f"\nBacktest Results:")
        print(f"  Total Return: {metrics['total_return']:.2%}")
        print(f"  Annualized Return: {metrics['annualized_return']:.2%}")
        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")
        print(f"  Excess Return: {metrics['excess_return']:.2%}")
    
    # Get final scores (latest prediction for each ticker) with feature values
    if not pd.api.types.is_datetime64_any_dtype(all_predictions_df['date']):
        all_predictions_df['date'] = pd.to_datetime(all_predictions_df['date'], format='mixed')
    latest_date = all_predictions_df['date'].max()
    final_scores_df = all_predictions_df[all_predictions_df['date'] == latest_date].copy()

    # Merge feature values from training_data
    if not pd.api.types.is_datetime64_any_dtype(training_data['date']):
        training_data['date'] = pd.to_datetime(training_data['date'], format='mixed')
    latest_features = training_data[training_data['date'] == latest_date][['ticker'] + feature_cols].copy()
    final_scores_df = final_scores_df.merge(latest_features, on='ticker', how='left')
    
    final_scores_df = final_scores_df.sort_values('prediction', ascending=False)
    final_scores_df['rank'] = range(1, len(final_scores_df) + 1)
    final_scores_df['percentile'] = (1 - final_scores_df['rank'] / len(final_scores_df)) * 100
    
    return BacktestResults(
        portfolio_returns=portfolio_returns,
        benchmark_returns=benchmark_returns_series,
        positions=all_positions_df,
        metrics=metrics,
        window_results=window_results,
        predictions=all_predictions_df,
        final_scores=final_scores_df
    )


def _calculate_portfolio_returns(
    positions: pd.DataFrame,
    price_data: pd.DataFrame,
    benchmark_data: pd.DataFrame,
    benchmark_price_col: str
) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate daily portfolio and benchmark returns.

    Pre-computes daily returns on the full price dataset, then for each
    trading day between the first and last rebalance date, looks up the
    active weights and computes the weighted portfolio return.

    Args:
        positions: DataFrame with columns ['date', 'ticker', 'weight']
        price_data: Stock price data with 'date', 'ticker', 'close'
        benchmark_data: Benchmark data with 'date' and price column
        benchmark_price_col: Name of the price column in benchmark_data

    Returns:
        Tuple of (portfolio_returns, benchmark_returns) as pd.Series
    """
    rebalance_dates = sorted(positions['date'].unique())
    if len(rebalance_dates) < 2:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    # Pre-compute daily returns for all stocks (full dataset)
    price_sorted = price_data.sort_values(['ticker', 'date'])
    price_sorted['daily_return'] = price_sorted.groupby('ticker')['close'].pct_change()

    # Pre-compute benchmark daily returns
    bench_sorted = benchmark_data.sort_values('date')
    bench_sorted['bench_return'] = bench_sorted[benchmark_price_col].pct_change()

    # Build a fast lookup: (date, ticker) -> daily_return
    returns_df = price_sorted[['date', 'ticker', 'daily_return']].dropna(subset=['daily_return'])
    returns_pivot = returns_df.pivot_table(index='date', columns='ticker', values='daily_return')

    # Benchmark return series indexed by date
    bench_ret_series = bench_sorted.set_index('date')['bench_return'].dropna()

    # Get all trading dates between first and last rebalance
    first_rebal = rebalance_dates[0]
    last_rebal = rebalance_dates[-1]
    all_trading_dates = sorted(returns_pivot.index[
        (returns_pivot.index > first_rebal) & (returns_pivot.index <= last_rebal)
    ])

    if len(all_trading_dates) == 0:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    # Build weight schedule: for each trading day, find the active rebalance weights
    # (the most recent rebalance date <= trading date)
    rebal_idx = 0
    portfolio_returns_list = []
    benchmark_returns_list = []
    dates_list = []

    for trade_date in all_trading_dates:
        # Advance rebalance pointer
        while rebal_idx < len(rebalance_dates) - 1 and rebalance_dates[rebal_idx + 1] <= trade_date:
            rebal_idx += 1

        active_rebal = rebalance_dates[rebal_idx]
        active_positions = positions[positions['date'] == active_rebal]

        if len(active_positions) == 0:
            continue

        # Get stock returns for this day
        if trade_date not in returns_pivot.index:
            continue

        day_returns = returns_pivot.loc[trade_date]

        # Compute weighted portfolio return
        port_ret = 0.0
        total_weight = 0.0
        for _, pos in active_positions.iterrows():
            ticker = pos['ticker']
            weight = pos['weight']
            if ticker in day_returns.index and not np.isnan(day_returns[ticker]):
                port_ret += weight * day_returns[ticker]
                total_weight += weight

        if total_weight == 0:
            continue

        # Normalize by total weight — overlapping walk-forward windows create
        # duplicate positions for the same dates, so total_weight >> 1.0.
        # Normalizing ensures the effective portfolio always sums to 1.0.
        port_ret /= total_weight

        # Get benchmark return
        if trade_date in bench_ret_series.index and not np.isnan(bench_ret_series[trade_date]):
            bench_ret = bench_ret_series[trade_date]
        else:
            bench_ret = 0.0

        dates_list.append(trade_date)
        portfolio_returns_list.append(port_ret)
        benchmark_returns_list.append(bench_ret)

    if len(dates_list) == 0:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    return pd.Series(portfolio_returns_list, index=dates_list), pd.Series(benchmark_returns_list, index=dates_list)
