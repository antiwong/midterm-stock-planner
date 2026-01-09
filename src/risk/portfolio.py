"""Portfolio-level risk management: correlation, constraints, stress testing."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class StressTestResult:
    """Result of a single stress test scenario."""
    scenario_name: str
    portfolio_value: float
    pnl: float
    pnl_pct: float
    position_pnl: Dict[str, float]


@dataclass
class CorrelationResult:
    """Result of correlation analysis."""
    correlation_matrix: pd.DataFrame
    avg_correlation: float
    max_correlation: float
    min_correlation: float
    highly_correlated_pairs: List[Tuple[str, str, float]]


class PortfolioRiskManager:
    """Advanced portfolio risk management."""
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize portfolio risk manager.
        
        Args:
            risk_free_rate: Annual risk-free rate
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_correlation_matrix(
        self,
        price_data: Dict[str, pd.DataFrame],
        symbols: Optional[List[str]] = None,
        lookback_days: int = 252
    ) -> CorrelationResult:
        """
        Calculate correlation matrix between positions.
        
        Args:
            price_data: Dict mapping symbols to DataFrames with 'close' column
            symbols: List of symbols to include (default all)
            lookback_days: Number of days for correlation calculation
        
        Returns:
            CorrelationResult with matrix and summary metrics
        """
        if symbols is None:
            symbols = list(price_data.keys())
        
        if len(symbols) < 2:
            return CorrelationResult(
                correlation_matrix=pd.DataFrame(),
                avg_correlation=0.0,
                max_correlation=0.0,
                min_correlation=0.0,
                highly_correlated_pairs=[]
            )
        
        # Extract returns for each symbol
        returns_dict = {}
        for symbol in symbols:
            if symbol in price_data:
                df = price_data[symbol]
                if "close" in df.columns:
                    prices = df["close"].tail(lookback_days)
                    returns = prices.pct_change().dropna()
                    returns_dict[symbol] = returns
        
        if len(returns_dict) < 2:
            return CorrelationResult(
                correlation_matrix=pd.DataFrame(),
                avg_correlation=0.0,
                max_correlation=0.0,
                min_correlation=0.0,
                highly_correlated_pairs=[]
            )
        
        # Align returns by date
        returns_df = pd.DataFrame(returns_dict).dropna()
        
        if len(returns_df) < 20:  # Need minimum data
            return CorrelationResult(
                correlation_matrix=pd.DataFrame(),
                avg_correlation=0.0,
                max_correlation=0.0,
                min_correlation=0.0,
                highly_correlated_pairs=[]
            )
        
        # Calculate correlation matrix
        corr_matrix = returns_df.corr()
        
        # Extract correlation values (excluding diagonal)
        correlations = []
        highly_correlated = []
        for i, sym1 in enumerate(corr_matrix.index):
            for j, sym2 in enumerate(corr_matrix.columns):
                if i < j:  # Upper triangle only
                    corr = corr_matrix.loc[sym1, sym2]
                    if not np.isnan(corr):
                        correlations.append(corr)
                        if abs(corr) > 0.7:
                            highly_correlated.append((sym1, sym2, float(corr)))
        
        return CorrelationResult(
            correlation_matrix=corr_matrix,
            avg_correlation=float(np.mean(correlations)) if correlations else 0.0,
            max_correlation=float(np.max(correlations)) if correlations else 0.0,
            min_correlation=float(np.min(correlations)) if correlations else 0.0,
            highly_correlated_pairs=sorted(highly_correlated, key=lambda x: -abs(x[2]))
        )
    
    def calculate_portfolio_variance(
        self,
        weights: Dict[str, float],
        correlation_matrix: pd.DataFrame,
        volatilities: Dict[str, float]
    ) -> float:
        """
        Calculate portfolio variance using correlation matrix.
        
        σ²_p = Σ Σ w_i * w_j * σ_i * σ_j * ρ_ij
        
        Args:
            weights: Dict mapping symbol to portfolio weight
            correlation_matrix: Correlation matrix DataFrame
            volatilities: Dict mapping symbol to annualized volatility
        
        Returns:
            Portfolio variance
        """
        symbols = [s for s in weights.keys() if s in correlation_matrix.index]
        if len(symbols) < 1:
            return 0.0
        
        variance = 0.0
        for sym1 in symbols:
            for sym2 in symbols:
                w1 = weights.get(sym1, 0)
                w2 = weights.get(sym2, 0)
                vol1 = volatilities.get(sym1, 0)
                vol2 = volatilities.get(sym2, 0)
                corr = correlation_matrix.loc[sym1, sym2] if sym1 in correlation_matrix.index else 0
                
                variance += w1 * w2 * vol1 * vol2 * corr
        
        return float(variance)
    
    def stress_test(
        self,
        positions: Dict[str, int],
        current_prices: Dict[str, float],
        scenarios: List[Dict]
    ) -> List[StressTestResult]:
        """
        Perform stress testing on portfolio.
        
        Args:
            positions: Dict mapping symbols to quantities
            current_prices: Dict mapping symbols to current prices
            scenarios: List of scenario dicts with 'name' and symbol->multiplier mapping
                      Example: {'name': 'Market Crash', 'AAPL': 0.8, 'MSFT': 0.75}
        
        Returns:
            List of StressTestResult for each scenario
        """
        # Current portfolio value
        current_value = sum(
            positions.get(sym, 0) * current_prices.get(sym, 0)
            for sym in positions.keys()
        )
        
        results = []
        
        for scenario in scenarios:
            scenario_name = scenario.get("name", "Unnamed")
            scenario_value = 0.0
            position_pnl = {}
            
            for symbol, quantity in positions.items():
                current_price = current_prices.get(symbol, 0)
                multiplier = scenario.get(symbol, 1.0)  # Default no change
                
                stressed_price = current_price * multiplier
                scenario_value += quantity * stressed_price
                
                pnl = quantity * (stressed_price - current_price)
                position_pnl[symbol] = float(pnl)
            
            total_pnl = scenario_value - current_value
            pnl_pct = (total_pnl / current_value * 100) if current_value > 0 else 0.0
            
            results.append(StressTestResult(
                scenario_name=scenario_name,
                portfolio_value=float(scenario_value),
                pnl=float(total_pnl),
                pnl_pct=float(pnl_pct),
                position_pnl=position_pnl
            ))
        
        return results
    
    @staticmethod
    def default_stress_scenarios() -> List[Dict]:
        """
        Get default stress test scenarios.
        
        Returns common market scenarios for stress testing.
        """
        return [
            {
                "name": "Market Crash (-20%)",
                "default_multiplier": 0.80
            },
            {
                "name": "Moderate Correction (-10%)",
                "default_multiplier": 0.90
            },
            {
                "name": "Tech Selloff",
                "default_multiplier": 0.95,
                "sector_multipliers": {"Technology": 0.75, "Communication Services": 0.80}
            },
            {
                "name": "Recession",
                "default_multiplier": 0.85,
                "sector_multipliers": {"Consumer Discretionary": 0.70, "Financials": 0.75}
            },
            {
                "name": "Interest Rate Spike",
                "default_multiplier": 0.92,
                "sector_multipliers": {"Real Estate": 0.75, "Utilities": 0.80}
            }
        ]
    
    def calculate_sector_exposure(
        self,
        positions: Dict[str, int],
        prices: Dict[str, float],
        sector_map: Dict[str, str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate portfolio exposure by sector.
        
        Args:
            positions: Dict mapping symbols to quantities
            prices: Dict mapping symbols to prices
            sector_map: Dict mapping symbols to sectors
        
        Returns:
            Dict with sector exposures (value and percentage)
        """
        total_value = sum(
            positions.get(sym, 0) * prices.get(sym, 0)
            for sym in positions.keys()
        )
        
        sector_values: Dict[str, float] = {}
        for symbol, quantity in positions.items():
            value = quantity * prices.get(symbol, 0)
            sector = sector_map.get(symbol, "Other")
            sector_values[sector] = sector_values.get(sector, 0) + value
        
        result = {}
        for sector, value in sector_values.items():
            result[sector] = {
                "value": value,
                "weight_pct": (value / total_value * 100) if total_value > 0 else 0.0,
                "num_positions": sum(
                    1 for s in positions.keys()
                    if sector_map.get(s, "Other") == sector and positions[s] > 0
                )
            }
        
        return result
    
    def check_risk_limits(
        self,
        positions: Dict[str, int],
        prices: Dict[str, float],
        total_capital: float,
        limits: Optional[Dict] = None
    ) -> Dict[str, List[str]]:
        """
        Check if portfolio violates risk limits.
        
        Args:
            positions: Dict mapping symbols to quantities
            prices: Dict mapping symbols to prices
            total_capital: Total portfolio capital
            limits: Dict with risk limits (defaults provided)
        
        Returns:
            Dict with 'alerts' and 'warnings' lists
        """
        if limits is None:
            limits = {
                "max_position_pct": 15.0,
                "max_exposure_pct": 100.0,
                "min_positions": 5,
                "max_positions": 30
            }
        
        alerts = []
        warnings = []
        
        # Calculate position values
        total_exposure = 0.0
        position_count = 0
        
        for symbol, quantity in positions.items():
            if quantity > 0:
                value = quantity * prices.get(symbol, 0)
                total_exposure += value
                position_count += 1
                weight_pct = (value / total_capital * 100) if total_capital > 0 else 0
                
                if weight_pct > limits.get("max_position_pct", 15.0):
                    alerts.append(
                        f"{symbol}: Position weight {weight_pct:.1f}% exceeds limit "
                        f"({limits.get('max_position_pct', 15.0)}%)"
                    )
        
        # Total exposure check
        exposure_pct = (total_exposure / total_capital * 100) if total_capital > 0 else 0
        if exposure_pct > limits.get("max_exposure_pct", 100.0):
            warnings.append(
                f"Total exposure {exposure_pct:.1f}% exceeds limit "
                f"({limits.get('max_exposure_pct', 100.0)}%)"
            )
        
        # Position count checks
        if position_count < limits.get("min_positions", 5):
            warnings.append(
                f"Only {position_count} positions, below minimum "
                f"({limits.get('min_positions', 5)})"
            )
        
        if position_count > limits.get("max_positions", 30):
            warnings.append(
                f"{position_count} positions exceeds maximum "
                f"({limits.get('max_positions', 30)})"
            )
        
        return {
            "alerts": alerts,
            "warnings": warnings,
            "status": "ALERT" if alerts else ("WARNING" if warnings else "OK")
        }
    
    def diversification_score(
        self,
        correlation_result: CorrelationResult,
        sector_exposure: Dict[str, Dict]
    ) -> Dict[str, float]:
        """
        Calculate portfolio diversification score.
        
        Args:
            correlation_result: Result from calculate_correlation_matrix
            sector_exposure: Result from calculate_sector_exposure
        
        Returns:
            Dict with diversification metrics
        """
        # Correlation-based score (lower correlation = better)
        corr_score = max(0, 100 - correlation_result.avg_correlation * 100)
        
        # Sector concentration score (more even = better)
        if sector_exposure:
            weights = [s["weight_pct"] for s in sector_exposure.values()]
            # Herfindahl index (sum of squared weights)
            herfindahl = sum(w**2 for w in weights) / 10000  # Normalize
            sector_score = max(0, 100 - herfindahl * 100)
        else:
            sector_score = 0.0
        
        # Overall diversification score
        overall = (corr_score + sector_score) / 2
        
        return {
            "correlation_score": float(corr_score),
            "sector_score": float(sector_score),
            "overall_score": float(overall),
            "num_correlated_pairs": len(correlation_result.highly_correlated_pairs)
        }
