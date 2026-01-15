"""
Data Completeness Validation
===========================
Validate that all required data is available before running analyses.
"""

from typing import Dict, List, Optional, Any, Set
import pandas as pd
import numpy as np
from enum import Enum


class DataRequirement(Enum):
    """Data requirements for different analyses."""
    PORTFOLIO_RETURNS = "portfolio_returns"
    PORTFOLIO_WEIGHTS = "portfolio_weights"
    STOCK_RETURNS = "stock_returns"
    STOCK_FEATURES = "stock_features"
    FUNDAMENTAL_DATA = "fundamental_data"
    BENCHMARK_DATA = "benchmark_data"
    SECTOR_MAPPING = "sector_mapping"
    FACTOR_DATA = "factor_data"


class AnalysisRequirement(Enum):
    """Analysis types and their data requirements."""
    ATTRIBUTION = [
        DataRequirement.PORTFOLIO_RETURNS,
        DataRequirement.PORTFOLIO_WEIGHTS,
        DataRequirement.STOCK_RETURNS,
        DataRequirement.SECTOR_MAPPING
    ]
    BENCHMARK_COMPARISON = [
        DataRequirement.PORTFOLIO_RETURNS,
        # BENCHMARK_DATA is optional - benchmark comparison can fetch from yfinance API
    ]
    FACTOR_EXPOSURE = [
        DataRequirement.PORTFOLIO_WEIGHTS,
        DataRequirement.STOCK_FEATURES
    ]
    REBALANCING = [
        DataRequirement.PORTFOLIO_WEIGHTS
    ]
    STYLE = [
        DataRequirement.PORTFOLIO_WEIGHTS,
        DataRequirement.FUNDAMENTAL_DATA
    ]


class DataCompletenessChecker:
    """Check data completeness before running analyses."""
    
    def __init__(self):
        self.requirements = {
            'attribution': AnalysisRequirement.ATTRIBUTION.value,
            'benchmark_comparison': AnalysisRequirement.BENCHMARK_COMPARISON.value,
            'factor_exposure': AnalysisRequirement.FACTOR_EXPOSURE.value,
            'rebalancing': AnalysisRequirement.REBALANCING.value,
            'style': AnalysisRequirement.STYLE.value
        }
    
    def check_data_completeness(
        self,
        portfolio_data: Dict[str, Any],
        stock_data: Dict[str, Any],
        benchmark_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check if all required data is available.
        
        Args:
            portfolio_data: Portfolio data dictionary
            stock_data: Stock data dictionary
            benchmark_data: Optional benchmark data
            
        Returns:
            Dictionary with completeness check results
        """
        results = {
            'is_complete': True,
            'missing_data': {},
            'warnings': [],
            'errors': [],
            'analysis_status': {}
        }
        
        # Check each analysis requirement
        for analysis_type, requirements in self.requirements.items():
            analysis_status = self._check_analysis_requirements(
                analysis_type,
                requirements,
                portfolio_data,
                stock_data,
                benchmark_data
            )
            
            results['analysis_status'][analysis_type] = analysis_status
            
            if not analysis_status['can_run']:
                results['is_complete'] = False
                if analysis_status['severity'] == 'error':
                    results['errors'].append({
                        'analysis': analysis_type,
                        'missing': analysis_status['missing'],
                        'message': analysis_status['message']
                    })
                else:
                    results['warnings'].append({
                        'analysis': analysis_type,
                        'missing': analysis_status['missing'],
                        'message': analysis_status['message']
                    })
        
        return results
    
    def _check_analysis_requirements(
        self,
        analysis_type: str,
        requirements: List[DataRequirement],
        portfolio_data: Dict[str, Any],
        stock_data: Dict[str, Any],
        benchmark_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Check requirements for a specific analysis."""
        missing = []
        can_run = True
        severity = 'warning'
        message = ""
        
        for requirement in requirements:
            if not self._check_requirement(
                requirement,
                portfolio_data,
                stock_data,
                benchmark_data
            ):
                missing.append(requirement.value)
                can_run = False
        
        # Determine severity and message
        if missing:
            if analysis_type in ['attribution', 'benchmark_comparison']:
                severity = 'error'
                message = f"Cannot run {analysis_type}: Missing critical data ({', '.join(missing)})"
            else:
                severity = 'warning'
                message = f"{analysis_type} may be incomplete: Missing data ({', '.join(missing)})"
        else:
            message = f"{analysis_type} can run: All required data available"
        
        return {
            'can_run': can_run,
            'missing': missing,
            'severity': severity,
            'message': message
        }
    
    def _check_requirement(
        self,
        requirement: DataRequirement,
        portfolio_data: Dict[str, Any],
        stock_data: Dict[str, Any],
        benchmark_data: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if a specific requirement is met."""
        if requirement == DataRequirement.PORTFOLIO_RETURNS:
            returns = portfolio_data.get('returns')
            return returns is not None and len(returns) > 0
        
        elif requirement == DataRequirement.PORTFOLIO_WEIGHTS:
            weights = portfolio_data.get('weights')
            return weights is not None and not weights.empty if hasattr(weights, 'empty') else weights is not None
        
        elif requirement == DataRequirement.STOCK_RETURNS:
            # Check if stock returns are available from multiple sources
            # 1. Check stock_data directly
            stock_returns = stock_data.get('returns')
            if stock_returns is not None:
                if hasattr(stock_returns, 'empty'):
                    return not stock_returns.empty
                return len(stock_returns) > 0
            
            # 2. Check portfolio_data (may have been loaded from redundant sources)
            stock_returns = portfolio_data.get('stock_returns')
            if stock_returns is not None:
                if hasattr(stock_returns, 'empty'):
                    return not stock_returns.empty
                return len(stock_returns) > 0
            
            # 3. Check if we can derive from stock features
            if isinstance(stock_data, pd.DataFrame):
                if 'return' in stock_data.columns or 'returns' in stock_data.columns:
                    return True
            
            return False
        
        elif requirement == DataRequirement.STOCK_FEATURES:
            # Check if stock features/scores are available
            if isinstance(stock_data, pd.DataFrame):
                # stock_data is a DataFrame directly
                return not stock_data.empty if hasattr(stock_data, 'empty') else len(stock_data) > 0
            elif isinstance(stock_data, dict):
                # Check for features or data keys
                features = stock_data.get('features')
                data = stock_data.get('data')
                
                # Check if we have a DataFrame
                if isinstance(features, pd.DataFrame):
                    return not features.empty
                elif isinstance(data, pd.DataFrame):
                    return not data.empty
                elif features is not None:
                    return len(features) > 0 if hasattr(features, '__len__') else True
                elif data is not None:
                    return len(data) > 0 if hasattr(data, '__len__') else True
                else:
                    # Check if dict itself has content
                    return len(stock_data) > 0
            return False
        
        elif requirement == DataRequirement.FUNDAMENTAL_DATA:
            # Check if fundamental data is available (PE ratios, etc.)
            if isinstance(stock_data, dict):
                # Check for fundamental fields
                fundamental_fields = ['pe_ratio', 'pb_ratio', 'roe', 'net_margin', 'portfolio_pe']
                has_fundamentals = any(
                    field in stock_data or 
                    (isinstance(stock_data.get('data'), pd.DataFrame) and field in stock_data['data'].columns)
                    for field in fundamental_fields
                )
                if has_fundamentals:
                    # Check if values are non-zero (not just placeholders)
                    if isinstance(stock_data.get('data'), pd.DataFrame):
                        df = stock_data['data']
                        if 'pe_ratio' in df.columns:
                            non_zero_pe = (df['pe_ratio'] > 0).any()
                            return non_zero_pe
                    return True
            return False
        
        elif requirement == DataRequirement.BENCHMARK_DATA:
            if benchmark_data is None:
                return False
            # Check if benchmark returns are available
            if isinstance(benchmark_data, dict):
                # Check for overlapping dates with portfolio
                portfolio_returns = portfolio_data.get('returns')
                if portfolio_returns is None:
                    return False
                
                # Check if any benchmark has overlapping dates
                for bench_name, bench_data in benchmark_data.items():
                    if isinstance(bench_data, dict):
                        bench_returns = bench_data.get('returns')
                        if bench_returns is not None:
                            if hasattr(portfolio_returns, 'index') and hasattr(bench_returns, 'index'):
                                overlap = portfolio_returns.index.intersection(bench_returns.index)
                                if len(overlap) > 0:
                                    return True
            return False
        
        elif requirement == DataRequirement.SECTOR_MAPPING:
            sector_mapping = portfolio_data.get('sector_mapping') or stock_data.get('sector_mapping')
            return sector_mapping is not None and len(sector_mapping) > 0
        
        elif requirement == DataRequirement.FACTOR_DATA:
            # Factor data is optional for most analyses
            return True
        
        return False
    
    def get_fix_instructions(self, missing_data: List[str]) -> List[str]:
        """Get instructions on how to fix missing data."""
        instructions = []
        
        for data_type in missing_data:
            if data_type == 'stock_returns':
                instructions.append(
                    "Stock Returns: Individual stock returns are needed for performance attribution. "
                    "These can be calculated from price data or loaded from backtest results."
                )
            elif data_type == 'fundamental_data':
                instructions.append(
                    "Fundamental Data: Run 'python scripts/download_fundamentals.py --watchlist <watchlist>' "
                    "to download PE ratios, ROE, margins, and other fundamental metrics."
                )
            elif data_type == 'benchmark_data':
                instructions.append(
                    "Benchmark Data: Ensure benchmark data (SPY, QQQ) is available for the portfolio's date range. "
                    "Check if benchmark data needs to be downloaded or updated."
                )
            elif data_type == 'sector_mapping':
                instructions.append(
                    "Sector Mapping: Ensure portfolio holdings have sector information. "
                    "This is usually included in portfolio output files."
                )
            elif data_type == 'portfolio_returns':
                instructions.append(
                    "Portfolio Returns: Ensure backtest_returns.csv or equity_curve.csv exists in the run output folder."
                )
            elif data_type == 'portfolio_weights':
                instructions.append(
                    "Portfolio Weights: Ensure backtest_positions.csv or portfolio_*.csv files exist in the run output folder."
                )
        
        return instructions
    
    def generate_report(self, completeness_results: Dict[str, Any]) -> str:
        """Generate a human-readable report."""
        report = []
        report.append("=" * 70)
        report.append("DATA COMPLETENESS CHECK")
        report.append("=" * 70)
        report.append("")
        
        # Overall status
        if completeness_results['is_complete']:
            report.append("✅ All required data is available")
        else:
            report.append("⚠️  Some required data is missing")
        report.append("")
        
        # Analysis status
        report.append("Analysis Status:")
        report.append("-" * 70)
        for analysis_type, status in completeness_results['analysis_status'].items():
            if status['can_run']:
                report.append(f"  ✅ {analysis_type}: Can run")
            else:
                icon = "❌" if status['severity'] == 'error' else "⚠️"
                report.append(f"  {icon} {analysis_type}: {status['message']}")
        report.append("")
        
        # Errors
        if completeness_results['errors']:
            report.append("❌ CRITICAL ISSUES:")
            report.append("-" * 70)
            for error in completeness_results['errors']:
                report.append(f"  {error['analysis']}: {error['message']}")
                missing = error['missing']
                if missing:
                    instructions = self.get_fix_instructions(missing)
                    for instruction in instructions:
                        report.append(f"    → {instruction}")
            report.append("")
        
        # Warnings
        if completeness_results['warnings']:
            report.append("⚠️  WARNINGS:")
            report.append("-" * 70)
            for warning in completeness_results['warnings']:
                report.append(f"  {warning['analysis']}: {warning['message']}")
                missing = warning['missing']
                if missing:
                    instructions = self.get_fix_instructions(missing)
                    for instruction in instructions:
                        report.append(f"    → {instruction}")
            report.append("")
        
        # Recommendations
        if not completeness_results['is_complete']:
            report.append("RECOMMENDATIONS:")
            report.append("-" * 70)
            all_missing = set()
            for error in completeness_results['errors']:
                all_missing.update(error['missing'])
            for warning in completeness_results['warnings']:
                all_missing.update(warning['missing'])
            
            instructions = self.get_fix_instructions(list(all_missing))
            for i, instruction in enumerate(instructions, 1):
                report.append(f"  {i}. {instruction}")
            report.append("")
        
        report.append("=" * 70)
        return "\n".join(report)
