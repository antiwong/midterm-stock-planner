"""
Portfolio Optimizer with User Parameters
=========================================
Creates personalized portfolios based on user-defined risk tolerance,
time horizon, and return objectives.

Workflow:
1. Vertical Analysis: Rank stocks within each sector
2. Horizontal Analysis: Select across sectors to build diversified portfolio
3. Optimization: Adjust weights to meet risk/return targets
4. AI Analysis: Generate personalized recommendations
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import json

import pandas as pd
import numpy as np

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class InvestorProfile:
    """User's investment preferences and constraints."""
    
    # Risk Parameters
    risk_tolerance: str = "moderate"  # conservative, moderate, aggressive
    max_drawdown_tolerance: float = 0.15  # Maximum acceptable drawdown (15%)
    volatility_preference: str = "medium"  # low, medium, high
    
    # Return Parameters
    target_annual_return: float = 0.12  # Target 12% annual return
    min_acceptable_return: float = 0.05  # Minimum 5% to consider
    
    # Time Horizon
    time_horizon: str = "medium"  # short (1-3mo), medium (3-12mo), long (1-3yr)
    holding_period_months: int = 6  # Expected holding period
    
    # Portfolio Construction
    portfolio_size: int = 10  # Target number of holdings
    max_position_weight: float = 0.15  # Max 15% in single stock
    min_position_weight: float = 0.03  # Min 3% position
    max_sector_weight: float = 0.35  # Max 35% in single sector
    
    # Quality Filters
    min_quality_score: float = 30  # Minimum quality score (0-100)
    min_value_score: float = 20  # Minimum value score (0-100)
    require_profitability: bool = True  # Only profitable companies
    max_debt_to_equity: float = 2.0  # Maximum leverage
    
    # Style Preferences
    style_preference: str = "blend"  # growth, value, blend
    dividend_preference: str = "neutral"  # income, growth, neutral
    market_cap_preference: str = "all"  # large, mid, small, all
    
    # Sector Preferences (optional overweights/underweights)
    sector_preferences: Dict[str, float] = field(default_factory=dict)
    excluded_sectors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'risk_tolerance': self.risk_tolerance,
            'max_drawdown_tolerance': self.max_drawdown_tolerance,
            'volatility_preference': self.volatility_preference,
            'target_annual_return': self.target_annual_return,
            'min_acceptable_return': self.min_acceptable_return,
            'time_horizon': self.time_horizon,
            'holding_period_months': self.holding_period_months,
            'portfolio_size': self.portfolio_size,
            'max_position_weight': self.max_position_weight,
            'min_position_weight': self.min_position_weight,
            'max_sector_weight': self.max_sector_weight,
            'min_quality_score': self.min_quality_score,
            'min_value_score': self.min_value_score,
            'require_profitability': self.require_profitability,
            'max_debt_to_equity': self.max_debt_to_equity,
            'style_preference': self.style_preference,
            'dividend_preference': self.dividend_preference,
            'market_cap_preference': self.market_cap_preference,
            'sector_preferences': self.sector_preferences,
            'excluded_sectors': self.excluded_sectors,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'InvestorProfile':
        """Create from dictionary."""
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def conservative(cls) -> 'InvestorProfile':
        """Conservative investor profile."""
        return cls(
            risk_tolerance="conservative",
            max_drawdown_tolerance=0.10,
            volatility_preference="low",
            target_annual_return=0.08,
            min_acceptable_return=0.04,
            time_horizon="long",
            holding_period_months=12,
            portfolio_size=15,
            max_position_weight=0.10,
            max_sector_weight=0.25,
            min_quality_score=50,
            min_value_score=40,
            require_profitability=True,
            max_debt_to_equity=1.0,
            style_preference="value",
            dividend_preference="income",
        )
    
    @classmethod
    def moderate(cls) -> 'InvestorProfile':
        """Moderate investor profile."""
        return cls(
            risk_tolerance="moderate",
            max_drawdown_tolerance=0.15,
            volatility_preference="medium",
            target_annual_return=0.12,
            min_acceptable_return=0.06,
            time_horizon="medium",
            holding_period_months=6,
            portfolio_size=10,
            max_position_weight=0.15,
            max_sector_weight=0.35,
            min_quality_score=30,
            min_value_score=20,
            require_profitability=True,
            max_debt_to_equity=2.0,
            style_preference="blend",
            dividend_preference="neutral",
        )
    
    @classmethod
    def aggressive(cls) -> 'InvestorProfile':
        """Aggressive investor profile."""
        return cls(
            risk_tolerance="aggressive",
            max_drawdown_tolerance=0.25,
            volatility_preference="high",
            target_annual_return=0.20,
            min_acceptable_return=0.10,
            time_horizon="short",
            holding_period_months=3,
            portfolio_size=8,
            max_position_weight=0.20,
            max_sector_weight=0.40,
            min_quality_score=20,
            min_value_score=10,
            require_profitability=False,
            max_debt_to_equity=3.0,
            style_preference="growth",
            dividend_preference="growth",
        )


@dataclass
class PortfolioResult:
    """Result of portfolio optimization."""
    
    holdings: pd.DataFrame  # Ticker, weight, sector, scores
    metrics: Dict[str, float]  # Expected return, volatility, sharpe, etc.
    sector_allocation: Dict[str, float]
    risk_assessment: Dict[str, Any]
    profile_used: InvestorProfile
    vertical_candidates: Dict[str, pd.DataFrame]  # Per-sector candidates
    optimization_log: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'holdings': self.holdings.to_dict('records'),
            'metrics': self.metrics,
            'sector_allocation': self.sector_allocation,
            'risk_assessment': self.risk_assessment,
            'profile': self.profile_used.to_dict(),
            'optimization_log': self.optimization_log,
        }


class PortfolioOptimizer:
    """
    Builds optimized portfolios based on investor profiles.
    """
    
    def __init__(self, profile: InvestorProfile):
        self.profile = profile
        self.log = []
    
    def _log(self, msg: str):
        """Add to optimization log."""
        self.log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        print(f"   {msg}")
    
    def run_vertical_analysis(
        self,
        stocks_df: pd.DataFrame,
        top_k_per_sector: int = 5,
    ) -> Dict[str, pd.DataFrame]:
        """
        Run vertical analysis: rank stocks within each sector.
        
        Returns:
            Dictionary mapping sector -> DataFrame of top candidates
        """
        self._log("Starting vertical analysis (within-sector ranking)...")
        
        # Ensure required columns
        required_cols = ['ticker', 'sector']
        for col in required_cols:
            if col not in stocks_df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Apply profile-based filters
        filtered_df = self._apply_filters(stocks_df)
        self._log(f"After filters: {len(filtered_df)}/{len(stocks_df)} stocks remain")
        
        # Compute composite score based on profile
        filtered_df = self._compute_composite_score(filtered_df)
        
        # Group by sector and select top K
        vertical_candidates = {}
        sectors = filtered_df['sector'].unique()
        
        for sector in sectors:
            if sector in self.profile.excluded_sectors:
                self._log(f"  Skipping excluded sector: {sector}")
                continue
            
            sector_df = filtered_df[filtered_df['sector'] == sector].copy()
            
            if len(sector_df) == 0:
                continue
            
            # Rank by composite score
            sector_df = sector_df.sort_values('composite_score', ascending=False)
            sector_df['rank_in_sector'] = range(1, len(sector_df) + 1)
            
            # Select top K
            top_k = sector_df.head(top_k_per_sector)
            vertical_candidates[sector] = top_k
            
            self._log(f"  {sector}: {len(top_k)} candidates (best: {top_k.iloc[0]['ticker']} @ {top_k.iloc[0]['composite_score']:.3f})")
        
        self._log(f"Vertical analysis complete: {sum(len(v) for v in vertical_candidates.values())} total candidates across {len(vertical_candidates)} sectors")
        
        return vertical_candidates
    
    def _apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply profile-based filters to stock universe."""
        filtered = df.copy()
        initial_count = len(filtered)
        
        # Quality filter
        if 'quality_score' in filtered.columns:
            filtered = filtered[filtered['quality_score'] >= self.profile.min_quality_score]
        
        # Value filter
        if 'value_score' in filtered.columns:
            filtered = filtered[filtered['value_score'] >= self.profile.min_value_score]
        
        # Profitability filter
        if self.profile.require_profitability and 'roe' in filtered.columns:
            filtered = filtered[filtered['roe'] > 0]
        
        # Leverage filter
        if 'debt_to_equity' in filtered.columns:
            filtered = filtered[filtered['debt_to_equity'] <= self.profile.max_debt_to_equity]
        
        # Excluded sectors
        if self.profile.excluded_sectors and 'sector' in filtered.columns:
            filtered = filtered[~filtered['sector'].isin(self.profile.excluded_sectors)]
        
        self._log(f"Filters applied: {initial_count} → {len(filtered)} stocks")
        
        return filtered
    
    def _compute_composite_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute composite score based on investor profile.
        
        Weights adjusted based on:
        - Risk tolerance: Conservative favors quality, Aggressive favors momentum
        - Style preference: Value vs Growth emphasis
        - Time horizon: Short-term favors technicals, Long-term favors fundamentals
        """
        result = df.copy()
        
        # Base weights
        w_model = 0.4  # Model prediction score
        w_value = 0.2  # Value score
        w_quality = 0.2  # Quality score
        w_tech = 0.2  # Technical score
        
        # Adjust weights based on profile
        if self.profile.risk_tolerance == "conservative":
            w_quality += 0.1
            w_model -= 0.1
        elif self.profile.risk_tolerance == "aggressive":
            w_model += 0.1
            w_quality -= 0.1
        
        if self.profile.style_preference == "value":
            w_value += 0.1
            w_tech -= 0.1
        elif self.profile.style_preference == "growth":
            w_model += 0.1
            w_value -= 0.1
        
        if self.profile.time_horizon == "short":
            w_tech += 0.1
            w_quality -= 0.1
        elif self.profile.time_horizon == "long":
            w_quality += 0.1
            w_tech -= 0.1
        
        # Normalize weights
        total_w = w_model + w_value + w_quality + w_tech
        w_model /= total_w
        w_value /= total_w
        w_quality /= total_w
        w_tech /= total_w
        
        self._log(f"Score weights: model={w_model:.2f}, value={w_value:.2f}, quality={w_quality:.2f}, tech={w_tech:.2f}")
        
        # Compute composite score
        result['composite_score'] = 0.0
        
        # Normalize scores to 0-1 range
        for col, weight in [('score', w_model), ('value_score', w_value), 
                            ('quality_score', w_quality), ('tech_score', w_tech)]:
            if col in result.columns:
                # Handle different score ranges
                col_data = result[col].fillna(0)
                if col_data.max() > 1:
                    # Assume 0-100 scale
                    normalized = col_data / 100
                else:
                    normalized = col_data
                result['composite_score'] += weight * normalized
        
        return result
    
    def run_horizontal_analysis(
        self,
        vertical_candidates: Dict[str, pd.DataFrame],
        price_history: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Run horizontal analysis: select across sectors to build portfolio.
        
        Returns:
            DataFrame with final portfolio holdings and weights
        """
        self._log("Starting horizontal analysis (cross-sector selection)...")
        
        # Combine all candidates
        all_candidates = pd.concat(vertical_candidates.values(), ignore_index=True)
        self._log(f"Candidate pool: {len(all_candidates)} stocks from {len(vertical_candidates)} sectors")
        
        # Sort by composite score
        all_candidates = all_candidates.sort_values('composite_score', ascending=False)
        
        # Initial selection: top N by score
        initial_n = min(self.profile.portfolio_size * 2, len(all_candidates))
        candidates = all_candidates.head(initial_n).copy()
        
        # Apply sector constraints
        portfolio = self._apply_sector_constraints(candidates)
        
        # Compute initial weights (score-weighted)
        portfolio = self._compute_initial_weights(portfolio)
        
        # Optimize weights based on risk/return targets
        if price_history is not None:
            portfolio = self._optimize_weights(portfolio, price_history)
        
        # Apply position constraints
        portfolio = self._apply_position_constraints(portfolio)
        
        # Final selection
        portfolio = portfolio.head(self.profile.portfolio_size)
        
        # Renormalize weights
        portfolio['weight'] = portfolio['weight'] / portfolio['weight'].sum()
        
        self._log(f"Final portfolio: {len(portfolio)} holdings")
        
        return portfolio
    
    def _apply_sector_constraints(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """Apply sector weight constraints."""
        result = candidates.copy()
        
        # Count per sector
        sector_counts = result['sector'].value_counts()
        max_per_sector = max(2, int(self.profile.portfolio_size * self.profile.max_sector_weight))
        
        # Limit stocks per sector
        filtered_rows = []
        sector_counter = {}
        
        for _, row in result.iterrows():
            sector = row['sector']
            sector_counter[sector] = sector_counter.get(sector, 0) + 1
            
            if sector_counter[sector] <= max_per_sector:
                filtered_rows.append(row)
        
        result = pd.DataFrame(filtered_rows)
        self._log(f"After sector constraints: {len(result)} candidates")
        
        return result
    
    def _compute_initial_weights(self, portfolio: pd.DataFrame) -> pd.DataFrame:
        """Compute initial weights based on scores."""
        result = portfolio.copy()
        
        # Score-weighted
        scores = result['composite_score'].values
        scores = np.maximum(scores, 0.01)  # Avoid zero/negative
        
        weights = scores / scores.sum()
        result['weight'] = weights
        
        return result
    
    def _optimize_weights(
        self,
        portfolio: pd.DataFrame,
        price_history: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Optimize weights based on risk/return targets.
        
        Uses simplified mean-variance optimization.
        """
        result = portfolio.copy()
        tickers = result['ticker'].tolist()
        
        # Get returns for portfolio stocks
        if 'ticker' not in price_history.columns or 'close' not in price_history.columns:
            self._log("Price history missing required columns, skipping optimization")
            return result
        
        # Pivot to get returns matrix
        try:
            prices = price_history[price_history['ticker'].isin(tickers)].pivot(
                index='date', columns='ticker', values='close'
            )
            returns = prices.pct_change().dropna()
            
            if len(returns) < 20:
                self._log("Insufficient price history for optimization")
                return result
            
            # Calculate expected returns and covariance
            mean_returns = returns.mean() * 252  # Annualized
            cov_matrix = returns.cov() * 252  # Annualized
            
            # Current weights
            current_weights = result.set_index('ticker')['weight'].reindex(tickers).fillna(0).values
            
            # Simple optimization: adjust weights to reduce volatility while maintaining return
            # This is a simplified approach - full optimization would use scipy.optimize
            
            # Calculate current portfolio metrics
            port_return = np.dot(current_weights, mean_returns.reindex(tickers).fillna(0))
            port_vol = np.sqrt(np.dot(current_weights, np.dot(cov_matrix.reindex(index=tickers, columns=tickers).fillna(0), current_weights)))
            
            self._log(f"Initial portfolio: Return={port_return:.1%}, Vol={port_vol:.1%}")
            
            # Adjust based on risk tolerance
            if self.profile.risk_tolerance == "conservative":
                # Reduce weight on high volatility stocks
                stock_vols = returns.std() * np.sqrt(252)
                vol_adj = 1 / (1 + stock_vols.reindex(tickers).fillna(stock_vols.mean()))
                adjusted_weights = current_weights * vol_adj.values
                adjusted_weights = adjusted_weights / adjusted_weights.sum()
            elif self.profile.risk_tolerance == "aggressive":
                # Increase weight on high return stocks
                ret_adj = 1 + mean_returns.reindex(tickers).fillna(0)
                adjusted_weights = current_weights * ret_adj.values
                adjusted_weights = adjusted_weights / adjusted_weights.sum()
            else:
                adjusted_weights = current_weights
            
            # Update weights
            for i, ticker in enumerate(tickers):
                if ticker in result['ticker'].values:
                    result.loc[result['ticker'] == ticker, 'weight'] = adjusted_weights[i]
            
            # Recalculate metrics
            port_return = np.dot(adjusted_weights, mean_returns.reindex(tickers).fillna(0))
            port_vol = np.sqrt(np.dot(adjusted_weights, np.dot(cov_matrix.reindex(index=tickers, columns=tickers).fillna(0), adjusted_weights)))
            
            self._log(f"Optimized portfolio: Return={port_return:.1%}, Vol={port_vol:.1%}")
            
        except Exception as e:
            self._log(f"Optimization error: {e}")
        
        return result
    
    def _apply_position_constraints(self, portfolio: pd.DataFrame) -> pd.DataFrame:
        """Apply min/max position weight constraints."""
        result = portfolio.copy()
        
        # Cap max weights
        result['weight'] = result['weight'].clip(
            lower=self.profile.min_position_weight,
            upper=self.profile.max_position_weight
        )
        
        # Renormalize
        result['weight'] = result['weight'] / result['weight'].sum()
        
        return result
    
    def calculate_portfolio_metrics(
        self,
        portfolio: pd.DataFrame,
        price_history: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """Calculate portfolio risk and return metrics."""
        metrics = {}
        
        # Basic metrics from scores
        metrics['avg_composite_score'] = portfolio['composite_score'].mean()
        metrics['holding_count'] = len(portfolio)
        
        # Score-based estimates
        if 'value_score' in portfolio.columns:
            metrics['avg_value_score'] = portfolio['value_score'].mean()
        if 'quality_score' in portfolio.columns:
            metrics['avg_quality_score'] = portfolio['quality_score'].mean()
        if 'tech_score' in portfolio.columns:
            metrics['avg_tech_score'] = portfolio['tech_score'].mean()
        
        # Concentration metrics
        weights = portfolio['weight'].values
        hhi = (weights ** 2).sum()
        metrics['hhi'] = hhi
        metrics['effective_n'] = 1 / hhi if hhi > 0 else 0
        metrics['diversification_score'] = 1 - hhi
        
        # Sector concentration
        sector_weights = portfolio.groupby('sector')['weight'].sum()
        metrics['sector_count'] = len(sector_weights)
        metrics['max_sector_weight'] = sector_weights.max()
        metrics['sector_hhi'] = (sector_weights ** 2).sum()
        
        # Price-based metrics if available
        if price_history is not None:
            try:
                tickers = portfolio['ticker'].tolist()
                prices = price_history[price_history['ticker'].isin(tickers)].pivot(
                    index='date', columns='ticker', values='close'
                )
                returns = prices.pct_change().dropna()
                
                if len(returns) > 20:
                    # Portfolio returns
                    port_weights = portfolio.set_index('ticker')['weight'].reindex(returns.columns).fillna(0)
                    port_returns = (returns * port_weights).sum(axis=1)
                    
                    # Risk metrics
                    metrics['expected_return'] = port_returns.mean() * 252
                    metrics['volatility'] = port_returns.std() * np.sqrt(252)
                    metrics['sharpe_ratio'] = metrics['expected_return'] / metrics['volatility'] if metrics['volatility'] > 0 else 0
                    
                    # Downside risk
                    neg_returns = port_returns[port_returns < 0]
                    metrics['sortino_ratio'] = metrics['expected_return'] / (neg_returns.std() * np.sqrt(252)) if len(neg_returns) > 0 else 0
                    
                    # Max drawdown
                    cumulative = (1 + port_returns).cumprod()
                    running_max = cumulative.expanding().max()
                    drawdown = (cumulative - running_max) / running_max
                    metrics['max_drawdown'] = drawdown.min()
                    
                    # VaR/CVaR
                    metrics['var_95'] = np.percentile(port_returns, 5)
                    metrics['cvar_95'] = port_returns[port_returns <= metrics['var_95']].mean()
                    
            except Exception as e:
                self._log(f"Metrics calculation error: {e}")
        
        return metrics
    
    def assess_risk(
        self,
        portfolio: pd.DataFrame,
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Assess portfolio risk relative to investor profile."""
        assessment = {
            'overall_risk_level': 'medium',
            'meets_criteria': True,
            'warnings': [],
            'recommendations': [],
        }
        
        # Check against profile targets
        if 'expected_return' in metrics:
            if metrics['expected_return'] < self.profile.min_acceptable_return:
                assessment['warnings'].append(
                    f"Expected return ({metrics['expected_return']:.1%}) below minimum ({self.profile.min_acceptable_return:.1%})"
                )
                assessment['meets_criteria'] = False
            elif metrics['expected_return'] < self.profile.target_annual_return:
                assessment['recommendations'].append(
                    f"Expected return ({metrics['expected_return']:.1%}) below target ({self.profile.target_annual_return:.1%})"
                )
        
        if 'max_drawdown' in metrics:
            if abs(metrics['max_drawdown']) > self.profile.max_drawdown_tolerance:
                assessment['warnings'].append(
                    f"Max drawdown ({metrics['max_drawdown']:.1%}) exceeds tolerance ({-self.profile.max_drawdown_tolerance:.1%})"
                )
                assessment['meets_criteria'] = False
        
        if 'volatility' in metrics:
            vol_thresholds = {'low': 0.15, 'medium': 0.25, 'high': 0.40}
            threshold = vol_thresholds.get(self.profile.volatility_preference, 0.25)
            if metrics['volatility'] > threshold:
                assessment['warnings'].append(
                    f"Volatility ({metrics['volatility']:.1%}) exceeds preference threshold ({threshold:.1%})"
                )
        
        # Position concentration
        if metrics.get('max_sector_weight', 0) > self.profile.max_sector_weight:
            assessment['warnings'].append(
                f"Sector concentration ({metrics['max_sector_weight']:.1%}) exceeds limit ({self.profile.max_sector_weight:.1%})"
            )
        
        # Diversification
        if metrics.get('effective_n', 0) < self.profile.portfolio_size * 0.5:
            assessment['recommendations'].append(
                "Portfolio is highly concentrated - consider more equal weighting"
            )
        
        # Overall risk level
        warning_count = len(assessment['warnings'])
        if warning_count == 0:
            assessment['overall_risk_level'] = 'low' if self.profile.risk_tolerance == 'conservative' else 'medium'
        elif warning_count <= 2:
            assessment['overall_risk_level'] = 'medium'
        else:
            assessment['overall_risk_level'] = 'high'
        
        return assessment
    
    def optimize(
        self,
        stocks_df: pd.DataFrame,
        price_history: Optional[pd.DataFrame] = None,
        top_k_per_sector: int = 5,
    ) -> PortfolioResult:
        """
        Run full portfolio optimization.
        
        Args:
            stocks_df: DataFrame with stock scores and fundamentals
            price_history: Optional price history for risk calculations
            top_k_per_sector: Number of candidates per sector in vertical analysis
        
        Returns:
            PortfolioResult with optimized portfolio
        """
        self._log("=" * 60)
        self._log(f"PORTFOLIO OPTIMIZATION")
        self._log(f"Profile: {self.profile.risk_tolerance}, Target: {self.profile.target_annual_return:.0%}")
        self._log("=" * 60)
        
        # Step 1: Vertical Analysis
        vertical_candidates = self.run_vertical_analysis(stocks_df, top_k_per_sector)
        
        # Step 2: Horizontal Analysis
        portfolio = self.run_horizontal_analysis(vertical_candidates, price_history)
        
        # Step 3: Calculate Metrics
        metrics = self.calculate_portfolio_metrics(portfolio, price_history)
        
        # Step 4: Risk Assessment
        risk_assessment = self.assess_risk(portfolio, metrics)
        
        # Step 5: Sector Allocation
        sector_allocation = portfolio.groupby('sector')['weight'].sum().to_dict()
        
        self._log("=" * 60)
        self._log("OPTIMIZATION COMPLETE")
        self._log(f"Holdings: {len(portfolio)}")
        self._log(f"Sectors: {len(sector_allocation)}")
        if 'expected_return' in metrics:
            self._log(f"Expected Return: {metrics['expected_return']:.1%}")
            self._log(f"Volatility: {metrics['volatility']:.1%}")
            self._log(f"Sharpe: {metrics.get('sharpe_ratio', 0):.2f}")
        self._log(f"Risk Level: {risk_assessment['overall_risk_level'].upper()}")
        self._log("=" * 60)
        
        return PortfolioResult(
            holdings=portfolio,
            metrics=metrics,
            sector_allocation=sector_allocation,
            risk_assessment=risk_assessment,
            profile_used=self.profile,
            vertical_candidates=vertical_candidates,
            optimization_log=self.log,
        )


def generate_ai_analysis(
    result: PortfolioResult,
    run_metrics: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate AI-powered analysis of the optimized portfolio.
    
    Uses Gemini to explain the portfolio and provide recommendations.
    """
    try:
        import google.generativeai as genai
        import os
        
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return "AI analysis unavailable: No API key configured"
        
        genai.configure(api_key=api_key)
        
        # Try different model names
        model_names = ['gemini-2.0-flash-exp', 'gemini-1.5-flash-latest', 'gemini-1.5-pro-latest', 'gemini-pro']
        model = None
        
        for name in model_names:
            try:
                model = genai.GenerativeModel(name)
                break
            except:
                continue
        
        if model is None:
            return "AI analysis unavailable: Could not initialize model"
        
        # Build prompt
        profile = result.profile_used
        holdings_str = result.holdings[['ticker', 'sector', 'weight', 'composite_score']].to_string()
        
        prompt = f"""You are a financial advisor analyzing a personalized stock portfolio.

## Investor Profile
- Risk Tolerance: {profile.risk_tolerance}
- Time Horizon: {profile.time_horizon} ({profile.holding_period_months} months)
- Target Annual Return: {profile.target_annual_return:.0%}
- Max Acceptable Drawdown: {profile.max_drawdown_tolerance:.0%}
- Style Preference: {profile.style_preference}
- Portfolio Size Target: {profile.portfolio_size} stocks

## Optimized Portfolio Holdings
{holdings_str}

## Portfolio Metrics
- Holdings: {result.metrics.get('holding_count', 'N/A')}
- Expected Return: {result.metrics.get('expected_return', 0):.1%}
- Volatility: {result.metrics.get('volatility', 0):.1%}
- Sharpe Ratio: {result.metrics.get('sharpe_ratio', 0):.2f}
- Max Drawdown: {result.metrics.get('max_drawdown', 0):.1%}
- Diversification Score: {result.metrics.get('diversification_score', 0):.2f}

## Sector Allocation
{json.dumps(result.sector_allocation, indent=2)}

## Risk Assessment
- Overall Risk Level: {result.risk_assessment['overall_risk_level']}
- Meets Criteria: {result.risk_assessment['meets_criteria']}
- Warnings: {result.risk_assessment['warnings']}

Please provide:
1. **Portfolio Summary**: A brief overview of this portfolio's characteristics
2. **Alignment with Profile**: How well does this portfolio match the investor's stated preferences?
3. **Risk Analysis**: Key risks to be aware of
4. **Sector Commentary**: Comments on the sector allocation
5. **Top Holdings Analysis**: Brief analysis of the top 3-5 holdings
6. **Recommendations**: Any adjustments or considerations for the investor
7. **Time Horizon Suitability**: Is this portfolio appropriate for the stated time horizon?

Keep the response concise but insightful. Focus on actionable insights.
"""
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"AI analysis error: {str(e)}"


# ============================================================================
# MAIN SCRIPT
# ============================================================================

def main():
    """Run portfolio optimization from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Optimize portfolio based on investor profile")
    parser.add_argument("--run-id", type=str, help="Backtest run ID to analyze")
    parser.add_argument("--output", type=str, default="output", help="Output directory")
    parser.add_argument("--profile", type=str, default="moderate", 
                       choices=["conservative", "moderate", "aggressive", "custom"],
                       help="Investor profile preset")
    
    # Custom profile parameters
    parser.add_argument("--risk-tolerance", type=str, choices=["conservative", "moderate", "aggressive"])
    parser.add_argument("--target-return", "--target-annual-return", type=float, dest="target_return",
                       help="Target annual return (e.g., 0.12 for 12%%)")
    parser.add_argument("--max-drawdown", type=float, help="Max acceptable drawdown (e.g., 0.15 for 15%%)")
    parser.add_argument("--time-horizon", type=str, choices=["short", "medium", "long"])
    parser.add_argument("--portfolio-size", type=int, help="Number of holdings")
    parser.add_argument("--max-position", "--max-position-weight", type=float, dest="max_position",
                       help="Max single position weight")
    parser.add_argument("--max-sector", "--max-sector-weight", type=float, dest="max_sector",
                       help="Max single sector weight")
    parser.add_argument("--style", "--investment-style", type=str, dest="style",
                       choices=["value", "growth", "blend"])
    parser.add_argument("--dividend-preference", type=str, choices=["income", "growth", "neutral"],
                       help="Dividend preference")
    
    parser.add_argument("--with-ai", "--with-ai-recommendations", action="store_true", dest="with_ai",
                       help="Generate AI analysis")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("PERSONALIZED PORTFOLIO OPTIMIZER")
    print("=" * 70)
    
    # Create investor profile
    if args.profile == "conservative":
        profile = InvestorProfile.conservative()
    elif args.profile == "aggressive":
        profile = InvestorProfile.aggressive()
    else:
        profile = InvestorProfile.moderate()
    
    # Override with custom parameters
    if args.risk_tolerance:
        profile.risk_tolerance = args.risk_tolerance
    if args.target_return:
        profile.target_annual_return = args.target_return
    if args.max_drawdown:
        profile.max_drawdown_tolerance = args.max_drawdown
    if args.time_horizon:
        profile.time_horizon = args.time_horizon
    if args.portfolio_size:
        profile.portfolio_size = args.portfolio_size
    if args.max_position:
        profile.max_position_weight = args.max_position
    if args.max_sector:
        profile.max_sector_weight = args.max_sector
    if args.style:
        profile.style_preference = args.style
    if args.dividend_preference:
        profile.dividend_preference = args.dividend_preference
    
    print(f"\nInvestor Profile: {profile.risk_tolerance}")
    print(f"  Target Return: {profile.target_annual_return:.0%}")
    print(f"  Max Drawdown: {profile.max_drawdown_tolerance:.0%}")
    print(f"  Time Horizon: {profile.time_horizon}")
    print(f"  Portfolio Size: {profile.portfolio_size}")
    print(f"  Style: {profile.style_preference}")
    
    # Load data
    from src.analytics.models import get_db, Run, StockScore
    
    db = get_db("data/analysis.db")
    session = db.get_session()
    
    try:
        # Get run
        if args.run_id:
            run = session.query(Run).filter_by(run_id=args.run_id).first()
        else:
            run = session.query(Run).order_by(Run.created_at.desc()).first()
        
        if not run:
            print("❌ No runs found")
            return 1
        
        print(f"\nUsing run: {run.run_id}")
        
        # Get scores
        scores = session.query(StockScore).filter_by(run_id=run.run_id).all()
        scores_df = pd.DataFrame([s.to_dict() for s in scores])
        
        print(f"Loaded {len(scores_df)} stocks")
        
        # Load price data
        price_path = Path("data/prices.csv")
        price_df = None
        if price_path.exists():
            price_df = pd.read_csv(price_path, parse_dates=['date'])
            print(f"Loaded price history: {len(price_df)} rows")
        
        # Create optimizer and run
        optimizer = PortfolioOptimizer(profile)
        result = optimizer.optimize(scores_df, price_df)
        
        # Save results - find existing run folder or create one
        output_dir = Path(args.output)
        
        # Look for existing run folder (might have watchlist prefix)
        run_folder = None
        for folder in output_dir.iterdir():
            if folder.is_dir() and run.run_id[:16] in folder.name:
                run_folder = folder
                break
        
        if not run_folder:
            # Create new folder (with watchlist if available)
            watchlist = getattr(run, 'watchlist', None)
            if watchlist:
                run_folder = output_dir / f"run_{watchlist}_{run.run_id[:16]}"
            else:
                run_folder = output_dir / f"run_{run.run_id[:16]}"
        
        run_folder.mkdir(parents=True, exist_ok=True)
        
        # Save holdings
        holdings_path = run_folder / f"optimized_portfolio_{profile.risk_tolerance}.csv"
        result.holdings.to_csv(holdings_path, index=False)
        print(f"\n✅ Saved portfolio: {holdings_path}")
        
        # Save full result
        result_path = run_folder / f"optimization_result_{profile.risk_tolerance}.json"
        with open(result_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        print(f"✅ Saved result: {result_path}")
        
        # Generate AI analysis
        if args.with_ai:
            print("\n" + "=" * 70)
            print("GENERATING AI ANALYSIS...")
            print("=" * 70)
            
            ai_analysis = generate_ai_analysis(result)
            
            # Save AI analysis
            ai_path = run_folder / f"ai_portfolio_analysis_{profile.risk_tolerance}.md"
            with open(ai_path, 'w') as f:
                f.write(f"# Personalized Portfolio Analysis\n\n")
                f.write(f"**Profile:** {profile.risk_tolerance.title()}\n")
                f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                f.write("---\n\n")
                f.write(ai_analysis)
            
            print(f"✅ Saved AI analysis: {ai_path}")
            print("\n--- AI Analysis Preview ---")
            print(ai_analysis[:1000] + "..." if len(ai_analysis) > 1000 else ai_analysis)
        
        print("\n" + "=" * 70)
        print("OPTIMIZATION COMPLETE")
        print("=" * 70)
        
        return 0
        
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
