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
        """Load individual stock returns."""
        # This would need to be loaded from price data
        # For now, return None - would need integration with data pipeline
        return None
    
    def load_stock_features(self) -> Optional[pd.DataFrame]:
        """Load stock features/scores."""
        # Try portfolio enriched file
        enriched_files = list(self.run_dir.glob("*portfolio_enriched*.csv"))
        if enriched_files:
            latest = max(enriched_files, key=lambda p: p.stat().st_mtime)
            df = pd.read_csv(latest)
            return df
        
        # Try scores from database
        return None
    
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
        
        # Get holdings from weights
        holdings = []
        if weights is not None:
            if isinstance(weights, pd.DataFrame):
                # Get latest weights
                latest_weights = weights.iloc[-1] if len(weights) > 0 else pd.Series()
                holdings = latest_weights[latest_weights > 0].index.tolist()
            else:
                holdings = weights[weights > 0].index.tolist()
        
        return {
            'returns': returns,
            'weights': weights,
            'holdings': holdings,
            'sector_mapping': sector_mapping,
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
        stock_data = loader.load_stock_data()
        
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
