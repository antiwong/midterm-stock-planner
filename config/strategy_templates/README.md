# Strategy Templates

Predefined strategy templates for diversified backtesting (QuantaAlpha-inspired).

**Documentation**: [docs/quantaalpha-feature-proposal.md](../docs/quantaalpha-feature-proposal.md) (§2), [docs/backtesting.md](../docs/backtesting.md), [docs/README.md](../docs/README.md)
Each template overrides backtest params and analysis weights to create distinct
strategy "tilts."

## Templates

| Template | Description | Backtest | Analysis Weights |
|----------|-------------|----------|------------------|
| **value_tilt** | Emphasize valuation | Longer train, MS rebalance | value 50%, model 30%, quality 20% |
| **momentum_tilt** | Emphasize model (momentum) | Shorter train, 2W rebalance | model 60%, value 15%, quality 25% |
| **quality_tilt** | Emphasize quality (ROE, margins) | Moderate rebalance | quality 50%, model 30%, value 20% |
| **balanced** | Equal factor weights | Default rebalance | model 40%, value 30%, quality 30% |
| **low_vol** | Lower turnover | Slower rebalance (ME) | Balanced |

## Usage

```bash
# Run all templates
python scripts/diversified_backtest.py

# Run specific templates
python scripts/diversified_backtest.py --templates value_tilt momentum_tilt quality_tilt

# With watchlist
python scripts/diversified_backtest.py --watchlist tech_giants

# Stricter diversification (max correlation 0.7)
python scripts/diversified_backtest.py --max-correlation 0.7

# Save report
python scripts/diversified_backtest.py --output output/diversified_report.json
```

## Data Requirements

Templates use `train_years: 1.0` and `test_years: 0.25` by default to work with
~600 days of data. For extended data, edit templates to use longer train (e.g.
value_tilt: 3.0, low_vol: 3.0).

## Integration with Evolutionary Optimizer

The diversified subset output can seed the evolutionary pool:
`scripts/evolutionary_backtest.py` can use template configs as initial population.
