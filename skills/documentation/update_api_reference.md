# Skill: Update API Reference Documentation

**Purpose**: Update existing API reference documentation when code changes, adding new methods/functions while preserving existing content.

**Category**: documentation

---

## Prerequisites

- Existing API reference document created using [`generate_api_docs.md`](generate_api_docs.md)
- Code modifications have been made (new classes, methods, functions, or attributes)
- Familiarity with Markdown syntax and the structure of existing API docs
- Read [`../../knowledgebase/AGENT_PROMPT.md`](../../knowledgebase/AGENT_PROMPT.md) for project context and documentation standards

---

## Inputs

### Required
- **api_reference_file**: Absolute path to existing API reference file (e.g., `docs/api_reference/backtest.md`)
- **changed_files**: List of source files that have been modified
- **change_summary**: Description of code changes (new methods, parameters, etc.)

### Optional
- **preserve_examples**: Whether to keep existing code examples (default: `true`)
- **update_timestamp**: Whether to update last modified date (default: `true`)

---

## Process

### Step 1: Identify Code Changes

Analyze the changed source files to identify what has been added or modified.

**Compare against existing API reference**:
- Read the current API reference file
- Read the modified source files
- Identify new classes (not documented)
- Identify new methods (not documented)
- Identify new functions (not documented)
- Identify new attributes/properties (not documented)
- Identify modified parameters or return types
- Identify deprecated items

**Tools to use**:
- Read the API reference file
- Read the modified source files
- Use grep to search for class/function definitions

**Example output**:
```
New additions in engine.py:
- Method: BacktestEngine.get_performance_summary() -> dict[str, float]
- Method: BacktestEngine.export_results(format: str) -> str
- Attribute: BacktestEngine.metadata (dict)

Modified:
- BacktestEngine.run_backtest() - added optional parameter: `confidence_level: float = 0.95`
- Portfolio class - now has `rebalance_history` attribute
```

---

### Step 2: Read Existing API Reference

Open and read the entire existing API reference file.

**Use**: Read tool on api_reference_file

**Extract and preserve**:
- Header section (module name, package, location)
- Overview section (purpose description)
- Key Concepts section (if exists)
- All existing class/function documentation
- All existing examples
- See Also section

---

### Step 3: Locate Documentation Sections to Update

Find where to insert new documentation.

**For new classes**:
- Find the "## Classes" section
- Determine alphabetical position
- Mark insertion point

**For new methods**:
- Find the relevant class documentation
- Find the "**Methods**" subsection
- Determine insertion order (typically by name or logical grouping)

**For new functions**:
- Find the "## Functions" section
- Determine alphabetical position

**For modified items**:
- Find existing documentation
- Identify what needs updating (parameters, return type, description)

---

### Step 4: Document New Classes

For each new class, write complete documentation following the existing style.

**Template** (same as in generate_api_docs.md):
```markdown
### [ClassName]

[1-2 sentence description of what this class represents]

**Purpose**: [Why this class exists - what problem it solves]

**Attributes**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `attribute_name` | `type` | [Description] |

**Methods**:
- `method_name(param: type = default) -> return_type`: [Description]

**Example**:
```python
# Initialization and usage example
obj = ClassName(param="value")
result = obj.method_name()
print(result)  # Expected output
```

**See Also**:
- [Related Class](#related-class)
```

**Placement**: Insert in alphabetical order within Classes section

---

### Step 5: Document New Methods

For each new method, add to the existing class documentation.

**Template**:
```markdown
- `new_method(param1: type1, param2: type2 = default) -> return_type`: [One-line description]
```

**Placement**:
- Add to existing "**Methods**:" list of the class
- Insert in alphabetical order
- Or group logically with related methods

**If method is complex**:
- Can expand with subsection similar to class documentation
- Include full signature, parameters, returns, example

**Example addition to BacktestEngine class**:
```markdown
- `get_performance_summary() -> dict[str, float]`: Get summary of backtest performance metrics
- `export_results(format: str = "csv") -> str`: Export backtest results in specified format
```

---

### Step 6: Document New Functions

For standalone module functions, add to the Functions section.

**Template** (same as generate_api_docs.md):
```markdown
### [function_name]

```python
def function_name(param1: type1, param2: type2 = default) -> return_type:
```

[1-2 sentence description]

**Parameters**:
- `param1` (`type1`): [Description]

**Returns**:
- (`return_type`): [Description]

**Example**:
```python
result = function_name(value1)
print(result)
```
```

---

### Step 7: Update Method/Parameter Signatures

For existing items with modified signatures, update the documentation.

**Changes to document**:
- New parameters (mark as optional if they have defaults)
- Removed parameters (mark as deprecated or document in notes)
- Changed return types
- Changed parameter types

**Update template for modified methods**:
```markdown
- `existing_method(old_param: type, new_param: type = default) -> return_type`:
  Updated description if needed. [NEW: added `new_param` parameter]
```

**Example**:
```markdown
- `run_backtest(strategy: str, start_date: str, end_date: str, confidence_level: float = 0.95) -> BacktestResult`:
  Run a backtest with specified strategy and date range. [NEW: added optional `confidence_level` parameter for VaR/CVaR calculations (0.0-1.0)]
```

---

### Step 8: Add New Attributes

If new attributes/properties are added, update the Attributes table.

**Update existing table**:
```markdown
| Attribute | Type | Description |
|-----------|------|-------------|
| `existing_attr` | `type` | [Description] |
| `new_attr` | `new_type` | [Description] |  <!-- NEW -->
```

**Placement**:
- Insert in logical order (typically alphabetical)
- Mark with comment `<!-- NEW -->` for clarity

---

### Step 9: Preserve and Update Examples

For existing examples, verify they still work with code changes.

**For methods with unchanged signatures**:
- Keep existing examples
- No changes needed

**For methods with new parameters**:
- Update example to show new parameter usage
- Keep showing original usage if still valid
- Mark new parameter usage with comment

**Example of updated example**:
```python
# Original usage (still valid)
results = engine.run_backtest(
    strategy="momentum",
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# NEW: With confidence level parameter
results = engine.run_backtest(
    strategy="momentum",
    start_date="2024-01-01",
    end_date="2024-12-31",
    confidence_level=0.99  # Higher confidence for risk metrics
)
```

**Add examples for new methods**:
- Write minimal but complete examples
- Show typical usage pattern
- Include expected output

---

### Step 10: Update Timestamps and Version

Update metadata if enabled.

**If update_timestamp is true**:

1. Find "**Last Updated**:" line at end of file
   ```markdown
   **Last Updated**: 2026-02-06
   ```

2. Update to current date
   ```markdown
   **Last Updated**: 2026-02-07
   ```

3. Update version if appropriate
   ```markdown
   **Version**: 1.1  <!-- was 1.0 -->
   ```

**Version numbering**:
- Minor change (new method): increase minor version (1.0 → 1.1)
- Major restructure: increase major version (1.0 → 2.0)
- Documentation-only change: keep version same

---

### Step 11: Validate All Changes

Ensure documentation is complete and consistent.

**Verification**:
- [ ] All new classes documented
- [ ] All new methods documented
- [ ] All new functions documented
- [ ] All modified signatures updated
- [ ] Examples updated if affected
- [ ] No broken links
- [ ] Markdown formatting correct
- [ ] Related content cross-referenced

**Tools**:
- Manual review of updated sections
- Verify examples are syntactically correct
- Check links are valid

---

### Step 12: Stage for Version Control

Add the updated file to git.

**Use**: `git add docs/api_reference/<module_name>.md`

---

## Outputs

### Primary
- **Updated File**: Modified API reference with new sections
  - All existing content preserved
  - New classes documented
  - New methods/functions documented
  - Updated signatures for modified items
  - Examples verified or updated
  - Metadata (timestamps) updated

### Secondary
- **File staged in git**: Ready for commit

---

## Examples

### Example 1: Adding New Method to BacktestEngine Class

**Input**:
- api_reference_file: `docs/api_reference/backtest.md`
- changed_files: `src/midterm_stock_planner/backtest/engine.py`
- change_summary: "Added get_performance_summary() and export_results() methods"

**Code Change** (in engine.py):
```python
class BacktestEngine:
    # ... existing methods ...

    def get_performance_summary(self) -> dict[str, float]:
        """Get summary of backtest performance metrics."""
        return {
            "total_return": self._total_return,
            "sharpe_ratio": self._sharpe_ratio,
            "max_drawdown": self._max_drawdown,
            "win_rate": self._win_rate,
        }

    def export_results(self, format: str = "csv") -> str:
        """Export backtest results in specified format."""
        if format == "csv":
            return self._results_df.to_csv()
        elif format == "json":
            return self._results_df.to_json()
        raise ValueError(f"Unsupported format: {format}")
```

**Before** (in api_reference/backtest.md):
```markdown
### BacktestEngine

Core engine for running stock portfolio backtests over historical data.

...

**Methods**:
- `run_backtest(strategy: str, start_date: str, end_date: str) -> BacktestResult`: Run a backtest with specified strategy and date range
- `set_portfolio(tickers: list[str], weights: list[float])`: Configure portfolio tickers and allocation weights
- `add_benchmark(ticker: str)`: Add a benchmark ticker for comparison
- `get_trade_history() -> pd.DataFrame`: Get full trade history from the last backtest run
```

**After** (in api_reference/backtest.md):
```markdown
### BacktestEngine

Core engine for running stock portfolio backtests over historical data.

...

**Methods**:
- `add_benchmark(ticker: str)`: Add a benchmark ticker for comparison
- `export_results(format: str = "csv") -> str`: Export backtest results in specified format  <!-- NEW -->
- `get_performance_summary() -> dict[str, float]`: Get summary of backtest performance metrics  <!-- NEW -->
- `get_trade_history() -> pd.DataFrame`: Get full trade history from the last backtest run
- `run_backtest(strategy: str, start_date: str, end_date: str) -> BacktestResult`: Run a backtest with specified strategy and date range
- `set_portfolio(tickers: list[str], weights: list[float])`: Configure portfolio tickers and allocation weights

**Example**:
```python
from midterm_stock_planner.backtest import BacktestEngine

# Create and configure engine (as before)
engine = BacktestEngine(name="momentum_test")
engine.set_portfolio(tickers=["AAPL", "MSFT", "GOOG"], weights=[0.4, 0.3, 0.3])
engine.add_benchmark(ticker="SPY")
engine.run_backtest(strategy="momentum", start_date="2024-01-01", end_date="2024-12-31")

# NEW: Get performance summary
summary = engine.get_performance_summary()
print(f"Total Return: {summary['total_return']:.2%}")  # e.g., 0.15
print(f"Sharpe Ratio: {summary['sharpe_ratio']:.2f}")  # e.g., 1.42

# NEW: Export results
csv_output = engine.export_results(format="csv")
print(csv_output[:100])  # First 100 chars of CSV output

json_output = engine.export_results(format="json")
print(json_output[:100])  # First 100 chars of JSON output
```

**See Also**:
- [BacktestResult](#backtestresult) - Result container returned by run_backtest
- [Portfolio](#portfolio) - Portfolio configuration and holdings
```

**Timestamp Update**:
```markdown
**Last Updated**: 2026-02-07
**Version**: 1.1
```

---

### Example 2: Adding Parameter to Existing Method

**Code Change**:
```python
def run_backtest(self, strategy: str, start_date: str, end_date: str,
                 confidence_level: float = 0.95) -> BacktestResult:  # NEW parameter
    """Run backtest with optional confidence level for risk metrics."""
```

**Before** (existing method):
```markdown
- `run_backtest(strategy: str, start_date: str, end_date: str) -> BacktestResult`: Run a backtest with specified strategy and date range
```

**After** (updated method):
```markdown
- `run_backtest(strategy: str, start_date: str, end_date: str, confidence_level: float = 0.95) -> BacktestResult`: Run a backtest with specified strategy and date range, using optional confidence level for VaR/CVaR calculations  <!-- NEW: added confidence_level parameter -->
```

**Updated Example**:
```python
# Original usage (still valid)
engine.run_backtest(
    strategy="momentum",
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# NEW: With confidence level for risk metrics
engine.run_backtest(
    strategy="momentum",
    start_date="2024-01-01",
    end_date="2024-12-31",
    confidence_level=0.99  # 99% confidence for VaR/CVaR calculations
)
```

---

### Example 3: Adding New Attribute to Class

**Code Change**:
```python
class BacktestEngine:
    def __init__(self, name: str) -> None:
        self._name = name
        self._portfolio = None
        self._results = None
        self.metadata = {}  # NEW attribute
```

**Before** (existing attributes):
```markdown
**Attributes**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Engine identifier (e.g., "momentum_test") |
| `portfolio` | `Portfolio` | Portfolio configuration with tickers and weights |
| `results` | `BacktestResult | None` | Results from the last backtest run |
| `benchmark` | `str` | Benchmark ticker symbol (e.g., "SPY") |
| `trade_log` | `list[dict]` | Log of all trades executed during backtest |
```

**After** (with new attribute):
```markdown
**Attributes**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Engine identifier (e.g., "momentum_test") |
| `portfolio` | `Portfolio` | Portfolio configuration with tickers and weights |
| `results` | `BacktestResult | None` | Results from the last backtest run |
| `benchmark` | `str` | Benchmark ticker symbol (e.g., "SPY") |
| `trade_log` | `list[dict]` | Log of all trades executed during backtest |
| `metadata` | `dict` | Custom metadata for backtest run (e.g., data source, run date) <!-- NEW --> |
```

---

## Validation Checklist

- [ ] Existing content fully preserved (no accidental deletions)
- [ ] All new classes documented with attributes, methods, examples
- [ ] All new methods added to existing class documentation
- [ ] All new functions documented with parameters, returns, examples
- [ ] All modified method signatures updated (parameters, return types)
- [ ] All new attributes added to attribute tables
- [ ] Examples are syntactically correct and reflect current code
- [ ] Documentation style matches existing content (formatting, tone)
- [ ] Cross-references and "See Also" sections updated if relevant
- [ ] Timestamps updated if new content added
- [ ] Version number incremented appropriately
- [ ] No markdown formatting errors
- [ ] No broken links
- [ ] File ready for git staging

---

## Related Skills

### Prerequisites
- [`generate_api_docs.md`](generate_api_docs.md) - Create initial API reference
- [`../code_exploration/analyze_module.md`](../code_exploration/analyze_module.md) - Understand code changes

### Follow-ups
- [`add_docstrings.md`](add_docstrings.md) - Update source code docstrings to match API docs
- [`../validation/check_doc_coverage.md`](../validation/check_doc_coverage.md) - Verify all code documented

### Related
- [`generate_api_docs.md`](generate_api_docs.md) - Generate new API reference documents
- [`../code_exploration/analyze_module.md`](../code_exploration/analyze_module.md) - Analyze module structure

---

**Last Updated**: 2026-02-20
**Version**: 1.0
