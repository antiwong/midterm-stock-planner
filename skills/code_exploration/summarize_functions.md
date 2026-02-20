# Skill: Summarize Functions

**Purpose**: Generate a quick overview of all functions and methods in a module to understand what utilities and capabilities are available.

**Category**: code_exploration

---

## Prerequisites

- Familiarity with Python syntax and docstrings
- Access to the midterm_stock_planner codebase
- Module already analyzed (see [`analyze_module.md`](analyze_module.md) for full structural analysis)
- Read [`../../knowledgebase/AGENT_PROMPT.md`](../../knowledgebase/AGENT_PROMPT.md) for project context

---

## Inputs

### Required
- **module_name**: Name of the module (e.g., `analytics`, `risk`, `backtest`, `models`)
- **module_path**: Absolute path to module directory (e.g., `/Users/antiwong/Documents/code/my_code/stock_all/midterm-stock-planner/src/midterm_stock_planner/analytics/`)

### Optional
- **include_private**: Include private functions (starting with `_`) (default: `false`)
- **group_by**: How to organize functions (default: `file`)
  - `file`: Group by source file
  - `purpose`: Group by inferred purpose (requires inference)
  - `name_pattern`: Group by function name prefix (e.g., compute_, check_, train_)
- **output_format**: Format for output (default: `markdown_table`)
  - `markdown_table`: Markdown table (good for markdown docs)
  - `markdown_list`: Markdown list (good for quick reference)
  - `csv`: CSV format (for spreadsheet import)

---

## Process

### Step 1: List All Python Files

List all Python files in the module directory.

**Using Glob tool**:
```
Pattern: <module_path>/**/*.py
Or for single directory: <module_path>/*.py
```

**Take Note Of**:
- Total file count
- Whether to include subdirectories
- Example: analytics has multiple files in root directory

---

### Step 2: Extract All Function Signatures

For each Python file, extract:
- **Function name**: Exact name as defined
- **Parameters**: Full parameter list with types (if annotated)
- **Return type**: If annotated
- **Location**: File name and line number

**Using Grep tool**:
```
Pattern: ^def\s+\w+\s*\(
Or for more detail: ^def\s+\w+\s*\([^)]*\):
```

**Take Note Of**:
- Total function count (before filtering)
- Private functions (starting with `_`)
- Nested functions (inside classes - usually skip these)
- Async functions (starting with `async def`)

---

### Step 3: Extract Docstrings

For each function, extract the docstring (first line or first few lines):

**Using Read tool**:
- Read each function definition
- Extract docstring if present (immediately after `def` line)
- Document docstring format (e.g., "single-line", "multi-line", "numpy style")

**Take Note Of**:
- How many functions have docstrings
- Docstring quality/completeness
- Common docstring patterns

**Example**:
```python
def compute_sharpe_ratio(df, risk_free_rate=0.02):
    """Calculate the Sharpe ratio for a given returns series."""
    # Has docstring: "Calculate the Sharpe ratio for a given returns series."
```

---

### Step 4: Infer Purpose from Name and Signature

For functions without docstrings, infer purpose from:
- **Function name pattern**:
  - `compute_*` → Computational/metric operations
  - `get_*` → Retrieval/accessor operations
  - `is_*` → Checks/validations (returns boolean)
  - `has_*` → Checks/validations (returns boolean)
  - `calculate_*` → Computational operations
  - `convert_*` / `transform_*` → Transformation operations
  - `create_*` / `build_*` → Construction operations
  - `validate_*` / `check_*` → Validation operations
  - `export_*` / `import_*` → I/O operations
  - `train_*` / `predict_*` / `fit_*` → Model operations
  - `sort_*` / `filter_*` / `group_*` → Data manipulation

- **Parameter types**:
  - Takes `df: pd.DataFrame` parameter → Data analysis function
  - Takes `config: AppConfig` parameter → Configuration-related function
  - Takes `portfolio: dict` parameter → Portfolio-related function
  - Takes `ticker: str` parameter → Single-stock function

- **Return type**:
  - Returns `bool` → Validation/check function
  - Returns `list`, `dict` → Search/retrieval function
  - Returns numeric → Calculation function

---

### Step 5: Group Functions

Organize functions by selected grouping strategy:

**Option 1: Group by File**
```
## risk.py (45 functions)
- check_concentration_limit(portfolio, config) - Check if position exceeds limit
- check_drawdown_limit(df, config) - Check if drawdown exceeds threshold
- ...

## analytics.py (20 functions)
- compute_sharpe_ratio(df, risk_free_rate) - Calculate Sharpe ratio
- ...
```

**Option 2: Group by Purpose**
```
## Risk Checks (10 functions)
- check_concentration_limit()
- check_drawdown_limit()
- ...

## Performance Metrics (15 functions)
- compute_sharpe_ratio()
- compute_sortino_ratio()
- ...

## Model Operations (20 functions)
- train_model()
- ...
```

**Option 3: Group by Name Pattern**
```
## compute_* (25 functions)
- compute_sharpe_ratio()
- compute_sortino_ratio()
- ...

## check_* (15 functions)
- check_concentration_limit()
- ...

## train_* (10 functions)
- train_model()
- ...
```

---

### Step 6: Create Summary Table

Format results as structured output:

**For markdown_table format**:
```markdown
| Function | File | Parameters | Return | Purpose |
|----------|------|-----------|--------|---------|
| compute_sharpe_ratio | analytics.py | df, risk_free_rate | float | Calculate Sharpe ratio |
| check_concentration_limit | risk.py | portfolio, config | bool | Check if position exceeds limit |
| ... | ... | ... | ... | ... |
```

**For markdown_list format**:
```markdown
- `compute_sharpe_ratio(df, risk_free_rate=0.02)` → `float`
  - File: analytics.py (line 45)
  - Purpose: Calculate Sharpe ratio for returns series
  - Docstring: "Calculate the Sharpe ratio for a given returns series."

- `check_concentration_limit(portfolio, config)` → `bool`
  - File: risk.py (line 120)
  - Purpose: Check if any position exceeds concentration limit
  - Status: No docstring
```

---

### Step 7: Add Summary Statistics

Include overview information:

```markdown
## Summary Statistics

- **Total Functions**: 85
- **Public Functions**: 85 (100%)
- **Private Functions**: 0 (0%)
- **With Docstrings**: 35 (41%)
- **Without Docstrings**: 50 (59%)
- **Type Hints**: 10 (12%)

## Grouping Breakdown
- By File:
  - risk.py: 45 functions
  - analytics.py: 20 functions
  - models.py: 15 functions
  - features.py: 5 functions

- By Purpose:
  - Risk Checks: 10 functions (12%)
  - Performance Metrics: 25 functions (29%)
  - Model Operations: 30 functions (35%)
  - Utilities: 20 functions (24%)
```

---

### Step 8: Add Quality Notes

Document observations about function quality:

```markdown
## Quality Assessment

### Strengths
- Consistent naming conventions (all compute_* functions follow same pattern)
- Good parameter naming (descriptive parameter names)
- Return types generally consistent

### Gaps
- 59% of functions missing docstrings
- Limited type hints (only 12% have annotations)
- Some functions have unclear purposes (inferred from name only)
- Long parameter lists (some functions take 5+ parameters)

### Recommendations
- Add docstrings for risk.py functions (highest priority)
- Add return type hints for validation functions
- Consider breaking down functions with 5+ parameters
- Group similar functions with common docstring template
```

---

## Outputs

### Primary
- **Function Summary Table**: Markdown table or list of all functions with metadata
- **Summary Statistics**: Counts and percentages
- **Quality Assessment**: Observations about documentation and style

### Secondary
- **Grouped Lists**: Functions organized by file, purpose, or pattern
- **Coverage Report**: What areas are well-documented vs gaps
- **Recommendations**: Suggestions for improvement

---

## Examples

### Example 1: Quick Summary of analytics Module (80+ Functions)

**Input**:
- module_name: `analytics`
- module_path: `/Users/antiwong/Documents/code/my_code/stock_all/midterm-stock-planner/src/midterm_stock_planner/analytics/`
- include_private: `false`
- group_by: `file`
- output_format: `markdown_table`

**Process**:
1. List files: risk.py, analytics.py, models.py, features.py, backtest.py
2. Extract functions from each file using grep
3. Read each function to get docstring (if exists)
4. Infer purpose from name and parameters
5. Group by file and create table

**Output**:

```markdown
# Function Summary: analytics Module

## Overview
- **Module**: analytics
- **Purpose**: Performance metrics, risk management, model training, feature engineering
- **Total Functions**: 85
- **Public Functions**: 85 (100%)
- **Functions with Docstrings**: 35 (41%)

## Summary by File

### risk.py (45 functions)

| Function | Parameters | Return | Purpose |
|----------|-----------|--------|---------|
| check_concentration_limit | portfolio: dict, config: AppConfig | bool | Check if any position exceeds concentration limit |
| check_drawdown_limit | df: pd.DataFrame, config: AppConfig | bool | Check if drawdown exceeds maximum threshold |
| compute_var | df: pd.DataFrame, confidence: float | float | Calculate Value at Risk at confidence level |
| check_sector_exposure | portfolio: dict, config: AppConfig | bool | Check if sector allocation exceeds limit |
| is_portfolio_balanced | portfolio: dict | bool | Check if portfolio weights sum to 1.0 |
| is_position_oversized | portfolio: dict, ticker: str | bool | Check if single position is too large |
| has_sufficient_diversification | portfolio: dict, config: AppConfig | bool | Check if portfolio meets diversification rules |
| has_exceeded_loss_limit | df: pd.DataFrame, config: AppConfig | bool | Check if cumulative loss exceeds threshold |
| get_portfolio_beta | portfolio: dict, df: pd.DataFrame | float | Get portfolio beta relative to benchmark |
| get_position_weight | portfolio: dict, ticker: str | float | Get weight of a single position |
| get_sector_weights | portfolio: dict | dict | Get allocation by sector |
| get_risk_contribution | portfolio: dict, df: pd.DataFrame | dict | Calculate risk contribution per position |
| get_portfolio_exposure | portfolio: dict | dict | Get long/short exposure breakdown |
| get_max_drawdown | df: pd.DataFrame | float | Get maximum drawdown from peak |
| compute_expected_shortfall | df: pd.DataFrame, confidence: float | float | Calculate expected shortfall (CVaR) |
| compute_tracking_error | df: pd.DataFrame, benchmark: pd.DataFrame | float | Calculate tracking error vs benchmark |
| compute_information_ratio | df: pd.DataFrame, benchmark: pd.DataFrame | float | Calculate information ratio |
| normalize_weights | portfolio: dict | dict | Normalize portfolio weights to sum to 1.0 |
| clip_position_size | portfolio: dict, config: AppConfig | dict | Clip position sizes to max allowed |
| rebalance_portfolio | portfolio: dict, config: AppConfig | dict | Rebalance to target weights |
| compute_correlation_matrix | df: pd.DataFrame | pd.DataFrame | Compute pairwise correlation matrix |
| ... | ... | ... | ... |

**Statistics**:
- Functions with docstrings: 18 (40%)
- Functions without docstrings: 27 (60%)
- Validation functions (check_*, is_*, has_*): 15 (33%)
- Calculation functions: 20 (44%)
- Accessor functions (get_*): 10 (23%)

### analytics.py (20 functions)

| Function | Parameters | Return | Purpose |
|----------|-----------|--------|---------|
| compute_sharpe_ratio | df: pd.DataFrame, risk_free_rate: float | float | Calculate annualized Sharpe ratio |
| compute_sortino_ratio | df: pd.DataFrame, risk_free_rate: float | float | Calculate Sortino ratio using downside deviation |
| run_monte_carlo | df: pd.DataFrame, config: AppConfig, n_sims: int | dict | Run Monte Carlo simulation for returns |
| compute_cagr | df: pd.DataFrame | float | Calculate compound annual growth rate |
| compute_volatility | df: pd.DataFrame, window: int | pd.Series | Calculate rolling volatility |
| compute_calmar_ratio | df: pd.DataFrame | float | Calculate Calmar ratio (return / max drawdown) |
| compute_omega_ratio | df: pd.DataFrame, threshold: float | float | Calculate Omega ratio |
| compute_rolling_returns | df: pd.DataFrame, window: int | pd.Series | Calculate rolling period returns |
| compute_cumulative_returns | df: pd.DataFrame | pd.Series | Calculate cumulative returns series |
| compute_drawdown_series | df: pd.DataFrame | pd.Series | Calculate drawdown series from peak |
| ... | ... | ... | ... |

**Statistics**:
- All 20 functions have docstrings: 100%
- All follow compute_* or run_* naming pattern
- Common parameters: df, config, risk_free_rate

### models.py (15 functions)

| Function | Parameters | Return | Purpose |
|----------|-----------|--------|---------|
| train_model | df: pd.DataFrame, config: AppConfig | object | Train ranking model on historical data |
| predict_rankings | df: pd.DataFrame, config: AppConfig | pd.DataFrame | Predict stock rankings for next period |
| compute_feature_importance | df: pd.DataFrame, config: AppConfig | dict | Calculate feature importance scores |
| ... | ... | ... | ... |

### features.py (5 functions)

| Function | Parameters | Return | Purpose |
|----------|-----------|--------|---------|
| compute_rsi | df: pd.DataFrame, ticker: str, period: int | pd.Series | Calculate Relative Strength Index |
| compute_macd | df: pd.DataFrame, ticker: str | pd.DataFrame | Calculate MACD indicator and signal line |
| compute_atr | df: pd.DataFrame, ticker: str, period: int | pd.Series | Calculate Average True Range |
| compute_bollinger_bands | df: pd.DataFrame, ticker: str, window: int | pd.DataFrame | Calculate Bollinger Bands |
| compute_obv | df: pd.DataFrame, ticker: str | pd.Series | Calculate On-Balance Volume |
| ... | ... | ... | ... |

## Overall Statistics

- **Total Functions**: 85
- **By Category**:
  - Risk Checks (check_*, is_*, has_*): 15 (18%)
  - Performance Metrics (compute_*, run_*): 20 (24%)
  - Model Operations (train_*, predict_*): 30 (35%)
  - Accessors (get_*): 10 (12%)
  - Other utilities: 10 (12%)

- **Documentation**:
  - With docstrings: 35 (41%)
  - Without docstrings: 50 (59%)
  - With type hints: 10 (12%)
  - Without type hints: 75 (88%)

- **By File**:
  - risk.py: 45 (53%) - Risk management utilities
  - analytics.py: 20 (24%) - Performance metrics
  - models.py: 15 (18%) - Model training and prediction
  - features.py: 5 (6%) - Technical indicator features

## Quality Assessment

### Strengths
- Consistent naming conventions (compute_*, check_*, train_* patterns are clear)
- Well-organized by file (related functions grouped together)
- Analytics functions have complete docstrings
- Good function granularity (single-purpose functions)

### Gaps
- risk.py functions lack docstrings (60% missing)
- Limited type hints across all files
- No parameter documentation in most docstrings
- Some utility functions could be grouped better

### Recommendations
1. **High Priority**: Add docstrings to risk.py functions (especially validation functions)
2. **Medium Priority**: Add type hints to all function signatures
3. **Low Priority**: Consider creating constants file for numeric thresholds
4. **Documentation**: Create conceptual guide for risk management concepts
```

---

### Example 2: Summary with Grouping by Purpose

**Input**:
- module_name: `analytics`
- module_path: `/Users/antiwong/Documents/code/my_code/stock_all/midterm-stock-planner/src/midterm_stock_planner/analytics/`
- group_by: `purpose`
- output_format: `markdown_list`

**Output**:

```markdown
# Function Summary: analytics Module (By Purpose)

## Risk Validation Functions (15 functions, 18%)

Check boolean conditions about portfolios, positions, and risk limits.

- `check_concentration_limit(portfolio: dict, config: AppConfig) → bool` [risk.py:120]
  - Docstring: "Check if any position exceeds concentration limit"
  - Purpose: Validate single-position concentration risk

- `check_drawdown_limit(df: pd.DataFrame, config: AppConfig) → bool` [risk.py:135]
  - Docstring: "Check if drawdown exceeds maximum threshold"
  - Purpose: Validate portfolio drawdown against limit

- `check_sector_exposure(portfolio: dict, config: AppConfig) → bool` [risk.py:150]
  - Purpose: Check if sector allocation exceeds limit (inferred from name)

- `is_portfolio_balanced(portfolio: dict) → bool` [risk.py:165]
  - Docstring: "Check if portfolio weights sum to 1.0"

- `is_position_oversized(portfolio: dict, ticker: str) → bool` [risk.py:180]
  - Docstring: "Check if single position exceeds max size"

- `has_sufficient_diversification(portfolio: dict, config: AppConfig) → bool` [risk.py:195]
  - Docstring: "Check if portfolio meets diversification rules"

- `has_exceeded_loss_limit(df: pd.DataFrame, config: AppConfig) → bool` [risk.py:210]
  - Docstring: "Check if cumulative loss exceeds threshold"

- `compute_var(df: pd.DataFrame, confidence: float) → float` [risk.py:280]
  - Docstring: "Calculate Value at Risk at given confidence level"

- ... (7 more validation functions)

## Performance Metric Functions (20 functions, 24%)

Compute numeric performance and risk-adjusted return metrics.

- `compute_sharpe_ratio(df: pd.DataFrame, risk_free_rate: float) → float` [analytics.py:310]
  - Docstring: "Calculate annualized Sharpe ratio"

- `compute_sortino_ratio(df: pd.DataFrame, risk_free_rate: float) → float` [analytics.py:325]
  - Docstring: "Calculate Sortino ratio using downside deviation"

- `compute_cagr(df: pd.DataFrame) → float` [analytics.py:340]
  - Docstring: "Calculate compound annual growth rate"

- `compute_volatility(df: pd.DataFrame, window: int) → pd.Series` [analytics.py:355]
  - Docstring: "Calculate rolling volatility over window"

- `compute_expected_shortfall(df: pd.DataFrame, confidence: float) → float` [risk.py:370]
  - Docstring: "Calculate expected shortfall (CVaR) at confidence level"

- ... (15 more calculation functions)

## Model/Prediction Functions (30 functions, 35%)

Train models, generate predictions, and evaluate model performance.

- `train_model(df: pd.DataFrame, config: AppConfig) → object` [models.py:45]
  - Docstring: "Train ranking model on historical data"

- `predict_rankings(df: pd.DataFrame, config: AppConfig) → pd.DataFrame` [models.py:70]
  - Docstring: "Predict stock rankings for next period"

- `compute_feature_importance(df: pd.DataFrame, config: AppConfig) → dict` [models.py:95]
  - Docstring: "Calculate feature importance scores from trained model"

- `compute_rsi(df: pd.DataFrame, ticker: str, period: int) → pd.Series` [features.py:20]
  - Docstring: "Calculate Relative Strength Index for ticker"

- ... (26 more model/feature functions)

## Accessor Functions (10 functions, 12%)

Retrieve single values or perform simple lookups.

- `get_portfolio_beta(portfolio: dict, df: pd.DataFrame) → float` [risk.py:400]
  - Docstring: "Get portfolio beta relative to benchmark"

- `get_position_weight(portfolio: dict, ticker: str) → float` [risk.py:415]
  - Docstring: "Get weight of a single position in portfolio"

- `get_sector_weights(portfolio: dict) → dict` [risk.py:430]
  - Docstring: "Get allocation breakdown by sector"

- `get_risk_contribution(portfolio: dict, df: pd.DataFrame) → dict` [risk.py:445]
  - Docstring: "Calculate risk contribution per position"

- `get_max_drawdown(df: pd.DataFrame) → float` [risk.py:460]
  - Docstring: "Get maximum drawdown from peak"

- ... (5 more accessor functions)

## Utility Functions (10 functions, 12%)

Helper functions for data transformation and I/O.

- `normalize_weights(portfolio: dict) → dict` [risk.py:475]
  - Purpose: Normalize portfolio weights to sum to 1.0 (inferred)

- `clip_position_size(portfolio: dict, config: AppConfig) → dict` [risk.py:490]
  - Purpose: Clip position sizes to maximum allowed (inferred)

- ... (8 more utility functions)
```

---

## Validation

Use this checklist to ensure complete function summary:

- [ ] All Python files in module identified
- [ ] All public functions extracted (def, not _def)
- [ ] Private functions handled appropriately (excluded if include_private=false)
- [ ] Docstrings extracted for functions that have them
- [ ] Functions without docstrings noted
- [ ] Purpose inferred for undocumented functions
- [ ] Parameters and return types documented (if available)
- [ ] Functions organized by selected grouping strategy
- [ ] Summary statistics calculated and verified
- [ ] Quality assessment completed
- [ ] Total function count validated against original list
- [ ] Output formatted in selected format (table/list/csv)

---

## Related Skills

### Prerequisites
- [`analyze_module.md`](analyze_module.md) - For full module structure analysis (optional but recommended)

### Follow-ups
- [`../documentation/generate_api_docs.md`](../documentation/generate_api_docs.md) - Create full API reference using summary
- [`../documentation/add_docstrings.md`](../documentation/add_docstrings.md) - Add missing docstrings to functions
- [`../documentation/generate_function_catalog.md`](../documentation/generate_function_catalog.md) - Create searchable function catalog

### Complementary
- [`analyze_module.md`](analyze_module.md) - Detailed structural analysis
- [`trace_data_flow.md`](trace_data_flow.md) - Follow data flow through functions
- [`find_dependencies.md`](find_dependencies.md) - Map function dependencies

---

**Last Updated**: 2026-02-07
**Version**: 1.0
