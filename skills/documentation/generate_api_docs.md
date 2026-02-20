# Skill: Generate API Documentation

**Purpose**: Create comprehensive API reference documentation for a module.

**Category**: documentation

---

## Prerequisites

- Module has been analyzed using [`../code_exploration/analyze_module.md`](../code_exploration/analyze_module.md)
- Familiarity with Markdown syntax
- Read [`../../knowledgebase/AGENT_PROMPT.md`](../../knowledgebase/AGENT_PROMPT.md) for project context and documentation standards

---

## Inputs

### Required
- **module_name**: Name of the module (e.g., `backtest`, `analytics`, `risk`)
- **module_path**: Absolute path to module directory
- **analysis_summary**: Output from `analyze_module.md` skill

### Optional
- **include_examples**: Whether to include code examples (default: `true`)
- **example_count**: Number of examples per class/function (default: `1`)

---

## Process

### Step 1: Create API Reference File

Create the API reference Markdown file.

**File Path**: `doc/api_reference/<module_name>.md`

**Example**:
- Module `backtest` → `doc/api_reference/backtest.md`
- Module `analytics` → `doc/api_reference/analytics.md`

---

### Step 2: Write Header Section

Write the module header with title and package information.

**Template**:
```markdown
# Module: [module_name]

**Package**: `midterm_stock_planner.[module_name]`

**Location**: `src/midterm_stock_planner/[module_name]/`
```

**Example**:
```markdown
# Module: backtest

**Package**: `midterm_stock_planner.backtest`

**Location**: `src/midterm_stock_planner/backtest/`
```

---

### Step 3: Write Overview Section

Write a comprehensive overview (2-4 paragraphs).

**Template**:
```markdown
## Overview

[First paragraph: What this module does - its primary purpose]

[Second paragraph: Key responsibilities and capabilities]

[Third paragraph (optional): How it fits into the overall system]

[Fourth paragraph (optional): Typical use cases]
```

**Content Guidelines**:
- Start with a clear, one-sentence purpose statement
- Explain what problems this module solves
- Describe key capabilities
- Mention relationships to other modules
- Keep it accessible (avoid jargon when possible, or define terms)

**Example**:
```markdown
## Overview

The `backtest` module provides the core engine for walk-forward backtesting of stock ranking strategies. It enables evaluation of portfolio construction methods across historical time periods, with support for configurable rebalance frequencies and benchmark comparison.

Key responsibilities include:
- Running walk-forward backtests with expanding or rolling training windows
- Constructing portfolios from LightGBM-ranked stock signals at each rebalance date
- Computing performance metrics (Sharpe ratio, max drawdown, cumulative returns)
- Generating trade logs and portfolio weight histories for analysis

This module serves as the primary evaluation framework for the stock ranking pipeline. It depends on `models` for signal generation, `risk` for portfolio allocation, and `analytics` for performance reporting.

Typical use cases include evaluating new feature sets against historical data, comparing allocation strategies (equal-weight vs. risk parity), and producing tearsheet reports for strategy review.
```

---

### Step 4: Write Key Concepts Section (if applicable)

For modules with domain-specific concepts, add a Key Concepts section.

**Template**:
```markdown
## Key Concepts

### [Concept 1]
[Definition and explanation]

### [Concept 2]
[Definition and explanation]
```

**When to Include**:
- Module has specialized terminology (e.g., "Walk-Forward Validation" in backtest module)
- Concepts are not obvious from class names alone
- Understanding concepts is prerequisite to using the API

**Example**:
```markdown
## Key Concepts

### Backtest Architecture
A BacktestEngine orchestrates:
- **Strategy**: The ranking model and feature pipeline producing stock signals
- **Portfolio**: Weighted collection of stocks constructed at each rebalance date
- **Metrics**: Performance statistics computed over the backtest period (Sharpe, drawdown, etc.)

The relationship is: BacktestEngine → Strategy → Signals (ranked stock scores)
                      BacktestEngine → Portfolio → Holdings (weights per rebalance)

### Walk-Forward Validation
The module supports expanding-window evaluation of strategies:
- **Training Window**: Historical period used to fit the LightGBM ranking model
- **Test Window**: Out-of-sample period where the trained model generates signals
- **Rebalance Frequency**: How often the portfolio is reconstructed (e.g., monthly, quarterly)
```

---

### Step 5: Document Classes

For each class in the module, write comprehensive documentation.

**Template**:
```markdown
## Classes

### [ClassName]

[1-2 sentence description of what this class represents]

**Purpose**: [Why this class exists - what problem it solves]

**Attributes**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `attribute_name` | `type` | [Description] |
| ... | ... | ... |

**Methods**:
- `method_name(param1: type1, param2: type2 = default) -> return_type`: [Description]
- ...

**Example**:
```python
# Initialization
obj = ClassName(param1="value", param2=123)

# Usage
result = obj.method_name(arg1, arg2)
print(result)  # Expected output: [description]
```

**See Also**:
- [Related Class](#related-class)
- [Related Function](#related-function)
```

**Attribute Table Guidelines**:
- List all public attributes (accessible via @property)
- Include type information (use Python type hints syntax)
- Provide clear, concise descriptions
- Note read-only vs read-write properties
- For dict attributes, specify key→value types (e.g., `dict[str, Position]`)

**Methods List Guidelines**:
- List all public methods (exclude private methods starting with _)
- Include full signature with types and defaults
- Use one-line descriptions (detailed docs for each method come later if needed)
- Group methods by purpose if many methods exist

**Example Guidelines**:
- Show initialization
- Show typical usage (2-3 operations)
- Include expected output
- Keep it minimal but complete (runnable code)

**Example for BacktestEngine class**:
```markdown
### BacktestEngine

Core engine for running walk-forward backtests on stock ranking strategies.

**Purpose**: Evaluate portfolio construction strategies over historical periods using walk-forward validation, producing performance metrics and trade logs.

**Attributes**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `config` | `BacktestConfig` | Configuration object (universe, date range, rebalance frequency) |
| `results` | `BacktestResults` | Container for performance metrics after a run completes |
| `strategy` | `Strategy` | The ranking strategy (LightGBM model + feature pipeline) |
| `start_date` | `str` | Backtest start date in "YYYY-MM-DD" format |
| `end_date` | `str` | Backtest end date in "YYYY-MM-DD" format |

**Methods**:
- `run(strategy: Strategy, start_date: str, end_date: str, rebalance_freq: str = "monthly") -> BacktestResults`: Execute the walk-forward backtest over the specified date range
- `get_results() -> BacktestResults`: Return the most recent backtest results (metrics, trade log, weight history)
- `export_report(output_path: str, format: str = "html") -> None`: Generate and save a tearsheet report to disk

**Example**:
```python
from midterm_stock_planner.backtest import BacktestEngine, BacktestConfig
from midterm_stock_planner.strategies import MomentumStrategy

# Configure backtest
config = BacktestConfig(
    universe="sp500",
    benchmark="SPY",
    top_k=30,
    rebalance_freq="monthly"
)

# Create engine and run backtest
engine = BacktestEngine(config=config)
results = engine.run(
    strategy=MomentumStrategy(),
    start_date="2020-01-01",
    end_date="2024-12-31"
)

# Inspect performance metrics
print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")  # e.g., 1.45
print(f"Max Drawdown: {results.max_drawdown:.2%}")   # e.g., -18.32%

# Export tearsheet report
engine.export_report("reports/momentum_tearsheet.html")
print("Report saved")
```

**See Also**:
- [BacktestConfig](#backtestconfig) - Configuration for backtest parameters
- [BacktestResults](#backtestresults) - Container for performance output
- [Strategy](#strategy) - Base class for ranking strategies
```

---

### Step 6: Document Enums (if applicable)

For enum classes, provide comprehensive documentation.

**Template**:
```markdown
### [EnumName] (Enum)

[Description of what this enum represents]

**Values**:
| Value | Integer | Description |
|-------|---------|-------------|
| `VALUE_NAME` | `0` | [Description] |
| ... | ... | ... |

**Example**:
```python
from midterm_stock_planner.[module] import [EnumName]

# Access enum value
type_value = [EnumName].VALUE_NAME.value  # Returns integer
type_name = [EnumName].VALUE_NAME.name    # Returns string "VALUE_NAME"

# Use in code
if position.risk == [EnumName].HIGH.value:
    print("High risk position")
```
```

**Example for RiskLevel**:
```markdown
### RiskLevel (Enum)

Classification of risk levels for portfolio positions and signals.

**Values**:
| Value | Integer | Description |
|-------|---------|-------------|
| `VERY_LOW` | `0` | Minimal risk (e.g., large-cap stable dividend stocks) |
| `LOW` | `1` | Below-average risk (e.g., defensive sectors) |
| `MODERATE` | `2` | Average market risk |
| `HIGH` | `3` | Above-average risk (e.g., small-cap growth stocks) |
| `VERY_HIGH` | `4` | Extreme risk (e.g., highly leveraged or speculative positions) |
| `UNKNOWN` | `255` | Risk level not yet assessed |

**Example**:
```python
from midterm_stock_planner.risk import RiskLevel

# Assign risk level to a position
position_risk = RiskLevel.HIGH.value  # 3

# Filter portfolio by risk level
if position.risk == RiskLevel.VERY_HIGH.value:
    print("Flagged for risk review")
elif position.risk == RiskLevel.LOW.value:
    print("Within acceptable risk tolerance")
```
```

---

### Step 7: Document Functions (if applicable)

For modules with standalone functions, document each function.

**Template**:
```markdown
## Functions

### [function_name]

```python
def function_name(param1: type1, param2: type2 = default) -> return_type:
```

[1-2 sentence description of what this function does]

**Parameters**:
- `param1` (`type1`): [Description]
- `param2` (`type2`, optional): [Description]. Default: `default`

**Returns**:
- (`return_type`): [Description of return value]

**Raises**:
- `ExceptionType`: [When this exception is raised]

**Example**:
```python
result = function_name(arg1, arg2)
print(result)  # [Expected output]
```

**See Also**:
- [Related Function](#related-function)
```

**Function Documentation Guidelines**:
- Include full signature with types
- Describe purpose clearly (what problem it solves, not how it works internally)
- List all parameters with types and descriptions
- Specify return type and value
- Document exceptions that can be raised
- Provide minimal but complete example
- Link to related functions

**Example for compute_rolling_metrics function**:
```markdown
### compute_rolling_metrics

```python
def compute_rolling_metrics(df: pd.DataFrame, window: int = 20, metrics: list[str] | None = None) -> pd.DataFrame:
```

Computes rolling performance metrics over a returns DataFrame for one or more stocks.

**Parameters**:
- `df` (`pd.DataFrame`): DataFrame with a DatetimeIndex and one column per stock containing daily returns
- `window` (`int`, optional): Rolling window size in trading days. Default: `20`
- `metrics` (`list[str]`, optional): Metrics to compute. Options: `"sharpe"`, `"volatility"`, `"max_drawdown"`. Default: all three.

**Returns**:
- (`pd.DataFrame`): MultiIndex DataFrame with rolling metric values for each stock and metric.

**Raises**:
- `ValueError`: If DataFrame does not have a DatetimeIndex
- `KeyError`: If an unrecognized metric name is provided

**Example**:
```python
from midterm_stock_planner.analytics import compute_rolling_metrics

# Compute 60-day rolling Sharpe and volatility
rolling = compute_rolling_metrics(returns_df, window=60, metrics=["sharpe", "volatility"])
print(f"Columns: {rolling.columns.tolist()}")

# Access rolling Sharpe for a specific stock
aapl_sharpe = rolling[("AAPL", "sharpe")]
print(f"Latest rolling Sharpe for AAPL: {aapl_sharpe.iloc[-1]:.2f}")  # e.g., 1.23
```

**See Also**:
- [compute_cumulative_returns](#compute_cumulative_returns) - Cumulative return series
- [compute_drawdown_series](#compute_drawdown_series) - Drawdown time series
```

---

### Step 8: Document Constants (if applicable)

For modules with important constants, document them.

**Template**:
```markdown
## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `CONSTANT_NAME` | `value` | [Description] |
| ... | ... | ... |
```

**Example**:
```markdown
## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_RISK_FREE_RATE` | `0.04` | Annual risk-free rate used for Sharpe ratio calculations |
| `MIN_TRADING_DAYS` | `252` | Minimum trading days required for annualized metrics |
| `MAX_POSITION_WEIGHT` | `0.10` | Maximum single-position weight in risk parity allocation (10%) |
```

---

### Step 9: Add See Also Section

Add cross-references to related modules and documentation.

**Template**:
```markdown
## See Also

### Related Modules
- [`[module_name]`](.module_name].md) - [Brief description]
- ...

### Related Documentation
- [User Guide: [Topic]](../user_guides/[topic].md) - [Brief description]
- [Design: [Component]](../design/2_component_designs/[component].md) - [Brief description]
```

**Example**:
```markdown
## See Also

### Related Modules
- [`analytics`](analytics.md) - Performance reporting and rolling metrics
- [`risk`](risk.md) - Risk parity allocation and position sizing
- [`models`](models.md) - LightGBM ranking model and SHAP explainability

### Related Documentation
- [User Guide: Backtesting](../user_guides/backtesting.md) - How to run and interpret backtests
- [Design: Portfolio Construction](../design/2_component_designs/portfolio_construction.md) - Architectural details
- [Glossary](../../knowledgebase/glossary.md) - Domain terminology
```

---

## Outputs

### Primary
- **File**: `doc/api_reference/<module_name>.md`
- **Content**: Complete API reference with:
  - Header (module name, package)
  - Overview (2-4 paragraphs)
  - Key Concepts (if applicable)
  - Classes (with attributes, methods, examples)
  - Enums (if applicable)
  - Functions (if applicable)
  - Constants (if applicable)
  - See Also (related modules and docs)

### Secondary
- **File added to git**: Stage the new file for commit

---

## Examples

### Example 1: Generate API Docs for backtest Module

**Input**:
- module_name: `backtest`
- module_path: `/Users/antiwong/Documents/code/my_code/stock_all/midterm-stock-planner/src/midterm_stock_planner/backtest/`
- analysis_summary: (from analyze_module.md)
- include_examples: `true`

**Process**:
1. Create `doc/api_reference/backtest.md`
2. Write header: "# Module: backtest"
3. Write overview (walk-forward backtesting engine for stock strategies)
4. Write key concepts (Backtest architecture, walk-forward validation)
5. Document classes:
   - BacktestEngine (with run, get_results, export_report examples)
   - BacktestConfig (with attributes and example)
   - BacktestResults (data class with example)
   - Strategy (with example)
6. Document enum:
   - RiskLevel (6 values with table)
7. Add See Also (analytics, risk, models modules)

**Output**:
File created at `doc/api_reference/backtest.md` with complete API reference (~300-400 lines).

---

## Validation

- [ ] File created at `doc/api_reference/<module_name>.md`
- [ ] Header section includes module name and package
- [ ] Overview section is 2-4 paragraphs and clearly explains purpose
- [ ] All classes documented (attributes table, methods list, example)
- [ ] All enums documented (values table, example)
- [ ] All functions documented (signature, parameters, returns, example)
- [ ] All constants documented (value, description)
- [ ] All code examples are syntactically correct and runnable
- [ ] See Also section links to related modules and docs
- [ ] Markdown formatting is correct (tables, code blocks, links)
- [ ] No broken links (verify all relative links work)

---

## Related Skills

### Prerequisites
- [`../code_exploration/analyze_module.md`](../code_exploration/analyze_module.md) - Must analyze module first

### Follow-ups
- [`add_docstrings.md`](add_docstrings.md) - Add docstrings to source files
- [`../validation/check_doc_coverage.md`](../validation/check_doc_coverage.md) - Verify completeness
- [`../validation/validate_examples.md`](../validation/validate_examples.md) - Test code examples

### Related
- [`generate_component_design.md`](generate_component_design.md) - Create architectural design docs
- [`update_api_reference.md`](update_api_reference.md) - Update existing API docs

---

**Last Updated**: 2026-02-20
**Version**: 1.0
