"""
Domain Analysis Module
======================
Implements vertical (within-sector) and horizontal (across-sector) analysis
for rigorous numeric stock selection.

Vertical Analysis:
- Composite domain score combining model, value, and quality scores
- Hard numeric filters (profitability, leverage)
- Per-sector candidate exports

Horizontal Analysis:
- Candidate pool aggregation from vertical top-K
- Risk-adjusted portfolio construction
- Optimization with constraints
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import itertools
import json

import pandas as pd
import numpy as np

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class AnalysisConfig:
    """Configuration for domain analysis."""
    # Composite score weights
    w_model: float = 0.5
    w_value: float = 0.3
    w_quality: float = 0.2
    
    # Hard filters
    min_roe: float = 0.0
    min_net_margin: float = 0.0
    max_debt_to_equity: float = 2.0
    min_market_cap: Optional[float] = None
    min_avg_volume: Optional[float] = None
    
    # Vertical settings
    top_k_per_sector: int = 5
    export_candidates: bool = True
    
    # Horizontal settings
    portfolio_size: int = 10
    max_position_weight: float = 0.15
    min_position_weight: float = 0.02
    max_sector_weight: float = 0.35
    
    # Optimization targets
    target_max_drawdown: float = 0.20
    target_volatility: float = 0.25
    min_diversification: float = 0.70
    
    # Selection method
    selection_method: str = 'heuristic'
    max_combinations: int = 1000
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'AnalysisConfig':
        """Create config from dictionary.
        
        Args:
            config: Either the full config dict (with 'analysis' key) or 
                   the analysis dict directly
        """
        # Handle both full config and analysis-only dict
        if 'analysis' in config:
            analysis = config.get('analysis', {})
        else:
            analysis = config
        
        weights = analysis.get('weights', {})
        filters = analysis.get('filters', {})
        vertical = analysis.get('vertical', {})
        horizontal = analysis.get('horizontal', {})
        
        return cls(
            w_model=weights.get('model_score', 0.5),
            w_value=weights.get('value_score', 0.3),
            w_quality=weights.get('quality_score', 0.2),
            min_roe=filters.get('min_roe', 0.0),
            min_net_margin=filters.get('min_net_margin', 0.0),
            max_debt_to_equity=filters.get('max_debt_to_equity', 2.0),
            min_market_cap=filters.get('min_market_cap'),
            min_avg_volume=filters.get('min_avg_volume'),
            top_k_per_sector=vertical.get('top_k_per_sector', 5),
            export_candidates=vertical.get('export_candidates', True),
            portfolio_size=horizontal.get('portfolio_size', 10),
            max_position_weight=horizontal.get('max_position_weight', 0.15),
            min_position_weight=horizontal.get('min_position_weight', 0.02),
            max_sector_weight=horizontal.get('max_sector_weight', 0.35),
            target_max_drawdown=horizontal.get('target_max_drawdown', 0.20),
            target_volatility=horizontal.get('target_volatility', 0.25),
            min_diversification=horizontal.get('min_diversification', 0.70),
            selection_method=horizontal.get('selection_method', 'heuristic'),
            max_combinations=horizontal.get('max_combinations', 1000),
        )


@dataclass
class VerticalResult:
    """Result of vertical analysis for a single sector."""
    sector: str
    date: datetime
    candidates: pd.DataFrame
    filtered_out: pd.DataFrame
    filter_reasons: Dict[str, int]


@dataclass
class HorizontalResult:
    """Result of horizontal portfolio construction."""
    date: datetime
    portfolio: pd.DataFrame  # Final portfolio with weights
    candidates: pd.DataFrame  # All candidates considered
    risk_metrics: Dict[str, float]
    constraints_satisfied: Dict[str, bool]


class DomainAnalyzer:
    """
    Performs vertical and horizontal analysis for portfolio construction.
    """
    
    # Default sector cache path
    SECTOR_CACHE_PATH = Path("data/sectors.json")
    
    def __init__(self, config: AnalysisConfig, output_dir: str = "output"):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Sector mapping - load from cache or use defaults
        self.sector_map = self._get_sector_mapping()
    
    def _get_sector_mapping(self) -> Dict[str, str]:
        """
        Get sector mapping for tickers.
        
        Priority:
        1. Cached sector data from data/sectors.json (fetched via yfinance)
        2. Fallback hardcoded mapping for common tickers
        
        Run `python scripts/fetch_sector_data.py` to populate the cache.
        """
        # Start with hardcoded fallback mapping
        fallback_mapping = {
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology',
            'AMZN': 'Consumer Cyclical', 'META': 'Technology', 'NVDA': 'Technology',
            'TSLA': 'Consumer Cyclical', 'AMD': 'Technology', 'INTC': 'Technology',
            'CRM': 'Technology', 'ADBE': 'Technology', 'NFLX': 'Communication Services',
            'JPM': 'Financial Services', 'BAC': 'Financial Services', 'WFC': 'Financial Services',
            'GS': 'Financial Services', 'MS': 'Financial Services', 'C': 'Financial Services',
            'V': 'Financial Services', 'MA': 'Financial Services', 'AXP': 'Financial Services',
            'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare',
            'MRK': 'Healthcare', 'ABBV': 'Healthcare', 'LLY': 'Healthcare',
            'PG': 'Consumer Defensive', 'KO': 'Consumer Defensive', 'PEP': 'Consumer Defensive',
            'WMT': 'Consumer Defensive', 'COST': 'Consumer Defensive', 'TGT': 'Consumer Cyclical',
            'HD': 'Consumer Cyclical', 'NKE': 'Consumer Cyclical', 'MCD': 'Consumer Cyclical',
            'DIS': 'Communication Services', 'CMCSA': 'Communication Services',
            'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy',
            'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities',
            'URA': 'Energy', 'NLR': 'Energy', 'URNM': 'Energy',
            'BA': 'Industrials', 'CAT': 'Industrials', 'GE': 'Industrials',
            'MMM': 'Industrials', 'HON': 'Industrials', 'UPS': 'Industrials',
            'MU': 'Technology', 'QCOM': 'Technology', 'AVGO': 'Technology',
        }
        
        # Try to load cached sector data
        if self.SECTOR_CACHE_PATH.exists():
            try:
                with open(self.SECTOR_CACHE_PATH, 'r') as f:
                    cached_mapping = json.load(f)
                
                # Merge: cached data takes precedence over fallback
                merged = {**fallback_mapping, **cached_mapping}
                return merged
            except Exception as e:
                import warnings
                warnings.warn(f"Failed to load sector cache: {e}")
        
        return fallback_mapping
    
    # =========================================================================
    # VERTICAL ANALYSIS (Within Domain)
    # =========================================================================
    
    def compute_value_score(self, df: pd.DataFrame) -> pd.Series:
        """
        Compute value score from PE and PB ratios.
        Lower PE/PB = higher value score.
        Handles multiple column name variations.
        
        IMPORTANT: Stocks without fundamental data are penalized (score = 30)
        rather than getting a neutral score (50). This ensures differentiation
        between stocks with data vs without data.
        """
        # Start with penalty score for missing data (30 instead of 50)
        scores = pd.Series(30.0, index=df.index)
        components = []
        
        # PE rank (lower is better) - check multiple column names
        pe_col = None
        for col in ['pe_ratio', 'pe', 'price_to_earnings']:
            if col in df.columns:
                pe_col = col
                break
        
        if pe_col:
            pe = df[pe_col].replace([np.inf, -np.inf], np.nan)
            pe_valid = pe[(pe > 0) & (pe < 1000)]  # Filter extreme outliers
            
            # Check if we have enough valid values to rank
            if len(pe_valid) > 1:  # Need at least 2 values to rank
                # Rank all values (NaN will remain NaN)
                pe_rank = pe.rank(pct=True, ascending=True, na_option='keep')  # Lower PE = lower rank = higher score
                pe_score = (1 - pe_rank) * 100
                # Fill NaN with penalty score (30) for missing data
                pe_score = pe_score.fillna(30.0)
                components.append(pe_score)
            elif len(pe_valid) == 1:
                # Single value - can't rank, use neutral for that stock
                single_idx = pe_valid.index[0]
                pe_score = pd.Series(30.0, index=df.index)
                pe_score.loc[single_idx] = 50.0  # Neutral for the one with data
                components.append(pe_score)
            else:
                # No valid values - all get penalty score
                components.append(pd.Series(30.0, index=df.index))
        
        # PB rank (lower is better) - check multiple column names
        pb_col = None
        for col in ['pb_ratio', 'pb', 'price_to_book']:
            if col in df.columns:
                pb_col = col
                break
        
        if pb_col:
            pb = df[pb_col].replace([np.inf, -np.inf], np.nan)
            pb_valid = pb[(pb > 0) & (pb < 100)]  # Filter extreme outliers
            
            if len(pb_valid) > 1:
                pb_rank = pb.rank(pct=True, ascending=True, na_option='keep')
                pb_score = (1 - pb_rank) * 100
                pb_score = pb_score.fillna(30.0)  # Penalty for missing
                components.append(pb_score)
            elif len(pb_valid) == 1:
                single_idx = pb_valid.index[0]
                pb_score = pd.Series(30.0, index=df.index)
                pb_score.loc[single_idx] = 50.0
                components.append(pb_score)
            else:
                components.append(pd.Series(30.0, index=df.index))
        
        # Calculate average if we have components
        if components:
            scores = pd.concat(components, axis=1).mean(axis=1)
        else:
            # No value data available - keep penalty score (30)
            import warnings
            warnings.warn(
                "No PE/PB data found for value score calculation. "
                "Stocks without fundamental data will receive penalty score (30) instead of neutral (50)."
            )
        
        return scores.clip(0, 100)
    
    def compute_quality_score(self, df: pd.DataFrame) -> pd.Series:
        """
        Compute quality score from ROE and margins.
        Higher ROE/margins = higher quality score.
        
        IMPORTANT: Stocks without fundamental data are penalized (score = 30)
        rather than getting a neutral score (50). This ensures differentiation
        between stocks with data vs without data.
        """
        # Start with penalty score for missing data (30 instead of 50)
        # This penalizes stocks without fundamental data
        scores = pd.Series(30.0, index=df.index)
        components = []
        has_data_mask = pd.Series(False, index=df.index)
        
        # ROE score - check multiple column names
        roe_col = None
        for col in ['roe', 'return_on_equity', 'roe_ratio']:
            if col in df.columns:
                roe_col = col
                break
        
        if roe_col:
            roe = df[roe_col].replace([np.inf, -np.inf], np.nan)
            roe_valid = roe[(roe > -1.0) & (roe < 10.0)]  # Filter extreme values (-100% to 1000%)
            if len(roe_valid) > 1:
                roe_rank = roe.rank(pct=True, ascending=True)
                roe_score = roe_rank * 100
                # Only fill NaN for stocks that have ROE data but it's invalid
                # Stocks without ROE column get penalty score (30)
                roe_score = roe_score.fillna(30.0)
                components.append(roe_score)
                has_data_mask |= roe.notna() & (roe > -1.0) & (roe < 10.0)
            elif len(roe_valid) == 1:
                # Single value - can't rank, use neutral for that stock
                single_idx = roe_valid.index[0]
                roe_score = pd.Series(30.0, index=df.index)
                roe_score.loc[single_idx] = 50.0  # Neutral for the one with data
                components.append(roe_score)
                has_data_mask.loc[single_idx] = True
        
        # Net margin score - check multiple column names
        net_margin_col = None
        for col in ['net_margin', 'net_margin_pct', 'profit_margin']:
            if col in df.columns:
                net_margin_col = col
                break
        
        if net_margin_col:
            margin = df[net_margin_col].replace([np.inf, -np.inf], np.nan)
            margin_valid = margin[(margin > -1.0) & (margin < 1.0)]  # Filter to -100% to 100%
            if len(margin_valid) > 1:
                margin_rank = margin.rank(pct=True, ascending=True)
                margin_score = margin_rank * 100
                margin_score = margin_score.fillna(30.0)  # Penalty for missing
                components.append(margin_score)
                has_data_mask |= margin.notna() & (margin > -1.0) & (margin < 1.0)
            elif len(margin_valid) == 1:
                single_idx = margin_valid.index[0]
                margin_score = pd.Series(30.0, index=df.index)
                margin_score.loc[single_idx] = 50.0
                components.append(margin_score)
                has_data_mask.loc[single_idx] = True
        
        # Gross margin score - check multiple column names
        gross_margin_col = None
        for col in ['gross_margin', 'gross_margin_pct', 'gross_profit_margin']:
            if col in df.columns:
                gross_margin_col = col
                break
        
        if gross_margin_col:
            gross = df[gross_margin_col].replace([np.inf, -np.inf], np.nan)
            gross_valid = gross[(gross > -1.0) & (gross < 1.0)]  # Filter to -100% to 100%
            if len(gross_valid) > 1:
                gross_rank = gross.rank(pct=True, ascending=True)
                gross_score = gross_rank * 100
                gross_score = gross_score.fillna(30.0)  # Penalty for missing
                components.append(gross_score)
                has_data_mask |= gross.notna() & (gross > -1.0) & (gross < 1.0)
            elif len(gross_valid) == 1:
                single_idx = gross_valid.index[0]
                gross_score = pd.Series(30.0, index=df.index)
                gross_score.loc[single_idx] = 50.0
                components.append(gross_score)
                has_data_mask.loc[single_idx] = True
        
        # Calculate average if we have components
        if components:
            scores = pd.concat(components, axis=1).mean(axis=1)
        else:
            # No quality data available at all - keep penalty score (30)
            import warnings
            warnings.warn(
                "No ROE/margin data found for quality score calculation. "
                "Stocks without fundamental data will receive penalty score (30) instead of neutral (50)."
            )
        
        # Ensure stocks with NO data at all get penalty score
        # Stocks with partial data (some metrics) get calculated score
        # Stocks with complete data get full ranking
        scores = scores.clip(0, 100)
        
        return scores
    
    def _normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize column names to expected format.
        Handles common variations in fundamental data column names.
        """
        result = df.copy()
        rename_map = {}
        
        # PE ratio variations
        if 'pe' in result.columns and 'pe_ratio' not in result.columns:
            rename_map['pe'] = 'pe_ratio'
        if 'price_to_earnings' in result.columns and 'pe_ratio' not in result.columns:
            rename_map['price_to_earnings'] = 'pe_ratio'
        
        # PB ratio variations
        if 'pb' in result.columns and 'pb_ratio' not in result.columns:
            rename_map['pb'] = 'pb_ratio'
        if 'price_to_book' in result.columns and 'pb_ratio' not in result.columns:
            rename_map['price_to_book'] = 'pb_ratio'
        
        # ROE variations
        if 'return_on_equity' in result.columns and 'roe' not in result.columns:
            rename_map['return_on_equity'] = 'roe'
        if 'roe_ratio' in result.columns and 'roe' not in result.columns:
            rename_map['roe_ratio'] = 'roe'
        
        # Margin variations
        if 'net_margin_pct' in result.columns and 'net_margin' not in result.columns:
            rename_map['net_margin_pct'] = 'net_margin'
        if 'profit_margin' in result.columns and 'net_margin' not in result.columns:
            rename_map['profit_margin'] = 'net_margin'
        
        if 'gross_margin_pct' in result.columns and 'gross_margin' not in result.columns:
            rename_map['gross_margin_pct'] = 'gross_margin'
        if 'gross_profit_margin' in result.columns and 'gross_margin' not in result.columns:
            rename_map['gross_profit_margin'] = 'gross_margin'
        
        if rename_map:
            result = result.rename(columns=rename_map)
        
        return result
    
    def compute_domain_score(
        self,
        df: pd.DataFrame,
        model_scores: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """
        Compute composite domain score for each stock.
        
        domain_score = w_m * model_score + w_v * value_score + w_q * quality_score
        
        Args:
            df: DataFrame with fundamentals
            model_scores: Series with model predictions (indexed by ticker)
        
        Returns:
            DataFrame with all scores and composite domain_score
        """
        result = df.copy()
        
        # Normalize column names first
        result = self._normalize_column_names(result)
        
        # Model score (normalize to 0-100 scale)
        if model_scores is not None and 'ticker' in result.columns:
            result['model_score_raw'] = result['ticker'].map(model_scores)
            # Normalize to percentile
            raw = result['model_score_raw']
            result['model_score'] = raw.rank(pct=True) * 100
        elif 'score' in result.columns:
            result['model_score'] = result['score']
        else:
            result['model_score'] = 50.0
        
        # Value score
        result['value_score'] = self.compute_value_score(result)
        
        # Quality score
        result['quality_score'] = self.compute_quality_score(result)
        
        # Composite domain score
        result['domain_score'] = (
            self.config.w_model * result['model_score'] +
            self.config.w_value * result['value_score'] +
            self.config.w_quality * result['quality_score']
        )
        
        return result
    
    def apply_hard_filters(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, int]]:
        """
        Apply hard numeric filters to candidates.
        
        Returns:
            Tuple of (passed_df, filtered_df, filter_reasons)
        """
        passed = df.copy()
        filter_reasons = {}
        
        # Track original count
        original_count = len(passed)
        
        # Filter: minimum ROE
        if 'roe' in passed.columns and self.config.min_roe is not None:
            mask = passed['roe'] >= self.config.min_roe
            failed = (~mask).sum()
            if failed > 0:
                filter_reasons['min_roe'] = int(failed)
            passed = passed[mask]
        
        # Filter: minimum net margin
        if 'net_margin' in passed.columns and self.config.min_net_margin is not None:
            mask = passed['net_margin'] >= self.config.min_net_margin
            failed = (~mask).sum()
            if failed > 0:
                filter_reasons['min_net_margin'] = int(failed)
            passed = passed[mask]
        
        # Filter: maximum debt-to-equity
        if 'debt_to_equity' in passed.columns and self.config.max_debt_to_equity is not None:
            mask = passed['debt_to_equity'] <= self.config.max_debt_to_equity
            failed = (~mask).sum()
            if failed > 0:
                filter_reasons['max_debt_to_equity'] = int(failed)
            passed = passed[mask]
        
        # Filter: minimum market cap
        if 'market_cap' in passed.columns and self.config.min_market_cap is not None:
            mask = passed['market_cap'] >= self.config.min_market_cap
            failed = (~mask).sum()
            if failed > 0:
                filter_reasons['min_market_cap'] = int(failed)
            passed = passed[mask]
        
        # Filter: minimum volume
        if 'avg_volume' in passed.columns and self.config.min_avg_volume is not None:
            mask = passed['avg_volume'] >= self.config.min_avg_volume
            failed = (~mask).sum()
            if failed > 0:
                filter_reasons['min_avg_volume'] = int(failed)
            passed = passed[mask]
        
        # Get filtered out stocks
        filtered = df[~df.index.isin(passed.index)]
        
        return passed, filtered, filter_reasons
    
    def run_vertical_analysis(
        self,
        df: pd.DataFrame,
        date: datetime,
        model_scores: Optional[pd.Series] = None
    ) -> Dict[str, VerticalResult]:
        """
        Run vertical analysis for all sectors.
        
        Args:
            df: DataFrame with all stocks and their features
            date: Rebalance date
            model_scores: Optional model predictions
        
        Returns:
            Dictionary of sector -> VerticalResult
        """
        # Add sector if not present
        if 'sector' not in df.columns and 'ticker' in df.columns:
            df['sector'] = df['ticker'].map(self.sector_map).fillna('Other')
        
        # Compute domain scores
        scored_df = self.compute_domain_score(df, model_scores)
        
        results = {}
        
        for sector in scored_df['sector'].unique():
            sector_df = scored_df[scored_df['sector'] == sector].copy()
            
            # Apply hard filters
            passed, filtered, reasons = self.apply_hard_filters(sector_df)
            
            # Rank by domain score and get top K
            if len(passed) > 0:
                passed = passed.sort_values('domain_score', ascending=False)
                passed['domain_rank'] = range(1, len(passed) + 1)
                candidates = passed.head(self.config.top_k_per_sector)
            else:
                candidates = passed
            
            results[sector] = VerticalResult(
                sector=sector,
                date=date,
                candidates=candidates,
                filtered_out=filtered,
                filter_reasons=reasons
            )
            
            # Export candidates CSV
            if self.config.export_candidates and len(candidates) > 0:
                self._export_vertical_candidates(candidates, date, sector)
        
        return results
    
    def _export_vertical_candidates(
        self,
        candidates: pd.DataFrame,
        date: datetime,
        sector: str
    ):
        """Export vertical candidates to CSV."""
        date_str = date.strftime('%Y%m%d') if isinstance(date, datetime) else str(date)[:10].replace('-', '')
        sector_clean = sector.replace(' ', '_').replace('/', '_')
        
        filename = f"vertical_candidates_{date_str}_{sector_clean}.csv"
        filepath = self.output_dir / filename
        
        # Select columns to export
        export_cols = [
            'ticker', 'sector',
            'model_score', 'value_score', 'quality_score', 'domain_score', 'domain_rank',
            'pe_ratio', 'pb_ratio', 'roe', 'net_margin', 'debt_to_equity',
        ]
        export_cols = [c for c in export_cols if c in candidates.columns]
        
        candidates[export_cols].to_csv(filepath, index=False)
        return filepath
    
    # =========================================================================
    # HORIZONTAL ANALYSIS (Across Domains)
    # =========================================================================
    
    def aggregate_candidates(
        self,
        vertical_results: Dict[str, VerticalResult]
    ) -> pd.DataFrame:
        """Aggregate top candidates from all sectors."""
        all_candidates = []
        
        for sector, result in vertical_results.items():
            if len(result.candidates) > 0:
                all_candidates.append(result.candidates)
        
        if not all_candidates:
            return pd.DataFrame()
        
        return pd.concat(all_candidates, ignore_index=True)
    
    def calculate_correlation_matrix(
        self,
        tickers: List[str],
        returns_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Calculate correlation matrix for given tickers."""
        if returns_df is None or len(returns_df) == 0:
            return pd.DataFrame()
        
        # Pivot to get ticker returns as columns
        if 'ticker' in returns_df.columns:
            pivot = returns_df.pivot_table(
                index='date',
                columns='ticker',
                values='return_1d',
                aggfunc='first'
            )
        else:
            pivot = returns_df
        
        # Filter to requested tickers
        available = [t for t in tickers if t in pivot.columns]
        if len(available) < 2:
            return pd.DataFrame()
        
        return pivot[available].corr()
    
    def calculate_covariance_matrix(
        self,
        tickers: List[str],
        returns_df: pd.DataFrame,
        annualize: bool = True
    ) -> pd.DataFrame:
        """Calculate covariance matrix for given tickers."""
        if returns_df is None or len(returns_df) == 0:
            return pd.DataFrame()
        
        # Pivot to get ticker returns as columns
        if 'ticker' in returns_df.columns:
            pivot = returns_df.pivot_table(
                index='date',
                columns='ticker',
                values='return_1d',
                aggfunc='first'
            )
        else:
            pivot = returns_df
        
        # Filter to requested tickers
        available = [t for t in tickers if t in pivot.columns]
        if len(available) < 2:
            return pd.DataFrame()
        
        cov = pivot[available].cov()
        
        if annualize:
            cov = cov * 252
        
        return cov
    
    def calculate_portfolio_volatility(
        self,
        weights: pd.Series,
        cov_matrix: pd.DataFrame
    ) -> float:
        """Calculate portfolio volatility given weights and covariance matrix."""
        if len(weights) == 0 or len(cov_matrix) == 0:
            return 0.0
        
        # Align weights with covariance matrix
        common = list(set(weights.index) & set(cov_matrix.index))
        if len(common) < 2:
            return weights.map(lambda x: 0.2).mean()  # Default volatility
        
        w = weights[common].values
        w = w / w.sum()  # Normalize
        cov = cov_matrix.loc[common, common].values
        
        portfolio_var = np.dot(w, np.dot(cov, w))
        return np.sqrt(portfolio_var)
    
    def calculate_diversification_score(self, weights: pd.Series) -> float:
        """Calculate diversification score (1 - HHI)."""
        if len(weights) == 0:
            return 0.0
        w = weights / weights.sum()
        hhi = (w ** 2).sum()
        return 1 - hhi
    
    def score_weighted_sizing(
        self,
        candidates: pd.DataFrame,
        score_col: str = 'domain_score'
    ) -> pd.Series:
        """Calculate score-weighted position sizes."""
        if len(candidates) == 0:
            return pd.Series()
        
        scores = candidates[score_col].fillna(0).clip(lower=0)
        total = scores.sum()
        
        if total == 0:
            # Equal weight fallback
            weights = pd.Series(1 / len(candidates), index=candidates.index)
        else:
            weights = scores / total
        
        return weights
    
    def apply_position_constraints(
        self,
        weights: pd.Series,
        candidates: pd.DataFrame
    ) -> pd.Series:
        """Apply position and sector weight constraints."""
        if len(weights) == 0:
            return weights
        
        constrained = weights.copy()
        
        # Apply max position weight
        constrained = constrained.clip(upper=self.config.max_position_weight)
        
        # Apply min position weight (drop if below)
        constrained = constrained[constrained >= self.config.min_position_weight]
        
        # Apply sector constraints
        if 'sector' in candidates.columns and self.config.max_sector_weight is not None:
            sector_map = candidates.set_index(candidates.index)['sector'].to_dict()
            
            for _ in range(10):  # Iterate to converge
                # Calculate sector weights
                sector_weights = {}
                for idx, weight in constrained.items():
                    sector = sector_map.get(idx, 'Other')
                    sector_weights[sector] = sector_weights.get(sector, 0) + weight
                
                # Scale down over-weight sectors
                any_violation = False
                for sector, sw in sector_weights.items():
                    if sw > self.config.max_sector_weight:
                        scale = self.config.max_sector_weight / sw
                        for idx in constrained.index:
                            if sector_map.get(idx) == sector:
                                constrained[idx] *= scale
                        any_violation = True
                
                if not any_violation:
                    break
        
        # Renormalize
        total = constrained.sum()
        if total > 0:
            constrained = constrained / total
        
        return constrained
    
    def evaluate_portfolio(
        self,
        tickers: List[str],
        weights: pd.Series,
        returns_df: pd.DataFrame,
        cov_matrix: pd.DataFrame
    ) -> Dict[str, float]:
        """Evaluate portfolio risk metrics."""
        metrics = {}
        
        # Portfolio volatility
        vol = self.calculate_portfolio_volatility(weights, cov_matrix)
        metrics['volatility'] = vol
        
        # Diversification score
        div = self.calculate_diversification_score(weights)
        metrics['diversification_score'] = div
        
        # Effective N
        if len(weights) > 0:
            hhi = (weights ** 2).sum()
            metrics['effective_n'] = 1 / hhi if hhi > 0 else 0
        
        # Calculate historical metrics if returns available
        if returns_df is not None and len(returns_df) > 0:
            # Get portfolio returns
            if 'ticker' in returns_df.columns:
                pivot = returns_df.pivot_table(
                    index='date',
                    columns='ticker',
                    values='return_1d',
                    aggfunc='first'
                )
            else:
                pivot = returns_df
            
            available = [t for t in tickers if t in pivot.columns]
            if len(available) > 0:
                w = weights.reindex(available).fillna(0)
                w = w / w.sum()
                
                port_returns = (pivot[available] * w).sum(axis=1)
                
                # Sharpe ratio
                ann_return = port_returns.mean() * 252
                ann_vol = port_returns.std() * np.sqrt(252)
                metrics['sharpe_ratio'] = ann_return / ann_vol if ann_vol > 0 else 0
                
                # Sortino ratio
                downside = port_returns[port_returns < 0]
                downside_vol = downside.std() * np.sqrt(252)
                metrics['sortino_ratio'] = ann_return / downside_vol if downside_vol > 0 else 0
                
                # Max drawdown
                cum_returns = (1 + port_returns).cumprod()
                peak = cum_returns.expanding().max()
                drawdown = (cum_returns - peak) / peak
                metrics['max_drawdown'] = drawdown.min()
                
                # VaR and CVaR (95%)
                var_95 = np.percentile(port_returns, 5)
                cvar_95 = port_returns[port_returns <= var_95].mean()
                metrics['var_95'] = var_95
                metrics['cvar_95'] = cvar_95
        
        return metrics
    
    def select_portfolio_heuristic(
        self,
        candidates: pd.DataFrame,
        returns_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """
        Select portfolio using heuristic approach:
        1. Score-weighted sizing
        2. Apply constraints
        3. Select top N by constrained weight
        """
        if len(candidates) == 0:
            return pd.DataFrame(), {}
        
        # Calculate initial weights
        weights = self.score_weighted_sizing(candidates, 'domain_score')
        weights.index = candidates.index
        
        # Apply constraints
        constrained = self.apply_position_constraints(weights, candidates)
        
        # Select top N
        top_indices = constrained.nlargest(self.config.portfolio_size).index
        final_weights = constrained.loc[top_indices]
        final_weights = final_weights / final_weights.sum()  # Renormalize
        
        # Build portfolio DataFrame
        portfolio = candidates.loc[top_indices].copy()
        portfolio['weight'] = final_weights
        portfolio = portfolio.sort_values('weight', ascending=False)
        
        # Calculate correlation/covariance
        tickers = portfolio['ticker'].tolist() if 'ticker' in portfolio.columns else []
        cov_matrix = self.calculate_covariance_matrix(tickers, returns_df)
        
        # Evaluate
        metrics = self.evaluate_portfolio(tickers, final_weights, returns_df, cov_matrix)
        
        return portfolio, metrics
    
    def select_portfolio_optimize(
        self,
        candidates: pd.DataFrame,
        returns_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """
        Select portfolio using optimization:
        1. Enumerate combinations of portfolio_size stocks
        2. For each, calculate weights and risk metrics
        3. Select best by Sharpe subject to constraints
        """
        if len(candidates) < self.config.portfolio_size:
            return self.select_portfolio_heuristic(candidates, returns_df)
        
        tickers = candidates['ticker'].tolist() if 'ticker' in candidates.columns else []
        
        # Calculate covariance matrix for all candidates
        cov_matrix = self.calculate_covariance_matrix(tickers, returns_df)
        
        # Generate combinations
        n_combinations = min(
            self.config.max_combinations,
            len(list(itertools.combinations(range(len(candidates)), self.config.portfolio_size)))
        )
        
        if n_combinations > self.config.max_combinations:
            # Random sampling of combinations
            import random
            all_indices = list(range(len(candidates)))
            combinations = [
                tuple(sorted(random.sample(all_indices, self.config.portfolio_size)))
                for _ in range(self.config.max_combinations)
            ]
            combinations = list(set(combinations))
        else:
            combinations = list(itertools.combinations(range(len(candidates)), self.config.portfolio_size))
        
        best_portfolio = None
        best_metrics = None
        best_score = float('-inf')
        
        for combo in combinations:
            combo_candidates = candidates.iloc[list(combo)]
            
            # Calculate weights
            weights = self.score_weighted_sizing(combo_candidates, 'domain_score')
            weights.index = combo_candidates.index
            constrained = self.apply_position_constraints(weights, combo_candidates)
            
            if len(constrained) < 2:
                continue
            
            # Evaluate
            combo_tickers = combo_candidates['ticker'].tolist() if 'ticker' in combo_candidates.columns else []
            metrics = self.evaluate_portfolio(combo_tickers, constrained, returns_df, cov_matrix)
            
            # Check constraints
            constraints_ok = True
            if metrics.get('max_drawdown', 0) < -self.config.target_max_drawdown:
                constraints_ok = False
            if metrics.get('volatility', 1) > self.config.target_volatility:
                constraints_ok = False
            if metrics.get('diversification_score', 0) < self.config.min_diversification:
                constraints_ok = False
            
            # Score (Sharpe if constraints satisfied, penalized otherwise)
            sharpe = metrics.get('sharpe_ratio', 0)
            if constraints_ok:
                score = sharpe
            else:
                score = sharpe - 10  # Heavy penalty
            
            if score > best_score:
                best_score = score
                best_metrics = metrics
                
                portfolio = combo_candidates.copy()
                portfolio['weight'] = constrained.reindex(portfolio.index).fillna(0)
                best_portfolio = portfolio.sort_values('weight', ascending=False)
        
        if best_portfolio is None:
            return self.select_portfolio_heuristic(candidates, returns_df)
        
        return best_portfolio, best_metrics
    
    def run_horizontal_analysis(
        self,
        vertical_results: Dict[str, VerticalResult],
        returns_df: pd.DataFrame,
        date: datetime
    ) -> HorizontalResult:
        """
        Run horizontal analysis to construct final portfolio.
        
        Args:
            vertical_results: Results from vertical analysis
            returns_df: Historical returns data
            date: Rebalance date
        
        Returns:
            HorizontalResult with portfolio and metrics
        """
        # Aggregate candidates
        candidates = self.aggregate_candidates(vertical_results)
        
        if len(candidates) == 0:
            return HorizontalResult(
                date=date,
                portfolio=pd.DataFrame(),
                candidates=candidates,
                risk_metrics={},
                constraints_satisfied={}
            )
        
        # Select portfolio
        if self.config.selection_method == 'optimize':
            portfolio, metrics = self.select_portfolio_optimize(candidates, returns_df)
        else:
            portfolio, metrics = self.select_portfolio_heuristic(candidates, returns_df)
        
        # Check constraints
        constraints = {
            'max_drawdown': abs(metrics.get('max_drawdown', 0)) <= self.config.target_max_drawdown,
            'volatility': metrics.get('volatility', 1) <= self.config.target_volatility,
            'diversification': metrics.get('diversification_score', 0) >= self.config.min_diversification,
        }
        
        # Export portfolio candidates
        self._export_portfolio_candidates(portfolio, candidates, metrics, date)
        
        return HorizontalResult(
            date=date,
            portfolio=portfolio,
            candidates=candidates,
            risk_metrics=metrics,
            constraints_satisfied=constraints
        )
    
    def _export_portfolio_candidates(
        self,
        portfolio: pd.DataFrame,
        candidates: pd.DataFrame,
        metrics: Dict[str, float],
        date: datetime
    ):
        """Export portfolio candidates and metrics."""
        date_str = date.strftime('%Y%m%d') if isinstance(date, datetime) else str(date)[:10].replace('-', '')
        
        # Export portfolio
        if len(portfolio) > 0:
            portfolio_file = self.output_dir / f"portfolio_candidates_{date_str}.csv"
            export_cols = [
                'ticker', 'sector', 'weight',
                'model_score', 'value_score', 'quality_score', 'domain_score',
                'pe_ratio', 'pb_ratio', 'roe', 'net_margin',
            ]
            export_cols = [c for c in export_cols if c in portfolio.columns]
            portfolio[export_cols].to_csv(portfolio_file, index=False)
        
        # Export metrics
        metrics_file = self.output_dir / f"portfolio_metrics_{date_str}.json"
        with open(metrics_file, 'w') as f:
            json.dump({
                'date': date_str,
                'n_candidates': len(candidates),
                'n_selected': len(portfolio),
                'metrics': metrics,
                'config': {
                    'w_model': self.config.w_model,
                    'w_value': self.config.w_value,
                    'w_quality': self.config.w_quality,
                    'portfolio_size': self.config.portfolio_size,
                    'selection_method': self.config.selection_method,
                }
            }, f, indent=2, default=str)
    
    # =========================================================================
    # FULL ANALYSIS PIPELINE
    # =========================================================================
    
    def run_full_analysis(
        self,
        stocks_df: pd.DataFrame,
        returns_df: pd.DataFrame,
        date: datetime,
        model_scores: Optional[pd.Series] = None
    ) -> Tuple[Dict[str, VerticalResult], HorizontalResult]:
        """
        Run full vertical + horizontal analysis.
        
        Args:
            stocks_df: DataFrame with stock features
            returns_df: Historical returns
            date: Rebalance date
            model_scores: Optional model predictions
        
        Returns:
            Tuple of (vertical_results, horizontal_result)
        """
        print(f"\n{'='*70}")
        print(f"DOMAIN ANALYSIS - {date}")
        print(f"{'='*70}")
        
        # Vertical analysis
        print("\n📊 VERTICAL ANALYSIS (Within Sectors)")
        print("-" * 50)
        vertical_results = self.run_vertical_analysis(stocks_df, date, model_scores)
        
        for sector, result in vertical_results.items():
            n_passed = len(result.candidates)
            n_filtered = len(result.filtered_out)
            print(f"   {sector}: {n_passed} candidates ({n_filtered} filtered)")
            if result.filter_reasons:
                for reason, count in result.filter_reasons.items():
                    print(f"      - {reason}: {count}")
        
        # Horizontal analysis
        print("\n🎯 HORIZONTAL ANALYSIS (Portfolio Construction)")
        print("-" * 50)
        horizontal_result = self.run_horizontal_analysis(vertical_results, returns_df, date)
        
        if len(horizontal_result.portfolio) > 0:
            print(f"   Portfolio size: {len(horizontal_result.portfolio)}")
            print(f"   Selection method: {self.config.selection_method}")
            print("\n   Risk Metrics:")
            for metric, value in horizontal_result.risk_metrics.items():
                if isinstance(value, float):
                    print(f"      {metric}: {value:.4f}")
            
            print("\n   Constraints:")
            for constraint, satisfied in horizontal_result.constraints_satisfied.items():
                status = "✅" if satisfied else "❌"
                print(f"      {constraint}: {status}")
            
            print("\n   Portfolio Holdings:")
            for _, row in horizontal_result.portfolio.iterrows():
                ticker = row.get('ticker', 'N/A')
                weight = row.get('weight', 0) * 100
                sector = row.get('sector', 'N/A')
                domain_score = row.get('domain_score', 0)
                print(f"      {ticker:6s} {weight:5.1f}% | {sector:20s} | Score: {domain_score:.1f}")
        else:
            print("   ⚠️ No portfolio constructed")
        
        return vertical_results, horizontal_result


def main():
    """Run domain analysis from command line."""
    import argparse
    import yaml
    
    parser = argparse.ArgumentParser(description="Run vertical and horizontal domain analysis")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="Config file path")
    parser.add_argument("--output", type=str, default="output", help="Output directory")
    parser.add_argument("--date", type=str, default=None, help="Analysis date (YYYY-MM-DD)")
    parser.add_argument("--run-id", type=str, default=None, help="Specific run ID to analyze (default: latest)")
    
    args = parser.parse_args()
    
    # Load config
    config_path = Path(args.config)
    if config_path.exists():
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)
    else:
        config_dict = {}
    
    analysis_config = AnalysisConfig.from_dict(config_dict)
    
    # Create analyzer
    analyzer = DomainAnalyzer(analysis_config, args.output)
    
    # Load data
    from src.analytics.models import get_db, Run, StockScore
    
    db = get_db("data/analysis.db")
    session = db.get_session()
    
    try:
        # Get run (specific or latest)
        if args.run_id:
            run = session.query(Run).filter_by(run_id=args.run_id).first()
            if not run:
                print(f"❌ Run not found: {args.run_id}")
                return 1
        else:
            run = session.query(Run).order_by(Run.created_at.desc()).first()
            if not run:
                print("❌ No runs found in database")
                return 1
        
        print(f"📥 Loading run: {run.run_id}")
        
        # Get scores
        scores = session.query(StockScore).filter_by(run_id=run.run_id).all()
        if not scores:
            print("❌ No scores found for run")
            return 1
        
        # Convert to DataFrame
        scores_df = pd.DataFrame([s.to_dict() for s in scores])
        
        # Load returns data - try run-specific folder first
        run_folder = Path("output") / f"run_{run.run_id[:16]}"
        returns_path = run_folder / "backtest_returns.csv"
        if not returns_path.exists():
            # Fallback to legacy path
            returns_path = Path("output/backtest_returns.csv")
        
        if returns_path.exists():
            returns_df = pd.read_csv(returns_path, parse_dates=['date'])
        else:
            returns_df = None
        
        # Load price data for returns
        price_path = Path("data/prices.csv")
        if price_path.exists():
            price_df = pd.read_csv(price_path, parse_dates=['date'])
            # Calculate daily returns
            price_df = price_df.sort_values(['ticker', 'date'])
            price_df['return_1d'] = price_df.groupby('ticker')['close'].pct_change(fill_method=None)
        else:
            price_df = None
        
        # Use price data for returns if backtest returns not available
        if returns_df is None and price_df is not None:
            returns_df = price_df[['date', 'ticker', 'return_1d']]
        
        # Run analysis
        analysis_date = datetime.strptime(args.date, '%Y-%m-%d') if args.date else datetime.now()
        
        vertical_results, horizontal_result = analyzer.run_full_analysis(
            stocks_df=scores_df,
            returns_df=returns_df,
            date=analysis_date,
            model_scores=None  # Scores already in DataFrame
        )
        
        print(f"\n{'='*70}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*70}")
        print(f"   Output directory: {args.output}")
        
    finally:
        session.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
