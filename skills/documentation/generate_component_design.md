# Skill: Generate Component Design

**Purpose**: Create a component design document following documentation guidelines for a module in `doc/design/2_component_designs/`.

**Category**: documentation

---

## Prerequisites

- Module has been analyzed using [`../code_exploration/analyze_module.md`](../code_exploration/analyze_module.md)
- API reference documentation created using [`generate_api_docs.md`](generate_api_docs.md)
- Read [`../../prompt/documentation_guidelines.md`](../../prompt/documentation_guidelines.md) for design doc standards
- Familiarity with Markdown and Mermaid diagram syntax
- Understand the module's purpose, inputs, outputs, and algorithms

---

## Inputs

### Required
- **module_name**: Name of the module (e.g., `backtest`, `analytics`, `risk`)
- **component_name**: Name of the component being designed (e.g., `backtest_engine`, `risk_management`)
- **module_path**: Absolute path to module directory
- **analysis_summary**: Output from `analyze_module.md` skill

### Optional
- **include_algorithms**: Whether to reference algorithm designs (default: `true`)
- **algorithm_count**: Number of related algorithms to document (default: `1`)
- **classification**: Document classification level (default: `Internal`)

---

## Process

### Step 1: Generate Document ID

Create a unique document identifier following the naming convention.

**Format**: `[MODULE]-CD-[COMPONENT]-001`

**Rules**:
- MODULE: 3-letter abbreviation (e.g., MSP = Midterm Stock Planner)
- CD: Always "CD" for Component Design
- COMPONENT: Abbreviation of component name (e.g., BACKTEST, RISK, ANALYTICS, MODELS)
- Number: Always start with 001

**Examples**:
- `MSP-CD-BACKTEST-001` for Backtest Engine
- `MSP-CD-RISK-001` for Risk Management
- `MSP-CD-ANALYTICS-001` for Analytics
- `MSP-CD-MODELS-001` for ML Models

---

### Step 2: Create Component Design File

Create the Markdown file in the correct location.

**File Path**: `doc/design/2_component_designs/<component_name>.md`

**Naming Rules**:
- Use snake_case for filenames
- Match component name to module functionality
- Examples:
  - Backtest Engine → `backtest_engine.md`
  - Risk Management → `risk_management.md`
  - Portfolio Optimization → `portfolio_optimization.md`

---

### Step 3: Write Header Section

Add metadata header with document information.

**Template**:
```markdown
# [Component] Component Design

**Document ID**: [MODULE]-CD-[ABBR]-001
**Version**: 1.0
**Date**: [YYYY-MM-DD]
**Classification**: Internal
**Prepared by**: Documentation Team
**Approved by**: Pending Review

---
```

**Guidelines**:
- Use clear, descriptive title (e.g., "Backtest Engine Component Design")
- Document ID must follow naming convention
- Version starts at 1.0
- Use current date in YYYY-MM-DD format
- Classification: "Internal" for internal projects, adjust as needed
- Approval status: "Pending Review" initially

---

### Step 4: Write Overview Section

Write comprehensive overview of the component.

**Template**:
```markdown
## 1. Overview

### 1.1 Purpose

[1-2 sentence summary of what this component does]

[Detailed description of component purpose and key responsibilities]

### 1.2 Scope

This component includes:
- **Element 1**: Description
- **Element 2**: Description
- **Element 3**: Description
- **Element 4**: Description
```

**Content Guidelines**:
- Purpose: Clear, concise explanation of why component exists
- Scope: Bullet list of key classes, modules, or features included
- Avoid implementation details (covered in later sections)
- Focus on what the component does from a user perspective
- 2-3 paragraphs total

**Example**:
```markdown
## 1. Overview

### 1.1 Purpose

The Backtest Engine component provides core data structures and logic for simulating stock trading strategies against historical market data, including strategy execution, position tracking, and performance measurement.

It enables efficient backtesting of portfolio strategies with support for configurable date ranges, multiple ticker universes, and comprehensive performance analytics.

### 1.2 Scope

This component includes:
- **BacktestEngine**: Top-level orchestrator for running backtests
- **BacktestConfig**: Configuration parameters for backtest runs
- **BacktestResults**: Container for performance metrics and trade history
- **RunRecord**: Timestamped record of portfolio state and transactions
```

---

### Step 5: Create Inputs and Outputs Table

Document all inputs and outputs with data types and sources.

**Template**:
```markdown
## 2. Inputs and Outputs

### 2.1 Inputs

| Input Name | Data Type | Source | Frequency | Description |
|------------|-----------|--------|-----------|-------------|
| **Input 1** | `type` | Source | Frequency | Description |
| **Input 2** | `type` | Source | Frequency | Description |

### 2.2 Outputs

| Output Name | Data Type | Destination | Frequency | Description |
|-------------|-----------|-------------|-----------|-------------|
| **Output 1** | `type` | Destination | Frequency | Description |
| **Output 2** | `type` | Destination | Frequency | Description |
```

**Table Guidelines**:
- List all major inputs to the component
- Include data type (Python types or custom classes)
- Specify source (User input, Data source, Other module, etc.)
- Specify frequency (Once, 10-30 Hz, Per record, On demand)
- Provide clear description of what each input represents
- Do the same for outputs
- Use backticks for type names and code identifiers

**Example**:
```markdown
## 2. Inputs and Outputs

### 2.1 Inputs

| Input Name | Data Type | Source | Frequency | Description |
|------------|-----------|--------|-----------|-------------|
| **Ticker symbols** | `list[str]` | User/config | Once per backtest | List of stock tickers to include (e.g., ["AAPL", "MSFT"]) |
| **OHLCV data** | `pd.DataFrame` | Market data API | Daily | Open, High, Low, Close, Volume price data |
| **Date range** | `tuple[datetime, datetime]` | User/config | Once per backtest | Start and end dates for the backtest period |
| **Portfolio weights** | `dict[str, float]` | Strategy/optimizer | Per rebalance | Target allocation weights per ticker |

### 2.2 Outputs

| Output Name | Data Type | Destination | Frequency | Description |
|-------------|-----------|-------------|-----------|-------------|
| **Backtest results** | `BacktestResults` | Analytics pipeline | On demand | Complete results with metrics and trade log |
| **Performance metrics** | `dict[str, float]` | Dashboard/reports | On demand | Sharpe ratio, max drawdown, CAGR, etc. |
```

---

### Step 6: Create Processing Flow Diagram

Add a Mermaid flowchart showing the component's main processing flow.

**Template**:
```markdown
## 3. Detailed Algorithm

### 3.1 Component Flow

\`\`\`mermaid
flowchart TB
    Start([Start]) --> Step1[Step 1: Description]
    Step1 --> Decision{Decision Point?}
    Decision -->|Yes| Step2[Step 2: Description]
    Decision -->|No| Step3[Alternative Step]
    Step2 --> Step4[Step 4: Description]
    Step3 --> Step4
    Step4 --> End([End])
\`\`\`
```

**Mermaid Guidelines**:
- Use flowchart TB (top-to-bottom) layout
- Use descriptive node labels (avoid generic "Process")
- Include decision diamonds for conditional logic
- Show all major processing paths
- Use camelCase or snake_case for node IDs (no spaces)
- Start with Start([...]) and end with End([...])
- Keep diagram readable (not too many nodes - consider 8-15 nodes)

**Example**:
```markdown
### 3.1 Component Flow

\`\`\`mermaid
flowchart TB
    Start([Start Backtest]) --> LoadConfig[Load Backtest Configuration<br/>tickers, date range, strategy]
    LoadConfig --> FetchData[Fetch Historical OHLCV Data]
    FetchData --> ValidateData{Data Complete?}
    ValidateData -->|No| HandleMissing[Handle Missing Data<br/>forward fill, drop, interpolate]
    ValidateData -->|Yes| InitPortfolio[Initialize Portfolio<br/>cash balance, empty positions]
    HandleMissing --> InitPortfolio
    InitPortfolio --> SimLoop{Simulation Loop<br/>each trading day}
    SimLoop -->|next day| GenSignals[Generate Trading Signals]
    GenSignals --> CalcWeights[Calculate Target Weights]
    CalcWeights --> ExecuteTrades[Execute Rebalance Trades]
    ExecuteTrades --> RecordState[Record Portfolio State]
    RecordState --> SimLoop
    SimLoop -->|done| CalcMetrics[Calculate Performance Metrics<br/>Sharpe, drawdown, CAGR]
    CalcMetrics --> End([Backtest Complete])
\`\`\`
```

---

### Step 7: Document Algorithm Steps

Write numbered steps describing the algorithm or processing logic.

**Template**:
```markdown
### 3.2 Algorithm Steps

1. **Step Name**: Detailed description of what happens in this step
   - Substep or detail A
   - Substep or detail B
   - Result: What is produced

2. **Step Name**: Next step in the process
   - How it builds on previous steps
   - Key logic or decision points
   - Result: What is produced

[Continue for all major steps]

**Performance** (if applicable):
- Operation 1: O(complexity) explanation
- Operation 2: O(complexity) explanation
```

**Guidelines**:
- Number steps 1, 2, 3, etc.
- Start each step with bold name followed by description
- Use bullet points for details or substeps
- Explain what data is used and produced
- Include performance characteristics (time/space complexity)
- Reference related algorithm designs if they exist

**Example**:
```markdown
### 3.2 Algorithm Steps

1. **Backtest Initialization**: Create BacktestEngine with configuration, initialize empty portfolio with starting cash, set benchmark index

2. **Data Loading and Validation**:
   - Fetch OHLCV data for all tickers in the universe
   - Validate date range coverage and data completeness
   - Forward-fill missing prices for holidays and halted tickers
   - Align all ticker DataFrames to a common date index

3. **Simulation Loop**:
   - For each trading day, generate signals from the active strategy
   - Calculate target portfolio weights from signals
   - Execute rebalancing trades (buy/sell to match target weights)
   - Record portfolio value, positions, and cash in RunRecord

4. **Performance Calculation**:
   - Compute daily returns from portfolio value series
   - Calculate Sharpe ratio, max drawdown, CAGR, and Sortino ratio
   - Compare against benchmark returns for alpha and beta

**Performance**:
- Data loading: O(T x N) where T = trading days, N = number of tickers
- Simulation loop: O(T x N) per backtest run
- Metrics calculation: O(T) from portfolio value series
```

---

### Step 8: Add Configuration Section

Document any runtime configuration parameters.

**Template**:
```markdown
## 4. Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `param_name` | `type` | `default_value` | Description of what this parameter controls |

**Notes**:
- Any special behavior or constraints
- When to adjust these parameters
```

**Guidelines**:
- If no configuration parameters, state "This component has no runtime configuration parameters. All behavior is controlled through method arguments."
- If parameters exist, create a table with type, default, and description
- Note dependencies between parameters
- Mention performance implications

---

### Step 9: Document Error Handling

Create a table of error cases and how they're handled.

**Template**:
```markdown
## 5. Error Handling

| Error Case | Condition | Handling | Recovery |
|------------|-----------|----------|----------|
| **Error Name** | When this error occurs | How it's handled | How caller recovers |
| **Error Name 2** | Specific condition | Error handling approach | Recovery steps |

**Error Prevention**:
- Best practice 1 for preventing errors
- Best practice 2 for preventing errors
```

**Guidelines**:
- List realistic error scenarios
- Describe the condition that triggers the error
- Explain how the component handles it (raises exception, returns None, logs, etc.)
- Provide recovery guidance for callers
- Include error prevention best practices
- Reference validation that happens in other stages

**Example**:
```markdown
## 5. Error Handling

| Error Case | Condition | Handling | Recovery |
|------------|-----------|----------|----------|
| **Missing ticker data** | Ticker has no OHLCV data for date range | Log warning, exclude ticker from universe | Reduce universe or widen date range |
| **API rate limit** | Data provider returns 429 status | Exponential backoff retry (max 3 attempts) | Wait and retry, or use cached data |
| **Insufficient history** | Date range shorter than strategy lookback | `ValueError` raised with required minimum | Extend start date to cover lookback period |
| **Invalid weights** | Portfolio weights do not sum to 1.0 | Normalize weights automatically, log warning | Validate weights before passing to engine |

**Error Prevention**:
- Always validate ticker symbols against available data before starting backtest
- Cache API responses locally to reduce rate limit exposure
- Check date range covers strategy lookback period during configuration
```

---

### Step 10: Add Related Documents Section

Link to related algorithms, components, and system documentation.

**Template**:
```markdown
## 6. Related Documents

### 6.1 Algorithm Designs
- [Algorithm Name](algorithms/algorithm_name.md) - [ID] - [Brief description]
- [Algorithm Name 2](algorithms/algorithm_name_2.md) - [ID] - [Brief description]

### 6.2 Related Components
- [Component Name](component_name.md) - [ID] - [Brief description]
- [Component Name 2](component_name_2.md) - [ID] - [Brief description]

### 6.3 System Documentation
- [System Overview](../0_system_overview.md) - High-level context
- [System Architecture](../system_architecture.md) - Component relationships
- [API Reference](../../api_reference/module_name.md) - API documentation
```

**Guidelines**:
- Reference algorithm designs that implement specific steps
- Link to related components that interact with this one
- Link to system-level documentation for context
- Use relative paths for links
- Include document IDs for cross-reference
- Keep descriptions brief (1 sentence)

---

### Step 11: Add Implementation Details Section (Optional)

Document class structures, data types, and coordinate systems.

**Template**:
```markdown
## 7. Implementation Details

### 7.1 Key Classes

**ClassName**:
\`\`\`python
class ClassName:
    attribute1: type  # Description
    attribute2: type  # Description
\`\`\`

### 7.2 Enumerations

| Enum Value | Integer | Description |
|------------|---------|-------------|
| `VALUE_1` | 0 | Description |
| `VALUE_2` | 1 | Description |

### 7.3 Coordinate Systems

- **Position**: Description of coordinate system
- **Angles**: Description of angle representation
- **Velocities**: Description of velocity representation
- **Dimensions**: Description of dimension representation

### 7.4 Storage Format

- **Format**: Storage format (pickle, JSON, binary, etc.)
- **Size**: Typical size range
- **Load time**: Typical load/save times
- **Thread safety**: Thread safety characteristics
```

**Guidelines**:
- Include class definitions in pseudo-code format
- Document enums with all values
- Explain coordinate systems if specific to domain
- Describe storage formats and typical performance
- Note thread safety and concurrency considerations
- Keep implementation details focused on data structures, not algorithms

---

### Step 12: Add Footer Section

Complete the document with metadata.

**Template**:
```markdown
---

**Document Status**: ✅ Complete
**Last Updated**: [YYYY-MM-DD]
**Next Review Date**: [YYYY-MM-DD]
**Version**: 1.0
**Classification**: Internal
```

**Guidelines**:
- Status: Draft (🔄), In Review (⏳), Complete (✅), Approved (✔️)
- Last Updated: Current date in YYYY-MM-DD format
- Next Review Date: 6 months from last updated date
- Version: 1.0 for new documents
- Classification: Internal, Confidential, Public, etc.

---

## Outputs

### Primary
- **File**: `doc/design/2_component_designs/<component_name>.md`
- **Content**: Complete component design document with:
  - Header (Document ID, version, classification)
  - Overview (purpose and scope)
  - Inputs and Outputs (data tables)
  - Detailed Algorithm (Mermaid diagram and steps)
  - Configuration Parameters (if applicable)
  - Error Handling (error table and prevention tips)
  - Related Documents (cross-references)
  - Implementation Details (optional - classes, enums, storage)
  - Footer (status, dates, version)

### Secondary
- **File added to git**: Stage the new file for commit

---

## Examples

### Example 1: Generate Component Design for Backtest Engine

**Input**:
- module_name: `backtest`
- component_name: `backtest_engine`
- module_path: `/Users/antiwong/Documents/code/my_code/stock_all/midterm-stock-planner/midterm_stock_planner/backtest/`
- analysis_summary: (from analyze_module.md)

**Process**:
1. Create Document ID: `MSP-CD-BACKTEST-001`
2. Create file: `doc/design/2_component_designs/backtest_engine.md`
3. Write header with Document ID and metadata
4. Write overview explaining BacktestEngine, BacktestConfig, BacktestResults, RunRecord classes
5. Create inputs table (ticker symbols, OHLCV data, date ranges, portfolio weights)
6. Create outputs table (BacktestResults object, performance metrics, trade log)
7. Create Mermaid flowchart showing data loading, simulation loop, and metrics calculation
8. Document algorithm steps (initialization, data validation, simulation, performance calculation)
9. Document configuration parameters (rebalance frequency, commission rate, slippage model)
10. Document error handling (missing data, API rate limits, insufficient history)
11. Link to related components (Risk Management, Analytics, Portfolio Optimization)
12. Add implementation details (BacktestEngine, BacktestConfig, BacktestResults, RunRecord class structures)
13. Add footer with status and dates

**Output**:
File created at `doc/design/2_component_designs/backtest_engine.md` with complete component design (~250-350 lines).

---

### Example 2: Generate Component Design for Risk Management

**Input**:
- module_name: `risk`
- component_name: `risk_management`
- module_path: `/Users/antiwong/Documents/code/my_code/stock_all/midterm-stock-planner/midterm_stock_planner/risk/`

**Process**:
1. Create Document ID: `MSP-CD-RISK-001`
2. Create file: `doc/design/2_component_designs/risk_management.md`
3. Write overview explaining risk metrics calculation (VaR, CVaR, volatility, beta)
4. Document inputs (portfolio returns, benchmark data) and outputs (risk report)
5. Create flowchart showing data ingestion → risk calculation → report generation
6. Document algorithm steps for each supported risk metric
7. Document configuration (confidence level, lookback window, risk model selection)
8. Document error handling (insufficient data, singular covariance matrix, convergence failures)
9. Link to Backtest Engine and Analytics components
10. Document statistical model assumptions and limitations

**Output**:
File created at `doc/design/2_component_designs/risk_management.md` (~280-400 lines).

---

## Validation

- [ ] File created at `doc/design/2_component_designs/<component_name>.md`
- [ ] Document ID follows format: `[MODULE]-CD-[ABBR]-001`
- [ ] Header section complete (Document ID, version, date, classification)
- [ ] Overview section explains purpose clearly (1-2 paragraphs)
- [ ] Scope section lists all major classes/features included
- [ ] Inputs table has all required columns (Name, Type, Source, Frequency, Description)
- [ ] Outputs table has all required columns (Name, Type, Destination, Frequency, Description)
- [ ] Mermaid diagram is syntactically correct and renders properly
- [ ] All node IDs in Mermaid use camelCase or snake_case (no spaces)
- [ ] Algorithm steps are numbered and clearly described
- [ ] Each step explains inputs, processing, and outputs
- [ ] Configuration section present (even if "no parameters")
- [ ] Error handling table documents realistic error cases
- [ ] Error prevention section includes best practices
- [ ] Related Documents section links to algorithms, components, and system docs
- [ ] All links use relative paths and are verifiable
- [ ] Implementation Details section includes key classes and data structures
- [ ] Footer includes Document Status, Last Updated, Next Review Date, Version
- [ ] All code blocks and tables are properly formatted
- [ ] No broken links or references to non-existent documents
- [ ] Markdown formatting is correct and renders properly

---

## Related Skills

### Prerequisites
- [`../code_exploration/analyze_module.md`](../code_exploration/analyze_module.md) - Analyze module first
- [`generate_api_docs.md`](generate_api_docs.md) - Create API reference first

### Follow-ups
- [`../code_exploration/design_algorithm.md`](../code_exploration/design_algorithm.md) - Create detailed algorithm designs
- [`../validation/validate_design_doc.md`](../validation/validate_design_doc.md) - Validate design completeness

### Related
- [`add_docstrings.md`](add_docstrings.md) - Add docstrings to source code
- [`update_component_design.md`](update_component_design.md) - Update existing design docs (if exists)
- [`../../prompt/documentation_guidelines.md`](../../prompt/documentation_guidelines.md) - Design standards

---

**Last Updated**: 2026-02-20
**Version**: 1.0
