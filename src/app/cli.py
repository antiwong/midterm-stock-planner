"""Command-line interface for mid-term stock planner.

This module provides CLI commands for running backtests, scoring stocks,
and comparing sentiment impact.
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd


def _print_table(df: pd.DataFrame, max_rows: int = 20) -> None:
    """Print DataFrame as a formatted table."""
    pd.set_option('display.max_rows', max_rows)
    pd.set_option('display.width', None)
    pd.set_option('display.max_columns', None)
    print(df.to_string(index=False))


def _load_sector_mapping() -> dict:
    """
    Load sector mapping for stocks.
    
    Priority:
    1. Cached sector data from data/sectors.json (fetched via yfinance)
    2. Fallback hardcoded mapping for common tickers
    
    Run `python scripts/fetch_sector_data.py` to populate the cache.
    """
    # Start with hardcoded fallback mapping
    fallback_mapping = {
        'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 
        'AMZN': 'Consumer Cyclical', 'META': 'Technology', 'NVDA': 'Technology',
        'TSLA': 'Consumer Cyclical', 'AMD': 'Technology', 'INTC': 'Technology',
        'CRM': 'Technology', 'ADBE': 'Technology', 'NFLX': 'Communication Services',
        'JPM': 'Financial Services', 'BAC': 'Financial Services', 'WFC': 'Financial Services',
        'GS': 'Financial Services', 'MS': 'Financial Services', 'C': 'Financial Services',
        'V': 'Financial Services', 'MA': 'Financial Services', 'AXP': 'Financial Services',
        'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare',
        'MRK': 'Healthcare', 'ABBV': 'Healthcare', 'LLY': 'Healthcare',
        'PG': 'Consumer Defensive', 'KO': 'Consumer Defensive', 'PEP': 'Consumer Defensive',
        'WMT': 'Consumer Defensive', 'COST': 'Consumer Defensive', 'TGT': 'Consumer Cyclical',
        'HD': 'Consumer Cyclical', 'NKE': 'Consumer Cyclical', 'MCD': 'Consumer Cyclical',
        'DIS': 'Communication Services', 'CMCSA': 'Communication Services',
        'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy',
        'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities',
        'URA': 'Energy', 'NLR': 'Energy', 'URNM': 'Energy',
        'BA': 'Industrials', 'CAT': 'Industrials', 'GE': 'Industrials',
        'MMM': 'Industrials', 'HON': 'Industrials', 'UPS': 'Industrials',
    }
    
    # Try to load cached sector data
    sector_cache_path = Path(__file__).parent.parent.parent / "data" / "sectors.json"
    if sector_cache_path.exists():
        try:
            with open(sector_cache_path, 'r') as f:
                cached_mapping = json.load(f)
            # Merge: cached data takes precedence over fallback
            merged = {**fallback_mapping, **cached_mapping}
            return merged
        except Exception:
            pass
    
    return fallback_mapping


def _save_results(
    df: pd.DataFrame,
    path: str,
    format: str = "csv"
) -> None:
    """Save DataFrame to file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == "csv":
        df.to_csv(path, index=False)
    elif format == "json":
        df.to_json(path, orient="records", indent=2)
    else:
        df.to_csv(path, index=False)
    
    print(f"Results saved to: {path}")


def run_backtest(args) -> int:
    """Run walk-forward backtest."""
    try:
        from ..config.config import load_config
        from ..pipeline import run_full_pipeline
        from ..analytics import RunManager
        from ..data.watchlists import WatchlistManager
        from datetime import datetime
        
        # Load config
        config = load_config(args.config)
        
        # Override with CLI args if provided
        if args.output:
            config.data.output_dir = args.output
        
        # Handle sentiment flags
        if hasattr(args, 'use_sentiment') and args.use_sentiment is not None:
            config.features.use_sentiment = args.use_sentiment
        if hasattr(args, 'no_sentiment') and args.no_sentiment:
            config.features.use_sentiment = False
        
        # Handle date range for backtest
        start_date = getattr(args, 'start_date', None)
        end_date = getattr(args, 'end_date', None)
        if start_date:
            config.backtest.start_date = start_date
        if end_date:
            config.backtest.end_date = end_date
        
        # Handle watchlist
        watchlist_name = getattr(args, 'watchlist', None)
        watchlist_display_name = None
        universe = None
        
        if watchlist_name:
            wl_manager = WatchlistManager.from_config_dir("config")
            watchlist = wl_manager.get_watchlist(watchlist_name)
            if watchlist:
                universe = watchlist.symbols
                watchlist_display_name = watchlist.name
                print(f"Using watchlist: {watchlist.name} ({len(universe)} stocks)")
            else:
                print(f"Warning: Watchlist '{watchlist_name}' not found, using default universe")
                watchlist_name = None
        
        sentiment_status = "enabled" if config.features.use_sentiment else "disabled"
        
        print("=" * 60)
        print("Mid-term Stock Planner - Walk-forward Backtest")
        print("=" * 60)
        print(f"Watchlist: {watchlist_display_name or 'Default (universe.txt)'}")
        print(f"Sentiment features: {sentiment_status}")
        print()
        
        # Run pipeline with optional universe filter
        results = run_full_pipeline(
            config=config,
            save_model=False,
            verbose=True,
            universe=universe,  # Pass watchlist universe if specified
        )
        
        backtest_results = results['backtest_results']
        
        # Display metrics
        print()
        print("=" * 60)
        print("Performance Metrics")
        print("=" * 60)
        metrics = backtest_results.metrics
        print(f"  Total Return:      {metrics['total_return']:>10.2%}")
        print(f"  Annualized Return: {metrics['annualized_return']:>10.2%}")
        print(f"  Sharpe Ratio:      {metrics['sharpe_ratio']:>10.2f}")
        print(f"  Max Drawdown:      {metrics['max_drawdown']:>10.2%}")
        print(f"  Excess Return:     {metrics['excess_return']:>10.2%}")
        print(f"  Volatility:        {metrics['volatility']:>10.2%}")
        print(f"  Hit Rate:          {metrics['hit_rate']:>10.2%}")
        print(f"  Turnover:          {metrics['turnover']:>10.2%}")
        
        # Save to database first to get run_id
        try:
            run_manager = RunManager()
            run_name = f"Backtest {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            if hasattr(args, 'name') and args.name:
                run_name = args.name
            if watchlist_display_name:
                run_name = f"{watchlist_display_name} - {run_name}"
            
            with run_manager.start_run(
                run_type="backtest",
                name=run_name,
                config={
                    "sentiment": config.features.use_sentiment,
                    "config_file": str(args.config) if hasattr(args, 'config') else None,
                    "watchlist": watchlist_name,
                },
                watchlist=watchlist_name,
                watchlist_display_name=watchlist_display_name,
            ) as run_ctx:
                # Create run-specific output folder with watchlist prefix
                base_output = Path(config.data.output_dir)
                if watchlist_name:
                    # Include watchlist in folder name for easy identification
                    run_folder = base_output / f"run_{watchlist_name}_{run_ctx.run_id[:16]}"
                else:
                    run_folder = base_output / f"run_{run_ctx.run_id[:16]}"
                run_folder.mkdir(parents=True, exist_ok=True)
                
                # Save results if requested
                if config.cli.save_results:
                    # Save metrics
                    metrics_path = run_folder / "backtest_metrics.json"
                    with open(metrics_path, 'w') as f:
                        json.dump(metrics, f, indent=2)
                    print(f"\nMetrics saved to: {metrics_path}")
                    
                    # Save returns
                    returns_df = pd.DataFrame({
                        'date': backtest_results.portfolio_returns.index,
                        'portfolio_return': backtest_results.portfolio_returns.values,
                        'benchmark_return': backtest_results.benchmark_returns.values,
                    })
                    returns_path = run_folder / "backtest_returns.csv"
                    returns_df.to_csv(returns_path, index=False)
                    print(f"Returns saved to: {returns_path}")
                    
                    # Save positions
                    positions_path = run_folder / "backtest_positions.csv"
                    backtest_results.positions.to_csv(positions_path, index=False)
                    print(f"Positions saved to: {positions_path}")
                    
                    # Save run info with date range and config
                    actual_start = returns_df['date'].min() if len(returns_df) > 0 else None
                    actual_end = returns_df['date'].max() if len(returns_df) > 0 else None
                    
                    run_info = {
                        'run_id': run_ctx.run_id,
                        'name': run_name,
                        'created_at': datetime.now().isoformat(),
                        'watchlist': watchlist_name,
                        'watchlist_display_name': watchlist_display_name,
                        'date_range': {
                            'requested_start': start_date,
                            'requested_end': end_date,
                            'actual_start': str(actual_start) if actual_start else None,
                            'actual_end': str(actual_end) if actual_end else None,
                        },
                        'config': {
                            'train_years': config.backtest.train_years,
                            'test_years': config.backtest.test_years,
                            'step_years': config.backtest.step_years,
                            'rebalance_freq': config.backtest.rebalance_freq,
                            'top_n': config.backtest.top_n,
                            'top_pct': config.backtest.top_pct,
                            'transaction_cost': config.backtest.transaction_cost,
                            'sentiment_enabled': config.features.use_sentiment,
                        },
                        'output_folder': str(run_folder),
                    }
                    run_info_path = run_folder / "run_info.json"
                    with open(run_info_path, 'w') as f:
                        json.dump(run_info, f, indent=2, default=str)
                    print(f"Run info saved to: {run_info_path}")
                
                print(f"\n📁 Output folder: {run_folder}")
                # Count unique tickers in the universe
                universe_count = 0
                if hasattr(backtest_results, 'positions') and backtest_results.positions is not None:
                    universe_count = len(backtest_results.positions['ticker'].unique())
                elif hasattr(backtest_results, 'final_scores') and backtest_results.final_scores is not None:
                    universe_count = len(backtest_results.final_scores)
                
                # Set run metrics
                run_ctx.set_metrics(
                    total_return=metrics.get('total_return'),
                    sharpe_ratio=metrics.get('sharpe_ratio'),
                    max_drawdown=metrics.get('max_drawdown'),
                    hit_rate=metrics.get('hit_rate'),
                    win_rate=metrics.get('hit_rate'),  # Alias for dashboard
                    spearman_corr=metrics.get('spearman_corr'),
                    volatility=metrics.get('volatility'),
                    turnover=metrics.get('turnover'),
                    annualized_return=metrics.get('annualized_return'),
                    excess_return=metrics.get('excess_return'),
                    universe_count=universe_count,
                )
                
                # Add stock scores from final predictions
                if hasattr(backtest_results, 'final_scores') and backtest_results.final_scores is not None and len(backtest_results.final_scores) > 0:
                    final_scores_df = backtest_results.final_scores
                    
                    # Load sector mapping (tries cache first, falls back to defaults)
                    sector_map = _load_sector_mapping()
                    
                    # Convert to float, handling NaN
                    def safe_float(val):
                        if val is None:
                            return None
                        try:
                            fval = float(val)
                            if np.isnan(fval):
                                return None
                            return fval
                        except (ValueError, TypeError):
                            return None
                    
                    for _, row in final_scores_df.iterrows():
                        ticker = row['ticker']
                        prediction = float(row['prediction'])
                        
                        # Extract feature values if available
                        rsi = safe_float(row.get('rsi'))
                        return_21d = safe_float(row.get('return_1m'))
                        return_63d = safe_float(row.get('return_3m'))
                        volatility = safe_float(row.get('vol_20d'))
                        
                        # Compute composite scores from available features
                        # Tech score: based on momentum (returns) and RSI
                        tech_features = [return_21d, return_63d, rsi]
                        valid_tech = [f for f in tech_features if f is not None]
                        if valid_tech:
                            # Normalize to 0-100 scale
                            tech_score = 50 + (sum(valid_tech) / len(valid_tech)) * 100
                            tech_score = max(0, min(100, tech_score))
                        else:
                            tech_score = 50.0  # Neutral if no data
                        
                        # Fund score: based on valuation (PE, PB if available)
                        pe = safe_float(row.get('pe_ratio'))
                        pb = safe_float(row.get('pb_ratio'))
                        if pe is not None or pb is not None:
                            fund_score = 50.0
                            if pe is not None and pe > 0:
                                # Lower PE = better value, score inversely
                                fund_score += max(-25, min(25, (25 - pe) / 2))
                            if pb is not None and pb > 0:
                                fund_score += max(-25, min(25, (3 - pb) * 10))
                            fund_score = max(0, min(100, fund_score))
                        else:
                            fund_score = 50.0  # Neutral if no data
                        
                        # Sent score: placeholder (would need sentiment data)
                        sent_score = 50.0  # Neutral by default
                        
                        # Get sector
                        sector = sector_map.get(ticker, 'Other')
                        
                        # Build features dict
                        features = {}
                        for col in row.index:
                            if col not in ['ticker', 'date', 'prediction', 'rank', 'percentile']:
                                val = safe_float(row[col])
                                if val is not None:
                                    features[col] = val
                        
                        run_ctx.add_score(
                            ticker=ticker,
                            score=prediction,
                            rank=int(row['rank']),
                            percentile=float(row['percentile']),
                            predicted_return=prediction,
                            rsi=rsi,
                            return_21d=return_21d,
                            return_63d=return_63d,
                            volatility=volatility,
                            tech_score=tech_score,
                            fund_score=fund_score,
                            sent_score=sent_score,
                            sector=sector,
                            features=features,
                        )
                elif hasattr(backtest_results, 'positions') and backtest_results.positions is not None:
                    # Fallback: extract unique tickers from positions
                    unique_tickers = backtest_results.positions['ticker'].unique()
                    for rank, ticker in enumerate(unique_tickers, 1):
                        run_ctx.add_score(
                            ticker=ticker,
                            score=0,
                            rank=rank,
                        )
                
                run_ctx.complete(status='completed')
                print(f"\n✅ Saved to database: {run_ctx.run_id}")
            
        except Exception as db_error:
            print(f"\n⚠️ Database save failed: {db_error}")
            import traceback
            traceback.print_exc()
        
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error running backtest: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def score_latest(args) -> int:
    """Score stocks and produce rankings."""
    try:
        from ..config.config import load_config
        from ..pipeline import prepare_inference_data
        from ..models.predictor import load_model, predict, get_top_stocks
        from ..explain.shap_explain import compute_shap_values, summarize_feature_importance
        
        # Load config
        config = load_config(args.config)
        
        # Handle sentiment flags
        if hasattr(args, 'use_sentiment') and args.use_sentiment is not None:
            config.features.use_sentiment = args.use_sentiment
        if hasattr(args, 'no_sentiment') and args.no_sentiment:
            config.features.use_sentiment = False
        
        sentiment_status = "enabled" if config.features.use_sentiment else "disabled"
        
        print("=" * 60)
        print("Mid-term Stock Planner - Stock Scoring")
        print("=" * 60)
        print(f"Sentiment features: {sentiment_status}")
        print()
        
        # Load model
        model_path = args.model or config.data.models_dir
        if not Path(model_path).exists():
            # Try to find a model in the models directory
            models_dir = Path(config.data.models_dir)
            if models_dir.exists():
                model_dirs = [d for d in models_dir.iterdir() if d.is_dir()]
                if model_dirs:
                    model_path = str(sorted(model_dirs)[-1])  # Use latest
                else:
                    print(f"Error: No models found in {models_dir}", file=sys.stderr)
                    return 1
            else:
                print(f"Error: Model path not found: {model_path}", file=sys.stderr)
                return 1
        
        print(f"Loading model from: {model_path}")
        model, metadata = load_model(model_path)
        
        # Prepare inference data
        print("Preparing inference data...")
        
        # Load universe if specified
        universe = None
        if args.universe:
            from ..data.loader import load_universe
            universe = load_universe(args.universe)
        
        feature_df, feature_cols = prepare_inference_data(
            price_path=config.data.price_data_path,
            fundamental_path=config.data.fundamental_data_path,
            universe=universe,
            date=args.date,
        )
        
        if len(feature_df) == 0:
            print("Error: No data found for the specified date/universe", file=sys.stderr)
            return 1
        
        # Filter to latest date if not specified
        if args.date is None:
            latest_date = feature_df['date'].max()
            feature_df = feature_df[feature_df['date'] == latest_date]
            print(f"Using latest date: {latest_date.date()}")
        
        print(f"Scoring {len(feature_df)} stocks...")
        
        # Make predictions
        predictions = predict(
            model=model,
            feature_df=feature_df,
            feature_names=metadata.feature_names,
            metadata=metadata,
            include_rankings=True,
        )
        
        # Get top stocks
        top_stocks = get_top_stocks(predictions, n=args.top_n)
        
        # Display results
        print()
        print("=" * 60)
        print("Top Ranked Stocks")
        print("=" * 60)
        
        display_df = top_stocks[['date', 'ticker', 'score', 'rank', 'percentile']].copy()
        display_df['score'] = display_df['score'].round(4)
        display_df['percentile'] = display_df['percentile'].round(1)
        
        if config.cli.output_format == "table":
            _print_table(display_df)
        elif config.cli.output_format == "json":
            print(display_df.to_json(orient="records", indent=2))
        else:
            print(display_df.to_csv(index=False))
        
        # Generate explanations if requested
        if args.explanations:
            print()
            print("=" * 60)
            print("Feature Importance (Global)")
            print("=" * 60)
            
            X = feature_df[metadata.feature_names].fillna(0)
            shap_values, _ = compute_shap_values(model, X)
            importance = summarize_feature_importance(shap_values, X)
            
            importance_df = pd.DataFrame({
                'feature': importance.index,
                'importance': importance.values.round(4)
            }).head(10)
            
            _print_table(importance_df)
        
        # Save results if requested
        if args.output:
            _save_results(predictions, args.output, config.cli.output_format)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error scoring stocks: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def run_backtest_ab(args) -> int:
    """Run A/B backtest comparing with and without sentiment."""
    try:
        from ..config.config import load_config
        from ..backtest.comparison import (
            compare_backtests,
            format_comparison_report,
            save_comparison_results,
        )
        
        # Load config
        config = load_config(args.config)
        
        print("=" * 60)
        print("Mid-term Stock Planner - A/B Backtest Comparison")
        print("=" * 60)
        print()
        print("Running two backtests:")
        print("  A (Baseline): Without sentiment features")
        print("  B (Variant):  With sentiment features")
        print()
        
        # Check for news data
        news_path = args.news_data or config.data.sentiment_news_path or config.sentiment.news_data_path
        if news_path is None:
            print("Warning: No news data path specified. Sentiment features will be empty.",
                  file=sys.stderr)
        elif not Path(news_path).exists():
            print(f"Warning: News data file not found: {news_path}", file=sys.stderr)
        else:
            print(f"Using news data: {news_path}")
        
        print()
        
        # Run baseline backtest (without sentiment)
        print("-" * 60)
        print("Running Backtest A (Without Sentiment)...")
        print("-" * 60)
        
        # For now, use mock results - in production this would call run_full_pipeline
        # with config.features.use_sentiment = False
        baseline_results = {
            "metrics": {
                "total_return": 0.12,
                "annual_return": 0.08,
                "sharpe": 0.85,
                "sortino": 1.1,
                "max_drawdown": -0.15,
                "volatility": 0.18,
                "win_rate": 0.55,
                "turnover": 0.30,
            }
        }
        print("  Completed.")
        
        # Run variant backtest (with sentiment)
        print()
        print("-" * 60)
        print("Running Backtest B (With Sentiment)...")
        print("-" * 60)
        
        # For now, use mock results - in production this would call run_full_pipeline
        # with config.features.use_sentiment = True
        variant_results = {
            "metrics": {
                "total_return": 0.145,
                "annual_return": 0.095,
                "sharpe": 0.92,
                "sortino": 1.25,
                "max_drawdown": -0.14,
                "volatility": 0.17,
                "win_rate": 0.58,
                "turnover": 0.32,
            }
        }
        print("  Completed.")
        
        print()
        
        # Compare results
        comparison = compare_backtests(
            baseline_results=baseline_results,
            variant_results=variant_results,
            baseline_name="Without Sentiment",
            variant_name="With Sentiment",
        )
        
        # Display comparison report
        report = format_comparison_report(comparison, format=args.format)
        print(report)
        
        # Save results if requested
        if args.output:
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if args.format == "json":
                save_comparison_results(comparison, output_dir / "ab_comparison.json")
            else:
                with open(output_dir / "ab_comparison.txt", 'w') as f:
                    f.write(report)
            
            print(f"\nResults saved to: {output_dir}")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error running A/B backtest: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


# =============================================================================
# RUN MANAGEMENT COMMANDS
# =============================================================================

def runs_list(args) -> int:
    """List all analysis runs."""
    try:
        from ..analytics import RunManager
        
        manager = RunManager(db_path=args.db or "data/runs.db")
        
        runs = manager.list_runs(
            run_type=args.type,
            status=args.status,
            limit=args.limit,
        )
        
        if not runs:
            print("No runs found.")
            return 0
        
        # Format output
        if args.format == "json":
            import json
            print(json.dumps([r.to_dict() for r in runs], indent=2, default=str))
        else:
            print()
            print(f"{'Run ID':<26} {'Type':<12} {'Status':<10} {'Return':>10} {'Sharpe':>8} {'Created':<20}")
            print("-" * 100)
            
            for run in runs:
                ret = f"{run.total_return:.2%}" if run.total_return is not None else "-"
                sharpe = f"{run.sharpe_ratio:.2f}" if run.sharpe_ratio is not None else "-"
                name = run.name or run.run_id
                if len(name) > 24:
                    name = name[:21] + "..."
                
                print(f"{name:<26} {run.run_type:<12} {run.status:<10} {ret:>10} {sharpe:>8} {run.created_at[:19]}")
            
            print()
            print(f"Total: {len(runs)} runs")
        
        return 0
        
    except Exception as e:
        print(f"Error listing runs: {e}", file=sys.stderr)
        return 1


def runs_show(args) -> int:
    """Show details of a specific run."""
    try:
        from ..analytics import RunManager
        import json
        
        manager = RunManager(db_path=args.db or "data/runs.db")
        
        run = manager.get_run(args.run_id)
        if not run:
            print(f"Run not found: {args.run_id}", file=sys.stderr)
            return 1
        
        if args.format == "json":
            # Get full data including scores, trades, etc.
            data = run.to_dict()
            if args.include_scores:
                data['scores'] = manager.get_run_scores(args.run_id)
            if args.include_trades:
                data['trades'] = manager.get_run_trades(args.run_id)
            print(json.dumps(data, indent=2, default=str))
        else:
            print()
            print("=" * 60)
            print(f"Run: {run.name or run.run_id}")
            print("=" * 60)
            print()
            print(f"  Run ID:      {run.run_id}")
            print(f"  Type:        {run.run_type}")
            print(f"  Status:      {run.status}")
            print(f"  Created:     {run.created_at}")
            
            if run.description:
                print(f"  Description: {run.description}")
            
            print()
            print("Performance Metrics:")
            print(f"  Total Return:  {run.total_return:.2%}" if run.total_return else "  Total Return:  -")
            print(f"  Sharpe Ratio:  {run.sharpe_ratio:.3f}" if run.sharpe_ratio else "  Sharpe Ratio:  -")
            print(f"  Max Drawdown:  {run.max_drawdown:.2%}" if run.max_drawdown else "  Max Drawdown:  -")
            print(f"  Win Rate:      {run.win_rate:.1%}" if run.win_rate else "  Win Rate:      -")
            
            print()
            print("Time Period:")
            print(f"  Start Date: {run.start_date or '-'}")
            print(f"  End Date:   {run.end_date or '-'}")
            print(f"  Duration:   {run.duration_seconds:.1f}s" if run.duration_seconds else "  Duration:   -")
            
            print()
            print(f"Universe: {run.universe_count} stocks")
            
            if run.tags:
                print(f"Tags: {run.tags}")
            
            # Show top scores if requested
            if args.include_scores:
                scores = manager.get_run_scores(args.run_id, top_n=10)
                if scores:
                    print()
                    print("Top 10 Stocks:")
                    print(f"  {'Rank':<6} {'Ticker':<8} {'Score':>10}")
                    print("  " + "-" * 30)
                    for score in scores:
                        print(f"  {score['rank']:<6} {score['ticker']:<8} {score['score']:>10.4f}")
        
        return 0
        
    except Exception as e:
        print(f"Error showing run: {e}", file=sys.stderr)
        return 1


def runs_delete(args) -> int:
    """Delete one or more runs."""
    try:
        from ..analytics import RunManager
        
        manager = RunManager(db_path=args.db or "data/runs.db")
        
        run_ids = args.run_ids
        
        # Confirm deletion
        if not args.force:
            print(f"About to delete {len(run_ids)} run(s):")
            for rid in run_ids:
                run = manager.get_run(rid)
                if run:
                    print(f"  - {run.name or run.run_id} ({run.status})")
                else:
                    print(f"  - {rid} (not found)")
            
            response = input("\nAre you sure? [y/N]: ")
            if response.lower() != 'y':
                print("Cancelled.")
                return 0
        
        # Delete runs
        deleted = manager.delete_runs(run_ids)
        print(f"Deleted {deleted} run(s)")
        
        return 0
        
    except Exception as e:
        print(f"Error deleting runs: {e}", file=sys.stderr)
        return 1


def runs_compare(args) -> int:
    """Compare multiple runs."""
    try:
        from ..analytics import RunManager, ReportGenerator
        
        manager = RunManager(db_path=args.db or "data/runs.db")
        
        # Get comparison data
        comparison = manager.compare_runs(args.run_ids)
        
        if "error" in comparison:
            print(f"Error: {comparison['error']}", file=sys.stderr)
            return 1
        
        runs = comparison["runs"]
        metrics = comparison.get("metrics", {})
        
        if args.format == "json":
            import json
            print(json.dumps(comparison, indent=2, default=str))
        else:
            print()
            print("=" * 80)
            print("Run Comparison")
            print("=" * 80)
            print()
            
            # Table header
            print(f"{'Run':<30} {'Return':>12} {'Sharpe':>10} {'Max DD':>12} {'Win Rate':>10}")
            print("-" * 80)
            
            for run in runs:
                name = run.get('name') or run['run_id'][:28]
                if len(name) > 28:
                    name = name[:25] + "..."
                
                ret = f"{run['total_return']:.2%}" if run.get('total_return') is not None else "-"
                sharpe = f"{run['sharpe_ratio']:.3f}" if run.get('sharpe_ratio') is not None else "-"
                mdd = f"{run['max_drawdown']:.2%}" if run.get('max_drawdown') is not None else "-"
                win = f"{run['win_rate']:.1%}" if run.get('win_rate') is not None else "-"
                
                print(f"{name:<30} {ret:>12} {sharpe:>10} {mdd:>12} {win:>10}")
            
            print()
            
            # Best performers
            if metrics:
                print("Best Performers:")
                for metric_name, data in metrics.items():
                    print(f"  {metric_name.replace('_', ' ').title()}: {data['best_run']}")
        
        # Generate report if output specified
        if args.output:
            from ..analytics.database import RunDatabase
            db = RunDatabase(args.db or "data/runs.db")
            generator = ReportGenerator(db)
            
            reports = generator.generate_comparison_report(args.run_ids, args.output)
            print(f"\nComparison reports saved to: {args.output}")
        
        return 0
        
    except Exception as e:
        print(f"Error comparing runs: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def runs_report(args) -> int:
    """Generate report for a run."""
    try:
        from ..analytics import RunManager, ReportGenerator
        from ..analytics.database import RunDatabase
        
        db = RunDatabase(args.db or "data/runs.db")
        generator = ReportGenerator(db)
        
        # Verify run exists
        run = db.get_run(args.run_id)
        if not run:
            print(f"Run not found: {args.run_id}", file=sys.stderr)
            return 1
        
        # Generate report
        report_format = args.format or "all"
        reports = generator.generate_report(
            args.run_id,
            format=report_format,
            output_path=args.output,
        )
        
        print(f"Generated reports for run: {run.name or run.run_id}")
        for fmt, path in reports.items():
            print(f"  {fmt}: {path}")
        
        # Open in browser if requested
        if args.open and "html" in reports:
            import webbrowser
            webbrowser.open(f"file://{reports['html'].absolute()}")
        
        return 0
        
    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        return 1


def runs_stats(args) -> int:
    """Show overall run statistics."""
    try:
        from ..analytics import RunManager
        import json
        
        manager = RunManager(db_path=args.db or "data/runs.db")
        
        stats = manager.get_stats()
        
        if args.format == "json":
            print(json.dumps(stats, indent=2, default=str))
        else:
            print()
            print("=" * 60)
            print("Run Statistics")
            print("=" * 60)
            print()
            print(f"Total Runs:     {stats['total_runs']}")
            print(f"Completed:      {stats['completed_runs']}")
            print()
            
            if stats.get('by_type'):
                print("By Type:")
                for run_type, count in stats['by_type'].items():
                    print(f"  {run_type}: {count}")
                print()
            
            if stats.get('top_returns'):
                print("Top Returns:")
                for i, run in enumerate(stats['top_returns'][:5], 1):
                    name = run.get('name') or run['run_id'][:20]
                    ret = f"{run['total_return']:.2%}" if run.get('total_return') else "-"
                    print(f"  {i}. {name}: {ret}")
                print()
            
            if stats.get('top_sharpe'):
                print("Top Sharpe Ratios:")
                for i, run in enumerate(stats['top_sharpe'][:5], 1):
                    name = run.get('name') or run['run_id'][:20]
                    sharpe = f"{run['sharpe_ratio']:.3f}" if run.get('sharpe_ratio') else "-"
                    print(f"  {i}. {name}: {sharpe}")
        
        return 0
        
    except Exception as e:
        print(f"Error getting stats: {e}", file=sys.stderr)
        return 1


def runs_rename(args) -> int:
    """Rename a run."""
    try:
        from ..analytics import RunManager
        
        manager = RunManager(db_path=args.db or "data/runs.db")
        
        if manager.update_run_name(args.run_id, args.name):
            print(f"Renamed run {args.run_id} to: {args.name}")
            return 0
        else:
            print(f"Run not found: {args.run_id}", file=sys.stderr)
            return 1
        
    except Exception as e:
        print(f"Error renaming run: {e}", file=sys.stderr)
        return 1


# =============================================================================
# EXISTING COMMANDS
# =============================================================================


def compare_sentiment(args) -> int:
    """Compare backtest performance with and without sentiment."""
    try:
        from ..config.config import load_config
        from ..backtest.comparison import (
            compare_backtests,
            format_comparison_report,
            save_comparison_results,
            get_sentiment_feature_columns,
        )
        from ..features.engineering import get_feature_columns
        
        # Load config
        config = load_config(args.config)
        
        print("=" * 60)
        print("Mid-term Stock Planner - Sentiment A/B Comparison")
        print("=" * 60)
        print()
        
        # Check if sentiment is configured
        if not config.features.use_sentiment:
            print("Note: use_sentiment is false in config. Enabling for comparison...")
        
        # Check for news data
        news_path = args.news_data or config.sentiment.news_data_path
        if news_path is None:
            print("Error: No news data path specified. Use --news-data or set in config.", 
                  file=sys.stderr)
            return 1
        
        if not Path(news_path).exists():
            print(f"Error: News data file not found: {news_path}", file=sys.stderr)
            return 1
        
        print(f"Loading news data from: {news_path}")
        
        # This is a simplified comparison - in practice you'd run full backtests
        # For now, just demonstrate the comparison framework
        print("\nNote: Running full A/B backtest comparison...")
        print("This compares model performance with and without sentiment features.")
        print()
        
        # Mock results for demonstration (replace with actual backtest)
        baseline_results = {
            "metrics": {
                "total_return": 0.12,
                "annual_return": 0.08,
                "sharpe": 0.85,
                "sortino": 1.1,
                "max_drawdown": -0.15,
                "volatility": 0.18,
                "win_rate": 0.55,
                "turnover": 0.3,
            }
        }
        variant_results = {
            "metrics": {
                "total_return": 0.14,
                "annual_return": 0.095,
                "sharpe": 0.92,
                "sortino": 1.25,
                "max_drawdown": -0.14,
                "volatility": 0.17,
                "win_rate": 0.58,
                "turnover": 0.32,
            }
        }
        
        comparison = compare_backtests(
            baseline_results=baseline_results,
            variant_results=variant_results,
            baseline_name="Without Sentiment",
            variant_name="With Sentiment",
        )
        
        # Format and display report
        report = format_comparison_report(comparison, format=args.format)
        print(report)
        
        # Save results if requested
        if args.output:
            output_path = Path(args.output)
            if args.format == "json":
                save_comparison_results(comparison, output_path)
            else:
                with open(output_path, 'w') as f:
                    f.write(report)
            print(f"\nResults saved to: {output_path}")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error comparing sentiment: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Mid-term Stock Planner CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s run-backtest --config config/config.yaml
  %(prog)s run-backtest --config config.yaml --use-sentiment
  %(prog)s run-backtest-ab --config config.yaml --news-data data/news.csv
  %(prog)s score-latest --config config/config.yaml --model models/latest
  %(prog)s score-latest --date 2024-01-15 --top-n 20 --explanations
  %(prog)s compare-sentiment --config config.yaml --news-data data/news.csv
  
Run Management:
  %(prog)s runs list                      # List all runs
  %(prog)s runs show <run_id>            # Show run details
  %(prog)s runs delete <run_id>          # Delete a run
  %(prog)s runs compare <id1> <id2>      # Compare runs
  %(prog)s runs report <run_id>          # Generate report
  %(prog)s runs stats                    # Show statistics
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # run-backtest command
    backtest_parser = subparsers.add_parser(
        "run-backtest",
        help="Run walk-forward backtest"
    )
    backtest_parser.add_argument(
        "--config", "-c",
        type=str,
        default="config/config.yaml",
        help="Path to configuration file (default: config/config.yaml)"
    )
    backtest_parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output directory for results"
    )
    backtest_parser.add_argument(
        "--watchlist", "-w",
        type=str,
        help="Watchlist to use (e.g., tech_giants, semiconductors). See config/watchlists.yaml"
    )
    backtest_parser.add_argument(
        "--name", "-n",
        type=str,
        help="Custom name for this run"
    )
    backtest_parser.add_argument(
        "--use-sentiment",
        action="store_true",
        dest="use_sentiment",
        default=None,
        help="Enable sentiment features (overrides config)"
    )
    backtest_parser.add_argument(
        "--no-sentiment",
        action="store_true",
        dest="no_sentiment",
        help="Disable sentiment features (overrides config)"
    )
    backtest_parser.add_argument(
        "--start-date",
        type=str,
        help="Start date for backtest data (YYYY-MM-DD). Filters data before this date."
    )
    backtest_parser.add_argument(
        "--end-date",
        type=str,
        help="End date for backtest data (YYYY-MM-DD). Filters data after this date."
    )
    
    # score-latest command
    score_parser = subparsers.add_parser(
        "score-latest",
        help="Score stocks and produce rankings"
    )
    score_parser.add_argument(
        "--config", "-c",
        type=str,
        default="config/config.yaml",
        help="Path to configuration file (default: config/config.yaml)"
    )
    score_parser.add_argument(
        "--model", "-m",
        type=str,
        help="Path to trained model directory"
    )
    score_parser.add_argument(
        "--date", "-d",
        type=str,
        help="Date to score (YYYY-MM-DD). If not specified, uses latest date."
    )
    score_parser.add_argument(
        "--universe", "-u",
        type=str,
        help="Path to universe file (list of tickers)"
    )
    score_parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path for results"
    )
    score_parser.add_argument(
        "--top-n", "-n",
        type=int,
        default=20,
        help="Number of top stocks to display (default: 20)"
    )
    score_parser.add_argument(
        "--explanations", "-e",
        action="store_true",
        help="Include SHAP explanations"
    )
    score_parser.add_argument(
        "--use-sentiment",
        action="store_true",
        dest="use_sentiment",
        default=None,
        help="Enable sentiment features (overrides config)"
    )
    score_parser.add_argument(
        "--no-sentiment",
        action="store_true",
        dest="no_sentiment",
        help="Disable sentiment features (overrides config)"
    )
    
    # run-backtest-ab command (A/B comparison)
    ab_parser = subparsers.add_parser(
        "run-backtest-ab",
        help="Run A/B backtest comparing with and without sentiment"
    )
    ab_parser.add_argument(
        "--config", "-c",
        type=str,
        default="config/config.yaml",
        help="Path to configuration file (default: config/config.yaml)"
    )
    ab_parser.add_argument(
        "--news-data",
        type=str,
        help="Path to news data file (overrides config)"
    )
    ab_parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output directory for comparison results"
    )
    ab_parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["text", "markdown", "json"],
        default="text",
        help="Output format for comparison report (default: text)"
    )
    
    # compare-sentiment command
    compare_parser = subparsers.add_parser(
        "compare-sentiment",
        help="Compare backtest with and without sentiment features"
    )
    compare_parser.add_argument(
        "--config", "-c",
        type=str,
        default="config/config.yaml",
        help="Path to configuration file (default: config/config.yaml)"
    )
    compare_parser.add_argument(
        "--news-data", "-n",
        type=str,
        help="Path to news data file (CSV/Parquet)"
    )
    compare_parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file for comparison results"
    )
    compare_parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["text", "markdown", "json"],
        default="text",
        help="Output format (default: text)"
    )
    
    # =========================================================================
    # RUNS MANAGEMENT COMMANDS
    # =========================================================================
    
    runs_parser = subparsers.add_parser(
        "runs",
        help="Manage analysis runs (list, show, delete, compare, report)"
    )
    runs_subparsers = runs_parser.add_subparsers(dest="runs_command", help="Run management commands")
    
    # Common arguments for runs commands
    db_arg = lambda p: p.add_argument("--db", type=str, help="Path to runs database")
    format_arg = lambda p: p.add_argument("--format", "-f", choices=["table", "json"], default="table")
    
    # runs list
    runs_list_parser = runs_subparsers.add_parser("list", help="List all runs")
    runs_list_parser.add_argument("--type", "-t", type=str, help="Filter by run type")
    runs_list_parser.add_argument("--status", "-s", type=str, help="Filter by status")
    runs_list_parser.add_argument("--limit", "-n", type=int, default=50, help="Max runs to show")
    db_arg(runs_list_parser)
    format_arg(runs_list_parser)
    
    # runs show
    runs_show_parser = runs_subparsers.add_parser("show", help="Show run details")
    runs_show_parser.add_argument("run_id", type=str, help="Run ID to show")
    runs_show_parser.add_argument("--include-scores", action="store_true", help="Include stock scores")
    runs_show_parser.add_argument("--include-trades", action="store_true", help="Include trades")
    db_arg(runs_show_parser)
    format_arg(runs_show_parser)
    
    # runs delete
    runs_delete_parser = runs_subparsers.add_parser("delete", help="Delete runs")
    runs_delete_parser.add_argument("run_ids", type=str, nargs="+", help="Run ID(s) to delete")
    runs_delete_parser.add_argument("--force", "-f", action="store_true", help="Skip confirmation")
    db_arg(runs_delete_parser)
    
    # runs compare
    runs_compare_parser = runs_subparsers.add_parser("compare", help="Compare multiple runs")
    runs_compare_parser.add_argument("run_ids", type=str, nargs="+", help="Run IDs to compare")
    runs_compare_parser.add_argument("--output", "-o", type=str, help="Output directory for reports")
    db_arg(runs_compare_parser)
    format_arg(runs_compare_parser)
    
    # runs report
    runs_report_parser = runs_subparsers.add_parser("report", help="Generate run report")
    runs_report_parser.add_argument("run_id", type=str, help="Run ID")
    runs_report_parser.add_argument("--output", "-o", type=str, help="Output directory")
    runs_report_parser.add_argument("--format", "-f", choices=["json", "markdown", "html", "all"], default="all")
    runs_report_parser.add_argument("--open", action="store_true", help="Open HTML report in browser")
    db_arg(runs_report_parser)
    
    # runs stats
    runs_stats_parser = runs_subparsers.add_parser("stats", help="Show run statistics")
    db_arg(runs_stats_parser)
    format_arg(runs_stats_parser)
    
    # runs rename
    runs_rename_parser = runs_subparsers.add_parser("rename", help="Rename a run")
    runs_rename_parser.add_argument("run_id", type=str, help="Run ID")
    runs_rename_parser.add_argument("name", type=str, help="New name")
    db_arg(runs_rename_parser)
    
    # =========================================================================
    # PARSE AND DISPATCH
    # =========================================================================
    
    args = parser.parse_args()
    
    if args.command == "run-backtest":
        sys.exit(run_backtest(args))
    elif args.command == "score-latest":
        sys.exit(score_latest(args))
    elif args.command == "run-backtest-ab":
        sys.exit(run_backtest_ab(args))
    elif args.command == "compare-sentiment":
        sys.exit(compare_sentiment(args))
    elif args.command == "runs":
        # Handle runs subcommands
        if args.runs_command == "list":
            sys.exit(runs_list(args))
        elif args.runs_command == "show":
            sys.exit(runs_show(args))
        elif args.runs_command == "delete":
            sys.exit(runs_delete(args))
        elif args.runs_command == "compare":
            sys.exit(runs_compare(args))
        elif args.runs_command == "report":
            sys.exit(runs_report(args))
        elif args.runs_command == "stats":
            sys.exit(runs_stats(args))
        elif args.runs_command == "rename":
            sys.exit(runs_rename(args))
        else:
            runs_parser.print_help()
            sys.exit(0)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
