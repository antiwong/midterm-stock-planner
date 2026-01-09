"""Performance visualization for backtesting results."""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class PerformanceVisualizer:
    """Visualize backtest performance and risk metrics."""
    
    def __init__(
        self,
        output_dir: str = "output",
        chart_format: str = "png"
    ):
        """
        Initialize performance visualizer.
        
        Args:
            output_dir: Directory for output files
            chart_format: Chart format (png, svg, pdf)
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib required: pip install matplotlib")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chart_format = chart_format
        
        try:
            plt.style.use("seaborn-v0_8-whitegrid")
        except Exception:
            plt.style.use("default")
    
    def plot_equity_curve(
        self,
        equity_curve: pd.Series,
        benchmark: Optional[pd.Series] = None,
        title: str = "Portfolio Equity Curve",
        filename: Optional[str] = None
    ) -> str:
        """
        Plot portfolio equity curve with optional benchmark comparison.
        
        Args:
            equity_curve: Series of portfolio values
            benchmark: Optional benchmark values for comparison
            title: Chart title
            filename: Output filename
        
        Returns:
            Path to saved chart file
        """
        if filename is None:
            filename = f"equity_curve.{self.chart_format}"
        filepath = self.output_dir / filename
        
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # Normalize to 100 at start
        eq_norm = equity_curve / equity_curve.iloc[0] * 100
        ax.plot(eq_norm.index, eq_norm.values, label="Portfolio", linewidth=2, color="#2196F3")
        
        if benchmark is not None:
            bm_norm = benchmark / benchmark.iloc[0] * 100
            ax.plot(bm_norm.index, bm_norm.values, label="Benchmark", linewidth=1.5, 
                   color="#757575", linestyle="--")
        
        ax.set_ylabel("Value (normalized to 100)", fontsize=10)
        ax.set_xlabel("Date", fontsize=10)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.legend(loc="upper left")
        ax.grid(True, alpha=0.3)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
        
        plt.tight_layout()
        plt.savefig(filepath, format=self.chart_format, dpi=150, bbox_inches="tight")
        plt.close()
        
        return str(filepath)
    
    def plot_drawdown(
        self,
        equity_curve: pd.Series,
        title: str = "Drawdown",
        filename: Optional[str] = None
    ) -> str:
        """
        Plot drawdown over time.
        
        Args:
            equity_curve: Series of portfolio values
            title: Chart title
            filename: Output filename
        
        Returns:
            Path to saved chart file
        """
        if filename is None:
            filename = f"drawdown.{self.chart_format}"
        filepath = self.output_dir / filename
        
        # Calculate drawdown
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve / running_max - 1) * 100
        
        fig, ax = plt.subplots(figsize=(14, 5))
        
        ax.fill_between(drawdown.index, 0, drawdown.values, alpha=0.5, color="#F44336")
        ax.plot(drawdown.index, drawdown.values, linewidth=1, color="#C62828")
        
        ax.set_ylabel("Drawdown (%)", fontsize=10)
        ax.set_xlabel("Date", fontsize=10)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3)
        
        # Add max drawdown annotation
        max_dd = drawdown.min()
        max_dd_date = drawdown.idxmin()
        ax.annotate(
            f"Max DD: {max_dd:.1f}%",
            xy=(max_dd_date, max_dd),
            xytext=(10, 10), textcoords="offset points",
            fontsize=9, color="#C62828",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#C62828")
        )
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
        
        plt.tight_layout()
        plt.savefig(filepath, format=self.chart_format, dpi=150, bbox_inches="tight")
        plt.close()
        
        return str(filepath)
    
    def plot_monthly_returns(
        self,
        returns: pd.Series,
        title: str = "Monthly Returns",
        filename: Optional[str] = None
    ) -> str:
        """
        Plot monthly returns heatmap.
        
        Args:
            returns: Series of daily returns
            title: Chart title
            filename: Output filename
        
        Returns:
            Path to saved chart file
        """
        if filename is None:
            filename = f"monthly_returns.{self.chart_format}"
        filepath = self.output_dir / filename
        
        # Calculate monthly returns
        monthly = (1 + returns).resample("M").prod() - 1
        monthly_df = monthly.to_frame("return")
        monthly_df["year"] = monthly_df.index.year
        monthly_df["month"] = monthly_df.index.month
        
        # Pivot to create heatmap data
        pivot = monthly_df.pivot(index="year", columns="month", values="return")
        pivot = pivot * 100  # Convert to percentage
        
        fig, ax = plt.subplots(figsize=(12, max(4, len(pivot) * 0.5)))
        
        # Create heatmap
        im = ax.imshow(pivot.values, cmap="RdYlGn", aspect="auto", 
                      vmin=-10, vmax=10)
        
        # Add colorbar
        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.ax.set_ylabel("Return (%)", rotation=-90, va="bottom")
        
        # Set ticks
        ax.set_xticks(np.arange(12))
        ax.set_yticks(np.arange(len(pivot)))
        ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        ax.set_yticklabels(pivot.index)
        
        # Add values
        for i in range(len(pivot)):
            for j in range(12):
                val = pivot.iloc[i, j] if j < len(pivot.columns) and not pd.isna(pivot.iloc[i, j]) else None
                if val is not None:
                    color = "white" if abs(val) > 5 else "black"
                    ax.text(j, i, f"{val:.1f}", ha="center", va="center", 
                           color=color, fontsize=8)
        
        ax.set_title(title, fontsize=12, fontweight="bold")
        
        plt.tight_layout()
        plt.savefig(filepath, format=self.chart_format, dpi=150, bbox_inches="tight")
        plt.close()
        
        return str(filepath)
    
    def plot_return_distribution(
        self,
        returns: pd.Series,
        title: str = "Return Distribution",
        filename: Optional[str] = None
    ) -> str:
        """
        Plot histogram of returns with normal distribution overlay.
        
        Args:
            returns: Series of returns
            title: Chart title
            filename: Output filename
        
        Returns:
            Path to saved chart file
        """
        if filename is None:
            filename = f"return_distribution.{self.chart_format}"
        filepath = self.output_dir / filename
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot histogram
        n, bins, patches = ax.hist(
            returns.dropna() * 100, bins=50, density=True,
            alpha=0.7, color="#2196F3", edgecolor="white"
        )
        
        # Overlay normal distribution
        from scipy import stats
        mu, std = returns.mean() * 100, returns.std() * 100
        x = np.linspace(mu - 4*std, mu + 4*std, 100)
        ax.plot(x, stats.norm.pdf(x, mu, std), "r--", linewidth=2, 
               label=f"Normal (μ={mu:.2f}%, σ={std:.2f}%)")
        
        # Add vertical lines for mean and 0
        ax.axvline(x=0, color="black", linestyle="-", linewidth=1, alpha=0.5)
        ax.axvline(x=mu, color="red", linestyle="--", linewidth=1, alpha=0.5)
        
        ax.set_xlabel("Return (%)", fontsize=10)
        ax.set_ylabel("Density", fontsize=10)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(filepath, format=self.chart_format, dpi=150, bbox_inches="tight")
        plt.close()
        
        return str(filepath)
    
    def plot_rolling_metrics(
        self,
        returns: pd.Series,
        window: int = 63,
        title: str = "Rolling Performance Metrics",
        filename: Optional[str] = None
    ) -> str:
        """
        Plot rolling Sharpe ratio and volatility.
        
        Args:
            returns: Series of returns
            window: Rolling window in days
            title: Chart title
            filename: Output filename
        
        Returns:
            Path to saved chart file
        """
        if filename is None:
            filename = f"rolling_metrics.{self.chart_format}"
        filepath = self.output_dir / filename
        
        # Calculate rolling metrics
        rolling_vol = returns.rolling(window).std() * np.sqrt(252) * 100
        rolling_mean = returns.rolling(window).mean() * 252 * 100
        rolling_sharpe = (returns.rolling(window).mean() * np.sqrt(252)) / returns.rolling(window).std()
        
        fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
        
        # Rolling Sharpe
        ax1 = axes[0]
        ax1.plot(rolling_sharpe.index, rolling_sharpe.values, linewidth=1.5, color="#2196F3")
        ax1.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
        ax1.axhline(y=1, color="green", linestyle="--", linewidth=0.5, alpha=0.5)
        ax1.axhline(y=-1, color="red", linestyle="--", linewidth=0.5, alpha=0.5)
        ax1.set_ylabel(f"Rolling {window}d Sharpe", fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_title(title, fontsize=12, fontweight="bold")
        
        # Rolling Volatility
        ax2 = axes[1]
        ax2.fill_between(rolling_vol.index, 0, rolling_vol.values, alpha=0.5, color="#FF9800")
        ax2.plot(rolling_vol.index, rolling_vol.values, linewidth=1, color="#E65100")
        ax2.set_ylabel(f"Rolling {window}d Vol (%)", fontsize=10)
        ax2.set_xlabel("Date", fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha="right")
        
        plt.tight_layout()
        plt.savefig(filepath, format=self.chart_format, dpi=150, bbox_inches="tight")
        plt.close()
        
        return str(filepath)
    
    def generate_performance_report(
        self,
        equity_curve: pd.Series,
        benchmark: Optional[pd.Series] = None,
        returns: Optional[pd.Series] = None
    ) -> Dict[str, str]:
        """
        Generate a complete set of performance charts.
        
        Args:
            equity_curve: Portfolio equity curve
            benchmark: Optional benchmark for comparison
            returns: Daily returns (calculated if not provided)
        
        Returns:
            Dict mapping chart name to file path
        """
        if returns is None:
            returns = equity_curve.pct_change().dropna()
        
        charts = {}
        
        charts["equity_curve"] = self.plot_equity_curve(equity_curve, benchmark)
        charts["drawdown"] = self.plot_drawdown(equity_curve)
        charts["monthly_returns"] = self.plot_monthly_returns(returns)
        charts["return_distribution"] = self.plot_return_distribution(returns)
        charts["rolling_metrics"] = self.plot_rolling_metrics(returns)
        
        return charts
