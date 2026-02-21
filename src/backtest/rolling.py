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
    min_stocks: int
) -> pd.DataFrame:
    """
    Construct equal-weight portfolio from predictions at a given date.
    
    Args:
        predictions: DataFrame with columns ['date', 'ticker', 'prediction']
        date: Date to construct portfolio for
        top_n: Number of top stocks to select (if None, use top_pct)
        top_pct: Top percentage of stocks to select
        min_stocks: Minimum stocks required
    
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
    
    # Equal weight
    weight = 1.0 / len(selected)
    
    portfolio = pd.DataFrame({
        'ticker': selected['ticker'].values,
        'weight': [weight] * len(selected)
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
    training_data['date'] = pd.to_datetime(training_data['date'])
    price_data = price_data.copy()
    price_data['date'] = pd.to_datetime(price_data['date'])
    benchmark_data = benchmark_data.copy()
    benchmark_data['date'] = pd.to_datetime(benchmark_data['date'])
    
    # Sort data
    training_data = training_data.sort_values(['date', 'ticker'])
    price_data = price_data.sort_values(['date', 'ticker'])
    benchmark_data = benchmark_data.sort_values('date')
    
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
    
    # Walk-forward loop
    train_start = min_date
    test_start = train_start + pd.Timedelta(days=train_days)
    test_end = test_start + pd.Timedelta(days=test_days)
    
    window_num = 0
    while test_end <= max_date:
        window_num += 1
        
        if verbose:
            print(f"Window {window_num}: Train {train_start.date()} to {test_start.date()}, "
                  f"Test {test_start.date()} to {test_end.date()}")
        
        # Extract training window
        train_mask = (training_data['date'] >= train_start) & (training_data['date'] < test_start)
        train_window = training_data[train_mask].copy()
        
        # Extract test window
        test_mask = (training_data['date'] >= test_start) & (training_data['date'] < test_end)
        test_window = training_data[test_mask].copy()
        
        if len(train_window) == 0 or len(test_window) == 0:
            reason = f"Insufficient data (train={len(train_window)}, test={len(test_window)})"
            if verbose:
                print(f"  Skipping window: {reason}")
            skipped_windows.append({'window': window_num, 'reason': reason})
            train_start = train_start + step_delta
            test_start = train_start + pd.Timedelta(days=train_days)
            test_end = test_start + pd.Timedelta(days=test_days)
            continue
        
        # Train model
        try:
            model, X_train, X_valid, metrics = train_lgbm_regressor(
                train_window,
                feature_cols,
                model_config
            )
            if verbose:
                print(f"  Model trained: RMSE={metrics.get('rmse', 'N/A'):.4f}")
        except Exception as e:
            reason = f"Error training model: {e}"
            if verbose:
                print(f"  Skipping: {reason}")
            skipped_windows.append({'window': window_num, 'reason': reason})
            train_start = train_start + step_delta
            test_start = train_start + pd.Timedelta(days=train_days)
            test_end = test_start + pd.Timedelta(days=test_days)
            continue
        
        # Make predictions on test window
        X_test = test_window[feature_cols].fillna(0)
        predictions = model.predict(X_test)
        
        test_predictions = test_window[['date', 'ticker']].copy()
        test_predictions['prediction'] = predictions
        all_predictions.append(test_predictions)
        
        # Information Coefficient (IC) and Rank IC per window
        target_col = getattr(model_config, "target_col", "target")
        ic, rank_ic = None, None
        if target_col in test_window.columns:
            ic, rank_ic = _compute_ic(
                test_predictions["prediction"].values,
                test_window[target_col].values,
            )
        if verbose and ic is not None:
            print(f"  IC={ic:.4f}" + (f"  Rank_IC={rank_ic:.4f}" if rank_ic is not None else ""))
        ic_threshold = getattr(config, "ic_min_threshold", None)
        ic_action = getattr(config, "ic_action", "warn")
        if ic_threshold is not None and ic_action == "warn" and ic is not None:
            if abs(ic) < ic_threshold:
                print(f"  ⚠ IC |{ic:.4f}| < {ic_threshold} (below threshold)")
        
        # Train-period Sharpe (for overfitting detection)
        train_sharpe: Optional[float] = None
        train_rebalance_dates = _get_rebalance_dates(train_start, test_start, config.rebalance_freq)
        train_predictions_df = train_window[['date', 'ticker']].copy()
        train_predictions_df['prediction'] = model.predict(train_window[feature_cols].fillna(0))
        train_positions_list: List[pd.DataFrame] = []
        for rebal_date in train_rebalance_dates:
            if rebal_date >= test_start:
                break
            portfolio = _construct_portfolio(
                train_predictions_df,
                rebal_date,
                config.top_n,
                config.top_pct,
                config.min_stocks
            )
            if len(portfolio) > 0:
                portfolio['date'] = rebal_date
                train_positions_list.append(portfolio[['date', 'ticker', 'weight']])
        if train_positions_list:
            train_positions_df = pd.concat(train_positions_list, ignore_index=True)
            train_port_ret, train_bench_ret = _calculate_portfolio_returns(
                train_positions_df, price_data, benchmark_data, benchmark_price_col
            )
            if len(train_port_ret) > 0:
                train_metrics = _calculate_metrics(
                    train_port_ret, train_bench_ret, train_positions_df
                )
                train_sharpe = train_metrics['sharpe_ratio']

        # Get rebalance dates in test window
        rebalance_dates = _get_rebalance_dates(test_start, test_end, config.rebalance_freq)
        window_positions_list: List[pd.DataFrame] = []

        # Construct portfolios
        for rebal_date in rebalance_dates:
            if rebal_date >= test_end:
                break

            # Construct portfolio
            portfolio = _construct_portfolio(
                test_predictions,
                rebal_date,
                config.top_n,
                config.top_pct,
                config.min_stocks
            )

            if len(portfolio) > 0:
                portfolio['date'] = rebal_date
                block = portfolio[['date', 'ticker', 'weight']]
                all_positions.append(block)
                window_positions_list.append(block)

        # Per-window test Sharpe (for overfitting detection)
        test_sharpe: Optional[float] = None
        if window_positions_list:
            window_positions_df = pd.concat(window_positions_list, ignore_index=True)
            window_port_ret, window_bench_ret = _calculate_portfolio_returns(
                window_positions_df, price_data, benchmark_data, benchmark_price_col
            )
            if len(window_port_ret) > 0:
                window_metrics = _calculate_metrics(
                    window_port_ret, window_bench_ret, window_positions_df
                )
                test_sharpe = window_metrics['sharpe_ratio']

        # Store window results
        wr: Dict[str, Any] = {
            'window': window_num,
            'train_start': train_start,
            'train_end': test_start,
            'test_start': test_start,
            'test_end': test_end,
            'n_train_samples': len(train_window),
            'n_test_samples': len(test_window),
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
        window_results.append(wr)
        
        # Move to next window
        train_start = train_start + step_delta
        test_start = train_start + pd.Timedelta(days=train_days)
        test_end = test_start + pd.Timedelta(days=test_days)
    
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
    ics = [w["ic"] for w in window_results if w.get("ic") is not None]
    rank_ics = [w["rank_ic"] for w in window_results if w.get("rank_ic") is not None]
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
    all_predictions_df['date'] = pd.to_datetime(all_predictions_df['date'])
    latest_date = all_predictions_df['date'].max()
    final_scores_df = all_predictions_df[all_predictions_df['date'] == latest_date].copy()
    
    # Merge feature values from training_data
    training_data['date'] = pd.to_datetime(training_data['date'])
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
    
    Args:
        positions: DataFrame with columns ['date', 'ticker', 'weight']
        price_data: Stock price data with 'date', 'ticker', 'close'
        benchmark_data: Benchmark data with 'date' and price column
        benchmark_price_col: Name of the price column in benchmark_data
    
    Returns:
        Tuple of (portfolio_returns, benchmark_returns) as pd.Series
    """
    # Get unique rebalance dates
    rebalance_dates = sorted(positions['date'].unique())
    
    if len(rebalance_dates) < 2:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    
    portfolio_returns_list = []
    benchmark_returns_list = []
    dates_list = []
    
    # Calculate returns for each period between rebalances
    for i in range(len(rebalance_dates) - 1):
        period_start = rebalance_dates[i]
        period_end = rebalance_dates[i + 1]
        
        # Get positions at start of period
        period_positions = positions[positions['date'] == period_start]
        
        if len(period_positions) == 0:
            continue
        
        # Get daily prices for this period
        period_prices = price_data[
            (price_data['date'] > period_start) &
            (price_data['date'] <= period_end)
        ].copy()
        
        period_benchmark = benchmark_data[
            (benchmark_data['date'] > period_start) &
            (benchmark_data['date'] <= period_end)
        ].copy()
        
        if len(period_prices) == 0:
            continue
        
        # Calculate daily returns for each stock
        period_prices = period_prices.sort_values(['ticker', 'date'])
        period_prices['daily_return'] = period_prices.groupby('ticker')['close'].pct_change(fill_method=None)
        
        # Calculate weighted portfolio return for each day
        for date in period_prices['date'].unique():
            day_prices = period_prices[period_prices['date'] == date]
            
            portfolio_return = 0.0
            total_weight = 0.0
            
            for _, pos in period_positions.iterrows():
                ticker = pos['ticker']
                weight = pos['weight']
                
                ticker_return = day_prices[day_prices['ticker'] == ticker]['daily_return'].values
                if len(ticker_return) > 0 and not np.isnan(ticker_return[0]):
                    portfolio_return += weight * ticker_return[0]
                    total_weight += weight
            
            # Get benchmark return
            day_benchmark = period_benchmark[period_benchmark['date'] == date]
            if len(day_benchmark) > 0:
                benchmark_prev = benchmark_data[benchmark_data['date'] < date][benchmark_price_col].iloc[-1] if len(benchmark_data[benchmark_data['date'] < date]) > 0 else None
                if benchmark_prev is not None:
                    benchmark_return = (day_benchmark[benchmark_price_col].values[0] / benchmark_prev) - 1
                else:
                    benchmark_return = 0.0
                
                if total_weight > 0:
                    dates_list.append(date)
                    portfolio_returns_list.append(portfolio_return)
                    benchmark_returns_list.append(benchmark_return)
    
    if len(dates_list) == 0:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    
    portfolio_returns = pd.Series(portfolio_returns_list, index=dates_list)
    benchmark_returns = pd.Series(benchmark_returns_list, index=dates_list)
    
    return portfolio_returns, benchmark_returns
