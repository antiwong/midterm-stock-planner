"""Risk metrics calculation and monitoring."""

import numpy as np
import pandas as pd
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class RiskMetricsResult:
    """Container for comprehensive risk metrics."""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    var_95: float
    cvar_95: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float


class RiskMetrics:
    """Calculate and monitor risk metrics for portfolio returns."""
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize risk metrics calculator.
        
        Args:
            risk_free_rate: Annual risk-free rate (default 2%)
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_returns(self, prices: pd.Series) -> pd.Series:
        """
        Calculate returns from price series.
        
        Args:
            prices: Series of prices
        
        Returns:
            Series of returns
        """
        return prices.pct_change().dropna()
    
    def calculate_sharpe_ratio(
        self,
        returns: pd.Series,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sharpe ratio.
        
        Sharpe = (annualized_return - risk_free_rate) / annualized_volatility
        
        Args:
            returns: Series of returns
            periods_per_year: Number of trading periods per year
        
        Returns:
            Sharpe ratio
        """
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        excess_returns = returns - (self.risk_free_rate / periods_per_year)
        sharpe = np.sqrt(periods_per_year) * excess_returns.mean() / returns.std()
        
        return float(sharpe)
    
    def calculate_sortino_ratio(
        self,
        returns: pd.Series,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sortino ratio (uses downside deviation only).
        
        More appropriate than Sharpe when returns are asymmetric.
        
        Args:
            returns: Series of returns
            periods_per_year: Number of trading periods per year
        
        Returns:
            Sortino ratio
        """
        if len(returns) == 0:
            return 0.0
        
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return float("inf") if returns.mean() > 0 else 0.0
        
        downside_std = downside_returns.std()
        excess_returns = returns.mean() - (self.risk_free_rate / periods_per_year)
        sortino = np.sqrt(periods_per_year) * excess_returns / downside_std
        
        return float(sortino)
    
    def calculate_max_drawdown(self, equity_curve: pd.Series) -> Dict[str, float]:
        """
        Calculate maximum drawdown and related metrics.
        
        Args:
            equity_curve: Series of portfolio values over time
        
        Returns:
            Dictionary with max_drawdown, max_drawdown_pct, peak_date, trough_date
        """
        if len(equity_curve) == 0:
            return {
                "max_drawdown": 0.0,
                "max_drawdown_pct": 0.0,
                "peak_date": None,
                "trough_date": None,
            }
        
        running_max = equity_curve.expanding().max()
        drawdown = equity_curve - running_max
        drawdown_pct = (equity_curve / running_max - 1) * 100
        
        max_dd_idx = drawdown.idxmin()
        max_drawdown = abs(drawdown.min())
        max_drawdown_pct = abs(drawdown_pct.min())
        
        return {
            "max_drawdown": float(max_drawdown),
            "max_drawdown_pct": float(max_drawdown_pct),
            "peak_date": running_max.idxmax() if not pd.isna(running_max.idxmax()) else None,
            "trough_date": max_dd_idx,
        }
    
    def calculate_calmar_ratio(
        self,
        returns: pd.Series,
        equity_curve: pd.Series,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Calmar ratio (annualized return / max drawdown).
        
        Higher is better. Measures return relative to drawdown risk.
        
        Args:
            returns: Series of returns
            equity_curve: Series of portfolio values
            periods_per_year: Trading periods per year
        
        Returns:
            Calmar ratio
        """
        if len(returns) == 0:
            return 0.0
        
        annualized_return = returns.mean() * periods_per_year
        dd_info = self.calculate_max_drawdown(equity_curve)
        max_dd_pct = dd_info["max_drawdown_pct"] / 100.0
        
        if max_dd_pct == 0:
            return float("inf") if annualized_return > 0 else 0.0
        
        return float(annualized_return / max_dd_pct)
    
    def calculate_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        method: str = "historical"
    ) -> float:
        """
        Calculate Value at Risk (VaR).
        
        VaR estimates the maximum loss at a given confidence level.
        
        Args:
            returns: Series of returns
            confidence_level: Confidence level (e.g., 0.95 for 95%)
            method: Calculation method ('historical', 'parametric', 'monte_carlo')
        
        Returns:
            VaR (negative value indicating potential loss)
        """
        if len(returns) == 0:
            return 0.0
        
        if method == "historical":
            var = np.percentile(returns, (1 - confidence_level) * 100)
        elif method == "parametric":
            from scipy import stats
            mean_return = returns.mean()
            std_return = returns.std()
            z_score = stats.norm.ppf(1 - confidence_level)
            var = mean_return + (z_score * std_return)
        elif method == "monte_carlo":
            mean_return = returns.mean()
            std_return = returns.std()
            simulated = np.random.normal(mean_return, std_return, 10000)
            var = np.percentile(simulated, (1 - confidence_level) * 100)
        else:
            raise ValueError(f"Unknown VaR method: {method}")
        
        return float(var)
    
    def calculate_cvar(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """
        Calculate Conditional VaR (Expected Shortfall).
        
        CVaR is the expected loss given that the loss exceeds VaR.
        
        Args:
            returns: Series of returns
            confidence_level: Confidence level
        
        Returns:
            CVaR (average loss beyond VaR)
        """
        if len(returns) == 0:
            return 0.0
        
        var = self.calculate_var(returns, confidence_level)
        cvar = returns[returns <= var].mean()
        
        return float(cvar) if not pd.isna(cvar) else float(var)
    
    def calculate_volatility(
        self,
        returns: pd.Series,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate annualized volatility.
        
        Args:
            returns: Series of returns
            periods_per_year: Trading periods per year
        
        Returns:
            Annualized volatility
        """
        if len(returns) == 0:
            return 0.0
        
        return float(returns.std() * np.sqrt(periods_per_year))
    
    def calculate_beta(
        self,
        portfolio_returns: pd.Series,
        market_returns: pd.Series
    ) -> float:
        """
        Calculate beta (market sensitivity).
        
        Beta > 1 = more volatile than market
        Beta < 1 = less volatile than market
        
        Args:
            portfolio_returns: Portfolio returns
            market_returns: Market benchmark returns
        
        Returns:
            Beta value
        """
        if len(portfolio_returns) == 0 or len(market_returns) == 0:
            return 1.0
        
        aligned = pd.DataFrame({
            "portfolio": portfolio_returns,
            "market": market_returns
        }).dropna()
        
        if len(aligned) < 2 or aligned["market"].var() == 0:
            return 1.0
        
        covariance = aligned["portfolio"].cov(aligned["market"])
        market_variance = aligned["market"].var()
        
        return float(covariance / market_variance)
    
    def calculate_information_ratio(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Information Ratio.
        
        IR = (portfolio_return - benchmark_return) / tracking_error
        
        Args:
            portfolio_returns: Portfolio returns
            benchmark_returns: Benchmark returns
            periods_per_year: Trading periods per year
        
        Returns:
            Information ratio
        """
        aligned = pd.DataFrame({
            "portfolio": portfolio_returns,
            "benchmark": benchmark_returns
        }).dropna()
        
        if len(aligned) < 2:
            return 0.0
        
        excess_returns = aligned["portfolio"] - aligned["benchmark"]
        tracking_error = excess_returns.std()
        
        if tracking_error == 0:
            return 0.0
        
        ir = np.sqrt(periods_per_year) * excess_returns.mean() / tracking_error
        return float(ir)
    
    def calculate_all_metrics(
        self,
        equity_curve: pd.Series,
        returns: Optional[pd.Series] = None,
        periods_per_year: int = 252
    ) -> RiskMetricsResult:
        """
        Calculate all risk metrics at once.
        
        Args:
            equity_curve: Series of portfolio values
            returns: Series of returns (calculated if not provided)
            periods_per_year: Trading periods per year
        
        Returns:
            RiskMetricsResult with all metrics
        """
        if returns is None:
            returns = self.calculate_returns(equity_curve)
        
        dd_info = self.calculate_max_drawdown(equity_curve)
        
        # Win/loss stats
        winning = returns[returns > 0]
        losing = returns[returns < 0]
        win_rate = len(winning) / len(returns) * 100 if len(returns) > 0 else 0.0
        avg_win = float(winning.mean()) if len(winning) > 0 else 0.0
        avg_loss = float(abs(losing.mean())) if len(losing) > 0 else 0.0
        
        profit_factor = abs(winning.sum() / losing.sum()) if len(losing) > 0 and losing.sum() != 0 else float("inf")
        
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100 if len(equity_curve) > 0 else 0.0
        
        return RiskMetricsResult(
            total_return=float(total_return),
            annualized_return=float(returns.mean() * periods_per_year * 100) if len(returns) > 0 else 0.0,
            volatility=self.calculate_volatility(returns, periods_per_year) * 100,
            sharpe_ratio=self.calculate_sharpe_ratio(returns, periods_per_year),
            sortino_ratio=self.calculate_sortino_ratio(returns, periods_per_year),
            calmar_ratio=self.calculate_calmar_ratio(returns, equity_curve, periods_per_year),
            max_drawdown=dd_info["max_drawdown"],
            max_drawdown_pct=dd_info["max_drawdown_pct"],
            var_95=self.calculate_var(returns, 0.95) * 100,
            cvar_95=self.calculate_cvar(returns, 0.95) * 100,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win * 100,
            avg_loss=avg_loss * 100,
        )
