#!/usr/bin/env python3
"""
Improve Purchase Triggers Configuration
=======================================
Implements AI recommendations to improve stock selection system:
1. Stricter filters
2. Better score weights
3. Enhanced value/quality differentiation
4. Sector diversification

Usage:
    python scripts/improve_purchase_triggers.py [--apply]
"""

import sys
import argparse
import yaml
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def analyze_current_config():
    """Analyze current configuration and provide recommendations."""
    config_path = Path("config/config.yaml")
    
    if not config_path.exists():
        print("❌ Config file not found: config/config.yaml")
        return None
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    analysis = config.get('analysis', {})
    filters = analysis.get('filters', {})
    weights = analysis.get('weights', {})
    
    print("=" * 70)
    print("CURRENT CONFIGURATION ANALYSIS")
    print("=" * 70)
    print()
    
    print("📊 Current Settings:")
    print(f"  Model Weight:   {weights.get('model_score', 0.5)*100:.0f}%")
    print(f"  Value Weight:   {weights.get('value_score', 0.3)*100:.0f}%")
    print(f"  Quality Weight: {weights.get('quality_score', 0.2)*100:.0f}%")
    print()
    print(f"  Min ROE:        {filters.get('min_roe', 0.0) or 'None'}")
    print(f"  Min Net Margin: {filters.get('min_net_margin', 0.0) or 'None'}")
    print(f"  Max Debt/Equity: {filters.get('max_debt_to_equity', 2.0) or 'None'}")
    print()
    
    # Analyze issues
    issues = []
    recommendations = []
    
    # Check filter strictness
    if filters.get('min_roe', 0.0) == 0.0:
        issues.append("⚠️  Min ROE is 0.0 - filters are too lenient")
        recommendations.append("Set min_roe to 0.05 (5%) for basic profitability")
    
    if filters.get('min_net_margin', 0.0) == 0.0:
        issues.append("⚠️  Min Net Margin is 0.0 - filters are too lenient")
        recommendations.append("Set min_net_margin to 0.03 (3%) for basic profitability")
    
    if filters.get('max_debt_to_equity', 2.0) >= 2.0:
        issues.append("⚠️  Max Debt/Equity is 2.0 or higher - may allow too much leverage")
        recommendations.append("Set max_debt_to_equity to 1.5 for tighter leverage control")
    
    # Check weight balance
    model_weight = weights.get('model_score', 0.5)
    if model_weight >= 0.5:
        issues.append("⚠️  Model weight is 50%+ - model dominates selection")
        recommendations.append("Reduce model_score to 0.40, increase value_score to 0.35, quality_score to 0.25")
    
    value_weight = weights.get('value_score', 0.3)
    quality_weight = weights.get('quality_score', 0.2)
    if value_weight + quality_weight < 0.5:
        issues.append("⚠️  Value + Quality weights < 50% - fundamentals underweighted")
        recommendations.append("Increase value and quality weights to balance model dominance")
    
    print("🔍 Issues Found:")
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  ✅ No major issues found")
    print()
    
    print("💡 Recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")
    print()
    
    return {
        'config': config,
        'issues': issues,
        'recommendations': recommendations
    }


def apply_improvements(config_path: Path, dry_run: bool = True):
    """Apply recommended improvements to configuration."""
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    analysis = config.setdefault('analysis', {})
    filters = analysis.setdefault('filters', {})
    weights = analysis.setdefault('weights', {})
    
    print("=" * 70)
    print("APPLYING IMPROVEMENTS" if not dry_run else "PROPOSED CHANGES (DRY RUN)")
    print("=" * 70)
    print()
    
    changes = []
    
    # Update filters
    if filters.get('min_roe', 0.0) == 0.0:
        old_val = filters.get('min_roe', 0.0)
        filters['min_roe'] = 0.05
        changes.append(f"min_roe: {old_val} → 0.05 (5% ROE threshold)")
    
    if filters.get('min_net_margin', 0.0) == 0.0:
        old_val = filters.get('min_net_margin', 0.0)
        filters['min_net_margin'] = 0.03
        changes.append(f"min_net_margin: {old_val} → 0.03 (3% margin threshold)")
    
    if filters.get('max_debt_to_equity', 2.0) >= 2.0:
        old_val = filters.get('max_debt_to_equity', 2.0)
        filters['max_debt_to_equity'] = 1.5
        changes.append(f"max_debt_to_equity: {old_val} → 1.5 (tighter leverage)")
    
    # Update weights
    old_model = weights.get('model_score', 0.5)
    old_value = weights.get('value_score', 0.3)
    old_quality = weights.get('quality_score', 0.2)
    
    if old_model >= 0.5:
        weights['model_score'] = 0.40
        weights['value_score'] = 0.35
        weights['quality_score'] = 0.25
        changes.append(f"weights: Model {old_model*100:.0f}%/{old_value*100:.0f}%/{old_quality*100:.0f}% → 40%/35%/25%")
    
    print("📝 Changes to apply:")
    if changes:
        for change in changes:
            print(f"  ✅ {change}")
    else:
        print("  ℹ️  No changes needed - configuration already optimal")
    print()
    
    if not dry_run and changes:
        # Backup original
        backup_path = config_path.with_suffix('.yaml.backup')
        import shutil
        shutil.copy(config_path, backup_path)
        print(f"💾 Backed up original config to: {backup_path}")
        
        # Write updated config
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)
        
        print(f"✅ Updated configuration saved to: {config_path}")
        print()
        print("🔄 Next steps:")
        print("  1. Review the changes in config/config.yaml")
        print("  2. Run a new analysis to see the impact")
        print("  3. Check Purchase Triggers page to verify improvements")
    elif dry_run and changes:
        print("💡 Run with --apply to save these changes")
    
    return changes


def main():
    parser = argparse.ArgumentParser(
        description="Improve purchase triggers configuration based on AI recommendations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze current config (dry run)
  python scripts/improve_purchase_triggers.py
  
  # Apply improvements
  python scripts/improve_purchase_triggers.py --apply
        """
    )
    
    parser.add_argument("--apply", action="store_true",
                        help="Apply changes to config file (default: dry run)")
    
    args = parser.parse_args()
    
    # Analyze current config
    result = analyze_current_config()
    
    if result:
        config_path = Path("config/config.yaml")
        changes = apply_improvements(config_path, dry_run=not args.apply)
        
        if changes:
            print("=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Found {len(result['issues'])} issues")
            print(f"Proposed {len(changes)} improvements")
            if args.apply:
                print("✅ Changes applied successfully")
            else:
                print("💡 Run with --apply to save changes")
        else:
            print("✅ Configuration is already optimal")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
