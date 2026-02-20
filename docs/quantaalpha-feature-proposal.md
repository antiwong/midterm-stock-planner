# QuantaAlpha-Inspired Feature Proposals

**Source**: QuantaAlpha: An Evolutionary Framework for LLM-Driven Alpha Mining (arXiv:2602.07085v1, Feb 2026)

**Context**: This document extracts ideas from the QuantaAlpha paper and adapts them for the Mid-term Stock Planner, respecting the project's constraint: **deterministic, numeric pipeline only—no LLM override of tickers, weights, or metrics**.

---

## Paper Summary

QuantaAlpha treats alpha mining as an evolutionary process:

1. **Trajectory-level evolution**: Each end-to-end mining run is a *trajectory* (hypothesis → factor → code → backtest). Evolution improves via *mutation* (targeted revision of suboptimal steps) and *crossover* (recombining high-reward segments from different trajectories).

2. **Diversified planning**: Multiple complementary research directions (momentum vs mean-reversion vs regime-conditioned) to avoid local optima.

3. **Controllable factor construction**: Symbolic representation (operator library + AST), semantic consistency verification (hypothesis ↔ expression ↔ code), complexity and redundancy controls.

4. **Key results**: IC 0.1501, ARR 27.75%, MDD 7.98% on CSI 300; strong transfer to CSI 500 and S&P 500. Overnight/gap factors, volatility structure, and trend-quality signals remain predictive under regime shifts.

---

## Proposed New Features

### 1. Evolutionary Strategy Optimization (Deterministic)

**Idea**: Treat backtest runs as *trajectories* and evolve them with mutation and crossover—without LLMs.

| QuantaAlpha | Mid-term Stock Planner Adaptation |
|-------------|-----------------------------------|
| Mutation on hypothesis/factor/code | Mutation on config params (RSI thresholds, domain weights, top-K, rebal freq) |
| Crossover of trajectory segments | Crossover of best parameter subsets from different runs |
| Terminal reward = IC/ARR − λ·R(f) | Fitness = Sharpe / total_return − λ·complexity |

**Implementation sketch**:
- Add `scripts/evolutionary_backtest.py`: population of configs, fitness = backtest Sharpe (or configurable objective), selection, mutation (perturb params), crossover (swap param blocks).
- Store run history as trajectories: `(config_hash, metrics, param_vector)`.
- Export best configs to YAML for reproducibility.

**Beads**: `quantaalpha-1-evolutionary-optimizer`

---

### 2. Diversified Planning / Multi-Strategy Seeds

**Idea**: Initialize search with complementary strategies instead of a single default.

| QuantaAlpha | Mid-term Stock Planner Adaptation |
|-------------|-----------------------------------|
| Multiple hypotheses (momentum, mean-reversion, regime) | Predefined strategy templates (value-tilt, momentum-tilt, quality-tilt, balanced) |
| Maximize complementarity | Ensure low correlation between seed portfolios |

**Implementation sketch**:
- Add `config/strategy_templates/`: YAML templates for value-heavy, momentum-heavy, quality-heavy, low-vol, etc.
- `scripts/diversified_backtest.py`: Run N templates in parallel, report correlation matrix of returns, select diversified subset for evolution pool.

**Beads**: `quantaalpha-2-diversified-templates`

---

### 3. Factor Complexity & Redundancy Control

**Idea**: Penalize overly complex and redundant factors (or portfolio constructions).

| QuantaAlpha | Mid-term Stock Planner Adaptation |
|-------------|-----------------------------------|
| C(f) = α₁·symbol_length + α₂·param_count + α₃·log(1+|features|) | Complexity = f(num_domains, num_filters, model_depth, feature_count) |
| Redundancy via AST subtree isomorphism | Redundancy via cross-sectional correlation of domain_scores / factor exposure |

**Implementation sketch**:
- Add `src/risk/complexity.py`: `compute_config_complexity(config)` and `compute_factor_redundancy(score_matrix)`.
- In optimization loop: reject or penalize configs exceeding complexity/redundancy thresholds.

**Beads**: `quantaalpha-3-complexity-redundancy`

---

### 4. Overnight & Gap-Based Features

**Idea**: Paper highlights overnight/gap factors as robust under regime shifts.

| QuantaAlpha examples | Mid-term Stock Planner Adaptation |
|----------------------|-----------------------------------|
| GapZ10_Overnight_vs_TR | `(open - prev_close) / true_range` normalized |
| Gap_IntradayAcceptanceScore_20D | Gap acceptance/rejection using intraday direction |
| Gap_IntradayAcceptance_VolWeighted_20D | Volume-weighted gap acceptance |

**Implementation sketch**:
- Add `src/features/gap_features.py`: `overnight_gap_pct`, `gap_acceptance_score`, `gap_vs_true_range`.
- Wire into feature pipeline; expose in domain_score combination if desired.

**Status**: ✅ Implemented (2026-02-20). `src/features/gap_features.py` with `add_gap_features()`. Wired into `compute_all_features_extended`. Tests in `tests/test_gap_features.py`.

---

### 5. Transfer & Robustness Testing

**Idea**: Test strategies on out-of-sample universes (e.g., train on S&P 500, test on MSCI World or sector sub-indices).

| QuantaAlpha | Mid-term Stock Planner Adaptation |
|-------------|-----------------------------------|
| Train on CSI 300 → test on CSI 500, S&P 500 | Train on config universe → test on alternate benchmark / sector |
| Zero-shot transfer, no re-optimization | Same weights/params, different universe, report metrics |

**Implementation sketch**:
- Add `--transfer-universe` to backtest CLI: run same config on second universe.
- Export side-by-side metrics (IC, Sharpe, MDD) for train vs transfer.
- Add `scripts/transfer_report.py` to summarize robustness.

**Status**: ✅ Implemented (2026-02-20). `scripts/transfer_report.py --transfer-watchlist <name>`. Runs backtest on primary + transfer universe, outputs side-by-side table and optional JSON.

---

### 6. Trajectory Lineage & Audit Trail

**Idea**: Maintain traceable lineage of configs and results (no LLM, but human-auditable).

| QuantaAlpha | Mid-term Stock Planner Adaptation |
|-------------|-----------------------------------|
| Parent trajectory IDs, evolution round, phase | Run ID, parent config hash, iteration, mutation/crossover tag |
| Factor card with lineage | Config card: `config_hash`, `parent_hashes`, `metrics`, `notes` |

**Implementation sketch**:
- Extend run output: JSON per run with `run_id`, `parent_run_ids`, `config_hash`, `mutation_type`, `metrics`.
- `scripts/lineage_report.py`: DAG of runs, highlight best branches.

**Beads**: `quantaalpha-6-lineage-audit`

---

## Alignment with Project Rules

| Rule | How proposals comply |
|------|----------------------|
| No LLM override of tickers/weights/metrics | All features use deterministic logic; evolution operates on config params, not holdings. |
| Vertical/horizontal structure preserved | Templates and evolution work within existing domain_score and portfolio construction. |
| Metric scaling (decimal returns, correct Sharpe, etc.) | Same definitions; no change to metric computation. |
| Config-driven (YAML + dataclasses) | Templates and evolution produce/consume YAML configs. |

---

## Priority Suggestion

1. **P0**: Gap features (#4) — low risk, adds robustness; no dependency.
2. **P1**: Transfer testing (#5) — validates robustness; simple CLI extension.
3. **P2**: Evolutionary optimizer (#1) — high impact; depends on run history format.
4. **P3**: Diversified templates (#2), complexity/redundancy (#3), lineage (#6).

---

## References

- QuantaAlpha: An Evolutionary Framework for LLM-Driven Alpha Mining. arXiv:2602.07085v1 [q-fin.ST] 6 Feb 2026.
- GitHub: https://github.com/QuantaAlpha/QuantaAlpha
