# Risk-Aware Portfolio Construction

> [← Back to Documentation Index](README.md)

This document describes the volatility-aware position sizing and risk parity features implemented in the Mid-term Stock Planner.

## Overview

Traditional equal-weight or score-based allocations can result in portfolios where high-volatility stocks dominate overall risk. The risk-aware portfolio construction module addresses this by:

1. **Inverse Volatility Weighting** - Lower volatility stocks get higher weights
2. **Risk Parity** - Equal risk contribution from each position
3. **Vol-Capped Sizing** - Maximum volatility contribution per position
4. **Beta-Adjusted Allocation** - Target a specific portfolio beta
5. **Sector Constraints** - Prevent over-concentration in volatile sectors

## Module Location

```
src/risk/risk_parity.py
```

## Key Classes

### RiskParityAllocator

Main class for risk-aware portfolio construction.

```python
from src.risk import RiskParityAllocator, SectorConstraints

allocator = RiskParityAllocator(
    capital=100_000,              # Total portfolio capital
    target_portfolio_vol=0.15,    # Target 15% annual volatility
    max_position_vol_contribution=0.05,  # Max 5% vol contribution per position
    max_single_position=0.10,     # Max 10% weight per position
    risk_free_rate=0.02,          # 2% risk-free rate
)
```

### SectorConstraints

Define maximum weights per sector to prevent concentration.

```python
constraints = SectorConstraints(
    max_weights={
        'Nuclear': 0.15,        # Max 15% in nuclear stocks
        'Semiconductors': 0.20, # Max 20% in semis
        'Technology': 0.30,     # Max 30% in tech
        'Energy': 0.15,         # Max 15% in energy
    }
)
```

### RiskAwarePosition

Data class containing position information with risk metrics.

```python
@dataclass
class RiskAwarePosition:
    ticker: str
    raw_weight: float       # Original score-based weight
    risk_weight: float      # Risk-adjusted weight
    vol_contribution: float # Contribution to portfolio volatility
    beta: float            # Beta vs benchmark
    sector: str
    volatility: float      # Individual stock volatility
    score: float           # Original model score
    shares: int
    position_value: float
```

### PortfolioRiskProfile

Complete portfolio risk analysis summary.

```python
@dataclass
class PortfolioRiskProfile:
    total_beta: float           # Weighted portfolio beta
    weighted_avg_vol: float     # Weighted average volatility
    portfolio_vol_estimate: float  # Estimated portfolio volatility
    sector_exposure: Dict[str, float]  # Sector weights
    beta_exposure: Dict[str, float]    # Low/Med/High beta breakdown
    concentration_hhi: float    # Herfindahl concentration index
    effective_n: float         # Effective number of positions
    risk_tilt: str            # "High Beta", "Balanced", "Defensive"
    warnings: List[str]       # Risk warnings
```

## Allocation Methods

### 1. Inverse Volatility Weighting

Simplest risk-aware method. Weight inversely proportional to volatility.

```python
weights = allocator.inverse_volatility_weights(volatilities, tickers)
```

**Formula:** `w_i = (1/σ_i) / Σ(1/σ_j)`

**Effect:** Low-vol stocks get higher weights, high-vol stocks get lower weights.

### 2. Risk Parity (Equal Risk Contribution)

Each position contributes equally to total portfolio risk.

```python
weights = allocator.risk_parity_weights(
    volatilities=volatilities,
    correlation_matrix=corr_matrix,  # Optional
    tickers=tickers,
)
```

**With correlations:** Uses iterative optimization to achieve equal marginal risk contribution.

**Without correlations:** Falls back to inverse volatility.

### 3. Vol-Capped Weights

Apply maximum volatility contribution constraint.

```python
weights = allocator.vol_capped_weights(
    base_weights=score_weights,
    volatilities=volatilities,
    max_vol_contribution=0.05,  # 5% max
)
```

**Formula:** If `w_i * σ_i > max_vol`, then `w_i = max_vol / σ_i`

### 4. Beta-Adjusted Weights

Adjust weights to achieve target portfolio beta.

```python
weights = allocator.beta_adjusted_weights(
    base_weights=weights,
    betas=betas,
    target_beta=1.0,  # Market-neutral
)
```

## Full Portfolio Allocation

The `allocate_portfolio` method combines all steps:

```python
positions, profile = allocator.allocate_portfolio(
    scores=scores,           # Dict[ticker, score]
    volatilities=vols,       # Dict[ticker, annualized_vol]
    betas=betas,            # Dict[ticker, beta]
    sector_map=sectors,     # Dict[ticker, sector]
    prices=prices,          # Dict[ticker, price]
    method="risk_parity",   # or "inverse_vol", "vol_capped", "beta_adjusted"
    correlation_matrix=corr,  # Optional
    constraints=constraints,  # SectorConstraints
    target_beta=1.0,
)
```

**Returns:**
- `positions`: List[RiskAwarePosition] - Sorted by weight
- `profile`: PortfolioRiskProfile - Risk analysis summary

## Risk Profile Analysis

### Beta Exposure

Portfolio beta indicates market sensitivity:
- **Beta > 1.15**: High beta tilt - aggressive market exposure
- **Beta 0.85-1.15**: Balanced
- **Beta < 0.85**: Defensive

### Concentration (HHI)

Herfindahl-Hirschman Index measures concentration:
- **HHI < 1000**: Low concentration
- **HHI 1000-2000**: Moderate concentration
- **HHI > 2000**: High concentration (warning)

### Effective N

Effective number of positions = `1 / Σ(w_i²)`

For equal weights: Effective N = actual N
For concentrated portfolios: Effective N < actual N

## Report Generation

Generate a formatted risk report:

```python
from src.risk import generate_risk_report

report = generate_risk_report(
    positions=positions,
    profile=profile,
    benchmark_name="SPY",
)
print(report)  # Markdown formatted
```

## Example Workflow

```python
from src.risk import RiskParityAllocator, SectorConstraints
import pandas as pd

# 1. Load data
prices_df = pd.read_csv("data/prices.csv")
scores = {"AAPL": 0.75, "NVDA": 0.85, "URA": 0.70, ...}

# 2. Calculate volatilities
allocator = RiskParityAllocator(capital=100_000)
returns_df = calculate_returns(prices_df)
vols = allocator.calculate_stock_volatilities(returns_df)

# 3. Calculate betas
benchmark = pd.read_csv("data/benchmark.csv")
betas = allocator.calculate_stock_betas(returns_df, benchmark['return'])

# 4. Define constraints
constraints = SectorConstraints(max_weights={
    'Nuclear': 0.15,
    'Semiconductors': 0.20,
})

# 5. Allocate
positions, profile = allocator.allocate_portfolio(
    scores=scores,
    volatilities=vols,
    betas=betas,
    sector_map=sector_map,
    prices=current_prices,
    method="risk_parity",
    constraints=constraints,
)

# 6. Analyze
print(f"Portfolio Beta: {profile.total_beta:.2f}")
print(f"Est. Volatility: {profile.portfolio_vol_estimate*100:.1f}%")
print(f"Risk Tilt: {profile.risk_tilt}")

for warning in profile.warnings:
    print(f"⚠️ {warning}")
```

## CLI Script

Run risk-aware analysis from command line:

```bash
python scripts/run_risk_aware_analysis.py \
    --method risk_parity \
    --capital 100000 \
    --target-vol 0.15 \
    --max-position 0.10
```

**Options:**
- `--run-id`: Specific analysis run to optimize (latest if omitted)
- `--method`: `risk_parity`, `inverse_vol`, `vol_capped`, `beta_adjusted`
- `--capital`: Portfolio capital
- `--target-vol`: Target portfolio volatility
- `--max-position`: Maximum single position weight

## Output Files

Generated in `output/{run_id}_risk_analysis/`:

| File | Description |
|------|-------------|
| `risk_report.md` | Comprehensive risk analysis report |
| `ai_risk_insights.md` | AI-generated risk analysis |
| `risk_adjusted_positions.json` | Machine-readable positions |

## Comparison: Equal Weight vs Risk Parity

| Aspect | Equal Weight | Risk Parity |
|--------|--------------|-------------|
| Simplicity | Simple | More complex |
| Risk distribution | Uneven (high-vol dominates) | Even |
| Turnover | Lower | Higher |
| Sharpe improvement | Baseline | Typically +0.1-0.3 |
| Best for | Diversified universe | Mixed volatility |

## Best Practices

1. **Use sector constraints** to prevent concentration in volatile sectors
2. **Cap individual positions** at 10% to ensure diversification
3. **Monitor beta exposure** to avoid unintended market tilts
4. **Rebalance monthly** to maintain risk targets
5. **Review warnings** in the risk profile before investing

## References

- Maillard, Roncalli, Teïletche (2010). "On the Properties of Equally-Weighted Risk Contributions Portfolios"
- Qian (2005). "Risk Parity Portfolios"

---

## See Also

- [Core risk metrics](risk-management.md)
- [Portfolio construction](portfolio-builder.md)
- [Advanced risk analysis](risk-analysis-guide.md)
- [Sector-based selection](domain-analysis.md)
