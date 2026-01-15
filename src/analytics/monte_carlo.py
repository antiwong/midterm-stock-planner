"""
Monte Carlo Simulation
======================
Portfolio simulation with probability distributions and confidence intervals.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from scipy import stats


class MonteCarloSimulator:
    """Run Monte Carlo simulations for portfolio analysis."""
    
    def __init__(self, random_seed: Optional[int] = None):
        """
        Initialize Monte Carlo simulator.
        
        Args:
            random_seed: Random seed for reproducibility
        """
        if random_seed is not None:
            np.random.seed(random_seed)
    
    def simulate_portfolio_returns(
        self,
        historical_returns: pd.Series,
        num_simulations: int = 10000,
        time_horizon_days: int = 252,
        method: str = 'bootstrap'
    ) -> Dict[str, Any]:
        """
        Simulate portfolio returns using Monte Carlo.
        
        Args:
            historical_returns: Historical portfolio returns
            num_simulations: Number of simulation runs
            time_horizon_days: Days to simulate forward
            method: Simulation method ('bootstrap', 'normal', 't_distribution')
            
        Returns:
            Dictionary with simulation results
        """
        if len(historical_returns) < 30:
            return {
                'error': 'Insufficient historical data (need at least 30 observations)',
                'num_simulations': 0
            }
        
        # Calculate historical statistics
        mean_return = historical_returns.mean()
        std_return = historical_returns.std()
        skew = historical_returns.skew()
        kurt = historical_returns.kurtosis()
        
        # Run simulations
        simulated_paths = []
        
        for _ in range(num_simulations):
            if method == 'bootstrap':
                # Bootstrap: sample from historical returns
                path = np.random.choice(
                    historical_returns.values,
                    size=time_horizon_days,
                    replace=True
                )
            elif method == 'normal':
                # Normal distribution
                path = np.random.normal(
                    mean_return,
                    std_return,
                    size=time_horizon_days
                )
            elif method == 't_distribution':
                # t-distribution (accounts for fat tails)
                df = max(3, len(historical_returns) - 1)  # Degrees of freedom
                path = stats.t.rvs(
                    df,
                    loc=mean_return,
                    scale=std_return,
                    size=time_horizon_days
                )
            else:
                raise ValueError(f"Unknown method: {method}")
            
            # Calculate cumulative return
            cumulative_return = (1 + pd.Series(path)).prod() - 1
            simulated_paths.append(cumulative_return)
        
        simulated_paths = np.array(simulated_paths)
        
        # Calculate statistics
        results = {
            'method': method,
            'num_simulations': num_simulations,
            'time_horizon_days': time_horizon_days,
            'historical_stats': {
                'mean': float(mean_return),
                'std': float(std_return),
                'skew': float(skew),
                'kurtosis': float(kurt),
                'min': float(historical_returns.min()),
                'max': float(historical_returns.max())
            },
            'simulation_stats': {
                'mean': float(np.mean(simulated_paths)),
                'median': float(np.median(simulated_paths)),
                'std': float(np.std(simulated_paths)),
                'min': float(np.min(simulated_paths)),
                'max': float(np.max(simulated_paths)),
                'percentile_5': float(np.percentile(simulated_paths, 5)),
                'percentile_10': float(np.percentile(simulated_paths, 10)),
                'percentile_25': float(np.percentile(simulated_paths, 25)),
                'percentile_75': float(np.percentile(simulated_paths, 75)),
                'percentile_90': float(np.percentile(simulated_paths, 90)),
                'percentile_95': float(np.percentile(simulated_paths, 95)),
            },
            'confidence_intervals': {
                '90_pct': [
                    float(np.percentile(simulated_paths, 5)),
                    float(np.percentile(simulated_paths, 95))
                ],
                '95_pct': [
                    float(np.percentile(simulated_paths, 2.5)),
                    float(np.percentile(simulated_paths, 97.5))
                ],
                '99_pct': [
                    float(np.percentile(simulated_paths, 0.5)),
                    float(np.percentile(simulated_paths, 99.5))
                ]
            },
            'probability_metrics': {
                'prob_positive_return': float(np.mean(simulated_paths > 0)),
                'prob_negative_return': float(np.mean(simulated_paths < 0)),
                'prob_exceed_10pct': float(np.mean(simulated_paths > 0.10)),
                'prob_exceed_20pct': float(np.mean(simulated_paths > 0.20)),
                'prob_loss_exceed_10pct': float(np.mean(simulated_paths < -0.10)),
                'prob_loss_exceed_20pct': float(np.mean(simulated_paths < -0.20)),
            },
            'value_at_risk': {
                'var_90': float(np.percentile(simulated_paths, 10)),
                'var_95': float(np.percentile(simulated_paths, 5)),
                'var_99': float(np.percentile(simulated_paths, 1)),
            },
            'conditional_var': {
                'cvar_90': float(np.mean(simulated_paths[simulated_paths <= np.percentile(simulated_paths, 10)])),
                'cvar_95': float(np.mean(simulated_paths[simulated_paths <= np.percentile(simulated_paths, 5)])),
                'cvar_99': float(np.mean(simulated_paths[simulated_paths <= np.percentile(simulated_paths, 1)])),
            }
        }
        
        return results
    
    def simulate_portfolio_paths(
        self,
        initial_value: float,
        historical_returns: pd.Series,
        num_simulations: int = 1000,
        time_horizon_days: int = 252,
        method: str = 'bootstrap'
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Simulate full portfolio paths (not just final values).
        
        Args:
            initial_value: Starting portfolio value
            historical_returns: Historical returns
            num_simulations: Number of paths to simulate
            time_horizon_days: Days to simulate
            method: Simulation method
            
        Returns:
            Tuple of (simulated_paths array, statistics dictionary)
        """
        if len(historical_returns) < 30:
            return np.array([]), {'error': 'Insufficient historical data'}
        
        mean_return = historical_returns.mean()
        std_return = historical_returns.std()
        
        paths = []
        
        for _ in range(num_simulations):
            if method == 'bootstrap':
                returns = np.random.choice(
                    historical_returns.values,
                    size=time_horizon_days,
                    replace=True
                )
            elif method == 'normal':
                returns = np.random.normal(mean_return, std_return, size=time_horizon_days)
            else:
                returns = np.random.normal(mean_return, std_return, size=time_horizon_days)
            
            # Calculate cumulative path
            path = initial_value * (1 + pd.Series(returns)).cumprod()
            paths.append(path.values)
        
        paths_array = np.array(paths)
        
        # Calculate path statistics
        stats_dict = {
            'mean_path': paths_array.mean(axis=0).tolist(),
            'median_path': np.median(paths_array, axis=0).tolist(),
            'percentile_5_path': np.percentile(paths_array, 5, axis=0).tolist(),
            'percentile_95_path': np.percentile(paths_array, 95, axis=0).tolist(),
            'final_value_stats': {
                'mean': float(paths_array[:, -1].mean()),
                'median': float(np.median(paths_array[:, -1])),
                'std': float(paths_array[:, -1].std()),
                'min': float(paths_array[:, -1].min()),
                'max': float(paths_array[:, -1].max()),
            }
        }
        
        return paths_array, stats_dict
    
    def stress_test(
        self,
        portfolio_returns: pd.Series,
        portfolio_weights: pd.DataFrame,
        stress_scenarios: List[Dict[str, float]],
        lookback_days: int = 252
    ) -> Dict[str, Any]:
        """
        Stress test portfolio under various scenarios.
        
        Args:
            portfolio_returns: Historical portfolio returns
            portfolio_weights: Current portfolio weights
            stress_scenarios: List of stress scenarios, each with:
                - name: Scenario name
                - market_shock: Market return shock (e.g., -0.20 for -20%)
                - correlation_change: Optional correlation multiplier
            lookback_days: Days of historical data to use
            
        Returns:
            Dictionary with stress test results
        """
        results = {
            'scenarios': [],
            'baseline': {
                'mean_return': float(portfolio_returns.tail(lookback_days).mean()),
                'volatility': float(portfolio_returns.tail(lookback_days).std()),
                'max_drawdown': float(self._calculate_max_drawdown(portfolio_returns.tail(lookback_days)))
            }
        }
        
        for scenario in stress_scenarios:
            scenario_name = scenario.get('name', 'Unknown')
            market_shock = scenario.get('market_shock', 0.0)
            
            # Apply shock to returns
            shocked_returns = portfolio_returns.tail(lookback_days) * (1 + market_shock)
            
            scenario_result = {
                'name': scenario_name,
                'market_shock': float(market_shock),
                'mean_return': float(shocked_returns.mean()),
                'volatility': float(shocked_returns.std()),
                'max_drawdown': float(self._calculate_max_drawdown(shocked_returns)),
                'sharpe_ratio': float(shocked_returns.mean() / shocked_returns.std()) if shocked_returns.std() > 0 else 0.0,
                'impact_vs_baseline': {
                    'return_change': float(shocked_returns.mean() - results['baseline']['mean_return']),
                    'volatility_change': float(shocked_returns.std() - results['baseline']['volatility']),
                    'drawdown_change': float(self._calculate_max_drawdown(shocked_returns) - results['baseline']['max_drawdown'])
                }
            }
            
            results['scenarios'].append(scenario_result)
        
        return results
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown from returns."""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return float(drawdown.min())
