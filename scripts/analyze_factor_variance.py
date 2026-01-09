#!/usr/bin/env python3
"""
Analyze Factor Variance and Suggest Optimal Weights
====================================================
Analyzes factor score distributions and suggests optimal weights to balance
factor contributions and reduce concentration risk.

Usage:
    python scripts/analyze_factor_variance.py --run-dir output/run_my_combined_list_1_20260109_144437_
    python scripts/analyze_factor_variance.py --run-dir output/run_my_combined_list_1_20260109_144437_ --apply
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import json
from typing import Dict, Tuple, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config import load_config


def analyze_factor_variance(enriched_df: pd.DataFrame) -> Dict:
    """
    Analyze variance and distribution of factor scores.
    
    Returns:
        Dictionary with analysis results
    """
    factor_cols = ['value_score', 'quality_score', 'model_score', 'momentum_score', 'tech_score']
    available_factors = [c for c in factor_cols if c in enriched_df.columns]
    
    if not available_factors:
        return {'error': 'No factor columns found in enriched data'}
    
    analysis = {
        'factors': {},
        'variance_contributions': {},
        'recommendations': {}
    }
    
    # Calculate statistics for each factor
    for factor in available_factors:
        scores = enriched_df[factor].dropna()
        if len(scores) == 0:
            continue
            
        analysis['factors'][factor] = {
            'count': len(scores),
            'mean': float(scores.mean()),
            'std': float(scores.std()),
            'var': float(scores.var()),
            'min': float(scores.min()),
            'max': float(scores.max()),
            'range': float(scores.max() - scores.min()),
            'cv': float(scores.std() / scores.mean()) if scores.mean() != 0 else 0.0  # Coefficient of variation
        }
    
    # Calculate variance contributions (how factor concentration check works)
    factor_vars = {f: analysis['factors'][f]['var'] for f in available_factors if f in analysis['factors']}
    total_var = sum(factor_vars.values())
    
    if total_var > 0:
        for factor in factor_vars:
            contribution = factor_vars[factor] / total_var
            analysis['variance_contributions'][factor] = {
                'variance': factor_vars[factor],
                'contribution_pct': contribution * 100,
                'is_dominant': contribution > 0.50
            }
    
    return analysis


def suggest_optimal_weights(
    analysis: Dict,
    current_weights: Dict[str, float],
    target_max_contribution: float = 0.50
) -> Dict[str, float]:
    """
    Suggest optimal weights to balance factor contributions.
    
    Strategy:
    1. If a factor has high variance contribution, reduce its weight
    2. Increase weights of factors with low variance contribution
    3. Maintain relative importance while balancing variance
    """
    if 'variance_contributions' not in analysis or not analysis['variance_contributions']:
        return current_weights
    
    variance_contribs = analysis['variance_contributions']
    
    # Calculate adjustment factors
    # Factors with high variance contribution should have reduced weight
    # Factors with low variance contribution should have increased weight
    adjustments = {}
    
    for factor in current_weights:
        if factor not in variance_contribs:
            adjustments[factor] = 1.0  # No change
            continue
        
        contrib_pct = variance_contribs[factor]['contribution_pct'] / 100.0
        
        # If contribution is too high, reduce weight
        # If contribution is too low, increase weight
        # Target: each factor should contribute roughly proportionally to its weight
        if contrib_pct > target_max_contribution:
            # Reduce weight proportionally to how much it exceeds target
            excess = contrib_pct - target_max_contribution
            adjustment = 1.0 - (excess * 1.5)  # Reduce by 1.5x the excess
            adjustment = max(0.1, adjustment)  # Don't reduce below 10%
        elif contrib_pct < target_max_contribution * 0.3:
            # Increase weight if contribution is very low
            adjustment = 1.0 + (target_max_contribution * 0.3 - contrib_pct) * 0.5
            adjustment = min(2.0, adjustment)  # Don't increase more than 2x
        else:
            adjustment = 1.0  # No change needed
        
        adjustments[factor] = adjustment
    
    # Apply adjustments
    suggested_weights = {}
    for factor in current_weights:
        suggested_weights[factor] = current_weights[factor] * adjustments[factor]
    
    # Normalize to sum to 1.0
    total = sum(suggested_weights.values())
    if total > 0:
        suggested_weights = {k: v / total for k, v in suggested_weights.items()}
    
    return suggested_weights


def load_enriched_data(run_dir: Path) -> Optional[pd.DataFrame]:
    """Load enriched portfolio data from run directory."""
    # Try to find enriched CSV
    enriched_files = list(run_dir.glob('portfolio_enriched_*.csv'))
    if not enriched_files:
        print(f"❌ No portfolio_enriched_*.csv found in {run_dir}")
        return None
    
    # Use the most recent one
    enriched_file = sorted(enriched_files)[-1]
    print(f"📊 Loading: {enriched_file.name}")
    
    df = pd.read_csv(enriched_file)
    return df


def print_analysis_report(analysis: Dict, current_weights: Dict, suggested_weights: Dict):
    """Print formatted analysis report."""
    print("\n" + "=" * 80)
    print("FACTOR VARIANCE ANALYSIS")
    print("=" * 80)
    
    # Factor statistics
    print("\n📊 Factor Statistics:")
    print("-" * 80)
    if 'factors' in analysis:
        for factor, stats in analysis['factors'].items():
            print(f"\n{factor}:")
            print(f"  Mean:   {stats['mean']:.2f}")
            print(f"  Std:    {stats['std']:.2f}")
            print(f"  Var:    {stats['var']:.2f}")
            print(f"  Range:  {stats['range']:.2f}")
            print(f"  CV:     {stats['cv']:.3f} (coefficient of variation)")
    
    # Variance contributions
    print("\n📈 Variance Contributions (Factor Concentration Check):")
    print("-" * 80)
    if 'variance_contributions' in analysis:
        for factor, contrib in analysis['variance_contributions'].items():
            status = "⚠️  DOMINANT" if contrib['is_dominant'] else "✅"
            print(f"{status} {factor:20s}: {contrib['contribution_pct']:6.1f}% "
                  f"(variance: {contrib['variance']:.2f})")
    
    # Current vs Suggested Weights
    print("\n⚖️  Weight Recommendations:")
    print("-" * 80)
    print(f"{'Factor':<20s} {'Current':>10s} {'Suggested':>10s} {'Change':>10s}")
    print("-" * 80)
    
    for factor in current_weights:
        current = current_weights[factor]
        suggested = suggested_weights.get(factor, current)
        change = suggested - current
        change_pct = (change / current * 100) if current > 0 else 0
        
        arrow = "↑" if change > 0.01 else "↓" if change < -0.01 else "→"
        print(f"{factor:<20s} {current:>9.2f}  {suggested:>9.2f}  {arrow} {change_pct:>6.1f}%")
    
    # Projected variance contributions with new weights
    print("\n📊 Projected Variance Contributions (with suggested weights):")
    print("-" * 80)
    if 'variance_contributions' in analysis:
        total_var = sum(v['variance'] for v in analysis['variance_contributions'].values())
        
        for factor in current_weights:
            if factor in analysis['variance_contributions']:
                variance = analysis['variance_contributions'][factor]['variance']
                new_weight = suggested_weights.get(factor, current_weights[factor])
                
                # Weighted variance contribution
                weighted_var = variance * (new_weight ** 2)
                projected_contrib = weighted_var / total_var * 100 if total_var > 0 else 0
                
                status = "⚠️" if projected_contrib > 50 else "✅"
                print(f"{status} {factor:20s}: {projected_contrib:6.1f}% "
                      f"(weight: {new_weight:.2f})")
    
    print("\n" + "=" * 80)


def apply_weights_to_config(config_path: Path, suggested_weights: Dict) -> bool:
    """Apply suggested weights to config.yaml file."""
    import yaml
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if 'analysis' not in config:
            config['analysis'] = {}
        if 'weights' not in config['analysis']:
            config['analysis']['weights'] = {}
        
        # Update weights
        for factor, weight in suggested_weights.items():
            # Map factor names to config keys
            config_key = factor.replace('_score', '_score')
            config['analysis']['weights'][config_key] = weight
        
        # Backup original
        backup_path = config_path.with_suffix('.yaml.backup')
        with open(backup_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        print(f"💾 Backup saved to: {backup_path}")
        
        # Write updated config
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ Updated weights in: {config_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating config: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Analyze factor variance and suggest optimal weights'
    )
    parser.add_argument(
        '--run-dir',
        type=str,
        required=True,
        help='Path to run output directory'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply suggested weights to config.yaml'
    )
    parser.add_argument(
        '--target-max-contribution',
        type=float,
        default=0.50,
        help='Target maximum variance contribution per factor (default: 0.50)'
    )
    
    args = parser.parse_args()
    
    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"❌ Run directory not found: {run_dir}")
        return 1
    
    # Load enriched data
    enriched_df = load_enriched_data(run_dir)
    if enriched_df is None:
        return 1
    
    # Load current config
    config = load_config()
    # Access analysis weights from config dict
    if hasattr(config, 'analysis') and hasattr(config.analysis, 'weights'):
        current_weights = config.analysis.weights
    else:
        # Try accessing from config dict directly
        config_dict = config.to_dict() if hasattr(config, 'to_dict') else {}
        analysis_config = config_dict.get('analysis', {})
        current_weights = analysis_config.get('weights', {
            'model_score': 0.40,
            'value_score': 0.35,
            'quality_score': 0.25
        })
    
    print(f"\n📋 Current Weights:")
    for factor, weight in current_weights.items():
        print(f"  {factor}: {weight:.2f}")
    
    # Analyze factor variance
    analysis = analyze_factor_variance(enriched_df)
    
    if 'error' in analysis:
        print(f"❌ {analysis['error']}")
        return 1
    
    # Suggest optimal weights
    suggested_weights = suggest_optimal_weights(
        analysis,
        current_weights,
        target_max_contribution=args.target_max_contribution
    )
    
    # Print report
    print_analysis_report(analysis, current_weights, suggested_weights)
    
    # Apply if requested
    if args.apply:
        config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
        if apply_weights_to_config(config_path, suggested_weights):
            print("\n✅ Weights updated! Re-run your analysis to see the improvements.")
        else:
            return 1
    else:
        print("\n💡 To apply these weights, run with --apply flag:")
        print(f"   python scripts/analyze_factor_variance.py --run-dir {run_dir} --apply")
    
    # Save analysis to JSON
    output_file = run_dir / 'factor_variance_analysis.json'
    with open(output_file, 'w') as f:
        json.dump({
            'analysis': analysis,
            'current_weights': current_weights,
            'suggested_weights': suggested_weights
        }, f, indent=2, default=str)
    
    print(f"\n💾 Analysis saved to: {output_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
