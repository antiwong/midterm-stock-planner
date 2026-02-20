# Skill: Add Docstrings

**Purpose**: Add Python docstrings to source code files for in-code documentation.

**Category**: documentation

---

## Prerequisites

- Module has been analyzed using [`../code_exploration/analyze_module.md`](../code_exploration/analyze_module.md)
- API reference documentation created using [`generate_api_docs.md`](generate_api_docs.md)
- Familiarity with Python docstring styles (Google, NumPy, or reStructuredText)

---

## Inputs

### Required
- **module_name**: Name of the module (e.g., `backtest`, `analytics`)
- **module_path**: Absolute path to module directory
- **api_reference_file**: Path to existing API reference doc (e.g., `docs/api_reference/backtest.md`)

### Optional
- **docstring_style**: Style to use (default: `google`)
  - `google`: Google-style docstrings
  - `numpy`: NumPy-style docstrings
  - `sphinx`: reStructuredText for Sphinx
- **coverage_target**: Target coverage percentage (default: `80`)

---

## Process

### Step 1: Read API Reference Documentation

Read the existing API reference to extract documentation content.

**Use**: Read tool on `api_reference_file`

**Extract**:
- Class descriptions
- Method descriptions
- Function descriptions with parameters and returns
- Example code

---

### Step 2: Add Class Docstrings

For each class, add a docstring immediately after the class definition.

**Google Style Template**:
```python
class ClassName:
    """Short one-line description.

    Longer description with more details about the class purpose,
    responsibilities, and typical usage patterns.

    Attributes:
        attribute_name (type): Description of attribute.
        another_attr (type): Description of another attribute.

    Example:
        Basic usage example::

            obj = ClassName(param="value")
            result = obj.method()
    """
```

**Where to Add**:
- Immediately after `class ClassName:` line
- Before `__init__` method
- Use triple double-quotes `"""`

---

### Step 3: Add Method Docstrings

For each method, add a docstring describing its purpose, parameters, and return value.

**Google Style Template**:
```python
def method_name(self, param1, param2=None):
    """Short one-line description.

    Longer description with details about what this method does,
    when to use it, and any important notes.

    Args:
        param1 (type): Description of param1.
        param2 (type, optional): Description of param2.
            Defaults to None.

    Returns:
        type: Description of return value.

    Raises:
        ExceptionType: When this exception occurs.

    Example:
        result = obj.method_name(value1, value2)
    """
```

---

### Step 4: Add Function Docstrings

For standalone functions, add docstrings.

**Google Style Template**:
```python
def function_name(param1, param2=None):
    """Short one-line description.

    Longer description.

    Args:
        param1 (type): Description.
        param2 (type, optional): Description. Defaults to None.

    Returns:
        type: Description of return value.

    Example:
        result = function_name(value1)
    """
```

---

### Step 5: Add Module Docstring

Add a module-level docstring at the top of each file.

**Template**:
```python
"""Module for [brief description].

This module provides [detailed description of module purpose and
key capabilities].

Typical usage example:
    from midterm_stock_planner.module import ClassName

    obj = ClassName()
    result = obj.method()
"""

import ...
```

---

### Step 6: Validate Docstrings

Check that docstrings are correct and complete.

**Validation Checklist**:
- [ ] All public classes have docstrings
- [ ] All public methods have docstrings
- [ ] All public functions have docstrings
- [ ] Module-level docstring exists
- [ ] Docstrings include examples where helpful
- [ ] Docstrings match API reference content

**Tools**:
- `pydocstyle` - Check docstring style compliance
- Manual review - Verify content accuracy

---

## Outputs

### Primary
- **Modified Files**: Source files with added docstrings
- **Coverage**: Percentage of classes/functions with docstrings

### Secondary
- **Git Changes**: Modified files staged for commit

---

## Examples

### Example 1: Add Docstrings to BacktestEngine Class

**Input**:
- module_name: `backtest`
- File: `src/midterm_stock_planner/backtest/engine.py`
- API reference: `docs/api_reference/backtest.md`

**Before**:
```python
class BacktestEngine:
    def __init__(self, strategy: str, config: dict) -> None:
        self._strategy = strategy
        self._config = config
        self._results = dict()
        self._portfolio = dict()

    @property
    def strategy(self):
        return self._strategy

    def run_walk_forward(self, tickers, start_date, end_date, window_size, step_size):
        # implementation...
```

**After**:
```python
class BacktestEngine:
    """Engine for walk-forward backtesting of stock ranking strategies.

    BacktestEngine executes walk-forward analysis by splitting historical
    data into rolling training and validation windows, re-fitting the
    strategy on each training window and evaluating out-of-sample
    performance on the subsequent validation window. It tracks portfolio
    returns, risk metrics, and ranking accuracy across all windows.

    Attributes:
        strategy (str): Name of the ranking strategy to backtest.
        config (dict): Backtest configuration parameters including
            rebalance frequency, commission rate, and slippage model.
        results (dict[str, pd.DataFrame]): Mapping of window ID to
            per-window performance results.
        portfolio (dict[str, float]): Current portfolio holdings as
            a mapping of ticker to weight.

    Example:
        engine = BacktestEngine(
            strategy="momentum_quality",
            config={"rebalance_freq": "monthly", "commission": 0.001}
        )
        engine.run_walk_forward(
            tickers=["AAPL", "MSFT", "GOOG"],
            start_date="2020-01-01",
            end_date="2025-01-01",
            window_size=252,
            step_size=63,
        )
    """

    def __init__(self, strategy: str, config: dict) -> None:
        self._strategy = strategy
        self._config = config
        self._results = dict()
        self._portfolio = dict()

    @property
    def strategy(self):
        """str: Name of the ranking strategy being backtested."""
        return self._strategy

    def run_walk_forward(self, tickers, start_date, end_date, window_size, step_size):
        """Run walk-forward backtest over the specified date range.

        Splits the historical period into rolling windows of
        ``window_size`` trading days, advancing by ``step_size`` days
        between iterations. On each iteration the strategy is trained
        on the in-sample window and evaluated on the subsequent
        out-of-sample window.

        Args:
            tickers (list[str]): List of stock ticker symbols to include.
            start_date (str): Backtest start date in YYYY-MM-DD format.
            end_date (str): Backtest end date in YYYY-MM-DD format.
            window_size (int): Number of trading days in each
                training window.
            step_size (int): Number of trading days to advance
                between windows.

        Returns:
            dict: Aggregated backtest results containing cumulative
                returns, Sharpe ratio, max drawdown, and per-window
                performance breakdowns.

        Raises:
            ValueError: When start_date is after end_date or the
                date range is shorter than window_size.

        Example:
            results = engine.run_walk_forward(
                tickers=["AAPL", "MSFT", "GOOG"],
                start_date="2020-01-01",
                end_date="2025-01-01",
                window_size=252,
                step_size=63,
            )
        """
        # implementation...
```

---

## Validation

- [ ] All public classes have docstrings
- [ ] All public methods have docstrings (including `__init__`)
- [ ] All public functions have docstrings
- [ ] Property accessors have one-line docstrings
- [ ] Module-level docstring exists
- [ ] Docstrings follow consistent style (Google/NumPy/Sphinx)
- [ ] Docstrings match API reference content
- [ ] Examples in docstrings are syntactically correct
- [ ] `pydocstyle` passes (if using)

---

## Related Skills

### Prerequisites
- [`generate_api_docs.md`](generate_api_docs.md) - Create API reference first

### Follow-ups
- None (this is typically the last documentation step)

### Related
- [`../code_exploration/analyze_module.md`](../code_exploration/analyze_module.md) - Understand code first
- [`../validation/check_doc_coverage.md`](../validation/check_doc_coverage.md) - Verify coverage

---

**Last Updated**: 2026-02-20
**Version**: 1.0
