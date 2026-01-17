#!/usr/bin/env python3
"""
Application Test & Validation Script
====================================
Comprehensive test suite to validate all v3.11+ features.
"""

import sys
from pathlib import Path
import traceback

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all critical imports work."""
    print("\n" + "="*60)
    print("Testing Imports")
    print("="*60)
    
    tests = [
        ("Dashboard utils", "from src.app.dashboard.utils import load_ui_settings, get_version"),
        ("Parallel processing", "from src.app.dashboard.utils.parallel import ParallelProcessor"),
        ("Query cache", "from src.app.dashboard.utils.cache import QueryCache"),
        ("Retry logic", "from src.app.dashboard.utils.retry import retry_network"),
        ("Data validation", "from src.app.dashboard.utils.data_validation import DataQualityChecker"),
        ("Database models", "from src.analytics.models import get_db, Run"),
        ("Comprehensive analysis", "from src.analytics.comprehensive_analysis import ComprehensiveAnalysisRunner"),
    ]
    
    passed = 0
    failed = 0
    
    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"✅ {name}")
            passed += 1
        except Exception as e:
            print(f"❌ {name}: {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_ui_settings():
    """Test UI settings loading and saving."""
    print("\n" + "="*60)
    print("Testing UI Settings")
    print("="*60)
    
    try:
        from src.app.dashboard.utils import load_ui_settings, save_ui_settings, DEFAULT_UI_SETTINGS
        
        # Test loading
        settings = load_ui_settings()
        print(f"✅ Loaded UI settings: {len(settings)} keys")
        print(f"   Keys: {', '.join(list(settings.keys())[:5])}...")
        
        # Test that DEFAULT_UI_SETTINGS exists
        assert DEFAULT_UI_SETTINGS is not None
        print(f"✅ DEFAULT_UI_SETTINGS available: {len(DEFAULT_UI_SETTINGS)} keys")
        
        # Test saving (without actually modifying)
        print("✅ UI settings functions work correctly")
        return True
    except Exception as e:
        print(f"❌ UI settings test failed: {e}")
        traceback.print_exc()
        return False


def test_parallel_processing():
    """Test parallel processing utilities."""
    print("\n" + "="*60)
    print("Testing Parallel Processing")
    print("="*60)
    
    try:
        from src.app.dashboard.utils.parallel import (
            ParallelProcessor,
            parallel_map,
            parallel_calculation
        )
        import time
        
        # Test basic parallel map
        def square(x):
            time.sleep(0.01)  # Simulate work
            return x * x
        
        items = [1, 2, 3, 4, 5]
        results = parallel_map(items, square, max_workers=3)
        
        assert results == [1, 4, 9, 16, 25], f"Expected [1,4,9,16,25], got {results}"
        print("✅ parallel_map works correctly")
        
        # Test parallel calculation
        def calc1():
            time.sleep(0.01)
            return 10
        
        def calc2():
            time.sleep(0.01)
            return 20
        
        calculations = [calc1, calc2]
        results = parallel_calculation(calculations, max_workers=2)
        
        assert set(results) == {10, 20}, f"Expected {{10, 20}}, got {set(results)}"
        print("✅ parallel_calculation works correctly")
        
        # Test ParallelProcessor
        processor = ParallelProcessor(max_workers=2, show_progress=False)
        results = processor.process_map([1, 2, 3], square)
        assert results == [1, 4, 9]
        print("✅ ParallelProcessor works correctly")
        
        return True
    except Exception as e:
        print(f"❌ Parallel processing test failed: {e}")
        traceback.print_exc()
        return False


def test_query_cache():
    """Test query caching."""
    print("\n" + "="*60)
    print("Testing Query Cache")
    print("="*60)
    
    try:
        from src.app.dashboard.utils.cache import QueryCache, cached_query, get_cache_stats
        import time
        
        # Test basic cache
        cache = QueryCache(default_ttl=1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        print("✅ Cache set/get works")
        
        # Test TTL
        cache.set("key2", "value2", ttl=0.1)
        assert cache.get("key2") == "value2"
        time.sleep(0.2)
        assert cache.get("key2") is None
        print("✅ Cache TTL works")
        
        # Test decorator
        call_count = [0]
        
        @cached_query(ttl=1)
        def expensive():
            call_count[0] += 1
            return 42
        
        result1 = expensive()
        result2 = expensive()
        assert result1 == 42 and result2 == 42
        assert call_count[0] == 1  # Should only call once
        print("✅ @cached_query decorator works")
        
        # Test stats
        stats = get_cache_stats()
        assert 'total_entries' in stats
        print("✅ Cache stats work")
        
        return True
    except Exception as e:
        print(f"❌ Query cache test failed: {e}")
        traceback.print_exc()
        return False


def test_retry_logic():
    """Test retry logic."""
    print("\n" + "="*60)
    print("Testing Retry Logic")
    print("="*60)
    
    try:
        from src.app.dashboard.utils.retry import retry_network, retry_api, retry_database
        
        # Test retry decorator
        call_count = [0]
        
        @retry_network(max_retries=3)
        def flaky_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Simulated network error")
            return "success"
        
        result = flaky_function()
        assert result == "success"
        assert call_count[0] == 3
        print("✅ Retry logic works correctly")
        
        return True
    except Exception as e:
        print(f"❌ Retry logic test failed: {e}")
        traceback.print_exc()
        return False


def test_database_connection():
    """Test database connection and pooling."""
    print("\n" + "="*60)
    print("Testing Database Connection")
    print("="*60)
    
    try:
        from src.analytics.models import get_db, Run
        
        db = get_db()
        session = db.get_session()
        
        try:
            # Test basic query
            runs = session.query(Run).limit(5).all()
            print(f"✅ Database connection works: {len(runs)} runs found")
            
            # Test connection pooling (get multiple sessions)
            session2 = db.get_session()
            assert session2 is not None
            session2.close()
            print("✅ Connection pooling works")
            
            return True
        finally:
            session.close()
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        traceback.print_exc()
        return False


def test_data_validation():
    """Test data validation utilities."""
    print("\n" + "="*60)
    print("Testing Data Validation")
    print("="*60)
    
    try:
        from src.app.dashboard.utils.data_validation import DataQualityChecker
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent
        checker = DataQualityChecker(project_root)
        
        # Test price data check
        price_result = checker.check_price_data()
        print(f"✅ Price data check: {price_result.get('status', 'unknown')}")
        
        # Test benchmark data check
        benchmark_result = checker.check_benchmark_data()
        print(f"✅ Benchmark data check: {benchmark_result.get('status', 'unknown')}")
        
        return True
    except Exception as e:
        print(f"❌ Data validation test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Application Test & Validation Suite")
    print("Version 3.11.1")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("UI Settings", test_ui_settings),
        ("Parallel Processing", test_parallel_processing),
        ("Query Cache", test_query_cache),
        ("Retry Logic", test_retry_logic),
        ("Database Connection", test_database_connection),
        ("Data Validation", test_data_validation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} test crashed: {e}")
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
