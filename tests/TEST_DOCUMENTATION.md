# Test Documentation

## Overview

This document describes all tests implemented to ensure the integrity and correctness of the Mid-term Stock Planner codebase. The test suite covers data quality, metric calculations, backtest configuration, and pipeline integration.

## Running Tests

```bash
# Activate virtual environment
source ~/venv/bin/activate

# Run all tests (76 tests)
cd midterm-stock-planner
pytest tests/ -v

# Run specific test file
pytest tests/test_data_integrity.py -v
pytest tests/test_safeguards.py -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html

# Run only critical tests (fast)
pytest tests/ -v -m "not slow"
```

**Latest Results**: 76 passed, 1 skipped

---

## Test Categories

### 1. Data Integrity Tests (`test_data_integrity.py`)

**Purpose**: Ensure raw data files are valid and consistent before running backtests.

| Test | Description | Criticality |
|------|-------------|-------------|
| `test_price_data_exists` | Verify prices.csv exists | HIGH |
| `test_price_data_has_required_columns` | Check for date, ticker, close columns | HIGH |
| `test_price_data_no_negative_prices` | No negative or zero prices | HIGH |
| `test_price_data_date_range` | At least 5 years of data for training | HIGH |
| `test_no_extreme_daily_returns` | No >100% daily moves (data corruption) | CRITICAL |
| `test_no_duplicate_date_ticker_pairs` | No duplicate records | MEDIUM |
| `test_sufficient_tickers` | At least 50 tickers for diversification | MEDIUM |
| `test_benchmark_data_exists` | Verify benchmark.csv exists | HIGH |
| `test_benchmark_has_required_columns` | Check for required columns | HIGH |
| `test_benchmark_aligns_with_price_data` | Benchmark covers price data dates | HIGH |
| `test_benchmark_no_gaps` | No significant gaps in benchmark | MEDIUM |
| `test_sector_data_exists` | Verify sectors.csv exists | MEDIUM |
| `test_sector_has_required_columns` | Check for ticker, sector columns | MEDIUM |
| `test_no_duplicate_tickers_in_sectors` | No duplicate sector mappings | MEDIUM |
| `test_other_sector_percentage` | Less than 20% unclassified stocks | MEDIUM |
| `test_sector_coverage_of_price_data` | 80%+ of price tickers have sectors | MEDIUM |

**Historical Issues Fixed**:
- Corrupt price data on US market holidays caused 444% single-day returns
- Missing benchmark data limited backtest to 2024-01 instead of 2024-12

---

### 2. Backtest Configuration Tests (`test_backtest_config.py`)

**Purpose**: Validate backtest parameters are correctly applied.

| Test | Description | Criticality |
|------|-------------|-------------|
| `test_config_has_backtest_section` | Config file has backtest section | HIGH |
| `test_top_n_is_configured` | Either top_n or top_pct is set | HIGH |
| `test_transaction_cost_reasonable` | Transaction cost 0-5% | LOW |
| `test_rebalance_freq_valid` | Valid pandas offset string | MEDIUM |
| `test_positions_weights_sum_to_one` | **CRITICAL**: Weights sum to 1.0 | CRITICAL |
| `test_positions_count_matches_config` | Position count matches top_n | HIGH |
| `test_positions_no_negative_weights` | Long-only constraint | HIGH |
| `test_positions_no_excessive_weights` | No >50% concentration | MEDIUM |
| `test_positions_dates_are_sorted` | Chronological order | LOW |
| `test_positions_have_valid_tickers` | No empty ticker symbols | MEDIUM |
| `test_sufficient_training_data` | Enough data for train windows | HIGH |
| `test_windows_do_not_overlap` | Walk-forward windows separate | MEDIUM |

**Historical Issues Fixed**:
- `top_n: null` with `top_pct: 0.1` resulted in ~33 stocks instead of intended 10
- Positions were not being validated for weight sums

---

### 3. Metric Scaling Tests (`test_metric_scaling.py`)

**Purpose**: Ensure financial metrics are correctly calculated and stored as decimals.

| Test | Description | Criticality |
|------|-------------|-------------|
| `test_total_return_is_decimal` | 50% stored as 0.50 not 50 | CRITICAL |
| `test_annualized_return_is_decimal` | Annualized in [-1, 2] range | CRITICAL |
| `test_excess_return_is_decimal` | Excess return properly scaled | HIGH |
| `test_volatility_is_decimal` | 25% stored as 0.25 not 25 | CRITICAL |
| `test_volatility_is_positive` | Volatility must be positive | HIGH |
| `test_sharpe_ratio_in_realistic_range` | Sharpe in [-3, 5] range | HIGH |
| `test_sharpe_not_nan_or_inf` | Valid numeric value | HIGH |
| `test_max_drawdown_is_negative` | Drawdown is a loss (negative) | HIGH |
| `test_max_drawdown_within_bounds` | Drawdown in [-1, 0] | CRITICAL |
| `test_hit_rate_is_decimal` | 55% stored as 0.55 not 55 | HIGH |
| `test_sharpe_consistent_with_return_and_vol` | Internal consistency | MEDIUM |
| `test_total_vs_annualized_return_consistent` | Sign consistency | MEDIUM |

**Historical Issues Fixed**:
- Corrupt data caused unrealistic metrics: Total Return 15,667,895%, Volatility 461%
- Metrics were displayed incorrectly due to double-scaling (decimal stored then multiplied by 100)

**Metric Scaling Rules** (from `.cursorrules`):
```
Returns: Store as decimal (0.10 = 10%)
Volatility: Store as decimal (0.25 = 25%)
Sharpe: Raw number (typically -3 to +3)
Max Drawdown: Negative decimal in [-1, 0]
Hit Rate: Decimal in [0, 1]
```

---

### 4. Safeguards Validation Tests (`test_safeguards.py`)

**Purpose**: Validate automated safeguards that fail runs if criteria aren't met.

| Test | Description | Criticality |
|------|-------------|-------------|
| `test_valid_weights` | Weights summing to 1.0 pass | CRITICAL |
| `test_invalid_weights` | Weights not summing to 1.0 fail | CRITICAL |
| `test_multiple_dates` | Multi-date weight validation | CRITICAL |
| `test_correct_count` | Correct position count passes | HIGH |
| `test_incorrect_count` | Incorrect position count fails | HIGH |
| `test_within_conservative_bounds` | Vol within conservative limits | HIGH |
| `test_exceeds_conservative_bounds` | Vol exceeding limits warns | HIGH |
| `test_within_aggressive_bounds` | High vol OK for aggressive | MEDIUM |
| `test_within_bounds` (drawdown) | DD within bounds passes | HIGH |
| `test_exceeds_bounds` (drawdown) | DD exceeding bounds warns | HIGH |
| `test_sane_returns` | Reasonable returns pass | CRITICAL |
| `test_insane_total_return` | >10000% return fails | CRITICAL |
| `test_insane_annualized_return` | >500% annual fails | CRITICAL |
| `test_diversified_portfolio` | Diversified sectors pass | MEDIUM |
| `test_concentrated_portfolio` | >50% in one sector warns | MEDIUM |
| `test_all_positive` | Long-only weights pass | HIGH |
| `test_negative_weight` | Short positions fail | HIGH |
| `test_balanced_positions` | Balanced weights pass | HIGH |
| `test_excessive_position` | >50% single position fails | HIGH |
| `test_conservative_strictest` | Conservative has strictest bounds | LOW |
| `test_aggressive_loosest` | Aggressive has loosest bounds | LOW |
| `test_all_profiles_have_required_keys` | All profiles configured | LOW |

**Risk Profile Bounds:**

| Profile | Max Vol | Max DD | Max Sector |
|---------|---------|--------|------------|
| Conservative | 25% | -20% | 35% |
| Moderate | 50% | -40% | 50% |
| Aggressive | 80% | -70% | 70% |

---

### 5. Pipeline Integration Tests (`test_pipeline.py`)

**Purpose**: Validate end-to-end data flow from loading to output.

| Test | Description | Criticality |
|------|-------------|-------------|
| `test_load_price_data` | Price loader works | HIGH |
| `test_load_benchmark_data` | Benchmark loader works | HIGH |
| `test_feature_generation_produces_valid_output` | Features are generated | HIGH |
| `test_no_future_data_leakage` | No look-ahead bias | CRITICAL |
| `test_load_watchlists` | Watchlist manager works | MEDIUM |
| `test_get_watchlist_symbols` | Can retrieve symbols | MEDIUM |
| `test_get_sector_mapping` | Sector mapping available | MEDIUM |
| `test_sector_mapping_completeness` | 70%+ coverage | MEDIUM |
| `test_backtest_config_loads` | Config parsing works | HIGH |
| `test_backtest_output_structure` | Output files exist | HIGH |
| `test_database_connection` | Database accessible | MEDIUM |
| `test_runs_table_structure` | Database schema valid | MEDIUM |

**Historical Issues Fixed**:
- Watchlist filtering was overridden by `universe.txt`
- Custom watchlists weren't loading from database
- Sector mapping was incomplete (90%+ "Other")

---

## Test Fixtures

Common fixtures defined in `conftest.py`:

| Fixture | Description |
|---------|-------------|
| `project_root` | Path to project root directory |
| `config_path` | Path to config/config.yaml |
| `data_dir` | Path to data/ directory |
| `output_dir` | Path to output/ directory |
| `config` | Loaded configuration dictionary |
| `price_data` | Loaded prices.csv DataFrame |
| `benchmark_data` | Loaded benchmark.csv DataFrame |
| `sector_data` | Loaded sectors.csv DataFrame |
| `sample_returns` | Generated sample returns for testing |
| `sample_positions` | Generated sample positions for testing |

---

## Critical Tests Summary

These tests **must pass** before any production run:

1. **`test_no_extreme_daily_returns`** - Prevents corrupt data from contaminating metrics
2. **`test_positions_weights_sum_to_one`** - Fundamental portfolio constraint
3. **`test_total_return_is_decimal`** - Prevents metric display errors
4. **`test_max_drawdown_within_bounds`** - Validates risk calculations
5. **`test_no_future_data_leakage`** - Ensures backtest validity

---

## Validation Performed During Development

### Manual Validation Steps Completed

1. **Data Refresh (Jan 2, 2026)**
   - Downloaded fresh price data for 346 tickers
   - Updated benchmark (SPY) to 2025-12-31
   - Identified and documented 11 missing tickers (delisted/invalid)

2. **Backtest Configuration Fix**
   - Changed `top_n: null` → `top_n: 10`
   - Verified 10 stocks per rebalance date
   - Confirmed weights sum to 1.0

3. **Extended Backtest Window**
   - Previous: 4 windows ending 2024-01
   - Current: 5 windows ending 2024-12
   - Root cause: Benchmark data was limiting

4. **Metric Validation Results**
   ```
   Total Return:        391.62%  ✓ Realistic
   Annualized Return:    41.42%  ✓ Within bounds
   Volatility:           59.00%  ✓ Expected for 10-stock
   Sharpe Ratio:          0.70  ✓ Normal range
   Max Drawdown:        -64.61%  ✓ Negative, in [-1, 0]
   ```

5. **Sector Classification**
   - Previous: 90%+ in "Other" category
   - Current: <5% in "Other" category
   - Solution: Integrated yfinance sector lookup

---

## Adding New Tests

When adding new functionality, include tests for:

1. **Data Validation** - Input data format and quality
2. **Output Validation** - Results are in expected format
3. **Metric Bounds** - Values are within realistic ranges
4. **Consistency** - Related values are internally consistent

Example test structure:

```python
class TestNewFeature:
    """Tests for new feature X."""
    
    def test_feature_produces_output(self, input_fixture):
        """Basic functionality test."""
        result = new_feature(input_fixture)
        assert result is not None
    
    def test_feature_output_valid(self, input_fixture):
        """Validate output format/values."""
        result = new_feature(input_fixture)
        assert 0 <= result <= 1  # Example bounds check
    
    def test_feature_handles_edge_cases(self):
        """Edge case handling."""
        assert new_feature(None) is None
        assert new_feature([]) == []
```

---

## Continuous Integration

Recommended CI pipeline:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest tests/ -v --cov=src
```

---

## Contact

For questions about tests or to report issues, check the project documentation or create an issue in the repository.
