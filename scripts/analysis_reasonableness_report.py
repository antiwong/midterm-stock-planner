#!/usr/bin/env python3
"""
Analysis Reasonableness Report
===============================
Generate a comprehensive report on analysis results reasonableness.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analytics.analysis_service import AnalysisService
import pandas as pd
import numpy as np
from datetime import datetime


def generate_report(run_id):
    """Generate a comprehensive reasonableness report."""
    print("=" * 70)
    print(f"ANALYSIS REASONABLENESS REPORT")
    print("=" * 70)
    print(f"Run ID: {run_id}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    service = AnalysisService()
    
    # Get all analysis results
    all_results = service.get_all_analysis_results(run_id)
    analysis_types = {r.analysis_type for r in all_results}
    
    print(f"Available Analyses: {', '.join(sorted(analysis_types))}")
    print()
    
    # 1. Benchmark Comparison
    if 'benchmark_comparison' in analysis_types:
        print("1. BENCHMARK COMPARISON")
        print("-" * 70)
        bench_result = service.get_analysis_result(run_id, 'benchmark_comparison')
        if bench_result:
            comparisons = bench_result.get_results()
            for bench_name, comp in comparisons.items():
                if 'error' in comp:
                    print(f"  {bench_name}: ❌ Error - {comp['error']}")
                    continue
                
                portfolio_metrics = comp.get('portfolio_metrics', {})
                benchmark_metrics = comp.get('benchmark_metrics', {})
                relative_metrics = comp.get('relative_metrics', {})
                
                port_return = portfolio_metrics.get('return', 0) * 100
                bench_return = benchmark_metrics.get('return', 0) * 100
                alpha = relative_metrics.get('alpha', 0) * 100
                beta = relative_metrics.get('beta', 1.0)
                sharpe_port = portfolio_metrics.get('sharpe', 0)
                sharpe_bench = benchmark_metrics.get('sharpe', 0)
                
                print(f"  Benchmark: {bench_name}")
                print(f"    Portfolio Return: {port_return:>8.2f}%")
                print(f"    Benchmark Return: {bench_return:>8.2f}%")
                print(f"    Alpha:            {alpha:>8.2f}%")
                print(f"    Beta:             {beta:>8.2f}")
                print(f"    Portfolio Sharpe: {sharpe_port:>7.2f}")
                print(f"    Benchmark Sharpe: {sharpe_bench:>7.2f}")
                
                # Reasonableness checks
                checks = []
                if abs(port_return) < 100 and abs(bench_return) < 100:
                    checks.append("✅ Returns within reasonable range")
                else:
                    checks.append("⚠️  Returns seem extreme")
                
                if 0.3 <= beta <= 2.0:
                    checks.append("✅ Beta within reasonable range")
                else:
                    checks.append("⚠️  Beta outside typical range (0.3-2.0)")
                
                if abs(alpha) < 50:
                    checks.append("✅ Alpha within reasonable range")
                else:
                    checks.append("⚠️  Alpha seems very high")
                
                for check in checks:
                    print(f"    {check}")
                print()
        else:
            print("  ⚠️  No benchmark comparison data found")
            print()
    
    # 2. Factor Exposure
    if 'factor_exposure' in analysis_types:
        print("2. FACTOR EXPOSURE")
        print("-" * 70)
        factor_result = service.get_analysis_result(run_id, 'factor_exposure')
        if factor_result:
            factor_data = factor_result.get_results()
            exposures = factor_data.get('exposures', {})
            if exposures:
                print(f"  Found {len(exposures)} factor exposures:")
                for factor_name, exp_data in exposures.items():
                    exposure = exp_data.get('exposure', 0)
                    ret_contrib = exp_data.get('contribution_to_return', 0) * 100
                    risk_contrib = exp_data.get('contribution_to_risk', 0) * 100
                    print(f"    {factor_name:20} Exposure: {exposure:>7.3f}  Return: {ret_contrib:>6.2f}%  Risk: {risk_contrib:>6.2f}%")
                
                # Reasonableness
                max_exposure = max(abs(exp_data.get('exposure', 0)) for exp_data in exposures.values())
                if max_exposure < 2.0:
                    print("  ✅ All exposures within reasonable range")
                else:
                    print(f"  ⚠️  Some exposures are large (max: {max_exposure:.3f})")
            else:
                print("  ⚠️  No factor exposures found")
                print(f"  Available keys: {list(factor_data.keys())}")
        else:
            print("  ⚠️  No factor exposure data found")
        print()
    
    # 3. Rebalancing Analysis
    if 'rebalancing' in analysis_types:
        print("3. REBALANCING ANALYSIS")
        print("-" * 70)
        rebal_result = service.get_analysis_result(run_id, 'rebalancing')
        if rebal_result:
            rebal_data = rebal_result.get_results()
            drift = rebal_data.get('current_drift', 0) * 100
            turnover = rebal_data.get('avg_turnover', 0) * 100
            costs = rebal_data.get('total_transaction_costs', 0) * 100
            events = rebal_data.get('num_rebalancing_events', 0)
            
            print(f"  Current Drift:        {drift:>8.2f}%")
            print(f"  Average Turnover:     {turnover:>8.2f}%")
            print(f"  Transaction Costs:   {costs:>8.2f}%")
            print(f"  Rebalancing Events:  {events:>8d}")
            
            # Reasonableness
            checks = []
            if abs(drift) < 20:
                checks.append("✅ Portfolio drift is low")
            elif abs(drift) < 50:
                checks.append("⚠️  Portfolio drift is moderate (20-50%)")
            else:
                checks.append("❌ Portfolio drift is very high (>50%)")
            
            if turnover < 100:
                checks.append("✅ Turnover is reasonable")
            else:
                checks.append("⚠️  Turnover is very high")
            
            if costs < 2:
                checks.append("✅ Transaction costs are low")
            else:
                checks.append("⚠️  Transaction costs are high")
            
            for check in checks:
                print(f"  {check}")
        else:
            print("  ⚠️  No rebalancing data found")
        print()
    
    # 4. Style Analysis
    if 'style' in analysis_types:
        print("4. STYLE ANALYSIS")
        print("-" * 70)
        style_result = service.get_analysis_result(run_id, 'style')
        if style_result:
            style_data = style_result.get_results()
            growth_value = style_data.get('growth_value_classification', 'N/A')
            size = style_data.get('size_classification', 'N/A')
            portfolio_pe = style_data.get('portfolio_pe', 0)
            market_pe = style_data.get('market_pe', 0)
            
            print(f"  Growth/Value:    {growth_value}")
            print(f"  Size:            {size}")
            print(f"  Portfolio PE:    {portfolio_pe:.2f}")
            print(f"  Market PE:       {market_pe:.2f}")
            
            # Reasonableness
            checks = []
            if portfolio_pe > 0 and 5 <= portfolio_pe <= 50:
                checks.append("✅ Portfolio PE is reasonable")
            elif portfolio_pe == 0:
                checks.append("⚠️  Portfolio PE is 0 (may indicate missing data)")
            else:
                checks.append("⚠️  Portfolio PE seems unusual")
            
            if market_pe > 0 and 10 <= market_pe <= 30:
                checks.append("✅ Market PE is reasonable")
            elif market_pe == 0:
                checks.append("⚠️  Market PE is 0 (may indicate missing data)")
            else:
                checks.append("⚠️  Market PE seems unusual")
            
            for check in checks:
                print(f"  {check}")
        else:
            print("  ⚠️  No style analysis data found")
        print()
    
    # 5. Performance Attribution
    if 'attribution' in analysis_types:
        print("5. PERFORMANCE ATTRIBUTION")
        print("-" * 70)
        attr_result = service.get_analysis_result(run_id, 'attribution')
        if attr_result:
            attr_data = attr_result.get_results()
            total_return = attr_data.get('total_return', 0) * 100
            attributions = attr_data.get('attributions', {})
            
            print(f"  Total Return: {total_return:.2f}%")
            print("  Attribution Breakdown:")
            for component, value in attributions.items():
                print(f"    {component:20} {value*100:>8.2f}%")
            
            # Check if attributions sum to total
            sum_attr = sum(attributions.values()) * 100
            diff = abs(total_return - sum_attr)
            if diff < 5:
                print(f"  ✅ Attributions sum correctly (diff: {diff:.2f}%)")
            else:
                print(f"  ⚠️  Attributions don't sum correctly (diff: {diff:.2f}%)")
        else:
            print("  ⚠️  No attribution data found (may need stock returns data)")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    successful = len([r for r in all_results if r.analysis_type != 'attribution' or 
                      service.get_analysis_result(run_id, 'attribution')])
    
    print(f"Analyses Completed: {successful}/{len(analysis_types)}")
    print()
    print("Overall Assessment:")
    
    if 'benchmark_comparison' in analysis_types:
        print("  ✅ Benchmark comparison available")
    if 'factor_exposure' in analysis_types:
        factor_result = service.get_analysis_result(run_id, 'factor_exposure')
        if factor_result and factor_result.get_results().get('exposures'):
            print("  ✅ Factor exposure available")
        else:
            print("  ⚠️  Factor exposure incomplete (no exposures found)")
    if 'rebalancing' in analysis_types:
        print("  ✅ Rebalancing analysis available")
    if 'style' in analysis_types:
        print("  ✅ Style analysis available")
    if 'attribution' not in analysis_types:
        print("  ⚠️  Performance attribution not available (requires stock returns)")
    
    print()
    print("=" * 70)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/analysis_reasonableness_report.py <run_id>")
        return 1
    
    run_id = sys.argv[1]
    generate_report(run_id)
    return 0


if __name__ == '__main__':
    sys.exit(main())
