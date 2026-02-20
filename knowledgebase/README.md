# Knowledge Base - midterm_stock_planner

**Purpose**: Centralised knowledge and context for AI agents and human developers working with the midterm_stock_planner stock ranking and portfolio optimization system.

---

## Quick Start

### For AI Agents
1. **Read** [`AGENT_PROMPT.md`](AGENT_PROMPT.md) first - Comprehensive system prompt containing all project context
2. **Consult** [`module_summaries.md`](module_summaries.md) for quick module overviews
3. **Reference** [`glossary.md`](glossary.md) for domain terminology
4. **Use** [`../skills/`](../skills/) for task-specific instructions

### For Human Developers
1. **Start** with [`AGENT_PROMPT.md`](AGENT_PROMPT.md) for comprehensive codebase overview
2. **Browse** [`module_summaries.md`](module_summaries.md) to understand module responsibilities
3. **Look up** [`glossary.md`](glossary.md) for stock analysis, ML, and risk management terminology
4. **Navigate** to [`../docs/`](../docs/) for full documentation

---

## Knowledge Base Files

### Core Files

#### [`AGENT_PROMPT.md`](AGENT_PROMPT.md) - AI Agent System Prompt
**Purpose**: Comprehensive context for AI agents (Claude Code, beads-managed agents)
**Contains**:
- Project overview (Python Streamlit stock ranking app, ~130+ files, ~49,000 LOC)
- Codebase architecture (17 modules: app, analytics, analysis, backtest, risk, etc.)
- Core algorithms (walk-forward backtest, LightGBM ranking, risk parity, portfolio optimization)
- Key data structures (AppConfig, InvestorProfile, BacktestResults, RunRecord)
- Documentation structure and standards (MSP-CD-[COMPONENT]-NNN)
- Task management with beads (commands, workflows)
- Common workflows (full analysis, document module, create component design)
- Code patterns and conventions (Python 3.11+, Streamlit, SQLAlchemy)
- Domain knowledge (stock analysis, ML, risk management)
- Run commands and dependency reference

**When to Use**:
- **AI agents**: Load this file before starting any task
- **Human developers**: Reference for comprehensive codebase understanding
- **New team members**: Onboarding guide to project structure

---

#### [`module_summaries.md`](module_summaries.md) - High-Level Module Descriptions
**Purpose**: Quick reference for module responsibilities
**Contains**:
- App (Dashboard + CLI, 27 pages, UI components)
- Analytics (Analysis engine, database, AI insights)
- Analysis (Domain analysis, portfolio optimization)
- Backtest (Walk-forward backtesting)
- Risk (Metrics, parity, position sizing)
- Sentiment (Multi-source, LLM-based)
- Features, Indicators, Models, Data, Config, Validation, etc.
- Module relationships diagram and data flow

**When to Use**:
- Quick lookup of "which module does X?"
- Understanding module boundaries and data flow
- Planning which modules to document first

---

#### [`glossary.md`](glossary.md) - Domain Terminology
**Purpose**: Define stock analysis, portfolio management, ML, and risk terms
**Contains**:
- Stock market & trading terminology (alpha, beta, rebalancing, watchlist)
- Portfolio management terms (position sizing, risk parity, sector allocation)
- Risk metrics (Sharpe, VaR, CVaR, drawdown, tracking error)
- Machine learning terms (LightGBM, SHAP, cross-sectional ranking, walk-forward)
- Technical analysis indicators (RSI, MACD, ADX, ATR, Bollinger)
- Fundamental analysis (PE, PB, ROE, market cap)
- Analytics & reporting (performance attribution, factor exposure, Monte Carlo)
- Data & infrastructure (yfinance, Gemini, Streamlit, SQLAlchemy)
- Acronyms reference

**When to Use**:
- Understanding unfamiliar terms in code or documentation
- Writing documentation that uses domain-specific terminology
- Onboarding to stock analysis and portfolio management concepts

---

### Additional Resources

#### [`../skills/`](../skills/) - AI Agent Task Guides
Task-oriented instructions for documentation, code exploration, beads integration, and validation.
See [`../skills/README.md`](../skills/README.md) for full index.

#### [`../docs/`](../docs/) - Developer Documentation
66 documentation files covering design, user guide, API reference, and feature documentation.

#### [`../prompt/`](../prompt/) - Design Documentation Templates
Templates and guidelines for creating component and algorithm design documents.
See [`../prompt/README.md`](../prompt/README.md) for usage.

---

## Knowledge Base Maintenance

### When to Update

**`AGENT_PROMPT.md`**:
- New analysis module added -> Update "Comprehensive Analysis System" table
- Architecture changes -> Update Mermaid diagram
- New features added -> Update "Key Capabilities"
- Dependencies changed -> Update "Key Dependencies"
- New workflow identified -> Update "Common Workflows"

**`module_summaries.md`**:
- New module added -> Add summary
- Module responsibility changes -> Update description
- File count or LOC changes significantly -> Update statistics

**`glossary.md`**:
- New domain term introduced -> Add definition
- Existing term definition needs clarification -> Update entry
- New acronym used -> Add to acronyms section

### Version Control
- Knowledge base files are versioned with the project (git)
- Update "Last Updated" date when making changes
- Consider updating version number for major changes

---

## Knowledge Base Structure

```
knowledgebase/
├── README.md                         # THIS FILE - Index and navigation
├── AGENT_PROMPT.md                   # Comprehensive system prompt for AI agents
├── AGENT_PROMPT.template.md          # Original template (reference only)
├── module_summaries.md               # Module overviews
├── module_summaries.template.md      # Original template (reference only)
└── glossary.md                       # Domain terminology
```

---

## How This Knowledge Base Supports Documentation

### The Documentation Workflow

1. **Agent loads context** -> Reads `AGENT_PROMPT.md` to understand project
2. **Agent identifies task** -> Uses beads (`bd ready`) or receives instructions
3. **Agent uses skill** -> Follows step-by-step instructions from `skills/`
4. **Agent consults glossary** -> References `glossary.md` for terminology
5. **Agent creates documentation** -> Writes to `docs/`
6. **Agent validates** -> Uses validation skills to check quality
7. **Agent marks complete** -> Updates beads task status

---

**Last Updated**: 2026-02-20
**Version**: 3.11.2 (matches project: midterm_stock_planner main branch)
