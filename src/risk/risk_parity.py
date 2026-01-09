"""
Risk-Aware Portfolio Construction
=================================
Implements volatility-aware position sizing, risk parity, 
beta-adjusted allocation, and sector constraints.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskAwarePosition:
    """Position with risk-aware sizing information."""
    ticker: str
    raw_weight: float          # Original score-based weight
    risk_weight: float         # Risk-adjusted weight
    vol_contribution: float    # Contribution to portfolio volatility
    beta: float               # Beta vs benchmark
    sector: str
    volatility: float         # Individual volatility
    score: float              # Original model score
    shares: int = 0
    position_value: float = 0.0


@dataclass
class PortfolioRiskProfile:
    """Complete portfolio risk analysis."""
    total_beta: float
    weighted_avg_vol: float
    portfolio_vol_estimate: float
    sector_exposure: Dict[str, float]
    beta_exposure: Dict[str, float]  # Low/Medium/High beta breakdown
    concentration_hhi: float         # Herfindahl index
    effective_n: float              # Effective number of positions
    risk_tilt: str                  # "High Beta", "Balanced", "Defensive"
    warnings: List[str] = field(default_factory=list)


@dataclass 
class SectorConstraints:
    """Sector weight constraints."""
    max_weights: Dict[str, float] = field(default_factory=dict)  # Sector -> max weight
    min_weights: Dict[str, float] = field(default_factory=dict)  # Sector -> min weight
    
    def __post_init__(self):
        # Default max constraints for high-volatility sectors
        if not self.max_weights:
            self.max_weights = {
                'Nuclear': 0.15,           # Cap nuclear at 15%
                'Semiconductors': 0.20,    # Cap semis at 20%
                'Technology': 0.30,        # Cap tech at 30%
                'Energy': 0.15,            # Cap energy at 15%
                'Utilities': 0.20,         # Cap utilities at 20%
            }


class RiskParityAllocator:
    """
    Risk-Parity and Volatility-Aware Position Sizing.
    
    Methods:
    - Inverse Volatility: 1/σ weighting
    - Risk Parity: Equal risk contribution
    - Vol-Capped: Max volatility contribution per position
    - Beta-Adjusted: Adjust for market sensitivity
    """
    
    def __init__(
        self,
        capital: float = 100_000,
        target_portfolio_vol: float = 0.15,
        max_position_vol_contribution: float = 0.05,
        max_single_position: float = 0.10,
        risk_free_rate: float = 0.02,
    ):
        """
        Initialize Risk Parity Allocator.
        
        Args:
            capital: Total portfolio capital
            target_portfolio_vol: Target annualized volatility (default 15%)
            max_position_vol_contribution: Max vol contribution per position (default 5%)
            max_single_position: Max single position weight (default 10%)
            risk_free_rate: Annual risk-free rate
        """
        self.capital = capital
        self.target_vol = target_portfolio_vol
        self.max_vol_contribution = max_position_vol_contribution
        self.max_position = max_single_position
        self.rf_rate = risk_free_rate
    
    def calculate_stock_volatilities(
        self,
        returns_df: pd.DataFrame,
        annualize: bool = True,
    ) -> Dict[str, float]:
        """
        Calculate annualized volatility for each stock.
        
        Args:
            returns_df: DataFrame with stock returns (columns = tickers)
            annualize: Whether to annualize (multiply by sqrt(252))
            
        Returns:
            Dict mapping ticker to annualized volatility
        """
        vols = {}
        factor = np.sqrt(252) if annualize else 1.0
        
        for col in returns_df.columns:
            vol = returns_df[col].std() * factor
            vols[col] = vol if not np.isnan(vol) else 0.30  # Default 30% vol
        
        return vols
    
    def calculate_stock_betas(
        self,
        returns_df: pd.DataFrame,
        benchmark_returns: pd.Series,
    ) -> Dict[str, float]:
        """
        Calculate beta vs benchmark for each stock.
        
        Args:
            returns_df: DataFrame with stock returns
            benchmark_returns: Series with benchmark returns (e.g., SPY)
            
        Returns:
            Dict mapping ticker to beta
        """
        betas = {}
        
        # Align data
        aligned = returns_df.copy()
        aligned['_benchmark'] = benchmark_returns
        aligned = aligned.dropna()
        
        if len(aligned) < 20:
            # Not enough data, return default betas
            return {col: 1.0 for col in returns_df.columns}
        
        benchmark_var = aligned['_benchmark'].var()
        if benchmark_var == 0:
            return {col: 1.0 for col in returns_df.columns}
        
        for col in returns_df.columns:
            if col == '_benchmark':
                continue
            cov = aligned[col].cov(aligned['_benchmark'])
            beta = cov / benchmark_var
            betas[col] = float(beta) if not np.isnan(beta) else 1.0
        
        return betas
    
    def inverse_volatility_weights(
        self,
        volatilities: Dict[str, float],
        tickers: List[str],
    ) -> Dict[str, float]:
        """
        Calculate inverse volatility weights (simple risk parity).
        
        Lower volatility → Higher weight
        
        Args:
            volatilities: Dict of ticker to annualized volatility
            tickers: List of tickers to include
            
        Returns:
            Dict of ticker to weight (sums to 1.0)
        """
        inv_vols = {}
        for ticker in tickers:
            vol = volatilities.get(ticker, 0.30)
            if vol > 0.01:  # Min vol threshold
                inv_vols[ticker] = 1.0 / vol
            else:
                inv_vols[ticker] = 1.0 / 0.30  # Default
        
        total = sum(inv_vols.values())
        if total == 0:
            # Equal weight fallback
            n = len(tickers)
            return {t: 1.0 / n for t in tickers}
        
        return {t: iv / total for t, iv in inv_vols.items()}
    
    def vol_capped_weights(
        self,
        base_weights: Dict[str, float],
        volatilities: Dict[str, float],
        max_vol_contribution: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Apply volatility cap to position weights.
        
        Ensures no single position contributes more than max_vol_contribution
        to portfolio volatility.
        
        Args:
            base_weights: Initial weights (from scores or equal weight)
            volatilities: Dict of ticker to volatility
            max_vol_contribution: Max vol contribution per position
            
        Returns:
            Adjusted weights (sums to 1.0)
        """
        max_vol = max_vol_contribution or self.max_vol_contribution
        
        # Calculate vol contribution for each position
        # Simple approximation: vol_contribution ≈ weight * individual_vol
        adjusted = {}
        
        for ticker, weight in base_weights.items():
            vol = volatilities.get(ticker, 0.30)
            vol_contrib = weight * vol
            
            # If vol contribution exceeds max, cap the weight
            if vol_contrib > max_vol:
                adjusted[ticker] = max_vol / vol
            else:
                adjusted[ticker] = weight
        
        # Renormalize to sum to 1.0
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {t: w / total for t, w in adjusted.items()}
        
        return adjusted
    
    def risk_parity_weights(
        self,
        volatilities: Dict[str, float],
        correlation_matrix: Optional[pd.DataFrame] = None,
        tickers: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Calculate true risk parity weights (equal risk contribution).
        
        Each position contributes equally to total portfolio risk.
        Uses iterative optimization when correlations are provided.
        
        Args:
            volatilities: Dict of ticker to volatility
            correlation_matrix: Optional correlation matrix
            tickers: Optional list of tickers (uses volatilities keys if None)
            
        Returns:
            Dict of ticker to weight
        """
        if tickers is None:
            tickers = list(volatilities.keys())
        
        if len(tickers) == 0:
            return {}
        
        # Simple case: no correlation matrix, use inverse vol
        if correlation_matrix is None or correlation_matrix.empty:
            return self.inverse_volatility_weights(volatilities, tickers)
        
        # With correlations: iterative risk parity
        # Target: each position contributes 1/N to total risk
        n = len(tickers)
        target_rc = 1.0 / n  # Target risk contribution
        
        # Initialize with inverse vol weights
        weights = self.inverse_volatility_weights(volatilities, tickers)
        
        # Iterative adjustment (simplified Newton-like)
        for _ in range(50):  # Max iterations
            # Calculate marginal risk contributions
            risk_contribs = self._calculate_risk_contributions(
                weights, volatilities, correlation_matrix, tickers
            )
            
            # Adjust weights
            total_rc = sum(risk_contribs.values())
            if total_rc == 0:
                break
                
            max_deviation = 0
            new_weights = {}
            for ticker in tickers:
                rc = risk_contribs.get(ticker, target_rc)
                if rc > 0:
                    # Adjust weight inversely to risk contribution deviation
                    adjustment = (target_rc / rc) ** 0.5
                    new_weights[ticker] = weights[ticker] * adjustment
                    max_deviation = max(max_deviation, abs(rc - target_rc))
                else:
                    new_weights[ticker] = weights[ticker]
            
            # Normalize
            total = sum(new_weights.values())
            if total > 0:
                weights = {t: w / total for t, w in new_weights.items()}
            
            # Convergence check
            if max_deviation < 0.001:
                break
        
        return weights
    
    def _calculate_risk_contributions(
        self,
        weights: Dict[str, float],
        volatilities: Dict[str, float],
        corr_matrix: pd.DataFrame,
        tickers: List[str],
    ) -> Dict[str, float]:
        """Calculate marginal risk contribution for each position."""
        n = len(tickers)
        
        # Build covariance matrix
        cov_matrix = np.zeros((n, n))
        for i, t1 in enumerate(tickers):
            for j, t2 in enumerate(tickers):
                vol1 = volatilities.get(t1, 0.30)
                vol2 = volatilities.get(t2, 0.30)
                corr = 1.0 if i == j else corr_matrix.loc[t1, t2] if t1 in corr_matrix.index and t2 in corr_matrix.columns else 0.3
                cov_matrix[i, j] = vol1 * vol2 * corr
        
        # Weight vector
        w = np.array([weights.get(t, 0) for t in tickers])
        
        # Portfolio variance
        port_var = w @ cov_matrix @ w
        port_vol = np.sqrt(port_var) if port_var > 0 else 0.001
        
        # Marginal contributions: w_i * (Σw)_i / σ_p
        marginal = cov_matrix @ w
        risk_contribs = {}
        for i, ticker in enumerate(tickers):
            rc = (w[i] * marginal[i]) / port_vol if port_vol > 0 else 0
            risk_contribs[ticker] = rc
        
        # Normalize to sum to 1
        total = sum(risk_contribs.values())
        if total > 0:
            risk_contribs = {t: rc / total for t, rc in risk_contribs.items()}
        
        return risk_contribs
    
    def beta_adjusted_weights(
        self,
        base_weights: Dict[str, float],
        betas: Dict[str, float],
        target_beta: float = 1.0,
    ) -> Dict[str, float]:
        """
        Adjust weights to achieve target portfolio beta.
        
        Args:
            base_weights: Initial weights
            betas: Dict of ticker to beta
            target_beta: Target portfolio beta (default 1.0 = market)
            
        Returns:
            Adjusted weights
        """
        # Current portfolio beta
        current_beta = sum(
            base_weights.get(t, 0) * betas.get(t, 1.0)
            for t in base_weights.keys()
        )
        
        if current_beta == 0:
            return base_weights
        
        # Adjust weights inversely to beta difference
        adjusted = {}
        for ticker, weight in base_weights.items():
            beta = betas.get(ticker, 1.0)
            if current_beta > target_beta:
                # Reduce high-beta names
                if beta > 1.0:
                    factor = target_beta / beta
                    adjusted[ticker] = weight * factor ** 0.5
                else:
                    adjusted[ticker] = weight * 1.1  # Slight boost to low-beta
            else:
                # Increase high-beta names
                if beta > 1.0:
                    adjusted[ticker] = weight * 1.1
                else:
                    factor = beta / target_beta if target_beta > 0 else 1.0
                    adjusted[ticker] = weight * factor ** 0.5
        
        # Normalize
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {t: w / total for t, w in adjusted.items()}
        
        return adjusted
    
    def apply_sector_constraints(
        self,
        weights: Dict[str, float],
        sector_map: Dict[str, str],
        constraints: Optional[SectorConstraints] = None,
    ) -> Tuple[Dict[str, float], List[str]]:
        """
        Apply sector weight constraints.
        
        Args:
            weights: Current weights
            sector_map: Dict mapping ticker to sector
            constraints: SectorConstraints object
            
        Returns:
            Tuple of (adjusted_weights, warnings)
        """
        if constraints is None:
            constraints = SectorConstraints()
        
        warnings = []
        
        # Calculate sector weights
        sector_weights: Dict[str, float] = {}
        sector_tickers: Dict[str, List[str]] = {}
        
        for ticker, weight in weights.items():
            sector = sector_map.get(ticker, 'Other')
            sector_weights[sector] = sector_weights.get(sector, 0) + weight
            if sector not in sector_tickers:
                sector_tickers[sector] = []
            sector_tickers[sector].append(ticker)
        
        # Check and apply constraints
        adjusted = weights.copy()
        excess_weight = 0.0
        
        for sector, max_weight in constraints.max_weights.items():
            current = sector_weights.get(sector, 0)
            if current > max_weight:
                warnings.append(
                    f"Sector {sector}: {current*100:.1f}% exceeds cap {max_weight*100:.1f}%"
                )
                
                # Scale down positions in this sector
                scale = max_weight / current
                for ticker in sector_tickers.get(sector, []):
                    old_weight = adjusted[ticker]
                    adjusted[ticker] = old_weight * scale
                    excess_weight += old_weight - adjusted[ticker]
        
        # Redistribute excess weight to under-constrained sectors
        if excess_weight > 0:
            # Find sectors that can absorb more weight
            available = []
            for ticker, weight in adjusted.items():
                sector = sector_map.get(ticker, 'Other')
                max_weight = constraints.max_weights.get(sector, 1.0)
                current = sector_weights.get(sector, 0)
                if current < max_weight:
                    available.append(ticker)
            
            if available:
                boost = excess_weight / len(available)
                for ticker in available:
                    adjusted[ticker] += boost
        
        # Normalize
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {t: w / total for t, w in adjusted.items()}
        
        return adjusted, warnings
    
    def allocate_portfolio(
        self,
        scores: Dict[str, float],
        volatilities: Dict[str, float],
        betas: Dict[str, float],
        sector_map: Dict[str, str],
        prices: Dict[str, float],
        method: str = "risk_parity",
        correlation_matrix: Optional[pd.DataFrame] = None,
        constraints: Optional[SectorConstraints] = None,
        target_beta: float = 1.0,
    ) -> Tuple[List[RiskAwarePosition], PortfolioRiskProfile]:
        """
        Full risk-aware portfolio allocation.
        
        Args:
            scores: Dict of ticker to model score
            volatilities: Dict of ticker to annualized volatility
            betas: Dict of ticker to beta
            sector_map: Dict of ticker to sector
            prices: Dict of ticker to current price
            method: Allocation method ('risk_parity', 'inverse_vol', 'vol_capped', 'equal')
            correlation_matrix: Optional correlation matrix
            constraints: Sector constraints
            target_beta: Target portfolio beta
            
        Returns:
            Tuple of (positions, risk_profile)
        """
        tickers = list(scores.keys())
        
        if not tickers:
            return [], PortfolioRiskProfile(
                total_beta=0, weighted_avg_vol=0, portfolio_vol_estimate=0,
                sector_exposure={}, beta_exposure={}, concentration_hhi=0,
                effective_n=0, risk_tilt="N/A", warnings=["No tickers provided"]
            )
        
        # Step 1: Calculate base weights from scores
        score_total = sum(scores.values())
        if score_total > 0:
            score_weights = {t: s / score_total for t, s in scores.items()}
        else:
            score_weights = {t: 1.0 / len(tickers) for t in tickers}
        
        # Step 2: Apply risk-based weighting
        if method == "risk_parity":
            weights = self.risk_parity_weights(volatilities, correlation_matrix, tickers)
        elif method == "inverse_vol":
            weights = self.inverse_volatility_weights(volatilities, tickers)
        elif method == "vol_capped":
            weights = self.vol_capped_weights(score_weights, volatilities)
        elif method == "beta_adjusted":
            weights = self.inverse_volatility_weights(volatilities, tickers)
            weights = self.beta_adjusted_weights(weights, betas, target_beta)
        else:  # equal weight
            weights = {t: 1.0 / len(tickers) for t in tickers}
        
        # Step 3: Apply volatility cap
        weights = self.vol_capped_weights(weights, volatilities)
        
        # Step 4: Apply single position cap
        for ticker in weights:
            if weights[ticker] > self.max_position:
                weights[ticker] = self.max_position
        
        # Renormalize
        total = sum(weights.values())
        if total > 0:
            weights = {t: w / total for t, w in weights.items()}
        
        # Step 5: Apply sector constraints
        weights, sector_warnings = self.apply_sector_constraints(
            weights, sector_map, constraints
        )
        
        # Step 6: Build positions
        positions = []
        for ticker in tickers:
            weight = weights.get(ticker, 0)
            vol = volatilities.get(ticker, 0.30)
            beta = betas.get(ticker, 1.0)
            sector = sector_map.get(ticker, 'Other')
            score = scores.get(ticker, 0)
            price = prices.get(ticker, 0)
            
            # Calculate shares
            position_value = self.capital * weight
            shares = int(position_value / price) if price > 0 else 0
            actual_value = shares * price
            
            # Vol contribution (simplified)
            vol_contrib = weight * vol
            
            positions.append(RiskAwarePosition(
                ticker=ticker,
                raw_weight=score_weights.get(ticker, 0),
                risk_weight=weight,
                vol_contribution=vol_contrib,
                beta=beta,
                sector=sector,
                volatility=vol,
                score=score,
                shares=shares,
                position_value=actual_value,
            ))
        
        # Sort by weight
        positions.sort(key=lambda p: p.risk_weight, reverse=True)
        
        # Step 7: Build risk profile
        profile = self._build_risk_profile(positions, sector_warnings)
        
        return positions, profile
    
    def _build_risk_profile(
        self,
        positions: List[RiskAwarePosition],
        warnings: List[str],
    ) -> PortfolioRiskProfile:
        """Build comprehensive portfolio risk profile."""
        if not positions:
            return PortfolioRiskProfile(
                total_beta=0, weighted_avg_vol=0, portfolio_vol_estimate=0,
                sector_exposure={}, beta_exposure={}, concentration_hhi=0,
                effective_n=0, risk_tilt="N/A", warnings=warnings
            )
        
        # Normalize weights
        total_weight = sum(p.risk_weight for p in positions)
        
        # Portfolio metrics
        total_beta = sum(p.risk_weight * p.beta for p in positions) / total_weight if total_weight > 0 else 1.0
        weighted_vol = sum(p.risk_weight * p.volatility for p in positions) / total_weight if total_weight > 0 else 0.20
        
        # Simplified portfolio vol estimate (ignores correlations)
        port_vol_sq = sum((p.risk_weight * p.volatility) ** 2 for p in positions)
        port_vol = np.sqrt(port_vol_sq) if port_vol_sq > 0 else weighted_vol
        
        # Sector exposure
        sector_exp: Dict[str, float] = {}
        for p in positions:
            sector_exp[p.sector] = sector_exp.get(p.sector, 0) + p.risk_weight
        
        # Normalize sector exposure
        if total_weight > 0:
            sector_exp = {s: w / total_weight for s, w in sector_exp.items()}
        
        # Beta exposure breakdown
        low_beta = sum(p.risk_weight for p in positions if p.beta < 0.8) / total_weight if total_weight > 0 else 0
        med_beta = sum(p.risk_weight for p in positions if 0.8 <= p.beta <= 1.2) / total_weight if total_weight > 0 else 0
        high_beta = sum(p.risk_weight for p in positions if p.beta > 1.2) / total_weight if total_weight > 0 else 0
        
        beta_exp = {
            "Low (<0.8)": low_beta,
            "Medium (0.8-1.2)": med_beta,
            "High (>1.2)": high_beta,
        }
        
        # Concentration (HHI)
        weights = [p.risk_weight / total_weight for p in positions] if total_weight > 0 else []
        hhi = sum(w ** 2 for w in weights) * 10000 if weights else 0
        
        # Effective N (inverse HHI normalized)
        effective_n = 1.0 / sum(w ** 2 for w in weights) if weights and sum(w ** 2 for w in weights) > 0 else 0
        
        # Risk tilt determination
        if total_beta > 1.15:
            risk_tilt = "High Beta Tilt"
            warnings.append(f"Portfolio beta {total_beta:.2f} indicates aggressive market exposure")
        elif total_beta < 0.85:
            risk_tilt = "Defensive"
        else:
            risk_tilt = "Balanced"
        
        # Additional warnings
        if hhi > 2000:
            warnings.append(f"High concentration (HHI={hhi:.0f}): Consider more diversification")
        
        if effective_n < 10:
            warnings.append(f"Low effective positions ({effective_n:.1f}): Risk may be concentrated")
        
        # Sector concentration warnings
        for sector, weight in sector_exp.items():
            if weight > 0.30:
                warnings.append(f"Sector {sector} at {weight*100:.1f}%: Consider reducing exposure")
        
        return PortfolioRiskProfile(
            total_beta=total_beta,
            weighted_avg_vol=weighted_vol,
            portfolio_vol_estimate=port_vol,
            sector_exposure=sector_exp,
            beta_exposure=beta_exp,
            concentration_hhi=hhi,
            effective_n=effective_n,
            risk_tilt=risk_tilt,
            warnings=warnings,
        )


def generate_risk_report(
    positions: List[RiskAwarePosition],
    profile: PortfolioRiskProfile,
    benchmark_name: str = "SPY",
) -> str:
    """
    Generate a formatted risk analysis report.
    
    Args:
        positions: List of risk-aware positions
        profile: Portfolio risk profile
        benchmark_name: Benchmark name
        
    Returns:
        Formatted markdown report
    """
    report = []
    report.append("# 📊 Portfolio Risk Analysis Report")
    report.append("")
    report.append("## 🎯 Portfolio Summary")
    report.append("")
    report.append(f"| Metric | Value |")
    report.append(f"|--------|-------|")
    report.append(f"| **Portfolio Beta** | {profile.total_beta:.2f} |")
    report.append(f"| **Weighted Avg Volatility** | {profile.weighted_avg_vol*100:.1f}% |")
    report.append(f"| **Est. Portfolio Volatility** | {profile.portfolio_vol_estimate*100:.1f}% |")
    report.append(f"| **Concentration (HHI)** | {profile.concentration_hhi:.0f} |")
    report.append(f"| **Effective # Positions** | {profile.effective_n:.1f} |")
    report.append(f"| **Risk Tilt** | {profile.risk_tilt} |")
    report.append("")
    
    # Beta exposure
    report.append("## 📈 Beta Exposure")
    report.append("")
    report.append(f"| Category | Weight |")
    report.append(f"|----------|--------|")
    for cat, weight in profile.beta_exposure.items():
        report.append(f"| {cat} | {weight*100:.1f}% |")
    report.append("")
    
    # Sector exposure
    report.append("## 🏢 Sector Exposure")
    report.append("")
    report.append(f"| Sector | Weight |")
    report.append(f"|--------|--------|")
    for sector, weight in sorted(profile.sector_exposure.items(), key=lambda x: -x[1]):
        bar = "█" * int(weight * 20)
        report.append(f"| {sector} | {weight*100:.1f}% {bar} |")
    report.append("")
    
    # Position details
    report.append("## 📋 Position Details (Risk-Adjusted)")
    report.append("")
    report.append("| Ticker | Weight | Vol | Beta | Vol Contrib | Sector |")
    report.append("|--------|--------|-----|------|-------------|--------|")
    
    for p in positions[:20]:  # Top 20
        report.append(
            f"| **{p.ticker}** | {p.risk_weight*100:.1f}% | "
            f"{p.volatility*100:.0f}% | {p.beta:.2f} | "
            f"{p.vol_contribution*100:.2f}% | {p.sector} |"
        )
    report.append("")
    
    # Equal vs Risk Parity comparison
    report.append("## ⚖️ Equal Weight vs Risk Parity Comparison")
    report.append("")
    n = len(positions)
    equal_weight = 1.0 / n if n > 0 else 0
    report.append(f"| Ticker | Score Weight | Risk Parity | Change |")
    report.append(f"|--------|--------------|-------------|--------|")
    
    for p in positions[:10]:
        change = (p.risk_weight - p.raw_weight) / p.raw_weight * 100 if p.raw_weight > 0 else 0
        arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
        report.append(
            f"| {p.ticker} | {p.raw_weight*100:.1f}% | "
            f"{p.risk_weight*100:.1f}% | {arrow} {abs(change):.0f}% |"
        )
    report.append("")
    
    # Warnings
    if profile.warnings:
        report.append("## ⚠️ Risk Warnings")
        report.append("")
        for warning in profile.warnings:
            report.append(f"- {warning}")
        report.append("")
    
    # Recommendations
    report.append("## 💡 Risk Management Recommendations")
    report.append("")
    
    if profile.total_beta > 1.1:
        report.append("1. **Reduce Beta Exposure**: Consider decreasing high-beta positions or adding defensive names")
    
    if profile.concentration_hhi > 1500:
        report.append("2. **Improve Diversification**: Portfolio is concentrated; consider adding uncorrelated positions")
    
    max_sector = max(profile.sector_exposure.items(), key=lambda x: x[1]) if profile.sector_exposure else (None, 0)
    if max_sector[1] > 0.25:
        report.append(f"3. **Reduce Sector Concentration**: {max_sector[0]} exposure ({max_sector[1]*100:.0f}%) is high")
    
    report.append("")
    report.append("---")
    report.append(f"*Risk analysis based on historical volatilities and {benchmark_name} as benchmark*")
    
    return "\n".join(report)


if __name__ == "__main__":
    # Test the allocator
    print("Testing Risk Parity Allocator...")
    
    allocator = RiskParityAllocator(capital=100_000)
    
    # Sample data
    scores = {
        'NVDA': 0.85, 'AMD': 0.80, 'AAPL': 0.75, 'MSFT': 0.70,
        'URA': 0.72, 'NLR': 0.68, 'BA': 0.65, 'UNH': 0.60,
        'JPM': 0.55, 'PG': 0.50,
    }
    
    volatilities = {
        'NVDA': 0.55, 'AMD': 0.50, 'AAPL': 0.28, 'MSFT': 0.25,
        'URA': 0.60, 'NLR': 0.45, 'BA': 0.40, 'UNH': 0.22,
        'JPM': 0.30, 'PG': 0.18,
    }
    
    betas = {
        'NVDA': 1.8, 'AMD': 1.6, 'AAPL': 1.2, 'MSFT': 1.1,
        'URA': 1.5, 'NLR': 1.3, 'BA': 1.4, 'UNH': 0.8,
        'JPM': 1.2, 'PG': 0.6,
    }
    
    sector_map = {
        'NVDA': 'Semiconductors', 'AMD': 'Semiconductors',
        'AAPL': 'Technology', 'MSFT': 'Technology',
        'URA': 'Nuclear', 'NLR': 'Nuclear',
        'BA': 'Industrials', 'UNH': 'Healthcare',
        'JPM': 'Financials', 'PG': 'Consumer',
    }
    
    prices = {t: 100.0 for t in scores.keys()}  # Simplified
    
    positions, profile = allocator.allocate_portfolio(
        scores=scores,
        volatilities=volatilities,
        betas=betas,
        sector_map=sector_map,
        prices=prices,
        method="risk_parity",
    )
    
    print(f"\n✅ Allocated {len(positions)} positions")
    print(f"   Portfolio Beta: {profile.total_beta:.2f}")
    print(f"   Risk Tilt: {profile.risk_tilt}")
    print(f"   Effective N: {profile.effective_n:.1f}")
    
    print("\nTop 5 positions (risk-adjusted):")
    for p in positions[:5]:
        print(f"   {p.ticker}: {p.risk_weight*100:.1f}% (vol={p.volatility*100:.0f}%, beta={p.beta:.1f})")
    
    # Generate report
    report = generate_risk_report(positions, profile)
    print("\n" + "="*50)
    print(report[:2000])
