# Skill: Manage Queries

**Purpose**: Track questions, uncertainties, and items needing clarification during documentation

**Category**: project_management

---

## Prerequisites

- Project root directory exists
- Basic understanding of the codebase being documented

## Inputs

- **Required**:
  - `project_root`: Root directory path of the project
  - `action`: Action to perform (`init`, `add`, `resolve`, `report`)

- **Optional**:
  - `query_id`: Query ID (e.g., "Q3") for resolve action
  - `module`: Module name the query relates to
  - `question`: Question text
  - `context`: Why this question matters
  - `answer`: Answer text (for resolve action)

---

## Process

### Step 1: Initialize Queries File

Create `queries.md` if it doesn't exist.

```bash
# Check if queries file exists
ls queries.md

# If not exists, create from template
```

**Template Structure**:
```markdown
# Documentation Queries & Unknowns

**Purpose**: Track questions, uncertainties, and items needing clarification during documentation.

**Created**: [Date]

---

## Instructions

For each query:
- **Status**: "open" (needs answer) or "resolved" (answered)
- **Module**: Which module this relates to
- **Question**: What needs clarification
- **Context**: Why this matters for documentation
- **Answer**: Your response (filled in later)

---

## Queries

### Q1: [Module] - [Brief topic]
**Status**: open
**Module**: [module_name]
**Question**: [Your question here]
**Context**: [Why this matters]
**Answer**:

---

## Template for New Queries

```markdown
### Q#: [Module] - [Brief topic]
**Status**: open
**Module**: [module_name]
**Question**: [Your question here]
**Context**: [Why this matters]
**Answer**:

---
```

## Resolved Queries

(Queries will be moved here once answered)

---

**Last Updated**: [Date]
```

### Step 2: Add New Query

When you encounter something unclear during documentation:

1. Count existing queries to get next number (Q1, Q2, Q3, ...)
2. Add new entry under ## Queries section
3. Fill in all fields except Answer
4. Update "Last Updated" date

**Format**:
```markdown
### Q5: [Module] - [Brief topic]
**Status**: open
**Module**: risk
**Question**: What are the threshold values for the VaR confidence level based on? Basel III standards, industry convention, or empirical data?
**Context**: Users may want to understand the rationale or adjust for different portfolio types.
**Answer**:

---
```

### Step 3: Resolve Query

When you get an answer:

1. Find the query by ID
2. Change **Status** from "open" to "resolved"
3. Fill in **Answer** field
4. Move entire query to "Resolved Queries" section
5. Update "Last Updated" date

**Example**:
```markdown
### Q2: risk - Full metric names
**Status**: resolved
**Module**: risk
**Question**: What do the risk metric abbreviations stand for?
**Answer**: Found in __init__.py RISK_METRIC enum:
- VaR = Value at Risk (confirmed)
- CVaR = Conditional Value at Risk
- MDD = Maximum Drawdown (NOT "Mean Daily Deviation")
- SR = Sharpe Ratio
- SOR = Sortino Ratio (NOT "Standard Deviation of Returns")
- CR = Calmar Ratio
- IR = Information Ratio (NOT "Interest Rate")
- TR = Tracking Error (NOT "Total Return")
- BETA = Portfolio Beta
**Context**: Need accurate descriptions for API documentation.

---
```

### Step 4: Generate Query Report

List all open queries for review:

```bash
# Count queries by status
grep -c "**Status**: open" queries.md
grep -c "**Status**: resolved" queries.md

# List open queries
grep -A 5 "**Status**: open" queries.md
```

**Report Format**:
```
Query Status Report - 2026-02-06
================================

Total Queries: 12
- Open: 10 (83%)
- Resolved: 2 (17%)

Open Queries by Module:
- validation: 1
- risk: 4
- strategies: 1
- visualization: 1
- data: 1
- general: 2

High Priority (blocking documentation):
- Q9: risk - Missing function definitions
- Q10: risk - Potential bug in drawdown calculation

Medium Priority (enhances documentation):
- Q1: validation - Outlier detection threshold values
- Q5: visualization - Chart export formats and parameters

Low Priority (nice to have):
- Q3: general - Project size discrepancy
```

---

## Outputs

- **Primary**:
  - File: `queries.md`
  - Content: Structured list of questions and answers

- **Updates**:
  - New query entries
  - Resolved query entries (moved to "Resolved Queries" section)
  - Updated "Last Updated" timestamp

---

## Examples

### Example 1: Initialize Queries File

**Input**:
```
project_root: /path/to/project
action: init
```

**Process**:
1. Create queries.md from template
2. Set creation date
3. Add template example

**Output**:
```
Created: queries.md
Status: Ready for tracking questions
Template: Q1 placeholder added
```

### Example 2: Add New Query

**Input**:
```
project_root: /path/to/project
action: add
module: filter
question: "What is the typical/recommended noise standard deviation value for SceneFilter?"
context: "Need to document the noise_std parameter and provide guidance to users."
```

**Process**:
1. Read queries.md
2. Count existing queries (found 5)
3. Add Q6 entry under ## Queries
4. Update "Last Updated"
5. Save file

**Output**:
```
Added to queries.md:
- Q6: filter - Noise standard deviation value
Status: open
Total queries: 6 (6 open, 0 resolved)
```

### Example 3: Resolve Query

**Input**:
```
project_root: /path/to/project
action: resolve
query_id: Q2
answer: "Found in __init__.py RISK_METRIC enum: IR = Information Ratio (NOT Interest Rate)"
```

**Process**:
1. Read queries.md
2. Find Q2 entry
3. Change status to "resolved"
4. Fill in answer
5. Move entry to "Resolved Queries" section
6. Update "Last Updated"
7. Save file

**Output**:
```
Resolved: Q2 - risk - Full metric names
Moved to: Resolved Queries section
Total queries: 6 (5 open, 1 resolved)
```

### Example 4: Generate Report

**Input**:
```
project_root: /path/to/project
action: report
```

**Process**:
1. Read queries.md
2. Count queries by status
3. Group by module
4. Generate summary report

**Output**:
```
Query Status Report - 2026-02-06
================================

Total Queries: 12
- Open: 10 (83%)
- Resolved: 2 (17%)

Open Queries:
  Q1: validation - Outlier detection threshold value
  Q3: general - Project size discrepancy
  Q4: strategies - Strategy types
  Q5: visualization - Chart export formats and parameters
  Q6: data - Data source definitions
  Q7: general - Dependencies
  Q8: indicators - Technical indicator parameters
  Q9: risk - Missing function definitions
  Q10: risk - Potential bug in drawdown calculation
  Q11: risk - Placeholder implementations

Resolved Queries:
  Q2: risk - Full metric names

Recommendation: Review open queries with domain expert
```

---

## Validation

- [ ] queries.md exists and is well-formed
- [ ] All queries have unique IDs (Q1, Q2, Q3, ...)
- [ ] All queries have required fields (Status, Module, Question, Context)
- [ ] Resolved queries are in "Resolved Queries" section
- [ ] "Last Updated" date is current
- [ ] No duplicate query IDs

---

## Related Skills

- **Prerequisites**: None (can be used anytime during documentation)
- **Follow-ups**:
  - `manage_project_status.md` - Reference queries in blockers
  - `manage_changelog.md` - Log query resolutions as "Fixed"
- **Alternatives**: None (queries.md is the standard pattern)

---

## Tips

1. **Ask Early**: Add queries as soon as you encounter uncertainty (don't wait)
2. **Be Specific**: Provide enough context for someone else to answer
3. **Reference Code**: Include file names, line numbers, or function names
4. **Prioritize**: Note if a query is blocking vs. nice-to-have
5. **Cross-Reference**: Link queries to specific documentation sections
6. **Group Related**: If multiple queries relate to same topic, mention in context
7. **Resolve Promptly**: When you find answers, update immediately

---

## Query Categories

### Critical (blocks documentation)
- Missing information required for documentation
- Conflicting information in code
- Potential bugs that affect documentation accuracy

**Example**: "Function signature unclear - missing type hints and docstring"

### Important (enhances documentation quality)
- Recommended values, thresholds, or defaults
- Best practices or usage patterns
- Performance considerations

**Example**: "What are recommended noise_std values for different scenarios?"

### Nice-to-have (enriches documentation)
- Historical context or design rationale
- Alternative approaches
- Future plans or deprecation notices

**Example**: "Why was this specific algorithm chosen over alternatives?"

---

## When to Add Queries

Add a query when you encounter:

1. **Missing Information**:
   - Undocumented parameters
   - Unclear function purposes
   - Missing type information

2. **Conflicting Information**:
   - Code comments contradict implementation
   - Different files have different constant values
   - Documentation says one thing, code does another

3. **Unclear Design Decisions**:
   - Magic numbers without explanation
   - Complex algorithms without rationale
   - Unusual patterns or workarounds

4. **Potential Issues**:
   - Possible bugs in code
   - Missing error handling
   - Suspicious edge cases

5. **User-Facing Concerns**:
   - What should users know?
   - What are safe vs unsafe values?
   - What are common pitfalls?

---

**Last Updated**: 2026-02-06
**Version**: 1.0
