# API Documentation

Complete API reference for all analysis modules and core functionality.

## Table of Contents

- [Analysis Modules](#analysis-modules)
- [Data Loading](#data-loading)
- [Database Models](#database-models)
- [Export Functions](#export-functions)
- [Utility Functions](#utility-functions)

---

## Analysis Modules

### Performance Attribution

**Module:** `src/analytics/performance_attribution.py`

Decomposes portfolio returns into factor, sector, stock selection, and timing components.

#### `PerformanceAttributionAnalyzer`

```python
from src.analytics.performance_attribution import PerformanceAttributionAnalyzer

analyzer = PerformanceAttributionAnalyzer()

results = analyzer.analyze(
    portfolio_returns=pd.Series(...),  # Date-indexed portfolio returns
    portfolio_weights=pd.DataFrame(...),  # Date x Ticker weight matrix
    stock_returns=pd.DataFrame(...),  # Date x Ticker return matrix
    factor_returns=pd.DataFrame(...),  # Date x Factor return matrix
    sector_mapping=dict(...)  # Ticker -> Sector mapping
)

# Returns:
{
    'total_attribution': float,
    'by_factor': {
        'market': float,
        'size': float,
        'value': float,
        ...
    },
    'by_sector': {
        'Technology': float,
        'Healthcare': float,
        ...
    },
    'stock_selection': float,
    'timing': float
}
```

**Example:**
```python
import pandas as pd
from src.analytics.performance_attribution import PerformanceAttributionAnalyzer

# Load your data
portfolio_returns = pd.read_csv('portfolio_returns.csv', index_col='date', parse_dates=True)
weights = pd.read_csv('weights.csv', index_col='date', parse_dates=True)
stock_returns = pd.read_csv('stock_returns.csv', index_col='date', parse_dates=True)

analyzer = PerformanceAttributionAnalyzer()
results = analyzer.analyze(
    portfolio_returns=portfolio_returns['return'],
    portfolio_weights=weights,
    stock_returns=stock_returns,
    factor_returns=None,  # Will use default factors
    sector_mapping={'AAPL': 'Technology', 'MSFT': 'Technology', ...}
)

print(f"Total attribution: {results['total_attribution']:.2%}")
print(f"Stock selection: {results['stock_selection']:.2%}")
```

---

### Benchmark Comparison

**Module:** `src/analytics/benchmark_comparison.py`

Compares portfolio performance against market benchmarks (SPY, QQQ).

#### `BenchmarkComparisonAnalyzer`

```python
from src.analytics.benchmark_comparison import BenchmarkComparisonAnalyzer

analyzer = BenchmarkComparisonAnalyzer()

results = analyzer.compare(
    portfolio_returns=pd.Series(...),  # Date-indexed portfolio returns
    benchmark_ticker='SPY',  # or 'QQQ'
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# Returns:
{
    'benchmark': 'SPY',
    'portfolio_return': float,
    'benchmark_return': float,
    'excess_return': float,
    'alpha': float,
    'beta': float,
    'sharpe_ratio': float,
    'tracking_error': float,
    'information_ratio': float,
    'up_capture': float,
    'down_capture': float,
    'max_drawdown': {
        'portfolio': float,
        'benchmark': float
    }
}
```

**Example:**
```python
from src.analytics.benchmark_comparison import BenchmarkComparisonAnalyzer

analyzer = BenchmarkComparisonAnalyzer()
results = analyzer.compare(
    portfolio_returns=portfolio_returns,
    benchmark_ticker='SPY'
)

print(f"Alpha: {results['alpha']:.2%}")
print(f"Beta: {results['beta']:.2f}")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
```

---

### Factor Exposure

**Module:** `src/analytics/factor_exposure.py`

Analyzes portfolio sensitivity to common market factors.

#### `FactorExposureAnalyzer`

```python
from src.analytics.factor_exposure import FactorExposureAnalyzer

analyzer = FactorExposureAnalyzer()

results = analyzer.analyze(
    portfolio_weights=pd.Series(...),  # Ticker -> Weight
    stock_features=pd.DataFrame(...),  # Ticker x Feature matrix
    factor_definitions=None  # Optional custom factor definitions
)

# Returns:
{
    'factor_exposures': [
        {
            'factor_name': 'Value',
            'exposure': float,
            'contribution_to_return': float,
            'contribution_to_risk': float,
            'metrics': {...}
        },
        ...
    ],
    'total_factors': int,
    'portfolio_characteristics': {
        'num_positions': int,
        'concentration': float,
        'effective_n': float
    }
}
```

**Example:**
```python
from src.analytics.factor_exposure import FactorExposureAnalyzer

# Load portfolio weights and stock features
weights = pd.Series({'AAPL': 0.15, 'MSFT': 0.12, ...})
features = pd.DataFrame({
    'pe_ratio': [25.0, 30.0, ...],
    'market_cap': [3e12, 2.5e12, ...],
    ...
}, index=weights.index)

analyzer = FactorExposureAnalyzer()
results = analyzer.analyze(
    portfolio_weights=weights,
    stock_features=features
)

for factor in results['factor_exposures']:
    print(f"{factor['factor_name']}: {factor['exposure']:.2f}")
```

---

### Turnover Analysis

**Module:** `src/analytics/turnover_analysis.py`

Analyzes portfolio turnover, churn rate, and holding periods.

#### `TurnoverAnalyzer`

```python
from src.analytics.turnover_analysis import TurnoverAnalyzer

analyzer = TurnoverAnalyzer()

# Calculate turnover
turnover_results = analyzer.calculate_turnover(
    portfolio_weights=pd.DataFrame(...),  # Date x Ticker weight matrix
    method='sum_of_abs_changes'  # or 'one_way', 'two_way'
)

# Calculate churn rate
churn_results = analyzer.calculate_churn_rate(
    portfolio_weights=pd.DataFrame(...),
    threshold=0.01  # Minimum weight change to count as churn
)

# Analyze holding periods
holding_results = analyzer.analyze_holding_periods(
    portfolio_weights=pd.DataFrame(...),
    min_weight=0.001  # Minimum weight to consider "held"
)

# Position stability
stability_results = analyzer.calculate_position_stability(
    portfolio_weights=pd.DataFrame(...),
    top_n=10  # Number of top positions to track
)
```

**Example:**
```python
from src.analytics.turnover_analysis import TurnoverAnalyzer

analyzer = TurnoverAnalyzer()

# Calculate turnover
turnover = analyzer.calculate_turnover(weights, method='sum_of_abs_changes')
print(f"Average turnover: {turnover['statistics']['mean']:.2%}")
print(f"Annualized turnover: {turnover['statistics']['annualized_turnover']:.2%}")

# Calculate churn
churn = analyzer.calculate_churn_rate(weights, threshold=0.01)
print(f"Mean churn rate: {churn['statistics']['mean_churn_rate']:.2%}")

# Holding periods
holdings = analyzer.analyze_holding_periods(weights)
print(f"Mean holding period: {holdings['statistics']['mean_holding_period_days']:.0f} days")
```

---

### Monte Carlo Simulation

**Module:** `src/analytics/monte_carlo.py`

Performs Monte Carlo simulation for portfolio risk analysis.

#### `MonteCarloSimulator`

```python
from src.analytics.monte_carlo import MonteCarloSimulator

simulator = MonteCarloSimulator()

results = simulator.simulate(
    portfolio_returns=pd.Series(...),  # Historical returns
    num_scenarios=1000,
    time_horizon=252,  # Trading days
    confidence_levels=[0.90, 0.95, 0.99]
)

# Returns:
{
    'scenarios': np.array(...),  # Simulated return paths
    'statistics': {
        'mean_return': float,
        'std_return': float,
        'percentiles': {
            '5th': float,
            '10th': float,
            ...
        }
    },
    'var': {
        '90%': float,
        '95%': float,
        '99%': float
    },
    'cvar': {
        '90%': float,
        '95%': float,
        '99%': float
    }
}
```

**Example:**
```python
from src.analytics.monte_carlo import MonteCarloSimulator

simulator = MonteCarloSimulator()
results = simulator.simulate(
    portfolio_returns=returns,
    num_scenarios=1000,
    time_horizon=252
)

print(f"VaR (95%): {results['var']['95%']:.2%}")
print(f"CVaR (95%): {results['cvar']['95%']:.2%}")
```

---

### Tax Optimization

**Module:** `src/analytics/tax_optimization.py`

Provides tax-loss harvesting suggestions and wash sale detection.

#### `TaxOptimizer`

```python
from src.analytics.tax_optimization import TaxOptimizer

optimizer = TaxOptimizer()

results = optimizer.analyze(
    portfolio_weights=pd.DataFrame(...),
    stock_returns=pd.DataFrame(...),
    current_prices=pd.Series(...),  # Ticker -> Current price
    cost_basis=pd.Series(...)  # Ticker -> Cost basis
)

# Returns:
{
    'tax_loss_harvesting': [
        {
            'ticker': str,
            'unrealized_loss': float,
            'harvest_amount': float,
            'tax_savings': float
        },
        ...
    ],
    'wash_sales': [
        {
            'ticker': str,
            'purchase_date': datetime,
            'sale_date': datetime,
            'days_apart': int
        },
        ...
    ],
    'tax_efficiency_score': float
}
```

---

## Data Loading

### `DataLoader`

**Module:** `src/analytics/data_loader.py`

Loads and merges data from multiple sources.

```python
from src.analytics.data_loader import DataLoader

loader = DataLoader()

# Load all data for a run
data = loader.load_run_data(
    run_id='20260116_235041_5286701f',
    include_fundamentals=True,
    include_benchmark=True
)

# Returns:
{
    'portfolio_returns': pd.Series(...),
    'portfolio_weights': pd.DataFrame(...),
    'stock_returns': pd.DataFrame(...),
    'stock_scores': pd.DataFrame(...),
    'fundamental_data': pd.DataFrame(...),
    'benchmark_data': pd.DataFrame(...),
    'sector_mapping': dict(...)
}
```

**Example:**
```python
from src.analytics.data_loader import DataLoader

loader = DataLoader()
data = loader.load_run_data('20260116_235041_5286701f')

# Access portfolio returns
returns = data['portfolio_returns']

# Access weights
weights = data['portfolio_weights']

# Access stock returns
stock_returns = data['stock_returns']
```

---

## Database Models

### `AnalysisService`

**Module:** `src/analytics/analysis_service.py`

Manages analysis results in the database.

```python
from src.analytics.analysis_service import AnalysisService

service = AnalysisService()

# Save analysis result
service.save_analysis_result(
    run_id='20260116_235041_5286701f',
    analysis_type='performance_attribution',
    results={...}
)

# Get analysis result
result = service.get_analysis_result(
    run_id='20260116_235041_5286701f',
    analysis_type='performance_attribution'
)

# Save AI insight
service.save_ai_insight(
    run_id='20260116_235041_5286701f',
    insight_type='commentary',
    content='...',
    context={...}
)
```

---

## Export Functions

### Export to PDF

**Module:** `src/app/dashboard/export.py`

```python
from src.app.dashboard.export import export_to_pdf

pdf_bytes = export_to_pdf(
    analysis_results={
        'performance_attribution': {...},
        'benchmark_comparison': {...},
        ...
    },
    run_info={
        'run_id': '...',
        'name': '...',
        'created_at': '...',
        'watchlist': '...'
    }
)

# Save to file
with open('report.pdf', 'wb') as f:
    f.write(pdf_bytes)
```

### Export to Excel

```python
from src.app.dashboard.export import export_to_excel

excel_bytes = export_to_excel(
    analysis_results={...},
    run_info={...}
)

# Save to file
with open('report.xlsx', 'wb') as f:
    f.write(excel_bytes)
```

### Export to CSV

```python
from src.app.dashboard.export import export_to_csv
import pandas as pd

df = pd.DataFrame({...})
csv_bytes = export_to_csv(df)

# Save to file
with open('data.csv', 'wb') as f:
    f.write(csv_bytes)
```

### Export to JSON

```python
from src.app.dashboard.export import export_to_json

data = {...}
json_bytes = export_to_json(data, indent=2)

# Save to file
with open('data.json', 'wb') as f:
    f.write(json_bytes)
```

---

## Utility Functions

### Formatting

**Module:** `src/app/dashboard/utils.py`

```python
from src.app.dashboard.utils import (
    format_percent,
    format_number,
    format_currency,
    format_date
)

# Format percentage
format_percent(0.15)  # "+15.00%"
format_percent(0.15, with_sign=False)  # "15.00%"

# Format number
format_number(1234567.89)  # "1,234,567.89"
format_number(1234567.89, decimals=0)  # "1,234,568"

# Format currency
format_currency(1234.56)  # "$1,234.56"
format_currency(1234.56, currency="€")  # "€1,234.56"

# Format date
format_date(datetime.now())  # "2026-01-17 14:30"
format_date(datetime.now(), fmt="%Y-%m-%d")  # "2026-01-17"
```

---

## Error Handling

All analysis modules raise exceptions for invalid inputs:

```python
from src.analytics.performance_attribution import PerformanceAttributionAnalyzer

analyzer = PerformanceAttributionAnalyzer()

try:
    results = analyzer.analyze(...)
except ValueError as e:
    print(f"Invalid input: {e}")
except Exception as e:
    print(f"Analysis failed: {e}")
```

---

## Best Practices

1. **Always validate data** before passing to analyzers
2. **Handle missing data** explicitly (use `fillna()` or drop)
3. **Check data types** (ensure dates are datetime, weights sum to 1.0)
4. **Use appropriate time periods** (ensure sufficient data for analysis)
5. **Cache results** for expensive operations
6. **Handle errors gracefully** with try/except blocks

---

## Additional Resources

- [User Guide](user-guide.md) - Complete user documentation
- [Turnover & Churn Analysis Guide](turnover-churn-analysis-guide.md) - Detailed turnover analysis guide
- [Risk Analysis Guide](risk-analysis-guide.md) - Risk analysis documentation
- [Comprehensive Analysis System](comprehensive-analysis-system.md) - System overview
