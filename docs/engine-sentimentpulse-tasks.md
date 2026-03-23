# Midterm-Stock-Planner — SentimentPulse Integration Tasks

> Tasks that must be done **in this repo** (midterm-stock-planner) to integrate with SentimentPulse.
> For SentimentPulse-side tasks, see `sentimental_blogs/docs/18-sentimentpulse-improvement-tasks.md`.

**Date**: 2026-03-20
**SentimentPulse repo**: `/Users/antiwong/Documents/code/my_code/stock_all/sentimental_blogs/`
**Sentiment data**: `data/sentiment/sentimentpulse_YYYY-MM-DD.csv`

---

## Already Done (session 2026-03-19/20)

| Task | What | Files |
|------|------|-------|
| Trigger layer | `TriggerSignal` enum: BUY/BUY_STRONG/HOLD/HOLD_BEARISH/WAIT_EVENT/NO_DATA | `src/trigger/sentiment_trigger.py` |
| Sentiment adapter | Bridges SP CSV → trigger layer, look-ahead bias prevention | `src/sentiment/sentiment_adapter.py` |
| Weight calibrator | scipy SLSQP optimization of source weights | `src/trigger/weight_calibrator.py` |
| Config update | `sentiment_trigger` section + architecture comments | `config/config.yaml` |
| Legacy deprecation | `prepare_sentiment_from_news()` marked deprecated | `src/features/engineering.py` |

---

## Phase 1 — Pre-Trigger-Enable

### ENG-1.1: Record Ranker Baseline Returns for Trigger Alpha
**Source**: sentimental_blogs doc 16 §1.1
**Why**: The weight calibrator currently optimizes for directional accuracy, but the trigger layer's job is to improve entry timing, not predict direction. Need a `ranker_baseline_return` to compute `trigger_alpha = actual_return_when_triggered - ranker_baseline_return`.

**What to do**:
1. In `src/backtest/paper_trading.py`: log the ranker's would-have-entered signals (every candidate above the ranking threshold, whether or not the trigger gate allowed entry)
2. For each would-have-entered signal, record the hypothetical return if entered without trigger gating
3. Export this as `ranker_baseline_return` in the paper trading log
4. SentimentPulse's `run_feedback.py` then computes `trigger_alpha = actual_return - ranker_baseline_return`

**Files**: `src/backtest/paper_trading.py`, paper trading log schema

### ENG-1.2: Enable Trigger Layer (after 30 days)
**When**: ~2026-04-20 (30 days after first crawl)
**How**: Run `python scripts/enable_trigger.py --enable` from the SentimentPulse repo

```yaml
# In config/config.yaml — will be changed by the script:
sentiment_trigger:
  enabled: true   # Flip from false to true
```

**Validation**: Run regression test comparing Sharpe with/without trigger gate before enabling in production.

---

## Phase 2 — Signal Quality

### ENG-2.1: Block Propagated Signals Without Organic Corroboration
**Source**: sentimental_blogs doc 16 §2.2

In `src/trigger/sentiment_trigger.py`, add check:
```python
if features.get('propagation_flag'):
    has_organic = features.get('headline_count', 0) > 0 or features.get('finnhub_score') is not None
    if not has_organic:
        signal = TriggerSignal.HOLD
        reasons.append("Propagated signal without organic corroboration")
```

**Files**: `src/trigger/sentiment_trigger.py`

### ENG-2.2: Separate US vs SGX Weight Calibration
**Source**: sentimental_blogs doc 16 §2.5

Split feedback dataset by market in `weight_calibrator.py`:
```python
us_weights  = recalibrate_weights(df[~df['ticker'].str.endswith('.SI')])
sgx_weights = recalibrate_weights(df[df['ticker'].str.endswith('.SI')])
```

Write: `source_weights_us_5d.json` and `source_weights_sgx_5d.json`.

**Files**: `src/trigger/weight_calibrator.py`

### ENG-2.3: Market Regime Confidence Multiplier
**Source**: sentimental_blogs doc 16 §2.3

Consume `market_regime` and `market_vix` from SentimentPulse CSV in the trigger layer. Apply confidence multiplier (FEAR=0.50, ELEVATED=0.75, NORMAL=1.00).

**Files**: `src/trigger/sentiment_trigger.py`

### ENG-2.4: Integrate Insider Cluster Flag
**Source**: sentimental_blogs doc 16 §2.6

`insider_cluster_flag=True` in SentimentPulse CSV → upgrade `HOLD → BUY` in trigger when confirmed by positive text sentiment. Already partially wired in `sentiment_trigger.py`.

**Files**: `src/trigger/sentiment_trigger.py` (verify integration)

---

## Phase 3 — Architecture

### ENG-3.1: Read DuckDB/Parquet Instead of CSV
**Source**: sentimental_blogs doc 17

When SentimentPulse migrates from CSV to DuckDB, the engine should read Parquet exports (faster, typed) instead of CSVs.

Update `src/sentiment/sentiment_adapter.py`:
```python
# Before: pd.read_csv("sentimentpulse_*.csv")
# After:  pd.read_parquet("sentimentpulse.parquet") or duckdb.query()
```

**Files**: `src/sentiment/sentiment_adapter.py`

### ENG-3.2: Trigger Attribution Logging
**Source**: sentimental_blogs doc 16 §3.4

Log every trigger evaluation to DuckDB `trigger_log` table:
- `eval_id`, `run_id`, `ticker`, `signal`, `confidence`, `regime`
- `was_acted_on` (did paper trading execute?)
- `blocking_reason` (why was it held?)

Enables: false negative analysis, trigger gate alpha computation.

**Files**: `src/trigger/sentiment_trigger.py`

### ENG-3.3: Regime-Adjusted Position Sizing
**Source**: sentimental_blogs doc 10 §1.4

```python
REGIME_SIZE_MULTIPLIERS = {
    'MOMENTUM': 1.0, 'CONTRARIAN': 0.7,
    'UNCERTAINTY': 0.5, 'NOISE': 0.3,
}
```

**Files**: `src/risk/position_sizer.py` (if it exists), or `src/backtest/paper_trading.py`

---

## Phase 4 — Long-Term

| # | Task | When |
|---|------|------|
| ENG-4.1 | Backtest trigger layer on historical data (Polygon backfill) | 6mo data |
| ENG-4.2 | Walk-forward validation of trigger alpha vs ranker-only | 90 days |
| ENG-4.3 | Integrate Quiver Congress signal into trigger features | $10/mo justified |

---

## Key Constraints

1. **`use_sentiment: false` is PERMANENT** — sentiment never enters the cross-sectional ranker
2. **Features and feedback are in separate directories** — `data/sentiment/` (features) vs `data/sentiment/feedback/` (returns)
3. **`FORBIDDEN_COLS` assertion** — `sentiment_adapter.py` raises `ValueError` if feedback columns appear in feature data
4. **Trigger layer is downstream** — ranker produces candidates → trigger gates timing → position sizer determines allocation

---

## Cross-References

- SentimentPulse tasks: `sentimental_blogs/docs/18-sentimentpulse-improvement-tasks.md`
- Gap analysis: `sentimental_blogs/docs/12-engine-sentimentpulse-gap-analysis.md`
- Engine integration design: `sentimental_blogs/docs/05-engine-integration.md`
- Trigger layer code: `src/trigger/sentiment_trigger.py`
- Sentiment adapter: `src/sentiment/sentiment_adapter.py`
- Weight calibrator: `src/trigger/weight_calibrator.py`
