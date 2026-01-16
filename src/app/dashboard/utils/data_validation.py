"""
Enhanced Data Validation
=========================
Pre-flight checks, data quality metrics, and auto-fix suggestions.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DataQualityChecker:
    """Check data quality and provide metrics."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.data_dir = project_root / "data"
    
    def check_price_data(self) -> Dict[str, Any]:
        """Check price data quality."""
        prices_path = self.data_dir / "prices.csv"
        
        if not prices_path.exists():
            return {
                'status': 'missing',
                'completeness': 0.0,
                'freshness_days': None,
                'issues': ['Price data file not found'],
                'suggestions': ['Run price data download']
            }
        
        try:
            df = pd.read_csv(prices_path, nrows=1000)  # Sample for speed
            
            # Check required columns
            required_cols = ['date', 'ticker', 'close']
            missing_cols = [c for c in required_cols if c not in df.columns]
            
            if missing_cols:
                return {
                    'status': 'invalid',
                    'completeness': 0.0,
                    'freshness_days': None,
                    'issues': [f'Missing required columns: {missing_cols}'],
                    'suggestions': ['Re-download price data']
                }
            
            # Check data freshness
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                latest_date = df['date'].max()
                freshness_days = (datetime.now() - latest_date.to_pydatetime()).days
            else:
                freshness_days = None
            
            # Check completeness (non-null values)
            completeness = 1.0 - (df['close'].isna().sum() / len(df))
            
            issues = []
            suggestions = []
            
            if freshness_days and freshness_days > 7:
                issues.append(f'Data is {freshness_days} days old')
                suggestions.append('Update price data')
            
            if completeness < 0.95:
                issues.append(f'Only {completeness*100:.1f}% of data is complete')
                suggestions.append('Check for missing data')
            
            return {
                'status': 'ok' if not issues else 'warning',
                'completeness': completeness,
                'freshness_days': freshness_days,
                'issues': issues,
                'suggestions': suggestions
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'completeness': 0.0,
                'freshness_days': None,
                'issues': [f'Error reading price data: {str(e)}'],
                'suggestions': ['Check file format and permissions']
            }
    
    def check_benchmark_data(self) -> Dict[str, Any]:
        """Check benchmark data quality."""
        benchmark_path = self.data_dir / "benchmark.csv"
        
        if not benchmark_path.exists():
            return {
                'status': 'missing',
                'completeness': 0.0,
                'freshness_days': None,
                'issues': ['Benchmark data file not found'],
                'suggestions': ['Run benchmark data download']
            }
        
        try:
            df = pd.read_csv(benchmark_path, nrows=1000)
            
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                latest_date = df['date'].max()
                freshness_days = (datetime.now() - latest_date.to_pydatetime()).days
            else:
                freshness_days = None
            
            completeness = 1.0 - (df.isna().sum().sum() / (len(df) * len(df.columns)))
            
            issues = []
            suggestions = []
            
            if freshness_days and freshness_days > 7:
                issues.append(f'Data is {freshness_days} days old')
                suggestions.append('Update benchmark data')
            
            return {
                'status': 'ok' if not issues else 'warning',
                'completeness': completeness,
                'freshness_days': freshness_days,
                'issues': issues,
                'suggestions': suggestions
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'completeness': 0.0,
                'freshness_days': None,
                'issues': [f'Error reading benchmark data: {str(e)}'],
                'suggestions': ['Check file format and permissions']
            }
    
    def check_fundamentals_data(self) -> Dict[str, Any]:
        """Check fundamentals data quality."""
        fundamentals_path = self.data_dir / "fundamentals.csv"
        
        if not fundamentals_path.exists():
            return {
                'status': 'missing',
                'completeness': 0.0,
                'ticker_count': 0,
                'issues': ['Fundamentals data file not found'],
                'suggestions': ['Run fundamentals download']
            }
        
        try:
            df = pd.read_csv(fundamentals_path, nrows=10000)  # Sample
            
            if 'ticker' not in df.columns:
                return {
                    'status': 'invalid',
                    'completeness': 0.0,
                    'ticker_count': 0,
                    'issues': ['Missing ticker column'],
                    'suggestions': ['Re-download fundamentals data']
                }
            
            ticker_count = df['ticker'].nunique()
            
            # Check for required fundamental fields
            important_fields = ['pe_ratio', 'pb_ratio', 'roe', 'profit_margin']
            missing_fields = [f for f in important_fields if f not in df.columns]
            
            issues = []
            suggestions = []
            
            if missing_fields:
                issues.append(f'Missing important fields: {missing_fields}')
                suggestions.append('Re-download fundamentals with all fields')
            
            # Check completeness
            if important_fields:
                available_fields = [f for f in important_fields if f in df.columns]
                if available_fields:
                    completeness = 1.0 - (df[available_fields].isna().all(axis=1).sum() / len(df))
                else:
                    completeness = 0.0
            else:
                completeness = 1.0
            
            if completeness < 0.5:
                issues.append(f'Only {completeness*100:.1f}% of stocks have fundamental data')
                suggestions.append('Download fundamentals for more stocks')
            
            return {
                'status': 'ok' if not issues else 'warning',
                'completeness': completeness,
                'ticker_count': ticker_count,
                'issues': issues,
                'suggestions': suggestions
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'completeness': 0.0,
                'ticker_count': 0,
                'issues': [f'Error reading fundamentals: {str(e)}'],
                'suggestions': ['Check file format']
            }
    
    def get_overall_quality(self) -> Dict[str, Any]:
        """Get overall data quality summary."""
        price_quality = self.check_price_data()
        benchmark_quality = self.check_benchmark_data()
        fundamentals_quality = self.check_fundamentals_data()
        
        all_issues = (
            price_quality.get('issues', []) +
            benchmark_quality.get('issues', []) +
            fundamentals_quality.get('issues', [])
        )
        
        all_suggestions = (
            price_quality.get('suggestions', []) +
            benchmark_quality.get('suggestions', []) +
            fundamentals_quality.get('suggestions', [])
        )
        
        # Calculate overall score
        scores = []
        if price_quality['status'] == 'ok':
            scores.append(1.0)
        elif price_quality['status'] == 'warning':
            scores.append(0.5)
        else:
            scores.append(0.0)
        
        if benchmark_quality['status'] == 'ok':
            scores.append(1.0)
        elif benchmark_quality['status'] == 'warning':
            scores.append(0.5)
        else:
            scores.append(0.0)
        
        if fundamentals_quality['status'] == 'ok':
            scores.append(1.0)
        elif fundamentals_quality['status'] == 'warning':
            scores.append(0.5)
        else:
            scores.append(0.0)
        
        overall_score = sum(scores) / len(scores) if scores else 0.0
        
        return {
            'overall_score': overall_score,
            'price_data': price_quality,
            'benchmark_data': benchmark_quality,
            'fundamentals_data': fundamentals_quality,
            'total_issues': len(all_issues),
            'issues': all_issues,
            'suggestions': list(set(all_suggestions))  # Deduplicate
        }


def validate_before_analysis(
    required_data: List[str] = None,
    min_data_freshness_days: int = 30
) -> Tuple[bool, List[str]]:
    """
    Pre-flight check before running analysis.
    
    Args:
        required_data: List of required data types ('prices', 'benchmark', 'fundamentals')
        min_data_freshness_days: Maximum age of data in days
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    if required_data is None:
        required_data = ['prices', 'benchmark']
    
    from ..utils import get_project_root
    checker = DataQualityChecker(get_project_root())
    
    issues = []
    
    if 'prices' in required_data:
        price_quality = checker.check_price_data()
        if price_quality['status'] == 'missing':
            issues.append("Price data is missing")
        elif price_quality['status'] == 'error':
            issues.append(f"Price data error: {price_quality['issues'][0]}")
        elif price_quality.get('freshness_days') and price_quality['freshness_days'] > min_data_freshness_days:
            issues.append(f"Price data is {price_quality['freshness_days']} days old (max: {min_data_freshness_days})")
    
    if 'benchmark' in required_data:
        benchmark_quality = checker.check_benchmark_data()
        if benchmark_quality['status'] == 'missing':
            issues.append("Benchmark data is missing")
        elif benchmark_quality['status'] == 'error':
            issues.append(f"Benchmark data error: {benchmark_quality['issues'][0]}")
        elif benchmark_quality.get('freshness_days') and benchmark_quality['freshness_days'] > min_data_freshness_days:
            issues.append(f"Benchmark data is {benchmark_quality['freshness_days']} days old (max: {min_data_freshness_days})")
    
    if 'fundamentals' in required_data:
        fundamentals_quality = checker.check_fundamentals_data()
        if fundamentals_quality['status'] == 'missing':
            issues.append("Fundamentals data is missing")
        elif fundamentals_quality['status'] == 'error':
            issues.append(f"Fundamentals data error: {fundamentals_quality['issues'][0]}")
        elif fundamentals_quality.get('completeness', 0) < 0.5:
            issues.append(f"Only {fundamentals_quality['completeness']*100:.1f}% of stocks have fundamentals")
    
    return len(issues) == 0, issues
