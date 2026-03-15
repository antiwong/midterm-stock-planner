# QuantaAlpha Integration Analysis

**Date**: 2026-03-15
**Status**: Proposal
**Related**: `docs/quantaalpha-feature-proposal.md`, `docs/quantaalpha-implementation-guide.md`

---

## What is QuantaAlpha?

QuantaAlpha (arXiv:2602.07085) is an **LLM-driven autonomous alpha factor mining framework**. Instead of manually designing features, it uses LLMs and evolutionary strategies to automatically discover, refine, and validate trading factors.

**Core Loop**: Research direction (natural language) -> LLM generates factor hypothesis -> code generation -> backtest (Qlib/LightGBM) -> feedback -> mutation/crossover -> repeat

**Reported Results** (CSI 300): IC 0.15, Rank IC 0.15, Annualized Excess Return 27.75%, Max Drawdown 7.98%, Calmar 3.47

**Source**: `/Users/antiwong/Documents/code/my_code/stock_all/QuantaAlpha/`

---

## Key Differences from midterm-stock-planner

| Dimension | QuantaAlpha | midterm-stock-planner |
|-----------|------------|----------------------|
| **Goal** | Autonomous factor discovery | Mid-term stock ranking & portfolio optimization |
| **Input** | Natural language research direction | Configured feature set + backtest params |
| **Universe** | CSI 300/500 (A-shares), zero-shot to S&P 500 | 114 US stocks (NASDAQ-100 + ETFs) |
| **Backtesting** | Qlib + LightGBM, TopkDropout | Walk-forward with LightGBM ranking |
| **Evolution** | LLM-guided mutation/crossover of factor expressions | Evolutionary hyperparameter tuning (Sharpe/return) |
| **Features** | Auto-generated factor expressions | Hardcoded in `src/features/` |
| **Risk** | IC/ICIR per window | VaR, CVaR, stress tests, tail risk, SHAP |
| **Data** | Price-volume only (HDF5) | Prices + fundamentals + macro + sentiment |
| **Frontend** | React + FastAPI | Streamlit |

---

## Should This Run as a Separate Analysis?

**Recommendation: Yes, run as a separate optional pipeline (Plugin Architecture).**

Reasons:
1. **Different data format** -- QuantaAlpha uses Qlib HDF5 data; midterm-stock-planner uses CSV. No shared data layer.
2. **Long runtime** -- Factor mining takes hours (multiple LLM calls + backtests per direction). Cannot run inline with existing analysis.
3. **LLM dependency** -- Requires OpenAI-compatible API key and significant token budget. Not all users will have this.
4. **Different universe** -- QuantaAlpha targets A-shares (CSI 300). Factors may not directly apply to US equities without adaptation.
5. **Qlib dependency** -- Heavy dependency (`pyqlib`) not needed for core midterm-stock-planner functionality.

However, **specific components can be integrated** without pulling in the full framework.

---

## Integration Architecture

### Option A: Plugin Architecture (Recommended)

```
midterm-stock-planner/
├── src/
│   └── quantaalpha_plugin/       # NEW: lightweight integration layer
│       ├── __init__.py
│       ├── factor_miner.py       # Wrapper for factor discovery
│       ├── evolution.py          # LLM-guided strategy evolution
│       └── loader.py             # Load mined factors into backtest
│
├── scripts/
│   ├── quantaalpha_mine.py       # Run factor mining (separate process)
│   └── integrate_factors.py      # Import mined factors into backtest
│
└── config/
    └── quantaalpha.yaml          # Mining direction config
```

**Flow**:
1. User runs `python scripts/quantaalpha_mine.py --direction "momentum factors"` (separate process, takes hours)
2. QuantaAlpha produces `all_factors_library.json` with discovered factors
3. User runs `python scripts/integrate_factors.py --factor-lib all_factors_library.json`
4. Factors are imported as custom features into the existing backtest pipeline
5. Standard regression test (`run_regression_test.py run`) evaluates them alongside built-in features

### Option B: Tight Integration (More Ambitious)

Embed QuantaAlpha's evolution operators directly into `scripts/evolutionary_backtest.py`:
- Replace random hyperparameter mutation with LLM-guided feature combination suggestions
- Use trajectory tracking for factor lineage across generations
- Tradeoff: requires refactoring existing evolutionary backtest, more complex state management

### Option C: Manual Import (Simplest)

Run QuantaAlpha completely separately, manually export/import JSON factor libraries.
- Zero code changes to midterm-stock-planner
- Requires manual orchestration

---

## High-Value Integrations (No Full Framework Required)

These can be adopted independently, without installing QuantaAlpha as a dependency:

### 1. LLM-Guided Feature Selection

**What**: Use an LLM to suggest orthogonal feature combinations for the regression test pipeline.

**How**: When running regression tests, instead of a fixed feature order, ask an LLM:
> "Given these features performed well [bollinger +0.64, macd +0.15, adx +0.08] and these hurt [rsi -0.28, momentum -0.24], suggest 3 alternative feature combinations to test."

**Integration point**: `src/regression/orchestrator.py` -- add an optional LLM-guided feature ordering step before the main loop.

**Effort**: Low (API call + prompt engineering, no QuantaAlpha dependency)

### 2. Factor Quality Gates (Redundancy Detection)

**What**: Before adding a new feature to the model, check if it's redundant with existing features via IC correlation.

**How**: Compute pairwise Rank IC correlation matrix. If a new feature has |correlation| > 0.8 with any existing feature, flag as redundant.

**Integration point**: `src/regression/orchestrator.py::_run_step()` -- add redundancy check before running backtest.

**Already partially done**: `marginal_ic` is computed per window in Tier 1 importance. Extend to cross-feature correlation.

**Effort**: Low (pure Python, no external dependency)

### 3. Trajectory-Based Lineage Tracking

**What**: Track which feature combinations lead to the best results across multiple regression runs.

**How**: Extend `src/regression/database.py` to store a DAG of feature set evolution:
- Each regression run is a node
- Edges connect parent configs to child configs (what was added/removed)
- Query: "What's the best feature set ever found? What path led to it?"

**Integration point**: `src/regression/database.py` + `scripts/lineage_report.py`

**Effort**: Medium (new DB table, query logic, visualization)

### 4. Per-Window IC Regime Detection

**What**: Monitor IC stability across walk-forward windows. Alert when IC drops significantly in recent windows (regime shift signal).

**How**: Already computing per-window ICs in `rolling.py`. Add:
- Rolling IC mean (last N windows) vs historical IC mean
- Z-score alert when recent IC is >2 sigma below historical mean
- Dashboard indicator: "Signal quality degrading in recent period"

**Integration point**: `src/backtest/rolling.py` metrics aggregation, dashboard `overview.py`

**Effort**: Low (statistics on existing data)

### 5. Custom Factor Expression Engine

**What**: Allow users to define custom factor expressions (e.g., `(close - sma_20) / atr_14`) that get auto-computed and backtested.

**How**: Simple expression parser that computes factors from existing columns. No LLM needed for basic expressions.

**Integration point**: `src/features/engineering.py` -- add `compute_custom_expression(df, expression_str)` function.

**Effort**: Medium (expression parser, safety validation)

---

## Dependency Analysis

| QuantaAlpha Dep | midterm-stock-planner | Conflict? |
|-----------------|----------------------|-----------|
| `lightgbm` | Yes (same) | No |
| `scikit-learn` | Yes (same) | No |
| `pandas`, `numpy` | Yes (same) | No |
| `openai` | Uses `google-generativeai` | No (separate) |
| `pyqlib` | Not used | New dep (heavy) |
| `rdagent==0.8.0` | Not used | New dep (pinned) |
| `docker` | Not used | Optional |
| `tables` (HDF5) | Not used | New dep |

**Recommendation**: Keep QuantaAlpha in a separate virtual environment. Import via subprocess or optional dependency.

---

## Implementation Roadmap

### Phase 1: Foundation (1-2 weeks)
- [ ] Create `src/quantaalpha_plugin/` module with lazy imports
- [ ] Factor library JSON loader (ingest QuantaAlpha output)
- [ ] Script: `scripts/integrate_factors.py`
- [ ] Test: load factors, add to regression test

### Phase 2: Quality Gates (1 week)
- [ ] IC-based redundancy detection in regression orchestrator
- [ ] Per-window IC regime detection + dashboard alert
- [ ] Extend regression report with redundancy flags

### Phase 3: LLM Integration (2 weeks)
- [ ] LLM client (OpenAI-compatible, reuse QuantaAlpha's pattern)
- [ ] Prompt templates for feature suggestion + orthogonal mutation
- [ ] Integrate into `evolutionary_backtest.py` as optional mode
- [ ] Trajectory pool for lineage tracking

### Phase 4: Advanced (2 weeks)
- [ ] Custom factor expression engine
- [ ] Transfer testing framework (cross-universe validation)
- [ ] Dashboard page for factor mining results

---

## Decision

| Question | Answer |
|----------|--------|
| Run as part of existing analysis? | **No** -- separate pipeline due to runtime, data format, and dependency differences |
| Share data? | **Partially** -- QuantaAlpha outputs JSON factor libraries that can be imported |
| Share backtest? | **No** -- QuantaAlpha uses Qlib; midterm-stock-planner uses custom walk-forward |
| Worth integrating? | **Yes** -- specific components (quality gates, LLM-guided selection, IC regime detection) add significant value without full framework dependency |
| Priority integrations? | 1. Factor quality gates (redundancy), 2. IC regime detection, 3. LLM feature suggestions |

---

## Implementation Status (2026-03-15)

| Integration | Status | Location |
|-------------|--------|----------|
| Factor redundancy gates (IC correlation) | **DONE** | `src/regression/metrics.py::check_feature_redundancy()` |
| IC regime detection (Z-score alert) | **DONE** | `src/regression/metrics.py::detect_ic_regime_shift()` |
| Overfitting mitigation (regularization) | **DONE** | `config/config.yaml` model params, `src/models/trainer.py` early stopping |
| Optimal feature set from regression | **DONE** | `config/config.yaml` regression.recommended_features |
| LLM-guided feature selection | Planned | Phase 3 |
| Custom factor expression engine | Planned | Phase 4 |
