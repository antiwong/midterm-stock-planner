#!/usr/bin/env python3
"""
Validate Analysis Reasonableness
==================================
Check if analysis results are reasonable and flag any anomalies.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.analysis_service import AnalysisService
import pandas as pd
import numpy as np


def check_attribution_reasonableness(attribution_data):
    """Check if attribution results are reasonable."""
    issues = []
    warnings = []
    
    total_return = attribution_data.get('total_return', 0)
    attributions = attribution_data.get('attributions', {})
    
    # Check if total return is reasonable (not extreme)
    if abs(total_return) > 2.0:  # >200% or <-200%
        issues.append(f"Extreme total return: {total_return*100:.2f}%")
    elif abs(total_return) > 1.0:  # >100% or <-100%
        warnings.append(f"Very high total return: {total_return*100:.2f}%")
    
    # Check if attributions sum approximately to total return
    sum_attributions = sum(attributions.values())
    diff = abs(total_return - sum_attributions)
    if diff > 0.1:  # >10% difference
        issues.append(f"Attributions don't sum to total return (diff: {diff*100:.2f}%)")
    elif diff > 0.05:  # >5% difference
        warnings.append(f"Attributions sum differs from total return (diff: {diff*100:.2f}%)")
    
    # Check individual attribution components
    for component, value in attributions.items():
        if abs(value) > 1.0:  # >100%
            warnings.append(f"Large {component} attribution: {value*100:.2f}%")
        if abs(value) > abs(total_return) * 1.5:  # Component >150% of total
            warnings.append(f"{component} attribution ({value*100:.2f}%) is very large relative to total return")
    
    return issues, warnings


def check_benchmark_reasonableness(comparison_data):
    """Check if benchmark comparison results are reasonable."""
    issues = []
    warnings = []
    
    portfolio_return = comparison_data.get('portfolio_metrics', {}).get('return', 0)
    benchmark_return = comparison_data.get('benchmark_metrics', {}).get('return', 0)
    alpha = comparison_data.get('relative_metrics', {}).get('alpha', 0)
    beta = comparison_data.get('relative_metrics', {}).get('beta', 1.0)
    
    # Check if returns are reasonable
    if abs(portfolio_return) > 2.0:
        issues.append(f"Extreme portfolio return: {portfolio_return*100:.2f}%")
    if abs(benchmark_return) > 2.0:
        issues.append(f"Extreme benchmark return: {benchmark_return*100:.2f}%")
    
    # Check if alpha is reasonable
    if abs(alpha) > 0.5:  # >50% alpha
        warnings.append(f"Very high alpha: {alpha*100:.2f}%")
    
    # Check if beta is reasonable
    if beta < 0 or beta > 3.0:
        issues.append(f"Unusual beta: {beta:.2f}")
    elif beta < 0.3 or beta > 2.0:
        warnings.append(f"Extreme beta: {beta:.2f}")
    
    # Check if alpha makes sense given returns
    expected_alpha = portfolio_return - benchmark_return
    if abs(alpha - expected_alpha) > 0.05:  # >5% difference
        warnings.append(f"Alpha ({alpha*100:.2f}%) doesn't match return difference ({expected_alpha*100:.2f}%)")
    
    return issues, warnings


def check_factor_exposure_reasonableness(factor_data):
    """Check if factor exposure results are reasonable."""
    issues = []
    warnings = []
    
    exposures = factor_data.get('exposures', {})
    
    if not exposures:
        issues.append("No factor exposures found")
        return issues, warnings
    
    # Check individual exposures
    for factor_name, exposure_data in exposures.items():
        exposure = exposure_data.get('exposure', 0)
        return_contrib = exposure_data.get('contribution_to_return', 0)
        risk_contrib = exposure_data.get('contribution_to_risk', 0)
        
        # Check exposure magnitude
        if abs(exposure) > 2.0:
            warnings.append(f"Large {factor_name} exposure: {exposure:.3f}")
        
        # Check if contributions are reasonable
        if abs(return_contrib) > 0.5:  # >50%
            warnings.append(f"Large {factor_name} return contribution: {return_contrib*100:.2f}%")
        
        if abs(risk_contrib) > 0.5:  # >50%
            warnings.append(f"Large {factor_name} risk contribution: {risk_contrib*100:.2f}%")
    
    return issues, warnings


def check_rebalancing_reasonableness(rebalancing_data):
    """Check if rebalancing results are reasonable."""
    issues = []
    warnings = []
    
    current_drift = rebalancing_data.get('current_drift', 0)
    avg_turnover = rebalancing_data.get('avg_turnover', 0)
    transaction_costs = rebalancing_data.get('total_transaction_costs', 0)
    
    # Check drift
    if abs(current_drift) > 0.5:  # >50% drift
        issues.append(f"Very high portfolio drift: {current_drift*100:.2f}%")
    elif abs(current_drift) > 0.2:  # >20% drift
        warnings.append(f"High portfolio drift: {current_drift*100:.2f}%")
    
    # Check turnover
    if avg_turnover > 2.0:  # >200% turnover
        issues.append(f"Extreme average turnover: {avg_turnover*100:.2f}%")
    elif avg_turnover > 1.0:  # >100% turnover
        warnings.append(f"Very high average turnover: {avg_turnover*100:.2f}%")
    
    # Check transaction costs
    if transaction_costs > 0.05:  # >5%
        issues.append(f"Very high transaction costs: {transaction_costs*100:.2f}%")
    elif transaction_costs > 0.02:  # >2%
        warnings.append(f"High transaction costs: {transaction_costs*100:.2f}%")
    
    return issues, warnings


def check_style_reasonableness(style_data):
    """Check if style analysis results are reasonable."""
    issues = []
    warnings = []
    
    portfolio_pe = style_data.get('portfolio_pe', None)
    market_pe = style_data.get('market_pe', None)
    
    # Check PE ratios
    if portfolio_pe is not None:
        if portfolio_pe < 0 or portfolio_pe > 100:
            issues.append(f"Unusual portfolio PE: {portfolio_pe:.2f}")
        elif portfolio_pe > 50:
            warnings.append(f"Very high portfolio PE: {portfolio_pe:.2f}")
    
    if market_pe is not None:
        if market_pe < 0 or market_pe > 100:
            issues.append(f"Unusual market PE: {market_pe:.2f}")
        elif market_pe > 50:
            warnings.append(f"Very high market PE: {market_pe:.2f}")
    
    # Check PE ratio comparison
    if portfolio_pe is not None and market_pe is not None:
        pe_ratio = portfolio_pe / market_pe if market_pe > 0 else None
        if pe_ratio is not None:
            if pe_ratio > 2.0 or pe_ratio < 0.3:
                warnings.append(f"Portfolio PE ({portfolio_pe:.2f}) very different from market ({market_pe:.2f})")
    
    return issues, warnings


def validate_analysis(run_id):
    """Validate all analysis results for a run."""
    print("=" * 60)
    print(f"Validating Analysis for Run: {run_id}")
    print("=" * 60)
    print()
    
    service = AnalysisService()
    
    all_issues = []
    all_warnings = []
    
    # Check Performance Attribution
    print("Checking Performance Attribution...")
    attr_result = service.get_analysis_result(run_id, 'attribution')
    if attr_result:
        attr_data = attr_result.get_results()
        issues, warnings = check_attribution_reasonableness(attr_data)
        all_issues.extend([f"Attribution: {i}" for i in issues])
        all_warnings.extend([f"Attribution: {w}" for w in warnings])
        if issues:
            print(f"  ❌ Issues: {len(issues)}")
            for issue in issues:
                print(f"     - {issue}")
        if warnings:
            print(f"  ⚠️  Warnings: {len(warnings)}")
            for warning in warnings:
                print(f"     - {warning}")
        if not issues and not warnings:
            print("  ✅ All checks passed")
    else:
        print("  ⚠️  No attribution data found")
    
    print()
    
    # Check Benchmark Comparison
    print("Checking Benchmark Comparison...")
    bench_result = service.get_analysis_result(run_id, 'benchmark_comparison')
    if bench_result:
        bench_data = bench_result.get_results()
        # Handle multiple benchmarks
        if isinstance(bench_data, dict):
            for benchmark, comparison in bench_data.items():
                if 'error' in comparison:
                    continue
                print(f"  Benchmark: {benchmark}")
                issues, warnings = check_benchmark_reasonableness(comparison)
                all_issues.extend([f"Benchmark {benchmark}: {i}" for i in issues])
                all_warnings.extend([f"Benchmark {benchmark}: {w}" for w in warnings])
                if issues:
                    print(f"    ❌ Issues: {len(issues)}")
                    for issue in issues:
                        print(f"       - {issue}")
                if warnings:
                    print(f"    ⚠️  Warnings: {len(warnings)}")
                    for warning in warnings:
                        print(f"       - {warning}")
                if not issues and not warnings:
                    print("    ✅ All checks passed")
    else:
        print("  ⚠️  No benchmark comparison data found")
    
    print()
    
    # Check Factor Exposure
    print("Checking Factor Exposure...")
    factor_result = service.get_analysis_result(run_id, 'factor_exposure')
    if factor_result:
        factor_data = factor_result.get_results()
        issues, warnings = check_factor_exposure_reasonableness(factor_data)
        all_issues.extend([f"Factor Exposure: {i}" for i in issues])
        all_warnings.extend([f"Factor Exposure: {w}" for w in warnings])
        if issues:
            print(f"  ❌ Issues: {len(issues)}")
            for issue in issues:
                print(f"     - {issue}")
        if warnings:
            print(f"  ⚠️  Warnings: {len(warnings)}")
            for warning in warnings:
                print(f"     - {warning}")
        if not issues and not warnings:
            print("  ✅ All checks passed")
    else:
        print("  ⚠️  No factor exposure data found")
    
    print()
    
    # Check Rebalancing
    print("Checking Rebalancing Analysis...")
    rebal_result = service.get_analysis_result(run_id, 'rebalancing')
    if rebal_result:
        rebal_data = rebal_result.get_results()
        issues, warnings = check_rebalancing_reasonableness(rebal_data)
        all_issues.extend([f"Rebalancing: {i}" for i in issues])
        all_warnings.extend([f"Rebalancing: {w}" for w in warnings])
        if issues:
            print(f"  ❌ Issues: {len(issues)}")
            for issue in issues:
                print(f"     - {issue}")
        if warnings:
            print(f"  ⚠️  Warnings: {len(warnings)}")
            for warning in warnings:
                print(f"     - {warning}")
        if not issues and not warnings:
            print("  ✅ All checks passed")
    else:
        print("  ⚠️  No rebalancing data found")
    
    print()
    
    # Check Style Analysis
    print("Checking Style Analysis...")
    style_result = service.get_analysis_result(run_id, 'style')
    if style_result:
        style_data = style_result.get_results()
        issues, warnings = check_style_reasonableness(style_data)
        all_issues.extend([f"Style: {i}" for i in issues])
        all_warnings.extend([f"Style: {w}" for w in warnings])
        if issues:
            print(f"  ❌ Issues: {len(issues)}")
            for issue in issues:
                print(f"     - {issue}")
        if warnings:
            print(f"  ⚠️  Warnings: {len(warnings)}")
            for warning in warnings:
                print(f"     - {warning}")
        if not issues and not warnings:
            print("  ✅ All checks passed")
    else:
        print("  ⚠️  No style analysis data found")
    
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total Issues: {len(all_issues)}")
    print(f"Total Warnings: {len(all_warnings)}")
    print()
    
    if all_issues:
        print("❌ CRITICAL ISSUES FOUND:")
        for issue in all_issues:
            print(f"  - {issue}")
        print()
    
    if all_warnings:
        print("⚠️  WARNINGS:")
        for warning in all_warnings[:10]:  # Show first 10
            print(f"  - {warning}")
        if len(all_warnings) > 10:
            print(f"  ... and {len(all_warnings) - 10} more warnings")
        print()
    
    if not all_issues and not all_warnings:
        print("✅ All analysis results appear reasonable!")
        return 0
    elif not all_issues:
        print("⚠️  Analysis has warnings but no critical issues")
        return 0
    else:
        print("❌ Analysis has critical issues that should be investigated")
        return 1


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_analysis_reasonableness.py <run_id>")
        return 1
    
    run_id = sys.argv[1]
    return validate_analysis(run_id)


if __name__ == '__main__':
    sys.exit(main())
