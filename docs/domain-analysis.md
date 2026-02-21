# Domain Analysis

Domain analysis provides systematic stock selection through vertical (within-sector) and horizontal (cross-sector) analysis.

## Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         STOCK UNIVERSE                                │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      VERTICAL ANALYSIS                                │
│                    (Within Each Sector)                               │
├──────────────────────────────────────────────────────────────────────┤
│  Technology    Healthcare    Finance    Consumer    Energy           │
│  ┌─────────┐  ┌─────────┐  ┌────────┐  ┌────────┐  ┌──────┐         │
│  │ Top 5   │  │ Top 5   │  │ Top 5  │  │ Top 5  │  │Top 5 │         │
│  │ stocks  │  │ stocks  │  │ stocks │  │ stocks │  │stocks│         │
│  └─────────┘  └─────────┘  └────────┘  └────────┘  └──────┘         │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     HORIZONTAL ANALYSIS                               │
│                    (Across All Sectors)                               │
├──────────────────────────────────────────────────────────────────────┤
│  Candidate Pool (25 stocks) ──▶ Apply Constraints ──▶ Final 10       │
│                                                                       │
│  Constraints:                                                         │
│  • Max sector weight: 35%                                            │
│  • Max position: 15%                                                 │
│  • Min diversification: 0.70                                         │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      FINAL PORTFOLIO                                  │
│                       (10 stocks)                                     │
└──────────────────────────────────────────────────────────────────────┘
```

## Vertical Analysis

Vertical analysis ranks stocks **within each sector** to identify the best opportunities in each domain.

### Process

1. **Filter by Sector**: Group stocks by sector
2. **Apply Quality Filters**: 
   - ROE > 0 (profitable)
   - Net margin > 0
   - Debt/equity < threshold
3. **Compute Domain Score**: Weighted combination of:
   - Model score (predicted excess return)
   - Value score (PE/PB ranking)
   - Quality score (ROE, margins)
4. **Rank Within Sector**: Sort by domain score
5. **Select Top K**: Pick top candidates per sector

### Domain Score Formula

```
domain_score = w_m × model_score + w_v × value_score + w_q × quality_score
```

Default weights (configurable in `config.yaml`):
- `w_m` (model) = 0.5
- `w_v` (value) = 0.3
- `w_q` (quality) = 0.2

### Configuration

```yaml
analysis:
  weights:
    model_score: 0.5
    value_score: 0.3
    quality_score: 0.2
  
  filters:
    min_roe: 0.0
    min_net_margin: 0.0
    max_debt_to_equity: 2.0
  
  vertical:
    top_k_per_sector: 5
    export_candidates: true
```

### Output Files

For each sector:
```
vertical_candidates_{date}_{sector}.csv
```

Columns:
- `ticker`: Stock symbol
- `sector`: Sector name
- `industry`: Industry within sector
- `model_score`: LightGBM prediction
- `value_score`: Valuation composite
- `quality_score`: Quality composite
- `domain_score`: Combined score
- `domain_rank_in_sector`: Rank within sector
- PE, PB, ROE, debt/equity, margins

## Horizontal Analysis

Horizontal analysis selects stocks **across sectors** to build a diversified portfolio.

### Process

1. **Pool Candidates**: Union of all vertical top-K
2. **Compute Returns**: Historical return time series
3. **Calculate Risk Metrics**:
   - Correlation matrix
   - Covariance matrix
   - Individual volatilities
4. **Initial Weighting**: Score-weighted sizing
5. **Apply Constraints**:
   - Max position weight
   - Max sector weight
   - Min diversification
6. **Evaluate Portfolio**:
   - Expected return
   - Volatility
   - Sharpe ratio
   - Max drawdown
   - VaR/CVaR
7. **Optimize** (optional): Select best combination

### Portfolio Construction Methods

#### 1. Score-Weighted (Default)

```python
weights = domain_scores / domain_scores.sum()
```

Higher scoring stocks get higher weights.

#### 2. Equal Weight

```python
weights = 1 / n_stocks
```

Simple, maximizes diversification.

#### 3. Risk Parity

```python
inv_vol = 1 / volatilities
weights = inv_vol / inv_vol.sum()
```

Lower volatility stocks get higher weights.

#### 4. Optimization (Heuristic)

Enumerate combinations and select best Sharpe ratio subject to constraints.

### Configuration

```yaml
analysis:
  horizontal:
    portfolio_size: 10
    max_position_weight: 0.15
    min_position_weight: 0.03
    max_sector_weight: 0.35
    selection_method: 'heuristic'  # or 'score_weighted'
    min_diversification: 0.70
    target_volatility: 0.25
    target_max_drawdown: 0.20
```

### Output Files

```
portfolio_candidates_{date}.csv
portfolio_metrics_{date}.json
```

Portfolio CSV columns:
- `ticker`, `sector`
- `domain_score`, `value_score`, `quality_score`
- `initial_weight`, `final_weight`
- `volatility`, `correlation_avg`
- `risk_contribution`

Metrics JSON:
```json
{
  "expected_return": 0.15,
  "volatility": 0.18,
  "sharpe_ratio": 0.83,
  "sortino_ratio": 1.2,
  "max_drawdown": -0.12,
  "var_95": -0.025,
  "cvar_95": -0.035,
  "diversification_score": 0.75,
  "effective_n": 8.5,
  "sector_hhi": 0.22
}
```

## Risk Metrics

### Portfolio-Level

| Metric | Description |
|--------|-------------|
| **Expected Return** | Annualized mean return |
| **Volatility** | Annualized standard deviation |
| **Sharpe Ratio** | Risk-adjusted return |
| **Sortino Ratio** | Downside risk-adjusted return |
| **Max Drawdown** | Largest peak-to-trough decline |
| **VaR (95%)** | 5th percentile daily return |
| **CVaR (95%)** | Average of worst 5% returns |

### Diversification

| Metric | Description | Target |
|--------|-------------|--------|
| **Diversification Score** | 1 - HHI (weight concentration) | > 0.70 |
| **Effective N** | 1/HHI (equivalent equal-weight positions) | > 5 |
| **Sector HHI** | Sector concentration | < 0.30 |

## Usage

### Dashboard

1. Go to **🎮 Run Analysis**
2. Select a run with backtest complete
3. Click **▶️ Run Domain Analysis** in Stage 3 tab
4. View results in **💼 Portfolio Analysis** > Domain Analysis Results

### Command Line

```bash
# Run domain analysis on latest run
python scripts/run_domain_analysis.py

# Specific run
python scripts/run_domain_analysis.py --run-id 20251231_115520_abc123

# Custom output
python scripts/run_domain_analysis.py --output output/my_analysis
```

### Programmatic

```python
from src.analysis.domain_analysis import (
    DomainAnalyzer,
    AnalysisConfig,
    VerticalResult,
    HorizontalResult,
)

# Create config
config = AnalysisConfig(
    weights={'model': 0.5, 'value': 0.3, 'quality': 0.2},
    filters={'min_roe': 0, 'max_debt_equity': 2.0},
    portfolio_size=10,
    max_position_weight=0.15,
    max_sector_weight=0.35,
)

# Create analyzer
analyzer = DomainAnalyzer(config, output_dir="output")

# Run vertical analysis
vertical_results = analyzer.run_vertical_analysis(
    stocks_df=scores_df,
    date=datetime.now(),
    top_k=5,
)

# Run horizontal analysis
horizontal_result = analyzer.run_horizontal_analysis(
    vertical_results=vertical_results,
    returns_df=returns_df,
)

# Access results
print(horizontal_result.portfolio)
print(horizontal_result.risk_metrics)
```

## Interpretation

### Good Portfolio Signs

- ✅ Sharpe ratio > 1.0
- ✅ Diversification score > 0.70
- ✅ Max sector weight < 35%
- ✅ Max drawdown < target

### Warning Signs

- ⚠️ Sharpe ratio < 0.5
- ⚠️ Diversification score < 0.50
- ⚠️ Single sector > 40%
- ⚠️ Single position > 20%
- ⚠️ Max drawdown > 25%

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Low diversification | Too few sectors | Increase top_k_per_sector |
| High volatility | Aggressive stocks | Lower risk tolerance |
| Poor Sharpe | Wrong weights | Adjust score weights |
| Sector concentration | Small universe | Add more stocks |

## Best Practices

1. **Start with Defaults**: Use standard config first
2. **Validate Filters**: Check filter impact on universe size
3. **Review Candidates**: Examine vertical CSVs before horizontal
4. **Check Constraints**: Ensure constraints don't over-restrict
5. **Compare Methods**: Try different weighting schemes

## Related Documentation

- [Portfolio Builder](portfolio-builder.md) - Personalized portfolios
- [Risk Management](risk-management.md) - Risk metrics, factor complexity & redundancy
- [Configuration](configuration-cli.md) - Config options
- [Backtesting](backtesting.md) - Walk-forward backtest
- [QuantaAlpha](quantaalpha-feature-proposal.md) - Strategy templates, domain_score weights
- [Design](design.md) - Architecture overview
- [Full index](README.md)
