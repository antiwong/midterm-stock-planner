#!/usr/bin/env bash
# Create beads tasks for QuantaAlpha implementation guide planned items (2.1–2.5).
# Run from repo root: ./scripts/beads_create_quantaalpha_tasks.sh



echo "Creating epic: QuantaAlpha implementation guide (planned tasks)..."
EPIC=$(bd create "QuantaAlpha implementation guide (planned tasks)" --type epic --priority 1 --description "Tasks from docs/quantaalpha-implementation-guide.md and quantaalpha-feature-proposal.md" --silent)
echo "  Epic: $EPIC"

echo "Creating task 2.1: IC threshold checking in pipeline (P1)..."
T1=$(bd create "IC threshold checking in pipeline" --parent "$EPIC" --priority 1 --type task \
  --description "Auto-reject factors with |IC| < 0.01 across walk-forward windows. See docs/quantaalpha-implementation-guide.md §2, §3." --silent)
echo "  $T1"

echo "Creating task 2.2: Volume surge + OBV institutional filter (P2)..."
T2=$(bd create "Volume surge + OBV institutional filter for AMD/NVDA" --parent "$EPIC" --priority 2 --type task \
  --description "volume_ratio > 2.0 + positive OBV slope as per-ticker filter. See implementation guide §6." --silent)
echo "  $T2"

echo "Creating task 2.3: Relative strength feature rel_strength_21d (P2)..."
T3=$(bd create "Relative strength feature rel_strength_21d" --parent "$EPIC" --priority 2 --type task \
  --description "Ticker outperformance vs SPY over 21d. See implementation guide §6 (AMD/AI stocks)." --silent)
echo "  $T3"

echo "Creating task 2.4: Regime-aware VIX gating for AI names (P2)..."
T4=$(bd create "Regime-aware VIX gating for AI names" --parent "$EPIC" --priority 2 --type task \
  --description "vix_buy_max: 25 in AMD/NVDA per-ticker YAML. See implementation guide §6." --silent)
echo "  $T4"

echo "Creating task 2.5: Overfitting detection in walk-forward (P1)..."
T5=$(bd create "Overfitting detection in walk-forward" --parent "$EPIC" --priority 1 --type task \
  --description "Alert when train Sharpe >> test Sharpe (e.g. ratio > 2x). See implementation guide §8." --silent)
echo "  $T5"

echo ""
echo "Done. List issues: bd list"
echo "Show epic: bd show $EPIC"
echo "Ready tasks: bd ready"
