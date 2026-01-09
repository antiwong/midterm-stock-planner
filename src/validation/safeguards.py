"""
Backtest Safeguards Module

Automated validation checks that fail a run if critical criteria aren't met.
These safeguards ensure data integrity and portfolio construction correctness
before results are used for recommendations.

Usage:
    from src.validation.safeguards import validate_backtest_run, ValidationError
    
    try:
        validate_backtest_run(run_dir, config, risk_profile='moderate')
    except ValidationError as e:
        print(f"Run failed validation: {e}")
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


class ValidationError(Exception):
    """Raised when a backtest run fails validation."""
    pass


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    check_name: str
    passed: bool
    message: str
    severity: str = "error"  # "error" fails the run, "warning" logs but continues
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Complete validation report for a run."""
    run_id: str
    passed: bool
    checks: List[ValidationResult] = field(default_factory=list)
    
    def add_check(self, result: ValidationResult):
        self.checks.append(result)
        if not result.passed and result.severity == "error":
            self.passed = False
    
    def to_dict(self) -> Dict:
        return {
            'run_id': self.run_id,
            'passed': self.passed,
            'checks': [
                {
                    'check': c.check_name,
                    'passed': c.passed,
                    'message': c.message,
                    'severity': c.severity,
                    'details': c.details
                }
                for c in self.checks
            ]
        }
    
    def __str__(self) -> str:
        lines = [f"Validation Report: {self.run_id}"]
        lines.append("=" * 60)
        for check in self.checks:
            status = "✅ PASS" if check.passed else ("❌ FAIL" if check.severity == "error" else "⚠️ WARN")
            lines.append(f"{status} {check.check_name}: {check.message}")
        lines.append("=" * 60)
        lines.append(f"Overall: {'PASSED' if self.passed else 'FAILED'}")
        return "\n".join(lines)


# Risk profile bounds for validation
RISK_PROFILE_BOUNDS = {
    'conservative': {
        'max_volatility': 0.25,      # 25% annual vol
        'max_drawdown': -0.20,       # -20% max DD
        'min_sharpe': 0.3,           # Minimum Sharpe
        'max_sector_weight': 0.35,   # 35% max sector
    },
    'moderate': {
        'max_volatility': 0.50,      # 50% annual vol
        'max_drawdown': -0.40,       # -40% max DD
        'min_sharpe': 0.0,           # Allow negative Sharpe
        'max_sector_weight': 0.50,   # 50% max sector
    },
    'aggressive': {
        'max_volatility': 0.80,      # 80% annual vol
        'max_drawdown': -0.70,       # -70% max DD
        'min_sharpe': -1.0,          # Allow poor Sharpe
        'max_sector_weight': 0.70,   # 70% max sector
    },
}


def check_weights_sum_to_one(
    positions: pd.DataFrame,
    tolerance: float = 1e-6
) -> ValidationResult:
    """
    Check that portfolio weights sum to 1.0 for each rebalance date.
    
    CRITICAL: This is a fundamental portfolio constraint.
    """
    weight_sums = positions.groupby('date')['weight'].sum()
    errors = weight_sums[abs(weight_sums - 1.0) >= tolerance]
    
    if len(errors) == 0:
        return ValidationResult(
            check_name="weights_sum_to_one",
            passed=True,
            message=f"All {len(weight_sums)} dates have weights summing to 1.0",
            details={'dates_checked': len(weight_sums)}
        )
    else:
        return ValidationResult(
            check_name="weights_sum_to_one",
            passed=False,
            message=f"{len(errors)} dates have weight sum errors",
            severity="error",
            details={
                'error_dates': {str(d): float(w) for d, w in errors.items()},
                'tolerance': tolerance
            }
        )


def check_position_count(
    positions: pd.DataFrame,
    expected_count: int
) -> ValidationResult:
    """
    Check that each rebalance date has exactly the expected number of positions.
    """
    counts = positions.groupby('date')['ticker'].count()
    errors = counts[counts != expected_count]
    
    if len(errors) == 0:
        return ValidationResult(
            check_name="position_count",
            passed=True,
            message=f"All {len(counts)} dates have exactly {expected_count} positions",
            details={'expected': expected_count, 'dates_checked': len(counts)}
        )
    else:
        return ValidationResult(
            check_name="position_count",
            passed=False,
            message=f"{len(errors)} dates have incorrect position count (expected {expected_count})",
            severity="error",
            details={
                'expected': expected_count,
                'error_dates': {str(d): int(c) for d, c in errors.items()}
            }
        )


def check_volatility_bounds(
    metrics: Dict,
    risk_profile: str = 'moderate'
) -> ValidationResult:
    """
    Check that annualized volatility is within bounds for the risk profile.
    """
    bounds = RISK_PROFILE_BOUNDS.get(risk_profile, RISK_PROFILE_BOUNDS['moderate'])
    max_vol = bounds['max_volatility']
    actual_vol = metrics.get('volatility', 0)
    
    if actual_vol <= max_vol:
        return ValidationResult(
            check_name="volatility_bounds",
            passed=True,
            message=f"Volatility {actual_vol*100:.1f}% within {risk_profile} limit ({max_vol*100:.0f}%)",
            details={'actual': actual_vol, 'limit': max_vol, 'profile': risk_profile}
        )
    else:
        return ValidationResult(
            check_name="volatility_bounds",
            passed=False,
            message=f"Volatility {actual_vol*100:.1f}% exceeds {risk_profile} limit ({max_vol*100:.0f}%)",
            severity="warning",  # Warning, not error - user may accept higher vol
            details={'actual': actual_vol, 'limit': max_vol, 'profile': risk_profile}
        )


def check_drawdown_bounds(
    metrics: Dict,
    risk_profile: str = 'moderate'
) -> ValidationResult:
    """
    Check that max drawdown is within bounds for the risk profile.
    """
    bounds = RISK_PROFILE_BOUNDS.get(risk_profile, RISK_PROFILE_BOUNDS['moderate'])
    max_dd_limit = bounds['max_drawdown']
    actual_dd = metrics.get('max_drawdown', 0)
    
    # More negative = worse drawdown
    if actual_dd >= max_dd_limit:
        return ValidationResult(
            check_name="drawdown_bounds",
            passed=True,
            message=f"Max drawdown {actual_dd*100:.1f}% within {risk_profile} limit ({max_dd_limit*100:.0f}%)",
            details={'actual': actual_dd, 'limit': max_dd_limit, 'profile': risk_profile}
        )
    else:
        return ValidationResult(
            check_name="drawdown_bounds",
            passed=False,
            message=f"Max drawdown {actual_dd*100:.1f}% exceeds {risk_profile} limit ({max_dd_limit*100:.0f}%)",
            severity="warning",
            details={'actual': actual_dd, 'limit': max_dd_limit, 'profile': risk_profile}
        )


def check_return_sanity(
    metrics: Dict
) -> ValidationResult:
    """
    Check that returns are within sane bounds (not corrupted data).
    """
    total_return = metrics.get('total_return', 0)
    ann_return = metrics.get('annualized_return', 0)
    
    issues = []
    
    # Total return sanity: -99% to +5000% over multi-year period
    if total_return < -0.99:
        issues.append(f"Total return {total_return*100:.1f}% < -99%")
    if total_return > 50:  # 5000%
        issues.append(f"Total return {total_return*100:.1f}% > 5000% (suspiciously high)")
    
    # Annualized return sanity: -90% to +200%
    if ann_return < -0.90:
        issues.append(f"Annualized return {ann_return*100:.1f}% < -90%")
    if ann_return > 2.0:  # 200%
        issues.append(f"Annualized return {ann_return*100:.1f}% > 200% (verify data)")
    
    if not issues:
        return ValidationResult(
            check_name="return_sanity",
            passed=True,
            message=f"Returns within sane bounds (Total: {total_return*100:.1f}%, Ann: {ann_return*100:.1f}%)",
            details={'total_return': total_return, 'annualized_return': ann_return}
        )
    else:
        return ValidationResult(
            check_name="return_sanity",
            passed=False,
            message=f"Return sanity check failed: {'; '.join(issues)}",
            severity="error",
            details={'issues': issues, 'total_return': total_return, 'annualized_return': ann_return}
        )


def check_sector_concentration(
    positions: pd.DataFrame,
    sector_map: Dict[str, str],
    risk_profile: str = 'moderate'
) -> ValidationResult:
    """
    Check that no sector exceeds concentration limit for the risk profile.
    """
    bounds = RISK_PROFILE_BOUNDS.get(risk_profile, RISK_PROFILE_BOUNDS['moderate'])
    max_sector = bounds['max_sector_weight']
    
    # Add sector to positions
    positions = positions.copy()
    positions['sector'] = positions['ticker'].map(sector_map).fillna('Other')
    
    # Check each date
    violations = []
    for date in positions['date'].unique():
        date_pos = positions[positions['date'] == date]
        sector_weights = date_pos.groupby('sector')['weight'].sum()
        
        for sector, weight in sector_weights.items():
            if weight > max_sector:
                violations.append({
                    'date': str(date.date() if hasattr(date, 'date') else date),
                    'sector': sector,
                    'weight': float(weight)
                })
    
    if not violations:
        return ValidationResult(
            check_name="sector_concentration",
            passed=True,
            message=f"No sector exceeds {max_sector*100:.0f}% limit ({risk_profile} profile)",
            details={'limit': max_sector, 'profile': risk_profile}
        )
    else:
        return ValidationResult(
            check_name="sector_concentration",
            passed=False,
            message=f"{len(violations)} sector concentration violations",
            severity="warning",
            details={'limit': max_sector, 'violations': violations[:10]}  # Limit to first 10
        )


def check_factor_concentration(
    enriched_df: pd.DataFrame,
    max_factor_weight: float = 0.50
) -> ValidationResult:
    """
    Check that no single factor dominates portfolio risk.
    
    Uses score columns to estimate factor exposure.
    """
    factor_cols = ['value_score', 'quality_score', 'momentum_score', 'tech_score', 'model_score']
    available_factors = [c for c in factor_cols if c in enriched_df.columns]
    
    if not available_factors:
        return ValidationResult(
            check_name="factor_concentration",
            passed=True,
            message="No factor columns available for concentration check",
            severity="warning",
            details={'available_factors': []}
        )
    
    # Calculate factor contribution to overall score variance
    factor_contributions = {}
    
    for factor in available_factors:
        if enriched_df[factor].std() > 0:
            # Normalize contribution
            factor_var = enriched_df[factor].var()
            factor_contributions[factor] = factor_var
    
    total_var = sum(factor_contributions.values())
    if total_var == 0:
        return ValidationResult(
            check_name="factor_concentration",
            passed=True,
            message="Factor variance is zero (all equal scores)",
            details={'factor_contributions': {}}
        )
    
    # Normalize to percentages
    factor_pcts = {f: v/total_var for f, v in factor_contributions.items()}
    max_factor = max(factor_pcts.values()) if factor_pcts else 0
    dominant_factor = max(factor_pcts, key=factor_pcts.get) if factor_pcts else None
    
    if max_factor <= max_factor_weight:
        return ValidationResult(
            check_name="factor_concentration",
            passed=True,
            message=f"No factor exceeds {max_factor_weight*100:.0f}% contribution",
            details={'factor_contributions': factor_pcts, 'max_factor': dominant_factor, 'max_pct': max_factor}
        )
    else:
        return ValidationResult(
            check_name="factor_concentration",
            passed=False,
            message=f"Factor '{dominant_factor}' contributes {max_factor*100:.1f}% (limit: {max_factor_weight*100:.0f}%)",
            severity="warning",
            details={'factor_contributions': factor_pcts, 'max_factor': dominant_factor, 'max_pct': max_factor}
        )


def check_no_negative_weights(positions: pd.DataFrame) -> ValidationResult:
    """Check that all weights are non-negative (long-only portfolio)."""
    negative = positions[positions['weight'] < 0]
    
    if len(negative) == 0:
        return ValidationResult(
            check_name="no_negative_weights",
            passed=True,
            message="All weights are non-negative (long-only)",
            details={}
        )
    else:
        return ValidationResult(
            check_name="no_negative_weights",
            passed=False,
            message=f"{len(negative)} positions have negative weights",
            severity="error",
            details={'negative_positions': negative[['date', 'ticker', 'weight']].to_dict('records')[:10]}
        )


def check_no_excessive_single_position(
    positions: pd.DataFrame,
    max_weight: float = 0.50
) -> ValidationResult:
    """Check that no single position exceeds concentration limit."""
    excessive = positions[positions['weight'] > max_weight]
    
    if len(excessive) == 0:
        return ValidationResult(
            check_name="no_excessive_position",
            passed=True,
            message=f"No single position exceeds {max_weight*100:.0f}%",
            details={'limit': max_weight}
        )
    else:
        return ValidationResult(
            check_name="no_excessive_position",
            passed=False,
            message=f"{len(excessive)} positions exceed {max_weight*100:.0f}% weight",
            severity="error",
            details={'limit': max_weight, 'excessive': excessive[['date', 'ticker', 'weight']].to_dict('records')[:10]}
        )


def validate_backtest_run(
    run_dir: Path,
    config: Dict,
    risk_profile: str = 'moderate',
    sector_map: Optional[Dict[str, str]] = None,
    strict: bool = True
) -> ValidationReport:
    """
    Run all validation checks on a backtest run.
    
    Args:
        run_dir: Path to the run output directory
        config: Configuration dictionary
        risk_profile: Risk profile for bounds checking
        sector_map: Ticker to sector mapping
        strict: If True, raise ValidationError on failure
        
    Returns:
        ValidationReport with all check results
        
    Raises:
        ValidationError: If strict=True and any critical check fails
    """
    run_dir = Path(run_dir)
    run_id = run_dir.name
    
    report = ValidationReport(run_id=run_id, passed=True)
    
    # Load required files
    positions_file = run_dir / 'backtest_positions.csv'
    metrics_file = run_dir / 'backtest_metrics.json'
    
    if not positions_file.exists():
        raise ValidationError(f"Missing backtest_positions.csv in {run_dir}")
    if not metrics_file.exists():
        raise ValidationError(f"Missing backtest_metrics.json in {run_dir}")
    
    positions = pd.read_csv(positions_file, parse_dates=['date'])
    with open(metrics_file) as f:
        metrics = json.load(f)
    
    # Get expected position count from config
    backtest_config = config.get('backtest', {})
    expected_top_n = backtest_config.get('top_n')
    
    # Load enriched data if available
    enriched_files = list(run_dir.glob('portfolio_enriched_*.csv'))
    enriched_df = pd.read_csv(enriched_files[0]) if enriched_files else None
    
    # Load sector map if not provided
    if sector_map is None:
        sector_file = Path('data/sectors.csv')
        if sector_file.exists():
            sectors = pd.read_csv(sector_file)
            sector_map = dict(zip(sectors['ticker'], sectors['sector']))
        else:
            sector_map = {}
    
    # Run all checks
    # Critical checks (errors)
    report.add_check(check_weights_sum_to_one(positions))
    report.add_check(check_no_negative_weights(positions))
    report.add_check(check_no_excessive_single_position(positions))
    report.add_check(check_return_sanity(metrics))
    
    if expected_top_n:
        report.add_check(check_position_count(positions, expected_top_n))
    
    # Profile-based checks (warnings)
    report.add_check(check_volatility_bounds(metrics, risk_profile))
    report.add_check(check_drawdown_bounds(metrics, risk_profile))
    
    if sector_map:
        report.add_check(check_sector_concentration(positions, sector_map, risk_profile))
    
    if enriched_df is not None:
        report.add_check(check_factor_concentration(enriched_df))
    
    # Save validation report
    report_file = run_dir / 'validation_report.json'
    with open(report_file, 'w') as f:
        json.dump(report.to_dict(), f, indent=2, default=str)
    
    # Raise error if strict and failed
    if strict and not report.passed:
        failed_checks = [c for c in report.checks if not c.passed and c.severity == "error"]
        error_msg = "; ".join([f"{c.check_name}: {c.message}" for c in failed_checks])
        raise ValidationError(f"Backtest validation failed: {error_msg}")
    
    return report


def validate_before_recommendations(
    run_dir: Path,
    config: Dict,
    risk_profile: str = 'moderate'
) -> bool:
    """
    Quick validation check before generating recommendations.
    
    Returns True if safe to proceed, False otherwise.
    """
    try:
        report = validate_backtest_run(
            run_dir=run_dir,
            config=config,
            risk_profile=risk_profile,
            strict=False
        )
        
        # Check critical failures only
        critical_failures = [
            c for c in report.checks 
            if not c.passed and c.severity == "error"
        ]
        
        return len(critical_failures) == 0
        
    except Exception as e:
        print(f"Validation error: {e}")
        return False


# CLI interface
if __name__ == "__main__":
    import argparse
    import yaml
    
    parser = argparse.ArgumentParser(description="Validate a backtest run")
    parser.add_argument("run_dir", help="Path to run directory")
    parser.add_argument("--config", default="config/config.yaml", help="Config file path")
    parser.add_argument("--profile", default="moderate", choices=['conservative', 'moderate', 'aggressive'])
    parser.add_argument("--strict", action="store_true", help="Fail on any error")
    
    args = parser.parse_args()
    
    with open(args.config) as f:
        config = yaml.safe_load(f)
    
    try:
        report = validate_backtest_run(
            run_dir=Path(args.run_dir),
            config=config,
            risk_profile=args.profile,
            strict=args.strict
        )
        print(report)
        
        if report.passed:
            print("\n✅ Run is valid for recommendations")
        else:
            print("\n⚠️ Run has validation issues - review before using")
            
    except ValidationError as e:
        print(f"\n❌ VALIDATION FAILED: {e}")
        exit(1)
