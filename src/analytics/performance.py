"""Performance attribution and trade analysis."""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from ..risk.metrics import RiskMetrics


@dataclass
class TradeAnalysis:
    """Analysis of trading performance."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    profit_factor: float = 0.0
    avg_holding_period: float = 0.0
    payoff_ratio: float = 0.0


@dataclass
class PerformanceReport:
    """Comprehensive performance report."""
    # Period info
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    trading_days: int = 0
    
    # Returns
    total_return: float = 0.0
    annualized_return: float = 0.0
    benchmark_return: float = 0.0
    excess_return: float = 0.0
    
    # Risk metrics
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    beta: float = 0.0
    
    # Drawdown
    max_drawdown: float = 0.0
    avg_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    
    # VaR
    var_95: float = 0.0
    cvar_95: float = 0.0
    
    # Trade analysis
    trade_analysis: Optional[TradeAnalysis] = None
    
    # Attribution
    factor_attribution: Dict[str, float] = field(default_factory=dict)


class PerformanceAnalyzer:
    """Analyze trading performance and generate reports."""
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize performance analyzer.
        
        Args:
            risk_free_rate: Annual risk-free rate
        """
        self.risk_free_rate = risk_free_rate
        self.risk_metrics = RiskMetrics(risk_free_rate)
    
    def analyze_trades(self, trades: List[Dict]) -> TradeAnalysis:
        """
        Analyze individual trades.
        
        Args:
            trades: List of trade dictionaries with at least 'pnl' field
                   Optional: 'entry_date', 'exit_date' for holding period
        
        Returns:
            TradeAnalysis with statistics
        """
        if not trades:
            return TradeAnalysis()
        
        df = pd.DataFrame(trades)
        
        if "pnl" not in df.columns:
            return TradeAnalysis()
        
        winning = df[df["pnl"] > 0]
        losing = df[df["pnl"] < 0]
        
        total = len(df)
        win_count = len(winning)
        loss_count = len(losing)
        
        win_rate = (win_count / total * 100) if total > 0 else 0.0
        
        avg_win = float(winning["pnl"].mean()) if len(winning) > 0 else 0.0
        avg_loss = abs(float(losing["pnl"].mean())) if len(losing) > 0 else 0.0
        
        largest_win = float(winning["pnl"].max()) if len(winning) > 0 else 0.0
        largest_loss = abs(float(losing["pnl"].min())) if len(losing) > 0 else 0.0
        
        profit_factor = (
            abs(winning["pnl"].sum() / losing["pnl"].sum())
            if len(losing) > 0 and losing["pnl"].sum() != 0
            else float("inf")
        )
        
        payoff_ratio = avg_win / avg_loss if avg_loss > 0 else float("inf")
        
        # Holding period analysis
        avg_holding = 0.0
        if "entry_date" in df.columns and "exit_date" in df.columns:
            df["entry_date"] = pd.to_datetime(df["entry_date"])
            df["exit_date"] = pd.to_datetime(df["exit_date"])
            df["holding_days"] = (df["exit_date"] - df["entry_date"]).dt.days
            avg_holding = float(df["holding_days"].mean())
        
        return TradeAnalysis(
            total_trades=total,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            profit_factor=profit_factor,
            avg_holding_period=avg_holding,
            payoff_ratio=payoff_ratio,
        )
    
    def calculate_drawdown_metrics(
        self,
        equity_curve: pd.Series
    ) -> Dict[str, float]:
        """
        Calculate detailed drawdown metrics.
        
        Args:
            equity_curve: Series of portfolio values
        
        Returns:
            Dict with drawdown metrics
        """
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve / running_max - 1) * 100
        
        max_dd = abs(drawdown.min())
        avg_dd = abs(drawdown[drawdown < 0].mean()) if len(drawdown[drawdown < 0]) > 0 else 0.0
        
        # Calculate max drawdown duration
        underwater = drawdown < 0
        if underwater.any():
            # Find consecutive underwater periods
            groups = (~underwater).cumsum()
            underwater_periods = underwater.groupby(groups).apply(
                lambda x: len(x) if x.any() else 0
            )
            max_duration = int(underwater_periods.max())
        else:
            max_duration = 0
        
        return {
            "max_drawdown": float(max_dd),
            "avg_drawdown": float(avg_dd),
            "max_drawdown_duration": max_duration,
        }
    
    def generate_report(
        self,
        equity_curve: pd.Series,
        trades: Optional[List[Dict]] = None,
        benchmark: Optional[pd.Series] = None,
        periods_per_year: int = 252
    ) -> PerformanceReport:
        """
        Generate comprehensive performance report.
        
        Args:
            equity_curve: Series of portfolio values
            trades: Optional list of trades for trade analysis
            benchmark: Optional benchmark for comparison
            periods_per_year: Trading periods per year
        
        Returns:
            PerformanceReport with all metrics
        """
        returns = self.risk_metrics.calculate_returns(equity_curve)
        
        # Basic info
        start_date = equity_curve.index[0] if len(equity_curve) > 0 else None
        end_date = equity_curve.index[-1] if len(equity_curve) > 0 else None
        trading_days = len(equity_curve)
        
        # Returns
        total_return = (
            (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100
            if len(equity_curve) > 0
            else 0.0
        )
        annualized_return = float(returns.mean() * periods_per_year * 100) if len(returns) > 0 else 0.0
        
        # Benchmark comparison
        benchmark_return = 0.0
        excess_return = 0.0
        information_ratio = 0.0
        beta = 1.0
        
        if benchmark is not None and len(benchmark) > 0:
            benchmark_return = (benchmark.iloc[-1] / benchmark.iloc[0] - 1) * 100
            excess_return = total_return - benchmark_return
            
            benchmark_returns = self.risk_metrics.calculate_returns(benchmark)
            information_ratio = self.risk_metrics.calculate_information_ratio(
                returns, benchmark_returns, periods_per_year
            )
            beta = self.risk_metrics.calculate_beta(returns, benchmark_returns)
        
        # Risk metrics
        volatility = self.risk_metrics.calculate_volatility(returns, periods_per_year) * 100
        sharpe_ratio = self.risk_metrics.calculate_sharpe_ratio(returns, periods_per_year)
        sortino_ratio = self.risk_metrics.calculate_sortino_ratio(returns, periods_per_year)
        calmar_ratio = self.risk_metrics.calculate_calmar_ratio(returns, equity_curve, periods_per_year)
        
        # Drawdown
        dd_metrics = self.calculate_drawdown_metrics(equity_curve)
        
        # VaR
        var_95 = self.risk_metrics.calculate_var(returns, 0.95) * 100
        cvar_95 = self.risk_metrics.calculate_cvar(returns, 0.95) * 100
        
        # Trade analysis
        trade_analysis = self.analyze_trades(trades) if trades else None
        
        return PerformanceReport(
            start_date=start_date,
            end_date=end_date,
            trading_days=trading_days,
            total_return=float(total_return),
            annualized_return=annualized_return,
            benchmark_return=float(benchmark_return),
            excess_return=float(excess_return),
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            information_ratio=information_ratio,
            beta=beta,
            max_drawdown=dd_metrics["max_drawdown"],
            avg_drawdown=dd_metrics["avg_drawdown"],
            max_drawdown_duration=dd_metrics["max_drawdown_duration"],
            var_95=var_95,
            cvar_95=cvar_95,
            trade_analysis=trade_analysis,
        )
    
    def monthly_breakdown(self, equity_curve: pd.Series) -> pd.DataFrame:
        """
        Calculate monthly performance breakdown.
        
        Args:
            equity_curve: Series of portfolio values
        
        Returns:
            DataFrame with monthly returns and cumulative returns
        """
        monthly = equity_curve.resample("M").last()
        monthly_returns = monthly.pct_change().dropna() * 100
        
        df = pd.DataFrame({
            "month": monthly_returns.index.strftime("%Y-%m"),
            "return_pct": monthly_returns.values,
            "cumulative_pct": ((1 + monthly_returns / 100).cumprod() - 1) * 100,
        })
        
        return df
    
    def yearly_breakdown(self, equity_curve: pd.Series) -> pd.DataFrame:
        """
        Calculate yearly performance breakdown.
        
        Args:
            equity_curve: Series of portfolio values
        
        Returns:
            DataFrame with yearly returns
        """
        yearly = equity_curve.resample("Y").last()
        yearly_returns = yearly.pct_change().dropna() * 100
        
        df = pd.DataFrame({
            "year": yearly_returns.index.year,
            "return_pct": yearly_returns.values,
        })
        
        return df
    
    def compare_strategies(
        self,
        results: Dict[str, pd.Series],
        periods_per_year: int = 252
    ) -> pd.DataFrame:
        """
        Compare multiple strategy equity curves.
        
        Args:
            results: Dict mapping strategy names to equity curves
            periods_per_year: Trading periods per year
        
        Returns:
            DataFrame comparing strategies
        """
        comparison = []
        
        for name, equity_curve in results.items():
            returns = self.risk_metrics.calculate_returns(equity_curve)
            dd = self.calculate_drawdown_metrics(equity_curve)
            
            comparison.append({
                "strategy": name,
                "total_return": (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100,
                "annual_return": returns.mean() * periods_per_year * 100,
                "volatility": self.risk_metrics.calculate_volatility(returns, periods_per_year) * 100,
                "sharpe": self.risk_metrics.calculate_sharpe_ratio(returns, periods_per_year),
                "sortino": self.risk_metrics.calculate_sortino_ratio(returns, periods_per_year),
                "max_drawdown": dd["max_drawdown"],
            })
        
        return pd.DataFrame(comparison)
    
    def format_report_text(self, report: PerformanceReport) -> str:
        """
        Format performance report as text.
        
        Args:
            report: PerformanceReport to format
        
        Returns:
            Formatted text string
        """
        lines = [
            "=" * 60,
            "PERFORMANCE REPORT",
            "=" * 60,
            "",
            f"Period: {report.start_date} to {report.end_date}",
            f"Trading Days: {report.trading_days}",
            "",
            "--- RETURNS ---",
            f"Total Return: {report.total_return:.2f}%",
            f"Annualized Return: {report.annualized_return:.2f}%",
            f"Benchmark Return: {report.benchmark_return:.2f}%",
            f"Excess Return: {report.excess_return:.2f}%",
            "",
            "--- RISK METRICS ---",
            f"Volatility: {report.volatility:.2f}%",
            f"Sharpe Ratio: {report.sharpe_ratio:.2f}",
            f"Sortino Ratio: {report.sortino_ratio:.2f}",
            f"Calmar Ratio: {report.calmar_ratio:.2f}",
            f"Information Ratio: {report.information_ratio:.2f}",
            f"Beta: {report.beta:.2f}",
            "",
            "--- DRAWDOWN ---",
            f"Max Drawdown: {report.max_drawdown:.2f}%",
            f"Avg Drawdown: {report.avg_drawdown:.2f}%",
            f"Max DD Duration: {report.max_drawdown_duration} days",
            "",
            "--- VALUE AT RISK ---",
            f"VaR (95%): {report.var_95:.2f}%",
            f"CVaR (95%): {report.cvar_95:.2f}%",
        ]
        
        if report.trade_analysis:
            ta = report.trade_analysis
            lines.extend([
                "",
                "--- TRADE STATISTICS ---",
                f"Total Trades: {ta.total_trades}",
                f"Win Rate: {ta.win_rate:.1f}%",
                f"Profit Factor: {ta.profit_factor:.2f}",
                f"Avg Win: {ta.avg_win:.2f}",
                f"Avg Loss: {ta.avg_loss:.2f}",
                f"Payoff Ratio: {ta.payoff_ratio:.2f}",
                f"Largest Win: {ta.largest_win:.2f}",
                f"Largest Loss: {ta.largest_loss:.2f}",
            ])
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
