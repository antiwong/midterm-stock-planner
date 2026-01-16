"""
Detailed Analysis Validation
============================
Creates multiple test watchlists and validates analysis results for reasonableness.
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

import subprocess
from src.analytics.models import get_db, Run
from src.analytics.analysis_service import AnalysisService
from src.app.dashboard.data import (
    load_run_scores,
    create_custom_watchlist,
    load_custom_watchlist_by_id
)


# Test watchlists with different characteristics
TEST_WATCHLISTS = {
    'tech_giants': {
        'name': 'Tech Giants Test',
        'symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA'],
        'description': 'Large cap technology stocks',
        'expected_sectors': ['Technology', 'Consumer Cyclical'],
        'min_stocks': 5
    },
    'diversified_blue_chips': {
        'name': 'Diversified Blue Chips Test',
        'symbols': ['JPM', 'JNJ', 'PG', 'WMT', 'V', 'MA', 'DIS'],
        'description': 'Diversified large cap stocks across sectors',
        'expected_sectors': ['Financial Services', 'Healthcare', 'Consumer Defensive', 'Consumer Cyclical'],
        'min_stocks': 5
    },
    'growth_stocks': {
        'name': 'Growth Stocks Test',
        'symbols': ['AMD', 'NFLX', 'SQ', 'ROKU', 'ZM', 'DOCU'],
        'description': 'High growth potential stocks',
        'expected_sectors': ['Technology', 'Communication Services'],
        'min_stocks': 4
    },
    'value_stocks': {
        'name': 'Value Stocks Test',
        'symbols': ['BRK.B', 'JPM', 'BAC', 'WFC', 'C'],
        'description': 'Value-oriented stocks',
        'expected_sectors': ['Financial Services'],
        'min_stocks': 3
    },
    'small_test': {
        'name': 'Small Test Watchlist',
        'symbols': ['AAPL', 'MSFT'],
        'description': 'Minimal test with 2 stocks',
        'expected_sectors': ['Technology'],
        'min_stocks': 2
    }
}


class AnalysisValidator:
    """Validates analysis results for reasonableness."""
    
    def __init__(self):
        self.validation_results = []
        self.analysis_service = AnalysisService()
    
    def create_test_watchlists(self) -> Dict[str, str]:
        """Create test watchlists and return their IDs."""
        created = {}
        
        print("\n" + "=" * 70)
        print("CREATING TEST WATCHLISTS")
        print("=" * 70)
        
        for watchlist_id, config in TEST_WATCHLISTS.items():
            try:
                # Check if watchlist exists
                existing = load_custom_watchlist_by_id(watchlist_id)
                if existing:
                    print(f"✅ Watchlist '{watchlist_id}' already exists")
                    created[watchlist_id] = watchlist_id
                    continue
                
                # Create watchlist
                result = create_custom_watchlist(
                    watchlist_id=watchlist_id,
                    name=config['name'],
                    symbols=config['symbols'],
                    description=config['description'],
                    category='validation_test'
                )
                
                if result:
                    print(f"✅ Created watchlist '{watchlist_id}' with {len(config['symbols'])} symbols")
                    created[watchlist_id] = watchlist_id
                else:
                    print(f"❌ Failed to create watchlist '{watchlist_id}'")
                
            except Exception as e:
                print(f"❌ Failed to create watchlist '{watchlist_id}': {e}")
                import traceback
                traceback.print_exc()
        
        return created
    
    def run_analysis(self, watchlist_id: str) -> Optional[str]:
        """Run analysis for a watchlist and return run_id."""
        print(f"\n📊 Running analysis for '{watchlist_id}'...")
        
        try:
            # Get watchlist
            watchlist = load_custom_watchlist_by_id(watchlist_id)
            if not watchlist:
                print(f"❌ Watchlist '{watchlist_id}' not found")
                return None
            
            symbols = watchlist.get('symbols', [])
            if not symbols:
                print(f"❌ Watchlist '{watchlist_id}' has no symbols")
                return None
            
            # Run analysis using the full analysis workflow script
            script_path = project_root / "scripts" / "full_analysis_workflow.py"
            cmd = [
                "python3",
                str(script_path),
                "--watchlist", watchlist_id,
                "--skip-validation"  # Skip validation to speed up test runs
            ]
            
            print(f"   Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                # Wait a moment for database to be updated
                import time
                time.sleep(2)
                
                # Get latest run from database for this watchlist
                db = get_db()
                session = db.get_session()
                try:
                    # Get the most recent run for this watchlist created in the last 5 minutes
                    from datetime import timedelta
                    cutoff_time = datetime.now() - timedelta(minutes=5)
                    
                    latest_run = session.query(Run).filter(
                        Run.watchlist == watchlist_id,
                        Run.created_at >= cutoff_time
                    ).order_by(Run.created_at.desc()).first()
                    
                    if latest_run:
                        print(f"✅ Analysis completed: {latest_run.run_id}")
                        return latest_run.run_id
                    else:
                        # Try without time filter (in case it took longer)
                        latest_run = session.query(Run).filter_by(
                            watchlist=watchlist_id
                        ).order_by(Run.created_at.desc()).first()
                        if latest_run:
                            print(f"✅ Analysis completed (found existing run): {latest_run.run_id}")
                            return latest_run.run_id
                        else:
                            print(f"⚠️  Analysis completed but no run found in database for watchlist '{watchlist_id}'")
                            return None
                finally:
                    session.close()
            else:
                print(f"❌ Analysis failed for '{watchlist_id}'")
                print(f"   Error: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"❌ Analysis timed out for '{watchlist_id}'")
            return None
        except Exception as e:
            print(f"❌ Error running analysis for '{watchlist_id}': {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def validate_run(self, run_id: str, watchlist_config: Dict) -> Dict[str, Any]:
        """Validate a single run's results."""
        validation = {
            'run_id': run_id,
            'watchlist_id': watchlist_config.get('watchlist_id'),
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
        validation['checks']['expected_min'] = watchlist_config.get('min_stocks', 1)
        
        if len(scores) < watchlist_config.get('min_stocks', 1):
            validation['warnings'].append(f"Only {len(scores)} stocks scored, expected at least {watchlist_config.get('min_stocks', 1)}")
        
        # Check 3: Score distribution is reasonable
        score_values = [s.get('score', 0) for s in scores if s.get('score') is not None]
        if score_values:
            validation['checks']['score_mean'] = float(np.mean(score_values))
            validation['checks']['score_std'] = float(np.std(score_values))
            validation['checks']['score_min'] = float(np.min(score_values))
            validation['checks']['score_max'] = float(np.max(score_values))
            validation['checks']['score_range'] = float(np.max(score_values) - np.min(score_values))
            
            # Scores should be in reasonable range (typically -1 to 1 or 0 to 100)
            if all(-2 <= s <= 2 for s in score_values):
                validation['checks']['score_range_valid'] = True
            elif all(0 <= s <= 100 for s in score_values):
                validation['checks']['score_range_valid'] = True
            else:
                validation['warnings'].append(f"Scores outside expected range: min={min(score_values):.3f}, max={max(score_values):.3f}")
            
            # Scores should have some variation
            if np.std(score_values) < 0.01:
                validation['warnings'].append("Scores have very low variation (std < 0.01), may indicate calculation issue")
        else:
            validation['errors'].append("No valid score values found")
            validation['passed'] = False
        
        # Check 4: Required fields present
        required_fields = ['ticker', 'score']
        for score in scores[:5]:  # Check first 5
            for field in required_fields:
                if field not in score:
                    validation['errors'].append(f"Missing required field '{field}' in scores")
                    validation['passed'] = False
        
        # Check 5: Sector distribution
        sectors = [s.get('sector', 'Unknown') for s in scores if s.get('sector')]
        if sectors:
            sector_counts = pd.Series(sectors).value_counts()
            validation['checks']['sectors'] = sector_counts.to_dict()
            validation['checks']['num_sectors'] = len(sector_counts)
            
            expected_sectors = watchlist_config.get('expected_sectors', [])
            if expected_sectors:
                found_sectors = set(sectors)
                expected_set = set(expected_sectors)
                overlap = found_sectors.intersection(expected_set)
                if len(overlap) == 0 and len(found_sectors) > 0:
                    validation['warnings'].append(f"Expected sectors {expected_sectors} but found {list(found_sectors)}")
        else:
            validation['warnings'].append("No sector information found")
        
        # Check 6: No duplicate tickers
        tickers = [s.get('ticker') for s in scores if s.get('ticker')]
        if len(tickers) != len(set(tickers)):
            validation['errors'].append("Duplicate tickers found in scores")
            validation['passed'] = False
        
        # Check 7: Rank ordering (if ranks exist)
        ranks = [s.get('rank') for s in scores if s.get('rank') is not None]
        if ranks:
            sorted_ranks = sorted(ranks)
            if sorted_ranks != list(range(1, len(sorted_ranks) + 1)):
                validation['warnings'].append("Ranks are not sequential starting from 1")
        
        # Check 8: Analysis results exist
        analysis_types = ['attribution', 'benchmark_comparison', 'factor_exposure']
        for analysis_type in analysis_types:
            result = self.analysis_service.get_analysis_result(run_id, analysis_type)
            if result:
                validation['checks'][f'{analysis_type}_exists'] = True
            else:
                validation['warnings'].append(f"Analysis result '{analysis_type}' not found")
        
        # Check 9: Data completeness
        # Check for missing critical data
        scores_with_data = [s for s in scores if s.get('score') is not None]
        if len(scores_with_data) < len(scores) * 0.8:  # At least 80% should have scores
            validation['warnings'].append(f"Only {len(scores_with_data)}/{len(scores)} stocks have scores")
        
        # Summary
        if validation['errors']:
            validation['passed'] = False
        
        return validation
    
    def print_validation_report(self, validations: List[Dict[str, Any]]):
        """Print detailed validation report."""
        print("\n" + "=" * 70)
        print("VALIDATION REPORT")
        print("=" * 70)
        
        total_runs = len(validations)
        passed_runs = sum(1 for v in validations if v['passed'])
        failed_runs = total_runs - passed_runs
        
        print(f"\n📊 Summary:")
        print(f"   Total runs validated: {total_runs}")
        print(f"   ✅ Passed: {passed_runs}")
        print(f"   ❌ Failed: {failed_runs}")
        print(f"   Success rate: {passed_runs/total_runs*100:.1f}%")
        
        # Detailed results
        print(f"\n{'='*70}")
        print("DETAILED RESULTS")
        print(f"{'='*70}")
        
        for validation in validations:
            status = "✅ PASSED" if validation['passed'] else "❌ FAILED"
            print(f"\n{status} - {validation['run_id'][:16]}... ({validation.get('watchlist_id', 'unknown')})")
            
            if validation['errors']:
                print(f"   Errors ({len(validation['errors'])}):")
                for error in validation['errors']:
                    print(f"     ❌ {error}")
            
            if validation['warnings']:
                print(f"   Warnings ({len(validation['warnings'])}):")
                for warning in validation['warnings']:
                    print(f"     ⚠️  {warning}")
            
            # Key metrics
            checks = validation.get('checks', {})
            if checks:
                print(f"   Key Metrics:")
                if 'num_scores' in checks:
                    print(f"     • Stocks scored: {checks['num_scores']}")
                if 'score_mean' in checks:
                    print(f"     • Average score: {checks['score_mean']:.3f}")
                if 'score_range' in checks:
                    print(f"     • Score range: {checks['score_min']:.3f} to {checks['score_max']:.3f}")
                if 'num_sectors' in checks:
                    print(f"     • Sectors: {checks['num_sectors']}")
        
        # Overall assessment
        print(f"\n{'='*70}")
        print("OVERALL ASSESSMENT")
        print(f"{'='*70}")
        
        if failed_runs == 0:
            print("✅ All validations passed! Analysis system is working correctly.")
        elif failed_runs < total_runs * 0.3:  # Less than 30% failed
            print("⚠️  Most validations passed, but some issues detected. Review failed runs.")
        else:
            print("❌ Significant issues detected. Multiple validations failed.")
        
        return {
            'total': total_runs,
            'passed': passed_runs,
            'failed': failed_runs,
            'success_rate': passed_runs/total_runs*100 if total_runs > 0 else 0
        }
    
    def run_full_validation(self) -> Dict[str, Any]:
        """Run full validation process."""
        print("=" * 70)
        print("DETAILED ANALYSIS VALIDATION")
        print("=" * 70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: Create test watchlists
        created_watchlists = self.create_test_watchlists()
        
        if not created_watchlists:
            print("❌ No watchlists created. Cannot proceed.")
            return {'error': 'No watchlists created'}
        
        # Step 2: Run analysis for each watchlist
        print("\n" + "=" * 70)
        print("RUNNING ANALYSES")
        print("=" * 70)
        
        run_ids = {}
        for watchlist_id in created_watchlists.keys():
            run_id = self.run_analysis(watchlist_id)
            if run_id:
                run_ids[watchlist_id] = run_id
        
        if not run_ids:
            print("❌ No analyses completed. Cannot validate.")
            return {'error': 'No analyses completed'}
        
        # Step 3: Validate each run
        print("\n" + "=" * 70)
        print("VALIDATING RESULTS")
        print("=" * 70)
        
        validations = []
        for watchlist_id, run_id in run_ids.items():
            config = TEST_WATCHLISTS[watchlist_id].copy()
            config['watchlist_id'] = watchlist_id
            validation = self.validate_run(run_id, config)
            validations.append(validation)
        
        # Step 4: Generate report
        summary = self.print_validation_report(validations)
        
        print(f"\n{'='*70}")
        print(f"Validation completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        
        return {
            'summary': summary,
            'validations': validations,
            'run_ids': run_ids
        }


def main():
    """Main validation function."""
    validator = AnalysisValidator()
    results = validator.run_full_validation()
    
    # Save results to file
    output_file = project_root / "output" / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    import json
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Validation report saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    main()
