# Visualization & Analytics

> [← Back to Documentation Index](README.md)
> **Part of**: [Mid-term Stock Planner Design](design.md)
> 
> This document covers charts, performance visualization, and analytics reporting.

## Related Documents

- [design.md](design.md) - Main overview and architecture
- [backtesting.md](backtesting.md) - Performance data source
- [risk-management.md](risk-management.md) - Risk metrics to visualize
- [explainability.md](explainability.md) - SHAP visualization

---

## 1. Visualization Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VISUALIZATION TYPES                                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│  PRICE CHARTS   │  PERFORMANCE    │  RISK CHARTS    │  ANALYTICS      │
├─────────────────┼─────────────────┼─────────────────┼─────────────────┤
│ • Candlesticks  │ • Equity Curve  │ • Drawdown      │ • Return Dist   │
│ • With Overlays │ • vs Benchmark  │ • Rolling Vol   │ • Monthly Heat  │
│ • Tech Indic.   │ • Cumulative    │ • VaR Chart     │ • Trade Stats   │
│ • Trading Sigs  │                 │ • Correlation   │ • SHAP Plots    │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

---

## 2. Price Charts

### 2.1 Price with Technical Indicators

```python
# src/visualization/charts.py

def plot_price_with_indicators(
    df: pd.DataFrame,
    ticker: str,
    indicators: List[str] = ["ema_20", "ema_50", "bb_upper", "bb_lower"],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Plot price chart with technical indicator overlays.
    
    Args:
        df: DataFrame with OHLCV and indicators
        ticker: Stock ticker to plot
        indicators: List of indicator columns to overlay
        start_date: Optional start date filter
        end_date: Optional end date filter
        save_path: Optional path to save figure
    
    Returns:
        matplotlib Figure
    """
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  NVDA - Price with Indicators                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  180 ┤                              ╭────╮                                   │
│      │                             ╱      ╲                                  │
│  160 ┤                  ╭─────────╱        ╲                                │
│      │    ──────────────┤  EMA 50            ╲                              │
│  140 ┤   ╱              │                     ╲                             │
│      │  ╱    ┌─────BB Upper─────┐              ╲                            │
│  120 ┤─╱─────┤                  │───────────────╲                           │
│      │       │     PRICE        │                                           │
│  100 ┤       │                  │                                            │
│      │       └─────BB Lower─────┘                                            │
│   80 ┤                                                                       │
│      └──────────────────────────────────────────────────────────────────────│
│        Jan    Feb    Mar    Apr    May    Jun    Jul    Aug    Sep          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Trading Signals

```python
def plot_trading_signals(
    df: pd.DataFrame,
    ticker: str,
    buy_dates: List[str],
    sell_dates: List[str],
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Plot price with buy/sell signal markers.
    """
```

---

## 3. Performance Charts

### 3.1 Equity Curve

```python
# src/visualization/performance.py

def plot_equity_curve(
    portfolio_values: pd.Series,
    benchmark_values: Optional[pd.Series] = None,
    title: str = "Portfolio Performance",
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Plot equity curve with optional benchmark comparison.
    """
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Portfolio Performance vs Benchmark                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  160% ┤                                         ╭──── Portfolio             │
│       │                                        ╱                            │
│  140% ┤                              ╭────────╱                             │
│       │                             ╱      ╱──── Benchmark                  │
│  120% ┤                    ╭───────╱      ╱                                 │
│       │           ╭───────╱             ╱                                   │
│  100% ┤──────────╱─────────────────────╱─────────────────────────────────── │
│       │                                                                      │
│   80% ┤                                                                      │
│       └──────────────────────────────────────────────────────────────────────│
│         2020      2021      2022      2023      2024                        │
│                                                                              │
│  Sharpe: 1.25    Max DD: -12%    Ann. Return: +15%                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Drawdown Chart

```python
def plot_drawdown(
    portfolio_values: pd.Series,
    title: str = "Portfolio Drawdown",
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Plot drawdown chart showing underwater curve.
    """
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Portfolio Drawdown                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│    0% ┤─────────────────────╮          ╭───────────────────────────────────│
│       │                      ╲        ╱                                      │
│   -5% ┤                       ╲      ╱                                       │
│       │                        ╲    ╱                                        │
│  -10% ┤                         ╲  ╱                                         │
│       │                          ╲╱                                          │
│  -15% ┤                          ↓ Max DD: -12%                              │
│       └──────────────────────────────────────────────────────────────────────│
│         2020      2021      2022      2023      2024                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Monthly Returns Heatmap

```python
def plot_monthly_returns_heatmap(
    returns: pd.Series,
    title: str = "Monthly Returns",
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Plot heatmap of monthly returns by year.
    """
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Monthly Returns Heatmap                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│        Jan   Feb   Mar   Apr   May   Jun   Jul   Aug   Sep   Oct   Nov  Dec │
│  2024  2.1% -0.5%  3.2%  1.8% -1.2%  4.5%                                   │
│  2023  1.5%  2.8% -2.1%  0.9%  3.4%  2.1%  1.2% -0.8%  1.5%  2.2%  3.1% 1.8%│
│  2022 -3.2%  1.2%  0.8% -4.5%  2.1% -1.8%  3.2%  1.5% -2.1%  0.5%  2.8% 1.2%│
│  2021  4.5%  2.1%  1.8%  3.2%  0.5%  1.2%  2.8% -0.5%  1.5%  4.2%  1.8% 2.5%│
│                                                                              │
│  Color: ████ Positive (green)  ████ Negative (red)                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Return Distribution

```python
def plot_return_distribution(
    returns: pd.Series,
    title: str = "Return Distribution",
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Plot histogram of returns with normal distribution overlay.
    """
```

---

## 4. Risk Charts

### 4.1 Rolling Metrics

```python
def plot_rolling_metrics(
    returns: pd.Series,
    window: int = 252,
    metrics: List[str] = ["sharpe", "volatility"],
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Plot rolling risk metrics over time.
    """
```

### 4.2 Correlation Heatmap

```python
def plot_correlation_heatmap(
    returns_df: pd.DataFrame,
    title: str = "Stock Correlations",
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Plot correlation matrix as heatmap.
    """
```

---

## 5. Analytics

### 5.1 Trade Analysis

```python
# src/analytics/performance.py

def analyze_trades(
    trades: pd.DataFrame
) -> Dict[str, Any]:
    """
    Analyze trade-by-trade performance.
    
    Returns:
        Dict with:
        - total_trades: Number of trades
        - winning_trades: Number of winners
        - losing_trades: Number of losers
        - win_rate: Win percentage
        - avg_win: Average winning trade
        - avg_loss: Average losing trade
        - profit_factor: Gross profit / Gross loss
        - largest_win: Best trade
        - largest_loss: Worst trade
        - avg_holding_period: Average days held
    """
```

### 5.2 Performance Report

```python
def generate_performance_report(
    results: BacktestResults
) -> Dict[str, Any]:
    """
    Generate comprehensive performance report.
    
    Returns:
        Dict with:
        - summary: Key metrics
        - returns: Return statistics
        - risk: Risk statistics
        - monthly: Monthly breakdown
        - yearly: Yearly breakdown
        - trades: Trade analysis
    """
```

### 5.3 Report Output

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PERFORMANCE REPORT                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SUMMARY                                                                     │
│  ───────────────────────────────────────────────────────────────            │
│  Total Return:        +45.2%          Sharpe Ratio:       1.25              │
│  Annualized Return:   +15.1%          Sortino Ratio:      1.85              │
│  Annualized Vol:      12.0%           Calmar Ratio:       1.26              │
│  Max Drawdown:        -12.0%          Information Ratio:  0.95              │
│                                                                              │
│  TRADE STATISTICS                                                            │
│  ───────────────────────────────────────────────────────────────            │
│  Total Trades:        156             Win Rate:           58.3%             │
│  Avg Win:             +2.8%           Avg Loss:           -1.5%             │
│  Profit Factor:       1.85            Avg Holding:        21 days           │
│  Largest Win:         +12.5%          Largest Loss:       -6.2%             │
│                                                                              │
│  YEARLY BREAKDOWN                                                            │
│  ───────────────────────────────────────────────────────────────            │
│  Year     Return    Sharpe    Max DD    vs Bench                            │
│  2024     +8.5%     1.45      -5.2%     +3.2%                               │
│  2023     +18.2%    1.35      -8.1%     +4.8%                               │
│  2022     +2.1%     0.45      -12.0%    +8.5%                               │
│  2021     +22.5%    1.65      -6.5%     +5.2%                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.4 Strategy Comparison

```python
def compare_strategy_results(
    results_list: List[BacktestResults],
    names: List[str]
) -> pd.DataFrame:
    """
    Compare multiple strategy results side by side.
    
    Returns:
        DataFrame with metrics as rows, strategies as columns
    """
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STRATEGY COMPARISON                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Metric              Strategy A    Strategy B    Strategy C    Benchmark    │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Ann. Return         +15.2%        +12.8%        +18.5%        +10.2%       │
│  Volatility          12.5%         10.2%         16.8%         15.0%        │
│  Sharpe Ratio        1.22          1.25          1.10          0.68         │
│  Max Drawdown        -12.5%        -8.2%         -18.5%        -25.0%       │
│  Win Rate            58%           62%           55%           -            │
│  Turnover            35%           25%           45%           -            │
│                                                                              │
│  Best: Strategy B (highest Sharpe with lowest drawdown)                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. SHAP Visualization

See [explainability.md](explainability.md) for detailed SHAP plots:

- Summary plots (beeswarm, bar)
- Waterfall plots (single prediction)
- Force plots (compact contribution view)
- Dependence plots (feature interactions)

---

## 7. Chart Generation API

```python
# src/visualization/charts.py

class ChartGenerator:
    """Unified chart generation interface."""
    
    def __init__(self, style: str = "default", figsize: Tuple[int, int] = (12, 6)):
        self.style = style
        self.figsize = figsize
    
    def price_chart(self, df, ticker, **kwargs) -> plt.Figure:
        """Generate price chart."""
        
    def equity_curve(self, values, benchmark=None, **kwargs) -> plt.Figure:
        """Generate equity curve."""
        
    def drawdown(self, values, **kwargs) -> plt.Figure:
        """Generate drawdown chart."""
        
    def monthly_heatmap(self, returns, **kwargs) -> plt.Figure:
        """Generate monthly returns heatmap."""
        
    def correlation(self, returns_df, **kwargs) -> plt.Figure:
        """Generate correlation heatmap."""
        
    def save_all(self, output_dir: Path):
        """Save all generated charts to directory."""
```

---

## 8. Usage Examples

```python
from src.visualization.charts import ChartGenerator
from src.visualization.performance import plot_equity_curve, plot_drawdown
from src.analytics.performance import generate_performance_report

# Initialize chart generator
charts = ChartGenerator(figsize=(14, 8))

# Generate price chart
fig = charts.price_chart(
    df, 
    ticker="NVDA", 
    indicators=["ema_20", "ema_50", "bb_upper", "bb_lower"]
)
fig.savefig("output/nvda_chart.png")

# Generate equity curve
plot_equity_curve(
    portfolio_values=results.equity_curve,
    benchmark_values=results.benchmark_curve,
    save_path=Path("output/equity_curve.png")
)

# Generate performance report
report = generate_performance_report(results)
print(format_report_to_text(report))
```

---

## Related Documents

- **Back to**: [design.md](design.md) - Main overview
- **Data Source**: [backtesting.md](backtesting.md) - Backtest results
- **Risk Charts**: [risk-management.md](risk-management.md) - Risk metrics
- **SHAP Plots**: [explainability.md](explainability.md) - Model explanations
