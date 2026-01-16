"""
Data Loader for Analysis
=========================
Load portfolio data from run output files for comprehensive analysis.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import warnings


class RunDataLoader:
    """Load portfolio and stock data from run output files."""
    
    def __init__(self, run_dir: Path):
        """
        Initialize loader with run directory.
        
        Args:
            run_dir: Path to run output directory
        """
        self.run_dir = Path(run_dir)
        if not self.run_dir.exists():
            raise ValueError(f"Run directory does not exist: {run_dir}")
    
    def load_portfolio_returns(self) -> Optional[pd.Series]:
        """Load portfolio returns from backtest results."""
        # Try backtest_returns.csv
        returns_path = self.run_dir / "backtest_returns.csv"
        if returns_path.exists():
            df = pd.read_csv(returns_path)
            if 'date' in df.columns and 'portfolio_return' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                return df.set_index('date')['portfolio_return']
        
        # Try equity curve
        equity_path = self.run_dir / "equity_curve.csv"
        if equity_path.exists():
            df = pd.read_csv(equity_path)
            if 'date' in df.columns and 'value' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                returns = df['value'].pct_change().dropna()
                returns.index = df['date'].iloc[1:]
                return returns
        
        return None
    
    def load_portfolio_weights(self) -> Optional[pd.DataFrame]:
        """Load portfolio weights over time."""
        # Try backtest_positions.csv
        positions_path = self.run_dir / "backtest_positions.csv"
        if positions_path.exists():
            df = pd.read_csv(positions_path)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                
                # Pivot to get weights by date and ticker
                if 'ticker' in df.columns and 'weight' in df.columns:
                    weights = df.pivot_table(
                        index='date',
                        columns='ticker',
                        values='weight',
                        aggfunc='first'
                    )
                    return weights.fillna(0)
        
        # Try portfolio files
        portfolio_files = list(self.run_dir.glob("portfolio_*.csv"))
        if portfolio_files:
            # Load latest portfolio
            latest = max(portfolio_files, key=lambda p: p.stat().st_mtime)
            df = pd.read_csv(latest)
            if 'ticker' in df.columns and 'weight' in df.columns:
                # Create single-row DataFrame (current weights)
                weights = df.set_index('ticker')['weight'].to_frame().T
                weights.index = [datetime.now()]
                return weights
        
        return None
    
    def load_stock_returns(self) -> Optional[pd.DataFrame]:
        """
        Load individual stock returns from multiple redundant sources.
        
        Tries in order:
        1. Backtest results (backtest_returns.csv with individual stock returns)
        2. Price data files (if available)
        3. Portfolio enriched files (may contain return columns)
        4. yfinance API (fallback - fetch from Yahoo Finance)
        """
        # Try 1: Backtest results with individual stock returns
        returns_path = self.run_dir / "backtest_returns.csv"
        if returns_path.exists():
            df = pd.read_csv(returns_path)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                # Check if we have individual stock returns (columns like ticker_return or ticker_ret)
                stock_cols = [col for col in df.columns if col.endswith('_return') or col.endswith('_ret')]
                if stock_cols:
                    # Pivot to get returns by date and ticker
                    # Assuming format: date, ticker, return or date, ticker_return columns
                    if 'ticker' in df.columns and 'return' in df.columns:
                        returns_df = df.pivot_table(
                            index='date',
                            columns='ticker',
                            values='return',
                            aggfunc='first'
                        )
                        return returns_df
        
        # Try 2: Price data files
        price_files = list(self.run_dir.glob("*price*.csv")) + list(self.run_dir.glob("*prices*.csv"))
        if price_files:
            for price_file in price_files:
                try:
                    df = pd.read_csv(price_file)
                    if 'date' in df.columns and 'ticker' in df.columns and 'close' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                        # Calculate returns from close prices
                        df = df.sort_values(['ticker', 'date'])
                        df['return'] = df.groupby('ticker')['close'].pct_change()
                        returns_df = df.pivot_table(
                            index='date',
                            columns='ticker',
                            values='return',
                            aggfunc='first'
                        )
                        return returns_df.dropna(how='all')
                except Exception:
                    continue
        
        # Try 3: Portfolio enriched files (may have return columns)
        enriched_files = list(self.run_dir.glob("*portfolio_enriched*.csv"))
        for enriched_file in enriched_files:
            try:
                df = pd.read_csv(enriched_file)
                # Check for return-related columns
                return_cols = [col for col in df.columns if 'return' in col.lower() or 'ret' in col.lower()]
                if return_cols and 'date' in df.columns and 'ticker' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    return_col = return_cols[0]  # Use first return column found
                    returns_df = df.pivot_table(
                        index='date',
                        columns='ticker',
                        values=return_col,
                        aggfunc='first'
                    )
                    return returns_df.dropna(how='all')
            except Exception:
                continue
        
        # Try 4: yfinance fallback (if we have holdings and date range)
        try:
            portfolio_files = list(self.run_dir.glob("portfolio_*.csv"))
            if portfolio_files:
                # Get holdings from portfolio file
                latest_portfolio = max(portfolio_files, key=lambda p: p.stat().st_mtime)
                portfolio_df = pd.read_csv(latest_portfolio)
                if 'ticker' in portfolio_df.columns:
                    tickers = portfolio_df['ticker'].unique().tolist()
                    
                    # Get date range from portfolio returns
                    portfolio_returns = self.load_portfolio_returns()
                    if portfolio_returns is not None and len(tickers) > 0:
                        start_date = portfolio_returns.index[0]
                        end_date = portfolio_returns.index[-1]
                        
                        # Fetch from yfinance
                        import yfinance as yf
                        all_returns = []
                        for ticker in tickers[:20]:  # Limit to avoid rate limits
                            try:
                                ticker_obj = yf.Ticker(ticker)
                                hist = ticker_obj.history(start=start_date, end=end_date)
                                if not hist.empty and 'Close' in hist.columns:
                                    returns = hist['Close'].pct_change().dropna()
                                    returns.name = ticker
                                    all_returns.append(returns)
                            except Exception:
                                continue
                        
                        if all_returns:
                            returns_df = pd.DataFrame(all_returns).T
                            returns_df.index = pd.to_datetime(returns_df.index)
                            return returns_df
        except ImportError:
            pass  # yfinance not available
        except Exception:
            pass  # Other errors
        
        return None
    
    def load_stock_features(self) -> Optional[pd.DataFrame]:
        """
        Load stock features/scores and merge fundamental data.
        
        Tries multiple sources and merges fundamental data from fundamentals.csv.
        """
        features_df = None
        
        # Try portfolio enriched file
        enriched_files = list(self.run_dir.glob("*portfolio_enriched*.csv"))
        if enriched_files:
            latest = max(enriched_files, key=lambda p: p.stat().st_mtime)
            features_df = pd.read_csv(latest)
        
        # If no enriched file, try scores from database or other sources
        if features_df is None:
            # Try scores files
            scores_files = list(self.run_dir.glob("*scores*.csv"))
            if scores_files:
                latest = max(scores_files, key=lambda p: p.stat().st_mtime)
                features_df = pd.read_csv(latest)
        
        if features_df is None:
            return None
        
        # Merge fundamental data from fundamentals.csv
        fundamentals_path = Path("data/fundamentals.csv")
        if fundamentals_path.exists():
            try:
                fundamentals_df = pd.read_csv(fundamentals_path)
                
                # Get latest fundamental data for each ticker
                if 'ticker' in fundamentals_df.columns and 'date' in fundamentals_df.columns:
                    fundamentals_df['date'] = pd.to_datetime(fundamentals_df['date'])
                    # Get most recent data for each ticker
                    fundamentals_latest = fundamentals_df.sort_values('date').groupby('ticker').last().reset_index()
                    
                    # Map column names (fundamentals.csv uses 'pe', 'pb', etc.)
                    column_mapping = {
                        'pe': 'pe_ratio',
                        'pb': 'pb_ratio',
                        'roe': 'roe',
                        'net_margin': 'net_margin',
                        'gross_margin': 'gross_margin',
                        'operating_margin': 'operating_margin',
                        'market_cap': 'market_cap'
                    }
                    
                    # Rename columns to match expected names
                    for old_col, new_col in column_mapping.items():
                        if old_col in fundamentals_latest.columns:
                            fundamentals_latest = fundamentals_latest.rename(columns={old_col: new_col})
                    
                    # Merge with features
                    if 'ticker' in features_df.columns:
                        # Long format - merge on ticker
                        features_df = features_df.merge(
                            fundamentals_latest[['ticker'] + [c for c in fundamentals_latest.columns 
                                                              if c in column_mapping.values() or c in ['pe', 'pb', 'roe', 'market_cap']]],
                            on='ticker',
                            how='left',
                            suffixes=('', '_fund')
                        )
                    elif features_df.index.name == 'ticker' or all(isinstance(x, str) for x in features_df.index[:5]):
                        # Index is ticker - merge on index
                        features_df = features_df.merge(
                            fundamentals_latest.set_index('ticker')[[c for c in fundamentals_latest.columns 
                                                                    if c in column_mapping.values() or c in ['pe', 'pb', 'roe', 'market_cap']]],
                            left_index=True,
                            right_index=True,
                            how='left',
                            suffixes=('', '_fund')
                        )
            except Exception as e:
                # If merge fails, continue without fundamentals
                import warnings
                warnings.warn(f"Could not merge fundamental data: {e}")
        
        return features_df
    
    def load_sector_mapping(self) -> Dict[str, str]:
        """Load ticker to sector mapping."""
        mapping = {}
        
        # Try from portfolio files
        portfolio_files = list(self.run_dir.glob("portfolio_*.csv"))
        for file in portfolio_files:
            try:
                df = pd.read_csv(file)
                if 'ticker' in df.columns and 'sector' in df.columns:
                    for _, row in df.iterrows():
                        mapping[row['ticker']] = row['sector']
            except Exception:
                continue
        
        return mapping
    
    def load_backtest_metrics(self) -> Optional[Dict[str, Any]]:
        """Load backtest metrics."""
        metrics_path = self.run_dir / "backtest_metrics.json"
        if metrics_path.exists():
            with open(metrics_path, 'r') as f:
                return json.load(f)
        
        # Try portfolio_metrics
        metrics_files = list(self.run_dir.glob("*portfolio_metrics*.json"))
        if metrics_files:
            latest = max(metrics_files, key=lambda p: p.stat().st_mtime)
            with open(latest, 'r') as f:
                return json.load(f)
        
        return None
    
    def load_portfolio_data(self) -> Dict[str, Any]:
        """
        Load all portfolio data for analysis.
        
        Returns:
            Dictionary with portfolio data
        """
        returns = self.load_portfolio_returns()
        weights = self.load_portfolio_weights()
        sector_mapping = self.load_sector_mapping()
        metrics = self.load_backtest_metrics()
        
        # Determine date range
        start_date = None
        end_date = None
        
        if returns is not None and len(returns) > 0:
            start_date = returns.index[0]
            end_date = returns.index[-1]
        elif weights is not None and len(weights) > 0:
            start_date = weights.index[0]
            end_date = weights.index[-1]
        else:
            start_date = datetime.now()
            end_date = datetime.now()
        
        # Get holdings from weights or sector mapping
        holdings = []
        if weights is not None:
            if isinstance(weights, pd.DataFrame):
                # Get latest weights
                latest_weights = weights.iloc[-1] if len(weights) > 0 else pd.Series()
                holdings = latest_weights[latest_weights > 0].index.tolist()
            else:
                holdings = weights[weights > 0].index.tolist()
        elif sector_mapping:
            holdings = list(sector_mapping.keys())
        else:
            # Try to get from portfolio files as fallback
            portfolio_files = list(self.run_dir.glob("portfolio_*.csv"))
            for file in portfolio_files:
                try:
                    df = pd.read_csv(file)
                    if 'ticker' in df.columns:
                        holdings = df['ticker'].unique().tolist()
                        break
                except Exception:
                    continue
        
        # Try to get stock returns from redundant sources
        stock_returns = self.load_stock_returns()
        
        return {
            'returns': returns,
            'weights': weights,
            'holdings': holdings,
            'sector_mapping': sector_mapping,
            'stock_returns': stock_returns,  # Added from redundant sources
            'start_date': start_date,
            'end_date': end_date,
            'metrics': metrics or {}
        }
    
    def load_stock_data(self) -> Optional[pd.DataFrame]:
        """Load stock data (returns and features)."""
        features_df = self.load_stock_features()
        if features_df is None:
            return None
        
        # This is a simplified version - would need full integration
        # For now, return features DataFrame
        return features_df


def load_run_data_for_analysis(run_id: str, run_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load all data needed for comprehensive analysis.
    
    Args:
        run_id: Run ID
        run_dir: Optional run directory path
        
    Returns:
        Dictionary with portfolio_data and stock_data
    """
    from src.app.dashboard.utils import get_run_folder
    
    if run_dir is None:
        run_dir = get_run_folder(run_id)
    
    if not run_dir.exists():
        return {
            'portfolio_data': None,
            'stock_data': None,
            'error': f'Run directory not found: {run_dir}'
        }
    
    loader = RunDataLoader(run_dir)
    
    try:
        portfolio_data = loader.load_portfolio_data()
        stock_features = loader.load_stock_features()
        
        # Get stock returns from portfolio_data (may have been loaded from redundant sources)
        stock_returns = portfolio_data.get('stock_returns')
        
        # Convert stock_features to dict format if it's a DataFrame
        if isinstance(stock_features, pd.DataFrame):
            stock_data = {
                'features': stock_features,
                'data': stock_features
            }
            # Add stock returns if available from redundant sources
            if stock_returns is not None:
                stock_data['returns'] = stock_returns
        else:
            stock_data = stock_features or {}
            # Add stock returns if available from redundant sources
            if stock_returns is not None:
                stock_data['returns'] = stock_returns
        
        # Try to fill missing fundamental data from enriched files
        if isinstance(stock_features, pd.DataFrame):
            # Check if we have fundamental columns
            fundamental_cols = ['pe_ratio', 'pb_ratio', 'roe', 'net_margin', 'pe', 'pb']
            has_fundamentals = any(col in stock_features.columns for col in fundamental_cols)
            
            if not has_fundamentals:
                # Try to get from other sources
                enriched_files = list(run_dir.glob("*portfolio_enriched*.csv"))
                for enriched_file in enriched_files:
                    try:
                        df = pd.read_csv(enriched_file)
                        fundamental_cols_found = [col for col in df.columns if any(fc in col.lower() for fc in ['pe', 'pb', 'roe', 'margin'])]
                        if fundamental_cols_found:
                            # Merge fundamental data
                            if 'ticker' in df.columns and 'ticker' in stock_features.columns:
                                stock_features = stock_features.merge(
                                    df[['ticker'] + fundamental_cols_found],
                                    on='ticker',
                                    how='left'
                                )
                                stock_data['features'] = stock_features
                                stock_data['data'] = stock_features
                            break
                    except Exception:
                        continue
        
        return {
            'portfolio_data': portfolio_data,
            'stock_data': stock_data,
            'error': None
        }
    except Exception as e:
        return {
            'portfolio_data': None,
            'stock_data': None,
            'error': str(e)
        }
