"""
Validate Existing Analysis Runs
================================
Validates existing analysis runs in detail to check if results are reasonable.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.analytics.models import get_db, Run
from src.analytics.analysis_service import AnalysisService
from src.app.dashboard.data import load_run_scores, load_runs


class RunValidator:
    """Validates individual analysis runs."""
    
    def __init__(self):
        self.analysis_service = AnalysisService()
    
    def validate_run(self, run_id: str) -> Dict[str, Any]:
        """Validate a single run's results."""
        validation = {
            'run_id': run_id,
            'passed': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }
        
        print(f"\n{'='*70}")
        print(f"VALIDATING RUN: {run_id[:16]}...")
        print(f"{'='*70}")
        
        # Check 1: Run exists in database
        db = get_db()
        session = db.get_session()
        try:
            run = session.query(Run).filter_by(run_id=run_id).first()
            if not run:
                validation['passed'] = False
                validation['errors'].append("Run not found in database")
                return validation
            
            validation['checks']['run_exists'] = True
            validation['checks']['run_status'] = run.status
            validation['checks']['run_type'] = run.run_type
            validation['checks']['watchlist'] = run.watchlist
            validation['checks']['created_at'] = run.created_at.isoformat()
            
            if run.status != 'completed':
                validation['passed'] = False
                validation['errors'].append(f"Run status is '{run.status}', expected 'completed'")
            
        finally:
            session.close()
        
        # Check 2: Stock scores exist
        scores = load_run_scores(run_id)
        if not scores:
            validation['passed'] = False
            validation['errors'].append("No stock scores found")
            return validation
        
        validation['checks']['num_scores'] = len(scores)
        
        if len(scores) < 1:
            validation['errors'].append("No stocks scored")
            validation['passed'] = False
            return validation
        
        # Check 3: Score distribution is reasonable
        score_values = [s.get('score', 0) for s in scores if s.get('score') is not None]
        if score_values:
            validation['checks']['score_mean'] = float(np.mean(score_values))
            validation['checks']['score_std'] = float(np.std(score_values))
            validation['checks']['score_min'] = float(np.min(score_values))
            validation['checks']['score_max'] = float(np.max(score_values))
            validation['checks']['score_range'] = float(np.max(score_values) - np.min(score_values))
            
            # Scores should be in reasonable range
            if all(-2 <= s <= 2 for s in score_values):
                validation['checks']['score_range_valid'] = True
                validation['checks']['score_type'] = 'normalized'
            elif all(0 <= s <= 100 for s in score_values):
                validation['checks']['score_range_valid'] = True
                validation['checks']['score_type'] = 'percentage'
            else:
                validation['warnings'].append(f"Scores outside expected range: min={min(score_values):.3f}, max={max(score_values):.3f}")
            
            # Scores should have some variation
            if np.std(score_values) < 0.01:
                validation['warnings'].append("Scores have very low variation (std < 0.01), may indicate calculation issue")
            elif np.std(score_values) > 10:
                validation['warnings'].append(f"Scores have very high variation (std = {np.std(score_values):.2f}), may indicate outliers")
            
            # Check for reasonable distribution
            if validation['checks']['score_range'] < 0.01:
                validation['warnings'].append("All scores are nearly identical, may indicate calculation issue")
        else:
            validation['errors'].append("No valid score values found")
            validation['passed'] = False
        
        # Check 4: Required fields present
        required_fields = ['ticker', 'score']
        missing_fields = set()
        for score in scores[:10]:  # Check first 10
            for field in required_fields:
                if field not in score:
                    missing_fields.add(field)
        
        if missing_fields:
            validation['errors'].append(f"Missing required fields: {', '.join(missing_fields)}")
            validation['passed'] = False
        
        # Check 5: Sector distribution
        sectors = [s.get('sector', 'Unknown') for s in scores if s.get('sector')]
        if sectors:
            sector_counts = pd.Series(sectors).value_counts()
            validation['checks']['sectors'] = sector_counts.to_dict()
            validation['checks']['num_sectors'] = len(sector_counts)
            
            # Check for reasonable sector diversity
            if len(sector_counts) == 1 and len(scores) > 3:
                validation['warnings'].append(f"All stocks in single sector: {sector_counts.index[0]}")
        else:
            validation['warnings'].append("No sector information found")
        
        # Check 6: No duplicate tickers
        tickers = [s.get('ticker') for s in scores if s.get('ticker')]
        if len(tickers) != len(set(tickers)):
            duplicates = [t for t in tickers if tickers.count(t) > 1]
            validation['errors'].append(f"Duplicate tickers found: {', '.join(set(duplicates))}")
            validation['passed'] = False
        
        # Check 7: Rank ordering (if ranks exist)
        ranks = [s.get('rank') for s in scores if s.get('rank') is not None]
        if ranks:
            sorted_ranks = sorted(ranks)
            expected_ranks = list(range(1, len(sorted_ranks) + 1))
            if sorted_ranks != expected_ranks:
                validation['warnings'].append("Ranks are not sequential starting from 1")
        
        # Check 8: Analysis results exist (optional)
        analysis_types = ['attribution', 'benchmark_comparison', 'factor_exposure']
        for analysis_type in analysis_types:
            result = self.analysis_service.get_analysis_result(run_id, analysis_type)
            if result:
                validation['checks'][f'{analysis_type}_exists'] = True
            else:
                validation['warnings'].append(f"Analysis result '{analysis_type}' not found (optional)")
        
        # Check 9: Data completeness
        scores_with_data = [s for s in scores if s.get('score') is not None]
        completeness = len(scores_with_data) / len(scores) if scores else 0
        validation['checks']['data_completeness'] = completeness
        
        if completeness < 0.8:  # At least 80% should have scores
            validation['warnings'].append(f"Only {completeness*100:.1f}% of stocks have scores")
        
        # Check 10: Score correlation with rank (if both exist)
        if ranks and score_values and len(ranks) == len(score_values):
            # Higher scores should generally have lower (better) ranks
            rank_score_corr = np.corrcoef(ranks, score_values)[0, 1]
            validation['checks']['rank_score_correlation'] = float(rank_score_corr)
            
            if abs(rank_score_corr) < 0.5:
                validation['warnings'].append(f"Low correlation between ranks and scores ({rank_score_corr:.2f}), may indicate ranking issue")
        
        # Summary
        if validation['errors']:
            validation['passed'] = False
        
        # Print summary
        status = "✅ PASSED" if validation['passed'] else "❌ FAILED"
        print(f"{status}")
        if validation['errors']:
            print(f"   Errors: {len(validation['errors'])}")
        if validation['warnings']:
            print(f"   Warnings: {len(validation['warnings'])}")
        print(f"   Stocks: {validation['checks'].get('num_scores', 0)}")
        if 'score_mean' in validation['checks']:
            print(f"   Avg Score: {validation['checks']['score_mean']:.3f}")
        if 'num_sectors' in validation['checks']:
            print(f"   Sectors: {validation['checks']['num_sectors']}")
        
        return validation


def main():
    """Main validation function."""
    print("=" * 70)
    print("DETAILED ANALYSIS VALIDATION - EXISTING RUNS")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get existing runs
    runs = load_runs()
    
    if not runs:
        print("❌ No runs found in database.")
        return
    
    # Filter to completed runs
    completed_runs = [r for r in runs if r.get('status') == 'completed']
    
    if not completed_runs:
        print("❌ No completed runs found.")
        return
    
    print(f"\n📊 Found {len(completed_runs)} completed runs")
    print(f"   Validating up to 10 most recent runs...")
    
    # Validate recent runs
    validator = RunValidator()
    validations = []
    
    for run in completed_runs[:10]:  # Validate up to 10 most recent
        run_id = run['run_id']
        validation = validator.validate_run(run_id)
        validations.append(validation)
    
    # Print summary report
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    total = len(validations)
    passed = sum(1 for v in validations if v['passed'])
    failed = total - passed
    
    print(f"\n📊 Results:")
    print(f"   Total runs validated: {total}")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   Success rate: {passed/total*100:.1f}%")
    
    # Show failed runs
    if failed > 0:
        print(f"\n❌ Failed Runs:")
        for v in validations:
            if not v['passed']:
                print(f"   • {v['run_id'][:16]}... ({len(v['errors'])} errors)")
                for error in v['errors'][:3]:
                    print(f"     - {error}")
    
    # Show warnings summary
    total_warnings = sum(len(v['warnings']) for v in validations)
    if total_warnings > 0:
        print(f"\n⚠️  Total Warnings: {total_warnings}")
        print(f"   (Review individual validations for details)")
    
    # Overall assessment
    print(f"\n{'='*70}")
    if failed == 0:
        print("✅ All validations passed! Analysis system is working correctly.")
    elif failed < total * 0.3:
        print("⚠️  Most validations passed, but some issues detected.")
    else:
        print("❌ Significant issues detected. Multiple validations failed.")
    print(f"{'='*70}")
    
    # Save results
    import json
    output_file = project_root / "output" / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    results = {
        'summary': {
            'total': total,
            'passed': passed,
            'failed': failed,
            'success_rate': passed/total*100 if total > 0 else 0
        },
        'validations': validations
    }
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Validation report saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    main()
