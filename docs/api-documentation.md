# API Documentation

> [← Back to Documentation Index](README.md)

Complete API reference for all analysis modules and core functionality (v3.11.2).

## Table of Contents

- [Model Training & Prediction](#model-training--prediction)
- [Backtesting](#backtesting)
- [Risk Metrics](#risk-metrics)
- [Position Sizing](#position-sizing)
- [Trading (Alpaca Broker)](#trading-alpaca-broker)
- [Analysis Modules](#analysis-modules)
- [Report Templates](#report-templates)
- [Data Loading](#data-loading)
- [Database Models](#database-models)
- [Export Functions](#export-functions)
- [Performance Utilities](#performance-utilities)
- [Utility Functions](#utility-functions)

---

## Model Training & Prediction

### Trainer

**Module:** `src/models/trainer.py`

| Function | Signature | Returns |
|----------|-----------|---------|
| `train_lgbm_regressor` | `train_lgbm_regressor(data: pd.DataFrame, feature_cols: List[str], config: Optional[ModelConfig] = None)` | `Tuple[LGBMRegressor, pd.DataFrame, pd.DataFrame, Dict[str, float]]` — (model, X_train, X_valid, metrics) |
| `save_model` | `save_model(model: LGBMRegressor, feature_names: List[str], config: ModelConfig, metrics: Dict[str, float], base_dir: str = "models", model_id: Optional[str] = None, data_info: Optional[Dict[str, Any]] = None)` | `str` — path to saved model directory |
| `load_model` | `load_model(model_dir: str)` | `Tuple[LGBMRegressor, ModelMetadata]` — (model, metadata) |

**`train_lgbm_regressor`** trains a LightGBM regressor with train/validation split. Returns the trained model, train/validation DataFrames, and validation metrics (MSE, RMSE, MAE, sample counts). Uses early stopping via callbacks when configured.

**`save_model`** persists a trained model to `{base_dir}/{model_id}/` containing `model.txt` (native LightGBM format) and `metadata.json` (feature names, config, training date, performance metrics).

**`load_model`** loads a previously saved model and its metadata from a directory path.

### Predictor

**Module:** `src/models/predictor.py`

| Function | Signature | Returns |
|----------|-----------|---------|
| `predict` | `predict(model, feature_df: pd.DataFrame, feature_names: List[str], metadata: Optional[ModelMetadata] = None, include_rankings: bool = True)` | `pd.DataFrame` with columns: `date`, `ticker`, `score`, `rank`, `percentile` |
| `get_top_stocks` | `get_top_stocks(predictions: pd.DataFrame, n: Optional[int] = None, top_pct: Optional[float] = None)` | `pd.DataFrame` — filtered to top-ranked stocks |

**`predict`** generates model predictions for a feature DataFrame. Validates features against metadata when provided, fills missing features with 0, and optionally computes cross-sectional rank and percentile within each date.

**`get_top_stocks`** filters predictions to the top N stocks or top percentage (default: top 10% decile) per date.

---

## Backtesting

### Walk-Forward Backtest

**Module:** `src/backtest/rolling.py`

| Function | Signature | Returns |
|----------|-----------|---------|
| `run_walk_forward_backtest` | `run_walk_forward_backtest(training_data: pd.DataFrame, benchmark_data: pd.DataFrame, price_data: pd.DataFrame, feature_cols: List[str], config: Optional[BacktestConfig] = None, model_config: Optional[ModelConfig] = None, verbose: bool = True, compute_shap: bool = False)` | `BacktestResults` |

Runs a rolling walk-forward backtest. For each window: trains a LightGBM model on the train split, predicts on the test split, selects top-N stocks, and computes portfolio returns vs benchmark. Set `compute_shap=True` to calculate TreeSHAP feature attributions per window (adds ~15 min).

---

## Risk Metrics

### RiskMetrics

**Module:** `src/risk/metrics.py`

```python
from src.risk.metrics import RiskMetrics
rm = RiskMetrics(risk_free_rate=0.02)
```

| Method | Signature | Returns |
|--------|-----------|---------|
| `calculate_sharpe_ratio` | `(returns: pd.Series, periods_per_year: int = 252)` | `float` |
| `calculate_sortino_ratio` | `(returns: pd.Series, periods_per_year: int = 252)` | `float` |
| `calculate_max_drawdown` | `(equity_curve: pd.Series)` | `Dict[str, float]` — keys: `max_drawdown`, `max_drawdown_pct`, `peak_date`, `trough_date` |
| `calculate_var` | `(returns: pd.Series, confidence_level: float = 0.95, method: str = "historical")` | `float` — VaR (negative value) |
| `calculate_cvar` | `(returns: pd.Series, confidence_level: float = 0.95)` | `float` — average loss beyond VaR |
| `calculate_beta` | `(portfolio_returns: pd.Series, market_returns: pd.Series)` | `float` |
| `calculate_information_ratio` | `(portfolio_returns: pd.Series, benchmark_returns: pd.Series, periods_per_year: int = 252)` | `float` |
| `calculate_all_metrics` | `(equity_curve: pd.Series, returns: Optional[pd.Series] = None, periods_per_year: int = 252)` | `RiskMetricsResult` |

`calculate_all_metrics` is a convenience method that computes all risk metrics at once and returns a `RiskMetricsResult` dataclass containing total return, annualized return, volatility, Sharpe, Sortino, max drawdown, VaR, and CVaR.

---

## Position Sizing

### PositionSizer

**Module:** `src/risk/position_sizing.py`

```python
from src.risk.position_sizing import PositionSizer
sizer = PositionSizer(capital=100000.0)
```

| Method | Signature | Returns |
|--------|-----------|---------|
| `equal_weight` | `(symbols: List[str], prices: Dict[str, float], max_positions: Optional[int] = None)` | `List[PositionSizeResult]` |
| `volatility_weighted` | `(symbols: List[str], prices: Dict[str, float], volatilities: Dict[str, float], target_volatility: float = 0.15)` | `List[PositionSizeResult]` |
| `score_weighted` | `(symbols: List[str], prices: Dict[str, float], scores: Dict[str, float], min_weight: float = 0.02, max_weight: float = 0.15)` | `List[PositionSizeResult]` |

Each method returns a list of `PositionSizeResult` objects with fields: `symbol`, `shares`, `position_value`, `weight_pct`, `method`.

- **`equal_weight`**: Allocates equal capital (1/N) to each position.
- **`volatility_weighted`**: Inverse-volatility weighting — lower-volatility stocks receive larger allocations.
- **`score_weighted`**: Allocates proportionally to model scores, clamped to `[min_weight, max_weight]`.

---

## Trading (Alpaca Broker)

### AlpacaBroker

**Module:** `src/trading/alpaca_broker.py`

```python
from src.trading.alpaca_broker import AlpacaBroker
broker = AlpacaBroker(api_key="...", secret_key="...", paper=True)
```

| Method | Signature | Returns |
|--------|-----------|---------|
| `get_account` | `()` | `dict` — account summary (equity, cash, buying_power, etc.) |
| `get_positions` | `()` | `List[dict]` — all open positions |
| `submit_order` | `(symbol: str, qty: float, side: str, type: str = "market", time_in_force: str = "day", limit_price: Optional[float] = None)` | `dict` — order confirmation |
| `submit_market_order` | `(symbol: str, notional: Optional[float] = None, qty: Optional[float] = None, side: str = "buy")` | `dict` — order confirmation |
| `close_position` | `(symbol: str)` | `dict` — close order confirmation |
| `close_all_positions` | `()` | `List[dict]` — list of close order confirmations |

All public methods return plain dicts/lists (never raw SDK objects) for easy JSON serialization. Requires `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` environment variables, or pass keys directly to the constructor.

- **`submit_order`**: Generic order submission supporting market and limit order types with configurable time-in-force.
- **`submit_market_order`**: Convenience method for market orders by dollar amount (`notional`) or share count (`qty`). Exactly one must be provided.

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

## Report Templates

**Module:** `src/analytics/report_templates.py`

Manages report template definitions, generation, and batch processing.

### `ReportTemplateEngine`

```python
from src.analytics.report_templates import ReportTemplateEngine

engine = ReportTemplateEngine(db_path="data/analysis.db")

# Create a template
template = engine.create_template(
    name="Monthly Portfolio Report",
    format="pdf",  # "pdf", "excel", "csv", "json"
    sections=[
        {"name": "executive_summary", "enabled": True},
        {"name": "performance_metrics", "enabled": True},
        {"name": "portfolio_composition", "enabled": True},
        {"name": "risk_analysis", "enabled": True},
        {"name": "recommendations", "enabled": True}
    ],
    description="Standard monthly report",
    created_by="user"
)

# Generate a single report
report = engine.generate_report(
    template_id=template.id,
    run_id="20260116_235041_5286701f",
    output_path="output/reports/",
    parallel=True  # Fetch analyses in parallel
)

# Generate reports for multiple runs in parallel
reports = engine.generate_reports_batch(
    template_id=template.id,
    run_ids=["run1", "run2", "run3"],
    output_dir="output/reports/",
    parallel=True,
    max_workers=4
)

# List and manage templates
templates = engine.get_templates(enabled_only=True)
engine.update_template(template.id, name="Updated Name")
engine.delete_template(template.id)

# View report history
history = engine.get_report_history(template_id=1, limit=50)
```

### `ReportFormat`

```python
from src.analytics.report_templates import ReportFormat

# Available formats
ReportFormat.PDF
ReportFormat.EXCEL
ReportFormat.CSV
ReportFormat.JSON
ReportFormat.HTML
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

## Performance Utilities

### Request Batching

**Module:** `src/app/dashboard/utils/request_batching.py`

Batches API requests with rate limiting and parallel execution.

```python
from src.app.dashboard.utils.request_batching import RequestBatcher, batch_api_requests

# Using RequestBatcher class
batcher = RequestBatcher(
    batch_size=10,
    max_wait_time=0.5,
    rate_limit_per_second=5
)
result, error = batcher.add_request(my_api_func, arg1, arg2)
results, errors = batcher.flush()

# Using batch_api_requests helper
requests = [
    (fetch_price, ("AAPL",)),
    (fetch_price, ("MSFT",)),
    (fetch_price, ("GOOGL",)),
]
results = batch_api_requests(
    requests,
    batch_size=10,
    max_workers=4,
    rate_limit_per_second=5
)
# Returns: [(result, error), ...]
```

### Parallel Processing

**Module:** `src/app/dashboard/utils/parallel.py`

Multi-threaded/multi-process execution for batch operations.

```python
from src.app.dashboard.utils.parallel import (
    ParallelProcessor,
    parallel_download,
    parallel_analysis,
    parallel_map,
    parallelize
)

# ParallelProcessor class
processor = ParallelProcessor(max_workers=8, use_processes=False)
results = processor.process_batch(items, my_func)
# Returns: [(item, result, error), ...]

successes, errors = processor.process_with_errors(items, my_func)

# Convenience functions
results = parallel_download(urls, download_func, batch_size=10)
results = parallel_analysis(run_ids, analysis_func)
results = parallel_map(items, transform_func, max_workers=4)

# Decorator
@parallelize(max_workers=4)
def process_items(items):
    return [transform(item) for item in items]
```

### Query Cache

**Module:** `src/app/dashboard/utils/cache.py`

TTL-based caching with automatic compression for large data.

```python
from src.app.dashboard.utils.cache import (
    QueryCache,
    cached_query,
    cache_key_for_run,
    clear_cache,
    get_cache_stats
)

# QueryCache class
cache = QueryCache(default_ttl=300)  # 5-minute TTL
cache.set("my_key", large_data, compress=True)
data = cache.get("my_key")  # Auto-decompresses
cache.clear(pattern="run:*")

# Decorator for caching function results
@cached_query(ttl=300)
def expensive_query(run_id):
    return fetch_data(run_id)

# Key generators
key = cache_key_for_run("run123", "attribution")  # "run:run123:attribution"

# Cache management
stats = get_cache_stats()  # {total_entries, active_entries, ...}
clear_cache(pattern="run:*")
```

### Lazy DataFrames

**Module:** `src/app/dashboard/components/lazy_dataframes.py`

On-demand DataFrame loading for Streamlit dashboards.

```python
from src.app.dashboard.components.lazy_dataframes import (
    lazy_dataframe,
    paginated_dataframe,
    virtual_scroll_dataframe
)

# Lazy load - only loads when user expands
df = lazy_dataframe("my_data", lambda: load_large_df(), max_rows_preview=10)

# Paginated display
displayed_df = paginated_dataframe(large_df, page_size=50)

# Virtual scroll with "Load More" button
displayed_df = virtual_scroll_dataframe(large_df, chunk_size=100, initial_rows=50)
```

### Progressive Charts

**Module:** `src/app/dashboard/components/progressive_charts.py`

Sequential/batch chart loading with automatic downsampling.

```python
from src.app.dashboard.components.progressive_charts import (
    progressive_chart_loader,
    optimized_chart
)

# Load multiple charts progressively
charts = progressive_chart_loader(
    "analysis_charts",
    chart_funcs=[make_chart1, make_chart2, make_chart3],
    chart_labels=["Returns", "Allocation", "Risk"],
    loading_strategy="batch",  # or "sequential"
    batch_size=2
)

# Optimize a single chart (auto-downsample large datasets)
fig = optimized_chart(
    make_chart,
    data_points=50000,
    max_points=1000,
    downsample=True
)
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

---

## See Also

- [System architecture](design.md)
- [Configuration and CLI](configuration-cli.md)
- [API key setup](api-configuration.md)
- [User workflows](user-guide.md)
- [Developer Guide](developer-guide.md)
