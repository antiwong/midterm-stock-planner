"""Generate sample data for testing the mid-term stock planner."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

def generate_price_data(
    tickers: list,
    start_date: str = "2015-01-01",
    end_date: str = "2024-12-31",
    seed: int = 42
) -> pd.DataFrame:
    """Generate synthetic price data for multiple tickers."""
    np.random.seed(seed)
    
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    
    # Generate business days
    dates = pd.bdate_range(start=start, end=end)
    
    all_data = []
    
    for ticker in tickers:
        # Random starting price
        base_price = np.random.uniform(50, 500)
        
        # Generate returns with some trend and volatility
        n_days = len(dates)
        daily_returns = np.random.normal(0.0005, 0.02, n_days)  # ~12% annual return, 32% vol
        
        # Add some autocorrelation
        for i in range(1, n_days):
            daily_returns[i] += 0.1 * daily_returns[i-1]
        
        # Compute prices
        prices = base_price * np.cumprod(1 + daily_returns)
        
        # Generate OHLCV
        for i, date in enumerate(dates):
            close = prices[i]
            daily_range = close * np.random.uniform(0.005, 0.03)
            high = close + np.random.uniform(0, daily_range)
            low = close - np.random.uniform(0, daily_range)
            open_price = low + np.random.uniform(0, high - low)
            volume = int(np.random.uniform(1e6, 1e8))
            
            all_data.append({
                'date': date,
                'ticker': ticker,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume
            })
    
    df = pd.DataFrame(all_data)
    df = df.sort_values(['ticker', 'date'])
    return df


def generate_benchmark_data(
    start_date: str = "2015-01-01",
    end_date: str = "2024-12-31",
    seed: int = 42
) -> pd.DataFrame:
    """Generate synthetic benchmark (index) data."""
    np.random.seed(seed + 100)  # Different seed
    
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    
    dates = pd.bdate_range(start=start, end=end)
    n_days = len(dates)
    
    # Generate returns with lower volatility than individual stocks
    daily_returns = np.random.normal(0.0003, 0.012, n_days)  # ~8% annual return, 19% vol
    
    # Starting price
    base_price = 2000
    prices = base_price * np.cumprod(1 + daily_returns)
    
    df = pd.DataFrame({
        'date': dates,
        'close': prices.round(2)
    })
    
    return df


def generate_fundamental_data(
    tickers: list,
    start_date: str = "2015-01-01",
    end_date: str = "2024-12-31",
    seed: int = 42
) -> pd.DataFrame:
    """Generate synthetic fundamental data (quarterly)."""
    np.random.seed(seed + 200)
    
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    
    # Generate quarterly dates
    dates = pd.date_range(start=start, end=end, freq='QE')
    
    all_data = []
    
    for ticker in tickers:
        # Random base values
        base_pe = np.random.uniform(10, 40)
        base_pb = np.random.uniform(1, 8)
        
        for date in dates:
            # Add some noise to fundamentals
            pe = base_pe * np.random.uniform(0.8, 1.2)
            pb = base_pb * np.random.uniform(0.9, 1.1)
            
            all_data.append({
                'date': date,
                'ticker': ticker,
                'pe': round(pe, 2),
                'pb': round(pb, 2),
            })
    
    df = pd.DataFrame(all_data)
    df = df.sort_values(['ticker', 'date'])
    return df


if __name__ == "__main__":
    # Define universe
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'JPM', 'JNJ', 'V',
               'PG', 'HD', 'MA', 'UNH', 'DIS', 'BAC', 'ADBE', 'CRM', 'NFLX', 'COST']
    
    # Generate data
    print("Generating price data...")
    price_df = generate_price_data(tickers)
    print(f"  Generated {len(price_df)} price records")
    
    print("Generating benchmark data...")
    benchmark_df = generate_benchmark_data()
    print(f"  Generated {len(benchmark_df)} benchmark records")
    
    print("Generating fundamental data...")
    fundamental_df = generate_fundamental_data(tickers)
    print(f"  Generated {len(fundamental_df)} fundamental records")
    
    # Save to data directory
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    price_df.to_csv(data_dir / "prices.csv", index=False)
    print(f"Saved: {data_dir / 'prices.csv'}")
    
    benchmark_df.to_csv(data_dir / "benchmark.csv", index=False)
    print(f"Saved: {data_dir / 'benchmark.csv'}")
    
    fundamental_df.to_csv(data_dir / "fundamentals.csv", index=False)
    print(f"Saved: {data_dir / 'fundamentals.csv'}")
    
    # Create universe file
    universe_file = data_dir / "universe.txt"
    with open(universe_file, 'w') as f:
        for ticker in tickers:
            f.write(f"{ticker}\n")
    print(f"Saved: {universe_file}")
    
    print("\nDone! Sample data generated.")
