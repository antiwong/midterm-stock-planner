# Check Documentation Coverage

## Purpose

Verify that all modules, classes, and functions in the codebase are adequately documented. This skill ensures comprehensive API documentation coverage by identifying gaps and measuring documentation completeness across the project.

## Prerequisites

- API reference documentation has been created and structured
- Source code has been analyzed to identify all public APIs
- Documentation directory structure is in place
- Tools for scanning code and documentation available (e.g., Python AST parser, documentation generators)

## Process

### Step 1: List All Public APIs

Scan the codebase to identify all public modules, classes, functions, and methods:

```
1. Traverse project source code directory
2. For each Python module (.py file):
   - Parse using AST (Abstract Syntax Tree)
   - Identify top-level functions (not starting with _)
   - Identify classes (not starting with _)
   - Identify class methods and properties (not starting with _)
3. Compile comprehensive list of public APIs
4. Organize by module/class hierarchy
```

Example structure:
```
- module: scene
  - class: SceneManager (public)
  - class: SceneLoader (public)
  - class: SceneValidator (public)
  - class: SceneBuilder (public)
  - function: load_scene()
  - function: validate_scene_data()

- module: processors
  - class: DataProcessor (public)
  - class: TransformProcessor (public)
  - function: process_data()
```

### Step 2: Check Documentation Status

For each identified public API:

```
1. Search documentation files for references
   - Check API reference docs (.md files)
   - Look for docstrings in source code
   - Verify examples in documentation
2. For each API item, determine:
   - Documented: Yes/No
   - Has description: Yes/No
   - Has parameters documented: Yes/No
   - Has return value documented: Yes/No
   - Has examples: Yes/No
3. Flag items with incomplete documentation
```

### Step 3: Calculate Coverage Percentage

```
1. Count total public APIs
2. Count documented APIs
3. Calculate: (Documented APIs / Total APIs) × 100
4. Calculate by category:
   - Module coverage: %
   - Class coverage: %
   - Function coverage: %
   - Method coverage: %
```

### Step 4: Generate Coverage Report

Create a detailed report including:

```
1. Overall statistics
   - Total public APIs found
   - Total documented
   - Total missing documentation
   - Overall coverage percentage

2. By category breakdown
   - Modules: count (documented/total)
   - Classes: count (documented/total)
   - Functions: count (documented/total)
   - Methods: count (documented/total)

3. Missing documentation details
   - List each undocumented item
   - Note type (function, class, method)
   - Indicate parent module/class
   - Priority level (high: core APIs, medium: utility, low: internal)

4. Gap analysis
   - Critical missing items
   - Modules with low coverage
   - Recommendations for priority documentation
```

## Outputs

### Coverage Report (coverage_report.md)

Structure:
```
# Documentation Coverage Report

Generated: [timestamp]
Coverage Target: 80%

## Summary

| Metric | Count | Documented | Coverage |
|--------|-------|------------|----------|
| Total APIs | XX | XX | XX% |
| Modules | XX | XX | XX% |
| Classes | XX | XX | XX% |
| Functions | XX | XX | XX% |
| Methods | XX | XX | XX% |

## Detailed Findings

### Module: [module_name]
- Coverage: XX%
- Documented Classes: X/X
- Documented Functions: X/X
- Missing Items:
  - [Item Name] (type: [class|function])

### Critical Gaps
- [High priority undocumented APIs]

### Coverage by Type
- [Breakdown by API type]
```

### Missing Items List (missing_documentation.json)

```json
{
  "undocumented": [
    {
      "name": "SceneManager",
      "type": "class",
      "module": "scene",
      "priority": "high",
      "reason": "Core API"
    },
    {
      "name": "validate_transform",
      "type": "function",
      "module": "processors.validation",
      "priority": "medium",
      "reason": "Public utility function"
    }
  ],
  "partially_documented": [
    {
      "name": "DataProcessor",
      "type": "class",
      "module": "processors",
      "missing_sections": ["return values", "examples"],
      "priority": "medium"
    }
  ]
}
```

## Examples

### Example 1: Backtest Module Coverage Check

Checking documentation completeness for the backtest module:

```
Module: backtest
Public Classes Found: 4
  - BacktestEngine ✓ (documented)
  - BacktestConfig ✓ (documented)
  - BacktestResults ✓ (documented)
  - RunRecord ✓ (documented)

Module Coverage: 100% (4/4)

Documentation Completeness:
  - BacktestEngine
    ✓ Description: Complete
    ✓ Methods: 8/8 documented
    ✓ Examples: Present

  - BacktestConfig
    ✓ Description: Complete
    ✓ Methods: 5/5 documented
    ✓ Examples: Present

  - BacktestResults
    ✓ Description: Complete
    ✓ Methods: 3/3 documented
    ✗ Examples: Missing

  - RunRecord
    ✓ Description: Complete
    ✓ Methods: 6/6 documented
    ✓ Examples: Present
```

### Example 2: Processor Module with Gaps

```
Module: processors
Public Classes Found: 3
  - DataProcessor ✓ (documented)
  - TransformProcessor ✗ (missing)
  - ValidationProcessor ✓ (documented)

Module Coverage: 66.7% (2/3)

Gap Analysis:
  TransformProcessor (PRIORITY: HIGH)
  - Type: Core class
  - Status: Completely undocumented
  - Recommendation: Add to documentation immediately
```

### Example 3: Coverage Trend

```
Coverage Timeline:
- Week 1: 65% coverage
- Week 2: 72% coverage
- Week 3: 78% coverage
- Week 4: 85% coverage ✓ Target met

Improvement: +20% in 4 weeks
Rate: ~5% per week
```

## Validation Checklist

Use this checklist to validate documentation coverage:

- [ ] **Coverage Minimum Met**: Overall coverage ≥ 80%
- [ ] **Critical APIs Documented**: All high-priority APIs documented
  - [ ] All public classes have descriptions
  - [ ] All public functions have descriptions
  - [ ] All class methods have descriptions
- [ ] **No Core Module Below 80%**: Each major module meets coverage target
  - [ ] Backtest module ≥ 80%
  - [ ] Processors module ≥ 80%
  - [ ] Validation module ≥ 80%
  - [ ] Utilities module ≥ 80%
- [ ] **Documentation Quality**: Documented items are complete
  - [ ] Descriptions are clear and accurate
  - [ ] Parameters are documented
  - [ ] Return values are documented
  - [ ] Examples are provided for key APIs
- [ ] **No Undocumented Critical APIs**: Zero critical APIs without documentation
- [ ] **Examples Provided**: Key modules have usage examples
- [ ] **Report Generated**: Coverage report created and reviewed
- [ ] **Gaps Addressed**: Missing documentation items have been scheduled/completed

## Related Skills

- [generate_api_reference.md](../documentation/generate_api_reference.md) - Create API documentation
- [validate_docstrings.md](../validation/validate_docstrings.md) - Check docstring quality
- [generate_examples.md](../documentation/generate_examples.md) - Create usage examples

## Notes

- Coverage target of 80% balances comprehensiveness with maintainability
- Critical APIs (core classes/functions) should have priority documentation
- Examples significantly improve documentation value beyond basic descriptions
- Regular coverage checks (weekly/monthly) help maintain documentation quality
- Use automated tools to scan for undocumented APIs to reduce manual effort
