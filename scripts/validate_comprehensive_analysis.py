#!/usr/bin/env python3
"""
Validate Comprehensive Analysis System
=======================================
Test and validate the comprehensive analysis system components.
"""

import sys
from pathlib import Path
import argparse

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all modules can be imported."""
    print("=" * 60)
    print("TEST 1: Module Imports")
    print("=" * 60)
    
    modules = [
        ("src.analytics.analysis_models", "Analysis Models"),
        ("src.analytics.analysis_service", "Analysis Service"),
        ("src.analytics.performance_attribution", "Performance Attribution"),
        ("src.analytics.benchmark_comparison", "Benchmark Comparison"),
        ("src.analytics.factor_exposure", "Factor Exposure"),
        ("src.analytics.rebalancing_analysis", "Rebalancing Analysis"),
        ("src.analytics.style_analysis", "Style Analysis"),
        ("src.analytics.comprehensive_analysis", "Comprehensive Analysis Runner"),
        ("src.analytics.data_loader", "Data Loader"),
    ]
    
    failed = []
    for module_name, display_name in modules:
        try:
            __import__(module_name)
            print(f"  ✅ {display_name}")
        except ImportError as e:
            print(f"  ❌ {display_name}: {e}")
            failed.append((display_name, str(e)))
        except Exception as e:
            print(f"  ⚠️  {display_name}: {e}")
            failed.append((display_name, str(e)))
    
    if failed:
        print(f"\n❌ {len(failed)} modules failed to import")
        return False
    else:
        print(f"\n✅ All {len(modules)} modules imported successfully")
        return True


def test_data_loader(run_dir):
    """Test data loader with a run directory."""
    print("\n" + "=" * 60)
    print("TEST 2: Data Loader")
    print("=" * 60)
    
    try:
        from src.analytics.data_loader import RunDataLoader
        
        if not Path(run_dir).exists():
            print(f"  ❌ Run directory not found: {run_dir}")
            return False
        
        loader = RunDataLoader(Path(run_dir))
        
        # Test loading methods
        tests = [
            ("Portfolio Returns", loader.load_portfolio_returns),
            ("Portfolio Weights", loader.load_portfolio_weights),
            ("Stock Features", loader.load_stock_features),
            ("Sector Mapping", loader.load_sector_mapping),
            ("Backtest Metrics", loader.load_backtest_metrics),
        ]
        
        results = {}
        for name, method in tests:
            try:
                result = method()
                if result is not None:
                    if isinstance(result, dict):
                        print(f"  ✅ {name}: {len(result)} items")
                    elif hasattr(result, '__len__'):
                        print(f"  ✅ {name}: {len(result)} rows/items")
                    else:
                        print(f"  ✅ {name}: Loaded")
                else:
                    print(f"  ⚠️  {name}: No data (may be expected)")
                results[name] = result
            except Exception as e:
                print(f"  ❌ {name}: {e}")
                results[name] = None
        
        # Test full portfolio data load
        try:
            portfolio_data = loader.load_portfolio_data()
            if portfolio_data:
                print(f"\n  ✅ Portfolio Data Loaded:")
                print(f"     - Returns: {'✓' if portfolio_data.get('returns') is not None else '✗'}")
                print(f"     - Weights: {'✓' if portfolio_data.get('weights') is not None else '✗'}")
                print(f"     - Holdings: {len(portfolio_data.get('holdings', []))} stocks")
                print(f"     - Date Range: {portfolio_data.get('start_date')} to {portfolio_data.get('end_date')}")
                return True
            else:
                print(f"  ❌ Failed to load portfolio data")
                return False
        except Exception as e:
            print(f"  ❌ Portfolio data load failed: {e}")
            return False
            
    except Exception as e:
        print(f"  ❌ Data loader test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_analysis_modules(run_dir):
    """Test that analysis modules can be instantiated."""
    print("\n" + "=" * 60)
    print("TEST 3: Analysis Module Instantiation")
    print("=" * 60)
    
    try:
        from src.analytics.performance_attribution import PerformanceAttributionAnalyzer
        from src.analytics.benchmark_comparison import BenchmarkComparator
        from src.analytics.factor_exposure import FactorExposureAnalyzer
        from src.analytics.rebalancing_analysis import RebalancingAnalyzer
        from src.analytics.style_analysis import StyleAnalyzer
        from src.analytics.data_loader import RunDataLoader
        
        modules = [
            ("Performance Attribution", PerformanceAttributionAnalyzer),
            ("Benchmark Comparison", BenchmarkComparator),
            ("Factor Exposure", FactorExposureAnalyzer),
            ("Rebalancing Analysis", RebalancingAnalyzer),
            ("Style Analysis", StyleAnalyzer),
        ]
        
        for name, cls in modules:
            try:
                instance = cls()
                print(f"  ✅ {name}")
            except Exception as e:
                print(f"  ❌ {name}: {e}")
                return False
        
        # Test data loader
        loader = RunDataLoader(Path(run_dir))
        portfolio_data = loader.load_portfolio_data()
        
        if not portfolio_data:
            print(f"\n  ⚠️  No portfolio data loaded - some tests may be skipped")
        else:
            returns = portfolio_data.get('returns')
            has_returns = returns is not None and (hasattr(returns, '__len__') and len(returns) > 0 if hasattr(returns, '__len__') else returns is not None)
            if not has_returns:
                print(f"\n  ⚠️  No portfolio returns data - some tests may be skipped")
            else:
                print(f"\n  ✅ Portfolio data available for testing")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Module instantiation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_connection(db_path="data/analysis.db"):
    """Test database connection and schema."""
    print("\n" + "=" * 60)
    print("TEST 4: Database Connection")
    print("=" * 60)
    
    try:
        from src.analytics.models import get_db
        
        db = get_db(db_path)
        session = db.get_session()
        
        try:
            # Test that we can query
            from src.analytics.models import Run
            runs = session.query(Run).limit(1).all()
            print(f"  ✅ Database connection successful")
            print(f"  ✅ Can query runs table")
            
            # Check for analysis tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            analysis_tables = [
                'analysis_results',
                'ai_insights',
                'recommendations',
                'benchmark_comparisons',
                'factor_exposures',
                'performance_attributions'
            ]
            
            print(f"\n  Database tables ({len(tables)} total):")
            for table in analysis_tables:
                if table in tables:
                    print(f"    ✅ {table}")
                else:
                    print(f"    ⚠️  {table} (not found - will be created on first use)")
            
            return True
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_analysis_service(db_path="data/analysis.db"):
    """Test analysis service."""
    print("\n" + "=" * 60)
    print("TEST 5: Analysis Service")
    print("=" * 60)
    
    try:
        from src.analytics.analysis_service import AnalysisService
        
        service = AnalysisService(db_path)
        print(f"  ✅ AnalysisService instantiated")
        
        # Test that methods exist
        methods = [
            'save_analysis_result',
            'get_analysis_result',
            'save_ai_insight',
            'get_ai_insight',
            'save_recommendations',  # Note: plural
            'get_recommendations',
        ]
        
        for method in methods:
            if hasattr(service, method):
                print(f"  ✅ Method: {method}")
            else:
                print(f"  ❌ Method missing: {method}")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Analysis service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Validate comprehensive analysis system')
    parser.add_argument('--run-dir', type=Path, help='Run directory to test with')
    parser.add_argument('--db-path', type=str, default='data/analysis.db', help='Database path')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("COMPREHENSIVE ANALYSIS SYSTEM VALIDATION")
    print("=" * 60)
    print()
    
    results = []
    
    # Test 1: Imports
    results.append(("Imports", test_imports()))
    
    # Test 2: Data Loader (if run_dir provided)
    if args.run_dir:
        results.append(("Data Loader", test_data_loader(args.run_dir)))
    else:
        print("\n" + "=" * 60)
        print("TEST 2: Data Loader (SKIPPED - no run-dir provided)")
        print("=" * 60)
        print("  ⚠️  Use --run-dir to test data loading")
        results.append(("Data Loader", None))
    
    # Test 3: Module Instantiation
    if args.run_dir:
        results.append(("Module Instantiation", test_analysis_modules(args.run_dir)))
    else:
        results.append(("Module Instantiation", test_analysis_modules("output")))
    
    # Test 4: Database
    results.append(("Database Connection", test_database_connection(args.db_path)))
    
    # Test 5: Analysis Service
    results.append(("Analysis Service", test_analysis_service(args.db_path)))
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    
    for test_name, result in results:
        if result is True:
            print(f"  ✅ {test_name}")
        elif result is False:
            print(f"  ❌ {test_name}")
        else:
            print(f"  ⚠️  {test_name} (skipped)")
    
    print()
    print(f"Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    
    if failed == 0:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
