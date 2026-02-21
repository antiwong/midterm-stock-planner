# Risk Management

> **Part of**: [Mid-term Stock Planner Design](design.md)
> 
> This document covers risk metrics, position sizing, and portfolio risk management.

## Related Documents

- [design.md](design.md) - Main overview and architecture
- [backtesting.md](backtesting.md) - Uses risk metrics for evaluation
- [visualization-analytics.md](visualization-analytics.md) - Risk visualization
- **[risk-parity.md](risk-parity.md)** - Advanced risk parity allocation, beta control, sector constraints
- **Factor complexity & redundancy** - `src/risk/complexity.py`: `compute_config_complexity`, `compute_factor_redundancy`. Used in evolutionary optimizer (`--complexity-penalty`, `--reject-complexity-above`). See [quantaalpha-feature-proposal.md §3](quantaalpha-feature-proposal.md)

---

## 1. Risk Metrics Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       RISK METRICS TAXONOMY                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│  RETURN-BASED   │   DRAWDOWN      │   VALUE-AT-RISK │   RELATIVE      │
├─────────────────┼─────────────────┼─────────────────┼─────────────────┤
│ • Sharpe Ratio  │ • Max Drawdown  │ • VaR (95%)     │ • Beta          │
│ • Sortino Ratio │ • Avg Drawdown  │ • CVaR/ES       │ • Info Ratio    │
│ • Calmar Ratio  │ • Drawdown Dur. │ • Parametric VaR│ • Tracking Err  │
│ • Win Rate      │                 │ • Monte Carlo   │ • Alpha         │
│ • Profit Factor │                 │                 │                 │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

---

## 2. Core Risk Metrics

### 2.1 Sharpe Ratio

```python
def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> float:
    """
    Sharpe Ratio = (Mean Return - Risk-Free Rate) / Std Dev
    
    Annualized: multiply by sqrt(periods_per_year)
    """
    excess_returns = returns - risk_free_rate / periods_per_year
    return np.sqrt(periods_per_year) * excess_returns.mean() / excess_returns.std()
```

### 2.2 Sortino Ratio

```python
def calculate_sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> float:
    """
    Sortino Ratio = (Mean Return - Risk-Free Rate) / Downside Deviation
    
    Only penalizes downside volatility, not upside.
    """
    excess_returns = returns - risk_free_rate / periods_per_year
    downside_returns = excess_returns[excess_returns < 0]
    downside_std = np.sqrt((downside_returns ** 2).mean())
    return np.sqrt(periods_per_year) * excess_returns.mean() / downside_std
```

### 2.3 Maximum Drawdown

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MAXIMUM DRAWDOWN                                     │
└─────────────────────────────────────────────────────────────────────────────┘

                    Peak
                     ↓
  Value    ●────────●
           │        │╲
           │        │ ╲
           │        │  ╲────────●  Trough
           │        │           │╲
           │        │           │ ╲
           │        │           │  ╲────●
           │        │           │       │
           └────────┴───────────┴───────┴──────▶ Time
           
           Max Drawdown = (Peak - Trough) / Peak
```

```python
def calculate_max_drawdown(equity_curve: pd.Series) -> Tuple[float, int, int]:
    """
    Calculate maximum drawdown and its duration.
    
    Returns:
        Tuple of (max_drawdown_pct, peak_idx, trough_idx)
    """
    rolling_max = equity_curve.expanding().max()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_dd = drawdown.min()
    trough_idx = drawdown.idxmin()
    peak_idx = equity_curve[:trough_idx].idxmax()
    return max_dd, peak_idx, trough_idx
```

### 2.4 Value at Risk (VaR)

```python
def calculate_var(
    returns: pd.Series,
    confidence: float = 0.95,
    method: str = "historical"
) -> float:
    """
    Value at Risk - maximum expected loss at confidence level.
    
    Methods:
    - historical: percentile of actual returns
    - parametric: assume normal distribution
    - monte_carlo: simulation-based
    """
    if method == "historical":
        return returns.quantile(1 - confidence)
    elif method == "parametric":
        return returns.mean() - stats.norm.ppf(confidence) * returns.std()
```

### 2.5 CVaR (Expected Shortfall)

```python
def calculate_cvar(
    returns: pd.Series,
    confidence: float = 0.95
) -> float:
    """
    Conditional VaR = Expected loss given loss exceeds VaR.
    Also called Expected Shortfall (ES).
    """
    var = calculate_var(returns, confidence)
    return returns[returns <= var].mean()
```

---

## 3. Position Sizing Methods

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    POSITION SIZING METHODS                                   │
└─────────────────────────────────────────────────────────────────────────────┘

  Method              Risk Profile    Best For
  ─────────────────────────────────────────────────────────────────────
  Equal Weight        Low             Simple baseline
  Vol-Weighted        Medium          Risk parity approach
  Score-Weighted      Medium-High     Factor tilting
  Kelly Criterion     High            Optimal growth (aggressive)
  ATR-Based           Adaptive        Volatility-adjusted stops
```

### 3.1 Equal Weight

```python
def equal_weight_sizing(tickers: List[str], capital: float) -> Dict[str, float]:
    """Equal allocation to all positions."""
    weight = 1.0 / len(tickers)
    return {ticker: weight * capital for ticker in tickers}
```

### 3.2 Volatility-Weighted (Risk Parity)

```python
def volatility_weighted_sizing(
    tickers: List[str],
    volatilities: Dict[str, float],
    capital: float,
    target_vol: float = 0.15
) -> Dict[str, float]:
    """
    Weight inversely by volatility for equal risk contribution.
    
    Higher vol stocks get smaller positions.
    """
    inv_vol = {t: 1.0 / v for t, v in volatilities.items()}
    total_inv_vol = sum(inv_vol.values())
    weights = {t: iv / total_inv_vol for t, iv in inv_vol.items()}
    return {t: w * capital for t, w in weights.items()}
```

### 3.3 Score-Weighted

```python
def score_weighted_sizing(
    scores: Dict[str, float],
    capital: float,
    min_weight: float = 0.02,
    max_weight: float = 0.10
) -> Dict[str, float]:
    """
    Weight by model scores, with constraints.
    
    Higher conviction stocks get larger positions.
    """
    # Normalize scores to positive
    min_score = min(scores.values())
    adjusted = {t: s - min_score + 0.01 for t, s in scores.items()}
    total = sum(adjusted.values())
    
    # Calculate raw weights
    weights = {t: s / total for t, s in adjusted.items()}
    
    # Apply constraints
    weights = {t: max(min_weight, min(max_weight, w)) for t, w in weights.items()}
    
    # Renormalize
    total = sum(weights.values())
    return {t: (w / total) * capital for t, w in weights.items()}
```

### 3.4 Kelly Criterion

```python
def kelly_criterion_sizing(
    win_rate: float,
    win_loss_ratio: float,
    capital: float,
    kelly_fraction: float = 0.5  # Half-Kelly for safety
) -> float:
    """
    Kelly Criterion for optimal growth.
    
    f* = (p * b - q) / b
    where p = win_rate, q = 1-p, b = win/loss ratio
    """
    p = win_rate
    q = 1 - p
    b = win_loss_ratio
    
    kelly = (p * b - q) / b
    return max(0, kelly * kelly_fraction) * capital
```

### 3.5 ATR-Based Sizing

```python
def atr_based_sizing(
    atr: float,
    capital: float,
    risk_per_trade: float = 0.02,  # Risk 2% per trade
    atr_multiplier: float = 2.0    # Stop at 2x ATR
) -> float:
    """
    Position size based on ATR for volatility-adjusted stops.
    
    Size = (Capital × Risk%) / (ATR × Multiplier)
    """
    stop_distance = atr * atr_multiplier
    position_size = (capital * risk_per_trade) / stop_distance
    return position_size
```

---

## 4. Portfolio Risk

### 4.1 Correlation Analysis

```python
def calculate_correlation_matrix(
    returns_df: pd.DataFrame
) -> pd.DataFrame:
    """Calculate correlation matrix of returns."""
    return returns_df.corr()

def calculate_diversification_score(
    weights: Dict[str, float],
    correlation_matrix: pd.DataFrame
) -> float:
    """
    Diversification score based on portfolio correlation.
    
    Score of 1.0 = perfectly diversified
    Score of 0.0 = highly concentrated
    """
    tickers = list(weights.keys())
    w = np.array([weights[t] for t in tickers])
    corr = correlation_matrix.loc[tickers, tickers].values
    
    avg_corr = (w @ corr @ w - w @ w) / (1 - w @ w)
    return 1 - avg_corr
```

### 4.2 Portfolio Volatility

```python
def calculate_portfolio_volatility(
    weights: Dict[str, float],
    cov_matrix: pd.DataFrame
) -> float:
    """
    Portfolio volatility from covariance matrix.
    
    σ_p = sqrt(w' Σ w)
    """
    tickers = list(weights.keys())
    w = np.array([weights[t] for t in tickers])
    cov = cov_matrix.loc[tickers, tickers].values
    
    return np.sqrt(w @ cov @ w)
```

### 4.3 Sector Exposure

```python
def analyze_sector_exposure(
    weights: Dict[str, float],
    sector_mapping: Dict[str, str],
    max_sector_weight: float = 0.25
) -> Dict[str, Any]:
    """
    Analyze and warn about sector concentration.
    """
    sector_weights = defaultdict(float)
    for ticker, weight in weights.items():
        sector = sector_mapping.get(ticker, "Unknown")
        sector_weights[sector] += weight
    
    warnings = []
    for sector, weight in sector_weights.items():
        if weight > max_sector_weight:
            warnings.append(f"{sector}: {weight:.1%} exceeds limit")
    
    return {
        "sector_weights": dict(sector_weights),
        "warnings": warnings,
        "max_sector": max(sector_weights.values())
    }
```

### 4.4 Risk Limits

```python
def monitor_risk_limits(
    portfolio: Dict[str, float],
    limits: Dict[str, float]
) -> List[str]:
    """
    Check portfolio against risk limits.
    
    Limits:
    - max_position: Maximum single position
    - max_sector: Maximum sector weight
    - max_drawdown: Maximum drawdown threshold
    - max_var: Maximum VaR threshold
    """
    violations = []
    
    # Check position limits
    for ticker, weight in portfolio.items():
        if weight > limits.get("max_position", 0.10):
            violations.append(f"{ticker} exceeds position limit: {weight:.1%}")
    
    return violations
```

---

## 5. Stress Testing

```python
def run_stress_test(
    returns: pd.DataFrame,
    scenarios: Dict[str, Dict[str, float]]
) -> Dict[str, float]:
    """
    Run stress test with custom scenarios.
    
    Example scenarios:
    - "2008_crisis": {"market": -0.50, "vol": +0.80}
    - "covid_crash": {"market": -0.35, "vol": +0.50}
    - "rate_shock": {"market": -0.15, "rates": +0.02}
    """
    results = {}
    for scenario_name, shocks in scenarios.items():
        stressed_returns = apply_shocks(returns, shocks)
        results[scenario_name] = stressed_returns.sum()
    return results
```

---

## 6. Position Constraints

```python
def apply_position_constraints(
    weights: Dict[str, float],
    max_weight: float = 0.05,
    min_weight: float = 0.01,
    max_sector_weight: float = 0.25,
    sector_mapping: Dict[str, str] = None
) -> Dict[str, float]:
    """
    Apply position and sector constraints.
    
    Returns adjusted weights that satisfy all constraints.
    """
    # Clip individual positions
    weights = {t: max(min_weight, min(max_weight, w)) for t, w in weights.items()}
    
    # Apply sector constraints if mapping provided
    if sector_mapping:
        weights = adjust_for_sector_limits(weights, sector_mapping, max_sector_weight)
    
    # Renormalize to sum to 1
    total = sum(weights.values())
    return {t: w / total for t, w in weights.items()}
```

---

## 7. Usage Examples

### 7.1 Calculate All Metrics

```python
from src.risk.metrics import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_var,
    calculate_cvar
)

# Calculate metrics
sharpe = calculate_sharpe_ratio(returns)
sortino = calculate_sortino_ratio(returns)
max_dd, peak, trough = calculate_max_drawdown(equity_curve)
var_95 = calculate_var(returns, confidence=0.95)
cvar_95 = calculate_cvar(returns, confidence=0.95)

print(f"Sharpe: {sharpe:.2f}")
print(f"Sortino: {sortino:.2f}")
print(f"Max DD: {max_dd:.2%}")
print(f"VaR 95%: {var_95:.2%}")
print(f"CVaR 95%: {cvar_95:.2%}")
```

### 7.2 Position Sizing

```python
from src.risk.position_sizing import volatility_weighted_sizing

# Get volatilities
volatilities = {"AAPL": 0.25, "NVDA": 0.45, "MSFT": 0.22}

# Calculate positions
positions = volatility_weighted_sizing(
    tickers=list(volatilities.keys()),
    volatilities=volatilities,
    capital=100000
)

print("Positions:")
for ticker, size in positions.items():
    print(f"  {ticker}: ${size:,.0f}")
```

---

## 8. Advanced Risk Parity

For advanced volatility-aware portfolio construction, see the dedicated **[risk-parity.md](risk-parity.md)** document which covers:

- **Inverse Volatility Weighting** - Simple risk-aware allocation
- **Risk Parity (Equal Risk Contribution)** - Each position contributes equally to risk
- **Vol-Capped Sizing** - Maximum volatility contribution per position
- **Beta-Adjusted Allocation** - Target specific portfolio beta
- **Sector Constraints** - Prevent over-concentration in volatile sectors

```python
from src.risk import RiskParityAllocator, SectorConstraints

allocator = RiskParityAllocator(capital=100_000, target_portfolio_vol=0.15)
positions, profile = allocator.allocate_portfolio(
    scores=scores,
    volatilities=vols,
    betas=betas,
    sector_map=sectors,
    method="risk_parity",
)

print(f"Portfolio Beta: {profile.total_beta:.2f}")
print(f"Risk Tilt: {profile.risk_tilt}")
```

---

## Related Documents

- **Back to**: [design.md](design.md) - Main overview
- **Backtesting**: [backtesting.md](backtesting.md) - Uses these metrics
- **Visualization**: [visualization-analytics.md](visualization-analytics.md) - Risk charts
- **Risk Parity**: [risk-parity.md](risk-parity.md) - Advanced allocation methods