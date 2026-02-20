# Skill: Analyze Module

**Purpose**: Understand a module's structure, functions, patterns, and dependencies before documenting it.

**Category**: code_exploration

---

## Prerequisites

- Familiarity with Python syntax
- Access to the midterm_stock_planner codebase
- Read [`../../knowledgebase/AGENT_PROMPT.md`](../../knowledgebase/AGENT_PROMPT.md) for project context

---

## Inputs

### Required
- **module_name**: Name of the module to analyze (e.g., `backtest`, `analytics`, `risk`, `models`)
- **module_path**: Absolute path to module directory (e.g., `/Users/antiwong/Documents/code/my_code/stock_all/midterm-stock-planner/src/midterm_stock_planner/backtest/`)

### Optional
- **depth**: Analysis depth level (default: `deep`)
  - `quick`: File list and class names only
  - `medium`: + function signatures
  - `deep`: + full code reading with patterns

---

## Process

### Step 1: List Module Files

List all Python files in the module directory.

**Using Glob tool**:
```
Pattern: <module_path>/*.py
```

**Expected Output**: List of .py files

**Take Note Of**:
- Total file count
- File sizes (lines of code)
- File naming patterns

---

### Step 2: Identify Key Components

For each Python file, identify:
- **Classes**: Names, base classes, purpose
- **Functions**: Names, signatures, purpose
- **Constants**: Names, values, usage
- **Enums**: Names, values, purpose

**Using Read tool**:
Read each file (limit to first 100-150 lines to get overview, then read more if needed)

**Pattern Recognition**:
- Classes with `__init__` methods -> Data structures
- Classes with many methods -> Service/utility classes
- Functions starting with `search_`, `find_`, `get_` -> Query functions
- Functions starting with `convert_`, `transform_` -> Conversion functions
- Classes inheriting from `Enum` -> Type enums

---

### Step 3: Analyze Class Structure

For each major class, document:
- **Purpose**: What does this class represent?
- **Attributes**: What data does it store?
  - Note: Private attributes (e.g., `self._name`) with `@property` accessors
- **Methods**: What operations does it support?
  - `__init__`: Initialization parameters
  - Public methods: Purpose and signatures
  - Property accessors: Read-only or read-write?
- **Relationships**: Does it reference other classes?
  - Composition (contains instances of other classes)
  - Association (references other class instances)

**Example Output**:
```
Class: BacktestEngine
Purpose: Walk-forward backtesting engine for stock ranking models
Attributes:
  - _config (BacktestConfig): Backtest configuration
  - _model (LightGBM): Trained ranking model
  - _results (BacktestResults): Accumulated results
Methods:
  - run(): Execute walk-forward backtest
  - _train_window(): Train model on window
  - _test_window(): Test model predictions
Relationships:
  - Uses AppConfig (composition)
  - Produces BacktestResults (creation)
```

---

### Step 4: Analyze Function Purpose

For modules with many standalone functions (e.g., `analytics/metrics.py`, `analytics/monte_carlo.py`):

Group functions by purpose:
- **Metric calculations**: Functions returning numeric results (e.g., `calculate_sharpe_ratio()`)
- **Risk computations**: Functions computing risk measures (e.g., `compute_risk_metrics()`)
- **Feature engineering**: Functions building model features (e.g., `get_stock_features()`)
- **Utilities**: Helper functions (e.g., `annualize_returns()`)

**Take Note Of**:
- Parameter types (if annotated)
- Return types (if annotated)
- Common parameter patterns (e.g., many functions take `returns`, `portfolio`, `config`)

---

### Step 5: Identify Code Patterns

Recognize common patterns in the module:

**Pattern 1: Private Attributes with @property**
```python
class Example:
    def __init__(self):
        self._value = 0

    @property
    def value(self):
        return self._value
```
-> Read-only encapsulation

**Pattern 2: Dictionary-Based Storage**
```python
self._items = dict()
self._items[key] = value
```
-> Fast O(1) lookups

**Pattern 3: Enum for Type Safety**
```python
class ItemType(Enum):
    TYPE_A = 0
    TYPE_B = 1
```
-> Type-safe constants

**Pattern 4: NamedTuple for Data**
```python
class DataPoint(NamedTuple):
    x: float
    y: float
```
-> Immutable structured data

**Pattern 5: Graph Relationships**
```python
class Node:
    def __init__(self):
        self._prev_nodes = []
        self._next_nodes = []
```
-> Graph structure

---

### Step 6: Map Module Dependencies

Identify imports from other modules:
- **Internal imports**: From other modules in this project
  - `from .engine import BacktestEngine` -> Same package
  - `from midterm_stock_planner.risk import RiskManager` -> Other module
- **External imports**: Third-party libraries
  - `import numpy as np`
  - `import pandas as pd`

**Take Note Of**:
- Which modules this module depends on
- Which external libraries are required
- Circular dependencies (if any)

---

### Step 7: Estimate Documentation Scope

Calculate documentation effort:
- **Class count**: Number of classes to document
- **Function count**: Number of standalone functions
- **Complexity**: Simple (data classes) vs Complex (algorithms)
- **Existing docs**: Any existing docstrings or comments?

**Example Output**:
```
Module: backtest
Classes: 4 (BacktestEngine, BacktestConfig, BacktestResults, RunRecord)
Functions: ~10 utility functions
Enums: 1 (RebalanceFrequency with 4 values)
Complexity: Medium (walk-forward logic, window management)
Existing docs: Minimal (no class docstrings, few function docstrings)
Estimated effort: 2-3 hours for API reference
```

---

### Step 8: Summarize Findings

Create a structured summary:

**Module Analysis Summary Template**:
```markdown
# Module Analysis: [module_name]

## Overview
- **Purpose**: [What this module does]
- **Size**: [X files, Y LOC]
- **Complexity**: [Low/Medium/High]

## File Structure
- `file1.py` - [Purpose]
- `file2.py` - [Purpose]
- ...

## Key Classes
1. **ClassName** ([file.py:line])
   - Purpose: [Description]
   - Attributes: [Count]
   - Methods: [Count]
   - Pattern: [E.g., "Private attrs with @property"]

2. **ClassName2** ([file.py:line])
   - ...

## Key Functions
- `function_name()` ([file.py:line]) - [Purpose]
- ...

## Code Patterns
- [Pattern 1: Description]
- [Pattern 2: Description]

## Dependencies
- Internal: [List modules]
- External: [List libraries]

## Documentation Scope
- Classes to document: [Count]
- Functions to document: [Count]
- Enums to document: [Count]
- Estimated effort: [Time estimate]

## Notes
- [Special considerations]
- [Challenges or complexities]
- [Questions to clarify]
```

---

## Outputs

### Primary
- **Analysis Summary**: Structured summary of module (not saved to file, used as context for next steps)
- **File List**: List of Python files with purposes
- **Class/Function Inventory**: Complete list of components to document

### Secondary
- **Pattern Recognition**: Common code patterns identified
- **Dependency Map**: Module relationships
- **Scope Estimate**: Effort required for documentation

---

## Examples

### Example 1: Analyze backtest/ Module

**Input**:
- module_name: `backtest`
- module_path: `/Users/antiwong/Documents/code/my_code/stock_all/midterm-stock-planner/src/midterm_stock_planner/backtest/`
- depth: `deep`

**Process**:
1. List files: `engine.py`, `config.py`, `results.py`, `run_record.py`, `window.py`, ... (10 files total)
2. Identify components:
   - 4 main classes: BacktestEngine, BacktestConfig, BacktestResults, RunRecord
   - 1 enum: RebalanceFrequency (4 values)
   - ~10 utility functions
3. Analyze BacktestEngine class:
   - Attributes: _config, _model (LightGBM), _results (BacktestResults), _universe
   - Methods: run(), _train_window(), _test_window(), _rebalance_portfolio()
   - Pattern: Private attrs with @property accessors, config-driven execution
4. Analyze functions:
   - Window management (split_walk_forward_windows, get_train_test_split)
5. Identify patterns:
   - Private attributes with @property (all classes)
   - Config-driven design (BacktestConfig controls all parameters)
   - Enum for type safety (RebalanceFrequency)
6. Dependencies:
   - Internal: models, risk, analytics
   - External: lightgbm, pandas, numpy
7. Scope: 4 classes + 1 enum + ~10 functions = ~2-3 hours

**Output**:
```markdown
# Module Analysis: backtest

## Overview
- **Purpose**: Walk-forward backtesting engine for stock ranking models
- **Size**: 10 files, ~1,200 LOC
- **Complexity**: Medium (walk-forward logic, window management)

## File Structure
- `engine.py` - BacktestEngine main class
- `config.py` - BacktestConfig configuration dataclass
- `results.py` - BacktestResults accumulator
- `run_record.py` - RunRecord for single backtest run
- `window.py` - Walk-forward window utilities
- ... (5 more files for helpers)

## Key Classes
1. **BacktestEngine** (engine.py:12)
   - Purpose: Orchestrates walk-forward backtesting for stock ranking
   - Attributes: 4 (config, model, results, universe)
   - Methods: 5 (run, _train_window, _test_window, _rebalance_portfolio, ...)
   - Pattern: Private attrs with @property accessors, config-driven execution

2. **BacktestConfig** (config.py:8)
   - Purpose: Configuration for backtest parameters
   - Attributes: 6 (start_date, end_date, rebalance_freq, train_window, test_window, top_k)
   - Methods: 0 (data class only)
   - Pattern: Dataclass with validation

3. **BacktestResults** (results.py:5)
   - Purpose: Accumulates portfolio returns and metrics across windows
   - Attributes: 3 (returns_series, holdings_history, metrics_dict)
   - Methods: 3 (add_window_result, compute_summary, to_dataframe)
   - Pattern: Accumulator pattern

4. **RunRecord** (run_record.py:4)
   - Purpose: Single walk-forward window result record
   - Attributes: 4 (train_start, train_end, test_start, test_end)
   - Pattern: Data class

## Key Enums
- **RebalanceFrequency** (config.py:3) - 4 frequency types (WEEKLY, BIWEEKLY, MONTHLY, QUARTERLY)

## Key Functions
- `split_walk_forward_windows()` (window.py:10) - Generate train/test window splits
- `get_train_test_split()` (window.py:45) - Get single train/test split for a date

## Code Patterns
- Private attributes with @property (BacktestEngine, BacktestResults)
- Config-driven design (BacktestConfig parameterizes all behavior)
- Enum for type safety (RebalanceFrequency)

## Dependencies
- Internal: models, risk, analytics
- External: lightgbm, pandas, numpy

## Documentation Scope
- Classes: 4 main classes
- Enums: 1 enum (4 values)
- Functions: ~10 functions
- Estimated effort: 2-3 hours for API reference

## Notes
- No existing docstrings (need to add)
- Walk-forward logic is the core algorithm to document clearly
- Config-driven design makes entry points easy to identify
```

---

### Example 2: Analyze analytics/ Module (High Complexity)

**Input**:
- module_name: `analytics`
- module_path: `/Users/antiwong/Documents/code/my_code/stock_all/midterm-stock-planner/src/midterm_stock_planner/analytics/`
- depth: `deep`

**Process**:
1. List files: `metrics.py` (60+ functions), `monte_carlo.py` (15+ functions), `factor_analysis.py`, `portfolio_stats.py`, ...
2. Identify components:
   - No major classes
   - 100+ standalone functions (mostly in metrics.py and monte_carlo.py)
3. Analyze functions:
   - Portfolio metrics: `compute_portfolio_metrics()`, `calculate_sharpe_ratio()`, ...
   - Simulation: `run_monte_carlo()`, `simulate_paths()`, ...
   - Factor analysis: `calculate_factor_exposures()`, `decompose_returns()`, ...
4. Patterns:
   - Many functions take similar parameters (returns, portfolio, config)
   - Return types: DataFrames, floats, dicts
5. Dependencies:
   - Internal: models, risk
   - External: pandas, numpy, scipy
6. Scope: 100+ functions = ~5-6 hours

**Output**:
```markdown
# Module Analysis: analytics

## Overview
- **Purpose**: Portfolio analytics, Monte Carlo simulation, and factor analysis
- **Size**: 7 files, ~1,400 LOC
- **Complexity**: High (100+ utility functions, statistical algorithms)

## File Structure
- `metrics.py` (60+ functions) - Portfolio metrics (Sharpe, Sortino, drawdown, etc.)
- `monte_carlo.py` (15+ functions) - Monte Carlo simulation and path generation
- `factor_analysis.py` - Factor exposure and return decomposition
- `portfolio_stats.py` - Aggregate portfolio statistics
- ... (3 more files)

## Key Functions
### Portfolio Metrics (metrics.py)
- `compute_portfolio_metrics()` - Calculate full suite of portfolio metrics
- `calculate_sharpe_ratio()` - Annualized Sharpe ratio
- `calculate_sortino_ratio()` - Downside deviation-adjusted return
- `compute_max_drawdown()` - Maximum peak-to-trough decline
- ... (50+ more)

### Monte Carlo Simulation (monte_carlo.py)
- `run_monte_carlo()` - Run full Monte Carlo simulation
- `simulate_paths()` - Generate simulated return paths
- `compute_var()` - Value at Risk calculation
- `compute_cvar()` - Conditional Value at Risk
- ... (10+ more)

### Factor Analysis (factor_analysis.py)
- `calculate_factor_exposures()` - Compute factor loadings
- `decompose_returns()` - Attribute returns to factors
- `run_regression_analysis()` - Multi-factor regression
- ... (8+ more)

## Code Patterns
- Functional style (stateless functions)
- Common parameter signatures (returns, portfolio, config)
- Heavy use of statistical libraries (scipy, numpy)

## Dependencies
- Internal: models, risk
- External: pandas, numpy, scipy

## Documentation Scope
- Functions: 100+ functions
- Estimated effort: 5-6 hours for API reference
- Challenge: Many similar functions (need clear grouping)

## Notes
- High function count (group by purpose in docs)
- Complex algorithms (Monte Carlo, factor decomposition) need detailed explanations
- No docstrings (need to add)
- Consider creating algorithm design docs for Monte Carlo and factor analysis
```

---

## Validation

- [ ] All Python files in module identified
- [ ] All classes documented (name, purpose, attributes, methods)
- [ ] All functions documented (name, purpose, signature)
- [ ] Code patterns recognized and noted
- [ ] Dependencies (internal and external) identified
- [ ] Documentation scope estimated (class/function counts)
- [ ] Analysis summary created with all required sections

---

## Related Skills

### Prerequisites
- None (this is typically the first skill in documentation workflow)

### Follow-ups
- [`../documentation/generate_api_docs.md`](../documentation/generate_api_docs.md) - Use analysis to create API reference
- [`../documentation/add_docstrings.md`](../documentation/add_docstrings.md) - Add docstrings based on analysis
- [`../documentation/generate_component_design.md`](../documentation/generate_component_design.md) - Create component design for complex modules

### Alternatives
- [`summarize_functions.md`](summarize_functions.md) - Quicker function-only summary (for high function count modules)
- [`trace_data_flow.md`](trace_data_flow.md) - Focus on data flow rather than structure

---

**Last Updated**: 2026-02-20
**Version**: 1.1
