"""Chart generation for technical analysis and backtesting."""

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


class ChartGenerator:
    """Generate trading charts with indicators and signals."""
    
    def __init__(
        self,
        chart_dir: str = "charts",
        chart_format: str = "png",
        style: str = "seaborn-v0_8-whitegrid"
    ):
        """
        Initialize chart generator.
        
        Args:
            chart_dir: Directory to save charts
            chart_format: Output format (png, svg, pdf)
            style: Matplotlib style
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib required: pip install matplotlib")
        
        self.chart_dir = Path(chart_dir)
        self.chart_dir.mkdir(parents=True, exist_ok=True)
        self.chart_format = chart_format
        
        try:
            plt.style.use(style)
        except Exception:
            try:
                plt.style.use("seaborn-whitegrid")
            except Exception:
                plt.style.use("default")
    
    def plot_price_with_indicators(
        self,
        df: pd.DataFrame,
        symbol: str,
        show_volume: bool = True,
        show_rsi: bool = True,
        show_macd: bool = True,
        filename: Optional[str] = None
    ) -> str:
        """
        Plot stock price with technical indicators.
        
        Args:
            df: DataFrame with OHLCV data and indicators
            symbol: Stock symbol
            show_volume: Show volume subplot
            show_rsi: Show RSI subplot
            show_macd: Show MACD subplot
            filename: Output filename (auto-generated if None)
        
        Returns:
            Path to saved chart file
        """
        if filename is None:
            filename = f"{symbol}_chart.{self.chart_format}"
        filepath = self.chart_dir / filename
        
        # Determine number of subplots
        n_plots = 1
        if show_volume and "volume" in df.columns:
            n_plots += 1
        if show_rsi and "rsi" in df.columns:
            n_plots += 1
        if show_macd and "macd" in df.columns:
            n_plots += 1
        
        # Create figure
        height_ratios = [3] + [1] * (n_plots - 1)
        fig, axes = plt.subplots(
            n_plots, 1, figsize=(14, 4 + 2 * n_plots),
            sharex=True, gridspec_kw={"height_ratios": height_ratios}
        )
        
        if n_plots == 1:
            axes = [axes]
        
        ax_idx = 0
        ax_price = axes[ax_idx]
        
        # Plot price
        ax_price.plot(df.index, df["close"], label="Close", linewidth=1.5, color="black")
        
        # Plot moving averages if available
        ma_cols = [c for c in df.columns if c.startswith(("ema_", "sma_"))]
        colors = ["#2196F3", "#FF9800", "#4CAF50", "#9C27B0"]
        for i, ma_col in enumerate(ma_cols[:4]):
            ax_price.plot(
                df.index, df[ma_col],
                label=ma_col.upper(), linewidth=1, alpha=0.7,
                color=colors[i % len(colors)]
            )
        
        # Plot Bollinger Bands if available
        if "bb_upper" in df.columns and "bb_lower" in df.columns:
            ax_price.fill_between(
                df.index, df["bb_lower"], df["bb_upper"],
                alpha=0.1, color="gray", label="BB"
            )
        
        ax_price.set_ylabel("Price ($)", fontsize=10)
        ax_price.set_title(f"{symbol} - Price Chart", fontsize=12, fontweight="bold")
        ax_price.legend(loc="upper left", fontsize=8)
        ax_price.grid(True, alpha=0.3)
        
        ax_idx += 1
        
        # Volume subplot
        if show_volume and "volume" in df.columns and ax_idx < len(axes):
            ax_vol = axes[ax_idx]
            colors = ["green" if c >= o else "red" 
                     for c, o in zip(df["close"], df["close"].shift(1))]
            ax_vol.bar(df.index, df["volume"], color=colors, alpha=0.7, width=0.8)
            ax_vol.set_ylabel("Volume", fontsize=10)
            ax_vol.grid(True, alpha=0.3)
            ax_idx += 1
        
        # RSI subplot
        if show_rsi and "rsi" in df.columns and ax_idx < len(axes):
            ax_rsi = axes[ax_idx]
            ax_rsi.plot(df.index, df["rsi"], label="RSI", linewidth=1.5, color="purple")
            ax_rsi.axhline(y=70, color="r", linestyle="--", alpha=0.5, label="Overbought")
            ax_rsi.axhline(y=30, color="g", linestyle="--", alpha=0.5, label="Oversold")
            ax_rsi.fill_between(df.index, 30, 70, alpha=0.1, color="gray")
            ax_rsi.set_ylabel("RSI", fontsize=10)
            ax_rsi.set_ylim(0, 100)
            ax_rsi.legend(loc="upper left", fontsize=8)
            ax_rsi.grid(True, alpha=0.3)
            ax_idx += 1
        
        # MACD subplot
        if show_macd and "macd" in df.columns and ax_idx < len(axes):
            ax_macd = axes[ax_idx]
            ax_macd.plot(df.index, df["macd"], label="MACD", linewidth=1.5, color="blue")
            if "macd_signal" in df.columns:
                ax_macd.plot(
                    df.index, df["macd_signal"],
                    label="Signal", linewidth=1, color="orange"
                )
            if "macd_histogram" in df.columns:
                colors = ["green" if x >= 0 else "red" for x in df["macd_histogram"]]
                ax_macd.bar(
                    df.index, df["macd_histogram"],
                    label="Histogram", alpha=0.3, color=colors, width=0.8
                )
            ax_macd.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
            ax_macd.set_ylabel("MACD", fontsize=10)
            ax_macd.set_xlabel("Date", fontsize=10)
            ax_macd.legend(loc="upper left", fontsize=8)
            ax_macd.grid(True, alpha=0.3)
        
        # Format x-axis
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        axes[-1].xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha="right")
        
        plt.tight_layout()
        plt.savefig(filepath, format=self.chart_format, dpi=150, bbox_inches="tight")
        plt.close()
        
        return str(filepath)
    
    def plot_signals(
        self,
        df: pd.DataFrame,
        symbol: str,
        buy_col: str = "signal",
        buy_val: int = 1,
        sell_val: int = -1,
        filename: Optional[str] = None
    ) -> str:
        """
        Plot price with buy/sell signals.
        
        Args:
            df: DataFrame with price and signal columns
            symbol: Stock symbol
            buy_col: Column name for signals
            buy_val: Value indicating buy signal
            sell_val: Value indicating sell signal
            filename: Output filename
        
        Returns:
            Path to saved chart file
        """
        if filename is None:
            filename = f"{symbol}_signals.{self.chart_format}"
        filepath = self.chart_dir / filename
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Plot price
        ax.plot(df.index, df["close"], label="Close", linewidth=1.5, color="black")
        
        # Plot signals
        if buy_col in df.columns:
            buy_mask = df[buy_col] == buy_val
            sell_mask = df[buy_col] == sell_val
            
            ax.scatter(
                df.index[buy_mask], df["close"][buy_mask],
                marker="^", color="green", s=100, label="Buy", zorder=5
            )
            ax.scatter(
                df.index[sell_mask], df["close"][sell_mask],
                marker="v", color="red", s=100, label="Sell", zorder=5
            )
        
        ax.set_ylabel("Price ($)", fontsize=10)
        ax.set_xlabel("Date", fontsize=10)
        ax.set_title(f"{symbol} - Trading Signals", fontsize=12, fontweight="bold")
        ax.legend(loc="upper left")
        ax.grid(True, alpha=0.3)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
        
        plt.tight_layout()
        plt.savefig(filepath, format=self.chart_format, dpi=150, bbox_inches="tight")
        plt.close()
        
        return str(filepath)
    
    def plot_correlation_heatmap(
        self,
        correlation_matrix: pd.DataFrame,
        title: str = "Correlation Matrix",
        filename: Optional[str] = None
    ) -> str:
        """
        Plot correlation matrix as heatmap.
        
        Args:
            correlation_matrix: Correlation matrix DataFrame
            title: Chart title
            filename: Output filename
        
        Returns:
            Path to saved chart file
        """
        if filename is None:
            filename = f"correlation_heatmap.{self.chart_format}"
        filepath = self.chart_dir / filename
        
        n = len(correlation_matrix)
        fig, ax = plt.subplots(figsize=(max(8, n * 0.5), max(6, n * 0.4)))
        
        # Create heatmap
        im = ax.imshow(correlation_matrix.values, cmap="RdYlGn", vmin=-1, vmax=1)
        
        # Add colorbar
        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.ax.set_ylabel("Correlation", rotation=-90, va="bottom")
        
        # Set ticks
        ax.set_xticks(np.arange(n))
        ax.set_yticks(np.arange(n))
        ax.set_xticklabels(correlation_matrix.columns, fontsize=8)
        ax.set_yticklabels(correlation_matrix.index, fontsize=8)
        
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
        
        # Add correlation values
        for i in range(n):
            for j in range(n):
                val = correlation_matrix.iloc[i, j]
                color = "white" if abs(val) > 0.5 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=7)
        
        ax.set_title(title, fontsize=12, fontweight="bold")
        
        plt.tight_layout()
        plt.savefig(filepath, format=self.chart_format, dpi=150, bbox_inches="tight")
        plt.close()
        
        return str(filepath)
    
    def plot_multiple_stocks(
        self,
        data_dict: Dict[str, pd.DataFrame],
        show_indicators: bool = True
    ) -> List[str]:
        """
        Generate charts for multiple stocks.
        
        Args:
            data_dict: Dict mapping symbols to DataFrames
            show_indicators: Whether to show technical indicators
        
        Returns:
            List of chart file paths
        """
        chart_paths = []
        
        for symbol, df in data_dict.items():
            try:
                path = self.plot_price_with_indicators(
                    df, symbol,
                    show_rsi=show_indicators,
                    show_macd=show_indicators
                )
                chart_paths.append(path)
            except Exception as e:
                print(f"Error generating chart for {symbol}: {e}")
        
        return chart_paths
