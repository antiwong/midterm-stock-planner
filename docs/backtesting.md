# Backtesting & Performance Evaluation

> **Part of**: [Mid-term Stock Planner Design](design.md)
> 
> This document covers walk-forward backtesting, performance metrics, and overfitting control.

## Related Documents

- [design.md](design.md) - Main overview and architecture
- [model-training.md](model-training.md) - Model training for each window
- [risk-management.md](risk-management.md) - Risk metrics details
- [visualization-analytics.md](visualization-analytics.md) - Performance visualization

---

## 1. Walk-Forward Framework

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       WALK-FORWARD BACKTEST                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                         TIME ──────────────────────────────────────────────▶
                         
Year:      2015    2016    2017    2018    2019    2020    2021    2022    2023
           │       │       │       │       │       │       │       │       │
           
STEP 1:    ├───────────────────────────────┤
           │      TRAIN (5 years)          │ TEST │
           └───────────────────────────────┴──────┘
                                           2019   2020
                                           
STEP 2:            ├───────────────────────────────┤
                   │      TRAIN (5 years)          │ TEST │
                   └───────────────────────────────┴──────┘
                                                   2020   2021
                                                   
STEP 3:                    ├───────────────────────────────┤
                           │      TRAIN (5 years)          │ TEST │
                           └───────────────────────────────┴──────┘
                                                           2021   2022
                                                           
STEP 4:                            ├───────────────────────────────┤
                                   │      TRAIN (5 years)          │ TEST │
                                   └───────────────────────────────┴──────┘
                                                                   2022   2023
```

### 1.1 Key Principles

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           KEY PRINCIPLES                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ✅ NEVER use future data for training                                      │
│   ✅ Each step: train on past, test on future                                │
│   ✅ Hyperparameter tuning ONLY within training window                       │
│   ✅ Aggregate all test results for final metrics                            │
│   ✅ Include transaction costs in P&L                                        │
│                                                                              │
│   ❌ Don't peek at test data during training                                 │
│   ❌ Don't optimize hyperparams using full backtest results                  │
│   ❌ Don't ignore transaction costs                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Backtest Configuration

### 2.1 BacktestConfig Dataclass

```python
@dataclass
class BacktestConfig:
    """Configuration for walk-forward backtesting."""
    
    # Window settings
    train_years: int = 5              # Training window length
    test_months: int = 12             # Test window length
    step_months: int = 12             # Step size between windows
    
    # Rebalancing
    rebalance_frequency: str = "M"    # Monthly rebalancing
    
    # Portfolio construction
    top_n: int = 10                   # Number of stocks to hold
    max_weight: float = 0.05          # Max single stock weight
    max_sector_weight: float = 0.25   # Max sector weight
    
    # Transaction costs
    commission_bps: float = 5.0       # Commission in basis points
    slippage_bps: float = 3.0         # Slippage in basis points
    
    # Risk controls
    max_turnover: float = 0.30        # Max turnover per rebalance
```

### 2.2 Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `train_years` | 5 | Training window in years |
| `test_months` | 12 | Test window in months |
| `step_months` | 12 | Step between windows |
| `rebalance_frequency` | "M" | Rebalance frequency (M=monthly) |
| `top_n` | 10 | Number of top stocks to hold |
| `max_weight` | 0.05 | Max single stock weight (5%) |
| `max_sector_weight` | 0.25 | Max sector weight (25%) |
| `commission_bps` | 5.0 | Trading commission (bps) |
| `slippage_bps` | 3.0 | Execution slippage (bps) |
| `max_turnover` | 0.30 | Max turnover per rebalance |

---

## 3. Backtest Function

### 3.1 API

```python
# src/backtest/rolling.py

def run_walk_forward_backtest(
    training_data: pd.DataFrame,
    benchmark_data: pd.DataFrame,
    price_data: pd.DataFrame,
    feature_cols: List[str],
    config: BacktestConfig,
    model_config: Optional[ModelConfig] = None
) -> BacktestResults:
    """
    Run walk-forward backtest.
    
    Args:
        training_data: Full training dataset with features and target
        benchmark_data: Benchmark price data
        price_data: Stock price data for returns
        feature_cols: Feature column names
        config: Backtest configuration
        model_config: Model training configuration
    
    Returns:
        BacktestResults with equity curves, metrics, and holdings
    """
```

### 3.2 Backtest Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKTEST FLOW                                        │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────┐
                    │   Initialize        │
                    │   - Set start date  │
                    │   - Initial capital │
                    └──────────┬──────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │     FOR EACH WALK-FORWARD      │◄─────────────┐
              │           WINDOW               │              │
              └────────────────┬───────────────┘              │
                               │                              │
                               ▼                              │
              ┌────────────────────────────────┐              │
              │  1. Get training window data   │              │
              └────────────────┬───────────────┘              │
                               │                              │
                               ▼                              │
              ┌────────────────────────────────┐              │
              │  2. Train model on window      │              │
              │     (See: model-training.md)   │              │
              └────────────────┬───────────────┘              │
                               │                              │
                               ▼                              │
              ┌────────────────────────────────┐              │
              │  3. FOR EACH REBALANCE DATE    │              │
              │     in test window:            │              │
              │     - Score universe           │              │
              │     - Build portfolio (top N)  │              │
              │     - Apply constraints        │              │
              │     - Calculate turnover       │              │
              │     - Deduct costs             │              │
              │     - Track P&L                │              │
              └────────────────┬───────────────┘              │
                               │                              │
                               ▼                              │
              ┌────────────────────────────────┐              │
              │  4. Save window results        │              │
              └────────────────┬───────────────┘              │
                               │                              │
                               ▼                              │
                    ┌─────────────────────┐                   │
                    │   More windows?     │───── YES ─────────┘
                    └──────────┬──────────┘
                               │ NO
                               ▼
              ┌────────────────────────────────┐
              │  5. Aggregate results          │
              │     - Equity curve             │
              │     - Performance metrics      │
              │     - Holdings history         │
              └────────────────┬───────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Return Results     │
                    └─────────────────────┘
```

---

## 4. Transaction Costs & Slippage

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRANSACTION COST MODEL                                    │
└─────────────────────────────────────────────────────────────────────────────┘

                    Trade Execution
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
   ┌────────────┐  ┌────────────┐  ┌────────────┐
   │ Commission │  │  Slippage  │  │  Market    │
   │   (bps)    │  │   (bps)    │  │  Impact    │
   └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
         │               │               │
         │    ┌──────────┘               │
         │    │                          │
         ▼    ▼                          │
   ┌────────────────┐                    │
   │  Total Cost    │◄───────────────────┘
   │  per Trade     │
   │  = comm + slip │
   │  + impact      │
   └────────┬───────┘
            │
            ▼
   ┌────────────────────────────────────┐
   │    P&L_net = P&L_gross - costs     │
   └────────────────────────────────────┘
```

### 4.1 Cost Calculation

```python
def calculate_transaction_costs(
    trade_value: float,
    commission_bps: float = 5.0,
    slippage_bps: float = 3.0
) -> float:
    """
    Calculate transaction costs for a trade.
    
    Example:
        Trade Value: $10,000
        Commission:  5 bps  =  $5
        Slippage:    3 bps  =  $3
        Total Cost:  8 bps  =  $8
    """
    total_bps = commission_bps + slippage_bps
    return trade_value * (total_bps / 10000)
```

### 4.2 Turnover Calculation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TURNOVER CALCULATION                                 │
└─────────────────────────────────────────────────────────────────────────────┘

  Previous Portfolio        New Portfolio           Turnover
  ┌─────────┬───────┐      ┌─────────┬───────┐    
  │ AAPL    │  10%  │      │ AAPL    │  10%  │     0%  (no change)
  │ NVDA    │  10%  │      │ NVDA    │   5%  │     5%  (reduce)
  │ MSFT    │  10%  │      │ MSFT    │  10%  │     0%  (no change)
  │ AMD     │  10%  │      │ AMD     │   0%  │    10%  (exit)
  │ INTC    │  10%  │      │ AMZN    │  10%  │    10%  (new)
  └─────────┴───────┘      └─────────┴───────┘   ─────────
                                                  25% turnover
                                                  
  Turnover = sum(|new_weight - old_weight|) / 2
```

---

## 5. Performance Metrics

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PERFORMANCE METRICS                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│    RETURNS      │      RISK       │   RISK-ADJ.     │   OPERATIONAL   │
├─────────────────┼─────────────────┼─────────────────┼─────────────────┤
│                 │                 │                 │                 │
│ • Total Return  │ • Volatility    │ • Sharpe Ratio  │ • Turnover      │
│ • Ann. Return   │ • Max Drawdown  │ • Sortino Ratio │ • Hit Rate      │
│ • Excess Return │ • VaR (95%)     │ • Calmar Ratio  │ • Avg Holding   │
│ • Alpha         │ • CVaR          │ • Info Ratio    │ • Trade Count   │
│                 │ • Beta          │                 │                 │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

### 5.1 Return Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| Total Return | `(final_value / initial_value) - 1` | Cumulative return |
| Annualized Return | `(1 + total_return)^(252/days) - 1` | Annualized compound return |
| Excess Return | `portfolio_return - benchmark_return` | Alpha over benchmark |
| Alpha | `jensen_alpha` | Risk-adjusted excess return |

### 5.2 Risk Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| Volatility | `std(returns) * sqrt(252)` | Annualized standard deviation |
| Max Drawdown | `max(peak - trough) / peak` | Worst peak-to-trough decline |
| VaR (95%) | `percentile(returns, 5)` | Value at Risk |
| CVaR | `mean(returns < VaR)` | Conditional VaR (Expected Shortfall) |
| Beta | `cov(port, bench) / var(bench)` | Market sensitivity |

> **See Also**: [risk-management.md](risk-management.md) for detailed risk calculations.

### 5.3 Risk-Adjusted Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| Sharpe Ratio | `(return - rf) / volatility` | Return per unit of risk |
| Sortino Ratio | `(return - rf) / downside_dev` | Return per unit of downside risk |
| Calmar Ratio | `annualized_return / max_drawdown` | Return per unit of drawdown |
| Information Ratio | `excess_return / tracking_error` | Alpha per unit of active risk |

### 5.4 Operational Metrics

| Metric | Description |
|--------|-------------|
| Turnover | Average portfolio turnover per rebalance |
| Hit Rate | % of periods where portfolio beats benchmark |
| Avg Holding Period | Average days a stock is held |
| Trade Count | Total number of trades |

---

## 6. BacktestResults

### 6.1 Results Dataclass

```python
@dataclass
class BacktestResults:
    """Results from a walk-forward backtest."""
    
    # Equity curves
    equity_curve: pd.DataFrame        # Daily portfolio values
    benchmark_curve: pd.DataFrame     # Daily benchmark values
    
    # Holdings history
    holdings: pd.DataFrame            # Per-rebalance holdings
    
    # Period returns
    period_returns: pd.DataFrame      # Per-period returns
    
    # Aggregate metrics
    metrics: Dict[str, float]         # Performance metrics
    
    # Per-window results
    window_results: List[WindowResult]
    
    # Configuration
    config: BacktestConfig
```

### 6.2 Output Files

```
runs/{run_id}/
├── config.yaml           # Configuration snapshot
├── summary.json          # Key metrics
├── equity_curve.csv      # Daily portfolio values
├── holdings.csv          # Per-period holdings
├── metrics.csv           # Detailed metrics
└── window_results/       # Per-window details
    ├── window_1.json
    ├── window_2.json
    └── ...
```

---

## 7. Regime Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       REGIME ANALYSIS                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  BULL MARKET          BEAR MARKET         HIGH VOL           LOW VOL        │
│  (SPY > 200d MA)      (SPY < 200d MA)     (VIX > 20)         (VIX < 15)     │
│                                                                              │
│  ┌─────────┐          ┌─────────┐          ┌─────────┐       ┌─────────┐   │
│  │ Return: │          │ Return: │          │ Return: │       │ Return: │   │
│  │  +15%   │          │  -5%    │          │  +8%    │       │  +12%   │   │
│  │ Sharpe: │          │ Sharpe: │          │ Sharpe: │       │ Sharpe: │   │
│  │  1.2    │          │  0.3    │          │  0.6    │       │  1.5    │   │
│  └─────────┘          └─────────┘          └─────────┘       └─────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.1 Regime Classification

```python
def classify_regime(
    benchmark_df: pd.DataFrame,
    vix_df: Optional[pd.DataFrame] = None
) -> pd.Series:
    """
    Classify market regimes.
    
    Regimes:
    - bull: SPY > 200-day MA
    - bear: SPY < 200-day MA
    - high_vol: VIX > 20 (if available)
    - low_vol: VIX < 15 (if available)
    """
```

### 7.2 Regime Performance Split

```python
def analyze_regime_performance(
    results: BacktestResults,
    regime_series: pd.Series
) -> Dict[str, Dict[str, float]]:
    """
    Split performance by regime.
    
    Returns:
        Dict mapping regime name to performance metrics
    """
```

---

## 8. Troubleshooting Backtest Errors

### 8.1 "No predictions generated" Error

If you encounter the error `ValueError: No predictions generated. Check data availability and date ranges.`, the enhanced error message will now provide detailed diagnostics:

```
No predictions generated. Check data availability and date ranges.

Data range: 2015-01-01 to 2023-12-31
Training window: 1825 days (5.0 years)
Test window: 365 days (1.0 years)
Step size: 365 days (1.0 years)
Total windows attempted: 3
Windows skipped: 3

Skipped windows:
  Window 1: Insufficient data (train=0, test=0)
  Window 2: Test window extends beyond available data
  Window 3: Error training model: ...

Possible causes:
  1. Date range too short for walk-forward windows
  2. Training window too long relative to available data
  3. All windows skipped due to insufficient data
  4. Model training failures in all windows
```

### 8.2 Diagnostic Script

Use the diagnostic script to check your data before running a backtest:

```bash
python scripts/diagnose_backtest_data.py
```

This script will:
- ✅ Check data date ranges
- ✅ Validate window size requirements
- ✅ Test training dataset creation
- ✅ Identify date filter issues
- ✅ Provide specific recommendations

**Example Output:**
```
📊 Configuration:
   Training years: 5.0
   Test years: 1.0
   Step years: 1.0

📅 Date Ranges:
   Price data: 2015-01-01 to 2023-12-31 (8.9 years)
   Benchmark data: 2015-01-01 to 2023-12-31 (8.9 years)

📏 Window Requirements:
   Training window: 5.0 years
   Test window: 1.0 years
   Minimum data needed: 6.0 years
   ✅ Data span (8.9 years) is sufficient
```

### 8.3 Common Solutions

| Issue | Solution |
|-------|----------|
| **Data range too short** | Reduce `train_years` in config.yaml (e.g., 5.0 → 3.0) |
| **All windows skipped** | Check date filters (`start_date`/`end_date` in config) |
| **Training failures** | Verify feature data quality and model config |
| **Insufficient test data** | Reduce `test_years` (e.g., 1.0 → 0.5) |

### 8.4 Quick Fixes

**Reduce window sizes:**
```yaml
backtest:
  train_years: 3.0  # Reduce from 5.0
  test_years: 0.5   # Reduce from 1.0
```

**Remove date filters:**
```yaml
backtest:
  start_date: null  # Remove if set
  end_date: null    # Remove if set
```

**Download more historical data:**
```bash
python scripts/download_prices.py --watchlist your_watchlist --start-date 2010-01-01
```

---

## 9. Overfitting Control

### 8.1 Signs of Overfitting

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OVERFITTING WARNING SIGNS                            │
└─────────────────────────────────────────────────────────────────────────────┘

  ⚠️  Train performance >> Test performance
  ⚠️  Performance degrades in recent periods
  ⚠️  High sensitivity to hyperparameters
  ⚠️  Strategy works only in specific market regime
  ⚠️  Very high turnover
  ⚠️  Concentrated in few features
```

### 8.2 Mitigation Strategies

| Strategy | Implementation |
|----------|----------------|
| **Walk-forward validation** | Never use future data for training |
| **Out-of-sample testing** | Reserve final period for true OOS test |
| **Regularization** | Use L1/L2 in model (reg_alpha, reg_lambda) |
| **Feature selection** | Use economically motivated features only |
| **Ensemble** | Average multiple model configurations |
| **Simplicity** | Prefer simpler models with fewer features |

---

## 10. Usage Example

```python
from src.backtest.rolling import run_walk_forward_backtest, BacktestConfig
from src.data.loader import load_price_data, load_benchmark_data
from src.features.engineering import compute_all_features, make_training_dataset

# Load data
price_df = load_price_data("data/prices.csv")
benchmark_df = load_benchmark_data("data/benchmark.csv")
fundamental_df = load_fundamental_data("data/fundamentals.csv")

# Prepare training data
feature_df = compute_all_features(price_df, fundamental_df, config)
training_data = make_training_dataset(feature_df, benchmark_df)

# Configure backtest
backtest_config = BacktestConfig(
    train_years=5,
    test_months=12,
    top_n=10,
    commission_bps=5,
    slippage_bps=3
)

# Run backtest
results = run_walk_forward_backtest(
    training_data=training_data,
    benchmark_data=benchmark_df,
    price_data=price_df,
    feature_cols=feature_cols,
    config=backtest_config
)

# View results
print(f"Sharpe Ratio: {results.metrics['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results.metrics['max_drawdown']:.2%}")
print(f"Annual Return: {results.metrics['annual_return']:.2%}")
```

---

## Related Documents

- **Previous**: [model-training.md](model-training.md) - Model training details
- **Risk Metrics**: [risk-management.md](risk-management.md) - Detailed risk calculations
- **Visualization**: [visualization-analytics.md](visualization-analytics.md) - Performance charts
- **Diagnostics**: `scripts/diagnose_backtest_data.py` - Backtest data diagnostic tool
- **Back to**: [design.md](design.md) - Main overview
