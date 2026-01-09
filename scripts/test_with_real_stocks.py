"""Test the mid-term stock planner with real stock data (AMD, AMZN)."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to import yfinance for real data
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("yfinance not installed. Install with: pip install yfinance")
    print("Will use synthetic data instead.\n")


def fetch_stock_data(symbols: list, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch stock data from Yahoo Finance or generate synthetic data."""
    
    if HAS_YFINANCE:
        print(f"Fetching data for {symbols} from Yahoo Finance...")
        all_data = []
        
        for symbol in symbols:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            df = df.reset_index()
            df["ticker"] = symbol
            df = df.rename(columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            })
            df = df[["date", "ticker", "open", "high", "low", "close", "volume"]]
            all_data.append(df)
        
        return pd.concat(all_data, ignore_index=True)
    else:
        # Generate synthetic data
        print(f"Generating synthetic data for {symbols}...")
        dates = pd.date_range(start=start_date, end=end_date, freq="B")
        all_data = []
        
        base_prices = {"AMD": 100, "AMZN": 150, "SPY": 450}
        
        for symbol in symbols:
            base = base_prices.get(symbol, 100)
            # Random walk with drift
            returns = np.random.normal(0.0005, 0.02, len(dates))
            prices = base * np.cumprod(1 + returns)
            
            df = pd.DataFrame({
                "date": dates,
                "ticker": symbol,
                "open": prices * (1 + np.random.normal(0, 0.005, len(dates))),
                "high": prices * (1 + np.abs(np.random.normal(0, 0.01, len(dates)))),
                "low": prices * (1 - np.abs(np.random.normal(0, 0.01, len(dates)))),
                "close": prices,
                "volume": np.random.randint(1000000, 50000000, len(dates))
            })
            all_data.append(df)
        
        return pd.concat(all_data, ignore_index=True)


def fetch_benchmark_data(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch SPY as benchmark."""
    
    if HAS_YFINANCE:
        print("Fetching SPY benchmark data...")
        spy = yf.Ticker("SPY")
        df = spy.history(start=start_date, end=end_date)
        df = df.reset_index()
        df = df.rename(columns={"Date": "date", "Close": "close"})
        return df[["date", "close"]]
    else:
        dates = pd.date_range(start=start_date, end=end_date, freq="B")
        returns = np.random.normal(0.0003, 0.01, len(dates))
        prices = 450 * np.cumprod(1 + returns)
        return pd.DataFrame({"date": dates, "close": prices})


def main():
    print("=" * 70)
    print("MID-TERM STOCK PLANNER - Testing with AMD & AMZN")
    print("=" * 70)
    print()
    
    # Settings
    symbols = ["AMD", "AMZN"]
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=3*365)).strftime("%Y-%m-%d")
    
    print(f"Period: {start_date} to {end_date}")
    print(f"Symbols: {symbols}")
    print()
    
    # Fetch data
    price_df = fetch_stock_data(symbols, start_date, end_date)
    benchmark_df = fetch_benchmark_data(start_date, end_date)
    
    print(f"Loaded {len(price_df)} price records")
    print(f"Loaded {len(benchmark_df)} benchmark records")
    print()
    
    # =========================================================================
    # Test Feature Engineering
    # =========================================================================
    print("-" * 70)
    print("TESTING FEATURE ENGINEERING")
    print("-" * 70)
    
    from src.features.engineering import (
        add_return_features,
        add_volatility_features,
        add_volume_features,
        compute_all_features,
        make_training_dataset,
        get_feature_columns,
    )
    
    # Compute basic features
    feature_df = compute_all_features(price_df)
    print(f"Basic features computed: {len(feature_df)} rows")
    print(f"Feature columns: {get_feature_columns(feature_df)}")
    print()
    
    # =========================================================================
    # Test Technical Indicators
    # =========================================================================
    print("-" * 70)
    print("TESTING TECHNICAL INDICATORS")
    print("-" * 70)
    
    from src.indicators.technical import (
        calculate_rsi,
        calculate_macd,
        calculate_bollinger_bands,
        calculate_atr,
        calculate_adx,
    )
    
    # Add technical indicators
    tech_df = feature_df.copy()
    tech_df = calculate_rsi(tech_df)
    tech_df = calculate_macd(tech_df)
    tech_df = calculate_bollinger_bands(tech_df)
    tech_df = calculate_atr(tech_df)
    tech_df = calculate_adx(tech_df)
    
    # Show latest indicator values
    latest = tech_df.groupby("ticker").last().reset_index()
    print("\nLatest Technical Indicators:")
    print("-" * 50)
    for _, row in latest.iterrows():
        print(f"\n{row['ticker']}:")
        print(f"  Price: ${row['close']:.2f}")
        print(f"  RSI: {row['rsi']:.1f}")
        print(f"  MACD: {row['macd']:.3f}")
        print(f"  BB %B: {row['bb_pct']:.2f} (0=lower band, 1=upper band)")
        print(f"  ATR: ${row['atr']:.2f}")
        print(f"  ADX: {row['adx']:.1f} (>25 = trending)")
    print()
    
    # =========================================================================
    # Test Momentum & Mean Reversion Features
    # =========================================================================
    print("-" * 70)
    print("TESTING MOMENTUM & MEAN REVERSION FEATURES")
    print("-" * 70)
    
    from src.strategies.momentum import (
        calculate_momentum_score,
        calculate_relative_strength,
        calculate_52w_high_low_distance,
    )
    from src.strategies.mean_reversion import (
        calculate_zscore,
        calculate_mean_reversion_score,
    )
    
    # Add momentum features
    momentum_df = tech_df.copy()
    momentum_df = calculate_momentum_score(momentum_df)
    momentum_df = calculate_52w_high_low_distance(momentum_df)
    momentum_df = calculate_relative_strength(momentum_df, benchmark_df)
    
    # Add mean reversion features
    momentum_df = calculate_zscore(momentum_df, lookback_days=20)
    momentum_df = momentum_df.rename(columns={"zscore": "zscore_20d"})
    momentum_df = calculate_mean_reversion_score(momentum_df)
    
    # Show latest values
    latest = momentum_df.groupby("ticker").last().reset_index()
    print("\nLatest Momentum & Mean Reversion Signals:")
    print("-" * 50)
    for _, row in latest.iterrows():
        print(f"\n{row['ticker']}:")
        print(f"  Momentum Score: {row['momentum_score']:.2f} (0-1, higher=stronger)")
        print(f"  Distance from 52w High: {row['distance_52w_high']*100:.1f}%")
        print(f"  Relative Strength vs SPY: {row['relative_strength']*100:.1f}%")
        print(f"  Z-Score (20d): {row['zscore_20d']:.2f}")
        print(f"  Mean Reversion Score: {row['mean_reversion_score']:.2f}")
    print()
    
    # =========================================================================
    # Test Training Dataset Creation
    # =========================================================================
    print("-" * 70)
    print("TESTING TRAINING DATASET CREATION")
    print("-" * 70)
    
    training_df = make_training_dataset(momentum_df, benchmark_df, horizon_days=63)
    print(f"Training dataset: {len(training_df)} rows")
    print(f"Target (excess return) stats:")
    print(f"  Mean: {training_df['target'].mean()*100:.2f}%")
    print(f"  Std: {training_df['target'].std()*100:.2f}%")
    print(f"  Min: {training_df['target'].min()*100:.2f}%")
    print(f"  Max: {training_df['target'].max()*100:.2f}%")
    print()
    
    # =========================================================================
    # Test Model Training
    # =========================================================================
    print("-" * 70)
    print("TESTING MODEL TRAINING")
    print("-" * 70)
    
    from src.models.trainer import train_lgbm_regressor, ModelConfig
    
    # Get feature columns
    feature_cols = get_feature_columns(training_df)
    feature_cols = [c for c in feature_cols if c in training_df.columns 
                    and not training_df[c].isna().all()]
    
    # Remove any columns with too many NaN
    valid_cols = []
    for col in feature_cols:
        if training_df[col].isna().sum() / len(training_df) < 0.5:
            valid_cols.append(col)
    feature_cols = valid_cols
    
    print(f"Training with {len(feature_cols)} features:")
    print(f"  {feature_cols[:10]}...")
    
    # Train model
    config = ModelConfig(target_col="target")
    model, X_train, X_valid, metrics = train_lgbm_regressor(training_df, feature_cols, config)
    
    print(f"\nModel trained!")
    print(f"  Train samples: {metrics.get('n_train', 0)}")
    print(f"  Valid samples: {metrics.get('n_valid', 0)}")
    print(f"  Validation RMSE: {metrics.get('rmse', 0):.4f}")
    print(f"  Validation MAE: {metrics.get('mae', 0):.4f}")
    print()
    
    # =========================================================================
    # Test Prediction / Scoring
    # =========================================================================
    print("-" * 70)
    print("TESTING PREDICTION / STOCK RANKING")
    print("-" * 70)
    
    from src.models.predictor import predict
    
    # Score latest date
    latest_date = momentum_df["date"].max()
    latest_features = momentum_df[momentum_df["date"] == latest_date].copy()
    
    # Make predictions
    predictions = predict(model, latest_features, feature_cols)
    
    print(f"\nStock Rankings for {latest_date.date()}:")
    print("-" * 50)
    print(predictions[["ticker", "score", "rank"]].to_string(index=False))
    print()
    
    # =========================================================================
    # Test Risk Metrics
    # =========================================================================
    print("-" * 70)
    print("TESTING RISK METRICS")
    print("-" * 70)
    
    from src.risk.metrics import RiskMetrics
    
    risk_calc = RiskMetrics()
    
    for symbol in symbols:
        symbol_data = price_df[price_df["ticker"] == symbol].copy()
        symbol_data = symbol_data.sort_values("date")
        symbol_data.index = pd.to_datetime(symbol_data["date"])
        equity_curve = symbol_data["close"]
        
        metrics = risk_calc.calculate_all_metrics(equity_curve)
        
        print(f"\n{symbol} Risk Metrics (3-year period):")
        print(f"  Total Return: {metrics.total_return:.1f}%")
        print(f"  Annual Return: {metrics.annualized_return:.1f}%")
        print(f"  Volatility: {metrics.volatility:.1f}%")
        print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"  Sortino Ratio: {metrics.sortino_ratio:.2f}")
        print(f"  Max Drawdown: {metrics.max_drawdown_pct:.1f}%")
        print(f"  VaR (95%): {metrics.var_95:.2f}%")
    print()
    
    # =========================================================================
    # Test Visualization
    # =========================================================================
    print("-" * 70)
    print("TESTING VISUALIZATION")
    print("-" * 70)
    
    try:
        from src.visualization.charts import ChartGenerator
        from src.visualization.performance import PerformanceVisualizer
        
        # Create output directory
        output_dir = Path(__file__).parent.parent / "output" / "test_charts"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        chart_gen = ChartGenerator(chart_dir=str(output_dir))
        
        # Generate chart for each stock
        for symbol in symbols:
            symbol_data = tech_df[tech_df["ticker"] == symbol].copy()
            symbol_data = symbol_data.sort_values("date")
            symbol_data.index = pd.to_datetime(symbol_data["date"])
            
            chart_path = chart_gen.plot_price_with_indicators(
                symbol_data, symbol,
                show_volume=True,
                show_rsi=True,
                show_macd=True
            )
            print(f"Generated chart: {chart_path}")
        
        # Generate equity curve comparison
        perf_viz = PerformanceVisualizer(output_dir=str(output_dir))
        
        # Create combined equity curve
        amd_data = price_df[price_df["ticker"] == "AMD"].copy().sort_values("date")
        amd_data.index = pd.to_datetime(amd_data["date"])
        
        benchmark_data = benchmark_df.copy().sort_values("date")
        benchmark_data.index = pd.to_datetime(benchmark_data["date"])
        
        eq_path = perf_viz.plot_equity_curve(
            amd_data["close"],
            benchmark_data["close"],
            title="AMD vs SPY",
            filename="amd_vs_spy.png"
        )
        print(f"Generated equity curve: {eq_path}")
        
    except Exception as e:
        print(f"Visualization skipped: {e}")
    
    print()
    print("=" * 70)
    print("TEST COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    main()
