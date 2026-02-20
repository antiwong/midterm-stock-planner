# Customization Guide - midterm_stock_planner

**Purpose**: Reference for how this documentation template was customized for midterm_stock_planner. Use as a guide if adapting for other projects.

---

## Customization Applied

This documentation infrastructure was adapted from a generic template for the midterm_stock_planner project.

### Replacements Made

| Placeholder | Replaced With |
|-------------|---------------|
| `[PROJECT_NAME]` | midterm_stock_planner |
| `[VERSION]` | 3.11.2 |
| `[DATE]` | 2026-02-20 |
| `[PROJECT_TYPE]` | Python Streamlit web application |
| `[PRIMARY_LANGUAGE]` | Python (3.11+) |
| `[PROJECT_PREFIX]` | MSP |

### Files Customized

| File | Changes |
|------|---------|
| `knowledgebase/AGENT_PROMPT.md` | Full rewrite with midterm_stock_planner architecture, 17 modules, dependencies, workflows |
| `knowledgebase/module_summaries.md` | Full rewrite with all project modules (app, analytics, backtest, risk, etc.) |
| `knowledgebase/glossary.md` | Full rewrite with stock analysis, ML, risk management, backtesting terminology |
| `knowledgebase/README.md` | Updated references to midterm_stock_planner |
| `skills/README.md` | Updated project name, examples, and workflows |
| `prompt/README.md` | Updated project reference |
| `prompt/documentation_guidelines.md` | Updated document ID format (MSP-CD-[COMPONENT]-NNN) |
| `CONTENTS.md` | Full rewrite with midterm_stock_planner inventory |

### Files Removed

| File/Folder | Reason |
|-------------|--------|
| `skills/av_domains/` | Autonomous vehicle domain skills not relevant to stock analysis |
| `skills/beads_integration/sync_jira.md` | No Jira integration in this project |
| `skills/documentation/generate_sar_behavior_scenario.md` | SAR (Safety Assessment Report) is AV-specific |
| `skills/documentation/generate_safety_interaction_diagram.md` | Safety interaction diagrams are AV-specific |
| `skills/validation/validate_sar_document.md` | SAR validation is AV-specific |

### Files Kept As-Is (Generic)

These files were updated with midterm_stock_planner examples but retain the same generic structure:
- Code exploration skills (`skills/code_exploration/*.md`)
- Documentation skills (`skills/documentation/*.md`)
- Validation skills (`skills/validation/*.md`)
- Project management skills (`skills/project_management/*.md`)
- Requirements skills (`skills/requirements/*.md`)
- Prompt templates (`prompt/generate_component_design.md`, `prompt/generate_algorithm_design.md`)
- Template files (`knowledgebase/AGENT_PROMPT.template.md`, `knowledgebase/module_summaries.template.md`)

---

## Document ID Format

**Pattern**: `MSP-CD-[COMPONENT]-NNN`

**Examples**:
- Component: `MSP-CD-BACKTEST-001` (walk-forward backtest engine design)
- Component: `MSP-CD-RISK-001` (risk management module design)
- Component: `MSP-CD-ANALYTICS-001` (comprehensive analysis system design)
- Algorithm: `MSP-CD-ALG-WALKFORWARD-001` (walk-forward algorithm)
- Algorithm: `MSP-CD-ALG-RISKPARITY-001` (risk parity allocation algorithm)
- Algorithm: `MSP-CD-ALG-RANKING-001` (cross-sectional stock ranking algorithm)

---

## Beads Setup

### Beads Initialization
```bash
bd init
```

---

## Validation Checklist

After customization, verify:

- [x] All `[PLACEHOLDERS]` replaced
- [x] AGENT_PROMPT.md has midterm_stock_planner modules and architecture
- [x] module_summaries.md has all 17 modules documented
- [x] glossary.md has stock analysis, ML, risk management terminology
- [x] Architecture diagrams updated with midterm_stock_planner components
- [x] Dependencies list accurate (streamlit, lightgbm, pandas, yfinance, etc.)
- [x] File paths match project structure
- [x] Document ID format customized (MSP-CD-[COMPONENT]-NNN)
- [x] Skills README updated with midterm_stock_planner examples
- [x] AV domain skills removed (not relevant)
- [x] Jira sync skill removed (no Jira)

---

**Last Updated**: 2026-02-20
**Version**: 3.11.2
