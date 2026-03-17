# GARCH Volatility Modeling: Design Document

> [← Back to Documentation Index](README.md)

**Version:** 2.0  
**Date:** January 2026  
**Status:** Design Phase (Updated with Professional-Grade Approach)  
**Related Documents:** [risk-management.md](risk-management.md), [risk-parity.md](risk-parity.md), [risk-analysis-guide.md](risk-analysis-guide.md)

**Update Notes (v2.0):**
- Added asset-class-specific model selection (EGARCH for equities, GJR-GARCH for commodities, ST-GARCH for FX)
- Added covariance matrix prediction from GARCH forecasts
- Added volatility targeting / risk parity with dynamic weights
- Added walk-forward validation for backtesting
- Added Skew-t distribution for tail risk estimation
- Updated metrics to focus on Sortino ratio and Expected Shortfall
- Added VaR breach tracking as primary validation metric

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [GARCH Approach Overview](#3-garch-approach-overview)
4. [Comparison & Benefits](#4-comparison--benefits)
5. [Technical Architecture](#5-technical-architecture)
6. [Implementation Phases](#6-implementation-phases)
7. [Integration Points](#7-integration-points)
8. [Configuration & Usage](#8-configuration--usage)
9. [Testing & Validation](#9-testing--validation)
10. [Future Enhancements](#10-future-enhancements)
11. [Risks & Mitigation](#11-risks--mitigation)
12. [Success Metrics](#12-success-metrics)
13. [Appendix](#13-appendix)

---

## 1. Executive Summary

### 1.1 Purpose

This document outlines the design for integrating **GARCH (Generalized Autoregressive Conditional Heteroskedasticity)** volatility models into the Mid-term Stock Planner system. GARCH models provide **time-varying, conditional volatility** estimates that adapt to market conditions, addressing critical limitations in the current static volatility approach.

### 1.2 Problem Statement

The current system uses **historical standard deviation** as a fixed volatility estimate. This approach:

- **Fails to adapt** to changing market conditions
- **Underestimates risk** during crisis periods (volatility clustering)
- **Overestimates risk** during calm periods
- **Cannot capture leverage effects** (asymmetric volatility response to positive/negative shocks)
- **Provides no forward-looking volatility forecasts** for dynamic risk management

### 1.3 Solution Overview

Integrate GARCH models using a **professional-grade approach** that shifts from "predicting returns" to "predicting the **Covariance Matrix**" for volatility-adjusted portfolio construction:

1. **Asset-Class-Specific Model Selection:**
   - **EGARCH** for equities (leverage effects)
   - **GJR-GARCH** for commodities (supply/demand shocks)
   - **ST-GARCH** for FX/currencies (smooth regime transitions)

2. **Covariance Matrix Prediction:**
   - Generate time-varying covariance matrices from GARCH volatility forecasts
   - Enable volatility-adjusted portfolio weights via risk parity

3. **Walk-Forward Backtesting:**
   - Rolling window estimation (not simple train-test split)
   - One-day-ahead volatility forecasts with memory preservation

4. **Volatility Targeting:**
   - Dynamic position sizing based on GARCH-predicted volatility
   - Automatic exposure reduction when volatility spikes

5. **Tail Risk Detection:**
   - Skew-t distribution for accurate tail event probability
   - Expected Shortfall (ES) as primary risk metric

### 1.4 Scope

**In Scope:**
- Standard GARCH(1,1) implementation
- **EGARCH** for equities (leverage effects)
- **GJR-GARCH** for commodities (threshold effects)
- **ST-GARCH** for FX/currencies (smooth transition regimes)
- Covariance matrix prediction from GARCH forecasts
- Volatility targeting / risk parity allocation
- Walk-forward validation for backtesting
- Skew-t distribution for tail risk
- Integration with VaR/CVaR/ES calculations
- Backward compatibility with existing risk metrics

**Out of Scope (Future Phases):**
- RealGARCH (intraday data)
- Hybrid AI models (GARCH + LSTM for correlation forecasting)
- Option pricing applications

---

## 2. Current State Analysis

### 2.1 Volatility Calculation

**Location:** `src/risk/risk_parity.py:99-121`

**Current Implementation:**
```python
def calculate_stock_volatilities(
    self,
    returns_df: pd.DataFrame,
    annualize: bool = True,
) -> Dict[str, float]:
    """Calculate annualized volatility for each stock."""
    vols = {}
    factor = np.sqrt(252) if annualize else 1.0
    
    for col in returns_df.columns:
        vol = returns_df[col].std() * factor  # Static historical std dev
        vols[col] = vol if not np.isnan(vol) else 0.30
    
    return vols
```

**Characteristics:**
- Uses **entire historical window** to compute standard deviation
- **No time-varying component** - same volatility estimate regardless of recent market conditions
- **Equal weight** to all historical returns (no recency weighting)
- **No clustering detection** - treats calm and volatile periods identically

**Limitations:**
1. **Slow reaction to shocks:** A -5% crash on day T has minimal impact on volatility estimate until it becomes a significant portion of the historical window
2. **Ghost effects:** When a crisis "falls out" of the window, volatility estimate drops abruptly even if market remains stressed
3. **No leverage effect:** Cannot distinguish between volatility from positive vs negative returns
4. **Backward-looking only:** Cannot forecast future volatility

### 2.2 VaR/CVaR Calculation

**Location:** `src/risk/metrics.py:171-234`

**Current Implementation:**
```python
def calculate_var(
    self,
    returns: pd.Series,
    confidence_level: float = 0.95,
    method: str = "historical"
) -> float:
    """Calculate Value at Risk."""
    if method == "historical":
        var = np.percentile(returns, (1 - confidence_level) * 100)
    elif method == "parametric":
        mean_return = returns.mean()
        std_return = returns.std()  # Static volatility
        z_score = stats.norm.ppf(1 - confidence_level)
        var = mean_return + (z_score * std_return)
    elif method == "monte_carlo":
        mean_return = returns.mean()
        std_return = returns.std()  # Static volatility
        simulated = np.random.normal(mean_return, std_return, 10000)
        var = np.percentile(simulated, (1 - confidence_level) * 100)
```

**Characteristics:**
- **Historical method:** Uses percentile of past returns (assumes past distribution = future distribution)
- **Parametric method:** Assumes normal distribution with **constant volatility**
- **Monte Carlo method:** Simulates from **constant volatility** distribution

**Limitations:**
1. **No conditional adjustment:** VaR estimate doesn't change based on recent volatility spikes
2. **Underestimates risk in crises:** During 2008 or 2020, VaR should spike but current method uses long-term average volatility
3. **Overestimates risk in calm periods:** During stable markets, VaR should be lower but current method uses historical average

**Example Problem:**
- **Day 1 (calm):** VaR(95%) = -2.5% (based on 20% annual vol)
- **Day 2 (after -5% crash):** VaR(95%) = -2.5% (unchanged, still uses historical average)
- **GARCH would show:** VaR(95%) = -4.5% (adjusted for volatility spike)

### 2.3 Risk Parity Allocation

**Location:** `src/risk/risk_parity.py:162-193`

**Current Implementation:**
```python
def inverse_volatility_weights(
    self,
    volatilities: Dict[str, float],  # Static historical vols
    tickers: List[str],
) -> Dict[str, float]:
    """Calculate inverse volatility weights."""
    inv_vols = {}
    for ticker in tickers:
        vol = volatilities.get(ticker, 0.30)
        if vol > 0.01:
            inv_vols[ticker] = 1.0 / vol
    
    total = sum(inv_vols.values())
    return {t: iv / total for t, iv in inv_vols.items()}
```

**Characteristics:**
- Uses **static historical volatility** to determine weights
- **No dynamic adjustment** when individual stock volatility spikes
- Portfolio weights remain fixed until next rebalance, even if volatility regime changes

**Limitations:**
1. **No crisis response:** If a stock's volatility spikes from 20% to 60%, portfolio weight doesn't adjust until next rebalance
2. **No volatility forecasting:** Cannot preemptively reduce exposure to stocks expected to become more volatile
3. **Equal treatment:** Treats a 20% vol stock the same whether it's in a calm or crisis period

### 2.4 Stress Testing

**Location:** `scripts/stress_testing.py`, `src/risk/portfolio.py:160-212`

**Current Implementation:**
- Uses **scenario-based stress tests** with fixed multipliers (e.g., "Tech Crash: -30%")
- **No volatility-based stress scenarios** (e.g., "What if volatility doubles?")
- Stress tests are **static** - same scenarios regardless of current volatility regime

**Limitations:**
1. **No conditional stress:** Stress scenarios don't adjust based on current volatility
2. **No volatility shock scenarios:** Cannot test "what if volatility spikes to 2008 levels?"
3. **No regime-aware stress:** Same stress test in calm vs crisis periods

### 2.5 Summary of Current Limitations

| Component | Current Approach | Key Limitation |
|-----------|-----------------|----------------|
| **Volatility** | Historical std dev | Static, no time-variation |
| **VaR/CVaR** | Historical/Parametric with static vol | No conditional adjustment |
| **Risk Parity** | Inverse vol with static estimates | No dynamic response to volatility spikes |
| **Stress Testing** | Fixed scenario multipliers | No volatility-based scenarios |
| **Portfolio Construction** | Uses historical vol at rebalance | No forward-looking volatility forecasts |

---

## 3. GARCH Approach Overview

### 3.1 Core Concept

GARCH models treat **volatility as time-varying** and **conditionally dependent** on past shocks. Unlike static historical standard deviation, GARCH volatility:

1. **Adapts immediately** to recent market shocks
2. **Decays smoothly** as shocks fade (no abrupt "ghost effects")
3. **Clusters** - high volatility periods followed by high volatility, calm by calm
4. **Forecasts** future volatility based on current state

### 3.2 GARCH(1,1) Model

**Mathematical Formulation:**

```
σ²ₜ = ω + α·ε²ₜ₋₁ + β·σ²ₜ₋₁

Where:
- σ²ₜ = conditional variance at time t
- ω = long-run variance (baseline)
- α = ARCH term (sensitivity to yesterday's shock)
- β = GARCH term (persistence of volatility)
- εₜ₋₁ = yesterday's return shock
```

**Intuition:**
- **ω (baseline):** Long-run average volatility
- **α (ARCH):** How much yesterday's shock increases today's volatility
- **β (GARCH):** How much yesterday's volatility persists today
- **α + β < 1:** Ensures volatility mean-reverts (doesn't explode)

**Example:**
- **Day 1:** σ = 20% (calm)
- **Day 2:** -5% crash → ε² = 0.0025 → σ spikes to 35% (GARCH reacts)
- **Day 3:** No shock → σ decays to 28% (smooth decay, no ghost effect)
- **Day 4:** No shock → σ decays to 24% (continues mean-reverting)

### 3.3 GARCH Variants for Implementation

**Critical Design Decision:** Asset-class-specific model selection is essential for professional-grade performance. Using one model for everything leads to poor out-of-sample results.

#### 3.3.1 EGARCH (Exponential GARCH) - **For Equities**
- **Asset Class:** Tech stocks, S&P 500, equity indices
- **Use Case:** Leverage effects (drops cause more vol than rises)
- **Feature:** Asymmetric response: `log(σ²ₜ) = ω + α·(|εₜ₋₁| - E|εₜ₋₁|) + γ·εₜ₋₁ + β·log(σ²ₜ₋₁)`
- **Why:** Stocks crash faster than they climb. EGARCH's exponential term captures panic selling better than symmetric models.
- **Example:** When AAPL drops -5%, EGARCH immediately predicts higher volatility tomorrow, while standard GARCH treats +5% and -5% the same.

#### 3.3.2 GJR-GARCH (Glosten-Jagannathan-Runkle) - **For Commodities**
- **Asset Class:** Gold, Oil, agricultural commodities
- **Use Case:** Threshold effects (volatility spikes after supply/demand shocks)
- **Feature:** Indicator function: `σ²ₜ = ω + α·ε²ₜ₋₁ + γ·I(εₜ₋₁<0)·ε²ₜ₋₁ + β·σ²ₜ₋₁`
- **Why:** Commodities have asymmetric shocks from supply disruptions. GJR-GARCH's threshold switch identifies exactly when a price spike enters a "high-risk" state.
- **Example:** Oil price spike from supply disruption → GJR-GARCH flags high volatility state immediately.

#### 3.3.3 ST-GARCH (Smooth Transition GARCH) - **For FX/Currencies**
- **Asset Class:** EUR/USD, JPY, currency pairs
- **Use Case:** Regime transitions (Risk-On vs Risk-Off, Carry Trade regimes)
- **Feature:** Smooth transition function between low-vol and high-vol regimes
- **Why:** Currencies move in regimes. ST-GARCH uses a "dimmer switch" to glide between states without false alarms on small movements.
- **Example:** JPY transitioning from carry trade (low vol) to safe haven (high vol) regime.

#### 3.3.4 Standard GARCH(1,1) - **Fallback/Default**
- **Use Case:** General volatility clustering when asset class is unknown
- **Feature:** Symmetric response to positive/negative shocks
- **When:** Default for assets without clear classification or when other models fail to converge

### 3.4 Financial Applications

#### 3.4.1 Conditional VaR
```
VaRₜ(95%) = μₜ - 1.645 × σₜ

Where σₜ is GARCH forecast, not historical std dev
```

**Benefit:** VaR adjusts daily based on current volatility regime.

#### 3.4.2 Dynamic Risk Parity
```
wᵢ = (1/σᵢₜ) / Σ(1/σⱼₜ)

Where σᵢₜ is GARCH forecast for stock i
```

**Benefit:** Portfolio weights adjust as volatility forecasts change.

#### 3.4.3 Covariance Matrix Prediction

**Key Innovation:** Shift from "predicting returns" to "predicting the **Covariance Matrix**" for professional-grade portfolio construction.

```
Σₜ = Dₜ × R × Dₜ

Where:
- Dₜ = diagonal matrix of GARCH-predicted volatilities [σ₁ₜ, σ₂ₜ, ..., σₙₜ]
- R = correlation matrix (estimated from historical returns or DCC-GARCH)
- Σₜ = time-varying covariance matrix
```

**Application:**
- Portfolio variance: `σₚ² = w' × Σₜ × w`
- Enables volatility-adjusted weights via risk parity
- Dynamic correlation modeling (future: DCC-GARCH)

#### 3.4.4 Volatility Targeting (Risk Parity)

**Professional Approach:** Instead of mean-variance optimization (notoriously unstable), use **Volatility Targeting** with GARCH forecasts.

```
wᵢ = (1/σᵢₜ) / Σⱼ(1/σⱼₜ)

Where σᵢₜ is GARCH-predicted volatility for asset i
```

**Dynamic Behavior:**
- **If EGARCH predicts Tech volatility spike:** Denominator grows → Tech exposure automatically shrinks before crash
- **If ST-GARCH shows FX entering calm regime:** Denominator shrinks → Increase position to capture carry trade
- **Automatic rebalancing:** Weights adjust daily based on volatility forecasts

**Example:**
- Day 1: Tech vol = 20% → Weight = 5.0%
- Day 2: Tech vol spikes to 60% (EGARCH forecast) → Weight = 1.7% (automatic reduction)

#### 3.4.5 Walk-Forward Backtesting

**Critical:** Cannot use simple train-test split. Volatility has "memory" - must use **Rolling Window (Walk-Forward Validation)**.

**Process:**
1. **Window Setup:** Define lookback (e.g., 500 days)
2. **Estimation:** On Day T, estimate GARCH parameters (ω, α, β, γ) for chosen model
3. **One-Day Forecast:** Predict volatility σₜ₊₁ for tomorrow
4. **Innovation Check:** Use Skew-t distribution to check probability of 3-sigma tail event
5. **Step Forward:** Move window by one day, repeat

**Why Rolling Window:**
- Preserves volatility memory across time
- Avoids look-ahead bias
- Realistic simulation of live trading conditions

#### 3.4.6 Tail Risk Detection with Skew-t Distribution

**Problem:** Normal distribution underestimates tail risk (fat tails, skewness).

**Solution:** Use **Skew-t (ST) distribution** for accurate tail event probability.

```
P(|return| > 3σ) = F_skewt(3σ; ν, λ)

Where:
- ν = degrees of freedom (controls tail thickness)
- λ = skewness parameter
```

**Application:**
- If Skew-t shows high probability of 3-sigma move → Flag asset as "High Tail Risk"
- More accurate VaR/CVaR estimates
- Better Expected Shortfall (ES) calculations

#### 3.4.7 Volatility-Based Stress Testing
```
Stress Scenario: "Volatility Doubles"
σ_stressed = 2 × σ_GARCH_forecast
VaR_stressed = μ - z_skewt × σ_stressed

Where z_skewt is quantile from Skew-t distribution
```

**Benefit:** Stress tests adapt to current volatility regime with accurate tail risk.

---

## 4. Comparison & Benefits

### 4.1 Volatility Estimation: Current vs GARCH

| Aspect | Current (Historical Std Dev) | GARCH(1,1) |
|--------|----------------------------|------------|
| **Reaction Time** | Slow (requires many days in window) | Instant (reacts to single shock) |
| **Ghost Effects** | Yes (abrupt drop when crisis exits window) | No (smooth exponential decay) |
| **Volatility Clustering** | Not captured | Explicitly modeled |
| **Leverage Effects** | Not captured | Captured (EGARCH/GJR) |
| **Forward Forecast** | None (backward-looking only) | Yes (1-step, multi-step ahead) |
| **Crisis Response** | Underestimates risk | Realistic risk adjustment |
| **Calm Period Response** | Overestimates risk | Lower, more accurate risk |

### 4.2 VaR Calculation: Current vs GARCH

**Scenario: September 2008 (Lehman Collapse)**

| Day | Market Return | Current VaR(95%) | GARCH VaR(95%) | Difference |
|-----|---------------|------------------|----------------|------------|
| Sep 10 | +0.5% | -2.5% | -2.5% | Same |
| Sep 15 | -5.0% | -2.5% | -4.2% | **GARCH +68%** |
| Sep 16 | -2.0% | -2.5% | -3.8% | **GARCH +52%** |
| Sep 17 | +1.0% | -2.5% | -3.5% | **GARCH +40%** |
| Oct 1 | +0.2% | -2.5% | -3.0% | **GARCH +20%** |

**Key Insight:** GARCH VaR **immediately adjusts** after shock, while current method remains static.

### 4.3 Risk Parity: Current vs GARCH

**Scenario: Stock A volatility spikes from 20% to 60%**

| Approach | Weight Before | Weight After Spike | Adjustment |
|----------|---------------|-------------------|------------|
| **Current** | 5.0% | 5.0% (unchanged until rebalance) | None |
| **GARCH** | 5.0% | 1.7% (immediate adjustment) | **-66% reduction** |

**Benefit:** GARCH enables **dynamic risk control** without waiting for rebalance.

### 4.4 Quantitative Benefits

**Expected Improvements:**

1. **VaR Accuracy:**
   - Current: Underestimates risk by 30-50% during crises
   - GARCH: Accurate within 10-15% during crises

2. **Drawdown Control:**
   - Current: No dynamic response to volatility spikes
   - GARCH: 20-30% reduction in max drawdown through dynamic position sizing

3. **Sharpe Ratio:**
   - Current: Volatility overestimated in calm periods (lower Sharpe)
   - GARCH: More accurate volatility → better risk-adjusted returns

4. **Crisis Detection:**
   - Current: No early warning system
   - GARCH: Volatility forecasts spike 1-3 days before major drawdowns

### 4.5 Real-World Example: 2008 Financial Crisis

**From GARCH.md comparison:**

| Feature | Simple Moving Average (20-Day) | GARCH(1,1) |
|---------|-------------------------------|------------|
| **Reaction Time** | Slow - takes weeks to show high risk | **Instant** - reacts to -5% crash immediately |
| **Ghost Effect** | Yes - abrupt drop when crisis exits window | **No** - smooth exponential decay |
| **Risk Estimate** | Underestimates during first week | **Realistic** - recognizes volatility clustering |

**Conclusion:** GARCH would have **flagged elevated risk immediately** after Lehman collapse, while current method would have shown "normal" risk for weeks.

---

## 5. Technical Architecture

### 5.1 Module Structure

```
src/risk/
├── garch.py                    # NEW: GARCH model estimation and forecasting
│   ├── GARCHModel (base)
│   ├── EGARCHModel
│   ├── GJRGARCHModel
│   ├── STGARCHModel            # NEW: Smooth Transition GARCH
│   ├── GARCHForecaster
│   ├── ModelSelector           # NEW: Asset-class-specific model selection
│   ├── CovariancePredictor      # NEW: Covariance matrix from GARCH forecasts
│   └── VolatilityTargeting      # NEW: Volatility-adjusted weights
├── distributions.py            # NEW: Skew-t distribution for tail risk
├── metrics.py                  # MODIFY: Add conditional VaR/CVaR/ES with Skew-t
├── risk_parity.py              # MODIFY: Add dynamic volatility inputs
└── portfolio.py                # MODIFY: Add volatility-based stress tests
```

### 5.2 Core Classes

#### 5.2.1 GARCHModel (Base Class)

```python
class GARCHModel:
    """
    Base class for GARCH volatility models.
    """
    
    def __init__(
        self,
        model_type: str = "GARCH",  # "GARCH", "EGARCH", "GJR-GARCH"
        p: int = 1,                  # ARCH order
        q: int = 1,                  # GARCH order
        distribution: str = "normal"  # "normal", "t", "skewt"
    ):
        self.model_type = model_type
        self.p = p
        self.q = q
        self.distribution = distribution
        self.fitted = False
        self.params = None
        self.residuals = None
        self.conditional_vol = None
    
    def fit(self, returns: pd.Series) -> Dict[str, Any]:
        """
        Estimate GARCH parameters using maximum likelihood.
        
        Returns:
            Dict with parameters, log-likelihood, AIC, BIC
        """
        pass
    
    def forecast(
        self,
        horizon: int = 1,
        start: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """
        Forecast conditional volatility.
        
        Args:
            horizon: Number of steps ahead (1 = next day)
            start: Starting point for forecast (default: last observation)
        
        Returns:
            Series of volatility forecasts
        """
        pass
    
    def get_conditional_volatility(self) -> pd.Series:
        """Get in-sample conditional volatility."""
        pass
```

#### 5.2.2 GARCHForecaster

```python
class GARCHForecaster:
    """
    High-level interface for GARCH volatility forecasting.
    Handles multiple stocks, model selection, and caching.
    """
    
    def __init__(
        self,
        default_model: str = "GARCH",
        min_observations: int = 252,  # 1 year minimum
        refit_frequency: str = "monthly"  # How often to re-estimate
    ):
        self.default_model = default_model
        self.min_observations = min_observations
        self.refit_frequency = refit_frequency
        self.models: Dict[str, GARCHModel] = {}
        self.last_fit_date: Dict[str, pd.Timestamp] = {}
    
    def fit_stock(
        self,
        ticker: str,
        returns: pd.Series,
        model_type: Optional[str] = None
    ) -> GARCHModel:
        """
        Fit GARCH model for a single stock.
        
        Returns:
            Fitted GARCHModel instance
        """
        pass
    
    def forecast_stock(
        self,
        ticker: str,
        horizon: int = 1
    ) -> float:
        """
        Get volatility forecast for a stock.
        
        Returns:
            Annualized volatility forecast
        """
        pass
    
    def forecast_portfolio(
        self,
        tickers: List[str],
        weights: Dict[str, float],
        returns_df: pd.DataFrame,
        correlation_matrix: Optional[pd.DataFrame] = None
    ) -> float:
        """
        Forecast portfolio volatility using GARCH forecasts.
        
        Uses: σₚ² = Σᵢ Σⱼ wᵢ wⱼ σᵢ σⱼ ρᵢⱼ
        """
        pass
```

#### 5.2.3 ModelSelector

```python
class ModelSelector:
    """
    Asset-class-specific GARCH model selection.
    Assigns the right model to the right asset class for optimal performance.
    """
    
    # Asset class mappings
    EQUITY_SECTORS = ['Technology', 'Semiconductors', 'Financials', 'Healthcare']
    COMMODITY_SECTORS = ['Energy', 'Materials', 'Agriculture']
    FX_ASSETS = ['EUR', 'JPY', 'GBP', 'USD']  # Currency pairs
    
    @classmethod
    def select_model(
        cls,
        ticker: str,
        sector: Optional[str] = None,
        asset_type: Optional[str] = None
    ) -> str:
        """
        Select appropriate GARCH model based on asset class.
        
        Returns:
            "EGARCH" for equities
            "GJR-GARCH" for commodities
            "ST-GARCH" for FX
            "GARCH" as fallback
        """
        # Check asset type first
        if asset_type == "FX" or any(fx in ticker.upper() for fx in cls.FX_ASSETS):
            return "ST-GARCH"
        
        # Check sector
        if sector in cls.COMMODITY_SECTORS:
            return "GJR-GARCH"
        elif sector in cls.EQUITY_SECTORS:
            return "EGARCH"
        
        # Default to EGARCH for equities (most common)
        return "EGARCH"
    
    @classmethod
    def select_best_model(
        cls,
        ticker: str,
        returns: pd.Series,
        sector: Optional[str] = None
    ) -> Tuple[str, float]:
        """
        Try multiple models, select best by AIC.
        
        Returns:
            (best_model_type, aic_score)
        """
        candidates = ["EGARCH", "GJR-GARCH", "GARCH"]
        if sector in cls.COMMODITY_SECTORS:
            candidates = ["GJR-GARCH", "GARCH", "EGARCH"]
        
        best_model = None
        best_aic = float('inf')
        
        for model_type in candidates:
            try:
                model = GARCHModel(model_type=model_type)
                result = model.fit(returns)
                if result['aic'] < best_aic:
                    best_aic = result['aic']
                    best_model = model_type
            except:
                continue
        
        return best_model or "GARCH", best_aic
```

#### 5.2.4 CovariancePredictor

```python
class CovariancePredictor:
    """
    Predict time-varying covariance matrix from GARCH volatility forecasts.
    """
    
    def __init__(
        self,
        garch_forecaster: GARCHForecaster,
        correlation_method: str = "historical"  # "historical", "dcc" (future)
    ):
        self.garch_forecaster = garch_forecaster
        self.correlation_method = correlation_method
    
    def predict_covariance(
        self,
        tickers: List[str],
        returns_df: pd.DataFrame,
        date: Optional[pd.Timestamp] = None
    ) -> pd.DataFrame:
        """
        Predict covariance matrix Σₜ = Dₜ × R × Dₜ
        
        Where:
        - Dₜ = diagonal matrix of GARCH-predicted volatilities
        - R = correlation matrix
        
        Returns:
            DataFrame with covariance matrix (tickers × tickers)
        """
        # Get GARCH volatility forecasts
        vols = {}
        for ticker in tickers:
            vol = self.garch_forecaster.forecast_stock(ticker, horizon=1)
            vols[ticker] = vol
        
        # Build diagonal matrix D
        D = pd.DataFrame(np.diag(list(vols.values())), 
                        index=tickers, columns=tickers)
        
        # Get correlation matrix R
        if self.correlation_method == "historical":
            R = returns_df[tickers].corr()
        else:
            # Future: DCC-GARCH for time-varying correlations
            R = returns_df[tickers].corr()
        
        # Covariance matrix: Σ = D × R × D
        cov_matrix = D @ R @ D
        
        return cov_matrix
    
    def predict_portfolio_variance(
        self,
        tickers: List[str],
        weights: Dict[str, float],
        returns_df: pd.DataFrame
    ) -> float:
        """
        Predict portfolio variance: σₚ² = w' × Σ × w
        """
        cov_matrix = self.predict_covariance(tickers, returns_df)
        w = pd.Series([weights.get(t, 0) for t in tickers], index=tickers)
        portfolio_var = (w @ cov_matrix @ w).iloc[0]
        return float(portfolio_var)
```

#### 5.2.5 VolatilityTargeting

```python
class VolatilityTargeting:
    """
    Volatility-adjusted portfolio weights using GARCH forecasts.
    Implements risk parity with dynamic volatility targeting.
    """
    
    def __init__(
        self,
        garch_forecaster: GARCHForecaster,
        target_volatility: float = 0.15  # 15% annual target
    ):
        self.garch_forecaster = garch_forecaster
        self.target_vol = target_volatility
    
    def calculate_weights(
        self,
        tickers: List[str],
        returns_df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Calculate volatility-targeted weights: wᵢ = (1/σᵢ) / Σ(1/σⱼ)
        
        Automatically reduces exposure when volatility spikes.
        """
        # Get GARCH volatility forecasts
        inv_vols = {}
        for ticker in tickers:
            vol = self.garch_forecaster.forecast_stock(ticker, horizon=1)
            if vol > 0.01:  # Avoid division by zero
                inv_vols[ticker] = 1.0 / vol
            else:
                inv_vols[ticker] = 1.0 / 0.30  # Default 30% vol
        
        # Normalize to sum to 1
        total = sum(inv_vols.values())
        weights = {t: iv / total for t, iv in inv_vols.items()}
        
        return weights
    
    def calculate_targeted_weights(
        self,
        tickers: List[str],
        returns_df: pd.DataFrame,
        target_portfolio_vol: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate weights targeting specific portfolio volatility.
        
        Uses: wᵢ = (target_vol / σᵢ) / Σ(target_vol / σⱼ)
        """
        target = target_portfolio_vol or self.target_vol
        
        # Get base volatility-targeted weights
        base_weights = self.calculate_weights(tickers, returns_df)
        
        # Scale to target volatility
        # (Simplified - full implementation would use covariance matrix)
        return base_weights
```

#### 5.2.6 SkewTDistribution

```python
class SkewTDistribution:
    """
    Skew-t distribution for accurate tail risk estimation.
    """
    
    def __init__(self, nu: float = 5.0, lambda_param: float = 0.0):
        """
        Args:
            nu: Degrees of freedom (controls tail thickness)
            lambda_param: Skewness parameter
        """
        self.nu = nu
        self.lambda_param = lambda_param
    
    def fit(self, returns: pd.Series) -> Dict[str, float]:
        """
        Fit Skew-t distribution to returns.
        
        Returns:
            Dict with nu, lambda, location, scale parameters
        """
        # Use scipy.stats or custom MLE estimation
        pass
    
    def tail_probability(
        self,
        threshold: float,
        vol: float
    ) -> float:
        """
        Calculate probability of exceeding threshold (e.g., 3-sigma move).
        
        Returns:
            P(|return| > threshold)
        """
        pass
    
    def var_skewt(
        self,
        confidence_level: float = 0.95,
        vol: float = 1.0
    ) -> float:
        """
        Calculate VaR using Skew-t distribution.
        
        More accurate than normal distribution for tail risk.
        """
        pass
```

### 5.3 Integration with Existing Modules

#### 5.3.1 RiskMetrics Enhancement

**File:** `src/risk/metrics.py`

**Changes:**
```python
class RiskMetrics:
    def __init__(self, use_garch: bool = False, garch_forecaster: Optional[GARCHForecaster] = None):
        self.use_garch = use_garch
        self.garch_forecaster = garch_forecaster
    
    def calculate_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        method: str = "historical",
        use_garch: Optional[bool] = None  # Override instance setting
    ) -> float:
        """
        Calculate VaR with optional GARCH conditional volatility.
        
        If use_garch=True:
        - Fits GARCH model to returns
        - Gets 1-step ahead volatility forecast
        - Calculates: VaR = μ - z × σ_GARCH
        
        Otherwise: Uses existing historical/parametric methods
        """
        use_garch = use_garch if use_garch is not None else self.use_garch
        
        if use_garch and self.garch_forecaster:
            # Get GARCH volatility forecast
            vol_forecast = self.garch_forecaster.forecast_stock(
                ticker="portfolio",  # Or use returns directly
                horizon=1
            )
            mean_return = returns.mean()
            z_score = stats.norm.ppf(1 - confidence_level)
            var = mean_return - (z_score * vol_forecast / np.sqrt(252))
            return float(var)
        else:
            # Existing implementation
            ...
```

#### 5.3.2 RiskParityAllocator Enhancement

**File:** `src/risk/risk_parity.py`

**Changes:**
```python
class RiskParityAllocator:
    def __init__(
        self,
        capital: float = 100_000,
        target_portfolio_vol: float = 0.15,
        use_garch: bool = False,  # NEW
        garch_forecaster: Optional[GARCHForecaster] = None,  # NEW
        ...
    ):
        self.use_garch = use_garch
        self.garch_forecaster = garch_forecaster
        ...
    
    def calculate_stock_volatilities(
        self,
        returns_df: pd.DataFrame,
        annualize: bool = True,
        use_garch: Optional[bool] = None  # NEW
    ) -> Dict[str, float]:
        """
        Calculate volatilities with optional GARCH forecasts.
        
        If use_garch=True:
        - Fits GARCH model for each stock
        - Returns 1-step ahead volatility forecasts
        
        Otherwise: Uses historical std dev (existing method)
        """
        use_garch = use_garch if use_garch is not None else self.use_garch
        
        if use_garch and self.garch_forecaster:
            vols = {}
            for ticker in returns_df.columns:
                returns = returns_df[ticker].dropna()
                if len(returns) >= self.garch_forecaster.min_observations:
                    # Fit GARCH if not already fitted
                    if ticker not in self.garch_forecaster.models:
                        self.garch_forecaster.fit_stock(ticker, returns)
                    
                    # Get forecast
                    vol_daily = self.garch_forecaster.forecast_stock(ticker, horizon=1)
                    vols[ticker] = vol_daily * np.sqrt(252) if annualize else vol_daily
                else:
                    # Fallback to historical
                    vol = returns.std() * (np.sqrt(252) if annualize else 1.0)
                    vols[ticker] = vol
            return vols
        else:
            # Existing implementation
            ...
```

### 5.4 Configuration

**File:** `config/config.yaml`

**New Section:**
```yaml
risk:
  volatility:
    method: "garch"  # "historical" or "garch"
    garch_model: "GARCH"  # "GARCH", "EGARCH", "GJR-GARCH"
    min_observations: 252  # Minimum days for GARCH estimation
    refit_frequency: "monthly"  # "daily", "weekly", "monthly"
    
  var:
    use_conditional: true  # Use GARCH for VaR if method=garch
    confidence_levels: [0.95, 0.99]
    
  risk_parity:
    use_garch_vol: true  # Use GARCH forecasts for risk parity
    dynamic_rebalance: false  # Rebalance when vol changes (future)
```

### 5.5 Dependencies

**New Requirements:**
```txt
arch>=6.0.0  # GARCH model estimation (Kevin Sheppard's arch package)
```

**Why `arch` package:**
- Industry-standard GARCH implementation
- Supports GARCH, EGARCH, GJR-GARCH, and many variants
- Well-tested, maintained, and documented
- Efficient Cython backend

---

## 6. Implementation Phases

### Phase 1: Core GARCH Infrastructure (Weeks 1-2)

**Goal:** Basic GARCH model estimation and forecasting

**Tasks:**
1. Create `src/risk/garch.py` module
2. Implement `GARCHModel` base class with `arch` package
3. Implement `GARCHForecaster` for multi-stock management
4. Add unit tests for GARCH estimation
5. Add configuration options

**Deliverables:**
- `GARCHModel` class with fit/forecast methods
- `GARCHForecaster` class for portfolio-level forecasting
- Unit tests with synthetic data
- Configuration integration

**Success Criteria:**
- Can fit GARCH(1,1) to stock returns
- Can forecast 1-step ahead volatility
- Tests pass with known GARCH parameters

### Phase 2: Conditional VaR/CVaR (Weeks 3-4)

**Goal:** Integrate GARCH into VaR/CVaR calculations

**Tasks:**
1. Modify `RiskMetrics.calculate_var()` to support GARCH
2. Modify `RiskMetrics.calculate_cvar()` to support GARCH
3. Add `conditional_var()` method that uses GARCH forecasts
4. Update comprehensive risk analysis scripts
5. Add comparison tests (GARCH VaR vs historical VaR)

**Deliverables:**
- Conditional VaR using GARCH volatility
- Conditional CVaR using GARCH volatility
- Updated risk analysis reports showing both methods
- Backtest comparison showing GARCH VaR accuracy

**Success Criteria:**
- GARCH VaR adjusts immediately after volatility shocks
- GARCH VaR more accurate than historical during crises
- Backward compatible (can still use historical method)

### Phase 3: Dynamic Risk Parity (Weeks 5-6)

**Goal:** Use GARCH forecasts for risk parity allocation

**Tasks:**
1. Modify `RiskParityAllocator.calculate_stock_volatilities()` to support GARCH
2. Add `dynamic_risk_parity_weights()` method
3. Update portfolio construction to use GARCH volatilities
4. Add volatility-based rebalancing triggers (optional)
5. Update risk-aware analysis scripts

**Deliverables:**
- Risk parity allocation using GARCH volatility forecasts
- Dynamic weight adjustment based on volatility changes
- Updated portfolio construction reports
- Performance comparison (GARCH risk parity vs historical)

**Success Criteria:**
- Portfolio weights adjust when volatility spikes
- Lower portfolio volatility during crises
- Improved Sharpe ratio vs static risk parity

### Phase 4: Advanced Features (Weeks 7-8)

**Goal:** Asset-class-specific models, covariance matrix prediction, volatility targeting, and Skew-t distribution

**Tasks:**
1. Implement `EGARCHModel` for equities (leverage effects)
2. Implement `GJRGARCHModel` for commodities (threshold effects)
3. Implement `STGARCHModel` for FX/currencies (smooth transitions)
4. Implement `ModelSelector` for asset-class-specific selection
5. Implement `CovariancePredictor` for covariance matrix from GARCH forecasts
6. Implement `VolatilityTargeting` for volatility-adjusted weights
7. Implement `SkewTDistribution` for accurate tail risk
8. Add volatility-based stress scenarios
9. Update stress testing scripts

**Deliverables:**
- EGARCH, GJR-GARCH, and ST-GARCH models
- Automatic model selection based on asset class
- Covariance matrix prediction from GARCH forecasts
- Volatility targeting / risk parity with dynamic weights
- Skew-t distribution for tail risk estimation
- Volatility-based stress scenarios
- Enhanced stress testing reports

**Success Criteria:**
- EGARCH captures leverage effects (negative returns → higher vol) for equities
- GJR-GARCH detects volatility spikes after crashes for commodities
- ST-GARCH identifies regime transitions for FX
- Model selector assigns correct model to asset class
- Covariance matrix enables portfolio-level risk estimation
- Volatility targeting automatically reduces exposure when vol spikes
- Skew-t provides accurate tail risk probabilities
- Stress tests adapt to current volatility regime

### Phase 5: Documentation & Validation (Week 9)

**Goal:** Complete documentation and validate improvements

**Tasks:**
1. Update `docs/risk-management.md` with GARCH section
2. Create `docs/garch-implementation.md` guide
3. Run comprehensive backtests comparing GARCH vs historical
4. Generate validation report
5. Update user guide with GARCH usage examples

**Deliverables:**
- Complete documentation
- Validation report showing GARCH benefits
- User guide with examples
- Performance benchmarks

**Success Criteria:**
- Documentation complete and accurate
- Validation shows clear benefits
- Users can easily enable/configure GARCH

---

## 7. Integration Points

### 7.1 Backtesting Integration (Walk-Forward Validation)

**File:** `src/backtest/rolling.py`

**Critical:** Cannot use simple train-test split. Volatility has "memory" - must use **Rolling Window (Walk-Forward Validation)**.

**Changes:**
- Implement rolling window estimation (e.g., 500-day lookback)
- At each day T, estimate GARCH parameters using only past data
- Forecast one-day-ahead volatility σₜ₊₁
- Use Skew-t distribution for tail risk checks
- Step forward one day and repeat

**Example:**
```python
def run_walk_forward_backtest(
    returns_df: pd.DataFrame,
    lookback_window: int = 500,
    ...
):
    """
    Walk-forward backtest with GARCH volatility forecasting.
    
    Process:
    1. Window Setup: Define lookback (e.g., 500 days)
    2. Estimation: On Day T, estimate GARCH parameters (ω, α, β, γ)
    3. One-Day Forecast: Predict volatility σₜ₊₁ for tomorrow
    4. Innovation Check: Use Skew-t to check probability of 3-sigma tail event
    5. Step Forward: Move window by one day, repeat
    """
    from src.risk.garch import GARCHForecaster, ModelSelector
    from src.risk.distributions import SkewTDistribution
    
    garch_forecaster = GARCHForecaster()
    skewt = SkewTDistribution()
    model_selector = ModelSelector()
    
    results = []
    
    # Rolling window: start from lookback_window
    for t in range(lookback_window, len(returns_df)):
        # Get training window (past 500 days)
        train_returns = returns_df.iloc[t-lookback_window:t]
        test_date = returns_df.index[t]
        
        # For each ticker, fit appropriate GARCH model
        for ticker in train_returns.columns:
            returns = train_returns[ticker].dropna()
            
            # Select model based on asset class
            sector = get_sector(ticker)  # From sector mapping
            model_type = model_selector.select_model(ticker, sector)
            
            # Fit GARCH model (only using past data)
            garch_forecaster.fit_stock(
                ticker=ticker,
                returns=returns,
                model_type=model_type
            )
        
        # Forecast volatility for tomorrow (one-day ahead)
        vols = {}
        for ticker in train_returns.columns:
            vol_forecast = garch_forecaster.forecast_stock(ticker, horizon=1)
            vols[ticker] = vol_forecast
        
        # Innovation Check: Use Skew-t for tail risk
        tail_risks = {}
        for ticker in train_returns.columns:
            returns = train_returns[ticker].dropna()
            skewt.fit(returns)
            prob_3sigma = skewt.tail_probability(3 * vols[ticker], vols[ticker])
            tail_risks[ticker] = prob_3sigma
        
        # Use GARCH vols for volatility targeting
        vol_targeting = VolatilityTargeting(garch_forecaster)
        weights = vol_targeting.calculate_weights(
            tickers=list(train_returns.columns),
            returns_df=train_returns
        )
        
        # Calculate portfolio metrics
        portfolio_return = calculate_portfolio_return(weights, test_date)
        
        results.append({
            'date': test_date,
            'vols': vols,
            'weights': weights,
            'tail_risks': tail_risks,
            'portfolio_return': portfolio_return
        })
    
    return results
```

**Key Points:**
- **No look-ahead bias:** Only uses past data for estimation
- **Preserves memory:** Rolling window maintains volatility clustering
- **One-day forecasts:** Realistic simulation of live trading
- **Tail risk checks:** Skew-t flags high-risk assets before crashes

### 7.2 Comprehensive Risk Analysis Integration

**File:** `scripts/comprehensive_risk_analysis.py`

**Changes:**
- Add GARCH-based tail risk analysis
- Compare GARCH VaR vs historical VaR
- Show volatility regime classification (calm vs crisis)

**New Output:**
```json
{
  "tail_risk": {
    "var_95_historical": -0.025,
    "var_95_garch": -0.032,
    "volatility_regime": "crisis",
    "garch_forecast_1d": 0.28,
    "garch_forecast_5d": 0.25
  }
}
```

### 7.3 Portfolio Optimizer Integration

**File:** `src/analysis/portfolio_optimizer.py`

**Changes:**
- Use GARCH volatility forecasts in `calculate_portfolio_metrics()`
- Add GARCH-based risk constraints
- Show GARCH vs historical volatility comparison

### 7.4 Dashboard Integration

**File:** `src/app/dashboard/pages/`

**Changes:**
- Add "Volatility Forecast" tab showing GARCH forecasts
- Add "GARCH vs Historical" comparison chart
- Show volatility regime indicator (calm/crisis)

---

## 8. Configuration & Usage

### 8.1 Basic Usage

**Enable GARCH in config:**
```yaml
risk:
  volatility:
    method: "garch"
    garch_model: "GARCH"
```

**Use in code:**
```python
from src.risk.garch import GARCHForecaster
from src.risk.risk_parity import RiskParityAllocator

# Initialize GARCH forecaster
garch = GARCHForecaster(default_model="GARCH")

# Fit models for stocks
for ticker in tickers:
    garch.fit_stock(ticker, returns_df[ticker])

# Get volatility forecasts
vols = {}
for ticker in tickers:
    vols[ticker] = garch.forecast_stock(ticker, horizon=1) * np.sqrt(252)

# Use in risk parity
allocator = RiskParityAllocator(use_garch=True, garch_forecaster=garch)
weights = allocator.inverse_volatility_weights(vols, tickers)
```

### 8.2 Advanced Usage

**Model Selection:**
```python
# Try multiple models, select best by AIC
garch = GARCHForecaster()

for model_type in ["GARCH", "EGARCH", "GJR-GARCH"]:
    model = garch.fit_stock(ticker, returns, model_type=model_type)
    aic = model.aic
    # Select model with lowest AIC
```

**Conditional VaR:**
```python
from src.risk.metrics import RiskMetrics

metrics = RiskMetrics(use_garch=True, garch_forecaster=garch)

# Historical VaR
var_historical = metrics.calculate_var(returns, method="historical")

# GARCH conditional VaR
var_garch = metrics.calculate_var(returns, method="garch")
```

### 8.3 CLI Integration

**New command:**
```bash
# Fit GARCH models for all stocks
python scripts/fit_garch_models.py --watchlist jan_26

# Forecast volatility
python scripts/forecast_volatility.py --tickers AAPL MSFT --horizon 5

# Compare GARCH vs historical VaR
python scripts/compare_var_methods.py --run-id run_xxx
```

---

## 9. Testing & Validation

### 9.1 Unit Tests

**File:** `tests/test_garch.py`

**Test Cases:**
1. GARCH model estimation with known parameters
2. Volatility forecasting accuracy
3. Model selection (AIC/BIC)
4. EGARCH leverage effect detection
5. GJR-GARCH threshold detection

**Example:**
```python
def test_garch_estimation():
    # Generate synthetic GARCH data
    np.random.seed(42)
    garch_params = {"omega": 0.01, "alpha": 0.1, "beta": 0.85}
    returns = simulate_garch(1000, garch_params)
    
    # Fit GARCH model
    model = GARCHModel()
    result = model.fit(returns)
    
    # Check parameter estimates are close to true values
    assert abs(result.params["alpha"] - 0.1) < 0.05
    assert abs(result.params["beta"] - 0.85) < 0.05
```

### 9.2 Integration Tests

**Test Cases:**
1. GARCH VaR vs historical VaR during crisis
2. Dynamic risk parity weight adjustment
3. Portfolio volatility forecast accuracy
4. Stress testing with GARCH volatility

### 9.3 Validation Study

**Methodology:**
1. Select 3-5 historical crisis periods (2008, 2020, 2022)
2. Run walk-forward backtest with GARCH vs historical methods
3. For each period:
   - Calculate VaR using historical method
   - Calculate VaR using GARCH-Skew-t
   - Compare to actual realized losses
4. Measure key metrics:

**Primary Metrics (Professional-Grade):**

1. **VaR Breaches:**
   - Count how many times actual loss exceeded GARCH-Skew-t VaR prediction
   - Target: < 1% breach rate (e.g., 95% VaR should be breached ~5% of time)
   - Formula: `breach_rate = (# days loss > VaR) / total_days`

2. **Sortino Ratio (More Important Than Sharpe):**
   - Since using asymmetric models (EGARCH/GJR), Sortino measures return relative to **downside volatility only**
   - Formula: `Sortino = (Return - RiskFree) / DownsideStdDev`
   - Target: Sortino > 1.5 for good performance

3. **Expected Shortfall (ES) / CVaR:**
   - Expected loss given VaR is breached
   - More informative than VaR for tail risk
   - Formula: `ES = E[Loss | Loss > VaR]`
   - Compare GARCH-Skew-t ES vs historical ES

4. **Early Warning:**
   - How many days before crisis did GARCH volatility spike?
   - Measure: Days between GARCH vol spike and major drawdown

**Expected Results:**
- **VaR Breaches:** GARCH-Skew-t breach rate within 1% of target (e.g., 4-6% for 95% VaR)
- **Sortino Ratio:** GARCH-based portfolios show 0.2-0.5 point improvement
- **Expected Shortfall:** GARCH-Skew-t ES more accurate (within 10-15% vs 30-50% error)
- **Early Warning:** GARCH provides 1-3 day early warning before major drawdowns
- **Drawdown Reduction:** GARCH risk parity reduces max drawdown by 20-30%

### 9.4 Performance Benchmarks

**Measure:**
1. GARCH model fitting time (should be <1 second per stock)
2. Forecast generation time (should be <0.1 seconds)
3. Memory usage (should be <100MB for 100 stocks)

**Targets:**
- Fit 100 stocks: <2 minutes
- Forecast 100 stocks: <5 seconds
- Memory: <200MB total

---

## 10. Future Enhancements

### 10.1 Phase 2 Features (Post-MVP)

**MS-GARCH (Markov Switching):**
- Detect regime switches (bull/bear, calm/crisis)
- Different GARCH parameters for each regime
- Regime probability forecasts

**RealGARCH:**
- Use intraday data (if available)
- More accurate daily volatility forecasts
- Better for high-frequency strategies

**Multivariate GARCH:**
- Model correlation dynamics (DCC-GARCH)
- Portfolio-level volatility with time-varying correlations
- More accurate portfolio risk estimates

### 10.2 Hybrid AI Models

**GARCH + LSTM:**
- LSTM for non-linear pattern detection
- GARCH for volatility structure
- Combine for enhanced forecasts

**GARCH + Sentiment:**
- Use sentiment scores as GARCH inputs
- Model how news affects volatility
- Early warning system for volatility spikes

### 10.3 Advanced Applications

**Option Pricing:**
- Use GARCH volatility for option valuation
- More accurate than Black-Scholes
- Support for derivatives strategies

**Dynamic Hedging:**
- Adjust hedge ratios based on GARCH volatility
- Delta-hedging with time-varying vol
- Volatility trading strategies

---

## 11. Risks & Mitigation

### 11.1 Model Risk

**Risk:** GARCH parameters may be unstable or overfit

**Mitigation:**
- Use robust estimation (robust standard errors)
- Regular refitting (monthly, not daily)
- Model diagnostics (Ljung-Box test for residuals)
- Fallback to historical if GARCH fails

### 11.2 Computational Cost

**Risk:** GARCH fitting may be slow for large universes

**Mitigation:**
- Cache fitted models (refit monthly, not daily)
- Parallel processing for multi-stock fitting
- Use fast optimization algorithms (BFGS)
- Limit to top N stocks (not entire universe)

### 11.3 Data Requirements

**Risk:** GARCH requires sufficient history (minimum 252 days)

**Mitigation:**
- Fallback to historical vol for new stocks
- Use sector/industry average GARCH for stocks with insufficient data
- Clearly document minimum data requirements

### 11.4 Backward Compatibility

**Risk:** Breaking changes to existing risk metrics

**Mitigation:**
- Make GARCH optional (default: historical)
- Preserve all existing methods
- Add new methods, don't replace old ones
- Comprehensive testing of both paths

---

## 12. Success Metrics

### 12.1 Technical Metrics

- ✅ GARCH models fit successfully for 95%+ of stocks
- ✅ Model selector assigns correct model to asset class (EGARCH→equities, GJR→commodities, ST→FX)
- ✅ VaR accuracy improves by 20%+ during crises
- ✅ Volatility forecasts within 15% of realized volatility
- ✅ Covariance matrix prediction enables portfolio-level risk estimation
- ✅ Computational performance: <2 min for 100 stocks

### 12.2 Professional-Grade Risk Metrics

**Primary Metrics (2026 Standard):**

- ✅ **VaR Breaches:** GARCH-Skew-t breach rate within 1% of target (e.g., 4-6% for 95% VaR)
  - Historical method: Often 8-12% breach rate (underestimates risk)
  - GARCH-Skew-t: 4-6% breach rate (accurate)

- ✅ **Sortino Ratio:** Improvement of 0.2-0.5 points vs historical method
  - More important than Sharpe for asymmetric models
  - Measures return relative to downside volatility only

- ✅ **Expected Shortfall (ES):** GARCH-Skew-t ES within 10-15% of actual losses
  - Historical ES: Often 30-50% error during crises
  - More informative than VaR for tail risk

- ✅ **Early Warning:** 1-3 days before major drawdowns
  - GARCH volatility spikes before crashes
  - Enables proactive risk management

### 12.3 Business Metrics

- ✅ Max drawdown reduction: 20-30% vs static risk parity
- ✅ Sharpe ratio improvement: 0.1-0.2 points (secondary to Sortino)
- ✅ Volatility targeting automatically reduces exposure during spikes
- ✅ User adoption: 50%+ of users enable GARCH within 3 months

---

## 13. Appendix

### 13.1 GARCH Model Equations

**Standard GARCH(1,1):**
```
σ²ₜ = ω + α·ε²ₜ₋₁ + β·σ²ₜ₋₁
```

**EGARCH(1,1) - For Equities:**
```
log(σ²ₜ) = ω + α·(|εₜ₋₁| - E|εₜ₋₁|) + γ·εₜ₋₁ + β·log(σ²ₜ₋₁)
```
Where γ captures leverage effect (negative returns → higher vol)

**GJR-GARCH(1,1) - For Commodities:**
```
σ²ₜ = ω + α·ε²ₜ₋₁ + γ·I(εₜ₋₁<0)·ε²ₜ₋₁ + β·σ²ₜ₋₁
```
Where I(εₜ₋₁<0) is indicator function (1 if negative return, 0 otherwise)

**ST-GARCH(1,1) - For FX/Currencies:**
```
σ²ₜ = σ²₀ + (σ²₁ - σ²₀) × G(zₜ₋₁; γ, c)

Where:
- σ²₀ = low-volatility regime variance
- σ²₁ = high-volatility regime variance
- G(zₜ₋₁; γ, c) = smooth transition function
- zₜ₋₁ = transition variable (e.g., lagged return)
- γ = smoothness parameter
- c = threshold parameter
```

**Covariance Matrix Prediction:**
```
Σₜ = Dₜ × R × Dₜ

Where:
- Dₜ = diag(σ₁ₜ, σ₂ₜ, ..., σₙₜ)  (GARCH-predicted volatilities)
- R = correlation matrix (historical or DCC-GARCH)
- Σₜ = time-varying covariance matrix
```

**Volatility Targeting:**
```
wᵢ = (1/σᵢₜ) / Σⱼ(1/σⱼₜ)

Where σᵢₜ is GARCH forecast for asset i
```

### 13.2 Key References

- Bollerslev (1986): "Generalized Autoregressive Conditional Heteroskedasticity"
- Engle (2001): "GARCH 101: The Use of ARCH/GARCH Models in Applied Econometrics"
- Sheppard (2024): `arch` package documentation
- [GARCH.md](../GARCH.md): Internal reference document

### 13.3 Glossary

- **ARCH:** Autoregressive Conditional Heteroskedasticity
- **GARCH:** Generalized ARCH
- **EGARCH:** Exponential GARCH - captures leverage effects in equities
- **GJR-GARCH:** Glosten-Jagannathan-Runkle GARCH - threshold model for commodities
- **ST-GARCH:** Smooth Transition GARCH - regime-switching model for FX/currencies
- **Conditional Volatility:** Time-varying volatility that depends on past shocks
- **Volatility Clustering:** Tendency for high volatility periods to cluster together
- **Leverage Effect:** Asymmetric response where negative returns cause more volatility than positive returns
- **Covariance Matrix:** Time-varying matrix of asset covariances, predicted from GARCH forecasts
- **Volatility Targeting:** Portfolio construction method using inverse volatility weights
- **Walk-Forward Validation:** Rolling window backtesting that preserves volatility memory
- **Skew-t Distribution:** Distribution with fat tails and skewness for accurate tail risk
- **VaR:** Value at Risk - maximum expected loss at confidence level
- **CVaR/ES:** Conditional VaR / Expected Shortfall - expected loss given VaR is exceeded
- **Sortino Ratio:** Return divided by downside volatility (more important than Sharpe for asymmetric models)
- **VaR Breach:** When actual loss exceeds predicted VaR (target: <1% deviation from expected rate)

---

## Document Status

- **Version:** 2.0
- **Last Updated:** January 2026
- **Status:** Ready for Review (Updated with Professional-Grade Approach)
- **Key Updates:**
  - Asset-class-specific model selection (EGARCH/GJR-GARCH/ST-GARCH)
  - Covariance matrix prediction for portfolio-level risk
  - Volatility targeting with dynamic weights
  - Walk-forward validation for backtesting
  - Skew-t distribution for tail risk
  - Focus on Sortino ratio and Expected Shortfall
- **Next Steps:** 
  1. Review and approval
  2. Begin Phase 1 implementation
  3. Set up development environment with `arch` package
  4. Implement model selector for asset-class assignment

---

## See Also

- [Risk metrics](risk-management.md)
- [Advanced risk analysis](risk-analysis-guide.md)
- [Backtesting framework](backtesting.md)
- [Model training](model-training.md)
